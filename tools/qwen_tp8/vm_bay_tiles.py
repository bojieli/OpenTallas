#!/usr/bin/env python3
"""VM bit-plane lanes, TILE LEGALITY of the lane plan (VM4, 2026-10-13): the plan (vm_plane_lanes.py) books lane bits per
bay; this makes it integer: every lane stage gets ONE tile slot of ONE leaf kit and 8 pins of it, every bay's tile slots
are counted in whole leaves, and every lane is padded to the common relay depth on its own path.

    python3 tools/qwen_tp8/vm_bay_tiles.py LEAF_PLAN.json LANES.json OUT.json [--depth 12]

Leaves (closed kits, 17.28 x 97.2, d on one face, q on the other):
  E  ot_qfd_vm_xrelay_t  kit qfd_vm_xrelay_t   512 b, d W / q E   one stage, 64 lanes of 8 b
  W  ot_qfd_vm_xrelay_t  kit qfd_vm_xrelay_w   512 b, d E / q W   one stage, 64 lanes
  P  ot_qfd_vm_xpad2_t   kit qfd_vm_xpad2_t    480 b, d W / q E   TWO stages, 60 lanes
A lane's visit of a bay = one relay stage in an E or W tile (the face of q = the direction of its NEXT hop; a vertical
hop keeps the direction of the hop that brought it; a bay's relay tiles are ONE pool: the westward share gets kit _w
tiles in whole tiles and the remainder turns round its tile, counted as relay_uturn_passes) + its pad stages there: pairs in P tiles BEFORE the relay (the
relay drives the long hop), an odd stage as one more relay pass.  A pad pair of a westward lane enters the P tile on
its W face after a U turn round the tile: counted (pad_uturn) and steered to eastward visits by the cost.
Assignment: odd stages greedily into relay tiles with room, pairs by min-cost flow lanes -> bays of their own path with
the bay's free whole tile slots as capacity; a bay that ends over its slots lowers its capacity and the flow is solved
again.  Verdict PASS = every lane at depth D, every bay within its tile slots in whole leaves.
Output: per bay the tile list (slot, kit, lanes in pin order), per lane its chain [(bay, slot, bit0, stages)]."""
import argparse, collections, hashlib, json, math, sys
from pathlib import Path
import networkx as nx

TW, SGAP = 17.28, 4.32
CAP = {'E': 64, 'W': 64, 'P': 60}
KIT = {'E': 'qfd_vm_xrelay_t', 'W': 'qfd_vm_xrelay_w', 'P': 'qfd_vm_xpad2_t'}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('lanes'); ap.add_argument('out'); ap.add_argument('--depth', type=int, default=0)
    ap.add_argument('--rounds', type=int, default=12)
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text()); lanes = json.loads(Path(a.lanes).read_text())
    D = a.depth or lanes['relay_depth']
    bays = {b['n']: b for b in plan['x_relay_bays']}; ch = {c['n']: c for c in plan['children']}
    cx = lambda o: o['x'] + o['w'] / 2
    cy = lambda o: o['y'] + o['h'] / 2
    P = []                                  # lanes: name, src leaf, plane, via, hop directions
    for p in lanes['paths']:
        s, pl = p['name'].split('>'); via = p['via']; src = ch[s]; k = int(pl[1:]); col = ch[f'vm_xcol_{k}']
        lower = src['region'] < 4
        pts = [(cx(src), cy(src))] + [(cx(bays[v]), cy(bays[v])) for v in via] + [(col['x'] + 26.0, col['y'] if lower else col['y'] + col['h'])]
        dirs = []; last = 'E'
        for i in range(1, len(pts) - 1):   # direction of the hop that LEAVES via[i-1]
            dx = pts[i + 1][0] - pts[i][0]
            if abs(dx) > TW: last = 'E' if dx > 0 else 'W'
            else:                           # vertical hop: keep the direction of arrival
                dxi = pts[i][0] - pts[i - 1][0]
                if abs(dxi) > TW: last = 'E' if dxi > 0 else 'W'
            dirs.append(last)
        P.append(dict(name=p['name'], src=s, plane=k, lower=lower, via=via, dirs=dirs, pads=D - len(via), y_in=[round(q[1], 2) for q in pts[:-2]], y_out=[round(q[1], 2) for q in pts[2:]]))
    assert all(l['pads'] >= 0 for l in P), 'a lane is deeper than D'
    # ---- relay visits per bay and class; odd pad stages as a second relay pass where a tile has room ----
    rel = collections.defaultdict(lambda: collections.Counter())
    for l in P:
        for b, d in zip(l['via'], l['dirs']): rel[b][d] += 1
    def rtiles(b):
        return math.ceil((rel[b]['E'] + rel[b]['W']) / 64)
    odd = [l for l in P if l['pads'] % 2]
    single = {}
    for l in sorted(odd, key=lambda l: len(l['via'])):
        best = None
        for i, (b, d) in enumerate(zip(l['via'], l['dirs'])):
            room = rtiles(b) * 64 - rel[b]['E'] - rel[b]['W']                    # free lane places in the bay's relay tiles
            grow = 0 if room >= 1 else 1
            free = bays[b]['tiles'] - rtiles(b) - grow
            if free < 0: continue
            key = (grow, bool(bays[b].get('padrow')), -free, -room)
            if best is None or key < best[0]: best = (key, i)
        if best is None: single[l['name']] = None; continue
        i = best[1]; rel[l['via'][i]][l['dirs'][i]] += 1; single[l['name']] = i
    odd_unplaced = [n for n, v in single.items() if v is None]
    # ---- pad pairs: min-cost flow, capacity = whole free tile slots x 60 ----
    capP = {b: max(0, bays[b]['tiles'] - rtiles(b)) for b in bays}
    need = {l['name']: l['pads'] // 2 for l in P}
    rounds = []; assign = {}
    for rnd in range(a.rounds):
        G = nx.DiGraph(); tot = 0
        for li, l in enumerate(P):
            n = need[l['name']]
            if n <= 0: continue
            tot += n; G.add_edge('s', ('l', li), capacity=n, weight=0)
            G.add_edge(('l', li), 'u', capacity=n, weight=1000)      # unplaced pairs (reported, never hidden)
            seen = set()
            for b, d in zip(l['via'], l['dirs']):
                if b in seen or capP[b] <= 0: continue
                seen.add(b)
                G.add_edge(('l', li), ('b', b), capacity=n, weight=(0 if d == 'E' else 4) + (1 if bays[b].get('padrow') else 0))
        for b in bays:
            if ('b', b) in G: G.add_edge(('b', b), 't', capacity=capP[b] * CAP['P'], weight=0)
        G.add_edge('u', 't', capacity=tot, weight=0)
        flow = nx.max_flow_min_cost(G, 's', 't')
        assign = collections.defaultdict(dict); unplaced = flow['u'].get('t', 0) if 'u' in flow else 0; padl = collections.Counter(); uturn = 0
        for li, l in enumerate(P):
            for tgt, f in (flow.get(('l', li)) or {}).items():
                if tgt == 'u': continue
                b = tgt[1]
                if f > 0:
                    assign[l['name']][b] = f; padl[b] += f
                    if l['dirs'][l['via'].index(b)] == 'W': uturn += f
        over = [b for b in bays if rtiles(b) + math.ceil(padl[b] / CAP['P']) > bays[b]['tiles']]
        relay_over = [b for b in bays if rtiles(b) > bays[b]['tiles']]
        rounds.append(dict(round=rnd, pair_stages=2 * tot, unplaced_pairs=unplaced, bays_over=len(over), bays_over_on_relays_alone=len(relay_over), pad_uturn_pairs=uturn))
        print('round', json.dumps(rounds[-1]), file=sys.stderr, flush=True)
        if not over or set(over) <= set(relay_over): break
        for b in over: capP[b] = max(0, capP[b] - 1)
    # ---- tiles and pins: per bay, class by class, lanes in the order of their entry / exit ordinate ----
    tiles = {}; chain = collections.defaultdict(list); bay_rep = {}
    visits = collections.defaultdict(list)
    for l in P:
        for i, (b, d) in enumerate(zip(l['via'], l['dirs'])):
            visits[b].append((l, i, d))
    over_final = []; uturn_relay = 0; loopback = 0; prev = 0
    for b, vs in sorted(visits.items()):
        slot = 0; tl = []
        def pack(kind, items):
            nonlocal slot
            for t0 in range(0, len(items), CAP[kind]):
                grp = items[t0:t0 + CAP[kind]]
                tl.append(dict(slot=slot, kind=kind, kit=KIT[kind], lanes=[g[0] for g in grp])); slot += 1
                for j, g in enumerate(grp): g[1].append((slot - 1, 8 * j))
        # per visit: pad pairs (in P tiles, in order), then relay pass(es)
        ent = []
        for l, i, d in vs:
            npair = assign.get(l['name'], {}).get(b, 0); nrel = 1 + (1 if single.get(l['name']) == i else 0)
            ent.append(dict(l=l, i=i, d=d, npair=npair, nrel=nrel, key=(l['y_in'][i], l['y_out'][i], l['name']), seq=[]))
        # pad pairs: P tiles (d W / q E), pass by pass; relay passes: one pool, W-facing tiles for the westward share
        # (a lane's k-th pair goes to the next P tile of the bay, W to E; when the bay has fewer P tiles than the lane
        # has pairs there, the lane comes back round to the first one: pad_loopbacks)
        q = sum(e['npair'] for e in ent); npt = math.ceil(q / CAP['P']); load = [[] for _ in range(npt)]
        for e in sorted(ent, key=lambda e: (-e['npair'], e['key'])):
            t = min(range(npt), key=lambda k: len(load[k])) if npt else 0
            for k in range(e['npair']):
                for off in range(npt):
                    tt = (t + k + off) % npt
                    if len(load[tt]) < CAP['P']: break
                load[tt].append(e)
                if k > 0 and tt <= prev: loopback += 1
                prev = tt
        for k in range(npt):
            tl.append(dict(slot=slot, kind='P', kit=KIT['P'], lanes=[e['l']['name'] for e in load[k]]))
            for j, e in enumerate(load[k]): e['seq'].append((slot, 8 * j))
            slot += 1
        passes = [(e, k) for e in sorted(ent, key=lambda e: (e['d'], e['key'])) for k in range(e['nrel'])]
        nt = math.ceil(len(passes) / 64); nw = sum(1 for e, _ in passes if e['d'] == 'W'); ntw = min(nt, int(round(nw / 64.0)))
        wl = [q for q in passes if q[0]['d'] == 'W']; el = [q for q in passes if q[0]['d'] == 'E']
        wt = wl[:64 * ntw]; rest_w = wl[64 * ntw:]; room_w = 64 * ntw - len(wt)
        et = el[:len(el) - min(room_w, len(el))] if room_w else el; ew = el[len(et):]
        uturn_relay += len(rest_w) + len(ew)
        pack('E', [(e['l']['name'], e['seq']) for e, _ in et + rest_w])
        pack('W', [(e['l']['name'], e['seq']) for e, _ in wt + ew])
        for e in ent:
            st = 0; segs = []
            for k, (s_, bit) in enumerate(e['seq']):
                kind = tl[s_]['kind']; n = 2 if kind == 'P' else 1; st += n
                segs.append(dict(slot=s_, kind=kind, bit0=bit, stages=n))
            chain[e['l']['name']].append(dict(bay=b, visit=e['i'], dir=e['d'], stages=st, tiles=segs))
        tiles[b] = tl; n = len(tl)
        bay_rep[b] = dict(slots=bays[b]['tiles'], tiles=n, E=sum(1 for t in tl if t['kind'] == 'E'), W=sum(1 for t in tl if t['kind'] == 'W'), P=sum(1 for t in tl if t['kind'] == 'P'),
                          lane_visits=len(vs), stage_bits=sum(8 * c['stages'] for l, i, d in vs for c in chain[l['name']] if c['bay'] == b and c['visit'] == i))
        if n > bays[b]['tiles']: over_final.append(b)
    short = []
    for l in P:
        got = sum(c['stages'] for c in chain[l['name']])
        if got != D: short.append((l['name'], got))
    kinds = collections.Counter(t['kind'] for tl in tiles.values() for t in tl)
    ok = not short and not over_final and not odd_unplaced
    fills = sorted(((v['tiles'] / v['slots'], b) for b, v in bay_rep.items()), reverse=True)
    rep = dict(status='VM_BAY_TILES_V1', owner='claude/qwen-tp8-vm-phys VM4', verdict='PASS_TILE_LEVEL' if ok else 'REJECT', depth=D,
               inputs={str(v): hashlib.sha256(Path(v).read_bytes()).hexdigest() for v in (a.plan, a.lanes, __file__)},
               lanes=len(P), lanes_at_depth=len(P) - len(short), lanes_short=short[:40], odd_stage_lanes=len(odd), odd_unplaced=odd_unplaced[:40],
               flow_rounds=rounds, bays=len(bays), bays_used=len(tiles), bays_over_slots=over_final,
               tile_slots=sum(b['tiles'] for b in bays.values()), tiles=dict(total=sum(kinds.values()), xrelay_t=kinds['E'], xrelay_w=kinds['W'], xpad2_t=kinds['P']),
               flops=kinds['E'] * 513 + kinds['W'] * 513 + kinds['P'] * 961, relay_uturn_passes=uturn_relay, pad_loopbacks=loopback, pad_uturn_pairs=rounds[-1]['pad_uturn_pairs'] if rounds else 0,
               fullest=[dict(bay=b, tiles=bay_rep[b]['tiles'], slots=bay_rep[b]['slots']) for _, b in fills[:12]],
               full_bays=sum(1 for f, _ in fills if f >= 1.0), pad_row=dict(tiles=sum(v['tiles'] for b, v in bay_rep.items() if bays[b].get('padrow')), slots=sum(b['tiles'] for b in bays.values() if b.get('padrow'))),
               rule='a lane visit = pad pairs in ot_qfd_vm_xpad2_t (60 lanes, 2 stages) then one relay stage in ot_qfd_vm_xrelay_t (64 lanes; kit _w when the next hop goes west); an odd pad stage = one more relay pass',
               bay_report=bay_rep, bay_tiles=tiles, lane_chain={name: sorted(cs, key=lambda c: c['visit']) for name, cs in chain.items()})
    Path(a.out).write_text(json.dumps(rep, separators=(',', ':')) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k not in ('bay_report', 'bay_tiles', 'lane_chain', 'inputs')}, indent=1)[:3000])


if __name__ == '__main__':
    main()
