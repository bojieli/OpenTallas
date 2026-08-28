"""Versioned hardware capability contract for tensor-accelerator lowering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_power_of_two,
    require_sha256,
    sha256_bytes,
)


SCHEMA = "opentallas.tensor_accelerator.capability.v1"


class CapabilityError(ArtifactError):
    """Raised when a hardware capability record is malformed or inconsistent."""


@dataclass(frozen=True)
class HBMCapability:
    channels: int
    pseudo_channels_per_channel: int
    capacity_bytes: int
    burst_bytes: int
    read_latency_cycles: int
    write_latency_cycles: int
    max_outstanding_per_channel: int


@dataclass(frozen=True)
class SRAMCapability:
    banks: int
    bytes_per_bank: int
    word_bytes: int
    read_ports_per_bank: int
    write_ports_per_bank: int
    read_latency_cycles: int
    write_latency_cycles: int

    @property
    def capacity_bytes(self) -> int:
        return self.banks * self.bytes_per_bank


@dataclass(frozen=True)
class DMAEngine:
    count: int
    issue_bytes_per_cycle: int


@dataclass(frozen=True)
class TensorEngine:
    count: int
    macs_per_cycle: int
    setup_cycles: int
    max_m: int
    max_n: int
    max_k: int


@dataclass(frozen=True)
class VectorEngine:
    count: int
    elements_per_cycle: int
    setup_cycles: int


@dataclass(frozen=True)
class Capability:
    capability_id: str
    clock_hz: int
    numeric_profiles: tuple[str, ...]
    hbm: HBMCapability
    sram: SRAMCapability
    dma: DMAEngine
    tensor: TensorEngine
    vector: VectorEngine
    limits: Mapping[str, int]
    raw: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)


def _object(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CapabilityError(f"{label} must be an object")
    return raw


def _parse_hbm(raw: Any) -> HBMCapability:
    value = _object(raw, "hbm")
    exact_keys(
        value,
        {
            "channels",
            "pseudo_channels_per_channel",
            "capacity_bytes",
            "burst_bytes",
            "read_latency_cycles",
            "write_latency_cycles",
            "max_outstanding_per_channel",
        },
        set(),
        "hbm",
    )
    return HBMCapability(
        require_int(value["channels"], "hbm.channels", minimum=1, maximum=32),
        require_int(
            value["pseudo_channels_per_channel"],
            "hbm.pseudo_channels_per_channel",
            minimum=1,
            maximum=8,
        ),
        require_int(
            value["capacity_bytes"],
            "hbm.capacity_bytes",
            minimum=4096,
            maximum=1 << 50,
        ),
        require_power_of_two(
            value["burst_bytes"],
            "hbm.burst_bytes",
            minimum=16,
            maximum=1024,
        ),
        require_int(
            value["read_latency_cycles"],
            "hbm.read_latency_cycles",
            minimum=1,
            maximum=1_000_000,
        ),
        require_int(
            value["write_latency_cycles"],
            "hbm.write_latency_cycles",
            minimum=1,
            maximum=1_000_000,
        ),
        require_int(
            value["max_outstanding_per_channel"],
            "hbm.max_outstanding_per_channel",
            minimum=1,
            maximum=1 << 20,
        ),
    )


def _parse_sram(raw: Any) -> SRAMCapability:
    value = _object(raw, "sram")
    exact_keys(
        value,
        {
            "banks",
            "bytes_per_bank",
            "word_bytes",
            "read_ports_per_bank",
            "write_ports_per_bank",
            "read_latency_cycles",
            "write_latency_cycles",
        },
        set(),
        "sram",
    )
    banks = require_power_of_two(
        value["banks"], "sram.banks", minimum=1, maximum=1024
    )
    bytes_per_bank = require_power_of_two(
        value["bytes_per_bank"],
        "sram.bytes_per_bank",
        minimum=256,
        maximum=1 << 40,
    )
    word_bytes = require_power_of_two(
        value["word_bytes"],
        "sram.word_bytes",
        minimum=1,
        maximum=128,
    )
    if bytes_per_bank % word_bytes:
        raise CapabilityError("sram.bytes_per_bank must be divisible by word_bytes")
    return SRAMCapability(
        banks,
        bytes_per_bank,
        word_bytes,
        require_int(
            value["read_ports_per_bank"],
            "sram.read_ports_per_bank",
            minimum=1,
            maximum=16,
        ),
        require_int(
            value["write_ports_per_bank"],
            "sram.write_ports_per_bank",
            minimum=1,
            maximum=16,
        ),
        require_int(
            value["read_latency_cycles"],
            "sram.read_latency_cycles",
            minimum=1,
            maximum=1000,
        ),
        require_int(
            value["write_latency_cycles"],
            "sram.write_latency_cycles",
            minimum=1,
            maximum=1000,
        ),
    )


def _parse_engines(raw: Any) -> tuple[DMAEngine, TensorEngine, VectorEngine]:
    engines = _object(raw, "engines")
    exact_keys(engines, {"dma", "tensor", "vector"}, set(), "engines")
    dma_raw = _object(engines["dma"], "engines.dma")
    exact_keys(
        dma_raw,
        {"count", "issue_bytes_per_cycle"},
        set(),
        "engines.dma",
    )
    dma = DMAEngine(
        require_int(dma_raw["count"], "engines.dma.count", minimum=1, maximum=64),
        require_int(
            dma_raw["issue_bytes_per_cycle"],
            "engines.dma.issue_bytes_per_cycle",
            minimum=1,
            maximum=1 << 20,
        ),
    )
    tensor_raw = _object(engines["tensor"], "engines.tensor")
    exact_keys(
        tensor_raw,
        {"count", "macs_per_cycle", "setup_cycles", "max_m", "max_n", "max_k"},
        set(),
        "engines.tensor",
    )
    tensor = TensorEngine(
        require_int(
            tensor_raw["count"], "engines.tensor.count", minimum=1, maximum=1024
        ),
        require_int(
            tensor_raw["macs_per_cycle"],
            "engines.tensor.macs_per_cycle",
            minimum=1,
            maximum=1 << 30,
        ),
        require_int(
            tensor_raw["setup_cycles"],
            "engines.tensor.setup_cycles",
            minimum=0,
            maximum=1_000_000,
        ),
        require_int(
            tensor_raw["max_m"], "engines.tensor.max_m", minimum=1, maximum=1 << 20
        ),
        require_int(
            tensor_raw["max_n"], "engines.tensor.max_n", minimum=1, maximum=1 << 20
        ),
        require_int(
            tensor_raw["max_k"], "engines.tensor.max_k", minimum=1, maximum=1 << 20
        ),
    )
    vector_raw = _object(engines["vector"], "engines.vector")
    exact_keys(
        vector_raw,
        {"count", "elements_per_cycle", "setup_cycles"},
        set(),
        "engines.vector",
    )
    vector = VectorEngine(
        require_int(
            vector_raw["count"], "engines.vector.count", minimum=1, maximum=1024
        ),
        require_int(
            vector_raw["elements_per_cycle"],
            "engines.vector.elements_per_cycle",
            minimum=1,
            maximum=1 << 30,
        ),
        require_int(
            vector_raw["setup_cycles"],
            "engines.vector.setup_cycles",
            minimum=0,
            maximum=1_000_000,
        ),
    )
    return dma, tensor, vector


def parse_capability(raw: dict[str, Any]) -> Capability:
    try:
        exact_keys(
            raw,
            {
                "schema",
                "capability_id",
                "clock_hz",
                "numeric_profiles",
                "hbm",
                "sram",
                "engines",
                "limits",
            },
            set(),
            "capability",
        )
        if raw["schema"] != SCHEMA:
            raise CapabilityError(f"unsupported capability schema {raw['schema']!r}")
        capability_id = require_sha256(raw["capability_id"], "capability_id")
        body = dict(raw)
        del body["capability_id"]
        observed_id = sha256_bytes(canonical_json_bytes(body))
        if capability_id != observed_id:
            raise CapabilityError(
                f"capability_id mismatch: expected {observed_id}, observed {capability_id}"
            )
        clock_hz = require_int(
            raw["clock_hz"], "clock_hz", minimum=1, maximum=100_000_000_000
        )
        profiles = raw["numeric_profiles"]
        if (
            not isinstance(profiles, list)
            or not profiles
            or len(set(profiles)) != len(profiles)
            or any(not isinstance(profile, str) or not profile for profile in profiles)
        ):
            raise CapabilityError("numeric_profiles must be a non-empty unique string array")
        hbm = _parse_hbm(raw["hbm"])
        sram = _parse_sram(raw["sram"])
        dma, tensor, vector = _parse_engines(raw["engines"])
        limits_raw = _object(raw["limits"], "limits")
        exact_keys(
            limits_raw,
            {
                "max_commands",
                "max_rank",
                "max_tensor_bytes",
                "max_runtime_symbols",
            },
            set(),
            "limits",
        )
        limits = {
            "max_commands": require_int(
                limits_raw["max_commands"],
                "limits.max_commands",
                minimum=1,
                maximum=1 << 30,
            ),
            "max_rank": require_int(
                limits_raw["max_rank"],
                "limits.max_rank",
                minimum=1,
                maximum=8,
            ),
            "max_tensor_bytes": require_int(
                limits_raw["max_tensor_bytes"],
                "limits.max_tensor_bytes",
                minimum=1,
                maximum=1 << 50,
            ),
            "max_runtime_symbols": require_int(
                limits_raw["max_runtime_symbols"],
                "limits.max_runtime_symbols",
                minimum=0,
                maximum=1024,
            ),
        }
        return Capability(
            capability_id,
            clock_hz,
            tuple(profiles),
            hbm,
            sram,
            dma,
            tensor,
            vector,
            limits,
            raw,
        )
    except CapabilityError:
        raise
    except ArtifactError as exc:
        raise CapabilityError(str(exc)) from exc


def load_capability(path: Path) -> Capability:
    try:
        return parse_capability(load_strict_json(path))
    except ArtifactError as exc:
        if isinstance(exc, CapabilityError):
            raise
        raise CapabilityError(str(exc)) from exc
