"""Compose q6 candidate slots onto source-qualified S1/two-dimensional sys_c plan.
All deltas are physical sites; fail closed on bus/width/station change. Not adoption.
"""
import json,sys,copy
from pathlib import Path
r=Path(sys.argv[1]);base=json.load(open(r/'hm_r26q6_s1.json'));ledger=[]
for tn,filename in [('kv3_hgi_v8','hm_r26q6_v8_split.json'),('kv3_hub_Wi','hm_r26q6_wi_split.json')]:
 donor=json.load(open(r/filename));a=base['partition_types'][tn];b=donor['partition_types'][tn];aa=copy.deepcopy(a);bb=copy.deepcopy(b);aa.pop('ft_slots');bb.pop('ft_slots');assert aa==bb,(tn,'non-FT delta')
 old={q['name']:q for q in a['ft_slots']};new={q['name']:q for q in b['ft_slots']};assert old.keys()==new.keys()
 for n,q in old.items():
  for key in ['width','stations','in_bus','out_bus']:assert q.get(key)==new[n].get(key),(tn,n,key)
 a['ft_slots']=copy.deepcopy(b['ft_slots']);ledger.append(dict(type=tn,slots=len(old),source=filename,cycles_added=0))
(r/'hm_r26q6_combined_candidate.json').write_text(json.dumps(base,indent=1)+'\n');(r.parent/'q6_composition_ledger.json').write_text(json.dumps(dict(status='UNADOPTED_FT_COUPONS_AND_PG_HOLD',merged=ledger,pg='UNCHANGED_Q5B_NOT_SIGNED',pv_tap='S1_SOURCE_QUALIFIED',sys_c_release_delta=2),indent=1)+'\n')
