"""Explicit bridge6 profile changes only SO source programme and real SOT reservations."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_lower_svc_h8 import synth, run
import lower_svc as L

def candidate():
    j=synth(16)
    j.so_input_profile='bridge6'
    j.frames=j._frames()
    return j

def test_bridge_order_and_gap_are_actual_ingress_order():
    old=run(synth(16));new=run(candidate())
    assert new['at']['SMJ_OP0']-new['at']['SMJ_SO']==6
    assert old['at']['SMJ_OP0']-old['at']['SMJ_SO']==45
    assert [n for n,_ in candidate().frames if n.startswith('SMJ_OP')] == ['SMJ_OP'+str(g)for g in range(16)]
    assert new['at']['SMJ_SO']==old['at']['SMJ_SO']
    for key in ('go','pvs','po','pvo','pv_first','pv_last'):
        assert new[key]==old[key]
    for key in ('CFG','OWN_ROW','WIN_LOAD','SOT','ATTN_Q0','ATTN_Q1','SMJ','GO'):
        assert new['at'][key]==old['at'][key]
    assert min(new['sot']['done'].values())>=max(c for c,w in new['words'])+2
    assert new['sot']['lifetime_fence']['added_state_bits']==0

def test_six_profile_cost_is_local_gap_only():
    j45=candidate()
    s45=j45.schedule(1805,3001,3763,6,12)
    # Same sequential source with baseline45 lead, no global profile/default change.
    delta=39
    at=dict(s45['at'])
    for g in range(16):at['SMJ_OP'+str(g)]+=delta
    last=max(c for c,w in s45['words'])+delta
    r45=L.sot_booking_for(j45,dict(at=at,job_last_q_edge=last))
    r6=run(candidate())['sot']
    assert all(r45['done'][half]-r6['done'][half]==delta for half in ('E','W'))
