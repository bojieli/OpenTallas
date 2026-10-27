import copy
from types import SimpleNamespace
import die_io


def vehicle():
    c=dict(inst='leaf',module='m',status='reuse',lef='model.lef',origin_um=[10,20],outline_um=[70,60])
    d=dict(name='phy',nets=['VDDPHY','VSS'],io=['sig'],rect_um=[10,20,80,80],phy_macro_um=[10,20,80,80],grid=[],bumps=dict(rect_um=[15,25,75,75],pitch_um=45))
    p=SimpleNamespace(die=dict(io=[dict(name='sig',part='p',iface='serdes',rect_um=[0,0,100,100])],pg=dict(domains=[d])),layer_budget={},parts={'p':{}},rect=lambda n:[0,0,100,100],ptype=lambda n:dict(contents=[c]),to_die=lambda n,xy:xy)
    return p,c,d


def findings(p):
    errors=[]
    r=SimpleNamespace(err=lambda check,msg:errors.append(msg),warn=lambda *a:None)
    die_io.check_pg_domains(p,r)
    return errors


def test_exact_physical_leaf_separates_glue():
    p,c,d=vehicle();assert not findings(p)


def test_no_lef_cannot_shrink_supply():
    p,c,d=vehicle();c.pop('lef');assert findings(p)


def test_wrong_actual_footprint_cannot_shrink_supply():
    p,c,d=vehicle();c['outline_um']=[69,60];assert findings(p)


def test_domain_cannot_include_unrelated_glue():
    p,c,d=vehicle();d['rect_um']=[9,20,80,80];assert findings(p)
