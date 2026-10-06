#!/usr/bin/env python3
"""Single source-bound router route, dispatched only by fleet coordinator."""
import argparse,hashlib,importlib.util,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=Path('physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1')
R=Path('results/physical/hbm_die_abstracts_20261006/compute/router_pipeline_r1')
IMAGE='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def capacity(out,phase):
 def sample():
  v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]));return sum(v[:8]),v[3]+v[4]
 t,i=sample();time.sleep(.5);tt,ii=sample();n=os.cpu_count();idle=(ii-i)/(tt-t)*n
 v=dict(phase=phase,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),load=os.getloadavg()[0],idle_cpus=idle,cpus=n,disk_free_bytes=os.statvfs(out).f_bavail*os.statvfs(out).f_frsize)
 v['fits']=idle>=16 and v['load']<n and v['disk_free_bytes']>=32*1024**3
 with (out/'capacity.jsonl').open('a') as f:f.write(json.dumps(v)+'\n')
 return v
BOOTSTRAP=r'''import hashlib,json,re
from pathlib import Path
base=Path('/OpenROAD-flow-scripts/flow/scripts');records=[]
for p in sorted(base.rglob('*')):
 if p.suffix not in ('.tcl','.ys'):continue
 text=p.read_text()
 # Preserve attributes in every intermediate synthesis Verilog in THIS container.
 updated=re.sub(r'(?<!\S)-noattr(?=\s|$)','',text)
 if updated!=text:
  records.append(dict(path=str(p),before_sha256=hashlib.sha256(text.encode()).hexdigest(),after_sha256=hashlib.sha256(updated.encode()).hexdigest(),removed_noattr=text.count('-noattr')-updated.count('-noattr')))
  p.write_text(updated)
Path('/work/attribute_preservation.json').write_text(json.dumps(records,indent=2)+'\n')
'''
def corners(out,work):
 spec=importlib.util.spec_from_file_location('router_corner_base',ROOT/'tools/w18/corner_sta.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 base=next((work/'results/asap7').glob('*/base'));rel='/work/'+str(base.relative_to(work));receipt={}
 for corner,kind in [('ss','max'),('ff','min')]:
  tcl=m.script(corner,rel,[]).replace('get_pins -hierarchical */D','all_registers -data_pins')
  extra=f'\nreport_checks -path_delay {kind} -from [get_ports rst_n] -to [get_pins -hierarchical */RESETN] -group_path_count 10 -format full_clock_expanded\nreport_check_types -max_slew -max_capacitance -max_fanout -violators\n'
  tcl=tcl.replace('\nexit\n',extra+'\nexit\n');(work/('router_'+corner+'.tcl')).write_text(tcl)
  cmd=['docker','run','--rm','--cpus','1','-v',str(work)+':/work',IMAGE,'bash','-lc','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/router_'+corner+'.tcl']
  with (out/('corner_'+corner+'.log')).open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
  log=(out/('corner_'+corner+'.log')).read_text();values={k:v for k,v in re.findall(r'^(OT_\w+) (\S+)',log,re.M)}
  receipt[corner]=dict(returncode=rc,metrics_raw=values,errors=re.findall(r'\[ERROR[^\n]*',log),log_sha256=sha(out/('corner_'+corner+'.log')),tcl_sha256=sha(work/('router_'+corner+'.tcl')))
 receipt['retained_sha256']={n:sha(base/n) for n in ['6_final.odb','6_final.spef','6_final.sdc']};receipt['parent_qualified']=False
 save(out/'corner_sta.json',receipt)
 return receipt
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admitted',action='store_true');a=ap.parse_args()
 if not Path('/srv/opentallas-scratch/admit.sh').is_file():ap.error('remote guard host required')
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if (out/'route.json').exists() or (out/'orfs').exists():ap.error('retained attempt exists; no replay/overwrite')
 gate=json.loads((ROOT/R/'gate-r1/gate.json').read_text());assert gate['passed'] and len(gate['runs'])==3
 for p,h in gate['source_sha256'].items():assert sha(ROOT/p)==h,p
 assert sha(ROOT/R/'before_rtl.json')==gate['model_sha256']
 assert sha(ROOT/P/'constraint.sdc')=='d817d08188fd7c345102875cdfcc2efc4019d750498d238fbf918f88e132894f'
 if not capacity(out,'post_guard' if a.admitted else 'pre_guard')['fits']:return 75
 if not a.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh','64','--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 work=out/'orfs';work.mkdir();(work/'constraint.sdc').write_bytes((ROOT/P/'constraint.sdc').read_bytes())
 files=[str(P/'pinned/ot_gpu_router_topk.sv'),str(P/'pinned/ot_gpu_router_topk_f.sv'),str(P/'ot_hbm_router_topk_pipeline.sv')]
 cfg='\n'.join(['export DESIGN_NICKNAME = carson_router_pipeline_r1','export DESIGN_NAME = ot_hbm_router_topk_pipeline','export PLATFORM = asap7','export VERILOG_FILES = '+' '.join('/src/'+p for p in files),'export VERILOG_TOP_PARAMS = ENABLE 1','export VERILOG_DEFINES = -DSYNTHESIS','export SDC_FILE = /work/constraint.sdc',
 'export DIE_AREA = 0 0 293.431 293.431','export CORE_AREA = 2.052 2.160 291.384 291.330','export PLACE_DENSITY = 0.60','export PLACE_DENSITY_LB_ADDON = 0.05','export SYNTH_REPEATABLE_BUILD = 1','export SYNTH_HIERARCHICAL = 0','export SYNTH_MEMORY_MAX_BITS = 65536','export LEC_CHECK = 0','export TNS_END_PERCENT = 100','export REPORT_CLOCK_SKEW = 1','export CORNER = WC','export ADDER_MAP_FILE =','export ASAP7_USE_VT = RVT','export SLEW_MARGIN = 30','export HOLD_SLACK_MARGIN = 10','export CORNERS = WC BC','export WC_LIB_FILES = $(WC_NLDM_LIB_FILES)','export BC_LIB_FILES = $(BC_NLDM_LIB_FILES)'])+'\n'
 (work/'config.mk').write_text(cfg);(work/'preserve_attributes.py').write_text(BOOTSTRAP)
 record=dict(status='STARTED_ONE_CHANGED_ROUTE',source_sha256={p:sha(ROOT/p) for p in files},gate_sha256=sha(ROOT/R/'gate-r1/gate.json'),sdc_sha256=sha(work/'constraint.sdc'),config_sha256=sha(work/'config.mk'),image=IMAGE,workers=16,declared_ram_gib=64,ram_basis='retained16CPU DRT28046084KiB times modeled1.70 cellgrowth =45.5GiB plus reserve; capacity reservation not process cap',parent_qualified=False,physical_closed=False,retained_core_from_DEF_rows=[2.052,2.160,291.384,291.330],target_cell_utilization_range=[.55,.60])
 save(out/'route.json',record)
 shell='python3 /work/preserve_attributes.py && python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && cd /OpenROAD-flow-scripts/flow && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 finish metadata-generate'
 cmd=['docker','run','--name','carson-router-pipeline-r1','--cpus','16','-e','OMP_NUM_THREADS=16','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work',IMAGE,'bash','-lc',shell]
 record['command']=cmd;save(out/'route.json',record)
 with (out/'route.log').open('w') as f:rc=subprocess.call(cmd,stdout=f,stderr=subprocess.STDOUT)
 record['flow_returncode']=rc;record['status']='ROUTE_TERMINAL_NEEDS_ACTUAL_CORNER_COLLECTION' if rc==0 else 'FAIL_RETAINED';record['post_capacity']=capacity(out,'terminal')
 record['route_log_sha256']=sha(out/'route.log')
 if rc==0:
  record['corners']=corners(out,work)
  record['status']='ACTUAL_ROUTE_AND_CORNERS_TERMINAL_REVIEW_UTIL_DRC_RESET_REQUIRED'
 save(out/'route.json',record)
 # No clock/reset exception and no closure inferred from a successful make.
 return rc
if __name__=='__main__':sys.exit(main())
