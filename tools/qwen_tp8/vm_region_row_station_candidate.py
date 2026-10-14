import json,re,sys,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
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
 sp,sm=view(sc['view']); tp,tm=view(tc['view']); sx=np.array([sp[n]+sc['at'] for n in snames]); tx=np.array([tp[n]+tc['at'] for n in tnames]); dx=np.concatenate([np.array([dp[n]+a for n in dnames[:512]]) for a in at]); qx=np.concatenate([np.array([dp[n]+a for n in qnames[:512]]) for a in at]); L1=np.abs(sx[:,None,:]-dx).sum(2);L2=np.abs(tx[:,None,:]-qx).sum(2); margins=[]
 for co in ['tt','ff','ss']:
  if co=='ff':
   a=np.array([sm[co][n]['lmin'] for n in snames])[:,None]-np.array([dm[co][n]['hold'] for n in dnames])-100
   b=np.array([dm[co][n]['lmin'] for n in qnames])-np.array([tm[co][n]['hold'] for n in tnames])[:,None]-100
  else:
   a=833.333-210-np.array([sm[co][n]['out'] for n in snames])[:,None]-np.array([dm[co][n]['inp'] for n in dnames])
   b=833.333-210-np.array([dm[co][n]['out'] for n in qnames])-np.array([tm[co][n]['inp'] for n in tnames])[:,None]
   if co=='tt': a-=.76*L1;b-=.76*L2
  margins.extend([a,b])
 cost=-np.minimum.reduce(margins+[500-L1,500-L2]);r,c=bottleneck(cost); mins=[float(np.min(x[r,c])) for x in margins];print('at',at,'bits',len(r),'bad',sum(cost[r,c]>0),'TT',mins[:2],'FF',mins[2:4],'SSzero',mins[4:],'maxL',float(np.max(L1[r,c])),float(np.max(L2[r,c])));
 pairs=[]
 for k,j in zip(r,c):
  pairs.append(dict(source_inst=sc['inst'], source_pin=snames[k], source_view=sc['view'], target_inst=tc['inst'], target_pin=tnames[k], target_view=tc['view'], station_index=int(j//512), station_d_pin=dnames[j], station_q_pin=qnames[j], input_L_um=float(L1[k,j]), output_L_um=float(L2[k,j]), margins=dict(zip(['input_TTdeep210','output_TTdeep210','input_FFidealH100','output_FFidealH100','input_SSzero','output_SSzero'],[float(a[k,j]) for a in margins]))))
 reports.append(dict(at_um=at, bits=len(r), failing_bits=int(sum(cost[r,c]>0)), minimum_margins=mins, mapping=pairs))
 return c.tolist(),mins

def bottleneck(cost):
 lo,hi=0.,float(-np.min(cost))
 for _ in range(22):
  mid=(lo+hi)/2; perm=maximum_bipartite_matching(csr_matrix(cost<=-mid),perm_type='column')
  if np.all(perm>=0):lo=mid
  else:hi=mid
 perm=maximum_bipartite_matching(csr_matrix(cost<=-lo),perm_type='column')
 if np.any(perm<0):raise ValueError('No all-bit necessary-screen matching')
 return np.arange(len(perm)),perm
positions=[[388.8,69.12],[410.4,274.32],[432,479.52],[410.4,479.52],[838.08,69.12],[859.68,274.32],[881.28,479.52],[859.68,479.52]]
for i,at in enumerate(positions):
 stations.append(dict(name=f'b{i}_row_station',at_um=at));assign(C[f'vm_g6_b{i}_bx'],qnames,C[f'vm_g6_rr4_{i//4}'],[f'bx[{(i%4)*512+j}]' for j in range(512)],[at])
for h,locations in [(0,[[781.92,278.64],[803.52,278.64]]),(1,[[838.08,278.64]])]:
 dnames=[f'd[{i}]' for i in range(512)]*len(locations);qnames=[f'q[{i}]' for i in range(512)]*len(locations)
 for k,at in enumerate(locations):stations.append(dict(name=f'rr4_{h}_link_station{k}',at_um=at))
 assign(C[f'vm_g6_rr4_{h}'],[f't1[{i}]' for i in range(512)],C['vm_g6_rr2'],[f't1'+('a' if h==0 else 'b')+f'[{i}]' for i in range(512)],locations)
boxes=[];hashes={}
for ch in p['children']:
 f=next((R/ch['view']).glob('*.lef'));txt=f.read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups());x,y=ch['at'];boxes.append([x,y,x+w,y+h,ch['inst']]);hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
bankpath=R/'results/arch/qwen_tp8_1012/rg6_bank_command_station_candidate.json';bank=json.load(open(bankpath));hashes[str(bankpath.relative_to(R))]=hashlib.sha256(bankpath.read_bytes()).hexdigest()
for st in bank['stations']+stations:
 x,y=st['at_um'];boxes.append([x,y,x+17.28,y+64.8,st['name']])
coll=[]
for k,(x,y,X,Y,n) in enumerate(boxes):
 for a,b,A,B,m in boxes[k+1:]:
  if x<A+2.16-1e-6 and X>a-2.16+1e-6 and y<B+2.16-1e-6 and Y>b-2.16+1e-6:coll.append([n,m])
for v in cache:
 for f in (R/v).iterdir():
  if f.suffix in ['.lib','.lef'] or f.name=='insertion.json':hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
q=dict(schema='opentallas.vm-row-station-candidate.v1',status='NECESSARY_SCREENS_NOT_PHYSICAL_FREEZE',existing_children_preserved=149,bank_command_roots_added=16,row_roots_added=11,combined_clock_roots=176,flops_per_added_root=512,actual_data_bits=5120,actual_hop_bit_edges=10240,source_hashes=hashes,geometry_gap_um=2.16,geometry_collisions=coll,stations=stations,paths=reports,clock_epoch_proposal={'bank_full_command_and_WD_CLOCK_delta':1,'BX_to_RR4_row_only_CLOCK_delta':1,'RR4_to_RR2_CLOCK_delta':1,'row_output_CLOCK_delta':3,'rr4_rqb_lowbits_required_CLOCK_delta':2,'rr2_rq_and_rqb2_required_CLOCK_delta':3},open_proofs=['Actual same-corner DATA RC missing; TT .76 geometric, FF idealwireH100, SS zero-wire only','RR4_0 first hop minimum TT margin is fragile; no route or closure assertion','No physical routing of scalar row tags or ME/PGW/XG/reset stations yet','Bank q-to-existing BX eight native SSzero failures remain; permutation would alter downstream pin maps and requires joint re-audit','Boundary launch220/capture190 failures remain','Whole production behavioral epoch/reset/row/X equalization proof not implemented before physical freeze'])
(R/'results/arch/qwen_tp8_1012/rg6_row_station_candidate.json').write_text(json.dumps(q,indent=1)+'\n');print('GEOMETRY',coll)
