"""``ot_a3_qwen_gqa`` is bit-exact at every geometry and query span it is
elaborated for.

Rung G1f's third blocker: "the attention engine has no geometry input: for one
query row at context 16 it read 135,168 operand words and wrote 4,096 result
words, 32.0x and 32.0x what the reduced configuration's attention row is".  The
engine's query-head count, KV-head count, head width and attention scale were
localparams fixed at Qwen3-8B's 32/8/128.

They are elaboration parameters now, defaulting to those same values.  The
attention scale travels with them because it is not independent: it is
bf16(1/sqrt(head_dim)), 0x3db5 at 128 and 0x3e80 at 16, and changing the head
width without it would compute a different attention in silence.

The engine also had no query-row dimension at all: its outermost loop level was
HEADS, the query fetch address carried no row term, and the result buffer was
sized for one row.  A prefill is a launch of SPAN query rows against one KV
plane, where row i may attend only to positions up to its own absolute sequence
position -- so the rows are NOT interchangeable and a span cannot be faked by
repeating a decode.  ``MAX_QUERY_SPAN`` (default 1) is the new bound, the span
and the first row's absolute position are configuration inputs, and the causal
mask is the contract's own finite BF16 code.

This test elaborates the engine at four points and compares every output word
against the reference.  Span 1 at the shipped geometry is a positive control, so
a decode regression fails here; span 1 at the reduced geometry is rung G1f's
case, and it also pins the traffic figures the blocker cited so the 32x it named
is measured as closed rather than asserted.  Span 4 is a prefill chunk landing
on a non-empty KV cache, and span 16 is a whole-context prefill whose first row
may attend to exactly one position -- the case that a masked implementation
reducing over a shortened row would get wrong, because a one-element softmax
denominator is not the frozen eight-lane reduction.
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

# (label, query heads, kv heads, head dim, span).  Every counter this test
# asserts is DERIVED from these by the formulas below, so adding a case cannot
# leave a pinned constant stale.
CASES = (
    ("shipped", 32, 8, 128, 1),
    ("reduced", 8, 2, 16, 1),
    ("reduced_chunk", 8, 2, 16, 4),
    ("reduced_prefill", 8, 2, 16, 16),
)

# The traffic figures rung G1f's blocker cited, at span 1.  They are checked
# against the formula, not used in place of it.
BLOCKER_TRAFFIC = {
    ("shipped", 1): (135_168, 4_096),
    ("reduced", 1): (4_224, 128),
}


def _expected_counters(
    query_heads: int, head_dim: int, span: int, context: int
) -> dict[str, int]:
    """The counts a span-S launch must report.

    The causal mask is ADDITIVE, so the work stays rectangular in S*C and the
    oracle's own accounting agrees: it evaluates an exponential for every one of
    the S*C*query_heads scores.  These are the expressions the engine issue
    bridge must self-check against.
    """

    row_words = query_heads * head_dim
    return {
        "reads": span * row_words * (1 + 2 * context),
        "writes": span * row_words,
        "smul": span * context * row_words,
        "vmul": span * context * row_words,
        "expc": span * query_heads * context,
    }


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


def _build(tmp_path, label, query_heads, kv_heads, head_dim, span, geometry, bad=0,
           ctx=None):
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
            f"-Ptb_a3_qwen_gqa_geometry.SPAN={span}",
            f"-Ptb_a3_qwen_gqa_geometry.BAD={bad}",
            *([f"-Ptb_a3_qwen_gqa_geometry.CTX={ctx}"] if ctx is not None else []),
            *SOURCES,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert build.returncode == 0, build.stderr
    return binary


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)
@pytest.mark.parametrize("bad", (1, 2, 3))
def test_gqa_refuses_a_misconfigured_span(tmp_path, bad):
    """The span bound and the tail-alignment rule are enforced, not decorative.

    A span past the elaborated MAX_QUERY_SPAN, and a first position that is not
    the one the context implies, must both refuse with ERR_CONFIG before any
    memory read -- which is also what happens to an elaboration that raises the
    bound and leaves the two new configuration inputs undriven.
    """

    geometry = AttentionGeometry(query_heads=8, kv_heads=2, head_dim=16)
    for name in ("q.hex", "k.hex", "v.hex"):
        (tmp_path / name).write_text("00000000\n")
    binary = _build(tmp_path, f"bad{bad}", 8, 2, 16, 4, geometry, bad=bad)
    run = subprocess.run(
        ["vvp", str(binary)], cwd=tmp_path, capture_output=True, text=True, timeout=600
    )
    assert run.returncode == 0, run.stderr
    # ERR_CONFIG is 1, and a refusal reads nothing and writes nothing.
    assert "err=1 failed=1" in run.stdout, run.stdout
    assert "reads=0 writes=0" in run.stdout, run.stdout


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)
@pytest.mark.parametrize("label,query_heads,kv_heads,head_dim,span", CASES)
def test_gqa_is_bit_exact_at_its_elaborated_geometry(
    tmp_path, label, query_heads, kv_heads, head_dim, span
):
    geometry = AttentionGeometry(
        query_heads=query_heads, kv_heads=kv_heads, head_dim=head_dim
    )
    rng = random.Random(0x9E37_79B9)
    query = [
        [
            [_bf16(rng.uniform(-1, 1)) for _ in range(head_dim)]
            for _ in range(query_heads)
        ]
        for _ in range(span)
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
        "".join(f"{c:08x}\n" for row in query for head in row for c in head)
    )
    (tmp_path / "k.hex").write_text(
        "".join(f"{c:08x}\n" for tok in keys for head in tok for c in head)
    )
    (tmp_path / "v.hex").write_text(
        "".join(f"{c:08x}\n" for tok in values for head in tok for c in head)
    )

    binary = _build(
        tmp_path, label, query_heads, kv_heads, head_dim, span, geometry
    )

    run = subprocess.run(
        ["vvp", str(binary)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=7200,
    )
    assert run.returncode == 0, run.stderr
    assert "err=0 failed=0" in run.stdout, run.stdout
    counters = _expected_counters(query_heads, head_dim, span, CONTEXT)
    if (label, span) in BLOCKER_TRAFFIC:
        reads, writes = BLOCKER_TRAFFIC[(label, span)]
        assert (counters["reads"], counters["writes"]) == (reads, writes)
    for name, value in counters.items():
        assert f"{name}={value} " in f"{run.stdout} ", (name, value, run.stdout)
    # Nothing saturates on this operand distribution, at any span: a masked
    # position's score is the finite mask code exactly, not an overflow.
    assert "sats=0 " in f"{run.stdout} ", run.stdout

    got = [w & 0xFFFF for w in _hex_words((tmp_path / "o.hex").read_text())]
    # A span of S is a committed snapshot of CONTEXT-S rows plus a prepared
    # append of the S rows the span computes, which is what makes the oracle's
    # visible_tokens = committed.length + i + 1 the engine's
    # cfg_first_position + i.
    committed = CONTEXT - span
    snapshot = make_kv_snapshot(
        resource_id="t.kv",
        generation=committed,
        capacity=8192,
        key_values=keys[:committed],
        value_values=values[:committed],
        geometry=geometry,
    )
    prepared = prepare_kv_append(
        snapshot,
        transaction_id=0x11,
        expected_generation=committed,
        position_start=committed,
        key_values=keys[committed:],
        value_values=values[committed:],
    )
    reference = gqa_causal_attention_bf16(query, snapshot, prepared)
    want = [
        code
        for row in reference.output_values
        for head in row
        for code in head
    ]
    assert len(got) == len(want) == span * query_heads * head_dim
    assert got == want, (
        f"{label}: first mismatch at "
        f"{next(i for i, (a, b) in enumerate(zip(got, want)) if a != b)}"
    )
    assert reference.accounting.exponential_evaluations == counters["expc"]

    if span > 1:
        # The mask must actually have FIRED, or this comparison would pass for
        # an engine with no causal boundary at all.  Query row 0 of a span sees
        # CONTEXT-span+1 positions; recompute it against the whole context and
        # require the RTL to disagree with that.
        unmasked_snapshot = make_kv_snapshot(
            resource_id="t.kv",
            generation=CONTEXT - 1,
            capacity=8192,
            key_values=keys[: CONTEXT - 1],
            value_values=values[: CONTEXT - 1],
            geometry=geometry,
        )
        unmasked_prepared = prepare_kv_append(
            unmasked_snapshot,
            transaction_id=0x12,
            expected_generation=CONTEXT - 1,
            position_start=CONTEXT - 1,
            key_values=keys[CONTEXT - 1 :],
            value_values=values[CONTEXT - 1 :],
        )
        unmasked = gqa_causal_attention_bf16(
            [query[0]], unmasked_snapshot, unmasked_prepared
        )
        row_words = query_heads * head_dim
        assert got[:row_words] != [
            code for head in unmasked.output_values[0] for code in head
        ], f"{label}: row 0 is identical with and without the causal mask"


@pytest.mark.skipif(
    shutil.which("iverilog") is None or shutil.which("vvp") is None,
    reason="iverilog/vvp not available",
)
def test_gqa_refuses_a_span_wider_than_its_context(tmp_path):
    """A span that exceeds its context must refuse, and modular arithmetic hides it.

    The tail-alignment rule is ``first_position + span == context_length``, a
    32-bit comparison -- so it ALSO holds when a caller computed the first
    position as ``context - span`` in unsigned arithmetic with span > context.
    That underflows to ``2**32 - (span - context)``, and adding span back gives
    the context again, exactly, modulo 2**32.

    Before the non-modular guard the engine accepted such a launch, and then
    ``row_visible_last_q`` took the low CTX_W bits of 0xfffffff8 -- a bound above
    every context index -- so NOTHING was masked and a full span of non-causal
    rows retired: context 8, span 16, first position 0xfffffff8, err=0, all
    2,048 words written.

    The hole required MAX_QUERY_SPAN > MIN_CONTEXT, which is unreachable in every
    elaboration that exists today and live in exactly the one a prefill needs.
    This is that case, and it must refuse before a single memory read.
    """

    geometry = AttentionGeometry(query_heads=8, kv_heads=2, head_dim=16)
    for name in ("q.hex", "k.hex", "v.hex"):
        (tmp_path / name).write_text("00000000\n")
    # MAX_QUERY_SPAN 16 against a context of 8: the bench's own
    # FIRST_POSITION = CTX - SPAN underflows, which is the whole point.
    binary = _build(tmp_path, "span_gt_ctx", 8, 2, 16, 16, geometry, ctx=8)
    run = subprocess.run(
        ["vvp", str(binary)], cwd=tmp_path, capture_output=True, text=True, timeout=600
    )
    assert run.returncode == 0, run.stderr
    assert "err=1 failed=1" in run.stdout, run.stdout
    assert "reads=0 writes=0" in run.stdout, run.stdout
