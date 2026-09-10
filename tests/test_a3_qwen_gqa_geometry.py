"""``ot_a3_qwen_gqa`` is bit-exact at every geometry it is elaborated for.

Rung G1f's third blocker: "the attention engine has no geometry input: for one
query row at context 16 it read 135,168 operand words and wrote 4,096 result
words, 32.0x and 32.0x what the reduced configuration's attention row is".  The
engine's query-head count, KV-head count, head width and attention scale were
localparams fixed at Qwen3-8B's 32/8/128.

They are elaboration parameters now, defaulting to those same values.  The
attention scale travels with them because it is not independent: it is
bf16(1/sqrt(head_dim)), 0x3db5 at 128 and 0x3e80 at 16, and changing the head
width without it would compute a different attention in silence.

This test elaborates the engine twice and compares every output word against
the reference.  The shipped geometry is a positive control, so a regression
there fails here; the reduced geometry is the new capability.  It also pins the
traffic figures the blocker cited, so the 32x it named is measured as closed
rather than asserted.
"""

from __future__ import annotations

import random
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

from runtime.reference.tensor_accelerator_attention import (
    AttentionGeometry,
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/test/tb_a3_qwen_gqa_geometry.sv",
)

CONTEXT = 16

# (label, query heads, kv heads, head dim, expected reads, expected writes).
# The traffic figures are the ones rung G1f's blocker cited.
CASES = (
    ("shipped", 32, 8, 128, 135_168, 4_096),
    ("reduced", 8, 2, 16, 4_224, 128),
)


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
@pytest.mark.parametrize("label,query_heads,kv_heads,head_dim,reads,writes", CASES)
def test_gqa_is_bit_exact_at_its_elaborated_geometry(
    tmp_path, label, query_heads, kv_heads, head_dim, reads, writes
):
    geometry = AttentionGeometry(
        query_heads=query_heads, kv_heads=kv_heads, head_dim=head_dim
    )
    rng = random.Random(0x9E37_79B9)
    query = [
        [_bf16(rng.uniform(-1, 1)) for _ in range(head_dim)]
        for _ in range(query_heads)
    ]
    keys = [
        [[_bf16(rng.uniform(-1, 1)) for _ in range(head_dim)] for _ in range(kv_heads)]
        for _ in range(CONTEXT)
    ]
    values = [
        [[_bf16(rng.uniform(-1, 1)) for _ in range(head_dim)] for _ in range(kv_heads)]
        for _ in range(CONTEXT)
    ]
    (tmp_path / "q.hex").write_text(
        "".join(f"{c:08x}\n" for head in query for c in head)
    )
    (tmp_path / "k.hex").write_text(
        "".join(f"{c:08x}\n" for tok in keys for head in tok for c in head)
    )
    (tmp_path / "v.hex").write_text(
        "".join(f"{c:08x}\n" for tok in values for head in tok for c in head)
    )

    binary = tmp_path / f"gqa_{label}.vvp"
    build = subprocess.run(
        [
            "iverilog",
            "-g2012",
            "-o",
            str(binary),
            f"-Ptb_a3_qwen_gqa_geometry.QH={query_heads}",
            f"-Ptb_a3_qwen_gqa_geometry.KVH={kv_heads}",
            f"-Ptb_a3_qwen_gqa_geometry.HW={head_dim}",
            f"-Ptb_a3_qwen_gqa_geometry.SC={geometry.scale_code << 16}",
            *SOURCES,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert build.returncode == 0, build.stderr

    run = subprocess.run(
        ["vvp", str(binary)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    assert run.returncode == 0, run.stderr
    assert "err=0 failed=0" in run.stdout, run.stdout
    # The traffic the blocker measured, now measured at the reduced geometry.
    assert f"reads={reads} writes={writes}" in run.stdout, run.stdout

    got = [w & 0xFFFF for w in _hex_words((tmp_path / "o.hex").read_text())]
    snapshot = make_kv_snapshot(
        resource_id="t.kv",
        generation=CONTEXT - 1,
        capacity=8192,
        key_values=keys[:-1],
        value_values=values[:-1],
        geometry=geometry,
    )
    prepared = prepare_kv_append(
        snapshot,
        transaction_id=0x11,
        expected_generation=CONTEXT - 1,
        position_start=CONTEXT - 1,
        key_values=keys[-1:],
        value_values=values[-1:],
    )
    reference = gqa_causal_attention_bf16([query], snapshot, prepared)
    want = [code for head in reference.output_values[0] for code in head]
    assert len(got) == len(want) == query_heads * head_dim
    assert got == want, (
        f"{label}: first mismatch at "
        f"{next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)}"
    )
