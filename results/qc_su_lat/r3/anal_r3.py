#!/usr/bin/env python3
"""anal_r3.py KIT NICK -> KIT/r3_summary.json + one line per corner.
All-sink TT/FF (lat_<C>.tsv), boundary (face) registers from RESULTS_DIR/ot_face_flops.txt, leaf-driver output window and
macro-leaf vs register-leaf offset from trunk_<C>.txt (GRT RC, setRC_rcx).  Read-only."""
import sys, os, json, statistics as st, re
K, nick = sys.argv[1], sys.argv[2]
face = set()
ff = os.path.join(K, 'run/results/asap7', nick, 'base/ot_face_flops.txt')
if os.path.exists(ff):
    for l in open(ff):
        if l.strip(): face.add(l.split('\t')[0].replace('\\', ''))
out = {}
for c in ('TT', 'FF'):
    f = os.path.join(K, 'lat_%s.tsv' % c)
    if not os.path.exists(f): continue
    rows = [l.rstrip('\n').split('\t') for l in open(f) if l.strip()]
    a = [float(r[1]) for r in rows]
    fa = [float(r[1]) for r in rows if r[0].rsplit('/', 1)[0].replace('\\', '') in face]
    tap, mac = [], []
    tf = os.path.join(K, 'trunk_%s.txt' % c)
    if os.path.exists(tf):
        for l in open(tf):
            m = re.match(r'TRUNK (\S+)\s+(\S+)\s+\(\s*([\d.]+),\s*([\d.]+)\)\s+in\s+([\d.]+)\s+out\s+([\d.]+)\s+slew\s+([\d.]+)', l)
            if not m: continue
            if m.group(1).endswith('_tap'): tap.append((float(m.group(6)), float(m.group(7))))
            elif m.group(1).endswith('_leaf'): mac.append(float(m.group(6)))
    d = dict(n=len(a), min=round(min(a), 1), mean=round(st.mean(a), 1), max=round(max(a), 1), spread=round(max(a) - min(a), 1))
    if fa: d.update(face_n=len(fa), face_mean=round(st.mean(fa), 1), face_min=round(min(fa), 1), face_max=round(max(fa), 1))
    if tap:
        to = [t[0] for t in tap]
        d.update(leaf_n=len(tap), leaf_out_min=round(min(to), 1), leaf_out_mean=round(st.mean(to), 1), leaf_out_max=round(max(to), 1),
                 leaf_window=round(max(to) - min(to), 1), max_slew=round(max(t[1] for t in tap), 1))
    if mac and tap:
        d.update(macro_leaf_out_mean=round(st.mean(mac), 1), macro_minus_leaf=round(st.mean(mac) - st.mean(to), 1))
    out[c] = d
    print(c, json.dumps(d))
json.dump(out, open(os.path.join(K, 'r3_summary.json'), 'w'), indent=1)
