from pathlib import Path
import hashlib,json,shutil
S=Path('/srv/opentallas-scratch2/claude/codex-pc-reload-0018/repair')
D=S.parent/'finalize'
HERE=Path(__file__).parent
assert (S/'RESULT').read_text().strip()=='REPAIR_CHECKPOINT_READY_UNQUALIFIED_GRT'
assert json.loads((S/'repair_checkpoint.clock_diff.json').read_text())['verdict']=='PASS'
def ignore(root,names):
    return [n for n in names if n in {'run','views','signoff','lec','lec_post','.ot-run-spill-copy','RESULT','REPAIR_CHECKPOINT','rc.txt'} or n.endswith(('.log','.odb','.def','.spef','.tsv'))]
shutil.copytree(S,D,ignore=ignore)
B=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base')
(D/B).mkdir(parents=True)
for n in ['1_2_yosys.v','4_cts.sdc','6_final.spef']:
    shutil.copy2(S/B/n,D/B/n)
shutil.copy2(S/'repair_checkpoint.odb',D/B/'4_cts.odb')
shutil.copy2(S/B/'4_cts.odb',D/'original_route.odb')
shutil.copy2(S/B/'clk_freeze_pre.tsv',D/'ORIGINAL.clock.tsv')
for n in ['reload_pre.tcl','reload_post.tcl']:
    shutil.copy2(HERE/n,D/n)
for n in ['eco_drt_pre.tcl','prd_route_keep.tcl']:
    shutil.copy2(HERE/n,D/n)
with (D/'config.mk').open('a') as f:
    f.write('''\n# PC true repair checkpoint reload: native DPL + fresh GRT only.
override export PRE_GLOBAL_ROUTE_TCL = /work/reload_pre.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/reload_post.tcl
override export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl
override export RECOVER_POWER = 0
override export OPT_POST_GRT_WNS = 1
''')
rec={'schema':'opentallas.pc_fresh_finalization.v1','repair_checkpoint_sha256':hashlib.sha256((S/'repair_checkpoint.odb').read_bytes()).hexdigest(),'original_routed_reference_sha256':hashlib.sha256((D/'original_route.odb').read_bytes()).hexdigest(),'original_sdc_sha256':hashlib.sha256((D/B/'4_cts.sdc').read_bytes()).hexdigest(),'repair_again':False,'source_unchanged':True,'clock_diff_reference':'ORIGINAL.clock.tsv','phase1_receipt':str(S/'CASE.json'),'phase':'UNQUALIFIED until native route/clock/PG/TT/FF/DRV/DRC/LEC gates'}
(D/'FRESH_FINALIZATION.json').write_text(json.dumps(rec,indent=2)+'\n')
print(D)
