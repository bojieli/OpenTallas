#!/usr/bin/env python3
"""Pack every mapped START cell beside its emitted clock node, before GRT.

Map per-stage modules before flattening so every actual cell retains its
u_st_<id> owner. Uses actual RVT LEF widths, the plan SiteMap and all physical
clock cells, rather than the emitter's flop-only row-area estimate.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/die_plan'))
import schema as S
import die_trial as D
import start_stage_emit as E


def lef_sizes(text):
    out = {}
    for m in re.finditer(r'\bMACRO\s+(\S+)(.*?)(?=\bEND\s+\1\b)', text, re.S):
        size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;', m[2])
        if size:
            out[m[1]] = tuple(map(float, size.groups()))
    return out


def pack(plan, stages, mapped, top, ctree_v, ctree_tcl, sizes):
    cells, xy = E.ctree_cells(ctree_v, ctree_tcl)
    occupied = E.Rows()
    for name, (master, _, _) in cells.items():
        w, h = sizes[master]
        if h > E.ROW_UM + 1e-6:
            raise ValueError('multi-row clock cell requires a real row occupancy extension')
        x, y = xy[name]
        occupied.add(x, x+w, y)
    by_id = {s['id']: s for s in stages['stages']}
    groups = defaultdict(dict)
    for n, c in mapped['modules'][top]['cells'].items():
        owner = re.match(r'u_st_([^./]+)[./]', n)
        if not owner or owner[1] not in by_id:
            raise ValueError(f'cell lacks preserved actual START stage owner: {n}')
        if c['type'] not in sizes or sizes[c['type']][1] > E.ROW_UM+1e-6:
            raise ValueError(f'unknown/multi-row START master {c["type"]}')
        groups[owner[1]][n] = c
    if set(groups) != set(by_id):
        raise ValueError('actual mapped stage inventory differs from emitted stages')
    result, rows = {}, {}
    site = D.SiteMap(plan)
    W, H = plan.die['outline_um']
    for owner in sorted(groups):
        group, s = groups[owner], by_id[owner]
        width = sum(sizes[c['type']][0] for c in group.values())
        # The existing stage placer reserves a whole legal row segment in units
        # of FF width; it never substitutes this bound for actual cell count.
        rect = E.place_stage(s['node_xy_um'], math.ceil(width/E.FLOP_W_UM), occupied, site, W, H)
        x, y = rect[:2]
        # Check the complete strip, including thin interior obstructions.
        if not all(site.legal((min(rect[2], rect[0]+j*.054), yy))
                   for j in range(math.ceil((rect[2]-rect[0])/.054)+1) for yy in (y, y+E.ROW_UM)):
            raise ValueError(f'stage row crosses a plan exclusion: {owner}')
        occupied.add(rect[0], rect[2], y)
        ff = 0
        for n, c in sorted(group.items(), key=lambda q: (not q[1]['type'].startswith(('DFF','SDFF')), q[0])):
            w, h = sizes[c['type']]
            result[n] = dict(cell=c['type'], stage=owner, xy_um=[round(x,3), round(y,3)],
                             rect_um=[round(x,3), round(y,3),round(x+w,3),round(y+h,3)],orient='R0')
            x += w
            ff += c['type'].startswith(('DFF','SDFF'))
        if ff != s['flops']:
            raise ValueError(f'actual stage {owner} has {ff} FFs; expected {s["flops"]}')
        rows[owner] = dict(rect_um=rect, actual_cells=len(group), actual_flops=ff, actual_width_um=width)
    return dict(cells=result, stages=rows, scope='prebuild exact mapped START cell sites, not routed evidence',
                counts=dict(cells=len(result), stages=len(rows), flops=sum(s['actual_flops'] for s in rows.values())))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','stages','mapped','top','ctree','lef','out'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args()
    raw=S.load(a.plan)
    r=pack(S.Plan(raw,Path(a.plan)),json.loads(Path(a.stages).read_text()),json.loads(Path(a.mapped).read_text()),
           a.top,(Path(a.ctree)/'ctree.v').read_text(),(Path(a.ctree)/'ctree.tcl').read_text(),lef_sizes(Path(a.lef).read_text()))
    out=Path(a.out)
    if out.exists():raise ValueError('preserve existing physical START placement')
    out.write_text(json.dumps(r,indent=1))
    print(json.dumps(r['counts']))


if __name__=='__main__':main()
