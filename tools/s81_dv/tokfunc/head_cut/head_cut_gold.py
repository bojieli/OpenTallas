#!/usr/bin/env python3
"""RTLGAP2-HEADTB (10-21): per-tile goldens for the head-die cut TB (CUT-A).

From the golden logits of the 1M-context token (DSROM_1M_HEAD_REF npz: xf + logits over all 129,280 rows, the same
reference head_die_images.py used for the ROM images) and the die's tile straps (tiles.txt "<INSTANCE> <row0> <ten>",
rank-0 rowbase 0) this writes, per tile, OUT/lg/<INSTANCE>.hex (the 128 golden FP32 logits of rows row0 .. row0+127 in
local row order) and OUT/tiles_gold.txt "<INSTANCE> <row0> <argmax row> <bits>" (lowest id on ties), plus the
die-level argmax of the held rows (must equal golden.json local).

    python3 head_cut_gold.py --ref ctx1048576_head.npz --tiles tiles.txt --golden img/golden.json --out OUT
"""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--golden", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rowbase", type=int, default=0)
    a = ap.parse_args()
    z = np.load(a.ref)
    lg = np.asarray(z["logits"], dtype=np.float32)
    u = lg.view(np.uint32)
    out = Path(a.out); (out / "lg").mkdir(parents=True, exist_ok=True)
    g = json.load(open(a.golden))
    rows = []
    best = None
    for ln in Path(a.tiles).read_text().split("\n"):
        if not ln.strip():
            continue
        inst, r0, ten = ln.split()
        r0 = a.rowbase + int(r0)
        seg = lg[r0:r0 + 128]
        assert len(seg) == 128 and not np.isnan(seg).any()
        k = int(np.argmax(seg))           # first (lowest id) maximum
        (out / "lg" / f"{inst}.hex").write_text("".join(f"{int(v):08x}\n" for v in u[r0:r0 + 128]))
        rows.append(f"{inst} {r0} {r0 + k} {int(u[r0 + k]):08x}")
        if ten.endswith("1") and (best is None or seg[k] > best[1] or (seg[k] == best[1] and r0 + k < best[0])):
            best = (r0 + k, seg[k], int(u[r0 + k]))
    (out / "tiles_gold.txt").write_text("\n".join(rows) + "\n")
    assert best[0] == g["local"]["row"] and f"{best[2]:08x}" == g["local"]["bits"], (best, g["local"])
    print(json.dumps(dict(tiles=len(rows), die_local_row=best[0], die_local_bits=f"{best[2]:08x}", golden_local=g["local"])))


if __name__ == "__main__":
    main()
