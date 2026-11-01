"""Explicit PG coverage follows actual physical PHY bodies, never shifts signal IO."""
import copy
from types import SimpleNamespace
import pytest
import die_io as D


def fixture():
    typ=dict(contents=[dict(inst='logical_phy',module='ot_pdie_serdes',physical_inst='u_bound.u_phy',
                           physical_master='ot_pdie_serdes_w1',lef='actual.lef',
                           origin_um=[20,20],outline_um=[60,60])])
    window=dict(name='io',part='p',iface='serdes',rect_um=[0,0,100,100])
    domain=dict(name='phy',io=['io'],nets=['VDDPHY','VSS'],rect_um=[20,20,80,80],
                phy_macro_um=[20,20,80,80],bumps=dict(rect_um=[25,25,75,75],pitch_um=10),
                grid=[dict(layer='M8',width_um=.4,pitch_um=10,offset_um=4)])
    P=SimpleNamespace(parts={'p':{'type':'T'}},types={'T':typ},ptype=lambda p:typ,
                      to_die=lambda p,xy:xy,rect=lambda p:[0,0,100,100],
                      layer_budget={'die_layers':['M8']},die=dict(io=[window],pg=dict(domains=[domain])))
    return P,domain,window,typ


def audit(P):
    errors=[]
    D.check_pg_domains(P,SimpleNamespace(err=lambda *a,**k:errors.append(a),warn=lambda *a,**k:None))
    return errors


def bind(d):
    d['phy_macro_binding']=dict(part='p',inst='u_bound.u_phy',module='ot_pdie_serdes_w1')


def test_default_requires_full_window_but_explicit_actual_phy_body_is_covered():
    p,d,w,t=fixture();original=copy.deepcopy(w)
    assert audit(p)  # old/default full-window contract remains strict
    bind(d)
    assert not audit(p)
    assert w==original
    assert D.bound_phy_macro(p,d)['rect_um']==[20,20,80,80]


@pytest.mark.parametrize('mutation', [
    lambda p,d,w,t:d['phy_macro_binding'].update(inst='logical_phy'),
    lambda p,d,w,t:d['phy_macro_binding'].update(module='wrong'),
    lambda p,d,w,t:d['phy_macro_binding'].update(part='unknown'),
    lambda p,d,w,t:t['contents'][0].pop('lef'),
    lambda p,d,w,t:t['contents'][0].update(module='SRAM'),
    lambda p,d,w,t:d.update(rect_um=[21,20,80,80]),
    lambda p,d,w,t:d.update(phy_macro_um=[20,20,79,80]),
    lambda p,d,w,t:w.update(part='other'),
    lambda p,d,w,t:w.update(iface='ucie'),
    lambda p,d,w,t:w.update(rect_um=[30,20,100,100]),
])
def test_wrong_identity_or_incomplete_physical_coverage_rejects(mutation):
    p,d,w,t=fixture();bind(d);mutation(p,d,w,t)
    assert audit(p)


def test_partition_mirror_is_applied_to_exact_macro_footprint():
    p,d,w,t=fixture();bind(d)
    t['contents'][0]['origin_um']=[10,20]
    p.to_die=lambda part,xy:(100-xy[0],xy[1])
    d.update(rect_um=[30,20,90,80],phy_macro_um=[30,20,90,80])
    d['bumps']['rect_um']=[35,25,85,75]
    assert not audit(p)
    assert D.bound_phy_macro(p,d)['rect_um']==[30,20,90,80]


def test_anchored_bump_sites_are_validated_without_changing_default(monkeypatch):
    import sys
    calls=[]
    def sites(domain):
        calls.append(domain['name'])
        raise ValueError('anchored site outside rectangle')
    monkeypatch.setitem(sys.modules,'phy_bumps',SimpleNamespace(sites=sites))
    p,d,w,t=fixture();bind(d)
    assert not audit(p) and not calls
    d['bumps']['origin_um']=[30,30]
    assert audit(p) and calls==['phy']


def test_real_anchored_bump_helper_integrates_with_body_coverage():
    p,d,w,t=fixture();bind(d)
    d['bumps'].update(origin_um=[30,30],counts=[5,5])
    assert not audit(p)
    d['bumps']['counts']=[6,5]
    assert audit(p)  # fixed site x80 leaves bump rectangle x75


def compound_fixture():
    p,d,w,t=fixture()
    t['contents']=[dict(inst='logical_phy',module='ot_pdie_serdes',physical_parts=[
        dict(physical_inst='u_phy.tx',physical_master='tx_macro',lef='tx.lef',
             origin_um=[30,60],outline_um=[20,10]),
        dict(physical_inst='u_phy.rx',physical_master='rx_macro',lef='rx.lef',
             origin_um=[50,60],outline_um=[20,10]),
        dict(physical_inst='u_phy.decoder',physical_master='SRAM',lef='ram.lef',
             origin_um=[1,1],outline_um=[10,10])])]
    d['phy_macro_binding']=dict(part='p',inst='logical_phy',module='ot_pdie_serdes',
                                physical_parts=['u_phy.tx','u_phy.rx'])
    d['phy_macro_um']=[30,60,70,70]
    # Signal contacts remain on the shore; their rectangle is deliberately
    # independent of the compound power body. Decoder SRAM stays on core VDD.
    w['rect_um']=[0,0,100,50]
    return p,d,w,t


def test_compound_pg_body_binds_only_named_physical_parts_and_keeps_signal_window():
    p,d,w,t=compound_fixture();original=copy.deepcopy(w)
    assert not audit(p)
    body=D.bound_phy_macro(p,d)
    assert body['rect_um']==[30,60,70,70] and body['pg_only']
    assert body['physical_parts']==['u_phy.tx','u_phy.rx']
    assert w==original


@pytest.mark.parametrize('mutation', [
    lambda p,d,w,t:d['phy_macro_binding'].update(physical_parts=[]),
    lambda p,d,w,t:d['phy_macro_binding'].update(physical_parts=['u_phy.tx','u_phy.tx']),
    lambda p,d,w,t:d['phy_macro_binding'].update(physical_parts=['unknown']),
    lambda p,d,w,t:d['phy_macro_binding'].update(inst='wrong'),
    lambda p,d,w,t:d['phy_macro_binding'].update(module='SRAM'),
    lambda p,d,w,t:t['contents'][0]['physical_parts'][0].pop('lef'),
    lambda p,d,w,t:t['contents'][0]['physical_parts'][0].update(outline_um=[float('nan'),10]),
    lambda p,d,w,t:t['contents'][0]['physical_parts'].append(copy.deepcopy(t['contents'][0]['physical_parts'][0])),
    lambda p,d,w,t:d.update(rect_um=[31,20,80,80]),
    lambda p,d,w,t:w.update(part='other'),
])
def test_compound_binding_rejects_ambiguous_unphysical_or_uncovered_parts(mutation):
    p,d,w,t=compound_fixture();mutation(p,d,w,t)
    assert audit(p)


def test_compound_body_uses_type_coordinates_and_partition_mirror():
    p,d,w,t=compound_fixture()
    # Logical lot origin must not offset its physical parts a second time.
    t['contents'][0]['origin_um']=[500,500]
    p.to_die=lambda part,xy:(100-xy[0],xy[1])
    assert D.bound_phy_macro(p,d)['rect_um']==[30,60,70,70]


def test_compound_binding_schema_is_explicit_without_widening_direct_binding():
    import jsonschema
    import schema
    binding=schema.SCHEMA['properties']['die']['properties']['pg']['properties']['domains']['items']['properties']['phy_macro_binding']
    p,d,w,t=compound_fixture()
    jsonschema.validate(d['phy_macro_binding'],binding)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(dict(d['phy_macro_binding'],physical_parts=[]),binding)
