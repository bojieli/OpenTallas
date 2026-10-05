#!/usr/bin/env python3
"""MTP verify (P = 6) vectors at the real 1M shapes for the streaming attention engine, in model row order
(tools/w11_attn_verify6.py vectors_model, the dshbm_verify_tile_batch bench): 'full' = compressed/indexed layers
(T = 640: 128 window + 512 selected rows per position) and 'full128' = sliding-window layers (T = 128, window only).
Run the vectors with `python3 tools/w11_attn_verify6.py run --exe <full-geometry _s build> --vectors D --ilv 1
--l0 0 --l0 188 --l0 218 --out R.json` (build: tools/hbm_fmax_attn_full.py --pwords 2 --param NJOBMAX=6 ...).

    python3 tools/hbm_fmax_attn_verify6.py --cfg full128 --out DIR
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import w11_attn_verify6 as V  # noqa: E402

V.CFGS["full128"] = dict(H=16, D=512, TD=32, NL=4, TROWS=640, TMAX=128, WIN=128)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", choices=("full", "full128"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    print(json.dumps(V.vectors_model(a.cfg, a.out)["counts"]))
