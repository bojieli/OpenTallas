"""WAVE-COPYBACK-1115 (FABLE-PD-PLACE-0830 class B): landing_placement.tcl initialises cland_col_cursor at top level.
cland_ring_place and cland_column_select read it through `global`; set only inside other procs it is unset when a ring band is
the first band placed after the reader-start grow (KV hgi/io_cor/io_ft: 'can't read "cland_col_cursor": no such variable').
    python3 -m pytest -q tools/die_plan/test_cland_col_cursor_init.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).with_name("landing_placement.tcl")


def top_level(text):
    """the file without proc bodies (brace-matched), comments dropped"""
    out, i = [], 0
    while True:
        m = re.compile(r"(?m)^\s*proc\s+\S+\s+\{[^\n]*\}\s*\{").search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        depth, j = 1, m.end()
        while depth and j < len(text):
            c = text[j]
            if c == "\\":
                j += 1
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            j += 1
        i = j
    return "\n".join(ln for ln in "".join(out).splitlines() if not ln.lstrip().startswith("#"))


def test_top_level_initialises_both_cursors():
    top = top_level(TCL.read_text())
    assert re.search(r"(?m)^set cland_cursor \{\}\s*$", top)
    assert re.search(r"(?m)^set cland_col_cursor \{\}\s*$", top)


def test_readers_declare_global_and_init_precedes_them():
    text = TCL.read_text()
    for proc in ("cland_ring_place", "cland_column_select"):
        m = re.search(r"proc %s \{[^\n]*\}\s*\{(.*?)\n\}" % proc, text, re.S)
        assert m and "cland_col_cursor" in m.group(1), proc
    first_proc = re.search(r"(?m)^\s*proc cland_(?:ring_place|column_select) ", text).start()
    assert text.index("\nset cland_col_cursor {}") < first_proc


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_tclsh_global_read_of_initialised_var_works():
    prog = ("set cland_col_cursor {}\nproc rd {} {global cland_col_cursor; return [llength $cland_col_cursor]}\nputs [rd]\n")
    r = subprocess.run(["tclsh"], input=prog, capture_output=True, text=True)
    assert r.stdout.strip() == "0"
    r = subprocess.run(["tclsh"], input=prog.replace("set cland_col_cursor {}\n", ""), capture_output=True, text=True)
    assert "no such variable" in r.stderr          # the failure the one-line init removes
