"""Typed L0 projection: CKV wire padding is unavailable, never a qualified zero.

Legacy packet width/offsets remain identical to the separate L20 packet. The
padding is an ABI representation only; no CKV hook exists in the L0 wrapper.
"""
from dataclasses import dataclass
import simulation_observation_api as base
import prepare_simulation_observation_wrapper as layout

CKV_FIELDS=frozenset(f['name'] for f in layout.layout() if f['ckv'])

@dataclass(frozen=True)
class L0Observation:
    fields: tuple
    available_groups: frozenset = frozenset({'common','WINDOW'})
    def value(self,name):
        values=dict(self.fields)
        if name not in values:raise KeyError(name)
        return values[name]
    def qualified_value(self,name):
        value=self.value(name)
        if value is None:raise ValueError('observation unavailable: '+name)
        return value


def decode_l0(packet):
    raw=base.decode(packet)
    if raw['ckv_available']!=0 or any(raw[name]!=0 for name in CKV_FIELDS):
        raise ValueError('L0 ABI carries forbidden CKV observations')
    return L0Observation(tuple((name,None if name in CKV_FIELDS else value) for name,value in raw.items()))


def observe_l0(state,packet):
    # Reject unavailable-domain misuse before consulting immutable base ledger.
    observation=decode_l0(packet)
    if any(getattr(state,slot) is not None for slot in ('selection','fetch','replay')) or any(key[0]=='ckv' for key,_ in state.requests):
        raise ValueError('CKV ledger cannot bind L0 observer')
    next_state,events=base.observe(state,packet)
    if any(event.operation and event.operation.family.startswith('ckv') for event in events):
        raise ValueError('unavailable domain produced event')
    return next_state,events,observation
