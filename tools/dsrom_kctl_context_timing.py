#!/usr/bin/env python3
"""One pinned drain-controller component route; no full-context clock claim.
Reuse Beauvoir's exact/zero-added-cycle receipt. Build without time/resource caps.
"""
import argparse, importlib.util, json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
 sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);a=p.parse_args()
 out=a.run_dir.resolve();out.mkdir(parents=True,exist_ok=True)
 def status(phase,**kwargs):
  (out/'status.json').write_text(json.dumps(dict(phase=phase,pid=os.getpid(),scope='COMPONENT_ONLY_CONTEXT_UNQUALIFIED',**kwargs),indent=2)+'\n')
 model=json.loads((ROOT/'results/uarch/dsrom_kctl_context_timing_20261003/model.json').read_text())
 import hashlib
 for path,h in model['pins'].items():
  if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=h:raise RuntimeError('Source changed: '+path)
 os.environ['OT_ORFS_NUM_CORES']='16'
 driver=module('kctl_physical',ROOT/'tools/run_abi3_physical.py')
 # Task-local override: repository driver defaults arbitrary 2h/6h ceilings.
 # No source-driver mutation or progressing-job restart; no wall/resource cap.
 def uncapped(cmd,*,cwd=None,timeout=None):
  return subprocess.run(cmd,cwd=cwd,capture_output=True,text=True)
 driver.run=uncapped;driver.flow_timeout_seconds=lambda:None;driver.synth_timeout_seconds=lambda:None
 status('ROUTE',source_commit=model['selected_source_commit'])
 args=['--view','asap7','--top','ot_hdc_v41x_idx_kctl_ring_drain',
       '--source','rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring_drain.sv',
       '--clock-period-ns','0.833','--clock-uncertainty-ns','0.060',
       '--clock-uncertainty-hold-ns','0.025','--orfs-corner','WC',
       '--hold-corners','WC,BC','--stages','pnr','--io-delay-fraction','0.2',
       '--max-transition-ns','library','--max-fanout','32',
       '--core-utilization','35','--keep-workdir',str(out/'work'),
       '--output',str(out/'physical.json')]
 for k,v in model['parameters'].items():args+=['--param',f'{k}={v}']
 rc=driver.main(args)
 odb=list((out/'work/orfs/results/asap7').glob('*/base/6_final.odb'))
 corner_rc=None
 if odb:
  status('CORNER_STA',physical_returncode=rc)
  corner=module('kctl_corner',ROOT/'tools/w18/corner_sta.py')
  corner_rc=corner.main(['--orfs-dir',str(out/'work/orfs'),'--output',str(out/'corner_sta.json')])
 status('TERMINAL',physical_returncode=rc,corner_returncode=corner_rc,routed=bool(odb),full_context_qualified=False)
 return rc
if __name__=='__main__':sys.exit(main())
