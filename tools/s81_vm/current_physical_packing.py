#!/usr/bin/env python3
"""Pack all source-extracted hard boundaries; expose missing inline parent hardware.
Preserve proven local predecessor vectors only after exact current outline equality.
The result is a development rectangle candidate, never a complete VM die macro.
"""
import argparse,collections,gzip,hashlib,json,math,pathlib,re

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--inventory',type=pathlib.Path,required=True);ap.add_argument('--local',type=pathlib.Path,required=True);ap.add_argument('--out',type=pathlib.Path,required=True);a=ap.parse_args();inv=json.loads(a.inventory.read_text());old=json.loads(a.local.read_text())['options'][0];oldnodes={n['name']:n for n in old['nodes']};leaves=inv['leaves'];gap=21.6;positions={};binding=[]
 # Bind exact current hierarchy to predecessor bank-local, q8 write and payload rectangles.
 def oldname(x):
  p=x['path'];m=x['master'];z=re.search(r'u_mem.slice\[(\d+)\].u_slice\.(.*)',p)
  if z:
   s=int(z[1]);t=z[2]
   for pat,label in [(r'bank\[(\d+)\].u_bank','bank'),(r'quarter\[(\d+)\].u_hop','quarter'),(r'bridge\[(\d+)\].u_hop','bridge')]:
    mm=re.fullmatch(pat,t)
    if mm:return f'vm_s{s}_{label}{mm[1]}'
   mm=re.fullmatch(r'write_group\[(\d+)\].capture\[(\d+)\].u_capture',t)
   if mm:return f'vm_s{s}_q{mm[1]}_capture{mm[2]}'
   mm=re.fullmatch(r'write_group\[(\d+)\].u_w',t)
   if mm:return f'vm_s{s}_q{mm[1]}_scatterout'
  z=re.search(r'u_ws.slice\[(\d+)\].(.*)',p)
  if z:
   s=int(z[1]);t=z[2];mm=re.fullmatch(r'quarter\[(\d+)\].u_d',t)
   if mm:return f'vm_s{s}_q{mm[1]}_dispatch'
   mm=re.fullmatch(r'bank\[(\d+)\].u_w',t)
   if mm:return f'vm_s{s}_q{int(mm[1])//8}_storage{int(mm[1])%8}'
  z=re.search(r'u_ws.w0_payload\[(\d+)\].u_payload',p)
  if z:return f'vm_payload{z[1]}'
  return None
 origin=old['slice_origins_um'][0]
 for i,x in enumerate(leaves):
  n=oldname(x)
  if n:
   o=oldnodes[n];assert all(abs(x['outline_um'][k]-o['outline_um'][k])<1e-6 for k in [0,1]),(x['path'],x['outline_um'],o['outline_um'])
   positions[i]=[round(o['xy_um'][k]-origin[k],6)for k in [0,1]];binding.append(dict(leaf=i,predecessor_rectangle=n,outline_equality=True))
 assert len(positions)==468,len(positions)
 baseW,baseH=3952.8,4903.2
 # Group actual cap lane plus its two related-clock halves; retain direct S-to-N interface locality.
 remaining=set(range(len(leaves)))-set(positions);groups=[]
 for lane in range(16):
  ids=[i for i in remaining if leaves[i]['path'].startswith(f'dut.u_cap.lane[{lane}].')];assert len(ids)==3
  by={leaves[i]['master']:i for i in ids};cap=by['dsfd_vm_static_cap_leaf'];s=by['ot_s81_vm_x34_s'];t=by['ot_s81_vm_x34_t'];w=max(leaves[cap]['outline_um'][0],leaves[s]['outline_um'][0]+gap+leaves[t]['outline_um'][0]);h=leaves[cap]['outline_um'][1]+gap+max(leaves[s]['outline_um'][1],leaves[t]['outline_um'][1]);local={cap:[0,0],s:[0,leaves[cap]['outline_um'][1]+gap],t:[leaves[s]['outline_um'][0]+gap,leaves[cap]['outline_um'][1]+gap]};groups.append((w,h,local,'cap_lane'+str(lane)));remaining-=set(ids)
 # Keep the eight data stripes and corresponding valid leaf in one coherent local read group.
 for q in range(8):
  ids=[i for i in remaining if leaves[i]['master']==f'dsfd_vm_static_read_q{q}_p'];ids.sort(key=lambda i:int(leaves[i]['path'].split('.d')[-1]));v=next(i for i in remaining if leaves[i]['master']==f'dsfd_vm_static_read_v{q}_p');loc={};xx=0;hh=0
  for i in ids:loc[i]=[xx,0];xx+=leaves[i]['outline_um'][0]+gap;hh=max(hh,leaves[i]['outline_um'][1])
  loc[v]=[0,hh+gap];groups.append((xx-gap,hh+gap+leaves[v]['outline_um'][1],loc,'read_q'+str(q)));remaining-=set(ids+[v])
 for i in remaining:groups.append((*leaves[i]['outline_um'],{i:[0,0]},'leaf'+str(i)))
 # Shelf packing scans real side-service widths; no fabricated control block is inserted.
 options=[]
 for sideW in [1555.2,1728,1965.6,2203.2]:
  rows=[];gpos={};placements={};height=0
  for w,h,loc,label in sorted(groups,key=lambda g:(-g[1],-g[0],g[3])):
   assert w<=sideW
   eligible=[(r[1]-w,j) for j,r in enumerate(rows)if r[1]>=w and r[2]>=h]
   if eligible:
    _,j=min(eligible);y,free,rh,x=rows[j];rows[j]=[y,free-w-gap,rh,x+w+gap]
   else:y=height;x=0;rows.append([y,sideW-w-gap,h,w+gap]);height=y+h+gap
   gpos[label]=[x,y]
   for i,p in loc.items():placements[i]=[baseW+gap+x+p[0],y+p[1]]
  allpos=dict(positions);allpos.update(placements);H=max(baseH,height-gap);W=baseW+gap+sideW;collisions=[]
  ids=sorted(allpos)
  for k,i in enumerate(ids):
   x,y=allpos[i];w,h=leaves[i]['outline_um']
   for j in ids[k+1:]:
    X,Y=allpos[j];ww,hh=leaves[j]['outline_um']
    if x<X+ww-1e-6 and x+w>X+1e-6 and y<Y+hh-1e-6 and y+h>Y+1e-6:collisions.append([i,j])
  assert not collisions,collisions[:5]
  options.append(dict(name=f'body2x2_plus_service_{sideW:g}',outline_um=[W,H],side_service_um=[sideW,height-gap],positions={str(k):v for k,v in allpos.items()},collisions=collisions,body2x2_um=[baseW,baseH],placed_hard_leaves=len(allpos)))
 for option in list(options):
  new=json.loads(json.dumps(option));new['name']=new['name'].replace('body2x2','body1x4v');new['outline_um']=[option['outline_um'][0]-1987.2,max(9828.0,option['outline_um'][1])];new['body1x4v_um']=[1965.6,9828.0];del new['body2x2_um']
  for key,xy in new['positions'].items():
   i=int(key)
   if i in positions:
    on=oldnodes[oldname(leaves[i])];sl=on['slice'];xy[0]-=1987.2*(sl%2);xy[1]+=2462.4*(sl-sl//2)
   else:xy[0]-=1987.2
  collision=[];ids=sorted(map(int,new['positions']))
  for n,i in enumerate(ids):
   x,y=new['positions'][str(i)];w,h=leaves[i]['outline_um']
   for j in ids[n+1:]:
    X,Y=new['positions'][str(j)];W,H=leaves[j]['outline_um']
    if x<X+W-1e-6 and x+w>X+1e-6 and y<Y+H-1e-6 and y+h>Y+1e-6:collision.append([i,j])
  assert not collision,collision[:5];new['collisions']=collision;options.append(new)
 best=min(options,key=lambda x:x['outline_um'][0]*x['outline_um'][1]);report=dict(status='ALL640_KNOWN_HARD_RECTANGLES_ONLY_PARENT_HARDWARE_INCOMPLETE',source_commit=inv['source_commit'],source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [a.inventory,a.local,pathlib.Path(__file__)]},source_binding= binding,options=options,smallest_area_option=best['name'],known_gaps=['WFC/XIO serial+stream control logic is actual inline hardware with no hardened outline or pin homes','Parent combinational glue and 32088 input bits not yet uniquely joined to a hard producer','All150 write-edge outlines are source-pin candidate geometry, not current native kits','No whole-die placement/hard-obstacle/clock/PG/cut or static-calendar qualification','All640 hard leaf homes are development assignments; 468 local predecessor rectangles preserve exact current outlines and local vectors'],leaves=[dict(leaf=i,path=x['path'],master=x['master'],outline_um=x['outline_um'],kit=x['kit'])for i,x in enumerate(leaves)])
 a.out.write_text(json.dumps(report,indent=1)+'\n');print(json.dumps([dict(name=x['name'],outline_um=x['outline_um'],placed=x['placed_hard_leaves'],collision_count=len(x['collisions']))for x in options],indent=1))
if __name__=='__main__':main()
