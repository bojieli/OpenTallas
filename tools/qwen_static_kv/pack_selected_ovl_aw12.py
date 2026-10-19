#!/usr/bin/env python3
"""Pack selected model list words into the actual4096x72 mux8 via-mask geometry.
This packages model data only; it does not certify the unresolved cold-prefix ABI.
"""
import argparse, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("model",type=Path);p.add_argument("out",type=Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r={"schema":"opentallas.kv-ovl-aw12-pack.v1","production_bound":False,"model_provenance":"codex/sysface-ovl-1019 e794853e1 selected_F16_origin0_model","files":{}}
for direction in ["tx","rx"]:
 src=a.model/f"list_K_{direction}.memh";v=[int(x,16) for x in src.read_text().split()]
 assert len(v)==3260 and all(0<=x<2**32 for x in v)
 rows=[0]*512
 for addr,word in enumerate(v):
  for b in range(32):
   if (word>>b)&1:rows[addr//8]|=1<<(b*8+addr%8)
 text="".join(f"{x:0144x}\n" for x in rows)
 # Decode the packed physical cells independently to prove row/column bit orientation.
 for addr in range(4096):
  decoded=sum(((rows[addr//8]>>(b*8+addr%8))&1)<<b for b in range(72))
  assert decoded==(v[addr] if addr<len(v) else 0)
 dst=a.out/f"ovl_k_{direction}.viamap.hex";dst.write_text(text)
 r["files"][direction]={"logical_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"physical_sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),"words":len(v),"decode_checked":4096}
(a.out/"pack_receipt.json").write_text(json.dumps(r,indent=2)+"\n")
