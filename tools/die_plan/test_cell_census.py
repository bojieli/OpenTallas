"""cell_census.tcl (VSN6-B 11-11, S7 class fix from HBM vsN6 form3): the non-tap count is recounted at every hook stage,
tap/endcap cells apart, with a max-wire buffer estimate before GRT, and every call prints one loud line against the
400k run cap (ADVISORY: it never stops a run).  OpenDB mock in tclsh."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).parent
CENSUS = HERE / 'cell_census.tcl'

MOCK = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1000}
set INSTS {}; set NETS {}
proc blk {m} {switch $m {getInsts {return $::INSTS} getNets {return $::NETS}}}
proc m_std {m} {switch $m {isBlock {return 0} getName {return BUFx2_ASAP7_75t_R}}}
proc m_tap {m} {switch $m {isBlock {return 0} getName {return TAPCELL_ASAP7_75t_R}}}
proc m_mac {m} {switch $m {isBlock {return 1} getName {return srambank}}}
proc i_std {m} {switch $m {getMaster {return m_std} getPlacementStatus {return PLACED}}}
proc i_tap {m} {switch $m {getMaster {return m_tap}}}
proc i_mac {m} {switch $m {getMaster {return m_mac}}}
# placed std cell at (x um, y um)
proc pinst {name x y {st PLACED}} {
  lappend ::INSTS $name
  proc $name {m} "switch \$m {getMaster {return m_std} getPlacementStatus {return $st} getLocation {return {[expr {$x*1000}] [expr {$y*1000}]}}}"
}
proc mknet {name sig insts} {
  lappend ::NETS $name
  set its {}
  foreach i $insts { proc it_${name}_$i {m} "return $i"; lappend its it_${name}_$i }
  proc $name {m} "switch \$m {getSigType {return $sig} getITerms {return {$its}} getBTerms {return {}}}"
}
'''


def run(tmp_path, body, stage, env=''):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    kit = tmp_path / 'kit'
    kit.mkdir(exist_ok=True)
    shutil.copyfile(CENSUS, kit / 'cell_census.tcl')
    script = (MOCK + body + f'\n{env}\nproc wrap {{}} {{ uplevel #0 [list source {{{kit / "cell_census.tcl"}}}] }}\n'
              + f'wrap\nputs "RET [ot_cell_census {stage}]"\n')
    p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr[-3000:]
    line = [l for l in p.stdout.splitlines() if l.startswith('OT_CELL_CENSUS')]
    assert len(line) == 1, p.stdout
    rec = [json.loads(l) for l in (kit / 'cell_census.jsonl').read_text().splitlines()]
    return line[0], rec[-1]


def test_form3_counts_split_tap_from_nontap(tmp_path):
    """vsN6 form3 after GRT: 440,169 leaf instances = 196,595 TAPCELL/endcap + 243,574 non-tap.  Under the cap."""
    body = 'set INSTS [concat [lrepeat 243574 i_std] [lrepeat 196595 i_tap] [lrepeat 3 i_mac]]\n'
    line, rec = run(tmp_path, body, 'grt')
    assert 'stage=grt nontap=243574 tap_endcap=196595 macros=3 recount (no estimate) projected_nontap=243574' in line, line
    assert 'cap=400000: OK (60.9% of cap' in line, line
    assert rec['nontap'] == 243574 and rec['tap_endcap'] == 196595 and rec['verdict'] == 'OK'


def test_place_stage_estimates_maxwire_buffers(tmp_path):
    body = r'''
pinst a 0 0; pinst b 200 0; pinst c 300 200; pinst d 10 0; pinst u 0 0 UNPLACED
mknet n_short SIGNAL {a d}
mknet n_200 SIGNAL {a b}
mknet n_500 SIGNAL {a c}
mknet n_clk CLOCK {a b c}
mknet n_un SIGNAL {a u}
'''
    line, rec = run(tmp_path, body, 'place', 'set ::env(OT_MAXWIRE_UM) 80')
    # n_200: ceil(200/80)-1 = 2; n_500 (HPWL 300+200): ceil(500/80)-1 = 6; short and clock nets add none
    assert 'maxwire_est=+8 (OT_MAXWIRE_UM 80, nets measured 3, unplaced 1)' in line, line
    assert 'nontap=5 ' in line and 'projected_nontap=13' in line and ': OK' in line, line
    assert rec['maxwire_est'] == 8 and rec['nets_unplaced'] == 1


def test_projection_over_cap_is_loud(tmp_path):
    body = 'set INSTS [lrepeat 399995 i_std]\npinst a 0 0; pinst b 800 0\nmknet n SIGNAL {a b}\n'
    line, rec = run(tmp_path, body, 'cts', 'set ::env(OT_MAXWIRE_UM) 80')
    assert 'nontap=399997' in line and 'maxwire_est=+9' in line and 'projected_nontap=400006' in line, line
    assert ': WARN OVER_CAP' in line and rec['verdict'] == 'WARN OVER_CAP'


def test_near_cap_and_custom_cap(tmp_path):
    line, _ = run(tmp_path, 'set INSTS [lrepeat 365000 i_std]\n', 'grt')
    assert ': WARN NEAR_CAP' in line, line
    line, rec = run(tmp_path, 'set INSTS [lrepeat 100 i_std]\n', 'route', 'set ::env(OT_CELL_CENSUS_CAP) 90')
    assert 'cap=90: WARN OVER_CAP' in line and rec['cap'] == 90


@pytest.mark.parametrize('hook,stage', [('cts_post.tcl', 'cts'), ('grt_post.tcl', 'grt'), ('face_flops.tcl', 'floorplan')])
def test_static_hooks_call_census_or_warn(hook, stage):
    text = (HERE / hook).read_text()
    assert f'ot_cell_census {stage}' in text
    assert f'OT_CELL_CENSUS WARN stage={stage}: cell_census.tcl is not in the kit' in text


def test_gen_phys_copies_census_and_hooks_place():
    text = (HERE / 'gen_phys.py').read_text()
    assert '"cell_census.tcl"' in text and 'ot_cell_census place' in text
