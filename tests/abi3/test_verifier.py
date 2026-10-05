"""Adversarial tests for the ABI 3.0 admission proofs.

Each test builds a deployment that is byte-legal -- correct CRCs, correct
digests, decodable descriptors -- and illegal in exactly one way, then requires
the verifier to name that one thing.  Matching on the error text matters: a
verifier that rejects everything is as useless as one that admits everything,
so every negative case is paired with the baseline that must still be admitted.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

import pytest

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    NO_ID,
    Control,
    DType,
    Feature,
    InstructionFlag,
    Major,
    Permission,
    Selection,
    State,
    StateClass,
    StorageClass,
    Tensor,
    TopologyClass,
    feature_vector,
)
from runtime.abi3.crc import sha256
from runtime.abi3.deployment import ObjectSource, Segment
from runtime.abi3.descriptors import (
    LOOP_CONTROL_PAYLOAD,
    MEMORY_OBJECT_PAYLOAD,
    SCHEDULE_PAYLOAD,
    TENSOR_VIEW_PAYLOAD,
    TOPOLOGY_PAYLOAD,
    ExtendedDescriptorType,
    Phase,
    Symbol,
)
from runtime.abi3.layout import RecordError
from runtime.abi3.verifier import (
    VerificationError,
    Verifier,
    require_admitted,
    verify_deployment,
)

from . import patched_payload, patched_table, probe_capability, probe_deployment, restamp


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def errors_of(deployment: Any, capability: Capability) -> list[str]:
    report = verify_deployment(deployment, capability)
    assert not report.admitted, "deployment was admitted but should have been rejected"
    return report.errors


def assert_rejected(deployment: Any, capability: Capability, pattern: str) -> None:
    errors = errors_of(deployment, capability)
    assert any(re.search(pattern, error) for error in errors), (
        f"no error matched {pattern!r}; got {errors}"
    )


def default_tail(builder: Any, ids: dict[str, int]) -> None:
    """The selection and completion tail every probe program ends with."""
    builder.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=ids["argmax"])
    builder.emit(Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=ids["append"])
    builder.emit(Major.CONTROL, Control.COMPLETE)


@pytest.fixture()
def capability() -> Capability:
    return probe_capability()


# ---------------------------------------------------------------------------
# the baseline must be admitted
# ---------------------------------------------------------------------------
def test_the_probe_deployment_is_admitted(capability: Capability) -> None:
    report = verify_deployment(probe_deployment(capability), capability)
    assert report.admitted, report.errors
    assert report.errors == []
    assert all(report.checks.values()), report.checks
    assert report.proved_retired_work <= report.declared_retired_work
    assert report.instruction_count == 6
    assert report.state_resources == 1


def test_a_generative_deployment_with_on_device_selection_is_admitted(
    capability: Capability,
) -> None:
    report = verify_deployment(
        probe_deployment(capability, generative=True), capability
    )
    assert report.admitted, report.errors
    assert report.checks["on_device_selection"] is True
    assert report.checks["token_append_present"] is True


def test_the_report_is_canonical_json(capability: Capability) -> None:
    report = verify_deployment(probe_deployment(capability), capability)
    body = report.to_dict()
    assert json.loads(json.dumps(body, sort_keys=True)) == body
    assert set(body) >= {
        "admitted",
        "checks",
        "declared_retired_work",
        "errors",
        "proved_retired_work",
    }


def test_require_admitted_raises_with_every_error(capability: Capability) -> None:
    deployment = probe_deployment(capability, max_retired_work=1)
    with pytest.raises(VerificationError, match="proved retired work"):
        require_admitted(deployment, capability)
    assert require_admitted(probe_deployment(capability), capability).admitted


def _source_probe(
    capability: Capability, source: ObjectSource, content_digest: bytes
) -> Any:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.objects[weights] = source
    deployment.table[weights].payload["content_digest"] = content_digest
    deployment.table.rewrite(weights)
    return restamp(deployment)


@pytest.mark.parametrize("kind", ["file", "segments"])
def test_complete_shared_sources_are_bound_during_in_memory_admission(
    capability: Capability, kind: str
) -> None:
    segments = (
        (Segment("weights.bin", 0, 128, sha256(b"weights").hex()),)
        if kind == "file"
        else (
            Segment("weights.bin", 0, 64, sha256(b"weights-0").hex()),
            Segment("weights.bin", 64, 64, sha256(b"weights-1").hex()),
        )
    )
    source = ObjectSource(kind=kind, size_bytes=128, segments=segments)
    deployment = _source_probe(
        capability, source, source.authenticated_content_digest()
    )

    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    assert report.checks["object_source_content_digest"] is True

    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table[weights].payload["content_digest"] = bytes(32)
    deployment.table.rewrite(weights)
    report = verify_deployment(restamp(deployment), capability)
    assert not report.admitted
    assert report.checks["object_source_content_digest"] is False
    assert any(
        f"{kind} content digest does not match" in error for error in report.errors
    )


def test_incomplete_shared_source_is_legacy_only_with_zero_sentinel(
    capability: Capability,
) -> None:
    source = ObjectSource(
        kind="segments",
        size_bytes=128,
        segments=(
            Segment("weights.bin", 0, 64),
            Segment("weights.bin", 64, 64, sha256(b"weights-1").hex()),
        ),
    )
    deployment = _source_probe(capability, source, bytes(32))
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors

    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table[weights].payload["content_digest"] = sha256(b"claimed")
    deployment.table.rewrite(weights)
    report = verify_deployment(restamp(deployment), capability)
    assert not report.admitted
    assert report.checks["object_source_content_digest"] is False
    assert any(
        "requires the all-zero MEMORY_OBJECT content digest sentinel" in error
        for error in report.errors
    )


@pytest.mark.parametrize("malformed", ["not-a-sha256", "00 " * 32])
def test_malformed_shared_hash_cannot_hide_behind_legacy_sentinel(
    capability: Capability,
    malformed: str,
) -> None:
    source = ObjectSource(
        kind="segments",
        size_bytes=128,
        segments=(
            Segment("weights.bin", 0, 64),
            Segment("weights.bin", 64, 64, malformed),
        ),
    )
    report = verify_deployment(_source_probe(capability, source, bytes(32)), capability)

    assert not report.admitted
    assert report.checks["object_source_content_digest"] is False
    assert any(
        "must carry a 64-hex SHA-256 digest" in error for error in report.errors
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (ObjectSource.zeros(128), bytes(32)),
        (
            ObjectSource.generated(
                "fixture_v1", {"size": 128}, 128, sha256(b"generated").hex()
            ),
            sha256(b"generated"),
        ),
    ],
    ids=["zero", "generated"],
)
def test_exact_source_digest_semantics_are_enforced(
    capability: Capability, source: ObjectSource, expected: bytes
) -> None:
    deployment = _source_probe(capability, source, expected)
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors

    wrong = bytearray(expected)
    wrong[0] ^= 0xFF
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table[weights].payload["content_digest"] = bytes(wrong)
    deployment.table.rewrite(weights)
    report = verify_deployment(restamp(deployment), capability)
    assert not report.admitted
    assert report.checks["object_source_content_digest"] is False


def test_malformed_generated_digest_returns_a_failed_report(
    capability: Capability,
) -> None:
    source = ObjectSource.generated("fixture_v1", {}, 128, "z" * 64)
    report = verify_deployment(_source_probe(capability, source, bytes(32)), capability)

    assert not report.admitted
    assert report.checks["object_source_content_digest"] is False
    assert any("generated result must carry" in error for error in report.errors)


def _node_segment_probe(
    capability: Capability,
    *,
    node_map_count: int = 32,
    topology_node_count: int = 32,
) -> Any:
    """A digest-consistent cluster probe with node-indexed immutable weights."""
    capability.topology_class = int(TopologyClass.CLUSTER_32)
    capability.features = tuple(
        sorted({*capability.features, int(Feature.INTER_CHIP_ENDPOINT)})
    )
    capability.limits["max_nodes"] = 32
    capability.validate()

    deployment = probe_deployment(capability)
    topology_id = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)[0]
    deployment.table = patched_payload(
        deployment.table,
        topology_id,
        TOPOLOGY_PAYLOAD,
        "topology_class",
        int(TopologyClass.CLUSTER_32),
    )
    deployment.table = patched_payload(
        deployment.table,
        topology_id,
        TOPOLOGY_PAYLOAD,
        "node_count",
        topology_node_count,
    )

    weights = deployment.notes["probe_ids"]["weights"]
    source = ObjectSource(
        kind="node_segments",
        size_bytes=128,
        node_segments=tuple(
            (
                Segment(
                    path=f"weights-node-{node_id}.bin",
                    offset=0,
                    bytes=128,
                    sha256=sha256(f"node-{node_id}".encode()).hex(),
                ),
            )
            for node_id in range(node_map_count)
        ),
    )
    deployment.objects[weights] = source
    descriptor = deployment.table[weights]
    descriptor.payload["content_digest"] = source.authenticated_content_digest()
    deployment.table.rewrite(weights)
    return restamp(
        deployment,
        topology_digest=sha256(deployment.table[topology_id].encode()),
    )


def test_node_segment_map_count_must_match_admitted_topology(
    capability: Capability,
) -> None:
    baseline = _node_segment_probe(capability)
    report = verify_deployment(baseline, capability)
    assert report.admitted, report.errors
    assert report.checks["node_source_count"] is True
    assert report.checks["node_source_content_digest"] is True
    assert report.checks["object_source_content_digest"] is True

    mutated = _node_segment_probe(capability, node_map_count=31)
    report = verify_deployment(mutated, capability)
    assert report.checks["deployment_digest"] is True
    assert report.checks["descriptor_table_digest"] is True
    assert report.checks["node_source_count"] is False
    assert not report.admitted
    assert any(
        "node-segments source declares 31 node maps, admitted topology declares "
        "32 nodes" in error
        for error in report.errors
    ), report.errors


def test_cluster_topology_cannot_shrink_below_the_capability(
    capability: Capability,
) -> None:
    deployment = _node_segment_probe(
        capability, node_map_count=16, topology_node_count=16
    )
    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["topology_node_count_identity"] is False
    assert report.checks["node_source_topology"] is False
    assert any(
        "topology declares 16 nodes" in error for error in report.errors
    ), report.errors


def test_topology_class_must_match_the_admitting_capability(
    capability: Capability,
) -> None:
    deployment = _node_segment_probe(capability)
    topology_id = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)[0]
    deployment.table = patched_payload(
        deployment.table,
        topology_id,
        TOPOLOGY_PAYLOAD,
        "topology_class",
        int(TopologyClass.WAFER_LOGICAL_DEVICE),
    )
    deployment.topology_class = int(TopologyClass.WAFER_LOGICAL_DEVICE)
    deployment = restamp(
        deployment,
        topology_digest=sha256(deployment.table[topology_id].encode()),
    )

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["topology_class_identity"] is False
    assert any("topology class mismatch" in error for error in report.errors)


def test_node_segment_source_must_name_an_immutable_object(
    capability: Capability,
) -> None:
    deployment = _node_segment_probe(capability)
    activations = deployment.notes["probe_ids"]["activations"]
    deployment.objects[activations] = deployment.objects[
        deployment.notes["probe_ids"]["weights"]
    ]
    deployment = restamp(deployment)

    assert_rejected(
        deployment,
        capability,
        rf"object {activations}: node-segments source must name an IMMUTABLE "
        rf"memory object",
    )


def test_node_segment_content_digest_is_checked_during_generic_admission(
    capability: Capability,
) -> None:
    deployment = _node_segment_probe(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table[weights].payload["content_digest"] = bytes(32)
    deployment.table.rewrite(weights)
    deployment = restamp(deployment)

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["node_source_content_digest"] is False
    assert report.checks["object_source_content_digest"] is False
    assert any(
        "node-segments content digest does not match" in error
        for error in report.errors
    )


def test_node_segment_ranges_require_digests_during_generic_admission(
    capability: Capability,
) -> None:
    deployment = _node_segment_probe(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    source = deployment.objects[weights]
    maps = list(source.node_segments)
    first = maps[0][0]
    maps[0] = (
        Segment(first.path, first.offset, first.bytes),
        *maps[0][1:],
    )
    deployment.objects[weights] = ObjectSource(
        kind="node_segments",
        size_bytes=source.size_bytes,
        node_segments=tuple(maps),
    )
    deployment = restamp(deployment)

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["node_source_content_digest"] is False
    assert any(
        "no authenticated content digest" in error for error in report.errors
    )


# ---------------------------------------------------------------------------
# schedules
# ---------------------------------------------------------------------------
def test_schedule_queue_zero_remains_admitted(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    schedule_id = deployment.notes["probe_ids"]["tensor_schedule"]
    assert deployment.table[schedule_id].payload["queue_index"] == 0
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors


def test_schedule_queue_index_must_name_an_advertised_queue(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    schedule_id = deployment.notes["probe_ids"]["tensor_schedule"]
    queue_count = capability.engines["tensor"]["queues"]
    deployment.table = patched_payload(
        deployment.table,
        schedule_id,
        SCHEDULE_PAYLOAD,
        "queue_index",
        queue_count,
    )
    assert_rejected(
        restamp(deployment),
        capability,
        rf"schedule {schedule_id} queue_index {queue_count} is outside the "
        rf"{queue_count} advertised tensor queues",
    )


def test_schedule_outstanding_must_not_exceed_the_global_queue_limit(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    schedule_id = deployment.notes["probe_ids"]["tensor_schedule"]
    limit = capability.limits["max_outstanding_per_queue"]
    deployment.table = patched_payload(
        deployment.table,
        schedule_id,
        SCHEDULE_PAYLOAD,
        "max_outstanding",
        limit + 1,
    )
    assert_rejected(
        restamp(deployment),
        capability,
        rf"schedule {schedule_id} max_outstanding {limit + 1} exceeds "
        rf"capability\.limits\.max_outstanding_per_queue bound {limit}",
    )


@pytest.mark.parametrize(
    "limit_name", ["queue_depth", "max_outstanding_per_queue"]
)
def test_schedule_outstanding_honours_a_narrower_engine_limit(
    limit_name: str,
) -> None:
    capability = probe_capability()
    capability.engines["tensor"][limit_name] = 1
    capability.validate()
    deployment = probe_deployment(capability)
    schedule_id = deployment.notes["probe_ids"]["tensor_schedule"]
    assert_rejected(
        deployment,
        capability,
        rf"schedule {schedule_id} max_outstanding 2 exceeds "
        rf"capability\.engines\.tensor\.{limit_name} bound 1",
    )


# ---------------------------------------------------------------------------
# loops
# ---------------------------------------------------------------------------
def loop_program(**loop_kwargs: Any) -> Callable[[Any, dict[str, int]], None]:
    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(**loop_kwargs)
        ids["probe_loop"] = loop
        builder.open_loop(loop)
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.close_loop()
        default_tail(builder, ids)

    return program


def test_a_bounded_loop_is_admitted(capability: Capability) -> None:
    deployment = probe_deployment(
        capability, program=loop_program(lower_bound=0, upper_bound=4, step=1)
    )
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    assert report.loop_depth == 1


def test_a_loop_with_a_zero_step_has_no_finite_bound(capability: Capability) -> None:
    deployment = probe_deployment(
        capability, program=loop_program(lower_bound=0, upper_bound=4, step=1)
    )
    loop = deployment.notes["probe_ids"]["probe_loop"]
    deployment.table = patched_payload(
        deployment.table, loop, LOOP_CONTROL_PAYLOAD, "step", 0
    )
    assert_rejected(restamp(deployment), capability, "loop step is zero")


def test_a_symbol_bounded_loop_with_no_declared_maximum_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(
        capability,
        program=loop_program(
            lower_bound=0,
            upper_bound=0,
            step=1,
            bound_symbol=Symbol.SPAN_TOKENS,
            max_iterations=8,
        ),
    )
    assert verify_deployment(deployment, capability).admitted
    loop = deployment.notes["probe_ids"]["probe_loop"]
    deployment.table = patched_payload(
        deployment.table, loop, LOOP_CONTROL_PAYLOAD, "max_iterations", 0
    )
    assert_rejected(restamp(deployment), capability, "non-positive span")


def test_a_loop_bound_symbol_outside_the_frozen_registry_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(
        capability,
        program=loop_program(
            lower_bound=0,
            upper_bound=0,
            step=1,
            bound_symbol=Symbol.SPAN_TOKENS,
            max_iterations=8,
        ),
    )
    loop = deployment.notes["probe_ids"]["probe_loop"]
    deployment.table = patched_payload(
        deployment.table, loop, LOOP_CONTROL_PAYLOAD, "bound_symbol_id", 99
    )
    assert_rejected(
        restamp(deployment), capability, "is not in the frozen registry"
    )


def test_a_loop_trip_over_its_declared_maximum_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(
        capability,
        program=loop_program(lower_bound=0, upper_bound=4, step=1, max_iterations=4),
    )
    loop = deployment.notes["probe_ids"]["probe_loop"]
    deployment.table = patched_payload(
        deployment.table, loop, LOOP_CONTROL_PAYLOAD, "upper_bound", 64
    )
    assert_rejected(
        restamp(deployment), capability, r"loop trip 64 exceeds its declared maximum 4"
    )


def test_a_declared_maximum_over_the_capability_is_rejected(
    capability: Capability,
) -> None:
    limit = capability.limits["max_loop_trip"]
    deployment = probe_deployment(
        capability,
        program=loop_program(
            lower_bound=0, upper_bound=4, step=1, max_iterations=limit + 1
        ),
        max_retired_work=capability.limits["max_retired_work"],
    )
    assert_rejected(deployment, capability, r"exceeds capability")


def test_loop_nesting_over_the_capability_depth_is_rejected(
    capability: Capability,
) -> None:
    depth = capability.limits["max_loop_depth"]

    def program(builder: Any, ids: dict[str, int]) -> None:
        for _ in range(depth + 1):
            builder.open_loop(
                builder.loop_control(lower_bound=0, upper_bound=2, step=1)
            )
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        for _ in range(depth + 1):
            builder.close_loop()
        default_tail(builder, ids)

    deployment = probe_deployment(
        capability,
        program=program,
        max_retired_work=capability.limits["max_retired_work"],
    )
    assert_rejected(
        deployment,
        capability,
        rf"loop nesting {depth + 1} exceeds capability depth {depth}",
    )


def test_a_loop_body_that_does_not_start_after_its_setup_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(
        capability, program=loop_program(lower_bound=0, upper_bound=4, step=1)
    )
    loop = deployment.notes["probe_ids"]["probe_loop"]
    deployment.table = patched_payload(
        deployment.table, loop, LOOP_CONTROL_PAYLOAD, "body_start", 0
    )
    assert_rejected(restamp(deployment), capability, "body_start")


def test_loop_next_without_an_open_loop_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(lower_bound=0, upper_bound=2, step=1)
        builder.emit(Major.CONTROL, Control.LOOP_NEXT, control_id=loop)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "LOOP_NEXT with no open loop",
    )


def test_a_program_that_ends_with_an_open_loop_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(lower_bound=0, upper_bound=2, step=1)
        builder.emit(Major.CONTROL, Control.LOOP_SETUP, control_id=loop)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "open loop",
    )


# ---------------------------------------------------------------------------
# branches
# ---------------------------------------------------------------------------
def test_a_backward_branch_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.emit(Major.CONTROL, Control.BRANCH, control_id=0)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "is not forward",
    )


def test_a_branch_to_itself_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.BRANCH, control_id=0)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "is not forward"
    )


@pytest.mark.parametrize("target", [999, NO_ID, 6])
def test_a_branch_outside_the_body_is_rejected(
    capability: Capability, target: int
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.BRANCH, control_id=target)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "outside the body",
    )


def test_a_forward_branch_inside_the_body_is_admitted(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.BRANCH, control_id=2)
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        default_tail(builder, ids)

    report = verify_deployment(probe_deployment(capability, program=program), capability)
    assert report.admitted, report.errors


# ---------------------------------------------------------------------------
# events
# ---------------------------------------------------------------------------
def test_a_wait_on_an_unproducible_event_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        wait = builder.wait_set([77])
        builder.emit(
            Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"], wait_set_id=wait
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"waits on event 77, which no instruction signals",
    )


def test_a_wait_set_with_no_producers_is_rejected(capability: Capability) -> None:
    from runtime.abi3.descriptors import EVENT_WAIT_SET_PAYLOAD

    def program(builder: Any, ids: dict[str, int]) -> None:
        event = builder.new_event()
        ids["wait"] = builder.wait_set([event])
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            signal_event_id=event,
        )
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            wait_set_id=ids["wait"],
        )
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    assert verify_deployment(deployment, capability).admitted
    wait = deployment.notes["probe_ids"]["wait"]
    deployment.table = patched_payload(
        deployment.table, wait, EVENT_WAIT_SET_PAYLOAD, "producer_count", 0
    )
    assert_rejected(restamp(deployment), capability, "declares no producers")


def test_a_producer_beyond_the_declared_count_is_rejected(
    capability: Capability,
) -> None:
    from runtime.abi3.descriptors import EVENT_WAIT_SET_PAYLOAD

    def program(builder: Any, ids: dict[str, int]) -> None:
        event = builder.new_event()
        ids["wait"] = builder.wait_set([event])
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            signal_event_id=event,
        )
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            wait_set_id=ids["wait"],
        )
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    wait = deployment.notes["probe_ids"]["wait"]
    deployment.table = patched_payload(
        deployment.table, wait, EVENT_WAIT_SET_PAYLOAD, "producer_5", 3
    )
    assert_rejected(
        restamp(deployment), capability, "producer beyond\n?\\s*its declared count"
    )


def test_an_event_signalled_twice_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        for _ in range(2):
            builder.emit(
                Major.TENSOR,
                Tensor.MATMUL,
                descriptor_id=ids["matmul"],
                signal_event_id=4,
            )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "single-assignment",
    )


def test_wait_without_a_wait_set_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.WAIT)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "WAIT without a wait set",
    )


# ---------------------------------------------------------------------------
# transactional state
# ---------------------------------------------------------------------------
def test_prepared_state_with_no_commit_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "has no reachable commit or discard",
    )


def test_a_double_prepare_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=ids["state"])
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "prepared twice without",
    )


def test_a_commit_without_a_prepare_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=ids["state"])
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "without a preceding prepare",
    )


def test_a_discard_resolves_a_prepare(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        builder.emit(Major.STATE, State.DISCARD, descriptor_id=ids["state"])
        default_tail(builder, ids)

    report = verify_deployment(probe_deployment(capability, program=program), capability)
    assert report.admitted, report.errors


def test_state_without_prepare_permission_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    state = deployment.notes["probe_ids"]["state"]
    deployment.table = patched_table(
        deployment.table, state, 32, int(Permission.READ).to_bytes(4, "little")
    )
    assert_rejected(
        restamp(deployment), capability, "lacks STATE_PREPARE permission"
    )


def test_state_without_commit_permission_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    state = deployment.notes["probe_ids"]["state"]
    deployment.table = patched_table(
        deployment.table,
        state,
        32,
        int(Permission.READ | Permission.STATE_PREPARE).to_bytes(4, "little"),
    )
    assert_rejected(restamp(deployment), capability, "lacks STATE_COMMIT permission")


# ---------------------------------------------------------------------------
# completion and termination
# ---------------------------------------------------------------------------
def test_a_program_with_no_completion_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"declares 0 COMPLETE instructions",
    )


def test_two_completions_are_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.COMPLETE)
        builder.emit(Major.CONTROL, Control.COMPLETE)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"declares 2 COMPLETE instructions",
    )


def test_a_completion_that_is_not_terminal_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.CONTROL, Control.COMPLETE)
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "COMPLETE is not the final instruction",
    )


def test_a_completion_inside_a_loop_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.open_loop(builder.loop_control(lower_bound=0, upper_bound=2, step=1))
        builder.emit(Major.CONTROL, Control.COMPLETE)
        builder.close_loop()

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "COMPLETE inside an open loop",
    )


# ---------------------------------------------------------------------------
# permissions and storage
# ---------------------------------------------------------------------------
def test_a_rom_object_with_a_write_permission_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.memory_object(
            storage_class=StorageClass.ROM,
            size_bytes=64,
            source=ObjectSource.zeros(64),
            permissions=int(Permission.READ | Permission.WRITE),
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "ROM storage declares a write permission",
    )


@pytest.mark.parametrize(
    "write_bit",
    [Permission.WRITE, Permission.STATE_PREPARE, Permission.STATE_COMMIT],
)
def test_an_immutable_object_with_a_write_path_never_decodes(
    capability: Capability, write_bit: Permission
) -> None:
    """A writable-immutable mask is refused by the descriptor decoder, so it
    cannot even reach the verifier's own IMMUTABLE check."""
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    with pytest.raises(RecordError, match="IMMUTABLE"):
        patched_table(
            deployment.table,
            weights,
            32,
            int(Permission.READ | write_bit | Permission.IMMUTABLE).to_bytes(
                4, "little"
            ),
        )


def test_a_zero_size_memory_object_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table = patched_payload(
        deployment.table, weights, MEMORY_OBJECT_PAYLOAD, "size_bytes", 0
    )
    assert_rejected(restamp(deployment), capability, "zero-size memory object")


def test_an_object_whose_source_disagrees_with_the_descriptor_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table = patched_payload(
        deployment.table, weights, MEMORY_OBJECT_PAYLOAD, "size_bytes", 256
    )
    assert_rejected(restamp(deployment), capability, "manifest source is")


def test_an_object_with_no_manifest_source_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.objects.pop(weights)
    assert_rejected(restamp(deployment), capability, "no source declared")


def test_an_unknown_storage_class_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table = patched_payload(
        deployment.table, weights, MEMORY_OBJECT_PAYLOAD, "storage_class", 9
    )
    assert_rejected(restamp(deployment), capability, "unknown storage class")


# ---------------------------------------------------------------------------
# tensor views
# ---------------------------------------------------------------------------
def test_a_view_that_exceeds_its_object_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.tensor_view(
            object_id=ids["weights"], dtype=DType.BF16, dims=[64, 64]
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"needs \d+ bytes but object \d+ is 128 bytes",
    )


def test_a_block_scale_that_does_not_tile_the_view_is_rejected(
    capability: Capability,
) -> None:
    """Amendment A15 requires both blocks to divide the view they scale.

    A leading extent that is not a whole number of row blocks leaves some rows
    with no defined scale, and the index arithmetic would silently read a
    neighbour's code.  Refusing it at admission is cheaper than trapping in the
    middle of an operator that has already read weights.
    """

    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[3, 8],
            scale_object_id=ids["weights"],
            scale_block_elements=4,
            scale_block_rows=2,
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"leading extent 3 is not a multiple of its 2-row scale block",
    )


def test_a_block_scale_that_does_not_divide_the_last_axis_is_rejected(
    capability: Capability,
) -> None:
    """The A8 half of the same requirement, unchanged by A15."""

    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[4, 6],
            scale_object_id=ids["weights"],
            scale_block_elements=4,
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        r"last axis 6 is not a multiple of its 4-element scale block",
    )


def test_a_dynamic_term_can_push_a_view_past_its_object(
    capability: Capability,
) -> None:
    """A4 terms move the window at run time; the bound must hold at the maximum."""
    from runtime.abi3.builder import DynamicTerm

    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(lower_bound=0, upper_bound=8, step=1)
        ids["probe_loop"] = loop
        builder.open_loop(loop)
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[8, 8],
            dynamic=[DynamicTerm.loop(loop, 64)],
        )
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.close_loop()
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "needs .* bytes but object",
    )


def test_a_runtime_symbol_term_is_bounded_by_the_capability(
    capability: Capability,
) -> None:
    from runtime.abi3.builder import DynamicTerm

    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[8, 8],
            dynamic=[DynamicTerm.symbol(Symbol.CONTEXT_LENGTH, 8)],
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "needs .* bytes"
    )


def test_a_view_term_naming_a_loop_that_is_never_set_up_is_rejected(
    capability: Capability,
) -> None:
    from runtime.abi3.builder import DynamicTerm

    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(lower_bound=0, upper_bound=2, step=1)
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[2, 2],
            dynamic=[DynamicTerm.loop(loop, 1)],
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "is not a verified loop",
    )


def test_a_symbol_bounded_edge_mask_is_admitted(capability: Capability) -> None:
    """A26 clamps a fixed-address block without adding a dynamic term."""

    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(
            lower_bound=0,
            upper_bound=8,
            step=1,
            bound_symbol=Symbol.SPAN_TOKENS,
            bound_divisor=4,
            max_iterations=8,
        )
        builder.open_loop(loop)
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[4, 8],
            edge_mask_id=loop,
        )
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.close_loop()
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    assert report.checks["edge_mask"] is True


def test_an_edge_mask_naming_a_loop_that_is_never_set_up_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(
            lower_bound=0,
            upper_bound=8,
            step=1,
            bound_symbol=Symbol.SPAN_TOKENS,
            bound_divisor=4,
            max_iterations=8,
        )
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[4, 8],
            edge_mask_id=loop,
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "edge-mask descriptor .* is not a verified loop",
    )


def test_an_edge_mask_cannot_claim_more_than_one_loop_block(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        loop = builder.loop_control(
            lower_bound=0,
            upper_bound=8,
            step=1,
            bound_symbol=Symbol.SPAN_TOKENS,
            bound_divisor=2,
            max_iterations=8,
        )
        builder.open_loop(loop)
        builder.tensor_view(
            object_id=ids["weights"],
            dtype=DType.BF16,
            dims=[4, 8],
            edge_mask_id=loop,
        )
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.close_loop()
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "edge-masked axis-0 extent 4 exceeds the 2 elements",
    )


def test_axes_beyond_the_declared_rank_must_be_zero(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    view = deployment.notes["probe_ids"]["weight_view"]
    deployment.table = patched_payload(
        deployment.table, view, TENSOR_VIEW_PAYLOAD, "dim4", 3
    )
    assert_rejected(restamp(deployment), capability, "beyond rank is nonzero")


def test_a_zero_extent_axis_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    view = deployment.notes["probe_ids"]["weight_view"]
    deployment.table = patched_payload(
        deployment.table, view, TENSOR_VIEW_PAYLOAD, "dim1", 0
    )
    assert_rejected(restamp(deployment), capability, "zero extent")


@pytest.mark.parametrize("rank", [0, 7, 255])
def test_a_rank_outside_one_to_six_is_rejected(
    capability: Capability, rank: int
) -> None:
    deployment = probe_deployment(capability)
    view = deployment.notes["probe_ids"]["weight_view"]
    deployment.table = patched_payload(
        deployment.table, view, TENSOR_VIEW_PAYLOAD, "rank", rank
    )
    assert_rejected(restamp(deployment), capability, "rank .* out of range")


def test_an_unknown_dtype_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    view = deployment.notes["probe_ids"]["weight_view"]
    deployment.table = patched_payload(
        deployment.table, view, TENSOR_VIEW_PAYLOAD, "dtype", 0x77
    )
    assert_rejected(restamp(deployment), capability, "unknown dtype")


def test_a_dynamic_term_beyond_the_declared_count_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    view = deployment.notes["probe_ids"]["weight_view"]
    deployment.table = patched_payload(
        deployment.table, view, TENSOR_VIEW_PAYLOAD, "term2_stride", 4
    )
    assert_rejected(restamp(deployment), capability, "beyond declared count")


# ---------------------------------------------------------------------------
# capability and digest admission
# ---------------------------------------------------------------------------
def test_a_missing_capability_feature_bit_is_rejected(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    required = feature_vector(
        sorted(set(capability.features) | {int(Feature.MXFP4_E2M1_E8M0)})
    )
    deployment.required_features = required
    assert_rejected(
        restamp(deployment, required_features=required),
        capability,
        r"does not implement required feature bits \[5\]",
    )


def test_a_program_over_the_instruction_bound_is_rejected() -> None:
    capability = probe_capability(max_instructions=4)
    assert_rejected(
        probe_deployment(capability),
        capability,
        "capability admits 4",
    )


def test_a_deployment_over_the_descriptor_bound_is_rejected() -> None:
    capability = probe_capability(max_descriptors=3)
    assert_rejected(probe_deployment(capability), capability, "capability admits 3")


def test_a_declared_work_bound_over_the_capability_is_rejected() -> None:
    capability = probe_capability(max_retired_work=4)
    deployment = probe_deployment(capability, max_retired_work=8)
    assert_rejected(deployment, capability, "declared maximum retired work exceeds")


def test_proved_work_over_the_declared_bound_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability, max_retired_work=1)
    assert_rejected(
        deployment, capability, r"proved retired work 6 exceeds the declared bound 1"
    )


def test_loop_work_is_multiplied_by_the_trip_count(capability: Capability) -> None:
    deployment = probe_deployment(
        capability, program=loop_program(lower_bound=0, upper_bound=4, step=1)
    )
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    # The loop body and its LOOP_NEXT retire once per trip. LOOP_SETUP itself
    # retires once, at the enclosing multiplier -- omitting it under-counted
    # the bound, so a program the verifier admitted could still trip the
    # device's watchdog. The tail retires once.
    assert report.proved_retired_work == 1 + 4 * 2 + 3


def test_a_header_that_does_not_bind_the_descriptor_table_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table = patched_payload(
        deployment.table, weights, MEMORY_OBJECT_PAYLOAD, "alignment_log2", 7
    )
    assert_rejected(deployment, capability, "does not bind the descriptor table")


def test_memory_object_range_must_fit_the_capability_address_space(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    weights = deployment.notes["probe_ids"]["weights"]
    deployment.table = patched_payload(
        deployment.table,
        weights,
        MEMORY_OBJECT_PAYLOAD,
        "base_address",
        int(capability.memory["hbm"]["bytes"]),
    )
    deployment = restamp(deployment)

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["memory_object_capacity"] is False
    assert any("exceeds the" in error and "HBM" in error for error in report.errors)


def test_explicit_hbm_and_state_address_ranges_cannot_overlap(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    ids = deployment.notes["probe_ids"]
    deployment.table = patched_payload(
        deployment.table,
        ids["weights"],
        MEMORY_OBJECT_PAYLOAD,
        "base_address",
        4096,
    )
    deployment.table = patched_payload(
        deployment.table,
        ids["kv_committed"],
        MEMORY_OBJECT_PAYLOAD,
        "base_address",
        4096,
    )
    deployment = restamp(deployment)

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["hbm_address_map_disjoint"] is False
    assert any("overlapping object pairs" in error for error in report.errors)


def test_same_nonzero_base_for_every_hbm_and_state_object_is_explicit_overlap(
    capability: Capability,
) -> None:
    """Equal nonzero bases may not masquerade as implicit placement."""

    deployment = probe_deployment(capability)
    for descriptor in list(deployment.table.descriptors()):
        if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        storage = StorageClass(int(descriptor.payload["storage_class"]))
        if storage not in (StorageClass.HBM, StorageClass.STATE):
            continue
        deployment.table = patched_payload(
            deployment.table,
            descriptor.descriptor_id,
            MEMORY_OBJECT_PAYLOAD,
            "base_address",
            4096,
        )
    deployment = restamp(deployment)

    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["hbm_address_map_disjoint"] is False
    assert any("overlapping object pairs" in error for error in report.errors)


def test_missing_hbm_dma_queue_capability_returns_a_rejection_report(
    capability: Capability,
) -> None:
    """A sparse capability must not turn verification into a KeyError."""

    deployment = probe_deployment(capability)
    deployment.backend = "hbm-sram-abi3"
    deployment.topology_class = int(TopologyClass.CLUSTER_32)
    capability.engines = {
        name: spec for name, spec in capability.engines.items() if name != "dma"
    }

    report = verify_deployment(deployment, capability)

    assert not report.admitted
    assert report.checks["hbm_exchange_dma_capability"] is False
    assert any(
        "capability.engines.dma.queues" in error for error in report.errors
    )


def test_a_header_that_does_not_bind_the_manifest_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    deployment.model_id = "something-else"
    assert_rejected(deployment, capability, "does not bind the deployment manifest")


def test_a_deployment_compiled_against_another_capability_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    other = probe_capability(max_sessions=8)
    assert other.digest != capability.digest
    assert_rejected(deployment, other, "was compiled against capability")


# ---------------------------------------------------------------------------
# descriptor typing
# ---------------------------------------------------------------------------
def test_an_engine_instruction_naming_the_wrong_descriptor_type_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["numeric"])
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "is NUMERIC, expected OPERATOR",
    )


def test_an_engine_instruction_with_no_descriptor_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "descriptor ID is NO_ID",
    )


def test_a_descriptor_id_out_of_range_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=4096)
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "descriptor ID 4096 is out of range",
    )


def test_a_predicate_id_that_is_not_a_predicate_descriptor_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            predicate_id=ids["numeric"],
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program),
        capability,
        "predicate: descriptor .* expected PREDICATE",
    )


def test_a_real_predicate_descriptor_is_admitted(capability: Capability) -> None:
    from runtime.abi3.descriptors import Comparison, PredicateKind, SelectorKind

    def program(builder: Any, ids: dict[str, int]) -> None:
        predicate = builder.predicate(
            kind=PredicateKind.PHASE_IS,
            comparison=Comparison.EQ,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(Symbol.PHASE),
        )
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            predicate_id=predicate,
        )
        default_tail(builder, ids)

    report = verify_deployment(probe_deployment(capability, program=program), capability)
    assert report.admitted, report.errors


# ---------------------------------------------------------------------------
# entrypoints and selection
# ---------------------------------------------------------------------------
def test_an_entrypoint_with_a_bad_first_instruction_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(
        capability,
        entrypoints=[
            {
                "entrypoint_id": 0,
                "first_instruction": 999,
                "phase": Phase.PREFILL,
                "generation_policy_id": NO_ID,
            }
        ],
    )
    assert_rejected(deployment, capability, "bad first instruction")


def test_an_entrypoint_naming_a_non_policy_descriptor_is_rejected(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    ids = deployment.notes["probe_ids"]
    deployment = probe_deployment(
        capability,
        entrypoints=[
            {
                "entrypoint_id": 0,
                "first_instruction": 0,
                "phase": Phase.PREFILL,
                "generation_policy_id": ids["numeric"],
            }
        ],
    )
    assert_rejected(deployment, capability, "expected GENERATION_POLICY")


def test_a_generative_entrypoint_without_device_selection_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.emit(Major.CONTROL, Control.COMPLETE)

    deployment = probe_deployment(capability, program=program, generative=True)
    errors = errors_of(deployment, capability)
    assert any("host-side argmax is prohibited" in error for error in errors), errors
    assert any("never appends a token" in error for error in errors), errors


def test_a_generative_entrypoint_needs_token_append_not_just_argmax(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=ids["argmax"])
        builder.emit(Major.CONTROL, Control.COMPLETE)

    assert_rejected(
        probe_deployment(capability, program=program, generative=True),
        capability,
        "never appends a token",
    )


def test_the_entrypoint_count_must_match_the_table(capability: Capability) -> None:
    deployment = probe_deployment(capability)
    assert_rejected(
        restamp(deployment, entrypoint_count=2),
        capability,
        "entrypoint table length does not match",
    )


# ---------------------------------------------------------------------------
# structurally illegal instruction bytes never reach a proof
# ---------------------------------------------------------------------------
def test_an_illegal_opcode_in_the_body_fails_before_verification(
    capability: Capability,
) -> None:
    deployment = probe_deployment(capability)
    body = bytearray(deployment.program[256:])
    body[0] = 0x0F  # not a registered major opcode
    from runtime.abi3.crc import record_crc

    body[28:32] = b"\x00\x00\x00\x00"
    body[28:32] = record_crc(bytes(body[:32]), 28).to_bytes(4, "little")
    restamp(deployment, body=bytes(body))
    with pytest.raises(RecordError, match="unknown major opcode"):
        Verifier(deployment, capability)


# ---------------------------------------------------------------------------
# proofs the verifier claims but does not make
# ---------------------------------------------------------------------------
def test_an_operator_writing_into_a_read_only_object_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.operator(
            engine_family=Major.TENSOR,
            engine_sub=Tensor.MATMUL,
            inputs=[ids["activation_view"]],
            outputs=[ids["weight_view"]],  # read-only view over an IMMUTABLE object
            numeric_profile_id=ids["numeric"],
            key="illegal_op",
        )
        builder.emit(
            Major.TENSOR, Tensor.MATMUL, descriptor_id=builder.lookup("illegal_op")
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "read-only|IMMUTABLE"
    )


def test_the_manifest_entrypoints_must_match_the_authenticated_table(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.emit(Major.CONTROL, Control.COMPLETE)

    deployment = probe_deployment(capability, program=program, generative=True)
    assert not verify_deployment(deployment, capability).admitted
    deployment.entrypoints = tuple(
        {**entry, "generation_policy_id": NO_ID} for entry in deployment.entrypoints
    )
    assert_rejected(restamp(deployment), capability, "entrypoint")


def test_a_program_over_the_event_bound_is_rejected() -> None:
    capability = probe_capability(max_events=2)

    def program(builder: Any, ids: dict[str, int]) -> None:
        for _ in range(8):
            builder.emit(
                Major.TENSOR,
                Tensor.MATMUL,
                descriptor_id=ids["matmul"],
                signal_event_id=builder.new_event(),
            )
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    assert_rejected(deployment, capability, "event")


def test_a_program_over_the_event_id_bound_is_rejected() -> None:
    """Amendment A23.

    ``max_events`` bounds how many distinct events a program signals;
    ``max_event_id`` bounds the identifiers.  An implementation whose event
    scoreboard is a bit per ID is bounded by the second, and this program shows
    why the first does not imply it: four events, well inside a count bound of
    256, naming IDs a capability with a four-entry ID space cannot address.
    """
    capability = probe_capability(max_event_id=1)

    def program(builder: Any, ids: dict[str, int]) -> None:
        for _ in range(4):
            builder.emit(
                Major.TENSOR,
                Tensor.MATMUL,
                descriptor_id=ids["matmul"],
                signal_event_id=builder.new_event(),
            )
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    report = verify_deployment(deployment, capability)
    assert not report.admitted
    assert report.checks["event_count_bound"], "the count bound is not what refuses it"
    assert not report.checks["event_id_bound"]
    assert_rejected(deployment, capability, "capability admits IDs up to 1")


def test_a_deployment_over_the_state_resource_bound_is_rejected() -> None:
    """Amendment A22.

    One ``STATE`` descriptor is one slot in the sequencer's state slot file,
    held for the whole transaction.  A deployment declaring more resources than
    the capability has slots for is refused here rather than discovered as a
    capability trap part-way through a run.
    """
    capability = probe_capability(max_state_resources=1)

    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.state(
            state_class=StateClass.KV_CACHE,
            committed_object_id=ids["kv_committed"],
            prepared_object_id=ids["kv_prepared"],
            row_bytes=16,
            capacity_rows=32,
            element_dtype=DType.BF16,
        )
        builder.emit(Major.STATE, State.PREPARE, descriptor_id=ids["state"])
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"])
        builder.emit(Major.STATE, State.COMMIT, descriptor_id=ids["state"])
        default_tail(builder, ids)

    deployment = probe_deployment(capability, program=program)
    report = verify_deployment(deployment, capability)
    assert report.state_resources == 2
    assert not report.checks["state_resource_bound"]
    assert_rejected(
        deployment, capability, "declares 2 state resources, capability admits 1"
    )


def test_global_scope_on_a_non_communication_descriptor_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            flags=int(InstructionFlag.GLOBAL_SCOPE),
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "scope"
    )


def test_optional_feature_without_an_alternative_path_is_rejected(
    capability: Capability,
) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        builder.emit(
            Major.SELECTION,
            Selection.SAMPLE,
            descriptor_id=ids["argmax"],
            flags=int(InstructionFlag.OPTIONAL_FEATURE),
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "alternative|optional"
    )


def test_a_wait_before_its_only_producer_is_rejected(capability: Capability) -> None:
    def program(builder: Any, ids: dict[str, int]) -> None:
        event = builder.new_event()
        wait = builder.wait_set([event])
        builder.emit(
            Major.TENSOR, Tensor.MATMUL, descriptor_id=ids["matmul"], wait_set_id=wait
        )
        builder.emit(
            Major.TENSOR,
            Tensor.MATMUL,
            descriptor_id=ids["matmul"],
            signal_event_id=event,
        )
        default_tail(builder, ids)

    assert_rejected(
        probe_deployment(capability, program=program), capability, "wait|event"
    )
