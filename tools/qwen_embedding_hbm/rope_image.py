#!/usr/bin/env python3
"""Canonical 4MiB RoPE HBM table. Source: dv_lower_vec.rope_words@6ff5be90f.
Logical E is appended after old scale sectors. One pseudo row packs eight positions.
"""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/qwen_layerbench'))
from dv_lower_vec import rope_words
E_ROPE=19457304

def write(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 payload=out/'rope_fp32_pairs.bin'
 with payload.open('xb') as f:
  for pos in range(8192):
   for word in rope_words(pos):f.write((word&((1<<512)-1)).to_bytes(64,'little'))
 raw=payload.read_bytes()
 (out/'rope_manifest.json').write_text(json.dumps(dict(schema='opentallas.qwen-rope-hbm.v1',
  file=payload.name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),positions=8192,pairs=64,
  source='tools/qwen_layerbench/dv_lower_vec.py:rope_words@6ff5be90f',pseudo_id_base=151936,
  logical_sector_base=E_ROPE,sectors=131072,physical_row_offset=149,
  layout='position*512+k*64;512b eight64b {sinhi32,coslo32};pseudoID151936+pos//8,rowword(pos%8)*8+k'),indent=1)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);write(p.parse_args().out)
