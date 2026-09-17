#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_qk_walk.sv``, from the contract's own add.

The QK contract is ONE FUSED product-add per reduction step, which the reference
states through its repair path: where its two-ufunc schedule may differ it calls
``_single_rounded_add(accumulator, q, k)`` -- one rounding of ``acc + q*k``. This
generator computes the expectation that way, exactly, with Python's arbitrary
precision doing the product before a single binary32 rounding, so the answer is
the contract and not numpy's schedule.

The scale multiply afterwards is one further rounding -- ``np.multiply(scores,
scale)`` -- and is applied as such, not folded into the last MAC.

``ascending_matters`` is built so a DESCENDING reduction order gives a different
score, and the manifest records whether it does. Without such a case the test
would pass on any order, and the order is the part of this contract that a
reimplementation is most likely to change.
"""

from __future__ import annotations

import argparse
import struct
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LANES = 64
KV_ROWS = 256


def bf16(x) -> np.uint16:
    raw = np.float32(x).view(np.uint32)
    return np.uint16((int(raw) + 0x7FFF + ((int(raw) >> 16) & 1)) >> 16)


def widen(code) -> np.float32:
    return np.array([int(code) << 16], dtype=np.uint32).view(np.float32)[0]


def rn32(value: Fraction) -> np.float32:
    """Round an exact rational to binary32, ties to even."""
    return np.float32(float(value)) if value == 0 else _rn32(value)


def _rn32(value: Fraction) -> np.float32:
    #: float() on a Fraction rounds to binary64 correctly, and every quantity
    #: here is a sum of BF16 products, whose exact value needs at most ~40 bits
    #: of significand -- well inside binary64 -- so one binary64 step then one
    #: binary32 step is exact. Asserted below rather than assumed.
    wide = float(value)
    assert Fraction(wide) == value, "intermediate does not fit binary64 exactly"
    return np.float32(wide)


def fused_dot(q_codes, k_codes) -> np.float32:
    """acc = RN(acc + q[d]*k[d]) for d ascending -- the contract, step by step."""
    acc = np.float32(0.0)
    for qc, kc in zip(q_codes, k_codes):
        exact = Fraction(float(widen(qc))) * Fraction(float(widen(kc)))
        acc = _rn32(Fraction(float(acc)) + exact)
    return acc


def case_inputs(name: str, seed: int, head_dim: int):
    rng = np.random.default_rng(seed)
    q = np.array([bf16(v) for v in rng.uniform(-2.0, 2.0, size=head_dim)],
                 dtype=np.uint16)
    kv = np.array([[bf16(v) for v in rng.uniform(-2.0, 2.0, size=head_dim)]
                   for _ in range(KV_ROWS)], dtype=np.uint16)
    rows = rng.integers(0, KV_ROWS, size=LANES).astype(np.uint32)
    valid = np.ones(LANES, dtype=bool)
    scale = np.float32(0.08838835)          # 1/sqrt(128), the shipped shape
    if name == "typical":
        return q, kv, rows, valid, scale
    if name == "padding_lanes":
        valid[9:] = False
        return q, kv, rows, valid, scale
    if name == "duplicate_rows":
        rows[:] = np.uint32(5)
        return q, kv, rows, valid, scale
    if name == "ascending_matters":
        #: One large term and many tiny ones: summed ascending the tiny terms
        #: accumulate before the large one arrives, and descending they are lost.
        q = np.array([bf16(1.0)] + [bf16(np.ldexp(1.0, -12))] * (head_dim - 1),
                     dtype=np.uint16)
        kv = np.array([[bf16(1.0)] + [bf16(np.ldexp(1.0, -12))] * (head_dim - 1)]
                      * KV_ROWS, dtype=np.uint16)
        return q, kv, rows, valid, np.float32(1.0)
    if name == "unit_scale":
        return q, kv, rows, valid, np.float32(1.0)
    if name == "short_depth":
        return q, kv, rows, valid, scale
    raise AssertionError(name)


CASES = (
    ("typical", 11, 128),
    ("padding_lanes", 13, 128),
    ("duplicate_rows", 17, 128),
    ("ascending_matters", 0, 64),
    ("unit_scale", 23, 32),
    ("short_depth", 29, 4),
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    lines = [str(len(CASES)), str(KV_ROWS)]
    order_notes = []
    for index, (name, seed, head_dim) in enumerate(CASES):
        q, kv, rows, valid, scale = case_inputs(name, seed, head_dim)
        scores = np.zeros(LANES, dtype=np.float32)
        for lane in range(LANES):
            k_codes = (kv[int(rows[lane])][:head_dim] if valid[lane]
                       else np.zeros(head_dim, dtype=np.uint16))
            dot = fused_dot(q[:head_dim], k_codes)
            scores[lane] = np.float32(np.multiply(dot, scale, dtype=np.float32))
        #: Does a descending reduction give a different answer here?
        desc = fused_dot(q[:head_dim][::-1], kv[int(rows[0])][:head_dim][::-1])
        asc = fused_dot(q[:head_dim], kv[int(rows[0])][:head_dim])
        differs = bool(np.float32(desc).view(np.uint32) !=
                       np.float32(asc).view(np.uint32))
        order_notes.append((name, differs))

        (args.out / f"q_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in q[:head_dim]) + "\n")
        (args.out / f"kv_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in kv[:, :head_dim].reshape(-1)) + "\n")
        (args.out / f"rows_{index}.hex").write_text(
            "\n".join(f"{int(r):08x}" for r in rows) + "\n")
        (args.out / f"scores_{index}.hex").write_text(
            "\n".join(f"{int(c):08x}" for c in scores.view(np.uint32)) + "\n")
        mask = "".join("1" if v else "0" for v in valid[::-1])
        lines.append(f"{name} {head_dim} {int(np.float32(scale).view(np.uint32)):08x} {mask}")

    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    assert any(d for _, d in order_notes), (
        "no case distinguishes ascending from descending reduction; the suite "
        "would pass on the wrong association")
    print(f"wrote {len(CASES)} cases to {args.out}")
    for name, differs in order_notes:
        print(f"   {name:20s} descending order differs: {differs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
