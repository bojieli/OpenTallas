#!/usr/bin/env python3
"""Conservative cut screen from exact child LEF OBS; no GRT closure claim."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
from child_lint import parse_lef


def merged_length(intervals):
    total = 0.0
    end = None
    for a, b in sorted(intervals):
        if end is None or a > end:
            total += b - a
            end = b
        elif b > end:
            total += b - end
            end = b
    return total


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tech', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    tech = a.tech.read_text()
    layers = {}
    for name in ('M3', 'M4', 'M5', 'M6', 'M7'):
        body = re.search(r'(?m)^LAYER ' + name + r'\s*$(.*?)^END ' + name + r'\s*$', tech, re.S).group(1)
        layers[name] = {'pitch_um': float(re.search(r'PITCH\s+([\d.]+)', body).group(1)),
                        'direction': re.search(r'DIRECTION\s+(\w+)', body).group(1),
                        'width_um': float(re.search(r'WIDTH\s+([\d.]+)', body).group(1))}
    spec_path = ROOT / 'physical/ref_tile/qw_h3_ref/spec.json'
    spec = json.loads(spec_path.read_text())
    rects = []
    sources = {}
    for child in spec['children'] + spec['macros']:
        path = next((ROOT / child['view']).glob('*.lef'))
        sources[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        lef = parse_lef(path.read_text())
        x, y = child['at']
        # Signal pin metal also occupies tracks; include all PG pin stripes.
        shapes = lef['obs'] + [r for pin in lef['pins'].values() for r in pin['rects']]
        rects.extend((ly, x+x0, y+y0, x+x1, y+y1) for ly,x0,y0,x1,y1 in shapes)
    cuts = [('read_center', 'x', 280, 0, 691.2, 4768),
            ('center_write', 'x', 570, 0, 691.2, 1728),
            ('whole_midrow', 'y', 345.6, 0, 777.6, 6303),
            # RTL dec3 seam: dxl xs/xb to dbq = 2048, dbq byo to daq = 512,
            # plus conservatively 42 header/valid/fault/clock/reset nets.
            ('decoder_tile_width_only', 'y', 345.6, 302.4, 423.36, 2602),
            ('reserved_decoder_corridor', 'y', 345.6, 270, 570, 2602),
            # Upper bound placing all global midpoint demand in central control region.
            ('center_all_bus_upper_bound', 'y', 345.6, 270, 570, 6303)]
    results = []
    for name, axis, pos, low, high, demand in cuts:
        detail = {}
        supply = 0.0
        for ly, info in layers.items():
            if info['direction'] != ('HORIZONTAL' if axis == 'x' else 'VERTICAL'):
                continue
            blocked = []
            margin = info['width_um'] / 2
            for layer,x0,y0,x1,y1 in rects:
                if layer != ly:
                    continue
                cross0,cross1,edge0,edge1 = (x0,x1,y0,y1) if axis == 'x' else (y0,y1,x0,x1)
                if cross0-margin <= pos <= cross1+margin:
                    lo,hi = max(low,edge0-margin),min(high,edge1+margin)
                    if hi > lo:
                        blocked.append((lo,hi))
            length = merged_length(blocked)
            usable = max(0,high-low-length) / info['pitch_um'] * .5
            supply += usable
            detail[ly] = {'blocked_um':round(length,4), 'usable_tracks_after_50pct_reserve':round(usable,2)}
        ratio = demand / supply if supply else None
        results.append({'name':name,'axis':axis,'position_um':pos,'span_um':[low,high],
                        'demand_bits':demand,'layers':detail,'usable_tracks':round(supply,2),
                        'demand_supply':round(ratio,4) if ratio else None,
                        'screen': 'PASS' if ratio and ratio <= .60 else 'FAIL'})
    out = {'schema':'opentallas.quant.overlap.cut-screen.v1',
           'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'tech_sha256':hashlib.sha256(a.tech.read_bytes()).hexdigest(),
           'tech_layers':layers,'child_lef_sha256':sources,
           'spec_sha256':hashlib.sha256(spec_path.read_bytes()).hexdigest(),'cuts':results,
           'scope':'Exact transformed OBS and pin shapes; half wire-width blockage expansion; 50% remaining supply reserved for PG/access/spacing. Demand is an explicit RTL bus envelope, not extracted net demand. No placement or global-route closure claim.',
           'required_action':'Reserve decoder seam corridor x270..570 across y336.96..388.8. Tile-width-only routing fails; all-midpoint-buses central upper bound fails. Route distinct gather/result buses by region and check actual GRT demand before adoption.'}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2)+'\n')
    for row in results:
        print(row['name'],row['demand_supply'],row['screen'])


if __name__ == '__main__':
    main()
