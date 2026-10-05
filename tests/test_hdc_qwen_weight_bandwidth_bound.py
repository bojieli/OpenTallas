"""Guard the matched memory-source bandwidth claim against unmatched inputs."""

import hashlib
import json

import pytest

from tools import rtl_hdc_qwen_weight_bandwidth_bound as gate


def _record(npc, cycles):
    summary = {"total_cycles": cycles, "generated": 0, "token_mismatches": 0,
               "logit_mismatches": 0, "vm_mismatches": 0,
               "kv_mismatches": 0}
    rom = {"pass": True, "summary": dict(summary, total_cycles=50_000),
           "steps": [{"cycles": 25_000}, {"cycles": 25_000}]}
    hbm = {"pass": True, "summary": summary,
           "steps": [{"cycles": cycles // 2}, {"cycles": cycles - cycles // 2}],
           "weights": {"weight_completed_sectors": 166_000,
                       "weight_consumed": 40_960,
                       "kv_completed_sectors": 176,
                       "weight_stall_cycles": 100_000 if npc == 1 else 1_000,
                       "embedding_stall_cycles": 200},
           "hbm_timing": {"backpressure_cycles": 0}}
    return {"status": "pass", "configuration": {"kv_hbm_pseudo_channels": npc,
             "steps_executed": 2, "weight_rate_words_x256": 50 if npc == 1 else 201},
            "rom": rom, "hbm": hbm, "source_sha256": {},
            "image_sha256": {"image": "same"}, "model_sha256": "model"}


def test_matched_bandwidth_knee_requires_exact_shared_inputs(tmp_path, monkeypatch):
    pin = tmp_path / "pin"
    pin.write_bytes(b"same compiled sources")
    digest = hashlib.sha256(pin.read_bytes()).hexdigest()
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    one, four = _record(1, 172_000), _record(4, 53_000)
    # Different channel counts can leave different speculative prefetch tails.
    four["hbm"]["weights"]["weight_completed_sectors"] -= 100
    one["source_sha256"] = four["source_sha256"] = {"pin": digest}
    one_path, four_path = tmp_path / "one.json", tmp_path / "four.json"
    one_path.write_text(json.dumps(one))
    four_path.write_text(json.dumps(four))
    result = gate.summarize(one, one_path, four, four_path)
    assert result["status"] == "pass"
    assert result["measurements"]["weight_completed_bytes"] == 166_000 * 32
    assert result["measurements"]["useful_weight_bytes_consumed"] == 40_960 * 128
    assert result["measurements"]["offered_weight_sectors_per_rom_cycle"] == 40_960 * 4 / 50_000
    assert result["measurements"]["delivered_fraction_of_peak"] > 0.98

    four["image_sha256"]["image"] = "different"
    with pytest.raises(ValueError, match="images differ"):
        gate.summarize(one, one_path, four, four_path)
    four["image_sha256"]["image"] = "same"
    four["model_sha256"] = "different"
    with pytest.raises(ValueError, match="model checkpoints differ"):
        gate.summarize(one, one_path, four, four_path)
    four["model_sha256"] = "model"
    pin.write_bytes(b"changed compiled sources")
    with pytest.raises(ValueError, match="stale source pins"):
        gate.summarize(one, one_path, four, four_path)
