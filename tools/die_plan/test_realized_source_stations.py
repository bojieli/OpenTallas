"""Declared relay stages must exist in both emitted source and its placement handoff."""
import copy
import json
from pathlib import Path
import pytest
import gen_rtl as G


def plan():
    p = json.loads(Path(__file__).with_name('examples').joinpath('tiny_plan.json').read_text())
    p['partition_types']['mid']['internal_stations'] = [
        dict(conn='bus:cfg_i', from_um=[0, 10], to_um=[30, 10], regs_um=[[10, 10], [20, 10]], bits=9),
        dict(conn='bus:cfg_o', from_um=[30, 20], to_um=[50, 20], regs_um=[[40, 20]], bits=9)]
    return p


def test_declared_but_unrealized_default_remains_explicit_and_optin_realizes(tmp_path):
    p = plan(); G.write_rtl(p, tmp_path / 'legacy')
    module = p['partition_types']['mid']['module']
    assert 'u_ist_' not in (tmp_path / 'legacy' / (module + '.sv')).read_text()
    p['partition_types']['mid']['realize_internal_stations'] = True
    G.write_rtl(p, tmp_path / 'real')
    text = (tmp_path / 'real' / (module + '.sv')).read_text()
    assert 'u_ist_cfg_i_0' in text and 'u_ist_cfg_i_1' in text and 'u_ist_cfg_o_0' in text
    assert '.d(cfg_i_q)' in text and '.d(cfg_o_is0_q)' in text
    placement = (tmp_path / 'real' / (module + '.istations.tcl')).read_text()
    assert 'u_ist_cfg_i_1' in placement and 'u_ist_cfg_o_0' in placement


def test_optin_without_declared_stations_fails(tmp_path):
    p = plan(); p['partition_types']['mid']['internal_stations'] = []
    p['partition_types']['mid']['realize_internal_stations'] = True
    with pytest.raises(G.GenError, match='explicit planned stations'):
        G.write_rtl(p, tmp_path / 'bad')
