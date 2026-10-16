#!/usr/bin/env python3
"""hgi-e2e (hgi-1010/g): the HC weight sets the REAL HC unit (ot_hgi_hc_unit) reads, for every HC record of an export.

The simulator (hgi_sim.ds_native hc_mix / hc_mix_rows / hc_mix_post) takes hc_{attn,ffn}_{fn,scale,base} from the
checkpoint by NAME (B.base only names the layer's set), and the compiler allocates the set as a 1-element BF16
placeholder (ds_native: self.W(f"{P}hc_{w}", 1, 1, "bf16")), so the exported HBM holds no weight set in the unit's
format.  This tool writes it: per HC record, the ot_hgi_hc_unit weight-set image at sector S0 = B.base >> 5
(W = 32: scale[0..2] at words 0..2 and base[0..23] at words 8..31 of sectors S0..S0+3; fn row o, bank k, word r at
sector S0 + 4 + (8 o + k) RS + r SPW), only the sectors the record reads (HC_MIX_POST: the 4 scale / base sectors;
HC_MIX_ROWS: its rows; HC_MIX: all).  The harness serves the HC unit's HBM lane from this map (hcw.bin
{u64 sector, 32 B}), separate from hbm.bin, because the compiler's placeholder does not reserve the set's span.

    python3 tools/hgi_e2e/hc_weights.py EXPORT_DIR --ckpt SNAPSHOT_DIR [--w 32]
"""
import argparse
import json
import struct
from pathlib import Path

import numpy as np


def tensor(ckpt, name):
    from safetensors import safe_open
    idx = json.loads((ckpt / "model.safetensors.index.json").read_text())["weight_map"] \
        if (ckpt / "model.safetensors.index.json").exists() else None
    files = [ckpt / idx[name]] if idx and name in idx else sorted(ckpt.glob("*.safetensors"))
    for f in files:
        with safe_open(str(f), "np") as s:
            if name in s.keys():
                return s.get_tensor(name).astype(np.float32)
    raise KeyError(name)


def weight_set(fn, scale, base, s0, W, rows):
    K = fn.shape[1]
    nchunk = K // 8
    R = -(-nchunk // W)
    SPW = W // 8
    RS = R * SPW
    out = {}
    pv = np.zeros(32, np.float32)
    pv[0:3] = scale
    pv[8:32] = base
    pw = pv.view(np.uint32)
    for s in range(4):
        out[s0 + s] = pw[8 * s:8 * s + 8].astype("<u4").tobytes()
    for row in rows:
        for k in range(8):
            flat = np.zeros(R * W, np.float32)
            flat[:nchunk] = fn[row, 8 * np.arange(nchunk) + k]
            lanes = flat.view(np.uint32).reshape(R, W)
            for r in range(R):
                for s in range(SPW):
                    out[s0 + 4 + (8 * row + k) * RS + r * SPW + s] = lanes[r, 8 * s:8 * s + 8].astype("<u4").tobytes()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export", type=Path)
    ap.add_argument("--ckpt", type=Path, required=True)
    ap.add_argument("--w", type=int, default=32)
    a = ap.parse_args()
    meta = json.loads((a.export / "meta.json").read_text())
    L = meta["layer"]
    secs, log = {}, []
    for r in meta["records"]:
        if r["unit"] != "HC":
            continue
        which = "attn" if r["tag"].startswith("hc_attn") else "ffn"
        pre = f"layers.{L}.hc_{which}_"
        fn, scale, base = (tensor(a.ckpt, pre + x) for x in ("fn", "scale", "base"))
        s0 = r["eff"]["B"][0] >> 5
        if r["op"] == "HC_MIX_POST":
            rows = []
        elif r["op"] == "HC_MIX_ROWS":
            lo = (int(r["hdr"], 16) >> 32) & 0xFFFFFFFF        # header imm_a (bits 63:32): the first row
            rows = range(lo, lo + r["eff"]["O"][1])
        else:
            rows = range(24)
        ws = weight_set(fn, scale, base, s0, a.w, rows)
        secs.update(ws)
        log.append(dict(k=r["k"], op=r["op"], tag=r["tag"], s0=s0, sectors=len(ws)))
    with open(a.export / "hcw.bin", "wb") as f:
        for s in sorted(secs):
            f.write(struct.pack("<Q", s) + secs[s])
    (a.export / "hcw.json").write_text(json.dumps(dict(w=a.w, records=log, sectors=len(secs)), indent=1) + "\n")
    print(json.dumps(dict(records=len(log), sectors=len(secs))))


if __name__ == "__main__":
    main()
