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
