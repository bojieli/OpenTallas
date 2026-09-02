"""Conformance suite for amendment A14 -- the scope of a collective's participants.

Wire format section 12.5 adds one byte to the ``COMMUNICATION`` payload and
changes nothing else.  Three properties carry the whole amendment, and each is
proved here rather than asserted:

*the field is where the document says it is*
    offset 80, one byte, with the reserved span shrunk to 47 bytes at 81.

*zero means* ``NODE``, *and no existing byte moves*
    reserved bytes must be zero on both encode and decode, so a program written
    before A14 carries zero at offset 80.  The test reconstructs the *pre-A14*
    layout from the document -- 48 reserved bytes at offset 80 -- encodes a
    payload with it, and requires the post-A14 decoder to read that exact byte
    string as ``NODE`` with every other field unchanged.  It is the record a
    pre-amendment encoder produced, not a re-encoding of it.

*the two admission rules*
    a scope the topology cannot support is refused, and a ``SINGLE_CHIP``
    topology admits only ``NODE``.

The suite is written against the contract: the pre-A14 layout is built here
from the document's own field table, not imported from history.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Feature,
    NO_ID,
    IntegrityMode,
    Major,
    Ordering,
    ParticipantScope,
    TopologyClass,
)
from runtime.abi3.descriptors import (
    COMMUNICATION_PAYLOAD,
    TOPOLOGY_PAYLOAD,
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
)
from runtime.abi3.crc import sha256
from runtime.abi3.layout import Field, Layout, RecordError
from runtime.abi3.verifier import verify_deployment

from . import patched_payload, probe_capability, probe_deployment, restamp

# ---------------------------------------------------------------------------
# The layout, from the document
# ---------------------------------------------------------------------------
#: The ``COMMUNICATION`` payload exactly as it was frozen *before* A14: the same
#: fields up to ``chunk_bytes``, then one 48-byte reserved span at offset 80.
#: Reconstructing it here is what makes the compatibility test meaningful --
#: the bytes it produces are the bytes a pre-amendment encoder produced.
PRE_A14_COMMUNICATION_PAYLOAD = Layout(
    "communication_pre_a14",
    128,
    [
        Field("collective_op", 0, 1),
        Field("ordering", 1, 1),
        Field("integrity_mode", 2, 1),
        Field("virtual_channel", 3, 1),
        Field("source_node", 4, 2),
        Field("destination_node", 6, 2),
        Field("group_id", 8, 4),
        Field("route_class", 12, 4),
        Field("local_object_id", 16, 4),
        Field("remote_object_id", 20, 4),
        Field("local_offset", 24, 8),
        Field("remote_offset", 32, 8),
        Field("byte_extent", 40, 8),
        Field("credit_bound", 48, 4),
        Field("retry_bound", 52, 4),
        Field("timeout_class", 56, 4),
        Field("completion_event_id", 60, 4),
        Field("reduction_numeric_id", 64, 4),
        Field("counter_class_id", 68, 4),
        Field("participant_count", 72, 4),
        Field("chunk_bytes", 76, 4),
        Field("reserved", 80, 48, "reserved"),
    ],
)

#: One fully populated pre-A14 payload.  Every field carries a distinctive
#: value so that a field that moved would be visible as a changed value, not
#: merely as a changed digest.
PRE_A14_VALUES: dict[str, int] = {
    "collective_op": int(CollectiveOp.SUM),
    "ordering": int(Ordering.RELEASE),
    "integrity_mode": int(IntegrityMode.CRC32C),
    "virtual_channel": 2,
    "source_node": 3,
    "destination_node": 7,
    "group_id": 1,
    "route_class": 2,
    "local_object_id": 11,
    "remote_object_id": 12,
    "local_offset": 4096,
    "remote_offset": 8192,
    "byte_extent": 65536,
    "credit_bound": 8,
    "retry_bound": 3,
    "timeout_class": 1,
    "completion_event_id": 5,
    "reduction_numeric_id": 9,
    "counter_class_id": 6,
    "participant_count": 32,
    "chunk_bytes": 4096,
}


def test_participant_scope_is_one_byte_at_offset_eighty() -> None:
    """Section 12.5: offset 80, one byte; reserved shrinks to 47 at 81."""
    scope = COMMUNICATION_PAYLOAD.field("participant_scope")
    assert (scope.offset, scope.size, scope.kind) == (80, 1, "uint")
    reserved = COMMUNICATION_PAYLOAD.field("reserved")
    assert (reserved.offset, reserved.size, reserved.kind) == (81, 47, "reserved")
    # The payload is still 128 bytes and still gap-free: Layout proves both at
    # construction, so reaching this line at all is part of the proof.
    assert COMMUNICATION_PAYLOAD.size == 128


def test_the_scope_registry_is_node_reticle_tile() -> None:
    assert [(s.name, int(s)) for s in ParticipantScope] == [
        ("NODE", 0),
        ("RETICLE", 1),
        ("TILE", 2),
    ]


# ---------------------------------------------------------------------------
# zero means NODE
# ---------------------------------------------------------------------------
def test_a_pre_amendment_record_decodes_as_node_with_no_field_moved() -> None:
    """The compatibility property, on bytes a pre-A14 encoder produced."""
    pre = bytes(PRE_A14_COMMUNICATION_PAYLOAD.encode(PRE_A14_VALUES))
    assert pre[80:128] == bytes(48)

    decoded = COMMUNICATION_PAYLOAD.decode(pre)
    assert decoded["participant_scope"] == int(ParticipantScope.NODE)
    for name, value in PRE_A14_VALUES.items():
        assert decoded[name] == value, name


def test_encoding_node_reproduces_the_pre_amendment_bytes_exactly() -> None:
    """No byte of any existing program moves: the encodings are identical."""
    pre = bytes(PRE_A14_COMMUNICATION_PAYLOAD.encode(PRE_A14_VALUES))
    post = bytes(
        COMMUNICATION_PAYLOAD.encode(
            {**PRE_A14_VALUES, "participant_scope": int(ParticipantScope.NODE)}
        )
    )
    assert post == pre


def test_a_whole_pre_amendment_descriptor_record_is_unchanged() -> None:
    """Header, payload and CRC together, not just the payload."""

    def record(payload: dict[str, int], raw: bytes | None) -> bytes:
        return Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=int(ExtendedDescriptorType.COMMUNICATION),
            payload=payload,
            raw_payload=raw,
        ).encode()

    pre = record({}, bytes(PRE_A14_COMMUNICATION_PAYLOAD.encode(PRE_A14_VALUES)))
    post = record(
        {**PRE_A14_VALUES, "participant_scope": int(ParticipantScope.NODE)}, None
    )
    assert post == pre
    assert len(pre) == 192
    # And the round trip reads the amendment's default out of the old record.
    assert Descriptor.decode(pre).payload["participant_scope"] == int(
        ParticipantScope.NODE
    )


def test_the_reserved_span_is_still_checked_on_encode_and_decode() -> None:
    """A14 is only additive because reserved bytes are zero in both directions.

    If either direction stopped checking, a nonzero byte at offset 80 could
    reach a decoder that reads it as a scope, and "zero means NODE" would stop
    being a property of every conforming record.
    """
    values = {**PRE_A14_VALUES, "participant_scope": int(ParticipantScope.TILE)}
    with pytest.raises(RecordError, match="reserved and must be zero"):
        COMMUNICATION_PAYLOAD.encode({**values, "reserved": 1})

    encoded = bytearray(COMMUNICATION_PAYLOAD.encode(values))
    for index in (81, 100, 127):
        corrupted = bytearray(encoded)
        corrupted[index] = 0xFF
        with pytest.raises(RecordError, match="reserved bytes are nonzero"):
            COMMUNICATION_PAYLOAD.decode(bytes(corrupted))


def test_the_byte_holds_values_the_registry_does_not_assign() -> None:
    """One byte holds 0..255; only three of those values name a scope.

    The layout carries an unsigned byte and says nothing about which values
    are legal, so an unassigned value survives a round trip.  Refusing it is
    the verifier's and the engine's job, and both do -- see the admission case
    below and ``tests/sim/test_engines_link_participant_scope.py``.
    """
    with pytest.raises(ValueError):
        ParticipantScope(3)
    assert COMMUNICATION_PAYLOAD.decode(
        bytes(COMMUNICATION_PAYLOAD.encode({**PRE_A14_VALUES, "participant_scope": 255}))
    )["participant_scope"] == 255


# ---------------------------------------------------------------------------
# admission
# ---------------------------------------------------------------------------
def link_program(scope: ParticipantScope) -> Any:
    """A probe program whose one LINK instruction names a scoped collective."""

    def program(builder: Any, ids: dict[str, int]) -> None:
        from runtime.abi3.constants import Control, Link, Selection

        communication = builder.communication(
            collective_op=CollectiveOp.SUM,
            local_object_id=ids["activations"],
            remote_object_id=ids["activations"],
            source_node=0,
            destination_node=0,
            byte_extent=64,
            participant_count=1,
            participant_scope=scope,
            reduction_numeric_id=ids["numeric"],
        )
        ids["communication"] = communication
        builder.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=communication)
        builder.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=ids["argmax"])
        builder.emit(
            Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=ids["append"]
        )
        builder.emit(Major.CONTROL, Control.COMPLETE)

    return program


def as_wafer(
    deployment: Any,
    capability: Capability,
    *,
    reticles: int,
    tiles: int,
    active_resources: int = 0,
    capability_link: dict[str, int] | None = None,
) -> tuple[Any, Capability]:
    """Bind the probe and a matching capability to one genuine wafer topology."""

    capability_body = capability.to_dict()
    capability_body["topology_class"] = int(TopologyClass.WAFER_LOGICAL_DEVICE)
    capability_body["features"] = sorted(
        {*capability.features, int(Feature.WAFER_ENDPOINT)}
    )
    capability_body["link"] = (
        capability_link
        if capability_link is not None
        else {
            "reticle_rows": 6,
            "reticle_columns": 8,
            "tiles_per_reticle": 16,
        }
    )
    wafer_capability = Capability.from_dict(capability_body)

    topology = deployment.table.ids_of_type(int(ExtendedDescriptorType.TOPOLOGY))[0]
    table = patched_payload(
        deployment.table,
        topology,
        TOPOLOGY_PAYLOAD,
        "topology_class",
        int(TopologyClass.WAFER_LOGICAL_DEVICE),
    )
    table = patched_payload(table, topology, TOPOLOGY_PAYLOAD, "reticle_count", reticles)
    table = patched_payload(
        table, topology, TOPOLOGY_PAYLOAD, "tiles_per_reticle", tiles
    )
    table = patched_payload(
        table,
        topology,
        TOPOLOGY_PAYLOAD,
        "active_resource_count",
        active_resources,
    )
    deployment.table = table
    deployment.topology_class = int(TopologyClass.WAFER_LOGICAL_DEVICE)
    deployment.capability_digest = wafer_capability.digest
    topology_digest = sha256(deployment.table[topology].encode())
    return restamp(deployment, topology_digest=topology_digest), wafer_capability


def errors_of(deployment: Any, capability: Capability) -> list[str]:
    report = verify_deployment(deployment, capability)
    assert not report.admitted, "deployment was admitted but should have been refused"
    return report.errors


def assert_refused(deployment: Any, capability: Capability, pattern: str) -> None:
    errors = errors_of(deployment, capability)
    assert any(re.search(pattern, error) for error in errors), (
        f"no error matched {pattern!r}; got {errors}"
    )


@pytest.fixture()
def capability() -> Capability:
    return probe_capability()


def test_a_node_scoped_collective_is_admitted_on_chip_and_on_wafer(capability) -> None:
    """The baseline every refusal below is measured against.

    ``NODE`` is what a pre-A14 program means, so it must be admitted on the
    single-chip topology the probe builds *and* on a wafer that declares no
    reticle or tile counts at all -- otherwise the amendment would refuse
    programs that were legal before it existed.
    """
    chip_deployment = probe_deployment(
        capability, program=link_program(ParticipantScope.NODE)
    )
    wafer_deployment = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.NODE)),
        capability,
        reticles=0,
        tiles=0,
    )
    for deployment, admitted_capability in (
        (chip_deployment, capability),
        wafer_deployment,
    ):
        report = verify_deployment(deployment, admitted_capability)
        assert report.admitted, report.errors
        assert report.checks["participant_scope_supported"]
        assert report.checks["participant_scope_topology_class"]


def test_a_reticle_scope_against_a_zero_reticle_count_is_refused(capability) -> None:
    """First admission rule: a scope the topology cannot support."""
    deployment, wafer_capability = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.RETICLE)),
        capability,
        reticles=0,
        tiles=16,
    )
    assert_refused(deployment, wafer_capability, "no reticle fabric to address")


def test_a_tile_scope_against_a_zero_tiles_per_reticle_is_refused(capability) -> None:
    """Same rule, the other fabric: reticles exist, tiles do not."""
    deployment, wafer_capability = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.TILE)),
        capability,
        reticles=4,
        tiles=0,
    )
    assert_refused(deployment, wafer_capability, "no tile fabric to address")


def test_a_supported_scope_on_a_wafer_is_admitted(capability) -> None:
    """The rule refuses an absent fabric, not the scope itself."""
    for scope in (ParticipantScope.RETICLE, ParticipantScope.TILE):
        deployment, wafer_capability = as_wafer(
            probe_deployment(capability, program=link_program(scope)),
            capability,
            reticles=4,
            tiles=16,
        )
        report = verify_deployment(deployment, wafer_capability)
        assert report.admitted, (scope, report.errors)


def test_wafer_topology_admits_an_active_prefix(capability) -> None:
    deployment, wafer_capability = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.NODE)),
        capability,
        reticles=37,
        tiles=16,
        active_resources=37 * 16,
    )
    report = verify_deployment(deployment, wafer_capability)
    assert report.admitted, report.errors
    assert report.checks["wafer_topology_active_prefix"]
    assert report.checks["wafer_topology_tiles_per_reticle"]
    assert report.checks["wafer_topology_active_resources"]


@pytest.mark.parametrize(
    "reticles,tiles,active,pattern",
    [
        (49, 16, 0, "larger than physical capacity 48"),
        (48, 8, 0, "exactly match capability value 16"),
        (1, 16, 17, "fit its declared endpoint prefix of 16"),
    ],
)
def test_wafer_topology_refuses_geometry_outside_the_capability(
    capability, reticles: int, tiles: int, active: int, pattern: str
) -> None:
    deployment, wafer_capability = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.NODE)),
        capability,
        reticles=reticles,
        tiles=tiles,
        active_resources=active,
    )
    assert_refused(deployment, wafer_capability, pattern)


@pytest.mark.parametrize(
    "capability_link,pattern",
    [
        ({"reticle_rows": 6}, "complete physical geometry"),
        (
            {
                "reticle_rows": 0,
                "reticle_columns": 8,
                "tiles_per_reticle": 16,
            },
            "physical geometry must be positive",
        ),
    ],
)
def test_wafer_capability_requires_complete_positive_geometry(
    capability, capability_link: dict[str, int], pattern: str
) -> None:
    deployment, wafer_capability = as_wafer(
        probe_deployment(capability, program=link_program(ParticipantScope.NODE)),
        capability,
        reticles=1,
        tiles=16,
        capability_link=capability_link,
    )
    assert_refused(deployment, wafer_capability, pattern)


def test_a_single_chip_topology_admits_only_node(capability) -> None:
    """Second admission rule, isolated from the first.

    The topology here declares a reticle and tile fabric, so the
    "unsupported scope" rule passes; what refuses the deployment is the
    topology *class*, because a chip has no such fabric however its counts
    are filled in.
    """
    for scope in (ParticipantScope.RETICLE, ParticipantScope.TILE):
        deployment = probe_deployment(capability, program=link_program(scope))
        topology = deployment.table.ids_of_type(
            int(ExtendedDescriptorType.TOPOLOGY)
        )[0]
        table = patched_payload(
            deployment.table, topology, TOPOLOGY_PAYLOAD, "reticle_count", 4
        )
        table = patched_payload(
            table, topology, TOPOLOGY_PAYLOAD, "tiles_per_reticle", 16
        )
        deployment.table = table
        deployment = restamp(deployment)
        report = verify_deployment(deployment, capability)
        assert not report.admitted
        assert report.checks["participant_scope_supported"], (
            "the unsupported-fabric rule must pass here, or this test is "
            "proving the wrong refusal"
        )
        assert not report.checks["participant_scope_topology_class"]
        assert any(
            "single-chip deployment admits only NODE" in error
            for error in report.errors
        ), report.errors


def test_a_scope_outside_the_registry_is_refused_at_admission(capability) -> None:
    deployment = probe_deployment(capability, program=link_program(ParticipantScope.NODE))
    communication = deployment.table.ids_of_type(
        int(ExtendedDescriptorType.COMMUNICATION)
    )[0]
    deployment.table = patched_payload(
        deployment.table,
        communication,
        COMMUNICATION_PAYLOAD,
        "participant_scope",
        7,
    )
    assert_refused(restamp(deployment), capability, "not in the frozen registry")


def test_a_deployment_with_no_communication_descriptor_is_untouched(capability) -> None:
    """A14 adds no obligation to a program that names no collective."""
    report = verify_deployment(probe_deployment(capability), capability)
    assert report.admitted, report.errors
    assert "participant_scope_supported" not in report.checks
