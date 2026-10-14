import json,re,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
R=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(R/'tools/hier_contract'));import pinreg_audit as A
p=json.load(open(R/'results/arch/qwen_tp8_1012/vm_rg6.json')); C=dict(zip(p['core_names'],p['children'][:72])); cache={}; reports=[]; stations=[]
def view(v):
 if v in cache:return cache[v]
 v=R/v; ins=json.load(open(v/'insertion.json')); txt=next(v.glob('*.lef')).read_text(); pins={}
 for m in re.finditer(r'\bPIN\s+(\S+)(.*?)\n\s*END\s+\1\s',txt,re.S):
  rr=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',m[2])
  if rr:x,y,X,Y=map(float,rr.groups());pins[m[1]]=np.array([(x+X)/2,(y+Y)/2])
 metrics={}
 for co in ['tt','ff','ss']:
  lib=A.parse_lib(v/(v.name+'_'+co+'.lib')); ck=next(n for n,q in lib['pins'].items() if q['clock']); data=ins.get('clock_measurements',{}).get(ck,ins);ref=data[co]['boundary']['mean'];metrics[co]=A.pin_metrics(lib,{ck:{'rise':ref,'fall':ref}})
 cache[str(v.relative_to(R))]=(pins,metrics);return pins,metrics
D=str(next((R/'physical/ref_tile').glob('*/views/ot_qwen_tree_delay1_t')).relative_to(R)); dp,dm=view(D);dnames=[f'd[{i}]' for i in range(512)];qnames=[f'q[{i}]' for i in range(512)]
def assign(sc,snames,tc,tnames,at):
 sp,sm=view(sc['view']); tp,tm=view(tc['view']); sx=np.array([sp[n]+sc['at'] for n in snames]); tx=np.array([tp[n]+tc['at'] for n in tnames]); dx=np.array([dp[n]+at for n in dnames]); qx=np.array([dp[n]+at for n in qnames]); L1=np.abs(sx[:,None,:]-dx).sum(2);L2=np.abs(tx[:,None,:]-qx).sum(2); margins=[]
 for co in ['tt','ff','ss']:
  if co=='ff':
   a=np.array([sm[co][n]['lmin'] for n in snames])[:,None]-np.array([dm[co][n]['hold'] for n in dnames])-100
   b=np.array([dm[co][n]['lmin'] for n in qnames])-np.array([tm[co][n]['hold'] for n in tnames])[:,None]-100
  else:
   a=833.333-210-np.array([sm[co][n]['out'] for n in snames])[:,None]-np.array([dm[co][n]['inp'] for n in dnames])
   b=833.333-210-np.array([dm[co][n]['out'] for n in qnames])-np.array([tm[co][n]['inp'] for n in tnames])[:,None]
   if co=='tt': a-=.76*L1;b-=.76*L2
  margins.extend([a,b])
 cost=-np.minimum.reduce(margins+[500-L1,500-L2]);r,c=linear_sum_assignment(cost); mins=[float(np.min(x[r,c])) for x in margins];print('at',at,'bits',len(r),'bad',sum(cost[r,c]>0),'TT',mins[:2],'FF',mins[2:4],'SSzero',mins[4:],'maxL',float(np.max(L1[r,c])),float(np.max(L2[r,c])));
 pairs=[]
 for k,j in zip(r,c):
  pairs.append(dict(source_inst=sc['inst'], source_pin=snames[k], source_view=sc['view'], target_inst=tc['inst'], target_pin=tnames[k], target_view=tc['view'], station_d_pin=dnames[j], station_q_pin=qnames[j], input_L_um=float(L1[k,j]), output_L_um=float(L2[k,j]), margins=dict(zip(['input_TTdeep210','output_TTdeep210','input_FFidealH100','output_FFidealH100','input_SSzero','output_SSzero'],[float(a[k,j]) for a in margins]))))
 reports.append(dict(at_um=at, bits=len(r), failing_bits=int(sum(cost[r,c]>0)), minimum_margins=mins, mapping=pairs))
 return c.tolist(),mins
for i in range(8):
 x=69.12 if i<4 else 518.4; y=(i%4)*205.2
 ctrl=[x,y+4.32];wd=[x,y+138.24]
 if i==5:wd=[x,412.56]
 if i==6:ctrl=[x,481.68]
 names=['re','we']+[f'{a}[{j}]' for a,N in [('ra',8),('wl',8),('wm',16)] for j in range(N)]
 stations.append(dict(name=f'b{i}_cmd_station',at_um=ctrl));print('BANK',i,'CTRL');assign(C[f'vm_g6_b{i}_ctl'],['m_'+n for n in names],C[f'vm_g6_b{i}'],names,ctrl)
 stations.append(dict(name=f'b{i}_wd_station',at_um=wd));print('BANK',i,'WD');assign(C[f'vm_g6_b{i}_in'],qnames,C[f'vm_g6_b{i}'],[f'wd[{j}]' for j in range(512)],wd)

boxes=[]; source_hashes={}
for ch in p['children']:
 v=R/ch['view']; f=next(v.glob('*.lef'));txt=f.read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups());x,y=ch['at'];boxes.append((x,y,x+w,y+h,ch['inst']));source_hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
for st in stations:
 x,y=st['at_um'];boxes.append((x,y,x+17.28,y+64.8,st['name']))
collisions=[]
for k,(x,y,X,Y,n) in enumerate(boxes):
 for a,b,A,B,m in boxes[k+1:]:
  if x<A+2.16-1e-6 and X>a-2.16+1e-6 and y<B+2.16-1e-6 and Y>b-2.16+1e-6:collisions.append([n,m])
for v in cache:
 for f in (R/v).iterdir():
  if f.suffix in ['.lib','.lef'] or f.name=='insertion.json':source_hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
plan=R/'results/arch/qwen_tp8_1012/vm_rg6.json';source_hashes[str(plan.relative_to(R))]=hashlib.sha256(plan.read_bytes()).hexdigest()
out=dict(schema='opentallas.vm-bank-command-station-candidate.v1',status='NECESSARY_INTERNAL_SCREENS_ONLY_NOT_FROZEN',clock_edges_added=1,engine_edges_added=0,core_masters_preserved=72,existing_children_preserved=149,added_clock_roots=16,flops_per_root=512,geometry_gap_um=2.16,geometry_collisions=collisions,station_view=D,stations=stations,source_hashes=source_hashes,pair_policy='Normalized O-R/S+R actual closed ETMs; TT .76 geometric screen with210reserve; FF idealwire H100; SS zero-wire only; measured DATA RC absent.',epoch_policy='All bank wd512 and re/we/ra8/wl8/wm16 commands delayed1CLOCK uniformly. Proposed NRI3 bank behavior. Row rqb/rq, xv/xg/FIFO pop/ME epochs/reset release must be globally aligned and proven before any RTL adoption. This candidate repairs bank input seams only, not other native or interface defects.',boundary_policy='Internal stations only; no190/220 boundary endorsement or assigned pins.',pairs=reports)
(R/'results/arch/qwen_tp8_1012/rg6_bank_command_station_candidate.json').write_text(json.dumps(out,indent=1)+'\n')
print('GEOMETRY collisions',collisions)
