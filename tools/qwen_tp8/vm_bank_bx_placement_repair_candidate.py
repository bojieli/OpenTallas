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

base=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_bank_bx_joint_permutation_candidate.json'))
bankst=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_bank_command_station_candidate.json'))
rowst=json.load(open(R/'results/arch/qwen_tp8_1012/rg6_row_station_candidate.json'))
moves={};byinst={ch['inst']:ch for ch in p['children']}
for b in range(8):
 for suffix,delta in [('_bx',[-2.16,-25.92]),('_ctl',[0,-19.44]),('_xf0',[2.16,0])]:
  ch=C[f'vm_g6_b{b}{suffix}']; moves[ch['inst']]=dict(old=ch['at'],new=(np.array(ch['at'])+delta).tolist(),delta=delta)
boxes=[]
for ch in p['children']:
 txt=next((R/ch['view']).glob('*.lef')).read_text();w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',txt).groups());x,y=moves.get(ch['inst'],{}).get('new',ch['at']);boxes.append((x,y,x+w,y+h,ch['inst']))
for st in bankst['stations']+rowst['stations']:
 x,y=st['at_um'];boxes.append((x,y,x+17.28,y+64.8,st['name']))
collisions=[]
for i,(x,y,X,Y,n) in enumerate(boxes):
 for a,b,A_,B,m in boxes[i+1:]:
  if x<A_+2.16-1e-6 and X>a-2.16+1e-6 and y<B+2.16-1e-6 and Y>b-2.16+1e-6:collisions.append([n,m])
edges=[]
def changed(inst,xy):return np.array(xy)+moves.get(inst,{}).get('delta',[0,0])
for bank in base['banks']:
 for a in bank['assignments']:
  src=a['bank_Q'];di=a['existing_BX_D'];qo=a['existing_BX_Q'];fi=a['FIFO_capture'];rs=a['row_station_capture']
  pairs=[(src,di),(qo,fi),(qo,dict(inst='newrow',xy_um=rs['xy_um']))]
  for h,(s,t) in enumerate(pairs):
   L=float(abs(changed(s['inst'],s['xy_um'])-changed(t['inst'],t['xy_um'])).sum());old=a['hop_margins'][h];m=dict(old);m['TTdeep210_geometric_ps']+=.76*(old['manhattan_um']-L);m['manhattan_um']=L
   edges.append(dict(bank=bank['bank'],logical_bit=a['logical_bit'],hop=h,source=s,target=t,source_xy_new=changed(s['inst'],s['xy_um']).tolist(),target_xy_new=changed(t['inst'],t['xy_um']).tolist(),margins=m))
# Moving bctl also changes its launch to the proposed command station.
cmd=[]
for path in bankst['pairs']:
 for a in path['mapping']:
  if a['source_inst'] not in moves:continue
  ch=byinst[a['source_inst']];sp,_=view(ch['view']);dp,_=view(bankst['station_view']);sx=sp[a['source_pin']]+moves[a['source_inst']]['new'];tx=dp[a['station_d_pin']]+path['at_um'];L=float(abs(sx-tx).sum());m=dict(a['margins']);m['input_TTdeep210']+=.76*(a['input_L_um']-L)
  cmd.append(dict(source_inst=a['source_inst'],source_pin=a['source_pin'],station_pin=a['station_d_pin'],L_um=L,margins=m))
# Existing scalar bctl->FIFO dependencies, with exact closed per-pin metrics.
scalars=[]
for b in range(8):
 sc=C[f'vm_g6_b{b}_ctl'];sp,sm=view(sc['view'])
 for h in range(2):
  tc=C[f'vm_g6_b{b}_xf{h}'];tp,tm=view(tc['view'])
  for pin in ['pgw','xg','rtg']:
   sx=sp[pin]+moves[sc['inst']]['new'];target_pin=pin if pin in tp else pin+'[0]';tx=tp[target_pin]+moves.get(tc['inst'],{}).get('new',tc['at']);L=float(abs(sx-tx).sum());m={};missing=[]
   for co in ['tt','ff','ss']:
    s=sm[co].get(pin,{});t=tm[co].get(target_pin,{});sk='lmin' if co=='ff' else 'out';tk='hold' if co=='ff' else 'inp'
    if sk not in s or tk not in t:missing.append(co);continue
    m[co]=s[sk]-t[tk]-100 if co=='ff' else 833.333-210-s[sk]-t[tk]-(.76*L if co=='tt' else 0)
   scalars.append(dict(bank=b,FIFO=h,pin=pin,manhattan_um=L,margins=m,missing_timing_arcs=missing))
out=dict(schema='opentallas.vm-bank-bx-placement-repair.v1',status='UNFROZEN_DATA_PLACEMENT_ONLY_RESET_SCREEN_REJECTED',reason='d3ba00197 nominalM5 SS−6.373402 on bank0q286→BXd219 motivates shorter placement; same closed masters, no new latency',moves=moves,children=176,gap_um=2.16,collisions=collisions,minimum_data_margins={k:min(e['margins'][k] for e in edges) for k in ['TTdeep210_geometric_ps','FFidealH100_ps','SSzero_ps']},failing_data_edges=sum(any(e['margins'][k]<0 for k in ['TTdeep210_geometric_ps','FFidealH100_ps','SSzero_ps']) or e['margins']['manhattan_um']>500 for e in edges),failing_scalar_paths=sum(any(v<0 for v in s['margins'].values()) for s in scalars),scalar_policy='Direct pin_metrics setup/hold screen includes rtg; 16 reset SSzero negatives are unresolved. Need actual native recovery/removal release semantics, no false-path or margin waiver.',data_edges=edges,command_launch_paths=cmd,scalar_FIFO_paths=scalars,open_proofs=['Specific new placement same-corner actual DATA RC, no transferable SS coefficient','All scalar control/tag/reset alignment and parent entry clocks','Full boundary190/220 and production behavior before freeze'])
out['source_hashes']={str(f.relative_to(R)):hashlib.sha256(f.read_bytes()).hexdigest() for f in [R/'results/arch/qwen_tp8_1012/vm_rg6.json',R/'results/arch/qwen_tp8_1012/rg6_bank_bx_joint_permutation_candidate.json',R/'results/arch/qwen_tp8_1012/rg6_bank_command_station_candidate.json',R/'results/arch/qwen_tp8_1012/rg6_row_station_candidate.json',Path(__file__)]};out['source_hashes'].update(base['source_hashes']);
(R/'results/arch/qwen_tp8_1012/rg6_bank_bx_placement_repair_candidate.json').write_text(json.dumps(out,indent=1)+'\n')
print('GEOMETRY',len(collisions),collisions[:10],'data',out['minimum_data_margins'],'bad',out['failing_data_edges']);print('cmdmin',min(a['margins']['input_TTdeep210'] for a in cmd));print('scalar',[(a['pin'],a['margins'],a['missing_timing_arcs']) for a in scalars[:3]])
