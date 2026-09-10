"""``ot_a3_vector_rms_norm`` is bit-exact at every width it admits.

The engine used to select its mean reciprocal from two hardcoded constants,
1/4096 and 1/128, and refused every other width with ``ERR_SHAPE``.  Rung G1f
measured that refusal as its second blocker: the reduced regression model
normalises 128-wide model rows and 16-wide attention-head rows, and the engine
would not run the 16.

The reciprocal is now derived from the width.  That is exact precisely when the
width is a power of two, because the golden model does not use a reciprocal at
all -- ``rms_norm_bf16`` takes the mean as ``binary32_divide(total,
encode_binary32_rne(width))`` -- and dividing by ``2**k`` and multiplying by
``2**-k`` are both pure exponent adjustments with no rounding.

This test is what makes that argument checkable rather than plausible: it runs
the real RTL over real operands at four geometries and compares every output
word against the golden.  The two shipped Qwen widths are positive controls, so
the test fails if the generalisation disturbed them.
"""

from __future__ import annotations

import random
import re
import shutil
import struct
import subprocess

import pytest

from pathlib import Path

from runtime.reference.tensor_accelerator_rmsnorm import rms_norm_bf16

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/test/tb_a3_rms_norm_width.sv",
)

# (rows, cols).  The first two are the reduced regression model's geometries,
# the last two the shipped Qwen ones, kept as positive controls.
GEOMETRIES = ((8, 16), (1, 128), (32, 128), (1, 4096))

WIDEST = 4096


def _bf16(value: float) -> int:
    return (struct.unpack("<I", struct.pack("<f", value))[0] >> 16) & 0xFFFF


def _hex_words(text: str) -> list[int]:
    words: list[int] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        if re.fullmatch(r"[0-9a-fA-F]{1,8}", line):
            words.append(int(line, 16))
    return words


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)
def test_rms_norm_is_bit_exact_at_every_admitted_width(tmp_path):
    # Deterministic operands of ordinary magnitude: the point is the width
    # handling, not saturation behaviour, which the engine reports separately.
    rng = random.Random(0x5150_4F54)
    inputs = [_bf16(rng.uniform(-2.0, 2.0)) for _ in range(WIDEST)]
    weights = [_bf16(rng.uniform(0.5, 1.5)) for _ in range(WIDEST)]
    (tmp_path / "in.hex").write_text("".join(f"{c:08x}\n" for c in inputs))
    (tmp_path / "w.hex").write_text("".join(f"{c:08x}\n" for c in weights))

    binary = tmp_path / "rms_width.vvp"
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", str(binary), *SOURCES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert build.returncode == 0, build.stderr

    for rows, cols in GEOMETRIES:
        run = subprocess.run(
            ["vvp", str(binary), f"+rows={rows}", f"+cols={cols}"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=2400,
        )
        assert run.returncode == 0, run.stderr
        assert f"cols={cols} count={rows * cols} err=0" in run.stdout, run.stdout

        got = [w & 0xFFFF for w in _hex_words((tmp_path / "out.hex").read_text())]
        reference = rms_norm_bf16(
            [inputs[r * cols : (r + 1) * cols] for r in range(rows)],
            weights[:cols],
        )
        want = [code for row in reference.values for code in row]
        assert len(got) == len(want) == rows * cols
        assert got == want, (
            f"{rows}x{cols}: first mismatch at "
            f"{next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)}"
        )


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)
def test_rms_norm_still_refuses_a_width_whose_reciprocal_is_inexact(tmp_path):
    """A negative control: the generalisation is to powers of two, not to all.

    Without this the test above would pass just as well if the shape check had
    been deleted outright, which would let the engine compute a width whose
    reciprocal rounds and silently disagree with the golden's division.
    """

    rng = random.Random(0x5150_4F54)
    (tmp_path / "in.hex").write_text(
        "".join(f"{_bf16(rng.uniform(-2.0, 2.0)):08x}\n" for _ in range(WIDEST))
    )
    (tmp_path / "w.hex").write_text(
        "".join(f"{_bf16(rng.uniform(0.5, 1.5)):08x}\n" for _ in range(WIDEST))
    )
    binary = tmp_path / "rms_width.vvp"
    build = subprocess.run(
        ["iverilog", "-g2012", "-o", str(binary), *SOURCES],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert build.returncode == 0, build.stderr

    # 24 is not a power of two, so 1/24 is not representable exactly and the
    # engine's multiply would not reproduce the golden's divide.
    run = subprocess.run(
        ["vvp", str(binary), "+rows=4", "+cols=24"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=2400,
    )
    assert run.returncode == 0, run.stderr
    assert "err=7" in run.stdout, run.stdout
