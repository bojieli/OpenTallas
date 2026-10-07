#!/usr/bin/env python3
"""Actual loader identity/reverse-grant seam with finite local client association."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
from hbm_sm_service_mux_model import model
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'rtl/hbm_accel/control_20261007/service_mux'
S=[ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',ROOT/'rtl/hbm_accel/loader/ot_hbm_accel_loader_addr_to_service.sv',*sorted(D.glob('*.sv'))]
def run():
 cases=[]
 with tempfile.TemporaryDirectory(prefix='native_mux_') as td:
  exe=Path(td)/'sim'
  for n in [4,5]:
   subprocess.run(['iverilog','-g2012','-s','tb_hbm_sm_service_mux',f'-Ptb_hbm_sm_service_mux.NCLIENT={n}','-o',str(exe),*map(str,S)],check=True,capture_output=True)
   for c in range(4):
    p=subprocess.run(['vvp',str(exe),f'+CASE={c}'],capture_output=True,text=True)
    if p.returncode or 'PASS' not in p.stdout:raise RuntimeError(p.stdout+p.stderr)
    cases.append(dict(clients=n,case=c,output=p.stdout.strip()))
  orig=D/'ot_hbm_sm_service_mux.sv';mut=Path(td)/'mut.sv'
  text=orig.read_text();assert 'wire mismatch=q!=~qn||r!=~rn||' in text
  mut.write_text(text.replace('wire mismatch=q!=~qn||r!=~rn||','wire mismatch='))
  subprocess.run(['iverilog','-g2012','-s','tb_hbm_sm_service_mux','-o',str(exe),*[str(mut if p==orig else p) for p in S]],check=True,capture_output=True)
  p=subprocess.run(['vvp',str(exe),'+CASE=3'],capture_output=True,text=True)
  if not p.returncode:raise RuntimeError('bank-check bypass not rejected')
  cases.append(dict(mutation='remove_request_response_bank_checks',rejected=True,output=p.stdout.strip()))
 files=S+[Path(__file__),ROOT/'tools/hbm_sm_service_mux_build.py',ROOT/'tools/hbm_sm_service_mux_model.py',ROOT/'rtl/hbm_accel/integration/ot_hbm_loader_service_join.sv']
 return dict(status='PASS',scope='4/5 finiteclients and actual loader ownedidentity/reversegrant logic with testowned stackpeer; no causalPHY provider or real dispatch identity issuer',model=model(),cases=cases,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},physical_admitted=False)
if __name__=='__main__':
 m=run();p=ROOT/'results/rtl/hbm_sm_service_mux_20261007/component.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(m,indent=2)+'\n');print(m['status'])
