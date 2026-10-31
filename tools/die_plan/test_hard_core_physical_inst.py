"""DIE-KV-49 10-31: a hard_cores[] entry may carry the kit-only physical identity (physical_inst/physical_master,
the contents[] form) so the kit places the core by its bound-netlist path; without it nothing changes."""
import json
from pathlib import Path
import pytest
import gen_phys as G
import schema as S


def _plan(alias=True):
    raw = json.loads((Path(__file__).parent / 'examples/tiny_plan.json').read_text())
    c = dict(inst='head0_e0', module='kv3_head_eighth_e0', origin_um=[17.28, 25.92], outline_um=[8.64, 8.64],
             orient='MX', lef='core.lef', lib='core_tt.lib')
    if alias:
        c.update(physical_inst='u_bound.u_head0_e0', physical_master='kv3_head_eighth_e0')
    raw['partition_types']['src']['hard_cores'] = [c]
    return S.Plan(raw), c


def test_hard_core_physical_inst_reaches_placement():
    p, c = _plan()
    assert G.type_macros(p, 'src')[0][:2] == ('u_bound.u_head0_e0', 'kv3_head_eighth_e0')
    assert c['inst'] == 'head0_e0'          # logical (bind / clock / pins) identity unchanged


def test_hard_core_without_alias_is_unchanged():
    p, c = _plan(False)
    assert G.type_macros(p, 'src')[0][:2] == ('head0_e0', 'kv3_head_eighth_e0')


def test_hard_core_incomplete_alias_fails_closed():
    p, c = _plan()
    c.pop('physical_master')
    with pytest.raises(ValueError, match='must be declared together'):
        G.type_macros(p, 'src')


def test_schema_accepts_hard_core_alias():
    p, c = _plan()
    assert not [e for e in S.validate(p.raw) if 'physical_' in e]
    c['physical_mastter'] = c.pop('physical_master')
    assert any('physical_mastter' in e for e in S.validate(p.raw))
