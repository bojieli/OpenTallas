"""A Tcl comment after the body of a one-line `if {...} {...}` is read as extra arguments of if: the step dies (tt_setup_repair.tcl line 134, 28 trees since 04:19)."""
import re
import subprocess
import shutil
from pathlib import Path

DIR = Path(__file__).resolve().parent
ONE_LINE_IF = re.compile(r"^\s*(?:\}\s*)?(?:else)?if\s*\{.*\}\s*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s+#")


def test_no_tcl_file_has_a_comment_trailing_a_one_line_if_body():
    bad = []
    for f in sorted(DIR.rglob("*.tcl")):
        for n, ln in enumerate(f.read_text(errors="replace").splitlines(), 1):
            if ONE_LINE_IF.match(ln):
                bad.append(f"{f.relative_to(DIR)}:{n}")
    assert not bad, bad


def test_tt_setup_repair_parses_with_tclsh():
    tclsh = shutil.which("tclsh")
    if not tclsh:
        return
    script = "set f [open $argv r]; set s [read $f]; close $f; if {![info complete $s]} {puts INCOMPLETE; exit 1}; " \
             "proc unknown {args} {return}; proc ot_tt_est {} {}; set ::env(ODB) /x; " \
             "foreach l [split $s \"\\n\"] { if {[regexp {^\\s*if \\{.*\\} \\{.*\\}\\s+#} $l]} {puts \"TRAILING: $l\"; exit 2} }; puts OK"
    r = subprocess.run([tclsh], input=script.replace("$argv", "\"%s\"" % (DIR / "tt_setup_repair.tcl")), capture_output=True, text=True)
    assert "OK" in r.stdout, r.stdout + r.stderr
