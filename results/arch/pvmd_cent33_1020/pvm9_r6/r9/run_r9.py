# HBM-PVM10 r9 (PVM9): r6c 3_place.odb (bf/work) -> COPY bf9<v>/work -> 4_1_cts..5_route + finish with ALL kernel
# dont_touch released pre-CTS (hooks/pvm9_release_all.tcl, never restored; equivalence replaces the native proof).
# v=a: kit CTS (main).  v=b: fallback, tighter sink clustering (size 16, diameter 30 um) so the 82 ps local skew inside
# the kernels drops.  Audits (r7a forms) at 5_1_grt and at 6_final; route proceeds when GRT passes (closure first).
import sys,subprocess,re,shutil
from pathlib import Path
v=sys.argv[1]
r=Path('/srv/opentallas-scratch/claude/pvm9-r6-1020');inv=r/'stage_inventory';A=r/'r7a'
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
orbin='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
D='opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate'
B=r/('bf9'+v)/'work';res='/work/results/asap7/%s/base/'%D;base=B/'results/asap7'/D/'base'
if not B.exists():
 B.parent.mkdir(exist_ok=True); subprocess.run(['cp','-a',str(r/'bf/work'),str(B)],check=True)
 for f in list(base.iterdir()):
  if re.match(r'(4_|5_|6_|pvm_cts_release|pvm8_)',f.name):f.unlink()
 shutil.copy(r/'r9'/'pvm9_release_all.tcl',B/'hooks'/'pvm9_release_all.tcl')
 add='\n# HBM-PVM10 r9%s: all kernel dont_touch released pre-CTS (r8 RSZ-3006 half-release)\nexport PRE_CTS_TCL = /work/hooks/pvm9_release_all.tcl\nexport POST_GLOBAL_ROUTE_TCL = /work/hooks/post_global_route_post_grt.tcl\n'%v
 if v=='b':add+='export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.75 -sink_clustering_levels 2 -sink_clustering_size 16 -sink_clustering_max_diameter 30 -distance_between_buffers 40 -no_obstruction_aware\n'
 with (B/'config.mk').open('a') as f:f.write(add)
env={'PVM_BF_EXPECTED':'/work/bindfirst_proof/expected.tcllist','PVM_BF_RECEIPTS':'/work/bindfirst_proof','PVM_BF_ORIGINAL_ODB':'/original/1_synth.odb','PVM_BF_PG_HELPER':'/src/physical/common_flow/native_pg_binding.tcl'}
def dock(e={}):
 b=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(B)+':/work','-v',str(base)+':/base','-v',str(A)+':/a']
 o=r/'orig/work/results/asap7'/D/'base/1_synth.odb'
 if o.exists():b+=['-v',str(o)+':/original/1_synth.odb:ro']
 for k,x in {**env,**e}.items():b+=['-e',k+'='+x]
 return b
def call(cmd,name,e={},entry=None):
 b=dock(e)+(['--entrypoint',entry] if entry else [])+['-w','/OpenROAD-flow-scripts/flow',img]+cmd
 with (inv/('r9%s_%s.log'%(v,name))).open('w') as f:rc=subprocess.run(b,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True);return rc
def mk(t):return call(['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 %s && chmod -R a+rwX /work'%t],t)
mac='/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_%s.lib'
def audit(st,sdc):
 o={'R7_ODB':'/base/%s.odb'%st}
 pg=call(['-exit','-no_init','/a/pg_audit2.tcl'],'pg_audit2_'+st,o,orbin)
 call(['-exit','-no_init','-python','/a/fanout_audit.py'],'fanout_'+st,{**o,'R7_OUT':'/work/%s_fanout.json'%st},orbin)
 call(['-exit','-no_init','-python','/a/sequential_reach.py'],'seqreach_'+st,{'AUDIT_ODB':'/base/%s.odb'%st,'AUDIT_OUT':'/work/%s_sequential_reach.json'%st},orbin)
 call(['-exit','-no_init','/a/sta_corner.tcl'],'sta_TT_'+st,{**o,'R7_CORNER':'TT','R7_MACRO_LIB':mac%'tt','R7_SDC':'/base/%s.sdc'%sdc},orbin)
 call(['-exit','-no_init','/a/sta_ff2.tcl'],'sta_ff2_'+st,{**o,'R7_MACRO_LIB':mac%'ff','R7_SDC':'/base/%s.sdc'%sdc},orbin)
 with (inv/('r9%s_ck_insertion_%s.log'%(v,st))).open('w') as f:subprocess.run(['python3',str(A/'ck_insertion.py'),'--base',str(base),'--clock','core_clk','--image',img,'--route-corner','TT','--output',str(B/('ck_insertion_%s.json'%st))],stdout=f,stderr=subprocess.STDOUT)
 m=re.search(r'R7_FF_HOLD from=reg violating_endpoints=(\d+) worst=(\S*)',(inv/('r9%s_sta_ff2_%s.log'%(v,st))).read_text())
 print('R9_AUDIT',v,st,'pg_rc',pg,'ff_reg_hold',m and m[2],'viol',m and m[1],flush=True)
def png(st):
 (B/('dump_%s.tcl'%st)).write_text('read_db %s%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\n'%(res,st))
 call(['-exit','-no_init','/work/dump_%s.tcl'%st],'dump_'+st,{'OT_LAYOUT_OUT':'/work/layout_%s.json'%st,'OT_LAYOUT_CLOCKS':'clk','OT_LAYOUT_TOP':'pvm9_r9%s_%s'%(v,st)},orbin)
 call(['python3','/src/tools/ref_tile/layout_png.py','/work/layout_%s.json'%st,'/work/png_%s'%st,'--title','PVM9 r9%s %s'%(v,st)],'png_'+st,{},'')
done=[]
for s in ['4_1_cts','4_cts','5_1_grt']:
 if mk('do-'+s):print('R9_STAGE_FAIL',v,s,flush=True);break
 done.append(s)
for st in [x for x in ['4_cts','5_1_grt'] if x in done]:png(st)
if '5_1_grt' in done:
 audit('5_1_grt','5_1_grt')
 for s in ['5_2_route','5_3_fillcell','5_route','5_route.sdc','finish']:
  if mk('do-'+s):print('R9_STAGE_FAIL',v,s,flush=True);break
  done.append(s)
 if 'finish' in done:
  png('6_final');audit('6_final','6_final')
  call(['bash','-lc','grep -h -i -E "violation|DRT-0199|Number of violations" /work/logs/asap7/%s/base/5_2_route.log | tail -5'%D],'drc_summary')
print('R9_DONE',v,done,flush=True)
