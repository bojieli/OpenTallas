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
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
row=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_row_station_candidate.json'))
permutations=[]
for b in range(8):
 bc=C[f'vm_g6_b{b}']; bx=C[f'vm_g6_b{b}_bx'];bp,bm=view(bc['view']);xp,xm=view(bx['view']);fifos=[C[f'vm_g6_b{b}_xf{h}'] for h in range(2)];fp,fm=view(fifos[0]['view']); rp=row['paths'][b];rmap={int(a['source_pin'][2:-1]):a for a in rp['mapping']};rx=np.array([dp[rmap[i]['station_d_pin']]+rp['at_um'][0] for i in range(512)]);sx=np.array([bp[f'q[{i}]']+bc['at'] for i in range(512)]);dx=np.array([xp[f'd[{i}]']+bx['at'] for i in range(512)]);qx=np.array([xp[f'q[{i}]']+bx['at'] for i in range(512)]);fx=np.array([fp[f'bx[{i%256}]']+fifos[i//256]['at'] for i in range(512)]);ls=[np.abs(sx[:,None,:]-dx).sum(2),np.abs(fx[:,None,:]-qx).sum(2),np.abs(rx[:,None,:]-qx).sum(2)];margins=[]
 for h in range(3):
  for co in ['tt','ff','ss']:
   if h==0:
    src=np.array([bm[co][f'q[{i}]']['lmin' if co=='ff' else 'out'] for i in range(512)])[:,None];dst=np.array([xm[co][f'd[{i}]']['hold' if co=='ff' else 'inp'] for i in range(512)])[None,:]
   elif h==1:
    src=np.array([xm[co][f'q[{i}]']['lmin' if co=='ff' else 'out'] for i in range(512)])[None,:];dst=np.array([fm[co][f'bx[{i%256}]']['hold' if co=='ff' else 'inp'] for i in range(512)])[:,None]
   else:
    src=np.array([xm[co][f'q[{i}]']['lmin' if co=='ff' else 'out'] for i in range(512)])[None,:];dst=np.array([dm[co][rmap[i]['station_d_pin']]['hold' if co=='ff' else 'inp'] for i in range(512)])[:,None]
   z=src-dst-100 if co=='ff' else 833.333-210-src-dst
   if co=='tt':z-=.76*ls[h]
   margins.append(z)
 cost=-np.minimum.reduce(margins+[500-l for l in ls]);rr,cc=linear_sum_assignment((cost>0)*1e9+cost);print('BANK',b,'bad',sum(cost[rr,cc]>0),'margins',[float(min(a[rr,cc])) for a in margins],'Lmax',[float(max(l[rr,cc])) for l in ls])

 assignments=[]
 for ii,jj in zip(rr,cc):
  i,j=int(ii),int(jj); f=fifos[i//256]
  assignments.append(dict(logical_bit=i,existing_BX_physical_bit=j,bank_Q=dict(inst=bc['inst'],pin=f'q[{i}]',view=bc['view'],xy_um=sx[i].tolist()),existing_BX_D=dict(inst=bx['inst'],pin=f'd[{j}]',view=bx['view'],xy_um=dx[j].tolist()),existing_BX_Q=dict(inst=bx['inst'],pin=f'q[{j}]',view=bx['view'],xy_um=qx[j].tolist()),FIFO_capture=dict(inst=f['inst'],pin=f'bx[{i%256}]',view=f['view'],xy_um=fx[i].tolist()),row_station_capture=dict(pin=rmap[i]['station_d_pin'],view=D,at_um=rp['at_um'][0],xy_um=rx[i].tolist()),hop_margins=[dict(zip(['TTdeep210_geometric_ps','FFidealH100_ps','SSzero_ps'],[float(margins[3*h+k][i,j]) for k in range(3)]),manhattan_um=float(ls[h][i,j])) for h in range(3)]))
 permutations.append(dict(bank=b,bijection=cc.tolist(),failing_bits=int(sum(cost[rr,cc]>0)),minimum_hop_margins=[[float(min(margins[3*h+k][rr,cc])) for k in range(3)] for h in range(3)],assignments=assignments))
hashes={}
for v in cache:
 for f in (R/v).iterdir():
  if f.suffix in ['.lib','.lef'] or f.name=='insertion.json':hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
for f in [R/'results/arch/qwen_tp8_1012/vm_rg6.json',R/'results/arch/qwen_tp8_1012/rg6_row_station_candidate.json']:hashes[str(f.relative_to(R))]=hashlib.sha256(f.read_bytes()).hexdigest()
a=dict(schema='opentallas.vm-bank-bx-permutation-candidate.v1',status='JOINT_NECESSARY_SCREENS_NOT_RTL_ADOPTED',bank_count=8,logical_bits=4096,affected_hop_bit_edges=12288,additional_CLOCK_edges=0,additional_ENGINE_edges=0,existing_BX_masters_and_positions_preserved=True,source_hashes=hashes,normalization='Direct actual Lib O-R/S+R, no packet boundary-extrema terms. TT210reserve and .76 geometric DATA screening; FFidealwireH100; SSzero only. No actual DATA RC closure.',supersedes='Bank q->BX native wiring and sourceq indexing of the first newrowstation hop in rg6_row_station_candidate.json ONLY; fixednewrowstation d/q indices and outgoingRR4 pinmaps preserved.',functional_identity='For bijection p_i, existingBX d[p_i]=bankq[i], then FIFObx[i] androwstationcapturek(i) readexistingBXq[p_i]. Eachdataword bit preserves its oneCLOCK BX delay; everylogicalconsumer restored. Whole production bench required after physicalfreeze/RTL implementation.',open_proofs=['Actual same-corner DATA RC and parent entry clocks','Scalarrowtag/ME/XG/PGW/pop/version/reset alignment','Full190/220 boundary receipts','Whole production behavioral proof after physicalfreeze'],banks=permutations)
(R/'results/arch/qwen_tp8_1012/rg6_bank_bx_joint_permutation_candidate.json').write_text(json.dumps(a,indent=1)+'\n')
