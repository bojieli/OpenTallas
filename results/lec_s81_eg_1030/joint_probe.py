import sys,json,collections,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import eg_lec as lec
p=Path(__file__).parent/'eg';log=[]
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
for k,v in json.load(open(p/'normalized_snapshot.json')).items():
 if k=='hyp':L.hyp={(sd,k):tuple(h) for sd,k,h in v}
 else:setattr(L,k,v)
new=[];aliases=[]
for sd in ['nh','nk']:
 for nr in [0,1]:
  root=f'ff:u_dut.u_{sd}.rsqrt.g_nr[{nr}]'
  key=root+'.m_yy.g_l5.u.u.y[31]'
  new.append(['gold',key,['fill',int(os.environ.get('FILL_VALUE','0')),None]])
  for stage,bit,hi in [(1,72,31),(3,204,63),(5,176,95),(6,44,127)]:
   key=root+f'.m_hm.g_l5.u.u.u_k{stage}.g_r.r[{bit}]'
   partner=root+f'.g_h.d_h.g_line.line[{hi}]'
   assert key in L.gonly and partner in L.matched
   aliases.append(['gold',key,['eq','gold',partner,0]])
base=lec.apply_hints(L,new,p,1000,log,propose_only=True);print('fills',base,flush=True)
if base['fill_refused']:
 (p/('joint_sign_wrong_fill.json' if os.environ.get('FILL_VALUE')=='1' else 'joint_sign_input_error.json')).write_text(json.dumps(base,indent=1));raise SystemExit(1)
a=lec.apply_hints(L,aliases,p,1000,log,propose_only=True);print('aliases',a,flush=True)
m,kind=L.build(with_compare=True,with_hyp=True)
lec.abc_bin=lambda:'/home/ubuntu/.local/opentallas-tools/bin/yosys-abc'
name='joint_sign_wrong' if os.environ.get('FILL_VALUE')=='1' else 'joint_sign'
st=lec.prove(m,p,1000,log,tag=name)
rec=dict(requests=new,aliases=aliases,base=base,counts=dict(collections.Counter(st.values())),failed={k:v for k,v in st.items() if v!='proved'})
(p/(name+'.json')).write_text(json.dumps(rec,indent=1));(p/(name+'.log')).write_text('\n'.join(log))
(p/(name+'_hints.json')).write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())]))
print(dict(counts=rec['counts'],failed=rec['failed']),flush=True)
