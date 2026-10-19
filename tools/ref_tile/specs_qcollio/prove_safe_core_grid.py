#!/usr/bin/env python3
"""Pre-route geometry only: immutable R0 core children, grid and raw-clock reach."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import check_macro_track_alignment as C

def main():
    spec = json.loads((ROOT/'tools/ref_tile/specs_qcollio/qfd_io_collective_safe_r0.json').read_text())
    floor = json.loads((ROOT/'physical/ref_tile/qfd_io_collective_safe_r0/floorplan.json').read_text())
    records = []
    for block in floor['blocks']:
        leaf = next((ROOT/block['view']).glob('*.lef'))
        macro = C.parse_lef(leaf.read_text())[0]
        x, y = block['x'], block['y']
        assert block['orient']=='R0'
        assert all(abs(v/43.2-round(v/43.2))<1e-8 for v in [x,y])
        tracks = C.check_placement(macro, 'R0', round(x*1000), round(y*1000))
        assert sum(layer['offtrack'] for layer in tracks['layers'].values())==0
        if block['kind']=='macro':
            source = next(m for m in spec['macros'] if m['inst']==block['inst'])
            root = source['clock_entry']['port']
        else:
            family = 'xfold' if 'g_xf' in block['inst'] else 'pfold'
            row = next(i for i in range(4) if '?'+str(i)+'?' in block['inst'])
            root = 'clk_'+family+str(row)
        pin = next(p for p in macro['pins'] if p['name']=='clk')
        rect = pin['rects'][0][1]
        px, py = x+(rect[0]+rect[2])/2000, y+(rect[1]+rect[3])/2000
        side = next(side for side, names in spec['pins'].items() if root in names)
        coordinate = sum(spec['pin_ranges'][root])/2
        rx, ry = (0,coordinate) if side=='W' else (spec['outline']['w'],coordinate)
        reach = abs(rx-px)+abs(ry-py)
        assert reach<=405
        records.append(dict(inst=block['inst'], origin_um=[x,y], orient='R0',
            lef=str(leaf.relative_to(ROOT)), lef_sha256=hashlib.sha256(leaf.read_bytes()).hexdigest(),
            tracks=tracks, root=root, side=side, root_nominal_um=[rx,ry],
            child_clock_um=[px,py], raw_clock_manhattan_um=reach))
    result = dict(schema='opentallas.safe_collective.core_grid.v1',
        verdict='PASS_GEOMETRY_ONLY', blocks=records,
        max_nominal_raw_clock_manhattan_um=max(r['raw_clock_manhattan_um'] for r in records),
        all_17_origins_on_43_2=True, all_17_orientations_R0=True,
        actual_pin_placement_route_native_clock_timing_qualification='PENDING_GATE')
    dest = ROOT/'results/rtl/qwen_coll_safe_1019/core_r0_grid_proof.json'
    dest.write_text(json.dumps(result,indent=2)+'\n')
    print(result['verdict'],len(records),result['max_nominal_raw_clock_manhattan_um'])
if __name__=='__main__':
    main()
