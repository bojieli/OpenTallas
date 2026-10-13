#!/usr/bin/env python3
"""Compact byte-exact safetensors subset of one released shard: the HC rows and norm weights of one layer (same tensor set as
shard4_subset_provenance.json, layer 1).  Needed only because the DSpark stage lowering prefetches layers.((40+st+1) % 40)."""
import json, struct, sys, hashlib
from pathlib import Path
snap, L, shard, out = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
names = [f"layers.{L}.{n}" for n in ("hc_attn_base", "hc_attn_fn", "hc_attn_scale", "hc_ffn_base", "hc_ffn_fn", "hc_ffn_scale",
                                      "attn.kv_norm.weight", "attn.q_norm.weight", "attn_norm.weight", "ffn_norm.weight")]
src = snap / shard
with open(src, "rb") as f:
    n = struct.unpack("<Q", f.read(8))[0]
    raw = f.read(n)
    hdr = json.loads(raw)
    base = 8 + n
    new, blobs, off, prov = {}, [], 0, {}
    for k in names:
        m = hdr[k]
        s, e = m["data_offsets"]
        f.seek(base + s)
        b = f.read(e - s)
        new[k] = dict(dtype=m["dtype"], shape=m["shape"], data_offsets=[off, off + len(b)])
        prov[k] = dict(dtype=m["dtype"], shape=m["shape"], source_offsets=[s, e], sha256=hashlib.sha256(b).hexdigest())
        blobs.append(b)
        off += len(b)
h = json.dumps(new, separators=(",", ":")).encode()
h += b" " * (-len(h) % 8)
data = struct.pack("<Q", len(h)) + h + b"".join(blobs)
(out / shard).write_bytes(data)
json.dump(dict(snapshot=snap.name, source_shard=shard, source_header_sha256=hashlib.sha256(raw).hexdigest(),
               subset_sha256=hashlib.sha256(data).hexdigest(), subset_bytes=len(data), tensors=prov),
          open(out / f"shard{int(shard[6:11])}_subset_provenance.json", "w"), indent=2)
print(shard, len(data), hashlib.sha256(data).hexdigest())
