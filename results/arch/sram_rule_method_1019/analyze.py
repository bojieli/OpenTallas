#!/usr/bin/env python3
"""Finite exact-source join classification; creates no physical views or jobs."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INPUTS = {
    'qwen': ('5666def4037d8b00a9bfccd6c3e51842d60bdace',
             'results/arch/qwen_dualclk_native_grid_1019/variant.json'),
    'sc2': ('e91e038034b5f75d65d683ae0a152dd839daaa9f',
            'results/rtl/s81_coll_wide_pitch_1019/native_grid/candidate_paths.json'),
}

def union_area(rects):
    xs = sorted({r[i] for r in rects for i in (0, 2)})
    total = 0
    for l, r in zip(xs, xs[1:]):
        spans = sorted((a[1], a[3]) for a in rects if a[0] <= l and a[2] >= r)
        end = -10**30
        for low, high in spans:
            total += (r-l)*max(0, high-max(low, end))
            end = max(end, high)
    return total

result = {'status': 'ANALYTICAL_METHOD_ONLY_NO_NATIVE_VERDICT', 'inputs': {}, 'families': {}}
for family, (rev, path) in INPUTS.items():
    raw = subprocess.check_output(['git', '-C', str(ROOT), 'show', rev+':'+path])
    data = json.loads(raw)
    paths = data['paths'] if family == 'qwen' else data
    result['inputs'][family] = {'commit': rev, 'path': path, 'sha256': hashlib.sha256(raw).hexdigest()}
    joins = []
    for p in paths:
        pads = [s for s in p['shapes'] if s['role'] == 'UNCHANGED_original_contact'] if family == 'qwen' else p['retained_pads']
        for pad in pads:
            a = pad['rect_nm']
            candidates = [s for s in p['shapes'] if s['layer'] == pad['layer'] and s is not pad
                          and min(a[2],s['rect_nm'][2]) > max(a[0],s['rect_nm'][0])
                          and min(a[3],s['rect_nm'][3]) > max(a[1],s['rect_nm'][1])]
            assert len(candidates) == 1, (family,p['pin'],pad)
            b = candidates[0]['rect_nm']
            box = [min(a[0],b[0]), min(a[1],b[1]), max(a[2],b[2]), max(a[3],b[3])]
            area = union_area([a,b])
            joins.append({'pin': p['pin'], 'pad_role': pad['role'], 'pad_nm': a, 'lead_nm': b,
                          'union_area_nm2': area, 'bbox_area_nm2': (box[2]-box[0])*(box[3]-box[1]),
                          'nonrectangle': area != (box[2]-box[0])*(box[3]-box[1]),
                          'visible_route_RECTONLY_prediction': 'marker if concave neighborhood contains routed metal; fixed-only suppressed'})
    assert all(j['nonrectangle'] for j in joins)
    result['families'][family] = {'paths': len(paths), 'joins': len(joins),
                                  'nonrectangular_joins': sum(j['nonrectangle'] for j in joins),
                                  'representatives': joins[:2], 'native_verdict': None}
result['source_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted((OUT/'source').glob('*')) if p.is_file()}
print(json.dumps(result, indent=2))
