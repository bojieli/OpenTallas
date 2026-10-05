#!/usr/bin/env python3
"""Offline lossless restore and independent replay; never launch a simulator."""
import argparse,gzip,json
from pathlib import Path
from qwen_rom_program_identity import ROOT,sha
from qwen_rom_atomic_request_headers import extract
from qwen_rom_L0_terminal_source_gate import gate
from qwen_rom_source_observer_replay import replay

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--packet',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(exist_ok=False)
 for name,want in json.loads((a.packet/'source-input-pins-r1.json').read_text()).items():
  if sha((ROOT/name).read_bytes())!=want:raise ValueError('source/input pin '+name)
 index=json.loads((a.packet/'archive-index-r1.json').read_text())
 for name,row in index.items():
  if Path(name).name!=name or name in ('.','..'):raise ValueError('archive basename')
  compressed=(a.packet/(name+'.gz')).read_bytes()
  if sha(compressed)!=row['artifact_sha256']:raise ValueError('compressed archive pin '+name)
  raw=gzip.decompress(compressed)
  if len(raw)!=row['bytes'] or sha(raw)!=row['sha256']:raise ValueError('lossless original archive pin '+name)
  (a.out/name).write_bytes(raw)
 bundle=json.loads(gzip.decompress((ROOT/'results/uarch/qwen_rom_program_identity_20261002/retained-reproduction-final.json.gz').read_bytes()))
 # Independently preserve the full return failure: never accept it as source PASS.
 try:
  with (a.out/'accepted-state.raw').open() as f:replay(bundle,f,require_reads=True,layers=1)
 except ValueError as e:
  if str(e)!='actual16lane source KV read width':raise
 else:raise ValueError('expected pinned return formatting FAIL was not reproduced')
 result=extract(bundle,(a.out/'accepted-state.raw').read_bytes())
 if result!=json.loads((a.out/'source-request-only-r1.json').read_text()):raise ValueError('independent source-request receipt differs')
 terminal=gate(a.out,result)
 if terminal!=json.loads((a.packet/'terminal-review-r1.json').read_text()):raise ValueError('independent terminal review differs')
 (a.out/'independent-source-only-replay.json').write_text(json.dumps(terminal,indent=2,sort_keys=True)+'\n')
 print(terminal['status'])
if __name__=='__main__':main()
