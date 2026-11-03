from pathlib import Path
import hashlib,json,os,shutil,subprocess
R=Path('/srv/opentallas-scratch2/claude/codex-pc-geo80-1102')
S=Path('/srv/opentallas-scratch2/claude/codex-pc-post-0355')
D=R/'repair'
seed=R/'seed'
base=Path('run/results/asap7/hc_qkd_kvs_pc__397_44x362_88/base')
assert not D.exists(), 'never prepare over an existing candidate'
expected=json.loads((R/'prep/GOLD_INPUTS.json').read_text())
for rel,want in expected.items():
    assert hashlib.sha256((S/rel).read_bytes()).hexdigest()==want, rel
(R/'.keep').touch()
assert not seed.exists()
# Remove only completed private stage hooks from an OWN copy; never replay the
# old reload_pre, which would import the earlier repair checkpoint as new gold.
def ignore(root,names):
    skip={'run','views','signoff','lec','lec_post','lec_own_final','original_post_failure'}
    return [n for n in names if n in skip or n.endswith(('.log','.odb','.def','.spef')) or (n.startswith('lec_async.') and n!='lec_async.sh')]
shutil.copytree(S,seed,ignore=ignore)
(seed/base).mkdir(parents=True)
for name in ('5_2_route.odb','6_final.spef','4_1_cts.odb','1_2_yosys.v'):
    shutil.copy2(S/base/name,seed/base/name)
for name in ('4_cts.sdc','clock_period.txt','mem.json','ot_face_flops.txt','ot_unreg_pins.txt'):
    if (S/base/name).is_file():shutil.copy2(S/base/name,seed/base/name)
if (S/'run/objects').exists():shutil.copytree(S/'run/objects',seed/'run/objects')
old=(seed/'config.mk').read_text()
remove=['override export PRE_GLOBAL_ROUTE_TCL = /work/reload_pre.tcl','override export POST_GLOBAL_ROUTE_TCL = /work/reload_post.tcl','override export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl']
for line in remove:
    assert old.splitlines().count(line)==1,line
new='\n'.join(x for x in old.splitlines() if x not in remove)+'\n'
(seed/'config.mk').write_text(new)
(seed/'COMPLETED_PRIVATE_HOOKS_REMOVED.json').write_text(json.dumps(dict(source=str(S),removed=remove,source_configuration_sha256=expected['config.mk'],source_SDC_unchanged=True),indent=2)+'\n')
env=os.environ.copy();env.update(OT_PRD_FROM='route',OT_PRD_TARGETED='1',OT_PRD_MAX_WIRE_LENGTH='80',OT_SETUP_MARGIN='10',OT_HOLD_ALLOW_SETUP='0',OT_PRD_HOOK=str(R/'prep/prd_hook_checkpoint.tcl'))
subprocess.run(['bash',str(R/'source/tools/die_plan/post_route_drv/prd_mk.sh'),str(seed),str(D),'m10',str(R/'source'),str(S/base/'6_final.spef')],env=env,check=True)
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
