#!/usr/bin/env python3
"""Minimum word/provider client component; real join, modeled owned stack peer."""
from pathlib import Path
import argparse,hashlib,json,subprocess,tempfile
from hbm_sm_program_provider_model import model
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'rtl/hbm_accel/control_20261007/program_provider'
SOURCES=[ROOT/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',ROOT/'rtl/hbm_accel/loader/ot_hbm_accel_loader_addr_to_service.sv',ROOT/'rtl/hbm_accel/integration/ot_hbm_loader_service_join.sv',*sorted(DIR.glob('*.sv'))]

def run(args):
 p=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return dict(returncode=p.returncode,output=p.stdout)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',default='results/rtl/hbm_sm_program_provider_20261007/component.json');args=parser.parse_args()
 cases=[]
 with tempfile.TemporaryDirectory(prefix='hbm-program-gate-') as tmp:
  exe=str(Path(tmp)/'sim')
  build=run(['iverilog','-g2012','-s','tb_hbm_sm_program_service','-o',exe,*map(str,SOURCES)])
  if build['returncode']:raise RuntimeError(build)
  for case in range(11):
   r=run(['vvp',exe,f'+CASE={case}']);r['case']=case;r['pass']=r['returncode']==0 and 'PASS' in r['output'];cases.append(r)
  mutants=[]
  for label,old,new,case in [('wrong_word_lane','saved_addr[4:2]*32','0*32',0),('parity_bypass','wire parity_ok=parity==^{saved_addr,saved_phys,saved_tag,saved_data};',"wire parity_ok=1'b1;",7)]:
   target=DIR/'ot_hbm_sm_program_word.sv';text=target.read_text();assert old in text
   mutated=Path(tmp)/(label+'.sv');mutated.write_text(text.replace(old,new))
   b=run(['iverilog','-g2012','-s','tb_hbm_sm_program_service','-o',exe,*[str(mutated if s==target else s) for s in SOURCES]])
   assert b['returncode']==0,b
   r=run(['vvp',exe,f'+CASE={case}']);r['mutant']=label;r['rejected']=r['returncode']!=0;mutants.append(r)
 files=SOURCES+[Path(__file__),ROOT/'tools/hbm_sm_program_provider_model.py',ROOT/'tools/hbm_sm_program_provider_build.py',ROOT/'results/rtl/hbm_sm_command_20261007/stress_seq.hex']
 result=dict(status='PASS' if all(x['pass'] for x in cases) and all(x['rejected'] for x in mutants) else 'FAIL',scope='real native word adapter and existing loader_service_join; test-owned shared stack peer, not full causal provider or PHY',model=model(),cases=cases,mutants=mutants,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},physical_admitted=False)
 out=ROOT/args.output
 if out.exists():raise RuntimeError('immutable receipt already exists; choose successor path')
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],cases=len(cases),mutants=len(mutants),receipt=str(out))))
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
