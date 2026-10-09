"""Remote-only source-pinned actual candidate store to native global consumer exactness gate.

This runner is executed inside fleet admission, never on localhost. Failed
receipts are exclusive immutable files; full literal extents are checked.
"""
import argparse,hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES=['rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv','rtl/hbm_accel/service/ot_hbm_accel_r5a_ecc_pkg.sv',
'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v',
'rtl/hbm_accel/index/ot_hbm_candidate_sram_bank.sv','rtl/hbm_accel/index/ot_hbm_candidate_publication_store.sv',
'rtl/hbm_accel/index/ot_hbm_index_global_order.sv','rtl/hbm_accel/index/ot_hbm_candidate_global_publication_join.sv','rtl/hbm_accel/index/tb_hbm_candidate_global_publication_join.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args()
 if os.uname().nodename in ('ip-172-31-7-30','localhost') or ROOT.parent==Path('/home/ubuntu'):
  raise SystemExit('Remote admitted scratch checkout required; no localhost compute')
 a.work.mkdir(parents=True,exist_ok=False)
 hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}
 rec=dict(schema='opentallas.hbm_candidate_join_gate.v1',source_commit=a.source_commit,source_sha256=hashes,host=os.uname().nodename,verdict='FAIL',cases=[])
 cmd=['/usr/bin/time','-v','iverilog','-g2012','-s','tb_hbm_candidate_global_publication_join','-o',str(a.work/'gate.vvp')]+[str(ROOT/s)for s in SOURCES]
 with (a.work/'build.log').open('w')as f:result=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rec['build_returncode']=result.returncode
 if result.returncode==0:
  for mode in range(6):
   with(a.work/f'mode{mode}.log').open('w')as f:r=subprocess.run(['/usr/bin/time','-v','vvp',str(a.work/'gate.vvp'),f'+mode={mode}'],stdout=f,stderr=subprocess.STDOUT)
   log=(a.work/f'mode{mode}.log').read_text();rss=re.search(r'Maximum resident set size \(kbytes\): (\d+)',log)
   rec['cases'].append(dict(mode=mode,returncode=r.returncode,pass_marker='JOIN_PASS'in log,max_rss_kib=int(rss[1])if rss else None))
  positive=(a.work/'mode0.log').read_text()
  if all(c['returncode']==0 and c['pass_marker']for c in rec['cases'])and'ranks=96 native_flits=380 literal_extent=5700 outputs=950'in positive:rec['verdict']='PASS'
 if result.returncode==0:
  mutant=a.work/'mutant.vvp'
  mcmd=cmd.copy();mcmd[mcmd.index(str(a.work/'gate.vvp'))]=str(mutant)
  mcmd.insert(mcmd.index('-s'),'-Ptb_hbm_candidate_global_publication_join.MUT_SLOT=1')
  with(a.work/'mutant_build.log').open('w')as f:mb=subprocess.run(mcmd,stdout=f,stderr=subprocess.STDOUT)
  rec['mutant_build_returncode']=mb.returncode
  if mb.returncode==0:
   with(a.work/'mutant.log').open('w')as f:mr=subprocess.run(['vvp',str(mutant),'+mode=0'],stdout=f,stderr=subprocess.STDOUT)
   log=(a.work/'mutant.log').read_text();rec['mutant']=dict(returncode=mr.returncode,rejected='JOIN_MISMATCH'in log)
   if mr.returncode==0 or not rec['mutant']['rejected']:rec['verdict']='FAIL'
  else:rec['verdict']='FAIL'
 rec['inputs_unchanged']=hashes=={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SOURCES}
 if not rec['inputs_unchanged']:rec['verdict']='FAIL'
 with(a.work/'record.json').open('x')as f:json.dump(rec,f,indent=2);f.write('\n')
 print(json.dumps(rec,indent=2));return 0 if rec['verdict']=='PASS'else 1
if __name__=='__main__':raise SystemExit(main())
