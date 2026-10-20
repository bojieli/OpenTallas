#!/usr/bin/env python3
"""Exact box planning proof for spatial GN relays; never placed evidence."""
import json,itertools
from pathlib import Path
P=Path(__file__).resolve().parent
geometry=json.loads((P/'geometry/smh_rp4hn_g1_k32.json').read_text())
blocks=geometry['layout']['blocks']
stations=[{'name':'pin_capture','box':[181.44,810.8,228.96,820.8],'bits':100},
 {'name':'u_v2/u_d2','box':[290,586,330,594],'bits':100},
 {'name':'u_v3/u_d3','box':[340,316,380,324],'bits':100},
 {'name':'u_v4/u_d4','box':[340,136,380,144],'bits':100},
 {'name':'S_output_pin','box':[423.36,0,453.6,0],'bits':100}]
def corners(b): return itertools.product((b[0],b[2]),(b[1],b[3]))
def bound(a,b):return max(abs(x-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b))
for st in stations:
 st['macro_overlaps']=[b[0] for b in blocks if st['box'][0]<b[4] and st['box'][2]>b[2] and st['box'][1]<b[5] and st['box'][3]>b[3]]
 assert not st['macro_overlaps'],st
hops=[{'from':a['name'],'to':b['name'],'max_manhattan_um':bound(a['box'],b['box'])} for a,b in zip(stations,stations[1:])]
# A straight line would cross the old XS. Reserve100 parallel tracks in
# the real43.2um E corridor, x347..366.2; evaluate the full routed dogleg.
bus_tracks=[347+0.192*i for i in range(100)]
a,b=stations[1]['box'],stations[2]['box']
detour=max(abs(x-t)+abs(t-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b) for t in bus_tracks)
hops[1]['obstacle_aware_manhattan_um']=detour
# The next hop crosses the TCL row, so route in its43.2um centre gap.
a,b=stations[2]['box'],stations[3]['box']
hops[2]['obstacle_aware_manhattan_um']=max(abs(x-t)+abs(t-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b) for t in [305+0.192*i for i in range(100)])
# Final pass goes EAST of the TCT, never over its obstructed footprint.
a,b=stations[3]['box'],stations[4]['box']
hops[3]['obstacle_aware_manhattan_um']=max(abs(x-t)+abs(t-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b) for t in [414+0.192*i for i in range(100)])
assert max(h.get('obstacle_aware_manhattan_um',h['max_manhattan_um']) for h in hops)<=405
assert max([h['max_manhattan_um'] for h in hops]+[detour])<=405
out={'scope':'PLANNED bounded station boxes against actual phase-declared closed LEF rectangles; no placed proof or current real-XS child binding',
 'source':'364f635c3','latency':'+2 result edges vs legacy -> gout+5','registered_stages_north':4,
 'storage':'four100b distributed physical reach relays, with196um+ Y separation; NOT co-located temporal padding; total400b, +100b vs prior+1. G1 computes capture/mask/OR,254FF per leaf (+96mask+2valid/fault vs prior156)',
 'stations':stations,'hops':hops,'additional_g1_bank':{'box':[270,136,330,144],'bits':254,'note':'exact mapped FF count pending; macrochannels21.52um below/28.8um above'},
 'obligations':['native32 all drivers incl reset','fulllegacy+5 exact','full placed allnet reach','new real XS475.2-wide successor reframe','critical geometry/phase review before layout gate']}
(P/'mask_relay_plan.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps(hops,indent=1))
