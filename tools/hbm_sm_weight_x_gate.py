#!/usr/bin/env python3
"""Actual REQCR helper + finite weight/X primitives; modeled sector responses."""
from pathlib import Path
import json,hashlib,subprocess,tempfile
from hbm_sm_weight_x_model import model
R=Path(__file__).resolve().parents[1];D=R/'rtl/hbm_accel/control_20261007/weight_x_provider'
SM=R/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'
def run(args):
 p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 return dict(returncode=p.returncode,output=p.stdout)
def main():
 cases=[];mutants=[];lint=[]
 with tempfile.TemporaryDirectory(prefix='hbm-weight-x-') as tmp:
  t=Path(tmp);s=SM.read_text();start=s.index('module ot_hbm_accel_smh_reqrl #(');end=s.index('endmodule',start)+len('endmodule')
  helper=t/'actual_reqrl.sv';helper.write_text(s[start:end]+'\n')
  for kind in ('weight','x'):
   src=[D/'ot_hbm_sm_sector_read.sv',D/f'ot_hbm_sm_{kind}_read.sv',D/f'tb_hbm_sm_{kind}_read.sv']
   if kind=='weight':src.append(helper)
   exe=str(t/kind);b=run(['iverilog','-g2012','-s',f'tb_hbm_sm_{kind}_read','-o',exe,*map(str,src)]);assert b['returncode']==0,b
   for case in range(5):
    v=run(['vvp',exe,f'+CASE={case}']);v.update(kind=kind,case=case,passed=v['returncode']==0 and 'PASS' in v['output']);cases.append(v)
   change=('base+37\'(index)*37\'d32',"base+37'(index)*37'd64")
   raw=src[0].read_text();assert change[0] in raw
   mutant=t/f'{kind}_stride.sv';mutant.write_text(raw.replace(*change))
   b=run(['iverilog','-g2012','-s',f'tb_hbm_sm_{kind}_read','-o',exe,str(mutant),*map(str,src[1:])]);assert b['returncode']==0,b
   v=run(['vvp',exe]);v.update(kind=kind,mutation='wrong_sector_stride',rejected=v['returncode']!=0);mutants.append(v)
   if kind=='weight':
    b=run(['iverilog','-g2012','-DOT_SMH_MUT_REQOVF','-s',f'tb_hbm_sm_{kind}_read','-o',exe,*map(str,src)]);assert b['returncode']==0,b
    v=run(['vvp',exe]);v.update(kind=kind,mutation='actual_REQCR_permission_bypass',rejected=v['returncode']!=0);mutants.append(v)
   deps=[R/'rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv',R/'rtl/hbm_accel/loader/ot_hbm_accel_loader_addr_to_service.sv',R/'rtl/hbm_accel/integration/ot_hbm_loader_service_join.sv']
   rtl=[p for p in D.glob('*.sv') if not p.name.startswith('tb_')]
   v=run(['verilator','--lint-only','-Wno-fatal','--top-module',f'ot_hbm_sm_{kind}_service_join','-GENABLE=1',*map(str,deps+rtl)])
   lint.append(dict(kind=kind,returncode=v['returncode'],warning_count=v['output'].count('%Warning'),errors=[l for l in v['output'].splitlines() if '%Error' in l]))
 files=[*sorted(D.glob('*.sv')),SM,*deps,R/'tools/hbm_sm_weight_x_model.py',R/'tools/hbm_sm_weight_x_build.py',Path(__file__)]
 result=dict(status='PASS' if all(c['passed'] for c in cases) and all(m['rejected'] for m in mutants) and all(l['returncode']==0 for l in lint) else 'FAIL',
 scope='actual extracted reqrl and sector primitives; bounded synthetic sector peer; concrete existing shared-service wrappers enabled lint only, no full provider/PHY simulation',model=model(),cases=cases,mutants=mutants,join_lint=lint,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},physical_admitted=False)
 out=R/'results/rtl/hbm_sm_weight_x_20261007/component.json'
 if out.exists():raise RuntimeError('immutable receipt exists')
 out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('status','scope')}))
 if result['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
