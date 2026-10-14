#!/usr/bin/env python3
"""Small IDX-P/native slot5 boundary gate; never a production-rate claim.
Run through ot-heavy --mem8: python3 tools/hbm_idx_b2_control_gate.py --out RUN.
"""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for name,rtl,tb,extra,old,new in [
 ('guard','ot_hgi_idx_b2_record_guard','tb_hgi_idx_b2_guard',[],"ab-40'd262144","ab"),
 ('station','ot_hgi_idx_b2_station','tb_hgi_idx_b2_station',['rtl/hbm_accel/generic/vm/ot_hgi_vm_lanechain.sv'],'.ID(5)','.ID(4)')]:
 source=ROOT/f'rtl/hbm_accel/generic/idx/{rtl}.sv';bench=ROOT/f'rtl/test/hbm_accel/idx_b2/{tb}.sv'
 for mutant in [False,True]:
  tag=name+('_mut' if mutant else '_exact');s=source
  if mutant:
   s=a.out/(tag+'.sv');s.write_text(source.read_text().replace(old,new))
   assert s.read_bytes()!=source.read_bytes()
  exe=a.out/(tag+'.vvp');cmd=['iverilog','-g2012','-s',tb,'-o',str(exe),str(s),str(bench)]+extra
  build=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (a.out/(tag+'.build.log')).write_bytes(build.stdout)
  assert build.returncode==0,tag+' compile failed'
  run=subprocess.run(['vvp',str(exe)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log=a.out/(tag+'.run.log');log.write_bytes(run.stdout)
  ok=(run.returncode!=0 and b'FATAL:' in run.stdout) if mutant else (run.returncode==0 and b'PASS IDX_B2_' in run.stdout)
  rows.append(dict(case=tag,mutant=mutant,exit=run.returncode,accepted=ok,log_sha256=sha(log),source_sha256=sha(s),bench_sha256=sha(bench)))
  assert ok,tag+' unexpected verdict'
record=dict(schema='opentallas.hbm.idx_b2.control_gate.v1',verdict='PASS',production_qualified=False,physical_closed=False,cases=rows)
(a.out/'gate.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS IDX_B2_CONTROL exact guard/native slot5, matching mutants FAIL; production and physical pending')
