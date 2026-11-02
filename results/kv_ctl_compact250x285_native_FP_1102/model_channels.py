"""Source-net placement estimate and actual-track PG/OBS cut coupon; no CAD/signoff claim."""
import sys,json,gzip,csv,math,re,inspect,collections,os
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O.parents[1]/'tools/autopilot'));import geom_rules as G
C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector')
D=G.Design(str(C/'geom.tsv'),[str(O.parent/'kv_ctl_place_1102/memory_tt.lib')],True);ids={q[6]:i for i,q in D.cells.items()};poses=json.loads(gzip.decompress((O/'FF_sites.json.gz').read_bytes()))
for p in poses:
 i=ids[p['name']];c=D.cells[i];x,y=p['ll_dbu'];w,h=p['size_dbu'];D.cells[i]=tuple([c[0],p['master'],x/1000,y/1000,(x+w)/1000,(y+h)/1000]+list(c[6:]))
old={q['name']:q for q in csv.DictReader(open('/srv/opentallas-scratch/claude/codex-kv-ctl-rowfix-r2-0250/collector/placed.csv'))}
mov=[i for i,c in D.cells.items() if c[0] in ['B','L']];movset=set(mov);macros=[c for c in D.cells.values() if c[0]=='M'];N=max(D.cells)+1;xy=np.zeros((N+len(D.pins),2));size=np.zeros((N,2));fixed=np.ones(len(xy),bool)
for i,c in D.cells.items():
 xy[i]=G.ctr(c);size[i]=[c[4]-c[2],c[5]-c[3]]
 if i in movset:
  fixed[i]=False;p=old.get(c[6]);xy[i]=[(float(p['x'])+float(p['w'])/2)*250.56/371.52,(float(p['y'])+float(p['h'])/2)*285.12/371.52] if p else [125.28,142.56]
pidx={p['k']:N+k for k,p in enumerate(D.pins)}
for p in D.pins:xy[pidx[p['k']]]=[p['x'],p['y']]
aa=[];bb=[];ww=[]
for sig,dr,sk in D.nets:
 if sig in ['CLOCK','POWER','GROUND'] or not dr:continue
 es=[dr]+sk;js=[e[1] if e[0]=='i' else pidx[e[1]] for e in es if (e[0]=='i' and e[1] in D.cells) or(e[0]=='p' and e[1] in pidx)]
 if len(js)<2:continue
 for j in js[1:]:aa.append(js[0]);bb.append(j);ww.append(1/math.sqrt(len(js)-1))
a=np.array(aa);b=np.array(bb);w=np.array(ww);den=np.bincount(a,weights=w,minlength=len(xy))+np.bincount(b,weights=w,minlength=len(xy));seed=xy.copy();move=np.array(mov)
def project():
 xy[move,0]=np.clip(xy[move,0],4.32+size[move,0]/2,246.24-size[move,0]/2);xy[move,1]=np.clip(xy[move,1],4.32+size[move,1]/2,280.8-size[move,1]/2)
 for c in macros:
  x0,y0,x1,y1=c[2]-4.32,c[3]-4.32,c[4]+4.32,c[5]+4.32;x,y=xy[move,0],xy[move,1];sel=(x>x0)&(x<x1)&(y>y0)&(y<y1);q=move[sel]
  if not len(q):continue
  dist=np.array([xy[q,0]-x0,x1-xy[q,0],xy[q,1]-y0,y1-xy[q,1]]);side=dist.argmin(axis=0)
  for k,axis,value in [(0,0,x0),(1,0,x1),(2,1,y0),(3,1,y1)]:xy[q[side==k],axis]=value
for it in range(int(os.environ.get("RELAX_ITERS","0"))):
 for dim in range(2):
  s=np.bincount(a,weights=w*xy[b,dim],minlength=len(xy))+np.bincount(b,weights=w*xy[a,dim],minlength=len(xy));target=(s[move]+.12*seed[move,dim])/(den[move]+.12);xy[move,dim]=.65*target+.35*xy[move,dim]
 project()
project()
for i in mov:
 c=D.cells[i];x,y=xy[i];hw,hh=size[i]/2;D.cells[i]=tuple(list(c[:2])+[x-hw,y-hh,x+hw,y+hh]+list(c[6:]))
rr=G.r2r_metrics(D);pr=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT));
(O/'locality_reach_report.json').write_text(json.dumps(dict(R2R=rr,pins=pr),indent=2)+'\n')
# Modeled combinational coordinates are estimates; no native ODB is written.
base=G.demand_metrics(D);print('MODEL_PROXY',json.dumps(base),flush=True)
# Actual native track coordinates; obstacles expanded by conservative signal spacing+half width.
tracks={q['layer']:q for q in json.load(open(C/'tracks.json'))['tracks']};obs=collections.defaultdict(list);pg=list(csv.DictReader(open(C/'pg_boxes.csv')))
for q in pg:
 layers=[q['layer']] if q['kind']=='metal' else ['M'+x for x in re.findall(r'VIA([1-9])([1-9])',q['via'])[0]] if re.findall(r'VIA([1-9])([1-9])',q['via']) else ['M2','M3','M4','M5']
 for layer in layers:
  if layer not in ['M2','M3','M4','M5']:continue
  margin=27 if layer in ['M2','M3'] else 36
  box=[int(q[k]) for k in ['x0_dbu','y0_dbu','x1_dbu','y1_dbu']];obs[layer].append([box[0]-margin,box[1]-margin,box[2]+margin,box[3]+margin])
for c in macros:
 for layer in ['M2','M3','M4']:
  obs[layer].append([round(c[2]*1000),round(c[3]*1000),round(c[4]*1000),round(c[5]*1000)])
obs={k:np.array(v) for k,v in obs.items()};coupon=[]
def native_cap(direction,cut,nb):
 out=np.zeros(nb);ci=cut*1000
 for layer in (['M3','M5'] if direction=='V' else ['M2','M4']):
  axis='X' if direction=='V' else 'Y';t=np.array(tracks[layer][axis]);rect=obs[layer];cross=(rect[:,1]<ci)&(rect[:,3]>ci) if direction=='V' else (rect[:,0]<ci)&(rect[:,2]>ci);rs=rect[cross];lo,hi=(rs[:,0],rs[:,2]) if direction=='V' else(rs[:,1],rs[:,3]);l=np.searchsorted(t,lo,'left');r=np.searchsorted(t,hi,'right');diff=np.zeros(len(t)+1,dtype=int);np.add.at(diff,l,1);np.add.at(diff,r,-1);free=np.cumsum(diff)[:-1]==0;bins=(t[free]/1000).astype(int);bins=bins[(bins>=0)&(bins<nb)];out+=np.bincount(bins,minlength=nb)*G.TRACK_DERATE
 coupon.append(dict(direction=direction,cut_um=cut,remaining_derated_tracks=float(out.sum())))
 return out
# Same native cut-demand algorithm; replace capacity ONLY with OBS/actual-PG/VIA-clipped actual tracks.
src=inspect.getsource(G.demand_metrics).replace('def demand_metrics(', 'def coupon_demand(').replace('cap = np.full(nb, full * step)','cap = native_cap(d, float(c), nb)')
ns=dict(vars(G));ns['native_cap']=native_cap;exec(src,ns);native=ns['coupon_demand'](D)
report=dict(status='PREP_ESTIMATE_NOT_PLACE_NOT_ROUTE',combinational_model=f'Prior actual DPL scaled seed,{os.environ.get("RELAX_ITERS","0")} source-net barycentric relaxations,macro halo projection; no detailed legalization or routing',moving_comb_cells=len(mov),signal_net_edges=len(a),R2R=rr,pins=pr,base_proxy=base,actual_track_PG_via_clipped_model=native,capacity_cuts=coupon,obstacle_margin_dbu=dict(M2=27,M3=27,M4=36,M5=36),limitations=['Net-box placement estimate only; no capacity PASS from unplaced native cells','Conservative PG via rectangles priced on both connected layers','Signal-signal via/pin access and detail-routing cost still unmeasured'])
(O/'channel_model_PREP.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(native),flush=True)
