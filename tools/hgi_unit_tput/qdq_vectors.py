#!/usr/bin/env python3
"""FUSED.QDQ_* throughput vectors (hgi-1010/g): several back-to-back records with the real DS-V4.1 1M per-die record
shapes, the released golden (hdc_golden_v41.qdq_*), and the simulator's price of each record
(hgi_sim.ds_native_timing.NativeCost: ceil(n / 32) + 8).

Shapes (results/arch/hgi_sim_20261009/programs/ds_v41_1M_L{00,20}_per_die.json traces):
  kv_row_qdq   FUSED.QDQ_FP8        A VM FP32 n 512 m 1 -> O VM FP32 n 512   every die, every layer
  cmp.ik_qdq   FUSED.QDQ_FP4_E8M0   A VM FP32 n 128     -> O VM FP32         compressor die (rank 31), CSA layers
  cmp.ckv_qdq  FUSED.QDQ_FP4_E4M3   A VM FP32 n 512     -> O VM FP32         compressor die (rank 31), CSA layers
Record 0's input is the REAL L0 kv row of the exported simulator run (exp_gf ds_L0 vm_final words 51,776..52,287) and
its golden is cross-checked against the simulator's own output words 52,288..52,799.  Each record k's operands sit at
the production base + k * 4096 words (sector alignment and bank phase unchanged) so the records' inputs can all be
preloaded.

    python3 tools/hgi_unit_tput/qdq_vectors.py --vm-final ds_L0_vm_final.bin --out DIR
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import hdc_golden_v41 as G  # noqa: E402
from hgi_sim.ds_native_timing import NativeCost  # noqa: E402
import hgi_qdq_vectors as CF  # noqa: E402

OPS = {"QDQ_FP8": (4, 32, G.qdq_fp8), "QDQ_FP4_E8M0": (5, 32, G.qdq_fp4_e8m0), "QDQ_FP4_E4M3": (6, 16, G.qdq_fp4_e4m3)}
# (tag, op, A base, n, O base, data)
RECS = [("L0 kv_row_qdq (real)", "QDQ_FP8", 51776, 512, 52288, "real"),
        ("L20 kv_row_qdq", "QDQ_FP8", 51776, 512, 52288, "normal"),
        ("L20 cmp.ik_qdq", "QDQ_FP4_E8M0", 185024, 128, 185664, "normal"),
        ("L20 cmp.ckv_qdq", "QDQ_FP4_E4M3", 185152, 512, 185792, "normal"),
        ("kv_row_qdq CF corners", "QDQ_FP8", 51776, 512, 52288, "corners"),
        ("cmp.ckv_qdq CF corners", "QDQ_FP4_E4M3", 185152, 512, 185792, "corners"),
        ("L40 kv_row_qdq", "QDQ_FP8", 51776, 512, 52288, "normal"),
        ("L40 cmp.ik_qdq", "QDQ_FP4_E8M0", 185024, 128, 185664, "normal")]


def price(op, n):
    r = SimpleNamespace(unit="FUSED", op=op, desc={"A": SimpleNamespace(n=n)})
    return NativeCost.__call__(None, r, None, 0)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vm-final", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=20261010)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    vm = np.fromfile(a.vm_final, dtype=np.uint32)
    rng = np.random.default_rng(a.seed)
    lines, meta = [], []
    for k, (tag, op, ab, n, ob, kind) in enumerate(RECS):
        code, block, gold = OPS[op]
        if kind == "real":
            x = vm[ab:ab + n].view(np.float32).copy()
        elif kind == "normal":
            x = (rng.standard_normal(n) * rng.uniform(0.05, 4.0)).astype(np.float32)
        else:
            rows = [v for _, v in CF.cases(block, a.seed)]
            x = np.concatenate([rows[(i * 7) % len(rows)] for i in range(n // 32)]).astype(np.float32)
        with np.errstate(over="ignore", under="ignore", invalid="raise"):
            y = gold(x.copy(), block=block)
        yb = G.bits(y).astype(np.uint32)
        assert not (yb & 0xFFFF).any(), "QDQ output must be BF16-valued"
        if kind == "real":
            assert (yb == vm[ob:ob + n]).all(), "golden != the simulator's output words"
        abk, obk = ab + 4096 * k, ob + 4096 * k
        xb = G.bits(x).astype(np.uint32)
        (a.out / f"in_{k}.hex").write_text("".join(
            "".join(f"{int(w):08x}" for w in reversed(xb[s:s + 8])) + "\n" for s in range(0, n, 8)))
        (a.out / f"out_{k}.hex").write_text("".join(
            "".join(f"{int(w):08x}" for w in reversed(yb[s:s + 8])) + "\n" for s in range(0, n, 8)))
        c = price(op, n)
        lines.append(f"{code} {n} {abk} {obk} {int(round(c))} {block}")
        meta.append(dict(k=k, tag=tag, op=op, op_idx=code, n=n, a_base=abk, o_base=obk, cost=c, data=kind,
                         production_a_base=ab, production_o_base=ob))
    (a.out / "recs.txt").write_text(f"{len(RECS)}\n" + "\n".join(lines) + "\n")
    (a.out / "meta.json").write_text(json.dumps(dict(records=meta, seed=a.seed), indent=1) + "\n")
    print(json.dumps(dict(status="PASS", records=len(RECS))))


if __name__ == "__main__":
    main()
