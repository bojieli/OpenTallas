"""Source-bound finite queue/visibility witnesses; not engine RTL tests."""
import hashlib
from dataclasses import replace
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from qwen_hbm_controller_events_r1 import (Beat, Controller, CompletionSink, REV, SOURCE,
                                          SOURCE_SHA, compose, pinned, source_timing, queue_port_schedule)

@pytest.fixture
def ctl():
    return Controller(source_timing())

def same_pc(n, pc=0):
    result=[]
    for addr in range(100000):
        if Controller.pc(addr) == pc:
            result.append(addr)
            if len(result) == n:
                return result
    raise AssertionError('address fixture')

def request(addr, i, write=False):
    return Beat(addr, i, (1 << 48)+i, 123+i, write=write, data=1000+i)

def test_source_bound_prior_failures_retained():
    assert hashlib.sha256(pinned(ROOT,REV,SOURCE)).hexdigest() == SOURCE_SHA
    raw=pinned(ROOT,REV,SOURCE)
    for fragment in (b'for (i = sel; i >= 1; i = i - 1)', b'r_tag[p][k] = q_tag[p][slot]',
                     b'mem[q_addr[p][slot] % MEM_WORDS]', b'last_wr[p] + CWL_PS + BURST_PS'):
        assert fragment in raw
    assert source_timing()['CWL_PS']+source_timing()['BURST_PS'] == 7274

def test_every_shift_and_return_keeps_acceptance_epochs(ctl):
    addresses=same_pc(16)
    originals=[request(a,i) for i,a in enumerate(addresses)]
    for b in originals:
        assert ctl.accept(b,0)
    # Exercise every displacement, not just moving the selected head.
    for selected in range(15,0,-1):
        before=list(ctl.q[0])
        estimates=[100]*16;estimates[selected]=0
        assert ctl.reorder(0,estimates) == selected
        assert ctl.q[0] == [before[selected]]+before[:selected]+before[selected+1:]
    snapshot=list(ctl.q[0])
    for now in range(16):
        assert ctl.column(0,now)
    for index,expected in enumerate(snapshot):
        time=100000+index*3
        offered=ctl.take(time,False)
        assert offered.request == expected
        assert ctl.take(time+1,False) == offered
        assert ctl.take(time+2,True) == offered
    assert ctl.drained()

def test_frfcfs_ties_hazard_and_maxskip(ctl):
    a,b=same_pc(2)
    for r in (request(a,1,True),request(a,2),request(b,3)):
        ctl.accept(r,0)
    assert ctl.reorder(0,[30,0,10]) == 2  # same-sector read cannot pass write
    assert ctl.reorder(0,[0,0,0]) == 0  # oldest tie
    ctl.skip[0]=16
    assert ctl.reorder(0,[30,20,0]) == 0
    assert ctl.skip[0] == 0

def test_reserve_before_WR_pop_and_retained_visible_ack(ctl):
    addresses=same_pc(5)
    for i,a in enumerate(addresses):
        ctl.accept(request(a,i,True),0)
    for now in range(4):
        assert ctl.column(0,now)
    before=list(ctl.q[0]);events=list(ctl.events)
    assert not ctl.column(0,4)
    assert ctl.q[0] == before and ctl.events == events
    assert not ctl.mem
    assert ctl.write_offer(7273) is None
    ctl.advance(7274)
    assert ctl.mem[addresses[0]] == 1000
    # Visibility alone is insufficient: all four slots retained until ready.
    assert not ctl.column(0,8000)
    held=ctl.write_take(17274,False)
    assert held is not None and held.request.producer_epoch > 2**32
    assert ctl.write_take(20000,False) == held
    assert not ctl.column(0,20000)
    assert ctl.write_take(20000,True) == held
    assert ctl.column(0,20000)
    first=[x[0] for x in ctl.events if x[1] == request(addresses[0],0,True)]
    assert first[:3] == ['accept','WR_reserved','column']

def test_RAW_waits_for_delayed_backing_fullAW34(ctl):
    a=0;b=1 << 32
    assert ctl.pc(a) == ctl.pc(b)
    ctl.accept(request(a,1,True),0)
    ctl.accept(request(b,2,True),0)
    ctl.accept(request(a,3),0)
    assert ctl.column(0,0)
    assert ctl.column(0,1)
    before=list(ctl.q[0])
    assert not ctl.column(0,7273)
    assert ctl.q[0] == before
    assert ctl.column(0,7274)
    assert ctl.take(50000,True).data == 1001
    assert ctl.mem[a] == 1001 and ctl.mem[b] == 1002

def test_return_queue_capacity_and_immutable_locked_PC_arb(ctl):
    for i in range(33):
        ctl.accept(request(0,i),0)
    for now in range(32):
        assert ctl.column(0,now)
    assert not ctl.column(0,32)
    other=same_pc(1,31)[0]
    ctl.accept(request(other,50),32)
    assert ctl.column(31,32)
    held=ctl.take(100000,False)
    assert held.request.tag == 0
    ctl.rr=31  # later arbitration preference must not overwrite held offer
    assert ctl.take(100001,False) == held
    assert ctl.take(100001,True) == held
    assert ctl.column(0,100001)
    assert not ctl.drained()

def test_WR_visible_capture_CDC_store_retire_reverse_and_drain(ctl):
    b=request(0,1,True);ctl.accept(b,0);ctl.column(0,0)
    sink=CompletionSink(ctl,1)
    assert sink.capture(17273) is None
    result=sink.capture(17274)
    assert result.request == b and not ctl.drained()
    with pytest.raises(ValueError):sink.transition(b,'retired')
    with pytest.raises(ValueError):sink.transition(replace(b,producer_epoch=b.producer_epoch+1),'forward_crossed')
    for event in ('forward_crossed','stored','retired'):
        sink.transition(b,event)
        assert not ctl.drained()
    sink.transition(b,'reverse_crossed')
    assert ctl.drained()
    with pytest.raises(ValueError):sink.transition(b,'reverse_crossed')
    for key in ctl.external:
        ctl.external[key]=1;assert not ctl.drained();ctl.external[key]=0

def test_finite_sink_backpressure_keeps_controller_slot(ctl):
    sink=CompletionSink(ctl,1)
    for i,a in enumerate(same_pc(2)):
        ctl.accept(request(a,i,True),0);ctl.column(0,i)
    result=sink.capture(20000)
    held=ctl.write_offer(20000)
    assert sink.capture(20001) is None
    assert ctl.write_offer(20002) == held and len(ctl.pending) == 1
    for event in ('forward_crossed','stored','retired','reverse_crossed'):
        sink.transition(result.request,event)
    assert sink.capture(20003) == held

def test_width_and_time_rejections(ctl):
    for r in (request(1<<34,1), replace(request(0,1), producer_epoch=1<<64),
              replace(request(0,1), transport_epoch=1<<32),replace(request(0,1),beat=32)):
        with pytest.raises(ValueError):ctl.accept(r,0)
    ctl.advance(2)
    with pytest.raises(ValueError):ctl.advance(1)

def test_model_closes_narrow_ports_not_hardware_or_rate():
    x=compose()
    assert x['queue_ports']['request_width'] == 472
    assert x['queue_ports']['return_width'] == 471
    assert x['memory_macro_candidate']['total'] == 512
    assert x['additional_state']['queue_epoch_bits'] == 2359296
    assert len(x['program_binding']['writer_bindings']) == 144
    assert x['program_binding']['actual_trace_instructions'] == 1737
    assert x['queue_ports']['selection_total_edges_max'] == 35
    assert all(d['partial_RMW_serial_edges_per_sector'] == 27 for d in x['program_binding']['writer_bindings'])
    assert all(d['retained_depth4_WR_column_to_last_ACK_work_floor_ps'] > 0 for d in x['program_binding']['writer_bindings'])
    assert not x['hardware_build_ready'] and x['hardware_rate_credit'] == 0


def test_port_schedule_matches_every_stable_source_shift_with_wrap():
    for window in range(1,17):
        for selected in range(window):
            for rp in (0,49,63):
                words={((rp+i)%64): request(i,i) for i in range(window)}
                before=[words[(rp+i)%64] for i in range(window)]
                cached=before[selected]
                prior_read=None
                schedule=queue_port_schedule(selected,window)
                assert len(schedule) == window+2+(selected+2 if selected else 0)
                for e in schedule:
                    # one read and one write maximum, old-data read semantics
                    old=words[(rp+e['read'])%64] if e['read'] is not None else None
                    if e['write'] is not None:
                        value=cached if e['write']==0 else prior_read
                        assert value is not None
                        words[(rp+e['write'])%64]=value
                    prior_read=old
                after=[words[(rp+i)%64] for i in range(window)]
                assert after == [before[selected]]+before[:selected]+before[selected+1:]
