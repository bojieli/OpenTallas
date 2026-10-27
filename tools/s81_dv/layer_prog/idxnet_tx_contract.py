"""Admission contract for the existing native TX score store, without choosing a new memory.

The native macro address is global_position//16 modulo D; its lane is position%16.
Each range must cover positions a concrete producer may actually write in this phase.
Dates are actual score-macro port edges, including input/write/read landing stages.
Rank-root and second-round pair forwarding need their own ranges and bookings.
"""


def score_store_contract(ranges, *, depth, capture_end, lookup_begin, lookup_end, next_capture_begin):
    if type(depth) is not int or depth <= 0 or depth & (depth-1):
        raise ValueError('native TX depth must be an explicit positive power of two')
    dates = (capture_end, lookup_begin, lookup_end, next_capture_begin)
    if any(type(t) is not int or t < 0 for t in dates):
        raise ValueError('actual macro capture/lookup/next-capture dates required')
    if not capture_end < lookup_begin <= lookup_end < next_capture_begin:
        raise ValueError('native TX capture and lookup lifetime overlaps another producer')
    if not ranges:
        raise ValueError('explicit reachable producer position ranges required')
    capacity = 16 * depth
    pieces = []
    for lo, hi in ranges:
        if type(lo) is not int or type(hi) is not int or not 0 <= lo < hi <= 1 << 20:
            raise ValueError('producer range must be a nonempty native20-bit half-open interval')
        if hi-lo > capacity:
            raise ValueError(f'native TX alias: positions {lo} and {lo+capacity} share score address {lo%capacity}')
        base = lo//capacity * capacity
        if hi <= base+capacity:
            pieces.append((lo-base, hi-base, base))
        else:
            pieces.extend(((lo-base, capacity, base), (0, hi-base-capacity, base+capacity)))
    for i, (lo, hi, base) in enumerate(pieces):
        for other_lo, other_hi, other_base in pieces[:i]:
            at = max(lo, other_lo)
            if at < min(hi, other_hi) and base != other_base:
                raise ValueError(f'native TX alias: positions {at+base} and {at+other_base} share score address {at}')
    return dict(depth=depth, score_capacity=capacity, producer_ranges=[list(r) for r in ranges],
                capture_end=capture_end, lookup_begin=lookup_begin, lookup_end=lookup_end,
                next_capture_begin=next_capture_begin, mapping='(position//16)%D, lane position%16',
                added_cycles=0, allocation_changed=False)
