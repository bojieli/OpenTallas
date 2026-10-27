#!/usr/bin/env python3
"""Materialize an S81 graded mesh as legal physical parallel rails and real driver cells.

Geometry preparation only. RC coupling, extraction, EM/IR and timing remain gates.
The historical single128w stripe exceeds ASAP7 MAXWIDTH and is not emitted.
"""
import argparse,collections,copy,hashlib,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parents[1]/'die_plan';sys.path.insert(0,str(HERE))
import die_clock_mesh as D,die_clock as DC,schema as S

def width_at(x,y,rx,ry,peak=128,band=4000):
 d=min(abs(x-rx),abs(y-ry)); target=4 if d>=band else max(4,round((4+(peak-4)*(1-d/band))/4)*4)
 # 3 equal rails; 80nm steps make each width transition's half-step >= MINSTEP40nm.
 return round(math.ceil(target*.04/3/.08-1e-9)*.08,6),target

def axis(v,pitch=8.64):
 # Existing PG centres are4.32+k*8.64, width.48. Worst rail1.76 has1um clearance.
 # Choose the nearest real80nm track that leaves that clearance on BOTH sides.
 candidates=[round(.04+round((v-.04)/.08)*.08+k*.08,6) for k in range(-55,56)]
 good=[q for q in candidates if abs(q-round(q/pitch)*pitch)+.88+.24+1.0<=pitch/2+1e-6]
 if not good:raise ValueError('no PG-safe rail track')
 return min(good,key=lambda q:(abs(q-v),q))

def blocked(K,c):
 r=(c['x'],c['y'],c['x']+D.BUF_W,c['y']+D.ROW_Y)
 for i in range(math.floor(r[0]/K.b),math.floor(r[2]/K.b)+1):
  for j in range(math.floor(r[1]/K.b),math.floor(r[3]/K.b)+1):
   for b in K.g.get((i,j),[]):
    if min(r[2],b[2])>max(r[0],b[0])+1e-6 and min(r[3],b[3])>max(r[1],b[1])+1e-6:return True
 return False

def cluster(x,y,count,cols):
 rows=math.ceil(count/cols)
 x0=D.snap(x-(cols-1)*D.BUF_W/2-D.BUF_W/2,D.SITE_X);y0=D.snap(y-(rows-1)*D.ROW_Y/2-D.ROW_Y/2,D.ROW_Y)
 return [dict(x=round(x0+(i%cols)*D.BUF_W,6),y=round(y0+(i//cols)*D.ROW_Y,6),kind='drv') for i in range(count)]

def materialize(plan,build,out,peak=128,band=4000):
 P=S.Plan(S.load(plan),str(plan));src=Path(build);dst=Path(out);dst.mkdir(parents=True,exist_ok=True)
 M=json.load(open(src/'mesh.json'));cells=json.load(open(src/'place.json'));N=json.load(open(src/'nets.json'));nets=N['nets'];ports=N['ports']
 olddrivers={u for d in M['drivers'].values() for u in d['cells']};new={n:copy.deepcopy(c) for n,c in cells.items() if n not in olddrivers}
 ko=list(DC.keepouts(P))+D.ft_halo_keepouts(P);K=DC.KeepIndex(ko,die=(P.W,P.H))
 for n,c in new.items():D.reserve_cell(K,n,c)
 incoming={ld:n for n in nets for ld in n['loads'] if ld in cells};replace={};fail=[];banks=[]
 rx,ry=M['meta'].get('root_xy',[P.W/2,P.H/2]);rx,ry=M['htree'][0]['a'] if M.get('htree') else (rx,ry)
 for key,d in M['drivers'].items():
  old=d['cells'];x,y=d.get('cell_site',d['site']);railw,target=width_at(x,y,rx,ry,peak,band)
  # Cap accounting is explicit3-rail inventory, not an R/rails timing claim.
  cf=3*.9+.0875*(3*railw/.04);basecf=.9+.0875*4;k=math.ceil(cf/basecf-1e-9);count=len(old)*k
  parentset={incoming[u]['drv'] for u in old};assert len(parentset)==1;parent=next(iter(parentset));py=D.C128.pin_xy(cells,parent,'Y',D.ROW_Y)
  picked=None;shift=0.;cols=0
  for dy in [0.]+[v*D.ROW_Y for j in range(1,186) for v in (j,-j)]:
   xx,yy=(x+dy,y) if d['strap']=='M8' else (x,y+dy)
   for nc in sorted({min(count,6),min(count,4),min(count,2),1,count},key=lambda nc:(math.ceil(count/nc)>4,abs(nc-math.sqrt(count)),nc)):
    cs=cluster(xx,yy,count,nc)
    if any(blocked(K,c) for c in cs):continue
    if any(abs(py[0]-(c['x']+.027))+abs(py[1]-(c['y']+.135))>405+1e-6 for c in cs):continue
    picked,shift,cols=cs,dy,nc;break
   if picked is not None:break
  if picked is None:picked=cluster(x,y,count,min(count,6));fail.append(key)
  names=[]
  for j,c in enumerate(picked):
   name=f'gb_{key}_{j}';names.append(name);new[name]=c;D.reserve_cell(K,name,c)
  replace.update({u:(names if i==0 else []) for i,u in enumerate(old)})
  d['cells']=names;d['physical_rail_width_um']=railw;d['physical_bank']=dict(rows=math.ceil(count/cols) if cols else None,cols=cols,shift_um=shift)
  banks.append(dict(site=key,anchor_um=d['site'],centre_um=[x,y],old_units=len(old),units=count,rail_width_um=railw,target_multiple=target,cap_proxy=cf,parent=parent,legal=key not in fail,cols=cols,shift_um=shift))
 for n in nets:n['loads']=[v for ld in n['loads'] for v in replace.get(ld,[ld])]
 # Explicit legal rails, interleaved with existing PG. Three rails at adjacent PG gaps.
 xs=[axis(v) for v in M['xs']];ys=[axis(v) for v in M['ys']];vx=sorted(v+j*8.64 for v in xs for j in (-1,0,1));hy=sorted(v+j*8.64 for v in ys for j in (-1,0,1))
 attachments=[]
 for b in banks:
  d=M['drivers'][b['site']];x,y=b['centre_um'];shift=b['shift_um']
  layer=d['strap'];xx,yy=(x+shift,y) if layer=='M8' else (x,y+shift)
  at=[xx,min(hy,key=lambda z:abs(z-yy))] if layer=='M8' else [min(vx,key=lambda z:abs(z-xx)),yy]
  attachments.append(dict(role='driver',net='ck_mesh',units=d['cells'],pin='Y',layer=layer,xy_um=at))
 for name,c in new.items():
  if c['kind']!='stub':continue
  px,py=D.C128.pin_xy(new,name,'A',D.ROW_Y);xx=min(vx,key=lambda z:abs(z-px));yy=min(hy,key=lambda z:abs(z-py))
  layer='M8' if abs(yy-py)<=abs(xx-px) else 'M9';at=[px,yy] if layer=='M8' else [xx,py]
  attachments.append(dict(role='local_tree_input',net='ck_mesh',units=[name],pin='A',layer=layer,xy_um=at))
 segments=[];via=[]
 for y in hy:
  for x0,x1 in zip(vx,vx[1:]):
   w,t=width_at((x0+x1)/2,y,rx,ry,peak,band);segments.append(dict(layer='M8',rect_um=[round(x0,6),round(y-w/2,6),round(x1,6),round(y+w/2,6)],width_um=w,centre_um=[x0,y,x1,y],target_multiple=t))
 for x in vx:
  for y0,y1 in zip(hy,hy[1:]):
   w,t=width_at(x,(y0+y1)/2,rx,ry,peak,band);segments.append(dict(layer='M9',rect_um=[round(x-w/2,6),round(y0,6),round(x+w/2,6),round(y1,6)],width_um=w,centre_um=[x,y0,x,y1],target_multiple=t))
 for x in vx:
  for y in hy:
   # Minimum adjacent wire width governs the array. Every crossing is physically connected.
   w,_=width_at(x,y,rx,ry,peak,band);n=max(1,int(math.floor((w-.08)/.098+1e-8))+1)
   via.append(dict(x_um=round(x,6),y_um=round(y,6),rows=n,cols=n,cut_um=.04,pitch_um=.098,pad_um=round(.08+(n-1)*.098,6)))
 D.write_verilog(new,nets,ports,dst/'ctree.v')
 hard=D.hard_keepout_violations(P,new);over=D.placement_overlaps(new);hop=D.actual_clock_hop_violations(new,nets,405)
 ft=D._body_keepout_violations(DC.KeepIndex(D.ft_halo_keepouts(P)),P.W,P.H,new)
 report=dict(status='BLOCKED_PHYSICAL_GEOMETRY' if (hard or ft or over or hop or fail) else 'GEOMETRY_READY_PENDING_METAL_CENSUS',source_plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),base_build=str(src),rail_count=3,peak_target_multiple=peak,rail_max_um=max(s['width_um'] for s in segments),tech_maxwidth_um=2.0,rail_pitch_um=8.64,pg_width_um=.48,long_prl_min_spacing_um=1.0,minstep_um=.04,segments=len(segments),crossings=len(via),via_cut_count=sum(v['rows']*v['cols'] for v in via),old_driver_units=len(olddrivers),actual_driver_units=sum(b['units'] for b in banks),bank_sites=len(banks),unplaced_banks=fail,hardbody_hits=len(hard),ft_halo_hits=len(ft),clock_overlap_pairs=len(over),actual_pin_hop_failures=len(hop),max_bad_pin_hop_um=max([h['span_um'] for h in hop]or[0]),limitations=['No equivalent R divided by rail count is used.','Rail coupling/crossconnects require extraction on this exact topology.','PG-clearance proof currently covers uniform declared8.64um M8/M9 grid; local-domain shapes and tree wires still require actual metal census.','EM/IR, current endpoint views and die timing remain OPEN.','No P&R or timing approval is implied.'])
 M['meta']['physical_encoder_qualified']=False;M['legacy_base_fixed_wires']=M.pop('fixed_wires',[]);M['clock_hard_keepout_violations']=hard;M['clock_actual_hop_violations']=hop;M['clock_ft_keepout_violations']=ft;M['clock_cell_overlaps']=over;M['meta']['graded_physical']=report;M['meta']['plan_sha256']=report['source_plan_sha256'];M['meta']['cells']=len(new);M['meta']['bufx24_drivers']=report['actual_driver_units']
 for fn,obj in [('place.json',new),('nets.json',dict(nets=nets,ports=ports)),('mesh.json',M),('graded_metal.json',dict(segments=segments,vias=via,xs=vx,ys=hy,root_xy=[rx,ry],attachments=attachments)),('banks.json',banks),('REPORT.json',report),('body_failures.json',hard),('hop_failures.json',hop)]: (dst/fn).write_text(json.dumps(obj,separators=(',',':'))+'\n')
 print(json.dumps(report,indent=1))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--plan',required=True);ap.add_argument('--build',required=True);ap.add_argument('--out',required=True);ap.add_argument('--peak',type=int,default=128);ap.add_argument('--band',type=float,default=4000);a=ap.parse_args();materialize(a.plan,a.build,a.out,a.peak,a.band)
