from __future__ import annotations

import hashlib
from pathlib import Path
import shutil

import pytest

from compiler.tensor_accelerator.common import canonical_json_bytes, load_strict_json
from tools import build_abi3_tensor_lane_mapper_vectors as vector_builder
from tools import run_abi3_tensor_lane_mapper_campaign as campaign_runner


ROOT = Path(__file__).resolve().parents[2]
VECTORS = ROOT / "testdata/rtl/abi3_tensor_lane_mapper_vectors.json"
CAMPAIGN = ROOT / "results/rtl/abi3_tensor_lane_mapper_campaign.json"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _identity(value: dict[str, object], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def test_lane_mapper_vectors_are_canonical_source_bound_and_complete() -> None:
    vectors = load_strict_json(VECTORS)
    assert VECTORS.read_bytes() == canonical_json_bytes(vectors)
    assert vectors["schema"] == vector_builder.SCHEMA
    assert vectors["vector_set_id"] == _identity(vectors, "vector_set_id")
    assert vectors["hardware"] == {
        "issue_groups": 4,
        "lanes": 256,
        "lanes_per_group": 64,
    }
    assert vectors["coverage"] == {
        "backpressure_required": True,
        "case_count": 34,
        "invalid_case_count": 5,
        "logical_output_count": 498429,
        "source_bound_real_shape_count": 6,
        "wave_count": 2065,
    }
    assert vectors["claim_boundary"] == {
        "complete_model_token_generated": False,
        "integrated_tensor_datapath": False,
        "standalone_lane_control_rtl": True,
        "target_tpot": False,
    }
    for source in vectors["sources"].values():
        path = Path(source["path"])
        if not path.is_absolute():
            path = ROOT / path
        assert path.is_file()
        assert _sha256_file(path) == source["sha256"]


def test_lane_mapper_vectors_cover_every_coordinate_exactly_once() -> None:
    vectors = load_strict_json(VECTORS)
    names = {case["name"] for case in vectors["cases"]}
    assert {
        "row_boundary_1",
        "row_boundary_256",
        "row_boundary_257",
        "column_boundary_63",
        "column_boundary_64",
        "column_boundary_65",
        "qwen_decode_hidden",
        "qwen_prefill_tile_hidden",
        "qwen_batch8_decode_hidden",
        "qwen_decode_intermediate",
        "qwen_vocabulary_head",
        "qwen_exact_8k_row_extent",
        "u32_schedule_product_no_wrap",
    } <= names
    for case in vectors["cases"]:
        config = case["config"]
        expected = case["expected"]
        if expected["error_code"] != 0:
            assert expected["error_code"] == vector_builder.ERR_SHAPE
            assert expected["waves"] == []
            assert expected["logical_output_count"] == 0
            continue
        seen: set[tuple[int, int]] = set()
        active_total = 0
        folded_total = 0
        for wave_index, wave in enumerate(expected["waves"]):
            assert 1 <= wave["rows"] <= 256
            assert 1 <= wave["cols_per_row"] <= 256 // wave["rows"]
            assert wave["active_lanes"] == wave["rows"] * wave["cols_per_row"]
            assert int(wave["lane_valid_hex"], 16) == (1 << wave["active_lanes"]) - 1
            assert wave["group_active_counts"] == [
                min(64, max(0, wave["active_lanes"] - group * 64)) for group in range(4)
            ]
            assert wave["last"] == (wave_index == len(expected["waves"]) - 1)
            for local_row in range(wave["rows"]):
                for local_col in range(wave["cols_per_row"]):
                    coordinate = (
                        wave["row_base"] + local_row,
                        wave["col_base"] + local_col,
                    )
                    assert coordinate not in seen
                    assert coordinate[0] < config["rows"]
                    assert coordinate[1] < config["cols"]
                    seen.add(coordinate)
            active_total += wave["active_lanes"]
            folded_total += wave["active_lanes"] - wave["rows"]
        assert len(seen) == config["rows"] * config["cols"]
        assert len(expected["waves"]) == expected["wave_count"]
        assert active_total == expected["active_lane_slots"] == len(seen)
        assert expected["logical_output_count"] == len(seen)
        assert folded_total == expected["row_folded_output_count"]
        assert expected["masked_lane_slots"] == len(expected["waves"]) * 256 - len(seen)


def test_lane_mapper_builder_reproduces_retained_vectors() -> None:
    assert canonical_json_bytes(vector_builder.build()) == VECTORS.read_bytes()


def test_lane_mapper_retained_campaign_is_dual_simulator_and_fail_closed() -> None:
    campaign = load_strict_json(CAMPAIGN)
    vectors = load_strict_json(VECTORS)
    assert CAMPAIGN.read_bytes() == canonical_json_bytes(campaign)
    assert campaign["schema"] == campaign_runner.SCHEMA
    assert campaign["campaign_id"] == _identity(campaign, "campaign_id")
    assert campaign["status"] == "pass"
    assert campaign["observations_identical"]
    assert campaign["coverage"] == vectors["coverage"]
    assert campaign["vector_set_id"] == vectors["vector_set_id"]
    assert campaign["vector_file_sha256"] == _sha256_file(VECTORS)
    assert [case["name"] for case in campaign["simulators"]] == [
        "iverilog",
        "verilator",
    ]
    assert all(case["status"] == "pass" for case in campaign["simulators"])
    assert (
        len(
            {
                canonical_json_bytes(case["observation"])
                for case in campaign["simulators"]
            }
        )
        == 1
    )
    assert campaign["claim_boundary"] == {
        "complete_model_token_generated": False,
        "host_verification_time_is_target_tpot": False,
        "integrated_tensor_datapath": False,
        "standalone_lane_control_rtl": True,
        "target_tpot": False,
    }
    for relative, expected_digest in campaign["sources"].items():
        assert _sha256_file(ROOT / relative) == expected_digest


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("iverilog", "vvp"))
    or not (
        campaign_runner.TOOLS_ROOT
        / f"verilator-{campaign_runner.PINNED_VERILATOR_VERSION}/bin/verilator"
    ).is_file(),
    reason="the pinned dual-simulator toolchain is unavailable",
)
def test_lane_mapper_focused_campaign_replays() -> None:
    replay = campaign_runner.run(VECTORS)
    retained = load_strict_json(CAMPAIGN)
    assert replay["status"] == "pass"
    assert replay["observations_identical"]
    assert replay["vector_set_id"] == retained["vector_set_id"]
    assert [case["observation"] for case in replay["simulators"]] == [
        case["observation"] for case in retained["simulators"]
    ]
