#!/usr/bin/env python3
"""Actual-DEF obstacle test for the requested TP8 head-cluster envelope.
Candidate geometry only; relay, clock, pin and cut regeneration still required.
"""
import argparse,json,math
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('input');ap.add_argument('out');ap.add_argument('--w',type=float,default=734.4);ap.add_argument('--h',type=float,default=855.36);ap.add_argument('--columns',type=int,default=3);a=ap.parse_args();D=json.load(open(a.input));I=D['insts'];W=31785.696;H=25870.32;w=a.w;h=a.h;gap=20
heads=[i for i in I if i['m']=='qkd_rhead'];B=[i for i in I if i['m']!='qkd_rhead' and not i['m'].startswith(('qfd_rly','qkd_rly'))]
def up(x):return round(math.ceil((x-1e-7)/2.16)*2.16,6)
def hit(r,b):return r['x']<b['x']+b['w']+gap and r['x']+r['w']+gap>b['x'] and r['y']<b['y']+b['h']+gap and r['y']+r['h']+gap>b['y']
placements=[];fail=[]
for side in ('W','E'):
 old=[i for i in heads if (i['x']<W/2)==(side=='W')];xs=[up(1447.2+j*(w+gap)) for j in range(a.columns)] if a.columns==3 else [2020.464,2889.216]
 if side=='E':xs=[up(W-x-w) for x in xs]
 slots=[]
 for x in xs:
  obs=[i for i in B if i['x']<x+w+gap and i['x']+i['w']+gap>x]
  anchors=[gap]+[i['y']+i['h']+gap for i in obs]
  ys=sorted({up(y+j*(h+gap)) for y in anchors for j in range(int(H/(h+gap))) if y+j*(h+gap)+h<H-gap})
  local=[]
  for y in ys:
   r=dict(x=x,y=y,w=w,h=h)
   if y+h>H-gap or any(hit(r,b) for b in obs+local):continue
   slots.append(r);local.append(r)
 # Greedy assignment of original ids to a measured legal slot, nearest center first.
 for o in sorted(old,key=lambda i:i['y']):
  avail=[s for s in slots if not any(hit(s,r) for r in placements)]
  if not avail:fail.append(o['n']);continue
  r=min(avail,key=lambda s:abs(s['x']+w/2-o['x']-o['w']/2)+abs(s['y']+h/2-o['y']-o['h']/2));slots.remove(r)
  placements.append(dict(r,n=o['n'],m='qkd_rhead',side=side,orient='R0' if side=='W' else 'MY',pins='S input; N score; E nb (before instance orientation)'))
 for r in placements:assert not any(hit(r,b) for b in B)
new_area=len(placements)*w*h/1e6;old_area=sum(i['w']*i['h'] for i in heads)/1e6
out=dict(source=a.input,head_source='codex/qwen-head-1013 38d5bf5b2',requested_count=len(heads),placed=len(placements),failed=fail,geometry_verdict='PASS' if not fail else 'REJECT_INCOMPLETE',minimum_gap_um=gap,requested_outline_um=[w,h],positions=placements,placed_envelope_area_mm2=new_area,required_envelope_area_mm2=len(heads)*w*h/1e6,old_head_area_mm2=old_area,requested_delta_area_mm2=len(heads)*w*h/1e6-old_area,closed_children=['physical/ref_tile/qkh_lane8_ref_b/views/ot_qkh_lane8 129.6sq x16','physical/ref_tile/qkh_ktree_ref/views/ot_qkh_ktree151.2x97.2'],limitation='Parent M7 routing remains open; this changes placement only, not functional die netlist. Real port relays <=500um, clocks, layer-aware cuts and child closure required; direct M5 child alternative may reduce track obstruction.')
Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print({k:out[k] for k in ('requested_count','placed','failed','geometry_verdict','required_envelope_area_mm2','requested_delta_area_mm2')})
