"""Top-owned freed channels retain clock sites; macros/PHY remain excluded."""
from types import SimpleNamespace
import die_trial as D
from clock_reach import actual_reach


def plan(channels=(),cores=(),phy=()):
    return SimpleNamespace(W=900,H=200,parts={'a':{'type':'t','origin_um':[0,0]},'b':{'type':'t','origin_um':[800,0]}},
        types={'t':{'outline_um':[100,200],'hard_cores':list(cores)}},
        die={'channels':list(channels),'pg':{'domains':list(phy)}},to_die=lambda n,q:((0 if n=='a' else 800)+q[0],q[1]))


def test_declared_freed_channel_is_legal_but_arbitrary_whitespace_is_not():
    assert not D.SiteMap(plan()).legal((450,50))
    s=D.SiteMap(plan([{'rect_um':[100,0,800,100]}]))
    assert s.legal((450,50))
    assert not s.legal((450,150))


def test_channel_never_releases_a_phy_or_macro_blockage():
    s=D.SiteMap(plan([{'rect_um':[0,0,900,200]}],
        cores=[{'origin_um':[20,20],'outline_um':[40,40]}],
        phy=[{'rect_um':[400,20,500,80],'nets':['VDDPHY','VSS']}]))
    assert not s.legal((40,40))
    assert not s.legal((450,50))
    assert s.legal((650,50))


def test_repeater_construction_uses_freed_channel_instead_of_crossing_it():
    s=D.SiteMap(plan([{'rect_um':[100,0,800,200]}]))
    nodes={0:{'x':50,'y':100,'parent':None,'taps':[]},1:{'x':850,'y':100,'parent':0,'taps':[]}}
    _,places,_,buf,parent=D.tree_netlist(nodes,[],rep_um=200,site=s,clock_cell='inv2')
    report=actual_reach({'sites':{n:[x,y] for n,x,y in places},'parent_of':parent,'node_buf':buf,'taps':[]},405)
    assert report['verdict']=='PASS'
    assert report['worst_um']<=200
