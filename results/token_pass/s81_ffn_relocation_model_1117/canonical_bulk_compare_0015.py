import json
from pathlib import Path
from collections import Counter
r=Path('/srv/opentallas-scratch2/claude/tok-verify-2/recovery1116/ds_current_compile1116')
old=json.loads((r/'final_ffn_calendar_model_2340/packets.json').read_text())
legs=[];packed=[]
for p in old:
 for z in p['legs']:
  eligible=len(p['legs'])==1 and z['kind'] in ('local_copy','wide') and z['mask']==255
  prev=packed[-1] if packed else None
  match=prev is not None and prev['eligible'] and eligible and prev['pairs']<4 and all(prev[k]==z[k] for k in ['rank','kind','source','source_leaf','destination','leaf','mask','path']) and z['source_row']==prev['source_row']+2*prev['pairs'] and z['row']==prev['row']+2*prev['pairs']
  if match:prev['pairs']+=1
  else:packed.append(dict(z,eligible=eligible))
ctl=Counter();alias=Counter();size=Counter()
for z in packed:
 eng=0 if z['source']%2 else 1;ctl[z['rank'],eng]+=2;alias[eng]+=2;size[z['pairs']]+=1
new=json.loads((r/'final_ffn_relocation_model_0000/restricted_bulk.json').read_text())
d=dict(schema='opentallas.s81.ffn.relocation-fair-restrictedbulk-comparison.v1',status='MODEL_ONLY_NOT_FIT_827',policy='Both candidates only bulk fullmask singleleg local/wide<=4; any V/multileg/partial staysonepair with2rowscratch.',canonical=dict(packets=len(packed),controls=2*len(packed),separate_rank_engine_floor=max(ctl.values()),aliased_rank_engine_floor=max(alias.values()),packet_sizes=dict(size)),relocated=dict(packets=new['packet_count'],controls=new['control_words'],separate_rank_engine_floor=new['separate_rank_engine_floor'],aliased_rank_engine_floor=new['aliased_rank_engine_floor']),relocation_saving=dict(control_words=2*len(packed)-new['control_words'],separate_rank_control_floor=max(ctl.values())-new['separate_rank_engine_floor'],aliased_rank_control_floor=max(alias.values())-new['aliased_rank_engine_floor']),additional_relocation_storage_bytes_per_rank=5120,remaining_minimum_budget_deficit=405,remaining='1232localtransportissuefloor alreadyexceeds827beforeVS13~75,POST~63,pathages,peerflow,reload; no newRTLeligible or rateclaim.')
(r/'final_ffn_relocation_model_0000/fair_bulk_comparison.json').write_text(json.dumps(d,indent=1)+'\n');print(json.dumps(d))
