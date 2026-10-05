#!/usr/bin/env python3
"""Standalone trace contract, not a live watchdog or a universal service bound.

An operation deadline never slides with heartbeat progress. Tagged admission and
response ages have separate bounds. Missing proof obligations remain UNKNOWN;
PC silence is a diagnostic only, while fault is independently terminal.
"""
from copy import deepcopy
from dataclasses import dataclass, field


def natural(value, name, positive=False):
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(name + ' must be an exact nonnegative integer')
    return value


@dataclass(frozen=True)
class Budget:
    requests: int
    admission: int
    response: int
    issue_gap: int
    stage: int
    drain: int
    authority: str
    conditions: tuple
    scope: str = 'synthetic'

    def __post_init__(self):
        natural(self.requests,'requests',True)
        for name in ('admission','response','issue_gap','stage','drain'):
            natural(getattr(self,name),name)
        if (self.scope not in ('synthetic','conditional') or type(self.authority) is not str
                or not self.authority or type(self.conditions) is not tuple or not self.conditions
                or any(type(c) is not str or not c for c in self.conditions)):
            raise ValueError('explicit bounded scenario authority and conditions required')

    @property
    def operation(self):
        # Conservative serial one-credit composition. Stage includes work to first
        # offer/publication; drain covers completion after the last matched reply.
        return self.stage + self.requests*(self.admission+self.response+self.issue_gap) + self.drain

    @property
    def universal_timeout_admitted(self):
        return False


@dataclass(frozen=True)
class Sample:
    pc: int
    busy: int = 0
    fault: int = 0
    done: bool = False

    def __post_init__(self):
        for name in ('pc','busy','fault'): natural(getattr(self,name),name)
        if self.pc>=2**14 or self.busy>=2**5 or self.fault>=2**8:
            raise ValueError('sample exceeds pinned interface width')
        if type(self.done) is not bool: raise ValueError('done must be bool')


@dataclass(frozen=True)
class Event:
    rank: int
    kind: str
    identity: str = ''

    def __post_init__(self):
        natural(self.rank,'rank')
        if self.kind not in ('offer','accept','response','complete'):
            raise ValueError('only causal service events are recognized')
        if self.kind!='complete' and (type(self.identity) is not str or not self.identity):
            raise ValueError('service event needs an operation-qualified unique identity')


@dataclass
class Rank:
    budget: Budget | None
    start: int
    last_useful: int
    pc: int | None = None
    offers: dict = field(default_factory=dict)
    inflight: dict = field(default_factory=dict)
    spent: set = field(default_factory=set)
    accepted: int = 0
    responses: int = 0
    complete: bool = False
    done: bool = False


class Watchdog:
    def __init__(self,budgets,start=0,diagnostic_pc_dwell=100000):
        natural(start,'start');natural(diagnostic_pc_dwell,'diagnostic dwell',True)
        if not budgets or any(b is not None and not isinstance(b,Budget) for b in budgets):
            raise ValueError('rank budgets must be Budget or unknown')
        self.ranks=[Rank(b,start,start) for b in budgets]
        self.cycle=start-1
        self.diagnostic_pc_dwell=diagnostic_pc_dwell
        self.failures=set()

    def advance(self,cycle,samples,events=()):
        natural(cycle,'cycle')
        if cycle<=self.cycle or len(samples)!=len(self.ranks) or any(not isinstance(s,Sample) for s in samples):
            raise ValueError('strictly increasing full rank samples required')
        # Transactional validation: malformed identities never leave an orphan.
        ranks=deepcopy(self.ranks);verdicts=list(sorted(self.failures))
        for i,(r,s) in enumerate(zip(ranks,samples)):
            if s.fault: verdicts.append((i,'FAULT')) # even if done/all done
            if not r.complete and not r.done and r.budget:
                if cycle-r.start>r.budget.operation: verdicts.append((i,'OPERATION_DEADLINE'))
                if any(cycle-t>r.budget.admission for t in r.offers.values()): verdicts.append((i,'ADMISSION_DEADLINE'))
                if any(cycle-t>r.budget.response for t in r.inflight.values()): verdicts.append((i,'RESPONSE_DEADLINE'))
            if s.pc!=r.pc:
                r.pc=s.pc;r.last_useful=cycle
        for e in events:
            if not isinstance(e,Event) or e.rank>=len(ranks): raise ValueError('invalid event rank')
            r=ranks[e.rank]
            if r.complete or r.done: raise ValueError('event after operation retirement')
            if e.kind=='offer':
                if e.identity in r.offers or e.identity in r.inflight or e.identity in r.spent:
                    raise ValueError('duplicate/spent identity')
                if r.offers or r.inflight: raise ValueError('one-credit scenario exceeded')
                r.offers[e.identity]=cycle
            elif e.kind=='accept':
                if e.identity not in r.offers: raise ValueError('accept without matching offer')
                if r.budget and r.accepted>=r.budget.requests: raise ValueError('request count exceeded')
                r.offers.pop(e.identity);r.inflight[e.identity]=cycle;r.accepted+=1;r.last_useful=cycle
            elif e.kind=='response':
                if e.identity not in r.inflight: raise ValueError('response without matching accepted request')
                r.inflight.pop(e.identity);r.spent.add(e.identity);r.responses+=1;r.last_useful=cycle
            else:
                if r.offers or r.inflight or (r.budget and r.responses!=r.budget.requests):
                    raise ValueError('completion before declared work/drain')
                r.complete=True;r.last_useful=cycle
        for i,(r,s) in enumerate(zip(ranks,samples)):
            if s.done:
                if r.offers or r.inflight or (r.budget and r.responses!=r.budget.requests):
                    verdicts.append((i,'DONE_WITH_UNRETIRED_SERVICE'))
                r.done=True
            if not r.done and not r.complete:
                if r.budget is None: verdicts.append((i,'BOUND_MISSING'))
                if cycle-r.last_useful>self.diagnostic_pc_dwell:
                    verdicts.append((i,'NO_OBSERVED_PROGRESS'))
        self.failures.update((r,k) for r,k in verdicts if k not in ('BOUND_MISSING','NO_OBSERVED_PROGRESS'))
        self.ranks=ranks;self.cycle=cycle
        return verdicts


def legacy_pc_timeout(trace,wd):
    """Exact shared ANY-rank PC reset and strict > comparator from pinned loop.

    Trace intentionally covers the no-fault/not-all-DONE branch only. Sparse
    samples cannot reconstruct unlogged intermediate PC changes.
    """
    natural(wd,'legacy watchdog',True)
    lastpc=None;last_move=None
    for cycle,pcs in trace:
        if lastpc is None or tuple(pcs)!=lastpc:
            lastpc=tuple(pcs);last_move=cycle
        if cycle-last_move>wd: return cycle
    return None
