#!/usr/bin/env python3
"""Minimum installed-span RTL gate; mutants are private copies, never pinned edits."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
RTL='rtl/hbm_accel/su/installed_span_20261007/ot_hbm_su_installed_span.sv'
TB='rtl/hbm_accel/su/installed_span_20261007/tb_hbm_su_installed_span.sv'
PKG='rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 source=(ROOT/RTL).read_text();runs={}
 mutants={'positive':None,
  'publication_bypass':('publication_owner==owner&&publication_record==record&&publication_source==source',"1'b1"),
  'response_owner_bypass':('rsp_record==record&&rsp_owner==owner&&rsp_source==source',"rsp_record==record&&rsp_source==source"),
  'address_truncation':("assign req_addr={d[5][36:5],5'd0};","assign req_addr={5'd0,d[5][31:5],5'd0};")}
 for name,mutation in mutants.items():
  p=a.out/name;p.mkdir(exist_ok=True);s=source
  if mutation:
   old,new=mutation;assert s.count(old)==1;s=s.replace(old,new)
  (p/'candidate.sv').write_text(s)
  cmd=['iverilog','-g2012','-s','tb_hbm_su_installed_span','-o',str(p/'sim'),str(ROOT/PKG),str(p/'candidate.sv'),str(ROOT/TB)]
  build=subprocess.run(cmd,capture_output=True,text=True);(p/'compile.log').write_text(build.stdout+build.stderr);build.check_returncode()
  run=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True);(p/'runtime.log').write_text(run.stdout+run.stderr)
  accepted=(run.returncode==0 and 'PASS SPAN reads=18 negatives=10 checks=300' in run.stdout) if name=='positive' else run.returncode!=0 and 'SPAN ' in run.stdout
  runs[name]=dict(expected_verdict_observed=accepted,exit_code=run.returncode,compile_command=cmd,source_sha256=hashlib.sha256(s.encode()).hexdigest())
 rec=dict(schema='opentallas.hbm.su.installed_span.gate.v1',status='PASS' if all(v['expected_verdict_observed'] for v in runs.values()) else 'FAIL',
  adopted=False,physical_qualified=False,full_program_join=False,model_pin='6ca8db61b',
  scope='One checked installed-span consumer with exact37bit addresses and owned return; upstream live association and fullSUprogram join remain required.',
  source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [PKG,RTL,TB]},runs=runs)
 (a.out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status']);return 0 if rec['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
