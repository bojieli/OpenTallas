#!/usr/bin/env python3
"""Actual relay composition proof only; execute via ot-run. No route adoption."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['rtl/test/hbm_sfu_relay_0330/tb_sfu_split48.sv','rtl/test/hbm_sfu_relay_0330/hbfd_rly_624_split48_candidate.sv','rtl/hbm_accel/die_glue/hbfd_rly_masters.sv','rtl/hbm_accel/die_glue/ot_hbm_rly.sv','rtl/lib/ot_rst_relay.sv']
def main():
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 rows=[]
 for r,m in [(1,0),(11,0),(23,0),(23,1),(23,2),(23,3)]:
  tag=f'R{r}_M{m}';obj=a.out/(tag+'.vvp')
  cmd=['iverilog','-g2012','-s','tb_sfu_split48',f'-Ptb_sfu_split48.R={r}',f'-Ptb_sfu_split48.MUT={m}','-o',str(obj)]+SOURCES
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);(a.out/(tag+'.compile.log')).write_text(p.stdout+p.stderr);p.check_returncode()
  p=subprocess.run(['vvp',str(obj.resolve())],cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr;(a.out/(tag+'.log')).write_text(log)
  ok=(p.returncode==0 and 'SPLIT48 PASS' in log) if m==0 else (p.returncode!=0 and 'SPLIT48 mismatch' in log)
  rows.append(dict(R=r,MUT=m,exit=p.returncode,passed=ok))
  if not ok:raise RuntimeError(tag+' failed expected verdict')
 receipt=dict(scope='functional source/reset/cycle equivalence only; station reset tree, clocks, placement, route, reach and full scheduled SFU proof remain OPEN',sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},cases=rows,payload_bits_per_station=624,literal_48_masters_per_station=13,reset_FF_per_station=15)
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('SPLIT48_GATE PASS')
if __name__=='__main__':main()
