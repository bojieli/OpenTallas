#!/usr/bin/env python3
"""Owner-authorized replay of only the frozen compiler's original emission.

Calls the original emitter without edits. Its internal reference return is
discarded: no golden output is emitted, used as DUT input, or changed. No RTL
compile, executable replay, model inference, or substitute schedule is run.
"""
import hashlib
import importlib
import json
import sys
from pathlib import Path

TARGET='0cfed448f54896266ce57d3a94826e4044cf47f8b09a22419fe16eb5e5a180d7'
PINS={
 'tools/rtl_hdc_v41x_vec_campaign.py':'619367dddf92d3d0c2c7664bf8fdb76072bd9c22c27eb8f997712fca5a383346',
 'tools/su_fmax_measure.py':'6a704ee43ed4305e440e70970c1eb071e2522b5e1758c3e4b8bd629defdb394d',
 'tools/hdc_golden.py':'85cd0710fd5d3926c31f0954729b22c18a75ba8835f7e3735018f02655f911a6',
 'tools/hdc_golden_v41.py':'7e6c677b72fc5178a622d192a517d223872dbc0ee1d5920d3441fcf4b5aa4816',
 'tools/hdc_isa_v41.py':'e32522bab7199130df40a0ba3e4452b6f6ad1cd008372b58ab4c3eda344c17c3'}
CASE_PIN='8c18c0655ccf6a147cde5e8a65e709ad5ccfd62ba9024e2644019289cd8d2108'


def main(root,cases,out):
 root,cases,out=map(Path,(root,cases,out))
 for path,pin in PINS.items():
  if hashlib.sha256((root/path).read_bytes()).hexdigest()!=pin:
   raise ValueError('frozen emitter dependency differs: '+path)
 if hashlib.sha256(cases.read_bytes()).hexdigest()!=CASE_PIN:
  raise ValueError('archived case input differs')
 sys.path.insert(0,str(root/'tools'))
 import pickle
 import numpy as np
 VC=importlib.import_module('rtl_hdc_v41x_vec_campaign')
 FM=importlib.import_module('su_fmax_measure')
 blob=pickle.loads(cases.read_bytes())
 cs=blob['cases'][4]
 assert cs['name']=='L0.hc_post.attn' and len(cs['ops'])==4
 # Exact cmd_su_run initialization from the source-pinned archived driver.
 VC.BCAST,VC.RET=7,8
 FM.set_mlat_f12(6,5,VC)
 vm=np.zeros(1<<VC.VMA,dtype=np.uint32)
 for ad,v in cs['init']:
  vm[ad:ad+len(v)]=np.asarray(v,dtype=np.float32).view(np.uint32)
 mem0=VC.Mem(vm,np.zeros(1<<VC.KVA,dtype=np.uint32),
             np.stack([cs['cr_lo'],cs['cr_hi']],axis=1),
             np.zeros(1<<VC.WRA,dtype=np.uint16))
 # Original emission entry and default chain=True, as archived run_program.
 # The internal numerical reference result is neither saved nor compared.
 _,sops,_,_=VC.schedule(cs['ops'],mem0,1024,256)
 out.mkdir(parents=True,exist_ok=False)
 pending=out/'emitted_unaccepted.hex'
 VC.write_hex(pending,[VC.encode(f) for f in sops],((VC.PW+3)//4)*4)
 actual=hashlib.sha256(pending.read_bytes()).hexdigest()
 accepted=actual==TARGET
 record=dict(schema='opentallas.ds20-su-original-program-reconstruction.v1',
  accepted=accepted,target_sha256=TARGET,actual_sha256=actual,
  source_root=str(root),source_sha256=PINS,case_sha256=CASE_PIN,
  archived_case_name=cs['name'],case_index=4,original_instruction_count=4,
  args=dict(N=1024,M=256,BCAST=7,RET=8,MLAT=6,ALAT=5,
            fp='dpi_beh',f12=True,cases='su_cases_v2_ildr.pkl',chain=True),
  input_initialization='source-pinned dshbm_baseline_measure.cmd_su_run',
  archived_driver_sha256='357f8408c32d5da7cd499bbf83a76bf07b4d943a0f24b9c78a2a195c90cc0978',
  emitter='original VC.schedule -> VC.encode -> VC.write_hex; unchanged formulas and arguments',
  reference_results_discarded=True,oracle_output_files_generated=False,
  RTL_or_native_execution=False,model_inference=False)
 if accepted:pending.rename(out/'prog.hex')
 (out/'reconstruction.json').write_text(json.dumps(record,indent=2)+'\n')
 print(json.dumps(record,indent=2))
 return 0 if accepted else 1


if __name__=='__main__':
 raise SystemExit(main(*sys.argv[1:]))
