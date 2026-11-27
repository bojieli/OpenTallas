"""C-GPL-TD-CHAIN 11-27: gpl_td.tcl must wrap whatever ::global_placement is (guard alias, logic_cluster proc) without dropping a layer."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import logic_cluster as LC
import test_gpl_guard as TG
from test_gpl_td import CALL, MOCK, GP

needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
LC_WRAP = """
rename ::global_placement ::ot_lc_gpl_native
proc ::global_placement {args} {
  set rc [catch {uplevel 1 [list ::ot_lc_gpl_native {*}$args]} res opts]
  if {$rc == 0} { puts "LC APPLY" }
  return -options $opts $res
}
"""


def _lc_wrapper_text():
    """the real wrapper block of logic_cluster.tcl (generated), so the test follows the generator"""
    src = Path(LC.__file__).read_text()
    i = src.index('"if {$lc_post && [info commands ::ot_lc_gpl_native] eq')
    lines = re.findall(r'^\s*"(.*)",?\]?$', src[i:src.index("if firm_small:", i)], re.M)
    return "\n".join(l.replace('\\"', '"') for l in lines)


@needs_tcl
def test_guard_then_logic_cluster_then_gpl_td_keeps_every_layer(tmp_path):
    body = TG.MOCK % dict(INSTS=" ".join("{" + " ".join(map(str, i)) + "}" for i in TG.SPARSE),
                          ENV="set ::env(OT_GPL_TD_TOP) 0.25", GPL="ok")
    tail = f'\nset rc [catch {{global_placement {TG.ARGS}}} res]\nputs "RC=$rc"\n'
    out = subprocess.run(["tclsh"], input=body + TG.GUARD + LC_WRAP + GP + tail, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "LC APPLY" in out.stdout and "OT_GPL_TD_TOP" in out.stdout and "RC=0" in out.stdout, out.stdout
    assert len(re.findall(r"^CALL \d+:", out.stdout, re.M)) == 1, out.stdout


@needs_tcl
def test_the_generated_logic_cluster_wrapper_survives_gpl_td(tmp_path):
    lc = _lc_wrapper_text()
    assert "rename ::global_placement ::ot_lc_gpl_native" in lc
    pre = (MOCK % dict(CELLS="A B", RES=str(tmp_path), ENV="set ::env(OT_GPL_TD_TOP) 0.25")
           + "rename global_placement ot_native\nproc guard {args} { return [uplevel 1 [list ::ot_native {*}$args]] }\n"
           + "interp alias {} ::global_placement {} ::guard\nset lc_post 1\nproc ot_logic_cluster_apply {} { puts LCAPPLY }\n")
    out = subprocess.run(["tclsh"], input=pre + lc + "\n" + GP + f"\nglobal_placement {CALL}\nputs N=[llength $::calls]\n",
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "LCAPPLY" in out.stdout and "N=1" in out.stdout and "OT_GPL_TD_TOP" in out.stdout, out.stdout


@needs_tcl
def test_sourcing_twice_installs_once(tmp_path):
    pre = MOCK % dict(CELLS="A", RES=str(tmp_path), ENV="set ::env(OT_GPL_TD_TOP) 0.25")
    out = subprocess.run(["tclsh"], input=pre + GP + GP + f"global_placement {CALL}\nputs N=[llength $::calls]\n", capture_output=True, text=True)
    assert out.returncode == 0 and "N=1" in out.stdout and out.stdout.count("OT_GPL_TD_TOP") == 1, out.stdout + out.stderr
