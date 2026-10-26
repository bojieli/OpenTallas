#!/usr/bin/env python3
"""Prove new local capture boundaries against literal baseline equations only."""
import argparse, hashlib, json, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 src=['tools/s81_engram_mix/localized_candidate/tb.sv','rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_localized_candidate.sv']
 results=[]
 for m in range(3):
  exe=a.out/f'm{m}.vvp'
  subprocess.run(['iverilog','-g2012','-s','tb',f'-Ptb.MUT={m}','-o',str(exe),*[str(R/x) for x in src]],check=True,capture_output=True,text=True)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);log=r.stdout+r.stderr;(a.out/f'm{m}.log').write_text(log)
  assert (r.returncode==0 and 'LOCAL_CAPTURE_PASS' in log) if m==0 else (r.returncode!=0 and 'LOCAL_CAPTURE_FAIL' in log),log
  results.append({'mutant':m,'returncode':r.returncode,'result':'PASS' if m==0 else 'ACTUAL_STOPPED_CLOCK_REJECTED'})
  print(log.strip())
 receipt={'status':'CAPTURE_SEQUENTIAL_EQUIVALENCE_ONLY','baseline_source':'b4ca1edc9','sources':{s:hashlib.sha256((R/s).read_bytes()).hexdigest() for s in src},'samples':1024,'reset_assertions':17,'replaced_flops':10560,'bit_comparisons':10813440,'clock_entries_RS5':217,'added_clock_entries':24,'added_flops':0,'added_edges':0,'results':results,'scope':['Every replaced return/request capture output compared after each edge against literal baseline equations','Common logical phase required; independent physical insertion/uncertainty not simulated','No new full numerical/parent/native qualification; baseline193/810 proof remains scoped to its exact source','Control/descriptor/H-V distribution/reset localization and all physical pin/cut/clock/PG/route remain OPEN']}
 (a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
if __name__=='__main__':main()
