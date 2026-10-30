"""Exact canonical state-cut AIG identity; no reset/initial-zero assumption, no simulation tolerance."""
from pathlib import Path
import json,hashlib,sys,collections
B=Path(sys.argv[1]);H=lambda s:hashlib.sha256(s.encode()).hexdigest()
def model(p):
 m=json.load(open(p))['modules']['bridge_top'];labels={};ports={}
 for n,r in m['ports'].items():
  ports[n]=(r['direction'],len(r['bits']))
  if r['direction']=='input':
   for i,q in enumerate(r['bits']):labels[q]='PI:'+n+'['+str(i)+']'
 aliases=collections.defaultdict(list);inits=collections.defaultdict(set)
 for n,r in m['netnames'].items():
  iv=r.get('attributes',{}).get('init','')
  for i,q in enumerate(r['bits']):
   if iv and isinstance(q,int):
    ch=iv[::-1][i] if i<len(iv) else 'x'
    if ch in '01':inits[q].add(ch)
  if n.startswith('$'):continue
  for i,q in enumerate(r['bits']):
   if isinstance(q,int):aliases[q].append(n+'['+str(i)+']')
 gates={};states={};types=collections.Counter()
 for name,c in m['cells'].items():
  t=c['type'];types[t]+=1;co=c['connections']
  if t=='$scopeinfo':assert not co;continue
  if t=='$_DFF_P_':
   assert len(co['Q'])==1;bit=co['Q'][0];assert aliases[bit];label=min(aliases[bit],key=lambda x:(len(x),x));assert label not in states;labels[bit]='FF:'+label;states[label]=dict(D=co['D'][0],C=co['C'][0],type=t,init=sorted(inits[bit]))
  else:
   assert t in ['$_AND_','$_NOT_'],('nonAIGcell',name,t)
   assert len(co['Y'])==1;bit=co['Y'][0];assert bit not in gates;gates[bit]=(t,co)
 cache={};active=set()
 def f(v):
  if isinstance(v,str):assert v in ['0','1'],('undefined constant',v);return H('CONST:'+v)
  if v in cache:return cache[v]
  if v in labels:ans=H(labels[v])
  else:
   assert v not in active,('combloop',v);active.add(v);t,co=gates[v]
   if t=='$_NOT_':ans=H('NOT:'+f(co['A'][0]))
   else:ans=H('AND:'+':'.join(sorted([f(co['A'][0]),f(co['B'][0])])))
   active.remove(v)
  cache[v]=ans;return ans
 state={n:dict(D=f(r['D']),C=f(r['C']),type=r['type'],init=r['init'])for n,r in states.items()};out={n:[f(q)for q in r['bits']]for n,r in m['ports'].items()if r['direction']=='output'}
 return dict(ports=ports,states=state,outputs=out,cell_types=dict(types),state_count=len(state),aig_digest=H(json.dumps(dict(ports=ports,states=state,outputs=out),sort_keys=True)))
a=model(B/'old.json');b=model(B/'current.json');c=model(B/'mutant.json')
assert a['ports']==b['ports']==c['ports'];assert a['aig_digest']==b['aig_digest'],'CURRENT DEFAULT-OFF NOT IDENTICAL';assert a['aig_digest']!=c['aig_digest'],'WRONG ZERO_LOW=1 MUTANT WAS NOT REFUSED'
R=dict(verdict='PASS',basis='Canonical complete AND/NOT state-function and output AIG identity under named arbitrary DFF-state inputs; all corresponding initial states, no init/reset/steady-state assumption',source=json.load(open(B/'inputs.json')),old=a,current=b,mutant_summary=dict(verdict='REFUSED',state_count=c['state_count'],aig_digest=c['aig_digest'],different_state_labels=sorted(set(a['states'])^set(c['states']))[:12],different_functions=[n for n in set(a['states'])&set(c['states'])if a['states'][n]!=c['states'][n]][:12]),added_cycles=0,scope='Changed reachable VE_s dly/ring component at actual LA4 delays 0,4,8,12,16,20,24,28/W32/MUT0; LM5 VES parameter retained; no fullbaselineLECrepeat/no physical or signoff claim')
(B/'bridge.json').write_text(json.dumps(R,indent=2));print('DEFAULT_OFF_BRIDGE PASS',a['state_count'],'arbitrary states',a['cell_types'],'mutantREFUSED',c['state_count'],'states')
