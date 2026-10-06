#!/usr/bin/env python3
"""Minimum fullshape production control/list/finite-consumer physical run."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--exact',type=Path,required=True);a=p.parse_args()
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():raise SystemExit('clean pinned source required')
 exact=json.loads(a.exact.read_text())
 if exact['status']!='pass' or not exact.get('backpressure',{}).get('pass_'):raise SystemExit('actual production exact and finite drain gates required')
 pre='rtl/dsrom_sys/reindex_parent/'
 src=[pre+n for n in ['ot_dsrom_reindex_parent_physctx.sv','ot_dsrom_reindex_parent_control.sv','ot_dsrom_reindex_kgctl_parent.sv','ot_dsrom_reindex_list_macro.sv','ot_dsrom_reindex_request_cut.sv','ot_dsrom_reindex_drain_queue.sv']]
 for f in src:
  if f.endswith('physctx.sv'):continue
  if exact['source_sha256'].get(f)!=hashlib.sha256((ROOT/f).read_bytes()).hexdigest():raise SystemExit('exact source mismatch: '+f)
 macro='ot_sram_1r1w_512x128_m4_r2c2'
 src+=['physical/asap7_memory_macros/'+macro+'/'+macro+'_bb.v']
 pins=src+['tools/run_abi3_physical.py','tools/orfs_allcorner_spef.py','tools/dsrom_reindex_parent_physical.py','physical/common/ot_macro_track_snap.tcl','physical/dsrom_reindex_parent/place.tcl','physical/dsrom_reindex_parent/regions.tcl','tools/dsrom_reindex_parent_model.py']
 a.out.mkdir(parents=True,exist_ok=False)
 (a.out/'source.json').write_text(json.dumps(dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in pins},exact_record_sha256=hashlib.sha256(a.exact.read_bytes()).hexdigest(),scope='Actual production control, list SRAM/capture, request slots and four-entry drain header; key data store outside scope; all interfaces timed; fixed control cap37452.2um2'),indent=2)+'\n')
 cmd=[sys.executable,str(ROOT/'tools/run_abi3_physical.py'),'--view','asap7','--top','ot_dsrom_reindex_parent_physctx']
 for f in src:cmd+=['--source',f]
 cmd+=['--clock-period-ns','0.833333','--clock-uncertainty-ns','0.060','--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC','--hold-corners','WC,BC','--stages','pnr','--hold-margin-ns','0.008','--max-transition-ns','library','--slew-margin-percent','20','--max-fanout','32','--io-delay-fraction','0.2','--die-area','0','0','728.384','460.964','--core-area','2.052','2.160','726.324','458.910','--macro-view',macro+'=physical/asap7_memory_macros/'+macro,'--macro-place-halo','2','2','--orfs-var','PLACE_DENSITY_LB_ADDON=','--step-tcl','POST_MACRO_PLACE=physical/dsrom_reindex_parent/place.tcl','--step-tcl','POST_PDN=physical/dsrom_reindex_parent/regions.tcl','--synth-timeout-seconds','unlimited','--flow-timeout-seconds','unlimited','--nickname-tag','reindex_parent','--keep-workdir',str(a.out.resolve()/'work'),'--output',str(a.out.resolve()/'physical.json')]
 env=os.environ.copy();env['OT_ORFS_NUM_CORES']='16';env['PLACE_DENSITY_LB_ADDON']=''
 with (a.out/'route.log').open('w') as log:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
 (a.out/'exit').write_text(str(r.returncode)+'\n')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()
