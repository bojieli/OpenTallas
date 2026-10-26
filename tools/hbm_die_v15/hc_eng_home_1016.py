#!/usr/bin/env python3
"""HC engine home witness (H-DIE-V790 10-16): per-link routed length / relay stages of every HC_ENG link of a plan
(same pin + lane model as v6_eval.py, 500 um reach) and the engine-face cut (bits on the face / (face um x 14.0625
tracks per um)), plus the cut ablation table from sibling eval.json files.

    hc_eng_home_1016.py PLAN [--ablation NAME=DIR ...]   -> PLAN/hc_eng_home.json
Geometry only: the actual engine view, pins, relays, clocks and TT/FF/DRC remain open.
"""
import argparse, collections, glob, json, math
from pathlib import Path

TR = 14.0625


def links(d):
    pins = json.loads(Path(glob.glob(str(d / 'pins' / '*.pins.json'))[0]).read_text())
    lanes = json.loads((d / 'lanes.json').read_text())
    ends = collections.defaultdict(list)
    for b, v in pins['blocks'].items():
        for f, fx in v['faces'].items():
            for p in fx['pins']:
                ends[p['link']].append(dict(p, block=b, face=f))
    out = {}
    for lk, e in ends.items():
        if ':HC_ENG' not in lk or len(e) != 2:
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
        eng = a if a['block'] == 'hc_eng' else b
        out[lk] = dict(bits=a['bits'], route_um=round(L, 1), stages=max(0, math.ceil(L / 500) - 1), engine_face=eng['face'])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('plan'); ap.add_argument('--ablation', nargs='*', default=[])
    a = ap.parse_args()
    d = Path(a.plan)
    P = json.loads((d / 'compact.P.json').read_text())
    L = links(d)
    e = P['hc_eng']
    face_len = dict(W=e['h'], E=e['h'], N=e['w'], S=e['w'])
    faces = collections.defaultdict(int)
    for v in L.values():
        faces[v['engine_face']] += v['bits']
    face_cut = {f: dict(bits=b, face_um=face_len[f], utilization=round(b / (face_len[f] * TR), 4)) for f, b in faces.items()}
    abl = {}
    for s in a.ablation:
        k, p = s.split('=', 1)
        ev = json.loads((Path(p) / 'eval.json').read_text())
        abl[k] = dict(cut_lanes=ev['cut_lanes'], stages_bw=ev['stages_bw'], hc_eng_stages_bw=ev.get('per_class', {}).get('HC_ENG', {}).get('stages_bw'))
    out = dict(schema='opentallas.hbm.hc_eng_home.v1', qualification='GEOMETRY_ONLY', plan=str(d), hc_eng=e,
               collars={k: P[k] for k in ('hc_eng_tgt', 'hc_tbl_tgt') if k in P}, links=L,
               max_stages=max((v['stages'] for v in L.values()), default=0), engine_face_cut=face_cut, ablation=abl)
    (d / 'hc_eng_home.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: out[k] for k in ('max_stages', 'engine_face_cut')}))
    for k, v in sorted(L.items()):
        print(k, v)
    for k, v in abl.items():
        print(k, v)


if __name__ == '__main__':
    main()
