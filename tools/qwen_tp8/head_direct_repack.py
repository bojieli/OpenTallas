#!/usr/bin/env python3
"""Repack all128 B4 heads using real CLOSED M5 children, preserving actual other hard obstacles.
This is a direct-child physical specification, not a legal functional die netlist.
"""
import json,math
from pathlib import Path
src='/tmp/qwen_it2_actual_placement_codex.json';D=json.load(open(src));I=D['insts'];W=31785.696;H=25870.32;gap=20
old=[i for i in I if i['m']=='qkd_rhead'];ctl=[i for i in I if i['m']=='qkd_ectl']
B=[i for i in I if i['m'] not in ('qkd_rhead','qkd_ectl') and not i['m'].startswith(('qfd_rly','qkd_rly'))]
w=626.4;h=745.2;cw=647.976;ch=129.576

def hit(r,b):return r['x']<b['x']+b['w']+gap-1e-6 and r['x']+r['w']+gap>b['x']+1e-6 and r['y']<b['y']+b['h']+gap-1e-6 and r['y']+r['h']+gap>b['y']+1e-6

def up(x):return round(math.ceil((x-1e-7)/2.16)*2.16,6)
boxes=[];kids=[];errors=[];newctl=[]
for side in ('W','E'):
 C=sorted({round(i['x'],6) for i in old if (i['x']<W/2)==(side=='W')},reverse=side=='E')
 for col,xold in enumerate(C):
  x=(2020.464 if col==0 else 2909.088);cx=(1998.864 if col==0 else 2909.088)
  if side=='E':x=W-x-w;cx=W-cx-cw
  os=sorted([i for i in old if abs(i['x']-xold)<1e-5],key=lambda i:i['y']);ec=sorted([i for i in ctl if abs(i['x']-xold)<.6],key=lambda i:i['y']);assert len(os)==32 and len(ec)==8,(side,xold,len(os),len(ec))
  y=up(20)
  for g in range(8):
   for j in range(4):
    o=os[g*4+j];box=dict(n=o['n'],m='DIRECT_HEAD_REGION',x=x,y=y,w=w,h=h,orient='R0' if side=='W' else 'MY');boxes.append(box)
    for t in range(16):
     k=dict(n=o['n']+f'_lane{t}',m='ot_qkh_lane8',x=x+21.6+151.2*(t%4),y=y+21.6+151.2*(t//4),w=129.6,h=129.6,pg_layer='M5',signal_max_layer='M5')
     # Direct die leaves use mirrored placement at the Eedge to retain parent orientation.
     if side=='E':k['x']=x+w-(k['x']-x)-k['w'];k['orient']='MY'
     else:k['orient']='R0'
     kids.append(k)
    k=dict(n=o['n']+'_ktree',m='ot_qkh_ktree',x=x+237.6,y=y+626.4,w=151.2,h=97.2,pg_layer='M5',signal_max_layer='M5',orient='R0')
    if side=='E':k['x']=x+w-237.6-151.2;k['orient']='MY'
    kids.append(k);y=up(y+h+gap)
   c=dict(ec[g],x=cx,y=y);newctl.append(c);y=up(y+ch+gap)
for r in kids+newctl:
 if r['x']<0 or r['y']<0 or r['x']+r['w']>W or r['y']+r['h']>H:errors.append(('outside',r['n']))
 for b in B:
  if hit(r,b):errors.append(('fixed_hard_overlap',r['n'],b['n']))
for j,r in enumerate(kids+newctl):
 for b in (kids+newctl)[:j]:
  if hit(r,b):errors.append(('peer_overlap',r['n'],b['n']))
rec=dict(source=dict(actual_def='ot-epyc1tb:/srv/opentallas-scratch/claude/qwen-tp8-die/it2/case_r22k/floorplan_placed.def',head_candidate='38d5bf5b2',lane_source='5df61de79'),status='PASS_DIRECT_CHILD_GEOMETRY' if not errors else 'REJECT',head_count=len(boxes),lane_count=sum(k['m']=='ot_qkh_lane8' for k in kids),ktree_count=128,ectl_count=len(newctl),errors=errors,regions=boxes,closed_children=kids,moved_ectl=newctl,minimum_gap_um=20,closed_child_area_mm2=sum(k['w']*k['h'] for k in kids)/1e6,region_area_mm2=sum(k['w']*k['h'] for k in boxes)/1e6,old_head_envelope_area_mm2=sum(k['w']*k['h'] for k in old)/1e6,remaining=['Real M5 hardened local input/control/score glue plus three relay bundles must fit region free space; no substantial soft die glue','All128 Nscore ports, Sinputs and oriented nb ports require real functional netlist/bindings and <=500um clocked seams','ECTL placement moves require re-derived external relay counts and minimum exact seam gates','Actual child layers/OBS, clocks, full lane-window cut scan, prototype GRT and die STA/IR still required'],limitation='Geometry specification only. Region boxes are NOT macro obstacles; only real M5children obstruct their own shapes. No head parent outline change accepted.')
p=Path('results/arch/qwen_tp8_1012/head_direct_repack_codex.json');p.write_text(json.dumps(rec,indent=2)+'\n');print({k:rec[k] for k in ('status','head_count','lane_count','ectl_count','errors','closed_child_area_mm2','region_area_mm2')})
