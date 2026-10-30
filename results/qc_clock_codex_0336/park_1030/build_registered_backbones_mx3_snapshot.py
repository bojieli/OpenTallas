import json,math,gzip,sys
from pathlib import Path
mode=sys.argv[1] if len(sys.argv)>1 else 'MX3';N=3 if mode=='MX3' else 9;R=Path('/tmp/qcclock0336');src=json.load(open(R/('serdes_mx_return_option.json' if mode=='MX3' else 'collar_geometry_prep.json')));bits=[b for b in src['bits'] if b.get('type','phy_serdes_b')=='phy_serdes_b'];site=.054;row=.54
softlo,softhi=(2.16,66.96) if mode=='MX3' else(2322.216,2391.12)
def tracks(layers,lo,hi):
 out=[]
 for layer,pitch in layers:
  raw=[pitch/2+i*pitch for i in range(math.ceil((lo-pitch/2)/pitch),math.floor((hi-pitch/2)/pitch)+1)];chosen=[(layer,v) for i,v in enumerate(raw) if i%5 in[0,2,4]][:math.floor(.6*len(raw))];out+=chosen
 return sorted(out,key=lambda a:(a[1],a[0]))
H=tracks([('M4',.048),('M6',.064)],softlo+.135,softhi-.135);H=[t for t in H if round((t[1]-.1845)/row)*row>=softlo and round((t[1]-.1845)/row)*row+.27<=softhi];V=tracks([('M5',.048),('M7',.064)],1568.22,1629.18)
assert len(H)>=1197 and len(V)>=1197
choose=lambda a,n:[a[math.floor(i*len(a)/n)] for i in range(n)]
Hs=choose(H,1197);Vs=choose(V,1197);Hs=Hs[::-1] if mode=='MX3' else Hs
key=lambda b:(b['bus'],b['bit']);paths={};hmap={key(b):t for b,t in zip(sorted(bits,key=lambda b:(-b.get('wire_um',b.get('length_um',sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(b['polyline_um'],b['polyline_um'][1:])))),b['bus'],b['bit'])),Hs)};vmap={key(b):t for b,t in zip(sorted(bits,key=lambda b:(b['polyline_um'][-1][1],b['bus'],b['bit'])),Vs)}
for b in bits:
 native=b['polyline_um'][0];outer=b['polyline_um'][-1];hl,hy=hmap[key(b)];vl,vx=vmap[key(b)];pp=[native,[native[0],hy],[vx,hy],[vx,outer[1]],outer];paths[key(b)]={'path':pp,'H':(hl,hy),'V':(vl,vx),'outer':outer,'native':native}
free={}
for yi in range(math.ceil(2.16/row),math.floor((2391.12-.27)/row)+1):
 y=yi*row;soft=(y+.27<=66.96) if mode=='MX3' else(y>=2322.216);xlo=2.16 if soft else 1566
 free[yi]=[(math.ceil(xlo/site),math.floor(1630.8/site))]
cells=[]
def remove(intervals,xi,w):
 new=[];found=False
 for lo,hi in intervals:
  if lo<=xi and xi+w<=hi:
   if lo<xi:new.append((lo,xi))
   if xi+w<hi:new.append((xi+w,hi))
   found=True
  else:new.append((lo,hi))
 if not found:raise ValueError('reserveoutside')
 return new

def nearest_x(ivals,w,wanted,lo_limit=-1e20,hi_limit=1e20):
 options=[]
 for lo,hi in ivals:
  lo=max(lo,math.ceil(lo_limit/site));hi=min(hi,math.floor(hi_limit/site)+w)
  if hi-lo>=w:
   xi=max(lo,min(hi-w,round(wanted/site)));options.append((abs(xi*site-wanted),xi))
 return min(options)[1] if options else None

def place(x,y,w,kind,ident,fixrow=None,fixx=None,xlo=-1e20,xhi=1e20,ylim=35,evenrow=False,pin_target=None):
 desiredy=round(y/row);best=None
 ys=[fixrow] if fixrow is not None else range(desiredy-math.ceil(ylim/row),desiredy+math.ceil(ylim/row)+1)
 for yi in ys:
  if yi not in free or evenrow and yi%2:continue
  if abs(yi*row-y)>ylim:continue
  xi=nearest_x(free[yi],w,x,xlo,xhi) if fixx is None else fixx
  if xi is None:continue
  if fixx is not None and not any(lo<=xi and xi+w<=hi for lo,hi in free[yi]):continue
  if pin_target is not None:
   px,py=pin_target;xx=xi*site;yy=yi*row
   if max(abs(xx+.262-px)+abs(yy+.135-py),abs(xx+1.037-px)+abs(yy+.234-py))>30:continue
  score=abs(xi*site-x)+abs(yi*row-y)
  if best is None or(score,yi,xi)<best:best=(score,yi,xi)
 if best is None:raise ValueError(('NO_SPACE',ident,x,y,w,fixrow,fixx))
 score,yi,xi=best;free[yi]=remove(free[yi],xi,w);rec={'id':ident,'kind':kind,'origin_um':[xi*site,yi*row],'reserved_bbox_um':[xi*site,yi*row,(xi+w)*site,(yi+1)*row],'anchor_shift_L1_um':score};cells.append(rec);return rec

def point(path,t):
 lens=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:])];d=sum(lens)*t
 for i,(a,b,ll) in enumerate(zip(path,path[1:],lens)):
  if ll and d<=ll:return[a[0]+(b[0]-a[0])*d/ll,a[1]+(b[1]-a[1])*d/ll],i
  d-=ll
 return path[-1],3
ff={}
for j in range(1,N+1):
 for b in bits:
  k=key(b);p=paths[k];total=sum(abs(a[0]-z[0])+abs(a[1]-z[1])for a,z in zip(p['path'],p['path'][1:]));ideal,seg=point(p['path'],1 if j==N else j*360/total);hy=p['H'][1];vx=p['V'][1];ident=f'b{j}.{k[0]}[{k[1]}]'
  if j==N:
   targetx=max(1609.04,min(1628.28,vx-1.07));c=place(targetx-1.128,ideal[1]-.135,67,'DATA_FF_INV_LAUNCH24',ident,xlo=1609.04-1.128,xhi=1628.28-1.128,ylim=7.0,evenrow=True,pin_target=p['outer'])
  elif seg==1:
   yy=round((hy-.1845)/row);c=place(ideal[0]-1.128,yy*row,67,'DATA_FF_INV_LAUNCH24',ident,fixrow=yy)
  elif seg==2:
   xx=round((vx-2.198)/site);c=place(xx*site,ideal[1]-.135,67,'DATA_FF_INV_LAUNCH24',ident,fixx=xx)
  else:raise ValueError(('unexpectedstage',j,seg))
  x,y=c['origin_um'];c.update(input_A_um=[x+1.128,y+.135],reg_D_um=[x+.262,y+.135],reg_QN_um=[x+1.037,y+.234],launch_A_um=[x+1.290,y+.135],launch_Y_um=[x+2.198,y+.234],clk_um=[x+.108,y+.2]);ff[(j,k)]=c
# Existing counts are real control/epoch footprint reserves; separate functionalmapping remainsHOLD.
for j in range(1,N+1):
 rr=[v for (jj,k),v in ff.items() if jj==j];anchor=[sum(c['origin_um'][k] for c in rr)/len(rr) for k in[0,1]]
 for e in range(5):place(*anchor,78,'EPOCH_ASR_INV_TIE_LAUNCH24',f'b{j}.epoch{e}')
 for c in range(6):place(*anchor,33,'CONTROL_FF_LOGIC',f'b{j}.control{c}')
# Place each wire repeater on its bit's fixed H-row or V-column; only primaryaxis moves.
wirebuf={};placement_fails=[]
for j in range(1,N+1):
 for b in bits:
  k=key(b);p=paths[k];prev=ff.get((j-1,k));cur=ff[(j,k)];start=p['native'] if prev is None else prev['launch_Y_um'];end=cur['input_A_um'];hy=p['H'][1];vx=p['V'][1]
  # Useactualroutebackbones, no diagonalshortcut.
  end_onH=abs(end[1]-hy)<1;start_onH=abs(start[1]-hy)<1
  if end_onH and (start_onH or j==1):pp=[start,[start[0],hy],[end[0],hy],end]
  elif start_onH or j==1:pp=[start,[start[0],hy],[vx,hy],[vx,end[1]],end]
  else:pp=[start,[vx,start[1]],[vx,end[1]],end]
  chain=[]
  for ri,t in enumerate([.2,.4,.6,.8]):
   ideal,seg=point(pp,t)
   if j==1 and seg==0:ideal=[p['native'][0],hy]
   if abs(ideal[1]-hy)<1e-6 and (mode=='N9' and hy>=2322.216 or mode=='MX3' and hy<=66.96):
    yi=round((hy-.1845)/row);c=place(ideal[0]-.048,yi*row,38,'DATA_WIRE_BUF24',f'{k}.h{j}.r{ri}',fixrow=yi)
   else:
    xx=round((vx-.5)/site);c=place(xx*site,ideal[1]-.135,38,'DATA_WIRE_BUF24',f'{k}.h{j}.r{ri}',fixx=xx)
   x,y=c['origin_um'];c.update(A_um=[x+.048,y+.135],Y_um=[x+.956,y+.234]);chain.append(c)
  wirebuf[(j,k)]=chain
# Actualdirectedroutes viafixedbackbone; verticallegtransitionskeepprimarydirection.
def wire_route(a,b,p):
 hy=p['H'][1];vx=p['V'][1];nat=p['native']
 isnat=lambda q:abs(q[0]-nat[0])+abs(q[1]-nat[1])<1e-6
 if isnat(a):return[a,[a[0],hy],[b[0],hy],b]
 if isnat(b):return[a,[a[0],hy],[b[0],hy],b]
 if abs(a[1]-hy)<1 and abs(b[1]-hy)<1:return[a,[a[0],hy],[b[0],hy],b]
 if a[0]>=1566 and b[0]>=1566:return[a,[vx,a[1]],[vx,b[1]],b]
 if abs(a[1]-hy)<1:return[a,[a[0],hy],[vx,hy],[vx,b[1]],b]
 return[a,[vx,a[1]],[vx,hy],[b[0],hy],b]
rows=[]
for j in range(1,N+1):
 for b in bits:
  k=key(b);p=paths[k];rev=k[0]in['tx_flit','tx_v'];a=ff[(j,k)];prev=ff.get((j-1,k));src=a['launch_Y_um'] if rev else(prev['launch_Y_um'] if prev else p['native']);dest=(prev['input_A_um'] if prev else p['native']) if rev else a['input_A_um'];chain=wirebuf[(j,k)][::-1] if rev else wirebuf[(j,k)];total=0;maximum=0;cur=src;pieces=[]
  for c in chain:
   pp=wire_route(cur,c['A_um'],p);ll=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pp,pp[1:]));total+=ll;maximum=max(maximum,ll);pieces.append(pp);cur=c['Y_um']
  pp=wire_route(cur,dest,p);ll=sum(abs(a[0]-z[0])+abs(a[1]-z[1]) for a,z in zip(pp,pp[1:]));total+=ll;maximum=max(maximum,ll);pieces.append(pp);total+=(0 if not rev and prev is None else .352)+(0 if rev and prev is None else 1.036);rows.append({'bus':k[0],'bit':k[1],'hop':j,'actual_total_wire_um':total,'maximum_wire_section_um':maximum,'pieces':pieces})
summary={'mode':mode,'status':'JOINT FIXED BACKBONE CONSTRUCTION PREP; no nativeadoption/RTL/STA','dataFF':N*1197,'station_pitch_um':360,'station_pitch_rule':'Historical MX3 snapshot360um; superseded construction source retains354.24um row-commensurate pitch','dataFF_group':'DFFHQN+inputINV+adjacentlaunchBUF24, width2.862 actual /3.618reserved onR0','launch_BUF24':N*1197,'wire_BUF24':N*1197*4,'max_total_wire_um':max(z['actual_total_wire_um']for z in rows),'hops_over405':sum(z['actual_total_wire_um']>405 for z in rows),'max_wire_section_um':max(z['maximum_wire_section_um']for z in rows),'hops_with_section_over120':sum(z['maximum_wire_section_um']>120 for z in rows),'max_cell_anchor_shift_um':max(c['anchor_shift_L1_um']for c in cells),'max_original_trackpath_um':max(sum(abs(a[0]-z[0])+abs(a[1]-z[1])for a,z in zip(p['path'],p['path'][1:]))for p in paths.values()),'body_clear':'Nativebody excluded, allrowsR0 x54nm/y540nm; fullgroupactualmaster footprint40pct reserve','HOLD':['sourceCLKanddataCQ/DRVfullpropagation','actualnonmonotonicroutebugsifany','clock/control/reset/epochfunctionalpathsandtap/PG','CBWFT/CApairedsourceevent','rootownerphysicalorientationchoice']}
out={'summary':summary,'cells':cells,'paths':[{**p,'key':k}for k,p in paths.items()],'hops':rows};gzip.open(R/f'{mode}_fixed_backbones.json.gz','wt').write(json.dumps(out,separators=(',',':')));(R/f'{mode}_fixed_backbones_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
