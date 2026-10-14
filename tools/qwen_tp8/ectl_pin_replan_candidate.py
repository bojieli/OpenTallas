"""Experimental pin assignment for the UN-CLOSED TP8 head parent, never enabled by default.

Align A-row/B-row/control/Q on the head input face with the real ectl leaf x
coordinates. The existing electrical multicast and edge timing are unchanged.
The granted head must implement/register these pins and close its own timing;
passing this geometric probe does not establish real source/fanout timing.
"""
from collections import defaultdict
import math


def _x_to_die(inst, local_x):
    return inst.x + (inst.w - local_x if inst.orient in ('MY', 'R180') else local_x)


def _x_from_die(inst, die_x):
    local_x = die_x - inst.x
    return inst.w - local_x if inst.orient in ('MY', 'R180') else local_x


def apply(model, masters):
    q = masters.get('qkd_rhead')
    if q is None:
        return
    record = model.setdefault('tp8b_v5', {}).setdefault('ectl_pin_replan_candidate', {})
    if 'plan' not in record:
        by = {i.name: i for i in model['insts']}
        proposals = defaultdict(list)
        for bid, cls, bits, ends in model['buses']:
            ec = [(by[n], p) for n, p in ends if by[n].master.startswith('qkd_ectl_')]
            hd = [(by[n], p) for n, p in ends if by[n].master == 'qkd_rhead' and p in ('ti_a', 'ti_b', 'ti_cl', 'ti_q', 'e', 's')]
            if len(ec) != 1 or not hd:
                continue
            source, port = ec[0]
            spec = masters[source.master].ports[port]
            assert spec[0] == 'pins' and spec[2] in 'NS', (bid, spec)
            for head, hp in hd:
                proposals[hp].append([_x_from_die(head, _x_to_die(source, x)) for x in spec[4]])
        plan = {}
        spreads = {}
        for port in ('ti_a', 'ti_b', 'ti_cl', 'ti_q', 'e', 's'):
            samples = proposals[port]
            if not samples:
                raise ValueError(f'head pin candidate: no real ectl peer for {port}')
            n = q.ports[port][1]
            assert all(len(s) == n for s in samples), port
            low = [min(s[b] for s in samples) for b in range(n)]
            high = [max(s[b] for s in samples) for b in range(n)]
            plan[port] = [round(0.012 + 0.048 * math.floor(((a + b) / 2 - 0.012) / 0.048 + 0.5 + 1e-8), 4) for a, b in zip(low, high)]
            spreads[port] = round(max(b - a for a, b in zip(low, high)), 4)
        # The legacy reset pin at x217 collides with the relocated A row window.
        # No closed head view is changed: the unclosed head parent owes this plan.
        plan['rst_n'] = [4.332]
        record.update(plan=plan, source_proposal_spread_um=spreads, extra_cycles=0, extra_flops=0,
                      clock=dict(master_spec=list(q.ports['ck']), status='unchanged from baseline; child-root timing still owed by head parent'),
                      status='candidate geometry only; no closure or adoption claimed')
    for port, positions in record['plan'].items():
        assert all(0.024 < x < q.w - 0.024 for x in positions), (port, q.w, positions)
        q.ports[port] = ('pins', len(positions), 'S', 'M5', positions, 1)
