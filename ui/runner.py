"""
ScriptRunner — QThread that runs a backend VectorCAST script via subprocess,
streaming real-time stdout/stderr line-by-line to the UI console.

Strategy
--------
Each backend script (vcast_auto_compile3.py, vcast_batch_compile.py,
vcast_it_manual_compilation.py) stores its configuration in module-level
globals.  To inject the user's form-field values we generate a small
temporary *wrapper* script that:

  1. Adds the scripts/ directory to sys.path
  2. Imports the real script as a module
  3. Overrides every relevant global with the value from the UI
  4. Calls main()

The wrapper is written to WORK_DIR (or a temp dir) and run via
``subprocess.Popen`` so the GUI process is fully isolated from
``os.chdir`` / ``sys.exit`` / global state mutations inside the scripts.

FIX (IndentationError):
  The original code used textwrap.dedent(f-string) to generate the wrapper.
  Because the f-string body was indented 12 spaces (inside the class method),
  and injected {overrides_block} lines were joined with "\n    ", dedent
  produced a file where override lines had inconsistent indentation relative
  to the surrounding top-level code — causing IndentationError on every run.

  The fix builds the wrapper by joining a plain list of strings, one per line,
  so indentation is always exactly what is written — no dedent, no f-string
  template magic.
"""

import contextlib
import os
import platform
import sys
import time
import tempfile
import subprocess
from PySide6.QtCore import QThread, Signal

from app_paths import app_root, is_frozen

_STOP_EXIT_CODE = 2


class ScriptRunner(QThread):
    """
    Signals
    -------
    log_line(text, kind)
        Append a line to the console.  *kind* is one of:
        ``ok`` / ``err`` / ``info`` / ``warn`` / ``dim``
    finished(passed, elapsed_secs, name)
        Emitted when the subprocess exits.
    """
    log_line = Signal(str, str)
    finished = Signal(bool, float, str)

    def __init__(
        self,
        name: str,
        script_path: str,
        overrides: dict,
        *,
        parent=None,
    ):
        """
        Parameters
        ----------
        name : str
            Human-readable label (shown in logs tab).
        script_path : str
            Absolute path to the backend .py script to run.
        overrides : dict
            ``{GLOBAL_NAME: value}`` pairs to inject into the script.
            Values will be ``repr()``-ed into the wrapper.
        """
        super().__init__(parent)
        self._name = name
        self._script_path = os.path.abspath(script_path)
        self._overrides = overrides
        self._proc = None
        self._stop_requested = False
        self._stopped = False
        self._stop_file = ""

    @staticmethod
    def _kill_process_tree(pid: int) -> None:
        if pid <= 0:
            return
        if platform.system() == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            try:
                os.killpg(os.getpgid(pid), 15)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    os.kill(pid, 15)
                except (ProcessLookupError, PermissionError, OSError):
                    pass

    def _signal_stop(self) -> None:
        """Write the cooperative stop flag consumed by backend scripts."""
        if not self._stop_file:
            return
        try:
            with open(self._stop_file, "w", encoding="utf-8") as f:
                f.write("stop\n")
        except OSError:
            pass

    def stop(self):
        """Request cancellation of the running compilation subprocess."""
        if self._stop_requested:
            return
        self._stop_requested = True
        self._stopped = True
        self._signal_stop()
        proc = self._proc
        if proc is not None and proc.poll() is None:
            self._kill_process_tree(proc.pid)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

    # ── classify output lines ─────────────────────────────────────────────
    @staticmethod
    def _classify(line: str) -> str:
        upper = line.upper()
        if "[SUCCESS]" in upper or "[PASS]" in upper or "[OK]" in upper:
            return "ok"
        if "[FAIL" in upper or "[ERROR" in upper:
            return "err"
        if "[WARN" in upper:
            return "warn"
        if "[STEP" in upper or "[INIT" in upper or "[COMP" in upper or "[SCAN" in upper:
            return "info"
        if line.startswith("─") or line.startswith("═") or line.startswith("==="):
            return "dim"
        return "info"

    # ── generate the wrapper script ───────────────────────────────────────
    def _make_wrapper(self) -> str:
        """
        Return the text of a self-contained wrapper .py file that:
          1. Loads the backend script as a module
          2. Overrides its globals with UI-provided values
          3. Calls main()

        IMPORTANT: Built by joining a plain list of strings (one per line)
        rather than textwrap.dedent(f-string).  The dedent approach caused
        IndentationError because injected override lines had different leading
        whitespace than the surrounding template lines after dedent ran.
        """
        script_path_r       = repr(self._script_path)
        scripts_dir_r       = repr(os.path.dirname(self._script_path))
        app_root_r          = repr(app_root())
        module_stem         = os.path.splitext(os.path.basename(self._script_path))[0]
        module_stem_r       = repr(module_stem)

        # One top-level assignment per override — all at column 0
        override_lines = [f"mod.{k} = {repr(v)}" for k, v in self._overrides.items()]
        overrides_block = "\n".join(override_lines) if override_lines else "# no overrides"

        lines = [
            "import sys, os, builtins, importlib.util",
            "",
            "# Suppress interactive prompts so scripts never block waiting for input",
            "builtins.input = lambda prompt='': None",
            "",
            "# Add app + scripts directories so backend imports resolve when bundled",
            f"sys.path.insert(0, {app_root_r})",
            f"sys.path.insert(0, {scripts_dir_r})",
            "",
            "# Force UTF-8 console output (avoids Windows charmap decode errors in GUI pipe)",
            "try:",
            "    from stdio_utils import ensure_utf8_stdio",
            "    ensure_utf8_stdio()",
            "except ImportError:",
            "    pass",
            "",
            "# Load the backend script as a Python module object",
            f"_spec = importlib.util.spec_from_file_location({module_stem_r}, {script_path_r})",
            "mod = importlib.util.module_from_spec(_spec)",
            "",
            "# Suppress GUI/PowerShell popups before exec so the module body is safe",
            "mod.show_alert = lambda title, message, icon='Information': None",
            "",
            "_spec.loader.exec_module(mod)",
            "",
            "# ── Inject UI field values as module globals ─────────────────────────",
            overrides_block,
            "",
            "# ── Cooperative stop (Stop button in UI) ─────────────────────────────",
            "import stop_control",
            f"stop_control.configure({repr(self._stop_file)})",
            "if hasattr(mod, 'STOP_FILE'):",
            f"    mod.STOP_FILE = {repr(self._stop_file)}",
            "",
            "# ── Re-derive file paths that depend on the overridden globals ───────",
            "if hasattr(mod, 'WORK_DIR') and hasattr(mod, 'ENV_NAME'):",
            "    mod.BUILD_LOG    = os.path.join(mod.WORK_DIR, 'build_log.txt')",
            "    mod.DETAILED_LOG = os.path.join(mod.WORK_DIR, 'detailed_log.txt')",
            "    mod.ERROR_LOG    = os.path.join(mod.WORK_DIR, 'error_log.txt')",
            "    mod.ENV_SCRIPT   = os.path.join(mod.WORK_DIR, mod.ENV_NAME + '.env')",
            "    mod.CFG_FILE     = os.path.join(mod.WORK_DIR, 'CCAST_.CFG')",
            "if hasattr(mod, 'VECTORCAST_DIR'):",
            "    mod.CLICAST_EXE = os.path.join(mod.VECTORCAST_DIR, 'clicast.exe')",
            "if hasattr(mod, 'WORKSPACE_ROOT'):",
            "    mod.BATCH_LOG = os.path.join(mod.WORKSPACE_ROOT, 'batch_compile_log.txt')",
            "if hasattr(mod, 'COMPILE_SCRIPT'):",
            f"    mod.COMPILE_SCRIPT = os.path.join({scripts_dir_r}, 'vcast_auto_compile3.py')",
            "",
            "# ── Override fail() to print + exit instead of showing a GUI alert ───",
            "def _fail_wrapper(reason):",
            "    print('[FAILED] ' + str(reason))",
            "    sys.exit(1)",
            "if hasattr(mod, 'fail'):",
            "    mod.fail = _fail_wrapper",
            "",
            "# ── Run ──────────────────────────────────────────────────────────────",
            "try:",
            "    _result = mod.main()",
            "    # Honour integer return codes (0 = success, non-zero = failure).",
            "    # bool is a subclass of int in Python, so check bool first.",
            "    if isinstance(_result, bool):",
            "        sys.exit(0 if _result else 1)",
            "    elif isinstance(_result, int):",
            "        sys.exit(_result)",
            "    # None / no return value → treat as success",
            "except SystemExit as _e:",
            "    sys.exit(_e.code if _e.code is not None else 0)",
            "except Exception as _exc:",
            "    print('[ERROR] ' + str(_exc))",
            "    import traceback",
            "    traceback.print_exc()",
            "    sys.exit(1)",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _subprocess_env() -> dict:
        env = {**os.environ}
        env["PYTHONIOENCODING"] = "utf-8:replace"
        env["PYTHONUTF8"] = "1"
        env["LC_ALL"] = "C"
        env["LANG"] = "C"
        return env

    def _stream_output(self, proc) -> int:
        self._proc = proc
        try:
            while True:
                if self._stop_requested:
                    if proc.poll() is None:
                        self._kill_process_tree(proc.pid)
                    break
                line = proc.stdout.readline()
                if not line:
                    break
                line = line.rstrip("\n\r")
                self.log_line.emit(line, self._classify(line))
            proc.wait()
            if self._stop_requested or proc.returncode == _STOP_EXIT_CODE:
                self._stopped = True
                return _STOP_EXIT_CODE
            return proc.returncode
        finally:
            self._proc = None

    def _run_inprocess(self, wrapper_code: str, work_dir: str) -> int:
        """Run the wrapper inside the GUI process (required for frozen .exe builds)."""
        old_cwd = os.getcwd()

        class _EmitWriter:
            def __init__(self, emit):
                self._emit = emit
                self._buf = ""

            def write(self, text: str) -> int:
                if not text:
                    return 0
                self._buf += text
                while "\n" in self._buf:
                    line, self._buf = self._buf.split("\n", 1)
                    if line:
                        self._emit(line)
                return len(text)

            def flush(self) -> None:
                if self._buf:
                    self._emit(self._buf)
                    self._buf = ""

        writer = _EmitWriter(lambda line: self.log_line.emit(line, self._classify(line)))
        namespace = {"__name__": "__main__"}

        try:
            if work_dir and os.path.isdir(work_dir):
                os.chdir(work_dir)
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                exec(compile(wrapper_code, "<vcast_wrapper>", "exec"), namespace)
            return 0
        except SystemExit as exc:
            code = exc.code
            if code == _STOP_EXIT_CODE:
                self._stopped = True
                return _STOP_EXIT_CODE
            if code is None:
                return 0
            if isinstance(code, bool):
                return 0 if code else 1
            return int(code)
        finally:
            writer.flush()
            os.chdir(old_cwd)

    # ── thread body ───────────────────────────────────────────────────────
    def run(self):
        t0 = time.time()
        passed = False

        # Determine work directory (use WORK_DIR override if available)
        work_dir = self._overrides.get("WORK_DIR", "") or \
                   self._overrides.get("WORKSPACE_ROOT", "")
        if work_dir:
            os.makedirs(work_dir, exist_ok=True)

        stop_dir = work_dir if work_dir and os.path.isdir(work_dir) else tempfile.gettempdir()
        self._stop_file = os.path.join(stop_dir, ".vcast_stop")
        try:
            if os.path.isfile(self._stop_file):
                os.remove(self._stop_file)
        except OSError:
            pass

        # Write wrapper to a temp file in WORK_DIR (or system temp)
        try:
            wrapper_code = self._make_wrapper()
            fd, wrapper_path = tempfile.mkstemp(
                suffix=".py",
                prefix="vcast_runner_",
                dir=work_dir if work_dir and os.path.isdir(work_dir) else None,
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(wrapper_code)
        except Exception as e:
            self.log_line.emit(f"[ERROR] Failed to create wrapper script: {e}", "err")
            self.finished.emit(False, time.time() - t0, self._name)
            return

        self.log_line.emit("══════════════════════════════════════════════════", "info")
        self.log_line.emit("  VectorCAST Automotive Compilation Tool", "info")
        self.log_line.emit("══════════════════════════════════════════════════", "info")
        self.log_line.emit("", "dim")
        self.log_line.emit(f"[INIT] Script: {os.path.basename(self._script_path)}", "ok")
        self.log_line.emit(f"[INIT] Module: {self._name}", "ok")
        self.log_line.emit(f"[INIT] Launching subprocess...", "info")
        self.log_line.emit("", "dim")

        try:
            cwd = work_dir if work_dir and os.path.isdir(work_dir) else None
            if is_frozen():
                return_code = self._run_inprocess(wrapper_code, cwd or "")
            else:
                proc = subprocess.Popen(
                    [sys.executable, wrapper_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    cwd=cwd,
                    env=self._subprocess_env(),
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return_code = self._stream_output(proc)
            if return_code == _STOP_EXIT_CODE:
                self._stopped = True
            passed = return_code == 0 and not self._stopped

            self.log_line.emit("", "dim")
            if self._stopped:
                self.log_line.emit(
                    "────── STOPPED  |  Cancelled by user ──────", "warn"
                )
            elif passed:
                self.log_line.emit(
                    "────── DONE  |  Exit 0  |  Status: PASS ──────", "ok"
                )
            else:
                self.log_line.emit(
                    f"────── DONE  |  Exit {return_code}  |  Status: FAIL ──────",
                    "err",
                )

        except FileNotFoundError:
            self.log_line.emit(
                f"[ERROR] Python executable not found: {sys.executable}", "err"
            )
        except Exception as e:
            self.log_line.emit(f"[ERROR] Subprocess error: {e}", "err")
        finally:
            try:
                os.remove(wrapper_path)
            except OSError:
                pass
            try:
                if self._stop_file and os.path.isfile(self._stop_file):
                    os.remove(self._stop_file)
            except OSError:
                pass

        elapsed = time.time() - t0
        self.finished.emit(passed, elapsed, self._name)
