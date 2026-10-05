import sys
from pathlib import Path
from fractions import Fraction as F
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_resource_schedule_r7 import Model,requests,physical_costs,Beat

def test_idle_refresh_is_current_time_without_request():
    m=Model([]);r=m.run(4300000)
    ref=next(e for e in r['commands'] if e['kind']=='REF' and e['pc']==0)
    assert ref['ps']==3900000
    assert not [e for e in r['journal'] if e['event']=='request_accept']
    assert r['timing']['status']=='PASS_COMMAND_TIMING_INEQUALITIES'

def test_strict_shared_four_maps_never_release_on_read_take():
    m=Model(requests(0));r=m.run(3000000)
    assert r['live_front_maps']==4 and r['remaining_jobs']==8
    assert r['stalls']['front_maps_held_without_consumer_retire']>0
    assert r['stored_WRs']==0 and r['peaks']['front_maps']==4

def test_WR_capacity_is_held_after_ACK_and_scoreboard_store():
    jobs=[dict(tag=i,addr=i*4096,length=1,write=True,data=i+1,release_ps=0) for i in range(5)]
    m=Model(jobs,front_capacity=64);r=m.run(300000)
    assert r['retained_WR_slots']==4 and r['stored_WRs']==4
    assert r['queued_beats']==1 and r['stalls']['WR_reservation_full_or_WAW']>0
    assert len(m.inflight)==4

def test_fullAW_RAW_wait_and_two_distinct_payloads():
    m=Model(requests(2));r=m.run(300000)
    assert m.values[2,0]!=m.values[3,0]
    assert m.values[2,0]==sum(0x71000000<<(32*i) for i in range(8))
    assert m.values[3,0]==sum(0x71000001<<(32*i) for i in range(8))
    for e in r['journal']:
        if e['event']=='held_visible_ACK_capture':
            assert e['forward_CDC_ps']>e['registered_ps']
            assert e['scoreboard_visible_ps']>e['forward_CDC_ps']

def test_exact_loaded_selected15_freezes35edges():
    m=Model([])
    m.q[0]=[Beat(0,tag,999,88,accepted_ps=tag*1000) for tag in range(17,32)]+[Beat(1,32,999,88,accepted_ps=33000),Beat(2,33,999,88,accepted_ps=34000)]
    bank=m.bank.b[0][0];bank.open=True;bank.row=0;bank.act=11000
    m.bank.last_col[0]=70000;m.bank.last_col_bg[0][0]=70000
    m.step(72000)
    scan=next(e for e in m.log if e['event']=='PC_frozen_scan')
    assert scan['tag']==32 and scan['selected']==15
    assert scan['edges']==35 and scan['end_ps']==107000
    assert m.phase[0] is not None

def test_OBS_macro_rectangle_and_required_local_arbiter():
    p=physical_costs()
    assert [x[0] for x in p['OBS']]==['M1','M2','M3','M4']
    assert p['macros_per_stack']==64 and p['queue_rectangle_fits']
    assert not p['raw_PC_read_bus_fits_vertical_channel']
    assert p['shared_bus_fits_vertical_estimate'] and not p['all_four_stack_trunk_fits']
    assert p['priced_subset_total_mm2_per_stack']<p['service_slot_area_mm2']


def test_command_service_journal_and_MAXSKIP_are_finite():
    m=Model(requests(2));r=m.run(300000)
    service=[e for e in r['journal'] if e['event']=='command_service_edge']
    assert len(service)==len(r['commands'])
    assert len({(e['pc'],e['ps']) for e in service})==len(service)
    m.q[0]=[Beat(0,0,1,1),Beat(1,1,1,1)];m.skip[0]=16
    assert m.choose(0,100000)==0
