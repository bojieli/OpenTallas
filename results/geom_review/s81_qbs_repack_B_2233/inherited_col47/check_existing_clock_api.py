from pathlib import Path
import json,sys,copy,re
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import schema as S,gen_phys as G,kit_core_clocks as K
R=Path(__file__).parent;J=json.load(open(R/'clock_context.json'));t=copy.deepcopy(J['type']);tn=t['module'];M={e['inst']:e for e in json.load(open(R/'DISABLED_physical_identity_overlay.json'))['content_identity_patch']}
for c in t.get('hard_cores',[])+t.get('contents',[]):
 if c['inst']in M:
  c.update({k:v for k,v in M[c['inst']].items()if k!='inst'})
updates=[]
for i,tp in enumerate(t['clock']['taps']):
 old=tp['name'];assert old.endswith('.ck');tp['name']=old[:-3]+'.clk'
 if i==2:tp['xy']=[298.592,561.568]
 updates.append(dict(index=i,old_name=old,new_name=tp['name'],xy=tp['xy']))
p=S.Plan(dict(die=J['die'],partition_types={tn:t},partitions=[],ports=[],lanes=[],clock={'insertion_ps':250,'insertion_ff_ps':202.5}))
rows=G.core_tap_rows(p,tn);bound=(R/'bound.sv').read_text();text,receipt=K.wire(bound,tn+'_bound',rows)
assert len(receipt)==6 and sum(q['mode']=='rtl'for q in receipt)==4
for q in receipt:
 assert q['pin']=='clk'
 if q['mode']=='rtl':assert re.search(r'\.clk\(\s*'+q['port']+r'\s*\)',text)
(R/'DISABLED_clock_binding_overlay.json').write_text(json.dumps(dict(type=tn,scope='DISABLED existing-API source-only repair recipe; regenerate exactnextS39; no adoption',clock_tap_updates=updates,core_tap_rows=rows,private_kit_clock_receipt=receipt),indent=2)+'\n');(R/'clock_binding_dry_result.json').write_text(json.dumps(dict(scope='Existing gen_phys+kit_core_clocks API exercised on OWN COPY of exacthistorical bound text only; noGEN/physical/job',core_tap_rows=len(rows),private_direct_RTL_rewires=sum(q['mode']=='rtl'for q in receipt),nested_physical_taps=sum(q['mode']=='physical_tap'for q in receipt),cycles_changed=0,common_tool_changes=0,source_bind_changes=0,missing_or_ambiguous_clock_pins=[]),indent=2)+'\n');print(json.dumps(receipt,indent=2))
