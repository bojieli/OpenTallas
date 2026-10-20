#!/usr/bin/env python3
"""Replay source-pinned production AQ transactions; optional stale-refresh mutant."""
import argparse,subprocess,os,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES=['rtl/test/hbm_accel/svg_rel/tb_hbm_aq_trace.sv','rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_safe.sv','rtl/test/hbm_accel/svg_rel/tb_svg_rel_dram_sparse.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
def main():
 a=argparse.ArgumentParser();a.add_argument('--work',required=True);a.add_argument('--trace',required=True);a.add_argument('--mutant',action='store_true');x=a.parse_args()
 work=Path(x.work).resolve();work.mkdir(parents=True,exist_ok=True);tr=Path(x.trace).resolve();tag='mutant' if x.mutant else 'positive'
 pins={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES};obj=work/('obj_'+tag+'_'+hashlib.sha256(str(pins).encode()).hexdigest()[:10]);exe=obj/'Vtb_hbm_aq_trace'
 if not exe.exists():
  cmd=[os.environ.get('VERILATOR',os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator')),'--binary','--timing','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_hbm_aq_trace','--Mdir',str(obj),'-j','8']+(['+define+BW_MUT_REF_STALE'] if x.mutant else [])+[str(ROOT/f) for f in FILES]
  r=subprocess.run(cmd,capture_output=True,text=True);(work/('build_'+tag+'.log')).write_text(r.stdout+r.stderr)
  if r.returncode:raise SystemExit(r.returncode)
 n=len(tr.read_text().splitlines());r=subprocess.run([str(exe),'TraceUnused=0',f'+TRACE={tr}',f'+N={n}'],capture_output=True,text=True)
 log=r.stdout+r.stderr;(work/(tag+'.log')).write_text(log)
 d={'source_sha256':pins,'trace_sha256':hashlib.sha256(tr.read_bytes()).hexdigest(),'trace_cycles':n,'mutant':x.mutant,'rc':r.returncode,'pass':'AQ_TRACE_PASS' in log,'fail_witness':('AQ_TRACE_REF_FAULT' in log or 'native command illegal REFpb' in log)}
 (work/(tag+'.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d));raise SystemExit(r.returncode)
if __name__=='__main__':main()
