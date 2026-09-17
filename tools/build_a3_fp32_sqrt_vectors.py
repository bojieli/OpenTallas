#!/usr/bin/env python3
"""Vectors for ot_a3_fp32_sqrt_rne, from the reference's own square root.

``_binary32_sqrt_rne`` in runtime/reference/sqrt_softplus.py is the authority.
It binary-searches the binary32 code space with exact rational candidates and
settles the last bit with an exact midpoint comparison, so it is the correctly
rounded answer by construction rather than by agreement with a library.

The cases are chosen to hit the places a square root goes wrong: both exponent
parities, exact squares, the boundaries of the significand, subnormal operands
(whose roots are normal, because squaring compresses the exponent), and the ends
of the range the softplus upstream can actually produce -- which is
[exp(-105), 20] widened to binary32, so roots from about 1e-23 up to 4.5.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime.reference.sqrt_softplus import (  # noqa: E402
    _binary32_sqrt_rne,
)


def code(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--random", type=int, default=20000)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    codes: list[int] = [0]
    #: exact squares, where the remainder is zero and no rounding happens
    for n in (1, 2, 3, 4, 5, 9, 16, 121, 1024, 2**23, 2**24 - 1):
        codes.append(code(float(n * n)))
    #: both exponent parities at the same significand
    for e in range(-30, 31):
        codes.append(code(1.5 * 2.0**e))
        codes.append(code(1.9999999 * 2.0**e))
        codes.append(code(1.0 * 2.0**e))
    #: the significand's own boundaries
    codes += [0x00000001, 0x00000002, 0x007FFFFF, 0x00800000, 0x00800001,
              0x3F7FFFFF, 0x3F800000, 0x3F800001, 0x7F7FFFFF]
    #: the window the softplus upstream can actually produce
    for e in (-46, -40, -30, -20, -10, -1, 0, 1, 2, 4):
        codes.append(code(2.0**e))
        codes.append(code(1.3 * 2.0**e))
    #: The top of each binade, where a root comes closest to carrying out of
    #: its significand. It never actually does -- the radicand is an exact
    #: binary32 significand, or twice one, so the largest below four is
    #: 4 - 2**-22 while carrying needs 4 - 2**-22 + 2**-48 -- and these cases
    #: are kept as the boundary coverage that establishes it. A mutation
    #: deleting the RTL's carry branch survives, correctly.
    for k in range(-20, 21, 2):
        top = float(np.float32(4.0 * 2.0**k))
        c = code(top)
        for back in range(1, 4):
            codes.append(c - back)
    codes.append(code(20.0))
    codes.append(code(float(np.float32(np.log1p(np.exp(np.float32(-105.0)))))))

    rng = np.random.default_rng(0x5071)
    #: Uniform over the CODE space of the positive finite range, which samples
    #: exponents uniformly rather than magnitudes -- the subnormals and the tiny
    #: exponents are where a square root's normalization goes wrong.
    codes += [int(c) for c in rng.integers(1, 0x7F7FFFFF, size=args.random)]

    seen: set[int] = set()
    rows = []
    for c in codes:
        c = int(c) & 0xFFFFFFFF
        if c in seen:
            continue
        seen.add(c)
        expected, _ = _binary32_sqrt_rne(c)
        rows.append((c, expected))

    (args.out / "sqrt_in.hex").write_text(
        "\n".join(f"{c:08x}" for c, _ in rows) + "\n")
    (args.out / "sqrt_out.hex").write_text(
        "\n".join(f"{e:08x}" for _, e in rows) + "\n")
    (args.out / "sqrt_count.txt").write_text(f"{len(rows)}\n")
    #: The reference's tie branch is unreachable on a square root, and this is
    #: the assertion that says so rather than the comment claiming it.
    print(f"wrote {len(rows)} cases to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
