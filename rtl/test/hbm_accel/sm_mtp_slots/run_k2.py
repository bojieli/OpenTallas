#!/usr/bin/env python3
"""Native P6/K2 diagnostic using the exact production BDC source set."""
import argparse,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('out');p.add_argument('--jobs',type=int,default=8);a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[4];out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
s=json.loads((r/'physical/ref_tile/smh_bdc_ref_p50/spec.json').read_text())
src=s['sources']+['rtl/hbm_accel/sm/mtp_slots/ot_hbm_sm_mtp_k2.sv','rtl/test/hbm_accel/sm_mtp_slots/tb_hbm_sm_mtp_k2.sv']
for mut in (0,1):
 b=out/f'build_m{mut}';cmd=['verilator','--binary','--timing','-O1','-Wno-fatal','--top-module','tb_hbm_sm_mtp_k2','--Mdir',str(b),'-j',str(a.jobs),f'-GMUT={mut}',*['-D'+d for d in s['defines']],*src]
 with (out/f'build_m{mut}.log').open('w') as f:subprocess.run(cmd,cwd=r,stdout=f,stderr=subprocess.STDOUT,check=True)
 v=subprocess.run([str(b/'Vtb_hbm_sm_mtp_k2')],capture_output=True,text=True,cwd=r);(out/f'run_m{mut}.log').write_text(v.stdout+v.stderr)
 ok=v.returncode==0 and 'PASS K2' in v.stdout if mut==0 else v.returncode!=0 and 'K2 mismatch' in v.stdout
 if not ok:raise SystemExit(f'gate failed mutant={mut} rc={v.returncode}; see {out}')
 print(f'K2 gate m{mut} PASS',flush=True)
