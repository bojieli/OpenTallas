#!/usr/bin/env python3
"""CLOCK-KV-R7 (12.4a b exception, 12.8e): signed continuous mesh = CPPR common point 'm'.
Writes a COPY of the AOCV-augmented tap_arrivals_<C>.json (aocv/aug.py output) in which every mesh-fed tap's clock is
split at its mesh load point (array stub input / band-tree root input, routed mesh transient mesh_<C>.json):
  late/early := M0 + (tap late/early - mesh-load late/early)      M0 = median mesh-load LATE arrival (one value for
  both: the late/early split above the common point is removed by CPPR)
cppr_node = 'm' for every tap (one continuous mesh), node 'm' stages = stages to the mesh driver output, so the
CLK-AOCV table charges only the below-mesh branch (stub / band tree); the signed mesh skew U (worst simulated tap skew,
declared uncertainty) is added per pair by die_sta_related_r7.py (--mesh-unc).  Nominal mesh skew is inside U (the
transformed arrivals carry none), so it is not double counted.
--band-upstream TT=g,FF=g (variant, item 3): band taps fed from an upstream tree node instead of the mesh: their
arrivals are the ABSOLUTE ones minus g and their cppr node is 'h' (they no longer share the mesh).
usage: mesh_cppr.py BUILD_DIR AUG_DIR OUT_DIR [--band-upstream TT=g,FF=g]"""
import json, sys, statistics as st, shutil
b, aug, out = sys.argv[1:4]
up = {}
if '--band-upstream' in sys.argv:
    up = {k: float(v) for k, v in (x.split('=') for x in sys.argv[sys.argv.index('--band-upstream') + 1].split(','))}
import os
os.makedirs(out, exist_ok=True)
M = json.load(open(b + '/mesh.json'))
load = {t['port']: (t.get('mesh_in') or t['stub']) for t in M['taps']}
band = {t['port'] for t in M['taps'] if t.get('mesh_in')}
for f in ('mesh.json', 'nets.json', 'place.json'):
    shutil.copy(f'{b}/{f}', f'{out}/{f}')
for C in ('TT', 'FF'):
    A = json.load(open(f'{aug}/tap_arrivals_{C}.json'))
    S = json.load(open(f'{b}/mesh_{C}.json'))['stubs']
    m0l, m0e = st.median(v['late'] for v in S.values()), st.median(v['early'] for v in S.values())
    # stages to mesh = stages of the mesh driver output = min stub-tap stages - 1 (aug.py: dst_ + chain below driver)
    smesh = min(r['stages_from_root'] for r in A['taps'] if r['port'] not in band) - 1
    for r in A['taps']:
        p = r['port']
        if p in band and C in up:
            r['late_ps'] -= up[C]; r['early_ps'] -= up[C]; r['cppr_node'] = 'h'
            r['band_feed'] = f'upstream tree node, absolute arrival - {up[C]} ps (prediction)'
            continue
        s = S[load[p]]
        r['abs_late_ps'], r['abs_early_ps'] = r['late_ps'], r['early_ps']
        # one common point: the same M0 for late and early (CPPR removes the late/early split above the mesh)
        r['late_ps'] = m0l + (r['late_ps'] - s['late']); r['early_ps'] = m0l + (r['early_ps'] - s['early'])
        r['cppr_node'] = 'm'; r['mesh_load'] = load[p]
    A['node_stages']['m'] = smesh; A['node_xy_um']['m'] = None
    A['spine_late']['m'], A['spine_early']['m'] = m0l, m0l
    A['cppr_node_range_ps'] = {'h': A['cppr_node_range_ps'].get('h', 0.0), 'm': 0.0}
    A['mesh_common_note'] = __doc__.split('\n')[0] + (f' ; band upstream {up}' if up else '')
    json.dump(A, open(f'{out}/tap_arrivals_{C}.json', 'w'))
    bl = [r['late_ps'] - m0l for r in A['taps'] if r['cppr_node'] == 'm']
    print(C, 'M0', round(m0l, 1), round(m0e, 1), 'mesh stages', smesh, 'below-mesh late min/max', round(min(bl), 1), round(max(bl), 1))
