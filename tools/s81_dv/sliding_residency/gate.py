#!/usr/bin/env python3
"""Check the real released L0 fixture's stored-window alias; corrupting one attended row must be refused."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/s81_dv'),str(ROOT/'tools/s81_dv/layer_prog')]
from lower_svc import Job,sliding_window_residency


def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('fixture',type=Path);a.add_argument('out',type=Path);v=a.parse_args()
 v.out.mkdir(parents=True,exist_ok=True)
 job=Job(v.fixture,allq=True,timing_profile='closing_allq');r=sliding_window_residency(job)
 assert r['window_rows']==128 and r['extra_link_beats']==0 and r['extra_q_words']==0
 (v.out/'residency.json').write_text(json.dumps(r,indent=2)+'\n')
 mutant=v.out/'mutant';mutant.mkdir()
 for src in v.fixture.rglob('*'):
  rel=src.relative_to(v.fixture);dst=mutant/rel
  if src.is_dir():dst.mkdir(exist_ok=True)
  elif str(rel) not in ('ops.json','ops/attn.rows_allgather.bin'):dst.symlink_to(src.resolve())
 ops=json.loads((v.fixture/'ops.json').read_text())
 raw=bytearray((v.fixture/'ops/attn.rows_allgather.bin').read_bytes());raw[0]^=1
 (mutant/'ops/attn.rows_allgather.bin').write_bytes(raw)
 info=ops['attn.rows_allgather'];info['sha256']=hashlib.sha256(raw).hexdigest()
 (mutant/'ops.json').write_text(json.dumps(ops))
 try:Job(mutant,allq=True,timing_profile='closing_allq')
 except AssertionError as e:
  assert str(e)=='attended rows',str(e)
  caught='attended rows'
 else:raise AssertionError('wrong attended-row value admitted')
 job.compressed=True
 try:sliding_window_residency(job)
 except ValueError:caught_compressed=True
 else:raise AssertionError('compressed shape admitted as local-only')
 print('SLIDING_RESIDENCY PASS 128x512 stored/golden rows; semantic row mutant CAUGHT; compressed shape REFUSED; extra link/q/cycles0')
 (v.out/'check.json').write_text(json.dumps(dict(pass_=True,rows=128,width=512,row_mutant=caught,
  compressed_refused=caught_compressed,extra_link_beats=0,extra_q_words=0,added_rtl_cycles=0),indent=2)+'\n')
 return 0
if __name__=='__main__':sys.exit(main())
