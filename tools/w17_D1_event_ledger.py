"""Simulation diagnostic ledger: source callbacks, never PHY or service bounds."""
from dataclasses import dataclass, field

def uint(v, bits):
    if type(v) is not int or not 0 <= v < 1 << bits:
        raise ValueError('integer envelope')
    return v

def admission(packet):
    if set(packet) != {'available', 'me_ready', 'kv_ok', 'kvd_v', 'win_idle'}:
        raise ValueError('four-bit schema')
    if type(packet['available']) is not bool:
        raise ValueError('availability type')
    if not packet['available']:
        if any(packet[k] is not None for k in packet if k != 'available'):
            raise ValueError('unavailable is not zero-qualified')
        return None
    for key in packet:
        if type(packet[key]) is not bool:
            raise ValueError('bit type')
    return packet['me_ready'] and packet['kv_ok'] and not packet['kvd_v'] and packet['win_idle']

@dataclass
class Ledger:
    pending: tuple | None = None
    accepted: int = 0
    retired: int = 0
    last_cycle: int = -1
    fault: bool = False
    seen: set = field(default_factory=set)

    def step(self, *, cycle, fault, event=None):
        # Validate complete packet before mutation. Fault is sticky and wins over done.
        uint(cycle, 64)
        if cycle <= self.last_cycle or type(fault) is not bool:
            raise ValueError('repeated/reversed step or fault type')
        pending, accepted, retired, seen = self.pending, self.accepted, self.retired, self.seen.copy()
        if event is not None:
            if self.fault or fault:
                raise ValueError('faulted completion/progress')
            if set(event) != {'kind','owner','generation','operation','address','tag','beat','state'}:
                raise ValueError('event schema')
            if event['kind'] not in ('READ_ACCEPT','WRITE_ACCEPT','READ_RETURN','WRITE_ACK'):
                raise ValueError('busy/PC/prediction is not a causal event')
            identity=tuple(uint(event[k], b) for k,b in [('owner',10),('generation',16),('operation',64),('address',30),('tag',16)])
            uint(event['beat'],4); uint(event['state'],3)
            kind=event['kind']
            if kind.endswith('ACCEPT'):
                if pending is not None or identity in seen or event['beat'] != 0:
                    raise ValueError('credit/spent identity/envelope')
                if event['state'] not in ((5,) if kind=='READ_ACCEPT' else (1,3)):
                    raise ValueError('accept state')
                pending=(identity, kind, cycle); accepted+=1; seen.add(identity)
            else:
                expected='READ_ACCEPT' if kind=='READ_RETURN' else 'WRITE_ACCEPT'
                if pending is None or pending[0]!=identity or pending[1]!=expected or cycle<=pending[2] or event['beat']!=0:
                    raise ValueError('unowned/wrong epoch/early/duplicate completion')
                if event['state'] not in ((6,) if kind=='READ_RETURN' else (2,4)):
                    raise ValueError('retirement state')
                pending=None; retired+=1
        self.pending, self.accepted, self.retired, self.seen = pending, accepted, retired, seen
        self.fault |= fault
        self.last_cycle = cycle
