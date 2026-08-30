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
