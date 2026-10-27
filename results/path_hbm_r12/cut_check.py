#!/usr/bin/env python3
"""NUMBER-CHECK (independent re-implementation, no plan_cut import): per-sink blocked hub cut on planA2 hub types.
Model as stated in R10/R11: cut lines every 4.32 um; a net = stations sharing (launch, from point); per cut line a net
contributes the widest sink slice whose own from->to span strictly crosses the line; tracks: x-cut = (H - core
height on line)*0.75/0.048 (M4) + H*0.75/0.064 (M6); y-cut = (W - core width on line)*0.75/0.048 (M5) + W*0.75/0.064 (M7)."""
import json, sys, bisect
def prof(W, H, nets, cores):
    res = {}
    for ax in 'xy':
        L = W if ax == 'x' else H; o = H if ax == 'x' else W
        n = int((L - 1e-6) / 4.32)
        V = [4.32 * (i + 1) for i in range(n) if 4.32 * (i + 1) < L - 1e-6]
        dem = [0.0] * len(V); face = [0.0] * len(V); blk = [0.0] * len(V)
        k = 0 if ax == 'x' else 1
        for (launch, a), sinks in nets.items():
            best = [0] * len(V)
            for p, b in sinks:
                lo, hi = min(a[k], p[k]), max(a[k], p[k])
                i0 = bisect.bisect_right(V, lo); i1 = bisect.bisect_left(V, hi)
                for i in range(i0, i1):
                    if b > best[i]: best[i] = b
            isf = str(launch or '').startswith('face')
            for i, b in enumerate(best):
                if b:
                    dem[i] += b
                    if isf: face[i] += b
        for (x0, y0, x1, y1) in cores:
            lo, hi, span = ((x0, x1, min(y1, H) - max(y0, 0)) if ax == 'x' else (y0, y1, min(x1, W) - max(x0, 0)))
            for i in range(bisect.bisect_right(V, lo), bisect.bisect_left(V, hi)):
                blk[i] += span
        best = (-1, None)
        for i, v in enumerate(V):
            tr = (o - min(blk[i], o)) * 0.75 / 0.048 + o * 0.75 / 0.064
            u = dem[i] / tr
            if u > best[0]: best = (u, dict(max_use=round(u, 3), at_um=round(v, 2), bits=int(dem[i]), face_bits=int(face[i]), tracks=int(tr)))
        best[1]['cuts_over_0p6'] = sum(1 for i in range(len(V)) if dem[i] / ((o - min(blk[i], o)) * 0.75 / 0.048 + o * 0.75 / 0.064) > 0.6 + 1e-9)
        res[ax] = best[1]
    return res
def main():
  P = json.load(open(sys.argv[1])); rep = json.load(open(sys.argv[2])); out = {}
  for tn in ('q_hub_nw', 'q_hub_ne'):
    t = P['partition_types'][tn]; W, H = t['outline_um']
    cores = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]) for h in t['hard_cores']]
    nets = {}
    for s in t['internal_stations']:
        nets.setdefault((s.get('launch'), tuple(s['from_um'])), []).append((s['to_um'], s['bits']))
    whole = prof(W, H, nets, cores)
    b = rep['hubs'][tn]['bound_um']; segs = []
    for x0, x1 in ((0.0, b), (b, W)):
        nn = {}
        for (l, a), sinks in nets.items():
            xs = [a[0]] + [p[0] for p, _ in sinks]
            if max(xs) < x0 or min(xs) > x1: continue
            cl = lambda p: (min(max(p[0], x0), x1) - x0, p[1])
            nn[(l, cl(a))] = nn.get((l, cl(a)), []) + [(cl(p), bb) for p, bb in sinks]
        cc = [(max(a, x0) - x0, y0, min(c, x1) - x0, y1) for a, y0, c, y1 in cores if c > x0 and a < x1]
        segs.append(prof(x1 - x0, H, nn, cc))
    r = rep['hubs'][tn]
    out[tn] = dict(outline=[W, H], mine_whole=whole, report_whole={a: {k: r['cut_per_sink_blocked'][a][k] for k in ('max_use', 'at_um', 'bits', 'tracks')} for a in 'xy'},
                   mine_segs=[(s['x']['max_use'], s['y']['max_use'], s['y']['at_um']) for s in segs],
                   report_segs=[(s['cut_x'], s['cut_y'], s['at_y']) for s in r['segments']])
  print(json.dumps(out, indent=1))
if __name__ == '__main__':
    main()
