"""Mixed transport/mission wrappers must boot without releasing computation."""
import copy
import json
import re
from pathlib import Path

import pytest
import gen_rtl
import reset_tree as RT
import schema as S

HERE = Path(__file__).parent


def mixed():
    p = json.loads((HERE/'examples/tiny_plan.json').read_text())
    p['reset'].update(release='wavefront', start='broadcast')
    for ty in p['partition_types'].values():
        ty.pop('sources', None)
    p['partition_types']['mid']['reset'].update(bootstrap_buses=['fx_i', 'fx_o'])
    p['partition_types']['src']['reset'].update(bootstrap_contents=['u_core'])
    return p


def test_raw_transport_has_same_depth_and_mission_gate_survives():
    p = S.Plan(mixed()); t = RT.for_type(p, 'mid')
    rel = {r['q']: r for r in RT.start_relays(t)}
    for i in t['bootstrap_taps']:
        mission, boot = rel[f'rst_n_t{i}'], rel[f'rst_boot_t{i}']
        assert mission['role'] == 'gated' and 'run' in mission
        assert boot['role'] == 'bootstrap_transport' and 'run' not in boot
        assert boot['d'] == mission['d'] and boot['depth'] == mission['depth']
    w = RT.wf_plan(p)
    assert w['types']['mid']['bootstrap_buses'] == ['fx_i', 'fx_o']
    assert w['types']['mid']['start_role'] == 'mission'


def test_wrapper_uses_raw_only_for_declared_transport_and_content(tmp_path):
    p = mixed()
    gen_rtl.write_rtl(p, tmp_path)
    mid = (tmp_path/'tiny_mid.sv').read_text()
    assert re.search(r'u_ft_fx_s0.*?\.rst_n\(rst_boot_t', mid)
    assert re.search(r'u_ft_fr_s0.*?\.rst_n\(rst_n_t', mid)
    src = (tmp_path/'tiny_src.sv').read_text()
    assert re.search(r'\.rst_n\(rst_boot_t', src)
    assert 'wire rst_n = rst_n_t' in src


@pytest.mark.parametrize('field,value', [('bootstrap_buses',['unknown']), ('bootstrap_contents',['missing'])])
def test_unknown_consumers_fail_closed(field, value):
    p = mixed(); p['partition_types']['mid']['reset'][field] = value
    with pytest.raises(RT.ResetError, match='unknown bootstrap consumers'):
        RT.for_type(S.Plan(p), 'mid')


def test_declaration_without_broadcast_fails_closed():
    p = mixed(); p['reset']['start'] = 'none'
    with pytest.raises(RT.ResetError, match='START-broadcast'):
        RT.for_type(S.Plan(p), 'mid')
