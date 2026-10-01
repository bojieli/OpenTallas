"""W10 item 1: golden-aligned K-split V4.1 ROM bank map (tools/v41_rom_ksplit_bankmap.py)."""
import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_rom_ksplit_bankmap as S  # noqa: E402

SNAP = Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots" \
    / "dba1be0a40aa45a94ad051997016db3960a90277"
REC = ROOT / "results/uarch/v41_rom_ksplit_bankmap.json"


def _region_bijection(segs):
    """Every 32-block (FP8/FP4) or element (BF16) of every segment appears in exactly one (word, slot), both in
    the segment's address order and in the element's issue order."""
    total = 0
    for i, sg in enumerate(segs):
        got = {}
        order = S.segment_order(sg["fmt"], sg["e0"], sg["elems"])
        for w, (u, b, h) in enumerate(order):
            for slot, e in enumerate(S.word_slots(sg["fmt"], sg["e0"], sg["elems"], u, b, h)):
                if e >= 0:
                    assert e not in got, (i, e)
                    got[e] = (w, slot)
        step = 1 if sg["fmt"] == "bf16" else 32
        assert set(got) == set(range(sg["e0"], sg["e0"] + sg["elems"], step)), (i, sg)
        assert len(order) == S.seg_words(sg["fmt"], sg["e0"], sg["elems"])
        total += len(order)
    issue = S.element_order(segs)
    assert len(issue) == total
    for i in range(len(segs)):                          # the element reads each segment in address order
        mine = [(u, b, h) for (j, u, b, h) in issue if j == i]
        assert mine == S.segment_order(segs[i]["fmt"], segs[i]["e0"], segs[i]["elems"])
    return total


def test_segments_are_golden_aligned():
    for K in (512, 1280, 2048, 2304, 4096, 5120):
        C = math.ceil(K / 256)
        for s in (1, 2, 4, 8, 16, 32):
            segs = S.segments(K, s)
            c = S.npow2(math.ceil(C / s))
            assert segs[0][1] == min(c * 256, K)
            assert all(e0 % (c * 256) == 0 for e0, _ in segs)
            assert sum(el for _, el in segs) == K and len(segs) == math.ceil(C / c)


def test_small_regions_bijective():
    cases = [
        [dict(fmt="fp8", e0=0, elems=1024, row=0, tensor="a"), dict(fmt="fp8", e0=1024, elems=256, row=1, tensor="a")],
        [dict(fmt="fp8", e0=512, elems=256, row=r, tensor="b") for r in range(3)]
        + [dict(fmt="fp8", e0=768, elems=256, row=5, tensor="b"), dict(fmt="fp4", e0=512, elems=512, row=0, tensor="g")],
        [dict(fmt="fp4", e0=0, elems=4096, row=0, tensor="c"), dict(fmt="fp4", e0=4096, elems=1024, row=0, tensor="c")],
        [dict(fmt="fp4", e0=2048, elems=256, row=4, tensor="d")],
        [dict(fmt="bf16", e0=0, elems=2048, row=0, tensor="e"), dict(fmt="bf16", e0=2048, elems=2048, row=9, tensor="e")],
        [dict(fmt="bf16", e0=256, elems=256, row=1, tensor="f")],
    ]
    for segs in cases:
        _region_bijection(segs)


@pytest.mark.skipif(not (SNAP / "model.safetensors.index.json").exists(), reason="checkpoint headers absent")
def test_busiest_die_every_word_once_and_record():
    keep = []
    dies = S.derive(SNAP, draws=2, seed=1, only=["layer_s01_r3"], keep=keep)
    die, d = keep[0], dies[0]
    assert d["macros"] == 13798 and d["pair_slots"] == 6899 and d["bf16_pair_slots"] == S.BF16_MACROS // 2
    assert d["capacity_ok"]
    # every distinct region shape is a bijection (segment coverage and region disjointness are checked in derive)
    shapes = {}
    for rg in die.regions:
        segs = [die.segs[i] for i in rg["seg_ids"]]
        key = tuple(sorted((s["fmt"], s["e0"], s["elems"], s["row"] == segs[0]["row"]) for s in segs))
        shapes.setdefault(key, segs)
        assert rg["words"] == sum(S.seg_words(s["fmt"], s["e0"], s["elems"]) for s in segs)
    for segs in shapes.values():
        _region_bijection(segs)
    rec = json.loads(REC.read_text())
    got = next(x for x in rec["dies"] if x["die"] == "layer_s01_r3")
    assert got["weight_words"] == d["weight_words"] and got["segments"] == d["segments"]
    assert [L["t_read"] for L in got["dense"]] == [L["t_read"] for L in d["dense"]]
    assert rec["all_capacity_ok"]


def test_phases_match_model():
    rec = json.loads(REC.read_text())
    model, params = S.model_rows()
    assert params["bf16_stripe_macros"] == S.BF16_MACROS
    for ph, r in rec["phase_vs_model"].items():
        assert r["model_issue"] == model[ph]["issue"], ph
        assert r["issue_ok"], (ph, r)
        assert r["t_read_within_model"], (ph, r)
    assert rec["verdict"].startswith("PASS")


PROD = ROOT / "results/uarch/v41_rom_ksplit_bankmap_product.json"


@pytest.mark.skipif(not PROD.exists(), reason="product bank map record not generated")
def test_product_bank_map_distance_aware_all_dies():
    """The product bank map (root decision 2026-09-30): BF16_PAIR option iii, L = 8 chains, distance-aware
    placement of the latency-critical phases.  Every die fits its ROM depth; the critical phases sit on a
    nearest-slot prefix no farther than the whole-die placement; the record binds current sources."""
    import hashlib
    rec = json.loads(PROD.read_text())
    for p, h in rec["source_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p
    rule = rec["rule"]
    assert rule["bf16_pair"] is None                       # product: dedicated BF16 columns (root, 2026-09-30)
    assert "v41_stage_owner_product.json" in " ".join(rec["source_sha256"])
    assert rule["chain_recurrence_cycles"] == 8
    da = rule["distance_aware"]
    assert set(da["critical"]) == {"a_proj", "wq_b", "cmp.wk", "wo_a", "wo_b", "router", "shared_gu", "down"}
    owners = json.loads((ROOT / "results/arch/v41_stage_owner_product.json").read_text())
    assert len(rec["dies"]) == owners["layer_dies"]        # every layer die of the product owners (41 TP-4 stages: 164)
    assert rec["all_capacity_ok"] and all(d["capacity_ok"] and d["max_address"] <= S.DEPTH for d in rec["dies"])
    whole = max(r["wire"]["farthest_um"] for r in rec["phase_vs_model"].values() if r.get("wire"))
    for ph in da["critical"]:
        w = rec["phase_vs_model"][ph]["wire"]
        if w is None:                                      # the phase has no rows on the busiest die
            continue
        assert w["farthest_um"] <= whole and w["wire_cycles"] == 2 * math.ceil(w["farthest_um"] / da["reach_um"]) \
            + da["gather_scatter_cycles"], ph
    for d in rec["dies"]:
        for L in d["dense"]:
            for ph, w in L["wire"].items():
                if ph in da["critical"] and w["near_slots"] is not None:
                    assert w["slots_used"] <= w["near_slots"] <= d["pair_slots"], (d["die"], ph)
    pr = rec["priced"]
    assert pr["with_measured_t_phase_and_wire"] is not None
