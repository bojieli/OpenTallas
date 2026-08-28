"""Strict development capability for the production tensor-accelerator ABI."""

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
from .production_command import (
    ABI_MAJOR,
    ABI_MINOR,
    LEGACY_ABI_MINOR,
    RMSNORM_ABI_MINOR,
    SUPPORTED_ABI_MINORS,
)


SCHEMA = "opentallas.tensor_accelerator.production_capability.v1"
UNCHARACTERIZED = "uncharacterized_development"
KNOWN_FORMATS = frozenset(
    {
        "bf16",
        "bool",
        "e8m0",
        "fp32",
        "fp4_e2m1",
        "fp8_e4m3fn",
        "i16",
        "i32",
        "i64",
        "i8",
        "mxfp4_e2m1",
        "u16",
        "u32",
        "u64",
        "u8",
    }
)
KNOWN_EXECUTION_MODES = frozenset(
    {
        "bf16_tensor",
        "fp8_tensor",
        "mxfp4_tensor",
        "routing_selection",
        "vector_fp32",
    }
)


class ProductionCapabilityError(ArtifactError):
    """Raised when a production capability is incomplete or overclaims evidence."""


@dataclass(frozen=True)
class ProductionHBM:
    address_bits: int
    base_address: int
    burst_bytes: int
    capacity_bytes: int
    external_at_130nm_boundary: bool


@dataclass(frozen=True)
class ProductionSRAM:
    banks: int
    bytes_per_bank: int
    bank_address_stride: int
    word_bytes: int
    read_ports_per_bank: int
    write_ports_per_bank: int

    @property
    def capacity_bytes(self) -> int:
        return self.banks * self.bytes_per_bank

    def bank_base(self, bank: int) -> int:
        return bank * self.bank_address_stride


@dataclass(frozen=True)
class ProductionTensorEngine:
    max_m: int
    max_n: int
    max_k: int


@dataclass(frozen=True)
class ProductionVectorEngine:
    max_rows: int
    max_width: int
    max_rope_positions: int | None
    max_query_heads: int | None
    max_key_value_heads: int | None
    rope_head_dim: int | None


@dataclass(frozen=True)
class ProductionCapability:
    capability_id: str
    architecture: str
    command_abi_major: int
    command_abi_minor: int
    declared_model_profiles: tuple[str, ...]
    formats: tuple[str, ...]
    declared_execution_modes: tuple[str, ...]
    qualified_execution_modes: tuple[str, ...]
    qualified_numeric_contracts: tuple[str, ...]
    hbm: ProductionHBM
    sram: ProductionSRAM
    tensor_engine: ProductionTensorEngine
    vector_engine: ProductionVectorEngine | None
    limits: Mapping[str, int]
    raw: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.raw)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProductionCapabilityError(f"{label} must be an object")
    return value


def _sorted_strings(
    value: Any,
    label: str,
    *,
    allowed: frozenset[str] | None = None,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
    ):
        raise ProductionCapabilityError(
            f"{label} must be a nonempty string array"
        )
    parsed = tuple(value)
    if parsed != tuple(sorted(set(parsed))):
        raise ProductionCapabilityError(
            f"{label} must be unique and lexicographically sorted"
        )
    if allowed is not None and not set(parsed) <= allowed:
        raise ProductionCapabilityError(f"{label} contains an unknown value")
    return parsed


def _parse_hbm(raw: Any) -> ProductionHBM:
    value = _object(raw, "hbm")
    exact_keys(
        value,
        {
            "address_bits",
            "base_address",
            "burst_bytes",
            "capacity_bytes",
            "external_at_130nm_boundary",
        },
        set(),
        "hbm",
    )
    address_bits = require_int(
        value["address_bits"], "hbm.address_bits", minimum=32, maximum=64
    )
    base = require_int(
        value["base_address"],
        "hbm.base_address",
        minimum=0,
        maximum=(1 << address_bits) - 1,
    )
    burst = require_power_of_two(
        value["burst_bytes"], "hbm.burst_bytes", minimum=16, maximum=4096
    )
    capacity = require_int(
        value["capacity_bytes"],
        "hbm.capacity_bytes",
        minimum=1 << 30,
        maximum=1 << 50,
    )
    external = value["external_at_130nm_boundary"]
    if external is not True:
        raise ProductionCapabilityError(
            "hbm.external_at_130nm_boundary must be true"
        )
    if base % burst or capacity % burst or base + capacity > 1 << address_bits:
        raise ProductionCapabilityError(
            "HBM address range must be burst-aligned and fit address_bits"
        )
    return ProductionHBM(address_bits, base, burst, capacity, external)


def _parse_sram(raw: Any) -> ProductionSRAM:
    value = _object(raw, "sram")
    exact_keys(
        value,
        {
            "bank_address_stride",
            "banks",
            "bytes_per_bank",
            "read_ports_per_bank",
            "word_bytes",
            "write_ports_per_bank",
        },
        set(),
        "sram",
    )
    banks = require_power_of_two(value["banks"], "sram.banks", minimum=4, maximum=1024)
    bytes_per_bank = require_power_of_two(
        value["bytes_per_bank"],
        "sram.bytes_per_bank",
        minimum=4096,
        maximum=1 << 30,
    )
    stride = require_power_of_two(
        value["bank_address_stride"],
        "sram.bank_address_stride",
        minimum=bytes_per_bank,
        maximum=1 << 40,
    )
    word = require_power_of_two(
        value["word_bytes"], "sram.word_bytes", minimum=1, maximum=256
    )
    if bytes_per_bank % word or stride < bytes_per_bank:
        raise ProductionCapabilityError(
            "SRAM bank bytes/stride must be legal multiples of word_bytes"
        )
    return ProductionSRAM(
        banks=banks,
        bytes_per_bank=bytes_per_bank,
        bank_address_stride=stride,
        word_bytes=word,
        read_ports_per_bank=require_int(
            value["read_ports_per_bank"],
            "sram.read_ports_per_bank",
            minimum=1,
            maximum=16,
        ),
        write_ports_per_bank=require_int(
            value["write_ports_per_bank"],
            "sram.write_ports_per_bank",
            minimum=1,
            maximum=16,
        ),
    )


def _parse_tensor_engine(raw: Any) -> ProductionTensorEngine:
    value = _object(raw, "tensor_engine")
    exact_keys(value, {"max_k", "max_m", "max_n"}, set(), "tensor_engine")
    return ProductionTensorEngine(
        max_m=require_int(value["max_m"], "tensor_engine.max_m", minimum=1),
        max_n=require_int(value["max_n"], "tensor_engine.max_n", minimum=1),
        max_k=require_int(value["max_k"], "tensor_engine.max_k", minimum=1),
    )


def _parse_vector_engine(raw: Any) -> ProductionVectorEngine:
    value = _object(raw, "vector_engine")
    rope_fields = {
        "max_key_value_heads",
        "max_query_heads",
        "max_rope_positions",
        "rope_head_dim",
    }
    exact_keys(value, {"max_rows", "max_width"}, rope_fields, "vector_engine")
    present = rope_fields & value.keys()
    if present and present != rope_fields:
        raise ProductionCapabilityError(
            "vector_engine RoPE bounds must be present as one complete group"
        )
    return ProductionVectorEngine(
        max_rows=require_int(value["max_rows"], "vector_engine.max_rows", minimum=1),
        max_width=require_int(
            value["max_width"], "vector_engine.max_width", minimum=1
        ),
        max_rope_positions=(
            require_int(
                value["max_rope_positions"],
                "vector_engine.max_rope_positions",
                minimum=1,
            )
            if present
            else None
        ),
        max_query_heads=(
            require_int(
                value["max_query_heads"],
                "vector_engine.max_query_heads",
                minimum=1,
            )
            if present
            else None
        ),
        max_key_value_heads=(
            require_int(
                value["max_key_value_heads"],
                "vector_engine.max_key_value_heads",
                minimum=1,
            )
            if present
            else None
        ),
        rope_head_dim=(
            require_int(
                value["rope_head_dim"],
                "vector_engine.rope_head_dim",
                minimum=2,
            )
            if present
            else None
        ),
    )


def parse_production_capability(raw: dict[str, Any]) -> ProductionCapability:
    """Parse a canonical development capability and reject performance claims."""

    try:
        exact_keys(
            raw,
            {
                "architecture",
                "capability_id",
                "command_abi",
                "declared_execution_modes",
                "declared_model_profiles",
                "evidence",
                "formats",
                "hbm",
                "limits",
                "qualified_execution_modes",
                "qualified_numeric_contracts",
                "schema",
                "sram",
                "tensor_engine",
            },
            {"vector_engine"},
            "production capability",
        )
        if raw["schema"] != SCHEMA:
            raise ProductionCapabilityError("unsupported production capability schema")
        capability_id = require_sha256(raw["capability_id"], "capability_id")
        body = {key: value for key, value in raw.items() if key != "capability_id"}
        expected_id = sha256_bytes(canonical_json_bytes(body))
        if capability_id != expected_id:
            raise ProductionCapabilityError(
                f"capability_id mismatch: expected {expected_id}, observed {capability_id}"
            )
        if raw["architecture"] != "opentallas-tensor-accelerator":
            raise ProductionCapabilityError("architecture identity differs")
        command_abi = _object(raw["command_abi"], "command_abi")
        exact_keys(command_abi, {"major", "minor"}, set(), "command_abi")
        command_major = command_abi["major"]
        command_minor = command_abi["minor"]
        if command_major != ABI_MAJOR or command_minor not in SUPPORTED_ABI_MINORS:
            raise ProductionCapabilityError("command ABI differs from the implementation")
        evidence = _object(raw["evidence"], "evidence")
        exact_keys(
            evidence,
            {
                "classification",
                "performance_claims_permitted",
                "physical_characterization_id",
                "process_node_nm",
            },
            set(),
            "evidence",
        )
        if evidence != {
            "classification": UNCHARACTERIZED,
            "performance_claims_permitted": False,
            "physical_characterization_id": None,
            "process_node_nm": None,
        }:
            raise ProductionCapabilityError(
                "development capability must remain explicitly uncharacterized"
            )
        models = _sorted_strings(
            raw["declared_model_profiles"], "declared_model_profiles"
        )
        if set(models) != {
            "deepseek-v4-flash-0731-ordinary-target",
            "qwen3-8b",
        }:
            raise ProductionCapabilityError(
                "development capability must declare both target model profiles"
            )
        formats = _sorted_strings(raw["formats"], "formats", allowed=KNOWN_FORMATS)
        if set(formats) != KNOWN_FORMATS:
            raise ProductionCapabilityError("format union is incomplete")
        declared_modes = _sorted_strings(
            raw["declared_execution_modes"],
            "declared_execution_modes",
            allowed=KNOWN_EXECUTION_MODES,
        )
        if set(declared_modes) != KNOWN_EXECUTION_MODES:
            raise ProductionCapabilityError("execution-mode union is incomplete")
        qualified_modes = _sorted_strings(
            raw["qualified_execution_modes"],
            "qualified_execution_modes",
            allowed=KNOWN_EXECUTION_MODES,
        )
        if not set(qualified_modes) <= set(declared_modes):
            raise ProductionCapabilityError(
                "qualified execution modes must be declared"
            )
        numeric_contracts = _sorted_strings(
            raw["qualified_numeric_contracts"], "qualified_numeric_contracts"
        )
        matrix_contract = "bf16_bf16_fp32_sequential_rne_v1"
        rmsnorm_contract = "qwen3_rmsnorm_fp32_bf16_v1"
        rope_contract = "qwen3_rope_fp32_bf16_v1"
        vector_raw = raw.get("vector_engine")
        if command_minor == LEGACY_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor",)
                or numeric_contracts != (matrix_contract,)
                or vector_raw is not None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.0 qualification must remain the BF16 projection profile"
                )
            vector = None
        elif command_minor == RMSNORM_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor", "vector_fp32")
                or numeric_contracts != (matrix_contract, rmsnorm_contract)
                or vector_raw is None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.1 qualification must include the bounded RMSNorm profile"
                )
            vector = _parse_vector_engine(vector_raw)
            if vector.max_width < 4096:
                raise ProductionCapabilityError(
                    "RMSNorm-qualified vector width must cover Qwen hidden width"
                )
            if vector.max_rope_positions is not None:
                raise ProductionCapabilityError(
                    "ABI 2.1 vector engine must not claim RoPE bounds"
                )
        else:
            if (
                command_minor != ABI_MINOR
                or qualified_modes != ("bf16_tensor", "vector_fp32")
                or numeric_contracts
                != (matrix_contract, rmsnorm_contract, rope_contract)
                or vector_raw is None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.2 qualification must include bounded Qwen RoPE"
                )
            vector = _parse_vector_engine(vector_raw)
            if (
                vector.max_width < 4096
                or vector.max_rows < 40
                or vector.max_rope_positions is None
                or vector.max_rope_positions < 8000
                or vector.max_query_heads is None
                or vector.max_query_heads < 32
                or vector.max_key_value_heads is None
                or vector.max_key_value_heads < 8
                or vector.rope_head_dim != 128
            ):
                raise ProductionCapabilityError(
                    "ABI 2.2 vector bounds do not cover the Qwen 8K Q/K path"
                )
        hbm = _parse_hbm(raw["hbm"])
        sram = _parse_sram(raw["sram"])
        tensor = _parse_tensor_engine(raw["tensor_engine"])
        limits_raw = _object(raw["limits"], "limits")
        exact_keys(
            limits_raw,
            {
                "max_commands",
                "max_context_tokens",
                "max_hbm_regions",
                "max_sram_regions",
            },
            set(),
            "limits",
        )
        limits = {
            "max_commands": require_int(
                limits_raw["max_commands"], "limits.max_commands", minimum=1
            ),
            "max_context_tokens": require_int(
                limits_raw["max_context_tokens"],
                "limits.max_context_tokens",
                minimum=8000,
            ),
            "max_hbm_regions": require_int(
                limits_raw["max_hbm_regions"],
                "limits.max_hbm_regions",
                minimum=1,
            ),
            "max_sram_regions": require_int(
                limits_raw["max_sram_regions"],
                "limits.max_sram_regions",
                minimum=4,
            ),
        }
        return ProductionCapability(
            capability_id=capability_id,
            architecture=raw["architecture"],
            command_abi_major=command_major,
            command_abi_minor=command_minor,
            declared_model_profiles=models,
            formats=formats,
            declared_execution_modes=declared_modes,
            qualified_execution_modes=qualified_modes,
            qualified_numeric_contracts=numeric_contracts,
            hbm=hbm,
            sram=sram,
            tensor_engine=tensor,
            vector_engine=vector,
            limits=limits,
            raw=raw,
        )
    except ProductionCapabilityError:
        raise
    except ArtifactError as exc:
        raise ProductionCapabilityError(str(exc)) from exc


def load_production_capability(path: Path) -> ProductionCapability:
    try:
        raw = Path(path).read_bytes()
        value = load_strict_json(Path(path))
    except (OSError, ArtifactError) as exc:
        raise ProductionCapabilityError(
            f"cannot load production capability: {exc}"
        ) from exc
    if raw != canonical_json_bytes(value):
        raise ProductionCapabilityError("production capability is not canonical JSON")
    return parse_production_capability(value)


__all__ = [
    "ProductionCapability",
    "ProductionCapabilityError",
    "ProductionHBM",
    "ProductionSRAM",
    "ProductionTensorEngine",
    "ProductionVectorEngine",
    "SCHEMA",
    "UNCHARACTERIZED",
    "load_production_capability",
    "parse_production_capability",
]
