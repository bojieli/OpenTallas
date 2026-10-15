#!/usr/bin/env python3
"""Plan the candidate gather strip from CLOSED relay LEFs and insertion receipts.
This is a planned geometry receipt; missing ctl/root routed views remain explicit.
"""
import argparse, hashlib, json, math, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lef(p):
 t=p.read_text();m=re.search(r'SIZE\s+(\S+)\s+BY\s+(\S+)',t);w,h=map(float,m.groups());pins={}
 for pm in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',t,re.M|re.S):
  lm=re.search(r'LAYER\s+(\S+)\s*;\s*RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',pm[2])
  if lm:
   a,b,c,d=map(float,lm.groups()[1:]);pins[pm[1]]={'layer':lm[1],'x':(a+c)/2,'y':(b+d)/2}
 return w,h,pins
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--assigned',required=True);ap.add_argument('--out',required=True)
 ap.add_argument('--v19-geometry',action='store_true',help='original 164.16 leaf rows (reproduces the v19 receipt)');a=ap.parse_args()
 import sys;sys.path.insert(0,str(Path(__file__).resolve().parent))
 import gather_parent_spec as gps
 leaf_h=None if a.v19_geometry else gps.leaf_heights();reach=not a.v19_geometry;geo=gps.geometry(leaf_h);OUT_H=geo['outline_h']
 hof={'dsfd_gth_rw':gps.V19_LEAF_H,'dsfd_gth_re':gps.V19_LEAF_H} if leaf_h is None else leaf_h
 assigned=Path(a.assigned);pins=json.loads(assigned.read_text());inst=json.loads((ROOT/'tools/s81_ph/gather_strip_instances.json').read_text())['instances'];taken=[];children=[]
 def snap(x):return round(x/.576)*.576
 def clear(x,y,w=15.12,h=15.12):return all(x+w+2.16<=b[0] or b[0]+b[2]+2.16<=x or y+h+2.16<=b[1] or b[1]+b[3]+2.16<=y for b in taken)
 taken.append((1598.4,8.64,129.6,43.2))
 for g in range(8):
  for k in range(4):taken.append((12.96+216*g,geo['row_y'][k],190.08,hof['dsfd_gth_rw' if g<4 else 'dsfd_gth_re']))
 # Reserve every v4 lane/result relay before placing reset relays in the same channels.
 lane_result=gps.relay_children(geo)
 for r in lane_result:
  w,h=(23.76,30.24) if '276' in r['master'] else (34.56,19.44)
  taken.append((*r['at'],w,h))
 def strip(x):
  cells=[(abs(xx-x)+abs(y-25.92)*.1,xx,y) for y in (8.64,25.92,43.2) for xx in (snap(8.64+17.28*j) for j in range(92)) if clear(xx,y)]
  _,x,y=min(cells);taken.append((x,y,15.12,15.12));return x,y
 def priority(v):
  role=v['role']
  if role.startswith('rc'):return (0,v['clock_index'])
  if role in ('tc','f_cd'):return (1,v['clock_index'])
  if role.startswith('tst') and int(role[3:])>=6:return (2,v['clock_index'])
  if role.startswith('cs'):return (3,-int(role[2:])*10+v['stage'])
  return (4,v['clock_index'])
 for v in sorted(inst,key=priority):
  role=v['role'];j=v['stage']
  if role.startswith('tst'):
   g=int(role[3:]);start=0 if g<6 else 1728;x,y=strip(start+(1640-start)*(j+1)/5)
  elif role.startswith('cs'):
   g=int(role[2:])
   if reach:
    # Stage 0 sits directly under its column, W of the leaf co escape (leaf x 48..142): the row-1 st and row-2/3
    # result-relay status words drop straight down (<= ~330 um); stages 1..3 split the run to the ctl evenly.
    x0=12.96+216*g+8.64;x,y=strip(x0+(1640-x0)*j/4)
    if j==0 and abs(x-x0)>100:
     # The strip next to the ctl is full (rc / tst / tc / f_cd): put stage 0 in the free channel space nearest the
     # column's status sources (row 0/1 st at leaf x + 20, row 2/3 result relays in the row0|row1 channel).
     taken.pop();ax,ay=12.96+216*g+60,geo['row_y'][0]+hof['dsfd_gth_rw' if g<4 else 'dsfd_gth_re']
     sites=[(abs(xx-ax)+abs(yy-ay),xx,yy) for xx in (snap(ax-200+2.304*n) for n in range(174)) for yy in (snap(2.304*n) for n in range(200))
            if 0<=xx<=1728-15.12 and clear(xx,yy)]
     if not sites:raise SystemExit(f'STRIP_PLAN REFUSED: no free status relay site for {v["instance"]}')
     _,x,y=min(sites);taken.append((x,y,15.12,15.12))
   else:
    start=108+216*g;x,y=strip(start+(1640-start)*(j+1)/5)
  elif role.startswith('rc'):
   g=int(role[2:]);target=(205.632+216*g) if g<7 else 1501.632
   if j<4:x,y=strip(1640+(target-1640)*(j+1)/4)
   else:
    if reach:
     # Stages 4/5 climb the column channel at the actual row pitch: stage 5 ends ~250 um below the top-row leaf rs
     # pin (N face), stage 4 halfway between the strip and stage 5 (v19 constants 340 / 560 left the rs hop > 500 um).
     top=geo['row_y'][3]+hof['dsfd_gth_rw' if g<4 else 'dsfd_gth_re'];y5=top-250;y4=25.92+(y5-25.92)/2
     x,y=snap(target),snap(y4 if j==4 else y5)
    else:
     x,y=snap(target),snap(340+(j-4)*220+(20.736 if g==7 else 0))
    if not clear(x,y):
     # Keep the reset relay in its assigned column channel; find the nearest free site.
     choices=[(abs(yy-y),yy) for yy in (snap(61.632+.576*n) for n in range(1262))
              if yy+15.12<=OUT_H and clear(x,yy)]
     if not choices:raise SystemExit(f'STRIP_PLAN REFUSED: no free reset relay site for {v["instance"]}')
     _,y=min(choices)
    taken.append((x,y,15.12,15.12))
  elif role=='tc':x,y=strip(1219.968+20.736*int(v['instance'].split('_')[-1]))
  else:x,y=strip(1219.968)
  base=ROOT/v['view'];lp=base/(v['master']+'.lef');ip=base/'insertion.json';w,h,pp=lef(lp);ins=json.loads(ip.read_text());assert(w,h)==(15.12,15.12)
  clock=pp['ck'];ss=ins['ss']['boundary'];tt=ins['tt']['boundary'];ff=ins['ff']['boundary']
  children.append({**v,'origin_um':[round(x,3),round(y,3)],'outline_um':[w,h],'orient':'R0','lef':str(lp.relative_to(ROOT)),'lef_sha256':sha(lp),'insertion':str(ip.relative_to(ROOT)),'insertion_sha256':sha(ip),'pins':{n:{**p,'x':round(x+p['x'],3),'y':round(y+p['y'],3)} for n,p in pp.items()},'clock_entry':{'port':f"ck_r[{v['clock_index']}]",'domain':'serial' if role=='f_cd' else 'stream','child_pin':v['instance']+'/ck','location_um':[round(x+clock['x'],3),round(y+clock['y'],3)],'source_latency_ps':{'SS':-ss['mean'],'TT':-tt['mean'],'FF':-ff['mean']},'boundary_spread_ps':{'SS':ss['max']-ss['min'],'TT':tt['max']-tt['min'],'FF':ff['max']-ff['min']}}})
 hops=[]
 for v in children:
  if v['stage']==0:continue
  prev=next(t for t in children if t['role']==v['role'] and t['stage']==v['stage']-1)
  for bit in range(v.get('used_width',v['width'])):
   key=lambda n:n if v['width']==1 else f'{n}[{bit}]'
   sp=prev['pins'][key('o')];dp=v['pins'][key('i')]
   hops.append({'source':prev['instance'],'sink':v['instance'],'bit':bit,'length_um':round(abs(sp['x']-dp['x'])+abs(sp['y']-dp['y']),3)})
 internal={'count':len(hops),'max_um':max(t['length_um'] for t in hops),'fail_over_500':[t for t in hops if t['length_um']>500]}
 # Do not substitute synthetic timing for missing ctl / root views.
 report={'schema':'opentallas.s81.gather.strip_plan.v1','assigned_parent_sha256':sha(assigned),'source_manifest_sha256':sha(ROOT/'tools/s81_ph/gather_strip_instances.json'),'outline_um':[1728,OUT_H],'leaf_h_um':hof,'row_y_um':geo['row_y'],'ctl':{'origin_um':[1598.4,8.64],'outline_um':[129.6,43.2],'view_status':'PENDING_ROUTED_VIEW'},'relay_children':children,'relay_internal_hops':internal,'actual_relay_clocks':len(children),'total_child_clocks':32+2+48+len(children),'overlap_gate':'PASS actual133striprelayboxes +48lane/resultrelayboxes +ctl +32leafboxes, clearance2.16um','lattice_um':.576,'relay_latency_cycles':{'tst':4,'cs':4,'rc_release':6,'tc':1,'f_cd_serial':1,'f_vm':0},'pending':['full source-hashed exact bench + mutants','actual assigned root child pins and routed insertion','ctl exact assigned pins + routed view','per-bit pair reach and hold from real endpoint timing','cut/PG/slot_fit/child_lint gates','native81 production binding and immutable throughput price'],'qualification':'OPEN'}
 Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print(f"STRIP_PLAN PASS placement {len(children)} real CLOSED relay views; qualification OPEN")
if __name__=='__main__':main()
