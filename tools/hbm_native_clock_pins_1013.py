#!/usr/bin/env python3
"""Clock-sink geometry of a native HBM die candidate, from the real LEF clock pins.

One row per (master, orientation): the clock pin(s) of the view (LEF USE CLOCK, else a
pin named clk/ck/clk_*), their layer and local RECT.  Per die quarter and per 2 x 2 mm
region: sink count and bounding box at the candidate's (track-legal) origins.  This is
the INPUT of the die clock plan (regions -> spine taps); it places no clock cell and
claims no skew.  Children without a LEF are counted as sinks at their centre, flagged.
"""
import argparse, collections, json, re
from pathlib import Path
import hbm_native_pin_track_audit_1013 as tracks
ROOT = Path(__file__).resolve().parents[1]


def clock_pins(path):
    text = path.read_text()
    out = []
    for m in re.finditer(r'\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1', text, re.S):
        name, body = m.group(1), m.group(2)
        if re.search(r'USE\s+CLOCK', body) or re.fullmatch(r'(clk|ck|clk_\w+|\w+_clk)', name):
            layer, rect = None, None
            for line in body.splitlines():
                t = line.split()
                if t[:1] == ['LAYER']:
                    layer = t[1]
                elif t[:1] == ['RECT'] and rect is None:
                    rect = [tracks.nm(v) for v in t[1:5]]
            out.append({'pin': name, 'layer': layer, 'rect_nm': rect, 'use_clock': bool(re.search(r'USE\s+CLOCK', body))})
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--region-um', type=float, default=2000.0)
    a = ap.parse_args()
    cand = json.loads(a.candidate.read_text())
    W, H = cand['die_um']
    cache, masters = {}, {}
    quarters = collections.defaultdict(lambda: {'sinks': 0, 'no_lef_sinks': 0, 'bbox_um': None})
    regions = collections.Counter()
    no_clock = collections.Counter()
    for r in cand['children']:
        w, h = r['w_um'], r['h_um']
        if r.get('view_lef'):
            if r['view_lef'] not in cache:
                cache[r['view_lef']] = clock_pins(ROOT / r['view_lef'])
            pins = cache[r['view_lef']]
            masters.setdefault(r['logical_module'] + '/' + r['orientation'], {'instances': 0, 'clock_pins': pins})['instances'] += 1
            if not pins:
                no_clock[r['logical_module']] += 1
            pts = []
            for p in pins:
                x0, y0, x1, y1 = [v / 1000 for v in p['rect_nm']]
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if r['orientation'] in ('MY', 'R180'):
                    cx = w - cx
                if r['orientation'] in ('MX', 'R180'):
                    cy = h - cy
                pts.append((r['xy_um'][0] + cx, r['xy_um'][1] + cy, False))
        else:
            pts = [(r['xy_um'][0] + w / 2, r['xy_um'][1] + h / 2, True)]
        for x, y, guessed in pts:
            q = quarters[('S' if y < H / 2 else 'N') + ('W' if x < W / 2 else 'E')]
            q['sinks'] += 1
            q['no_lef_sinks'] += guessed
            b = q['bbox_um']
            q['bbox_um'] = [x, y, x, y] if b is None else [min(b[0], x), min(b[1], y), max(b[2], x), max(b[3], y)]
            regions[(int(x // a.region_um), int(y // a.region_um))] += 1
    rec = {'schema': 'opentallas.hbm.native_clock_pins.v1', 'candidate': str(a.candidate), 'variant': cand['variant'],
           'die_um': [W, H], 'sinks': sum(q['sinks'] for q in quarters.values()),
           'sinks_without_lef_at_centre': sum(q['no_lef_sinks'] for q in quarters.values()),
           'real_children_without_clock_pin': dict(no_clock),
           'quarters': {k: dict(v, bbox_um=[round(x, 3) for x in v['bbox_um']]) for k, v in sorted(quarters.items())},
           'region_um': a.region_um, 'regions_with_sinks': len(regions), 'max_sinks_per_region': max(regions.values()),
           'regions': [{'ix': k[0], 'iy': k[1], 'sinks': v} for k, v in sorted(regions.items())],
           'masters': masters,
           'status': 'INPUT ONLY: no spine, tap, insertion delay or skew is planned or claimed here.'}
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps({k: rec[k] for k in ['sinks', 'sinks_without_lef_at_centre', 'real_children_without_clock_pin', 'quarters', 'regions_with_sinks', 'max_sinks_per_region']}))
    print({k: [(p['pin'], p['layer']) for p in v['clock_pins']] for k, v in masters.items() if v['clock_pins'] and not k.endswith(('MY', 'MX'))})
