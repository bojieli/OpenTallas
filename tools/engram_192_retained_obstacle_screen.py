"""Check proposed192-home origins against ALL retained source obstacles."""
import collections
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'sensitivity_192_homes.json').read_bytes();d=json.loads(raw)
pin=d['source_pin']['commit'];p=d['source_pin']['path']
src=subprocess.check_output(['git','show',pin+':'+p]);fp=json.loads(src)
sizes={};lef_pins={}
for master in sorted({r[1] for r in fp['instances']}):
    if master=='ASSUMED_serdes_112g_lane':sizes[master]=(400.,1000.)
    elif master=='ASSUMED_ucie_a_x64':sizes[master]=(388.8,1043.)
    else:
        path=f'physical/asap7_memory_macros/{master}/{master}.lef'
        b=subprocess.check_output(['git','show',pin+':'+path])
        m=re.search(rb'SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)',b)
        assert m;sizes[master]=tuple(float(x) for x in m.groups())
        lef_pins[master]=dict(commit=pin,path=path,sha256=hashlib.sha256(b).hexdigest())
obstacles=[]
for name,master,x,y,orient,group in fp['instances']:
    w,h=sizes[master]
    if orient in ('R90','R270'):w,h=h,w
    obstacles.append((name,'hard:'+group,x,y,w,h))
for name,group,x,y,w,h in fp['soft_regions']:
    obstacles.append((name,'soft:'+group,x,y,w,h))
for name,group,x,y,w,h in fp['channel_rects']:
    obstacles.append((name,'channel:'+group,x,y,w,h))
ox,oy=d['grid_origin_um'];gw,gh=d['grid_size_um'];px=gw/64;py=gh/128
def overlap(a,b):
    x,y,w,h=a;xx,yy,ww,hh=b
    return x<xx+ww and xx<x+w and y<yy+hh and yy<y+h
grid_hits=collections.Counter();examples=[]
for name,typ,x,y,w,h in obstacles:
    if overlap((ox,oy,gw,gh),(x,y,w,h)):
        grid_hits[typ]+=1
        if len(examples)<12:examples.append(dict(name=name,kind=typ,bbox=[x,y,w,h]))
def index(x,y):
    return sum(((y>>(6-k))&1)<<(12-2*k) for k in range(7))+sum(((x>>(5-k))&1)<<(11-2*k) for k in range(6))
screens=[]
for count in sorted({h['actual_macros'] for h in d['homes']}):
    pairs=collections.Counter();bad=set()
    for name,typ,x,y,w,h in obstacles:
        if not overlap((ox,oy,gw,gh),(x,y,w,h)):continue
        # Bounded nearby cell lookup; include a one-cell pad then exact test.
        for gx in range(max(0,math.floor((x-ox)/px)-1),min(64,math.floor((x+w-ox)/px)+2)):
            for gy in range(max(0,math.floor((y-oy)/py)-1),min(128,math.floor((y+h-oy)/py)+2)):
                local=index(gx,gy)
                if local<count and overlap((ox+gx*px+8,oy+gy*py+8,125.28,62.91),(x,y,w,h)):
                    pairs[typ]+=1;bad.add(local)
    screens.append(dict(actual_macros_per_home=count,candidate_macros_with_any_retained_obstacle_overlap=len(bad),overlap_pairs_by_kind=dict(pairs)))
assert any(s['candidate_macros_with_any_retained_obstacle_overlap'] for s in screens)
out=dict(schema='opentallas.engram.192-home-retained-obstacle-screen.v1',
    sensitivity_sha256=hashlib.sha256(raw).hexdigest(),source_floorplan_pin=d['source_pin'],
    source_LEF_pins=lef_pins,generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    all_source_obstacle_count=len(obstacles),assumed_abstract_sizes_um={'ASSUMED_serdes_112g_lane':[400,1000],'ASSUMED_ucie_a_x64':[388.8,1043]},
    grid_bbox_overlap_source_counts=dict(grid_hits),examples=examples,
    per_populated_shard_size_macro_overlap_screen=screens,
    verdict='FAIL_IF_ALL_CURRENT_SOURCE_OBSTACLES_RETAINED',
    meaning='192 grid passes core/hub/halo bounds only. Exact candidate R0 macro bboxes intersect retained current-role hard/soft/channel obstacles. It is not a legal fullhome floorplan. No obstacle is removed or treated free by this receipt.',
    next_owner_requirement='Ram must compose a role-specific full floorplan specifying every retained/replaced field reservation, current hub/service/PHY, selector/hold/CTS area, channels and IO before placement admission. No implicit area-only conversion of the existing expert field.',
    channel_capacity_note='Existing640/1525 HBM corridors and832/1153 spines are source reservations, not free new800track lanes; selector/ACK/clock must be assigned available layers/cuts jointly.',
    L1_generated_source=None,checkpoint_reads=0,RTL_or_PnR_runs=False,physical_admission=False)
target=ROOT/'sensitivity_192_obstacle_screen.json';assert not target.exists()
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),grid_hits=dict(grid_hits),screens=screens)))
