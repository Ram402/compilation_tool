# VectorCAST — Automotive Software Verification Suite
### PySide6 Desktop Application

---

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

---

## File Structure

```
vcast_app/
│
├── main.py                  ← Entry point
├── theme.qss                ← Full automotive QSS stylesheet
├── requirements.txt
│
└── ui/
    ├── main_window.py       ← Main window: hero, stats bar, tabs, footer
    ├── widgets.py           ← AccentStrip, HeroHeader, StatsBar, FooterBar,
    │                           SectionBanner, ConsoleWidget, FieldRow,
    │                           SectionSep, DynamicList, StatusBadge
    ├── style_helpers.py     ← UI_FONT / MONO_FONT / DISPLAY_FONT helpers
    ├── runner.py            ← CompileRunner QThread (sim → replace with real)
    ├── module_table.py      ← Editable UUT_NAME / UUT_FILE table widget
    ├── tab_batch.py         ← UT Compilation tab
    ├── tab_integration.py   ← Integration Test tab
    ├── tab_excel.py         ← Import Excel tab
    └── tab_logs.py          ← Logs tab
```

---

## Connecting to Your Real Scripts

Open `ui/runner.py` and replace the `run()` method's simulation with a
`subprocess.Popen` call to your actual VectorCAST scripts:

```python
# ui/runner.py  — real implementation skeleton
import subprocess, os

def run(self):
    cmd = [
        "python", self._script_path,
        "--vcast-dir", self._vcast_dir,
        "--env",       self._env_name,
        "--work-dir",  self._work_dir,
        "--uut",       self._uut_name,
        "--defines",   self._defines,
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=self._work_dir or ".",
    )
    passed = False
    t0 = time.time()
    for line in proc.stdout:
        line = line.rstrip()
        # Classify the line
        kind = "ok"  if "PASS"  in line else \
               "err" if "FAIL"  in line or "ERROR" in line else \
               "warn" if "WARN" in line else \
               "info"
        self.log_line.emit(line, kind)
    proc.wait()
    passed  = proc.returncode == 0
    elapsed = time.time() - t0
    self.finished.emit(passed, elapsed, self._name)
```

Each tab's `_run()` method builds the runner — wire in the form field
values as constructor arguments, then update runner's `__init__` to accept them.

---

## Automotive Theme Reference

| Token        | Hex       | Use                    |
|--------------|-----------|------------------------|
| `--black`    | `#060810` | page background        |
| `--dark1`    | `#0d1117` | tab bar / side panels  |
| `--dark2`    | `#111820` | stats bar / toolbars   |
| `--dark3`    | `#172030` | input fields           |
| `--border`   | `#1e2d3d` | all borders            |
| `--red`      | `#e63946` | primary action / brand |
| `--blue`     | `#00b4d8` | info / secondary       |
| `--green`    | `#2dc653` | PASS / status OK       |
| `--errclr`   | `#ff4d6d` | FAIL / error           |
| `--amber`    | `#f4a261` | WARN / in-progress     |
| `--text`     | `#d6e4f0` | primary text           |
| `--muted`    | `#5e7a8a` | labels / placeholders  |
| `--metal`    | `#8fa8bc` | secondary text         |

---

## Optional: Offline Background Images

Place automotive JPEGs in `assets/` and update the URL constants in
`widgets.py` (`HeroHeader.BG_URL`) and each `SectionBanner` IMG constant
to `file:///absolute/path/to/assets/hero.jpg` — the fallback gradient
activates automatically when images can't load.
