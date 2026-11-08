import copy
import json
import subprocess
from pathlib import Path
import pytest
from tools.die_plan.landing_place import _native_stage_group_tcl, _dataflow_tcl

PROFILE = Path(__file__).parents[1] / 's81_head/profiles/head_lep_vf_placement.json'


def typ():
    row = dict(prefix=r'u_core\.g_s\\\[0\\\]', rect_um=[1, 2, 11, 12], tag='stage:pin_s0')
    return dict(outline_um=[100, 100], contents=[dict(inst='u_core', module='native', params={'N': 2})],
                clock={'landing_contract': {'native_stage_groups': dict(
                    schema='opentallas.native_stage_groups.v1', content='u_core', module='native',
                    params={'N': 2}, groups=[row])}})


def cfg(t):
    return t['clock']['landing_contract']['native_stage_groups']


def test_absent_preserves_output():
    assert _native_stage_group_tcl({}) == ''


def test_existing_native_group_reaches_same_escaped_generate_instance():
    t = typ()
    script = 'set cland_groups {}\n' + _native_stage_group_tcl(t)
    script += ('lassign [lindex $cland_groups 0] p r tag\n'
               'puts [regexp [format {(^|[/.])%s[/.]} $p] {u_core.g_s\\[0\\].q}]\n'
               'puts [llength $cland_groups]\n')
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
    assert result.stdout.splitlines() == ['1', '1']


@pytest.mark.parametrize('change', ['module', 'params', 'content', 'outside', 'duplicate', 'command', 'nan', 'bool', 'coherence'])
def test_bad_native_profile_fails_closed(change):
    t = typ(); c = cfg(t); row = c['groups'][0]
    if change == 'module': c['module'] = 'other'
    if change == 'params': c['params']['N'] = 3
    if change == 'content': c['content'] = 'missing'
    if change == 'outside': row['rect_um'][2] = 101
    if change == 'duplicate': c['groups'].append(copy.deepcopy(row))
    if change == 'command': row['prefix'] += ';puts'
    if change == 'nan': row['rect_um'][0] = float('nan')
    if change == 'bool': row['rect_um'][0] = True
    if change == 'coherence':
        other = copy.deepcopy(row); other['prefix'] += '_next'; other['rect_um'][0] = 2; c['groups'].append(other)
    with pytest.raises(ValueError): _native_stage_group_tcl(t)


def test_dataflow_constructor_installs_native_before_actual_placer():
    t = typ(); c = t['clock']['landing_contract']; c.update(monitor='dataflow', bands={}, pins=[])
    script = _dataflow_tcl('example', c, t)
    assert script.index('lappend ::cland_groups') < script.index('proc cland_group_insts')
