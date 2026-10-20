#!/usr/bin/env python3
"""Size two structural band/face successors before any layout gate."""
from collections import Counter
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import sys

sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
mods=m.parse_verilog(Path('resynth.v').read_text())
g,top=m.flatten(mods,'qkd_hr_core_order_n32');a=m.build(g,None)
areas={}
for p in Path('libs').glob('*.lib'):
    text=p.read_text()
    cells=list(re.finditer(r'cell\s*\(\s*(\w+)\s*\)\s*\{',text))
    for i,match in enumerate(cells):
        body=text[match.end():cells[i+1].start() if i+1<len(cells) else len(text)]
        area=re.search(r'\barea\s*:\s*([0-9.eE+-]+)',body)
        assert area,(p,match[1])
        areas[match[1]]=float(area[1])
count=Counter(typ for ci,(typ,_,_) in enumerate(g.cells) if a['kind'][ci]!='macro')
assert not (set(count)-areas.keys()),set(count)-areas.keys()
area=sum(n*areas[typ] for typ,n in count.items())
ports=mods[top]
face=dict(N=['ck_core','chain_f','u_rank__od','u_rank__local_marker','landed','u_rank__oa',
             'host_upstream_quiet','u_rank__dispatch_fault','u_rank__local_marker_cr',
             'u_rank__local_marker_v','u_rank__image_check','u_rank__ov','u_rank__owe',
             'u_rank__ocr','u_rank__global_prefix_v'],
          E=['hb','issued','physical_ack_n','service_faults','host_rst_n'],
          W=['chain_c','chain_a','slice_ack','chain_fault_i','hb_cr'],S=[])
assert sorted(itertools.chain.from_iterable(face.values()))==sorted(ports.ports)
width=lambda p:abs(ports.widths[p][0]-ports.widths[p][1])+1 if p in ports.widths else 1
counts={f:sum(width(p) for p in ps) for f,ps in face.items()}
result=dict(top=top,measured_synthesis_standard_area_um2=area,cell_areas='pinned ASAP7 RVT TT Liberty',
            pins=face,pin_counts=counts,added_schedule_cycles=0,sram_count=6,
            sram_origins_um=[[x,y] for y in (43.2,129.6) for x in (43.2,129.6,216)],variants=[])
for w,h in [(302.4,302.4),(345.6,302.4)]:
    band=[2.16,216.0,w-2.16,h-2.16]
    usable=(band[2]-band[0])*(band[3]-band[1])
    density={f:counts[f]/((w-4.32) if f=='N' else (h-2.16-216)) for f in ('N','E','W')}
    # Every functional terminal is either in this band or on one of six macros.
    # A convex pairwise-corner bound is stronger than assuming outline diagonal.
    rects=[band]+[[x,y,x+51.408,y+39.96] for x,y in result['sram_origins_um']]
    corners=[(x,y) for x0,y0,x1,y1 in rects for x,y in [(x0,y0),(x0,y1),(x1,y0),(x1,y1)]]
    reach=max(math.dist(x,y) for x in corners for y in corners)
    result['variants'].append(dict(outline_um=[w,h],std_band_um=band,band_area_um2=usable,
                                  modeled_std_density=area/usable,pin_density_per_um=density,
                                  all_terminal_pair_distance_bound_um=reach,
                                  planning_reach_pass=reach<=405,
                                  clock_entry='N centre beside all boundary/core register mass',
                                  qualification='PLAN ONLY: actual row occupancy, clock spread, native placed reach and routing required'))
Path('geometry_plan.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
