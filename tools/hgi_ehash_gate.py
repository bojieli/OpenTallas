#!/usr/bin/env python3
"""Run on admitted fleet host only; immutable independent EHASH exact/mutant gate."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--work',required=True);a=p.parse_args()
r=Path(__file__).resolve().parents[1];w=Path(a.work);w.mkdir(parents=True,exist_ok=True);out=Path(a.output)
if out.exists():raise FileExistsError(out)
paths=['rtl/hdc/v41/ot_hdc_engram_tables_shipped_pkg.sv','rtl/hdc/v41/ot_hdc_engram_hash_shipped.sv','rtl/hbm_accel/generic_20261009/ot_hbm_idx_ehash_ds.sv','rtl/hbm_accel/generic_20261009/tb_hbm_idx_ehash_ds.sv']
rec={'schema':'opentallas.hgi-ehash-gate.v1','host':subprocess.check_output(['hostname'],text=True).strip(),'sources':{x:hashlib.sha256((r/x).read_bytes()).hexdigest() for x in paths},'cases':{},'generic_dynamic_B_conformance':False}
for m in range(5):
 cmd=['iverilog','-g2012','-s','tb_hbm_idx_ehash_ds',f'-Ptb_hbm_idx_ehash_ds.MUTANT={m}','-o',str(w/f'gate.{m}'),*[str(r/x) for x in paths]]
 build=subprocess.run(cmd,capture_output=True,text=True);(w/f'build.{m}.log').write_text(build.stdout+build.stderr)
 if build.returncode:rec['cases'][str(m)]={'build_rc':build.returncode,'pass':False};break
 run=subprocess.run(['vvp',str(w/f'gate.{m}')],capture_output=True,text=True);log=run.stdout+run.stderr;(w/f'run.{m}.log').write_text(log)
 ok=('PASS EHASH DS LOCKSTEP HISTORY ACCEPT 10 cases 240 row ids' in log and run.returncode==0) if m==0 else (run.returncode!=0 and 'FATAL:' in log and ('EHASH' in log or 'unexpected fault' in log))
 rec['cases'][str(m)]={'build_rc':0,'run_rc':run.returncode,'pass':ok,'log':log}
rec['pass']=len(rec['cases'])==5 and all(x['pass'] for x in rec['cases'].values());out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));raise SystemExit(not rec['pass'])
