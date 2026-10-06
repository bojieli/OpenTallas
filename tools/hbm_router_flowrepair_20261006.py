#!/usr/bin/env python3
"""One native GPL flow repair: retain mapping/I/O/checkpoints, never replay synthesis."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
import hbm_router_pipeline_route_20261006 as base
ROOT=Path(__file__).resolve().parents[1]
SUB=Path('results/asap7/carson_router_pipeline_r1/base')
RECORD=Path('results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1/route-r1_FAIL_RETAINED')
MAKE=['make','DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work','FLOW_VARIANT=base','NUM_CORES=16','GPL_TIMING_DRIVEN=0','-o','/work/'+str(SUB/'3_2_place_iop.odb'),'-o','/work/'+str(SUB/'2_floorplan.sdc'),'finish','metadata-generate']
def docker(work,command,name=None):
 cmd=['docker','run']+(['--name',name,'--cpus','16'] if name else ['--rm','--cpus','1'])
 return cmd+['-e','OMP_NUM_THREADS=16','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',base.IMAGE,'bash','-lc',command]
def prepare(retained,out):
 if out.exists():raise ValueError('new output root required; preserve prior attempts')
 r=json.loads((retained/'route.json').read_text());assert r['status']=='FAIL_RETAINED' and r['flow_returncode']==2
 for p,h in r['source_sha256'].items():assert base.sha(ROOT/p)==h,p
 pins=json.loads((ROOT/RECORD/'retained_checkpoints.json').read_text())
 old=retained/'orfs';checkpoint=old/SUB/'3_2_place_iop.odb'
 assert base.sha(checkpoint)==pins[checkpoint.name]['sha256']
 assert base.sha(old/'constraint.sdc')==r['sdc_sha256'];assert base.sha(old/'config.mk')==r['config_sha256']
 out.mkdir();work=out/'orfs';work.mkdir()
 # Independent copies; later ORFS writes cannot mutate retained original files.
 shutil.copytree(old/'results',work/'results',copy_function=shutil.copy2)
 for n in ['constraint.sdc','config.mk','attribute_preservation.json']:shutil.copy2(old/n,work/n)
 for p in (work/SUB).glob('*'):
  if p.is_file() and p.name in pins:assert base.sha(p)==pins[p.name]['sha256'],p
 record=dict(status='PREPARED_ONE_NATIVE_GPL_FLOW_REPAIR',repair_number=1,escalate_after_two_flow_repair_failures=True,source_sha256=r['source_sha256'],retained_original_root=str(retained),checkpoint_sha256=pins['3_2_place_iop.odb']['sha256'],mapped_verilog_sha256=pins['1_2_yosys.v']['sha256'],sdc_sha256=r['sdc_sha256'],config_sha256=r['config_sha256'],image=base.IMAGE,workers=16,declared_ram_gib=64,changed_flow_variable={'GPL_TIMING_DRIVEN':0},RTL_changed=False,synthesis_replayed=False,golden_replayed=False,clock_or_uncertainty_relaxed=False,frame_changed=False,later_resize_CTS_GRT_timing_repair_disabled=False,parent_qualified=False,physical_closed=False,make_command=MAKE,cloned_checkpoint_sha256=pins)
 base.save(out/'preparation.json',record)
 validate_prepared(out)
def validate_prepared(out):
 work=out/'orfs';record=json.loads((out/'preparation.json').read_text())
 for n in ['3_2_place_iop.odb','1_2_yosys.v','2_floorplan.sdc']:assert base.sha(work/SUB/n)==record['cloned_checkpoint_sha256'][n]['sha256']
 # ORFS creates extra SDC side effects at runtime: a finish-wide dry-run cannot
 # materialize these. Check installed native phony stages without executing them.
 plan_args=MAKE[:6]+['-n','do-3_3_place_gp','do-3_4_place_resized','do-3_5_place_dp','do-4_1_cts','do-5_1_grt']
 shell='cd /OpenROAD-flow-scripts/flow && '+' '.join(plan_args)
 log=out/'native_make_plan.log'
 if log.exists():shutil.copy2(log,out/'native_make_plan_initial_unmaterialized_sdc_FAIL.log')
 with log.open('w') as f:rc=subprocess.call(docker(work,shell),stdout=f,stderr=subprocess.STDOUT)
 plan=log.read_text();assert rc==0,plan[-3000:]
 assert not re.search(r'flow\.sh\s+(?:1_|2_|3_1_|3_2_)',plan),'native graph would replay an earlier stage'
 for name in ['3_3_place_gp global_place','3_4_place_resized resize','4_1_cts cts','5_1_grt global_route']:assert 'flow.sh '+name in plan,name
 record['native_make_plan_sha256']=base.sha(log);record['native_make_plan_verified_no_synth_or_IO_replay']=True
 record['dry_run_scope']='Installed native do-stage recipes; finish dependencies frozen at copied3_2IOP+2floorplanSDC; missing future SDC side effects require actual sequential run'
 base.save(out/'preparation.json',record);print(json.dumps(record),flush=True)
def run(out,admitted):
 if not Path('/srv/opentallas-scratch/admit.sh').is_file():raise ValueError('remote unchanged guard required')
 if (out/'continuation.json').exists():raise ValueError('immutable continuation record exists')
 r=json.loads((out/'preparation.json').read_text());assert r['native_make_plan_verified_no_synth_or_IO_replay']
 for p,h in r['source_sha256'].items():assert base.sha(ROOT/p)==h
 work=out/'orfs'
 for n in ['3_2_place_iop.odb','1_2_yosys.v','2_floorplan.sdc']:assert base.sha(work/SUB/n)==r['cloned_checkpoint_sha256'][n]['sha256']
 assert base.sha(work/'constraint.sdc')==r['sdc_sha256'];assert base.sha(work/'config.mk')==r['config_sha256']
 if not base.capacity(out,'post_guard' if admitted else 'pre_guard')['fits']:return 75
 if not admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','64','--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 shell='python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && cd /OpenROAD-flow-scripts/flow && '+' '.join(MAKE)
 cmd=docker(work,shell,'carson-router-pipeline-flowrepair-r2');r.update(status='RUNNING_ONE_NATIVE_GPL_FLOW_REPAIR',command=cmd)
 base.save(out/'continuation.json',r)
 with (out/'continuation.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 r.update(flow_returncode=rc,status='FLOW_REPAIR_TERMINAL_FAIL_RETAINED' if rc else 'FLOW_REPAIR_ROUTE_TERMINAL',post_capacity=base.capacity(out,'terminal'),log_sha256=base.sha(out/'continuation.log'))
 if not rc:r['corners']=base.corners(out,work)
 base.save(out/'continuation.json',r);return rc
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--retained',type=Path);ap.add_argument('--prepare',action='store_true');ap.add_argument('--admitted',action='store_true');ap.add_argument('--validate-prepared',action='store_true');a=ap.parse_args()
 if a.validate_prepared:validate_prepared(a.out.resolve())
 elif a.prepare:
  if not a.retained:ap.error('--retained required for preparation')
  prepare(a.retained.resolve(),a.out.resolve())
 else:sys.exit(run(a.out.resolve(),a.admitted))
