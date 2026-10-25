"""A standalone A-kit cannot silently become release SIGNED without actual parent evidence."""
import copy
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import io_hold_parent as parent
import io_hold_qualification as Q
import signoff
from test_io_hold import _plan, _sta
from test_signoff import record


@pytest.mark.parametrize('field,value', [('period_ps',833.333),('unc_hold_ps',0),('unc_setup_ps',30),('spine','ideal')])
def test_parent_rejects_wrong_real_timing_contract(field,value):
    sta=_sta(3);sta[field]=value
    assert parent.check(_plan('sender_min'),sta)['verdict']=='INCOMPLETE'


@pytest.mark.parametrize('mutation', ['budget','bare','zero_paths','zero_pairs','nan_pair','missing_exit'])
def test_parent_never_qualifies_budget_or_untimed(mutation):
    sta=_sta(3)
    if mutation=='budget':sta['boundary_hold_contract']={'cells':['OT_BHOLD_40p0']}
    if mutation=='bare':
        for v in sta['view_evidence'].values():v['kind']='budget'
    if mutation=='zero_paths':
        for seam in sta['corners']['FF']['seams'].values():seam['min']['paths']=0
    if mutation=='zero_pairs':
        for ps in sta['corners']['FF']['pairskew'].values():ps['n']=0
    if mutation=='nan_pair':
        for ps in sta['corners']['FF']['pairskew'].values():ps['min_cppr']=float('nan')
    if mutation=='missing_exit':sta['corners']['FF'].pop('exit')
    assert parent.check(_plan('sender_min'),sta)['verdict']=='INCOMPLETE'


def a_record(tmp_path):
    r=record()
    v=tmp_path/'6_final.v';v.write_text('module blk; wire a; endmodule\n')
    sp=tmp_path/'6_final.spef';sp.write_text('*SPEF fixture\n')
    r['inputs']={'final_v':str(v),'spef':str(sp)}
    r['io_hold']=dict(mode='sender_min',die='tiny',receiver_type='fb',input_ports=['x_i','z_i'],plan_sha256='planfixture')
    return r


def test_signoff_defers_only_A_and_keeps_actual_views_available(tmp_path):
    r=a_record(tmp_path)
    signoff.evaluate(r)
    assert r['local_verdict']=='SIGNED' and r['verdict']=='LOCAL_PASS_NEEDS_PARENT'
    assert r['parent_qualification']['provisional_views_allowed']
    legacy=record();signoff.evaluate(legacy)
    assert legacy['verdict']=='SIGNED' and 'parent_qualification' not in legacy


def receipt(r):
    sha=Q.digest(r['inputs']['final_v'])
    return dict(schema='opentallas.io_hold_parent.v2',verdict='PASS',plan='tiny',plan_sha256='planfixture',qualification={'complete':True},
                ports=[dict(dst_type='fb',bus=p,status='PASS',receiver_netlist_sha256=sha,receiver_spef_sha256=Q.digest(r['inputs']['spef'])) for p in ['x_i','z_i']])


@pytest.mark.parametrize('mutation',[None,'stale','stale_rc','stale_plan','missing_port','wrong_die','old_schema'])
def test_matching_parent_receipt_is_required(tmp_path,mutation):
    r=a_record(tmp_path);r['io_hold_parent_receipt']=receipt(r);proof=r['io_hold_parent_receipt']
    if mutation=='stale':proof['ports'][0]['receiver_netlist_sha256']='old'
    if mutation=='stale_rc':proof['ports'][0]['receiver_spef_sha256']='old'
    if mutation=='stale_plan':proof['plan_sha256']='old'
    if mutation=='missing_port':proof['ports'].pop()
    if mutation=='wrong_die':proof['plan']='other'
    if mutation=='old_schema':proof['schema']='opentallas.io_hold_parent.v1'
    signoff.evaluate(r)
    assert (r['verdict']=='SIGNED') == (mutation is None)


def test_budget_netlist_detection_requires_no_caller_flag(tmp_path):
    (tmp_path/'6_final.v').write_text('module b;\n DFFHQNx1_ASAP7_75t_R f0 (.D(a),.QN(q));\n endmodule\n')
    (tmp_path/'6_final.spef').write_text('*SPEF "IEEE 1481-1998"\n')
    assert Q.view_snapshot(tmp_path)['kind']=='budget'
    # Marker handles all future stand-ins, including a minimal marker-only fixture.
    (tmp_path/'6_final.v').write_text('// OPENTALLAS_BUDGET_STANDIN\nmodule b; endmodule\n')
    assert Q.view_snapshot(tmp_path)['kind']=='budget'
