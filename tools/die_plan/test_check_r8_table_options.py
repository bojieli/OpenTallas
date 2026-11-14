import json
from types import SimpleNamespace
import pytest
import check
import r8


@pytest.fixture(autouse=True)
def restore_r8_options():
    ex, ld = list(r8.EXEMPT), dict(r8.LANDED, rx=list(r8.LANDED['rx']))
    yield
    r8.EXEMPT[:] = ex
    r8.LANDED.clear(); r8.LANDED.update(ld)


def state():
    return ([x.pattern for x in r8.EXEMPT], {**r8.LANDED, 'rx':[x.pattern for x in r8.LANDED['rx']]})


def vehicle(tmp_path, exempt=(), landed=False, window=4):
    raw = {'die':{'name':'t'}, 'partitions':[{'name':'s','type':'S'},{'name':'d','type':'D'}]}
    members = [dict(sink_port=port, sink_bits=[[0,0]], source='u_src.'+port,
                    asbuilt_stages=asb, bound_stages=bnd, landed_stages=bnd, lane='L'+port,
                    **({'landed_bundle':True} if landed else {}))
               for port,asb,bnd in ([('d',0,10),('kreq',3,10)] if landed else [('d',0,5),('kreq',0,9)])]
    bg = {'die':'t','landing':[dict(sink='u_dst',sink_part='d',src_part='s',members=members)],'replica':[]}
    r8.configure(exempt, (), window, .5, 'keep')
    table, _ = r8.write_pads(raw,bg,tmp_path)
    groups = tmp_path/'groups.json';groups.write_text(json.dumps(bg))
    return SimpleNamespace(raw=raw,name='t'), groups, table


def test_header_exempt_is_applied_and_never_leaks(tmp_path):
    p,bg,table=vehicle(tmp_path,exempt=['^kreq$'])
    r8.configure(['ambient'], ['ambientlane'], 7, .25, 'collapse'); before=state()
    report=check.Report();st=check.check_r8(p,report,tmp_path,groups=bg,landing=table)
    assert not report.errors() and st['async_skipped']==1 and st['groups_unequal']==0
    assert state()==before


def test_absent_header_options_use_authoritative_defaults(tmp_path):
    p,bg,table=vehicle(tmp_path)
    data=json.loads(table.read_text())
    for key in ['replica','bus','exempt','landed']:data.pop(key)
    table.write_text(json.dumps(data))
    r8.configure(['^d$'], ['ambient'], 7, .25, 'collapse');before=state()
    report=check.Report();st=check.check_r8(p,report,tmp_path,groups=bg,landing=table)
    assert not report.errors() and st['async_skipped']==0
    assert st['replica_mode']=='all' and st['bus_mode']=='part' and state()==before


def test_recorded_landed_window_is_not_ambient_or_default(tmp_path):
    p,bg,table=vehicle(tmp_path,landed=True,window=2)
    r8.configure([],[],9,.25,'collapse');before=state()
    report=check.Report();st=check.check_r8(p,report,tmp_path,groups=bg,landing=table)
    assert st['landed_over_margin']==1 and report.errors()
    assert state()==before


@pytest.mark.parametrize('change',[
    {'exempt':'^kreq$'},
    {'exempt':['^kreq$'],'landed':{'rx':['[']}},
    {'landed':{'window':'invalid'}},
    {'landed':{'stage_cycles':float('nan')}},
    {'replica':'typo'},
])
def test_malformed_options_fail_closed_without_partial_global_leak(tmp_path,change):
    p,bg,table=vehicle(tmp_path)
    data=json.loads(table.read_text());data.update(change);table.write_text(json.dumps(data))
    r8.configure(['ambient'], ['ambientlane'],7,.25,'collapse');before=state()
    report=check.Report();st=check.check_r8(p,report,tmp_path,groups=bg,landing=table)
    assert st['invalid_options'] and report.errors() and state()==before
