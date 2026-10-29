#!/usr/bin/env python3
"""Estimate-only plan candidates after C24 macro/halo congestion failures. No timing/route PASS claim."""
import json, math, re
from pathlib import Path
P=Path(__file__).parent
S=4.32; HALO=4.32; TRACKS=1/.036+1/.048; BUDGET=.6
snap=lambda x: math.ceil((x-1e-8)/S)*S
# vp4: all pins of five macros per column through the shared vertical channel is a conservative bound.
vw,vh=94.8,41.1
loads=[5*410,5*(410+409),5*409]
gaps=[n/(TRACKS*BUDGET)+(HALO if c in (0,2) else 2*HALO) for c,n in enumerate(loads)]
W=2*S*math.ceil((2*S+2*vw+sum(gaps))/(2*S)); H=311.04
extra=W-(2*S+2*vw+sum(gaps)); gaps=[v+extra/3 for v in gaps]
xs=[round(round(x/.054)*.054,3) for x in [S+gaps[0],S+gaps[0]+vw+gaps[1]]]
gaps=[xs[0]-S,xs[1]-xs[0]-vw,W-S-xs[1]-vw]
# Keep all SRAMs R0; preserve one centre entry crossing and place 2 below / 3 above it per column.
yc=H/2; lowtop=yc-S-HALO-.048; hitop=yc+S+HALO+.048
vp=[]
for c,x in enumerate(xs):
 for r in range(5):
  y=lowtop-vh-r*(vh+2*HALO) if r<2 else hitop+(r-2)*(vh+2*HALO)
  vp.append(dict(column=c,row=r,origin_um=[round(x,3),round(y,3)],orient='R0'))
v=dict(module='ot_hgi_dma_back_static_vp4_banks_cp',status='ESTIMATE ONLY; instance assignment and current plan pins pending',outline_um=[round(W,3),H],old_outline_um=[239.976,275.4],clock_entry_um=[W/2,H/2],macro_size_um=[vw,vh],macro_count=10,columns=2,channel_gaps_um=gaps,channel_load_bits=loads,vertical_track_density=TRACKS,escape_bound=[loads[c]/((gaps[c]-(HALO if c in (0,2) else 2*HALO))*TRACKS) for c in range(3)],macro_positions=vp,assumptions=['all ten macros same R0 abstract','M3+M5 usable in vertical channels; macro halo excluded','whole-column summed edge pins bound <=0.6; sufficient channel budget, not GRT proof','clock islands/entry must be resited before build; external pins regenerate from die owner','no RTL/calendar/cycle change'])
# Programme store: recover intended 11-leaf source topology, avoiding the current random placement of each leaf's pages.
old=(P/'progstore_c24_macro_placement.tcl').read_text(); before={}
for n,x,y,o in re.findall(r'\{(u_fcore\.g_leaf.*?u_program)\}\s+\S+\s+([\d.]+)\s+([\d.]+)\s+(\S+)',old):
 l=int(re.search(r'g_leaf\\\[(\d+)',n)[1]); before.setdefault(l,[]).append([float(x),float(y)])
reach={str(l):round(max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in p for b in p),3) for l,p in before.items()}
rows=[[2,1,0],[6,None,8],[7,10,9],[5,4,3]]; tw,th=285.12,181.44; mw,mh=96.552,69.66
outer=19.44; middle=tw-2*mw-2*outer; bottom=10.8; hgap=th-2*mh-2*bottom
mac=[];zones=[]
for r,row in enumerate(rows):
 for c,l in enumerate(row):
  if l is None:continue
  ox,oy=S+c*tw,S+r*th
  zones.append(dict(leaf=l,rect_um=[ox,oy,ox+tw,oy+th],pattern=f'u_fcore.g_leaf[{l}].u_leaf.*'))
  for p in range(4):
   col=p%2; rr=p//2
   # MY left macro faces its active W pin bank toward the middle; R0 right macro does likewise.
   x=ox+outer+col*(mw+middle);y=oy+bottom+rr*(mh+hgap)
   mac.append(dict(k=f'g_leaf[{l}].u_leaf.g_page[{p}].u_program',macro='ot_sram_1r1w_512x256_m1_r2c2',origin_um=[round(x,3),round(y,3)],orient='MY' if col==0 else 'R0'))
p=dict(schema='opentallas.macro_placement.v1',design='ot_hgi_sfu_programme_store_r10',outline_um=[2*S+3*tw,2*S+4*th],macro_placement=mac,note='ESTIMATE ONLY: source-local11leaf form; requires row/head relay placement, leaf fences, current pins and clock islands before trial')
pe=dict(status='ESTIMATE ONLY; not build-approved',old_outline_um=[574.56,738.72],outline_um=p['outline_um'],source_rows_south_to_north=rows,leaf_box_um=[tw,th],within_leaf_macro_origin_max_manhattan_um=round(mw+middle+mh+hgap,3),old_same_leaf_macro_origin_max_manhattan_um=reach,local_spine_inner_usable_um=middle-2*HALO,outer_usable_um=outer-HALO,local_spine_escape_bound=2*414/((middle-2*HALO)*TRACKS),outer_escape_bound=414/((outer-HALO)*TRACKS),leaf_logic_guides=zones,needed_before_build=['clock islands repositioned to local spines; preserve current plan ports','guide every g_leaf[n] standard cell to its own leaf zone','position per-row pr/cr/sp/si and output o_ctl/o_io relay FFs from RTL row topology','check every output face path and head/row relay reach405; candidate is macro-fit only','source constant resets/cycles unchanged; no new latency claimed'],reason='C24 leaf0 and leaf9 SRAM page spans >405um; original RTL explicitly specifies three-column/four-row local leaves. Whole-column edge sum assumes nonexistent long-distance demand and is only an upper bound.')
(P/'vp4_estimate.json').write_text(json.dumps(v,indent=2)+'\n');(P/'programme_store_macro_candidate.json').write_text(json.dumps(p,indent=2)+'\n');(P/'programme_store_estimate.json').write_text(json.dumps(pe,indent=2)+'\n')
print(json.dumps({'vp4_outline':v['outline_um'],'vp4_escape':v['escape_bound'],'prog_outline':p['outline_um'],'prog_local_escape':[pe['local_spine_escape_bound'],pe['outer_escape_bound']],'old_leaf_spans':reach},indent=2))
