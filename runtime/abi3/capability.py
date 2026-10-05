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
    NodeClass,
    TopologyClass,
    feature_bits,
    feature_vector,
)
from .crc import sha256_hex

CAPABILITY_SCHEMA = "opentallas.abi3.capability.v1"

#: Amendment AM-R1.  The keys a ``fabric`` block may carry, and the three
#: quantities that describe a two-level cluster fabric.  A capability that
#: declares no fabric omits the key entirely -- it is *not* published as an
#: empty object -- so every capability record written before AM-R1 keeps its
#: canonical bytes and therefore its digest.  That is the whole reason this
#: amendment can land without re-emitting the deployments bound to those
#: digests.
FABRIC_KEYS = ("node_class", "cluster")
FABRIC_CLUSTER_FIELDS = ("domain_size", "domains", "inter_domain_class")


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
    fabric: dict[str, Any] = dc_field(default_factory=dict)
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
        # AM-R1: absent is absent.  Publishing ``"fabric": {}`` here would move
        # the canonical bytes of every shipped capability record, and with them
        # the digests that 27 built deployment bundles and 65 committed result
        # artifacts quote (``results/abi3/amr1_topology_amendment.json``).  A
        # capability that declares no fabric between devices says so by
        # carrying no key.
        if self.fabric:
            body["fabric"] = self._canonical_fabric()
        return body

    def _canonical_fabric(self) -> dict[str, Any]:
        fabric: dict[str, Any] = {}
        if "node_class" in self.fabric:
            fabric["node_class"] = int(self.fabric["node_class"])
        cluster = self.fabric.get("cluster")
        if cluster is not None:
            fabric["cluster"] = {
                k: int(v) for k, v in sorted(dict(cluster).items())
            }
        return fabric

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
            # Exactly 32, not at least 32.  ``>= 32`` let a 48-node capability
            # pass under the wrong class name; a cluster of another size is a
            # different topology class (CLUSTER_N, amendment AM-R1), not a
            # larger CLUSTER_32.  Found while planning the ROM array target.
            # AM-R1 does not relax this: four shipped records name CLUSTER_32
            # and the deployments bound to them quote their digests, so the
            # class keeps its exact cardinality and the amendment adds a class
            # beside it rather than widening this one.
            if self.limits.get("max_nodes", 0) != 32:
                raise ValueError(
                    "CLUSTER_32 capability must declare exactly 32 nodes; "
                    f"declares {self.limits.get('max_nodes', 0)}"
                )
            if Feature.INTER_CHIP_ENDPOINT not in self.features:
                raise ValueError("CLUSTER_32 capability must advertise bit 8")
        if self.topology_class == TopologyClass.WAFER_LOGICAL_DEVICE:
            if Feature.WAFER_ENDPOINT not in self.features:
                raise ValueError("wafer capability must advertise bit 9")
        self._validate_fabric()

    def _validate_fabric(self) -> None:
        """Amendment AM-R1: the node count and the fabric between the nodes.

        Two rules carry the amendment.  A ``CLUSTER_N`` must say how many nodes
        it has *and* what fabric joins them, because the class exists precisely
        to stop a multi-die machine being described as a single chip; and a
        fabric may be declared only where there is more than one device for it
        to join, because a fabric on a one-device capability is a field no
        consumer can act on.
        """

        nodes = int(self.limits.get("max_nodes", 0))
        is_cluster_n = self.topology_class == TopologyClass.CLUSTER_N

        if is_cluster_n:
            if nodes < 2:
                raise ValueError(
                    "CLUSTER_N capability must declare at least 2 nodes; a "
                    f"one-node machine is SINGLE_CHIP, and this declares {nodes}"
                )
            if nodes == 32:
                raise ValueError(
                    "CLUSTER_N capability must not declare exactly 32 nodes; "
                    "32 nodes is CLUSTER_32, and one machine with two "
                    "expressible topology classes is an asymmetry no digest "
                    "comparison can see through"
                )
            if Feature.INTER_CHIP_ENDPOINT not in self.features:
                raise ValueError("CLUSTER_N capability must advertise bit 8")
            if "cluster" not in self.fabric:
                raise ValueError(
                    "CLUSTER_N capability must declare fabric.cluster "
                    f"{list(FABRIC_CLUSTER_FIELDS)}; the class exists to name "
                    "the fabric between its nodes"
                )

        if not self.fabric:
            return

        unknown = sorted(set(self.fabric) - set(FABRIC_KEYS))
        if unknown:
            raise ValueError(f"capability fabric declares unknown keys {unknown}")
        if nodes < 2:
            raise ValueError(
                "capability declares a fabric between devices but only "
                f"{nodes} node(s); a fabric needs something to join"
            )

        node_class = NodeClass(int(self.fabric.get("node_class", NodeClass.DIE)))
        if node_class == NodeClass.WAFER:
            # Both bits, together.  A wafer-class node has an internal fabric
            # (bit 9) *and* sits on a fabric between nodes (bit 8); a record
            # that claims one is describing half a machine.
            required = {Feature.INTER_CHIP_ENDPOINT, Feature.WAFER_ENDPOINT}
            absent = sorted(int(f) for f in required - set(self.features))
            if absent:
                raise ValueError(
                    "wafer-class nodes require feature bits 8 and 9 together; "
                    f"capability omits {absent}"
                )

        cluster = self.fabric.get("cluster")
        if cluster is None:
            return
        missing = [k for k in FABRIC_CLUSTER_FIELDS if k not in cluster]
        if missing:
            raise ValueError(f"capability fabric.cluster is missing {missing}")
        extra = sorted(set(cluster) - set(FABRIC_CLUSTER_FIELDS))
        if extra:
            raise ValueError(f"capability fabric.cluster declares unknown {extra}")
        domain_size = int(cluster["domain_size"])
        domains = int(cluster["domains"])
        inter_domain_class = int(cluster["inter_domain_class"])
        if domain_size < 1 or domains < 1:
            raise ValueError(
                "capability fabric.cluster domain_size and domains must be "
                f"positive; declares {domain_size} and {domains}"
            )
        if inter_domain_class < 0:
            raise ValueError(
                "capability fabric.cluster inter_domain_class must be a link "
                f"class id; declares {inter_domain_class}"
            )
        if domain_size * domains != nodes:
            raise ValueError(
                f"capability fabric.cluster partitions {domain_size} x "
                f"{domains} = {domain_size * domains} nodes, but the "
                f"capability declares {nodes}"
            )
        if domains == 1 and inter_domain_class != 0:
            raise ValueError(
                "capability fabric.cluster declares one domain and an "
                f"inter-domain link class {inter_domain_class}; a single-level "
                "fabric has no inter-domain hop to price"
            )

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
            fabric={
                key: (dict(value) if isinstance(value, Mapping) else value)
                for key, value in dict(body.get("fabric", {})).items()
            },
            technology_view=body.get("technology_view", "uncharacterized"),
            abi_minor=abi["minor"],
        )
        capability.validate()
        return capability
