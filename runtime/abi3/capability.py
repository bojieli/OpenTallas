"""ABI 3.0 capability record.

ADR-003 section 14 requires a capability that "reports exact limits and
implemented numeric contracts", and requires every program to bind the digest of
the capability it was compiled against.  The capability is expressed as
canonical JSON rather than a fixed binary record: it is a discovery structure
read once at admission, and the quantitative fields in it (SRAM size, engine
lane count, link width, clock) are explicitly deferred by ADR-003 section 19, so
freezing a binary layout for them would freeze the wrong thing.

What *is* frozen is the field set, the digest rule, and the admission rule.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping

from .constants import (
    ABI_MAJOR,
    ABI_MINOR,
    Feature,
    TopologyClass,
    feature_bits,
    feature_vector,
)
from .crc import sha256_hex

CAPABILITY_SCHEMA = "opentallas.abi3.capability.v1"


def canonical_json(value: Any) -> bytes:
    """Deterministic JSON: sorted keys, compact separators, ASCII, trailing LF.

    Every digest in ABI 3.0 that covers a JSON document covers exactly these
    bytes, so two builds of the same content are byte-identical.
    """
    text = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return (text + "\n").encode("ascii")


def digest_of(value: Any) -> str:
    return sha256_hex(canonical_json(value))


@dataclass(slots=True)
class Capability:
    """One implementation's exact advertised limits."""

    capability_id: str
    topology_class: int
    features: tuple[int, ...]
    limits: dict[str, int]
    numeric_contracts: tuple[str, ...]
    engines: dict[str, dict[str, int]]
    memory: dict[str, dict[str, int]]
    link: dict[str, int] = dc_field(default_factory=dict)
    technology_view: str = "uncharacterized"
    abi_major: int = ABI_MAJOR
    abi_minor: int = ABI_MINOR

    REQUIRED_LIMITS = (
        "max_instructions",
        "max_descriptors",
        "max_loop_depth",
        "max_loop_trip",
        "max_retired_work",
        "max_events",
        # Amendment A23.  ``max_events`` counts distinct event IDs; an
        # implementation whose scoreboard is indexed by event ID is bounded by
        # the largest ID it must hold, which the count does not express.  Both
        # are required: the count bounds the scoreboard's occupancy and the ID
        # bounds its address space.
        "max_event_id",
        "max_outstanding_per_queue",
        "max_context_positions",
        "max_expert_ids",
        "max_topk",
        "max_vocabulary",
        "max_sessions",
        "max_nodes",
        # Amendment A22.  The number of STATE resources a deployment may
        # declare.  A transactional-state implementation holds one slot per
        # declared resource for the life of a transaction, so this is real
        # storage and, before A22, was the one sequencer bound no capability
        # field named.
        "max_state_resources",
    )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema": CAPABILITY_SCHEMA,
            "abi": {"major": self.abi_major, "minor": self.abi_minor},
            "topology_class": int(self.topology_class),
            "features": sorted(int(f) for f in self.features),
            "limits": {k: int(v) for k, v in sorted(self.limits.items())},
            "numeric_contracts": sorted(self.numeric_contracts),
            "engines": {
                name: {k: int(v) for k, v in sorted(spec.items())}
                for name, spec in sorted(self.engines.items())
            },
            "memory": {
                name: {k: int(v) for k, v in sorted(spec.items())}
                for name, spec in sorted(self.memory.items())
            },
            "link": {k: int(v) for k, v in sorted(self.link.items())},
            "technology_view": self.technology_view,
        }
        return body

    @property
    def digest(self) -> str:
        return digest_of(self.to_dict())

    def validate(self) -> None:
        TopologyClass(self.topology_class)
        missing = [k for k in self.REQUIRED_LIMITS if k not in self.limits]
        if missing:
            raise ValueError(f"capability is missing limits: {missing}")
        for name, value in self.limits.items():
            if int(value) <= 0:
                raise ValueError(f"capability limit {name} must be positive")
        # A22/A23 self-consistency.  A scoreboard addressed by event ID holds
        # ``max_event_id + 1`` entries, so it cannot carry more distinct
        # signalled events than that.  A capability claiming otherwise is
        # describing a machine nothing can build, and before this check it
        # could: ``hbm_sram_*`` advertised 4,096 distinct events over an ID
        # space no implementation provides.
        if self.limits["max_events"] > self.limits["max_event_id"] + 1:
            raise ValueError(
                f"capability admits {self.limits['max_events']} distinct events "
                f"in an event ID space of {self.limits['max_event_id'] + 1}"
            )
        for bit in self.features:
            Feature(bit)
        mandatory = {
            Feature.HOST_QUEUE_ABI,
            Feature.DEPLOYMENT_DESCRIPTOR_ABI,
            Feature.DETERMINISTIC_MICROSEQUENCER,
            Feature.TRANSACTIONAL_STATE,
            Feature.ON_DEVICE_SELECTION,
        }
        absent = sorted(int(f) for f in mandatory - set(self.features))
        if absent:
            raise ValueError(f"capability omits mandatory feature bits {absent}")
        if self.topology_class == TopologyClass.CLUSTER_32:
            if self.limits.get("max_nodes", 0) < 32:
                raise ValueError("CLUSTER_32 capability must admit 32 nodes")
            if Feature.INTER_CHIP_ENDPOINT not in self.features:
                raise ValueError("CLUSTER_32 capability must advertise bit 8")
        if self.topology_class == TopologyClass.WAFER_LOGICAL_DEVICE:
            if Feature.WAFER_ENDPOINT not in self.features:
                raise ValueError("wafer capability must advertise bit 9")

    def feature_vector(self) -> bytes:
        return feature_vector(self.features)

    def admits(self, required: bytes) -> tuple[bool, list[int]]:
        """Return ``(ok, missing_bits)`` for a program's required-feature vector.

        ADR-003 section 14: a 3.x implementation accepts a program only when all
        required feature bits are supported.  There is no silent emulation.
        """
        need = feature_bits(required)
        have = set(int(f) for f in self.features)
        missing = sorted(need - have)
        return (not missing), missing

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "Capability":
        if body.get("schema") != CAPABILITY_SCHEMA:
            raise ValueError(f"unexpected capability schema {body.get('schema')!r}")
        abi = body["abi"]
        if abi["major"] != ABI_MAJOR:
            raise ValueError("capability declares a different ABI major version")
        capability = cls(
            capability_id=digest_of(dict(body)),
            topology_class=body["topology_class"],
            features=tuple(body["features"]),
            limits=dict(body["limits"]),
            numeric_contracts=tuple(body["numeric_contracts"]),
            engines={k: dict(v) for k, v in body["engines"].items()},
            memory={k: dict(v) for k, v in body["memory"].items()},
            link=dict(body.get("link", {})),
            technology_view=body.get("technology_view", "uncharacterized"),
            abi_minor=abi["minor"],
        )
        capability.validate()
        return capability
