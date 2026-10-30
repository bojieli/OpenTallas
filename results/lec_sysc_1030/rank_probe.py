import sys,json,collections,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent));import sysc_lec as lec
p=Path(__file__).parent/'sysc'
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
for k,v in json.load(open(p/'snapshot.json')).items():
 if k=='hyp':L.hyp={(sd,k):tuple(h) for sd,k,h in v}
 else:setattr(L,k,v)
for sd,k,h in json.load(open(p/'backward_hints.json')):L.hyp[sd,k]=tuple(h)
m,kind=L.build(with_compare=False,with_hyp=False)
groups={}
for sd,keys,kd in [('gold',L.gonly,'gold_only'),('gate',L.tonly,'gate_only')]:
 groups[sd]={}
 for k in keys:
  if (sd=='gold' and 'u_dcal.u_seq.e[' not in k) or (sd=='gate' and not k.startswith('ff:u_dut._824')):continue
  if (sd,k) in L.hyp:continue
  ins=m.cone_inputs(L.dlit[sd,k]);un={kind[v][1] for v in ins if kind[v][0]==kd}
  if k not in un:continue
  groups[sd].setdefault(len(un),[]).append(k)
added=[]
for n,gs in sorted(groups['gold'].items()):
 ts=groups['gate'].get(n,[])
 if len(gs)==len(ts)==1:
  L.hyp['gate',ts[0]]=('eq','gold',gs[0],0);added.append([ts[0],gs[0],n])
print('rank candidates',added,flush=True)
m,kind=L.build(with_compare=False,with_hyp=False)
groups={}
for sd,keys,kd in [('gold',L.gonly,'gold_only'),('gate',L.tonly,'gate_only')]:
 groups[sd]={}
 for k in keys:
  if (sd=='gold' and 'u_dcal.u_seq.t[' not in k) or (sd=='gate' and not k.startswith('ff:u_dut._824')):continue
  if (sd,k) in L.hyp:continue
  ins=m.cone_inputs(L.dlit[sd,k]);un={kind[v][1] for v in ins if kind[v][0]==kd}
  if k not in un:continue
  groups[sd].setdefault(len(un),[]).append(k)
print('t groups',groups,flush=True)
for n,gs in sorted(groups['gold'].items()):
 ts=groups['gate'].get(n,[])
 if len(gs)==len(ts)==1:
  L.hyp['gate',ts[0]]=('eq','gold',gs[0],0);added.append([ts[0],gs[0],n])
print('all rank candidates',added,flush=True)
(p/'rank2_hints.json').write_text(json.dumps([[sd,k,list(h)] for (sd,k),h in sorted(L.hyp.items())],indent=1))
m,kind=L.build(with_compare=True,with_hyp=True)
lec.abc_bin=lambda:'/home/ubuntu/.local/opentallas-tools/bin/yosys-abc'
log=[];st=lec.prove(m,p,1000,log,tag='rank2_candidates')
rec=dict(added=added,counts=dict(collections.Counter(st.values())),failed={k:v for k,v in st.items() if v!='proved'})
(p/'rank2_candidates.json').write_text(json.dumps(rec,indent=1));(p/'rank2_candidates.log').write_text('\n'.join(log))
print(json.dumps(dict(counts=rec['counts'],failed=rec['failed'])),flush=True)
