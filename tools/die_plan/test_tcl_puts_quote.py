"""TCL-PUTS-QUOTE (GEN-CLASS-1 11-12, class of CLAND-PUTS-QUOTE 7fa736b945): every generated puts "..." that carries a
plan value (instance / port / net name, which can hold a bus index [k], or a python list) prints it as text.
tclsh evaluates the real generated line with the value; before the fix '[1]' ran as a command."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g2  # noqa: E402
import signed_children as SC  # noqa: E402
import signoff as SO  # noqa: E402

needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
NASTY = 'u_bound.g_w[1].u_m$x"q\\[2]'


def tcl_out(line, pre=""):
    r = subprocess.run(["tclsh"], input=pre + line + "\n", capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.mark.parametrize("mod", [g2, SC, SO])
def test_tq_round_trips_in_tcl(mod):
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    for v in (NASTY, "[72.38399999999999, 0.0]", "plain_name", 'a"b'):
        assert tcl_out(f'puts "{mod._tq(v)}"') == v


@needs_tclsh
def test_signed_children_puts_line():
    src = (HERE / "signed_children.py").read_text()
    m = re.search(r'f"puts \\"hard child \{_tq\(c\[\'inst\'\]\)\}', src)
    assert m, "hard child puts must quote the instance name"
    c = dict(inst="u_bound.g_w[1].u_m", orient="R0", at=[1.0, 2.0])
    gen = f"puts \"hard child {SC._tq(c['inst'])} -> [$i getName] {c['orient']} at {c['at'][0]} {c['at'][1]}\""
    out = tcl_out(gen, pre='proc fake {m} {return {real[3]}}\nset i fake\n')
    assert out == "hard child u_bound.g_w[1].u_m -> real[3] R0 at 1.0 2.0"


@needs_tclsh
def test_signoff_ft_arc_line():
    txt = SO.ft_char_tcl(dict(arcs=[dict(source="ft_i[3]", sink="ft_o[3]")]))
    line = next(l for l in txt.splitlines() if l.startswith('puts "SO_FT_ARC'))
    assert tcl_out(line, pre="array set so_ft_v {min 1.0 max 2.0}\n") == "SO_FT_ARC ft_i[3] ft_o[3] 1.0 2.0"


def test_g2_reach_line_quotes_net():
    src = (HERE / "g2.py").read_text()
    assert "OT_REACH {_tq(net)}" in src
