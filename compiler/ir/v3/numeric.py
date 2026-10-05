"""Canonical numeric-contract identities and the capability union.

Two problems this module exists to solve, both found by running the two
exporters against one backend:

*The exporters had disagreed on naming.* Qwen emitted semantic identifiers such
as ``qwen3_rope_fp32_bf16_v1`` while DeepSeek emitted Python module paths such
as ``runtime.reference.rope.rope_apply_bf16#...``. A module path is an
implementation detail, and ADR-003 section 15 forbids the neutral IR from
carrying one: rename the module and every published graph silently changes
identity. Contract names are now canonicalised to opaque semantic identifiers,
and the mapping from a legacy name is explicit rather than incidental.

*The capability had no way to state what it implements.* ADR-003 section 14
forbids silent emulation, so a backend must refuse a contract the capability
does not declare — which it correctly did, and which is what surfaced the
naming problem. The shared HBM/SRAM chip serves both models, so its capability
must declare the *union* of both models' contracts. That union is derived here
from the published graphs rather than hand-maintained, because a hand-listed
union drifts the moment an exporter adds an operation.

Two contracts with different names are different operations. Qwen's RMSNorm
materialises the normalised value in BF16 before the gain multiply and
DeepSeek's stays in binary32; they disagree by one ulp on roughly 27 % of
elements. Collapsing them onto one name would corrupt whichever model did not
get its own.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO = Path(__file__).resolve().parents[3]

#: Contract identifiers must be lowercase, dot-free and version-suffixed.
CONTRACT_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*_v\d+$")

#: Prefixes that mark a name as an implementation path rather than a contract.
IMPLEMENTATION_PREFIXES = ("runtime.", "compiler.", "tests.", "tools.")


class NumericContractError(ValueError):
    """Raised when a contract identity is malformed or unmappable."""


def canonical_contract_id(name: str) -> str:
    """Return the canonical identifier for ``name``.

    Already-canonical names pass through unchanged. A ``runtime.reference.*``
    path is rewritten mechanically: the implementation prefix is dropped, the
    module qualifier and the ``#variant`` suffix become underscore-separated
    segments, and a ``_v1`` version suffix is appended. The rewrite is total and
    injective, so two different implementation paths never collide.
    """
    if not name:
        raise NumericContractError("numeric contract name is empty")
    if CONTRACT_PATTERN.match(name):
        return name
    stripped = name
    for prefix in IMPLEMENTATION_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break
    else:
        if "." not in stripped and "#" not in stripped:
            raise NumericContractError(
                f"contract {name!r} is neither canonical nor a recognised "
                "implementation path; canonical names are lowercase, "
                "underscore-separated and end in _v<major>"
            )
    if stripped.startswith("reference."):
        stripped = stripped[len("reference.") :]
    # Drop a redundant module qualifier: "rope.rope_apply_bf16" -> "rope_apply_bf16"
    head, _, tail = stripped.partition(".")
    if tail and (tail.startswith(head + "_") or head in tail):
        stripped = tail
    else:
        stripped = stripped.replace(".", "_")
    stripped = stripped.replace("#", "__").replace(".", "_")
    stripped = re.sub(r"[^a-z0-9_]", "_", stripped.lower())
    stripped = re.sub(r"_+", "_", stripped).strip("_")
    canonical = f"{stripped}_v1"
    if not CONTRACT_PATTERN.match(canonical):
        raise NumericContractError(
            f"contract {name!r} canonicalised to {canonical!r}, which is not a "
            "legal identifier"
        )
    return canonical


def is_implementation_path(name: str) -> bool:
    """True when ``name`` leaks an implementation location into the IR."""
    return name.startswith(IMPLEMENTATION_PREFIXES) or "#" in name or "." in name


def contracts_of(graph: Mapping[str, Any]) -> dict[str, int]:
    """Canonical contract identities used by a published graph, with counts."""
    counts: dict[str, int] = {}
    for kernel in graph.get("kernels", []):
        canonical = canonical_contract_id(kernel["numeric_contract"])
        counts[canonical] = counts.get(canonical, 0) + 1
    return dict(sorted(counts.items()))


def capability_union(graph_paths: Iterable[Path]) -> dict[str, Any]:
    """Derive the numeric-contract union the shared chip must implement.

    The union is derived from the published graphs rather than hand-listed,
    because a hand-listed union silently goes stale the moment an exporter adds
    an operation, and the failure mode is an admission error at the very end of
    a long build.
    """
    per_model: dict[str, dict[str, int]] = {}
    union: dict[str, list[str]] = {}
    for path in graph_paths:
        body = json.loads(Path(path).read_text())
        model = body["model_id"]
        counts = contracts_of(body)
        per_model[model] = counts
        for name in counts:
            union.setdefault(name, []).append(model)
    return {
        "schema": "opentallas.abi3.numeric_contract_union.v1",
        "contract_count": len(union),
        "contracts": {
            name: sorted(models) for name, models in sorted(union.items())
        },
        "per_model_counts": {m: c for m, c in sorted(per_model.items())},
        "shared_by_all": sorted(
            name for name, models in union.items() if len(models) == len(per_model)
        ),
    }


#: The neutral graphs whose union the *shipped* chip declares, named rather
#: than globbed.  A glob over ``build/ir-v3`` was the original form, and it made
#: the shipped capability a function of whatever happened to be on disk: a
#: speculative export placed beside the shipped ones silently widened the union,
#: moved both HBM capability digests and so invalidated the deployments already
#: admitted against them.  Naming the inputs makes an addition to the union a
#: deliberate edit to this list.
SHIPPED_GRAPH_STEMS: tuple[str, ...] = (
    "deepseek-v4-flash-0731",
    "qwen3-8b",
)

#: Graphs exported with the DSpark speculative decoder attached.  These are
#: research artifacts, not shipped products, and they are deliberately kept out
#: of the shipped union; see :func:`speculative_graph_paths`.
SPECULATIVE_GRAPH_STEMS: tuple[str, ...] = (
    "deepseek-v4-flash-0731-speculative",
    "deepseek-v4-pro-0813-speculative",
)


#: Graphs exported for a model that has no deployment in any store yet.  These
#: are held out of the shipped union for exactly the reason
#: :data:`SPECULATIVE_GRAPH_STEMS` is: adding a stem here would widen the shipped
#: HBM capability's contract tuple, move its digest, and invalidate every
#: deployment already admitted against it -- as a side effect of an export
#: appearing on disk.  A comparator deployment is built against a record that
#: names this union deliberately instead.
COMPARATOR_GRAPH_STEMS: tuple[str, ...] = ("deepseek-v4.1-flash",)


def _graph_paths(stems: Iterable[str]) -> list[Path]:
    root = REPO / "build" / "ir-v3"
    return [
        path
        for path in (root / stem / "kernel_ir.v3.json" for stem in stems)
        if path.exists()
    ]


def default_graph_paths() -> list[Path]:
    """The shipped graphs the shared-chip capability union is derived from."""
    return _graph_paths(SHIPPED_GRAPH_STEMS)


def speculative_graph_paths() -> list[Path]:
    """The speculative graphs, whose union is published separately."""
    return _graph_paths(SPECULATIVE_GRAPH_STEMS)


def load_union() -> dict[str, Any]:
    """Load the published union, or derive it if it has not been published."""
    published = REPO / "spec" / "abi3" / "numeric_contract_union.json"
    if published.exists():
        return json.loads(published.read_text())
    return capability_union(default_graph_paths())


def union_contract_ids() -> tuple[str, ...]:
    return tuple(load_union()["contracts"])


def speculative_union_path() -> Path:
    return REPO / "spec" / "abi3" / "numeric_contract_union_speculative.json"


def load_speculative_union() -> dict[str, Any]:
    """Load the published speculative union, or derive it if unpublished."""
    published = speculative_union_path()
    if published.exists():
        return json.loads(published.read_text())
    return capability_union(speculative_graph_paths())


def speculative_union_contract_ids() -> tuple[str, ...]:
    return tuple(load_speculative_union()["contracts"])


def comparator_graph_paths() -> list[Path]:
    """The graphs of models with no deployment in any store yet."""
    return _graph_paths(COMPARATOR_GRAPH_STEMS)


def comparator_union_path() -> Path:
    return REPO / "spec" / "abi3" / "numeric_contract_union_comparator.json"


def load_comparator_union() -> dict[str, Any]:
    """Load the published comparator union, or derive it if unpublished."""
    published = comparator_union_path()
    if published.exists():
        return json.loads(published.read_text())
    return capability_union(comparator_graph_paths())


def comparator_union_contract_ids() -> tuple[str, ...]:
    return tuple(load_comparator_union()["contracts"])


# -- implementation, as distinct from declaration ---------------------------
#
# ADR-003 section 14 forbids silent emulation, and a capability that merely
# *names* a contract emulates it silently in the only way that matters: the
# build admits, the program runs, and nothing ever executed the arithmetic the
# name promised.  Declaring is cheap -- it is one string in a tuple -- so the
# declaration has to be earned.  These helpers are what earns it: a contract may
# be declared only when something in the tree implements it.
#
# Most contract names are mechanically derived from the reference that owns the
# arithmetic (``runtime.reference.structural.dspark_noise_embed_bf16`` ->
# ``structural_dspark_noise_embed_bf16``, plus the kernel's sub-operation), so
# most of the resolution is the inverse of :func:`canonical_contract_id`.  The
# rest are names the ABI froze *before* any module layout existed, or froze
# deliberately against one -- amendment A8's two RMSNorms are the standing
# example -- and those cannot be recovered from a module path by construction.
# They are listed here, each against the implementation that actually executes
# it, because an explicit short list of exceptions is honest and a silently
# permissive resolver is not.

#: Contracts whose ABI-frozen name does not encode its implementation location,
#: mapped to the implementation that executes them.  Every entry was read out of
#: the named module, not inferred from the contract's spelling.
FROZEN_CONTRACT_IMPLEMENTATIONS: Mapping[str, str] = {
    "bf16_payload_lookup_v1": "runtime.reference.lookup.bf16_token_embedding",
    "exact_token_append_eos_v1": "runtime.sim.engines.selection.token_append",
    "greedy_lowest_token_id_argmax_v1": "runtime.sim.engines.selection.argmax",
    # -- DeepSeek-V4.1-Flash (AM-E10) -----------------------------------------
    #
    # The V4.1 exporter names a contract after the SOURCE OPERATION it came from
    # and appends the sub-operation, so most of its names cannot be recovered
    # from a module path: `candidate_mask_block_maximum_v1` is one step of
    # `CANDIDATE_BLOCK_SELECT`, and the reference that executes it is named after
    # the arithmetic (`block_max_rows`), not after the source operator.  Each
    # entry below was established by reading the kernel out of
    # `build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json` -- kind, iteration
    # domain, operands and every attribute -- and then reading the named
    # reference.  Where the evidence is an attribute-for-attribute identity with
    # a kernel whose contract already has a reference, that is said so, because
    # "same operation, different name" is the only honest ground for pointing two
    # contract names at one implementation.
    #
    # ENGRAM n-gram hash.  `runtime.reference.engram.ngram_row_ids` computes, per
    # position and per (order, head) column: the STICKY look-back window
    # (`tokens`/`blocked`, contract `..._lookback_ids_v1`, the GATHER kernel's
    # `lookback_bound: sequence_start_and_any_blocked_position`), the XOR fold of
    # `order` products and its modulus (`..._order2/3/4_v1`, one contract per
    # `order` attribute), and the column's position in the flattened
    # ngram-major/head-minor layout plus that column's prefix-sum `offset`
    # (`..._column_join_v1`, the CONCAT kernel's
    # `segment_order: ascending_ngram_order_then_hash_head`).  One reference, five
    # named steps of it.
    "ngram_hash_u32_lookback_ids_v1": "runtime.reference.engram.ngram_row_ids",
    "ngram_hash_u32_order2_v1": "runtime.reference.engram.ngram_row_ids",
    "ngram_hash_u32_order3_v1": "runtime.reference.engram.ngram_row_ids",
    "ngram_hash_u32_order4_v1": "runtime.reference.engram.ngram_row_ids",
    "ngram_hash_u32_column_join_v1": "runtime.reference.engram.ngram_row_ids",
    #
    # FP4 main-latent quantize/dequantize.  `runtime.reference.fp4_kv` is the
    # reference for E2M1 elements with one E4M3 scale per 16 -- its own
    # `DEFAULT_SCALE_GROUP` is 16 and its `CONTRACT` constant is
    # `fp4_e2m1_s16_e4m3_to_fp8_v1`, the base both kernels' contracts extend.
    # The QUANTIZE kernel declares `block_size: 16`, `output_dtype:
    # fp4_e2m1_s16_e4m3`, `scale_format: e4m3`; the DEQUANTIZE kernel declares
    # the same block and scale format.
    #
    # THE TWO DIRECTIONS ARE NOT EQUALLY ESTABLISHED, and the difference is
    # recorded here rather than left to be discovered.  `dequantize_to_fp8` is
    # exact and vendor-independent -- it decodes two released storage formats and
    # multiplies, and `results/rtl/a3_v41_fp4kv_dequant_campaign.json` qualified
    # it against RTL.  `quantize_to_fp4` implements the rule
    # `docs/SOURCES.md` records for the V4.1 compressor (SRC-DSV41-FLASH-MODEL:
    # "the main latent is quantized after RoPE in groups of 16 with E4M3
    # scales") -- scale = RNE_E4M3(amax / 6), clamp to +-6, round E2M1 -- but its
    # own docstring says the pinned `model.py` is absent from this checkout, so
    # any floor constant and whether the vendor multiplies by a rounded
    # reciprocal of six rather than dividing are NOT confirmed.  Declaring the
    # contract therefore says "this chip implements the documented forward rule",
    # and does NOT yet say "bit-identical to DeepSeek's".  A capability consumer
    # that needs the stronger claim must wait on that qualification.
    "fp4_e2m1_s16_e4m3_to_fp8_quantize_v1": "runtime.reference.fp4_kv.quantize_to_fp4",
    "fp4_e2m1_s16_e4m3_to_fp8_reconstruct_v1": (
        "runtime.reference.fp4_kv.dequantize_to_fp8"
    ),
    #
    # CANDIDATE_BLOCK_SELECT, three kernels of one source operator.
    # `block_max_rows` is the blockwise maximum under the ordered-IEEE contract
    # with -inf padding (BLOCK_MAX, `block: 8`, `padding_value:
    # negative_infinity`); `select_candidate_blocks` is the block top-k under
    # `score_descending_then_index_ascending` with the newest block pinned
    # (INDEX_TOPK, `k: 2048`, `pinned_block:
    # the_block_holding_the_newest_position`); `select_candidate_mask` expands the
    # chosen ids into the admission plane (CANDIDATE_MASK, `polarity:
    # one_admits_the_position`, `population_bound: 16384`).
    "candidate_mask_block_maximum_v1": (
        "runtime.reference.candidate_pool.block_max_rows"
    ),
    "candidate_mask_block_top_k_v1": (
        "runtime.reference.candidate_pool.select_candidate_blocks"
    ),
    "candidate_mask_admission_plane_v1": (
        "runtime.reference.candidate_pool.select_candidate_mask"
    ),
    "candidate_mask_view_v1": (
        "runtime.reference.candidate_pool.candidate_mask_view"
    ),
    #
    # SAMPLE.  The V4.1 front end's own comment says "IR3-GAP-1 unchanged from
    # V4", and the three emitted kernels bear it out: V4.1's SCALE/ARGMAX/
    # TOKEN_APPEND carry a strict SUBSET of V4's attributes -- identical `kind`,
    # identical iteration domain (`rows: 1, width: 129280`; `rows: 1`), identical
    # `operation: reciprocal_temperature_product`, identical `scale_bits`
    # 1065353216 (0x3F800000), identical `tie_rule: lowest_token_id`, identical
    # `eos_token_id: 1`, with V4 additionally carrying provenance attributes that
    # name no arithmetic.  Same three operations, renamed by the per-model
    # contract prefix, so the V4 reference is the implementation.
    "sampling_deepseek_v41_sample_binary32_temperature_v1": (
        "runtime.reference.sampling.deepseek_v4_sample_binary32"
    ),
    "sampling_deepseek_v41_sample_binary32_greedy_argmax_v1": (
        "runtime.reference.sampling.deepseek_v4_sample_binary32"
    ),
    "sampling_deepseek_v41_sample_binary32_token_append_v1": (
        "runtime.reference.sampling.deepseek_v4_sample_binary32"
    ),
    #
    # HC_FINAL_COLLAPSE.  `main.hyper_connection_collapse` is
    # attribute-for-attribute the same EXPERT_REDUCE as every layer's
    # `hyper_connection.<sublayer>.collapse`, whose contract
    # `hyper_connection_hc_pre_bf16_branch_collapse_v1` already resolves to
    # `hc_pre_bf16`: same kind, same iteration domain (4 hyper streams, width
    # 5120), same `reduction_axis: 1`, `reduction_order: pairwise_tree`,
    # `routing_weight_application: applied_at_the_reduction`,
    # `contribution_row_order: ascending_hyper_stream`, `stream_count: 4`.  The
    # two differ only in `weight_source`, which names WHICH tensor supplies the
    # branch weights, not what is computed with them -- the pinned
    # `Transformer.forward` ends `h = layer.hc_pre(h, pre_mix)`, i.e. the epilogue
    # IS one more hc_pre collapse.
    "hyper_connection_hc_collapse_bf16_v1": (
        "runtime.reference.hyper_connection.hc_pre_bf16"
    ),
    #
    # INDEX_KEY_WRITE.  The indexer key append is attribute-for-attribute the
    # compressed-KV append beside it -- both KV_APPEND, both `cache_row:
    # compressed_group_index`, both `ratio: 2`, both predicated on
    # `span_groups_ratio2 > 0`, same `capacity` 131072 -- differing only in the
    # row width, 128 against 512.  The compressed-KV append's contract
    # `compressed_kv_write_bf16_v1` already resolves to
    # `compressed_kv.compressed_kv_write_bf16`, whose `value_width` is a state
    # parameter and whose own `PINNED_INDEX_HEAD_DIM` is 128: the same
    # transaction, at the index row width.
    "index_key_write_bf16_v1": (
        "runtime.reference.compressed_kv.compressed_kv_write_bf16"
    ),
    #
    # SHARED_INDEX_REUSE's join.  `main.layerNN.attention.indexer.reuse.index_join`
    # is attribute-for-attribute `main.layerNN.attention.indexer.select.index_join`
    # -- both CONCAT, `axis: 1`, `padding_index: -1`, `segment_order:
    # window_then_rebased_compressed`, `segment_widths: [128, 512]` -- and the
    # latter's contract already resolves to `selection.index_topk_indices`.  One
    # join, reached from two producers.  (The STATE_READ that feeds it is a
    # different question and has its own reference,
    # `selection.shared_index_view`, which this table does not need because its
    # name derives from that module path.)
    "selection_shared_index_view_window_then_compressed_v1": (
        "runtime.reference.selection.index_topk_indices"
    ),
}

#: Modules scanned for contract names declared as module constants.  These carry
#: the frozen identities the engines dispatch on.
_DECLARING_MODULES: tuple[str, ...] = ("runtime.sim.backend",)

_IMPLEMENTATION_INDEX: dict[str, dict[str, str]] | None = None


def _index_implementations() -> dict[str, dict[str, str]]:
    """Scan the tree once for contract implementations.

    Returns two indices: ``exact`` maps a canonical contract id to the
    implementation that declares it by name, and ``bases`` maps a derived
    contract *base* to the reference callable it was derived from.  A kernel
    that implements one step of a reference appends its sub-operation to the
    base, so a base match is a prefix match.
    """
    global _IMPLEMENTATION_INDEX
    if _IMPLEMENTATION_INDEX is not None:
        return _IMPLEMENTATION_INDEX

    import importlib
    import pkgutil

    exact: dict[str, str] = dict(FROZEN_CONTRACT_IMPLEMENTATIONS)
    bases: dict[str, str] = {}

    # A frozen entry is a *claim* that a named module attribute executes the
    # contract, and a claim about a name is cheap: a typo, or a reference that
    # was renamed or deleted, would leave the contract resolving to a site that
    # does not exist -- and `require_implemented` would then admit a declaration
    # backed by nothing, which is precisely the failure this module exists to
    # prevent.  So every entry is resolved here, and an entry that does not
    # resolve is an error in this table rather than a silently permissive one.
    for contract, site in FROZEN_CONTRACT_IMPLEMENTATIONS.items():
        module_name, _, attribute = site.rpartition(".")
        try:
            module = importlib.import_module(module_name)
        except Exception as error:  # pragma: no cover - a broken table
            raise NumericContractError(
                f"contract {contract!r} names implementation {site!r}, whose "
                f"module could not be imported: {error}"
            ) from error
        if not hasattr(module, attribute):
            raise NumericContractError(
                f"contract {contract!r} names implementation {site!r}, which "
                f"{module_name} does not define"
            )

    def _record_strings(value: Any, site: str) -> None:
        items = (
            [value]
            if isinstance(value, str)
            else list(value)
            if isinstance(value, (tuple, list, set, frozenset))
            else []
        )
        for item in items:
            if isinstance(item, str) and CONTRACT_PATTERN.match(item):
                exact.setdefault(item, site)

    reference = importlib.import_module("runtime.reference")
    for info in pkgutil.iter_modules(reference.__path__):
        module_name = f"runtime.reference.{info.name}"
        try:
            module = importlib.import_module(module_name)
        except Exception:  # pragma: no cover - a broken module is not a contract
            continue
        for attr in dir(module):
            if attr.startswith("_"):
                continue
            value = getattr(module, attr)
            site = f"{module_name}.{attr}"
            _record_strings(value, site)
            if callable(value) and getattr(value, "__module__", None) == module_name:
                try:
                    derived = canonical_contract_id(site)
                except NumericContractError:
                    continue
                bases.setdefault(derived[: -len("_v1")], site)

    for module_name in _DECLARING_MODULES:
        try:
            module = importlib.import_module(module_name)
        except Exception:  # pragma: no cover
            continue
        for attr in dir(module):
            if not attr.startswith("CONTRACT"):
                continue
            _record_strings(getattr(module, attr), f"{module_name}.{attr}")

    _IMPLEMENTATION_INDEX = {"exact": exact, "bases": bases}
    return _IMPLEMENTATION_INDEX


def implementation_of(contract: str) -> str | None:
    """Return where ``contract`` is implemented, or ``None`` if nowhere.

    The longest matching base wins, so a contract that is both a reference in
    its own right and a step of a longer one resolves to the longer.
    """
    canonical = canonical_contract_id(contract)
    index = _index_implementations()
    exact = index["exact"].get(canonical)
    if exact is not None:
        return exact
    stem = canonical[: -len("_v1")]
    best: tuple[int, str] | None = None
    for base, site in index["bases"].items():
        if stem == base or stem.startswith(base + "_"):
            if best is None or len(base) > best[0]:
                best = (len(base), site)
    return None if best is None else best[1]


def unimplemented_contracts(contracts: Iterable[str]) -> tuple[str, ...]:
    """The subset of ``contracts`` nothing in the tree implements, sorted."""
    return tuple(
        sorted(
            {
                canonical_contract_id(name)
                for name in contracts
                if implementation_of(name) is None
            }
        )
    )


def require_implemented(contracts: Iterable[str], *, what: str) -> tuple[str, ...]:
    """Return ``contracts`` canonicalised, refusing any that is not implemented.

    A capability declares what the chip *implements*.  Widening a declaration to
    make a build admit, without the arithmetic behind it, converts an honest
    refusal into a wrong answer that no later check can catch.
    """
    canonical = tuple(sorted({canonical_contract_id(n) for n in contracts}))
    missing = unimplemented_contracts(canonical)
    if missing:
        raise NumericContractError(
            f"{what} declares numeric contracts nothing in this tree "
            f"implements: {list(missing)}. ADR-003 section 14 forbids silent "
            "emulation, so a contract must be implemented before it is "
            "declared; add the reference, do not widen the declaration"
        )
    return canonical
