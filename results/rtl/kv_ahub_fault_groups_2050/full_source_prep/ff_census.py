from pathlib import Path
from collections import defaultdict
import json
root=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-fault-full-2055')

def census(path):
 m=json.loads(path.read_text())['modules']['lec_top']; aliases=defaultdict(set)
 for name,n in m['netnames'].items():
  for i,b in enumerate(n['bits']):
   if isinstance(b,int): aliases[b].add(f'{name}[{i}]')
 rows=[]
 for cell,d in m['cells'].items():
  if 'dff' not in d['type'].lower():continue
  clocks=sorted({n for b in d['connections'].get('CLK',[]) for n in aliases[b]})
  for i,q in enumerate(d['connections'].get('Q',[])):
   names=sorted(aliases[q]);rows.append({'cell':cell,'q_index':i,'names':names,'clock_aliases':clocks,'type':d['type']})
 bank=[r for r in rows if any('.gqv[' in n or '.gqv_groups[' in n for n in r['names'])]
 return {'flops':len(rows),'records':rows,'fault_bank':bank}
base=census(root/'gold.aliases.json');candidate=census(root/'proof/normal/gold.aliases.json')
result={'scope':'native actual AHUB source-flop bits; child macro internal flops excluded','baseline_flops':base['flops'],'candidate_flops':candidate['flops'],'delta':candidate['flops']-base['flops'],'baseline_fault_bank':base['fault_bank'],'candidate_fault_bank':candidate['fault_bank'],'unchanged_semantic_roles':{'old_gqv[0,1,3,4]':'gqv_groups[0,1,3,4]','old_gqv[2]':'OR(gqv_groups[2],gqv_groups[5:20])'},'extra_clock_role':'original ck[0]/u_core.clk, same rn[3] reset'}
oldclocks={tuple(r['clock_aliases']) for r in base['fault_bank']};newclocks={tuple(r['clock_aliases']) for r in candidate['fault_bank']}
result['clock_alias_sets_equal']=oldclocks==newclocks
result['baseline_bank_count']=len(base['fault_bank']);result['candidate_bank_count']=len(candidate['fault_bank'])
result['verdict']='PASS' if result['delta']==16 and len(base['fault_bank'])==5 and len(candidate['fault_bank'])==21 and oldclocks==newclocks else 'FAIL'
(root/'named_ff_census.json').write_text(json.dumps(result,indent=2)+'\n')
(root/'all_source_ff_census.json').write_text(json.dumps({'baseline':base,'candidate':candidate},indent=1)+'\n')
print({k:v for k,v in result.items() if not isinstance(v,(list,dict))})
