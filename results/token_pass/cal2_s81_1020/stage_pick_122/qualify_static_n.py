"""Qualify the exact map without mistaking capacity PASS for a static schedule."""
from pathlib import Path
import collections,hashlib,json,sys
p=Path(sys.argv[1]); b=p.read_bytes(); m=json.loads(b)
N=m["stages_count"]; assert len(m["stages"])==N
assert m['verdict']['all_pass'] and not m['verdict']['missing']
coverage=collections.Counter(); dense=[]
for s in m['stages']:
 c=s['capacity']; assert c['pass'] and c['layout_identical_all'],(s['stage'],c)
 assert c['dense_layer']==s['dense_layer'] and c['experts']==s['n_experts']
 for layer,first,last in s['experts']:
  coverage.update((layer,e) for e in range(first,last+1))
 if s['dense_layer'] is not None: dense.append(s['dense_layer'])
assert sorted(dense)==list(range(40)),dense
assert set(coverage)=={(l,e) for l in range(40) for e in range(384)}
assert set(coverage.values())=={1}
r={'verdict':'PASS','scope':'actual allocator capacity and identical expert slot layouts; full MU schedule and behavioural token chain still owed','map_sha256':hashlib.sha256(b).hexdigest(),"stages":N,"rank_dies_per_stage":4,"layer_dies":4*N,"nominal_total_dies":4*N+32+52,'experts_exactly_once':len(coverage),'dense_layers_exactly_once':len(dense),'worst_q_fill':max(s['capacity']['q_max_fill'] for s in m['stages']),'all_expert_layouts_identical':True}
p.with_name('static_capacity_receipt_%d.json'%N if False else 'static_capacity_receipt_'+str(N)+'.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
