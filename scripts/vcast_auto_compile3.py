"""
VectorCAST Automated Compilation Script
  - AUTO MISSING-HEADER RESOLUTION
  - AUTO MACRO EXPANSION ERROR BACKTRACING & FIX  (P2VAR / FUNC / VAR / P2CONST etc.)

HOW THE MACRO FIX WORKS
========================
AUTOSAR/MCAL headers define macros like P2VAR, FUNC, VAR twice:

    #if defined(MCAL_SUPPORT_MOBILGENE_1_0) || defined(MCAL_SUPPORT_MOBILGENE_2_0)
    #define P2VAR(ptrtype, memclass, ptrclass)   ptrtype *          <-- simple, safe
    #else
    #define P2VAR(ptrtype, memclass, ptrclass)   ptrclass ptrtype * memclass  <-- breaks MinGW
    #endif

VectorCAST uses MinGW which has neither guard defined → falls into #else → broken expansion.

Fix:
  1. Detect "expected X before Y" parse errors in the log.
  2. If the error is ON a #define line (e.g. line 479 in #else), walk upward
     in the same file to the controlling #if (e.g. line 476) and pick one guard
     from defined(MCAL_...) || defined(MCAL_...).
  3. Otherwise read the offending line, extract CAPS_MACRO( calls, and search
     the project for all #define occurrences (preferring the error file first).
  4. Identify which definition is inside an #else block and which #if guards it.
  5. FALLBACK: when project-wide backtrace cannot resolve the error (last file
     in the include chain), scan upward from the error line in that same file.
  6. Add the chosen guard macro as a C_DEFINE_LIST entry in CCAST_.CFG and rebuild.
"""

import os, sys, re, shutil, subprocess, platform, time

from stdio_utils import ensure_utf8_stdio
from stop_control import check as check_stop, is_requested as stop_requested

# Suppress console windows on Windows for all subprocess calls
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0

ensure_utf8_stdio()

from datetime import datetime

# ============================================================================
# CONFIGURATION  – edit these values for each project
# ============================================================================

VECTORCAST_DIR = r"C:\VCAST"
ENV_NAME       = "PDC_OptionProcessingConfirm"
WORK_DIR       = r"D:\Rama\Workspace_UT\PDC_OptionProcessingConfirm"

BASE_DIR_NAME  = "R"
BASE_DIR_PATH  = r"D:\project_4\BC4i_P E2.0_B2412\B2412"

SOURCE_DIR_1   = rf"{BASE_DIR_PATH}\Static_Code\KSC\SYSTEMS\Interface\Option_Processing_Confirm"
SOURCE_DIR_2   = ""
SOURCE_DIR_3   = ""

UUT_FILE       = "PDC_OptionProcessingConfirm"

# Extended at runtime by macro-fix engine – do NOT hardcode MCAL guards here,
# the script discovers and adds them automatically.
DEFINES: list = ["__USE_MINGW_ANSI_STDIO"]

EXTRA_INCLUDE_1 = ""
EXTRA_INCLUDE_2 = ""
EXTRA_INCLUDE_3 = ""

HEADER_SEARCH_ROOT = BASE_DIR_PATH
MAX_RETRY_ROUNDS   = 100
STOP_FILE          = ""   # set by GUI wrapper; polled for Stop button

# ============================================================================
# DERIVED PATHS  (do not edit)
# ============================================================================
BUILD_LOG    = os.path.join(WORK_DIR, "build_log.txt")
DETAILED_LOG = os.path.join(WORK_DIR, "detailed_log.txt")
ERROR_LOG    = os.path.join(WORK_DIR, "error_log.txt")
CLICAST_EXE  = os.path.join(VECTORCAST_DIR, "clicast.exe")
ENV_SCRIPT   = os.path.join(WORK_DIR, f"{ENV_NAME}.env")
CFG_FILE     = os.path.join(WORK_DIR, "CCAST_.CFG")

# ============================================================================
# LOGGING
# ============================================================================

def log(msg: str, also_print: bool = True) -> None:
    with open(DETAILED_LOG, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    if also_print:
        print(msg)


def show_alert(title: str, message: str, icon: str = "Information") -> None:
    ps = (
        "Add-Type -AssemblyName PresentationFramework; "
        f"[System.Windows.MessageBox]::Show('{message}', '{title}', 'OK', '{icon}')"
    )
    subprocess.run(["powershell", "-command", ps],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   creationflags=_NO_WINDOW)


def fail(reason: str) -> None:
    log(f"\n[FAILED] {reason}")
    print(f"\nLog files:\n  {BUILD_LOG}\n  {ERROR_LOG}\n  {DETAILED_LOG}")
    show_alert("VectorCAST Build Failed",
               f"FAILED: {ENV_NAME}\\n{reason}\\nLogs: {WORK_DIR}", "Error")
    input("\nPress Enter to exit...")
    sys.exit(1)


# ============================================================================
# SHARED UTILITY
# ============================================================================

def squash_file(path: str) -> str:
    """Read file and collapse every whitespace run to a single space."""
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return re.sub(r"\s+", " ", f.read())


def normalize_log_text(text: str) -> str:
    """
    Collapse whitespace and repair identifiers split across wrapped log lines.
    VectorCAST often breaks long paths like 'Rte_QuarterGlassCurtain.h' into
    'Rte _QuarterGlassCurtain.h' which breaks filename regexes.
    """
    text = re.sub(r"\s+", " ", text.strip())
    for _ in range(20):
        repaired = re.sub(
            r"(\b[A-Za-z0-9]+)\s+(_[A-Za-z0-9][A-Za-z0-9_]*)",
            r"\1\2",
            text,
        )
        if repaired == text:
            break
        text = repaired
    return text


def combine_logs(log_paths: tuple) -> str:
    """Squash and normalize one or more compiler log files for regex parsing."""
    return normalize_log_text(" ".join(squash_file(p) for p in log_paths))


def read_lines(path: str) -> list:
    """Return list of text lines from path, or [] on failure."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()
    except OSError:
        return []


def find_file_under(root: str, filename: str, path_hint: str = "") -> str:
    """
    Case-insensitive search for filename under root.
    When multiple matches exist (e.g. several Compiler.h files), prefer the
    one whose path best matches path_hint (e.g. 'GHS/Compiler.h').
    """
    target = os.path.basename(filename.replace("\\", "/")).lower()
    hint = (path_hint or filename).replace("\\", "/").lower()
    hint_parts = [p for p in hint.split("/") if p and p != target]

    candidates: list[str] = []
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower() == target:
                candidates.append(os.path.join(dirpath, fn))

    if not candidates:
        return ""
    if len(candidates) == 1:
        return candidates[0]

    best = candidates[0]
    best_score = -1
    for candidate in candidates:
        c_norm = candidate.replace("\\", "/").lower()
        score = sum(1 for part in hint_parts if part in c_norm)
        if score > best_score:
            best_score = score
            best = candidate
    return best


def _basename_from_log_ref(file_ref: str) -> str:
    return os.path.basename(file_ref.replace("\\", "/"))


# ============================================================================
# MISSING-HEADER DETECTION
# ============================================================================

_MISSING_RE = re.compile(
    r"fatal\s+error\s*:\s*"
    r"(?:[^\s:]+[\\/])?"
    r"([^\s/\\:]+\.h)"
    r"\s*:\s*"
    r"No\s+such\s+file\s+or\s+directory",
    re.IGNORECASE,
)


def extract_missing_headers(*log_paths) -> list:
    missing = set()
    for path in log_paths:
        for m in _MISSING_RE.finditer(squash_file(path)):
            hdr = m.group(1)
            missing.add(hdr)
            log(f"    [MISSING HEADER] {hdr}", also_print=False)
    return sorted(missing)


# ============================================================================
# MACRO ERROR DETECTION & AUTO-FIX ENGINE
# ============================================================================
#
# BUG FIXES vs previous version:
#  1. Log is squashed before regex so wrapped lines are matched.
#  2. Regex anchored to just the basename (VectorCAST prefixes paths
#     with indentation that becomes spaces after squash).
#  3. _find_all_macro_definitions returns ALL occurrences, not just the first.
#     We look for the one inside an #else block.
#  4. CCAST_.CFG is fully rewritten each attempt from DEFINES[], so we never
#     lose or duplicate entries across retries.

# After squashing, error lines appear in two formats:
#
#   VectorCAST internal log (pipe-separated):
#     "... App_Variable.h : 2818 | 18: error: expected ';' before 'void' ..."
#
#   GCC / vcqik.ERR direct output (colon-separated, optional column):
#     "App_Variable.h:2818:5: error: expected ';' before 'void'"
#     "App_Variable.h:2818: error: expected ';' before 'void'"
#
# File reference in logs — may include subdirs such as GHS/Compiler.h
_LOG_FILE_REF = r"([\w./\\-]+\.(?:h|c|cpp))"

# The regex below covers both formats.
# Capture: group(1)=file ref, group(2)=line number
_MACRO_ERR_RE = re.compile(
    _LOG_FILE_REF +
    r"\s*[:|]\s*(\d+)"                  # :line  or  | line
    r"(?:\s*[:|]\s*\d+)?"              # optional :col  (gcc format)
    r"\s*[:|]\s*(?:\d+\s*[:|]\s*)?"   # optional VectorCAST pipe col
    r"error\s*:\s*"
    r"expected\s+.+?\s+before\s+'?[\w_]+'?",
    re.IGNORECASE,
)

# ── #error "Please specify compiler." detector ───────────────────────────────
# Matches lines like:
#   Crypto_76_HaeModule_MemMap.h:88: error: #error "Please specify compiler."
# Captures group(1)=filename, group(2)=line number
_HASH_ERROR_RE = re.compile(
    r"([\w.]+\.h)"
    r"\s*[:|]\s*(\d+)"
    r"(?:\s*[:|]\s*\d+)?"
    r"\s*[:|]\s*(?:\d+\s*[:|]\s*)?"
    r'error\s*:\s*#\s*error\b[^"]*"([^"]*)"',
    re.IGNORECASE,
)

# Any ALL-CAPS identifier followed by (
_MACRO_CALL_RE = re.compile(r"\b([A-Z][A-Z0-9_]{2,})\s*\(")

# #define MACRONAME(  – captures name
_DEFINE_RE = re.compile(r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\s*\(")

# All defined(GUARD) occurrences on one line
_DEFINED_ARGS_RE = re.compile(r"defined\s*\(\s*([A-Z0-9_]+)\s*\)", re.IGNORECASE)

# #ifdef GUARD  (no parentheses)
_IFDEF_RE = re.compile(r"^\s*#\s*ifdef\s+([A-Z0-9_]+)", re.IGNORECASE)


def _classify_define_block(lines: list, def_idx: int):
    """
    Given all lines of a file and the 0-based index of a #define line,
    walk backwards to determine whether it sits in an #if or #else block.

    Returns (block_type, guard_macros) where:
      block_type   : 'if_branch' | 'else_branch' | 'top_level'
      guard_macros : list of macro names from the controlling #if condition
    """
    depth = 0
    in_else = False
    for back in range(def_idx - 1, -1, -1):
        bline = lines[back].strip()

        if bline.startswith("#endif"):
            depth += 1                       # nested block – skip its opener
        elif re.match(r"^#\s*if", bline) and depth > 0:
            depth -= 1                       # matched a nested #if – skip it
        elif bline.startswith("#else") and depth == 0:
            in_else = True                   # we are in the #else arm
        elif re.match(r"^#\s*if", bline) and depth == 0:
            # This is the controlling #if
            guards = _DEFINED_ARGS_RE.findall(bline)
            if not guards:
                m = _IFDEF_RE.match(bline)
                if m:
                    guards = [m.group(1)]
            block_type = "else_branch" if in_else else "if_branch"
            return block_type, guards

    return "top_level", []


def _walk_back_to_if_guards(lines: list, error_line_idx: int) -> list:
    """
    Starting at error_line_idx (0-based), walk backwards through preprocessor
    directives to collect the guards from the outermost controlling #if / #elif
    chain.

    Returns a flat list of guard macro names found in defined() or #ifdef.
    """
    depth   = 0
    guards  = []
    seen_else = False

    for back in range(error_line_idx - 1, -1, -1):
        bline = lines[back].strip()

        if not bline.startswith("#"):
            continue

        if bline.startswith("#endif"):
            depth += 1
            continue

        if re.match(r"^#\s*if", bline) and depth > 0:
            depth -= 1
            continue

        if depth > 0:
            continue

        # depth == 0 from here
        if bline.startswith("#else") and not seen_else:
            seen_else = True
            continue

        if re.match(r"^#\s*elif", bline):
            guards += _DEFINED_ARGS_RE.findall(bline)
            m_ifdef = _IFDEF_RE.match(bline)
            if m_ifdef:
                guards.append(m_ifdef.group(1))
            continue

        if re.match(r"^#\s*if\b", bline) and depth == 0:
            guards += _DEFINED_ARGS_RE.findall(bline)
            m_ifdef = _IFDEF_RE.match(bline)
            if m_ifdef:
                guards.append(m_ifdef.group(1))
            break

    return guards


def _append_first_guard(guards: list, existing_defines: list, new_defines: list) -> str:
    """Add the first guard not already defined; return it or ''."""
    for g in guards:
        if g not in existing_defines and g not in new_defines:
            new_defines.append(g)
            return g
    return ""


def _pick_guard_from_lines_above(lines: list, error_line_idx: int,
                                 existing_defines: list, new_defines: list) -> str:
    """
    When project-wide macro backtrace fails (e.g. last file in the include chain),
    walk upward in the same file from the error line and pick one guard macro
    from the nearest controlling #if / #elif condition.
    """
    guards = _walk_back_to_if_guards(lines, error_line_idx)
    return _append_first_guard(guards, existing_defines, new_defines)


def _same_file_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def _prioritize_error_file(defs: list, error_path: str) -> list:
    return sorted(defs, key=lambda d: 0 if _same_file_path(d[0], error_path) else 1)


def _find_all_macro_definitions(macro_name: str, search_root: str) -> list:
    """
    Return list of (file_path, def_line_idx, block_type, guard_macros)
    for EVERY #define of macro_name found anywhere under search_root.
    """
    results = []
    for dirpath, _dirs, filenames in os.walk(search_root):
        for fn in filenames:
            if not fn.lower().endswith((".h", ".c", ".cpp")):
                continue
            fpath = os.path.join(dirpath, fn)
            lines = read_lines(fpath)
            for idx, line in enumerate(lines):
                m = _DEFINE_RE.match(line)
                if m and m.group(1) == macro_name:
                    block_type, guard_macros = _classify_define_block(lines, idx)
                    results.append((fpath, idx, block_type, guard_macros))
    return results


def resolve_macro_errors(log_paths: tuple, search_root: str,
                         existing_defines: list) -> list:
    """
    Scan logs for parse errors, backtrace macro definitions, and return
    a list of new guard macro names that should be added as -D defines.
    """
    # Squash all logs together
    combined = combine_logs(log_paths)

    errors = []
    seen = set()
    for m in _MACRO_ERR_RE.finditer(combined):
        file_ref = m.group(1)
        key = (_basename_from_log_ref(file_ref).lower(), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            errors.append((file_ref, int(m.group(2))))

    if not errors:
        log("  [MACRO] No macro-parse errors detected in logs.")
        return []

    log(f"  [MACRO] {len(errors)} parse-error location(s) found.")
    new_defines = []

    for file_ref, lineno in errors:
        fname = _basename_from_log_ref(file_ref)
        log(f"  [MACRO] Error location: {file_ref}:{lineno}")

        real_path = find_file_under(search_root, fname, file_ref)
        if not real_path:
            log(f"  [MACRO][WARN] File not found on disk: {file_ref}")
            continue

        lines = read_lines(real_path)
        if lineno < 1 or lineno > len(lines):
            log(f"  [MACRO][WARN] Line {lineno} out of range ({len(lines)} lines) in {fname}")
            continue

        src_line = lines[lineno - 1]
        log(f"  [MACRO] Offending line {lineno}: {src_line.rstrip()}")
        fixed_this_error = False

        # ── FAST PATH: error is directly on a #define line ────────────────
        # e.g. Compiler.h:479  #define VAR(...) memclass vartype  (in #else)
        # Walk upward to line 476  #if (defined(MCAL_...) || defined(MCAL_...))
        _DEFINE_LINE_RE = re.compile(r"^\s*#\s*define\s+([A-Z][A-Z0-9_]*)\s*\(")
        _dm = _DEFINE_LINE_RE.match(src_line)
        if _dm:
            macro_name_on_line = _dm.group(1)
            log(f"  [MACRO] Error is ON a #define line — macro: {macro_name_on_line}")
            btype, guards = _classify_define_block(lines, lineno - 1)
            log(f"  [MACRO] block={btype}  guards={guards}")
            if btype in ("else_branch", "if_branch") and guards:
                added = _append_first_guard(guards, existing_defines, new_defines)
                if added:
                    branch = "#else" if btype == "else_branch" else "#if"
                    log(f"  [MACRO][FIX] Adding -D{added}  "
                        f"(error at #define in {branch} block of {macro_name_on_line}; "
                        f"activates alternate #if branch)")
                    fixed_this_error = True
            if fixed_this_error:
                continue

        macros = _MACRO_CALL_RE.findall(src_line)
        log(f"  [MACRO] Macros on that line: {macros}")

        for macro in macros:
            all_defs = _find_all_macro_definitions(macro, search_root)
            if not all_defs:
                log(f"  [MACRO] No definition found for {macro} in project tree")
                continue

            log(f"  [MACRO] {macro} has {len(all_defs)} definition(s):")
            for fpath, didx, btype, guards in all_defs:
                log(f"    {fpath}:{didx+1}  block={btype}  guards={guards}")

            else_defs = _prioritize_error_file(
                [(f, i, bt, g) for f, i, bt, g in all_defs if bt == "else_branch"],
                real_path,
            )
            if_defs = _prioritize_error_file(
                [(f, i, bt, g) for f, i, bt, g in all_defs if bt == "if_branch"],
                real_path,
            )

            if else_defs:
                for ef, ei, _, else_guards in else_defs:
                    matching_if = [d for d in if_defs if _same_file_path(d[0], ef)]
                    if matching_if:
                        guards = matching_if[0][3]
                        src = "matching #if def"
                    elif if_defs:
                        guards = if_defs[0][3]
                        src = "first #if def in project"
                    else:
                        guards = else_guards
                        src = "#if guards recovered from #else def"
                    log(f"  [MACRO] Guard source: {src}  guards={guards}")
                    added = _append_first_guard(guards, existing_defines, new_defines)
                    if added:
                        log(f"  [MACRO][FIX] Adding -D{added}  "
                            f"(activates #if branch of {macro}, suppresses broken #else)")
                        fixed_this_error = True
                    break

            elif if_defs:
                for _, _, _, guards in if_defs:
                    added = _append_first_guard(guards, existing_defines, new_defines)
                    if added:
                        log(f"  [MACRO][FIX] Adding -D{added}  "
                            f"(activates #if-only definition of {macro})")
                        fixed_this_error = True
                        break
            else:
                log(f"  [MACRO] {macro} is top-level in all files – skipping.")

        # ── FALLBACK: same-file upward scan (last file / no project backtrace) ─
        if not fixed_this_error:
            guards = _walk_back_to_if_guards(lines, lineno - 1)
            log(f"  [MACRO] Project backtrace did not resolve error; "
                f"scanning upward in {fname} for #if guards: {guards}")
            added = _append_first_guard(guards, existing_defines, new_defines)
            if added:
                log(f"  [MACRO][FIX] Adding -D{added}  "
                    f"(from #if condition above line {lineno} in {fname})")
            else:
                log(f"  [MACRO][WARN] No usable guard found above line {lineno} in {fname}")

    return new_defines


def _guards_from_define_at(search_root: str, file_ref: str, def_lineno: int,
                           existing_defines: list, new_defines: list) -> str:
    """Extract one guard macro from the #if chain above a #define line."""
    basename = _basename_from_log_ref(file_ref)
    real_path = find_file_under(search_root, basename, file_ref)
    if not real_path:
        log(f"  [MNOTE][WARN] Definition file not found: {file_ref}")
        return ""

    lines = read_lines(real_path)
    if not (1 <= def_lineno <= len(lines)):
        log(f"  [MNOTE][WARN] Line {def_lineno} out of range in {basename}")
        return ""

    btype, guards = _classify_define_block(lines, def_lineno - 1)
    log(f"  [MNOTE] {real_path}:{def_lineno}  block={btype}  guards={guards}")
    added = _append_first_guard(guards, existing_defines, new_defines)
    if added:
        return added

    guards = _walk_back_to_if_guards(lines, def_lineno - 1)
    log(f"  [MNOTE] Upward scan above line {def_lineno}: {guards}")
    return _append_first_guard(guards, existing_defines, new_defines)


def resolve_from_macro_definition_notes(log_paths: tuple, search_root: str,
                                        existing_defines: list) -> list:
    """
    Fix macro expansion failures using GCC/MinGW 'note: in definition of macro'
    lines — e.g. GHS/Compiler.h:479 for VAR(uint8, RTE_DATA) / RTE_DATA errors.

    This is the most reliable path when the compiler already points at the
    broken #define in an #else branch.
    """
    combined = combine_logs(log_paths)
    if not re.search(
        r"unknown\s+type\s+name|expected\s+.+?\s+before",
        combined,
        re.IGNORECASE,
    ):
        log("  [MNOTE] No macro-related compiler errors in logs.")
        return []

    new_defines: list = []
    seen: set = set()

    for m in _NOTE_MACRO_DEF_RE.finditer(combined):
        file_ref  = m.group(1)
        def_line  = int(m.group(2))
        macro     = m.group(3)
        key = (file_ref.lower(), def_line, macro)
        if key in seen:
            continue
        seen.add(key)

        log(f"  [MNOTE] Compiler note: macro '{macro}' defined at {file_ref}:{def_line}")
        added = _guards_from_define_at(
            search_root, file_ref, def_line, existing_defines, new_defines,
        )
        if added:
            log(f"  [MNOTE][FIX] Adding -D{added}  "
                f"(from #if guard above {macro} @ {file_ref}:{def_line})")

    return new_defines


# ============================================================================
# #error "Please specify compiler." AUTO-FIX ENGINE
# ============================================================================
#
# Pattern seen in AUTOSAR MCAL / crypto module headers:
#
#   #if defined(COMPILER_GHS)
#     #define CRYPTO_START_SEC_CODE
#     #include "Crypto_76_HaeModule_MemMap.h"
#   #elif defined(COMPILER_IAR)
#     ...
#   #else
#     #error "Please specify compiler."    ← triggered when no guard active
#   #endif
#
# Strategy:
#   1. Find every   filename:line: error: #error "..."  in the logs.
#   2. Open that file on disk, go to that line.
#   3. Walk backwards from the #error line to find the controlling #if.
#   4. Collect ALL defined(GUARD) / #ifdef GUARD identifiers from that #if chain.
#   5. Pick the first guard that looks like a compiler selector
#      (contains "COMPILER", "GCC", "MINGW", "GNU", "GHS", "IAR", "TASKING",
#       "GREEN_HILLS", "WINDRIVER", or "COSMIC") — that is the one MinGW needs.
#   6. If no compiler-shaped guard is found, return all guards and let the
#      caller decide.

_COMPILER_GUARD_KEYWORDS = re.compile(
    r"COMPILER|GCC|MINGW|GNU|GHS|IAR|TASKING|GREEN_HILLS|WINDRIVER|COSMIC|LLVM|ARMCC",
    re.IGNORECASE,
)


def resolve_hash_errors(log_paths: tuple, search_root: str,
                        existing_defines: list) -> list:
    """
    Scan logs for   filename:line: error: #error "..."   messages.
    Backtrace the file to find the compiler-selector guard that should be
    defined so that MinGW falls into the right #if branch instead of hitting
    the #else/#error.

    Returns a list of new guard macro names to add as -D defines.
    """
    combined = " ".join(squash_file(p) for p in log_paths)

    # Collect unique (filename, lineno, message) triples
    hash_errors: list = []
    seen: set = set()
    for m in _HASH_ERROR_RE.finditer(combined):
        key = (m.group(1).lower(), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            hash_errors.append((m.group(1), int(m.group(2)), m.group(3)))

    if not hash_errors:
        log("  [HASH_ERR] No #error directive failures detected.")
        return []

    log(f"  [HASH_ERR] {len(hash_errors)} #error location(s) found.")
    new_defines: list = []

    for fname, lineno, msg in hash_errors:
        log(f"  [HASH_ERR] {fname}:{lineno}  msg='{msg}'")

        real_path = find_file_under(search_root, fname)
        if not real_path:
            log(f"  [HASH_ERR][WARN] File not found on disk: {fname}")
            continue

        lines = read_lines(real_path)
        if lineno < 1 or lineno > len(lines):
            log(f"  [HASH_ERR][WARN] Line {lineno} out of range in {fname}")
            continue

        log(f"  [HASH_ERR] Offending line: {lines[lineno - 1].rstrip()}")

        guards = _walk_back_to_if_guards(lines, lineno - 1)   # 0-based
        log(f"  [HASH_ERR] Candidate guards from #if chain: {guards}")

        if not guards:
            log(f"  [HASH_ERR][WARN] Could not find controlling #if for {fname}:{lineno}")
            continue

        # Prefer a guard that looks like a compiler selector
        compiler_guards = [g for g in guards if _COMPILER_GUARD_KEYWORDS.search(g)]
        chosen = compiler_guards if compiler_guards else guards

        for g in chosen:
            if g not in existing_defines and g not in new_defines:
                log(f"  [HASH_ERR][FIX] Adding -D{g}  "
                    f"(satisfies compiler guard in {fname}:{lineno})")
                new_defines.append(g)

    return new_defines

# ============================================================================
# "unknown type name" AUTO-FIX ENGINE
# ============================================================================
#
# Pattern (seen with AUTOSAR RTE / MCAL VAR macro on MinGW):
#
#   Rte_QuarterGlassCurtain.h:318:14: error: unknown type name 'RTE_DATA'
#     318 |   VAR(uint8, RTE_DATA) _dummy;
#   Compiler.h:479:32: note: in definition of macro 'VAR'
#     479 | #define VAR(vartype, memclass) memclass vartype
#
# Root cause:
#   The macro VAR expands to   memclass vartype   (the #else branch).
#   The memclass argument 'RTE_DATA' is undefined because the #if guard
#   (e.g. MCAL_SUPPORT_MOBILGENE_1_0) is not active.
#
# Fix strategy:
#   1. Find every   filename:line: error: unknown type name 'X'  in logs.
#   2. Read that source line and collect every CAPS_MACRO( call on it.
#   3. For each such macro look for a   note: in definition of macro 'MACRONAME'
#      in the same squashed log to get the file/line of the actual #define.
#   4. Open that file, walk backwards from the #define to find the controlling
#      #if guard (reuse _classify_define_block / _find_all_macro_definitions).
#   5. Add the #if-branch guard as a -D define so the clean expansion is used.
#
# NOTE: The 'unknown type name' error appears BEFORE the 'expected X before Y'
# error in some toolchains, so we handle it independently here.

# Matches:   filename.h:318:14: error: unknown type name 'RTE_DATA'
# Groups:    (1) file ref  (2) lineno  (3) unknown type name
_UNKNOWN_TYPE_RE = re.compile(
    _LOG_FILE_REF +
    r"\s*[:|]\s*(\d+)"
    r"(?:\s*[:|]\s*\d+)?"
    r"\s*[:|]\s*error\s*:\s*unknown\s+type\s+name\s+'([A-Za-z_][A-Za-z0-9_]*)'",
    re.IGNORECASE,
)

# Matches:   GHS/Compiler.h:479:32: note: in definition of macro 'VAR'
# Groups:    (1) file ref  (2) lineno  (3) macro name
_NOTE_MACRO_DEF_RE = re.compile(
    _LOG_FILE_REF +
    r"\s*[:|]\s*(\d+)"
    r"(?:\s*[:|]\s*\d+)?"
    r"\s*[:|]\s*note\s*:\s*in\s+definition\s+of\s+macro\s+'([A-Za-z_][A-Za-z0-9_]*)'",
    re.IGNORECASE,
)


def resolve_unknown_type_errors(log_paths: tuple, search_root: str,
                                existing_defines: list) -> list:
    """
    Scan logs for  'unknown type name'  errors that are caused by a macro
    memclass argument being undefined (e.g. RTE_DATA inside VAR(uint8, RTE_DATA)).

    Strategy:
      - Find the error location (file + line).
      - Read that line, extract the macro call(s) on it.
      - If a 'note: in definition of macro' line points to the #define file,
        use it; otherwise fall back to _find_all_macro_definitions.
      - Walk back from the #define to find the controlling #if guard.
      - Return the guards from the #if branch (not #else) so the clean
        expansion is activated.

    Returns a list of new guard macro names to add as -D defines.
    """
    combined = combine_logs(log_paths)

    # ── collect unique (source_file, lineno, unknown_name) triples ──
    errors: list = []
    seen:   set  = set()
    for m in _UNKNOWN_TYPE_RE.finditer(combined):
        file_ref = m.group(1)
        key = (_basename_from_log_ref(file_ref).lower(), int(m.group(2)))
        if key not in seen:
            seen.add(key)
            errors.append((file_ref, int(m.group(2)), m.group(3)))

    if not errors:
        log("  [UTYPE] No 'unknown type name' errors detected.")
        return []

    log(f"  [UTYPE] {len(errors)} unknown-type-name error(s) found.", also_print=True)

    # ── build note map: macro_name -> (def_file_ref, def_lineno) ──
    note_map: dict = {}
    for m in _NOTE_MACRO_DEF_RE.finditer(combined):
        mname = m.group(3)
        if mname not in note_map:
            note_map[mname] = (m.group(1), int(m.group(2)))
    if note_map:
        log(f"  [UTYPE] Macro-definition notes found: {list(note_map.keys())}")

    new_defines: list = []

    for src_ref, lineno, unknown_name in errors:
        src_fname = _basename_from_log_ref(src_ref)
        log(f"  [UTYPE] {src_ref}:{lineno}  unknown type='{unknown_name}'")

        real_src = find_file_under(search_root, src_fname, src_ref)
        if real_src:
            src_lines = read_lines(real_src)
            if 1 <= lineno <= len(src_lines):
                src_line = src_lines[lineno - 1]
                log(f"  [UTYPE] Offending line: {src_line.rstrip()}")
                macros_on_line = _MACRO_CALL_RE.findall(src_line)
                log(f"  [UTYPE] Macro calls on that line: {macros_on_line}")
            else:
                macros_on_line = []
        else:
            log(f"  [UTYPE][WARN] Source file not found: {src_fname}")
            macros_on_line = []

        # For each macro call on the line (or compiler note macros if line unreadable)
        macros_to_try = macros_on_line or list(note_map.keys())
        fixed_this_error = False

        for macro in macros_to_try:
            log(f"  [UTYPE] Backtracing macro '{macro}'...")
            preferred_path = real_src or ""
            real_def = ""

            # Prefer the note-pointed definition file (exact file + line)
            if macro in note_map:
                def_ref, def_lineno = note_map[macro]
                def_fname = _basename_from_log_ref(def_ref)
                real_def = find_file_under(search_root, def_fname, def_ref)
                if real_def:
                    preferred_path = real_def
                    log(f"  [UTYPE] Using note-pointed definition: {real_def}:{def_lineno}")
                    def_lines = read_lines(real_def)
                    if 1 <= def_lineno <= len(def_lines):
                        btype, guards = _classify_define_block(def_lines, def_lineno - 1)
                        log(f"  [UTYPE] block={btype}  guards={guards}")
                        all_defs = [(real_def, def_lineno - 1, btype, guards)]
                    else:
                        all_defs = []
                else:
                    log(f"  [UTYPE][WARN] Note-pointed file not found: {def_ref}")
                    all_defs = []
            else:
                all_defs = []

            # Fall back to full search if note didn't help
            if not all_defs:
                log(f"  [UTYPE] Falling back to full search for macro '{macro}'")
                all_defs = _find_all_macro_definitions(macro, search_root)

            if not all_defs:
                log(f"  [UTYPE] No definition found for macro '{macro}'")
                continue

            log(f"  [UTYPE] '{macro}' has {len(all_defs)} definition(s):")
            for fpath, didx, btype, guards in all_defs:
                log(f"    {fpath}:{didx+1}  block={btype}  guards={guards}")

            # Guard-selection logic:
            # _classify_define_block always stores the guards of the CONTROLLING #if
            # in tuple index [3], regardless of whether the define is in the #if or
            # #else branch.  So else_def[3] already holds the #if guards we need.
            #
            # Priority:
            #  1. A matching #if-branch def in the same file as the #else def
            #     (guards from the #if side, avoids activating a stale guard)
            #  2. Any #if-branch def in any file
            #  3. The else_def's own guard list (same controlling #if guards,
            #     already stored by _classify_define_block) — this is the key
            #     fallback that was missing and caused the bug when only ONE
            #     definition was loaded via the note map
            else_defs = _prioritize_error_file(
                [(f, i, bt, g) for f, i, bt, g in all_defs if bt == "else_branch"],
                preferred_path,
            )
            if_defs = _prioritize_error_file(
                [(f, i, bt, g) for f, i, bt, g in all_defs if bt == "if_branch"],
                preferred_path,
            )

            if else_defs:
                for ef, ei, _, else_guards in else_defs:
                    matching_if = [d for d in if_defs if _same_file_path(d[0], ef)]
                    if matching_if:
                        guards = matching_if[0][3]
                        src = "matching #if def in same file"
                    elif if_defs:
                        guards = if_defs[0][3]
                        src = "first #if def in project"
                    else:
                        guards = else_guards
                        src = "#if guards recovered directly from #else def"
                    log(f"  [UTYPE] Guard source: {src}  guards={guards}")
                    added = _append_first_guard(guards, existing_defines, new_defines)
                    if added:
                        log(f"  [UTYPE][FIX] Adding -D{added}  "
                            f"(activates #if branch of '{macro}', "
                            f"suppresses broken #else that expands memclass)")
                        fixed_this_error = True
                    break
            elif if_defs:
                for _, _, _, guards in if_defs:
                    added = _append_first_guard(guards, existing_defines, new_defines)
                    if added:
                        log(f"  [UTYPE][FIX] Adding -D{added}  "
                            f"(activates #if-only definition of '{macro}')")
                        fixed_this_error = True
                        break
            else:
                log(f"  [UTYPE] '{macro}' is top-level in all files – skipping.")

        if not fixed_this_error and note_map:
            for macro, (def_ref, def_lineno) in note_map.items():
                log(f"  [UTYPE] Fallback via compiler note for '{macro}' @ {def_ref}:{def_lineno}")
                added = _guards_from_define_at(
                    search_root, def_ref, def_lineno, existing_defines, new_defines,
                )
                if added:
                    log(f"  [UTYPE][FIX] Adding -D{added}  (from note above {macro})")
                    break

    return new_defines


def find_header_dirs(root: str, headers: list) -> dict:
    needed  = set(headers)
    found   = {}
    lowered = {h.lower(): h for h in needed}

    log(f"  [SEARCH] Walking: {root}")
    log(f"  [SEARCH] Looking for: {sorted(needed)}")

    for dirpath, _dirs, filenames in os.walk(root):
        files_lower = {fn.lower() for fn in filenames}
        for lh, orig in list(lowered.items()):
            if lh in files_lower and orig not in found:
                found[orig] = dirpath
                log(f"  [FOUND]  {orig}  ->  {dirpath}")
        if set(found.keys()) == needed:
            break

    for h in sorted(needed - set(found.keys())):
        log(f"  [NOT FOUND]  {h}")

    return found


# ============================================================================
# CCAST_.CFG WRITER  –  always a full rewrite so DEFINES[] is the single source
# ============================================================================

_ftrack_supported = None

def is_ftrack_supported() -> bool:
    global _ftrack_supported
    if _ftrack_supported is not None:
        return _ftrack_supported
    creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
    try:
        proc = subprocess.run(
            ["gcc", "-E", "-ftrack-macro-expansion=0", "-xc", "-"],
            input="",
            capture_output=True,
            text=True,
            creationflags=creationflags,
            timeout=2
        )
        _ftrack_supported = (proc.returncode == 0 and "unrecognized" not in proc.stderr.lower())
    except Exception:
        _ftrack_supported = False
    return _ftrack_supported


def is_licensing_error(exit_code: int, build_log: str, error_log: str) -> bool:
    """Check if the build failure was due to a licensing issue."""
    if exit_code == 16:
        return True
    
    for path in (build_log, error_log):
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read().lower()
                    if "license" in content or "licensing" in content or "flexlm" in content:
                        return True
            except Exception:
                pass
    return False


def run_clicast_with_licensing_retry(cmd: list, **kwargs) -> subprocess.CompletedProcess:
    """Run a clicast subprocess, retrying if it encounters a licensing error."""
    max_retries = 10
    retry_delay = 5  # seconds
    
    if "creationflags" not in kwargs:
        kwargs["creationflags"] = _NO_WINDOW

    # Force English locale
    env = kwargs.get("env") or os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    kwargs["env"] = env

    for attempt in range(1, max_retries + 1):
        r = subprocess.run(cmd, **kwargs)
        
        is_lic = (r.returncode == 16)
        if not is_lic and r.returncode != 0:
            if hasattr(r, "stderr") and r.stderr:
                stderr_str = r.stderr if isinstance(r.stderr, str) else r.stderr.decode("utf-8", errors="replace")
                if "license" in stderr_str.lower() or "licensing" in stderr_str.lower() or "flexlm" in stderr_str.lower():
                    is_lic = True
            if not is_lic and hasattr(r, "stdout") and r.stdout:
                stdout_str = r.stdout if isinstance(r.stdout, str) else r.stdout.decode("utf-8", errors="replace")
                if "license" in stdout_str.lower() or "licensing" in stdout_str.lower() or "flexlm" in stdout_str.lower():
                    is_lic = True
            
            if not is_lic:
                for stream_arg in ("stdout", "stderr"):
                    stream_obj = kwargs.get(stream_arg)
                    if stream_obj and hasattr(stream_obj, "name") and os.path.isfile(stream_obj.name):
                        try:
                            with open(stream_obj.name, "r", encoding="utf-8", errors="replace") as f:
                                content = f.read().lower()
                                if "license" in content or "licensing" in content or "flexlm" in content:
                                    is_lic = True
                                    break
                        except Exception:
                            pass
                            
        if is_lic:
            if attempt < max_retries:
                log(f"  [LICENSE] Clicast licensing error (exit code {r.returncode}). Retrying in {retry_delay}s (attempt {attempt}/{max_retries})...")
                time.sleep(retry_delay)
                continue
            else:
                log(f"  [LICENSE] Clicast licensing error persisted after {max_retries} attempts.")
        
        return r


def write_cfg() -> None:
    """
    Write CCAST_.CFG from scratch using the current DEFINES list.
    Called before every build attempt so newly discovered defines are included.
    """
    preprocess_cmd = "gcc -E -ftrack-macro-expansion=0 -C" if is_ftrack_supported() else "gcc -E -C"
    cfg_lines = [
        "C_COMPILER_CFG_SOURCE: PY_CONFIGURATOR",
        "C_COMPILER_FAMILY_NAME: GNU_Native",
        "C_COMPILER_HIERARCHY_STRING: VectorCAST MinGW_C",
        "C_COMPILER_OUTPUT_FLAG: -o",
        "C_COMPILER_PY_ARGS: --lang c --version Built-in-MinGW",
        "C_COMPILER_TAG: BUILTIN_MINGW_C",
        "C_COMPILER_VERSION_CMD: gcc --version",
        "C_COMPILE_CMD: gcc -c -g",
        "C_DEBUG_CMD: gdb",
        "C_EDG_FLAGS: -w --gcc --gnu_version 100200 --64_bit_target --x86_64 --mingw",
        "C_LINKER_VERSION_CMD: ld --version",
        "C_LINK_CMD: gcc -g",
        f"C_PREPROCESS_CMD: {preprocess_cmd}",
        "VARIANT_LOGICS_PATH: ",
        "VCAST_ASSEMBLY_FILE_EXTENSIONS: s",
        "VCAST_COLLAPSE_STD_HEADERS: COLLAPSE_NONE",
        "VCAST_COMMAND_LINE_DEBUGGER: TRUE",
        "VCAST_DISABLE_STD_WSTRING_DETECTION: TRUE",
        "VCAST_DISPLAY_UNINST_EXPR: FALSE",
        "VCAST_ENVIRONMENT_FILES: ",
        "VCAST_GNU_SYSTEM_MARKER: TRUE",
        "VCAST_HAS_LONGLONG: TRUE",
        f"VCAST_PREPEND_TO_PATH_DIRS: $(VECTORCAST_DIR)/MinGW/bin",
        "VCAST_TEST_VALUES_DICTIONARY: ",
        "VCAST_TYPEOF_OPERATOR: TRUE",
        "VCAST_VCDB_FLAG_STRING: -isystem=1",
        "VCDB_CMD_VERB: ",
        "VCDB_FILENAME: ",
        "WHITEBOX: YES",
        # Coverage instrumentation (matches IT write_it_cfg – enables the
        # "Instrument for function and function call coverage" checkbox)
        "VCAST_COVERAGE_SOURCE_FILE_PERSPECTIVE: FALSE",
        "VCAST_DISPLAY_FUNCTION_COVERAGE: TRUE",
        "VCAST_ENABLE_FUNCTION_AND_CALL_COVERAGE: TRUE",
        "VCAST_ENABLE_FUNCTION_CALL_COVERAGE: TRUE",
    ]
    with open(CFG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(cfg_lines) + "\n")
        if DEFINES:
            f.write(f"C_DEFINE_LIST: {' '.join(DEFINES)}\n")
    log(f"  [CFG] Defines active ({len(DEFINES)}): {' '.join(DEFINES)}")


# ============================================================================
# ENV SCRIPT WRITER
# ============================================================================

def write_env_script(extra_includes: list) -> None:
    lines = [
        "ENVIRO.NEW",
        f"ENVIRO.NAME: {ENV_NAME}",
        "ENVIRO.COVERAGE_TYPE: Statement+MCDC",
        "ENVIRO.WHITE_BOX: YES",
        "ENVIRO.STUB: ALL_BY_PROTOTYPE",
        "ENVIRO.COMPILER: CC",
        "ENVIRO.TYPE_HANDLED_DIRS_ALLOWED:",
        f"ENVIRO.UUT: {UUT_FILE}",
        f"ENVIRO.BASE_DIRECTORY: {BASE_DIR_NAME}={BASE_DIR_PATH}",
    ]
    for src in [SOURCE_DIR_1, SOURCE_DIR_2, SOURCE_DIR_3]:
        if src:
            norm_base = os.path.normcase(os.path.normpath(BASE_DIR_PATH))
            norm_src  = os.path.normcase(os.path.normpath(src))
            if norm_src.startswith(norm_base):
                rel = os.path.normpath(src)[len(os.path.normpath(BASE_DIR_PATH)):].lstrip(os.sep)
                entry = f"$({BASE_DIR_NAME})\\{rel}"
            else:
                entry = src
            lines.append(f"ENVIRO.SEARCH_LIST: {entry}")
    for inc in extra_includes:
        # Convert absolute path to $(BASE_DIR_NAME)\relative form when possible
        # so VectorCAST resolves it the same way as the manually built .env
        norm_base = os.path.normcase(os.path.normpath(BASE_DIR_PATH))
        norm_inc  = os.path.normcase(os.path.normpath(inc))
        if norm_inc.startswith(norm_base):
            rel = os.path.normpath(inc)[len(os.path.normpath(BASE_DIR_PATH)):].lstrip(os.sep)
            entry = f"$({BASE_DIR_NAME})\\{rel}"
        else:
            entry = inc
        lines.append(f"ENVIRO.SEARCH_LIST: {entry}")

    with open(ENV_SCRIPT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(ENV_SCRIPT, "a", encoding="utf-8") as f:
        f.write("ENVIRO.END\n")


# ============================================================================
# BUILD RUNNER
# ============================================================================

def collect_vcqik_errors(env_dir: str) -> None:
    """
    After a failed build VectorCAST writes the real compiler diagnostics into
    vcqik/*.vcqik.ERR files inside the environment directory.  The main build
    log only says "See error log for complete message", so the header/macro
    scanners never see the actual error lines unless we collect them here.

    This function reads every .vcqik.ERR file and appends its content to
    ERROR_LOG so that extract_missing_headers(), resolve_macro_errors(), and
    resolve_hash_errors() can all find them in the normal post-build scan.
    """
    vcqik_dir = os.path.join(env_dir, "vcqik")
    if not os.path.isdir(vcqik_dir):
        return

    appended = 0
    with open(ERROR_LOG, "a", encoding="utf-8", errors="replace") as out:
        for fname in sorted(os.listdir(vcqik_dir)):
            if not fname.lower().endswith(".err"):
                continue
            fpath = os.path.join(vcqik_dir, fname)
            lines = read_lines(fpath)
            if not lines:
                continue
            out.write(f"\n\n=== vcqik/{fname} ===\n")
            out.writelines(lines)
            appended += 1

    if appended:
        log(f"  [VCQIK] Appended {appended} .vcqik.ERR file(s) to error_log.txt for scanning")


def run_build(env_dir: str) -> int:
    """
    Delete the previous environment directory, run clicast build,
    and save stdout to BUILD_LOG and stderr to ERROR_LOG.
    
    If the build fails with a licensing error, we retry up to 10 times with 5s delay.
    """
    max_lic_retries = 10
    lic_retry_delay = 5  # seconds
    
    # Force English locale
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"

    for lic_attempt in range(1, max_lic_retries + 1):
        if os.path.isdir(env_dir):
            collect_vcqik_errors(env_dir)
            log("  Cleaning previous environment directory...")
            shutil.rmtree(env_dir)

        cmd = [CLICAST_EXE, "-lc", "ENvironment", "Build", ENV_SCRIPT]
        log(f"  CMD: {' '.join(cmd)}")

        check_stop("before clicast build")

        with open(BUILD_LOG, "w", encoding="utf-8") as bout, \
             open(ERROR_LOG, "w", encoding="utf-8") as berr:
            proc = subprocess.Popen(
                cmd, stdout=bout, stderr=berr, env=env, creationflags=_NO_WINDOW,
            )
            while proc.poll() is None:
                if stop_requested():
                    proc.terminate()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                    return -1
                time.sleep(0.25)

        returncode = proc.returncode

        # Check for licensing error
        if is_licensing_error(returncode, BUILD_LOG, ERROR_LOG):
            if lic_attempt < max_lic_retries:
                log(f"  [LICENSE] Environment build licensing error (exit code {returncode}). Retrying in {lic_retry_delay}s (attempt {lic_attempt}/{max_lic_retries})...")
                time.sleep(lic_retry_delay)
                continue
            else:
                log(f"  [LICENSE] Licensing error persisted after {max_lic_retries} attempts.")

        # FIX: also collect vcqik ERR files from THIS attempt immediately after
        # the build so the very first failure is also diagnosed correctly.
        if returncode != 0 and os.path.isdir(env_dir):
            collect_vcqik_errors(env_dir)

        return returncode


# ============================================================================
# ENABLE FUNCTION COVERAGE (post-build)
# ============================================================================

def enable_function_coverage() -> None:
    log("\n[FUNCTION COVERAGE] Enabling Function + FunctionCall instrumentation...")

    for key, label in [
        ("VCAST_INSTRUMENT_FOR_FUNCTION_COVERAGE",      "Function"),
        ("VCAST_INSTRUMENT_FOR_FUNCTION_CALL_COVERAGE", "FunctionCall"),
        ("VCAST_ENABLE_FUNCTION_AND_CALL_COVERAGE",     "Function+FunctionCall"),
    ]:
        cmd = [CLICAST_EXE, "-lc", "-e", ENV_NAME, "options", "Coverage", key, "TRUE"]
        log(f"  CMD: {' '.join(cmd)}")
        r = run_clicast_with_licensing_retry(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            log(f"  [WARN] {label} coverage option exit {r.returncode}: {r.stderr.strip()}")

    ri_log = os.path.join(WORK_DIR, "reinstrument_log.txt")
    cmd_ri = [CLICAST_EXE, "-lc", "-e", ENV_NAME, "ENvironment", "Re_instrument"]
    log(f"  CMD: {' '.join(cmd_ri)}")
    with open(ri_log, "w", encoding="utf-8") as rout:
        r3 = run_clicast_with_licensing_retry(cmd_ri, stdout=rout, stderr=rout)

    ri_text = "".join(read_lines(ri_log)).strip()
    if ri_text:
        print(ri_text)

    if r3.returncode != 0:
        log(f"  [WARN] Re-instrumentation exit {r3.returncode}. Check: {ri_log}")
    else:
        log("  [OK] Function + FunctionCall coverage active.")
        print("  [OK] Function + FunctionCall coverage enabled.")


# ============================================================================
# MAIN
# ============================================================================

def main() -> None:
    sep = "=" * 76

    print(sep)
    print("  VectorCAST Auto-Compile  |  Header + Macro Auto-Resolution")
    print(f"  Environment   : {ENV_NAME}")
    print(f"  VectorCAST    : {VECTORCAST_DIR}")
    print(f"  Working Dir   : {WORK_DIR}")
    print(f"  Search Root   : {HEADER_SEARCH_ROOT}")
    print(f"  Max retries   : {MAX_RETRY_ROUNDS}")
    print(sep)

    # Init detailed log
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(WORK_DIR, exist_ok=True)
    with open(DETAILED_LOG, "w", encoding="utf-8") as f:
        f.write(f"{sep}\nVectorCAST Auto-Compile Log\nStarted: {now}\n{sep}\n\n")
        f.write(f"  VECTORCAST_DIR : {VECTORCAST_DIR}\n")
        f.write(f"  ENV_NAME       : {ENV_NAME}\n")
        f.write(f"  WORK_DIR       : {WORK_DIR}\n")
        f.write(f"  BASE_DIR_PATH  : {BASE_DIR_PATH}\n")
        f.write(f"  UUT_FILE       : {UUT_FILE}\n")
        f.write(f"  DEFINES        : {' '.join(DEFINES)}\n\n")

    # STEP 0 – verify VectorCAST
    log("\n[STEP 0] Checking VectorCAST...")
    if not os.path.isfile(CLICAST_EXE):
        log(f"[ERROR] clicast.exe not found: {CLICAST_EXE}")
        input("Press Enter to exit...")
        sys.exit(1)
    log(f"  [OK] {CLICAST_EXE}")

    mingw_bin = os.path.join(VECTORCAST_DIR, "MinGW", "bin")
    os.environ["PATH"] = f"{VECTORCAST_DIR};{mingw_bin};{os.environ.get('PATH', '')}"
    os.environ.pop("VECTORCAST_DIR", None)

    os.chdir(WORK_DIR)
    log(f"  [OK] Working dir: {os.getcwd()}")

    # STEP 1 – write initial CCAST_.CFG
    log("\n[STEP 1] Writing CCAST_.CFG...")
    write_cfg()

    # Seed static extra-includes
    extra_includes: list = [
        ei for ei in [EXTRA_INCLUDE_1, EXTRA_INCLUDE_2, EXTRA_INCLUDE_3] if ei
    ]
    already_searched: set  = set()
    already_defines_tried: set = set()   # guards we've already attempted
    env_dir = os.path.join(WORK_DIR, ENV_NAME)

    # ================================================================
    #  AUTO-RETRY LOOP
    # ================================================================
    for attempt in range(1, MAX_RETRY_ROUNDS + 1):
        check_stop(f"attempt {attempt}")
        print()
        print(f"{'─'*76}")
        print(f"  BUILD ATTEMPT {attempt} / {MAX_RETRY_ROUNDS}")
        if DEFINES:
            print(f"  Active defines ({len(DEFINES)}): {' '.join(DEFINES)}")
        if extra_includes:
            print(f"  Include paths  ({len(extra_includes)}):")
            for p in extra_includes:
                print(f"    {p}")
        print(f"{'─'*76}\n")
        log(f"\n{'─'*76}\n[ATTEMPT {attempt}]")

        # Always rewrite CCAST_.CFG from DEFINES[] so nothing is lost or doubled
        write_cfg()

        write_env_script(extra_includes)
        log(f"  [OK] {ENV_NAME}.env written")

        build_exit = run_build(env_dir)
        log(f"  Exit code: {build_exit}")
        if build_exit == -1:
            check_stop(f"attempt {attempt}")

        check_stop(f"after attempt {attempt}")

        # Print build output
        print("=== BUILD OUTPUT ===")
        print("".join(read_lines(BUILD_LOG)))
        err_lines = read_lines(ERROR_LOG)
        if err_lines:
            print("=== ERROR OUTPUT ===")
            print("".join(err_lines))

        # ── SUCCESS ──────────────────────────────────────────────────
        if build_exit == 0:
            log(f"\n[SUCCESS] Built on attempt {attempt}!")
            print(f"\n[SUCCESS] Environment built successfully! (attempt {attempt})")
            if len(DEFINES) > 1:
                print(f"  Auto-added defines: {[d for d in DEFINES if d != '__USE_MINGW_ANSI_STDIO']}")
            if extra_includes:
                print(f"  Auto-added include paths:")
                for p in extra_includes:
                    print(f"    {p}")
            print(f"\n  Environment : {env_dir}")
            print(f"  Build log   : {BUILD_LOG}")
            enable_function_coverage()
            show_alert(
                "VectorCAST Build Success",
                f"SUCCESSFUL after {attempt} attempt(s)!\\n\\n"
                f"Environment: {ENV_NAME}\\nLocation: {env_dir}\\n\\n"
                f"Coverage: Statement+MC/DC+Function+FunctionCall",
            )
            break

        # ── FAILURE ──────────────────────────────────────────────────
        log(f"\n[ATTEMPT {attempt}] Failed.")

        # 1. Try missing-header fix first
        log("  Scanning for missing headers...")
        all_missing  = extract_missing_headers(BUILD_LOG, ERROR_LOG)
        new_headers  = [h for h in all_missing if h not in already_searched]
        log(f"  Missing headers (new): {new_headers}")

        if new_headers:
            already_searched.update(new_headers)
            found_map = find_header_dirs(HEADER_SEARCH_ROOT, new_headers)
            if not found_map:
                fail(
                    f"Could not find {new_headers} under '{HEADER_SEARCH_ROOT}'.\n"
                    "Try setting HEADER_SEARCH_ROOT to a higher-level directory."
                )
            norm_existing = [os.path.normcase(os.path.normpath(p)) for p in extra_includes]
            added = []
            for hdr, dirpath in found_map.items():
                norm = os.path.normcase(os.path.normpath(dirpath))
                if norm not in norm_existing:
                    extra_includes.append(dirpath)
                    norm_existing.append(norm)
                    added.append((hdr, dirpath))
                    log(f"  [+INCLUDE] {dirpath}  (provides {hdr})")
            if added:
                print(f"\n[HEADER-FIX] {len(added)} new include path(s) added:")
                for hdr, p in added:
                    print(f"    {hdr}  ->  {p}")
            print("  Retrying build...\n")
            continue

        # 2. Macro definition notes — GCC points at broken #define (e.g. GHS/Compiler.h:479)
        log("  Trying macro-definition-note resolver...")
        new_note_defines = resolve_from_macro_definition_notes(
            (BUILD_LOG, ERROR_LOG),
            HEADER_SEARCH_ROOT,
            DEFINES,
        )
        new_note_defines = [d for d in new_note_defines if d not in already_defines_tried]

        if new_note_defines:
            already_defines_tried.update(new_note_defines)
            print(f"\n[MNOTE-FIX] {len(new_note_defines)} platform guard(s) from compiler notes:")
            for d in new_note_defines:
                print(f"  * -D{d}")
                DEFINES.append(d)
            log(f"  [MNOTE-FIX] DEFINES now: {DEFINES}")
            print("  Retrying build with updated defines...\n")
            continue

        # 3. No note-based fix – try macro-error fix
        log("  No macro-definition notes resolved. Trying macro-error resolver...")
        new_defines = resolve_macro_errors(
            (BUILD_LOG, ERROR_LOG),
            HEADER_SEARCH_ROOT,
            DEFINES,
        )
        # Filter out any guard we've already tried (avoid infinite loop)
        new_defines = [d for d in new_defines if d not in already_defines_tried]

        if new_defines:
            already_defines_tried.update(new_defines)
            print(f"\n[MACRO-FIX] {len(new_defines)} platform guard(s) detected:")
            for d in new_defines:
                print(f"  * -D{d}")
                DEFINES.append(d)
            log(f"  [MACRO-FIX] DEFINES now: {DEFINES}")
            print("  Retrying build with updated defines...\n")
            continue

        # 4. No 'expected X before Y' macro errors –
        #    try 'unknown type name' macro-memclass fix
        log("  No 'expected' macro-parse errors. Trying unknown-type-name resolver...")
        new_utype_defines = resolve_unknown_type_errors(
            (BUILD_LOG, ERROR_LOG),
            HEADER_SEARCH_ROOT,
            DEFINES,
        )
        new_utype_defines = [d for d in new_utype_defines if d not in already_defines_tried]

        if new_utype_defines:
            already_defines_tried.update(new_utype_defines)
            print(f"\n[UTYPE-FIX] {len(new_utype_defines)} memclass guard(s) detected:")
            for d in new_utype_defines:
                print(f"  * -D{d}")
                DEFINES.append(d)
            log(f"  [UTYPE-FIX] DEFINES now: {DEFINES}")
            print("  Retrying build with updated defines...\n")
            continue

        # 5. No 'unknown type name' fix – try #error "Please specify compiler." fix
        log("  No macro-parse errors. Trying #error compiler-guard resolver...")
        new_hash_defines = resolve_hash_errors(
            (BUILD_LOG, ERROR_LOG),
            HEADER_SEARCH_ROOT,
            DEFINES,
        )
        new_hash_defines = [d for d in new_hash_defines if d not in already_defines_tried]

        if new_hash_defines:
            already_defines_tried.update(new_hash_defines)
            print(f"\n[HASH-ERROR-FIX] {len(new_hash_defines)} compiler guard(s) detected:")
            for d in new_hash_defines:
                print(f"  * -D{d}")
                DEFINES.append(d)
            log(f"  [HASH-ERROR-FIX] DEFINES now: {DEFINES}")
            print("  Retrying build with updated defines...\n")
            continue

        # 6. No fix worked – extract compiler errors and give up
        log("[ERROR] No header fix, macro-note fix, macro fix, unknown-type fix, "
            "or #error compiler-guard fix resolved the failure.")
        if os.path.isdir(env_dir):
            ce_file = os.path.join(WORK_DIR, "compile_errors.txt")
            run_clicast_with_licensing_retry(
                [CLICAST_EXE, "-e", ENV_NAME,
                 "ENvironment", "Extract", "Compile_errors", ce_file],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            if os.path.isfile(ce_file):
                print("\n--- COMPILER ERRORS ---")
                print("".join(read_lines(ce_file)))
        fail("Build failed. Check detailed_log.txt for the full backtrace.")

    else:
        fail(f"Did not succeed after {MAX_RETRY_ROUNDS} attempts.")

    # ================================================================
    #  SUMMARY
    # ================================================================
    print()
    print(sep)
    print("  BUILD SUMMARY")
    print(sep)
    print(f"  Compiler    : VectorCAST MinGW (C)")
    print(f"  Environment : {ENV_NAME}")
    print(f"  Coverage    : Statement+MC/DC+Function+FunctionCall  |  Whitebox: YES")
    print(f"  UUT         : {UUT_FILE}.c")
    print(f"  Working Dir : {WORK_DIR}")
    print(f"  Defines     : {' '.join(DEFINES)}")
    if extra_includes:
        print(f"  Auto-includes ({len(extra_includes)}):")
        for p in extra_includes:
            print(f"    {p}")
    print(sep)
    log(f"\n{sep}\nSUMMARY – {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Defines ({len(DEFINES)}): {DEFINES}")
    log(f"Includes ({len(extra_includes)}): {extra_includes}")
    print("\nDone.")


if __name__ == "__main__":
    main()
