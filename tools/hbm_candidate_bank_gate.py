"""Remote admitted full-depth 3-macro bank proof, same-source failing mutant."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv',
'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
'rtl/hbm_accel/index/ot_hbm_candidate_sram_bank.sv','rtl/hbm_accel/index/tb_hbm_candidate_sram_bank.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args()
 if ROOT.parent==Path('/home/ubuntu')or os.uname().nodename=='localhost':raise SystemExit('remote scratch only')
 a.work.mkdir(parents=True,exist_ok=False)
 hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SOURCES}
 rec=dict(source_commit=a.source_commit,source_sha256=hashes,cases=[],verdict='FAIL',host=os.uname().nodename)
 for mut in (0,1):
  exe=a.work/f'bank{mut}.vvp'
  cmd=['iverilog','-g2012','-s','tb_hbm_candidate_sram_bank',f'-Ptb_hbm_candidate_sram_bank.MUT_PAYLOAD={mut}','-o',str(exe)]+[str(ROOT/s)for s in SOURCES]
  with(a.work/f'build{mut}.log').open('w')as f:b=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
  c=dict(mutant=mut,build_returncode=b.returncode)
  if b.returncode==0:
   with(a.work/f'run{mut}.log').open('w')as f:r=subprocess.run(['/usr/bin/time','-v','vvp',str(exe)],stdout=f,stderr=subprocess.STDOUT)
   log=(a.work/f'run{mut}.log').read_text();c.update(returncode=r.returncode,pass_marker='BANK_PASS writes=128 reads=128'in log,failed_mismatch='BANK_MISMATCH'in log)
  rec['cases'].append(c)
 if rec['cases'][0].get('returncode')==0 and rec['cases'][0].get('pass_marker')and rec['cases'][1].get('returncode',0)!=0 and rec['cases'][1].get('failed_mismatch'):rec['verdict']='PASS'
 rec['inputs_unchanged']=hashes=={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SOURCES}
 if not rec['inputs_unchanged']:rec['verdict']='FAIL'
 with(a.work/'record.json').open('x')as f:json.dump(rec,f,indent=2);f.write('\n')
 print(json.dumps(rec,indent=2));return 0 if rec['verdict']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
