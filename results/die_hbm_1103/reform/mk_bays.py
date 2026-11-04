#!/usr/bin/env python3
"""DIE-HBM-61/PLAN d44v part 2 (2): relay bays on the first FT hop of the die lanes over the 405-um hop.
ft_s0_resite.py finds no chain (k..k+3) for these slots: the input window is 450-700 um wide and S1 sits 600-950 um
from its far end behind the slot's hard cores.  A relay bay = extra station(s) at the head of the chain: bay 1 at the
input-window centre, one 4.32-um row in from the in face (every bit's pin -> bay hop <= half the window + inset), then
bays along the free L path (face strip first, then the channel) until S1 is within --limit.  Each bay is checked
outside every hard core (+4.32 halo) of the slot's type.  stations += bays (declared cycles; gen.py latency --inplace
regenerates latency.lanes; the census reads the before/after table).
    python3 mk_bays.py PLAN_DIR T/S,... [--limit 364.5]   (in place; bays_event.json)"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools' / 'die_plan'))
import schema as SC                                     # noqa: E402
from placement_obstacles import probe_blockages         # noqa: E402
d = Path(sys.argv[1]); slots = [x.split('/') for x in sys.argv[2].split(',')]
LIM = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == '--limit' else 364.5
pp = d / 'die_plan.json'; P = json.loads(pp.read_text())
G, HALO = 4.32, 4.32
sn_ = lambda v: round(round(v / G) * G, 3)
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
ev = []
for tn, sn in slots:
    t = P['partition_types'][tn]; W, H = t['outline_um']; s = next(s for s in t['ft_slots'] if s['name'] == sn)
    boxes = [(h['origin_um'][0] - HALO, h['origin_um'][1] - HALO, h['origin_um'][0] + h['outline_um'][0] + HALO,
              h['origin_um'][1] + h['outline_um'][1] + HALO) for h in t.get('hard_cores') or []]
    for b in list(SC.placed_macro_boxes(t).values()) + [(c['origin_um'][0], c['origin_um'][1], c['origin_um'][0] +
              c['outline_um'][0], c['origin_um'][1] + c['outline_um'][1]) for c in probe_blockages(t)]:
        boxes.append((b[0] - HALO, b[1] - HALO, b[2] + HALO, b[3] + HALO))   # the check.py geometry macros too
    free = lambda p: all(not (b[0] < p[0] < b[2] and b[1] < p[1] < b[3]) for b in boxes)
    w0, w1 = s['in_window_um']; f = s['in_face']
    ends = {'N': ([w0, H], [w1, H]), 'S': ([w0, 0], [w1, 0]), 'W': ([0, w0], [0, w1]), 'E': ([W, w0], [W, w1])}[f]
    inset = {'N': (0, -G), 'S': (0, G), 'W': (G, 0), 'E': (-G, 0)}[f]
    s1 = s['regs_um'][1] if len(s['regs_um']) > 1 else None
    along = 0 if f in 'NS' else 1
    step = LIM - 8.64
    lo, hi = sorted((ends[0][along], ends[1][along]))
    rng = (hi - step + 4.32, lo + step - 4.32)            # bay-1 coordinates every pin of the window reaches
    tgt = s1[along] if s1 else (lo + hi) / 2
    a1 = min(max(tgt, rng[0]), rng[1])
    c = [0.0, 0.0]; c[along] = sn_(a1); c[1 - along] = sn_(ends[0][1 - along] + inset[1 - along])

    def walk(p, q, dist, order):                          # move dist along the L path p -> q (order = axis order)
        p = list(p)
        for ax in order:
            dd = q[ax] - p[ax]; mv = max(-dist, min(dist, dd)); p[ax] = sn_(p[ax] + mv); dist -= abs(mv)
        return p

    def chain(order):
        bays, cur = [c], c
        while s1 is not None and man(cur, s1) > LIM and len(bays) < 8:
            cur = walk(cur, s1, step, order); bays.append(cur)
        return bays
    def greedy():                                         # free 4.32-grid point nearest S1 within one step, per bay
        bays, cur = [c], c
        while s1 is not None and man(cur, s1) > LIM and len(bays) < 8:
            xs = [sn_(v) for v in frange(min(cur[0], s1[0]) - step, max(cur[0], s1[0]) + step)]
            ys = [sn_(v) for v in frange(min(cur[1], s1[1]) - step, max(cur[1], s1[1]) + step)]
            pts = [[x, y] for x in xs for y in ys if 0 < x < W and 0 < y < H and man(cur, [x, y]) <= step and free([x, y])]
            if not pts:
                break
            cur = min(pts, key=lambda p: (man(p, s1), man(cur, p))); bays.append(cur)
        return bays
    frange = lambda a, b: [a + i * G for i in range(int((b - a) / G) + 1)]
    cands = [chain((along, 1 - along)), chain((1 - along, along))]  # face axis first, else the channel axis first
    bays = next((b for b in cands if all(map(free, b))), None) or greedy()
    ok = all(free(b) for b in bays)
    hops = [max(man(e, bays[0]) for e in ends)] + [man(a, b) for a, b in zip(bays, bays[1:])] + ([man(bays[-1], s1)] if s1 else [])
    old_k = s['stations']; old_hop = max(man(e, s['regs_um'][1]) for e in ends) if s1 else None
    s['regs_um'] = [s['regs_um'][0]] + [list(b) for b in bays] + [list(r) for r in s['regs_um'][1:]]
    s['stations'] = old_k + len(bays)
    s['note'] = (s.get('note') or '') + ' | DIE-HBM-61 d44v p2: %d relay bay(s) on the first hop (%.0f -> %.0f um)' % (len(bays), old_hop or 0, max(hops))
    ev.append(dict(type=tn, slot=sn, width=s.get('width'), stations=[old_k, s['stations']], bays=bays, bays_free=ok,
                   first_hop_before_um=round(old_hop or 0, 1), hops_after_um=[round(h, 1) for h in hops]))
pp.unlink(); pp.write_text(json.dumps(P, indent=1) + '\n')
(d / 'bays_event.json').write_text(json.dumps(dict(schema='opentallas.hbm_plan_event.v1', event='d44v-p2-relay-bays', limit_um=LIM, slots=ev), indent=1) + '\n')
for e in ev: print(e['type'], e['slot'], e['stations'], e['first_hop_before_um'], '->', max(e['hops_after_um']), 'free', e['bays_free'], e['bays'])
