import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/src')
import lec_fixed as lec
src=Path('/old'); out=Path('/new'); out.mkdir(exist_ok=True)
log=[]
L=lec.Lec(lec.read_aig(src/'gold.aig'),lec.read_map(src/'gold.map'),lec.read_aig(src/'gate.aig'),lec.read_map(src/'gate.map'))
lec.normalize_gold_elements(L,lec.slang_elements(src/'gold.aliases.json'),log)
lec.json_alias_keys(L,log,work=src)
lec.slang_element_keys(L,log,work=src)
lec.alias_arrays(L,log,work=src)
original_log=(src/'lec.log').read_text().splitlines()
assert not any(line.startswith(('relayout:', 'renamed:')) for line in original_log), 'unreplayed mapping decision'
log.append('Original final proof made no accepted relayout/renamed changes: exact mapping replay omits rejected simulation trials.')
L.hyp={(sd,k):tuple(v) for sd,k,v in json.loads((src/'hyp.json').read_text())}
# FSM constraints are separate from hyp.json; restore the complete retained
# six-state domain identified by all six preserved one-hot cube obligations.
fsm={}
for h in L.hyp.values():
 if h[0]=='cube':fsm.setdefault((h[1],tuple(h[2])),[]).append(h[3])
L.cons=[(sd,list(keys),allowed) for (sd,keys),allowed in fsm.items()]
assert len(L.cons)==1 and len(L.cons[0][2])==6, 'retained FSM domain changed'
log.append('Restored retained six-state FSM domain; its invariant is reproved in this miter.')
base='ff:u_dut.u_bound.u_d2d_kv.u_core.u_end.u_link.u_ctl.s1_c'
added=[]
for b in range(6,24):
 k=f'{base}[{b}]'; rep=f'{base}[{b%6}]'
 if k in L.gp and k in L.tp and rep in L.gp and rep in L.tp:
  L.hyp['both',k]=('eq','gold',rep,0); added.append(k)
# Untrusted equality candidates from exact gold public wire bit identity.
# Full-vector alias matching currently omits these scalar/subvector aliases.
d=json.loads((src/'gold.aliases.json').read_text()); wirebits={}
for mn,mod in d['modules'].items():
 for nn,net in mod.get('netnames',{}).items():
  if net.get('hide_name'):continue
  name=nn.replace('\\',''); bits=net['bits']; off=int(net.get('offset',0))
  for i,b in enumerate(bits):
   if isinstance(b,int):wirebits[f'ff:{name}[{i+off}]']=(mn,b)
  if len(bits)==1 and isinstance(bits[0],int):wirebits[f'ff:{name}']=(mn,bits[0])
pairs={}
for entry in json.loads((src/'lec.json').read_text())['unproven_points']:
 gs=[x.split(':',1)[1] for x in entry['cone_state_keys'] if x.startswith('gold_only:')]
 ts=[x.split(':',1)[1] for x in entry['cone_state_keys'] if x.startswith('gate_only:')]
 if len(gs)==len(ts)==1 and gs[0] in wirebits and wirebits.get(ts[0])==wirebits[gs[0]]:
  pairs[ts[0]]=gs[0]
for tk,gk in pairs.items():
 assert tk in L.tp and gk in L.gp
 L.hyp['gate',tk]=('eq','gold',gk,0)
before=set(L.hyp)
copy_count=lec.matched_d_copy_closure(L,log,collections.Counter())
newcopies=[(sd,k,list(L.hyp[sd,k])) for sd,k in sorted(set(L.hyp)-before)]
(out/'exact_d_copy_hints.json').write_text(json.dumps(newcopies,indent=1))
print('explicit copies',len(added),'exact-bit aliases',len(pairs),'additional exact-D copies',copy_count,flush=True)
(out/'alias_hints.json').write_text(json.dumps([['gate',k,['eq','gold',v,0]] for k,v in pairs.items()],indent=1))
m,kind=L.build(with_compare=True,with_hyp=True)
print('built',len(m.outs),flush=True)
status=lec.prove(m,out,1000,log,tag='copy_trial')
rec=dict(added=added,alias_pairs=pairs,newcopies=newcopies,counts=dict(collections.Counter(status.values())),failed={k:v for k,v in status.items() if v!='proved'})
(out/'result.json').write_text(json.dumps(rec,indent=1))
idx={n:i for i,n in enumerate(m.onames)}
detail={}
for n in rec['failed']:
 ins=m.cone_inputs(m.outs[idx[n]])
 detail[n]=dict(support_n=len(ins), inputs=[kind[v] for v in sorted(ins)])
(out/'failed_cones.json').write_text(json.dumps(detail,indent=1))
(out/'probe.log').write_text('\n'.join(log))
print(json.dumps({'counts':rec['counts'],'failed_n':len(rec['failed']),'failed_first':list(rec['failed'])[:12]}),flush=True)
