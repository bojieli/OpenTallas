from pathlib import Path
import json,hashlib,shutil
R=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102');S=R/'grt_only';D=R/'drt_only';H=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not D.exists(),'never overwrite a capsule'
assert (S/'RESULT').read_text().strip()=='DPL_DATA_GRT_COMPLETE_REOPENED_PG_PASS_NOT_SIGNED'
assert json.load(open(S/'SAVED_GRT_PG_AUDIT.json'))['failure_count']==0
assert json.load(open(S/'original_to_grt.clock_diff.json'))['verdict']=='PASS'
B=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base')
assert sha(S/B/'5_1_grt.odb')=='4342fc7ada90cf8c4def596e0b3ab47bd9a65bd877776061927beb4b2a1905b5'
assert sha(S/B/'5_1_grt.sdc')=='33eedc741276a249b53e5f029c3c4e451d1e3bd76fa0153be7c7c5f3c77f1e48'
exclude={'run','views','signoff','lec','lec_post','physical_completion','__pycache__','.ot-run-spill-copy','RESULT','REPAIR_CHECKPOINT','PG_BIRTH_CLEANUP_PASS','FRESH_GRT_NATIVE_CLEANUP_PASS','SAVED_GRT_PG_AUDIT.json','ACTUAL_GRT_OUTPUTS.json'}
def ignore(root,names):return [n for n in names if n in exclude or n.endswith(('.log','.odb','.def','.spef','.tsv')) or n.startswith(('CHECKPOINT_CENSUS','ORIGINAL_COMPONENTS','checkpoint_points'))]
shutil.copytree(S,D,ignore=ignore);(D/B).mkdir(parents=True)
for n in ['5_1_grt.odb','5_1_grt.sdc','route.guide','1_2_yosys.v','4_cts.sdc','4_1_cts.odb','clk_freeze_pre.tsv','clk_freeze_nets.txt']:
 shutil.copy2(S/B/n,D/B/n)
shutil.copy2(S/'ORIGINAL.clock.tsv',D/'ORIGINAL.clock.tsv')
for n in ['patch_private_drt.py','private_drt_driver.tcl','pg_drt_diag_init.tcl','pg_drt_diag_before_save.tcl','pg_drt_diag_library_guard.tcl','preflight.tcl','preflight.mk','preflight.sh','run_drt_only.sh']:
 shutil.copy2(H/n,D/n)
a=(S/'audit_saved.tcl').read_text()
assert a.count('load_design 5_1_grt.odb 5_1_grt.sdc')==1
a=a.replace('load_design 5_1_grt.odb 5_1_grt.sdc','load_design 5_2_route.odb 5_1_grt.sdc').replace('SAVED_GRT_PG_AUDIT.json','SAVED_ROUTE_PG_AUDIT.json').replace('INDEPENDENT_SAVED_GRT_PG_PASS','INDEPENDENT_SAVED_ROUTE_PG_PASS')
(D/'audit_saved.tcl').write_text(a)
assert sha(D/'eco_drt_pre.tcl')=='bdda428129a59ba06014d747b1f4caa2a61d8aab4a67697622d4e6b05be53dfd'
assert sha(D/'native_pg_binding.tcl')=='e19c5fd9872e37f68d610e2dc46608359c9970b7c9e6de84f546f3b3c3ea3a2d'
assert sha(D/'nativepgbirth.so')=='8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b'
(D/'DRT_INPUTS.json').write_text(json.dumps({'status':'PREP_ONLY_NO_DISPATCH','source_GRT':'4342fc7a','source_SDC':'33eedc74','scope':'ordinary DRT only; no filler/finish/STA/source/repair variant','normal_antenna_policy':'must be collected, not overridden','resource':{'gb':32,'threads':8,'disk_gb':5}},indent=2)+'\n')
print(D)
