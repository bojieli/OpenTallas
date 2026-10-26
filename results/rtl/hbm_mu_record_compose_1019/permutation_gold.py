exec((__import__('pathlib').Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019/guard_profile.py')).read_text().split('n=0\n')[0])
from pathlib import Path
import json
# Address/sector identity comes from the actual compiler placement, not lane assumptions.
data=dict(fixture['vm_in']);pairs=[]
for bank in [0,1]:
 sectors=sorted(sec for sec in r['preload'] if sec%8==bank)
 assert len(sectors)==2,sectors
 a,b=(r['preload'][sec]for sec in sectors)
 for x,y in zip(a,b):data[x],data[y]=data[y],data[x];pairs.append((x,y))
place=LI.Placement(0);place.nxt=[33]*8
second=LI.su_record(raw,data=data,place=place,pad_zero=True,timing=NativeTiming(18,15),safe_calendar=True)
assert second['lines']==r['lines']
proof=[]
for bank in [0,1]:
 one=sorted((e for e in r['expect']if e['sector']%8==bank),key=lambda e:e['sector'])
 two=sorted((e for e in second['expect']if e['sector']%8==bank),key=lambda e:e['sector'])
 assert len(one)==len(two)==2
 assert two[0]['value']==one[1]['value'] and two[1]['value']==one[0]['value']
 for k,e in enumerate(two):proof.append(dict(bank=bank,sector=e['sector'],words=e['words'],value=e['value'],request0_source_sector=one[1-k]['sector']))
print('INDEPENDENT_HDC_GOLDEN_PERMUTATION PASS original32 words, exact record operator, same programme')
Path('permutation_gold.json').write_text(json.dumps(dict(operator=r['sut'],input_address_pairs=pairs,outputs=proof),indent=2))
