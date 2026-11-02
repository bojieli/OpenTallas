from pathlib import Path
import hashlib,json,os,shutil,subprocess
R=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-1102')
S=Path('/srv/opentallas-scratch2/claude/codex-pc-post-0355')
D=R/'repair'
base=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base')
assert not D.exists(), 'never prepare over an existing candidate'
expected=json.loads((R/'prep/GOLD_INPUTS.json').read_text())
for rel,want in expected.items():
    assert hashlib.sha256((S/rel).read_bytes()).hexdigest()==want, rel
(R/'.keep').touch()
env=os.environ.copy();env.update(OT_PRD_FROM='route',OT_PRD_TARGETED='1',OT_PRD_MAX_WIRE_LENGTH='80',OT_SETUP_MARGIN='10',OT_HOLD_ALLOW_SETUP='0',OT_PRD_HOOK=str(R/'prep/prd_hook_checkpoint.tcl'))
subprocess.run(['bash',str(R/'source/tools/die_plan/post_route_drv/prd_mk.sh'),str(S),str(D),'m10',str(R/'source'),str(S/base/'6_final.spef')],env=env,check=True)
shutil.copy2(R/'prep/prd_targeted.tcl',D/'prd_targeted.tcl')
# This reference is the CURRENT native routed input, never the earlier r27c seed.
shutil.copy2(S/base/'5_2_route.odb',D/'original_route.odb')
shutil.copy2(S/base/'clk_freeze_post.tsv',D/'ORIGINAL.clock.tsv')
for name in ('lec_async.sh','lec_completed_transfer.py'):
    shutil.copy2(R/'source/tools/die_plan'/name,D/name)
record=dict(status='PREPARED_NOT_DISPATCHED',source=str(S),source_hashes=expected,private_target='net41987 exact four endpoints/masters plus current normal DRV targets',source_RTL_changed=False,source_SDC_changed=False,clock_changed=False,phase='repair-only before DPL/GRT',genuine_CTS_sha256=hashlib.sha256((D/base/'4_1_cts.odb').read_bytes()).hexdigest(),variant_env=(D/'variant.env').read_text())
assert record['genuine_CTS_sha256']==expected[str(base/'4_1_cts.odb')]
(D/'PC_GEO80_PREPARED.json').write_text(json.dumps(record,indent=2)+'\n')
print(D)
