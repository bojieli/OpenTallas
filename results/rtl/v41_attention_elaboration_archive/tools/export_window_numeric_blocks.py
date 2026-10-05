#!/usr/bin/env python3
"""Export same golden window128 FP8 rows to actual WINDOW blk producer format."""
import json,hashlib,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--vectors',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rows=[int(x,16) for x in (a.vectors/'window128/kv.hex').read_text().splitlines()]
assert len(rows)==128
blocks=[]
for row in rows:
 for group in range(16):
  x=(row>>(265*group))&((1<<265)-1)
  assert x>>264==0,'WINDOW must be FP8'
  blocks.append(x&((1<<264)-1))
f=a.out/'window_blocks264.hex';f.write_text(''.join(f'{x:066x}\n' for x in blocks))
(a.out/'manifest.json').write_text(json.dumps({'scope':'Same fullgeometrywindow128goldenKV as numericgate; 128rows x16blocks, low256codes+high8scale. Feed actualblkwrite port, noHBMpreload.','rows':128,'blocks':len(blocks),'block_hex_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'source_kv_sha256':hashlib.sha256((a.vectors/'window128/kv.hex').read_bytes()).hexdigest()},indent=2)+'\n')
