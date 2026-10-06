#!/usr/bin/env python3
"""Owner-corrected real one-group streamed golden gate, before HC64 build."""
import argparse,json,socket,subprocess,sys
from pathlib import Path
import numpy as np
import hbm_compute_enabled_runner_20261006 as R
import dsrom_su_hcpost as H
F=np.float32
FILES=['rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/ot_hdc_fp32_f12.sv',
 'rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_delay.sv',
 'physical/hbm_die_abstracts_20261006/compute/tb_hc_corrected_group.sv']

def vectors(out):
 rng=np.random.default_rng(20261006)
 c=rng.integers(-128,129,(4,4)).astype(F)/F(64)
 p=rng.integers(-128,129,4).astype(F)/F(64)
 req=[];exp=[]
 def pack(v):return sum(int(x)<<(32*i) for i,x in enumerate(np.asarray(v,F).view(np.uint32).reshape(-1)))
 for k in range(32):
  r=rng.integers(-8192,8193,(4,1)).astype(F)/F(256)
  y=rng.integers(-8192,8193,1).astype(F)/F(256)
  req.append(pack(np.concatenate([r[:,0],y])))
  exp.append(pack(H.golden(r,y,c,p).reshape(-1)))
 for name,rows,bits in [('req',req,160),('exp',exp,128),('cfg',[pack(c)|(pack(p)<<512)],640)]:
  (out/('group_'+name+'.mem')).write_text(''.join(f'{v:0{bits//4}x}\n' for v in rows))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--admitted',action='store_true');a=ap.parse_args()
 release=R.hc_corrected_release() # blocks known failing/unreleased RTL BEFORE guard
 if socket.gethostname()!='climbing-locust':ap.error('EPYC2 only')
 out=a.out.resolve()
 if not str(out).startswith('/srv/opentallas-scratch2/'):ap.error('NVMe2 only')
 out.mkdir(parents=True,exist_ok=True)
 if (out/'terminal.json').exists():ap.error('immutable result exists')
 cap=R.capacity(out,'hc_group_post_admission' if a.admitted else 'hc_group_pre_admission')
 inv=json.loads((R.RESULT/'admission_inventory.json').read_text())['families']['hc']
 if not cap['cpu_fit'] or cap['disk_free_gib']<inv['disk_inventory_gib'] or cap['available_gib']<inv['declared_peak_gib']+100:return 75
 if not a.admitted:return subprocess.call(['/srv/opentallas-scratch/admit.sh',str(inv['declared_peak_gib']),'--',sys.executable,str(Path(__file__).resolve()),'--out',str(out),'--admitted'])
 pins={p:R.sha(R.ROOT/p) for p in FILES+['tools/dsrom_su_hcpost.py','tools/hdc_golden_v41.py','tools/hdc_golden.py','tools/hbm_compute_hc_minimum_20261006.py','tools/hbm_compute_enabled_runner_20261006.py']}
 source=dict(source_files=pins,owner_release=release,parameters=R.HC_PARAMS)
 if (out/'source.json').exists() and json.loads((out/'source.json').read_text())!=source:raise ValueError('source changed; preserve previous attempt and choose a new output directory')
 R.write(out/'source.json',source)
 vectors(out)
 v=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 version=subprocess.check_output([str(v),'--version'],text=True).strip()
 if not version.startswith('Verilator 5.050 '):raise ValueError('pinned tool mismatch')
 cmd=[str(v),'--binary','--timing','--hierarchical','--top-module','tb_hc_corrected_group','-O2','-Wno-fatal','-Wno-WIDTH','--build-jobs','16','--verilate-jobs','1','--hierarchical-threads','1','--unroll-count','4','-Mdir',str(out/'obj'),*FILES]
 binary=out/'obj/Vtb_hc_corrected_group'
 if not (out/'compile_pass.json').exists():
  rc,log=R.run(cmd,out,'compile')
  if rc:R.write(out/'terminal.json',dict(status='COMPILE_FAIL',returncode=rc));return rc
  R.write(out/'compile_pass.json',dict(binary_sha256=R.sha(binary)))
 elif R.sha(binary)!=json.loads((out/'compile_pass.json').read_text())['binary_sha256']:raise ValueError('held binary changed')
 if not R.capacity(out,'hc_group_before_golden')['cpu_fit']:return 75
 rc,log=R.run([str(binary),'+DIR='+str(out)],out,'golden')
 passed=rc==0 and 'HC_CORRECTED_GROUP_GOLDEN_PASS' in log
 R.write(out/'terminal.json',dict(status='PASS' if passed else 'GROUP_GOLDEN_FAIL',returncode=rc,source_files=pins,parameters=R.HC_PARAMS,tool_version=version,tool_sha256=R.sha(v),binary_sha256=R.sha(binary),seed=20261006,scope='one real four-lane group,32 streamed beats with bubbles; quarter/physical OPEN'))
 return 0 if passed else 1
if __name__=='__main__':sys.exit(main())
