from pathlib import Path
import json,sys
r=Path('/srv/opentallas-scratch2/claude/codex-ds-native-cadence-0141');sys.path.insert(0,str(r))
from check_native_go_pair import inspect
old=Path('/srv/opentallas-scratch2/claude/codex-ds-native-go-pair-2355/retry2');gold=json.loads((old/'independent_gold.json').read_text())
for P in [141,142]:
 d=r/f'P{P}';cases={n:inspect(d,n,gold,5)for n in ['original_direct','current_direct']}
 eq={k:cases['original_direct'][k]==cases['current_direct'][k]for k in ['core','partial_words','feedback','cfg','stream']}
 s=dict(period=P,clock_ps=833,period_ps=P*833,cases={n:dict(status=v['status'],errors=v['errors'],terminal=v['terminal'],GO=v['core'],partial_edges=[x[0]for x in v['partial_words']],partial_edge_offsets_from_GO=[x[0]-v['core'][i//2][0]for i,x in enumerate(v['partial_words'])])for n,v in cases.items()},exact_original_current=eq,native_provider_qualified=False,production_enabled=False,extra_FF=0)
 (d/'cadence_check.json').write_text(json.dumps(s,indent=2)+'\n')
 print(P,{n:v['status']for n,v in cases.items()},eq)
