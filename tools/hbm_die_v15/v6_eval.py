#!/usr/bin/env python3
"""H-DIE-V6PLAN (10-16, OWNER 02:15 die may grow): evaluate one compact_plan output exactly like compact660_v5 was --
pins (tools/hbm_globalfp_pins.py rule), lane plan (band_lanes.py, SLACK), sliding-window pin cut (pin_cut.py), and
bit-weighted relay stages per link class (pin-to-pin route through the link's lane, ceil(L / 480) - 1 stages).

    v6_eval.py PLAN_DIR [--slack 1200] [--tag NAME]   (PLAN_DIR has compact.P.json + compact.graph.json)
Writes PLAN_DIR/pins/<tag>.pins.json, lanes.json, eval.json."""
import argparse, collections, json, math, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import hbm_globalfp as F  # noqa: E402
import hbm_globalfp_pins as PINS  # noqa: E402
import pin_cut  # noqa: E402
REACH = 480.0


def stages(pins, lanes):
    ends = collections.defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append(p)
    cls = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for lk, e in ends.items():
        if len(e) != 2:
            continue
        a, b = e
        p0, p1 = (a['x'], a['y']), (b['x'], b['y'])
        ln = lanes.get(lk, {})
        if 'v' in ln:
            L = abs(p0[0] - ln['v']) + abs(p1[1] - p0[1]) + abs(p1[0] - ln['v'])
        elif 'h' in ln:
            L = abs(p0[1] - ln['h']) + abs(p1[0] - p0[0]) + abs(p1[1] - ln['h'])
        else:
            L = abs(p0[0] - p1[0]) + abs(p0[1] - p1[1])
        s = max(0, math.ceil(L / REACH) - 1)
        c = cls[a['cls']]; c[0] += a['bits'] * s; c[1] += a['bits']; c[2] += a['bits'] * s
    tot_b = sum(v[1] for v in cls.values())
    out = {k: dict(bits=int(v[1]), stages_bw=round(v[0] / v[1], 2)) for k, v in sorted(cls.items(), key=lambda z: -z[1][1])}
    return round(sum(v[0] for v in cls.values()) / tot_b, 3), out, int(sum(v[2] for v in cls.values()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan'); ap.add_argument('--slack', default='1200'); ap.add_argument('--tag', default=None)
    ap.add_argument('--spread', nargs='*', default=[], help="BLOCK_PREFIX:FACES[:RESERVE_UM] - spread that face's pin segments evenly over the full face (order kept), leaving a free RESERVE_UM window at the face centre (calendar home), e.g. vmh_SW:W:159.84")
    ap.add_argument('--face', nargs='*', default=[], help="CLS:BLOCK_PREFIX:FACE - put every CLS pin of those blocks on FACE (e.g. SM_HBM:sm_:S, the SM column's PC-facing face), re-packed 1-D")
    ap.add_argument('--sm-carve', type=float, help="SM frame edge carve (W column + N row, um): N/S pin windows shift +carve (content shift), none in the carve feet")
    ap.add_argument('--lanes-mode', default=None, help="band_lanes 5th arg, e.g. 'legs' (H-DIE-V790: lane legs charged to cut windows)")
    ap.add_argument('--ref', default='results/arch/hbm_globalfp_1015/noatt/ref_sm.json')
    a = ap.parse_args()
    d = Path(a.plan); tag = a.tag or d.name
    P = json.loads((d / 'compact.P.json').read_text()); G = json.loads((d / 'compact.graph.json').read_text())
    W = max(r['x'] + r['w'] for r in P.values()) + 120.0
    met = json.loads((d / 'compact.metrics.json').read_text()); W, H = met['die_um']
    F.W_DIE, F.H_DIE = W, H
    Pg = {k: v for k, v in P.items() if k in G['nodes']}
    m = F.score(G, Pg, json.loads((ROOT / a.ref).read_text()), cut_detail=False)
    pp, faces = PINS.pins(G, Pg, m)
    if a.sm_carve:                 # H-DIE-V790 10-16: OWNER SM feedthrough carve (H-SM rp4c frame, content +carve in x)
        c, mg = a.sm_carve, 10.0
        for b, fx in pp.items():
            if not b.startswith('sm_'):
                continue
            r = Pg[b]
            for f, v in fx.items():
                flen = r['w'] if f in 'NS' else r['h']
                L = sorted(v['pins'], key=lambda q: q['offset_um'])
                lo_lim, hi_lim = (c + mg, flen) if f in "NS" else (0.0, flen - c - mg)
                cur = lo_lim
                for q in L:
                    want = q['offset_um'] + (c if f in 'NS' else 0.0)
                    q['offset_um'] = round(max(cur, want), 2); cur = q['offset_um'] + q['span_um']
                if cur > hi_lim:
                    cur = hi_lim
                    for q in reversed(L):
                        q['offset_um'] = round(min(q['offset_um'], cur - q['span_um']), 2); cur = q['offset_um']
                assert not L or L[0]['offset_um'] >= lo_lim - 1e-6, (b, f, 'carve leaves no room')
                for q in L:
                    cc = q['offset_um'] + q['span_um'] / 2
                    if f in 'NS':
                        q['x'] = round(r['x'] + cc, 1)
                    else:
                        q['y'] = round(r['y'] + cc, 1)
    for spec in a.face:            # H-DIE-V790 10-16: forced port face (SM column HBM port faces the PC-row channel)
        cls_, pre, F_ = spec.split(':')
        peerxy = {}
        for b, fx in pp.items():
            for f, v in fx.items():
                for q in v['pins']:
                    peerxy.setdefault(q['link'], []).append((b, q['x'], q['y']))
        for b in list(pp):
            if not b.startswith(pre):
                continue
            r = Pg[b]
            moved = []
            for f in list(pp[b]):
                if f == F_:
                    continue
                keep = [q for q in pp[b][f]['pins'] if q['cls'] != cls_]
                moved += [q for q in pp[b][f]['pins'] if q['cls'] == cls_]
                pp[b][f]['pins'] = keep
            if not moved:
                continue
            flen = r['w'] if F_ in 'NS' else r['h']
            tgt = pp[b].setdefault(F_, dict(face_len_um=round(flen, 1), bits=0, utilisation=0.0, pins=[]))
            for q in moved:
                o = next(((x, y) for bb, x, y in peerxy[q['link']] if bb != b), (q['x'], q['y']))
                q['_want'] = min(max((o[0] - r['x']) if F_ in 'NS' else (o[1] - r['y']), 0.0), flen)
            for q in tgt['pins']:
                q['_want'] = q['offset_um'] + q['span_um'] / 2
            L = sorted(tgt['pins'] + moved, key=lambda q: q['_want'])
            cur = 0.0
            for q in L:
                lo = max(cur, q['_want'] - q['span_um'] / 2); q['offset_um'] = round(lo, 2); cur = lo + q['span_um']
            if cur > flen:                                   # shift back inside the face
                cur = flen
                for q in reversed(L):
                    q['offset_um'] = round(min(q['offset_um'], cur - q['span_um']), 2); cur = q['offset_um']
            for q in L:
                c = q['offset_um'] + q['span_um'] / 2; q.pop('_want')
                if F_ in 'NS':
                    q['x'] = round(r['x'] + c, 1); q['y'] = round(r['y'] + (0 if F_ == 'S' else r['h']), 1)
                else:
                    q['y'] = round(r['y'] + c, 1); q['x'] = round(r['x'] + (0 if F_ == 'W' else r['w']), 1)
            tgt['pins'] = L; tgt['bits'] = sum(q['bits'] for q in L)
    for spec in a.spread:          # H-DIE-V790 10-16: hub-face pin windows over the full face height (not packed at a corner)
        pre, fs, *rv = spec.split(':')
        res = float(rv[0]) if rv else 0.0
        for b, fx in pp.items():
            if not b.startswith(pre):
                continue
            for f, v in fx.items():
                if f not in fs:
                    continue
                L = sorted(v['pins'], key=lambda q: q['offset_um']); flen = v['face_len_um']
                tot = sum(q['span_um'] for q in L); gap = max(0.0, (flen - tot - res) / (len(L) + 1)); cur = gap
                r = Pg[b]; half = len(L) // 2
                for k, q in enumerate(L):
                    if res and k == half:
                        cur += res           # reserved centre window (no pins): the calendar sits here
                    q['offset_um'] = round(cur, 2); c = cur + q['span_um'] / 2
                    if f in 'WE':
                        q['y'] = round(r['y'] + c, 1)
                    else:
                        q['x'] = round(r['x'] + c, 1)
                    cur += q['span_um'] + gap
    # non-graph blocks (carried grants) are obstacles for lanes/cut: give them an empty face set
    blocks = {b: dict(x=round(P[b]['x'], 1), y=round(P[b]['y'], 1), w=P[b]['w'], h=P[b]['h'],
                      kind=G['nodes'].get(b, {}).get('kind', 'GRANT'), orient=P[b].get('orient', 'R0'), faces=pp.get(b, {}))
              for b in P}
    doc = dict(schema='opentallas.hbm_globalfp.pins.v1', candidate=tag, die_outline_um=[W, H], pin_density_per_um=PINS.PIN_DENSITY,
               rule='one pin segment per link end on the face nearest its peer, centred at the closest-outline point, 1-D packed',
               blocks=blocks, faces_over_1=[dict(block=b, face=f, utilisation=u, bits=bits) for b, f, u, bits in faces if u > 1.0])
    (d / 'pins').mkdir(exist_ok=True)
    pf = d / 'pins' / f'{tag}.pins.json'; pf.write_text(json.dumps(doc, indent=1))
    lf = d / 'lanes.json'
    subprocess.run([sys.executable, str(ROOT / 'tools/hbm_die_v15/band_lanes.py'), str(pf), str(d / 'compact.P.json'), str(lf), a.slack] + ([a.lanes_mode] if a.lanes_mode else []),
                   check=True, stdout=subprocess.DEVNULL)
    lanes = json.loads(lf.read_text())
    cut, _ = pin_cut.run(doc, P, lanes)
    cut0, _ = pin_cut.run(doc, P, None)
    bw, per, _ = stages(doc, lanes)
    rec = dict(tag=tag, die_um=[W, H], die_mm2=round(W * H / 1e6, 2), placed_mm2=met['placed_mm2'], cut_lanes=cut,
               cut_no_lanes=cut0['worst_v']['ratio'], faces_over_1=len(doc['faces_over_1']), stages_bw=bw, per_class=per,
               relay_flops=m.get('relay_flops'), su_slice=[P['su_SW0']['w'], P['su_SW0']['h']], sm=[P['sm_SW0']['w'], P['sm_SW0']['h']],
               fits_reticle=bool(W <= 33000 and H <= 26000))
    (d / 'eval.json').write_text(json.dumps(rec, indent=1))
    print(json.dumps({k: rec[k] for k in ('tag', 'die_um', 'die_mm2', 'placed_mm2', 'cut_lanes', 'stages_bw', 'faces_over_1', 'su_slice', 'sm', 'fits_reticle')}))
    print(json.dumps({k: v['stages_bw'] for k, v in per.items()}))


if __name__ == '__main__':
    main()
