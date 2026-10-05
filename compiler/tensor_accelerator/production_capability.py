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
    ATTENTION_ABI_MINOR,
    ELEMENTWISE_ABI_MINOR,
    LEGACY_ABI_MINOR,
    RMSNORM_ABI_MINOR,
    ROPE_ABI_MINOR,
    SELECTION_ABI_MINOR,
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
        "transactional_state",
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
    max_attention_context_tokens: int | None
    attention_head_dim: int | None
    softmax_reduction_lanes: int | None


@dataclass(frozen=True)
class ProductionStateEngine:
    generation_bits: int
    length_bits: int
    max_inflight_transactions: int
    max_resources_per_transaction: int
    position_bits: int
    transaction_id_bits: int


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
    state_engine: ProductionStateEngine | None
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
        raise ProductionCapabilityError(f"{label} must be a nonempty string array")
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
        raise ProductionCapabilityError("hbm.external_at_130nm_boundary must be true")
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
    attention_fields = {
        "attention_head_dim",
        "max_attention_context_tokens",
        "softmax_reduction_lanes",
    }
    exact_keys(
        value,
        {"max_rows", "max_width"},
        rope_fields | attention_fields,
        "vector_engine",
    )
    present = rope_fields & value.keys()
    if present and present != rope_fields:
        raise ProductionCapabilityError(
            "vector_engine RoPE bounds must be present as one complete group"
        )
    attention_present = attention_fields & value.keys()
    if attention_present and attention_present != attention_fields:
        raise ProductionCapabilityError(
            "vector_engine attention bounds must be present as one complete group"
        )
    return ProductionVectorEngine(
        max_rows=require_int(value["max_rows"], "vector_engine.max_rows", minimum=1),
        max_width=require_int(value["max_width"], "vector_engine.max_width", minimum=1),
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
        max_attention_context_tokens=(
            require_int(
                value["max_attention_context_tokens"],
                "vector_engine.max_attention_context_tokens",
                minimum=1,
            )
            if attention_present
            else None
        ),
        attention_head_dim=(
            require_int(
                value["attention_head_dim"],
                "vector_engine.attention_head_dim",
                minimum=1,
            )
            if attention_present
            else None
        ),
        softmax_reduction_lanes=(
            require_power_of_two(
                value["softmax_reduction_lanes"],
                "vector_engine.softmax_reduction_lanes",
                minimum=1,
                maximum=1024,
            )
            if attention_present
            else None
        ),
    )


def _parse_state_engine(raw: Any) -> ProductionStateEngine:
    value = _object(raw, "state_engine")
    exact_keys(
        value,
        {
            "generation_bits",
            "length_bits",
            "max_inflight_transactions",
            "max_resources_per_transaction",
            "position_bits",
            "transaction_id_bits",
        },
        set(),
        "state_engine",
    )
    return ProductionStateEngine(
        generation_bits=require_int(
            value["generation_bits"], "state_engine.generation_bits", minimum=1
        ),
        length_bits=require_int(
            value["length_bits"], "state_engine.length_bits", minimum=1
        ),
        max_inflight_transactions=require_int(
            value["max_inflight_transactions"],
            "state_engine.max_inflight_transactions",
            minimum=1,
        ),
        max_resources_per_transaction=require_int(
            value["max_resources_per_transaction"],
            "state_engine.max_resources_per_transaction",
            minimum=1,
        ),
        position_bits=require_int(
            value["position_bits"], "state_engine.position_bits", minimum=1
        ),
        transaction_id_bits=require_int(
            value["transaction_id_bits"],
            "state_engine.transaction_id_bits",
            minimum=1,
        ),
    )


def _require_attention_state_bounds(
    vector: ProductionVectorEngine,
    state: ProductionStateEngine,
    *,
    profile: str,
) -> None:
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
        or vector.max_attention_context_tokens is None
        or vector.max_attention_context_tokens < 8000
        or vector.attention_head_dim != 128
        or vector.softmax_reduction_lanes != 8
    ):
        raise ProductionCapabilityError(
            f"{profile} vector bounds do not cover Qwen 8K causal GQA"
        )
    if (
        state.generation_bits != 64
        or state.transaction_id_bits != 64
        or state.position_bits < 20
        or state.length_bits < 21
        or state.max_inflight_transactions < 8
        or state.max_resources_per_transaction < 64
    ):
        raise ProductionCapabilityError(
            f"{profile} state bounds do not cover the cross-model union"
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
            {"state_engine", "vector_engine"},
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
            raise ProductionCapabilityError(
                "command ABI differs from the implementation"
            )
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
        expected_declared_modes = (
            KNOWN_EXECUTION_MODES
            if command_minor >= ATTENTION_ABI_MINOR
            else KNOWN_EXECUTION_MODES - {"transactional_state"}
        )
        if set(declared_modes) != expected_declared_modes:
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
        state_contract = "bf16_byte_preserving_state_v1"
        attention_contract = "qwen3_gqa_fp32_softmax_bf16_v1"
        rmsnorm_contract = "qwen3_rmsnorm_fp32_bf16_v1"
        rope_contract = "qwen3_rope_fp32_bf16_v1"
        vector_raw = raw.get("vector_engine")
        state_raw = raw.get("state_engine")
        if command_minor == LEGACY_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor",)
                or numeric_contracts != (matrix_contract,)
                or vector_raw is not None
                or state_raw is not None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.0 qualification must remain the BF16 projection profile"
                )
            vector = None
            state = None
        elif command_minor == RMSNORM_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor", "vector_fp32")
                or numeric_contracts != (matrix_contract, rmsnorm_contract)
                or vector_raw is None
                or state_raw is not None
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
            state = None
        elif command_minor == ROPE_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor", "vector_fp32")
                or numeric_contracts
                != (matrix_contract, rmsnorm_contract, rope_contract)
                or vector_raw is None
                or state_raw is not None
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
            if vector.max_attention_context_tokens is not None:
                raise ProductionCapabilityError(
                    "ABI 2.2 vector engine must not claim attention bounds"
                )
            state = None
        elif command_minor == ATTENTION_ABI_MINOR:
            if (
                qualified_modes != ("bf16_tensor", "transactional_state", "vector_fp32")
                or numeric_contracts
                != (
                    matrix_contract,
                    state_contract,
                    attention_contract,
                    rmsnorm_contract,
                    rope_contract,
                )
                or vector_raw is None
                or state_raw is None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.3 qualification must include bounded attention and state"
                )
            vector = _parse_vector_engine(vector_raw)
            state = _parse_state_engine(state_raw)
            _require_attention_state_bounds(vector, state, profile="ABI 2.3")
        elif command_minor == ELEMENTWISE_ABI_MINOR:
            add_contract = "bf16_add_rne_v1"
            silu_contract = "qwen3_silu_mul_bf16_v1"
            if (
                qualified_modes != ("bf16_tensor", "transactional_state", "vector_fp32")
                or numeric_contracts
                != (
                    add_contract,
                    matrix_contract,
                    state_contract,
                    attention_contract,
                    rmsnorm_contract,
                    rope_contract,
                    silu_contract,
                )
                or vector_raw is None
                or state_raw is None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.4 qualification must include bounded residual and SiLU"
                )
            vector = _parse_vector_engine(vector_raw)
            state = _parse_state_engine(state_raw)
            _require_attention_state_bounds(vector, state, profile="ABI 2.4")
            if vector.max_width < 12288:
                raise ProductionCapabilityError(
                    "ABI 2.4 vector width does not cover the Qwen MLP"
                )
        else:
            add_contract = "bf16_add_rne_v1"
            select_contract = "exact_index_select_v1"
            silu_contract = "qwen3_silu_mul_bf16_v1"
            if (
                command_minor != SELECTION_ABI_MINOR
                or qualified_modes
                != ("bf16_tensor", "transactional_state", "vector_fp32")
                or numeric_contracts
                != (
                    add_contract,
                    matrix_contract,
                    state_contract,
                    select_contract,
                    attention_contract,
                    rmsnorm_contract,
                    rope_contract,
                    silu_contract,
                )
                or vector_raw is None
                or state_raw is None
            ):
                raise ProductionCapabilityError(
                    "ABI 2.5 qualification must include bounded index selection"
                )
            vector = _parse_vector_engine(vector_raw)
            state = _parse_state_engine(state_raw)
            _require_attention_state_bounds(vector, state, profile="ABI 2.5")
            if vector.max_width < 12288:
                raise ProductionCapabilityError(
                    "ABI 2.5 vector width does not cover Qwen MLP and selection"
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
            state_engine=state,
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
    "ProductionStateEngine",
    "ProductionTensorEngine",
    "ProductionVectorEngine",
    "SCHEMA",
    "UNCHARACTERIZED",
    "load_production_capability",
    "parse_production_capability",
]
