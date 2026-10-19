#!/usr/bin/env python3
"""Fleet-only bounded real endpoint health mechanism; no die/CQ qualification."""
import argparse,hashlib,json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
BASE='rtl/qwen_sys/host_integrated_20261014/'
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 v='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator';version=subprocess.check_output([v,'--version'],text=True);assert '5.050' in version
 src=R/BASE/'qkd_host_native_token_endpoint_cancel_health.sv';raw=src.read_text();receipts=[]
 cases=[('healthy','tb_qkd_host_native_token_endpoint_health',raw),('fault','tb_qkd_host_native_token_endpoint_health_fault',raw),('no_sticky','tb_qkd_host_native_token_endpoint_health_fault',raw.replace('&&health_sticky','&&1\'b0')),('retire_bypass','tb_qkd_host_native_token_endpoint_health_fault',raw.replace('&&!protocol_fault&&!health_block;','&&!protocol_fault;')),('admit_bypass','tb_qkd_host_native_token_endpoint_health_fault',raw.replace('&&!fault_q&&!health_block','&&!fault_q').replace('&&!cancel_release_v&&!health_block','&&!cancel_release_v')),('done_bypass','tb_qkd_host_native_token_endpoint_health_fault',raw.replace('(retire||(local_tk[92]&&!accept))&&!health_block','(retire||(local_tk[92]&&!accept))'))]
 for name,top,s in cases:
  out=a.out/name;out.mkdir(exist_ok=True);sf=out/'source.sv';sf.write_text(s);tb=R/'rtl/test/qwen_host'/f'{top}.sv'
  sources=[sf,R/BASE/'qkd_host_native_token_endpoint_cancel.sv',R/'rtl/qwen_sys/host_20261013/qkd_host_native_token_endpoint.sv',tb]
  cmd=[v,'--binary','--timing','-Wno-fatal','--top-module',top,'-j','2','--Mdir',str(out/'obj'),*[str(x) for x in sources]]
  c=subprocess.run(cmd,capture_output=True,text=True);(out/'compile.log').write_text(c.stdout+c.stderr)
  if c.returncode:print(name,'COMPILE_FAIL',c.returncode);return c.returncode
  q=subprocess.run([str(out/'obj'/('V'+top))],capture_output=True,text=True);(out/'runtime.log').write_text(q.stdout+q.stderr)
  expected={'no_sticky':'HEALTH_RETIRE','retire_bypass':'HEALTH_RETIRE','admit_bypass':'HEALTH_ADMIT','done_bypass':'HEALTH_DONE'}.get(name)
  ok=(q.returncode!=0 and expected in q.stdout+q.stderr) if expected else (q.returncode==0 and 'PASS HOST_' in q.stdout)
  row=dict(case=name,exit_code=q.returncode,expected_failure=expected,pass_=ok,source_sha256=hashlib.sha256(s.encode()).hexdigest(),bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest());receipts.append(row);print(name,row,q.stdout[-600:])
  (a.out/'receipt.json').write_text(json.dumps(dict(verilator=version.strip(),cases=receipts),indent=2)+'\n')
  if not ok:return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
