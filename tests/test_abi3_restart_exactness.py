"""Focused guards for the governed checkpoint/restart campaign."""

from __future__ import annotations

import hashlib
import json

from runtime.abi3.constants import StorageClass, TopologyClass
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.sim.checkpoint import (
    read_manifest,
    restore_device_state,
    save_device_state,
)
from runtime.sim.device import Device
from tools.run_abi3_restart_exactness import (
    REPO,
    _blind_checkpoint,
    _node_counter_differences,
    _source_identity,
)


def _cluster(nodes: int = 32) -> Device:
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment = build_fixture(
        storage_class=StorageClass.HBM,
        capability=capability,
        node_count=nodes,
    )
    return Device(deployment, capability, verify=True)


def test_source_identity_records_auditable_per_file_hashes() -> None:
    identity = _source_identity()
    source_sha256 = identity["python_source_sha256"]

    assert identity["python_file_count"] == len(source_sha256)
    assert {
        "runtime/sim/checkpoint.py",
        "runtime/sim/device.py",
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/rom/qwen3.py",
        "tools/run_abi3_restart_exactness.py",
    } <= set(source_sha256)
    for relative, expected in source_sha256.items():
        assert hashlib.sha256((REPO / relative).read_bytes()).hexdigest() == expected

    digest = hashlib.sha256()
    for relative, file_digest in sorted(source_sha256.items()):
        digest.update(relative.encode())
        digest.update(bytes.fromhex(file_digest))
    assert digest.hexdigest() == identity["python_source_digest"]


def _load_json(relative: str) -> dict:
    return json.loads((REPO / relative).read_text())


def _assert_recorded_sources_are_current(root: dict) -> None:
    for source in root.get("source", {}).values():
        path = REPO / source["path"]
        payload = path.read_bytes()
        if "bytes" in source:
            assert len(payload) == source["bytes"]
        assert hashlib.sha256(payload).hexdigest() == source["sha256"]


def _retained_certificate_identities() -> dict[str, dict[str, str]]:
    hbm_cases: dict[str, dict] = {}
    for relative, expected_case in (
        (
            "results/abi3/hbm_qwen_deployment_certificate.json",
            "qwen3-hbm-single-chip",
        ),
        (
            "results/abi3/hbm_deepseek_deployment_certificate.json",
            "deepseek-v4-flash-hbm-cluster",
        ),
    ):
        root = _load_json(relative)
        assert root["schema"] == "opentallas.hbm_sram.deployment_campaign.v1"
        assert root["status"] == "pass"
        assert root["case_count"] == len(root["cases"])
        case_names = [case["case"] for case in root["cases"]]
        assert len(case_names) == len(set(case_names))
        assert case_names.count(expected_case) == 1
        _assert_recorded_sources_are_current(root)
        for case in root["cases"]:
            assert case["schema"] == "opentallas.hbm_sram.deployment_certificate.v1"
            assert case["status"] == "pass"
            assert case["ok"] is True
            assert case["independent_checker"]["verifier"]["admitted"] is True
            hbm_cases[case["case"]] = case

    rom_root = _load_json("results/abi3/rom_schedule_checks.json")
    assert rom_root["schema"] == "opentallas.rom.schedule_campaign.v1"
    assert rom_root["status"] == "pass"
    assert rom_root["case_count"] == len(rom_root["cases"])
    rom_case_names = [case["case"] for case in rom_root["cases"]]
    assert len(rom_case_names) == len(set(rom_case_names))
    assert {
        "qwen3-rom-single-chip",
        "deepseek-v4-flash-rom-wafer",
    } <= set(rom_case_names)
    _assert_recorded_sources_are_current(rom_root)
    rom_cases = {case["case"]: case for case in rom_root["cases"]}
    for case in rom_cases.values():
        assert case["schema"] == "opentallas.rom.schedule_check.v1"
        assert case["status"] == "pass"
        assert case["ok"] is True
        assert case["verifier"]["admitted"] is True

    def hbm(case_name: str) -> dict[str, str]:
        identity = hbm_cases[case_name]["identity"]
        return {
            "capability_digest": identity["capability_sha256"],
            "deployment_digest": identity["deployment_sha256"],
            "graph_id": identity["graph_id"],
        }

    def rom(case_name: str) -> dict[str, str]:
        case = rom_cases[case_name]
        return {
            "capability_digest": case["capability_sha256"],
            "deployment_digest": case["deployment_sha256"],
            "graph_id": case["graph_id"],
        }

    return {
        "results/abi3/restart_exactness_qwen3_hbm.json": hbm("qwen3-hbm-single-chip"),
        "results/abi3/restart_exactness_qwen3_rom.json": rom("qwen3-rom-single-chip"),
        "results/abi3/restart_exactness_deepseek_hbm_p32.json": hbm(
            "deepseek-v4-flash-hbm-cluster"
        ),
        "results/abi3/restart_exactness_deepseek_rom_p32.json": rom(
            "deepseek-v4-flash-rom-wafer"
        ),
    }


def test_retained_restart_artifacts_are_source_current_and_fully_gated() -> None:
    current_source = _source_identity()
    identities = _retained_certificate_identities()
    expectations = {
        "results/abi3/restart_exactness_qwen3_hbm.json": {
            "backend": "hbm-sram-abi3",
            "node_count": 1,
            "target_id": "hbm-sram-abi3-single_chip",
            "topology_class": 0,
            "workload_record": (
                "results/abi3/accelerator_tokens/qwen3_8b_hbm_chat1.json"
            ),
        },
        "results/abi3/restart_exactness_qwen3_rom.json": {
            "backend": "rom.single_chip",
            "node_count": 1,
            "target_id": "qwen3-8b-rom-single-chip",
            "topology_class": 0,
            "workload_record": (
                "results/abi3/accelerator_tokens/qwen3_8b_rom_chat1.json"
            ),
        },
        "results/abi3/restart_exactness_deepseek_hbm_p32.json": {
            "backend": "hbm-sram-abi3",
            "node_count": 32,
            "target_id": "hbm-sram-abi3-cluster_32",
            "topology_class": 1,
            "workload_record": (
                "results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json"
            ),
        },
        "results/abi3/restart_exactness_deepseek_rom_p32.json": {
            "backend": "rom.wafer_logical_device",
            "node_count": 1,
            "target_id": "deepseek-v4-flash-rom-wafer",
            "topology_class": 2,
            "workload_record": (
                "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json"
            ),
        },
    }
    required_guards = {
        "three_distinct_processes",
        "same_deployment_digest",
        "same_node_count",
        "same_implementation_identity",
        "same_runtime_source_tree",
        "baseline_non_empty",
        "baseline_reached_expected_length",
        "interrupt_produced_expected_prefix_length",
        "interrupt_prefix_matches_baseline",
        "baseline_longer_than_the_interrupted_prefix",
        "resume_did_real_work",
        "resume_did_not_prefill",
        "restarted_non_empty",
        "restarted_length_matches_baseline",
        "restarted_reached_expected_length",
        "no_phase_failed",
        "negative_control_completed",
        "negative_control_same_deployment_digest",
        "negative_control_same_node_count",
        "negative_control_same_implementation_identity",
        "negative_control_same_runtime_source_tree",
        "state_only_control_completed",
        "state_only_control_same_deployment_digest",
        "state_only_control_same_node_count",
        "state_only_control_same_implementation_identity",
        "state_only_control_same_runtime_source_tree",
        "all_enabled_processes_distinct",
    }

    for relative, expected in expectations.items():
        body = _load_json(relative)
        record = body["record"]
        notes = record["notes"]
        target = record["target"]
        workload_record = _load_json(expected["workload_record"])
        workload = workload_record["workload"]
        identity = identities[relative]

        assert body["schema"] == "opentallas.abi3.restart_exactness.v2"
        assert body["status"] == "pass"
        assert record["failure"] is None
        assert record["evidence_class"] == "functional_artifact_only"
        assert record["depends_on_assumption"] is False

        assert target["deployment_digest"] == identity["deployment_digest"]
        assert target["capability_digest"] == identity["capability_digest"]
        assert target["backend"] == expected["backend"]
        assert target["target_id"] == expected["target_id"]
        assert target["topology_class"] == expected["topology_class"]
        assert target["node_count"] == expected["node_count"]

        assert workload_record["schema"] == "opentallas.abi3.accelerator_tokens.v1"
        assert workload_record["status"] == "pass"
        assert workload_record["failure"] is None
        assert workload_record["token_legitimacy_problems"] == []
        assert (
            workload_record["target"]["deployment_digest"]
            == identity["deployment_digest"]
        )
        assert (
            workload_record["target"]["capability_digest"]
            == identity["capability_digest"]
        )
        assert workload_record["model"]["graph_id"] == identity["graph_id"]
        assert record["workload"]["model_id"] == workload_record["model"]["model_id"]
        assert (
            record["workload"]["numeric_profile"]
            == workload_record["model"]["numeric_profile"]
        )
        assert (
            record["workload"]["generation_policy_digest"]
            == workload_record["generation_policy_digest"]
        )
        assert (
            record["workload"]["generation_policy"]
            == workload_record["generation_policy"]
        )
        assert record["workload"]["graph_id"] == identity["graph_id"]
        assert record["workload"]["workload_id"] == workload["workload_id"]
        assert record["workload"]["workload_digest"] == workload["workload_digest"]
        assert (
            record["workload"]["prompt_token_count"] == workload["prompt_token_count"]
        )
        assert record["workload"]["tokenizer_sha256"] == workload["tokenizer_sha256"]
        assert record["workload"]["max_new_tokens"] == 3

        baseline = notes["baseline_token_ids"]
        interrupted = notes["interrupted_prefix_token_ids"]
        restarted = notes["restarted_token_ids"]
        tail = notes["resumed_tail_token_ids"]
        assert (
            record["generated_token_count"] == len(record["generated_token_ids"]) == 3
        )
        assert record["stop_reason"] == "max_new_tokens"
        assert notes["stop_after_tokens"] == 2
        assert notes["expected_token_count"] == 3
        assert baseline == restarted == record["generated_token_ids"]
        assert interrupted == baseline[:2]
        assert tail == baseline[2:]
        assert len(tail) == 1
        assert notes["first_divergence"] is None
        assert notes["first_divergence_index"] is None
        assert notes["phase_stop_reasons"] == {
            "baseline": "max_new_tokens",
            "interrupt": "stopped",
            "resume": "max_new_tokens",
        }

        assert required_guards <= notes["guards"].keys()
        assert all(value is True for value in notes["guards"].values())
        assert notes["failed_guards"] == []
        assert notes["verification"]["admitted"] is True
        assert notes["verification"]["errors"] == []
        assert notes["verification"]["warnings"] == []
        assert all(value is True for value in notes["verification"]["checks"].values())
        assert notes["token_identical"] is True
        assert notes["retired_work_identical"] is True
        assert notes["counters_identical"] is True
        assert notes["node_counters_identical"] is True
        assert notes["counter_differences"] == {}
        assert notes["node_counter_differences"] == {}
        assert notes["token_legitimacy_problems"] == []

        assert set(notes["source_identity"]) == {"baseline", "interrupt", "resume"}
        for phase in ("baseline", "interrupt", "resume"):
            assert notes["source_identity"][phase] == current_source

        checkpoint = notes["checkpoint"]
        objects = checkpoint["objects"]
        object_ids = {(obj["node_id"], obj["object_id"]) for obj in objects}
        state_ids = {
            (obj["node_id"], obj["object_id"])
            for obj in objects
            if obj["storage_class"] == "STATE"
        }
        scratch_ids = object_ids - state_ids
        assert state_ids
        assert scratch_ids
        assert checkpoint["schema"] == "opentallas.abi3.device_checkpoint.v2"
        assert checkpoint["node_count"] == target["node_count"]
        assert checkpoint["object_count"] == len(objects)
        assert len(object_ids) == len(objects) > 0
        assert {obj["node_id"] for obj in objects} == set(range(target["node_count"]))
        assert checkpoint["mutable_bytes"] == sum(obj["size_bytes"] for obj in objects)
        assert checkpoint["stored_bytes"] == sum(obj["stored_bytes"] for obj in objects)
        assert 0 < checkpoint["stored_bytes"] <= checkpoint["mutable_bytes"]
        assert all(obj["writable"] is True for obj in objects)
        assert len(notes["node_counters"]) == target["node_count"]

        negative = notes["negative_control"]
        negative_ids = {
            (obj["node_id"], obj["object_id"]) for obj in negative["erased_objects"]
        }
        assert negative["exit_status"] == 0
        assert negative["failure"] is None
        assert negative["stop_reason"] == "max_new_tokens"
        assert len(negative["token_ids"]) == 3
        assert negative["diverged_from_baseline"] is True
        assert negative["first_divergence_index"] == 2
        assert negative["erased_storage_classes"] == ["STATE"]
        assert negative_ids == state_ids
        assert negative["token_ids"][:2] == baseline[:2]
        assert negative["token_ids"] != baseline

        state_only = notes["state_only_control"]
        state_only_ids = {
            (obj["node_id"], obj["object_id"]) for obj in state_only["erased_objects"]
        }
        assert state_only["exit_status"] == 0
        assert state_only["failure"] is None
        assert state_only["stop_reason"] == "max_new_tokens"
        assert state_only["reported_only"] is True
        assert state_only["matches_baseline"] is True
        assert state_only["first_divergence_index"] is None
        assert state_only["token_ids"] == baseline
        assert state_only_ids == scratch_ids
        assert set(state_only["erased_storage_classes"]) == {
            obj["storage_class"] for obj in objects if obj["storage_class"] != "STATE"
        }

        for control in (negative, state_only):
            control_identity = control["identity"]
            assert set(control_identity) == {
                "deployment_digest",
                "node_count",
                "implementation_identity",
                "source_identity",
            }
            assert control_identity["deployment_digest"] == target["deployment_digest"]
            assert control_identity["node_count"] == target["node_count"]
            assert (
                control_identity["implementation_identity"]
                == record["implementation_identity"]
            )
            assert control_identity["source_identity"] == current_source

        process_ids = [
            *notes["process_ids"].values(),
            negative["pid"],
            state_only["pid"],
        ]
        assert set(notes["process_ids"]) == {"baseline", "interrupt", "resume"}
        assert len(process_ids) == len(set(process_ids)) == 5


def test_node_counter_differences_include_values_and_sticky_overflow() -> None:
    baseline = [
        {
            "counters": {"dma.transfers": 2},
            "sticky_overflow": [],
            "registry_size": 121,
        },
        {
            "counters": {"tensor.additions": (1 << 64) - 1},
            "sticky_overflow": ["tensor.additions"],
            "registry_size": 121,
        },
    ]
    assert _node_counter_differences(baseline, baseline) == {}

    restarted = [dict(baseline[0]), dict(baseline[1])]
    restarted[0] = {
        **restarted[0],
        "counters": {"dma.transfers": 3},
    }
    restarted[1] = {
        **restarted[1],
        "sticky_overflow": [],
    }
    differences = _node_counter_differences(baseline, restarted)

    assert differences["0"]["counter_differences"]["dma.transfers"] == {
        "baseline": 2,
        "restarted": 3,
    }
    assert differences["1"]["sticky_overflow"] == {
        "baseline": ["tensor.additions"],
        "restarted": [],
    }


def test_blinded_cluster_checkpoint_erases_state_on_every_node(tmp_path) -> None:
    device = _cluster()
    for node_id, memory in enumerate(device.node_memories):
        for obj in memory.objects.values():
            if obj.storage_class is not StorageClass.STATE:
                continue
            buffer = obj.anonymous_buffer()
            assert buffer is not None
            buffer[:32] = node_id + 3

    source = tmp_path / "source"
    target = tmp_path / "blinded"
    save_device_state(device, device.create_session(), source)
    source_manifest = (source / "checkpoint.json").read_bytes()
    erased = _blind_checkpoint(source, target, {"STATE"})

    assert (source / "checkpoint.json").read_bytes() == source_manifest
    source_body = read_manifest(source)
    target_body = read_manifest(target)
    unchanged = next(
        entry for entry in target_body["objects"] if entry["storage_class"] != "STATE"
    )
    blinded = next(
        entry for entry in target_body["objects"] if entry["storage_class"] == "STATE"
    )
    assert (source / unchanged["file"]).stat().st_ino == (
        target / unchanged["file"]
    ).stat().st_ino
    source_blinded = next(
        entry
        for entry in source_body["objects"]
        if entry["node_id"] == blinded["node_id"]
        and entry["object_id"] == blinded["object_id"]
    )
    assert (source / source_blinded["file"]).stat().st_ino != (
        target / blinded["file"]
    ).stat().st_ino

    expected = {
        (node_id, object_id)
        for node_id, memory in enumerate(device.node_memories)
        for object_id, obj in memory.objects.items()
        if obj.storage_class is StorageClass.STATE
    }
    assert {(entry["node_id"], entry["object_id"]) for entry in erased} == expected

    restored = _cluster()
    restore_device_state(restored, target)
    for node_id, object_id in expected:
        buffer = restored.node_memories[node_id][object_id].anonymous_buffer()
        assert buffer is not None
        assert not buffer.any()
