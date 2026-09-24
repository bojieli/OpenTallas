"""The KV-in-HBM record of the hardwired decode core is current and says what it claims."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import rtl_hdc_kv_stream_campaign as campaign  # noqa: E402

needs_checkpoint = pytest.mark.skipif(
    not G.CHECKPOINT.exists(), reason="build the reduced checkpoint: tools/build_qwen3_reduced_model.py")


def record():
    return json.loads(campaign.OUT.read_text())


def test_record_is_current():
    for name, digest in record()["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_record_passes_and_every_hbm_run_is_bit_exact():
    rec = record()
    assert rec["status"] == "pass" and all(rec["checks"].values())
    for run in ("single_step", "long_context", "prompt60_from_empty"):
        r = rec["runs"][run]
        assert r["next_token"] == r["isa_next_token"]
        assert r["logit_mismatches"] == r["vector_memory_mismatches"] == r["kv_cache_mismatches"] == 0
        assert r["fault"] == r["stream_fault"] == r["delivered_word_mismatches"] == 0
    e2e = rec["runs"]["end_to_end"]
    assert e2e["generated_tokens"] == e2e["oracle_generated_tokens"] == [1073, 382, 93]


def test_underflow_is_detected_not_silent():
    rec = record()
    assert rec["runs"]["unit_unprovisioned_npc4"]["verdict"] == "FAULT_DETECTED"
    for lead in (0, 32, 128):
        assert rec["runs"][f"lead_{lead}"]["outcome"] in ("bit_exact", "underflow_detected")


def test_lead_and_bandwidth_are_tied_to_their_sources():
    rec = record()
    assert rec["lead"]["lead_cycles"] >= rec["lead"]["worst_single_fetch_latency_cycles"]
    tech = json.loads((ROOT / "configs/hardware/technology.json").read_text())
    stack = tech["hbm"]["hbm3e"]["stack_bandwidth_bytes_s"]["value"]
    assert rec["hbm_model"]["stack_bandwidth_bytes_s"] == stack
    # a 32-byte burst on a 32-bit pseudo-channel, 32 of them sharing the stack's bandwidth
    pin_bps = stack * 8 / (32 * 32)
    assert abs(rec["hbm_model"]["timings_ps"]["BURST_PS"] - 32 * 8 / 32 / pin_bps * 1e12) < 1


def test_sram_configuration_is_unchanged():
    rec = record()
    decode = json.loads((ROOT / "results/rtl/hdc_decode_campaign.json").read_text())
    assert rec["runs"]["sram_single_step"]["cycles"] == decode["single_step"]["cycles"]
    assert rec["runs"]["sram_long_context"]["cycles"] == decode["long_context"]["cycles"]


@needs_checkpoint
def test_timing_model_tracks_the_hbm_rtl():
    import hdc_program as P
    import hdc_timing as T
    rec = record()
    assert T.KV == rec["timing_model"]["constants"]
    for ctx, run in ((None, "single_step"), (60, "long_context")):
        model, prompt, _, _ = P.golden_state(ctx)
        cycles = T.simulate(P.build_program(P.Layout(model)), len(prompt) - 1, kv=T.KV)[1]
        rtl = rec["runs"][run]["cycles"]
        assert abs(cycles - rtl) / rtl < 0.005
