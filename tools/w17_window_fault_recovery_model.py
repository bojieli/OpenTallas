#!/usr/bin/env python3
"""Finite protocol specification, NOT a backend/HW model or live recovery provider.

Caller supplies future drain/fence acknowledgements. No existing RTL signal
can supply the full contract today; model-only certificates never admit RTL.
"""
from dataclasses import dataclass
from enum import Enum

class Rejected(ValueError): pass
class Phase(Enum):
    RESERVED='reserved'
    KARB_HELD='karb_held'
    QUEUED='backend_queued'
    RETURN='backend_return'
    HELD='registered_held_return'

@dataclass(frozen=True)
class Identity:
    lease: int
    serial: int
    epoch: int
    sector: int
    pc: int
    address: int
    owner: str='WINDOW'
    beat: int=0
    def __post_init__(self):
        for name,bits in [('lease',64),('serial',64),('epoch',9),('sector',5),('pc',5),('address',30),('beat',4)]:
            v=getattr(self,name)
            if type(v) is not int or not 0<=v<1<<bits:raise Rejected('typed identity aperture: '+name)
        if self.owner!='WINDOW' or self.sector>16 or self.beat!=0:raise Rejected('WINDOW identity shape')
        if self.pc!=(((self.address>>2)^(self.address>>7)^(self.address>>12))&31):
            raise Rejected('actual KARB/backend PC map')
    @property
    def wire_tag(self):return (self.epoch<<5)|self.sector

@dataclass(frozen=True)
class DrainAck:
    # Proposed exact owner-scope signals: no production provider exists yet.
    actor: str
    lease: int
    revision: int
    outstanding: int
    q: tuple=(0,)*32
    r: tuple=(0,)*32
    held: tuple=(0,)*32
    frozen: bool=True
    no_future_delivery: bool=False
    provider: str='MODEL_ONLY'

ACTORS=('WINDOW','MUX','KARB','BACKEND','DELIVERY_FENCE')

class RecoveryModel:
    def __init__(self, credits=8, epoch=0):
        if type(credits) is not int or not 1<=credits<=8:raise Rejected('bounded credits')
        if type(epoch) is not int or not 0<=epoch<512:raise Rejected('epoch aperture')
        self.credits=credits;self.epoch=epoch;self.lease=0;self.serial=0
        self.entries={};self.fault_code=0;self.frozen=False;self.revision=0
        self.reserved=self.cancelled=self.accepted=self.retired=0
        self.acks={};self.events=[];self.published=False;self.return_order=[[] for _ in range(32)]
    def guard_revision(self):
        if self.revision>=2**64-1:raise Rejected('ack revision exhaustion; no wrap')
    def changed(self,event,identity=None):
        self.revision+=1;self.acks.clear();self.events.append((event,identity));self.invariants()
    def invariants(self):
        assert len(self.entries)<=self.credits
        assert self.reserved-self.cancelled-self.retired==len(self.entries)
        assert self.accepted-self.retired==sum(p!=Phase.RESERVED for p in self.entries.values())
        for pc in range(32):
            assert sum(i.pc==pc and p==Phase.QUEUED for i,p in self.entries.items())<=64
            assert sum(i.pc==pc and p in (Phase.RETURN,Phase.HELD) for i,p in self.entries.items())<=32
        assert len({i.wire_tag for i in self.entries})==len(self.entries)
        assert sum(map(len,self.return_order))==sum(p in (Phase.RETURN,Phase.HELD) for p in self.entries.values())
    def reserve(self,sector,address):
        self.guard_revision()
        if self.frozen or self.fault_code:raise Rejected('original fault admission remains closed')
        if len(self.entries)>=self.credits:raise Rejected('finite credit capacity')
        if self.serial==2**64-1:raise Rejected('serial exhaustion requires external requalification')
        pc=((address>>2)^(address>>7)^(address>>12))&31
        identity=Identity(self.lease,self.serial,self.epoch,sector,pc,address)
        if any(i.wire_tag==identity.wire_tag for i in self.entries):raise Rejected('wire tag already leased')
        self.serial+=1;self.entries[identity]=Phase.RESERVED;self.reserved+=1
        self.changed('reserve',identity);return identity
    def cancel(self,identity):
        self.guard_revision()
        if self.entries.get(identity)!=Phase.RESERVED:raise Rejected('accepted work cannot cancel without provider retirement')
        del self.entries[identity];self.cancelled+=1;self.changed('cancel_unaccepted',identity)
    def accept(self,identity,pipe_out=False):
        self.guard_revision()
        if self.frozen or self.entries.get(identity)!=Phase.RESERVED:raise Rejected('accept after freeze or without reserve')
        self.entries[identity]=Phase.KARB_HELD if pipe_out else Phase.QUEUED
        self.accepted+=1;self.changed('accept',identity)
    def backend_accept(self,identity):
        self.guard_revision()
        if self.entries.get(identity)!=Phase.KARB_HELD:raise Rejected('no KARB-held lease')
        self.entries[identity]=Phase.QUEUED;self.changed('backend_accept',identity)
    def complete(self,identity):
        self.guard_revision()
        if self.entries.get(identity)!=Phase.QUEUED:raise Rejected('no queued lease')
        self.entries[identity]=Phase.RETURN;self.return_order[identity.pc].append(identity);self.changed('queue_return',identity)
    def offer(self,identity):
        self.guard_revision()
        if self.entries.get(identity)!=Phase.RETURN:raise Rejected('no return head')
        # Each PC registers only its RQ head; held is an alias, not another lease.
        if self.return_order[identity.pc][0]!=identity:raise Rejected('not per-PC return head')
        self.entries[identity]=Phase.HELD;self.changed('hold_registered_return',identity)
    def consume(self,identity,ready=True):
        self.guard_revision()
        if self.entries.get(identity)!=Phase.HELD:raise Rejected('stale/duplicate/wrong-lease return')
        if not ready:return False
        pcs=[i.pc for i,p in self.entries.items() if p==Phase.HELD]
        if identity.pc!=min(pcs):raise Rejected('actual lowest-PC KARB selection')
        self.return_order[identity.pc].pop(0)
        del self.entries[identity];self.retired+=1
        self.changed('retire_discard_on_fault' if self.fault_code else 'retire',identity);return True
    def inject(self,identity):
        self.guard_revision()
        # An invalid delivery never frees another reservation/credit.
        if self.entries.get(identity)!=Phase.HELD:
            self.fault(4);raise Rejected('stale/duplicate return rejected; no retirement')
        return self.consume(identity)
    def fault(self,code=4):
        self.guard_revision()
        if type(code) is not int or not 0<code<32:raise Rejected('fault code aperture')
        self.fault_code|=code;self.frozen=True;self.published=False
        self.changed('fault_freeze')
    def reset(self):
        self.guard_revision()
        # No reset is a retirement operation, regardless of reset domain.
        if self.entries or not self.can_restart():raise Rejected('reset denied until complete fenced quiescence')
        self.restart(reset_epoch=True)
    def acknowledge(self,ack):
        if ack.actor not in ACTORS or ack.lease!=self.lease or ack.revision!=self.revision:
            raise Rejected('stale/wrong acknowledgement identity')
        if not ack.frozen or not self.frozen or ack.outstanding!=0 or self.entries:
            raise Rejected('unfrozen/owned acknowledgement')
        for vector in (ack.q,ack.r,ack.held):
            if len(vector)!=32 or any(type(v) is not int or v!=0 for v in vector):raise Rejected('nonempty/malformed drain')
        if ack.actor=='DELIVERY_FENCE' and not ack.no_future_delivery:raise Rejected('quiet samples are not delivery fence')
        self.acks[ack.actor]=ack
    def can_restart(self):
        return self.frozen and not self.entries and set(self.acks)==set(ACTORS) and all(
            a.lease==self.lease and a.revision==self.revision for a in self.acks.values())
    def rtl_admission(self):
        # Certificates in this executable specification have no live provider.
        return False
    def restart(self,reset_epoch=False):
        self.guard_revision()
        if not self.can_restart():raise Rejected('missing end-to-end quiescence/fence acknowledgement')
        if self.lease==2**64-1:raise Rejected('lease exhaustion')
        self.lease+=1;self.epoch=0 if reset_epoch else (self.epoch+1)%512
        self.fault_code=0;self.frozen=False;self.changed('restart_after_fence')
    def state(self):
        return dict(epoch=self.epoch,lease=self.lease,fault=self.fault_code,frozen=self.frozen,
                    outstanding=len(self.entries),reserved=self.reserved,cancelled=self.cancelled,
                    accepted=self.accepted,retired=self.retired,acknowledgements=sorted(self.acks),
                    rtl_admission=False)

def candidate_wire_accepts(current_epoch,issued,received,tag,beat=0,fault=False):
    """Source-bound FR_PIPE comparator; deliberately lacks lease/serial identity."""
    sector=tag&31
    return not fault and sector<=16 and tag>>5==current_epoch and sector in issued and sector not in received and beat==0

def model_only_fence(model):
    """Test convenience, explicitly NOT a production acknowledgement provider."""
    for actor in ACTORS:
        model.acknowledge(DrainAck(actor,model.lease,model.revision,0,no_future_delivery=actor=='DELIVERY_FENCE'))
