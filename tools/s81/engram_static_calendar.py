"""Compile reserved on-chip lookup slots; never certify an external-memory bound.

The source emits six requests at launch+20..25 (PIPE1). It reserves all
54 response atoms until RETURN_AGE, then emits 48 words at RETURN_AGE+5..52.
The source's active reservation drains at RETURN_AGE+64. These offsets must
stay bound to the real source proof; a request/response service schedule is
separately required before canonical adoption.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Lookup:
    source_operation: str
    launch: int
    slot: int
    return_age: int


def compile_calendar(operations, *, slots=8):
    """Reject collisions rather than insert stalls, retries or shifted epochs."""
    if not isinstance(slots, int) or isinstance(slots, bool) or slots < 1 or slots > 8:
        raise ValueError('actual slot count must be 1..8')
    events = []
    prior_end = -1
    identities = set()
    for op in operations:
        if not isinstance(op.source_operation, str) or not op.source_operation:
            raise ValueError('literal source operation is mandatory')
        if op.source_operation in identities:
            raise ValueError('duplicate source operation')
        identities.add(op.source_operation)
        if any(not isinstance(v, int) or isinstance(v, bool) for v in (op.launch,op.slot,op.return_age)):
            raise ValueError('cycles and slot must be integers')
        if op.launch < 0 or not 0 <= op.slot < slots or not 32 <= op.return_age <= 65000:
            raise ValueError('invalid source reservation')
        if op.launch <= prior_end:
            raise ValueError('lookup reservations overlap; producer must change its programme')
        prior_end = op.launch + op.return_age + 64
        events.append({'source_operation': op.source_operation, 'launch': op.launch,
            'slot': op.slot, 'request_cycles': list(range(op.launch+20,op.launch+26)),
            'response_deadline_exclusive': op.launch+op.return_age+1,
            'output_cycles': list(range(op.launch+op.return_age+5,op.launch+op.return_age+53)),
            'reservation_last_edge': prior_end,
            'external_service_qualification': 'UNBOUND',
            'collective_consumer_qualification': 'UNBOUND'})
    return events
