# HBM-SMATT6 r3: r2 bounded stages + canonical post-tapcell global_connect, then PDN/GPL/CTS/GRT.
from pathlib import Path
import subprocess,json,hashlib,os
r=Path('/srv/opentallas-scratch/claude/smatt6-pvm-r3-1020');w=r/'work';out=r/'stage_inventory';out.mkdir(exist_ok=True)
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
D='opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate'
base=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow',img]
res=w/'results/asap7'/D/'base'
def call(cmd,name,fatal=True):
 with (out/(name+'.log')).open('w') as f:rc=subprocess.run(base+cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True)
 if rc and fatal:raise SystemExit(rc)
 return rc
def mk(step,cores=16):
 call(['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=%d do-%s'%(cores,step)],step)
def orpy(script,name):
 call(['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -python /work/'+script],name,fatal=False)
def ortcl(script,name,env={}):
 e=[];[e.extend(['-e','%s=%s'%kv]) for kv in env.items()]
 with (out/(name+'.log')).open('w') as f:rc=subprocess.run(base[:3]+e+base[3:]+['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_init /work/'+script],stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True);return rc
mk('2_3_floorplan_tapcell',4)
orpy('tap_pg_census_r3.py','post_tapcell_pg_census')
mk('2_4_floorplan_pdn',4)
mk('2_floorplan');mk('2_floorplan.sdc')
for s in ['3_1_place_gp_skip_io','3_2_place_iop','3_3_place_gp','3_4_place_resized','3_5_place_dp','3_place','4_1_cts','4_cts','5_1_grt']:mk(s)
for st in ['3_place','4_cts','5_1_grt']:
 (w/('dump_%s.tcl'%st)).write_text('read_db /work/results/asap7/%s/base/%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\n'%(D,st))
 ortcl('dump_%s.tcl'%st,'dump_'+st,{'OT_LAYOUT_OUT':'/work/layout_%s.json'%st,'OT_LAYOUT_CLOCKS':'clk','OT_LAYOUT_TOP':'pvm_r3_'+st})
 call(['python3','/src/tools/ref_tile/layout_png.py','/work/layout_%s.json'%st,'/work/png_%s'%st,'--title','PVM r3 '+st],'png_'+st,fatal=False)
(w/'post_grt_audit.tcl').write_text('read_db /work/results/asap7/%s/base/5_1_grt.odb\nwrite_verilog /work/5_1_grt.v\nset pvm_bf_stage post_grt_audit\nsource /src/physical/common_flow/native_pg_binding.tcl\nset b [ord::get_db_block]\not_pg_assert_all_native $b [ot_pg_prepare $b]\nputs PVM_R3_POST_GRT_PG_ALL_BOUND\n'%D)
ortcl('post_grt_audit.tcl','post_grt_audit')
libs=json.loads((r/'native_reference.json').read_text())['liberty']
cmd=['python3','/src/tools/ref_tile/native_census.py','--netlist','/work/5_1_grt.v','--top','ot_hbm_sm_pv_merge_distributed','--out','/work/post_grt_native_census.json']
for l in libs:cmd+=['--liberty',l['path']]
call(cmd,'post_grt_native32',fatal=False)
print('R3_DONE',flush=True)
