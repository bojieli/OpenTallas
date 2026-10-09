#!/usr/bin/env python3
"""Minimum finite endpoint gate. Output directories are immutable; no PHY/route claim."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from hbm_loader_native_service_model import model
R=Path(__file__).resolve().parents[1]
D=R/'rtl/hbm_accel/loader/service_native'
def run(src,td,mode=0):
 exe=td/'sim'
 cp=subprocess.run(['iverilog','-g2012','-s','tb_loader_native_endpoint','-o',str(exe),str(src),str(D/'tb_loader_native_endpoint.sv')],capture_output=True,text=True)
 if cp.returncode:return dict(passed=False,compile=cp.stdout+cp.stderr)
 cp=subprocess.run(['vvp',str(exe),f'+mode={mode}'],capture_output=True,text=True)
 return dict(passed=cp.returncode==0 and 'PASS' in cp.stdout,output=cp.stdout+cp.stderr)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 src=D/'ot_hbm_loader_native_endpoint.sv';raw=src.read_text()
 with tempfile.TemporaryDirectory(prefix='loader-native-') as t:
  td=Path(t);cases=[dict(mode=i,**run(src,td,i)) for i in range(6)]
  mutations={'acceptance_is_completion':('if(wr_v&&wr_rdy)state<=WRITE_WAIT;','if(wr_v&&wr_rdy)state<=REPLY;'),
   'ignore_read_identity':('wire rd_match=rd_rsp_pc==pc_q&&rd_rsp_tag==tag_q&&rd_rsp_beat==0;','wire rd_match=1;')}
  mutants=[]
  for name,(before,after) in mutations.items():
   assert raw.count(before)==1
   candidate=td/(name+'.sv');candidate.write_text(raw.replace(before,after));res=run(candidate,td)
   mutants.append(dict(name=name,detected=not res['passed'],**res))
 files=[src,D/'tb_loader_native_endpoint.sv',Path(__file__),R/'tools/hbm_loader_native_service_model.py']
 ok=all(x['passed'] for x in cases) and all(x['detected'] for x in mutants)
 receipt=dict(verdict='PASS_ENDPOINT_ONLY' if ok else 'FAIL',model=model(),cases=cases,mutants=mutants,
  source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
  physical_admitted=False,service_join_proven=False,
  limitations=['external translated address validity is an input contract; actual aperture mapper must be joined',
   'write ACK is test-owned; real source-owned physical completion counter join is required',
   'read peer is test-owned; service read lease arbiter required','no SS/FF, die routing or token credit'])
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(receipt['verdict']);return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
