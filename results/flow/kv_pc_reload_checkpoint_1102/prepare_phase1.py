from pathlib import Path
import hashlib,json,shutil
S=Path('/srv/opentallas-scratch2/claude/codex-pc-eco-2135/r27c_m10')
D=Path('/srv/opentallas-scratch2/claude/codex-pc-reload-0018/repair')
D.parent.mkdir();D.parent.joinpath('.keep').touch()
def ignore(root,names):
    out=[]
    for n in names:
        if n in {'run','views','signoff','lec','lec_post','.ot-run-spill-copy','rc.txt','after_repair_source.odb','native_after_repair_receipt.json','checkpoint_reuse.json'} or n.endswith(('.log','.odb','.def','.spef','.png','.webp')):out.append(n)
        elif n.startswith('lec_async.') and n!='lec_async.sh':out.append(n)
    return out
shutil.copytree(S,D,ignore=ignore)
base=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base');(D/base).mkdir(parents=True)
for n in ['1_2_yosys.v','4_cts.odb','4_cts.sdc','6_final.spef']:shutil.copy2(S/base/n,D/base/n)
footer='detailed_placement\nglobal_route -end_incremental\not_clk_freeze_assert post_grt\nestimate_parasitics -global_routing\nwrite_guides $::env(RESULTS_DIR)/route.guide\n'
p=D/'eco_route.tcl';s=p.read_text();assert s.endswith(footer)
s=s[:-len(footer)]+'''# PC native Signal11 case: retain true repaired state before DPL / dirty-net finalization.
# This checkpoint is NOT a completed GRT and this process is invoked only as do-5_1_grt.
puts "PC_REPAIR_CHECKPOINT writing unqualified post-repair state before DPL"
write_db /work/repair_checkpoint.raw.odb
ot_clk_freeze_assert repair_checkpoint
source /work/pg_connect.tcl
ot_pg_connect_all pc_repair_checkpoint
ot_pg_require_bound pc_repair_checkpoint
write_db /work/repair_checkpoint.odb
write_sdc -no_timestamp /work/repair_checkpoint.active_mode.sdc
ot_clk_dump /work/repair_checkpoint.clock.tsv repair_checkpoint
set pc_rc [open /work/REPAIR_CHECKPOINT w]
puts $pc_rc "REPAIR_ONLY_UNQUALIFIED_GRT: DB saved before DPL; original SDC/MM frame must be retained on reload"
close $pc_rc
exit 0
'''
p.write_text(s)
old=(D/'ECO.json').read_text();(D/'ECO.original.json').write_text(old)
rec={'schema':'opentallas.pc_repair_checkpoint_case.v1','source':str(S),'clock_reference':'original routed r27c 5_2_route copied as immutable4_cts.odb','source_rtl_changed':False,'sdc_changed':False,'clock_policy_changed':False,'phase':'repair checkpoint only; NOT qualified GRT','source_hashes':{str(n):hashlib.sha256((D/base/n).read_bytes()).hexdigest() for n in ['1_2_yosys.v','4_cts.odb','4_cts.sdc','6_final.spef']},'eco_source_sha256':hashlib.sha256(s.encode()).hexdigest(),'stale_1528_checkpoint_excluded':True,'next':'fresh-process native DPL and fresh data GRT, explicit original_route ref, no second repair, normal freeze/signoff'}
(D/'CASE.json').write_text(json.dumps(rec,indent=2)+'\n')
print(D)
