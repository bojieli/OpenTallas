# HBM-SMATT9 r8 (PVM9): r6c 3_place.odb -> 4_1_cts/4_cts/5_1_grt in a COPY (bf8/work; r6c verdicts preserved) with the
# kernel hold fix (hooks/pvm8_release.tcl + pvm8_restore.tcl), then the fixed post-GRT audits (r7a forms), then
# 5_2_route + 5_3_fillcell only if PG binds after global_connect and FF reg->reg hold >= -5 ps at GRT.
from pathlib import Path
import subprocess,json,re,shutil
r=Path('/srv/opentallas-scratch/claude/pvm9-r6-1020');inv=r/'stage_inventory';A=r/'r7a'
img='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
orbin='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
D='opentallas_ot_hbm_sm_pv_merge_distributed_asap7_ref_gate'
B=r/'bf8/work';res='/work/results/asap7/%s/base/'%D;base=B/'results/asap7'/D/'base'
if not B.exists():
 B.parent.mkdir(exist_ok=True); subprocess.run(['cp','-a',str(r/'bf/work'),str(B)],check=True)
 for s in ('4_1_cts','4_cts','5_1_grt','5_1_grt.grt183_resume','5_1_grt-failed'):
  for f in base.glob(s+'.*'):f.unlink()
 for h in ('pvm8_release.tcl','pvm8_restore.tcl','pvm8_post_grt.tcl'):shutil.copy(r/'r8'/h,B/'hooks'/h)
 with (B/'config.mk').open('a') as f:f.write('\n# HBM-SMATT9 r8 kernel hold fix\nexport PRE_CTS_TCL = /work/hooks/pvm8_release.tcl\nexport POST_GLOBAL_ROUTE_TCL = /work/hooks/pvm8_post_grt.tcl\n')
env={'PVM_BF_EXPECTED':'/work/bindfirst_proof/expected.tcllist','PVM_BF_RECEIPTS':'/work/bindfirst_proof','PVM_BF_ORIGINAL_ODB':'/original/1_synth.odb','PVM_BF_PG_HELPER':'/src/physical/common_flow/native_pg_binding.tcl'}
def dock(e={}):
 b=['docker','run','--rm','-v',str(r/'src')+':/src:ro','-v',str(B)+':/work','-v',str(base)+':/base','-v',str(A)+':/a']
 if (r/'orig/work/results/asap7'/D/'base/1_synth.odb').exists():b+=['-v',str(r/'orig/work/results/asap7'/D/'base/1_synth.odb')+':/original/1_synth.odb:ro']
 for k,v in {**env,**e}.items():b+=['-e',k+'='+v]
 return b
def call(cmd,name,e={},entry=None):
 b=dock(e)+(['--entrypoint',entry] if entry else [])+['-w','/OpenROAD-flow-scripts/flow',img]+cmd
 with (inv/('r8_'+name+'.log')).open('w') as f:rc=subprocess.run(b,stdout=f,stderr=subprocess.STDOUT).returncode
 print(name,rc,flush=True);return rc
def mk(t):return call(['bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 %s && chmod -R a+rwX /work'%t],t)
done=[]
for s in ['4_1_cts','4_cts','5_1_grt']:
 if mk('do-'+s):print('R8_STAGE_FAIL',s,flush=True);break
 done.append(s)
for st in [x for x in ['4_cts','5_1_grt'] if x in done]:
 (B/('dump_%s.tcl'%st)).write_text('read_db %s%s.odb\nsource /src/tools/ref_tile/layout_dump.tcl\n'%(res,st))
 call(['-exit','-no_init','/work/dump_%s.tcl'%st],'dump_'+st,{'OT_LAYOUT_OUT':'/work/layout_%s.json'%st,'OT_LAYOUT_CLOCKS':'clk','OT_LAYOUT_TOP':'pvm9_r8_'+st},orbin)
 call(['python3','/src/tools/ref_tile/layout_png.py','/work/layout_%s.json'%st,'/work/png_%s'%st,'--title','PVM9 r8 '+st],'png_'+st,{},'')
ok=False
if '5_1_grt' in done:
 o={'R7_ODB':'/base/5_1_grt.odb'}
 pg=call(['-exit','-no_init','/a/pg_audit2.tcl'],'pg_audit2',o,orbin)
 call(['-exit','-no_init','-python','/a/fanout_audit.py'],'fanout',{**o,'R7_OUT':'/work/post_grt_fanout.json'},orbin)
 call(['-exit','-no_init','-python','/a/sequential_reach.py'],'seqreach',{'AUDIT_ODB':'/base/5_1_grt.odb','AUDIT_OUT':'/work/post_grt_sequential_reach.json'},orbin)
 mac='/src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2_p192_mir/ot_sram_1r1w_64x512_m1_r2c2_p192_mir_%s.lib'
 call(['-exit','-no_init','/a/sta_corner.tcl'],'sta_TT',{**o,'R7_CORNER':'TT','R7_MACRO_LIB':mac%'tt','R7_SDC':'/base/5_1_grt.sdc'},orbin)
 call(['-exit','-no_init','/a/sta_ff2.tcl'],'sta_ff2',{**o,'R7_MACRO_LIB':mac%'ff','R7_SDC':'/base/5_1_grt.sdc'},orbin)
 with (inv/'r8_ck_insertion.log').open('w') as f:subprocess.run(['python3',str(A/'ck_insertion.py'),'--base',str(base),'--clock','core_clk','--image',img,'--route-corner','TT','--output',str(B/'ck_insertion.json')],stdout=f,stderr=subprocess.STDOUT)
 m=re.search(r'R7_FF_HOLD from=reg violating_endpoints=(\d+) worst=(\S*)',(inv/'r8_sta_ff2.log').read_text())
 hold=float(m[2]) if m and m[2] else 0.0
 print('R8_GRT_SUMMARY pg_rc',pg,'ff_reg_hold',hold,m and m[1],flush=True)
 ok=(pg==0 and hold>=-5)
if ok:
 for s in ['5_2_route','5_3_fillcell']:
  if mk('do-'+s):print('R8_STAGE_FAIL',s,flush=True);break
  done.append(s)
print('R8_DONE',done,flush=True)
