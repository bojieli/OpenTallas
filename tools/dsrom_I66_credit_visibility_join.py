"""Gate accepted drain credit against visibility or a reserved downstream lease.
Nash's frozen replay returns credit after consumer acceptance. That is safe for
this join only if a distinct downstream seat holds ownership until VM visibility,
or if the credit return itself follows visibility. No provider is invented here.
"""
from fractions import Fraction


def check(journal, credit_delay, downstream_leases=None):
    delay = Fraction(credit_delay)
    if delay <= 0:
        raise ValueError('positive captured credit-return latency')
    events = {}
    kinds = ('read_accept_reserved', 'consumer_accept', 'home_visible', 'credit_return_capture')
    for e in journal:
        if e['kind'] not in kinds:
            continue
        row = e['row']
        if type(row) is not int or not 0 <= row < 576:
            raise ValueError('source row')
        key = (row, e['kind'])
        if key in events:
            raise ValueError('duplicate accepted event')
        events[key] = Fraction(e['time'])
    if len(events) != 576 * len(kinds):
        raise ValueError('complete accepted credit/visibility journal required')
    leases = {} if downstream_leases is None else downstream_leases
    if downstream_leases is not None and set(leases) != set(range(576)):
        raise ValueError('complete separate downstream lease required')
    transfer = 0
    for row in range(576):
        issue, accepted, visible, returned = (events[(row, k)] for k in kinds)
        if not issue < accepted < visible or returned <= accepted:
            raise ValueError('causal read/delivery/visibility/credit edges')
        if downstream_leases is None:
            if returned < visible + delay:
                raise ValueError('credit released before visibility plus captured return')
        else:
            lease = leases[row]
            if (type(lease['address']) is not int or not 0 <= lease['address'] < 2**19 or
                not isinstance(lease['owner'], str) or not lease['owner'] or
                Fraction(lease['reserved_before']) >= issue or
                Fraction(lease['released_after']) <= visible or
                returned < accepted + delay):
                raise ValueError('downstream owner/VM capacity/credit transfer not reserved')
            transfer += 1
    if leases and len({p['address'] for p in leases.values()}) != 576:
        raise ValueError('overlapping downstream VM lease')
    return {'rows': 576, 'downstream_transfers': transfer,
            'scope': 'SUPPLIED_ACCEPTED_EDGE_OWNERSHIP_JOIN_ONLY',
            'actual_provider_qualified': False, 'C_selected': False,
            'packet_ACK_is_home_visibility': False}
