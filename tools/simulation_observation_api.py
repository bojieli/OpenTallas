"""Immutable simulation packets. Diagnostic association only; no deadline admission.

Native acceptance facts are source-bound; legacy wire tags lack epoch provenance.
Matched replies are local consistency checks, never a stale-response certificate.
"""
from dataclasses import dataclass, replace
from prepare_simulation_observation_wrapper import BITS, layout


def uint(value, bits):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError('unsigned packet envelope')
    return value


def encode(values):
    fields = {f['name']: f for f in layout()}
    if set(values) - fields.keys():
        raise ValueError('unknown packet field')
    packet = 0
    for name, f in fields.items():
        packet |= uint(values.get(name, 0), f['width']) << f['offset']
    return packet


def decode(packet):
    uint(packet, BITS)
    return {f['name']: (packet >> f['offset']) & ((1 << f['width']) - 1)
            for f in layout()}


@dataclass(frozen=True)
class Operation:
    epoch: int
    rank: int
    family: str
    serial: int
    generation: int
    selection: int = 0
    context: tuple = ()


@dataclass(frozen=True)
class Event:
    kind: str
    operation: Operation | None
    metadata: tuple = ()
    # Never true for these legacy responses without independent fence evidence.
    causal_certificate: bool = False


@dataclass(frozen=True)
class State:
    epoch: int = -1
    rank: int = -1
    cycle: int = -1
    serial: int = 0
    request_serial: int = 0
    source: Operation | None = None
    merge: Operation | None = None
    block: Operation | None = None
    refill: Operation | None = None
    selection: Operation | None = None
    fetch: Operation | None = None
    replay: Operation | None = None
    requests: tuple = ()
    stages: tuple = ()


def observe(state, packet):
    """Return new ledger/events or reject without changing the supplied ledger.

    Host drains exactly once after the rising-edge eval, supplying reset epoch.
    Staged/rows_ready/busy/PC do not retire or renew an operation.
    """
    f = decode(packet)
    epoch, rank, cycle = f['epoch'], f['rank'], f['cycle']
    if epoch < state.epoch or (epoch == state.epoch and rank != state.rank):
        raise ValueError('epoch/rank mismatch')
    if epoch == state.epoch and cycle <= state.cycle:
        raise ValueError('repeated or reversed sampled edge')
    if epoch == state.epoch and cycle != state.cycle+1:
        raise ValueError('sample gap: event loss unavailable')
    if epoch > state.epoch:
        # Reset abandons local ledger; does not certify physical transport drain.
        state = State(epoch=epoch, rank=rank)
    s = replace(state, cycle=cycle)
    events = []
    pending = dict(s.requests)
    stages = list(s.stages)
    def accept(slot, family, generation, selection=0, context=()):
        nonlocal s
        if getattr(s, slot) is not None:
            raise ValueError('overlapping '+family)
        uint(s.serial+1,64)
        ident = Operation(epoch, rank, family, s.serial+1, generation, selection, context)
        s = replace(s, serial=s.serial+1, **{slot: ident})
        events.append(Event('accept', ident))
        return ident
    def retire(slot, label):
        nonlocal s
        op = getattr(s, slot)
        if op is None or any(v[0] == op for v in pending.values()):
            raise ValueError('early/unowned '+label)
        if slot == 'source' and (s.merge or s.refill or stages):
            raise ValueError('source retires before merge/stage drain')
        events.append(Event(label, op))
        s = replace(s, **{slot: None})
    if f['source_accept']:
        accept('source','window_source',f['source_gen'])
    if f['window_blk_accept']:
        accept('block','window_block',0,context=(f['window_blk_row'],f['window_blk_user']))
    if f['window_prefetch_accept']:
        accept('refill','window_refill',s.source.generation if s.source else 0,context=(f['window_prefetch_row'],f['window_prefetch_user']))
    if f['merge_accept']:
        if not s.source or f['active_gen'] != s.source.generation:
            raise ValueError('wrong WINDOW generation')
        accept('merge','window_stream',f['active_gen'])
    if f['window_req_take'] != (f['window_req_offer'] & f['window_req_ready']):
        raise ValueError('WINDOW acceptance qualifier')
    if f['window_req_take']:
        if not f['window_req_offer'] or f['window_req_tag'] >> 14:
            raise ValueError('unoffered/reserved WINDOW request')
        write = f['window_req_we']
        op = s.block if write else s.refill
        expected_state = (1,3) if write else (5,)
        if op is None or f['window_state'] not in expected_state:
            raise ValueError('unowned WINDOW request')
        if (f['window_row'],f['window_active_user']) != op.context:
            raise ValueError('request differs from accepted row/user')
        key = ('window',0,f['window_req_tag'])
        if key in pending: raise ValueError('duplicate WINDOW request')
        uint(s.request_serial+1,64)
        s=replace(s,request_serial=s.request_serial+1)
        pending[key]=(op,write,f['window_row'],f['window_active_user'],f['window_sector'],s.request_serial)
        events.append(Event('request',op,key+(s.request_serial,f['window_req_addr'],write)))
    if f['window_rsp_take']:
        key=('window',0,f['window_rsp_tag'])
        owned=pending.get(key)
        if not owned or owned[1] or not f['window_reply_ok'] or f['window_rsp_beat'] or f['window_rsp_poison']:
            raise ValueError('unmatched/invalid WINDOW reply')
        if (f['window_row'],f['window_active_user'],f['window_sector']) != owned[2:5]:
            raise ValueError('WINDOW row lifetime mismatch')
        del pending[key]; events.append(Event('reply',owned[0],key))
    if f['window_write_done'] and f['window_state'] in (2,4):
        owned=[k for k,v in pending.items() if v[0]==s.block and v[1]]
        if len(owned)!=1: raise ValueError('unowned write acknowledgement')
        del pending[owned[0]]; events.append(Event('write_ack',s.block))
    if f['window_row_publish']:
        if not (f['window_reply_ok'] and f['window_rsp_take'] and f['window_sector']==16):
            raise ValueError('early row publication')
        retire('refill','row_publish')
    if f['window_block_publish']:
        if not (f['window_write_done'] and f['window_state']==4):
            raise ValueError('early block publication')
        retire('block','block_publish')
    if f['stage_req_take']:
        if s.merge is None: raise ValueError('unowned staged read')
        key=(f['stage_req_user'],f['stage_req_first'],f['stage_req_mask'])
        if key in stages: raise ValueError('duplicate stage request')
        stages.append(key);events.append(Event('stage_request',s.merge,key))
    if f['stage_rsp_take']:
        key=(f['stage_rsp_user'],f['stage_rsp_first'],f['stage_rsp_mask'])
        if key not in stages or f['stage_rsp_fault'] or f['stage_rsp_valid'] & key[2] != key[2]:
            raise ValueError('invalid stage reply')
        stages.remove(key);events.append(Event('stage_reply',s.merge,key))
    if f['staged']: events.append(Event('staged',s.source))
    if f['stream_take']:
        if not s.merge or f['active_gen']!=s.merge.generation: raise ValueError('wrong stream generation')
        events.append(Event('stream_take',s.merge,(f['stream_mask'],)))
    if f['merge_done']:
        if stages: raise ValueError('early merge retire')
        retire('merge','merge_done')
    if f['source_done']: retire('source','source_done')
    ckv_fields=[k for k in f if k.startswith('ckv') and k!='ckv_available']
    if not f['ckv_available'] and any(f[k] for k in ckv_fields):
        raise ValueError('CKV hooks unavailable')
    if f['ckv_select_accept']:
        if s.fetch or s.replay or any(k[0]=='ckv' for k in pending):
            raise ValueError('selection replacement while lifetime outstanding')
        # No native selection retirement hook: keep epoch until next acceptance.
        s=replace(s,selection=None)
        accept('selection','ckv_selection',0)
    if f['ckv_fetch_accept']:
        if not s.selection: raise ValueError('fetch without selection')
        accept('fetch','ckv_fetch',0,s.selection.serial)
    if f['ckv_job_accept']:
        if not s.selection: raise ValueError('replay without selection')
        accept('replay','ckv_replay',f['ckv_job_gen'],s.selection.serial)
    for stack in range(4):
        pre=f'ckv{stack}_'
        if f[pre+'req_take'] != (f[pre+'req_offer'] & f[pre+'req_ready']):
            raise ValueError('CKV acceptance qualifier')
        if f[pre+'req_take']:
            tag=f[pre+'req_tag']
            if not s.fetch or not f[pre+'req_offer'] or f[pre+'req_we'] or tag>>10 or (tag&15)>8:
                raise ValueError('invalid owned CKV read')
            key=('ckv',stack,tag)
            if key in pending: raise ValueError('duplicate CKV slot/sector')
            uint(s.request_serial+1,64)
            s=replace(s,request_serial=s.request_serial+1)
            pending[key]=(s.fetch,False,s.selection.serial,s.request_serial)
            events.append(Event('request',s.fetch,key+(s.request_serial,f[pre+'req_addr'],)))
        if f[pre+'rsp_take']:
            key=('ckv',stack,f[pre+'rsp_tag']); owned=pending.get(key)
            if not owned or f[pre+'rsp_beat'] or owned[2]!=s.selection.serial:
                raise ValueError('unmatched CKV reply/epoch')
            # Poison and issued/got source DMA checks still require future binding.
            del pending[key]; events.append(Event('raw_matched_reply',owned[0],key))
    if f['ckv_collect_take']:
        if not s.selection or f['ckv_collect_bad']: raise ValueError('invalid collector')
        for lane in range(5):
            if (f['ckv_collect_take']>>lane)&1:
                r=(f['ckv_collect_rank']>>(lane*10))&1023
                gid=(f['ckv_collect_gid']>>(lane*21))&((1<<21)-1)
                events.append(Event('collector_observed',s.selection,(lane,r,gid)))
    if f['ckv_stream_take']:
        if not s.replay or f['ckv_job_gen']!=s.replay.generation:
            raise ValueError('wrong QK/PV generation')
        events.append(Event('stream_take',s.replay,(f['ckv_stream_mask'],)))
    if f['ckv_job_done']: retire('replay','job_done')
    if f['ckv_fetch_done']: retire('fetch','fetch_done')
    if f['ckv_rows_ready']: events.append(Event('rows_ready',s.selection))
    return replace(s,requests=tuple(pending.items()),stages=tuple(stages)),tuple(events)
