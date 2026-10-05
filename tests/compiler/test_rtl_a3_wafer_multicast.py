"""Focused evidence checks for the exact DeepSeek ROM wafer multicast RTL."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from tools import build_a3_wafer_multicast_vectors as vectors
from tools import rtl_a3_wafer_multicast_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_wafer_multicast"
RESULT = ROOT / "results/rtl/a3_wafer_multicast_campaign.json"


def test_vectors_are_byte_exact_and_source_current() -> None:
    with tempfile.TemporaryDirectory() as name:
        generated = Path(name)
        manifest = vectors.build(generated)
        for filename in campaign.VECTOR_FILES:
            assert (generated / filename).read_bytes() == (
                VECTOR_ROOT / filename
            ).read_bytes()

    source = manifest["source"]
    assert source["deployment_sha256"] == vectors.EXPECTED_DEPLOYMENT
    assert source["capability_sha256"] == vectors.EXPECTED_CAPABILITY
    assert source["pc"] == 13
    assert source["communication_descriptor_id"] == 368
    assert source["communication_prefix_hex"].startswith(
        "5441334406000100c0000000000000006d0100006e010000ffffffffffffffff"
    )


def test_vector_matrix_covers_exact_movement_and_fail_closed_boundaries() -> None:
    manifest = json.loads((VECTOR_ROOT / "index.json").read_text())
    assert manifest["geometry"] == {
        "participants": 256,
        "rounds": 8,
        "messages": 255,
        "bytes_per_message": 65536,
        "payload_bytes": 16711680,
        "words_per_message": 16384,
        "payload_flits": 4177920,
        "remote_writes_including_root": 4194304,
    }
    cases = {case["label"]: case for case in manifest["cases"]}
    assert cases["exact_pc13_multicast_crc_replay"] == {
        "index": 0,
        "label": "exact_pc13_multicast_crc_replay",
        "admitted": True,
        "refusal_reason": 0,
        "inject_crc": True,
    }
    required = {
        "wrong_pc",
        "wrong_major",
        "wrong_subopcode",
        "wrong_communication_id",
        "nonzero_view_count",
        "nonzero_state_count",
        "communication_stale_crc",
        "communication_ordering",
        "communication_scope",
        "communication_participants",
        "communication_chunk",
        "communication_extent",
        "communication_source_outside_group",
        "communication_destination_outside_group",
        "topology_stale_crc",
        "topology_reserved_nonzero",
        "topology_class",
        "topology_node_count",
        "topology_group_geometry",
        "topology_selected_group_inactive",
        "topology_selected_group_quarantined",
        "local_object_stale_crc",
        "remote_object_stale_crc",
        "local_object_permissions",
        "remote_object_permissions",
        "local_object_range",
        "remote_object_range",
        "counter_stale_crc",
        "counter_reserved_nonzero",
        "counter_id_sideband",
        "counter_group",
        "counter_event_count",
    }
    assert required <= set(cases)
    assert all(not case["admitted"] for name, case in cases.items() if name != "exact_pc13_multicast_crc_replay")


def test_adapter_compiles_with_iverilog() -> None:
    iverilog, _, _ = campaign.resolve_tools()
    with tempfile.TemporaryDirectory() as name:
        output = Path(name) / "tb.vvp"
        proc = subprocess.run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_wafer_multicast",
                "-o",
                str(output),
                *[str(ROOT / source) for source in campaign.RTL_SOURCES],
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_retained_two_simulator_campaign_is_source_current() -> None:
    assert campaign.validate_retained(RESULT) == []
    result = json.loads(RESULT.read_text())
    assert result["status"] == "pass"
    assert result["simulators_agree"]
    assert result["scope"]["exact_full_payload"]
    assert result["scope"]["packet_crc_replay_injected"]
    assert result["scope"]["architectural_tpot_claim"] is False
    assert result["normalized_cases"][0]["payload_flits"] == 4_177_920
    assert result["normalized_cases"][0]["writes"] == 4_194_304
