#!/usr/bin/env python3
"""One W6 metadata retention element, loaded two-fF ports, SS60/FF25.

This physical probe prices the real codec/FFs/repair feedback, not a parent
allocation or the SM's full ownership/control path. Never claim full adoption.
Run on admitted E2; source and dependency hashes are retained in every result.
"""
import argparse,os,json,time,subprocess,shutil,hashlib,importlib.util,re
from pathlib import Path
IMAGE='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
HERE=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--resume-yosys',type=Path);a=p.parse_args()
 w=a.work.resolve();src=a.source.resolve();w.mkdir(parents=True,exist_ok=False)
 cfg=HERE/'results/uarch/hbm_simt_gu_coded_20261005/probe'
 for name in ['config.mk','constraint.sdc','pins.tcl']:shutil.copy2(cfg/name,w/name)
 if a.resume_yosys:
  old=a.resume_yosys.resolve()
  assert json.loads((old/'flow_exit.json').read_text())['rc']!=0
  oldpins=json.loads((old/'source_binding.json').read_text())['source_sha256']
  for f,h in oldpins.items():assert sha(src/f)==h,f
  base=next((old/'results/asap7').glob('*/base'))
  assert (base/'1_2_yosys.v').is_file() and not (base/'1_synth.odb').exists()
  for sub in ['results','objects']:shutil.copytree(old/sub,w/sub)
  (w/'resumed_yosys.json').write_text(json.dumps(dict(previous=str(old),
   retained_netlist_sha256=sha(base/'1_2_yosys.v'),source_byte_identical=True,
   failure='Missing WC_LIB_FILES/BC_LIB_FILES aliases; add actual SS/FF lists, no synthesis replay'),indent=2)+'\n')
 sysroot='/srv/opentallas-scratch'
 import sys;sys.path.insert(0,sysroot);import admit_core
 def guard(stage):
  while True:
   load=os.getloadavg();avail=admit_core._avail();free=shutil.disk_usage(w).free
   # Approved whole-SM24GiB guard reused conservatively for216FF codec probe.
   # Measured tile output inventory4GiB is larger than this mechanism; reserve
   # two such inventories. This is admission, never a process/file/time limit.
   if load[0]<128 and free>8*2**30 and admit_core.try_admit(24*2**30):break
   time.sleep(10)
  (w/(stage+'_admission.json')).write_text(json.dumps(dict(load=load,MemAvailable=avail,disk_free=free,
   reservation_GiB=24,cores=8,execution_caps=None,utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())),indent=2)+'\n')
 model=HERE/'results/uarch/hbm_simt_gu_coded_20261005/parallel_repair_before_edit.json'
 if not model.is_file():model=HERE/'results/uarch/hbm_simt_gu_coded_20261005/physical_probe_prebuild.json'
 files=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/collective/ot_hbm_accel_gu_metadata.sv','tools/w18/corner_sta.py']
 (w/'source_binding.json').write_text(json.dumps(dict(source_sha256={f:sha(src/f) for f in files},image=IMAGE,
  driver_sha256=sha(__file__),model_path=str(model.relative_to(HERE)),model_sha256=sha(model),
  scope='192data/216coded state; real encoder/decoder CE feedback, loaded2fF isolated element; parent control/lease/slot unqualified',
  clock_ps=833,SS_setup_ps=60,FF_hold_ps=25,normal_added_cut_edges=0,CE_scrub_minimum_edges=1,
  additional_payload_bits=0),indent=2)+'\n')
 def docker(command):
  return ['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(w)+':/work','-w','/OpenROAD-flow-scripts/flow',IMAGE,'bash','-lc',command]
 guard('flow');(w/'status').write_text('LIVE_MINIMUM_CODED_ELEMENT_FLOW\n')
 targets='finish'
 if a.resume_yosys:
  targets='do-1_synth do-floorplan do-place do-cts do-route do-finish'
 cmd=docker('source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 '+targets)
 (w/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with (w/'flow.log').open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 subprocess.run(docker('chmod -R a+rwX /work'),check=True)
 (w/'flow_exit.json').write_text(json.dumps(dict(rc=rc))+'\n')
 if rc:(w/'status').write_text('FAIL_FLOW_RC='+str(rc)+'\n');return rc
 base=next((w/'results/asap7').glob('*/base'))
 for name in ['6_final.odb','6_final.spef','6_final.sdc']:assert (base/name).is_file()
 S=(base/'6_final.sdc').read_text()
 assert re.search(r'create_clock[^\n]*-period\s+833',S) and re.search(r'set_clock_uncertainty\s+-setup\s+60',S) and re.search(r'set_clock_uncertainty\s+-hold\s+25',S)
 spec=importlib.util.spec_from_file_location('corner',src/'tools/w18/corner_sta.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 rec=dict(scope='Isolated loaded real W6 metadata retention; full selected SM/parent unqualified',corners={},adopted=False,parent_context_closed=False,
  final_sha256={n:sha(base/n) for n in ['6_final.odb','6_final.spef','6_final.sdc']})
 for corner in ['ss','ff']:
  guard(corner);tcl=w/('sta_'+corner+'.tcl')
  tcl.write_text(C.script(corner,'/work/'+str(base.relative_to(w)),[]).replace('-group_path_count 1 -format full_clock_expanded','-group_path_count 10 -format full_clock_expanded'))
  r=subprocess.run(docker('/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/'+tcl.name),text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (w/('sta_'+corner+'.log')).write_text(r.stdout)
  assert r.returncode==0 and '[ERROR' not in r.stdout,corner
  def field(k):
   m=re.search(r'^'+k+r' (\S+)',r.stdout,re.M);assert m is not None,k;return m[1]
  rec['corners'][corner]=dict(check='setup' if corner=='ss' else 'hold',worst_slack_ps=float(field('OT_WS'))*1e12,TNS_ps=float(field('OT_TNS'))*1e12,
    violating_D_pins=int(field('OT_VIOL_D_PINS')),worst_reg_D_ps=field('OT_WS_REG_D'),worst_output_ps=field('OT_WS_OUT'),worst_R2R_ps=field('OT_WS_R2R'),worst_I2R_ps=field('OT_WS_I2R'))
 rec['isolated_SSFF_pass']=all(c['worst_slack_ps']>=0 for c in rec['corners'].values())
 (w/'corner_sta.json').write_text(json.dumps(rec,indent=2)+'\n')
 (w/'status').write_text('TERMINAL_ISOLATED_SSFF_'+('PASS' if rec['isolated_SSFF_pass'] else 'FAIL')+'\n')
 return 0
if __name__=='__main__':raise SystemExit(main())
