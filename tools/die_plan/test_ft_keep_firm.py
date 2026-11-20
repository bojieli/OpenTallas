"""FT site authority must survive DPL only when explicitly selected."""
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import gen_phys as G
import schema as S


def run_release(tmp_path, flag=None):
    names = ['u_bound.u_ft_ft0_o_0/q0', 'u_bound.u_ft_ft0_s1/q0',
             'u_bound.u_ft_ft1_o_0/q0', 'u_bound.u_ft_ft0_o_0/inv',
             'u_bound.u_rrl_5/q']
    (tmp_path/'ot_face_flops.txt').write_text(''.join(n+'\tW\t1\t2\tport\n' for n in names))
    (tmp_path/'ot_reset_pair_fixed.txt').write_text(names[-1]+'\n')
    mock = r'''
namespace eval ord {proc get_db_block {} {return block}}
proc block {method nm} {return $::byname($nm)}
proc dffmaster {method} {return DFFHQNx1_ASAP7_75t_R}
proc invmaster {method} {return INVx1_ASAP7_75t_R}
proc inst {id method args} {
 switch $method {
  getName {return $::nm($id)}
  getMaster {return [expr {$id == 3 ? "invmaster" : "dffmaster"}]}
  getPlacementStatus {return $::state($id)}
  setPlacementStatus {set ::state($id) [lindex $args 0]}
 }
}
'''
    for i,n in enumerate(names):
        mock += f'set nm({i}) {{{n}}}\nset byname({n}) f{i}\nset state({i}) FIRM\ninterp alias {{}} f{i} {{}} inst {i}\n'
    mock += f'set ::env(RESULTS_DIR) {{{tmp_path}}}\nset ::env(OT_RESET_PAIR_FIXED) 1\n'
    if flag is not None:
        mock += f'set ::env(OT_FT_KEEP_FIRM) {{{flag}}}\n'
    mock += f'if {{[catch {{source {{{BASE / "face_flops_release.tcl"}}}}} e]}} {{puts stderr $e;exit 1}}\n'
    mock += 'puts "STATES $state(0) $state(1) $state(2) $state(3) $state(4)"\n'
    return subprocess.run(['tclsh'], input=mock, text=True, capture_output=True)


def test_default_off_releases_ft_and_preserves_existing_reset_anchor(tmp_path):
    p = run_release(tmp_path)
    assert p.returncode == 0, p.stderr
    assert 'STATES PLACED PLACED PLACED PLACED FIRM' in p.stdout


def test_opt_in_preserves_selected_ft_dffs_only(tmp_path):
    p = run_release(tmp_path, 'ft0')
    assert p.returncode == 0, p.stderr
    assert 'STATES FIRM FIRM PLACED PLACED FIRM' in p.stdout
    assert 'OT_FT_KEEP_FIRM ft0 2' in p.stdout


def test_missing_selected_slot_refuses_silent_zero(tmp_path):
    p = run_release(tmp_path, 'ft_missing')
    assert p.returncode != 0
    assert 'without FIRM DFFs' in p.stderr


def test_generator_flag_and_schema_are_default_off_and_synchronized():
    assert G.ft_keep_firm_exports({}) == []
    assert G.ft_keep_firm_exports({'ft_slots': [{'name': 'ft0'}]}) == []
    assert G.ft_keep_firm_exports({'ft_slots': [{'name': 'ft0', 'keep_firm': True}]}) == [
        'export OT_FT_KEEP_FIRM = ft0']
    with pytest.raises(ValueError, match='boolean'):
        G.ft_keep_firm_exports({'ft_slots': [{'name': 'ft0', 'keep_firm': 'yes'}]})
    assert json.loads((BASE/'die_plan.schema.json').read_text()) == S.SCHEMA
    props = S.SCHEMA['properties']['partition_types']['additionalProperties']['properties']
    item = props['ft_slots']['items']
    row = dict(name='ft0', in_face='E', out_face='W', width=512, stations=8, keep_firm=True)
    jsonschema.validate(row, item)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(row, keep_firm='yes'), item)


def _grown(tmp_path, keep):
    """CLAND_RELEASE_GROWN_TCL on a mock row: tap | ft0 flop on the tap | ft0 flop free | ft1 flop on a tap | cland on a tap"""
    import re
    rel = (BASE / "face_flops_release.tcl").read_text()
    proc = re.search(r"^proc ff_ft_keep_slot \{nm\} \{.*?^\}", rel, re.S | re.M).group(0)
    cells = [("TAP_1", "FIXED", 0, 54), ("u_bound.u_ft_ft0_o_0/q1", "FIRM", 27, 351), ("u_bound.u_ft_ft0_o_0/q2", "FIRM", 400, 724),
             ("TAP_2", "FIXED", 1000, 1054), ("u_bound.u_ft_ft1_o_0/q1", "FIRM", 1027, 1351),
             ("TAP_3", "FIXED", 2000, 2054), ("u_cland_a/x", "FIRM", 2027, 2100)]
    mock = proc + r'''
proc block {method} {return $::insts}
proc master {method} {return 0}
proc bbox {id method} {return [expr {$method eq "yMin" ? 0 : ($method eq "xMin" ? $::x0($id) : $::x1($id))}]}
proc inst {id method args} {
 switch $method {
  getName {return $::nm($id)}
  getMaster {return master}
  getBBox {return b$id}
  getPlacementStatus {return $::state($id)}
  setPlacementStatus {set ::state($id) [lindex $args 0]}
 }
}
set ff_blk block
'''
    for i, (n, st, a, b) in enumerate(cells):
        mock += f'set nm({i}) {{{n}}}\nset state({i}) {st}\nset x0({i}) {a}\nset x1({i}) {b}\ninterp alias {{}} c{i} {{}} inst {i}\ninterp alias {{}} b{i} {{}} bbox {i}\nlappend insts c{i}\n'
    if keep:
        mock += f'set ::env(OT_FT_KEEP_FIRM) {{{keep}}}\n'
    mock += G.CLAND_RELEASE_GROWN_TCL + '\nputs "STATES $state(1) $state(2) $state(4) $state(6)"\n'
    return subprocess.run(['tclsh'], input=mock, text=True, capture_output=True)


def test_keep_firm_flop_on_a_tap_cell_is_released_for_dpl(tmp_path):
    """leaf__t21 11-19: 3_5 DPL-0033, 202 of 11,050 keep_firm ft2 / ft3 flops FIRM on TAPCELL / PHY_EDGE sites"""
    p = _grown(tmp_path, 'ft0')
    assert p.returncode == 0, p.stderr
    # the ft0 flop on the tap goes to PLACED, the free ft0 flop stays FIRM, ft1 (not keep_firm) is not this block's, cland as before
    assert 'STATES PLACED FIRM FIRM PLACED' in p.stdout, p.stdout
    assert 'OT_FT_KEEP_FIRM released 1 keep_firm ft station cells' in p.stdout
    assert 'OT_CLAND released 1 FIRM cland cells' in p.stdout


def test_without_keep_firm_the_scan_releases_cland_only(tmp_path):
    p = _grown(tmp_path, None)
    assert p.returncode == 0, p.stderr
    assert 'STATES FIRM FIRM FIRM PLACED' in p.stdout, p.stdout
    assert 'OT_FT_KEEP_FIRM released' not in p.stdout
