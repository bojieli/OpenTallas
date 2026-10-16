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
