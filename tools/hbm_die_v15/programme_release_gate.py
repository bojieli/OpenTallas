#!/usr/bin/env python3
"""Actual release-leaf component proof; not programme or physical closure."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SRC=['rtl/test/hbm_programme_local_1016/tb_programme_release.sv','rtl/test/hbm_programme_local_1016/ot_hbm_su_bridge_release_local_candidate.sv','rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_bridge_release.sv']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);rows=[]
 for m in range(3):
  obj=a.out/f'm{m}.vvp';cmd=['iverilog','-g2012','-s','tb_programme_release',f'-Ptb_programme_release.MUT={m}','-o',str(obj)]+SRC
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(a.out/f'm{m}.compile.log').write_text(p.stdout+p.stderr);p.check_returncode()
  p=subprocess.run(['vvp',str(obj.resolve())],cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr;(a.out/f'm{m}.log').write_text(log)
  ok=(p.returncode==0 and 'LOCAL_RELEASE PASS' in log) if m==0 else (p.returncode!=0 and 'LOCAL_RELEASE_MISMATCH' in log)
  rows.append(dict(MUT=m,exit=p.returncode,passed=ok));assert ok,rows
 receipt=dict(scope='Actualreleaseleaf/twoFFcandidate component only. Full302/476 programme+SU composition and physicalclock/resetnativequalification remainOPEN',sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},cases=rows)
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('LOCAL_RELEASE_GATE PASS')
if __name__=='__main__':main()
