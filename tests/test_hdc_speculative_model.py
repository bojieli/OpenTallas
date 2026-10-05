"""Checks for tools/hdc_speculative_model.py, the design-faithful speculative-decoding model of the HDC."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_critical_path as D  # noqa: E402
import hdc_speculative_model as H  # noqa: E402

RECORD = ROOT / "results/roofline/speculative/hdc_design_faithful.json"


@pytest.fixture(scope="module")
def env():
    return H.Env()


def test_gamma0_reproduces_the_qwen_reticle_record(env):
    """n = 1, m = 1 is the autoregressive token: the committed critical-path record, to rounding."""
    rec = json.loads(H.CRIT_RECORD.read_text())["qwen3_8b_single_reticle"]
    tgt = H.qwen_target(env, 1, rec["context_tokens"])
    _, r = H.verify(env, tgt, 1, 1)
    assert r["period"] == pytest.approx(rec["token_period_s"], rel=1e-9)
    assert 1 / r["period"] == pytest.approx(rec["tokens_s_per_user"], rel=1e-9)


@pytest.mark.parametrize("batch", [1, 64])
def test_gamma0_reproduces_the_option_b_headline(env, batch):
    """n = 1, m = 1 on the V4.1 array is decode_critical_path's headline machine (packaging option b)."""
    opt = D.packaging("b")
    m = D.v41_machine("array", opt["group"], batch, env.points, env.designs, env.p, env.clock,
                      placement=D.HEADLINE_PLACEMENT)
    b = D.Built(m, env.p, env.clock, D.v41_graph, env.c, m.context)
    ref = b.evaluate(D.default_fabric("array", env.links, opt["group"]))
    _, r = H.verify(env, H.v41_target(env, batch, m.context), 1, 1)
    assert r["T"] == pytest.approx(ref["T"], rel=1e-9)
    assert r["period"] == pytest.approx(ref["period"], rel=1e-9)


def test_verification_is_monotone_in_positions_and_lanes(env):
    tgt = H.qwen_target(env, 1, 2048)
    T = {(n, m): H.verify(env, tgt, n, m)[1]["T"] for n in (1, 2, 4, 8, 17) for m in (1, 2, 4, 8, 16)}
    for m in (1, 2, 4, 8, 16):
        seq = [T[(n, m)] for n in (1, 2, 4, 8, 17)]
        assert all(b >= a - 1e-15 for a, b in zip(seq, seq[1:])), m
    for n in (1, 2, 4, 8, 17):
        seq = [T[(n, m)] for m in (1, 2, 4, 8, 16)]
        assert all(b <= a + 1e-15 for a, b in zip(seq, seq[1:])), n
    # extra MAC lanes buy nothing once every position has one (the matrix engine saturates)
    assert T[(8, 8)] == pytest.approx(T[(8, 16)], rel=1e-12)
    # a verification pass costs less than n autoregressive tokens: every latency is paid once
    assert T[(8, 1)] < 8 * T[(1, 1)]


def test_engine_passes_are_ceil_positions_over_lanes(env):
    tgt = H.qwen_target(env, 1, 2048)
    for n, m in ((8, 1), (8, 3), (17, 4), (17, 16)):
        ps, _ = H.verify(env, tgt, n, m)
        passes = {nd["engine_passes"] for nd in ps.g.nodes.values() if nd.get("sweep")}
        assert passes == {math.ceil(n / m)}


def test_latencies_are_paid_once_per_pass(env):
    """Control (sequencer issue gaps and barriers) does not scale with the positions of a pass."""
    tgt = H.qwen_target(env, 1, 2048)
    ar = H.verify(env, tgt, 1, 1)[1]["breakdown_us"]["control"]
    v = H.verify(env, tgt, 17, 16)[1]["breakdown_us"]["control"]
    assert v == pytest.approx(ar, rel=0.05)


def test_draft_passes_are_monotone_and_positive(env):
    tgt = H.v41_target(env, 1, 8192)
    d = [H.v41_draft(env, tgt, g, 1)[1]["T"] for g in (1, 3, 5, 7)]
    assert all(x > 0 for x in d)
    assert all(b >= a for a, b in zip(d, d[1:]))
    # the DSpark draft is a few MTP layers, not a sweep of the target: far below one AR token
    ar = H.verify(env, tgt, 1, 1)[1]["T"]
    assert d[-1] < ar


def test_program_replay_law_is_identity_at_one_position():
    assert H.program_replay(1, 1, groups=64) == H.program_replay(1, 16, groups=64)
    assert H.program_replay(4, 1, groups=64) >= H.program_replay(4, 4, groups=64)


def test_head_divisibility():
    assert H.head_class("Qwen3-8B", 8) == "kv_split"
    assert H.head_class("Qwen3-8B", 32) == "kv_replicated"
    for tg in (25, 29, 31, 38, 50, 58, 64, 72):
        assert H.head_class("Qwen3-8B", tg) == "infeasible"


def test_survival_derivation_is_inside_its_bounds():
    d = H.v4_survival_derivation()
    lo, hi = d["hard_bounds"]["low"], d["hard_bounds"]["high"]
    for k in ("geometric", "linear"):
        assert lo < d[k]["tau"] < hi
        s = d[k]["survival"]
        assert s[0] == pytest.approx(0.70) and s[-1] == pytest.approx(0.10)
        assert all(b <= a + 1e-12 for a, b in zip(s, s[1:]))


@pytest.mark.skipif(not RECORD.exists(), reason="record not generated")
def test_record_is_consistent():
    rec = json.loads(RECORD.read_text())
    assert rec["schema"] == H.SCHEMA
    # every speculative rate is tau / cycle, and every tau on a curve is a grid rung or a cited point
    cited = {p["tau"] for k in ("v41", "qwen") for p in rec["tau"][k]}
    for key, t in rec["targets"].items():
        for ctx, bys in t["contexts"].items():
            for bt, cell in bys.items():
                for gm, g in cell["gamma"].items():
                    roms = [g["rom"]] if key.startswith("deepseek") else list(g["rom"].values())
                    for rom in roms:
                        for v, byv in rom.items():
                            for m, r in byv.items():
                                for tau, c in r["curve"].items():
                                    t_ = float(tau)
                                    assert t_ <= int(gm) + 1
                                    assert t_ in cited or t_ in H.TAU_GRID
                                    assert c["tokens_s_per_user"] == pytest.approx(t_ / r["cycle_s"], rel=1e-9)
    for p in rec["tau"]["v41"] + rec["tau"]["qwen"]:
        assert p["grade"] in ("published", "derived") and p["source"]
    for key, r in rec["summary"]["recommendation"].items():
        assert r["recommended_m"] in H.M_LADDER
    for blk, v in rec["summary"]["verdict"]["by_gpu_block"].items():
        n_opts = sum(len(r["by"]) for r in rec["summary"]["rows"] if blk in r["gpu"])
        assert v["spec_vs_spec"]["narrowing"] + v["spec_vs_spec"]["not_narrowing"] == n_opts, blk
    hl = rec["summary"]["verdict"]["headline_gpu"]["spec_vs_spec"]
    assert hl["narrowing"] + hl["not_narrowing"] == sum(len(r["by"]) for r in rec["summary"]["rows"])
    # today's hardware (m = 1) never widens the ratio against any GPU level
    for blk, v in rec["summary"]["verdict"]["today_m1"].items():
        assert v["not_narrowing"] == 0, blk
    # the GPU calibration reproduces DFlash's measured single-B200 rates within its stated 5%
    cal = rec["gpu_calibration"]
    assert cal["passes"]
    for r in cal["concurrency_1"]:
        assert abs(r["dflash_error"]) <= 0.05 and abs(r["ar_error"]) <= 0.05
    # the feasible GPU blocks never use a tensor group that cannot split the heads
    for key, t in rec["targets"].items():
        for bys in t["contexts"].values():
            for cell in bys.values():
                for g in cell["gamma"].values():
                    for blk in [b for b in g["gpu"] if b != "idealised" and isinstance(g["gpu"][b], dict) and "ar" in g["gpu"][b]]:
                        assert g["gpu"][blk]["ar"]["head_class"] != "infeasible"
                        assert g["gpu"][blk]["spec"]["draft_kv_low"]["head_class"] != "infeasible"
    assert set(rec["sources"]) >= {"tools/hdc_speculative_model.py", "tools/decode_critical_path.py",
                                   "tools/hdc_timing.py", "configs/studies/speculative_profiles.json"}
