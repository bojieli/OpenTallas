#!/usr/bin/env python3
"""Additive fault-quiescence write-tail specification; not a PHY/provider model.

The seven-cycle timer is conditional on these exact timing/reset bindings.
It does not make any actual RTL drain acknowledgement available.
"""
from dataclasses import dataclass

CLK_PS=1000
CWL_PS=6250
BURST_PS=1024
TAIL_PS=CWL_PS+BURST_PS
GUARD_CYCLES=7
class Rejected(ValueError):pass

def ceil_edge(ps):return ((ps+CLK_PS-1)//CLK_PS)*CLK_PS

def timing(column_ps):
    if type(column_ps) is not int or column_ps<0:raise Rejected('column timestamp')
    issue=ceil_edge(column_ps)
    ack=issue+CLK_PS
    return dict(column_ps=column_ps,issue_ps=issue,source_ack_ps=ack,
                physical_visible_ps=column_ps+TAIL_PS,
                guarded_ps=ack+GUARD_CYCLES*CLK_PS)

@dataclass(frozen=True)
class WriteIdentity:
    lease:int
    serial:int
    address:int
    mask:int
    def __post_init__(self):
        for name,bits in [('lease',64),('serial',64),('address',30),('mask',32)]:
            value=getattr(self,name)
            if type(value) is not int or not 0<=value<1<<bits:raise Rejected('write identity aperture: '+name)
        if self.mask==0:raise Rejected('empty write mask')
    @property
    def pc(self):return ((self.address>>2)^(self.address>>7)^(self.address>>12))&31

class WriteVisibilityLedger:
    def __init__(self,mem_words=264320,clk_ps=1000,lease=0):
        if clk_ps!=CLK_PS:raise Rejected('seven-cycle guard bound to CLK_PS1000')
        if type(mem_words) is not int or not 0<mem_words<=1<<30:raise Rejected('allocation aperture')
        if type(lease) is not int or not 0<=lease<2**64:raise Rejected('lease aperture')
        self.lease=lease;self.last_serial=-1
        self.mem_words=mem_words;self.owned={};self.frozen=False;self.fault_code=0
        self.accepted=0;self.transport_acked=0;self.visible_retired=0
    def accept(self,identity):
        if self.frozen:raise Rejected('fault freezes producer/write ingress')
        if not isinstance(identity,WriteIdentity):raise Rejected('typed write identity required')
        if identity.lease!=self.lease or identity.serial<=self.last_serial:raise Rejected('stale/reused write reservation identity')
        if identity.address>=self.mem_words:raise Rejected('AW30 modulo alias outside allocated MEM_WORDS')
        if identity in self.owned or len(self.owned)>=32:raise Rejected('duplicate/finite row write capacity')
        if any(e['ack_ps'] is None for e in self.owned.values()):raise Rejected('source one global write at a time')
        self.owned[identity]=dict(column_ps=None,issue_ps=None,ack_ps=None,visible_ps=None)
        self.last_serial=identity.serial;self.accepted+=1
    def issue(self,identity,column_ps):
        e=self.owned.get(identity)
        if e is None or e['column_ps'] is not None:raise Rejected('unaccepted/duplicate WR issue')
        t=timing(column_ps);e.update(column_ps=column_ps,issue_ps=t['issue_ps'],visible_ps=t['physical_visible_ps'])
    def acknowledge(self,identity,ack_ps):
        e=self.owned.get(identity)
        if e is None or e['issue_ps'] is None or e['ack_ps'] is not None:raise Rejected('unissued/duplicate/wrong write acknowledgement')
        if type(ack_ps) is not int or ack_ps%CLK_PS or ack_ps<e['issue_ps']+CLK_PS:raise Rejected('source observes ack no earlier than I+1')
        e['ack_ps']=ack_ps;self.transport_acked+=1
        # Ownership persists beyond transport ack; fault does not erase it.
    def retire_visible(self,identity,now_ps):
        e=self.owned.get(identity)
        if e is None or e['ack_ps'] is None:raise Rejected('no acknowledged write lease')
        if now_ps<max(e['visible_ps'],e['ack_ps']+GUARD_CYCLES*CLK_PS):raise Rejected('physical write tail still owned')
        del self.owned[identity];self.visible_retired+=1
    def fault(self,code=4):
        if type(code) is not int or not 0<code<32:raise Rejected('fault aperture')
        self.fault_code|=code;self.frozen=True
    def reset_allowed(self):
        """Write-side predicate only; never authorizes die/source reset alone."""
        return self.frozen and not self.owned
    def rtl_admission(self):return False # Actual physical-visibility provider remains absent.
    def state(self):
        return dict(owned=len(self.owned),accepted=self.accepted,transport_acked=self.transport_acked,
                    visible_retired=self.visible_retired,fault_code=self.fault_code,
                    logically_empty=self.accepted==self.transport_acked,
                    physically_drained=not self.owned,rtl_admission=False)


def recovery_can_restart(read_model,write_model):
    """Conjunction for model-only certificates; actual RTL admission still false."""
    return read_model.can_restart() and write_model.reset_allowed()
