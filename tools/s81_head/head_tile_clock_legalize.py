#!/usr/bin/env python3
"""Retain HEAD's declared clock topology at legal, source-defined cell homes.

Moves complete prebuild cell groups by the smallest legal site/row displacement.
Only geometry participates: actual rows, macros with halos, fixed cells, islands,
and other planned clock bodies. No timing observations or per-sink edits.
Input plan is produced by head_tile_clock_plan.py; rerun that model after applying
source_moves.json to its fresh_unpadded_spec.json, then require the final audit.
"""
import argparse,copy,gzip,json,math,re
from pathlib import Path

SW,SH,OX,OY=.054,.27,4.32,4.32
WIDTH={'BUFx4_ASAP7_75t_R':.378,'BUFx24_ASAP7_75t_R':1.62}
def overlap(a,b):
 return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
def snap(x,y):return OX+round((x-OX)/SW)*SW,OY+round((y-OY)/SH)*SH
class Geometry:
 def __init__(self,path):
  self.rows=[];self.keep=[];self.fixed={}
  text=gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)
  for line in text:
   f=line.strip().split('\t');r=tuple(map(float,f[1:5]))
   if f[0]=='W':self.rows.append(r)
   elif f[0]=='B':self.keep.append(r)
   elif f[0]=='F':
    if f[5].startswith('ot_'):self.keep.append((r[0]-2.16,r[1]-2.16,r[2]+2.16,r[3]+2.16))
    else:
     for x in range(math.floor(r[0]/5),math.floor(r[2]/5)+1):self.fixed.setdefault((x,round(r[1]/SH)),[]).append(r)
  text.close()
 def bad(self,r):
  if not any(w[0]-1e-6<=r[0] and r[2]<=w[2]+1e-6 and abs(w[1]-r[1])<1e-3 for w in self.rows):return 'row'
  if any(overlap(r,k) for k in self.keep):return 'macro_halo_or_island'
  for x in range(math.floor(r[0]/5),math.floor(r[2]/5)+1):
   if any(overlap(r,k) for k in self.fixed.get((x,round(r[1]/SH)),[])):return 'fixed'
  return None

def groups(spec,plan):
 out={}
 def add(group,name,x,y,master):
  x,y=snap(x,y);out.setdefault(group,[]).append((name,(x,y,x+WIDTH[master],y+SH)))
 root=spec.get('root_cell','BUFx24_ASAP7_75t_R');pad=spec.get('pad_cell','BUFx4_ASAP7_75t_R');tr=spec.get('trunk_cell','BUFx24_ASAP7_75t_R');tap=spec.get('tap_cell','BUFx24_ASAP7_75t_R');pitch=spec.get('pad_pitch_um',.81)
 add('root','rsp_rs',*spec['root_split_xy'],root)
 for n,x,y,p in plan['trunk']:
  if p!='-':add('trunk:'+n,'rsp_n_'+n,x,y,tr)
 for t in plan['taps']:
  tag='tap:'+str(t['id']);add(tag,'rsp_t%d_drv'%t['id'],t['x'],t['y'],tap)
  for i in range(t['pad']):
   x,y=t.get('pad_xy',[])[i] if t.get('pad_xy') else (t['x']-(t['pad']-i)*pitch-.3,t['y'])
   add(tag,'rsp_t%d_d%d'%(t['id'],i),x,y,pad)
 for c in spec['core_taps']:
  tag='core:'+c['inst'];nm=re.sub('[^A-Za-z0-9_]','_',c['inst'].split('.')[-1]);x,y=c['xy']
  for i in range(c['stages']):add(tag,'rsp_%s_d%d'%(nm,i),x+i*pitch,y,pad)
  add(tag,'rsp_'+nm+'_drv',x+c['stages']*pitch+.3,y,root)
  for i,(x,y) in enumerate(c.get('repeaters',[])):add('core_rep:'+c['inst']+':'+str(i),'rsp_%s_r%d'%(nm,i),x,y,root)
 return out

def audit(spec,plan,geo):
 gs=groups(spec,plan);items=[(g,n,r) for g,rs in gs.items() for n,r in rs];bad=[]
 for i,(g,n,r) in enumerate(items):
  why=geo.bad(r)
  if why:bad.append([n,why])
  for _,nn,rr in items[:i]:
   if overlap(r,rr):bad.append([n,'planned_overlap:'+nn])
 return bad

def legalize(spec,plan,geo):
 spec,plan=copy.deepcopy(spec),copy.deepcopy(plan);gs=groups(spec,plan);moves={}
 candidates=sorted((abs(i*SW)+abs(j*SH),j*SH,i*SW) for i in range(-185,186) for j in range(-37,38) if abs(i*SW)+abs(j*SH)<=10)
 for group,rs in list(gs.items()):
  other=[r for gg,rr in gs.items() if gg!=group for _,r in rr]
  def valid(rr):return all(not geo.bad(r) and not any(overlap(r,k) for k in other) for _,r in rr)
  if valid(rs):continue
  if group.startswith('tap:'):raise ValueError('tap footprint must be legalized by head_tile_clock_plan.py first: '+group)
  for _,dy,dx in candidates:
   trial=[(n,(r[0]+dx,r[1]+dy,r[2]+dx,r[3]+dy)) for n,r in rs]
   if valid(trial):break
  else:raise ValueError('no legal source homes within10um: '+group)
  gs[group]=trial;moves[group]=[round(dx,6),round(dy,6)]
  if group=='root':spec['root_split_xy']=[spec['root_split_xy'][0]+dx,spec['root_split_xy'][1]+dy]
  elif group.startswith('trunk:'):
   for tree in [spec['trunk'],plan['trunk']]:
    for n in tree:
     if n[0]==group[6:]:n[1]+=dx;n[2]+=dy
  elif group.startswith('core:'):
   c=next(c for c in spec['core_taps'] if c['inst']==group[5:]);c['xy']=[c['xy'][0]+dx,c['xy'][1]+dy]
  elif group.startswith('core_rep:'):
   _,name,idx=group.split(':');c=next(c for c in spec['core_taps'] if c['inst']==name);xy=c['repeaters'][int(idx)];xy[0]+=dx;xy[1]+=dy
 spec['placement_status']='FIRM'
 ledger=copy.deepcopy(spec.get('prebuild_body_moves_um',{}))
 for group,(dx,dy) in moves.items():
  old=ledger.get(group,[0.,0.]);ledger[group]=[round(old[0]+dx,6),round(old[1]+dy,6)]
 spec['prebuild_body_moves_um']=ledger
 bad=audit(spec,plan,geo)
 if bad:raise ValueError('remaining clock body violations: '+str(bad))
 return spec,plan,moves

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--blockages',type=Path,required=True);p.add_argument('--audit',action='store_true');a=p.parse_args();d=a.directory
 spec=json.load(open(d/'reg_spine.json'));plan=json.load(open(d/'reg_spine_plan.json'));geo=Geometry(a.blockages)
 if a.audit:
  bad=audit(spec,plan,geo);print(json.dumps(dict(planned_cells=sum(map(len,groups(spec,plan).values())),violations=bad),indent=2));raise SystemExit(bool(bad))
 spec,plan,moves=legalize(spec,plan,geo)
 (d/'source_fixed_spec.json').write_text(json.dumps(spec,indent=2)+'\n');(d/'source_fixed_plan.json').write_text(json.dumps(plan,indent=2)+'\n');(d/'source_moves.json').write_text(json.dumps(moves,indent=2)+'\n');print(json.dumps(moves))
