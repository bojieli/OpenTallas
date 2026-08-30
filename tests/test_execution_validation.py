"""The join between the analytical model and the machine that executed tokens.

These tests do not check that the accelerator is fast.  They check that the
*quantities* a roofline divides by bandwidth are the quantities a real decode
actually moved, and -- just as important -- that the check would notice if they
were not.  A validator that cannot fail is not evidence.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from opentallas.schema import ModelProfile  # noqa: E402
from tools.validate_model_against_execution import (  # noqa: E402
    _causal_position_reads,
    _kv_bytes_per_layer_position,
)

TOOL = ROOT / "tools/validate_model_against_execution.py"
QWEN = ROOT / "configs/models/qwen3-8b.json"
CHAT_HBM = ROOT / "results/abi3/qwen3_hbm_ta-qw-chat-1_execution.json"
CHAT_ROM = ROOT / "results/abi3/qwen3_rom_ta-qw-chat-1_execution.json"


def _brute_force_pairs(prompt: int, decode: int) -> int:
    """The definition, written the slow obvious way."""

    total = 0
    context = 0
    for _ in range(prompt):  # prefill: one query per prompt token
        context += 1
        total += context
    for _ in range(decode):  # decode: one query per generated token
        context += 1
        total += context
    return total


@pytest.mark.parametrize(
    "prompt,decode",
    [(1, 0), (1, 1), (8, 3), (128, 24), (8000, 192)],
)
def test_causal_pair_count_is_the_definition(prompt: int, decode: int) -> None:
    assert _causal_position_reads(prompt, decode) == _brute_force_pairs(prompt, decode)


def test_kv_entry_size_is_taken_from_the_profile_not_restated() -> None:
    model = ModelProfile.load(QWEN)
    entry = _kv_bytes_per_layer_position(model, 8192)
    # One K row and one V row, eight key/value heads, 128 elements, BF16.
    assert entry == pytest.approx(2 * 8 * 128 * 2)
    # It must not depend on the context it is evaluated at.
    assert _kv_bytes_per_layer_position(model, 1024) == pytest.approx(entry)


def _run(tmp_path: Path, *executions: Path) -> tuple[int, dict]:
    out = tmp_path / "validation.json"
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--model", str(QWEN), "--context", "8192",
         "--output", str(out), "--force",
         *[arg for path in executions for arg in ("--execution", str(path))]],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    return proc.returncode, json.loads(out.read_text()) if out.exists() else {}


@pytest.mark.skipif(
    not (CHAT_HBM.is_file() and CHAT_ROM.is_file()),
    reason="executed Qwen records are unavailable",
)
def test_both_lanes_move_exactly_the_kv_traffic_the_profile_predicts(tmp_path) -> None:
    code, body = _run(tmp_path, CHAT_HBM, CHAT_ROM)
    assert code == 0, body.get("problems")
    assert body["status"] == "pass"
    assert body["arithmetic_agreement_across_lanes"] is True
    for lane in body["lanes"]:
        kv = lane["kv"]
        # The KV term carries nothing but KV, so it is exact, not approximate.
        assert kv["byte_ratio"] == pytest.approx(1.0, abs=1e-9)
        assert kv["position_ratio"] == pytest.approx(1.0, abs=1e-9)
        assert kv["measured_bytes_per_layer_position"] == pytest.approx(4096.0)


@pytest.mark.skipif(not CHAT_HBM.is_file(), reason="no executed record")
def test_the_check_fails_when_the_machine_skips_kv_reads(tmp_path) -> None:
    """A validator nobody can fail is decoration.  Break the record; expect a fail."""

    body = json.loads(CHAT_HBM.read_text())
    counters = body["record"]["counters"]
    counters["attention.kv_bytes_read"] = int(
        counters["attention.kv_bytes_read"] * 0.5
    )
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(body))

    code, out = _run(tmp_path, tampered)
    assert code == 2
    assert out["status"] == "fail"
    assert any("KV read traffic" in problem for problem in out["problems"])


@pytest.mark.skipif(not CHAT_HBM.is_file(), reason="no executed record")
def test_the_check_fails_when_attention_skips_context_positions(tmp_path) -> None:
    body = json.loads(CHAT_HBM.read_text())
    counters = body["record"]["counters"]
    # A machine attending to a fixed window rather than the whole causal past
    # would report far fewer pairs while still reading 4096 bytes for each.
    counters["attention.context_positions"] = int(
        counters["attention.context_positions"] * 0.8
    )
    counters["attention.kv_bytes_read"] = counters["attention.context_positions"] * 4096
    tampered = tmp_path / "windowed.json"
    tampered.write_text(json.dumps(body))

    code, out = _run(tmp_path, tampered)
    assert code == 2
    assert any("causal attention" in problem for problem in out["problems"])


# --- the sparse KV model, against the engine that ran it ----------------------

#: The live ladder is rebuilt as rungs are added, so a test that reads it races a
#: running oracle. The pinned snapshot is what justified the profile correction and
#: does not move; the live ladder is checked separately, when it carries measurements.
DS_SNAPSHOT = ROOT / "testdata/roofline/deepseek_v4_kv_measurement_snapshot.json"
DS_ORACLE = ROOT / "results/abi3/deepseek_v4_reference_oracle_context_ladder.json"
DS_MODEL = ROOT / "configs/models/deepseek-v4-flash-0731.json"
KV_TOOL = ROOT / "tools/validate_kv_model_against_oracle.py"


def _run_kv(tmp_path: Path, model: Path, oracle: Path) -> tuple[int, dict]:
    out = tmp_path / "kv.json"
    proc = subprocess.run(
        [sys.executable, str(KV_TOOL), "--model", str(model), "--oracle", str(oracle),
         "--output", str(out), "--force"],
        capture_output=True, text=True, cwd=ROOT,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'src'}", "PATH": "/usr/bin:/bin"},
    )
    return proc.returncode, json.loads(out.read_text()) if out.exists() else {}


def _ladder_has_kv() -> bool:
    """The ladder is rebuilt as rungs are added, so it may transiently carry none."""

    if not DS_ORACLE.is_file():
        return False
    body = json.loads(DS_ORACLE.read_text())
    return any(
        (rung.get("kv_measurement") or {}).get("decode_steps")
        for rung in body.get("results", {}).values()
    )


@pytest.mark.skipif(not DS_SNAPSHOT.is_file(), reason="no pinned KV snapshot")
def test_the_sparse_kv_model_matches_the_engine_at_every_measured_context(tmp_path) -> None:
    """The term the ROM argument rests on, checked where it is hardest.

    A dense model's KV traffic is arithmetic. A sparse model's is whatever its
    own routing selected, so this is the profile field most likely to be wrong
    and least likely to be noticed -- and it was wrong by 2.7-3.1x until it was
    measured rather than read off the implementation.
    """

    code, body = _run_kv(tmp_path, DS_MODEL, DS_SNAPSHOT)
    assert code == 0, body.get("problems")
    assert body["status"] == "pass"
    assert len(body["rungs"]) >= 2, "one rung cannot distinguish a scale error from a slope error"
    for rung in body["rungs"]:
        assert rung["ratio"] == pytest.approx(1.0, abs=0.01)


@pytest.mark.skipif(not DS_SNAPSHOT.is_file(), reason="no pinned KV snapshot")
def test_the_check_fails_on_the_entry_sizes_it_was_built_to_catch(tmp_path) -> None:
    """Restore the pre-measurement constants; the check must reject them.

    This is the actual historical defect, not an invented one: 583 bytes per KV
    entry and 68 per index entry, which under-predicted by 2.7x at 32,000 tokens
    and 3.1x at 128,000 -- growing with context, because the index term carried
    the larger error and grows fastest.
    """

    profile = json.loads(DS_MODEL.read_text())
    for group in profile["attention_groups"]:
        group["entry_bytes"] = 583
        if group["index_entry_bytes"]:
            group["index_entry_bytes"] = 68.0
    stale = tmp_path / "stale_profile.json"
    stale.write_text(json.dumps(profile))

    code, body = _run_kv(tmp_path, stale, DS_SNAPSHOT)
    assert code == 2
    assert body["status"] == "fail"
    assert len(body["problems"]) == len(body["rungs"])
    ratios = {r["context_tokens"]: r["ratio"] for r in body["rungs"]}
    assert min(ratios.values()) > 2.5
    # The error grows with context; a pure scale error would not.
    ordered = [ratios[c] for c in sorted(ratios)]
    assert ordered == sorted(ordered)


@pytest.mark.skipif(not CHAT_HBM.is_file(), reason="no executed record")
def test_the_decode_share_is_separated_from_prefill(tmp_path) -> None:
    """A roofline models a decode step, so it must be told which bytes those are.

    The logical KV count is dominated by prefill's causal triangle at long
    context, and prefill's logical and physical reads diverge because a real
    implementation blocks. For a decode step they coincide. Reporting only the
    total would invite a reader to divide the wrong number by KV bandwidth.
    """

    code, body = _run(tmp_path, CHAT_HBM)
    assert code == 0
    kv = body["lanes"][0]["kv"]
    decode = kv["decode_only"]
    assert 0 < decode["pairs"] < kv["measured_context_positions"]
    assert decode["bytes"] == pytest.approx(
        decode["pairs"] * kv["profile_bytes_per_layer_position"]
    )
    # Prefill and decode must partition the causal pairs exactly, with nothing
    # left over: that is what makes the split a decomposition and not an estimate.
    body_record = json.loads(CHAT_HBM.read_text())["record"]
    prompt = int(body_record["workload"]["prompt_token_count"])
    layers = 36
    prefill_pairs = layers * (prompt * (prompt + 1) // 2)
    assert prefill_pairs + decode["pairs"] == kv["predicted_context_positions"]


@pytest.mark.skipif(not _ladder_has_kv(), reason="the live ladder carries no KV measurement yet")
def test_the_live_ladder_agrees_with_the_profile_wherever_it_has_measured(tmp_path) -> None:
    """The pinned snapshot must not become a place where a stale number hides.

    Whenever the reference oracle has measured a rung, the profile must match it
    too -- so a later re-run that disagrees with the snapshot surfaces here
    rather than being masked by the pin.
    """

    code, body = _run_kv(tmp_path, DS_MODEL, DS_ORACLE)
    assert code == 0, body.get("problems")
    for rung in body["rungs"]:
        assert rung["ratio"] == pytest.approx(1.0, abs=0.01)
