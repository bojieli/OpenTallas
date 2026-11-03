"""Read-only finite old/new23-state transition graph comparison; no LEC assumptions."""
from pathlib import Path
import sys,json,collections,hashlib
P=Path('/work/producer');sys.path.insert(0,str(P/'tools/die_plan/tt_regional_origin'))
from native_inventory import parse_dump,L
j=json.loads((P/'native_name_diagnosis.json').read_text());libs=[Path(p) for p in json.loads((P/'actual_source_readset.json').read_text())['inputs'] if '.lib' in p];models=L.read_liberty(libs)
old,op,ob,od,_=parse_dump('/old/actual_old_reference.tsv');new,np,nb,nd,_=parse_dump(P/'actual_synth.tsv')
proposed={n:v[0] for n,v in j['same_literal_inputs_candidates'].items() if len(v)==1}
remaining_old=set(j['missing'])-set(proposed);remaining_new={n for n in j['extra'] if n.startswith('_')}-set(proposed.values())
if len(remaining_old)!=1 or len(remaining_new)!=1:raise ValueError('Finite unmatched state pair is not unique')
proposed[next(iter(remaining_old))]=next(iter(remaining_new));inverse={v:k for k,v in proposed.items()}
if len(inverse)!=23:raise ValueError('Proposed transition correspondence is not bijective23')
def canonical(expr):
 op0=expr[0]
 if op0=='not':
  x=canonical(expr[1]);return x[1] if x[0]=='not' else ('not',x)
 if op0 in ('and','or'):
  args=[]
  for x in expr[1]:
   x=canonical(x);args.extend(x[1] if x[0]==op0 else [x])
  return (op0,tuple(sorted(set(args),key=repr)))
 if op0=='xor':return ('xor',*sorted([canonical(expr[1]),canonical(expr[2])],key=repr))
 return expr
def engine(cells,pins,ports,drivers,rename):
 memo={};visiting=set();used=set()
 def net(n):
  if n in memo:return memo[n]
  if n in visiting:raise ValueError('Combinational loop in actual native cone')
  visiting.add(n);ds=drivers[n]
  if len(ds)!=1:raise ValueError('Missing/multiple actual native cone drivers: '+n)
  kind,name,pin=ds[0]
  if kind=='port':out=('port',name)
  else:
   c=cells[name];model=models[c['master']]
   if model.get('ff'):
    # Explicit actual state-output function, normalized to proposed state names.
    out=('ff_output',rename.get(name,name),model['pins'][pin].get('function'),model['ff'].get('next_state'),model['ff'].get('clocked_on'));used.add(name)
   elif c['is_block']:out=('macro_output',name,pin)
   else:
    fun=model['pins'][pin].get('function')
    if not fun:raise ValueError('Missing actual Liberty combinational function '+c['master']+'.'+pin)
    def subst(x):
     if x[0]=='var':return net(pins[name][x[1]]['net'])
     if x[0]=='const':return x
     if x[0] in ('and','or'):return (x[0],[subst(z) for z in x[1]])
     return (x[0],*[subst(z) for z in x[1:]])
    out=canonical(subst(L.parse_function(fun)))
  visiting.remove(n);memo[n]=out;return out
 return net,used
og,ou=engine(old,op,ob,od,{});ng,nu=engine(new,np,nb,nd,inverse)
rows=[]
for on,nn in sorted(proposed.items()):
 om=models[old[on]['master']];nm=models[new[nn]['master']]
 def transition(model,name,pins,graph):
  def subst(x):
   if x[0]=='var':
    if x[1] in pins[name]:return graph(pins[name][x[1]]['net'])
    return ('internal_state',inverse.get(name,name),x[1])
   if x[0]=='const':return x
   if x[0] in ('and','or'):return (x[0],[subst(z) for z in x[1]])
   return (x[0],*[subst(z) for z in x[1:]])
  return canonical(subst(L.parse_function(model['ff']['next_state'])))
 oe=transition(om,on,op,og);ne=transition(nm,nn,np,ng);clk_o=op[on][om['ff']['clocked_on']]['net'];clk_n=np[nn][nm['ff']['clocked_on']]['net']
 if oe!=ne:
  def leaves(e):
   if e[0] in ('ff_output','macro_output','port','const','internal_state'):return {repr(e)}
   if e[0] in ('and','or'):return set().union(*(leaves(x) for x in e[1]))
   return set().union(*(leaves(x) for x in e[1:]))
  ol,nl=leaves(oe),leaves(ne)
  (P/'residual_anonymous_cone.json').write_text(json.dumps(dict(old=on,new=nn,old_ast=oe,new_ast=ne,old_leaf_count=len(ol),new_leaf_count=len(nl),old_only_leaves=sorted(ol-nl),new_only_leaves=sorted(nl-ol),same_leaf_interface=ol==nl,accepted_alias=False),indent=1)+'\n')
 rows.append(dict(old=on,new=nn,transition_ast_equal=oe==ne,clock_net_equal=clk_o==clk_n,clock_old=clk_o,clock_new=clk_n,ff_function_equal=om['ff']==nm['ff'],old_ast_sha256=hashlib.sha256(repr(oe).encode()).hexdigest(),new_ast_sha256=hashlib.sha256(repr(ne).encode()).hexdigest()))
result=dict(status='FINITE_TRANSITION_DIAGNOSIS_ONLY',rows=rows,proposed_correspondence=proposed,all_step_ast_equal=all(r['transition_ast_equal'] and r['clock_net_equal'] and r['ff_function_equal'] for r in rows),actual_old_leaf_ff=len(ou),actual_new_leaf_ff=len(nu),accepted_alias=False,native_base_proved=False,full_source_lec_credit=False,physical_release=False)
(P/'anonymous_transition_diagnosis.json').write_text(json.dumps(result,indent=1)+'\n');print('ANONYMOUS_TRANSITION_DIAGNOSIS',sum(r['transition_ast_equal'] for r in rows),'/23 AST identical;',result['all_step_ast_equal'],'no accepted alias/base/fullproof',flush=True)
