"""Finite exact source/IL traversal and six-condition truth tables; no SAT."""
from pathlib import Path
import json,itertools,collections,hashlib,functools,sys
sys.setrecursionlimit(5000)
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');f=T/'subject/lec/gold.aliases.json';assert hashlib.sha256(f.read_bytes()).hexdigest()=='4335dbca42fd196d3a31e13457b05db653b2a0386a4c82d43ca7372f170d9cfb'
m=json.load(open(f))['modules']['lec_top'];driver={};names=collections.defaultdict(list)
for n,x in m['netnames'].items():
 for b in x['bits']:names[b].append(n)
for n,c in m['cells'].items():
 for port,bs in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for i,b in enumerate(bs):driver[b]=(n,c,i)
seq=lambda c:c['type']in('$dff','$aldff','$adff','$dffe','$adffe','$sdff','$sdffe','$dlatch')
@functools.lru_cache(None)
def hasx(bit,context=()):
 if bit=='x':return True
 if bit in ('0','1')or bit not in driver:return False
 n,c,i=driver[bit]
 if seq(c):return False
 con=c['connections'];ctx=dict(context)
 if c['type']=='$mux':
  S=con['S'][0]
  if S in ctx:return hasx(con['B'if ctx[S]else'A'][i],context)
  if hasx(S,context):return True
  for value,arm in [(0,'A'),(1,'B')]:
   q=tuple(sorted([*context,(S,value)],key=lambda x:str(x[0])))
   if hasx(con[arm][i],q):return True
  return False
 return any(hasx(b,context)for p,bs in con.items()if c.get('port_directions',{}).get(p)=='input'for b in bs)
old=json.load(open(T/'subject/lec/lec.json'));rows=[x for x in old['failing']if x['cone_unmatched_keys']and x['cone_unmatched_keys'][0].startswith('x')];assert len(rows)==27;out=[]
for row in rows:
 field=row['point'].removeprefix('ff:');ix=0
 if field not in m['netnames']:
  field,ixs=field.rsplit('[',1);ix=int(ixs.rstrip(']'))
 Q=m['netnames'][field]['bits'][ix];n,c,i=driver[Q];D=c['connections']['D'][i];bad=hasx(D)
 out.append({'point':row['point'],'gold_primitive':c['type'],'CLK':c['connections'].get('CLK'),'async_reset':c['connections'].get('ALOAD'),'reset_value':c['connections'].get('AD',[None])[i],'Qbit':Q,'Dbit':D,'literal_X_reachable_after_consistent_mux_paths':bad,'D_source':c.get('attributes',{}).get('src'),'current_native_verdict':'DIFFERS_UNCHANGED'})
 assert not bad,row['point']
fault=[]
for lane in ['a','b']:
 e=f'u_dut.u_core.u_l{lane}.u_ln.u.u_ep.';bits=m['netnames'][e+'fault_n']['bits'];todo=list(bits);seen=set();selectors=set()
 while todo:
  b=todo.pop()
  if b in seen or b not in driver:continue
  seen.add(b);n,c,i=driver[b];assert c['type']=='$mux';co=c['connections'];selectors.add(co['S'][0]);todo +=[co['A'][i],co['B'][i]]
 priority=[m['netnames'][e+n]['bits'][0]for n in ['retry_exh','ack_bad','c_ovf']];middle=selectors-set(priority)-{m['netnames'][e+n]['bits'][0]for n in ['fr_bad','c_unexpl']};assert len(middle)==1
 priority +=[*middle,m['netnames'][e+'fr_bad']['bits'][0],m['netnames'][e+'c_unexpl']['bits'][0]];assert set(priority)==selectors and len(priority)==6
 def evaluate(bit,values):
  if bit in values:return values[bit]
  if bit in ('0','1','x'):return bit
  n,c,i=driver[bit];co=c['connections'];t=c['type']
  if t=='$mux':return evaluate(co['B'if evaluate(co['S'][0],values)=='1'else'A'][i],values)
  if t=='$logic_not':return '1'if all(evaluate(x,values)=='0'for x in co['A'])else'0'
  if t=='$logic_and':return '1'if any(evaluate(x,values)=='1'for x in co['A'])and any(evaluate(x,values)=='1'for x in co['B'])else'0'
  if t=='$reduce_bool':return '1'if any(evaluate(x,values)=='1'for x in co['A'])else'0'
  raise AssertionError((n,t))
 codes=[];q=m['netnames'][e+'fault']['bits'][0];_,c,i=driver[q];D=c['connections']['D'][i]
 for vals in itertools.product('01',repeat=6):
  v=dict(zip(priority,vals));actual=[evaluate(b,v)for b in bits];assert 'x'not in actual
  actual_code=sum(int(b)<<i for i,b in enumerate(actual));expect=next((i+1 for i,b in enumerate(vals)if b=='1'),0);assert actual_code==expect
  for priorfault in '01':assert evaluate(D,{**v,q:priorfault})==('1'if priorfault=='1'or expect else'0')
  codes.append(actual_code)
 fault.append({'lane':lane,'priority_selector_bits':priority,'conditions':['retry_exh','ack_bad','c_ovf','accept && occ>=RPS','fr_bad','c_unexpl'],'priority_cases':64,'fault_next_cases':128,'reachable_literal_X_cases':0,'exact_priority_code_matches':64,'fault_next_matches_sticky_OR':128,'code_histogram':dict(collections.Counter(codes))})
result={'scope':'SOURCE_IL_SEMANTICS_ONLY_NO_SOLVER_MASK_OR_NEW_CONSTRAINT','gold_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'raw_gold_X_points':27,'consistent_mux_path_literal_X_points':sum(x['literal_X_reachable_after_consistent_mux_paths']for x in out),'rows':out,'fault_truth_tables':fault,'classification':'All27RTLdriversarefullydefined. LiteralXnodesarefrontendtemporaryarmsmaskedbyconsistentconditions, notdeliberateinvalid-cycle unspecified-value contracts.'}
(P/'gold_il_semantics.json').write_text(json.dumps(result,indent=1)+'\n');print('27points, reachableliteralX',result['consistent_mux_path_literal_X_points'],'faulttables',fault)
