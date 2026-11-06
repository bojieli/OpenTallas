from pathlib import Path
from itertools import zip_longest
import hashlib,json,re
R=Path('/srv/opentallas-scratch2/claude/codex-qc-tapsplit-1106');d=R/'canary_cbn_97'
report={'source':'a3ab6b89bd','prototype_only':True,'physical_cts':'NOT RUN','instances_unchanged':0,'pins_unchanged':0,'clock_pins_changed':0,'invalid_changes':[],'examples':[]}
for a,b in zip_longest((d/'after_A.tsv').open(),(d/'after_B.tsv').open()):
 if a is None or b is None:raise ValueError('different instance/pin census')
 aa=a.split();bb=b.split()
 if aa[0]=='I':
  assert a==b;report['instances_unchanged']+=1;continue
 if a==b:report['pins_unchanged']+=1;continue
 report['clock_pins_changed']+=1
 if aa[:3]!=bb[:3] or aa[2] not in ('CLK','CK','clk') or not re.search(r'(u_d\d+_|u_lpad_|u_r8b_strap_|u_pd\d+_)',aa[1]) or not all(x.startswith('ot_proto_clk_') for x in [aa[3],bb[3]]):report['invalid_changes'].append([aa,bb])
 if len(report['examples'])<5:report['examples'].append([aa,bb])
assert not report['invalid_changes'],report['invalid_changes'][:3]
# Every declared joined group is within unchanged bound, and exact chain-group
# memberships come from the actual captured positive register clocks.
groups={}
for line in (d/'ot_tap_chain_groups.tsv').read_text().splitlines()[1:]:
 a=line.split('\t');groups.setdefault(a[0],[]).append(a)
taps=json.loads((R/'ev/model.json').read_text())['cbn_q00__cldbcda913']['new_tap_rows'];tapxy={'ot_proto_clk_'+str(j):(row[1],row[2]) for j,row in enumerate(taps)}
maxreach=0
for rows in groups.values():
 assert len(rows)<=128
 for a in rows:
  x,y=tapxy[a[1]];reach=abs(float(a[6])-x)+abs(float(a[7])-y);assert reach<=200+1e-6;maxreach=max(maxreach,reach)
report.update(joined_groups=len(groups),max_joined_group_reach_um=maxreach)
loads={}
for line in (d/'after_B.tsv').open():
 a=line.split()
 if a[0]=='P' and len(a)>3 and a[3].startswith('ot_proto_clk_'):loads[a[3]]=loads.get(a[3],0)+1
assert max(loads.values())<=1200
report['max_grid_load']=max(loads.values());(d/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
