"""The HBM comparator record of the hardwired decode core is current and says what it claims."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import rtl_hdc_hbm_campaign as campaign  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced checkpoint: tools/build_qwen3_reduced_model.py")
needs_record = pytest.mark.skipif(not campaign.OUT.exists(), reason="run tools/rtl_hdc_hbm_campaign.py")


def record():
    return json.loads(campaign.OUT.read_text())


@needs_record
def test_record_is_current():
    for name, digest in record()["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


@needs_record
def test_record_passes():
    rec = record()
    assert rec["status"] == "pass" and all(rec["checks"].values())


@needs_record
def test_qwen_weights_and_kv_in_hbm_are_bit_exact_at_every_provisioning():
    q = record()["qwen3"]
    for n in campaign.SWEEP:
        r = q["runs"][f"single_npc{n}"]
        assert r["next_token"] == r["isa_next_token"] == 1073
        assert r["logit_mismatches"] == r["vector_memory_mismatches"] == r["kv_cache_mismatches"] == 0
        s = r["stream"]
        assert s["ws_fault"] == s["kvs_fault"] == s["wq_bad"] == s["kvq_bad"] == 0
        # every weight word the engine read came from HBM and matched the ROM image
        assert s["w_words"] == q["configuration"]["weight_image"]["stream_words"] + 128
    for n in campaign.E2E_NPC:
        e = q["runs"][f"e2e_npc{n}"]
        assert e["generated_tokens"] == e["oracle_generated_tokens"] == [1073, 382, 93]


@needs_record
def test_underflow_is_detected_not_silent():
    rec = record()
    q = rec["qwen3"]["runs"]
    assert q["unit_unprovisioned_npc2"]["verdict"] == "FAULT_DETECTED"
    assert q["failclosed_rate_npc2"]["outcome"] == "underflow_detected"
    assert q["failclosed_lead0_npc4"]["outcome"] in ("bit_exact", "underflow_detected")
    if rec.get("v41"):
        assert rec["v41"]["runs"]["failclosed_lead0_npc4"]["outcome"] in ("bit_exact", "underflow_detected")


@needs_record
def test_the_sweep_finds_the_bandwidth_knee():
    q = record()["qwen3"]
    rows = {r["pseudo_channels"]: r for r in q["sweep"]}
    # starved channels are bandwidth-bound and slower than the ROM; enough channels are compute-bound
    assert rows[1]["bound"] == "hbm_bandwidth" and rows[1]["hbm_over_rom"] > 2
    assert rows[32]["bound"] == "compute" and rows[32]["hbm_over_rom"] < 1.05
    assert q["knee_pseudo_channels"] in rows


@needs_record
@needs_checkpoint
def test_timing_model_tracks_the_rtl():
    import hdc_program as P
    import hdc_timing as T
    rec = record()
    q = rec["qwen3"]
    assert T.WH == q["timing_model"]["constants"]
    assert all(abs(f["error_pct"]) < (1.5 if f["refresh_collision"] else 0.5) for f in q["timing_model"]["fits"])
    assert sum(f["refresh_collision"] for f in q["timing_model"]["fits"]) <= 1
    model, prompt, _, _ = P.golden_state()
    prog = P.build_program(P.Layout(model), wchunk=campaign.WCHUNK)
    for n in campaign.SWEEP:
        rtl = q["runs"][f"single_npc{n}"]["cycles"]
        cyc, _ = campaign.model_single(prog, len(prompt) - 1, n, q["configuration"]["guaranteed_rate_x256"][str(n)])
        tol = 0.015 if q["runs"][f"single_npc{n}"]["stream"]["kv_stall_cycles"] >= 250 else 0.005
        assert abs(cyc - rtl) / rtl < tol, (n, cyc, rtl)
    if rec.get("v41"):
        fits = rec["v41"]["timing_model"]["fits"]
        assert all(abs(f["error_pct"]) < (1.5 if f["non_monotonic_outlier"] else 0.5) for f in fits)
        assert sum(f["non_monotonic_outlier"] for f in fits) <= 1


@needs_checkpoint
def test_chunked_program_computes_the_same_token():
    """Round chunks of the weight ops (and the argmax fold) change nothing numerically."""
    import hdc_program as P
    model, prompt, _, cache = P.golden_state()
    lay = P.Layout(model)
    token, pos = prompt[-1], len(prompt) - 1
    kv = lay.kv_image(cache)
    a, b = P.Machine(lay, kv), P.Machine(lay, kv)
    ta = a.run(P.build_program(lay), token, pos)
    tb = b.run(P.build_program(lay, wchunk=campaign.WCHUNK), token, pos)
    assert ta == tb
    assert np.array_equal(G.bits(a.logits), G.bits(b.logits)) and np.array_equal(G.bits(a.vm), G.bits(b.vm))


@needs_checkpoint
def test_hbm_weight_image_is_the_stream_in_consumption_order():
    import hdc_program as P
    model, _, _, _ = P.golden_state()
    lay = P.Layout(model)
    prog = P.build_program(lay, wchunk=campaign.WCHUNK)
    img = P.hbm_weight_image(lay, prog)
    stream = P.weight_stream(prog)
    spw = img["meta"]["sectors_per_word"]
    for n in (0, 1, len(stream) // 2, len(stream) - 1):
        word = sum(int(img["sectors"][n * spw + j]) << (256 * j) for j in range(spw))
        assert word == P.pack_lanes(lay.words[stream[n]], 16)
    assert img["meta"]["stream_words"] == len(stream) == img["args"]["ntot"]


@needs_record
def test_projections_cite_their_sources():
    p = record()["projections"]
    q = p["qwen3_8b"]
    for b in q["analytical_rom"].values():
        path, sel = b["source"].split("#", 1)
        assert (ROOT / path).exists()
    for row in q["rows"]:
        assert row["cycles_hbm"] >= row["cycles_rom_kv_hbm"] * 0.999
    for row in p["deepseek_v41_flash"]["rows"]:
        assert row["batch1"]["hbm_over_rom_time"] >= 1.0
