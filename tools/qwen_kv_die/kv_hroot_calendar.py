"""Static HROOT observation intervals. No run-time waiting or slot movement.

Edge convention: a producer changes AFTER last_change; N sampled stages expose
that value AFTER last_change+N. A consumer with capture+decision (two edges)
can use it at last_change+N+2. The interval must hold through the decision.
This pass checks supplied native event traces; it never fabricates deadlines.
"""
STACKS = ('WS', 'WN', 'ES', 'EN')


def observation_intervals(rows, root_edges=2):
    if root_edges != 2:
        raise ValueError('selected _hl root needs capture+launch, exactly two edges')
    required = {(st, g, phase) for st in STACKS for g in range(8)
                for phase in ('enter', 'leave')}
    seen, out = set(), []
    for r in rows:
        key = r['stack'], r['group'], r['phase']
        if key not in required or key in seen:
            raise ValueError('unknown/duplicate gather observation')
        seen.add(key)
        for k in ('last_change', 'first_use', 'hold_through', 'transport_edges'):
            if type(r[k]) is not int or r[k] < 0:
                raise ValueError(k + ': nonnegative edge required')
        # Source drain/fault fields are sampled together in the same root word.
        at_pin = r['last_change'] + root_edges + r['transport_edges']
        safe = at_pin + 2
        if r['first_use'] < safe or r['hold_through'] < r['first_use']:
            raise ValueError(f'gather observation before settled sample: {key} '
                             f'use={r["first_use"]} earliest={safe}')
        out.append(dict(**r, root_pin_after_edge=at_pin, first_safe_use_edge=safe,
                        settled_margin=r['first_use']-safe))
    if seen != required:
        raise ValueError('missing production gather observation interval')
    return out
