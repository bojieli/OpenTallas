import argparse,json,hashlib,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable output exists')
sources=['rtl/hbm_accel/control/ot_hbm_native_mtp_transaction_cp_join.sv','rtl/test/hbm_accel/tb_hbm_native_mtp_transaction_cp_join.sv']
cases=[]
for mutant in (0,1,2):
 src=root/sources[0]
 if mutant:
  src=a.work/f'ownership_mutant{mutant}.sv';original=(root/sources[0]).read_text();needle=' && eng_cpl_epoch==owner_epoch' if mutant==1 else 'inflight && owned && !fault';assert needle in original;src.write_text(original.replace(needle,'' if mutant==1 else 'inflight && !fault'))
 exe=a.work/f'gate{mutant}.vvp'
 b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_mtp_transaction_cp_join',f'-Ptb_hbm_native_mtp_transaction_cp_join.MUT={mutant}','-o',str(exe),str(src),str(root/sources[1])],capture_output=True,text=True)
 if b.returncode:raise RuntimeError(b.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 cases.append(dict(mutant=mutant,returncode=r.returncode,output=r.stdout))
ok=cases[0]['returncode']==0 and all(c['returncode']!=0 for c in cases[1:])
rec=dict(schema='opentallas.hbm.native_mtp_transaction_cp_result.rtl.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in sources},scope='minimum full201 command/tagged ownership mechanism; engine operation translator and finite host queue integration pending')
a.out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2));raise SystemExit(0 if ok else 1)
