#!/usr/bin/env python3
"""Pure provider projection over immutable causal observations; no selected hook.

Operation identity is supplied by an acceptance/epoch observer, never inferred
from PC, busy or a link queue. Legacy wire tags alone cannot disambiguate reused
sectors/slots or old responses across reset/selection lifetimes.
"""
from dataclasses import dataclass

FAMILIES=('window_source','window_stream','window_block_write','packed_descriptor','ckv_selection','ckv_fetch','ckv_stream')
RETIRE_HOOKS={'window_source':'window_schedule_done',
 'window_stream':'window_merge_done','window_block_write':'window_scale_write_done',
 'packed_descriptor':'descriptor_done_after_engine_idle','ckv_fetch':'ckv_fetch_done',
 'ckv_stream':'ckv_stream_job_done'}

KINDS=('op_accept','op_retire','request_accept','read_reply','write_done','row_commit','phase','link_queue')


def uint(value,bits,name):
    if type(value) is not int or not 0<=value<2**bits: raise ValueError('invalid '+name)


@dataclass(frozen=True)
class Operation:
    reset_epoch: int
    rank: int
    family: str
    accept_serial: int
    native_generation: int|None=None
    selection_epoch: 'Operation|None'=None

    def __post_init__(self):
        uint(self.reset_epoch,64,'reset epoch');uint(self.rank,2,'rank');uint(self.accept_serial,64,'accept serial')
        if self.family not in FAMILIES:raise ValueError('operation family')
        if self.native_generation is not None:uint(self.native_generation,16,'native descriptor generation')
        if self.selection_epoch is not None:
            s=self.selection_epoch
            if not isinstance(s,Operation) or s.family!='ckv_selection' or s.rank!=self.rank or s.reset_epoch!=self.reset_epoch:
                raise ValueError('selection epoch owner mismatch')


@dataclass(frozen=True)
class Request:
    operation: Operation
    ordinal: int
    stack: int
    client: str
    tag: int
    write: bool=False

    def __post_init__(self):
        if not isinstance(self.operation,Operation): raise ValueError('operation identity missing')
        uint(self.ordinal,64,'request ordinal');uint(self.stack,2,'stack')
        uint(self.tag,14,'client tag (two transport-owner bits reserved)')
        if self.client not in ('window','selected_ckv'):raise ValueError('client')
        if type(self.write) is not bool:raise ValueError('write boolean')
        if (self.client=='window') != self.operation.family.startswith('window_'):
            raise ValueError('request client/family mismatch')


@dataclass(frozen=True)
class StageRead:
    operation: Operation
    ordinal: int
    user: int
    first_row: int
    mask: int

    def __post_init__(self):
        if not isinstance(self.operation,Operation) or self.operation.family not in ('window_source','window_stream'):
            raise ValueError('WINDOW staged-row operation required')
        uint(self.ordinal,64,'stage ordinal');uint(self.user,10,'user')
        uint(self.first_row,21,'first row');uint(self.mask,4,'row mask')
        if self.mask==0:raise ValueError('empty stage request')

    @property
    def write(self):return False
    @property
    def client(self):return 'window_stage'


def wire_key(request):
    op=request.operation
    if isinstance(request,StageRead):
        return (op.reset_epoch,op.rank,'window_stage',request.user,request.first_row,request.mask)
    return (op.reset_epoch,op.rank,request.client,request.stack,request.tag,request.write)


@dataclass(frozen=True)
class Observation:
    cycle: int
    kind: str
    operation: Operation|None=None
    request: Request|StageRead|None=None
    qualified: bool=True
    association_proven: bool=False
    beat: int=0
    selection_rank: int|None=None
    gid: int|None=None
    label: str=''
    valid_mask: int|None=None

    def __post_init__(self):
        uint(self.cycle,64,'cycle')
        if self.kind not in KINDS:raise ValueError('uncausal event kind')
        if type(self.qualified) is not bool or type(self.association_proven) is not bool:raise ValueError('qualification flags')
        uint(self.beat,4,'beat')
        if self.valid_mask is not None:uint(self.valid_mask,4,'valid lane mask')
        if self.kind=='link_queue':
            if self.operation is not None or self.request is not None:raise ValueError('link queue is not a DUT operation')
        elif not isinstance(self.operation,Operation):raise ValueError('operation required')
        if self.kind=='op_retire' and self.label!=RETIRE_HOOKS.get(self.operation.family):
            raise ValueError('source-owned retirement hook unavailable or mismatched')
        if self.kind in ('request_accept','read_reply','write_done'):
            if not isinstance(self.request,(Request,StageRead)) or self.request.operation!=self.operation:raise ValueError('owned request required')
        if self.kind=='row_commit':
            if self.selection_rank is None or self.gid is None:raise ValueError('row metadata missing')
            uint(self.selection_rank,10,'selection rank');uint(self.gid,21,'gid')
            if self.selection_rank>=512:raise ValueError('selection rank outside K512')


@dataclass(frozen=True)
class Bounds:
    operation_cycles: int|None=None
    response_cycles: int|None=None
    scope: str='missing'
    authority: str=''

    def __post_init__(self):
        for value in (self.operation_cycles,self.response_cycles):
            if value is not None:
                uint(value,64,'bound');
                if value==0:raise ValueError('positive bound')
        if self.scope not in ('missing','synthetic'):raise ValueError('actual causal bounds not yet supplied/reviewed')
        if self.scope=='missing' and (self.operation_cycles is not None or self.response_cycles is not None):
            raise ValueError('missing cannot admit a number')
        if self.scope=='synthetic' and not self.authority:raise ValueError('synthetic authority required')


@dataclass(frozen=True)
class View:
    operation: Operation
    accepted_cycle: int
    retired_cycle: int|None
    outstanding: tuple
    rows_committed: tuple
    operation_age: int
    deadline: int|None
    response_deadlines: tuple
    status: tuple
    universal_timeout_admitted: bool=False


def project(observations,now,bounds=Bounds()):
    """Pure projection. Input tuple and DUT/provider state are never mutated.

    Each read/write acknowledgement needs association proof from source-owned
    accept table plus epoch/fence provenance. Missing proof leaves the request
    outstanding, even if ready/valid is observed. Retirement cannot erase a
    previous deadline violation. Bounds in this model are missing or synthetic.
    """
    uint(now,64,'now')
    if type(observations) is not tuple or not isinstance(bounds,Bounds):raise ValueError('immutable tuple and bounds required')
    ops={};last=-1
    for e in observations:
        if not isinstance(e,Observation) or not last<=e.cycle<=now:raise ValueError('ordered causal observations required')
        last=e.cycle
        if e.kind=='link_queue':continue
        op=e.operation
        if not e.qualified:
            if op in ops:ops[op]['status'].add('SOURCE_QUALIFICATION_FAILED')
            continue
        if e.kind=='op_accept':
            if any((x.reset_epoch,x.rank,x.family,x.accept_serial)==
                   (op.reset_epoch,op.rank,op.family,op.accept_serial) for x in ops):
                raise ValueError('operation identity reused with changed context')
            if op.selection_epoch is not None and op.selection_epoch not in ops:
                raise ValueError('selection context not observed accepted')
            ops[op]={'start':e.cycle,'retire':None,'live':{},'spent':set(),'rows':set(),'status':set()}
            continue
        if op not in ops:raise ValueError('event without operation acceptance')
        s=ops[op]
        if s['retire'] is not None:raise ValueError('event after retirement')
        if e.kind=='request_accept':
            r=e.request
            if r.client=='selected_ckv' and r.write:raise ValueError('pinned mux rejects selected-CKV writes')
            if any(x.ordinal==r.ordinal for x in set(s['live'])|s['spent']):
                raise ValueError('request ordinal identity reused')
            if any(wire_key(x)==wire_key(r) for state in ops.values() for x in state['live']):
                raise ValueError('ambiguous concurrently reused wire identity')
            s['live'][r]=e.cycle
        elif e.kind in ('read_reply','write_done'):
            r=e.request
            if r not in s['live']:raise ValueError('response not associated with accepted request')
            if (e.kind=='write_done')!=r.write:raise ValueError('read/write response kind mismatch')
            if isinstance(r,StageRead):
                if e.valid_mask is None:raise ValueError('stage lane validity missing')
                if (e.valid_mask&r.mask)!=r.mask:
                    s['status'].add('SOURCE_QUALIFICATION_FAILED');continue
            elif e.beat!=0:raise ValueError('one-sector beat must be zero')
            if not e.association_proven:
                s['status'].add('IDENTITY_UNAVAILABLE');continue
            if bounds.response_cycles is not None and e.cycle-s['live'][r]>bounds.response_cycles:
                s['status'].add('SYNTHETIC_RESPONSE_DEADLINE_VIOLATION')
            del s['live'][r];s['spent'].add(r)
        elif e.kind=='row_commit':
            key=(e.selection_rank,e.gid)
            if any(rank==e.selection_rank for rank,gid in s['rows']):raise ValueError('duplicate collector rank')
            s['rows'].add(key)
        elif e.kind=='op_retire':
            if s['live']:raise ValueError('retirement with unretired request')
            s['retire']=e.cycle
        # stage/rows_ready/links/PC/busy are not operation retirement.
        if bounds.operation_cycles is not None and e.cycle-s['start']>bounds.operation_cycles:
            s['status'].add('SYNTHETIC_OPERATION_DEADLINE_VIOLATION')
    views=[]
    for op,s in ops.items():
        end=s['retire'] if s['retire'] is not None else now
        if bounds.operation_cycles is not None and end-s['start']>bounds.operation_cycles:
            s['status'].add('SYNTHETIC_OPERATION_DEADLINE_VIOLATION')
        if bounds.response_cycles is not None and any(now-t>bounds.response_cycles for t in s['live'].values()):
            s['status'].add('SYNTHETIC_RESPONSE_DEADLINE_VIOLATION')
        if op.family in ('window_source','window_stream','packed_descriptor','ckv_stream') and op.native_generation is None:
            s['status'].add('DESCRIPTOR_CONTEXT_UNAVAILABLE')
        if op.family in ('ckv_fetch','ckv_stream') and op.selection_epoch is None:
            s['status'].add('SELECTION_CONTEXT_UNAVAILABLE')
        s['status'].add('BOUND_MISSING' if bounds.scope=='missing' else 'SYNTHETIC_BOUND_ONLY')
        if bounds.operation_cycles is not None:uint(s['start']+bounds.operation_cycles,64,'derived operation deadline')
        if bounds.response_cycles is not None:
            for t in s['live'].values():uint(t+bounds.response_cycles,64,'derived response deadline')
        views.append(View(op,s['start'],s['retire'],tuple(s['live'].items()),tuple(sorted(s['rows'])),
            end-s['start'],None if bounds.operation_cycles is None else s['start']+bounds.operation_cycles,
            tuple((r,t+bounds.response_cycles) for r,t in s['live'].items()) if bounds.response_cycles is not None else (),
            tuple(sorted(s['status']))))
    return tuple(views)
