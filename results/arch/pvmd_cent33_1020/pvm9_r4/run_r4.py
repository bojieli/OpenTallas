# HBM-PVM9 r4: PVM9 source (per-lane valid/operand stage + lane reset leaves) from synthesis:
#  1 original (non-bind-first) synthesis -> reference 1_synth.odb
#  2 bind-first synthesis 1_2_yosys.v + actual native32 census (must PASS)
#  3 bind-first transaction (export expected from 1, PRE/POST_SYNTH protect at birth), persisted audit, fence dry run
#  4 stages floorplan..GRT with 16 lane fences (PRE_GLOBAL_PLACE), PNGs, kernel-input census, post-GRT PG + native32.
from pathlib import Path
import subprocess,json,hashlib,shutil,sys
r=Path('/srv/opentallas-scratch/claude/pvm9-r4-1020');inv=r/'stage_inventory';inv.mkdir(exist_ok=True)
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
orbin='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
D='opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate'
kit='/src/physical/ref_tile/pvm_bindfirst_private'
env={'PVM_BF_EXPECTED':'/work/bindfirst_proof/expected.tcllist','PVM_BF_RECEIPTS':'/work/bindfirst_proof',
     'PVM_BF_ORIGINAL_ODB':'/original/1_synth.odb','PVM_BF_PG_HELPER':'/src/physical/common_flow/native_pg_binding.tcl'}
def base(work,e={}):
 b=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(work)+':/work']
 if (r/'orig/work/results/asap7'/D/'base/1_synth.odb').exists():
  b+=['-v',str(r/'orig/work/results/asap7'/D/'base/1_synth.odb')+':/original/1_synth.odb:ro']
 for k,v in {**env,**e}.items():b+=['-e',k+'='+v]
 return b+['-w','/OpenROAD-flow-scripts/flow',img]
def call(work,cmd,name,fatal=True,e={}):
 with (inv/(name+'.log')).open('w') as f:rc=subprocess.run(base(work,e)+cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
 if rc and fatal:print('R4_STOP',name,flush=True);raise SystemExit(rc)
 return rc
def mk(work,target,name,cores=16,fatal=True):
 return call(work,['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=%d %s && chmod -R a+rwX /work'%(cores,target)],name,fatal)
O=r/'orig/work';B=r/'bf/work';res='/work/results/asap7/%s/base/'%D
libs=json.loads((r/'native_reference.json').read_text())['liberty']
def census(work,netlist,out,name,fatal):
 cmd=['python3','/src/tools/ref_tile/native_census.py','--netlist',netlist,'--top','ot_hbm_sm_pv_merge_distributed','--out',out]
 for l in libs:cmd+=['--liberty',l['path']]
 return call(work,cmd,name,fatal)
if not (O/'results/asap7'/D/'base/1_synth.odb').exists():mk(O,res+'1_synth.odb','orig_synth')
if not (B/'native_census.json').exists():
 shutil.copy(B/'config_synth.mk',B/'config.mk')
 mk(B,res+'1_2_yosys.v','bf_synth')
 census(B,res+'1_2_yosys.v','/work/native_census.json','bf_native32',True)
d=json.loads((B/'native_census.json').read_text());print('NATIVE32',{k:d.get(k) for k in ['status','roots_examined','max_dynamic_loads','role_errors']},flush=True)
print('MAPPED_SHA256',hashlib.sha256((B/('results/asap7/%s/base/1_2_yosys.v'%D)).read_bytes()).hexdigest(),flush=True)
if d.get('status')!='PASS':print('R4_STOP native32',flush=True);raise SystemExit(3)
shutil.copy(B/'config_full.mk',B/'config.mk')
if not (B/'bindfirst_proof/expected.tcllist').exists():
 (B/'bindfirst_proof').mkdir(exist_ok=True)
 call(B,[orbin,'-exit',kit+'/export_expected.tcl'],'bf_export_expected')
if not (B/'results/asap7'/D/'base/1_synth.odb').exists():
 mk(B,res+'1_synth.odb','bf_transaction',4)
 call(B,[orbin,'-exit',kit+'/audit_persisted.tcl'],'bf_audit_persisted',True,{'PVM_BF_AUDIT_ODB':res+'1_synth.odb','PVM_BF_AUDIT_STAGE':'persisted_1_synth'})
(B/'fence_dry.tcl').write_text('read_db %s1_synth.odb\nsource %s/stages/pvm9_lane_fences.tcl\n'%(res,kit))
call(B,[orbin,'-exit','-no_init','/work/fence_dry.tcl'],'fence_dry_run')
for s in ['2_1_floorplan','2_2_floorplan_macro','2_3_floorplan_tapcell']:mk(B,'do-'+s,s,4)
call(B,['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -python /work/tap_pg_census_r3.py'],'post_tapcell_pg_census',False)
for s in ['2_4_floorplan_pdn','2_floorplan','2_floorplan.sdc','3_1_place_gp_skip_io','3_2_place_iop']:mk(B,'do-'+s,s,4 if s<'3' else 16)
call(B,['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -python /work/kernel_input_nets.py'],'kernel_input_nets',False)
stages=['3_3_place_gp','3_4_place_resized','3_5_place_dp','3_place','4_1_cts','4_cts','5_1_grt']
done=[]
for s in stages:
 if mk(B,'do-'+s,s,16,False):print('R4_STAGE_FAIL',s,flush=True);break
 done.append(s)
for st in [x for x in ['3_place','4_cts','5_1_grt'] if x in done]:
 (B/('dump_%s.tcl'%st)).write_text('read_db %s%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\n'%(res,st))
 call(B,[orbin,'-exit','-no_init','/work/dump_%s.tcl'%st],'dump_'+st,False,{'OT_LAYOUT_OUT':'/work/layout_%s.json'%st,'OT_LAYOUT_CLOCKS':'clk','OT_LAYOUT_TOP':'pvm9_r4_'+st})
 call(B,['python3','/src/tools/ref_tile/layout_png.py','/work/layout_%s.json'%st,'/work/png_%s'%st,'--title','PVM9 r4 '+st],'png_'+st,False)
if '5_1_grt' in done:
 (B/'post_grt_audit.tcl').write_text('read_db %s5_1_grt.odb\nwrite_verilog /work/5_1_grt.v\nset pvm_bf_stage post_grt_audit\nsource /src/physical/common_flow/native_pg_binding.tcl\nset b [ord::get_db_block]\not_pg_assert_all_native $b [ot_pg_prepare $b]\nputs PVM_R4_POST_GRT_PG_ALL_BOUND\n'%res)
 call(B,[orbin,'-exit','-no_init','/work/post_grt_audit.tcl'],'post_grt_audit',False)
 census(B,'/work/5_1_grt.v','/work/post_grt_native_census.json','post_grt_native32',False)
print('R4_DONE',done,flush=True)
