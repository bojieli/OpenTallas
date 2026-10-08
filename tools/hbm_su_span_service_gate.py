#!/usr/bin/env python3
"""SU installed-span client4 bound to actual five-client native shared join."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from hbm_sm_service_mux_gate import S
R=Path(__file__).resolve().parents[1]
D=R/'rtl/hbm_accel/su/installed_span_20261007'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 installed=R/'results/uarch/hbm_sm_native_production_20261007/installed_spans_candidate.json'
 record=json.loads(installed.read_text())['records'][0]
 assert record['record']==0 and record['result_byte_base']==119440480 and record['result_rows']==1
 files=[R/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',*S,D/'ot_hbm_su_installed_span.sv',D/'ot_hbm_su_installed_span_client.sv',D/'tb_hbm_su_span_service.sv']
 exe=a.out/'sim';cmd=['iverilog','-g2012','-s','tb_hbm_su_span_service','-o',str(exe),*map(str,files)]
 build=subprocess.run(cmd,capture_output=True,text=True);(a.out/'compile.log').write_text(build.stdout+build.stderr);build.check_returncode()
 cases=[]
 for case in range(3):
  run=subprocess.run(['vvp',str(exe),f'+CASE={case}'],capture_output=True,text=True)
  (a.out/f'case{case}.log').write_text(run.stdout+run.stderr)
  assert run.returncode==0 and 'PASS SPAN_SERVICE' in run.stdout,run.stdout+run.stderr
  cases.append(dict(case=case,exit_code=run.returncode,output=run.stdout.strip()))
 rec=dict(schema='opentallas.hbm.su.span_service.gate.v1',status='PASS',adopted=False,physical_qualified=False,
  scope='Actual span-client and five-client shared/loader identity join; eight exact words from installed record0 using test-issued owner and testowned stack peer. Wrong returned producer and responsebank corruption inhibit operand publication.',
  logical_word_base=123,logical_mapping_scope='bench descriptor; native consumer program mapping not yet installed',
  allocation_record=record,context_layout='{owner73,record16,source5}',checks_not_tied=True,
  missing=['production native dispatch owner issuer','causal service PHY/backend','actual SU program/virtual-edge scheduling join','SS/FF in context'],
  source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files+[installed,Path(__file__)]},compile_command=cmd,cases=cases)
 (a.out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n');print('PASS')
if __name__=='__main__':main()
