import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w19_transport_contract as T


def read(p, stack=0, sector=16):
    assert p.enqueue(stack, 2, sector)
    tag=p.issue(stack,2)
    assert tag is not None
    return tag


def finish(p, stack, tag):
    for beat in (3,0,2,1):
        p.response(stack,tag,beat,bytes([beat])*32,p.epoch)


def test_sizing_ack_and_build_guard():
    r=T.build(); g=r['geometry']
    assert r['W16_input_ack']['acknowledged']
    assert not r['W16_input_ack']['dedicated_HCP']
    assert g['descriptor_bits']==160
    assert g['bandwidth_delay_required_128B_slots']==3907
    assert g['read_line_slots']==4096
    assert g['total_storage_bytes_per_rank'] > 2_400_000
    assert r['source_ports']['proposed_commit_bits_per_cycle']==576
    assert not r['ready_to_build'] and not r['unified_model_composed']
    assert not r['actual_RTL_gate'] and not r['hardware_adopted']
    assert T.sizing(slots=512)['selected_slots_cover_bandwidth_delay'] is False


def test_queue_and_return_credit_backpressure():
    p=T.Protocol(depth=1,reads=1)
    tag=read(p)
    assert p.enqueue(0,2,24)
    assert not p.enqueue(0,2,28)
    assert p.issue(0,2) is None
    finish(p,0,tag)
    assert p.deliver(0,tag,False) is None
    assert p.issue(0,2) is None
    assert p.deliver(0,tag)==b''.join(bytes([i])*32 for i in range(4))
    assert p.issue(0,2) is not None


@pytest.mark.parametrize('fault', ['duplicate','unissued','badbeat','stale','short'])
def test_bad_return_never_completes(fault):
    p=T.Protocol(reads=1); tag=read(p)
    p.response(0,tag,0,bytes(32),0)
    args=dict(stack=0,tag=tag,beat=1,data=bytes(32),epoch=0)
    if fault=='duplicate': args['beat']=0
    if fault=='unissued': args['tag']=99
    if fault=='badbeat': args['beat']=4
    if fault=='stale': args['epoch']=1
    if fault=='short': args['data']=bytes(31)
    with pytest.raises(ValueError): p.response(**args)
    assert not p.fence_ready(p.fence())


def test_tag_generation_prevents_retired_duplicate_alias():
    p=T.Protocol(reads=1); old=read(p); finish(p,0,old); p.deliver(0,old)
    new=read(p)
    assert new!=old
    with pytest.raises(ValueError): p.response(0,old,0,bytes(32),0)
    for _ in range(7):
        finish(p,0,new); p.deliver(0,new)
        if _<6: new=read(p)
    assert not p.enqueue(0,2,16)  # reject before creating an undrainable queue
    p.reset_epoch()
    assert p.enqueue(0,2,16)


def test_cross_controller_fence_waits_queued_committed_and_delivered():
    p=T.Protocol(reads=1,writes=1)
    tags=[read(p,st) for st in range(4)]
    assert p.enqueue(3,3,32,bytes([9])*32)
    fence=p.fence()
    for st,tag in enumerate(tags):
        finish(p,st,tag); p.deliver(st,tag)
    assert not p.fence_ready(fence)  # queued write included
    tag=p.issue(3,3)
    with pytest.raises(ValueError): p.commit(3,tag,0,visible=False)
    assert not p.fence_ready(fence)
    p.commit(3,tag,0,visible=True)
    assert p.fence_ready(fence)
    with pytest.raises(ValueError): p.commit(3,tag,0,visible=True)
    assert p.memory[3,32]==bytes([9])*32


def test_partial_scale_sector_merge_and_read_hazard():
    p=T.Protocol(writes=2)
    p.memory[0,64]=bytes(range(32))
    assert p.enqueue(0,3,64,bytes([99])*32,mask=0xf)
    assert p.enqueue(0,2,64)
    tag=p.issue(0,3)
    assert p.issue(0,2) is None
    assert p.enqueue(0,3,128,bytes(32),mask=1)
    assert p.issue(0,3) is None  # single RMW lock per controller
    p.commit(0,tag,0,visible=True)
    assert p.memory[0,64]==bytes([99])*4+bytes(range(4,32))
    assert p.issue(0,2) is not None
    assert p.issue(0,3) is not None


def test_reset_requires_drain_and_stale_fence_rejected():
    p=T.Protocol(reads=1); tag=read(p); fence=p.fence()
    with pytest.raises(ValueError): p.reset_epoch()
    finish(p,0,tag); p.deliver(0,tag)
    p.reset_epoch()
    with pytest.raises(ValueError): p.fence_ready(fence)
    tag=read(p)
    with pytest.raises(ValueError): p.response(0,tag,0,bytes(32),0)


@pytest.mark.parametrize('sector',[-1,1<<27,(1<<27)-3])
def test_no_modulo_or_aperture_crossing(sector):
    p=T.Protocol()
    with pytest.raises(ValueError): p.enqueue(0,2,sector)


def test_sequence_wrap_does_not_publish():
    p=T.Protocol(); p.sequence[0]=(1<<32)-1
    with pytest.raises(ValueError): p.enqueue(0,2,16)
    p.reset_epoch()
    assert p.enqueue(0,2,16)


def test_later_write_cannot_pass_earlier_read_or_write():
    p=T.Protocol(); first=read(p)
    assert p.enqueue(0,3,16,bytes(32))
    assert p.issue(0,3) is None
    finish(p,0,first); p.deliver(0,first)
    tag=p.issue(0,3)
    assert p.enqueue(0,3,16,bytes([1])*32)
    assert p.issue(0,3) is None
    p.commit(0,tag,0,True)
    assert p.issue(0,3) is not None


def test_paired_code_scale_publication_requires_both_controllers():
    p=T.Protocol(writes=1)
    for stack,sector in [(0,64),(2,96)]:
        assert p.enqueue(stack,3,sector,bytes([stack+1])*32)
    fence=p.fence(); code=p.issue(0,3); scale=p.issue(2,3)
    p.commit(0,code,0,True)
    assert not p.fence_ready(fence)
    with pytest.raises(ValueError): p.commit(2,scale,1,True)
    assert not p.fence_ready(fence)
    p.commit(2,scale,0,True)
    assert p.fence_ready(fence)


def test_finite_write_credits_survive_commit_stall():
    p=T.Protocol(depth=2,writes=1)
    assert p.enqueue(1,3,64,bytes(32)); first=p.issue(1,3)
    assert p.enqueue(1,3,128,bytes(32))
    assert p.issue(1,3) is None
    p.commit(1,first,0,True)
    second=p.issue(1,3)
    assert second is not None and second != first
    with pytest.raises(ValueError): p.commit(1,first,0,True)
