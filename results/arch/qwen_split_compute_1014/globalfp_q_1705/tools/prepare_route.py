import sys,json,copy,math,collections,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,'/home/ubuntu/artifacts/globalfp/qwen/recovery-1325/recovered-source');import gfp_core as C
p=Path(sys.argv[1]);die=C.Die(p);C.attach_ports(die);h=json.load(open(sys.argv[2]));m=copy.deepcopy(die.base)
for n,v in h['homes'].items():
 for k in ('x','y','o'):m[n][k]=v[k]
out=Path(sys.argv[3]);out.mkdir(exist_ok=True);B=float(sys.argv[4]) if len(sys.argv)>4 else 125.;nx=math.ceil(die.die['w']/B);ny=math.ceil(die.die['h']/B);N=nx*ny;rcm=die.d.get('routing_capacity_model');actual_adj=max(rcm['regional_layer_adjustment'][r['kind']] for r in rcm['regions']) if rcm else .3778;CAPFREE=(1/.064+1/.080)*(1-actual_adj);CAPMAC=(1/.080)*(1-actual_adj);gate=float(sys.argv[5]) if len(sys.argv)>5 else .5
phy_mode=sys.argv[6] if len(sys.argv)>6 else 'blocked';allowed_phy={'ot_qfd_ucie_x64_phy','ot_qfd_serdes_112g_x12_phy_s597'} if phy_mode=='actual_bound_io' else set();phyrect=np.array([[i['x'],i['y'],i['x']+i['w'],i['y']+i['h']] for i in m.values() if 'phy' in i['m'].lower() and i['m'] not in allowed_phy]);io_upper_rect=np.array([[i['x'],i['y'],i['x']+i['w'],i['y']+i['h']] for i in m.values() if i['m'] in allowed_phy]);phy_obs_receipt=json.load(open(Path(__file__).resolve().parents[1]/'actual-bound-PHY-OBS-audit.json')) if allowed_phy else None
# Exact occupied length along each grid cut, using rectangle union rather than bin-area averaging.
rects=np.array([[i['x'],i['y'],i['x']+i['w'],i['y']+i['h']] for i in m.values()]);caps=[];edge_meta=[]
def union_len(intervals):
 if not intervals:return 0
 intervals.sort();s=0;lo,hi=intervals[0]
 for a,b in intervals[1:]:
  if a<=hi:hi=max(hi,b)
  else:s+=hi-lo;lo,hi=a,b
 return s+hi-lo
# Cell index x*ny+y; edges horizontal first, then vertical. Full boundary windows truncated at dieedge.
for direction in ['H','V']:
 for ix in range(nx-(direction=='H')):
  for iy in range(ny-(direction=='V')):
   cut=(ix+1)*B if direction=='H' else(iy+1)*B;lo=iy*B if direction=='H' else ix*B;hi=min(lo+B,die.die['h'] if direction=='H' else die.die['w']);axis=0 if direction=='H' else 1;cross=(rects[:,axis]<cut-1e-5)&(rects[:,axis+2]>cut+1e-5);rs=rects[cross];ints=[(max(lo,r[1-axis]),min(hi,r[3-axis])) for r in rs if min(hi,r[3-axis])>max(lo,r[1-axis])];occ=union_len(ints);phyints=[(max(lo,r[1-axis]),min(hi,r[3-axis])) for r in phyrect if r[axis]<cut-1e-5 and r[axis+2]>cut+1e-5 and min(hi,r[3-axis])>max(lo,r[1-axis])];phyocc=union_len(phyints);ioints=[(max(lo,r[1-axis]),min(hi,r[3-axis])) for r in io_upper_rect if r[axis]<cut-1e-5 and r[axis+2]>cut+1e-5 and min(hi,r[3-axis])>max(lo,r[1-axis])];ioocc=union_len(ioints);cap=(hi-lo-occ)*CAPFREE+max(0,occ-phyocc)*CAPMAC+ioocc*(CAPFREE-CAPMAC);u=ix*ny+iy;v=(ix+(direction=='H'))*ny+iy+(direction=='V');line_lo=(ix+.5)*B if direction=='H' else (iy+.5)*B;line_hi=line_lo+B;cross_center=(lo+hi)/2
   if any(r[1-axis]<cross_center<r[3-axis] and min(line_hi,r[axis+2])>max(line_lo,r[axis])+1e-5 for r in phyrect):cap=0
   caps.append((u,v,math.floor(cap*gate+1e-8),max(.0,occ/(hi-lo))));edge_meta.append((direction,ix,iy,cut,lo,hi,cap,occ))
def grid_center(q):return np.array([(q//ny*B+min((q//ny+1)*B,die.die['w']))/2,(q%ny*B+min((q%ny+1)*B,die.die['h']))/2])
def node(pt):
 ix=min(nx-1,max(0,int(pt[0]//B)));iy=min(ny-1,max(0,int(pt[1]//B)));q=ix*ny+iy;cc=grid_center(q)
 for r in phyrect:
  if r[0]<cc[0]<r[2] and r[1]<cc[1]<r[3]:
   side=int(np.argmin([abs(pt[0]-r[0]),abs(pt[0]-r[2]),abs(pt[1]-r[1]),abs(pt[1]-r[3])]))
   if side==0:ix=max(0,math.ceil(r[0]/B-.5)-1)
   elif side==1:ix=min(nx-1,math.floor(r[2]/B-.5)+1)
   elif side==2:iy=max(0,math.ceil(r[1]/B-.5)-1)
   else:iy=min(ny-1,math.floor(r[3]/B-.5)+1)
   q=ix*ny+iy;cc=grid_center(q)
 return q
# 64-bit physical pin bundles: exact bit count and endpoint pin centroids; every current bit represented.
nets=[];local_groups=[];recs=die.recs+die.ctrl;original=[]
for ri,r in enumerate(recs):
 pts=C.bus_geom(r,m)[4];n=r['n'];original.append({'bus':r['b'],'class':r['c'],'bits':n,'ports':list(zip([n for n,_ in r['ends']],r['port']))})
 lo=0
 while lo<n:
  nodevec=tuple(node(pt) for pt in pts[:,lo]);z=lo+1
  while z<min(n,lo+64) and tuple(node(pt) for pt in pts[:,z])==nodevec:z+=1
  coords=pts[:,lo:z].mean(1);terms=list(dict.fromkeys(nodevec));stubs=[]
  for j,q in enumerate(nodevec):
   center_point=grid_center(q);stubs.append(float(np.abs(pts[j,lo:z]-center_point).sum(1).max()))
  rec={'rid':ri,'lo':lo,'bits':z-lo,'terms':terms,'endpoint_nodes':list(nodevec),'coordinates_um':coords.round(6).tolist(),'max_endpoint_stub_um':stubs,'priority':1000000000 if r['b']=='bword_5' else r['n']}
  (nets if len(terms)>1 else local_groups).append(rec);lo=z
# Wide producer interfaces first; clock/reset/control later. Ties stable preserve provenance.
nets.sort(key=lambda n:(-n['priority'],n['rid'],n['lo']))
with open(out/'route.in','w') as f:
 f.write(f'{nx} {ny} {B} {len(caps)} {len(nets)}\n')
 for u,v,cap,occ in caps:f.write(f'{u} {v} {cap} {occ:.6f}\n')
 for k,n in enumerate(nets):f.write(f'{k} {n["bits"]} {len(n["terms"])} '+ ' '.join(map(str,n['terms']))+'\n')
meta={'source_graph_sha256':die.sha,'source_model_sha256':die.d['source_model_sha256'],'candidate':h['candidate'],'allocation_target':gate,'physical_gate':.6,'phy_overmacro_routing_capacity':{'mode':phy_mode,'known_IO_M6_to_M9_allowed_above':sorted(allowed_phy),'all_other_PHY_capacity':0,'actual_bound_view_audit':phy_obs_receipt,'PHY_bodies_forbidden_relay_sites':True},'actual_global_layers':{'M2_M3_M4_M5_adjustment':1.0,'free_H':['M6','M8'],'free_V':['M7','M9'],'free_tracks_per_um_before_PG':28.125,'worst_regional_reduction_used_everywhere':actual_adj,'actual_source_contract':rcm,'free_tracks_per_um_after_PG':CAPFREE,'overmacro_tracks_per_um_after_PG':CAPMAC,'OBS_assumption':'NonPHY obs_top<=7; actual export required. PHY allupperlayers blocked.'},'over_nonphy_macro_capacity_assumption':'M8 per horizontal direction/M9 per vertical direction, actual OBS/PG still required','grid_um':B,'nx':nx,'ny':ny,'grid_centers_x':[(x*B+min((x+1)*B,die.die['w']))/2 for x in range(nx)],'grid_centers_y':[(y*B+min((y+1)*B,die.die['h']))/2 for y in range(ny)],'edge_metadata':edge_meta,'nets':nets,'local_groups':local_groups,'buses':original,'data_bus_count':len(die.recs),'source_pins_missing':die.g.missing,'total_source_bus_bits':sum(r['n'] for r in recs),'scope':'All current data, clock and reset buses, represented in <=64-bit pin bundles; same-cell local pin access is not a global route edge. No detailed routing or physical-clock proof.'};(out/'route-metadata.json').write_text(json.dumps(meta,separators=(',',':'))+'\n');print('prepared',len(caps),'edges',len(nets),'nonlocal64b nets',flush=True)
