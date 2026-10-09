#!/usr/bin/env python3
"""Sparse copy of the released DeepSeek-V4.1-Flash checkpoint holding exactly the bytes one 1M reference token reads.

The full snapshot (476 GB) exists only on the workstation; the DS round-trip runs on an EPYC host.  This writes, for
every shard, a SPARSE file of the original size whose safetensors header is copied verbatim and whose data holds:
  * every tensor whole, except routed experts, the Engram tables, the token embedding and the MTP stages;
  * the routed experts the reference token selects in each layer (the W17 reference shards' `experts`);
  * the Engram table rows (codes + UE8M0 scales) the token history hashes to in each Engram layer;
  * the embedding row of the last history token.
Bytes never copied read as zero, so a read outside the set shows up as a golden mismatch, never a silent pass.

    python3 tools/hgi_sim/ckpt_subset.py --out DIR [--refs W17_SHARDS]     (then rsync -S DIR to the host)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--refs", type=Path, default=Path("/home/ubuntu/w17work/ref/ctx1048576_seed20260930"))
    a = ap.parse_args()
    import rtl_v41_fullshape_layer_campaign as LC
    import w19_hbm_tp96_isa as W
    snap = LC.HF
    idx = json.loads((snap / "model.safetensors.index.json").read_text())["weight_map"]
    ref = json.loads(W.REF_RECORD.read_text())
    hist = list(ref["token_history"])
    experts = {}
    for L in range(43):
        p = a.refs / f"ctx1048576_L{L:02d}.json"
        if p.exists():
            experts[L] = set(json.loads(json.loads(p.read_text())["experts"]) if isinstance(
                json.loads(p.read_text())["experts"], str) else json.loads(p.read_text())["experts"])
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=True)
    eng_rows = {}
    for li, L in enumerate(m.engram.layer_ids):
        ids = np.asarray(m.engram.hashes(hist, li)).reshape(-1)
        eng_rows[f"layers.{L}.engram.embed.weight"] = ids
        eng_rows[f"layers.{L}.engram.embed.scale"] = ids
    eng_rows["embed.weight"] = np.array([hist[-1]])
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "model.safetensors.index.json").write_bytes((snap / "model.safetensors.index.json").read_bytes())
    for fn in ("config.json", "tokenizer.json", "tokenizer_config.json", "inference"):
        if (snap / fn).exists() and (snap / fn).is_file():
            (a.out / fn).write_bytes((snap / fn).read_bytes())
    exp_re = re.compile(r"^layers\.(\d+)\.ffn\.experts\.(\d+)\.")
    total = 0
    for fn in sorted(set(idx.values())):
        src = snap / fn
        size = src.stat().st_size
        with open(src, "rb") as f:
            n = struct.unpack("<Q", f.read(8))[0]
            hdr = json.loads(f.read(n))
        base = 8 + n
        dst = a.out / fn
        with open(src, "rb") as fi, open(dst, "wb") as fo:
            fo.truncate(size)
            fi.seek(0)
            fo.write(fi.read(base))
            for name, meta in hdr.items():
                if name == "__metadata__" or name.startswith("mtp."):
                    continue
                s, e = meta["data_offsets"]
                mo = exp_re.match(name)
                if mo and int(mo.group(2)) not in experts.get(int(mo.group(1)), set()):
                    continue
                if name in eng_rows:
                    shape, dt = meta["shape"], meta["dtype"]
                    w = {"BF16": 2, "F32": 4, "F8_E4M3": 1, "F8_E8M0": 1}[dt] * shape[1]
                    for r in sorted(set(int(x) for x in eng_rows[name])):
                        fi.seek(base + s + r * w)
                        fo.seek(base + s + r * w)
                        fo.write(fi.read(w))
                        total += w
                    continue
                fi.seek(base + s)
                fo.seek(base + s)
                left = e - s
                while left:
                    buf = fi.read(min(left, 1 << 26))
                    fo.write(buf)
                    left -= len(buf)
                total += e - s
        print(f"{fn}: {total / 1e9:.2f} GB so far", flush=True)
    (a.out / "SUBSET.json").write_text(json.dumps(dict(
        source=str(snap), bytes_copied=total, experts={str(k): sorted(v) for k, v in experts.items()},
        engram_rows={k: sorted(set(int(x) for x in v)) for k, v in eng_rows.items()}), indent=1) + "\n")


if __name__ == "__main__":
    main()
