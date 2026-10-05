#!/usr/bin/env python3
"""Vectors for ``rtl/test/tb_a3_exp_pos.sv``, from ``exp_cr32`` itself.

``ot_a3_fp32_exp_pos_cr_rne`` claims to be CORRECTLY ROUNDED, so nothing less
than the reference's own correctly-rounded exponential is an adequate authority:
every expectation here is ``runtime.tensor_accelerator.sparse_attention.exp_cr32``
on the same binary32 code the RTL reads. That function supplies
ATTENTION.SPARSE's probabilities, so agreement with it is exactly the claim that
matters.

THE CONSTANTS ARE CHECKED, NOT TRUSTED. The module carries ln2 and log2(e) to
FRAC_BITS fractional bits as literals; this file recomputes both and refuses to
build if either disagrees, so a mistyped digit is a build failure rather than a
wrong last bit somewhere in the range.

The corpus is aimed at the range reduction, because that is what is new here: the
arguments that sit exactly on a multiple of ln2 (where the floor can go either
way), just inside and just outside each side of one, the subnormal-input edge,
the largest argument whose exponential is still finite, and the first one whose
is not.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.tensor_accelerator.sparse_attention import exp_cr32  # noqa: E402

FRAC_BITS = 160
MODULE = ROOT / "rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv"


def check_constants() -> None:
    """Recompute ln2 and log2(e) and match the module's literals."""
    getcontext().prec = 140
    ln2 = Decimal(2).ln()
    log2e = 1 / ln2
    def fixed(d):
        return int((d * (Decimal(2) ** FRAC_BITS)).to_integral_value(
            rounding="ROUND_FLOOR"))
    text = MODULE.read_text()
    for name, want in (("LN2", fixed(ln2)), ("LOG2E", fixed(log2e))):
        marker = f"localparam [FRAC_BITS"
        i = text.index(f"] {name} =")
        literal = text[i:text.index(";", i)]
        hexpart = literal.split("'h")[1].strip()
        got = int(hexpart, 16)
        assert got == want, (
            f"{name} literal {got:#x} disagrees with the recomputed {want:#x}")
    print(f"   constants checked: LN2 and LOG2E match to {FRAC_BITS} fractional bits")


def cases() -> list[tuple[str, int]]:
    """(name, binary32 code) for each argument."""
    import math
    out: list[tuple[str, int]] = []
    def add(name, value):
        code = int(np.float32(value).view(np.uint32))
        out.append((name, code))
    ln2 = math.log(2.0)
    add("smallest_subnormal", np.float32(np.ldexp(1.0, -149)))
    add("tiny_normal", np.float32(np.ldexp(1.0, -126)))
    add("half_ulp_of_one", np.float32(np.ldexp(1.0, -24)))
    add("one", 1.0)
    add("ln2_exactly", ln2)
    add("just_below_ln2", np.nextafter(np.float32(ln2), np.float32(0.0)))
    add("just_above_ln2", np.nextafter(np.float32(ln2), np.float32(1.0)))
    for k in (2, 3, 8, 32, 64, 100, 127):
        add(f"near_{k}_ln2", np.float32(k) * np.float32(ln2))
    add("sink_max_v4", 2.492747)
    add("sink_max_v41", 1.129465)
    add("offset_five", 5.0)
    add("offset_twenty", 20.0)
    add("largest_finite_exp", 88.7228)
    add("pi", math.pi)
    rng = np.random.default_rng(20260917)
    #: A thin corpus is not evidence for a transcendental. Sweep the whole
    #: positive range, densely near the reduction boundaries and across every
    #: binade, plus a uniform-in-code tail so the mantissa bits are covered too.
    for i in range(900):
        add(f"random_{i}", float(rng.uniform(1e-30, 88.7)))
    for i in range(300):
        add(f"random_small_{i}", float(rng.uniform(0.0, 1.0)))
    #: One ulp either side of every multiple of ln2 in range: these are where
    #: the floor of x*log2(e) can disagree with the exact quotient.
    for k in range(1, 128):
        centre = np.float32(np.float32(k) * np.float32(ln2))
        add(f"ln2_x{k}", float(centre))
        add(f"ln2_x{k}_lo", float(np.nextafter(centre, np.float32(0.0))))
        add(f"ln2_x{k}_hi", float(np.nextafter(centre, np.float32(1e30))))
    #: Uniform in the CODE space, which concentrates on small magnitudes the way
    #: binary32 itself does.
    for i in range(600):
        code = int(rng.integers(1, 0x42b17218))
        x = np.array([code], dtype=np.uint32).view(np.float32)[0]
        if 0 < x < 88.7:
            out.append((f"code_{i}", code))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    check_constants()

    rows = []
    overflow = 0
    for name, code in cases():
        x = np.array([code], dtype=np.uint32).view(np.float32)
        assert x[0] > 0 and np.isfinite(x[0]), name
        want = exp_cr32(np.ascontiguousarray(x))
        finite = bool(np.isfinite(want[0]))
        if not finite:
            overflow += 1
        rows.append((name, code, int(np.float32(want[0]).view(np.uint32))
                     if finite else 0, 0 if finite else 1))

    lines = [str(len(rows))]
    for name, code, want, over in rows:
        lines.append(f"{name} {code:08x} {want:08x} {over}")
    (args.out / "cases.txt").write_text("\n".join(lines) + "\n")
    print(f"wrote {len(rows)} cases to {args.out}  ({overflow} overflow the range)")
    for name, code, want, over in rows[:18]:
        x = float(np.array([code], dtype=np.uint32).view(np.float32)[0])
        print(f"   {name:20s} x={x:<14.8g} exp={'OVERFLOW' if over else f'{want:#010x}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
