"""Keep a native logical leaf while placing/powering its exact physical specialization."""
import copy,json
from pathlib import Path
import pytest
import gen_phys as G
import schema as S


def _plan(alias=True):
    raw=json.loads((Path(__file__).parent/'examples/tiny_plan.json').read_text())
    c=dict(inst='serdes',module='logical_phy',status='planned',origin_um=[17.28,25.92],outline_um=[8.64,8.64],lef='phy.lef',lib='phy_tt.lib')
    if alias:c.update(physical_inst='u_bound.u_core.u_phy.g_native.u_macro',physical_master='fixed_w522')
    raw['partition_types']['src']['contents']=[c]
    p=S.Plan(raw);n=next(n for n,r in p.parts.items() if r['type']=='src');a=p.to_die(n,(17.28,25.92));b=p.to_die(n,(25.92,34.56))
    raw['die']['pg']={'domains':[dict(name='native_phy',nets=['VDDPHY_SW','VSS'],rect_um=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])])]}
    return S.Plan(raw),c


def test_alias_reaches_placement_and_only_the_phy_power_connection(tmp_path):
    p,c=_plan();before=copy.deepcopy(c)
    (tmp_path/'phy.lef').write_text('MACRO fixed_w522\n PIN VDD\n PORT\n LAYER M6 ;\n END\n END VDD\n PIN VSS\n PORT\n LAYER M6 ;\n END\n END VSS\nEND fixed_w522\n')
    macros=G.type_macros(p,'src');assert macros[0][:2]==(c['physical_inst'],'fixed_w522')
    doms=G.phy_pg_domains(p,'src');assert doms[0][4]==[c['physical_inst']]
    text=G.phy_pg_pdn(p,'src',doms,macros,root=tmp_path)
    escaped=G._tcl_re(c['physical_inst'])
    assert f'add_global_connection -net {{VDDPHY_SW}} -inst_pattern {{^({escaped})$}} -pin_pattern {{^VDD$}} -power' in text
    assert f'-macro -name {{ot_phy_pg_0_macro}} -instances {{{G._pdn_inst_patterns([c["physical_inst"]])}}}' in text
    assert c==before  # Functional bind sees the same inst/module/params object.


def test_existing_macro_identity_is_unchanged_without_specialization():
    p,c=_plan(False);assert G.type_macros(p,'src')[0][:2]==('serdes','logical_phy')
    assert G.phy_pg_domains(p,'src')[0][4]==['serdes']


@pytest.mark.parametrize('missing',['physical_inst','physical_master'])
def test_incomplete_physical_alias_fails_before_a_kit_can_be_placed(missing):
    p,c=_plan();c.pop(missing)
    with pytest.raises(ValueError,match='must be declared together'):G.type_macros(p,'src')


def test_schema_accepts_explicit_alias_but_rejects_unknown_spelling():
    p,c=_plan();assert not [e for e in S.validate(p.raw) if 'physical_' in e]
    c['physical_mastter']=c.pop('physical_master')
    assert any('physical_mastter' in e for e in S.validate(p.raw))
