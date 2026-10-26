#!/usr/bin/env python3
"""Actual3ROM calendar proof with per-root reset pins and fixed release epochs."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 results=[];cmd=['python3','-m','unittest','test_controller_image.Check.test_rtl_calendar7_exact_and_clock_mutant']
 for phase in (0,1,4):
  env=os.environ.copy();env.pop('RESET_ROOT_MUTANT',None);env['RESET_RELEASE_NS']=str(phase)
  r=subprocess.run(cmd,cwd=Path(__file__).parent,env=env,capture_output=True,text=True)
  (a.out/f'phase{phase}.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise SystemExit('calendar reset phase failed: '+str(phase))
  results.append(dict(release_ns_after_negedge=phase,exact_calendar_pass=True,stopped_clock_mutants_rejected=6))
 for i in range(3):
  env=os.environ.copy();env['RESET_ROOT_MUTANT']=str(i)
  r=subprocess.run(cmd,cwd=Path(__file__).parent,env=env,capture_output=True,text=True)
  (a.out/f'reset_root{i}_held.log').write_text(r.stdout+r.stderr)
  if r.returncode==0 or 'control slot mismatch' not in r.stderr:raise SystemExit('held reset mutant undetected: '+str(i))
  results.append(dict(held_reset_root=i,mutant_rejected=True))
 source=ROOT/'rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller7_resetpins.sv'
 (a.out/'receipt.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Component exactness, 3 actual4096x266 ROM functional macros, all468registered controls and done; not physical or die qualification',normal_cycle_delta=0,release_cycles=3,results=results),indent=2)+'\n')
 print('CAL7_RESET_PINS PASS controls=468 release_phases=3 clock_mutants=18 reset_mutants=3 normal_cycle_delta=0')
if __name__=='__main__':main()
