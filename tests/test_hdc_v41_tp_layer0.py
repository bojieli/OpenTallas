"""The first shipped-shape TP layer must preserve the golden's FP32/BF16 order."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import hdc_golden_v41 as golden
import hdc_isa_v41 as isa
import hdc_replay_v41 as replay


def test_layer0_collectives_encode_with_aligned_disjoint_regions():
    lay = replay.ShapeLayout(replay.SHIPPED, tp_exact=True)
    assert lay.vm.map["CKV2"] == 448_736 < 1 << 19  # first HBM-only region
    prog = replay.build_tp_layer0()
    assert len(prog) == 103
    coll = [f for f in prog if f["unit"] == isa.UNIT_COLL]
    assert len(coll) == 12
    assert [f["coll_seq"] for f in coll] == list(range(len(coll)))
    assert [f["coll_op"] for f in coll].count(isa.COLL_ALL_REDUCE_SUM) == 1
    assert [f["coll_op"] for f in coll].count(isa.COLL_ALL_GATHER) == 11
    for f in coll:
        src, dst, n = f["coll_src"], f["coll_dst"], f["coll_n"]
        written = n if f["coll_op"] == isa.COLL_ALL_REDUCE_SUM else 4 * n
        assert src % 16 == dst % 16 == n % 16 == 0
        assert src + n <= dst or dst + written <= src
        assert f["coll_k"] == f["coll_ibase"] == 0
    wo_b = next(f for f in prog if f.get("_tag") == "L0.out" and f["unit"] == isa.UNIT_QE
                and f.get("qe_unrounded"))
    reduce = next(f for f in coll if f["coll_op"] == isa.COLL_ALL_REDUCE_SUM)
    assert wo_b["qe_nb"] == 64 and reduce["coll_n"] == 5120 and reduce["coll_rnd"] == 1
    assert all(isa.decode(isa.encode(full_shape=True, **f), full_shape=True)["unit"] == f["unit"]
               for f in prog)


def test_w2_row_split_and_wo_b_rank_tree_match_golden(monkeypatch):
    monkeypatch.setattr(golden, "ARITH", "chunk8")
    rng = np.random.default_rng(41)
    # 2,304 = 4 x 576 = 72 blocks. A gather of BF16 activations
    # reconstructs the exact vector, and each block's FP8 quantisation is local.
    x = golden.to_bf16(rng.normal(size=2304).astype(np.float32))
    parts = [x[r * 576:(r + 1) * 576] for r in range(4)]
    q_all, e_all = golden.quant_fp8(x)
    q_parts, e_parts = zip(*(golden.quant_fp8(part) for part in parts))
    assert np.array_equal(q_all, np.concatenate(q_parts))
    assert np.array_equal(e_all, np.concatenate(e_parts))
    q = rng.choice(golden.E2M1, size=(32, 2304))
    w = golden.Q8(q, np.zeros((32, 72), dtype=np.int64))
    full = golden.linear_q(w, x)
    rows = [golden.linear_q(golden.Q8(w.q[r * 8:(r + 1) * 8],
                                     w.e[r * 8:(r + 1) * 8]), x) for r in range(4)]
    assert np.array_equal(full.view(np.uint32), np.concatenate(rows).view(np.uint32))

    # wo_b's 256 K blocks split into 64-block aligned subtrees. The die's
    # ((r0+r1)+(r2+r3)) FP32 order reconstructs chunk8 before BF16 rounding.
    terms = rng.normal(size=(32, 256)).astype(np.float32)
    whole = golden.csum(terms)
    partial = [golden.csum(terms[:, r * 64:(r + 1) * 64]) for r in range(4)]
    merged = golden.add(golden.add(partial[0], partial[1]), golden.add(partial[2], partial[3]))
    assert np.array_equal(whole.view(np.uint32), merged.view(np.uint32))
    assert np.array_equal(golden.to_bf16(whole).view(np.uint32),
                          golden.to_bf16(merged).view(np.uint32))


def test_exact_tp_emitter_fails_closed_for_other_layers():
    lay = replay.ShapeLayout(replay.SHIPPED, tp_exact=True)
    with pytest.raises(ValueError, match="only layer 0"):
        replay.ShapeBuilder(lay).build([1], embed=False, head=False)


def test_sequential_blockdot_is_not_the_chunk8_contract():
    terms = np.zeros(64, dtype=np.float32)
    terms[0] = np.float32(1e20)
    terms[8] = np.float32(-1e20)
    terms[9] = np.float32(1)
    sequential = np.float32(0)
    for term in terms:
        sequential = golden.add(sequential, term)
    chunk8 = golden.csum(terms)
    assert sequential == np.float32(1)
    assert chunk8 == np.float32(0)


def test_attention_uses_bounded_local_rows_at_both_contexts():
    prog = replay.build_tp_layer0()
    cur_kt = next(f for f in prog if f.get("_tag") == "L0.attn" and f.get("dst") == isa.DST_KVT)
    cur_kr = next(f for f in prog if f.get("_tag") == "L0.attn" and f.get("dst") == isa.DST_KV)
    assert cur_kt["o_d"] == "WINM1"
    assert cur_kr["o_d"] == "WINM1_ROW"
    # Layer 0 has no CKV selection. Later compressed-KV layers use WIN and
    # WIN_ROW as the first local selected row, never the absolute position.
    for position in (0, 199_999, 1_048_575):
        dyn = replay.dyn_values(replay.SHIPPED, position)
        win = min(position + 1, 128)
        assert dyn["WINM1"] == win - 1
        assert dyn["WIN_ROW"] == win * 512
        assert dyn["WINM1_ROW"] == (win - 1) * 512
        assert dyn["T0"] <= 640
    encoded = isa.decode(isa.encode(full_shape=True, **cur_kt), full_shape=True)
    assert encoded["o_d"] == isa.FULL_DYN["WINM1"]


def test_compressed_layer_attention_stages_selected_rows_after_window():
    # The exact TP layer-2 program is not yet emitted, but its attention
    # composite already gives the die prefetcher bounded local row addresses.
    builder = replay.ShapeBuilder(replay.ShapeLayout(replay.SHIPPED, tp_exact=True))
    builder.attention(2)
    fields = [item[0] for item in builder.prog]
    assert any(f.get("dst") == isa.DST_KVT and f.get("o_d") == "WIN" for f in fields)
    assert any(f.get("dst") == isa.DST_KV and f.get("o_d") == "WIN_ROW" for f in fields)
    assert all(f.get("o_d") not in (isa.DYN["POS1"], isa.DYN["ROW1"])
               for f in fields if f.get("dst") in (isa.DST_KVT, isa.DST_KV))
