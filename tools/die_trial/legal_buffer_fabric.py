#!/usr/bin/env python3
"""Build a fabric repeater successor with explicit macro-free, row-legal sites.
Proxy endpoint flops retain the lane abstract geometry; only new buffer cells
are actual allocated footprints. Review emitted heat map before STA/GRT.
"""
import argparse,collections,json,math,sys,time
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,str(Path(__file__).parent))
import fabric
from legal_sites import RowAllocator

def main():
 a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('--out',type=Path,required=True);z=a.parse_args();out=z.out;out.mkdir(parents=True,exist_ok=True)
 if (out/'fabric.def').exists():raise FileExistsError(out/'fabric.def')
 raw=fabric.S.load(z.plan);P=fabric.S.Plan(raw);cells,nets=fabric.build(P,z.plan.parent);print('ENDPOINTS',len(cells),'NETS',len(nets),flush=True);cells,nets=fabric.insert_repeaters(cells,nets,200,'BUFx12_ASAP7_75t_R');print('WITH_BUFFERS',len(cells),flush=True)
 ht=z.plan.with_name('clock_htree.json');blks=fabric.blockages(P,z.plan.parent,ht if ht.exists() else None);rects=[(a-3.78,b-3.78,c+3.78,d+3.78) for L,a,b,c,d,kind in blks if L=='M4' and kind.split()[0] in ('core','leaf','keepout')];groups=collections.defaultdict(list);fixed=collections.defaultdict(set)
 for n,(x,y,p,k) in cells.items():
  if k.startswith('buf:'):groups[(p,round(x/2.16)*2.16,round(y/.27)*.27)].append(n)
  else:fixed[p].add((round(x,3),round(y,3)))
 alloc={};boxes={};origins={}
 for p in set(k[0] for k in groups):
  x0,y0,x1,y1=P.rect(p);origins[p]=(x0,y0);bb=[r for r in rects if r[0]<x1 and x0<r[2] and r[1]<y1 and y0<r[3]];boxes[p]=[(a-x0,b-y0,c-a,d-b) for a,b,c,d in bb];alloc[p]=RowAllocator((x0+4.32,y0+4.32,x1-4.32,y1-4.32),bb)
  for x,y in fixed[p]:alloc[p].reserve_rectangle((x-.54,y-.135,x+.54,y+.135))
 stats=[];xs=[];ys=[];maximum=0.;start=time.time()
 try:
  for i,((p,x,y),names) in enumerate(sorted(groups.items(),key=lambda kv:(kv[0][0],-len(kv[1])))):
   ox,oy=origins[p];x0,y0,x1,y1=P.rect(p);px,py=alloc[p].project((x,y),clearance=0.);pts,st=alloc[p].allocate((px,py),len(names),max_radius_um=150)
   dist=np.abs(pts[:,0]-x)+np.abs(pts[:,1]-y);maximum=max(maximum,float(dist.max()))
   if dist.max()>750:raise ValueError('buffer moved beyond750um geometric budget')
   for n,(xx,yy) in zip(names,pts):cells[n]=(float(xx),float(yy),p,cells[n][3])
   xs.extend(pts[:,0]);ys.extend(pts[:,1]);stats.append(dict(part=p,count=len(names),max_distance_um=float(dist.max())))
   if i%1000==0:print('ALLOCATED',i,'/',len(groups),'buffers',len(xs),'seconds',round(time.time()-start),flush=True)
 except Exception as e:
  (out/'site_failure.json').write_text(json.dumps(dict(status='FAIL',error=str(e),groups_done=len(stats),buffers_done=len(xs)))+'\n');raise
 # Keep macro detours electrically segmented: allocated sites can otherwise
 # leave a rare long gap when two targets project onto opposite macro edges.
 sys.path.insert(0,str(z.plan.resolve().parent.parent));import cores_b2 as B
 routers={};repaired=[];extra=0
 for i,(name,src,dst,meta) in enumerate(nets):
  aa,bb=cells[src],cells[dst];length=abs(aa[0]-bb[0])+abs(aa[1]-bb[1])
  if length<=650:repaired.append((name,src,dst,meta));continue
  part=aa[2]
  if bb[2]!=part:raise ValueError('long inter-part edge requires plan correction')
  ox,oy=origins[part];x0,y0,x1,y1=P.rect(part)
  if part not in routers:routers[part]=B.RelayRouter(boxes[part],x1-x0,y1-y0,400,margin=5.4)
  path=routers[part]((aa[0]-ox,aa[1]-oy),(bb[0]-ox,bb[1]-oy));previous=src
  for j,(xx,yy) in enumerate(path):
   pts,_=alloc[part].allocate((xx+ox,yy+oy),1,max_radius_um=150);x,y=map(float,pts[0]);nm=f'gapfix_{i}_{j}';cells[nm]=(x,y,part,'buf:BUFx12_ASAP7_75t_R');xs.append(x);ys.append(y);repaired.append((f'{name}_gap{j}',previous,nm,meta));previous=nm;extra+=1
  repaired.append((name+'_last',previous,dst,meta))
 nets=repaired
 maxgap=max(abs(cells[a][0]-cells[b][0])+abs(cells[a][1]-cells[b][1]) for _,a,b,_ in nets)
 if maxgap>750:raise ValueError(f'buffer segment{maxgap}um exceeds750um')
 print('GAPFIX',extra,'MAX',maxgap,flush=True)
 print('WRITING_DEF',flush=True);root=P.clock.get('spine',{}).get('root_um') or [P.W/2,P.H/2];fabric.write_def(P,out/'fabric.def',cells,nets,blks,root);(out/'fabric.tcl').write_text(fabric.tcl(P,.5,30,True,False).replace('set_routing_layers -signal M4-M9','set_routing_layers -signal M8-M9'));(out/'run.sh').write_text(fabric.RUN.format(image=fabric.IMAGE,threads=16,mem=192));
 fig,ax=plt.subplots(figsize=(14,10));h,xedges,yedges=np.histogram2d(xs,ys,bins=(max(1,int(P.W/100)),max(1,int(P.H/100))),range=((0,P.W),(0,P.H)));im=ax.imshow(h.T,origin='lower',extent=(0,P.W,0,P.H),cmap='magma',aspect='equal');fig.colorbar(im,ax=ax,label='new legal buffer cells /100um bin')
 for a,b,c,d in rects:ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,lw=.15,color='cyan'))
 ax.set_title('B2l explicit macro-free BUF12 sites; endpoint flops remain abstract');fig.savefig(out/'buffer_sites.png',dpi=150)
 lens=[abs(cells[a][0]-cells[b][0])+abs(cells[a][1]-cells[b][1]) for _,a,b,_ in nets];(out/'summary.json').write_text(json.dumps(dict(status='REVIEW REQUIRED before STA/GRT',plan=str(z.plan),cells=len(cells),nets=len(nets),buffers=len(xs),placement_keepouts=len(rects),macro_clearance_um=3.78,gapfix_buffers=extra,site_groups=len(stats),max_buffer_displacement_um=maximum,actual_signal_segment_max_um=max(lens),actual_signal_segment_p90_um=float(np.percentile(lens,90)),clock='idealcommon; notphysicalclosure',added_register_cycles=0,signal_layers='M8-M9',proxy_endpoint_flops='unchanged abstractions; not full standard-cell legalization'),indent=1)+'\n');print('SITE_ASSIGNMENT_DONE',len(xs),flush=True)
if __name__=='__main__':main()
