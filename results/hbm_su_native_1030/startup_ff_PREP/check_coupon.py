import collections,itertools,json,pathlib
D=pathlib.Path(__file__).with_name('mapped_coupon');results={}
for tag in ['good','wrong_value','omit_upstream']:
 j=json.load(open(D/('ff_'+tag+'.json')));mods=j['modules'];top=mods['coupon'];ff=[]
 def expand(mod,prefix,portmap):
  M=mods[mod]
  def bit(b):return b if isinstance(b,str)else portmap.get(b,(prefix,b))
  for n,c in M['cells'].items():
   C={p:[bit(b)for b in v]for p,v in c['connections'].items()}
   if c['type']in mods:
    child=mods[c['type']];mp={bb:C[p][i]for p,info in child['ports'].items()for i,bb in enumerate(info['bits'])};expand(c['type'],prefix+'/'+n,mp)
   elif c['type'].startswith('$_DFF'):ff.append(dict(name=prefix+'/'+n,Q=C['Q'][0],D=C['D'][0],type=c['type']))
   elif c['type']!='$scopeinfo':raise AssertionError(c['type'])
 expand('coupon','coupon',{})
 def get(name,idx):
  ns=[v for n,v in top['netnames'].items()if n==name or n.endswith(name)];assert len(ns)==1,name;b=ns[0]['bits'][idx];return b if isinstance(b,str)else('coupon',b)
 ids=[get('a_lo30',0)]+[get('g_line.line',i)for i in [30,62,94,126]]+[get('g_rv.rd',71)]
 byq={f['Q']:f for f in ff};owners=[byq.get(b)for b in ids];unique=len(set(f['name']for f in owners if f));dependencies=[f['D']if f else b for f,b in zip(owners,ids)]
 allowed=set(ids)|{'0','1'};assert all(d in allowed for d in dependencies),(tag,dependencies)
 expected=['0']+ids[:-1]
 bad=0;first=None
 for ini in itertools.product([0,1],repeat=6):
  actual={b:v for b,v in zip(ids,ini)if not isinstance(b,str)};ref=list(ini)
  for edge in range(8):
   value=lambda b:int(b)if isinstance(b,str)else actual[b]
   got=[value(b)for b in ids]
   if got!=ref:
    bad+=1
    if first is None:first=dict(initial=list(ini),edge=edge,native=ref,gate=got)
    break
   actual={b:value(d)for b,d in zip(ids,dependencies)if not isinstance(b,str)};ref=[0]+ref[:-1]
 results[tag]=dict(actual_selected_Q_scalar_FFs=unique,all_six_Q_distinct=unique==6,transition_graph_exact_native=dependencies==expected,assignments=64,edges_per_assignment=8,bad_assignments=bad,first_counterexample=first,owners=[f['name']if f else None for f in owners],total_expanded_FFs=len(ff))
assert results['good']['bad_assignments']==0 and results['good']['all_six_Q_distinct']and results['good']['transition_graph_exact_native']
assert results['wrong_value']['bad_assignments']>0 and results['omit_upstream']['bad_assignments']>0
print(json.dumps(results,indent=2))
pathlib.Path(__file__).with_name('coupon_receipt.json').write_text(json.dumps(dict(status='PASS_EXACT6_STATE_REPLACEMENT_AND_MUTANTS',scope='Actual Yosys0.68 synthesized six-state cone, all64 independent initial states; universal transition dependence excludes every other input/state. Not full-core LEC or PNR.',results=results),indent=2)+'\n')
