import json
from types import SimpleNamespace
import pytest
import check
import r8


def vehicle(tmp_path, slow=4, capacity=None):
    raw={'die':{'name':'t'},'partitions':[{'name':'src','type':'S'},
         {'name':'s_A_x','type':'T'},{'name':'s_B_x','type':'T'}]}
    if capacity is not None:raw['partition_types']={'T':{'r8_strap_pad_max':capacity}}
    groups=[]
    for name,depth in [('A',1),('B',slow)]:
        groups.append(dict(sink=f'u_{name}',sink_part=f's_{name}_x',src_part='src',members=[
            dict(sink_port='d',sink_bits=[[0,1]],source='u_src.d',asbuilt_stages=0,
                 bound_stages=depth,landed_stages=depth,lane='L'+name)]))
    bg=dict(die='t',landing=groups,replica=[dict(source='u_src.d',asbuilt_stages=0,
                                             sink_parts=['s_A_x','s_B_x'])])
    oldex,oldld=list(r8.EXEMPT),dict(r8.LANDED,rx=list(r8.LANDED['rx']))
    try:
        r8.configure()
        table,_=r8.write_pads(raw,bg,tmp_path)
    finally:
        r8.EXEMPT[:]=oldex;r8.LANDED.clear();r8.LANDED.update(oldld)
    path=tmp_path/'groups.json';path.write_text(json.dumps(bg))
    return SimpleNamespace(raw=raw,name='t'),path,table


def test_explicit_optin_allows_real_count_sites_and_default_stays_off(tmp_path):
    p,g,t=vehicle(tmp_path)
    off=check.Report();st=check.check_r8(p,off,tmp_path,groups=g,landing=t)
    assert off.errors() and st['types_conflicting']==1
    on=check.Report();st=check.check_r8(p,on,tmp_path,groups=g,landing=t,strap_pads=True)
    assert not on.errors() and st['strap_site_count']==1
    assert st['strap_sites'][0]['span']==3 and st['strap_sites'][0]['strap_counts']==[0,3]


def test_capacity_metadata_does_not_implicitly_enable_strap_mode(tmp_path):
    p,g,t=vehicle(tmp_path,capacity=63)
    report=check.Report();st=check.check_r8(p,report,tmp_path,groups=g,landing=t)
    assert report.errors() and st['types_conflicting']==1


def test_optin_preserves_hardware_capacity_rejection(tmp_path):
    p,g,t=vehicle(tmp_path,slow=17)
    report=check.Report();check.check_r8(p,report,tmp_path,groups=g,landing=t,strap_pads=True)
    assert any('pad 16 > strap capacity 15' in x['msg'] for x in report.errors())


@pytest.mark.parametrize('enabled',[False,True])
def test_cli_flag_forwards_to_run_without_implicit_enable(tmp_path,monkeypatch,enabled):
    got={}
    monkeypatch.setattr(check.S,'load',lambda _: {})
    def fake_run(raw,**kwargs):got.update(kwargs);return check.Report(),{}
    monkeypatch.setattr(check,'run',fake_run)
    args=['plan.json','--out',str(tmp_path),'--quiet']
    if enabled:args.append('--r8-strap-pads')
    assert check.main(args)==0 and got['r8_strap_pads'] is enabled
