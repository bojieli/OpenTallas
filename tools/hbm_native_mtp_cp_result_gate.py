import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=json.loads((ROOT/'results/rtl/hbm_token_fifo_reservation_20261009/native_mtp_sources.json').read_text())['sources']+['rtl/test/hbm_accel/tb_hfd_mtp_x_cp_stop.sv']
SRC=[x.replace('ot_dshbm_dspark_top_stop.sv','ot_dshbm_dspark_top_cp_stop.sv').replace('ot_hfd_mtp_core_stop.sv','ot_hfd_mtp_core_cp_stop.sv').replace('hfd_mtp_x_stop.sv','hfd_mtp_x_cp_stop.sv') for x in SRC]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable fresh evidence path required')
cases=[]
for k,reset in [(k,r) for k in (0,1,2) for r in (0,1)]:
 exe=a.work/f'k{k}r{reset}.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_hfd_mtp_x_cp_stop',f'-Ptb_hfd_mtp_x_cp_stop.KIND={k}',f'-Ptb_hfd_mtp_x_cp_stop.RESET_FIRST={reset}','-o',str(exe),*[str(ROOT/s) for s in SRC]],capture_output=True,text=True)
 if b.returncode:raise RuntimeError(b.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(kind=k,reset_first=reset,returncode=r.returncode,output=r.stdout))
ok=all(c['returncode']==0 for c in cases)
record=dict(schema='opentallas.hbm.native_mtp_cp_result.rtl.v1',verdict='PASS' if ok else 'FAIL',scope='actual fullshape nativeXSEL384/gamma5/40layer core, checked externalCPRESULT/accept/specstate/outputskid; synthetic result tokens and layer completions, no fulltensor arithmetic claim',cases=cases,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
