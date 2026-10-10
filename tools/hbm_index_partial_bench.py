#!/usr/bin/env python3
"""Measure actual odd-block port/credit behavior; preserve failure evidence."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['physical/hbm_accel_die_views/svc/rtl/ot_hbm_index_lines.sv','rtl/test/hbm_accel/tb_hbm_index_partial.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
 rec=dict(source_commit=os.environ['PINNED_SOURCE_COMMIT'],input_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},scope='actual behavioral assembler final partial-group valid and real credit debt; no physical adoption',cases=[],verdict='INCOMPLETE');out=a.work/'record.json'
 def save():out.write_text(json.dumps(rec,indent=2)+'\n')
 save()
 for blocks in [2,1,3]:
  exe=a.work/f'blocks{blocks}.vvp'
  with (a.work/f'blocks{blocks}.build.log').open('w') as log:cp=subprocess.run(['iverilog','-g2012','-s','tb_hbm_index_partial',f'-Ptb_hbm_index_partial.BLOCKS={blocks}','-o',str(exe)]+[str(ROOT/s) for s in SRC],stdout=log,stderr=subprocess.STDOUT)
  row=dict(blocks=blocks,build_exit=cp.returncode,passed=False)
  if cp.returncode==0:
   lp=a.work/f'blocks{blocks}.run.log'
   with lp.open('w') as log:cp=subprocess.run(['vvp',str(exe)],stdout=log,stderr=subprocess.STDOUT)
   raw=lp.read_text();row.update(run_exit=cp.returncode,passed=cp.returncode==0 and 'PASS_INDEX_PARTIAL' in raw,spurious_line_observed='SPURIOUS_PARTIAL_LINE' in raw,raw_sha256=hashlib.sha256(lp.read_bytes()).hexdigest())
  rec['cases'].append(row);save()
 rec['verdict']='PASS' if all(c['passed'] for c in rec['cases']) else 'FAIL';save();print(rec['verdict']);return int(rec['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
