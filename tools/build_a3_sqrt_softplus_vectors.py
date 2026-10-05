#!/usr/bin/env python3
"""Vectors for ot_a3_vector_sqrt_softplus, from the reference itself.

``binary32_sqrt_softplus_rne_with_diagnostics`` in
runtime/reference/sqrt_softplus.py is the authority for the whole operator: it
evaluates log(1+exp(x)) with exact rational interval enclosures, refines until
both outward endpoints land in one binary32 rounding cell, and then correctly
rounds the square root of that already-rounded softplus. No host floating point,
libm call, or answer table participates in producing these expectations.

Each case also carries the BRANCH the reference took, so the device is checked
for taking the same one rather than only for agreeing on the value -- the
linear-threshold and proved-underflow branches return exactly right answers by
construction, so a device that reached them by accident would still look
correct on the value alone.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.reference.sqrt_softplus import (  # noqa: E402
    binary32_sqrt_softplus_rne_with_diagnostics as diagnostics,
)

BRANCH_CODE = {
    "linear_threshold": 0,
    "proved_underflow_zero": 1,
    "transcendental": 2,
}


def code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--random", type=int, default=900)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    values: list[float] = [0.0, -0.0]
    #: The two branch boundaries, from both sides. 20 itself is transcendental
    #: because the threshold branch is STRICT, and -105 itself underflows
    #: because that cutoff is not.
    for v in (20.0, -105.0):
        c = code(v)
        values += [struct.unpack("<f", struct.pack("<I", c + d))[0]
                   for d in (-2, -1, 0, 1, 2)]
    #: A spread across the transcendental interior, both signs.
    values += list(np.linspace(-104.5, -0.5, 120).astype(np.float32))
    values += list(np.linspace(-0.5, 19.9, 80).astype(np.float32))
    #: Where softplus is subnormal -- the deep tail, which is the part a
    #: fixed-point evaluation gets wrong first.
    values += list(np.linspace(-104.9, -86.0, 60).astype(np.float32))
    #: The linear branch and the underflow branch.
    values += [20.5, 21.0, 30.0, 100.0, 1e10, 3.4e38]
    values += [-105.5, -110.0, -200.0, -1e10, -3.4e38]
    #: Tiny magnitudes, where softplus is log(2) plus a hair.
    for e in range(-30, 0, 3):
        values += [2.0**e, -(2.0**e)]

    rng = np.random.default_rng(0x50F7)
    values += list(rng.uniform(-105.0, 21.0, args.random).astype(np.float32))

    seen: set[int] = set()
    rows = []
    branches: dict[int, int] = {}
    for v in values:
        c = code(float(v))
        if c in seen:
            continue
        seen.add(c)
        result = diagnostics(c)
        branch = BRANCH_CODE[result.softplus_branch]
        branches[branch] = branches.get(branch, 0) + 1
        rows.append((c, result.output_binary32_code, branch,
                     result.softplus_binary32_code))

    (args.out / "sp_in.hex").write_text(
        "\n".join(f"{c:08x}" for c, _, _, _ in rows) + "\n")
    (args.out / "sp_out.hex").write_text(
        "\n".join(f"{o:08x}" for _, o, _, _ in rows) + "\n")
    (args.out / "sp_branch.hex").write_text(
        "\n".join(f"{b:08x}" for _, _, b, _ in rows) + "\n")
    (args.out / "sp_softplus.hex").write_text(
        "\n".join(f"{s:08x}" for _, _, _, s in rows) + "\n")
    (args.out / "sp_count.txt").write_text(f"{len(rows)}\n")

    #: Every branch must actually appear, or the suite silently tests one path.
    for name, value in BRANCH_CODE.items():
        assert branches.get(value, 0) > 0, f"no case took the {name} branch"
    subnormal = sum(1 for _, _, _, s in rows if (s >> 23) & 0xFF == 0 and s != 0)
    print(f"wrote {len(rows)} cases to {args.out}")
    print(f"  branches: {branches}")
    print(f"  cases whose softplus is subnormal: {subnormal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
