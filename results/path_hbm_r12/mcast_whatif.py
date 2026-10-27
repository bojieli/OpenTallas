#!/usr/bin/env python3
"""WHAT-IF: add the R10 'unused' outbound bus bits (census multicast copies) back as extra sinks of the nearest allowed
core-pin net in planA2, then re-run the independent cut (cut_check.prof). Diagnostic plan arithmetic only."""
import json, sys, math, importlib.util
W, tb, a2, ub, rep = sys.argv[1:6]
sys.path.insert(0, W + '/tools/die_plan')
import hbm_r10_delta as R10
spec = importlib.util.spec_from_file_location('CC', sys.argv[6]); CC = importlib.util.module_from_spec(spec)
_argv = sys.argv; sys.argv = ['x', a2 + '/die_plan.json', rep]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(CC)
sys.argv = _argv
TB = json.load(open(tb + '/die_plan.json')); A2 = json.load(open(a2 + '/die_plan.json')); U = json.load(open(ub))
R = json.load(open(rep))
out = {}
for part, tn in (('NW_hub', 'q_hub_nw'), ('NE_hub', 'q_hub_ne')):
    t0 = TB['partition_types'][tn]; t = A2['partition_types'][tn]; Wd, H = t['outline_um']
    bi = R10.bus_intervals(A2, part, t)
    allowed = {}; bface = {}
    W0, H0 = t0['outline_um']
    for s in t0['internal_stations']:
        if s['conn'].startswith('bus:'):
            f = R10.face_of(s['to_um'], W0, H0) or R10.face_of(s['from_um'], W0, H0)
            if f: bface[s['conn'][4:]] = f
    for s in t0['internal_stations']:
        if s['conn'].startswith('bus:'):
            allowed.setdefault(s['conn'][4:], set()).add(s['capture'] if str(s['launch']).startswith('face') else s['launch'])
    face_pts = {}
    for s in t['internal_stations']:
        if s['conn'].startswith('bus:'):
            p = s['to_um'] if R10.face_of(s['to_um'], Wd, H) else s['from_um']
            face_pts.setdefault(s['conn'][4:], []).append(p)
    srcs = {}
    for s in t['internal_stations']:
        if str(s['launch']).startswith('face'):
            srcs.setdefault(s['capture'], set()).add(tuple(s['to_um']))
        else:
            srcs.setdefault(s['launch'], set()).add(tuple(s['from_um']))
    added = 0; skipped = []
    st = list(t['internal_stations'])
    for r in U[tn]['buses']:
        if r['unused'] <= 0 or not allowed.get(r['bus']):
            if r['unused'] > 0: skipped.append((r['bus'], r['dir'], r['unused']))
            continue
        if face_pts.get(r['bus']):
            fp = face_pts[r['bus']][0]
        else:
            iv = bi.get(r['bus'], {})
            f = bface.get(r['bus'])
            if f in ('N', 'S'):
                x = sum(iv['ivx']) / 2 if iv.get('ivx') else Wd / 2; fp = [x, H if f == 'N' else 0.0]
            elif f in ('W', 'E'):
                y = sum(iv['ivy']) / 2 if iv.get('ivy') else H / 2; fp = [0.0 if f == 'W' else Wd, y]
            else:
                skipped.append((r['bus'], 'noface', r['unused'])); continue
        best = None
        for l in allowed[r['bus']]:
            for p in srcs.get(l, ()):
                d = abs(p[0] - fp[0]) + abs(p[1] - fp[1])
                if best is None or d < best[0]: best = (d, l, p)
        if not best: skipped.append((r['bus'], 'nosrc', r['unused'])); continue
        st.append(dict(launch='face bus ' + r['bus'] + ' mcast', from_um=list(fp), to_um=list(best[2]), bits=r['unused'], conn='bus:' + r['bus']))
        added += r['unused']
    nets = {}
    for s in st:
        nets.setdefault((s.get('launch'), tuple(s['from_um'])), []).append((s['to_um'], s['bits']))
    cores = [(h['origin_um'][0], h['origin_um'][1], h['origin_um'][0] + h['outline_um'][0], h['origin_um'][1] + h['outline_um'][1]) for h in t['hard_cores']]
    whole = CC.prof(Wd, H, nets, cores)
    b = R['hubs'][tn]['bound_um']; segs = []
    for x0, x1 in ((0.0, b), (b, Wd)):
        nn = {}
        for (l, a), sinks in nets.items():
            xs = [a[0]] + [p[0] for p, _ in sinks]
            if max(xs) < x0 or min(xs) > x1: continue
            cl = lambda p: (min(max(p[0], x0), x1) - x0, p[1])
            nn.setdefault((l, tuple(a)), []).extend((cl(p), bb) for p, bb in sinks)
        nn2 = {}
        for (l, a), v in nn.items():
            nn2[(l, cl(a))] = v
        cc = [(max(a, x0) - x0, y0, min(c, x1) - x0, y1) for a, y0, c, y1 in cores if c > x0 and a < x1]
        segs.append(CC.prof(x1 - x0, H, nn2, cc))
    out[tn] = dict(added_bits=added, skipped=skipped, whole={k: v['max_use'] for k, v in whole.items()},
                   whole_detail=whole, segs=[(s['x']['max_use'], s['y']['max_use']) for s in segs])
print(json.dumps(out, indent=1))
