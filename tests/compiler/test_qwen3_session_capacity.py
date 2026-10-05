"""Source-current Qwen session-capacity contract across ABI 3.0 layers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.backends.rom.qwen3 import qwen3_rom_capability, qwen3_rom_policy
from compiler.frontends.v3.qwen3 import MAX_CONTEXT_TOKENS
from compiler.qwen3.constants import SESSION_CONTEXT_CAPACITY, TOKEN_BLOCK_ROWS
from compiler.workloads.qwen3 import LONG_PROMPT_TOKENS, Workload
from runtime.tensor_accelerator.rope import MAX_POSITIONS
from tools.build_qwen3_workloads import (
    _check_context_budget,
    _validate_retained_workloads,
    _validated_body,
)


ROOT = Path(__file__).resolve().parents[2]


def _long_workload(max_new_tokens: int) -> Workload:
    return Workload(
        workload_id="TA-QW-8K-1",
        kind="long_natural",
        description="capacity test",
        rendered_text="",
        token_ids=(0,) * LONG_PROMPT_TOKENS,
        max_new_tokens=max_new_tokens,
    )


def test_frozen_natural_prompt_and_decode_budget_fit_exactly() -> None:
    assert LONG_PROMPT_TOKENS == 8_000
    assert SESSION_CONTEXT_CAPACITY == MAX_CONTEXT_TOKENS == MAX_POSITIONS == 8_256
    _check_context_budget(_long_workload(256))
    assert (
        _validated_body(_long_workload(256))["metadata"][
            "session_context_capacity"
        ]
        == 8_256
    )
    with pytest.raises(ValueError, match="exceeds the 8256-position session context"):
        _validated_body(_long_workload(257))


def test_reasoning_only_merge_rejects_a_stale_or_over_budget_base(
    tmp_path: Path,
) -> None:
    workload = _validated_body(_long_workload(256))
    path = tmp_path / "TA-QW-8K-1.json"
    path.write_text(json.dumps(workload))
    records = {"TA-QW-8K-1": {"path": path.name}}
    _validate_retained_workloads(tmp_path, records)

    workload["max_new_tokens"] = 257
    path.write_text(json.dumps(workload))
    with pytest.raises(ValueError, match="exceeds the 8256-position session context"):
        _validate_retained_workloads(tmp_path, records)

    workload["max_new_tokens"] = 256
    workload["metadata"]["session_context_capacity"] = 8192
    path.write_text(json.dumps(workload))
    with pytest.raises(ValueError, match="declares session capacity 8192"):
        _validate_retained_workloads(tmp_path, records)

    workload["metadata"]["session_context_capacity"] = 8256
    workload["prompt_token_count"] = 7999
    path.write_text(json.dumps(workload))
    with pytest.raises(ValueError, match="declares 7999 prompt tokens but carries 8000"):
        _validate_retained_workloads(tmp_path, records)


def test_both_published_capabilities_admit_the_source_session() -> None:
    capability_root = ROOT / "configs/hardware/abi3_capability"
    hbm = json.loads((capability_root / "hbm_sram_single_chip.json").read_text())
    rom = json.loads((capability_root / "rom_qwen3.json").read_text())

    assert hbm["limits"]["max_context_positions"] >= SESSION_CONTEXT_CAPACITY
    assert rom["limits"]["max_context_positions"] == SESSION_CONTEXT_CAPACITY
    assert (
        qwen3_rom_capability().limits["max_context_positions"]
        == SESSION_CONTEXT_CAPACITY
    )


def test_rom_uses_the_frozen_hbm_token_block_association() -> None:
    assert TOKEN_BLOCK_ROWS == 512
    assert qwen3_rom_policy().token_block_rows == TOKEN_BLOCK_ROWS
