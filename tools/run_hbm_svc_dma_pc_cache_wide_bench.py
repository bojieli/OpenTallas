#!/usr/bin/env python3
"""One physical PC cache CPU exactness gate; no whole-array simulation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['tests/rtl/tb_hbm_svc_dma_pc_cache_wide.sv','rtl/common/ot_secded.sv',
 'rtl/hbm/hbm_svc_dma_sram_bank_wide.sv','rtl/hbm/ot_hbm_svc_dma_pc_cache_wide.sv',
 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v']

def run():
 records=[]
 pins=SOURCES+['rtl/common/ot_secded_cols.svh','tools/hbm_svc_dma_pc_cache_wide_model.py',
               'tools/run_hbm_svc_dma_pc_cache_wide_bench.py']
 before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins}
 with tempfile.TemporaryDirectory(prefix='hbm-pc-') as scratch:
  for mutant in (0,1):
   binary=str(Path(scratch)/f'pc-{mutant}.vvp')
   subprocess.run(['iverilog','-g2012','-DOT_MEM_NO_INIT','-I','rtl/common',
    '-s','tb_hbm_svc_dma_pc_cache_wide',f'-Ptb_hbm_svc_dma_pc_cache_wide.MUT={mutant}',
    '-o',binary,*SOURCES],cwd=ROOT,capture_output=True,text=True,check=True)
   proc=subprocess.run(['vvp',binary],cwd=ROOT,capture_output=True,text=True)
   passed=proc.returncode==0 and 'PASS bundles=' in proc.stdout
   records.append({'mutant':mutant,'returncode':proc.returncode,'stdout':proc.stdout,
    'stderr':proc.stderr,'expected':'PASS' if mutant==0 else 'FAIL_stale_epoch',
    'gate_pass':passed if mutant==0 else not passed})
 after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in pins}
 return {'scope':'onePC, four real wide banks/eight macro models; CPU, initialization disabled',
   'verdict':'PASS' if before==after and all(r['gate_pass'] for r in records) else 'FAIL',
   'records':records,'source_sha256':before,'sources_unchanged_during_gate':before==after,
   'epoch_scope':'onebit no-wrap; allocation blocked by native/write/issued-read debt; upstream cannot replay drained sameepoch generation',
   'physical_scope':'exactness only; no routed closure claim'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
 args=parser.parse_args();evidence=run()
 with args.output.open('x') as f:json.dump(evidence,f,indent=2);f.write('\n')
 print(json.dumps(evidence,indent=2))
 raise SystemExit(0 if evidence['verdict']=='PASS' else 1)
