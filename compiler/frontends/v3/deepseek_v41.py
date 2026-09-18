"""Export the pinned DeepSeek-V4.1-Flash checkpoint into Tensor Kernel IR v3.

This is the V4.1 sibling of :mod:`compiler.frontends.v3.deepseek_v4`, and it is
deliberately a re-parameterisation of that front end rather than a second
derivation of DeepSeek semantics.  What the two releases share -- hyper
connections, the grouped output projection, the sqrt-softplus router, the MXFP4
expert SwiGLU, the compressor, the indexer, the DSpark draft stack -- keeps the
V4 source-operator names and the V4 lowering, so a reader who knows one knows
the other and the ROM/HBM backends see one shape.  What V4.1 adds is stated
once, here:

CSA2 with three modes
---------------------
DeepSeek-V4.1-Flash does not give every attention layer its own compressed
cache.  Four layers own one (``kv_source_layer_ids``), eight compute an index
selection (``index_source_layer_ids``), one publishes a candidate pool
(``candidate_source_layer_id``), and every other CSA2 layer reads what a
predecessor published.  That is three distinct per-layer shapes, and this
module names them ``attention_full``, ``attention_reindex`` and
``attention_reuse`` -- plus ``attention_window_only`` for the two leading
sliding-window layers, whose compression ratio is zero.

The mode of a layer is **derived** from the three released id lists and the
released ``compress_ratios``, never tabulated:

* ratio 0                                   -> ``attention_window_only``
* not an index source                       -> ``attention_reuse``
* an index source after the candidate source -> ``attention_reindex``
* an index source otherwise                  -> ``attention_full``

:meth:`DeepSeekV41Profile.layer_modes` computes that, and
:func:`confront_layer_modes` confronts the result with the mode sequence
committed in ``configs/models/candidates/deepseek-v4.1-flash.json``, which the
analytical layer derived independently.  Two derivations of the same sequence
from the same released fields is the whole point: the group structure the
technical report describes -- 18 CSA2 encoder layers as three groups of six,
one Full and five Reuse, at ratio 2; 20 decoder layers as five groups of four
at ratio 1, Full then Reuse in the first group and Reindex then Reuse in the
rest -- is an *observation about* the released id lists, and nothing in this
module is allowed to assume it.

Engram
------
Two Engram modules, at the layers ``engram_layer_ids`` names, read
``(engram_max_ngram_size - 1) * engram_n_heads`` FP8 rows per token from a
table whose rows are addressed by an integer n-gram hash of compressed token
ids.  AM-E10 gave the IR the three kinds that needs -- ``NGRAM_HASH``,
``EMBEDDING_LOOKUP`` as it already stood, and the fused ``ENGRAM_GATE`` -- and
this module's lowering names them.  The hash columns, the row width and the
layer ids are all read from the released configuration.

The plan, and the document that realises it
------------------------------------------
Everything above the bindings is derivable without a single payload byte, and it
is all here and tested: the profile and its
:attr:`DeepSeekV41Profile.architecture_pins`, confronted against the released
``config.json``; the mode sequence; the lowering plan; the per-layer source
plan; and :func:`planned_census`, whose per-layer content
``tests/compiler/test_deepseek_v41_kernel_ir.py`` confronts with the analytical
operator inventory in ``src/opentallas/operations.py``.  That cross-check
between the analytical and the executable layer is the thing V4 never had, and
it holds before the checkpoint finishes arriving.

:func:`export_deepseek_v41_kernel_graph` emits the document itself, and it walks
that plan to do it: one handler per source operator kind, in the order
:func:`layer_source_plan` and :func:`unlayered_source_plan` give, and a refusal
at the end unless the source kinds it emitted -- and the neutral kinds they
lowered to -- are the ones the plan named, layer by layer.  So the plan and the
document are one description of one model rather than two descriptions that
agree today.  Where the checkpoint artifacts a byte-pinned graph needs are
absent the build stops naming each one and the tool that produces it, exactly as
the V4 front end does for the Pro release, rather than emitting a graph whose
weights point nowhere.

Two things are still planned rather than emitted, and each says so where a
caller meets it.  ``include_speculative`` refuses, naming the seven DSpark
source kinds it would need (their verification and acceptance contract is open,
DSV4-SEM-001).  And the emitted ``ENGRAM_GATE`` states a key/value plane layout
the AM-E10 engine does not read yet: the released projection publishes
``hc_mult + 1`` planes, one key per hyper-connection copy and one shared value,
where ``VECTOR.ENGRAM_GATE``'s ``in1`` is documented as a two-plane view.  No
strided view of that one buffer presents the pair the engine wants, so the
layout is declared on the kernel rather than materialised by duplicating the
value plane; closing it is a WP-C amendment, not an exporter's licence to invent
a weight the checkpoint does not have.

What it reuses rather than restates
----------------------------------
* ``compiler.frontend.deepseek_v4_releases.V41_FLASH`` supplies every released
  fact: the widths, the four layer-mode id lists, the compression sequence, the
  quantization and rope objects, the digests and the artifact paths.  This
  module holds no constant beside a config value it is supposed to equal.
* ``compiler.frontend.deepseek_v41.load_official_config`` supplies the
  configuration gate -- digest, byte length, checkpoint-source witness and every
  pinned key -- and ``build_official_tensor_specs`` the 96,085 per-tensor
  records a binding would be written against.
* ``compiler.frontends.v3.deepseek_v4`` supplies the census reader, the graph
  accumulator with its arity and join gates, the checkpoint-binding reader and
  the leading-axis split that authenticates one group of a stacked weight.  One
  implementation, two models: a V4.1 copy of any of them would be a second shape
  for the same thing.

Sources
-------
``SRC-DSV41-FLASH-CONFIG`` (the released ``config.json``),
``SRC-DSV41-FLASH-MODEL`` (``inference/model.py`` and ``inference/engram.py``)
and ``SRC-DSV41-FLASH-REPORT``, all at revision
``dba1be0a40aa45a94ad051997016db3960a90277``.  See ``docs/SOURCES.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from compiler.frontend.checkpoint import CheckpointError, load_checkpoint_lock
from compiler.frontend.deepseek_v4 import TensorSpec
from compiler.frontend.deepseek_v4_releases import V41_FLASH, DeepSeekV4Release, V41_FLASH_REDUCED
from compiler.frontend.deepseek_v41 import (
    DeepSeekV41AdapterError,
    build_official_tensor_specs,
    load_official_config,
)
from compiler.ir.v3.kernel_ir import (
    DTYPES,
    FORBIDDEN_TERMS,
    OPERATION_KINDS,
    TOKEN_DTYPE,
    BindingSegment,
    CheckpointBinding,
    Entrypoint,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    check_neutral,
)
from compiler.ir.v3.lowering import ABSENT_OPERANDS, KERNEL_TO_ENGINE
from compiler.ir.v3.numeric import CONTRACT_PATTERN

#: The V4 front end owns the census reader, the graph accumulator, the checkpoint
#: binding reader and the leading-axis split: one implementation, two models.  A
#: V4.1 module that restated any of them would be a second shape for the same
#: thing, which is the defect this front end's docstring opens by refusing.
from compiler.frontends.v3.deepseek_v4 import (  # noqa: F401
    DeepSeekV4KernelIRError,  # re-raised as this module's error at the emit site
    _STORAGE_DTYPE,
    _Builder,
    binary32_bits,
    graph_census,
    read_checkpoint_bindings,
    split_binding_by_leading_groups,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The committed candidate profile the analytical layer reads.  This front end
#: reads exactly one thing from it -- ``metadata.csa2_layer_modes``, the mode
#: sequence the analytical layer derived -- so that
#: :func:`confront_layer_modes` can confront two independent derivations of it.
#: Every width comes from the release record instead.
CANDIDATE_PROFILE_PATH = (
    REPOSITORY_ROOT / "configs" / "models" / "candidates" / "deepseek-v4.1-flash.json"
)

#: Published digests of the two released documents this front end's *semantics*
#: are read off, from ``docs/SOURCES.md`` ``SRC-DSV41-FLASH-MODEL``.  The
#: release record pins the released configuration and the tensor structure; it
#: does not pin the inference source, and the lowering plan below is a claim
#: about that source, so it is pinned here and confronted by
#: :func:`confront_source_digests`.
MODEL_SOURCE_SHA256 = (
    "4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65"
)
ENGRAM_SOURCE_SHA256 = (
    "11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884f94d476d3897"
)

#: Architectural capacity published for this model, read from the release
#: record's ``max_position_embeddings`` rather than written down beside it.  The
#: V4 front end spells this constant the same way; unlike V4's, this one is not
#: a literal, because a capacity written twice is a capacity that can drift.
ARCHITECTURAL_MAX_CONTEXT = int(V41_FLASH.scalar("max_position_embeddings"))


def architectural_max_context(profile: "DeepSeekV41Profile") -> int:
    """One profile's published capacity, read from ITS OWN release record.

    ``ARCHITECTURAL_MAX_CONTEXT`` above reads the released record, and its own
    comment gives the reason a capacity should not be written twice: it can
    drift. The same argument says a SECOND model must not inherit the first's
    capacity, which is what a module constant does -- the reduced fixture
    publishes 24 and was refused against the release's 1,048,576.
    """

    return int(profile.release.scalar("max_position_embeddings"))

#: Deployment maximum this export targets, as for V4: the next power of two
#: above the 200,000-token DeepSeek acceptance run of ADR-003 section 18.  It is
#: a program decision, not a released fact, so it is stated here -- and it is a
#: whole number of sliding windows, which the export checks.
DEFAULT_CONTEXT_TOKENS = 262_144

#: Block sizes the released kernels quantize in.  Each is named so the lowering
#: can be read; the profile re-reads the released values it is sized by.
#:
#: ``inference/model.py`` sets ``fp8_block_size = 32`` and spends it on both
#: sides -- "one fp8 scale per 32x32 weight block / 32 activations" -- so the
#: activation block is the released weight block and is read from the released
#: ``quantization_config`` rather than written down.  V4 quantizes activations
#: in 128s; a V4.1 export that inherited that number would hand the engine one
#: scale per 128 elements where the released kernel writes four.
ACTIVATION_BLOCK = int(V41_FLASH.quantization_config["weight_block_size"][0])
#: FP4 index query/key: one E8M0 scale per 32 elements (``Indexer.forward``).
FP4_INDEX_BLOCK = 32
#: FP4 main latent: one E4M3 scale per 16 elements
#: (``Attention._compress_kv``), which is what makes it a new dtype and not
#: MXFP4 with a parameter.
FP4_MAIN_BLOCK = 16


class DeepSeekV41KernelIRError(RuntimeError):
    """Raised when the pinned DeepSeek-V4.1 source cannot produce a graph."""


# ---------------------------------------------------------------------------
# Released facts
# ---------------------------------------------------------------------------
def _candidate_layer_modes(
    path: Path = CANDIDATE_PROFILE_PATH,
) -> tuple[Mapping[str, Any], ...]:
    """The mode sequence the analytical layer committed, for confrontation."""

    try:
        document = json.loads(path.read_text())
    except OSError as exc:
        raise DeepSeekV41KernelIRError(
            f"cannot read the committed candidate profile {path}: {exc}"
        ) from exc
    modes = document.get("metadata", {}).get("csa2_layer_modes")
    if not isinstance(modes, list):
        raise DeepSeekV41KernelIRError(
            f"{path} carries no metadata.csa2_layer_modes"
        )
    return tuple(modes)


def confront_source_digests(
    profile: "DeepSeekV41Profile",
    snapshot: Path | None = None,
) -> dict[str, str]:
    """Confront the pinned inference-source digests with the snapshot's copies.

    The lowering plan is a claim about ``inference/model.py`` and
    ``inference/engram.py`` at one revision.  A re-upload that changed either
    would leave every kind name in this module unchanged and every lowering
    wrong, so the claim is checked rather than asserted.  Returns the digests it
    read; raises when either differs.  A snapshot that is not present yet is not
    an error -- there is nothing to confront -- and the mapping comes back
    empty.
    """

    snapshot = profile.release.snapshot if snapshot is None else Path(snapshot)
    pinned = {
        "inference/model.py": MODEL_SOURCE_SHA256,
        "inference/engram.py": ENGRAM_SOURCE_SHA256,
    }
    read: dict[str, str] = {}
    for relative, expected in pinned.items():
        path = snapshot / relative
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            raise DeepSeekV41KernelIRError(
                f"{path} has sha256 {digest} against the pinned {expected}; the "
                "lowering plan in this module describes the pinned source"
            )
        read[relative] = digest
    return read


@dataclass(frozen=True)
class LayerMode:
    """One backbone layer's CSA2 role, derived from the released id lists."""

    layer: int
    ratio: int
    mode: str
    kv_owner: bool
    index_source: bool
    is_candidate_source: bool
    uses_candidates: bool

    @property
    def label(self) -> str:
        """The label the analytical layer publishes for this role."""

        return "swa" if self.ratio == 0 else f"csa2-{self.ratio}-{self.mode}"

    @property
    def plan_key(self) -> str:
        """The :func:`lowering_plan` key that carries this mode's kernels."""

        return f"attention_{'window_only' if self.mode == 'swa' else self.mode}"


#: The four per-layer attention shapes, in the order a decode token meets them.
#: ``attention_window_only`` is the leading sliding-window pair; the other three
#: are the CSA2 modes the model card names Full, Reindex and Reuse.
ATTENTION_MODES = (
    "attention_window_only",
    "attention_full",
    "attention_reindex",
    "attention_reuse",
)


@dataclass(frozen=True)
class DeepSeekV41Profile:
    """Everything this exporter has to know about DeepSeek-V4.1-Flash.

    Structured exactly as :class:`compiler.frontends.v3.deepseek_v4.DeepSeekV4Profile`:
    a released-facts record, the numeric-profile identity that owns every
    emitted kernel's precision contract, and the generation-policy identity the
    entrypoints reference.  Two models must not share either, because a graph
    that did could not be told apart from the other in the numeric
    qualification ledger.

    Every width is a property reading the released configuration.  There is no
    module-level constant beside a config value it is supposed to equal, and
    ``architecture_pins`` confronts the lot with the released ``config.json``
    before anything is emitted.
    """

    release: DeepSeekV4Release
    numeric_profile: str
    generation_policy_id: str

    # -- identity ---------------------------------------------------------
    @property
    def model_id(self) -> str:
        return self.release.model_id

    @property
    def repository(self) -> str:
        return self.release.repository

    @property
    def revision(self) -> str:
        return self.release.revision

    # -- released widths --------------------------------------------------
    @property
    def hidden(self) -> int:
        return int(self.release.scalar("hidden_size"))

    @property
    def hc_mult(self) -> int:
        return int(self.release.scalar("hc_mult"))

    @property
    def hc_sinkhorn_iterations(self) -> int:
        return int(self.release.scalar("hc_sinkhorn_iters"))

    @property
    def heads(self) -> int:
        return int(self.release.scalar("num_attention_heads"))

    @property
    def head_dim(self) -> int:
        return int(self.release.scalar("head_dim"))

    @property
    def rope_dim(self) -> int:
        return int(self.release.scalar("qk_rope_head_dim"))

    @property
    def nope_dim(self) -> int:
        return self.head_dim - self.rope_dim

    @property
    def q_rank(self) -> int:
        return int(self.release.scalar("q_lora_rank"))

    @property
    def o_groups(self) -> int:
        return int(self.release.scalar("o_groups"))

    @property
    def o_rank(self) -> int:
        return int(self.release.scalar("o_lora_rank"))

    @property
    def index_heads(self) -> int:
        return int(self.release.scalar("index_n_heads"))

    @property
    def index_head_dim(self) -> int:
        return int(self.release.scalar("index_head_dim"))

    @property
    def index_topk(self) -> int:
        return int(self.release.scalar("index_topk"))

    @property
    def vocabulary(self) -> int:
        return int(self.release.scalar("vocab_size"))

    @property
    def routed_experts(self) -> int:
        return int(self.release.scalar("n_routed_experts"))

    @property
    def shared_experts(self) -> int:
        return int(self.release.scalar("n_shared_experts"))

    @property
    def top_k(self) -> int:
        return int(self.release.scalar("num_experts_per_tok"))

    @property
    def moe_intermediate(self) -> int:
        return int(self.release.scalar("moe_intermediate_size"))

    @property
    def sliding_window(self) -> int:
        return int(self.release.scalar("sliding_window"))

    @property
    def weight_scale_block(self) -> int:
        """The released FP8 weight block, both dimensions of it being equal.

        ``quantization_config.weight_block_size`` is ``[32, 32]`` on this
        release and ``[128, 128]`` on both V4 ones, so nothing downstream may
        assume either.
        """

        block = list(self.release.quantization_config["weight_block_size"])
        if len(block) != 2 or block[0] != block[1]:
            raise DeepSeekV41KernelIRError(
                f"the released weight block {block} is not square; this export "
                "sizes one scale group by it"
            )
        return int(block[0])

    @property
    def layers(self) -> int:
        return self.release.num_hidden_layers

    @property
    def compress_ratios(self) -> tuple[int, ...]:
        """The released sequence: one entry per layer, DSpark stages included."""

        return tuple(int(value) for value in self.release.compress_ratios)

    @property
    def backbone_compress_ratios(self) -> tuple[int, ...]:
        """The backbone prefix, which is what decides the CSA2 mode sequence."""

        ratios = self.compress_ratios[: self.layers]
        if len(ratios) != self.layers:
            raise DeepSeekV41KernelIRError(
                f"the released compression sequence covers {len(ratios)} of "
                f"{self.layers} layers"
            )
        return ratios

    # -- CSA2 sharing -----------------------------------------------------
    @property
    def kv_source_layers(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self.release.scalar("kv_source_layer_ids"))

    @property
    def index_source_layers(self) -> tuple[int, ...]:
        return tuple(
            int(value) for value in self.release.scalar("index_source_layer_ids")
        )

    @property
    def candidate_source_layer(self) -> int:
        return int(self.release.scalar("candidate_source_layer_id"))

    @property
    def candidate_blocks(self) -> int:
        return int(self.release.scalar("candidate_topk_blocks"))

    @property
    def candidate_block(self) -> int:
        return int(self.release.scalar("candidate_block_size"))

    @property
    def candidate_pool_entries(self) -> int:
        """The bound ``candidate_pool_bound`` checks (plan section 6.3)."""

        return self.candidate_blocks * self.candidate_block

    # -- Engram -----------------------------------------------------------
    @property
    def engram_layers(self) -> tuple[int, ...]:
        return tuple(int(value) for value in self.release.scalar("engram_layer_ids"))

    @property
    def engram_head_dim(self) -> int:
        return int(self.release.scalar("engram_head_dim"))

    @property
    def engram_heads(self) -> int:
        return int(self.release.scalar("engram_n_heads"))

    @property
    def engram_max_ngram(self) -> int:
        return int(self.release.scalar("engram_max_ngram_size"))

    @property
    def engram_hash_columns(self) -> int:
        """``(max_ngram_size - 1) * n_heads``, per ``engram.py``.

        ``NgramHashState.forward`` hashes each position as the 2-gram through
        the ``max_ngram_size``-gram, each split over ``engram_n_heads`` heads,
        and returns one row id per pair.  The analytical layer carries the
        product as ``engram_hash_columns``; this derives it, so the two can be
        confronted.
        """

        return (self.engram_max_ngram - 1) * self.engram_heads

    @property
    def engram_rows(self) -> tuple[int, ...]:
        rows = self.release.scalar("engram_num_embeddings")
        return tuple(int(value) for value in rows)

    @property
    def engram_compressed_vocabulary(self) -> int:
        return int(self.release.scalar("engram_compressed_vocab_size"))

    @property
    def engram_pad_token(self) -> int:
        """``engram_pad_id``: the token a blocked lookback substitutes.

        ``NgramHashState`` hashes ``token_map[args.engram_pad_id]``, the
        *compressed* image of this id, which is what the emitted operator states.
        """

        return int(self.release.scalar("engram_pad_token_id"))

    @property
    def engram_bucket_base(self) -> int:
        """``engram_vocab_size``: the base each column's prime modulus is drawn above."""

        return int(self.release.scalar("engram_vocab_size"))

    # -- numeric scalars ---------------------------------------------------
    @property
    def rms_epsilon(self) -> float:
        return float(self.release.scalar("rms_norm_eps"))

    @property
    def hc_epsilon(self) -> float:
        return float(self.release.scalar("hc_eps"))

    @property
    def route_scale(self) -> float:
        return float(self.release.scalar("routed_scaling_factor"))

    @property
    def swiglu_limit(self) -> float:
        return float(self.release.scalar("swiglu_limit"))

    @property
    def normalize_top_k(self) -> bool:
        return bool(self.release.scalar("norm_topk_prob"))

    @property
    def scoring_function(self) -> str:
        """``scoring_func``: which router transcendental the released Gate takes.

        Anything but ``softmax`` or ``sigmoid`` is the sqrt-softplus branch, which
        is what this release ships and what ``SQRT_SOFTPLUS`` implements.
        """

        return str(self.release.scalar("scoring_func"))

    # -- speculation ------------------------------------------------------
    @property
    def draft_block(self) -> int:
        """``dspark_block_size``: draft tokens one speculative pass proposes."""

        return int(self.release.scalar("dspark_block_size"))

    @property
    def markov_rank(self) -> int:
        return int(self.release.scalar("dspark_markov_rank"))

    @property
    def target_layers(self) -> tuple[int, ...]:
        """Backbone layers whose attention input the draft head reads."""

        return tuple(
            int(value)
            for value in self.release.scalar("dspark_target_layer_ids")
        )

    @property
    def draft_stages(self) -> int:
        """DSpark stages, from the record's own count of them."""

        return self.release.dspark_stage_count

    @property
    def draft_layers(self) -> tuple[int, ...]:
        return tuple(range(self.layers, self.layers + self.draft_stages))

    # -- derived ----------------------------------------------------------
    @property
    def hc_mix(self) -> int:
        return (2 + self.hc_mult) * self.hc_mult

    @property
    def hc_coefficients(self) -> int:
        return self.hc_mult + self.hc_mult * self.hc_mult

    @property
    def output_join_levels(self) -> int:
        """CONCAT kernels in ``GROUPED_OUTPUT_PROJECT``'s feature-axis join.

        Amendment A17's rule, unchanged: joins take four input views at a time.
        """

        joins, remaining = 0, self.o_groups
        while remaining > 1:
            remaining = -(-remaining // 4)
            joins += remaining
        return joins

    def moe_config(self, layer: int) -> tuple[int, int]:
        """Routed expert count and top-k for one layer.

        ``ModelArgs.get_moe_config``: a backbone layer takes the backbone
        counts, a DSpark stage its own.  The DSpark counts are the released
        ones when the config states them and the backbone ones otherwise; WP-B
        pins them, and until then a draft stage falls back to the backbone
        counts exactly as the released source does.
        """

        if layer < self.layers:
            return self.routed_experts, self.top_k
        experts = int(self.release.scalar("dspark_n_routed_experts"))
        top_k = int(self.release.scalar("dspark_num_experts_per_tok"))
        return (experts or self.routed_experts, top_k or self.top_k)

    def layer_modes(self) -> tuple[LayerMode, ...]:
        """Derive every backbone layer's CSA2 role from the released fields.

        This is the one place the mode sequence exists.  Nothing here is a
        table: ``inference/model.py`` decides a layer's shape from exactly
        these four facts (``Attention.__init__``'s ``is_kv_source`` and
        ``is_index_source``, and ``Indexer.__init__``'s ``is_candidate_source``
        and ``uses_candidates``), and so does this.
        """

        kv_sources = frozenset(self.kv_source_layers)
        index_sources = frozenset(self.index_source_layers)
        candidate_source = self.candidate_source_layer
        modes: list[LayerMode] = []
        for layer, ratio in enumerate(self.backbone_compress_ratios):
            index_source = layer in index_sources
            uses_candidates = 0 <= candidate_source < layer
            if ratio == 0:
                mode = "swa"
            elif not index_source:
                mode = "reuse"
            elif uses_candidates:
                mode = "reindex"
            else:
                mode = "full"
            modes.append(
                LayerMode(
                    layer=layer,
                    ratio=ratio,
                    mode=mode,
                    kv_owner=layer in kv_sources,
                    index_source=index_source,
                    is_candidate_source=layer == candidate_source,
                    uses_candidates=uses_candidates,
                )
            )
        return tuple(modes)

    @property
    def architecture_pins(self) -> tuple[tuple[str, Any], ...]:
        """Released ``text_config`` key and the value this export will use.

        Every field the graph is sized by, confronted with the config it claims
        to come from.  ``candidate_source_layer_id`` is the clearest case for
        why all of them are checked rather than the ones that look risky:
        nothing downstream would notice a candidate source of 24 instead of 20,
        because either value produces a legal mode sequence -- one with four
        Reindex layers and one with three.
        """

        return (
            ("hidden_size", self.hidden),
            ("hc_mult", self.hc_mult),
            ("hc_sinkhorn_iters", self.hc_sinkhorn_iterations),
            ("num_attention_heads", self.heads),
            ("head_dim", self.head_dim),
            ("qk_rope_head_dim", self.rope_dim),
            ("q_lora_rank", self.q_rank),
            ("o_groups", self.o_groups),
            ("o_lora_rank", self.o_rank),
            ("index_head_dim", self.index_head_dim),
            ("index_n_heads", self.index_heads),
            ("index_topk", self.index_topk),
            ("vocab_size", self.vocabulary),
            ("n_routed_experts", self.routed_experts),
            ("n_shared_experts", self.shared_experts),
            ("num_experts_per_tok", self.top_k),
            ("moe_intermediate_size", self.moe_intermediate),
            ("sliding_window", self.sliding_window),
            ("num_hidden_layers", self.layers),
            ("kv_source_layer_ids", list(self.kv_source_layers)),
            ("index_source_layer_ids", list(self.index_source_layers)),
            ("candidate_source_layer_id", self.candidate_source_layer),
            ("candidate_topk_blocks", self.candidate_blocks),
            ("candidate_block_size", self.candidate_block),
            ("engram_layer_ids", list(self.engram_layers)),
            ("engram_head_dim", self.engram_head_dim),
            ("engram_n_heads", self.engram_heads),
            ("engram_max_ngram_size", self.engram_max_ngram),
            ("engram_num_embeddings", list(self.engram_rows)),
            ("engram_compressed_vocab_size", self.engram_compressed_vocabulary),
            ("engram_pad_token_id", self.engram_pad_token),
            ("engram_vocab_size", self.engram_bucket_base),
            ("max_position_embeddings", architectural_max_context(self)),
            # The scalars the emitted kernels carry rather than are sized by.
            # They are pinned for the reason the V4 front end pins its route
            # scale: a wrong one has no downstream witness at all.  1.5 applied
            # where the release says 2.5 is a finite number either way, an
            # epsilon of 1e-6 where the release says 1e-20 is a healthy
            # normalisation of the wrong model, and a router that takes the
            # softmax branch where the release takes sqrt-softplus produces a
            # legal distribution over the wrong experts.
            ("rms_norm_eps", self.rms_epsilon),
            ("hc_eps", self.hc_epsilon),
            ("routed_scaling_factor", self.route_scale),
            ("swiglu_limit", self.swiglu_limit),
            ("norm_topk_prob", self.normalize_top_k),
            ("scoring_func", self.scoring_function),
        )


#: DeepSeek-V4.1-Flash at revision ``dba1be0a...``.  Both identities are this
#: model's alone, for the reason the V4 profiles state.
V41_FLASH_PROFILE = DeepSeekV41Profile(
    release=V41_FLASH,
    numeric_profile="deepseek_v41_flash_target_precision_v1",
    generation_policy_id="deepseek_v41_flash_greedy_argmax_v1",
)

#: The reduced regression fixture, as its own profile.
#:
#: Its own numeric-profile and generation-policy identities, for the reason the
#: released profiles state: two models must not share either, because a graph
#: that did could not be told apart from the other in the numeric qualification
#: ledger. Every width is still a property reading the released configuration --
#: this profile just reads a different one, and ``architecture_pins`` confronts
#: it with that config before anything is emitted.
V41_FLASH_REDUCED_PROFILE = DeepSeekV41Profile(
    release=V41_FLASH_REDUCED,
    numeric_profile="deepseek_v41_flash_reduced_target_precision_v1",
    generation_policy_id="deepseek_v41_flash_reduced_greedy_argmax_v1",
)

MODEL_ID = V41_FLASH_PROFILE.model_id

MODEL_PROFILES: Mapping[str, DeepSeekV41Profile] = {
    profile.model_id: profile
    for profile in (V41_FLASH_PROFILE, V41_FLASH_REDUCED_PROFILE)
}

DEFAULT_SNAPSHOT = V41_FLASH.snapshot
DEFAULT_CHECKPOINT_LOCK = V41_FLASH.checkpoint_lock


def resolve_model_profile(
    model: str | DeepSeekV41Profile | DeepSeekV4Release = MODEL_ID,
) -> DeepSeekV41Profile:
    """Return the profile for a model id, a release record, or a profile."""

    if isinstance(model, DeepSeekV41Profile):
        return model
    if isinstance(model, DeepSeekV4Release):
        model = model.model_id
    try:
        return MODEL_PROFILES[model]
    except KeyError:
        raise DeepSeekV41KernelIRError(
            f"unknown DeepSeek-V4.1 model {model!r}; this front end carries "
            + ", ".join(sorted(MODEL_PROFILES))
        ) from None


# ---------------------------------------------------------------------------
# The released configuration, and the pins confronted with it
# ---------------------------------------------------------------------------
def released_architecture_config(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
    path: Path | None = None,
    source_path: Path | None = None,
) -> Mapping[str, Any]:
    """The authenticated released architecture section, as a flat mapping.

    ``compiler.frontend.deepseek_v41.load_official_config`` owns the gate: it
    authenticates the committed config bytes against the release record's
    digest and byte length, against the checkpoint source contract wherever
    that is committed, and confronts every pinned key with the record.  This
    resolves the release's own ``config_layout`` to hand back the section the
    architecture lives in -- ``text_config`` on this release -- so the pin
    confrontation below reads one flat mapping and no path is spelled twice.
    """

    try:
        config = load_official_config(
            path=path, source_path=source_path, release=profile.release
        )
        section = profile.release.config_section(config, "architecture")
    except DeepSeekV41AdapterError as exc:
        raise DeepSeekV41KernelIRError(str(exc)) from None
    if not isinstance(section, Mapping):
        raise DeepSeekV41KernelIRError(
            f"the {profile.model_id} config's architecture section is not an object"
        )
    return section


def validate_architecture_pins(
    profile: DeepSeekV41Profile,
    config: Mapping[str, Any],
) -> None:
    """Confront every width this export sizes by with the released config.

    The compression sequence is confronted separately, because the released one
    is longer than the backbone: its first ``num_hidden_layers`` entries are the
    layers whose CSA2 mode this export derives, and its tail is the DSpark
    stages, whose ratio ``DSparkAttention.forward`` asserts is zero.  Every
    other pin is a scalar or an id list compared as it stands.
    """

    released_ratios = config.get("compress_ratios")
    if not isinstance(released_ratios, list):
        raise DeepSeekV41KernelIRError(
            "the released architecture section states no compress_ratios sequence"
        )
    layers = profile.layers
    if [int(value) for value in released_ratios] != list(profile.compress_ratios):
        raise DeepSeekV41KernelIRError(
            f"the released compression sequence {released_ratios} differs from "
            f"the record's {list(profile.compress_ratios)}"
        )
    draft_ratios = [int(value) for value in released_ratios[layers:]]
    if len(draft_ratios) != profile.draft_stages:
        raise DeepSeekV41KernelIRError(
            f"the released compression sequence carries {len(draft_ratios)} "
            f"entries past the backbone against {profile.draft_stages} DSpark "
            "stages"
        )
    if any(ratio != 0 for ratio in draft_ratios):
        raise DeepSeekV41KernelIRError(
            f"a DSpark stage states a compression ratio {draft_ratios}; the "
            "released DSparkAttention asserts every one of them is zero"
        )

    for key, expected in profile.architecture_pins:
        if key not in profile.release.config_scalars:
            raise DeepSeekV41KernelIRError(
                f"{profile.model_id} sizes the graph by {key}, which its release "
                "record does not pin"
            )
        if key not in config:
            raise DeepSeekV41KernelIRError(
                f"{profile.model_id} sizes the graph by {key}, which the "
                "released architecture section does not state"
            )
        released = config[key]
        if isinstance(released, (list, tuple)):
            released = list(released)
        if released != expected:
            raise DeepSeekV41KernelIRError(
                f"released config {key}={released!r} differs from the pinned "
                f"{expected!r}"
            )


def confront_layer_modes(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
) -> tuple[LayerMode, ...]:
    """Derive the mode sequence and confront it with the committed one.

    The committed sequence in ``metadata.csa2_layer_modes`` was derived by the
    analytical layer from the same released id lists.  Two independent
    derivations that agree is evidence; one table copied twice is not.
    """

    derived = profile.layer_modes()
    committed = _candidate_layer_modes()
    if len(committed) != len(derived):
        raise DeepSeekV41KernelIRError(
            f"the committed mode sequence covers {len(committed)} layers, the "
            f"released configuration {len(derived)}"
        )
    for mode, record in zip(derived, committed):
        if int(record["layer"]) != mode.layer:
            raise DeepSeekV41KernelIRError(
                f"the committed mode sequence is out of order at {record['layer']}"
            )
        if str(record["mode"]) != mode.mode or str(record["label"]) != mode.label:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives as {mode.label!r} from the released "
                f"configuration and is committed as {record['label']!r}"
            )
        if int(record["ratio"]) != mode.ratio:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives ratio {mode.ratio} and is committed "
                f"as {record['ratio']}"
            )
        if mode.mode == "swa":
            continue
        if bool(record["kv_owner"]) != mode.kv_owner:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives kv_owner {mode.kv_owner} against the "
                f"committed {record['kv_owner']}"
            )
        if bool(record["scans_index"]) != mode.index_source:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives index_source {mode.index_source} "
                f"against the committed {record['scans_index']}"
            )
        if bool(record["is_candidate_source"]) != mode.is_candidate_source:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives is_candidate_source "
                f"{mode.is_candidate_source} against the committed "
                f"{record['is_candidate_source']}"
            )
        cap = int(record["index_scan_entries_cap"])
        # A cap bounds a scan, so only a layer that scans has one: a Reuse
        # layer after the candidate source scores nothing and is uncapped.
        derived_cap = (
            profile.candidate_pool_entries
            if mode.index_source and mode.uses_candidates
            else 0
        )
        #: THE COMMITTED TABLE IS THE RELEASED MODEL'S, so for any other
        #: profile the cap is confronted twice rather than not at all: the
        #: committed number must be the RELEASED pool, which is what proves the
        #: table is the one it claims to be, and the derived number must be THIS
        #: profile's pool. For the released profile the two collapse into the
        #: single equality this check has always made.
        #:
        #: The cap is the candidate pool when a layer scans, and a reduction
        #: that narrows the pool narrows the cap with it -- the released 16,384
        #: against the reduced fixture's 512. Comparing the reduced derivation
        #: with the released table directly refused a model whose mode sequence
        #: is identical, which is the one thing the reduction keeps exactly.
        released_cap = (
            V41_FLASH_PROFILE.candidate_pool_entries
            if mode.index_source and mode.uses_candidates
            else 0
        )
        if cap != released_cap:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer}'s committed index scan cap {cap} is not "
                f"the released model's {released_cap}, so the committed table "
                f"is not the one this check confronts"
            )
        if profile.model_id == V41_FLASH_PROFILE.model_id and cap != derived_cap:
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer} derives an index scan cap of {derived_cap} "
                f"against the committed {cap}"
            )
        if derived_cap != (
            profile.candidate_pool_entries
            if mode.index_source and mode.uses_candidates
            else 0
        ):  # pragma: no cover - derived_cap is that expression
            raise DeepSeekV41KernelIRError(
                f"layer {mode.layer}'s derived cap is not its own profile's pool"
            )
    return derived


# ---------------------------------------------------------------------------
# Source-kind to neutral-kind plan
# ---------------------------------------------------------------------------
#: Ordered source operator kinds one CSA2 layer emits *in addition to* the
#: kinds every layer emits, per attention mode.  Everything about a mode that
#: is not a width lives here, and :func:`lowering_plan` expands it through the
#: source-kind plan so the mode entries cannot drift from the kind entries.
_ATTENTION_MODE_SOURCE_KINDS: Mapping[str, tuple[str, ...]] = {
    # Layers 0 and 1: ratio 0, so there is no compressed path, no index and no
    # KV view to join -- ``Attention.forward`` skips ``_compress_kv`` entirely.
    "attention_window_only": (),
    # A cache owner and an unbounded index scan.  The order is the released
    # one, and it is not the obvious one: ``Attention._compress_kv`` runs the
    # compressor, then the indexer -- which derives its own key from the
    # *unrotated* latent -- and only then rotates, quantizes and writes that
    # latent, because "the indexer needs the latent before RoPE, so it runs
    # before the cache is written".  A plan that wrote the cache first would
    # hand the indexer a rotated, requantized latent and change its keys.
    #
    # ``CANDIDATE_BLOCK_SELECT`` belongs between the score and the top-k and is
    # emitted only at the candidate source, so :func:`layer_source_plan` splices
    # it there rather than this table carrying a fifth mode.
    "attention_full": (
        "COMPRESS_PROJECT",
        # The state update carries the partial group and hands the pool its two
        # candidate planes, so it runs *before* the pool.  This pair was listed
        # the other way round while nothing consumed the plan; the emitted graph
        # is single assignment, so a pool ahead of its producer is not a
        # cosmetic ordering question -- it names two tensors that do not exist.
        "COMPRESS_STATE_UPDATE",
        "COMPRESS_POOL",
        # ``Compressor.forward`` ends ``return self.norm(kv.to(dtype))``: the
        # pooled latent is binary32 because the softmax gate runs in fp32, and it
        # is CAST BACK to the activation dtype before the norm.  The cast was
        # missing here, so the norm was handed an fp32 view and refused it -- its
        # contract is BF16 in and BF16 out.  V4's own export emits the same
        # conversion after its pool (``BINARY32_TO_BF16`` there too).
        "BINARY32_TO_BF16",
        "RMS_NORM",
        "INDEX_KEY_PROJECT",
        "RMS_NORM",
        "ROPE_APPLY",
        "FP4_INDEX_QDQ",
        "INDEX_KEY_WRITE",
        # The readable prefix of the index key cache, published as its own
        # operand: the scorer's candidate axis is the groups this request has
        # completed, not the cache's capacity.
        "COMPRESSED_KV_VALID_VIEW",
        "INDEX_QUERY_PROJECT",
        "ROPE_APPLY",
        "FP4_INDEX_QDQ",
        "INDEX_WEIGHT_PROJECT",
        "INDEX_SCORE",
        "INDEX_TOPK",
        "ROPE_APPLY",
        "FP4_MAIN_QDQ",
        "COMPRESS_KV_WRITE",
        "COMPRESSED_KV_VALID_VIEW",
        "ATTENTION_KV_VIEW",
    ),
    # Scores its own queries, but only inside the pool the candidate source
    # published: the mask is read as state and enters ``INDEX_TOPK``'s optional
    # slot 3 (AM-E10).  No compressor and no index key: this layer owns neither.
    "attention_reindex": (
        "INDEX_QUERY_PROJECT",
        "ROPE_APPLY",
        "FP4_INDEX_QDQ",
        "INDEX_WEIGHT_PROJECT",
        "INDEX_SCORE",
        "CANDIDATE_MASK_READ",
        "INDEX_TOPK",
        "COMPRESSED_KV_VALID_VIEW",
        "ATTENTION_KV_VIEW",
    ),
    # Scores nothing at all: ``Attention._compress_topk_idxs`` returns the
    # selection its index source published, and the cache is the owner's.
    "attention_reuse": (
        "SHARED_INDEX_REUSE",
        "COMPRESSED_KV_VALID_VIEW",
        "ATTENTION_KV_VIEW",
    ),
}

#: Source operator kinds the ordinary profile leaves out; they belong to the
#: DSpark speculative path, which ADR-003 section 18 sequences afterwards.
SPECULATIVE_SOURCE_KINDS = frozenset(
    {
        "CONFIDENCE_SCORE",
        "DSPARK_MAIN_PROJECT",
        "DSPARK_NOISE_EMBED",
        "DSPARK_PREFILL_KV",
        "DSPARK_WINDOW_INDEX",
        "MARKOV_AUTOREGRESSIVE_LOOP",
        "TARGET_HIDDEN_CAPTURE",
    }
)


def source_kind_plan(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
    *,
    include_speculative: bool = False,
) -> Mapping[str, tuple[str, ...]]:
    """One profile's source-kind to neutral-kind plan.

    ``include_speculative`` adds the seven :data:`SPECULATIVE_SOURCE_KINDS`.
    They are behind the flag rather than always present because two of them are
    sized by a speculation width the committed candidate profile does not carry
    (the analytical layer charges DSpark only under speculation), so building
    them reads the released configuration; the ordinary plan reads nothing
    outside the repository.

    Kinds DeepSeek-V4 already lowers keep the V4 lowering byte for byte; a V4.1
    module that invented its own shape for ``HC_PRE`` or ``MXFP4_SWIGLU`` would
    be a defect even if it ran.  The entries that are new are the ones the
    released source made new:

    * ``FP4_MAIN_QDQ`` is not ``FP4_INDEX_QDQ``.  The main latent takes one
      E4M3 scale per 16 channels and the index key one E8M0 per 32, which is
      two dtypes and two numeric contracts, not one operator with a parameter.
    * ``ENGRAM_*`` splits into the compressed-id map, the n-gram hash, the row
      read and the fused gate, because each is a different engine family:
      ``TENSOR``, ``DMA``, ``TENSOR`` and ``VECTOR``.
    * ``CANDIDATE_BLOCK_SELECT`` is one source operator lowering to three
      neutral kernels -- block maximum, a top-k over blocks, and the expansion
      of the chosen block ids into a position mask.  ``select_candidate_blocks``
      is one function and this keeps it one auditable contract.
    * ``HC_FINAL_COLLAPSE`` replaces V4's ``HC_HEAD``: this checkpoint has no
      final mHC head projection tensor, and the released collapse reuses the
      last block's own pre coefficients (``Transformer.forward``).
    """

    plan: dict[str, tuple[str, ...]] = {
        "ATTENTION_KV_VIEW": ("CONCAT",),
        "BIASED_TOPK_ROUTE": ("BIASED_TOPK",),
        # ``select_candidate_blocks``: block maximum, top-k over blocks, then
        # the block ids expanded to a per-position mask of ``width``.
        "CANDIDATE_BLOCK_SELECT": ("BLOCK_MAX", "INDEX_TOPK", "CANDIDATE_MASK"),
        "CANDIDATE_MASK_READ": ("STATE_READ",),
        "COMPRESSED_KV_VALID_VIEW": ("STATE_READ",),
        "COMPRESS_KV_WRITE": ("KV_APPEND",),
        "BINARY32_TO_BF16": ("CONVERT",),
        "COMPRESS_POOL": ("COMPRESS_POOL",),
        "COMPRESS_PROJECT": ("COMPRESS_PROJECT",),
        "COMPRESS_STATE_UPDATE": ("COMPRESS_STATE_UPDATE",),
        # The fused gate of plan section 5: normalized dot, signed sqrt,
        # sigmoid and the residual add, reading (h, key, value, q, k).
        "ENGRAM_GATE": ("ENGRAM_GATE",),
        # ``Engram.wkv`` projects the flattened rows into hc_mult keys and one
        # shared value.  ONE projection and no movement after it: the released
        # ``kv.split([hc_mult * dim, dim])`` is a *view* of that output, and the
        # gate reads its planes -- ``[hc_mult + 1, hidden]`` per token, the key
        # of stream m at plane m and the shared value at plane hc_mult.  The two
        # ``SELECT`` kernels this entry used to name could not express the split
        # in any case: a neutral ``SELECT`` names one index of one axis and drops
        # it, so from an ``[hc_mult + 1, hidden]`` packing it can only ever
        # produce one ``[hidden]`` plane, never the ``hc_mult`` of them the key
        # operand holds.
        "ENGRAM_KV_PROJECT": ("QUANTIZE", "MATMUL"),
        # ``NgramHashState.forward``: gather the look-back window of compressed
        # ids, multiply-xor-modulo them into row ids, and join the orders into
        # the one selector the row read is indexed by.
        #
        # One ``NGRAM_HASH`` per n-gram ORDER, which is a property of the
        # operator rather than a choice here: ``DMA.NGRAM_HASH`` states the
        # order it computes in ``aux_id_0`` (both backends refuse a kernel that
        # declares none) and writes ``[positions, heads]``, so the 24 columns of
        # a released module are ``engram_max_ngram_size - 1`` operators of
        # ``engram_n_heads`` columns each.  A single kernel covering all 24
        # could not say which order any column carried.
        # NO LOOKBACK GATHER.  The plan used to lead with one, and the emitter
        # produced a (span, max_ngram) window for NGRAM_HASH to consume.  The
        # operator owns that lookback: its RTL declares the IR kind
        # ``NGRAM_HASH(token_ids, order, head) -> row_ids`` and forms
        # ``t_j = pad_id when blocked, else the compressed id`` itself; the
        # functional engine requires one token id per output position, not a
        # window per position; and the contract's authority,
        # ``runtime.reference.engram.ngram_row_ids``, takes ``token_ids`` and
        # indexes ``compressed[p - j]`` with the sticky blocked rule.  The window
        # was also not describable as a movement -- the lookback descends while a
        # view's strides are unsigned, and a blocked lookback substitutes a pad
        # instead of addressing anything -- which is what V4.1 PC 241 reported.
        "ENGRAM_NGRAM_HASH": (
            ("NGRAM_HASH",) * (profile.engram_max_ngram - 1)
            + ("CONCAT",)
        ),
        # ``ParallelEngramEmbedding.forward`` keeps the table FP8 and
        # dequantizes each row on lookup, gathering the row's scale with the
        # same indices -- which is TWO lookups, the codes and their scales.
        "ENGRAM_ROW_LOOKUP": ("EMBEDDING_LOOKUP", "EMBEDDING_LOOKUP",
                              "DEQUANTIZE"),
        # ``build_compressed_token_map``'s table, read once per token.
        "ENGRAM_TOKEN_COMPRESS": ("EMBEDDING_LOOKUP",),
        "EXPERT_DISPATCH": ("EXPERT_DISPATCH",),
        "EXPERT_REDUCE": ("EXPERT_REDUCE",),
        "FP4_INDEX_QDQ": ("QUANTIZE", "DEQUANTIZE"),
        "FP4_MAIN_QDQ": ("QUANTIZE", "DEQUANTIZE"),
        "FP8_LINEAR": ("QUANTIZE", "MATMUL"),
        "FP8_QDQ": ("QUANTIZE", "DEQUANTIZE"),
        "FP8_SWIGLU": (
            "QUANTIZE",
            "MATMUL",
            "MATMUL",
            "SWIGLU",
            "QUANTIZE",
            "MATMUL",
        ),
        # ``Attention.forward`` ends ``x = self.wo_b(o.flatten(2))``: the
        # block-diagonal ``wo_a`` over groups, the feature-axis join of their
        # results, and *then* a dense FP8 contraction back to the hidden width.
        # The V4 entry this was copied from covered only the grouped half,
        # because V4's source graph carried ``wo_b`` as a separate
        # ``FP8_LINEAR`` node; V4.1's layer plan has no such node, so without
        # the last two kinds here the graph would hand ``HC_POST`` an
        # ``o_groups * o_lora_rank``-wide branch where the residual stream is
        # ``hidden_size`` wide, and no layer would be emittable at all.
        "GROUPED_OUTPUT_PROJECT": (
            ("COPY",)
            + ("SELECT", "MATMUL") * profile.o_groups
            + ("CONCAT",) * profile.output_join_levels
            + ("QUANTIZE", "MATMUL")
        ),
        "HC_EXPAND": ("BROADCAST",),
        "HC_FINAL_COLLAPSE": ("EXPERT_REDUCE",),
        "HC_POST": ("HYPER_CONNECT_POST",),
        "HC_PRE": ("HYPER_CONNECT_PRE", "SELECT", "SELECT", "EXPERT_REDUCE"),
        # THE MODEL'S FINAL NORM IS AN ORDINARY RMSNorm, and it used to name
        # ``HEAD_RMS_NORM`` here.  ``VECTOR.HEAD_RMS_NORM`` is a different
        # operator: the released QUERY HEAD norm, unweighted and at a pinned head
        # width the engine carries as a constant (``HEAD_RMS_NORM_WIDTH``).  The
        # final norm is ``self.norm(h)`` in ``Transformer.forward``, the same
        # weighted ``RMSNorm(args.dim)`` class as every layer norm, over the whole
        # hidden width -- so it lowers to the same operator and names the same
        # contract as those 168 kernels.  Issued as the head norm it reached the
        # engine with a contract that engine does not implement, at PC 4,321 of
        # 4,337: the last operator before the LM head.
        "FINAL_RMS_NORM": ("RMS_NORM",),
        "INDEX_KEY_PROJECT": ("MATMUL",),
        "INDEX_KEY_WRITE": ("KV_APPEND",),
        "INDEX_QUERY_PROJECT": ("QUANTIZE", "MATMUL"),
        "INDEX_SCORE": ("INDEX_SCORE",),
        "INDEX_TOPK": ("INDEX_TOPK", "CONCAT"),
        "INDEX_WEIGHT_PROJECT": ("MATMUL", "SCALE"),
        "KV_WINDOW_WRITE": ("KV_APPEND",),
        "LM_HEAD": ("LAST_TOKEN_SELECT", "VOCAB_PROJECT"),
        "MXFP4_SWIGLU": (
            "QUANTIZE",
            "ROUTED_MATMUL",
            "ROUTED_MATMUL",
            "SWIGLU",
            "MUL",
            "QUANTIZE",
            "ROUTED_MATMUL",
        ),
        "RMS_NORM": ("RMS_NORM",),
        "ROPE_APPLY": ("GATHER", "ROPE"),
        "ROPE_INVERSE": ("ROPE_INVERSE",),
        "ROUTER_SCORE": ("ROUTER_SCORE",),
        "ROUTER_WEIGHT_NORMALIZE": ("GATHER", "WEIGHT_NORMALIZE", "SCALE"),
        "SAMPLE": ("SCALE", "ARGMAX", "TOKEN_APPEND"),
        # ``Attention.forward`` concatenates the window block with the
        # compressed selection *in the layer*, after
        # ``_compress_topk_idxs`` has returned either this layer's own selection
        # or the one its source published, so what a source publishes is the
        # compressed half alone and every CSA2 layer owns the join.  That is what
        # makes the per-layer ``WINDOW_INDEX`` of the layer plan a read rather
        # than a dead enumeration: the reused half is rebased onto the joined
        # rows, and the window block ahead of it is the layer's own.
        "SHARED_INDEX_REUSE": ("STATE_READ", "CONCAT"),
        "SPARSE_ATTENTION": ("ATTENTION_SPARSE",),
        "SQRT_SOFTPLUS": ("SQRT_SOFTPLUS",),
        "TOKEN_EMBED": ("EMBEDDING_LOOKUP",),
        "WINDOW_INDEX": ("WINDOW_INDEX",),
    }
    if not include_speculative:
        return plan
    plan.update(
        {
            "CONFIDENCE_SCORE": ("CONCAT", "MATMUL"),
            "DSPARK_MAIN_PROJECT": ("CONCAT", "QUANTIZE", "MATMUL", "RMS_NORM"),
            "DSPARK_NOISE_EMBED": ("CONCAT", "EMBEDDING_LOOKUP", "BROADCAST"),
            "DSPARK_PREFILL_KV": (
                "QUANTIZE",
                "MATMUL",
                "RMS_NORM",
                "ROPE",
                "QUANTIZE",
                "DEQUANTIZE",
                "KV_APPEND",
            ),
            "DSPARK_WINDOW_INDEX": ("DSPARK_WINDOW_INDEX",),
            # One draft block is ``draft_block`` autoregressive Markov steps
            # and the four concatenations that assemble their outputs.
            "MARKOV_AUTOREGRESSIVE_LOOP": (
                "EMBEDDING_LOOKUP",
                "VOCAB_PROJECT",
                "ADD",
                "ARGMAX",
                "TOKEN_APPEND",
            )
            * profile.draft_block
            + ("CONCAT",) * 4,
            "TARGET_HIDDEN_CAPTURE": ("PARTITION_SUM", "SCALE"),
        }
    )
    return plan


def attention_mode_plan(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
) -> Mapping[str, tuple[str, ...]]:
    """The ordered neutral kinds each attention mode adds, per mode.

    Derived by expanding :data:`_ATTENTION_MODE_SOURCE_KINDS` through
    :func:`source_kind_plan`, so a mode entry is never a second statement of a
    kind's lowering.
    """

    kinds = source_kind_plan(profile)
    plan: dict[str, tuple[str, ...]] = {}
    for mode, sources in _ATTENTION_MODE_SOURCE_KINDS.items():
        expanded: list[str] = []
        for source in sources:
            expanded.extend(kinds[source])
        plan[mode] = tuple(expanded)
    return plan


def lowering_plan(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
    *,
    include_speculative: bool = False,
) -> Mapping[str, tuple[str, ...]]:
    """The full plan: one entry per source kind, one per attention mode.

    Two namespaces in one mapping, told apart by case, because they answer two
    different questions about the same lowering and the plan for this work
    package names both:

    * an ``UPPER_CASE`` key is a **source operator kind** and its value is the
      ordered neutral kinds that kind lowers to -- the V4 contract, unchanged;
    * a ``lower_case`` key is one of :data:`ATTENTION_MODES` and its value is
      the ordered neutral kinds a layer in that mode emits *beyond* the ones
      every layer emits.

    The second is computed from the first.  Use :func:`source_kind_plan` or
    :func:`attention_mode_plan` where only one namespace is wanted.
    """

    plan = dict(source_kind_plan(profile, include_speculative=include_speculative))
    plan.update(attention_mode_plan(profile))
    return plan


#: The release profile's plan, under the name the tests and the census import.
LOWERING_PLAN: Mapping[str, tuple[str, ...]] = lowering_plan(V41_FLASH_PROFILE)


#: Canonical numeric-contract base per source operator kind.  Identical in kind
#: to the V4 table: opaque semantic identifiers, never module paths, and where
#: the ABI has already frozen a name for an arithmetic this table uses *that*
#: name.  ``RMS_NORM`` keeps amendment A8's ``deepseek_rmsnorm_binary32``,
#: because the engine dispatches on the name and a front end does not get to
#: restate a frozen contract identity.  The four new bases are the ones plan
#: section 6.4 publishes in the V4.1 capability.
CONTRACT_VERSION = 1

CONTRACT_BASE_BY_SOURCE_KIND: Mapping[str, str] = {
    "ATTENTION_KV_VIEW": "attention_kv_view_bf16",
    "BIASED_TOPK_ROUTE": "selection_biased_topk_route_indices",
    "CANDIDATE_BLOCK_SELECT": "candidate_mask",
    "CANDIDATE_MASK_READ": "candidate_mask_view",
    "COMPRESSED_KV_VALID_VIEW": "compressed_kv_valid_view_bf16",
    "COMPRESS_KV_WRITE": "compressed_kv_write_bf16",
    #: The narrowing is the reference's own, named after it so that the
    #: implementation resolves without a frozen table entry.
    "BINARY32_TO_BF16": "conversion_binary32_tensor_to_bf16_rne",
    "COMPRESS_POOL": "compression_pool_compress_pool_f32",
    "COMPRESS_PROJECT": "compression_compress_project_bf16",
    "COMPRESS_STATE_UPDATE": "compression_state_compress_state_update_f32",
    "CONFIDENCE_SCORE": "confidence_score_bf16",
    "DSPARK_MAIN_PROJECT": "dspark_main_project_bf16",
    "DSPARK_NOISE_EMBED": "structural_dspark_noise_embed_bf16",
    "DSPARK_PREFILL_KV": "dspark_prefill_kv_bf16",
    "DSPARK_WINDOW_INDEX": "indexing_dspark_window_indices",
    #: THE RELEASE'S GATE, not the frozen v1 contract.  ``engram_gate_fp32_v1``
    #: differs from this release's own ``Engram.forward`` in four ways that all
    #: change the value -- ``engram_gate_pinned_divergences()`` enumerates them and
    #: ``prove_pinned_form_differs()`` runs both on one input and gets gates of
    #: 0.784 and 0.683.  Naming v1 here asked the device to compute a gate this
    #: model does not have, which is why the emitted token disagreed with the
    #: reference oracle while the V4-Flash token, whose path has no Engram at all,
    #: agreed with its own.  v1 is frozen ABI and is left alone; this names the
    #: contract whose implementation is the release's expression.
    "ENGRAM_GATE": "engram_gate_pinned_form",
    "ENGRAM_KV_PROJECT": "matrix_dense_fp8_linear_bf16",
    "ENGRAM_NGRAM_HASH": "ngram_hash_u32",
    "ENGRAM_ROW_LOOKUP": "lookup_engram_row_fp8_e4m3",
    "ENGRAM_TOKEN_COMPRESS": "lookup_compressed_token_ids",
    "EXPERT_DISPATCH": "dispatch_routed_experts_bf16",
    "EXPERT_REDUCE": "dispatch_reduce_expert_outputs_bf16",
    "FP4_INDEX_QDQ": "quantization_fp4_qdq_bf16",
    "FP4_MAIN_QDQ": "fp4_e2m1_s16_e4m3_to_fp8",
    "FP8_LINEAR": "matrix_dense_fp8_linear_bf16",
    "FP8_QDQ": "quantization_fp8_qdq_bf16",
    "FP8_SWIGLU": "fp8_swiglu_bf16",
    "GROUPED_OUTPUT_PROJECT": "grouped_output_project_bf16",
    "HC_EXPAND": "structural_hc_expand_bf16",
    "HC_FINAL_COLLAPSE": "hyper_connection_hc_collapse_bf16",
    "HC_POST": "vector_hc_post_bf16",
    "HC_PRE": "hyper_connection_hc_pre_bf16",
    #: The same contract the layer norms name; see ``FINAL_RMS_NORM``'s entry in
    #: the expansion table for why it is not the head norm's.
    "FINAL_RMS_NORM": "deepseek_rmsnorm_binary32",
    "INDEX_KEY_PROJECT": "matrix_bf16_linear_bf16",
    "INDEX_KEY_WRITE": "index_key_write_bf16",
    "INDEX_QUERY_PROJECT": "matrix_dense_fp8_linear_bf16",
    "INDEX_SCORE": "index_score_bf16",
    "INDEX_TOPK": "selection_index_topk_indices",
    "INDEX_WEIGHT_PROJECT": "matrix_bf16_linear_bf16",
    "KV_WINDOW_WRITE": "kv_window_write_bf16",
    "LM_HEAD": "lm_head_bf16",
    "MARKOV_AUTOREGRESSIVE_LOOP": "markov_loop_markov_autoregressive_loop_bf16",
    "MXFP4_SWIGLU": "mxfp4_swiglu_bf16",
    "RMS_NORM": "deepseek_rmsnorm_binary32",
    "ROPE_APPLY": "rope_apply_bf16",
    "ROPE_INVERSE": "rope_inverse_bf16",
    "ROUTER_SCORE": "routing_router_score_bf16",
    "ROUTER_WEIGHT_NORMALIZE": "routing_normalize_routed_weight_codes",
    "SAMPLE": "sampling_deepseek_v41_sample_binary32",
    "SHARED_INDEX_REUSE": "selection_shared_index_view",
    "SPARSE_ATTENTION": "sparse_attention_bf16",
    "SQRT_SOFTPLUS": "sqrt_softplus_router_binary32",
    "TARGET_HIDDEN_CAPTURE": "vector_target_hidden_capture_bf16",
    "TOKEN_EMBED": "lookup_bf16_token_embedding",
    "WINDOW_INDEX": "indexing_window_indices",
}


def contract_for(source_kind: str, step: str = "") -> str:
    """Return the canonical numeric-contract identity for one emitted kernel."""

    try:
        base = CONTRACT_BASE_BY_SOURCE_KIND[source_kind]
    except KeyError:
        raise DeepSeekV41KernelIRError(
            f"source kind {source_kind!r} has no frozen numeric contract"
        ) from None
    name = (
        f"{base}_{step}_v{CONTRACT_VERSION}"
        if step
        else f"{base}_v{CONTRACT_VERSION}"
    )
    if not CONTRACT_PATTERN.match(name):
        raise DeepSeekV41KernelIRError(
            f"numeric contract {name!r} is not a canonical identifier"
        )
    return name


# ---------------------------------------------------------------------------
# The per-layer source plan, and the census it implies
# ---------------------------------------------------------------------------
#: Source kinds every backbone layer emits, in released order, with the
#: attention mode's own kinds spliced in where ``inference/model.py`` runs them:
#: after the window KV is written and the window index is built, before the two
#: KV sources are concatenated for ``sparse_attn``.
_LAYER_PREFIX: tuple[str, ...] = (
    "HC_PRE",          # Block.hc_mixes + Block.hc_pre, attention branch
    "RMS_NORM",        # Block.attn_norm
    "FP8_LINEAR",      # Attention.wq_a
    "RMS_NORM",        # Attention.q_norm
    "FP8_LINEAR",      # Attention.wq_b
    "ROPE_APPLY",      # query rotation
    "FP8_LINEAR",      # Attention.wkv, the sliding-window KV
    "RMS_NORM",        # Attention.kv_norm
    "ROPE_APPLY",      # window KV rotation
    "FP8_QDQ",         # act_quant over the whole post-RoPE window vector
    "KV_WINDOW_WRITE",
    "WINDOW_INDEX",
)

_LAYER_SUFFIX: tuple[str, ...] = (
    "SPARSE_ATTENTION",
    "ROPE_INVERSE",              # the query rotation removed from the output
    "GROUPED_OUTPUT_PROJECT",    # wo_a block-diagonal over groups, then wo_b
    "HC_POST",
    "HC_PRE",                    # Block.hc_mixes + Block.hc_pre, FFN branch
    "RMS_NORM",                  # Block.ffn_norm
    "ROUTER_SCORE",
    "SQRT_SOFTPLUS",
    "BIASED_TOPK_ROUTE",
    "ROUTER_WEIGHT_NORMALIZE",
    "EXPERT_DISPATCH",
    "MXFP4_SWIGLU",
    "FP8_SWIGLU",                # the one shared expert every token runs
    "EXPERT_REDUCE",
    "HC_POST",
)

#: The Engram module runs before the block it is attached to
#: (``Transformer.forward``), and its row read needs the n-gram hash first.
_ENGRAM_LAYER_PREFIX: tuple[str, ...] = (
    "ENGRAM_NGRAM_HASH",
    "ENGRAM_ROW_LOOKUP",
    "ENGRAM_KV_PROJECT",
    "ENGRAM_GATE",
)


def layer_source_plan(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
    *,
    include_speculative: bool = False,
) -> tuple[tuple[str, ...], ...]:
    """Ordered source operator kinds for every layer the profile emits.

    Index ``i`` is layer ``i``.  With ``include_speculative`` the three DSpark
    stages are appended; their attention is ``DSparkAttention``, whose
    compression ratio the released ``compress_ratios`` tail states as zero, so
    they carry the window-only shape plus the draft block's own index.
    """

    modes = profile.layer_modes()
    engram_layers = frozenset(profile.engram_layers)
    target_layers = (
        frozenset(profile.target_layers) if include_speculative else frozenset()
    )
    #: A ratio-1 compressor is a plain projection: no softmax gate, so no
    #: pooled reduction and no partial-group state to carry across steps
    #: (``Compressor.forward``'s first branch, and ``Compressor.__init__``
    #: registers neither buffer).
    #: and therefore no binary32 latent to cast back either: ratio 1's ``wkv``
    #: is declared ``torch.bfloat16`` where ratio > 1 promotes it to fp32.
    pooled_only = ("COMPRESS_POOL", "COMPRESS_STATE_UPDATE", "BINARY32_TO_BF16")
    plan: list[tuple[str, ...]] = []
    for mode in modes:
        kinds: list[str] = []
        if mode.layer in engram_layers:
            kinds.extend(_ENGRAM_LAYER_PREFIX)
        if mode.layer in target_layers:
            kinds.append("TARGET_HIDDEN_CAPTURE")
        kinds.extend(_LAYER_PREFIX)
        attention = list(_ATTENTION_MODE_SOURCE_KINDS[mode.plan_key])
        if mode.ratio == 1:
            attention = [kind for kind in attention if kind not in pooled_only]
        if mode.is_candidate_source:
            # Level one of the two-level top-k runs on the scores, before the
            # layer's own selection reads them (``Indexer.forward``).
            attention.insert(
                attention.index("INDEX_SCORE") + 1, "CANDIDATE_BLOCK_SELECT"
            )
        kinds.extend(attention)
        kinds.extend(_LAYER_SUFFIX)
        plan.append(tuple(kinds))

    if not include_speculative:
        return tuple(plan)

    for stage, layer in enumerate(profile.draft_layers):
        kinds = []
        if stage == 0:
            kinds.append("DSPARK_MAIN_PROJECT")
        kinds.append("DSPARK_NOISE_EMBED")
        kinds.append("DSPARK_PREFILL_KV")
        kinds.extend(_LAYER_PREFIX)
        kinds.append("DSPARK_WINDOW_INDEX")
        kinds.extend(_LAYER_SUFFIX)
        if stage == profile.draft_stages - 1:
            kinds.extend(("HC_PRE", "RMS_NORM", "MARKOV_AUTOREGRESSIVE_LOOP",
                          "CONFIDENCE_SCORE"))
        plan.append(tuple(kinds))
    return tuple(plan)


#: Source kinds emitted once for the whole graph rather than per layer.
def unlayered_source_plan(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
) -> tuple[str, ...]:
    """Prologue and epilogue source kinds, in released order."""

    prologue: list[str] = ["TOKEN_EMBED"]
    if profile.engram_layers:
        # ``NgramHashState.forward`` maps the token ids through the compressed
        # table once for every Engram module, before any layer runs.
        prologue.append("ENGRAM_TOKEN_COMPRESS")
    prologue.append("HC_EXPAND")
    return tuple(prologue) + (
        "HC_FINAL_COLLAPSE",
        "FINAL_RMS_NORM",
        "LM_HEAD",
        "SAMPLE",
    )


def planned_census(
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
    *,
    include_speculative: bool = False,
) -> dict[str, Any]:
    """The census :func:`export_deepseek_v41_kernel_graph` must reproduce.

    A census of the plan, not of a document: it is a pure function of the
    released configuration, so it is checkable now and it is what the emitted
    graph is checked against once the checkpoint artifacts exist.  Its keys
    that :func:`compiler.frontends.v3.deepseek_v4.graph_census` also produces
    carry the same meaning, so the two can be compared directly.
    """

    kinds = source_kind_plan(profile, include_speculative=include_speculative)
    layers = layer_source_plan(profile, include_speculative=include_speculative)
    unlayered = unlayered_source_plan(profile)

    def expand(sources: Sequence[str]) -> Counter:
        counted: Counter = Counter()
        for source in sources:
            counted.update(kinds[source])
        return counted

    per_layer_kinds = [expand(sources) for sources in layers]
    per_layer_sources = [Counter(sources) for sources in layers]
    unlayered_kinds = expand(unlayered)
    total: Counter = Counter(unlayered_kinds)
    for item in per_layer_kinds:
        total.update(item)
    total_sources: Counter = Counter(unlayered)
    for item in per_layer_sources:
        total_sources.update(item)

    modes = profile.layer_modes()
    return {
        "attention_modes_by_layer": [mode.plan_key for mode in modes],
        "kernel_count": sum(total.values()),
        "kernels_by_kind": dict(sorted(total.items())),
        "layer_count": len(layers),
        "layers_by_attention_mode": dict(
            sorted(Counter(mode.plan_key for mode in modes).items())
        ),
        "model_id": profile.model_id,
        "per_layer_kernels_by_kind": [
            dict(sorted(item.items())) for item in per_layer_kinds
        ],
        "per_layer_source_kinds": [
            dict(sorted(item.items())) for item in per_layer_sources
        ],
        "source_kinds": dict(sorted(total_sources.items())),
        "unlayered_kernels_by_kind": dict(sorted(unlayered_kinds.items())),
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def missing_ir_artifacts(
    profile: DeepSeekV41Profile,
    snapshot: Path,
    checkpoint_lock_path: Path,
) -> list[str]:
    """Name every artifact a byte-pinned V4.1 graph needs and does not have.

    A kernel IR document binds each weight to a byte range in a shard, so it
    cannot be produced from a configuration alone.  Reporting all of them at
    once, each with the tool or work package that produces it, is the
    difference between a build that stops and a build that stops somewhere.
    """

    missing: list[str] = []
    if not snapshot.is_dir():
        missing.append(
            f"snapshot {snapshot} is absent; download {profile.repository} at "
            f"revision {profile.revision}"
        )
    else:
        index = snapshot / "model.safetensors.index.json"
        shards = sorted(snapshot.glob("model-*-of-*.safetensors"))
        if not index.is_file():
            missing.append(
                f"checkpoint index {index} is absent ({len(shards)} of "
                f"{profile.release.shard_count} shards present); it arrives with the "
                f"rest of the {profile.repository} snapshot at revision "
                f"{profile.revision}"
            )
        elif len(shards) < profile.release.shard_count:
            absent = sorted(
                name
                for name in json.loads(index.read_text())
                .get("weight_map", {})
                .values()
                if not (snapshot / name).is_file()
            )
            missing.append(
                f"{profile.release.shard_count - len(shards)} of "
                f"{profile.release.shard_count} shards have not arrived "
                f"({', '.join(sorted(set(absent))) or 'names unknown'}); the "
                f"{profile.repository} snapshot at revision {profile.revision} "
                "is still downloading"
            )
    if not profile.release.checkpoint_source_path.is_file():
        missing.append(
            f"checkpoint source contract {profile.release.checkpoint_source_path} "
            "is absent; produce it with tools/build_checkpoint_source.py against "
            "the complete snapshot and the committed registry listing"
        )
    if not profile.release.config_path.is_file():
        missing.append(
            f"committed official config {profile.release.config_path} is absent; "
            "tools/build_checkpoint_source.py writes the release's committed "
            "contract beside it"
        )
    if not checkpoint_lock_path.is_file():
        missing.append(
            f"checkpoint lock {checkpoint_lock_path} is absent; produce it with "
            "tools/build_checkpoint_lock.py, which reads all "
            f"{profile.release.payload_bytes:,} payload bytes once"
        )
    elif not profile.release.lock_identity_established:
        missing.append(
            f"no pinned lock identity for {profile.model_id}; record the lock's "
            "lock_id and tensor_content_sha256 on its release in "
            "compiler/frontend/deepseek_v4_releases.py"
        )
    return missing


def _nonempty(extent: Symbolic) -> str:
    """The ``execution_predicate`` of a kernel whose extent can floor to zero.

    Amendment A18's rule, in the V4 front end's own words: an extent that floors
    to zero is not a clamp, ABI 3.0 has no zero-extent view, so "the request has
    none of this axis" is a predicate question.  Every V4.1 kernel that leads
    with a compressed-group extent states it.
    """

    return f"{extent.symbol} > 0"


def export_deepseek_v41_kernel_graph(
    *,
    model: str | DeepSeekV41Profile = MODEL_ID,
    snapshot: Path | None = None,
    checkpoint_lock_path: Path | None = None,
    config_path: Path | None = None,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    maximum_new_tokens: int | None = None,
    include_speculative: bool = False,
) -> KernelGraph:
    """Export DeepSeek-V4.1-Flash as a neutral Tensor Kernel IR v3 graph.

    Everything that does not need a payload byte runs first and runs always:
    the released configuration is authenticated, every architecture pin is
    confronted with it, the deployment context is bounded, and the mode
    sequence is derived and confronted with the committed one.  The graph body
    then needs the checkpoint artifacts :func:`missing_ir_artifacts` names, and
    stops naming each one it does not have rather than emitting a document
    whose weights point nowhere.

    The lowering itself walks :func:`layer_source_plan` and
    :func:`unlayered_source_plan` **in order**, one handler per source operator
    kind, and refuses at the end unless the source kinds it emitted are the ones
    those two functions planned, layer by layer and in sequence.  That is what
    makes the plan and the document one description rather than two: a handler
    that quietly emitted a different mechanism, or a mode whose kinds drifted
    from the released id lists, is a build that stops.
    """

    profile = resolve_model_profile(model)
    release = profile.release
    snapshot = release.snapshot if snapshot is None else Path(snapshot)
    checkpoint_lock_path = (
        release.checkpoint_lock
        if checkpoint_lock_path is None
        else Path(checkpoint_lock_path)
    )

    capacity = architectural_max_context(profile)
    if context_tokens < 1 or context_tokens > capacity:
        raise DeepSeekV41KernelIRError(
            f"deployment context {context_tokens} is outside "
            f"{profile.model_id}'s architectural capacity 1..{capacity}"
        )
    if context_tokens % profile.sliding_window:
        raise DeepSeekV41KernelIRError(
            "deployment context must be a whole number of sliding windows"
        )
    if maximum_new_tokens is None:
        maximum_new_tokens = context_tokens
    if not 1 <= maximum_new_tokens <= context_tokens:
        raise DeepSeekV41KernelIRError(
            f"generation bound {maximum_new_tokens} is outside 1..{context_tokens}"
        )

    architecture = released_architecture_config(profile, config_path)
    validate_architecture_pins(profile, architecture)
    modes = confront_layer_modes(profile)
    source_digests = confront_source_digests(profile, snapshot)
    defects = plan_defects(profile)
    if defects:
        raise DeepSeekV41KernelIRError(
            f"the {profile.model_id} lowering plan is not a legal IR plan:\n  "
            + "\n  ".join(defects)
        )
    if include_speculative:
        raise DeepSeekV41KernelIRError(
            "the speculative profile is planned but not emitted: "
            + ", ".join(sorted(SPECULATIVE_SOURCE_KINDS))
            + " have no node-by-node lowering here, and the DSpark verification "
            "and acceptance contract is open (DSV4-SEM-001).  planned_census("
            "include_speculative=True) is the complete plan for them"
        )

    missing = missing_ir_artifacts(profile, snapshot, checkpoint_lock_path)
    if missing:
        raise DeepSeekV41KernelIRError(
            f"the {profile.model_id} kernel IR needs "
            f"{len(missing)} artifact{'s' if len(missing) > 1 else ''} that "
            "this host does not have:\n  " + "\n  ".join(missing)
        )

    root_config = load_official_config(path=config_path, release=release)
    specs = build_official_tensor_specs(root_config, release)
    try:
        lock = load_checkpoint_lock(checkpoint_lock_path)
    except CheckpointError as exc:
        raise DeepSeekV41KernelIRError(
            f"invalid {profile.model_id} checkpoint lock: {exc}"
        ) from exc
    if (
        lock["lock_id"] != release.checkpoint_lock_id
        or lock["checkpoint"]["tensor_count"] != release.tensor_count
        or lock["checkpoint"]["payload_bytes"] != release.payload_bytes
    ):
        raise DeepSeekV41KernelIRError(
            f"checkpoint lock is not the pinned {profile.model_id} release: "
            f"lock {lock['lock_id'][:16]} over "
            f"{lock['checkpoint']['tensor_count']} tensors and "
            f"{lock['checkpoint']['payload_bytes']} payload bytes against the "
            f"pinned {release.checkpoint_lock_id[:16]}, {release.tensor_count} "
            f"and {release.payload_bytes}"
        )
    bindings = read_checkpoint_bindings(snapshot, lock)
    if len(bindings) != release.tensor_count:
        raise DeepSeekV41KernelIRError(
            f"checkpoint headers describe {len(bindings)} tensors, expected "
            f"{release.tensor_count}"
        )

    # ------------------------------------------------------------------
    # Released widths, every one a read of the confronted configuration
    # ------------------------------------------------------------------
    HIDDEN = profile.hidden
    HC_MULT = profile.hc_mult
    HC_MIX = profile.hc_mix
    HC_COEFFICIENTS = profile.hc_coefficients
    HEADS = profile.heads
    HEAD_DIM = profile.head_dim
    ROPE_DIM = profile.rope_dim
    # No ``NOPE_DIM`` here: V4 quantizes the *unrotated* prefix of its window KV
    # and carries the rotated tail, so it needs the split; V4.1's
    # ``act_quant(kv, fp8_block_size, ..., True)`` covers the whole post-RoPE
    # vector, so the width is the head's.
    Q_RANK = profile.q_rank
    O_GROUPS = profile.o_groups
    O_RANK = profile.o_rank
    O_REDUCTION = HEADS * HEAD_DIM // O_GROUPS
    O_JOINED = O_GROUPS * O_RANK
    INDEX_HEADS = profile.index_heads
    INDEX_HEAD_DIM = profile.index_head_dim
    INDEX_TOPK_WIDTH = profile.index_topk
    VOCABULARY = profile.vocabulary
    ROUTED_EXPERTS = profile.routed_experts
    TOP_K = profile.top_k
    MOE_INTERMEDIATE = profile.moe_intermediate
    WINDOW = profile.sliding_window
    WEIGHT_BLOCK = profile.weight_scale_block
    ENGRAM_HEAD_DIM = profile.engram_head_dim
    ENGRAM_HEADS = profile.engram_heads
    ENGRAM_ORDERS = profile.engram_max_ngram - 1
    ENGRAM_COLUMNS = profile.engram_hash_columns
    ENGRAM_ROW_WIDTH = ENGRAM_COLUMNS * ENGRAM_HEAD_DIM
    CANDIDATE_BLOCK = profile.candidate_block
    CANDIDATE_BLOCKS = profile.candidate_blocks
    CANDIDATE_POOL = profile.candidate_pool_entries
    RMS_EPSILON = profile.rms_epsilon
    HC_EPSILON = profile.hc_epsilon
    ROUTE_SCALE = profile.route_scale
    SWIGLU_LIMIT = profile.swiglu_limit
    INDEX_SCORE_SCALE = INDEX_HEAD_DIM**-0.5 * INDEX_HEADS**-0.5
    BOS_TOKEN_ID = int(root_config["bos_token_id"])
    EOS_TOKEN_ID = int(root_config["eos_token_id"])
    ratios = profile.backbone_compress_ratios
    engram_layers = tuple(profile.engram_layers)
    kv_sources = tuple(profile.kv_source_layers)
    index_sources = tuple(profile.index_source_layers)

    def kv_owner(layer: int) -> int:
        """The layer whose compressed cache ``layer`` attends, released order.

        ``SharedAttentionRuntime`` holds one published latent and the layers run
        in order, so the owner of any layer is the last source before it -- which
        is what makes the CSA2 groups an *observation* about the id list rather
        than a table.
        """

        owners = [source for source in kv_sources if source <= layer]
        if not owners:
            raise DeepSeekV41KernelIRError(
                f"layer {layer} reads a compressed cache and no KV source "
                f"precedes it in {list(kv_sources)}"
            )
        return owners[-1]

    def index_owner(layer: int) -> int:
        owners = [source for source in index_sources if source <= layer]
        if not owners:
            raise DeepSeekV41KernelIRError(
                f"layer {layer} reuses an index selection and no index source "
                f"precedes it in {list(index_sources)}"
            )
        return owners[-1]

    # ------------------------------------------------------------------
    # Tensor specification index
    # ------------------------------------------------------------------
    spec_index: dict[tuple[str, int | None, str], list[TensorSpec]] = defaultdict(list)
    for spec in specs:
        spec_index[(spec.scope, spec.layer, spec.semantic_role)].append(spec)
    for group in spec_index.values():
        group.sort(key=lambda s: (-1 if s.expert is None else s.expert, s.name))
    scale_of: dict[str, TensorSpec] = {
        spec.scale_for: spec for spec in specs if spec.scale_for is not None
    }

    builder = _Builder()

    # ------------------------------------------------------------------
    # Runtime symbols and extents
    # ------------------------------------------------------------------
    # A18: every extent below is an affine image of one registered symbol.  A
    # ratio-1 axis is the *symbol itself* -- one compressed row per token -- so
    # this export declares a derived name only where the ratio makes one
    # necessary, which on this release is the ratio-2 encoder and the
    # eight-position candidate blocks.
    span = Symbolic("span_tokens", 1, context_tokens)
    context = Symbolic("context_length", 1, context_tokens)
    dispatch_rows = Symbolic("span_tokens", TOP_K, TOP_K * context_tokens)
    ratio_kinds = sorted({ratio for ratio in ratios if ratio > 1})

    def span_groups(ratio: int) -> Symbolic:
        if ratio == 1:
            return span
        return Symbolic(f"span_groups_ratio{ratio}", 1, context_tokens // ratio)

    def context_groups(ratio: int) -> Symbolic:
        if ratio == 1:
            return context
        return Symbolic(f"context_groups_ratio{ratio}", 1, context_tokens // ratio)

    def join_rows(ratio: int) -> Symbolic:
        """Rows of the fused KV view: the window beside the compressed prefix.

        The declared form is the prefill one, as V4's is: prefill joins the
        current request's window rows and its compressed prefix, so ratio 1 is
        ``2 * span`` -- expressible as a multiplier on the registered symbol and
        therefore not a new name -- and ratio 2 is ``3 * span / 2``, which is not.
        """

        if ratio == 1:
            return Symbolic("span_tokens", 2, 2 * context_tokens)
        return Symbolic(
            f"attention_rows_ratio{ratio}",
            1,
            context_tokens + context_tokens // ratio,
        )

    candidate_blocks_extent = Symbolic(
        f"context_groups_ratio{CANDIDATE_BLOCK}",
        1,
        context_tokens // CANDIDATE_BLOCK,
    )

    symbols: list[RuntimeSymbol] = [
        RuntimeSymbol("span_tokens", 1, context_tokens, 1, "request"),
        RuntimeSymbol("context_length", 1, context_tokens, 1, "request"),
    ]
    for ratio in ratio_kinds:
        symbols.extend(
            (
                RuntimeSymbol(
                    f"span_groups_ratio{ratio}", 0, context_tokens // ratio, 1, "derived"
                ),
                RuntimeSymbol(
                    f"context_groups_ratio{ratio}",
                    0,
                    context_tokens // ratio,
                    1,
                    "derived",
                ),
                RuntimeSymbol(
                    f"attention_rows_ratio{ratio}",
                    1,
                    context_tokens + context_tokens // ratio,
                    1,
                    "derived",
                ),
            )
        )
    if profile.candidate_source_layer >= 0:
        symbols.append(
            RuntimeSymbol(
                candidate_blocks_extent.symbol,
                0,
                context_tokens // CANDIDATE_BLOCK,
                1,
                "derived",
            )
        )

    # ------------------------------------------------------------------
    # Request inputs and deployment constants
    # ------------------------------------------------------------------
    token_ids = builder.tensor("input.token_ids", TOKEN_DTYPE, (span,), "input")
    position_offset = builder.tensor("input.position_offset", "i32", (1,), "input")
    session_ids = builder.tensor("input.session_ids", "u32", (1,), "input")
    entropy = builder.tensor(
        "input.entropy_stream", "fp32", (1, VOCABULARY), "input"
    )
    # IR3-GAP-1 unchanged from V4: ``sample()`` divides by an exponential draw
    # and takes the argmax, and no neutral kind produces or consumes randomness,
    # so the greedy branch is what is expressible, and the entropy stream is
    # declared and carried so a later graph can bind it.
    #
    # There is no ``sample.temperature`` *tensor*.  V4 declares one because its
    # frozen source graph names ``request.temperature_binary32`` as the SAMPLE
    # node's second input, and the tensor is where a reader looks for the pinned
    # number -- but no operator reads it, because a scalar an ABI 3.0 operator
    # scales by lives in the numeric descriptor's ``scale_bits``.  This front end
    # has no such contract to satisfy, so the constant is stated only where the
    # operator reads it, on the ``SCALE`` kernel below.  A declared constant that
    # nothing reads is precisely what the V4 export warns about for the unread
    # rotary profile: two backends may legally disagree about whether to place it.
    identity_pre = builder.tensor(
        "hyper_connection.identity_branch_weights",
        "fp32",
        (HC_MULT,),
        "constant",
        generator="one_hot_binary32_v1",
        generator_parameters={"count": HC_MULT, "index": 0},
    )

    rope_tables: dict[str, str] = {}
    for rope_profile, theta, scaling in (
        ("base", float(architecture["rope_theta"]), "none"),
        ("yarn", float(architecture["compress_rope_theta"]), "yarn"),
    ):
        reads = any((ratio > 0) == (rope_profile == "yarn") for ratio in ratios)
        if not reads:
            continue
        parameters: dict[str, Any] = {
            "maximum_position": context_tokens,
            "position_scaling": scaling,
            "rotary_width": ROPE_DIM,
            "theta": theta,
        }
        if scaling == "yarn":
            scaling_config = architecture["rope_scaling"]
            parameters.update(
                {
                    "beta_fast": int(scaling_config["beta_fast"]),
                    "beta_slow": int(scaling_config["beta_slow"]),
                    "factor": float(scaling_config["factor"]),
                    "original_max_position": int(
                        scaling_config["original_max_position_embeddings"]
                    ),
                }
            )
        rope_tables[rope_profile] = builder.tensor(
            f"rope.coefficient_table.{rope_profile}",
            "fp32",
            (context_tokens, 2 * ROPE_DIM),
            "constant",
            generator="deepseek_rope_coefficients_v1",
            generator_parameters=parameters,
        )

    ratio_constants: dict[int, str] = {}

    def ratio_constant(value: int) -> str:
        """Amendment A19's compression-ratio operand of ``ROUTE.INDEX_TOPK``."""

        name = f"index.compression_ratio.{value}"
        if name not in ratio_constants:
            ratio_constants[name] = builder.tensor(
                name,
                "u32",
                (1,),
                "constant",
                generator="constant_u32_v1",
                generator_parameters={"value": value, "count": 1},
            )
        return name

    # ------------------------------------------------------------------
    # Weights
    # ------------------------------------------------------------------
    def declare_weight(spec: TensorSpec) -> str:
        if builder.has_tensor(spec.name):
            return spec.name
        binding = bindings.get(spec.name)
        if binding is None:
            raise DeepSeekV41KernelIRError(
                f"checkpoint has no payload for {spec.name!r}"
            )
        if binding.bytes != spec.size_bytes:
            raise DeepSeekV41KernelIRError(
                f"{spec.name!r} byte length differs from the derived contract"
            )
        dtype = _STORAGE_DTYPE[spec.storage_dtype]
        shape: tuple[int, ...] = tuple(spec.shape)
        if spec.logical_dtype == "MXFP4_E2M1_X2":
            dtype = "mxfp4_e2m1"
            shape = (spec.shape[0], spec.shape[1] * 2)
        scale_spec = scale_of.get(spec.name)
        scale_id: str | None = None
        block = 0
        if scale_spec is not None:
            scale_id = declare_weight(scale_spec)
            block = FP4_INDEX_BLOCK if dtype == "mxfp4_e2m1" else WEIGHT_BLOCK
        return builder.tensor(
            spec.name,
            dtype,
            shape,
            "weight",
            binding=binding,
            scale_tensor_id=scale_id,
            scale_block_elements=block,
        )

    def role_specs(role: str, layer: int | None) -> list[TensorSpec]:
        for key in (("main", layer, role), ("global", None, role)):
            if key in spec_index:
                return spec_index[key]
        raise DeepSeekV41KernelIRError(
            f"role {role!r} has no tensor at layer {layer!r}"
        )

    def role_weight(role: str, layer: int | None = None) -> str:
        found = role_specs(role, layer)
        if len(found) != 1:
            raise DeepSeekV41KernelIRError(
                f"role {role!r} resolves to {len(found)} tensors, expected one"
            )
        return declare_weight(found[0])

    group_weights: dict[tuple[str, int], str] = {}

    def group_weight(spec: TensorSpec, group: int, groups: int) -> str:
        """One group's rows of the block-diagonal output projection.

        Exactly the V4 mechanism: a group of a row-major ``[groups * rank, ..]``
        tensor is a contiguous byte range, so each group is an ordinary binding
        whose digest is derived in one sequential pass and accepted only when the
        groups reassemble to the locked whole-tensor SHA-256.
        """

        key = (spec.name, group)
        if key in group_weights:
            return group_weights[key]
        binding = bindings.get(spec.name)
        if binding is None:
            raise DeepSeekV41KernelIRError(
                f"checkpoint has no payload for {spec.name!r}"
            )
        ranges = split_binding_by_leading_groups(
            snapshot, binding, groups, int(spec.shape[0])
        )
        scale_spec = scale_of.get(spec.name)
        scale_ranges: Sequence[CheckpointBinding] = ()
        if scale_spec is not None:
            scale_binding = bindings.get(scale_spec.name)
            if scale_binding is None:
                raise DeepSeekV41KernelIRError(
                    f"checkpoint has no payload for {scale_spec.name!r}"
                )
            scale_ranges = split_binding_by_leading_groups(
                snapshot, scale_binding, groups, int(scale_spec.shape[0])
            )
        dtype = _STORAGE_DTYPE[spec.storage_dtype]
        rows = int(spec.shape[0]) // groups
        for index in range(groups):
            member = (spec.name, index)
            if member in group_weights:
                continue
            scale_id: str | None = None
            block = 0
            if scale_spec is not None:
                scale_id = builder.tensor(
                    f"{scale_spec.name}.group{index}",
                    _STORAGE_DTYPE[scale_spec.storage_dtype],
                    (int(scale_spec.shape[0]) // groups, int(scale_spec.shape[1])),
                    "weight",
                    binding=scale_ranges[index],
                )
                block = WEIGHT_BLOCK
            group_weights[member] = builder.tensor(
                f"{spec.name}.group{index}",
                dtype,
                (rows, int(spec.shape[1])),
                "weight",
                binding=ranges[index],
                scale_tensor_id=scale_id,
                scale_block_elements=block,
            )
        return group_weights[key]

    def _stacked_id(spec: TensorSpec) -> str:
        parts = spec.name.split(".")
        marker = str(spec.expert)
        for index in range(len(parts) - 1, -1, -1):
            if parts[index] == marker:
                del parts[index]
                break
        else:  # pragma: no cover - the family is expert-indexed by construction
            raise DeepSeekV41KernelIRError(
                f"{spec.name!r} carries no expert index to stack over"
            )
        return ".".join(parts)

    def _stack_binding(
        tensor_id: str, members: Sequence[TensorSpec]
    ) -> CheckpointBinding:
        """One segmented binding over an ordered family of checkpoint ranges.

        IR3-GAP-3's resolution, unchanged: ``TENSOR.ROUTED_MATMUL``'s weight slot
        is a mandatory operand, the released checkpoint interleaves a layer's
        experts, and a segmented binding is how one operand names many
        authenticated ranges in ascending logical expert order.
        """

        segments: list[BindingSegment] = []
        for member in members:
            binding = bindings.get(member.name)
            if binding is None:
                raise DeepSeekV41KernelIRError(
                    f"checkpoint has no payload for {member.name!r}"
                )
            if binding.bytes != member.size_bytes:
                raise DeepSeekV41KernelIRError(
                    f"{member.name!r} byte length differs from the derived contract"
                )
            segments.append(
                BindingSegment(
                    source_name=binding.source_name,
                    path=binding.path,
                    offset=binding.offset,
                    bytes=binding.bytes,
                    sha256=binding.sha256,
                )
            )
        digest = hashlib.sha256()
        for segment in segments:
            digest.update(bytes.fromhex(segment.sha256))
        return CheckpointBinding(
            source_name=tensor_id,
            path=segments[0].path,
            offset=segments[0].offset,
            bytes=sum(segment.bytes for segment in segments),
            sha256=digest.hexdigest(),
            transform="identity",
            segments=tuple(segments),
        )

    def role_weight_stack(role: str, layer: int) -> str:
        members = role_specs(role, layer)
        if len(members) < 2 or any(member.expert is None for member in members):
            raise DeepSeekV41KernelIRError(
                f"role {role!r} at layer {layer} is not an expert-indexed family"
            )
        tensor_id = _stacked_id(members[0])
        if builder.has_tensor(tensor_id):
            return tensor_id
        head = members[0]
        dtype = _STORAGE_DTYPE[head.storage_dtype]
        member_shape: tuple[int, ...] = tuple(head.shape)
        if head.logical_dtype == "MXFP4_E2M1_X2":
            dtype = "mxfp4_e2m1"
            member_shape = (head.shape[0], head.shape[1] * 2)
        if any(tuple(m.shape) != tuple(head.shape) for m in members):
            raise DeepSeekV41KernelIRError(
                f"expert family {tensor_id!r} is not uniformly shaped"
            )
        scale_id: str | None = None
        block = 0
        scale_members = [scale_of[m.name] for m in members if m.name in scale_of]
        if scale_members:
            if len(scale_members) != len(members):
                raise DeepSeekV41KernelIRError(
                    f"expert family {tensor_id!r} is partially block-scaled"
                )
            scale_id = _stacked_id(scale_members[0])
            scale_head = scale_members[0]
            builder.tensor(
                scale_id,
                _STORAGE_DTYPE[scale_head.storage_dtype],
                (len(scale_members), *scale_head.shape),
                "weight",
                binding=_stack_binding(scale_id, scale_members),
            )
            block = FP4_INDEX_BLOCK if dtype == "mxfp4_e2m1" else WEIGHT_BLOCK
        return builder.tensor(
            tensor_id,
            dtype,
            (len(members), *member_shape),
            "weight",
            binding=_stack_binding(tensor_id, members),
            scale_tensor_id=scale_id,
            scale_block_elements=block,
        )

    # ------------------------------------------------------------------
    # Emission
    # ------------------------------------------------------------------
    emitted_layer_sources: list[list[str]] = [[] for _ in modes]
    emitted_unlayered_sources: list[str] = []
    current: dict[str, Any] = {"layer": None, "kind": "", "op": ""}

    def act(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "activation")

    def view(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "state")

    def start(source_kind: str, leaf: str, layer: int | None) -> str:
        """Open one source operation, recording it in the emission sequence."""

        if layer is None:
            emitted_unlayered_sources.append(source_kind)
            op = f"main.{leaf}"
        else:
            emitted_layer_sources[layer].append(source_kind)
            op = f"main.layer{layer:02d}.{leaf}"
        current.update({"layer": layer, "kind": source_kind, "op": op})
        return op

    def emit(
        kernel_id: str,
        kind: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        *,
        step: str = "",
        iteration_domain: Mapping[str, Any],
        attributes: Mapping[str, Any] | None = None,
        phases: Sequence[str] = ("prefill", "decode"),
        state_reads: Sequence[str] = (),
        state_writes: Sequence[str] = (),
    ) -> None:
        source_kind = current["kind"]
        try:
            builder.kernel(
                kernel_id,
                kind,
                inputs,
                outputs,
                numeric_contract=contract_for(source_kind, step),
                iteration_domain=iteration_domain,
                attributes={
                    **(dict(attributes) if attributes else {}),
                    "source_operation_kind": source_kind,
                },
                source_operation_id=current["op"],
                source_kind=source_kind,
                phases=phases,
                layer=current["layer"],
                state_reads=state_reads,
                state_writes=state_writes,
            )
        except DeepSeekV4KernelIRError as exc:
            # The shared accumulator owns the arity gate, the join checks and the
            # counter-class table, and it raises the V4 front end's error.  A
            # caller of this export gets one error type, so a build that stops
            # says which kernel rather than which module.
            raise DeepSeekV41KernelIRError(f"{kernel_id}: {exc}") from exc

    states: dict[str, StateResource] = {}

    def ensure_state(resource: StateResource) -> str:
        states.setdefault(resource.state_id, resource)
        return builder.state(states[resource.state_id])

    def window_state(layer: int) -> str:
        return ensure_state(
            StateResource(
                state_id=f"attention_window.main.layer.{layer}",
                state_class="kv_window",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=WINDOW,
                initialization="zero",
            )
        )

    def compressed_state(layer: int) -> str:
        return ensure_state(
            StateResource(
                state_id=f"compressed_key_value.main.layer.{layer}",
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=context_tokens // ratios[layer],
                initialization="zero",
            )
        )

    def compressor_state(layer: int, plane: str) -> str:
        return ensure_state(
            StateResource(
                state_id=f"compressor_window_{plane}.main.layer.{layer}",
                state_class="compressor_window",
                dtype="fp32",
                row_elements=HEAD_DIM,
                capacity_rows=ratios[layer],
                initialization="zero" if plane == "kv" else "negative_infinity",
            )
        )

    def index_key_state(layer: int) -> str:
        return ensure_state(
            StateResource(
                state_id=f"index_key_value.main.layer.{layer}",
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=INDEX_HEAD_DIM,
                capacity_rows=context_tokens // ratios[layer],
                initialization="zero",
            )
        )

    def index_selection_state(layer: int) -> str:
        # The published selection of one index source, read by every Reuse layer
        # that follows it.  ``scratch`` rather than a cache class: it is derived
        # per query row and lives for the query block, which is what makes plan
        # section 6.1's locality rule a *placement* clause -- every reader is on
        # the node that owns it -- rather than a residency one.
        #
        # THE QUERY BLOCK IS THE CAPACITY, and the sentence above is why.  This
        # was ``capacity_rows = 1``, which is one query ROW, and it only looks
        # right for decode.  A backend that bands by layer runs the whole query
        # block through this kernel before the next layer reads any of it, so a
        # one-row store keeps the last token's selection and every Reuse layer
        # reads a selection that is not its own.  The HBM lowering said so ten
        # times over -- ``view 2904: maximum element 18447 needs 73792 bytes but
        # object 1638 is 9216 bytes`` -- once a state-resident operand could be
        # bound at all.  ``span.maximum`` is ``context_tokens``, so this is the
        # block the schedule actually presents.
        return ensure_state(
            StateResource(
                state_id=f"index_selection.main.layer.{layer}",
                state_class="scratch",
                dtype="u32",
                row_elements=WINDOW + INDEX_TOPK_WIDTH,
                capacity_rows=context_tokens,
                initialization="zero",
            )
        )

    def candidate_mask_state(layer: int) -> str:
        return ensure_state(
            StateResource(
                state_id=f"candidate_pool_mask.main.layer.{layer}",
                state_class="scratch",
                dtype="u8",
                row_elements=context_tokens // ratios[layer],
                # The query block, for the reason index_selection_state gives.
                capacity_rows=context_tokens,
                initialization="zero",
            )
        )

    def quantize(
        source: str,
        *,
        block: int,
        dtype: str,
        width: int | None,
        contract: str,
        attributes: Mapping[str, Any],
        name: str,
    ) -> tuple[str, str]:
        """Quantize one activation for one consumer.

        Deliberately *not* shared between consumers, unlike the V4 export's:
        ``Linear.forward`` calls ``act_quant`` on its own input every time it
        runs, so the released model quantizes the attention norm's output twice
        -- once for ``wq_a`` and once for ``wkv`` -- and a graph that quantized
        it once would be a graph of a different kernel sequence.  The two
        results are bit-identical, which is why this is a fidelity question and
        not a correctness one; the lowering plan counts one per consumer.
        """

        shape = builder.shape[source]
        full_width = int(shape[-1])
        if width is None:
            width = full_width
        if width % block:
            raise DeepSeekV41KernelIRError(
                f"{source!r} width {width} is not a whole number of {block}-blocks"
            )
        #: THE SCALE'S DTYPE IS THE CALLER'S DECLARED ``scale_format``, not a
        #: constant.  ``fp4_act_quant``'s own docstring is "FP4 with E8M0 scales
        #: for the indexer or E4M3 scales for compressed KV", and both call sites
        #: already state which they are -- but this helper wrote ``e8m0`` for both,
        #: so the main latent carried E2M1 codes beside an E8M0 scale.  That pair
        #: IS MXFP4_E2M1: the scale format is what distinguishes it from
        #: FP4_E2M1_S16_E4M3, so the declaration and the storage disagreed and the
        #: quantiser refused the operand.  Deriving it from the attribute the
        #: caller already writes makes the two impossible to separate.
        scale_format = str(attributes.get("scale_format") or "")
        scale_dtypes = {"e4m3": "fp8_e4m3fn", "e8m0": "e8m0", "ue8m0": "e8m0"}
        if scale_format not in scale_dtypes:
            raise DeepSeekV41KernelIRError(
                f"{name!r} declares scale_format {scale_format!r}; a block "
                f"quantizer states one of {sorted(scale_dtypes)}"
            )
        scale = act(
            f"{name}.scale", scale_dtypes[scale_format], (*shape[:-1], width // block)
        )
        payload = builder.tensor(
            f"{name}.payload",
            dtype,
            (*shape[:-1], width),
            "activation",
            scale_tensor_id=scale,
            scale_block_elements=block,
        )
        emit(
            name,
            "QUANTIZE",
            (source,),
            (payload, scale),
            step="quantize",
            iteration_domain={"rows": shape[0], "width": width, "block": block},
            attributes=dict(attributes),
        )
        return payload, scale

    def rope_attributes(ratio: int, *, inverse: bool) -> dict[str, Any]:
        if ratio:
            scaling = architecture["rope_scaling"]
            return {
                "beta_fast": int(scaling["beta_fast"]),
                "beta_slow": int(scaling["beta_slow"]),
                "factor": float(scaling["factor"]),
                "inverse": inverse,
                "original_max_position": int(
                    scaling["original_max_position_embeddings"]
                ),
                "position_scaling": "yarn",
                "rotary_width": ROPE_DIM,
                "theta": float(architecture["compress_rope_theta"]),
            }
        return {
            "inverse": inverse,
            "position_scaling": "none",
            "rotary_width": ROPE_DIM,
            "theta": float(architecture["rope_theta"]),
        }

    rope_coefficients: dict[str, str] = {}

    def rope_apply(
        op: str,
        source: str,
        *,
        ratio: int,
        rows: Any,
        group_stride: int = 0,
        predicate: str = "",
    ) -> str:
        """``ROPE_APPLY``: the coefficient rows this rotation reads, then the rotation.

        A compressed rotation strides the table by the compression ratio, because
        a latent stands for the first token of its group; every other rotation
        reads one row per token.  The gather is the plan's first kind and it is
        emitted per rotation rather than shared, which is what lets the two
        cases differ without a second source kind.
        """

        table = rope_tables["yarn" if ratio else "base"]
        coefficients = act(f"{op}.coefficient_rows", "fp32", (rows, 2 * ROPE_DIM))
        gather_attributes: dict[str, Any] = {
            "coefficient_layout": "cos_rotary_width_then_sin_rotary_width",
            "pair_layout": "adjacent_complex",
            "rotary_width": ROPE_DIM,
            "selector": "input.position_offset",
        }
        if group_stride:
            gather_attributes["position_stride"] = group_stride
        if predicate:
            gather_attributes["execution_predicate"] = predicate
        emit(
            f"{op}.coefficient_gather",
            "GATHER",
            (position_offset, table),
            (coefficients,),
            step="coefficient_rows",
            iteration_domain={"rows": rows, "width": 2 * ROPE_DIM},
            attributes=gather_attributes,
        )
        rope_coefficients[op] = coefficients
        shape = builder.shape[source]
        rotated = act(f"{op}.rotated", "bf16", shape)
        attributes = rope_attributes(ratio, inverse=False)
        if predicate:
            attributes["execution_predicate"] = predicate
        emit(
            f"{op}.rotate",
            "ROPE",
            (source, coefficients),
            (rotated,),
            step="rotate",
            iteration_domain={"rows": shape[0], "width": ROPE_DIM},
            attributes=attributes,
        )
        return rotated

    def fp8_linear(
        leaf: str,
        source: str,
        weight_role: str,
        *,
        layer: int | None,
        out_shape: tuple[Any, ...],
        attributes: Mapping[str, Any] | None = None,
    ) -> str:
        op = start("FP8_LINEAR", leaf, layer)
        weight = role_weight(weight_role, layer)
        out_features, in_features = builder.shape[weight]
        payload, _ = quantize(
            source,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("FP8_LINEAR", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
                "scale_selection": "bit_ceiling_power_of_two",
            },
            name=f"{op}.quantized_input",
        )
        rows = builder.shape[source][0]
        output = act(f"{op}.projection", "bf16", out_shape)
        emit(
            f"{op}.contract",
            "MATMUL",
            (payload, weight),
            (output,),
            step="block_scaled_contraction",
            iteration_domain={
                "rows": rows,
                "output_width": out_features,
                "reduction_width": in_features,
            },
            attributes={
                **(dict(attributes) if attributes else {}),
                "accumulator_dtype": "fp32",
                "activation_block_elements": ACTIVATION_BLOCK,
                "input_dtype": "fp8_e4m3fn",
                "output_dtype": "bf16",
                "reduction_order": "increasing_reduction_index",
                "transpose_weight": True,
                "weight_block_elements": WEIGHT_BLOCK,
            },
        )
        return output

    def rms_norm(
        leaf: str,
        source: str,
        weight_role: str,
        *,
        layer: int | None,
        predicate: str = "",
    ) -> str:
        op = start("RMS_NORM", leaf, layer)
        weight = role_weight(weight_role, layer)
        shape = builder.shape[source]
        output = act(f"{op}.normalized", "bf16", shape)
        attributes: dict[str, Any] = {"epsilon": RMS_EPSILON}
        if predicate:
            # A18, and the V4 export's rule that a repeated declaration is
            # checkable where an inference from a neighbour is not: a norm over a
            # compressed group leads with an extent that floors to zero, so it
            # says when it must not be issued even though the operator that feeds
            # it says the same thing.
            attributes["execution_predicate"] = predicate
        emit(
            op,
            "RMS_NORM",
            (source, weight),
            (output,),
            iteration_domain={"rows": shape[0], "width": int(shape[-1])},
            attributes=attributes,
        )
        return output

    def hyper_connection_pre(
        leaf: str, stream: str, carried: str, branch: str, layer: int
    ) -> tuple[str, str, str, str]:
        """``Block.hc_mixes`` then ``Block.hc_pre``.

        The coefficients a sublayer computes are used by the *next* one, so the
        reduction that collapses the copies reads ``carried`` -- the previous
        sublayer's branch weights -- while the operator computes this
        sublayer's, which the next one will read.  Emitting the collapse against
        this kernel's own output would shift every coefficient one sublayer
        early and nothing downstream would notice.
        """

        op = start("HC_PRE", leaf, layer)
        projection = role_weight(f"hyper_connection.{branch}.projection", layer)
        scale = role_weight(f"hyper_connection.{branch}.scale", layer)
        base = role_weight(f"hyper_connection.{branch}.base", layer)
        planes = act(f"{op}.weights", "fp32", (span, 2, HC_MULT))
        combination = act(f"{op}.combination", "fp32", (span, HC_MULT, HC_MULT))
        emit(
            op,
            "HYPER_CONNECT_PRE",
            (stream, projection, scale, base),
            (planes, combination),
            iteration_domain={
                "tokens": span,
                "hyper_streams": HC_MULT,
                "width": HIDDEN,
                "mix_width": HC_MIX,
            },
            attributes={
                "coefficient_layout": "pre_then_post",
                "coefficient_width": HC_COEFFICIENTS,
                "combination_width": HC_MULT * HC_MULT,
                "epsilon": RMS_EPSILON,
                "hyper_connection_epsilon": HC_EPSILON,
                "mix_width": HC_MIX,
                "post_width": HC_MULT,
                "sinkhorn_iterations": profile.hc_sinkhorn_iterations,
            },
        )
        pre = act(f"{op}.branch_weights", "fp32", (span, HC_MULT))
        emit(
            f"{op}.branch_plane",
            "SELECT",
            (planes,),
            (pre,),
            step="branch_weight_plane",
            iteration_domain={"tokens": span, "hyper_streams": HC_MULT},
            attributes={"axis": 1, "index": 0, "plane": "branch_weight"},
        )
        post = act(f"{op}.residual_weights", "fp32", (span, HC_MULT))
        emit(
            f"{op}.residual_plane",
            "SELECT",
            (planes,),
            (post,),
            step="residual_weight_plane",
            iteration_domain={"tokens": span, "hyper_streams": HC_MULT},
            attributes={"axis": 1, "index": 1, "plane": "residual_weight"},
        )
        collapsed = act(f"{op}.collapsed", "bf16", (span, HIDDEN))
        emit(
            f"{op}.collapse",
            "EXPERT_REDUCE",
            (stream, carried),
            (collapsed,),
            step="branch_collapse",
            iteration_domain={
                "tokens": span,
                "hyper_streams": HC_MULT,
                "width": HIDDEN,
            },
            attributes={
                "contribution_row_order": "ascending_hyper_stream",
                "reduction_axis": 1,
                "reduction_order": "pairwise_tree",
                "routing_weight_application": "applied_at_the_reduction",
                "stream_count": HC_MULT,
                "weight_source": (
                    "the previous sublayer's branch weights, one deployment "
                    "constant at the first"
                ),
            },
        )
        return collapsed, pre, post, combination

    def hyper_connection_post(
        leaf: str, branch: str, residual: str, post: str, combination: str, layer: int
    ) -> str:
        op = start("HC_POST", leaf, layer)
        output = act(f"{op}.stream", "bf16", (span, HC_MULT, HIDDEN))
        emit(
            op,
            "HYPER_CONNECT_POST",
            (branch, residual, post, combination),
            (output,),
            iteration_domain={
                "tokens": span,
                "hyper_streams": HC_MULT,
                "width": HIDDEN,
            },
            attributes={
                "coefficient_layout": "post_and_combination_are_separate",
                "combination_width": HC_MULT * HC_MULT,
                "post_width": HC_MULT,
            },
        )
        return output

    # ------------------------------------------------------------------
    # Prologue
    # ------------------------------------------------------------------
    op = start("TOKEN_EMBED", "token_embedding", None)
    embedded = act(f"{op}.hidden", "bf16", (span, HIDDEN))
    emit(
        op,
        "EMBEDDING_LOOKUP",
        (token_ids, role_weight("model.token_embedding.weight")),
        (embedded,),
        iteration_domain={"tokens": span, "width": HIDDEN},
        attributes={"table_rows": VOCABULARY},
    )

    compressed_ids = ""
    if engram_layers:
        op = start("ENGRAM_TOKEN_COMPRESS", "compressed_token_ids", None)
        compressed_map = builder.tensor(
            "engram.compressed_token_map",
            "u32",
            (VOCABULARY,),
            "constant",
            generator="engram_compressed_token_map_v1",
            generator_parameters={
                "compressed_vocabulary": profile.engram_compressed_vocabulary,
                "repository": profile.repository,
                "revision": profile.revision,
                "tokenizer_file": "tokenizer.json",
                "tokenizer_sha256": release.tokenizer_sha256,
                "vocabulary": VOCABULARY,
            },
        )
        # The look-back of an n-gram reaches positions the current span does not
        # hold, so the compressed ids are a session resource -- ``NgramHashState``
        # keeps exactly this buffer -- and the lookup commits the span's own
        # positions into it.  The declared view is the resource; the rows written
        # are the request's, as for every other append in this graph.
        #: EXTENTED BY THE REQUEST, not by the resource.  The buffer's capacity is
        #: the whole context, but what a transaction has committed is
        #: ``context_length`` ids -- and ``DMA.NGRAM_HASH`` downstream emits one
        #: row per position of the sequence it is given, so a view presenting all
        #: 128 ring rows asked it to hash 128 positions for an 8-token prompt.
        #: That was the trap the first token died on, and it is the last of them.
        compressed_ids = view(
            f"{op}.committed",
            "u32",
            (Symbolic("context_length", 1, context_tokens),),
        )
        emit(
            op,
            "EMBEDDING_LOOKUP",
            (token_ids, compressed_map),
            (compressed_ids,),
            iteration_domain={"tokens": span, "width": 1},
            attributes={
                "committed_row": "absolute_position",
                "table_rows": VOCABULARY,
                "table_value_maximum": profile.engram_compressed_vocabulary - 1,
            },
            state_writes=(
                ensure_state(
                    StateResource(
                        state_id="compressed_token_ids.main.layer.0",
                        state_class="token_ring",
                        dtype="u32",
                        row_elements=1,
                        capacity_rows=context_tokens,
                        initialization="zero",
                    )
                ),
            ),
        )

    op = start("HC_EXPAND", "hyper_connection_expand", None)
    stream = act(f"{op}.stream", "bf16", (span, HC_MULT, HIDDEN))
    emit(
        op,
        "BROADCAST",
        (embedded,),
        (stream,),
        iteration_domain={"tokens": span, "hyper_streams": HC_MULT, "width": HIDDEN},
        attributes={
            "axis": 1,
            "extent": HC_MULT,
            "source_replication": "single_embedding",
        },
    )

    carried_pre = identity_pre
    published_selection: dict[int, str] = {}
    published_mask: dict[int, str] = {}
    published_index_key: dict[int, str] = {}
    published_compressed: dict[int, str] = {}

    # ------------------------------------------------------------------
    # The forty backbone layers
    # ------------------------------------------------------------------
    for mode in modes:
        layer = mode.layer
        ratio = mode.ratio
        groups = span_groups(ratio) if ratio else None
        committed = context_groups(ratio) if ratio else None
        # Every kernel of the compressed path AFTER the carry runs exactly when
        # the carry says the group completed, so each names the carry's computed
        # predicate rather than restating a comparison.
        #
        # The comparison this used to be, ``span_groups_ratioN > 0``, is the
        # PREFILL condition only.  During decode ``span_tokens`` is one and
        # ``span_groups_ratio2`` is zero, so a chain predicated on it never fires
        # on the step that has something to pool -- the decode boundary -- and
        # the released compressor pools exactly there
        # (``should_compress = (start_pos + 1) % ratio == 0``).  Naming the
        # carry's predicate is also what makes a backend treat these kernels as
        # the carry's consumers: the ROM lane then emits the two-phase chain and
        # orders it on the carry's own events, where a symbol comparison left the
        # pool reading the histories the carry had not finished writing.
        group_predicate = (
            f"main.layer{layer:02d}.attention.compressor.carry.should_compress"
            if ratio > 1 and mode.kv_owner
            else ""
        )
        committed_predicate = _nonempty(committed) if ratio > 1 else ""

        # -- Engram, ahead of the block it is attached to ----------------
        if layer in engram_layers:
            table_spec = role_specs("engram.table.weight", layer)[0]
            op = start("ENGRAM_NGRAM_HASH", "engram.ngram_hash", layer)
            multipliers = builder.tensor(
                f"layers.{layer}.engram.hash_multipliers",
                "u64",
                (profile.engram_max_ngram,),
                "constant",
                generator="engram_hash_multipliers_v1",
                generator_parameters={
                    "compressed_vocabulary": profile.engram_compressed_vocabulary,
                    "count": profile.engram_max_ngram,
                    "layer_id": layer,
                },
            )
            columns = builder.tensor(
                f"layers.{layer}.engram.hash_columns",
                "u64",
                (2, ENGRAM_ORDERS, ENGRAM_HEADS),
                "constant",
                generator="engram_hash_columns_v1",
                generator_parameters={
                    "bucket_base": profile.engram_bucket_base,
                    "heads": ENGRAM_HEADS,
                    "layer_id": layer,
                    "layer_ids": list(engram_layers),
                    "orders": ENGRAM_ORDERS,
                },
            )
            # THE LOOKBACK BELONGS TO NGRAM_HASH, NOT TO A MOVEMENT AHEAD OF IT.
            # This used to emit a GATHER producing a (span, max_ngram) lookback
            # window and feed that window to NGRAM_HASH.  Three independent
            # authorities say the operator owns the lookback instead:
            #
            #   * rtl/abi3/ot_a3_dma_ngram_hash.sv declares its IR kind as
            #     ``NGRAM_HASH(token_ids, order, head) -> row_ids`` and computes
            #     "t_j = pad_id when the lookback is blocked, else the compressed
            #     id" itself, fully pipelined at II 1;
            #   * runtime/sim/engines/dma.py requires
            #     ``id_view.element_count == positions`` -- one token id per
            #     output position, not a window per position; and
            #   * runtime.reference.engram.ngram_row_ids, the contract's own
            #     authority, takes ``token_ids`` and forms ``compressed[p - j]``
            #     with the sticky blocked rule internally.
            #
            # And the window was not expressible as a movement in any case: the
            # lookback runs *descending* (t_0 is position p, t_1 is p-1) while a
            # tensor view's strides are unsigned, and a blocked lookback
            # substitutes a pad rather than addressing anything.  V4.1 refused at
            # PC 241 with "DMA.GATHER output view dims (1, 4) differ from the
            # gathered shape (1,)", which is the ABI declining to describe it.
            # Passing the compressed ids straight through is what all three
            # authorities read.
            order_rows: list[str] = []
            for index in range(ENGRAM_ORDERS):
                order = index + 2
                rows = act(
                    f"{op}.order{order}.row_identifiers",
                    "u32",
                    (span, ENGRAM_HEADS),
                )
                emit(
                    f"{op}.order{order}",
                    "NGRAM_HASH",
                    (compressed_ids, multipliers, columns),
                    (rows,),
                    step=f"order{order}",
                    iteration_domain={"tokens": span, "heads": ENGRAM_HEADS},
                    attributes={
                        "absent_operands": [3],
                        "compressed_vocabulary": (
                            profile.engram_compressed_vocabulary
                        ),
                        "first_order": 2,
                        "head": ENGRAM_HEADS,
                        "order": order,
                        "pad_id": profile.engram_pad_token,
                        "table_rows": int(table_spec.shape[0]),
                    },
                )
                order_rows.append(rows)
            row_identifiers = act(
                f"{op}.row_identifiers", "u32", (span, ENGRAM_COLUMNS)
            )
            emit(
                f"{op}.columns",
                "CONCAT",
                tuple(order_rows),
                (row_identifiers,),
                step="column_join",
                iteration_domain={"tokens": span, "width": ENGRAM_COLUMNS},
                attributes={
                    "axis": 1,
                    "segment_order": "ascending_ngram_order_then_hash_head",
                    "segment_widths": [ENGRAM_HEADS] * ENGRAM_ORDERS,
                },
            )

            op = start("ENGRAM_ROW_LOOKUP", "engram.row_lookup", layer)
            table = declare_weight(table_spec)
            table_scale = declare_weight(scale_of[table_spec.name])
            # The gathered codes carry NO tensor-level scale declaration, and
            # that is deliberate.  A declared block scale is addressed by the
            # data view's own element offsets -- amendments A8 and A15 put the
            # code for ``(row, col)`` at ``(row // row_block) * (cols // block)
            # + col // block`` of that view's row-major space -- and these rows
            # were *gathered*, so their scales are at the hashed table rows and
            # nowhere near the arena offsets this block holds.  Declaring it
            # anyway asked the backend to divide 3,072 gathered rows by the
            # table's 189,998 scale rows, which it refused.
            #
            # The release dequantizes on lookup and gathers the scale with the
            # SAME indices (``ParallelEngramEmbedding.forward``:
            # ``scales = F.embedding(local_indices, self.scale)``).  So THIS
            # EXPORT GATHERS IT TOO, with a second lookup on the same row
            # identifiers, and the reconstruction below consumes the gathered
            # plane.  Passing the whole table scale to the dequantiser instead
            # and recording "addressed_by_the_same_row_identifiers" as an
            # attribute did not work: no engine can act on that attribute,
            # because the row identifiers are not one of the dequantiser's
            # operands -- slot 2 is the carried-plane operand of the partial
            # dequantisation contract -- so the device refused the pair with a
            # 189,998-row scale against 3,072 gathered rows.  Gathering it here
            # needs no new operator and no engine change: EMBEDDING_LOOKUP is
            # exactly the release's ``F.embedding``.
            rows_payload = builder.tensor(
                f"{op}.rows",
                "fp8_e4m3fn",
                (span, ENGRAM_COLUMNS, ENGRAM_HEAD_DIM),
                "activation",
            )
            emit(
                f"{op}.read",
                "EMBEDDING_LOOKUP",
                (row_identifiers, table),
                (rows_payload,),
                step="row_read",
                iteration_domain={
                    "tokens": span,
                    "rows": ENGRAM_COLUMNS,
                    "width": ENGRAM_HEAD_DIM,
                },
                attributes={
                    "table_rows": int(table_spec.shape[0]),
                    "row_dtype": "fp8_e4m3fn",
                },
            )
            # The flattened row block is what the projection contracts against:
            # ``self.wkv(self.embed(hash_ids).flatten(-2))``.  The element order
            # is unchanged, so the reconstruction writes the rank-2 form directly
            # rather than moving it twice.
            #: One scale per gathered row, gathered by the same identifiers.
            #: The table scale is ``[table_rows, 1]``, so the gathered plane is
            #: one block scale per row and the block is the row's full width.
            row_scales = builder.tensor(
                f"{op}.row_scales",
                "e8m0",
                (span, ENGRAM_COLUMNS, 1),
                "activation",
            )
            emit(
                f"{op}.read_scales",
                "EMBEDDING_LOOKUP",
                (row_identifiers, table_scale),
                (row_scales,),
                step="row_scale_read",
                iteration_domain={
                    "tokens": span,
                    "rows": ENGRAM_COLUMNS,
                    "width": 1,
                },
                attributes={
                    "table_rows": int(scale_of[table_spec.name].shape[0]),
                    "row_dtype": "e8m0",
                },
            )
            rows_bf16 = act(f"{op}.values", "bf16", (span, ENGRAM_ROW_WIDTH))
            emit(
                f"{op}.reconstruct",
                "DEQUANTIZE",
                (rows_payload, row_scales),
                (rows_bf16,),
                step="reconstruct",
                iteration_domain={
                    "tokens": span,
                    "width": ENGRAM_ROW_WIDTH,
                    "block": WEIGHT_BLOCK,
                },
                attributes={
                    "block_size": WEIGHT_BLOCK,
                    "output_dtype": "bf16",
                    "row_layout": "ascending_column_then_row_element",
                    "scale_rows": "gathered_by_the_same_row_identifiers",
                },
            )

            op = start("ENGRAM_KV_PROJECT", "engram.key_value_project", layer)
            projection_weight = role_weight("engram.lookup_projection.weight", layer)
            out_features, in_features = builder.shape[projection_weight]
            payload, _ = quantize(
                rows_bf16,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                contract=contract_for("ENGRAM_KV_PROJECT", "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                },
                name=f"{op}.quantized_input",
            )
            key_value = act(
                f"{op}.key_value", "bf16", (span, HC_MULT + 1, HIDDEN)
            )
            emit(
                f"{op}.contract",
                "MATMUL",
                (payload, projection_weight),
                (key_value,),
                step="block_scaled_contraction",
                iteration_domain={
                    "rows": span,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "activation_block_elements": ACTIVATION_BLOCK,
                    "input_dtype": "fp8_e4m3fn",
                    "output_dtype": "bf16",
                    # ``kv.split([hc_mult * dim, dim])`` is a view of this one
                    # result: plane m is stream m's key and the last plane is the
                    # value every stream shares.  Stated here because the gate
                    # reads the planes and nothing moves them.
                    "plane_layout": "key_per_hyper_stream_then_shared_value",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                    "value_plane_index": HC_MULT,
                    "weight_block_elements": WEIGHT_BLOCK,
                },
            )

            op = start("ENGRAM_GATE", "engram.gate", layer)
            gated = act(f"{op}.stream", "bf16", (span, HC_MULT, HIDDEN))
            emit(
                op,
                "ENGRAM_GATE",
                (
                    stream,
                    key_value,
                    role_weight("engram.gate.q_weight", layer),
                    role_weight("engram.gate.k_weight", layer),
                ),
                (gated,),
                iteration_domain={
                    "tokens": span,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
                attributes={
                    "clamp_floor_binary32": binary32_bits(1e-6),
                    "epsilon": RMS_EPSILON,
                    "gate_weight_product": "query_times_key",
                    # ``VECTOR.ENGRAM_GATE``'s ``in1`` is documented as the two
                    # planes of a ``[2, width]`` view, and the released
                    # projection publishes ``hc_mult + 1`` planes instead: one
                    # key per hyper-connection copy and one value they share.
                    # The pair the engine reads for stream m is (plane m, plane
                    # hc_mult), which no single strided view of this buffer
                    # presents, so the layout is stated here rather than
                    # materialised by duplicating the value plane hc_mult times.
                    "key_plane_count": HC_MULT,
                    "key_value_plane_layout": (
                        "key_per_hyper_stream_then_one_shared_value_plane"
                    ),
                    "normalization_axis": "hidden_width_per_hyper_stream",
                    "value_plane_index": HC_MULT,
                },
            )
            stream = gated

        # -- attention branch -------------------------------------------
        residual = stream
        collapsed, attention_pre, attention_post, attention_comb = (
            hyper_connection_pre("hyper_connection.attention", stream, carried_pre,
                                 "attn", layer)
        )
        normed = rms_norm("attention.norm", collapsed, "block.attention_norm.weight",
                          layer=layer)
        query_a = fp8_linear(
            "attention.query_a", normed, "attention.query_a.weight",
            layer=layer, out_shape=(span, Q_RANK),
        )
        query_rank = rms_norm(
            "attention.query_norm", query_a, "attention.q_norm.weight", layer=layer
        )
        query_b = fp8_linear(
            "attention.query_b", query_rank, "attention.query_b.weight",
            layer=layer, out_shape=(span, HEADS, HEAD_DIM),
            attributes={"head_count": HEADS, "head_width": HEAD_DIM},
        )
        op = start("ROPE_APPLY", "attention.query_rotation", layer)
        query_rotation = op
        query = rope_apply(op, query_b, ratio=ratio, rows=span)

        window_projection = fp8_linear(
            "attention.key_value", normed, "attention.kv_projection.weight",
            layer=layer, out_shape=(span, HEAD_DIM),
        )
        window_normed = rms_norm(
            "attention.key_value_norm", window_projection,
            "attention.kv_norm.weight", layer=layer,
        )
        op = start("ROPE_APPLY", "attention.key_value_rotation", layer)
        window_rotated = rope_apply(op, window_normed, ratio=ratio, rows=span)

        op = start("FP8_QDQ", "attention.key_value_quantize", layer)
        payload, scale = quantize(
            window_rotated,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("FP8_QDQ", "quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "quantized_width": HEAD_DIM,
                "rounding": "rne",
                "scale_format": "ue8m0",
                # ``act_quant(kv, fp8_block_size, ..., True)`` covers the whole
                # post-RoPE vector, the rotated tail included, so there is no
                # carried prefix here -- unlike V4, which quantized the
                # unrotated width only.
                "quantized_span": "whole_post_rotation_vector",
            },
            name=f"{op}.quantized",
        )
        window_kv = act(f"{op}.key_value", "bf16", (span, HEAD_DIM))
        emit(
            f"{op}.reconstruct",
            "DEQUANTIZE",
            (payload, scale),
            (window_kv,),
            step="reconstruct",
            iteration_domain={
                "rows": span,
                "width": HEAD_DIM,
                "block": ACTIVATION_BLOCK,
            },
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "carried_width": 0,
                "output_dtype": "bf16",
                "reconstructed_width": HEAD_DIM,
            },
        )

        op = start("KV_WINDOW_WRITE", "attention.window_write", layer)
        window_view = view(f"{op}.committed", "bf16", (WINDOW, HEAD_DIM))
        emit(
            op,
            "KV_APPEND",
            (window_kv, position_offset),
            (window_view,),
            iteration_domain={"rows": span, "width": HEAD_DIM, "capacity": WINDOW},
            attributes={
                "cache_row": "absolute_position_mod_window",
                "window_size": WINDOW,
            },
            state_writes=(window_state(layer),),
        )

        op = start("WINDOW_INDEX", "attention.window_index", layer)
        window_indices = act(f"{op}.indices", "u32", (span, WINDOW))
        emit(
            op,
            "WINDOW_INDEX",
            (position_offset,),
            (window_indices,),
            iteration_domain={"tokens": span, "width": WINDOW},
            attributes={
                "index_family": "causal_circular_window",
                "padding_index": -1,
                "window_size": WINDOW,
            },
        )

        # -- the compressed path, per CSA2 mode ---------------------------
        latent_normed = ""
        if mode.kv_owner:
            op = start("COMPRESS_PROJECT", "attention.compressor.project", layer)
            compressor_kv = role_weight("attention.compressor.wkv.weight", layer)
            operands = [normed, compressor_kv]
            projection_attributes: dict[str, Any] = {
                "projection_order": "key_value_then_gate",
                "ratio": ratio,
            }
            if ratio > 1:
                operands.append(
                    role_weight("attention.compressor.wgate.weight", layer)
                )
                packed = act(f"{op}.packed", "fp32", (span, 2, HEAD_DIM))
                projection_attributes["projections"] = 2
            else:
                # ``Compressor.forward``'s ratio-1 branch: ``norm(wkv(x))`` and
                # nothing else.  There is no learned pooling score, so the gate
                # operand does not exist rather than being empty.
                #
                # AND IT IS BF16, not fp32.  ``Compressor.__init__`` declares
                # ``Linear(args.dim, head_dim, dtype=torch.float32 if
                # compress_ratio > 1 else torch.bfloat16)`` and says why in its
                # own comment: "ratio 1 is a plain projection, so it stays in the
                # checkpoint's bf16; the softmax pooling above ratio 1 runs in
                # fp32, so those weights are promoted to fp32 to match".  Declared
                # fp32, this latent reached an RMSNorm whose contract is BF16 in
                # and BF16 out, and the norm refused it -- the one operand in the
                # whole graph that did.
                packed = act(f"{op}.latent", "bf16", (span, HEAD_DIM))
                projection_attributes["projections"] = 1
                projection_attributes["pooling"] = "none"
            emit(
                op,
                "COMPRESS_PROJECT",
                tuple(operands),
                (packed,),
                iteration_domain={
                    "tokens": span,
                    "output_width": HEAD_DIM,
                    "reduction_width": HIDDEN,
                    "projections": projection_attributes["projections"],
                },
                attributes=projection_attributes,
            )
            latent = packed
            if ratio > 1:
                op = start("COMPRESS_STATE_UPDATE", "attention.compressor.carry", layer)
                pool_kv = act(f"{op}.candidate_key_value", "fp32",
                              (groups, ratio, HEAD_DIM))
                pool_score = act(f"{op}.candidate_scores", "fp32",
                                 (groups, ratio, HEAD_DIM))
                emit(
                    op,
                    "COMPRESS_STATE_UPDATE",
                    (packed,),
                    (pool_kv, pool_score),
                    step="raw_window_transaction",
                    iteration_domain={
                        "tokens": span,
                        "groups": groups,
                        "candidates": ratio,
                        "width": HEAD_DIM,
                    },
                    # A18 again, and the same exception the V4 export documents:
                    # the released compressor writes its carry on every step and
                    # only the *pooled* outputs are conditional, so the operator
                    # is issued unconditionally and its two outputs name the
                    # predicate.  The decode condition is
                    # ``(start_pos + 1) % ratio == 0``, which the frozen
                    # comparison registry cannot state, so it is a computed
                    # predicate rather than a symbol comparison.
                    attributes={
                        # ``VECTOR.COMPRESS`` sub-case 2 reads (candidates,
                        # projection, position_embedding).  A state update has no
                        # projection matrix, so ``in1`` is a hole, and this
                        # export states it rather than leaving each backend to
                        # seed one privately.  ``in2``, the absolute position
                        # embedding, is not bound at all: ``Compressor.forward``
                        # computes ``score = self.wgate(x)`` and adds nothing to
                        # it, and the released checkpoint has no ``.ape`` tensor
                        # for any layer.  A backend reads that absence off the
                        # operand row, and the numeric attributes an added
                        # position would need are correspondingly absent here.
                        ABSENT_OPERANDS: [1],
                        "conditional_outputs": {
                            "pool_key_value": f"{op}.should_compress",
                            "pool_scores": f"{op}.should_compress",
                        },
                        "predicate_condition": {
                            "prefill": _nonempty(groups),
                            "decode": f"context_length % {ratio} == 0",
                        },
                        "predicate_output": f"{op}.should_compress",
                        "ratio": ratio,
                        # The head width, which the V4 export also declares.  It
                        # is not new information -- a backend can divide the
                        # packed projection row by the overlap coefficient and
                        # get it -- and that is the point: the emitter derives it
                        # and checks this declaration against what it derived,
                        # and ``check.py``'s compressor reconstruction reads the
                        # geometry from the GRAPH precisely so that it owes
                        # nothing to the lowering. Leaving it out made the two
                        # disagree about whether it was optional, and the
                        # deployment check stopped on ``KeyError: 'head_dim'``.
                        "head_dim": HEAD_DIM,
                    },
                    # The carry is a read-modify-write of both histories, not a
                    # write.  ``Compressor.forward``'s decode branch fills one
                    # slot -- ``self.kv_state[:bsz, slot] = kv.squeeze(1)`` --
                    # and then, on the step that completes the group, pools
                    # ``self.kv_state[:bsz] * self.score_state[:bsz].softmax(1)``
                    # over the *whole* buffer, so the rows earlier steps wrote
                    # are read back; the prefill branch's remainder split writes
                    # slots that only a later decode step reads.  Declaring the
                    # writes alone would hide a real read from the stage
                    # partition, the schedule certificate's
                    # ``shared_state_locality`` rule and the inverse proof, all
                    # three of which reason from ``state_reads``.  A ratio-1
                    # compressor has no such buffer to read -- the released
                    # module registers ``kv_state``/``score_state`` only when
                    # ``compress_ratio > 1`` -- and correspondingly emits no
                    # carry kernel at all, which is why the invariant is
                    # unconditional here rather than a predicate on the ratio.
                    state_reads=(
                        compressor_state(layer, "kv"),
                        compressor_state(layer, "score"),
                    ),
                    state_writes=(
                        compressor_state(layer, "kv"),
                        compressor_state(layer, "score"),
                    ),
                )
                op = start("COMPRESS_POOL", "attention.compressor.pool", layer)
                latent = act(f"{op}.latent", "fp32", (groups, HEAD_DIM))
                emit(
                    op,
                    "COMPRESS_POOL",
                    (pool_kv, pool_score),
                    (latent,),
                    iteration_domain={
                        "groups": groups,
                        "candidates": ratio,
                        "width": HEAD_DIM,
                    },
                    attributes={
                        "execution_predicate": group_predicate,
                        "gate": "softmax_over_the_group",
                        "ratio": ratio,
                    },
                )
            latent_rows = groups if ratio > 1 else span
            if ratio > 1:
                op = start("BINARY32_TO_BF16", "attention.compressor.narrow", layer)
                narrowed = act(f"{op}.latent", "bf16", (groups, HEAD_DIM))
                emit(
                    op,
                    "CONVERT",
                    (latent,),
                    (narrowed,),
                    iteration_domain={"rows": groups, "width": HEAD_DIM},
                    attributes={
                        "execution_predicate": group_predicate,
                        "output_dtype": "bf16",
                        "rounding": "round_to_nearest_even",
                    },
                )
                latent = narrowed
            latent_normed = rms_norm(
                "attention.compressor.norm", latent,
                "attention.compressor.norm.weight", layer=layer,
                predicate=group_predicate,
            )

        index_key_view = ""
        if mode.kv_owner:
            # The index key is derived from this layer's latent *before* the
            # cache is written, because the rotation and the FP4 round trip
            # below overwrite that same value.  Emitting the cache write first
            # would hand the indexer a rotated, requantized latent.
            op = start("INDEX_KEY_PROJECT", "attention.indexer.key_project", layer)
            key_weight = role_weight("attention.indexer.key.weight", layer)
            out_features, in_features = builder.shape[key_weight]
            index_key = act(f"{op}.key", "bf16", (latent_rows, INDEX_HEAD_DIM))
            emit(
                op,
                "MATMUL",
                (latent_normed, key_weight),
                (index_key,),
                iteration_domain={
                    "rows": latent_rows,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "execution_predicate": group_predicate,
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                },
            )
            index_key_normed = rms_norm(
                "attention.indexer.key_norm", index_key,
                "attention.indexer.k_norm.weight", layer=layer,
                predicate=group_predicate,
            )
            op = start("ROPE_APPLY", "attention.indexer.key_rotation", layer)
            index_key_rotated = rope_apply(
                op, index_key_normed, ratio=ratio, rows=latent_rows,
                group_stride=ratio, predicate=group_predicate,
            )
            op = start("FP4_INDEX_QDQ", "attention.indexer.key_quantize", layer)
            payload, scale = quantize(
                index_key_rotated,
                block=FP4_INDEX_BLOCK,
                dtype="mxfp4_e2m1",
                width=None,
                contract=contract_for("FP4_INDEX_QDQ", "quantize"),
                attributes={
                    "block_size": FP4_INDEX_BLOCK,
                    "execution_predicate": group_predicate,
                    "output_dtype": "mxfp4_e2m1",
                    "scale_format": "ue8m0",
                },
                name=f"{op}.quantized",
            )
            index_key_fp4 = act(f"{op}.key", "bf16", (latent_rows, INDEX_HEAD_DIM))
            emit(
                f"{op}.reconstruct",
                "DEQUANTIZE",
                (payload, scale),
                (index_key_fp4,),
                step="reconstruct",
                iteration_domain={
                    "rows": latent_rows,
                    "width": INDEX_HEAD_DIM,
                    "block": FP4_INDEX_BLOCK,
                },
                attributes={
                    "block_size": FP4_INDEX_BLOCK,
                    "carried_width": 0,
                    "execution_predicate": group_predicate,
                    "output_dtype": "bf16",
                    "reconstructed_width": INDEX_HEAD_DIM,
                },
            )
            op = start("INDEX_KEY_WRITE", "attention.indexer.key_write", layer)
            index_key_view = view(
                f"{op}.committed", "bf16",
                (context_tokens // ratio, INDEX_HEAD_DIM),
            )
            emit(
                op,
                "KV_APPEND",
                (index_key_fp4, position_offset),
                (index_key_view,),
                iteration_domain={
                    "rows": latent_rows,
                    "width": INDEX_HEAD_DIM,
                    "capacity": context_tokens // ratio,
                },
                attributes={
                    "cache_row": "compressed_group_index",
                    "execution_predicate": group_predicate,
                    "ratio": ratio,
                },
                state_writes=(index_key_state(layer),),
            )
            # The append addresses the cache's CAPACITY; a reader must not.  The
            # scorer's operand row is ``in1 [B, C, D]`` against ``out0 [B, S, C]``
            # with one C, and C is the groups this request has completed, so the
            # readable plane is published as its own valid prefix -- the same
            # STATE_READ re-presentation this file already emits for the main
            # compressed cache below, and the same one the V4 export emits for
            # both planes (``main.layer02.index_compress_kv_valid_view``).
            #
            # Handing the scorer the append's destination instead states a
            # capacity where a request extent belongs, and that is not a
            # cosmetic difference: an operand that presents its declared maximum
            # scores 131,072 rows of a mostly-unwritten cache and the rows it
            # reads are legally zero, so nothing traps.  This graph said the
            # compressed context on the score's own candidate axis and in its
            # iteration domain, and only its key operand did not.
            op = start("COMPRESSED_KV_VALID_VIEW", "attention.indexer.key_view", layer)
            index_key_valid = view(f"{op}.valid", "bf16", (committed, INDEX_HEAD_DIM))
            key_view_attributes: dict[str, Any] = {
                "capacity_rows_exposed": False,
                "output": "active_batch_contiguous_valid_prefix_only",
                "projection_scope": "indexer",
                "published_by_layer": layer,
                "ratio": ratio,
            }
            if committed_predicate:
                key_view_attributes["execution_predicate"] = committed_predicate
            emit(
                op,
                "STATE_READ",
                (index_key_view,),
                (index_key_valid,),
                iteration_domain={"rows": committed, "width": INDEX_HEAD_DIM},
                attributes=key_view_attributes,
                state_reads=(index_key_state(layer),),
            )
            published_index_key[layer] = index_key_valid

        selection = ""
        if mode.index_source:
            source_key = published_index_key[kv_owner(layer)]
            op = start("INDEX_QUERY_PROJECT", "attention.indexer.query_project", layer)
            query_weight = role_weight("attention.indexer.query.weight", layer)
            out_features, in_features = builder.shape[query_weight]
            payload, _ = quantize(
                query_rank,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                contract=contract_for("INDEX_QUERY_PROJECT", "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                },
                name=f"{op}.quantized_input",
            )
            index_query = act(
                f"{op}.query", "bf16", (span, INDEX_HEADS, INDEX_HEAD_DIM)
            )
            emit(
                f"{op}.contract",
                "MATMUL",
                (payload, query_weight),
                (index_query,),
                step="block_scaled_contraction",
                iteration_domain={
                    "rows": span,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "activation_block_elements": ACTIVATION_BLOCK,
                    "head_count": INDEX_HEADS,
                    "head_width": INDEX_HEAD_DIM,
                    "input_dtype": "fp8_e4m3fn",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                    "weight_block_elements": WEIGHT_BLOCK,
                },
            )
            op = start("ROPE_APPLY", "attention.indexer.query_rotation", layer)
            index_query = rope_apply(op, index_query, ratio=ratio, rows=span)
            op = start("FP4_INDEX_QDQ", "attention.indexer.query_quantize", layer)
            payload, scale = quantize(
                index_query,
                block=FP4_INDEX_BLOCK,
                dtype="mxfp4_e2m1",
                width=None,
                contract=contract_for("FP4_INDEX_QDQ", "quantize"),
                attributes={
                    "block_size": FP4_INDEX_BLOCK,
                    "output_dtype": "mxfp4_e2m1",
                    "scale_format": "ue8m0",
                },
                name=f"{op}.quantized",
            )
            index_query_fp4 = act(
                f"{op}.query", "bf16", (span, INDEX_HEADS, INDEX_HEAD_DIM)
            )
            emit(
                f"{op}.reconstruct",
                "DEQUANTIZE",
                (payload, scale),
                (index_query_fp4,),
                step="reconstruct",
                iteration_domain={
                    "rows": span,
                    "width": INDEX_HEAD_DIM,
                    "block": FP4_INDEX_BLOCK,
                },
                attributes={
                    "block_size": FP4_INDEX_BLOCK,
                    "carried_width": 0,
                    "output_dtype": "bf16",
                    "reconstructed_width": INDEX_HEAD_DIM,
                },
            )
            op = start("INDEX_WEIGHT_PROJECT", "attention.indexer.head_weights", layer)
            head_weight = role_weight("attention.indexer.head_weights.weight", layer)
            out_features, in_features = builder.shape[head_weight]
            head_scores = act(f"{op}.projection", "bf16", (span, INDEX_HEADS))
            emit(
                op,
                "MATMUL",
                (normed, head_weight),
                (head_scores,),
                iteration_domain={
                    "rows": span,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                },
            )
            head_weights = act(f"{op}.head_weights", "bf16", (span, INDEX_HEADS))
            emit(
                f"{op}.scale",
                "SCALE",
                (head_scores,),
                (head_weights,),
                step="softmax_and_head_scale",
                iteration_domain={"tokens": span, "heads": INDEX_HEADS},
                attributes={
                    "scale_bits": binary32_bits(INDEX_SCORE_SCALE),
                    "scale_dtype": "fp32",
                    "scale_source": "index_head_dim**-0.5 * index_n_heads**-0.5",
                },
            )
            op = start("INDEX_SCORE", "attention.indexer.score", layer)
            scores = act(f"{op}.scores", "bf16", (span, committed))
            score_attributes: dict[str, Any] = {
                "candidate_axis": "completed_compression_groups",
                # ``index_score.masked_fill_(arange(...) >= compress_lens, -inf)``
                # is applied here, before either level of the selection, and it is
                # what makes a block score of minus infinity mean "not reachable
                # yet" rather than "scored badly".
                "causal_mask": "compressed_group_completed_before_position",
                "head_reduction": "rectified_then_head_weighted_sum",
                # THE ENGINE'S OWN HEAD-WEIGHT FACTOR IS ONE, and saying so is
                # not a formality.  ``VECTOR.INDEX_SCORE`` reads a learned-index
                # scale off its numeric descriptor and refuses one that is not a
                # positive finite binary32 -- V4 carries the whole factor there
                # (``deepseek_v4_graph`` states 0x3c3504f3, which is
                # ``1/sqrt(index_n_heads * index_head_dim)``) and has the engine
                # apply it.  This export applies it UPSTREAM instead, in the
                # ``SCALE`` kernel just above, because the release writes it as a
                # multiplication on ``weights_proj``'s output
                # (``weights = self.weights_proj(x) * (self.softmax_scale *
                # self.n_heads**-0.5)``) and that is a kernel of its own here.
                # Declaring nothing left the descriptor's scale at zero and the
                # operator could not be issued at all; declaring the factor again
                # would apply it twice.  One is the third option and the true one,
                # and it keeps the refusal meaningful for a graph that forgets.
                "head_weight_scale_binary32": binary32_bits(1.0),
                "head_weight_scale_applied_by": (
                    "the_preceding_scale_kernel_on_the_head_weights"
                ),
                "ratio": ratio,
            }
            if committed_predicate:
                score_attributes["execution_predicate"] = committed_predicate
            emit(
                op,
                "INDEX_SCORE",
                (index_query_fp4, source_key, head_weights),
                (scores,),
                iteration_domain={
                    "tokens": span,
                    "candidates": committed,
                    "heads": INDEX_HEADS,
                    "width": INDEX_HEAD_DIM,
                },
                attributes=score_attributes,
                state_reads=(index_key_state(kv_owner(layer)),),
            )

            if mode.is_candidate_source:
                op = start("CANDIDATE_BLOCK_SELECT", "attention.indexer.pool", layer)
                block_scores = act(
                    f"{op}.block_scores", "bf16", (span, candidate_blocks_extent)
                )
                emit(
                    f"{op}.block_maximum",
                    "BLOCK_MAX",
                    (scores,),
                    (block_scores,),
                    step="block_maximum",
                    iteration_domain={
                        "tokens": span,
                        "candidates": committed,
                        "blocks": candidate_blocks_extent,
                    },
                    attributes={
                        "block": CANDIDATE_BLOCK,
                        "padding_value": "negative_infinity",
                    },
                )
                chosen = act(f"{op}.block_identifiers", "u32",
                             (span, CANDIDATE_BLOCKS))
                # ``in2`` is the number of request tokens one element of the
                # ranked axis spans, which for a block of ``candidate_block``
                # compressed positions at compression ratio ``ratio`` is their
                # product.  On this release the candidate source is a ratio-1
                # layer, so the product is the block size -- which is exactly why
                # it is written as a product: a candidate source at ratio 2 would
                # otherwise count its horizon at half speed and nothing would
                # refuse it.
                emit(
                    f"{op}.block_select",
                    "INDEX_TOPK",
                    (block_scores, ratio_constant(ratio * CANDIDATE_BLOCK)),
                    (chosen,),
                    step="block_top_k",
                    iteration_domain={
                        "tokens": span,
                        "top_k": CANDIDATE_BLOCKS,
                        "width": CANDIDATE_BLOCKS,
                    },
                    attributes={
                        # No window block to join and no rebase: this selection
                        # names blocks of the candidate axis, which is why slot 1
                        # is absent rather than empty.
                        "absent_operands": [1, 3],
                        "block": CANDIDATE_BLOCK,
                        "compression_ratio": ratio,
                        "k": CANDIDATE_BLOCKS,
                        "order": "score_descending_then_index_ascending",
                        "padding_index": -1,
                        "pinned_block": "the_block_holding_the_newest_position",
                    },
                )
                mask = view(f"{op}.admission", "u8", (span, committed))
                emit(
                    f"{op}.mask",
                    "CANDIDATE_MASK",
                    (chosen,),
                    (mask,),
                    step="admission_plane",
                    iteration_domain={
                        "tokens": span,
                        "blocks": candidate_blocks_extent,
                        "width": committed,
                    },
                    attributes={
                        "block": CANDIDATE_BLOCK,
                        "polarity": "one_admits_the_position",
                        "population_bound": CANDIDATE_POOL,
                        "width": committed,
                    },
                    state_writes=(candidate_mask_state(layer),),
                )
                published_mask[layer] = mask

            pool_mask = ""
            if mode.uses_candidates and mode.index_source:
                op = start("CANDIDATE_MASK_READ", "attention.indexer.pool_read", layer)
                source_mask = published_mask[profile.candidate_source_layer]
                pool_mask = act(f"{op}.admission", "u8", (span, committed))
                emit(
                    op,
                    "STATE_READ",
                    (source_mask,),
                    (pool_mask,),
                    iteration_domain={"tokens": span, "width": committed},
                    attributes={
                        "population_bound": CANDIDATE_POOL,
                        "published_by_layer": profile.candidate_source_layer,
                    },
                    state_reads=(
                        candidate_mask_state(profile.candidate_source_layer),
                    ),
                )

            op = start("INDEX_TOPK", "attention.indexer.select", layer)
            selected = view(f"{op}.selection", "u32", (span, INDEX_TOPK_WIDTH))
            topk_inputs = [scores, ratio_constant(ratio)]
            topk_attributes: dict[str, Any] = {
                "absent_operands": [1],
                "causal_mask": "compressed_group_completed_before_position",
                "compression_ratio": ratio,
                "k": INDEX_TOPK_WIDTH,
                "order": "index_ascending",
                "padding_index": -1,
                "rebase": "the_joined_key_value_rows_of_the_window_ahead_of_it",
            }
            if pool_mask:
                topk_inputs.append(pool_mask)
                topk_attributes["absent_operands"] = [1]
                topk_attributes["candidate_mask"] = "read_as_state"
            else:
                topk_attributes["absent_operands"] = [1, 3]
            if committed_predicate:
                topk_attributes["operand_present_predicate"] = {
                    "0": committed_predicate
                }
            emit(
                op,
                "INDEX_TOPK",
                tuple(topk_inputs),
                (selected,),
                step="masked_topk",
                iteration_domain={
                    "tokens": span,
                    "top_k": INDEX_TOPK_WIDTH,
                    "candidates": committed,
                    "width": INDEX_TOPK_WIDTH,
                },
                attributes=topk_attributes,
                state_writes=(index_selection_state(layer),),
            )
            published_selection[layer] = selected
            selection = selected
        elif ratio:
            op = start("SHARED_INDEX_REUSE", "attention.indexer.reuse", layer)
            source_layer = index_owner(layer)
            reused = act(f"{op}.selection", "u32", (span, INDEX_TOPK_WIDTH))
            emit(
                op,
                "STATE_READ",
                (published_selection[source_layer],),
                (reused,),
                iteration_domain={"tokens": span, "width": INDEX_TOPK_WIDTH},
                attributes={
                    "published_by_layer": source_layer,
                    "selection_lifetime": "until_the_next_index_source",
                },
                state_reads=(index_selection_state(source_layer),),
            )
            selection = reused

        attention_indices = window_indices
        if ratio:
            # Every CSA2 layer joins its own window block to the compressed
            # selection, which is what ``Attention.forward`` does:
            # ``torch.cat([topk_idxs, compress_idxs], dim=-1)`` runs in the layer,
            # after the selection -- its own or its source's -- is in hand.  The
            # published state is therefore the compressed half alone.
            attention_indices = act(
                f"{current['op']}.joined_indices",
                "u32",
                (span, WINDOW + INDEX_TOPK_WIDTH),
            )
            emit(
                f"{current['op']}.index_join",
                "CONCAT",
                (window_indices, selection),
                (attention_indices,),
                step="window_then_compressed",
                iteration_domain={
                    "tokens": span,
                    "width": WINDOW + INDEX_TOPK_WIDTH,
                },
                attributes={
                    "axis": 1,
                    "padding_index": -1,
                    "segment_order": "window_then_rebased_compressed",
                    "segment_widths": [WINDOW, INDEX_TOPK_WIDTH],
                },
            )

        if mode.kv_owner:
            op = start("ROPE_APPLY", "attention.compressor.rotation", layer)
            latent_rotated = rope_apply(
                op, latent_normed, ratio=ratio, rows=latent_rows,
                group_stride=ratio, predicate=group_predicate,
            )
            op = start("FP4_MAIN_QDQ", "attention.compressor.quantize", layer)
            payload, scale = quantize(
                latent_rotated,
                block=FP4_MAIN_BLOCK,
                dtype=MAIN_LATENT_DTYPE,
                width=None,
                contract=contract_for("FP4_MAIN_QDQ", "quantize"),
                attributes={
                    # ``fp4_act_quant(latent, 16, True, scale_dtype=float8_e4m3fn)``
                    # -- one E4M3 scale per sixteen elements, which is neither the
                    # MXFP4 block nor the MXFP4 scale format, and is why AM-E10
                    # gave the latent a dtype of its own.
                    "block_size": FP4_MAIN_BLOCK,
                    "execution_predicate": group_predicate,
                    "output_dtype": MAIN_LATENT_DTYPE,
                    "scale_format": "e4m3",
                },
                name=f"{op}.quantized",
            )
            latent_fp4 = act(f"{op}.latent", "bf16", (latent_rows, HEAD_DIM))
            emit(
                f"{op}.reconstruct",
                "DEQUANTIZE",
                (payload, scale),
                (latent_fp4,),
                step="reconstruct",
                iteration_domain={
                    "rows": latent_rows,
                    "width": HEAD_DIM,
                    "block": FP4_MAIN_BLOCK,
                },
                attributes={
                    "block_size": FP4_MAIN_BLOCK,
                    "carried_width": 0,
                    "execution_predicate": group_predicate,
                    "output_dtype": "bf16",
                    "reconstructed_width": HEAD_DIM,
                    "scale_format": "e4m3",
                },
            )
            op = start("COMPRESS_KV_WRITE", "attention.compressor.write", layer)
            compressed_view = view(
                f"{op}.committed", "bf16", (context_tokens // ratio, HEAD_DIM)
            )
            emit(
                op,
                "KV_APPEND",
                (latent_fp4, position_offset),
                (compressed_view,),
                iteration_domain={
                    "rows": latent_rows,
                    "width": HEAD_DIM,
                    "capacity": context_tokens // ratio,
                },
                attributes={
                    "cache_row": "compressed_group_index",
                    "execution_predicate": group_predicate,
                    "ratio": ratio,
                },
                state_writes=(compressed_state(layer),),
            )
            published_compressed[layer] = compressed_view

        attention_kv = window_view
        if ratio:
            op = start("COMPRESSED_KV_VALID_VIEW", "attention.compressed_view", layer)
            owner = kv_owner(layer)
            compressed_source = published_compressed.get(owner, "")
            if not compressed_source:
                raise DeepSeekV41KernelIRError(
                    f"layer {layer} reads layer {owner}'s compressed cache before "
                    "that layer has written it"
                )
            valid = act(f"{op}.valid", "bf16", (committed, HEAD_DIM))
            view_attributes: dict[str, Any] = {
                "published_by_layer": owner,
                "ratio": ratio,
            }
            if committed_predicate:
                view_attributes["execution_predicate"] = committed_predicate
            emit(
                op,
                "STATE_READ",
                (compressed_source,),
                (valid,),
                iteration_domain={"rows": committed, "width": HEAD_DIM},
                attributes=view_attributes,
                state_reads=(compressed_state(owner),),
            )
            op = start("ATTENTION_KV_VIEW", "attention.key_value_view", layer)
            fused = view(f"{op}.fused", "bf16", (join_rows(ratio), HEAD_DIM))
            join_attributes: dict[str, Any] = {
                "axis": 0,
                # The row space is phase-dependent in the released source, and
                # this is V4's own resolution: prefill consumes the current
                # request's rows and never a duplicate window, decode consumes
                # the whole circular window and never a duplicate current row,
                # and both append the same valid compressed prefix.
                "phase_inputs": {"prefill": [0, 2], "decode": [1, 2]},
                "phase_segment_order": {
                    "prefill": "current_then_valid_compressed_prefix",
                    "decode": "committed_window_then_valid_compressed_prefix",
                },
                "phase_symbol_binding": {
                    "prefill": {"position_start": 0},
                    "decode": {"span_tokens": 1},
                },
            }
            if committed_predicate:
                join_attributes["operand_present_predicate"] = {
                    "2": committed_predicate
                }
            emit(
                op,
                "CONCAT",
                (window_kv, window_view, valid),
                (fused,),
                iteration_domain={"rows": join_rows(ratio), "width": HEAD_DIM},
                attributes=join_attributes,
                state_reads=(window_state(layer), compressed_state(owner)),
            )
            attention_kv = fused

        op = start("SPARSE_ATTENTION", "attention.sparse", layer)
        attention_out = act(f"{op}.output", "bf16", (span, HEADS, HEAD_DIM))
        attention_attributes: dict[str, Any] = {
            "group_size": HEADS,
            "key_value_heads": 1,
            "padding_index": -1,
            "softmax_scale_bits": binary32_bits(HEAD_DIM**-0.5),
        }
        if not ratio:
            # A window-only layer attends one row space, and the released one is
            # phase-dependent with no operator between: prefill attends the
            # current request's rows and decode the committed window.  The CSA2
            # layers state the same fact on their join's ``phase_inputs``, which
            # neutral admission checks; here there is no join to carry it, so it
            # is stated on the operand and a backend that ignores it attends the
            # ring in prefill.
            attention_attributes["phase_key_value_rows"] = {
                "prefill": "the_current_request_rows_of_this_resource",
                "decode": "the_committed_window",
            }
        emit(
            op,
            "ATTENTION_SPARSE",
            (query, attention_kv, attention_indices,
             role_weight("attention.sink", layer)),
            (attention_out,),
            iteration_domain={
                "tokens": span,
                "heads": HEADS,
                "key_value_heads": 1,
                "width": HEAD_DIM,
                "candidates": builder.shape[attention_indices][-1],
            },
            attributes=attention_attributes,
            state_reads=(window_state(layer),) if not ratio else (),
        )

        op = start("ROPE_INVERSE", "attention.output_rotation", layer)
        # RANK-3, LIKE ITS INPUT.  This was ``(span, HEADS * HEAD_DIM)``, the
        # rank-2 form the grouped projection contracts against, on the reasoning
        # that ``o.view(bsz, seqlen, n_groups, -1)`` reads the head axis as one
        # row and nothing moves.  Nothing does move -- but VECTOR.ROPE is
        # shape-preserving and the engine checks it, so a rank-2 output against
        # a rank-3 input refused V4.1 at PC 80: "view 1299 is (1, 64, 512) and
        # view 1301 is (1, 32768)".  The two described the same bytes at the
        # same stride.  ABI 3.0 views are per-operand, so the tensor is declared
        # at the rank the operator that writes it requires and the consumer
        # below presents whatever rank it contracts against; the flattening is a
        # property of a reader, not of the tensor.
        unrotated = act(f"{op}.output", "bf16", (span, HEADS, HEAD_DIM))
        # ``apply_rotary_emb(o, freqs_cis, True)`` conjugates *the query's own*
        # coefficient rows -- the same positions, the same table, the same rotary
        # profile -- so the inverse reads the rows the query rotation already
        # gathered.  That is why the plan gives ``ROPE_INVERSE`` one kernel where
        # ``ROPE_APPLY`` has two: a second gather here would be the same rows
        # under a second name.
        coefficients = rope_coefficients[query_rotation]
        emit(
            op,
            "ROPE_INVERSE",
            (attention_out, coefficients),
            (unrotated,),
            step="rotate",
            iteration_domain={"rows": span, "width": ROPE_DIM},
            attributes={
                **rope_attributes(ratio, inverse=True),
                # ``o.view(bsz, seqlen, n_groups, -1)`` reads the head axis as
                # one row, so the result is written in the rank-2 form the
                # grouped projection contracts against; the element order is the
                # same and nothing moves.
                "head_axis": "flattened_into_the_row",
                "head_count": HEADS,
            },
        )

        # -- the grouped output projection, both stages -------------------
        op = start("GROUPED_OUTPUT_PROJECT", "attention.output_project", layer)
        weight_spec = role_specs("attention.output_a.weight", layer)[0]
        if int(weight_spec.shape[0]) != O_JOINED or int(
            weight_spec.shape[1]
        ) != O_REDUCTION:
            raise DeepSeekV41KernelIRError(
                f"{weight_spec.name!r} is {tuple(weight_spec.shape)}, not the "
                f"{(O_JOINED, O_REDUCTION)} the grouped projection reads"
            )
        grouped = act(f"{op}.group_axis", "bf16", (span, O_GROUPS, O_REDUCTION))
        emit(
            f"{op}.group_axis",
            "COPY",
            (unrotated,),
            (grouped,),
            step="group_axis",
            iteration_domain={
                "tokens": span,
                "groups": O_GROUPS,
                "reduction_width": O_REDUCTION,
            },
            attributes={
                "group_axis": 1,
                "group_count": O_GROUPS,
                "row_order": "token_major_group_minor",
            },
        )
        blocks: list[str] = []
        for group in range(O_GROUPS):
            columns = act(f"{op}.group{group}.columns", "bf16", (span, O_REDUCTION))
            emit(
                f"{op}.group{group}.select",
                "SELECT",
                (grouped,),
                (columns,),
                step="group_columns",
                iteration_domain={"tokens": span, "reduction_width": O_REDUCTION},
                attributes={
                    "axis": 1,
                    "index": group,
                    "plane": "attention_output_group",
                },
            )
            partial = act(f"{op}.group{group}.projection", "bf16", (span, O_RANK))
            emit(
                f"{op}.group{group}.project",
                "MATMUL",
                (columns, group_weight(weight_spec, group, O_GROUPS)),
                (partial,),
                step="group_contraction",
                iteration_domain={
                    "tokens": span,
                    "output_width": O_RANK,
                    "reduction_width": O_REDUCTION,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "group_index": group,
                    "input_dtype": "bf16",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                    "weight_dequantization": "block_scaled_fp8_to_bf16",
                },
            )
            blocks.append(partial)
        level: list[tuple[str, int]] = [(name, O_RANK) for name in blocks]
        joined_id = f"{op}.joined"
        stage_index = 0
        while len(level) > 1:
            nxt: list[tuple[str, int]] = []
            for index in range(0, len(level), 4):
                members = level[index : index + 4]
                if len(members) == 1:
                    nxt.append(members[0])
                    continue
                widths = [width for _, width in members]
                out_width = sum(widths)
                name = (
                    joined_id
                    if len(level) <= 4
                    else f"{op}.join{stage_index}.{index // 4}"
                )
                tensor_id = act(name, "bf16", (span, out_width))
                emit(
                    name,
                    "CONCAT",
                    tuple(member for member, _ in members),
                    (tensor_id,),
                    step="group_join",
                    iteration_domain={"tokens": span, "width": out_width},
                    attributes={"axis": 1, "segment_widths": widths},
                )
                nxt.append((tensor_id, out_width))
            level = nxt
            stage_index += 1
        joined = level[0][0]
        output_b = role_weight("attention.output_b.weight", layer)
        out_features, in_features = builder.shape[output_b]
        payload, _ = quantize(
            joined,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("GROUPED_OUTPUT_PROJECT", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
            },
            name=f"{op}.quantized_join",
        )
        attention_branch = act(f"{op}.output", "bf16", (span, HIDDEN))
        emit(
            f"{op}.contract",
            "MATMUL",
            (payload, output_b),
            (attention_branch,),
            step="block_scaled_contraction",
            iteration_domain={
                "rows": span,
                "output_width": out_features,
                "reduction_width": in_features,
            },
            attributes={
                "accumulator_dtype": "fp32",
                "activation_block_elements": ACTIVATION_BLOCK,
                "input_dtype": "fp8_e4m3fn",
                "output_dtype": "bf16",
                "reduction_order": "increasing_reduction_index",
                "transpose_weight": True,
                "weight_block_elements": WEIGHT_BLOCK,
            },
        )

        stream = hyper_connection_post(
            "hyper_connection.attention_post", attention_branch, residual,
            attention_post, attention_comb, layer,
        )

        # -- feed-forward branch ----------------------------------------
        residual = stream
        collapsed, ffn_pre, ffn_post, ffn_comb = hyper_connection_pre(
            "hyper_connection.feed_forward", stream, attention_pre, "ffn", layer
        )
        ffn_normed = rms_norm(
            "feed_forward.norm", collapsed, "block.ffn_norm.weight", layer=layer
        )

        op = start("ROUTER_SCORE", "feed_forward.router", layer)
        router_weight = role_weight("moe.router.weight", layer)
        router_scores = act(f"{op}.scores", "fp32", (span, ROUTED_EXPERTS))
        emit(
            op,
            "ROUTER_SCORE",
            (ffn_normed, router_weight),
            (router_scores,),
            iteration_domain={
                "tokens": span,
                "experts": ROUTED_EXPERTS,
                "reduction_width": HIDDEN,
            },
            attributes={"accumulator_dtype": "fp32", "gate_temperature": 1.0},
        )
        op = start("SQRT_SOFTPLUS", "feed_forward.router_activation", layer)
        gate_scores = act(f"{op}.scores", "fp32", (span, ROUTED_EXPERTS))
        emit(
            op,
            "SQRT_SOFTPLUS",
            (router_scores,),
            (gate_scores,),
            iteration_domain={"tokens": span, "experts": ROUTED_EXPERTS},
            attributes={"scoring_function": profile.scoring_function},
        )
        op = start("BIASED_TOPK_ROUTE", "feed_forward.route", layer)
        bias = role_weight("moe.router.selection_bias", layer)
        expert_indices = act(f"{op}.expert_identifiers", "u32", (span, TOP_K))
        selected_scores = act(f"{op}.selected_scores", "fp32", (span, TOP_K))
        emit(
            op,
            "BIASED_TOPK",
            (gate_scores, bias),
            (expert_indices, selected_scores),
            iteration_domain={
                "tokens": span,
                "experts": ROUTED_EXPERTS,
                "top_k": TOP_K,
            },
            attributes={
                "bias_scope": "selection_only",
                "order": "score_descending_then_index_ascending",
                "selected_score_output": (
                    "unused_the_released_gate_regathers_unbiased_scores"
                ),
            },
        )
        op = start("ROUTER_WEIGHT_NORMALIZE", "feed_forward.route_weights", layer)
        gathered = act(f"{op}.gathered", "fp32", (span, TOP_K))
        emit(
            f"{op}.gather",
            "GATHER",
            (gate_scores, expert_indices),
            (gathered,),
            step="unbiased_score_gather",
            iteration_domain={"tokens": span, "top_k": TOP_K},
        )
        normalized = act(f"{op}.normalized", "fp32", (span, TOP_K))
        emit(
            f"{op}.normalize",
            "WEIGHT_NORMALIZE",
            (gathered,),
            (normalized,),
            step="selected_sum_normalize",
            iteration_domain={"tokens": span, "top_k": TOP_K},
            attributes={
                "normalize": profile.normalize_top_k,
                # ``weights /= weights.sum(-1) + 1e-20`` -- the released comment
                # says in terms that this is *not* norm_eps and matches training.
                "sum_floor_binary32": binary32_bits(1e-20),
            },
        )
        route_weights = act(f"{op}.route_weights", "fp32", (span, TOP_K))
        emit(
            f"{op}.scale",
            "SCALE",
            (normalized,),
            (route_weights,),
            step="route_scale",
            iteration_domain={"tokens": span, "top_k": TOP_K},
            attributes={
                "scale_bits": binary32_bits(ROUTE_SCALE),
                "scale_dtype": "fp32",
            },
        )
        op = start("EXPERT_DISPATCH", "feed_forward.dispatch", layer)
        dispatched = act(f"{op}.rows", "bf16", (dispatch_rows, HIDDEN))
        expert_rows = act(f"{op}.row_expert_identifiers", "u32", (dispatch_rows,))
        emit(
            op,
            "EXPERT_DISPATCH",
            (ffn_normed, expert_indices),
            (dispatched, expert_rows),
            iteration_domain={
                "tokens": span,
                "top_k": TOP_K,
                "routed_rows": dispatch_rows,
                "width": HIDDEN,
            },
            attributes={
                # THE BOUND THE OPERATOR CHECKS ITS IDS AGAINST, stated rather
                # than left to each backend to guess.  ``ROUTE.EXPERT_DISPATCH``
                # rejects an id outside its aux0 count -- an unbounded expert id
                # is a memory-safety problem, not a routing detail -- and this
                # kernel declared none, so the two lanes guessed differently: ROM
                # fell back to the capability's ``max_expert_ids`` (permissive but
                # working) and HBM inferred 1 from a routed contraction and
                # refused 42 of its own ids.  The expert SWIGLU immediately below
                # has always declared the same number; the operator that
                # bound-checks against it had not.
                "expert_count": ROUTED_EXPERTS,
                "row_order": "ascending_token_then_ascending_selection",
                "routed_row_expert_output": True,
            },
        )

        op = start("MXFP4_SWIGLU", "feed_forward.routed_expert", layer)
        gate_stack = role_weight_stack("moe.routed_expert.gate.weight", layer)
        up_stack = role_weight_stack("moe.routed_expert.up.weight", layer)
        down_stack = role_weight_stack("moe.routed_expert.down.weight", layer)
        weight_attributes = {
            "expert_count": ROUTED_EXPERTS,
            "expert_weight_block_elements": FP4_INDEX_BLOCK,
            "expert_weight_dtype": "mxfp4_e2m1",
            "expert_weight_order": "ascending_logical_expert_id",
        }
        payload, _ = quantize(
            dispatched,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("MXFP4_SWIGLU", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
            },
            name=f"{op}.quantized_input",
        )
        routed_gate = act(f"{op}.gate", "bf16", (dispatch_rows, MOE_INTERMEDIATE))
        routed_up = act(f"{op}.up", "bf16", (dispatch_rows, MOE_INTERMEDIATE))
        for name, target in (("gate", routed_gate), ("up", routed_up)):
            emit(
                f"{op}.{name}",
                "ROUTED_MATMUL",
                (payload, gate_stack if name == "gate" else up_stack, expert_rows),
                (target,),
                step=f"{name}_contraction",
                iteration_domain={
                    "rows": dispatch_rows,
                    "output_width": MOE_INTERMEDIATE,
                    "reduction_width": HIDDEN,
                },
                attributes={**weight_attributes, "projection": name},
            )
        activated = act(f"{op}.activated", "bf16", (dispatch_rows, MOE_INTERMEDIATE))
        emit(
            f"{op}.activate",
            "SWIGLU",
            (routed_gate, routed_up),
            (activated,),
            step="clamped_silu_product",
            iteration_domain={"rows": dispatch_rows, "width": MOE_INTERMEDIATE},
            attributes={
                "clamp": "gate_upper_and_up_symmetric",
                "compute_dtype": "fp32",
                "swiglu_limit": SWIGLU_LIMIT,
            },
        )
        weighted = act(f"{op}.weighted", "bf16", (dispatch_rows, MOE_INTERMEDIATE))
        emit(
            f"{op}.route_weight",
            "MUL",
            (activated, route_weights),
            (weighted,),
            step="routing_weight_product",
            iteration_domain={"rows": dispatch_rows, "width": MOE_INTERMEDIATE},
            attributes={"broadcast": "routed_row_to_intermediate_width"},
        )
        down_payload, _ = quantize(
            weighted,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("MXFP4_SWIGLU", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
            },
            name=f"{op}.quantized_activation",
        )
        routed_output = act(f"{op}.output", "bf16", (dispatch_rows, HIDDEN))
        emit(
            f"{op}.down",
            "ROUTED_MATMUL",
            (down_payload, down_stack, expert_rows),
            (routed_output,),
            step="down_contraction",
            iteration_domain={
                "rows": dispatch_rows,
                "output_width": HIDDEN,
                "reduction_width": MOE_INTERMEDIATE,
            },
            attributes={**weight_attributes, "projection": "down"},
        )

        op = start("FP8_SWIGLU", "feed_forward.shared_expert", layer)
        shared_gate_weight = role_weight("moe.shared_expert.gate.weight", layer)
        shared_up_weight = role_weight("moe.shared_expert.up.weight", layer)
        shared_down_weight = role_weight("moe.shared_expert.down.weight", layer)
        payload, _ = quantize(
            ffn_normed,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("FP8_SWIGLU", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
            },
            name=f"{op}.quantized_input",
        )
        shared_gate = act(f"{op}.gate", "bf16", (span, MOE_INTERMEDIATE))
        shared_up = act(f"{op}.up", "bf16", (span, MOE_INTERMEDIATE))
        for name, target, weight in (
            ("gate", shared_gate, shared_gate_weight),
            ("up", shared_up, shared_up_weight),
        ):
            emit(
                f"{op}.{name}",
                "MATMUL",
                (payload, weight),
                (target,),
                step=f"{name}_contraction",
                iteration_domain={
                    "rows": span,
                    "output_width": MOE_INTERMEDIATE,
                    "reduction_width": HIDDEN,
                },
                attributes={
                    "accumulator_dtype": "fp32",
                    "activation_block_elements": ACTIVATION_BLOCK,
                    "input_dtype": "fp8_e4m3fn",
                    "output_dtype": "bf16",
                    "projection": name,
                    "transpose_weight": True,
                    "weight_block_elements": WEIGHT_BLOCK,
                },
            )
        shared_activated = act(f"{op}.activated", "bf16", (span, MOE_INTERMEDIATE))
        emit(
            f"{op}.activate",
            "SWIGLU",
            (shared_gate, shared_up),
            (shared_activated,),
            step="clamped_silu_product",
            iteration_domain={"rows": span, "width": MOE_INTERMEDIATE},
            attributes={
                "clamp": "gate_upper_and_up_symmetric",
                "compute_dtype": "fp32",
                "swiglu_limit": SWIGLU_LIMIT,
            },
        )
        shared_payload, _ = quantize(
            shared_activated,
            block=ACTIVATION_BLOCK,
            dtype="fp8_e4m3fn",
            width=None,
            contract=contract_for("FP8_SWIGLU", "activation_quantize"),
            attributes={
                "block_size": ACTIVATION_BLOCK,
                "output_dtype": "fp8_e4m3fn",
                "rounding": "rne",
                "scale_format": "ue8m0",
            },
            name=f"{op}.quantized_activation",
        )
        shared_output = act(f"{op}.output", "bf16", (span, HIDDEN))
        emit(
            f"{op}.down",
            "MATMUL",
            (shared_payload, shared_down_weight),
            (shared_output,),
            step="down_contraction",
            iteration_domain={
                "rows": span,
                "output_width": HIDDEN,
                "reduction_width": MOE_INTERMEDIATE,
            },
            attributes={
                "accumulator_dtype": "fp32",
                "activation_block_elements": ACTIVATION_BLOCK,
                "input_dtype": "fp8_e4m3fn",
                "output_dtype": "bf16",
                "projection": "down",
                "transpose_weight": True,
                "weight_block_elements": WEIGHT_BLOCK,
            },
        )

        op = start("EXPERT_REDUCE", "feed_forward.reduce", layer)
        ffn_branch = act(f"{op}.output", "bf16", (span, HIDDEN))
        emit(
            op,
            "EXPERT_REDUCE",
            (routed_output, shared_output, expert_rows),
            (ffn_branch,),
            iteration_domain={"tokens": span, "top_k": TOP_K, "width": HIDDEN},
            attributes={
                "base_operand_index": 1,
                "contribution_row_order": (
                    "ascending_token_then_ascending_selection"
                ),
                "reduction_order": "pairwise_tree",
                "routing_weight_application": (
                    "already_applied_inside_the_expert_before_the_down_projection"
                ),
                "top_k": TOP_K,
            },
        )
        stream = hyper_connection_post(
            "hyper_connection.feed_forward_post", ffn_branch, residual,
            ffn_post, ffn_comb, layer,
        )
        carried_pre = ffn_pre

    # ------------------------------------------------------------------
    # Epilogue
    # ------------------------------------------------------------------
    op = start("HC_FINAL_COLLAPSE", "hyper_connection_collapse", None)
    collapsed = act(f"{op}.hidden", "bf16", (span, HIDDEN))
    emit(
        op,
        "EXPERT_REDUCE",
        (stream, carried_pre),
        (collapsed,),
        iteration_domain={
            "tokens": span,
            "hyper_streams": HC_MULT,
            "width": HIDDEN,
        },
        attributes={
            "contribution_row_order": "ascending_hyper_stream",
            "reduction_axis": 1,
            "reduction_order": "pairwise_tree",
            "routing_weight_application": "applied_at_the_reduction",
            "stream_count": HC_MULT,
            # ``Transformer.forward`` ends ``h = layer.hc_pre(h, pre_mix)``: the
            # last block's own branch weights, with no head projection tensor of
            # its own.  V4 had an ``hc_head`` matrix here and this checkpoint has
            # none, which is why the collapse is a reduction and not a projection.
            "weight_source": "the_last_block_feed_forward_branch_weights",
        },
    )
    op = start("FINAL_RMS_NORM", "final_norm", None)
    head_normed = act(f"{op}.hidden", "bf16", (span, HIDDEN))
    emit(
        op,
        "RMS_NORM",
        (collapsed, role_weight("model.final_norm.weight")),
        (head_normed,),
        iteration_domain={"tokens": span, "width": HIDDEN},
        attributes={"epsilon": RMS_EPSILON},
    )
    op = start("LM_HEAD", "vocabulary_head", None)
    final_position = act(f"{op}.final_position", "bf16", (1, HIDDEN))
    emit(
        f"{op}.select",
        "LAST_TOKEN_SELECT",
        (head_normed, position_offset),
        (final_position,),
        step="final_source_position",
        iteration_domain={"rows": 1, "width": HIDDEN},
    )
    logits = act(f"{op}.logits", "fp32", (1, VOCABULARY))
    emit(
        f"{op}.project",
        "VOCAB_PROJECT",
        (final_position, role_weight("model.lm_head.weight")),
        (logits,),
        step="vocabulary_projection",
        iteration_domain={
            "rows": 1,
            "output_width": VOCABULARY,
            "reduction_width": HIDDEN,
        },
        attributes={"accumulator_dtype": "fp32", "output_dtype": "fp32"},
    )
    op = start("SAMPLE", "sample", None)
    scaled = act(f"{op}.scaled_logits", "fp32", (1, VOCABULARY))
    emit(
        f"{op}.temperature",
        "SCALE",
        (logits,),
        (scaled,),
        step="temperature",
        iteration_domain={"rows": 1, "width": VOCABULARY},
        attributes={
            "operation": "reciprocal_temperature_product",
            "scale_bits": binary32_bits(1.0),
            "scale_dtype": "fp32",
            "temperature_source": (
                "deployment_constant_official_default; ABI 3.0 carries no "
                "per-request temperature field"
            ),
        },
    )
    token = act(f"{op}.argmax", TOKEN_DTYPE, (1,))
    emit(
        f"{op}.select",
        "ARGMAX",
        (scaled,),
        (token,),
        step="greedy_argmax",
        iteration_domain={"rows": 1, "width": VOCABULARY},
        attributes={"tie_rule": "lowest_token_id"},
    )
    appended = act(f"{op}.tokens", TOKEN_DTYPE, (1,))
    emit(
        f"{op}.append",
        "TOKEN_APPEND",
        (token,),
        (appended,),
        step="token_append",
        iteration_domain={"rows": 1},
        attributes={"eos_token_id": EOS_TOKEN_ID},
    )

    # ------------------------------------------------------------------
    # Confront the emission with the plan
    # ------------------------------------------------------------------
    disagreements: list[str] = []
    planned_layers = layer_source_plan(profile)
    for index, planned in enumerate(planned_layers):
        observed = tuple(emitted_layer_sources[index])
        if observed != tuple(planned):
            disagreements.append(
                f"layer {index} emitted {list(observed)} against the planned "
                f"{list(planned)}"
            )
    planned_unlayered = tuple(unlayered_source_plan(profile))
    if tuple(emitted_unlayered_sources) != planned_unlayered:
        disagreements.append(
            f"the unlayered path emitted {emitted_unlayered_sources} against the "
            f"planned {list(planned_unlayered)}"
        )
    plan = planned_census(profile)
    observed_layer_kinds: list[Counter] = [Counter() for _ in planned_layers]
    observed_unlayered_kinds: Counter = Counter()
    for kernel in builder.kernels:
        if kernel.layer is None:
            observed_unlayered_kinds[kernel.kind] += 1
        else:
            observed_layer_kinds[kernel.layer][kernel.kind] += 1
    for index, expected in enumerate(plan["per_layer_kernels_by_kind"]):
        observed = dict(sorted(observed_layer_kinds[index].items()))
        if observed != expected:
            disagreements.append(
                f"layer {index} emitted kinds {observed} against the planned "
                f"{expected}"
            )
    if dict(sorted(observed_unlayered_kinds.items())) != plan[
        "unlayered_kernels_by_kind"
    ]:
        disagreements.append(
            f"the unlayered path emitted kinds "
            f"{dict(sorted(observed_unlayered_kinds.items()))} against the "
            f"planned {plan['unlayered_kernels_by_kind']}"
        )
    if disagreements:
        raise DeepSeekV41KernelIRError(
            "the emitted graph is not the planned one:\n  "
            + "\n  ".join(disagreements[:20])
        )

    declared_symbols = {symbol.name for symbol in symbols}
    for tensor in builder.tensors:
        for extent in tensor.shape:
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV41KernelIRError(
                    f"tensor {tensor.tensor_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )
    for kernel in builder.kernels:
        for extent in kernel.iteration_domain.values():
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV41KernelIRError(
                    f"kernel {kernel.kernel_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )
    for resource in builder.states:
        if isinstance(resource.capacity_rows, Symbolic) and (
            resource.capacity_rows.symbol not in declared_symbols
        ):
            raise DeepSeekV41KernelIRError(
                f"state {resource.state_id} uses undeclared symbol "
                f"{resource.capacity_rows.symbol!r}"
            )

    generation_policy = {
        "bos_token_id": BOS_TOKEN_ID,
        "eos_token_ids": [EOS_TOKEN_ID],
        "eos_source": "config.json",
        "include_eos_in_output": True,
        "maximum_new_tokens": int(maximum_new_tokens),
        "policy_id": profile.generation_policy_id,
        "selection_mode": "greedy_argmax_lowest_id",
        "speculative_profile": False,
        "stochastic_sampling": (
            "not_expressible_in_the_frozen_neutral_registry; the released "
            "sample() draws Gumbel-max noise and no neutral kind produces or "
            "consumes an entropy stream, so this export declares the greedy "
            "boundary and carries the entropy input unchanged"
        ),
        "stop_condition": "first_official_eos_or_maximum_new_tokens",
        "tie_rule": "lowest_token_id",
        "vocabulary_size": VOCABULARY,
    }
    inputs = (token_ids, position_offset, session_ids, entropy)
    outputs = (appended, logits)
    state_ids = tuple(resource.state_id for resource in builder.states)
    graph = KernelGraph(
        model_id=profile.model_id,
        source={
            "architectural_max_context": ARCHITECTURAL_MAX_CONTEXT,
            "candidate_source_layer": profile.candidate_source_layer,
            "checkpoint_lock_id": lock["lock_id"],
            "checkpoint_payload_bytes": release.payload_bytes,
            "checkpoint_tensor_count": release.tensor_count,
            "config_sha256": release.config_sha256,
            "deployment_context_tokens": context_tokens,
            "engram_layer_ids": list(engram_layers),
            "engram_source_sha256": source_digests.get("inference/engram.py", ""),
            "index_source_layer_ids": list(index_sources),
            "kv_source_layer_ids": list(kv_sources),
            "model_source_sha256": source_digests.get("inference/model.py", ""),
            "profile": "target_only",
            "repository": profile.repository,
            "revision": profile.revision,
            "tensor_structure_sha256": release.tensor_structure_sha256,
            "tokenizer_sha256": release.tokenizer_sha256,
        },
        symbols=tuple(symbols),
        tensors=tuple(builder.tensors),
        states=tuple(builder.states),
        kernels=tuple(builder.kernels),
        entrypoints=(
            Entrypoint(
                phase="prefill",
                inputs=inputs,
                outputs=outputs,
                states=state_ids,
                generation_policy=profile.generation_policy_id,
            ),
            Entrypoint(
                phase="decode",
                inputs=inputs,
                outputs=outputs,
                states=state_ids,
                generation_policy=profile.generation_policy_id,
            ),
        ),
        numeric_profile=profile.numeric_profile,
        generation_policy=generation_policy,
    )
    errors = check_neutral(graph)
    if errors:
        raise DeepSeekV41KernelIRError(
            "neutral IR rejected:\n  " + "\n  ".join(errors[:40])
        )
    return graph


#: The frozen ABI 3.0 counter groups, as the neutral ``counter_class`` spells
#: them.  A kernel whose class is not one of these is *unpriced*: the deployment
#: has nowhere to count its work, which ADR-003 section 15 makes a compile error
#: rather than a missing statistic.
COUNTER_CLASSES = frozenset(
    name.lower() for name in ("INSTRUCTION", "ENGINE_QUEUE", "MEMORY", "TENSOR",
                              "VECTOR_REDUCTION", "ATTENTION", "ROUTE_EXPERT",
                              "STATE", "SELECTION_EOS", "COMMUNICATION",
                              "FAULT_RECOVERY", "LATENCY")
)


def graph_census_v41(
    graph: KernelGraph, profile: DeepSeekV41Profile = V41_FLASH_PROFILE
) -> dict[str, Any]:
    """The census gate DS41-I2 quotes, and the four counts it has to be zero on.

    The V4 census is the base -- one implementation, two models -- and this adds
    the per-layer view the analytical cross-check reads and the four
    exit-criterion counts, each of which is a *derived* set rather than a claim:

    ``unknown``
        a kernel whose kind is outside the neutral registry, or which no entry of
        the frozen lowering table maps to an ABI 3.0 operation, or whose numeric
        contract is not a canonical contract identifier.
    ``unpriced``
        a kernel whose counter class is empty or outside the frozen ABI 3.0
        counter groups, so its work would be counted nowhere.
    ``unreferenced``
        a declared tensor that no kernel reads, no kernel writes, no entrypoint
        names and no block-scaled tensor links as its scale -- a declaration with
        no reader, which two backends are free to place differently.
    ``unbound``
        a weight or constant with neither a checkpoint binding nor a declared
        generator, which is a tensor whose contents nothing states.
    """

    census = graph_census(graph)
    modes = profile.layer_modes()
    layers = profile.layers
    per_layer_kinds: list[Counter] = [Counter() for _ in range(layers)]
    per_layer_sources: list[Counter] = [Counter() for _ in range(layers)]
    unlayered_kinds: Counter = Counter()
    unlayered_sources: Counter = Counter()
    source_kinds: Counter = Counter()
    seen_operations: set[str] = set()
    for kernel in graph.kernels:
        source_kind = str(kernel.attributes.get("source_operation_kind", ""))
        first = kernel.source_operation_id not in seen_operations
        seen_operations.add(kernel.source_operation_id)
        if first:
            source_kinds[source_kind] += 1
        if kernel.layer is None:
            unlayered_kinds[kernel.kind] += 1
            if first:
                unlayered_sources[source_kind] += 1
        else:
            per_layer_kinds[kernel.layer][kernel.kind] += 1
            if first:
                per_layer_sources[kernel.layer][source_kind] += 1

    read: set[str] = set()
    written: set[str] = set()
    for kernel in graph.kernels:
        read.update(kernel.inputs)
        written.update(kernel.outputs)
    for entrypoint in graph.entrypoints:
        read.update(entrypoint.inputs)
        read.update(entrypoint.outputs)
    for tensor in graph.tensors:
        if tensor.scale_tensor_id:
            read.add(tensor.scale_tensor_id)
    unknown = [
        kernel.kernel_id
        for kernel in graph.kernels
        if kernel.kind not in OPERATION_KINDS
        or kernel.kind not in KERNEL_TO_ENGINE
        or not CONTRACT_PATTERN.match(kernel.numeric_contract)
    ]
    unpriced = [
        kernel.kernel_id
        for kernel in graph.kernels
        if kernel.counter_class not in COUNTER_CLASSES
    ]
    unreferenced = [
        tensor.tensor_id
        for tensor in graph.tensors
        if tensor.tensor_id not in read and tensor.tensor_id not in written
    ]
    unbound = [
        tensor.tensor_id
        for tensor in graph.tensors
        if tensor.role in {"weight", "constant"}
        and tensor.binding is None
        and not tensor.generator
    ]
    census.update(
        {
            "attention_modes_by_layer": [mode.plan_key for mode in modes],
            "layer_count": layers,
            "layers_by_attention_mode": dict(
                sorted(Counter(mode.plan_key for mode in modes).items())
            ),
            "per_layer_kernels_by_kind": [
                dict(sorted(item.items())) for item in per_layer_kinds
            ],
            "per_layer_source_kinds": [
                dict(sorted(item.items())) for item in per_layer_sources
            ],
            "source_kinds": dict(sorted(source_kinds.items())),
            "unlayered_kernels_by_kind": dict(sorted(unlayered_kinds.items())),
            "unlayered_source_kinds": dict(sorted(unlayered_sources.items())),
            "unknown": len(unknown),
            "unknown_kernels": sorted(unknown)[:20],
            "unpriced": len(unpriced),
            "unpriced_kernels": sorted(unpriced)[:20],
            "unreferenced": len(unreferenced),
            "unreferenced_tensors": sorted(unreferenced)[:20],
            "unbound": len(unbound),
            "unbound_tensors": sorted(unbound)[:20],
        }
    )
    return census


# ---------------------------------------------------------------------------
# Self-checks the plan has to pass whatever the checkpoint's state
# ---------------------------------------------------------------------------
def plan_defects(profile: DeepSeekV41Profile = V41_FLASH_PROFILE) -> list[str]:
    """Every way the lowering plan is not a legal IR plan, as strings.

    Cheap enough to run from a test and from the build tool: a kind that is not
    registered, a kind no engine lowers, a source kind with no numeric
    contract, an identifier carrying a term ``check_neutral`` forbids.
    """

    defects: list[str] = []
    kinds = source_kind_plan(profile, include_speculative=True)
    for source, neutral in sorted(kinds.items()):
        if source not in CONTRACT_BASE_BY_SOURCE_KIND:
            defects.append(f"{source} has no frozen numeric contract")
        else:
            contract_for(source)
        for kind in neutral:
            if kind not in OPERATION_KINDS:
                defects.append(f"{source} lowers to unregistered kind {kind}")
            elif kind not in KERNEL_TO_ENGINE:
                defects.append(f"{source} lowers to unlowerable kind {kind}")
    for name in sorted(set(kinds) | set(ATTENTION_MODES)):
        for term in FORBIDDEN_TERMS:
            if term in name.lower():
                defects.append(f"plan key {name} carries the forbidden term {term}")
    for base in sorted(set(CONTRACT_BASE_BY_SOURCE_KIND.values())):
        for term in FORBIDDEN_TERMS:
            if term in base:
                defects.append(f"contract {base} carries the forbidden term {term}")
    for mode in ATTENTION_MODES:
        if mode not in _ATTENTION_MODE_SOURCE_KINDS:
            defects.append(f"attention mode {mode} has no source-kind plan")
    # A plan entry no layer emits is a catalogue entry, not a lowering.  The
    # V4.1 index key and index weight projections are BF16 matmuls with their
    # own contracts, so a general ``BF16_LINEAR`` entry would sit here unused
    # and read as a mechanism this model has.
    used = set(unlayered_source_plan(profile))
    for layer in layer_source_plan(profile, include_speculative=True):
        used |= set(layer)
    for source in sorted(set(kinds) - used):
        defects.append(f"{source} is planned but no layer emits it")
    for source in sorted(used - set(kinds)):
        defects.append(f"{source} is emitted but the plan does not lower it")
    return defects


#: The released dtype AM-E10 added for the main compressed latent.
MAIN_LATENT_DTYPE = "fp4_e2m1_s16_e4m3"
if MAIN_LATENT_DTYPE not in DTYPES:  # pragma: no cover - AM-E10 landed
    raise DeepSeekV41KernelIRError(
        f"the neutral IR does not declare {MAIN_LATENT_DTYPE}; AM-E10 adds it"
    )


__all__ = [
    "ACTIVATION_BLOCK",
    "ARCHITECTURAL_MAX_CONTEXT",
    "ATTENTION_MODES",
    "FP4_INDEX_BLOCK",
    "FP4_MAIN_BLOCK",
    "CANDIDATE_PROFILE_PATH",
    "confront_source_digests",
    "CONTRACT_BASE_BY_SOURCE_KIND",
    "DEFAULT_CHECKPOINT_LOCK",
    "DEFAULT_CONTEXT_TOKENS",
    "DEFAULT_SNAPSHOT",
    "DeepSeekV41KernelIRError",
    "DeepSeekV41Profile",
    "ENGRAM_SOURCE_SHA256",
    "LOWERING_PLAN",
    "LayerMode",
    "MAIN_LATENT_DTYPE",
    "MODEL_ID",
    "MODEL_PROFILES",
    "V41_FLASH_REDUCED_PROFILE",
    "MODEL_SOURCE_SHA256",
    "SPECULATIVE_SOURCE_KINDS",
    "V41_FLASH_PROFILE",
    "attention_mode_plan",
    "confront_layer_modes",
    "contract_for",
    "export_deepseek_v41_kernel_graph",
    "COUNTER_CLASSES",
    "graph_census",
    "graph_census_v41",
    "layer_source_plan",
    "released_architecture_config",
    "lowering_plan",
    "missing_ir_artifacts",
    "plan_defects",
    "planned_census",
    "resolve_model_profile",
    "source_kind_plan",
    "unlayered_source_plan",
]
