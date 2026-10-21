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


def profile_requests(model, port_widths=None):
    """Endpoint requests for a final-pin exporter, never ages from the plan.

    Every fork destination is included. External relay/landing ages must be
    measured per bit; internal root/player/observer stages are priced separately.
    """
    def relevant(inst, port):
        return (inst.startswith('kvs_hroot_') or
                (inst == 'kvs_ctl' and port.startswith('o_hroot_')) or
                (inst.startswith('kvpc_') and port in ('o_prev', 'o_next')) or
                (inst.startswith('slg_') and port in ('o_dn', 'o_ctl')))
    out = []
    for bid, ep in sorted(model['bus_src'].items()):
        if len(ep) != 4 or not relevant(ep[0], ep[1]):
            continue
        destinations = {tuple(ep[2:])}
        destinations.update(tuple(x) for x in model.get('dsts', {}).get(bid, []))
        destinations.update(tuple(x) for x in model.get('forks', {}).get(bid, []))
        for dst in sorted(destinations):
            width = None if port_widths is None else port_widths.get('.'.join(ep[:2]))
            if port_widths is not None and (type(width) is not int or width <= 0 or
                                           width != port_widths.get('.'.join(dst))):
                raise ValueError('missing or unequal physical endpoint width')
            out.append(dict(id=':'.join((bid, *dst)), bid=bid,
                            src=ep[:2], dst=list(dst), expected_width=width, coverage='every functional bit',
                            basis='final-pin external age; excludes both endpoint internal stages'))
    if not all(any(r['src'] == [f'kvs_hroot_{st}', port] for r in out)
               for st in STACKS for port in ('o_pc', 'o_ctl', 'o_emb', 'o_ch0')):
        raise ValueError('missing full four-root path inventory')
    return out


def validate_profiles(requests, profiles, identity):
    """Validate complete exported profiles, without treating this as qualification.

    Equal ages on every bit of a bundle are required; clocks with phase-varying
    landed latency need their full phase profile resolved by the exporter first.
    """
    for field in ('candidate_sha256', 'die_v_sha256', 'strict_bind_sha256',
                  'root_rtl_sha256', 'relay_table_sha256'):
        v = identity.get(field, '')
        if len(v) != 64 or any(c not in '0123456789abcdef' for c in v):
            raise ValueError('missing source-bound identity: ' + field)
    want = {r['id']: r for r in requests}
    got = {}
    for p in profiles:
        key = p['id']
        if key not in want or key in got:
            raise ValueError('duplicate/unknown final-pin profile')
        if p['src'] != want[key]['src'] or p['dst'] != want[key]['dst']:
            raise ValueError('final-pin endpoint identity mismatch')
        n = p['width']
        if type(want[key].get('expected_width')) is not int or n != want[key]['expected_width']:
            raise ValueError('missing rendered-port width or masked functional bits')
        bits = p['bits']
        if type(n) is not int or n <= 0 or set(bits) != {str(b) for b in range(n)}:
            raise ValueError('missing functional bit profile')
        ages = list(bits.values())
        if any(type(a) is not int or a < 0 for a in ages) or len(set(ages)) != 1:
            raise ValueError('unresolved/torn final-pin age profile')
        got[key] = ages[0]
    if got.keys() != want.keys():
        raise ValueError('missing final-pin endpoint profile')
    return got
