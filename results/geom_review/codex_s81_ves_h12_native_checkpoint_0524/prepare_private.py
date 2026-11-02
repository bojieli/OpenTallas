from pathlib import Path
import json,hashlib,shutil
r=Path('/srv/opentallas-scratch2/claude/codex-ves-h12-prep-0524');k=r/'pass_m12';b=k/'run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base';orig=r/'base/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base';receipt={'scope':'OWN_TYPED_ROUTED_GRT_PREP_ONLY','changes':{}}
if (k/'PRIVATE_ROUTED_PREP.json').exists():raise SystemExit('REFUSE_REPEATED_PREP')
def change(name,before,after):
 f=k/name;assert f.read_text().count(before)==1,(name,'anchor count');a=f.read_bytes();f.write_text(f.read_text().replace(before,after));receipt['changes'].setdefault(name,[]).append({'before':hashlib.sha256(a).hexdigest(),'after':hashlib.sha256(f.read_bytes()).hexdigest(),'old':before,'new':after})
receipt['prior_canonical_route_to_cts_alias_sha256']=hashlib.sha256((b/'4_cts.odb').read_bytes()).hexdigest();shutil.copy2(orig/'4_cts.odb',b/'4_cts.odb');shutil.copy2(orig/'4_cts.sdc',b/'4_cts.sdc')
change('prd_route_keep.tcl','set ref_odb $::env(RESULTS_DIR)/4_cts.odb','set ref_odb /work/baseline/6_final.odb')
change('prd_route_keep.tcl','  set clk [dict create]','  foreach name [dict get $sel rip] {if {[info exists ::ves_reset_preserve] && $name in $::ves_reset_preserve} {error "VES_RESET_DIRTY_FORBIDDEN $name"}}\n  set clk [dict create]')
change('prd_hook.tcl','# A measured OpenROAD route-tree defect may require preserving a specific data','source /work/reset_freeze.tcl\n# A measured OpenROAD route-tree defect may require preserving a specific data')
with (k/'config.mk').open('a') as f:f.write('\n# OWN typed routed-source GRT-only native-PG checkpoint; no later-stage admission\noverride export PRE_GLOBAL_ROUTE_TCL = /work/native_pg_birth_pre.tcl\noverride export POST_GLOBAL_ROUTE_TCL = /work/native_pg_birth_post.tcl\n')
p=json.loads((k/'PRD.json').read_text());p['source_route']=str(k/'baseline/6_final.odb');p['original_source']='intel1:/srv/opentallas-scratch2/claude/codex-s81-ves-2042/kit';p['source_seed_kind']='REAL_ROUTED_6_FINAL';p['original_cts_kept']=True;p['cts_credit']=False;p['GRT_only']=True;p['later_DRT_fill_finish_held']=True;(k/'PRD.json').write_text(json.dumps(p,indent=2))
receipt['baseline_ODB_sha256']=hashlib.sha256((k/'baseline/6_final.odb').read_bytes()).hexdigest();receipt['original_CTS_ODB_sha256']=hashlib.sha256((b/'4_cts.odb').read_bytes()).hexdigest();receipt['original_CTS_SDC_sha256']=hashlib.sha256((b/'4_cts.sdc').read_bytes()).hexdigest();receipt['stage5_outputs']=[p.name for p in b.glob('5*')];receipt['routed_seed_alias_present']=receipt['baseline_ODB_sha256']==receipt['original_CTS_ODB_sha256']
assert not receipt['routed_seed_alias_present'] and not receipt['stage5_outputs']
(k/'PRIVATE_ROUTED_PREP.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=1))
