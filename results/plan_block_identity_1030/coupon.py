import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools/autopilot"))
import plan_block_identity as B
root=Path('/srv/opentallas-scratch2/claude')
paths={
'old':root/'die-kv-40-1029/kv40/event28w/plan_c.json',
'e0':root/'codex-kv-1030/plan_of_record/plan_c_e0.json',
'ahub':root/'codex-kv-1030/plan_of_record/plan_c_e0_ahubtrack.json'}
plans={k:json.loads(p.read_text()) for k,p in paths.items()}
ids={k:B.identities(plans[k],paths[k],B.PINS) for k in paths}
report={'schema':'opentallas.portable_identity_coupon.v1','plans':{k:{'path':str(p),'sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest()} for k,p in paths.items()},'comparisons':{}}
for a,b in [('old','e0'),('e0','ahub')]:
    same=[];changed=[];pathonly=[];ambiguous=[]
    for item in sorted(set(ids[a])&set(ids[b])):
        x,y=ids[a][item],ids[b][item]
        if x['normalized_node']==y['normalized_node']:
            same.append(item)
            if x['raw_sha']!=y['raw_sha']:pathonly.append(item)
        else:changed.append(item)
        if x.get('legacy_ambiguous'):ambiguous.append(item)
    report['comparisons'][a+'_'+b]={'same_count':len(same),'changed_count':len(changed),'path_only_count':len(pathonly),'path_only_items':pathonly,'changed_items':changed,'legacy_ambiguous_count':len(ambiguous),'added':sorted(set(ids[b])-set(ids[a])),'removed':sorted(set(ids[a])-set(ids[b]))}
print(json.dumps(report,indent=2))
