from pathlib import Path
import json,shutil,hashlib
p=Path('/srv/opentallas-scratch2/claude/codex-kv-pv-resume-1029')
kits=[p/'e0_converge_04',Path('/srv/opentallas-scratch2/claude/codex-kv-pvj-load-1029/kits/ot_qwen_tp8_pv_join_t__172.8x172.8')]
pre='''# Reviewed selected-RC data repair replacement; preserve original clock/inputframe hooks.
source /work/grt_pre_core.tcl
source /work/clk_freeze.tcl
set ::ot_coupled_outer [file join $::env(RESULTS_DIR) coupled_outer_[clock microseconds]]
file mkdir $::ot_coupled_outer
ot_clk_freeze $::ot_coupled_outer
'''
post='''# Runs after ORFS recover_power/antenna/data mutations, immediately before final checkpoint writes.
source /work/grt_post_core.tcl
source /work/final_ff_hold.tcl
ot_final_ff_converge
source /work/pg_connect.tcl
ot_pg_connect_all coupled_final
ot_pg_require_bound coupled_final
ot_clk_freeze_assert coupled_final
ot_clk_dump $::ot_coupled_outer/clk_final.tsv final $::ot_coupled_outer/clk_freeze_nets.txt
puts [exec python3 -I /work/clk_geom_diff.py $::ot_coupled_outer/clk_freeze_pre.tsv $::ot_coupled_outer/clk_final.tsv --json $::ot_coupled_outer/clock_diff.json]
puts "COUPLED_GRT_FINAL_PASS_NO_DRT"
'''
for k in kits:
 for n in ['final_ff_hold.tcl','clk_freeze.tcl','clk_geom_diff.py']:shutil.copy2(p/n,k/n)
 (k/'coupled_grt_pre.tcl').write_text(pre);(k/'coupled_grt_post.tcl').write_text(post)
 c=k/'config.mk';s=c.read_text();assert 'coupled_grt'not in s
 s+='\n# CODEX reviewed actual-selected-RC repair replaces stalled legacy incremental repair. Same margins/constraints.\noverride export SKIP_INCREMENTAL_REPAIR = 1\noverride export PRE_GLOBAL_ROUTE_TCL = /work/coupled_grt_pre.tcl\noverride export POST_GLOBAL_ROUTE_TCL = /work/coupled_grt_post.tcl\n';c.write_text(s)
 base=next(k.glob('run/results/asap7/*/base'))
 if not(base/'4_cts.odb').exists():shutil.copy2(base/'4_1_cts.odb',base/'4_cts.odb')
 rec=dict(method='actual selected-RC coupled data-only hold/DRV repair after ordinary routing/recoverpower/antenna; no DRT',helper_commit='798d747f7',clock='pre-GRT frozen plus outer before/after exactgeometry gate',constraints='unchanged actual833/60/25, IO−40/0, FF202.5; e0margin10/PVJmargin5',ordering='sourcepre -> pinaccess -> globalroute -> skip legacy incrementalrepair -> ordinaryrecoverpower/antenna -> selectedRC helper -> PGbind -> outerclockdiff -> writes',helpers={n:hashlib.sha256((k/n).read_bytes()).hexdigest()for n in ['final_ff_hold.tcl','clk_freeze.tcl','clk_geom_diff.py']},checkpoint_sha256=hashlib.sha256((base/'4_cts.odb').read_bytes()).hexdigest())
 (k/'coupled_grt_recipe.json').write_text(json.dumps(rec,indent=1)+'\n')
 print('PREPARED_COUPLED_GRT',k,rec['checkpoint_sha256'])
