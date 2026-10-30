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
