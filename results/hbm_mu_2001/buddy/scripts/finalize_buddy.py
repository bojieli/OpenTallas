#!/usr/bin/env python3
"""Finalize short native buddy links and period-4 FUSED tree serialization in a NEW plan fragment.
Analytical plan only: native pin replan, binding, calendar/latency proof and P&R remain required.
"""
import json,sys,re,math,copy
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-2001/tools/die_plan')
import hbm_r9_delta as R9,hbm_r10_delta as R10
src,out=sys.argv[1:3];t=json.load(open(src));changes=[];native=0
for s in t['internal_stations']:
 a,c=s.get('launch',''),s.get('capture','')
 f=lambda x:re.match(r'^u_mu_fused_\d+(?:\.|$)',x) is not None
 is_native=(a.startswith('u_vmb_') and f(c)) or(f(a) and c.startswith('u_vmb_'))
 if is_native:
  native+=1
  if s.get('serial_k',1)!=1:raise ValueError('native buddy is serialized')
  length=sum(abs(x-y) for x,y in zip(s['from_um'],s['to_um']))
  if length>405:raise ValueError('native buddy direct reach exceeds405')
  old=len(s.get('regs_um',[]));s['regs_um']=[]
  if old:changes.append(dict(conn=s['conn'],kind='direct_native_gap',removed_cycles=old,length_um=round(length,3)))
 if a.startswith('u_mu_fused_n') and s.get('bits_parallel',s['bits'])==271 and s.get('serial_k',1)>4:
  old=s['serial_k'];s['serial_k']=4;s['bits']=math.ceil(271/4)
  changes.append(dict(conn=s['conn'],kind='period4_tree_up',old_k=old,new_k=4,old_wires=math.ceil(271/old),new_wires=s['bits'],removed_cycles=old-4))
assert native==48,native
W,H=t['outline_um'];u=R9.cut(t)['blocked'];segments=[]
for a,b in [(0,3957.12),(3957.12,W)]:segments.append(R10.profile(W,H,t,a,b))
mx=max([u[a]['max_use'] for a in 'xy']+[r[a]['max_use'] for r in segments for a in 'xy'])
r=dict(source=src,native_links=native,cut=u,segments=segments,max_axis=mx,verdict='PASS_MODEL_CUT' if mx<=.6+1e-9 else 'FAIL_MODEL_CUT',changes=changes,removed_relay_cycles=sum(x['removed_cycles'] for x in changes if x['kind']=='direct_native_gap'))
t['note']+=' | FINAL MU buddy plan: native557-bit ports cross direct8.64umgap, no relays; tree up period4 protected. FUSED W/E repin/rekit and calendar latency rebinding REQUIRED.'
Path(out).write_text(json.dumps(t,indent=1)+'\n');Path(out+'.report.json').write_text(json.dumps(r,indent=1)+'\n')
print(json.dumps({k:v for k,v in r.items() if k not in ['changes','segments','cut']}))
