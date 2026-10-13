#!/usr/bin/env python3
"""x-rotation lane router on the VM leaf plan (claude/qwen-tp8-vm-1013, 2026-10-13).

  python3 tools/qwen_tp8/vm_plane_lanes.py NET_DUMP PLAN.json OUT.json --mode {stage,plane}

stage: the 1,536-lane demand unchanged (6 stages, shifts 8,16,32,1,2,4 banks, x 64 banks x 4 lanes of 128 b; alternate lane
       from bank (i + shift) % 64 to bank i; identity inside the bank's helper), on the parent's folded region / bank map.
       Endpoints = centroid of the bank's two ot_qfd_vm_xfifo8_t xo pin groups (real LEF pins; the helper abuts them).
plane: the same rotation re-cut along the element bit: rot1 / rot2 move whole 512-b words, so bit p of every 32-b element
       never meets another bit position.  32 plane leaves (ot_qfd_vm_xplane_t, 1,024 b = 64 banks x 16 elements, pin flop +
       rot1 + rot2 inside the leaf) replace all six stages; die demand = 32,768 b ONCE, bank -> plane leaf:
       2,048 lanes of 16 b (xfifo8 xo pin-group centroid -> plane-pair pin centroid).  No demand is dropped: every xo bit
       has exactly one lane and every rotation mux is inside a leaf.
Model (as tools/qwen_tp8/vm_regular_corridors.py, Codex): every existing it2 die bus is baseline demand (no discount, the
old VM buses included); usable tracks from results/arch/qwen_tp8_1012/cuts.py CAP_MODE v3; every hop <= 500 um and ends
in a register; a hop is an L; each leg books 128 / 16 b in the two overlapping 260-um windows of every cut interval (between consecutive node
coordinates, exact) it crosses, limit 0.60 x usable - existing.  Relays (me-enabled ot_qfd_vm_xrelay_t, 512 b) only in the plan's bays, bay
capacity enforced.  An independent 100-um cut scan of the final legs gives the reported worst window.  PLAN ONLY."""
import argparse, heapq, json, math, sys, collections, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'results/arch/qwen_tp8_1012'))
import cuts as C
LIM = 0.60

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('net'); ap.add_argument('plan'); ap.add_argument('out'); ap.add_argument('--mode', required=True)
    a = ap.parse_args(); d = json.loads(Path(a.net).read_text()); p = json.loads(Path(a.plan).read_text())
    ch = p['children']; bays = p['x_relay_bays']; pins = p['real_pins']
    old = [i for i in d['insts'] if i['n'] not in p['geometry']['removed'] and not i['m'].startswith(('qfd_rly', 'qkd_rly'))]
    C.CAP_MODE = 'v3'; C.CLUSTER = C.CLUSTER + ('UNSIZED_SU64_ACTUAL_LEAF_ENVELOPE',)
    obs = old + ch + [p['geometry']['su64_reservation']]
    blocks, cap5, clb = C.block_model(obs)
    small = [i for i in ch if i['w'] * i['h'] <= 4e4] + bays          # M5-capped leaves below the block threshold: opaque below M6
    blocks = np.concatenate((blocks, np.array([(i['x'], i['y'], i['x'] + i['w'], i['y'] + i['h']) for i in small])))
    cap5 = np.concatenate((cap5, np.ones(len(small), dtype=bool))); clb = np.concatenate((clb, np.zeros(len(small), dtype=bool)))
    base = C.Net(a.net)
    # ---- nodes: relay bays (capacity in bits) and terminals (real pin centroids) ----
    P = []; cap = []; name = []
    for b in bays: P.append((b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)); cap.append(b['tiles'] * 512); name.append(b['n'])
    NB = len(P)
    def term(pt, n): P.append((round(pt[0], 3), round(pt[1], 3))); cap.append(0); name.append(n); return len(P) - 1
    xo = pins['ot_qfd_vm_xfifo8_t']['xo']['centroid']
    xf = {(c['logical_bank'], c['bits'][0] // 256): c for c in ch if c['m'] == 'ot_qfd_vm_xfifo8_t'}
    jobs = []
    if a.mode == 'stage':
        T = {b: term(((xf[b, 0]['x'] + xf[b, 1]['x']) / 2 + xo[0], (xf[b, 0]['y'] + xf[b, 1]['y']) / 2 + xo[1]), f'bank{b}_xo') for b in range(64)}
        for s, sh in enumerate((8, 16, 32, 1, 2, 4)):
            for b in range(64):
                for l in range(4): jobs.append(dict(name=f's{s}_b{b}_alt_l{l}', stage=s, A=T[(b + sh) % 64], Q=T[b], bits=128))
    else:
        pl = sorted((c for c in ch if c['m'] == 'ot_qfd_vm_xplane_t'), key=lambda c: c['plane'])
        S = {k: term((c['x'] + xo[0], c['y'] + xo[1]), c['n'] + '.xo') for k, c in xf.items()}
        K = {}
        for q in range(16):
            for top in (0, 1):   # planned pins: banks of the bottom region row on the S face, top row on the N face
                # PHYS 2026-10-13: the kit has ALL d pins on the N face (q on S), so both region rows land on N
                K[q, top] = term((pl[2 * q + 1]['x'] - 2.16, pl[2 * q]['y'] + pl[2 * q]['h']), f'xplane{2*q}_{2*q+1}.N')
        row = {c['logical_bank']: c['region'] // 4 for c in ch if c['m'] == 'ot_qfd_vm_bank_t'}
        for (b, h), s in S.items():
            for q in range(16): jobs.append(dict(name=f'b{b}_h{h}_planes{2*q}_{2*q+1}', stage=0, A=s, Q=K[q, row[b]], bits=16))
    P = np.round(np.array(P), 3); N = len(P)
    # ---- per-stage wire audit (PHYS 2026-10-13).  A stage = launch register pin -> capture register pin.  Estimated pin-to-pin
    # length = centre-to-centre L1 + an end allowance: xfifo8 xo terminal: half its N face (a lane's 16 pins = 2 bit positions of
    # 8 elements, spread over the face); plane terminal: plane width + 2.16 (the lane feeds the bank's pins of BOTH planes of the
    # pair, bank-major along the face); a relay bay facing a terminal: 51 um (which of its 2 x 2 tiles, pin on the tile face).
    # bay -> bay: 0 (tiles and pin order are assignable so that the pins face each other; pin-level assignment NOT done here).
    AL = np.zeros(N); TERM_BAY = 51.0
    if a.mode == 'plane':
        xw = next(c['w'] for c in ch if c['m'] == 'ot_qfd_vm_xfifo8_t') / 2; pw = pl[0]['w'] + 2.16
        for v in S.values(): AL[v] = xw
        for v in K.values(): AL[v] = pw
    def est(u, v, d):
        return float(d) + float(AL[u]) + float(AL[v]) + (TERM_BAY if (u >= NB) != (v >= NB) else 0.0)
    # ---- cut bookkeeping ----
    ccache = {}; used = collections.defaultdict(int)
    # Demand along a cut axis only changes at a node coordinate, so one booking line per interval between consecutive
    # node coordinates is exact; its room is 0.60 x the fewest usable tracks - the most existing bits over samples every 12.5 um inside the interval.
    AX = {'x': sorted({float(v) for v in P[:, 0]}), 'y': sorted({float(v) for v in P[:, 1]})}
    IX = {ax: {v: k for k, v in enumerate(vs)} for ax, vs in AX.items()}
    def capof(key):
        if key not in ccache:
            ax, k, w = key; lo, hi = AX[ax][k], AX[ax][k + 1]; bounds = np.array([w, w + 260.0])
            qs = [(lo + hi) / 2] + [float(v) for v in np.arange(math.ceil(lo / 12.5) * 12.5, hi, 12.5) if lo < v < hi]
            # fewest usable tracks and most existing bits anywhere in the interval (existing chains start and end inside it)
            ccache[key] = max(0.0, LIM * min(C.usable(ax, q, bounds, blocks, cap5, clb)[0][0] for q in qs) - max(base.cut(ax, q, bounds)[0][0] for q in qs))
        return ccache[key]
    def legkeys(ax, lo, hi, other):
        lo, hi = min(lo, hi), max(lo, hi)
        if hi - lo < 1e-6: return []
        st = math.floor(other / 130) * 130
        return [(ax, k, w) for k in range(IX[ax][float(lo)], IX[ax][float(hi)]) for w in (st - 130.0, float(st))]
    def lkeys(u, v, hfirst):
        (x1, y1), (x2, y2) = P[u], P[v]
        return legkeys('x', x1, x2, y1 if hfirst else y2) + legkeys('y', y1, y2, x2 if hfirst else x1)
    E = collections.defaultdict(list)
    for u in range(N):
        dist = np.abs(P[:, 0] - P[u, 0]) + np.abs(P[:, 1] - P[u, 1])
        for v in np.nonzero((dist <= 500.0) & (dist > 0))[0]:
            if est(u, int(v), float(dist[v])) <= 500.0: E[u].append((int(v), float(dist[v]), lkeys(u, int(v), True), lkeys(u, int(v), False)))
    nused = collections.defaultdict(int)
    def rem(keys): return min((capof(k) - used[k] for k in keys), default=float('inf'))
    def route(s, g, bits):
        h = lambda n: (abs(P[n, 0] - P[g, 0]) + abs(P[n, 1] - P[g, 1])) / 500.0 * 1.6
        heap = [(h(s), 0.0, s)]; dist = {s: 0.0}; prev = {}; done = set()
        while heap:
            _, c, u = heapq.heappop(heap)
            if u in done: continue
            if u == g:
                path = []
                while u in prev: path.append(prev[u]); u = prev[u][0]
                return path[::-1]
            done.add(u)
            for v, ln, kh, kv in E[u]:
                if v in done or (v != g and (v >= NB or nused[v] + bits > cap[v])): continue
                rh, rv = rem(kh), rem(kv); r, hf = (rh, True) if rh >= rv else (rv, False)
                if r < bits: continue
                alt = c + 1.0 + ln / 500.0 + 4.0 * bits / (r + 1.0)
                if alt < dist.get(v, float('inf')): dist[v] = alt; prev[v] = (u, v, hf); heapq.heappush(heap, (alt + h(v), alt, v))
        return None
    jobs.sort(key=lambda j: -(abs(P[j['A'], 0] - P[j['Q'], 0]) + abs(P[j['A'], 1] - P[j['Q'], 1])))
    done = []; fail = []; legs = []
    for j in jobs:
        path = route(j['A'], j['Q'], j['bits'])
        if path is not None:   # a path may cross one window twice: re-check its own total before booking
            dem = collections.Counter()
            for u, v, hf in path:
                for k in lkeys(u, v, hf): dem[k] += j['bits']
            if any(used[k] + n > capof(k) for k, n in dem.items()): path = None
        if path is None: fail.append(j); continue
        for k, n in dem.items(): used[k] += n
        ln = 0.0; hops = []
        for u, v, hf in path:
            hops.append(round(est(u, v, float(abs(P[u, 0] - P[v, 0]) + abs(P[u, 1] - P[v, 1]))), 1))
            if v != j['Q']: nused[v] += j['bits']
            (x1, y1), (x2, y2) = P[u], P[v]; mid = (x2, y1) if hf else (x1, y2)
            legs.append((x1, y1, mid[0], mid[1], j['bits'])); legs.append((mid[0], mid[1], x2, y2, j['bits'])); ln += abs(x1 - x2) + abs(y1 - y2)
        done.append(dict(name=j['name'], stage=j['stage'], bits=j['bits'], relay_stages=len(path) - 1, route_um=round(ln, 1), stage_um=hops,
                         lower_um=round(float(abs(P[j['A'], 0] - P[j['Q'], 0]) + abs(P[j['A'], 1] - P[j['Q'], 1])), 1),
                         A=[float(v) for v in P[j['A']]], Q=[float(v) for v in P[j['Q']]], via=[name[v] for _, v, _ in path[:-1]]))
    # ---- independent fine scan of the booked legs ----
    S = np.array(legs).reshape(-1, 5); worst = []
    x0, y0 = p['slot']['origin_um']; w, h = p['slot']['size_um']
    for ax, axis, other, span, win in (('x', 0, 1, np.arange(x0 - 600, x0 + w + 700, 100.0), np.arange(math.floor((y0 - 700) / 130) * 130, y0 + h + 700, 130.0)),
                                      ('y', 1, 0, np.arange(y0 - 600, y0 + h + 700, 100.0), np.arange(math.floor((x0 - 700) / 130) * 130, x0 + w + 700, 130.0))):
        for cp in span:
            T = S[(np.minimum(S[:, axis], S[:, axis + 2]) < cp) & (cp < np.maximum(S[:, axis], S[:, axis + 2]))]
            if not len(T): continue
            for lo in win:
                bits = int(T[(T[:, other] >= lo) & (T[:, other] < lo + 260), 4].sum())
                if not bits: continue
                bounds = np.array([lo, lo + 260.0]); u = float(C.usable(ax, cp, bounds, blocks, cap5, clb)[0][0]); ex = int(base.cut(ax, cp, bounds)[0][0])
                worst.append(dict(ax=ax, pos=float(cp), win=[float(lo), float(lo + 260)], new_bits=bits, existing_bits=ex, usable=round(u, 1), util=round((ex + bits) / u, 4)))
    worst.sort(key=lambda r: -r['util'])
    import bisect
    for r in worst[:12]:   # the booking's own view of the same window (must agree with the scan)
        k = bisect.bisect_right(AX[r['ax']], r['pos']) - 1
        if 0 <= k < len(AX[r['ax']]) - 1:
            key = (r['ax'], k, r['win'][0]); r.update(booked_bits=int(used.get(key, 0)), booking_room=round(capof(key), 1), interval=[AX[r['ax']][k], AX[r['ax']][k + 1]])
    # ---- coarse separators (column / row midlines of the envelope, +-500 um detour room), demand = straight endpoints ----
    coarse = []
    xs = sorted({v[0] for v in p['slot']['region_origins'].values()}); ys = sorted({v[1] for v in p['slot']['region_origins'].values()})
    for ax, cps, lo, hi in (('x', [x - 10.8 for x in xs[1:]], y0 - 500, y0 + h + 500), ('y', [ys[1] - 100.0], x0 - 500, x0 + w + 500)):
        k = 0 if ax == 'x' else 1
        for cp in cps:
            bits = sum(j['bits'] for j in jobs if (P[j['A'], k] - cp) * (P[j['Q'], k] - cp) < 0)
            bounds = np.array([lo, hi]); u = float(C.usable(ax, cp, bounds, blocks, cap5, clb)[0][0]); ex = int(base.cut(ax, cp, bounds)[0][0])
            coarse.append(dict(ax=ax, pos=round(cp, 2), win=[round(lo, 1), round(hi, 1)], new_bits=bits, existing_bits=ex, usable=round(u), util=round((ex + bits) / u, 4)))
    sat = collections.Counter(); satl = []
    for k, n in used.items():
        if capof(k) - n < 128 and n: sat[k[0], int(k[2])] += 1; satl.append(k)
    saturated = [dict(ax=ax, window_lo=w, cut_intervals=n, at=sorted(round(AX[ax][k[1]]) for k in satl if k[0] == ax and int(k[2]) == w)[:40]) for (ax, w), n in sat.most_common(14)]
    zero = sum(1 for k in ccache if ccache[k] < 16)
    depth = {s: max((v['relay_stages'] for v in done if v['stage'] == s), default=0) for s in sorted({j['stage'] for j in jobs})}
    pad = sum(v['bits'] * (depth[v['stage']] - v['relay_stages']) for v in done)
    relay_bits = sum(nused.values()); spare = sum(cap[:NB]) - relay_bits
    bayload = sorted(((nused[v], cap[v], name[v]) for v in range(NB) if nused[v]), reverse=True)
    if a.mode == 'stage':
        # the bank's helper: six stage registers of 512 b + selects, and the equalisation of its four lanes
        helper = dict(leaf='rotation helper per bank (NEW, unsized)', sinks_per_root=6 * 512 + 6 * 16, note='plus the lane relays in ot_qfd_vm_xrelay_t leaves (528 sinks per root)')
    else:
        helper = dict(leaf='ot_qfd_vm_xplane_t', sinks_per_root=p['clock_roots']['ot_qfd_vm_xplane_t']['sinks_per_root'], note='lane relays in ot_qfd_vm_xrelay_t leaves (%d sinks per root)' % p['clock_roots']['ot_qfd_vm_xrelay_t']['sinks_per_root'])
    ok = not fail and (not worst or worst[0]['util'] <= LIM) and pad <= spare and max(c['util'] for c in coarse) <= LIM
    allst = [h for v in done for h in v.get('stage_um', [])]
    stage_audit = dict(rule='every stage (register pin -> wire -> register pin) <= 500 um, estimated pin to pin (see AL / TERM_BAY in the tool)',
                       stages=len(allst), max_um=max(allst, default=0), over_500=int(sum(h > 500 for h in allst)), over_450=int(sum(h > 450 for h in allst)),
                       allowance_um=dict(xfifo8_xo=float(AL[NB]) if N > NB else 0, plane=float(AL[-1]) if N > NB else 0, bay_facing_terminal=TERM_BAY, bay_to_bay=0.0),
                       not_proven='bay-to-bay stages assume the pin-level assignment (tile of the bay, pin order) that makes the pins face each other')
    ok = ok and stage_audit['over_500'] == 0
    rep = dict(status='PLAN_REAL_SIZES', owner='claude/qwen-tp8-vm-phys', mode=a.mode, stage_audit=stage_audit,
        inputs={str(v): hashlib.sha256(Path(v).read_bytes()).hexdigest() for v in (a.net, a.plan, __file__)},
        verdict='PASS_PLAN_LEVEL' if ok else 'REJECT', limit=LIM, lanes_requested=len(jobs), lanes_routed=len(done), lanes_failed=len(fail),
        bits_requested=sum(j['bits'] for j in jobs), bits_routed=sum(v['bits'] for v in done),
        coarse_cuts=coarse, fine_worst=worst[:12], relay_depth_per_stage=depth,
        added_x_latency_engine_edges=(sum(depth.values()) + 6 if a.mode == 'stage' else depth[0] + 1),
        latency_note=('stage: per stage, equalised lane relays + the stage register (rot1 / rot2 are 2 edges today)' if a.mode == 'stage' else
                      'plane: equalised lane relays + the plane leaf pin flop, then rot1 / rot2 unchanged (2 edges, in the leaf); the parent carries the added edges in XS / XVM (never re-priced)'),
        relay=dict(leaf='ot_qfd_vm_xrelay_t (512 b, me-enabled)', routed_relay_bits=relay_bits, equalisation_pad_bits=pad, bay_capacity_bits=sum(cap[:NB]),
                   spare_bits_after_routing=spare, pad_fits=pad <= spare, tiles_routed=sum(math.ceil(n / 512) for n in nused.values()),
                   fullest_bays=[dict(bits=n, capacity=c, bay=b) for n, c, b in bayload[:6]]),
        max_helper_root=helper, failed_sample=[dict(name=j['name'], A=[float(v) for v in P[j['A']]], Q=[float(v) for v in P[j['Q']]]) for j in fail[:12]],
        saturated_windows=saturated, cut_bins_without_room=zero, failed_by_sink=dict(collections.Counter(name[j['Q']] for j in fail).most_common(40)),
        failed_by_stage=dict(collections.Counter(j['stage'] for j in fail)),
        route_um=dict(total_bit_mm=round(sum(v['bits'] * v['route_um'] for v in done) / 1e3), max=max((v['route_um'] for v in done), default=0),
                      max_detour=max((round(v['route_um'] - v['lower_um'], 1) for v in done), default=0)),
        not_covered=['clock / PDN', 'x output side (rot2 -> bv -> line -> x_q): plane-separable, stays with the plane leaves; not routed here',
                     'write / address / SU / row-read die buses to the regions', 'pin-level legality of relay leaves inside a bay'],
        paths=done)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('mode', 'verdict', 'lanes_requested', 'lanes_routed', 'lanes_failed', 'bits_requested', 'bits_routed', 'relay_depth_per_stage',
                                          'added_x_latency_engine_edges', 'failed_by_stage', 'route_um')}))
    print('stage_audit', json.dumps(stage_audit)); print('coarse', json.dumps(coarse)); print('fine', json.dumps(worst[:3])); print('relay', json.dumps(rep['relay'])[:400]); print('sat', json.dumps(saturated)[:1500], zero); print('fsink', json.dumps(rep['failed_by_sink'])[:900])

if __name__ == '__main__': main()
