from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from runtime.abi3.deployment import ObjectSource, Segment
from tools import build_rom_service_vectors as vectors
from tools import rtl_rom_service_campaign as campaign


def test_executed_stream_source_boundary_covers_admission_and_all_engines() -> None:
    recorded = vectors.runtime_digests()
    required = {
        "runtime/abi3/capability.py",
        "runtime/abi3/verifier.py",
        "runtime/sim/counters.py",
        "runtime/sim/generators.py",
        "runtime/sim/engines/deepseek_vector.py",
        "runtime/sim/engines/link.py",
        "runtime/sim/engines/reduction.py",
        "runtime/sim/engines/route.py",
    }
    assert required <= recorded.keys()
    assert set(campaign.REQUIRED_EXECUTED_SOURCE_PATHS) <= recorded.keys()


def test_campaign_rejects_an_executed_stream_missing_required_source_pins(
    tmp_path: Path,
) -> None:
    for name in campaign.IMAGE_FILES:
        (tmp_path / name).write_bytes(b"")
    manifest = {
        "image_sha256": {
            name: hashlib.sha256(b"").hexdigest() for name in campaign.IMAGE_FILES
        },
        "executed_source": {
            "runtime_source_sha256": {
                "runtime/sim/device.py": vectors.runtime_digests()[
                    "runtime/sim/device.py"
                ]
            }
        },
    }
    (tmp_path / "rom_service_vectors.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    loaded = campaign.load_vector_set(tmp_path)

    assert "runtime/abi3/verifier.py" in loaded["_runtime_source_missing"]
    assert "runtime/sim/engine.py" in loaded["_runtime_source_missing"]
    assert loaded["_runtime_source_drift"] == []


def test_plan_derived_set_does_not_invent_an_executed_source_requirement(
    tmp_path: Path,
) -> None:
    for name in campaign.IMAGE_FILES:
        (tmp_path / name).write_bytes(b"")
    manifest = {
        "image_sha256": {
            name: hashlib.sha256(b"").hexdigest() for name in campaign.IMAGE_FILES
        },
        "executed_source": {},
    }
    (tmp_path / "rom_service_vectors.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    loaded = campaign.load_vector_set(tmp_path)

    assert loaded["_runtime_source_missing"] == []
    assert loaded["_runtime_source_drift"] == []


def test_campaign_rehashes_repo_relative_loaded_inputs(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(campaign, "ROOT", tmp_path)
    vector_dir = tmp_path / "vectors"
    vector_dir.mkdir()
    for name in campaign.IMAGE_FILES:
        (vector_dir / name).write_bytes(b"")
    capability = tmp_path / "capability.json"
    workload = tmp_path / "workload.json"
    capability.write_bytes(b"capability\n")
    workload.write_bytes(b"workload\n")
    manifest = {
        "image_sha256": {
            name: hashlib.sha256(b"").hexdigest() for name in campaign.IMAGE_FILES
        },
        "executed_source": {
            "runtime_source_sha256": {},
            "loaded_inputs": {
                "capability": {
                    "path": "capability.json",
                    "sha256": hashlib.sha256(capability.read_bytes()).hexdigest(),
                },
                "workload": {
                    "path": "workload.json",
                    "sha256": hashlib.sha256(workload.read_bytes()).hexdigest(),
                },
            },
            "checkpoint_binding": {
                "authenticated_range_count": 1,
                "range_map_sha256": "34" * 32,
                "verified_on_device_activation": True,
            },
            "deployment_admitted": True,
            "events_not_expressible_as_contiguous_ranges": 0,
            "failure": None,
        },
    }
    (vector_dir / "rom_service_vectors.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    loaded = campaign.load_vector_set(vector_dir)
    assert loaded["_executed_source_integrity_problems"] == []

    workload.write_bytes(b"changed\n")
    loaded = campaign.load_vector_set(vector_dir)
    assert loaded["_executed_source_integrity_problems"] == [
        "loaded input workload moved: workload.json"
    ]


def test_checkpoint_binding_identity_is_range_bound_and_location_independent() -> None:
    digest = "12" * 32
    source = ObjectSource(
        kind="segments",
        size_bytes=4,
        segments=(Segment("checkpoint/model.safetensors", 17, 4, digest),),
    )
    deployment = SimpleNamespace(objects={9: source})

    identity = vectors.checkpoint_binding_identity(deployment)

    expected = json.dumps(
        [
            {
                "bytes": 4,
                "node_id": None,
                "object_id": 9,
                "offset": 17,
                "path": "checkpoint/model.safetensors",
                "sha256": digest,
            }
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert identity == {
        "authenticated_range_count": 1,
        "range_map_sha256": hashlib.sha256(expected).hexdigest(),
    }
