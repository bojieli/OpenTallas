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
