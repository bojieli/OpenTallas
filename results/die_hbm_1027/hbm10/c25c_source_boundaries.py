"""SRC OUT SCORER_PACKET KEYBUF_PACKET: exact proved source boundary adoption.
No arithmetic, placement, latency or timing authority is inferred by this transform.
"""
import json,sys,shutil,hashlib,re
from pathlib import Path
src,out,sp,kp=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
for f in src.glob('*.json'):shutil.copy2(f,out/f.name)
shutil.copytree(src/'cores',out/'cores',dirs_exist_ok=True)
p=json.load(open(src/'die_plan.json')); scorer=json.load(open(sp)); keybuf=json.load(open(kp));part={x['name']:x['type'] for x in p['partitions']};changed=[];done={};renames={}
for row in scorer['exact_children']:
 tn=part[row['partition']];t=p['partition_types'][tn];cs=[c for c in t['hard_cores'] if c['inst']==row['plan_inst']];assert len(cs)==1,(tn,row);c=cs[0];assert c['module'] in (row['previous_module'],row['module']);old=c['pins_file']
 mode='h0' if row['module'].endswith('_h0') else 'tail' if row['module']=='ot_hbm_idx_tail_native' else None
 if mode:
  new='cores/'+Path(old).stem+'__c25c_native.json'
  if old.endswith('__c25c_native.json'):
   continue
  if old not in done:
   pins=json.load(open(src/old));before=len(pins)
   if mode=='h0':
    removed=[q['name'] for q in pins if q['name']=='cf_in' or re.fullmatch(r'cs_in\[\d+\]',q['name'])];assert len(removed)==33,(old,removed);pins=[q for q in pins if q['name'] not in removed]
   else:
    for q in pins:q['name']=re.sub(r'^ge_[01]_u_t_','',q['name']) if q['name']!='clk_tail' else 'clk'
    assert len(pins)==612 and len({q['name'] for q in pins})==612
   (out/new).write_text(json.dumps(pins,indent=1));done[old]=new
  c['pins_file']=new;c['module']=row['module'];c['note']=c.get('note','')+' | C25c exact native source boundary; source recipe DELIVERED_RESET=1/MUT=0, no timing qualification'
  for x in t['contents']:
   if x['inst']==c['inst']:x['module']=row['module']
  if mode=='tail':
   for tap in t['clock'].get('taps',[]):
    if tap['name'] in (c['inst'],c['inst']+'.clk_tail'):
     if tap['name'].endswith('.clk_tail'):tap['name']=c['inst']+'.clk'
     tap['budget_owner']=row['module']
   renames[(tn,c['inst'])]='clk_tail'
  changed.append(dict(type=tn,inst=c['inst'],module=c['module'],pins_file=new,recipe_params=row['params']))
assert len(changed)>0
# Shared partition types are transformed once; source instance census remains264.
for row in keybuf['active']:
 t=p['partition_types'][part[row['partition']]];c=next(c for c in t['hard_cores'] if c['inst']==row['plan_inst']);assert c['module']==row['module'];c['parent_id_straps']=row['parent_id_straps'];c['position_id_contract']=row['position_id_contract']
removed=[]
for row in keybuf['reserved_unbound']:
 tn=part[row['partition']];t=p['partition_types'][tn];inst=row['inst'];old=[c for c in t['hard_cores'] if c['inst']==inst];assert len(old)==1
 # Source census proves these exact slots absent. Station inventory was separately checked;
 # fail closed if the current candidate has acquired any station referencing them.
 assert inst not in json.dumps(t.get('internal_stations',[])),inst
 t['hard_cores']=[c for c in t['hard_cores'] if c['inst']!=inst];t['contents']=[c for c in t['contents'] if c['inst']!=inst];t['clock']['taps']=[c for c in t['clock'].get('taps',[]) if c['name']!=inst and not c['name'].startswith(inst+'.')];removed.append(dict(type=tn,inst=inst))
assert len(removed)==16
# Remove/rename only exact stale interface keys; this is not regeneration of source graph.
for fn in ('clock_entries.json','core_conns.json'):
 side=json.load(open(src/fn))
 for row in keybuf['reserved_unbound']:side.get(part[row['partition']],{}).pop(row['inst'],None)
 for row in scorer['exact_children']:
  if row['module']!='ot_hbm_idx_tail_native':continue
  tn=part[row['partition']];node=side.get(tn,{}).get(row['plan_inst'])
  if not node:continue
  if fn=='clock_entries.json':
   node['port']='clk';node['module']=row['module'];node['merged_clock_ports']=[]
   if node.get('tap','').endswith('.clk_tail'):node['tap']=node['tap'][:-8]+'clk'
  else:
   replacement={re.sub(r'^ge_[01]_u_t_','',k) if k!='clk_tail' else 'clk':v for k,v in node.items()}
   side[tn][row['plan_inst']]=replacement
 (out/fn).write_text(json.dumps(side,indent=1))
(out/'die_plan.json').write_text(json.dumps(p,indent=1))
r=dict(schema='opentallas.hbm.c25c_source_boundaries.v1',source_sha256=hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest(),scorer_exact_children=264,scorer_changed=changed,keybuf_active=keybuf['active'],keybuf_removed_source_absent=removed,active_keybuf_srams=80,packed_reference_srams=68,old_plan_srams=160,cycles_added=0,qualification='SOURCE_BOUNDARY_ONLY; sidecar graph regeneration, native GEN params, strict bind and all physical gates remain required')
(out/'c25c_source_boundaries_report.json').write_text(json.dumps(r,indent=1));print(json.dumps({k:v for k,v in r.items() if k not in ('scorer_changed','keybuf_active','keybuf_removed_source_absent')},indent=1))
