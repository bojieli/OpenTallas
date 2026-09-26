"""Checks for the shipped-scale V4.1 selects: the candidate-block select (ot_hdc_tselect_cand) and the index
top-512 on ot_hdc_tselect at 1M context.  The RTL campaigns are long; these tests read their records, pin the
golden mirrors the campaigns rely on, and check the records are bound to the current sources."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import rtl_hdc_v41_cand_campaign as CC  # noqa: E402
import rtl_hdc_v41_tselect_campaign as TC  # noqa: E402

CAND = ROOT / "results/rtl/hdc_v41_cand_campaign.json"
SCALE = ROOT / "results/rtl/hdc_v41_tselect_scale_campaign.json"
PHYS = ROOT / "results/physical_abi3/asap7/hdc/v41/ot_hdc_tselect_cand/physical.json"
CONTEXTS = {8192, 200000, 1048576}


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


@pytest.mark.parametrize("path", [CAND, SCALE])
def test_record_passes_and_is_current(path):
    rec = json.loads(path.read_text())
    assert rec["status"] == "pass"
    for p, h in rec["input_sha256"].items():
        if p.startswith("rtl/"):
            assert sha(p) == h, p


def test_candidate_expected_stream_is_the_goldens_keep_mask():
    rng = np.random.default_rng(1)
    for n in (1, 7, 8, 9, 63, 64, 65, 1000, 20000):
        s = CC.SC.random_values(rng, n, 16)
        for k in (0, 1, 5, 64, 2048):
            exp, bs = CC.expected_blocks(s, k, 2048, 0, True)
            keep = CC.golden_keep(s, min(k, 2048))
            kept = [i for i, _, ninf in exp if not ninf]
            assert kept == [int(i) for i in np.nonzero(keep)[0]]
            assert [i for i, _, _ in exp] == sorted(i for i, _, _ in exp)


def test_candidate_campaign_covers_the_shipped_shape():
    rec = json.loads(CAND.read_text())
    ship = next(c for c in rec["configurations"] if c["name"] == "candidate_shipped_p64_wb64")
    assert ship["K"] == rec["shipped_shape"]["candidate_topk_blocks"] == 2048
    assert ship["max_positions"] >= rec["shipped_shape"]["max_context_tokens"]
    assert ship["multi_die"]["pass"] and ship["multi_die"]["golden_keep_mask_agrees"]
    assert all(r["pass"] for r in ship["runs"].values())
    rows = rec["latency_at_shipped_context"]["rows"]
    assert {r["context"] for r in rows} == CONTEXTS
    for r in rows:
        assert r["cycles_after_last_beat"] in (r["formula"], r["formula"] + 1)
    muts = rec["mutations"]
    assert muts[0]["control"] and not muts[0]["caught"]
    assert all(m["caught"] for m in muts[1:]) and len(muts) == len(CC.MUTATIONS) + 1


def test_index_select_scales_to_the_full_context():
    rec = json.loads(SCALE.read_text())
    par = rec["parameters"]
    assert par["max_positions"] >= rec["shipped_shape"]["max_context_tokens"]
    assert par["K"] == 512 and par["lat0"] == TC.lat0(par["W"])
    rows = rec["shipped_context_rows"]
    assert {r["context"] for r in rows} == CONTEXTS
    for r in rows:
        assert r["pass"] and r["errors"] == 0
        assert r["cycles_after_last_beat"] - r["formula_after_last_beat"] in (0, 1)
    assert rec["two_level"]["pass"]


@pytest.mark.skipif(not PHYS.exists(), reason="route not recorded")
def test_candidate_route_is_bound_to_the_source():
    d = json.loads(PHYS.read_text())["design"]
    assert d["clock_period_ns"] == 0.9
    for src in d["sources"]:
        assert sha(src["path"]) == src["sha256"], src["path"]
    assert d["parameters"] == {"P": 64, "WB": 64, "IW": 17, "K": 2048, "AW": 11}
