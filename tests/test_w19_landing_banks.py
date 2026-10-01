import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_landing_banks as B


def test_storage_macro_rounding_and_Turing_ack():
    r=B.build();g=r['layout']
    assert r['Turing_input_ack']['acknowledged']
    assert g['SRAM']['landing_macros']==32 and g['SRAM']['context_macros']==8
    assert g['SRAM']['used_rows_per_macro']==512
    assert g['bytes_per_rank']==5346800
    assert g['bytes_per_rank']>2452028
    assert g['control_storage_bits']['scoreboard_bits']==4096*9
    assert not r['ready_to_build'] and not r['composed_service_provider']
    assert r['physical']['area_mm2'] is None
    assert r['pipeline']['upstream_one_4sector_request_per_cycle_ceiling_bytes_second']==153600000000


def test_balanced_same_line_merges_exact_in_four_cycles():
    r=B.campaigns()['balanced32PC']
    assert r['accepted_sectors']==r['written_sectors']==32
    assert r['same_line_merge_events']==8
    assert r['first_delivery_cycle']==r['last_delivery_cycle']==4


def test_actual_bitmap_no_lost_update_and_exact_bytes():
    m=B.Landing();m.allocate(0,5)
    accepted,_=m.step({pc:(0,pc,bytes([pc])*32) for pc in range(4)})
    assert len(accepted)==4
    m.step();assert m.lines[0]['mask']==15
    assert len(m.cq[0])==1
    m.drain();assert m.delivered[0]['data']==b''.join(bytes([i])*32 for i in range(4))


def test_same_sector_bank_contention_is_charged():
    r=B.campaigns()['same_sector_bank32PC']
    assert r['sector_collision_cycles']==31
    assert r['last_delivery_cycle']==38
    assert r['written_sectors']==128 and r['delivered_lines']==32


def test_same_destination_cannot_receive_eight_lines_at_once():
    r=B.campaigns()['same_SM8banks']
    assert (r['first_delivery_cycle'],r['last_delivery_cycle'])==(4,11)


def test_rank_arbitration_no_duplicate_SM_across_four_controllers():
    candidates=[(0,c,b,b) for c in range(4) for b in range(8)]
    grants=B.delivery_grants(candidates,set(range(32)))
    assert grants==[(0,b) for b in range(8)]
    # Distinct SMs may accept all32 banks; no unused-SM area credit.
    candidates=[(0,c,b,8*c+b) for c in range(4) for b in range(8)]
    assert len(B.delivery_grants(candidates,set(range(32))))==32
    assert B.delivery_grants(candidates,set())==[]


def test_stalled_destination_keeps_credit_and_finite_skid():
    m=B.Landing()
    for slot in (0,8,16,24):m.allocate(slot,0)
    for tag in (0,8,16,24):
        m.step({b:(tag,b,bytes([b])*32) for b in range(4)},ready=set())
        m.step(ready=set())
    for _ in range(12):m.step(ready=set())
    assert len(m.skid[0])==2
    assert len(m.cq[0])==2
    assert len(m.lines)==4 and not m.delivered
    m.drain();assert len(m.delivered)==4


def test_registered_ingress_credit_backpressures_without_drop():
    m=B.Landing(depth=1)
    for pc in range(32):m.allocate(8*pc,pc)
    responses={pc:(8*pc,0,bytes(32)) for pc in range(32)}
    accepted,_=m.step(responses)
    assert len(accepted)==32
    # Every queue was full at registered ready; even the granted PC retries.
    accepted,_=m.step({pc:(8*pc,1,bytes(32)) for pc in range(32)})
    assert not accepted and m.accepted==32 and m.writes==1
    assert sum(map(len,m.pc))==31


@pytest.mark.parametrize('fault',['duplicate','stale','unissued'])
def test_fault_never_becomes_complete(fault):
    m=B.Landing();m.allocate(0,0)
    m.step({0:(0,0,bytes(32))});m.step()
    tag,beat=(0,0) if fault=='duplicate' else ((4096,1) if fault=='stale' else (8,1))
    m.step({0:(tag,beat,bytes(32))})
    with pytest.raises(ValueError):m.step()
    assert not m.delivered and m.lines[0]['mask']==1


def test_HC_raw_scatter_final_and_fences_remain_serial_unknown():
    h=B.hc_reconciliation()
    assert h['conditional_transpose_increment_HC_cycles']==35248
    assert h['external_raw_buffers_bytes_per_rank']==98304
    assert h['source_conflicts']==dict(naive_coefficient=8,packed_activation=4,term_major=1)
    for kind,size in [('coefficient',1966080),('activation',1024000)]:
        assert h['raw_write_endpoint_bytes_operator'][kind]==size
        assert h['scatter_write_bytes_operator'][kind]==size
        assert h['retained_r3_final_refill_write_bytes_operator'][kind]==size
    assert h['global_barrier_cycles'] is None and h['CDC_completed_cycles'] is None
    assert h['full_HC_service_cycles'] is None and h['no_overlap_credit']
    assert not h['RF32_register_reserve_qualified']
    assert h['numerical_proof_scope']['boundaries']==91
    assert not h['numerical_proof_scope']['target_connected_GPU_hardware_proved']


def test_four_controllers_share_rank_destination_credit():
    models=[B.Landing() for _ in range(4)]
    for c,m in enumerate(models):
        for b in range(8):m.allocate(b,b)
        m.step({4*b+s:(b,s,bytes([c*32+4*b+s])*32) for b in range(8) for s in range(4)})
    for cycle in range(1,9):
        candidates=[item for c,m in enumerate(models) for item in m.candidates(c)]
        granted=B.delivery_grants(candidates,set(range(32)))
        events=[]
        for c,m in enumerate(models):
            _,out=m.step(grants={b for cc,b in granted if cc==c})
            events+=out
        assert len({e['owner'] for e in events})==len(events)
    assert sum(len(m.delivered) for m in models)==32
    assert max(e['cycle'] for m in models for e in m.delivered)==7
    assert sum(m.writes for m in models)==128
    for c,m in enumerate(models):
        for e in m.delivered:
            assert e['data']==b''.join(bytes([c*32+4*(e['tag']&7)+s])*32 for s in range(4))


def test_register_fifo_burst_cannot_hide_unbounded_sector_collision():
    m=B.Landing()
    for pc in range(32):
        for wave in range(9):m.allocate(8*(pc*9+wave),pc)
    for wave in range(8):
        accepted,_=m.step({pc:(8*(pc*9+wave),0,bytes(32)) for pc in range(32)})
        assert len(accepted)==32
    accepted,_=m.step({pc:(8*(pc*9+8),0,bytes(32)) for pc in range(32)})
    assert len(accepted)<32
    for _ in range(300):m.step()
    assert m.accepted==m.writes
    assert not m.delivered  # only beat0 supplied; incomplete lines never publish


def test_generation_and_reset_include_all_banked_pipeline_state():
    m=B.Landing();m.allocate(0,0)
    m.step({b:(0,b,bytes(32)) for b in range(4)})
    with pytest.raises(ValueError):m.reset_drained()
    m.drain()
    with pytest.raises(ValueError):m.allocate(0,0)
    m.allocate(4096,0)
    with pytest.raises(ValueError):m.reset_drained()


def test_all4096_slots_map_bijectively_into_eight_banks():
    assert len({(slot&7,slot>>3) for slot in range(4096)})==4096
    assert max(slot>>3 for slot in range(4096))==511
    assert sum(1 for slot in range(4096) if slot&7==0)==512
