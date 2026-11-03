from pathlib import Path
import hashlib,json,shutil
S=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-birth-1102/repair');D=S.parent/'grt_only';H=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not D.exists(),'never overwrite a capsule'
assert sha(S/'repair_checkpoint.odb')=='59d797ccd83581ad87d59d8b191cb73b94916e9fd9db198c5d49c5858ffd4db2'
assert 'PC_NATIVE_PROTECTED_REPAIR_CHECKPOINT_READY active=0' in (S/'repair_phase.log').read_text()
assert json.load(open(S/'repair_checkpoint.clock_diff.json'))['verdict']=='PASS'
assert (S/'PG_BIRTH_CLEANUP_PASS').stat().st_size>0
ignore_names={'run','views','signoff','lec','lec_post','physical_completion','__pycache__','.ot-run-spill-copy','RESULT','REPAIR_CHECKPOINT','rc.txt','PG_BIRTH_CLEANUP_PASS','FRESH_GRT_NATIVE_CLEANUP_PASS'}
def ignore(root,names):
 return [n for n in names if n in ignore_names or n.endswith(('.log','.odb','.def','.spef','.tsv')) or n.startswith(('CHECKPOINT_CENSUS','ORIGINAL_COMPONENTS','checkpoint_points'))]
shutil.copytree(S,D,ignore=ignore)
B=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base');(D/B).mkdir(parents=True)
for n in ['1_2_yosys.v','4_cts.sdc','4_1_cts.odb','6_final.spef']:
 shutil.copy2(S/B/n,D/B/n)
assert sha(S/B/'4_cts.odb')=='68650b4a50d838feab16db8b742775f5e05b1904d6e6a34687ea0faf14767404'
shutil.copy2(S/'repair_checkpoint.odb',D/B/'4_cts.odb')
shutil.copy2(S/B/'4_cts.odb',D/'original_route.odb')
shutil.copy2(S/'ORIGINAL.clock.tsv',D/'ORIGINAL.clock.tsv')
for n in ['reload_pre.tcl','reload_post.tcl','eco_drt_pre.tcl','prd_route_keep.tcl','patch_entry.py','pc_native_grt_only.sh','audit_saved.tcl','audit_only.mk']:
 shutil.copy2(H/n,D/n)
assert sha(D/'native_pg_binding.tcl')=='e19c5fd9872e37f68d610e2dc46608359c9970b7c9e6de84f546f3b3c3ea3a2d'
assert sha(D/'nativepgbirth.so')=='8c9e1eef9ec6451a5bc1710da15fe683785aa8791d21099e4ee9ec30fee0a93b'
with (D/'config.mk').open('a') as f:f.write('''\n# Explicit bounded fresh process: only DPL+data GRT, no second repair.\noverride export PRE_GLOBAL_ROUTE_TCL = /work/reload_pre.tcl\noverride export POST_GLOBAL_ROUTE_TCL = /work/reload_post.tcl\noverride export SKIP_INCREMENTAL_REPAIR = 1\noverride export SKIP_ANTENNA_REPAIR = 1\noverride export RECOVER_POWER = 0\noverride export OPT_POST_GRT_WNS = 1\noverride export GENERATE_ARTIFACTS_ON_FAILURE = 0\noverride export OT_PG_STRICT = 1\n''')
rec={'schema':'pc.protected_fresh_dpl_grt_only.v1','repair_checkpoint':sha(D/B/'4_cts.odb'),'original_current_routed_gold':sha(D/'original_route.odb'),'native_helper':sha(D/'native_pg_binding.tcl'),'native_module':sha(D/'nativepgbirth.so'),'repair_again':False,'stage':'do-5_1_grt only','resource':{'gb':32,'threads':8,'disk_gb':5},'status':'PREP_ONLY_NOT_DISPATCHED'}
(D/'FRESH_GRT_PREP.json').write_text(json.dumps(rec,indent=2)+'\n')
files={str(p.relative_to(D)):sha(p) for p in sorted(D.rglob('*')) if p.is_file()}
(H/'STAGED_READSET.json').write_text(json.dumps(files,indent=2)+'\n')
print(json.dumps(rec));print('staged',len(files))
