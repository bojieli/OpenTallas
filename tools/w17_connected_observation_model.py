"""Offline real packet adapter and conditional guards; no runtime/admission claims."""
from dataclasses import dataclass,replace
import re
from simulation_observation_api import decode,observe,State,uint
from observer_l0_unavailable_api import observe_l0

@dataclass(frozen=True)
class Frame:
    rank:int
    host_cycle:int
    done:bool
    fault:int
    fault_sources:int
    state:int
    packet:int

def parse_frame(line):
    parts=line.split()
    if len(parts)!=8 or parts[0]!='OBS' or not re.fullmatch(r'[0-9a-f]{256}',parts[7]):raise ValueError('trace frame')
    if not all(re.fullmatch(r'0|[1-9][0-9]*',parts[i]) for i in (1,2,3)):raise ValueError('decimal envelope')
    if not all(re.fullmatch(r'[0-9a-f]{'+str(n)+'}',parts[i]) for i,n in [(4,8),(5,8),(6,16)]):raise ValueError('hex envelope')
    rank,cycle,done=map(int,parts[1:4]);uint(rank,2);uint(cycle,64);uint(done,1)
    packet=int(parts[7],16);f=decode(packet)
    if f['rank']!=rank or f['epoch']!=1:raise ValueError('rank/reset era mismatch')
    return Frame(rank,cycle,bool(done),int(parts[4],16),int(parts[5],16),int(parts[6],16),packet)

@dataclass(frozen=True)
class Capture:
    states:tuple=(State(),State(),State(),State())
    host_cycles:tuple=(-1,-1,-1,-1)
    sticky_faults:tuple=(0,0,0,0)
    done_seen:tuple=(False,False,False,False)
    frames:int=0

def feed(state,frame,mode):
    if mode not in ('WINDOW','CKV') or not isinstance(state,Capture) or not isinstance(frame,Frame):raise ValueError('capture type/mode')
    uint(frame.rank,2);uint(frame.host_cycle,64);uint(frame.fault,32);uint(frame.fault_sources,32);uint(frame.state,64)
    if type(frame.done) is not bool:raise ValueError('DONE boolean')
    r=frame.rank;f=decode(frame.packet)
    if bool(f['ckv_available'])!=(mode=='CKV'):raise ValueError('availability mismatch')
    if state.host_cycles[r]>=0 and frame.host_cycle!=state.host_cycles[r]+1:raise ValueError('lost/repeated host edge')
    projection=(observe_l0(state.states[r],frame.packet) if mode=='WINDOW' else observe(state.states[r],frame.packet))
    ledger,events=projection[:2]
    ledgers=list(state.states);ledgers[r]=ledger;cycles=list(state.host_cycles);cycles[r]=frame.host_cycle
    sticky=list(state.sticky_faults)
    # Fault first; DONE never clears fault or proves owner quiescence.
    sticky[r]|=frame.fault|frame.fault_sources|(frame.state>>32)
    done=list(state.done_seen);done[r]|=frame.done
    return Capture(tuple(ledgers),tuple(cycles),tuple(sticky),tuple(done),state.frames+1),events

@dataclass(frozen=True)
class Guard:
    accepted_cycle:int
    outstanding:tuple=()
    last_retired_cycle:int|None=None
    sticky_violations:tuple=()

def accepted(g,key,cycle):
    uint(cycle,64)
    if cycle<g.accepted_cycle or key in dict(g.outstanding):raise ValueError('duplicate/reversed owned acceptance')
    return replace(g,outstanding=g.outstanding+((key,cycle),))

def retirement(g,key,cycle,*,source_qualified,association_proven,operation_budget=None,response_budget=None,scope='missing'):
    uint(cycle,64)
    if g.last_retired_cycle is not None and cycle<g.last_retired_cycle:raise ValueError('reversed retirement')
    g,_=inspect_guard(g,cycle,operation_budget,response_budget,scope)
    pending=dict(g.outstanding)
    if type(source_qualified) is not bool or type(association_proven) is not bool:raise ValueError('qualification flags')
    if key not in pending or cycle<pending[key]:raise ValueError('wrong owner or early retirement')
    if not (source_qualified and association_proven):return g # raw reply/busy is not causal retirement
    del pending[key]
    return replace(g,outstanding=tuple(pending.items()),last_retired_cycle=cycle)

def inspect_guard(g,now,operation_budget=None,response_budget=None,scope='missing'):
    uint(now,64)
    if now<g.accepted_cycle or scope not in ('missing','conditional','synthetic'):raise ValueError('guard scope/time')
    if scope=='missing' and (operation_budget is not None or response_budget is not None):raise ValueError('no causal bound authority')
    violations=set(g.sticky_violations)
    if operation_budget is not None:
        uint(operation_budget,64)
        if not operation_budget:raise ValueError('positive budget')
        if now-g.accepted_cycle>operation_budget:violations.add('OPERATION_WINDOW_EXCEEDED')
    if response_budget is not None:
        uint(response_budget,64)
        if not response_budget:raise ValueError('positive budget')
        if any(now-t>response_budget for _,t in g.outstanding):violations.add('RESPONSE_WINDOW_EXCEEDED')
    return replace(g,sticky_violations=tuple(sorted(violations))),dict(operation_age=now-g.accepted_cycle,outstanding_ages=tuple((k,now-t) for k,t in g.outstanding),diagnostics=tuple(sorted(violations)),scope=scope,causal_service='BOUND_MISSING',completion=False,universal_timeout_admitted=False)

def fulltoken_verdict(coverage,captures,owner_receipts,exact_outputs):
    required=[f'layer{i}' for i in range(40)]+['final_norm','vocabulary_head']
    blockers=[]
    if coverage!=required:blockers.append('CONNECTED_FULLTOKEN_STAGE_COVERAGE_MISSING')
    if set(captures)!=set(required):blockers.append('PERSISTENT_STAGE_RANK_CAPTURES_MISSING')
    # No verified physical fences/provider quiescence implementation is bound yet.
    blockers.append('SOURCE_OWNER_PROVIDER_QUIESCENCE_UNAVAILABLE')
    if not exact_outputs:blockers.append('EXACT_FINAL_OUTPUT_COMPARISON_MISSING')
    if any(any(c.sticky_faults) for c in captures.values()):blockers.append('STICKY_FAULT')
    return dict(status='PREPARATION_BLOCKED_NOT_FULLTOKEN_PASS',blockers=blockers,causal_deadlines='BOUND_MISSING',numeric_or_fulltoken_credit=False)
