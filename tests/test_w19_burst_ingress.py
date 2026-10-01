import sys
from collections import Counter
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_burst_ingress as M


def finish(m,tag):
    p=m.pending[tag].copy()
    for beat in reversed(range(p['length'])):
        m.step({M.pc_of(p['addr']+beat):(tag,beat,bytes([beat])*32,m.epoch)})
    for _ in range(20):m.step()


def test_source_width_and_true_ceiling():
    r=M.build();w=r['source_wire_contract'];t=r['throughput']
    assert (w['LENW'],w['BEATW'],w['safe_max_read_sectors'])==(5,4,16)
    assert t['single_request_port_ceiling_bytes_s']==614400000000
    assert t['minimum_request_ports_for_nominal_1TB_s']==2
    assert t['proposed_two_port_ceiling_bytes_s']==1228800000000
    assert not t['one_TB_credited'] and t['sustained_completed_service_bytes_s'] is None
    assert not r['ready_to_build'] and not r['new_RTL']
    assert r['storage']['one_port_macros_per_controller']==41
    assert r['storage']['two_port_macros_per_controller']==42
    assert r['storage']['one_port_total_bytes_per_rank']==5494288
    assert r['storage']['two_port_total_bytes_per_rank']==5625388


@pytest.mark.parametrize('n',[1,2,3,4])
def test_short_and_full_burst_exact_out_of_order(n):
    m=M.Burst(groups=1,credits=Counter({0:4}))
    tag=m.prepare((1<<27)-16,[0]*n,1<<27)
    assert tag==0 and m.grant(tag,[64]*32)
    finish(m,tag)
    assert not m.pending
    assert len(m.ring_lines)==n
    assert m.credits[0]==4-n  # delivery cannot release ring credits
    for e in m.landing.delivered:
        line=e['tag']&3
        assert e['data']==b''.join(bytes([4*line+i])*32 for i in range(4))
    for i in range(n):m.consume_SM_line(tag+i)
    assert m.credits[0]==4


def test_reservation_atomic_and_request_stable_during_ready_stall():
    m=M.Burst(groups=1,credits=Counter({0:3}))
    assert m.prepare(0,[0]*4,16) is None
    assert not m.pending and not m.landing.lines and m.credits[0]==3
    tag=m.prepare(0,[0]*3,16);snapshot=m.request(tag)
    for _ in range(3):
        assert not m.grant(tag,[64]*32,controller_ready=False)
        assert m.request(tag)==snapshot
    assert len(m.landing.lines)==3 and m.credits[0]==0
    with pytest.raises(ValueError):m.step({0:(tag,0,bytes(32),0)})
    assert m.grant(tag,[64]*32)


def test_joint_two_request_PC_admission_not_independent_ready():
    rooms=[64]*32
    for pc in range(4):rooms[pc]=4
    assert M.joint_ready([(0,16)],rooms)
    assert not M.joint_ready([(0,16),(0,16)],rooms)
    assert M.joint_ready([(0,16),(16,16)],rooms)


def test_NPC_fold_boundary_can_double_target_one_PC():
    n=M.need(4092,16)
    assert sum(n)==16 and max(n)==8
    assert M.pc_of(4092)==M.pc_of(4100)
    rooms=[64]*32;rooms[M.pc_of(4092)]=4
    assert not M.joint_ready([(4092,16)],rooms)


@pytest.mark.parametrize('addr,length',[(0,0),(0,17),(0,31),(1,16),((1<<27)-4,16),(-4,4)])
def test_no_alias_oversized_or_wrapped_burst(addr,length):
    with pytest.raises(ValueError):M.need(addr,length)


def test_region_extent_is_not_free_padding():
    m=M.Burst(credits=Counter({0:4}))
    with pytest.raises(ValueError):m.prepare(0,[0]*4,15)
    assert not m.pending and m.credits[0]==4


def test_full_group_held_until_last_stalled_destination():
    m=M.Burst(groups=1,credits=Counter({s:2 for s in range(4)}))
    tag=m.prepare(0,list(range(4)),16);assert m.grant(tag,[64]*32)
    for beat in range(16):
        m.step({M.pc_of(beat):(tag,beat,bytes([beat])*32,0)},ready={0,1,2})
    for _ in range(8):m.step(ready={0,1,2})
    assert len(m.ring_lines)==3 and tag in m.pending
    assert m.prepare(16,[0],20) is None  # complete group locked
    m.step(ready={3})
    assert tag not in m.pending
    new=m.prepare(16,[0],20)
    assert new==4096
    with pytest.raises(ValueError):m.step({0:(tag,0,bytes(32),0)})


@pytest.mark.parametrize('fault',['duplicate','stale_epoch','bad_PC','bad_beat'])
def test_fault_does_not_publish(fault):
    m=M.Burst(credits=Counter({0:4}));tag=m.prepare(0,[0]*4,16);m.grant(tag,[64]*32)
    m.step({0:(tag,0,bytes(32),0)})
    pc,beat,epoch=0,1,0
    if fault=='duplicate':beat=0
    if fault=='stale_epoch':epoch=1
    if fault=='bad_PC':pc=31
    if fault=='bad_beat':beat=16
    with pytest.raises(ValueError):m.step({pc:(tag,beat,bytes(32),epoch)})
    assert not m.ring_lines and m.pending[tag]['seen']==1


def test_epoch_requires_burst_AND_SM_consumer_drain():
    m=M.Burst(groups=1,credits=Counter({0:1}));tag=m.prepare(0,[0],4);m.grant(tag,[64]*32)
    with pytest.raises(ValueError):m.reset_drained()
    finish(m,tag)
    with pytest.raises(ValueError):m.reset_drained()
    m.consume_SM_line(tag);m.reset_drained()
    assert m.epoch==1
    tag=m.prepare(0,[0],4);m.grant(tag,[64]*32)
    with pytest.raises(ValueError):m.step({0:(tag,0,bytes(32),0)})


def test_finite_generation_never_silently_wraps():
    m=M.Burst(groups=1,credits=Counter({0:1}))
    for gen in range(8):
        tag=m.prepare(0,[0],4);assert tag==gen<<12
        m.grant(tag,[64]*32);finish(m,tag);m.consume_SM_line(tag)
    assert m.prepare(0,[0],4) is None
    m.reset_drained();assert m.prepare(0,[0],4)==0


def test_rank_authoritative_credit_ledger_shared_between_controllers():
    credits=Counter({0:4});a=M.Burst(credits=credits);b=M.Burst(credits=credits)
    assert a.prepare(0,[0]*3,16) is not None
    assert b.prepare(0,[0]*2,16) is None
    assert credits[0]==1


def test_32PC_bursts_expose_synchronized_landing_collision():
    r=M.trace32PC()
    assert r['accepted_sectors']==r['written_sectors']==128
    assert r['delivered_lines']==32
    assert r['sector_bank_collision_cycles']>0
    assert r['last_delivery_cycle']>7
    assert r['serial_request_grant_cycles']==8
