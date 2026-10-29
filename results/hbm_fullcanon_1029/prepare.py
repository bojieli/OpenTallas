#!/usr/bin/env python3
"""Prepare a C25 fullcanon5/4/WCOPY1 shadow-plan candidate; source plan remains untouched."""
import json,re,sys,shutil,hashlib
from pathlib import Path
W,P,O=map(Path,sys.argv[1:4]);R=Path(__file__).resolve().parent
M='ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77';BUS={'clk_bank':4,'clk_bank_macro':24,'clk_insert':16,'clk_lane':32}
O.mkdir(parents=True,exist_ok=True)
for f in ['die_plan.json','clock_entries.json','core_conns.json','core_macros.json','type_reduce_report.json']:
 shutil.copy(P/f,O/f)
shutil.copytree(P/'cores',O/'cores',dirs_exist_ok=True)
plan=json.load(open(O/'die_plan.json'));ce=json.load(open(O/'clock_entries.json'));cn=json.load(open(O/'core_conns.json'))
changes=[];done={};entryxy=set()
for tn,t in plan['partition_types'].items():
 for h in t.get('hard_cores',[]):
  if h['module']!=M:continue
  e=ce[tn][h['inst']];entryxy.add(tuple(e['xy_um']));assert e['merged_clock_ports']==list(BUS),e
  cs={k:cn[tn][h['inst']][k] for k in BUS};assert all(v==cs['clk_bank'] for v in cs.values()),cs
  for k in BUS:
   if k!='clk_bank':del cn[tn][h['inst']][k]
  e['merged_clock_ports']=['clk_bank'];e['port']='clk_bank'
  old=h['pins_file'];new=old[:-5]+'__m5a4w1_oneclk.json'
  if old not in done:
   pins=json.load(open(O/old));ck=[p for p in pins if p['name'].split('[')[0] in BUS];assert len(ck)==76
   data=[p for p in pins if p not in ck];c=dict(next(p for p in ck if p['name']=='clk_bank[0]'));c.update(name='clk_bank',x=e['xy_um'][0],y=e['xy_um'][1]);out=data+[c]
   assert [p for p in out if p['name']!='clk_bank']==data
   json.dump(out,open(O/new,'w'),indent=1);done[old]=new
   changes.append(dict(old=old,new=new,clock_bits_old=76,clock_bits_new=1,clock_pin=c,nonclock_count=len(data),nonclock_sha256=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()))
  h['pins_file']=new;h['note']=h.get('note','')+' | CODEX candidate m5/a4/WCOPY1,76same-tap clock aliases->scalar at current centre; array/driver packet'
assert len(entryxy)==1 and changes,entryxy
for f,d in [('die_plan.json',plan),('clock_entries.json',ce),('core_conns.json',cn)]:json.dump(d,open(O/f,'w'),indent=1)
# One source wrapper per type; every clock bus is an alias of the existing scalar same-tap input.
s=(W/'results/die_hbm_kits_1027/fixes/canon_wrappers'/f'{M}.sv').read_text();head,body=s.split(');',1)
for b,n in BUS.items():
 pat=re.compile(r'^\s*input\s+wire\s+\['+str(n-1)+r':0\]\s+'+b+r'\s*,?\s*$\n',re.M);assert len(pat.findall(head))==1,b
 head=pat.sub('    input wire clk_bank,\n' if b=='clk_bank' else '',head)
head=re.sub(r',(\s*)$',r'\1',head)
for b in BUS:body=re.sub(r'\b'+b+r'\b',b+'_v',body)
old='    ot_hbm_su_pg_lanes4_core u_core (';assert body.count(old)==1
body=body.replace(old,'    ot_hbm_su_pg_lanes4_core #(.MLAT(5),.ALAT(4),.WCOPY(1)) u_core (')
(R/'wrappers').mkdir(exist_ok=True)
(R/'wrappers'/f'{M}.sv').write_text(head+');\n'+''.join(f'    wire [{n-1}:0] {b}_v = {{{n}{{clk_bank}}}};\n' for b,n in BUS.items())+body)
# Replace only the same 24 source-listed macro instances, dimensions and R0 orientation explicit.
cm=json.load(open(O/'core_macros.json'));oldms=cm['cores'][M]['macros'];newms=json.load(open(R/'macros.json'))['placements']
assert {p['name'].removeprefix('u_fcore.') for p in oldms}=={p['inst'] for p in newms}
assert len(oldms)==len(newms)==24
cm['cores'][M]['macros']=[dict(name='u_fcore.'+p['inst'],master=p['macro'],rect_um=[p['xy_um'][0],p['xy_um'][1],round(p['xy_um'][0]+94.824,3),round(p['xy_um'][1]+41.064,3)],orient=p['orient']) for p in newms]
cm['cores'][M]['basis']='CODEX current C25 bank-aware candidate; same24 instances/outline, positive pre-build estimate, no physical closure claim'
json.dump(cm,open(O/'core_macros.json','w'),indent=1)
json.dump(dict(module=M,source_plan_sha256=hashlib.sha256((P/'die_plan.json').read_bytes()).hexdigest(),profile=dict(MLAT=5,ALAT=4,WCOPY=1),pins=changes,clock_entries=len([e for t in ce.values() if isinstance(t,dict) for e in t.values() if isinstance(e,dict) and e.get('module')==M]),entry_xy_um=list(next(iter(entryxy))),macro_instances_preserved=24,owner_adoption='PENDING die owner; shadow candidate only',cycles='ALAT4 adds1 per add vs3; tokens_hbm priced programme deltas, before adoption'),open(O/'candidate_report.json','w'),indent=1)
print(json.dumps(dict(module=M,entry_xy=list(next(iter(entryxy))),nonclock_pins=changes[0]['nonclock_count'],macro_instances=24)))
