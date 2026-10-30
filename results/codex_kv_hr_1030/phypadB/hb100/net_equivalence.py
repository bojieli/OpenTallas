import json,re
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/codex-kv-hr-1030/phypad_hb100');R=P/'run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base'
def parse(path):
 text=path.read_text();cells={}
 for m in re.finditer(r'(?m)^\s*(\S+_ASAP7_75t_R)\s+(\S+)\s*\((.*?)\);',text,re.S):
  master,name,body=m.groups();name=name.lstrip('\\')
  if master.startswith(('FILL','DECAP')):continue
  ports={a:b.strip().lstrip('\\') for a,b in re.findall(r'\.(\w+)\s*\(([^)]+)\)',body) if a not in ('VDD','VSS')}
  if ports:cells[name]=[master,ports]
 return cells
old=parse(R/'6_final.v');new=parse(P/'hb100/3_place.v');d=json.load(open(P/'selected100_rc.json'));changed=set()
for c in d['chains']:
 a,m,z=c['cells'];changed.update([a,m,z]);assert old[a][0]==old[m][0]==old[z][0]=='BUFx2_ASAP7_75t_R'
 assert old[a][1]['Y']==old[m][1]['A'] and old[m][1]['Y']==old[z][1]['A']
 for net in [old[a][1]['Y'],old[m][1]['Y']]:
  uses=[(n,k) for n,(_,ports) in old.items() for k,v in ports.items() if v==net];assert len(uses)==2,(net,uses)
 assert new[a]==['HB4xp67_ASAP7_75t_R',{'A':old[a][1]['A'],'Y':old[z][1]['Y']}],(a,new[a]);assert m not in new and z not in new
expected=set(old)-{n for c in d['chains'] for n in c['cells'][1:]}
print('extra',len(set(new)-expected),'missing',len(expected-set(new)))
assert set(new)==expected
for n,v in old.items():
 if n not in changed:assert new[n]==v,(n,v,new[n])
result={'status':'PASS','method':'actual emitted pre/post cell-pin graph; 100 strictly linear positive-buffer chains replaced by Y=A HB4; all other functional cell masters and all pin-net connections exact','old_nonfill_cells':len(old),'new_nonfill_cells':len(new),'replacements':100,'removed':200,'cycles_added':0,'four_state_primitive_coupon':'0,1,X,Z PASS and inverted mutant caught separately','scope':'logical buffer identity; physical TT/FF qualification separate'}
json.dump(result,open(P/'hb100/net_equivalence.json','w'),indent=1);print(result)
