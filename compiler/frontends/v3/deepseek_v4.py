"""Export a pinned DeepSeek-V4 checkpoint into Tensor Kernel IR v3.

This front end is the only place the DeepSeek-V4 forward is expressed for ABI
3.0.  The shared HBM/SRAM backend and the ROM backend consume the one document
it emits, so it carries complete model semantics and no backend concept: no
memory target, no schedule, no engine instance, no address (ADR-003 section 15,
enforced by ``compiler.ir.v3.kernel_ir.check_neutral``).

Which release is being exported is an argument.  :class:`DeepSeekV4Profile`
carries every parameter that differs between DeepSeek-V4-Flash-0731 and
DeepSeek-V4-Pro-0813 -- the released widths, read from the pinned configuration
in ``compiler.frontend.deepseek_v4_releases``, plus the numeric-profile and
generation-policy identities, which two models must not share -- and
``export_deepseek_v4_kernel_graph`` sizes everything from the profile it is
given.  The two releases ship the same ``inference/model.py`` byte for byte, so
a second model is a re-parameterisation of this export and not a second
derivation of its semantics.  Figures quoted below are the release profile's,
DeepSeek-V4-Flash-0731.

What it reuses rather than restates
-----------------------------------
* ``compiler.frontend.deepseek_v4_graph.build_official_graph_contract`` supplies
  the frozen 2,136-node, 46-operator-kind semantic graph -- 3,011 nodes over
  the same 46 kinds for Pro.  This module walks
  that graph node by node and lowers each node into one or more neutral
  kernels, so the neutral IR cannot drift from the source-mapped semantics and
  the census can be reported per source operator kind.
* ``compiler.frontend.deepseek_v4`` supplies the 72,317 :class:`TensorSpec`
  records for Flash and 149,782 for Pro -- exact name, storage dtype, shape,
  semantic role, scope, layer and expert -- derived from the released
  configuration.
* ``compiler.frontend.checkpoint`` supplies the hash-locked checkpoint whose
  shard headers are re-read here to derive each weight's exact byte range.
* ``runtime.reference.*`` supplies the bit-exact target-precision identity per
  source operator kind; each neutral kernel names the reference that owns its
  numeric contract, qualified by the sub-operation it implements.

Weight bindings
---------------
Every weight tensor carries a :class:`CheckpointBinding` naming the shard file,
the absolute byte offset (safetensors 8-byte length prefix + header length +
the header's ``data_offsets`` start), the byte length, and the SHA-256 of
exactly those bytes.  A backend turns that into an ABI 3.0 object source and
never materialises a private copy of the weight image, which is 156 GB on
Flash and 831 GB on Pro.  Paths are
relative to the checkpoint snapshot so the graph identity is reproducible on
any host that holds the pinned revision.

Block-scaled formats
--------------------
FP8-E4M3 and MXFP4-E2M1 payloads and their E8M0 scale payloads are separate
tensors linked by ``scale_tensor_id``.  ``scale_block_elements`` is the number
of contiguous logical elements **along the reduction axis** covered by one
scale value: 128 for the released 128x128 FP8 weight blocks, 32 for the MXFP4
expert weights, 128 for dynamic activation quantization, and 64 for the
attention KV quantize/dequantize round trip.  The scale tensor's own declared
shape carries the remaining geometry.

Speculation
-----------
``include_speculative`` selects the profile.  The first release graph is the
ordinary target-model path -- the main layers plus the head -- because
ADR-003 section 18 sequences ordinary DeepSeek generation before speculative
execution, and the DSpark verification/acceptance contract is still open
(DSV4-SEM-001).  Setting the flag adds the three ``mtp.*`` DSpark blocks, the
DSpark conditioning projection, the Markov draft head and the confidence head.

Required contract changes
-------------------------
Three source behaviours cannot be expressed in the frozen neutral registry.
No opcode is invented here; each is reported so it can be added through a
versioned change to ``compiler/ir/v3/kernel_ir.py`` and
``compiler/ir/v3/lowering.py``, never privately.

**IR3-GAP-1, stochastic token selection.**  ``inference/model.py:sample``
divides by an exponential draw and takes the argmax (Gumbel-max).  No neutral
kind produces or consumes randomness, so only the greedy branch is
expressible; this export emits ``SCALE`` + ``ARGMAX`` + ``TOKEN_APPEND`` and
declares the boundary in ``generation_policy``.  ``input.entropy_stream`` is
declared and carried unchanged so a later graph can bind it.  Proposal: add
``CATEGORICAL_SAMPLE`` taking (logits, temperature, entropy) and producing
(token, entropy_continuation), lowered to a new ``Selection`` subopcode.
Both-model impact: Qwen3 needs the same kind for any non-greedy request, so
until it exists both lanes are pinned to greedy argmax and neither can honour
the released ``do_sample: true`` generation configuration.

**IR3-GAP-2, predicated execution.**  ``Compressor.forward`` runs its pooling,
normalisation, rotation, quantize/dequantize and compressed-KV commit only at
a ratio-derived boundary, and the source graph carries that as a first-class
node ``guard`` over a boolean predicate value.  :class:`Kernel` has no
predicate field and no neutral kind produces a ``bool`` tensor, so this export
carries the guard in the ``execution_predicate`` attribute, which a backend is
not obliged to honour.

Amendment A18 widened that from one chain to a rule.  Four of this graph's ten
runtime symbols floor to zero at a legal request, and A18 settles what that
means: *"an extent that floors to zero is not a clamp ... ABI 3.0 has no
zero-extent view -- the verifier refuses one -- so 'the request has none of
this axis' is a* predicate *question, and the operator must be predicated off
rather than issued against an empty operand."*  Every kernel whose own extent
can floor is therefore declared here with its condition, in
``SYMBOL_PREDICATE_OPERATORS``' grammar, **including where the condition
repeats a neighbour's** -- a repeated declaration is checkable, and a predicate
a backend infers from a sibling kernel's attribute is not.  Two kernels are
deliberately *not* predicated and each says why on itself:
``ATTENTION_KV_VIEW`` and the two index joins carry A18's bias, so their own
extent is never zero and they are always issued -- what vanishes is one
*operand*, which they name in ``operand_present_predicate``; and
``COMPRESS_STATE_UPDATE`` writes its raw window on every step, so only its two
pooled outputs are conditional, which it names in ``conditional_outputs``.

Proposal: add ``predicate: str = ""`` to ``Kernel``,
let ``COMPRESS_STATE_UPDATE`` declare a ``bool`` predicate output, and have
``check_neutral`` require a predicate to be an earlier kernel's output.  ABI
3.0 already carries ``predicate_id`` on its loop descriptor, so the neutral IR
is the only layer missing the concept.  Both-model impact: Qwen3 has no
data-dependent predicate today, but every conditional, early-exit or
speculative profile in either lane needs one, including this model's own
speculative profile.

**IR3-GAP-3, stacked weights (closed by the segmented binding).**
``TENSOR.ROUTED_MATMUL``'s operand row is (activations, routed weights, expert
IDs, route weights), so the ``[E, N, K]`` stack is a *mandatory operand*.
:class:`CheckpointBinding` used to name exactly one contiguous byte range and
the released checkpoint interleaves a layer's experts, so no single
range covered a stack; this export therefore declared every routed expert
tensor individually -- 66,048 of them on Flash -- and named the ordered family
in an
``expert_weight_tensors`` attribute.  An attribute is not an operand: the
weight slot stayed empty, the expert IDs sat in it, and every routed
contraction named two of the three operands its engine requires.
:class:`CheckpointBinding` now carries ``segments``, so a stack is one declared
tensor whose payload is an ordered list of authenticated ranges -- each keeping
its own digest, so verification stays incremental rather than needing the
assembled 1 GiB image -- and the operand row is filled from the graph.  A
backend reads the per-expert structure back out of ``binding.segments``, which
names every member tensor, its shard, its offset and its digest.
Both-model impact: Qwen3-8B has no expert stack and is unaffected, but any
stacked weight -- mixture-of-experts, stacked adapters, or a tensor-parallel
shard set -- now has an operand instead of an attribute.

**IR3-GAP-4, computed constants (closed by amendment A9).**  ``check_neutral``
used to require every tensor whose role is ``constant`` to carry a
:class:`CheckpointBinding`, so a table that is *derived* rather than stored --
the YaRN rotary coefficient rows, the causal window index table, the
compressed-group enumeration -- could not be declared at all, and
TA-ABI3-OPCONV-1's ``VECTOR.ROPE`` ``in1`` "coefficient rows" slot went to the
position offset instead.  :class:`Tensor` now carries ``generator`` and
``generator_parameters``, so this export declares two rotary tables -- theta
10,000 unscaled for the pure sliding-window layers, theta 160,000 with the
committed YaRN interpolation for the compressed ones -- names
``deepseek_rope_coefficients_v1``, and gathers the rows an operator actually
reads.  The deployment binds the SHA-256 of the generator's output and the
device re-derives and re-checks it at load, so nothing is injected and nothing
is taken on trust.

The rows are ``cos[rotary_width] || sin[rotary_width]``, not
``cos[head_dim] || sin[head_dim]``: DeepSeek's rotation is *partial*.  Only the
final 64 channels of a 512- or 128-wide head rotate, and they rotate as 32
adjacent complex pairs rather than as a half-split, so the row spans the
rotated channels and repeats each pair's coefficient across the two channels it
multiplies.  ``aux_id_0`` -- which the frozen operand row already reserves for
the rotary width -- is what tells the engine how much of the axis moves; the
untouched prefix is carried through by the same operator rather than by a
separate movement, which is what the released kernel does and what the
reference's ``prefix_bf16_values_preserved`` counter reconciles.

**IR3-GAP-5, feature-axis concatenation (closed by amendment A17).**
``CONCAT`` lowers to ``REDUCTION.GROUPED_CONCAT``, which used to join on **axis
0** only: it took its output extent from the sum of its inputs' *leading*
extents and required every input to share the trailing shape.  Several sites in
this graph join on the feature axis instead -- the sparse-attention index
assembly (``COMPRESSED_DENSE_INDEX`` and ``INDEX_TOPK``, ``[span, 128] ++
[span, 384] -> [span, 512]``) and DSpark's target-hidden assembly -- and there
was no operator that did it.  The two backends disagreed about what to do, which
is the usual symptom: the shared HBM/SRAM planner re-expressed an axis-one
concatenation as one ``DMA.TRANSFER`` per column window (and its own independent
checker then objected that the kernel did not reach ``REDUCTION.3``), while the
ROM backend emitted the frozen operator and the engine refused the shape.

``REDUCTION.GROUPED_CONCAT`` now reads a join axis from ``aux_id_0``; ``NO_ID``
and ``0`` are the axis-0 join it always was, and ``1`` joins rank-2 operands on
their feature axis.  Every ``CONCAT`` this export emits states its axis, and the
one that did not -- ``DSPARK_MAIN_PROJECT``'s target-hidden assembly, a feature
join every reader was defaulting to a join of rows -- now does.  The change also
retired one kernel that was not a concatenation at all: DSpark's noise-embedding
expansion joined four copies of ``[rows, hidden]`` into ``[rows, 4, hidden]``,
which is a ``BROADCAST``, and is what ``HC_EXPAND`` had already been corrected
to.

Amendments A19 and A20 have since folded both *index* joins into
``ROUTE.INDEX_TOPK`` itself -- A19 the ratio-4 one, A20 the ratio-128 one -- so
the feature-axis joins this export still emits are DSpark's.  The axis is stated
on every one of them; what changed is that there are fewer of them to state it
on.

This is also what makes ``GROUPED_OUTPUT_PROJECT`` sayable; see below.

Arity notes
-----------
``KERNEL_TO_ENGINE`` records a nominal operand arity per kind and
TA-ABI3-OPCONV-1 freezes what each slot means.  This export never exceeds
either, and follows the released semantics where they use fewer operands:
``HEAD_RMS_NORM`` takes one input because the released query head norm is
unweighted; ``SWIGLU`` is binary per amendment A8,
with the clamp limit in the numeric contract; ``HYPER_CONNECT_PRE`` fills both
output views with what the ``VECTOR.MHC`` row names -- the pre/post coefficient
block and the Sinkhorn combination matrix -- and the branch input the released
``Block.hc_pre`` returns is emitted as the separate ``REDUCTION.EXPERT_SUM`` the
ABI leaves it to, with one ``SELECT`` per coefficient plane between them; and
``COMPRESSED_DENSE_INDEX`` is ``ROUTE.INDEX_TOPK`` with its score operand
absent, which is amendment A20: the dense family is the top-k family with the
ranking removed, and everything else about it -- the causal horizon counted in
compression groups, the rebase onto the joined KV rows, the compaction, the
ascending order -- is what A19 already put in that operator.  It used to reuse
``WINDOW_INDEX`` parameterised by ``index_family``, on the reasoning that both
enumerate causal indices from a position.  They do not: ``WINDOW_INDEX``
enumerates *absolute positions* of a sliding window and the dense family
enumerates *completed compression groups*, so the substitution emitted the
sliding-window block twice and nothing downstream could tell, every index it
named being a legal KV row.
``ATTENTION_SPARSE`` follows amendment A6 exactly: query, fused KV, index,
per-head sink.

Two operations were previously emitted as an operator that does not do what the
released model does, and each is now emitted as the one that does.  Neither
needed an amendment.

* The **compressor projection** is one operator over *both* matrices writing a
  packed ``[.., 2, N]`` row, and the state update adds the absolute position
  embedding itself.  Emitting two one-projection kernels and a separate
  ``VECTOR.ADD`` left the mandatory gate slot empty and would have added the
  position twice; the ``ADD`` was unexecutable in any case, because
  ``VECTOR.ADD`` implements ``bf16_add_rne_v1`` and that addition is binary32
  against a cyclic ``[ratio, W]`` table.
* The **token-to-expert route** reads ``tid2eid[token_id]`` over the shipped
  ``[129280, 6]`` table and keeps all six rows.  ``ROUTE.HASH_ROUTE`` computes
  ``table[mix32(key) % slots]`` and returns one destination; the exact row
  gather is ``TENSOR.EMBED_LOOKUP``, so the neutral kind is
  ``EMBEDDING_LOOKUP``.  Every entry is an expert ID in ``[0, 255]`` in the low
  word of a little-endian int64, which the ``table_element_reading`` attribute
  states, so a 32-bit reading of the table is exact.

One cross-lane observation: the frozen ``REDUCTION.EXPERT_SUM`` row reads
(contributions, weights, optional base), but the released DeepSeek expert
multiplies by its routing weight *before* the down projection -- confirmed by
the qualified references ``runtime/reference/swiglu.py:mxfp4_swiglu_bf16``,
which takes ``route_weight_binary32_codes``, and
``runtime/reference/dispatch.py:reduce_expert_outputs_bf16``, which takes none.
``EXPERT_REDUCE`` is therefore emitted as (routed contributions, shared base,
routed row expert identity) with an explicit
``routing_weight_application`` attribute; a backend that re-applies the weights
at the reduction would square them.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compiler.frontend.checkpoint import (
    CheckpointError,
    load_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    DeepSeekV4AdapterError,
    TensorSpec,
    build_official_tensor_specs,
    load_official_config,
    validate_official_checkpoint_lock,
)
from compiler.frontend.deepseek_v4_releases import (
    FLASH,
    PRO,
    DeepSeekV4Release,
)
from compiler.frontend.deepseek_v4_graph import (
    MODEL_SOURCE_SHA256,
    KERNEL_SOURCE_SHA256,
    OPERATOR_CATALOG,
    DeepSeekV4GraphError,
    build_official_graph_contract,
)
from compiler.ir.v3.kernel_ir import (
    TOKEN_DTYPE,
    BindingSegment,
    CheckpointBinding,
    Entrypoint,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from compiler.ir.v3.numeric import CONTRACT_PATTERN

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The DeepSeek-V4-Flash-0731 snapshot and lock, under the names the tests and
#: the build tool import.  Both are fields of that release's record; a build of
#: another release takes them from the record it names.
DEFAULT_SNAPSHOT = FLASH.snapshot
DEFAULT_CHECKPOINT_LOCK = FLASH.checkpoint_lock

#: Architectural capacity published for this model.  It is not the deployment
#: capacity: ADR-003 section 18 fixes a 200,000-token DeepSeek acceptance run,
#: and the first release targets the next power of two above it.
ARCHITECTURAL_MAX_CONTEXT = 1_048_576

#: Deployment maximum this export targets.  Every ``Symbolic`` maximum and every
#: state capacity below is derived from it.
DEFAULT_CONTEXT_TOKENS = 262_144

@dataclass(frozen=True)
class DeepSeekV4Profile:
    """Everything this exporter has to know that differs between releases.

    The record in :mod:`compiler.frontend.deepseek_v4_releases` carries the
    released facts -- identity, digests, the compression-ratio tables and the
    complete pinned root configuration.  A profile adds what only the neutral
    export names: the numeric-profile identity that owns every emitted kernel's
    precision contract, and the generation-policy identity the two entrypoints
    reference.  Both are per release, because a graph that shared either with
    another model could not be told apart from it in the numeric-qualification
    ledger.

    Every width below is read from the release's pinned configuration, so the
    exporter has one number per fact rather than a module constant beside the
    config value it is supposed to equal.  ``architecture_pins`` is the list
    the export confronts with the released ``config.json`` before it emits
    anything; a config that disagrees with the profile in any of those fields
    stops the build.
    """

    release: DeepSeekV4Release
    numeric_profile: str
    generation_policy_id: str

    # -- identity ---------------------------------------------------------
    @property
    def model_id(self) -> str:
        return self.release.model_id

    # -- released widths --------------------------------------------------
    @property
    def hidden(self) -> int:
        return int(self.release.scalar("hidden_size"))

    @property
    def hc_mult(self) -> int:
        return int(self.release.scalar("hc_mult"))

    @property
    def heads(self) -> int:
        return int(self.release.scalar("num_attention_heads"))

    @property
    def kv_heads(self) -> int:
        """One *fused* KV head: key and value share one 512-wide row."""

        return int(self.release.scalar("num_key_value_heads"))

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
    def top_k(self) -> int:
        return int(self.release.scalar("num_experts_per_tok"))

    @property
    def moe_intermediate(self) -> int:
        return int(self.release.scalar("moe_intermediate_size"))

    @property
    def sliding_window(self) -> int:
        return int(self.release.scalar("sliding_window"))

    @property
    def swiglu_limit(self) -> float:
        return float(self.release.scalar("swiglu_limit"))

    @property
    def route_scale(self) -> float:
        return float(self.release.scalar("routed_scaling_factor"))

    @property
    def draft_block(self) -> int:
        return int(self.release.scalar("dspark_block_size"))

    @property
    def markov_rank(self) -> int:
        return int(self.release.scalar("dspark_markov_rank"))

    @property
    def rms_epsilon(self) -> float:
        return float(self.release.scalar("rms_norm_eps"))

    @property
    def bos_token_id(self) -> int:
        return int(self.release.scalar("bos_token_id"))

    @property
    def eos_token_id(self) -> int:
        return int(self.release.scalar("eos_token_id"))

    @property
    def layers(self) -> int:
        return self.release.num_hidden_layers

    @property
    def target_layers(self) -> tuple[int, ...]:
        return tuple(int(layer) for layer in self.release.scalar("dspark_target_layer_ids"))

    @property
    def main_compress_ratios(self) -> tuple[int, ...]:
        return self.release.main_compress_ratios

    # -- derived ----------------------------------------------------------
    @property
    def hc_mix(self) -> int:
        """``(2 + hc_mult) * hc_mult`` mixing rows.

        The Sinkhorn split yields ``hc_mult`` pre, ``hc_mult`` post and
        ``hc_mult * hc_mult`` combination coefficients.
        """

        return (2 + self.hc_mult) * self.hc_mult

    @property
    def hc_coefficients(self) -> int:
        return self.hc_mult + self.hc_mult * self.hc_mult

    @property
    def output_join_levels(self) -> int:
        """CONCAT kernels in ``GROUPED_OUTPUT_PROJECT``'s feature-axis join.

        Amendment A17 joins the per-group products four views at a time, so
        eight blocks are two joins of four plus one of two -- three kernels --
        and sixteen are four joins of four plus one of four, which is five.
        """

        joins, remaining = 0, self.o_groups
        while remaining > 1:
            remaining = -(-remaining // 4)
            joins += remaining
        return joins

    @property
    def architecture_pins(self) -> tuple[tuple[str, Any], ...]:
        """Released config key and the value this export will use for it.

        Twelve of these move between the two pinned releases and the rest do
        not; all of them are checked, because a width that is not confronted
        with the config it claims to come from is a width that can drift
        silently.  ``routed_scaling_factor`` is the clearest case: nothing
        downstream would notice a route scale of 1.5 applied to a model whose
        released value is 2.5, because the product is finite either way.
        """

        return (
            ("hidden_size", self.hidden),
            ("hc_mult", self.hc_mult),
            ("num_attention_heads", self.heads),
            ("num_key_value_heads", self.kv_heads),
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
            ("num_experts_per_tok", self.top_k),
            ("moe_intermediate_size", self.moe_intermediate),
            ("sliding_window", self.sliding_window),
            ("swiglu_limit", self.swiglu_limit),
            ("routed_scaling_factor", self.route_scale),
            ("dspark_block_size", self.draft_block),
            ("dspark_markov_rank", self.markov_rank),
            ("dspark_target_layer_ids", list(self.target_layers)),
            ("rms_norm_eps", self.rms_epsilon),
            ("bos_token_id", self.bos_token_id),
            ("eos_token_id", self.eos_token_id),
            ("num_hidden_layers", self.layers),
            ("compress_ratios", self.release.compress_ratios),
        )


FLASH_PROFILE = DeepSeekV4Profile(
    release=FLASH,
    numeric_profile="deepseek_v4_flash_target_precision_v1",
    generation_policy_id="deepseek_v4_flash_greedy_argmax_v1",
)

#: DeepSeek-V4-Pro-0813.  The neutral semantics are the Flash ones -- the two
#: releases ship the same ``inference/model.py`` byte for byte -- so this
#: profile differs only in the released widths its record carries and in the
#: two identities above, which must not be shared: every emitted kernel's
#: numeric contract is recorded against ``numeric_profile``, and two models
#: under one profile id would be indistinguishable in the qualification ledger.
PRO_PROFILE = DeepSeekV4Profile(
    release=PRO,
    numeric_profile="deepseek_v4_pro_target_precision_v1",
    generation_policy_id="deepseek_v4_pro_greedy_argmax_v1",
)

MODEL_PROFILES: Mapping[str, DeepSeekV4Profile] = {
    profile.model_id: profile for profile in (FLASH_PROFILE, PRO_PROFILE)
}


def resolve_model_profile(
    model: str | DeepSeekV4Profile | DeepSeekV4Release = MODEL_ID,
) -> DeepSeekV4Profile:
    """Return the profile for a model id, a release record, or a profile."""

    if isinstance(model, DeepSeekV4Profile):
        return model
    if isinstance(model, DeepSeekV4Release):
        model = model.model_id
    try:
        return MODEL_PROFILES[model]
    except KeyError:
        raise DeepSeekV4KernelIRError(
            f"unknown DeepSeek-V4 model {model!r}; this front end carries "
            + ", ".join(sorted(MODEL_PROFILES))
        ) from None


#: The DeepSeek-V4-Flash-0731 profile's values, under the names this module and
#: its tests have always used.  A build reads the profile it was given; these
#: stay because the release profile is the default one.
NUMERIC_PROFILE = FLASH_PROFILE.numeric_profile
GENERATION_POLICY_ID = FLASH_PROFILE.generation_policy_id

EOS_TOKEN_ID = FLASH_PROFILE.eos_token_id
BOS_TOKEN_ID = FLASH_PROFILE.bos_token_id

#: Architectural widths taken from the released configuration and re-checked
#: against it in :func:`export_deepseek_v4_kernel_graph`.
HIDDEN = FLASH_PROFILE.hidden
HC_MULT = FLASH_PROFILE.hc_mult
HEADS = FLASH_PROFILE.heads
KV_HEADS = FLASH_PROFILE.kv_heads
HEAD_DIM = FLASH_PROFILE.head_dim
ROPE_DIM = FLASH_PROFILE.rope_dim
NOPE_DIM = FLASH_PROFILE.nope_dim
Q_RANK = FLASH_PROFILE.q_rank
O_GROUPS = FLASH_PROFILE.o_groups
O_RANK = FLASH_PROFILE.o_rank
INDEX_HEADS = FLASH_PROFILE.index_heads
INDEX_HEAD_DIM = FLASH_PROFILE.index_head_dim
INDEX_TOPK = FLASH_PROFILE.index_topk
VOCABULARY = FLASH_PROFILE.vocabulary
ROUTED_EXPERTS = FLASH_PROFILE.routed_experts
TOP_K = FLASH_PROFILE.top_k
MOE_INTERMEDIATE = FLASH_PROFILE.moe_intermediate
SLIDING_WINDOW = FLASH_PROFILE.sliding_window
SWIGLU_LIMIT = FLASH_PROFILE.swiglu_limit
ROUTE_SCALE = FLASH_PROFILE.route_scale
DRAFT_BLOCK = FLASH_PROFILE.draft_block
MARKOV_RANK = FLASH_PROFILE.markov_rank
RMS_EPSILON = FLASH_PROFILE.rms_epsilon
HC_MIX = FLASH_PROFILE.hc_mix
HC_COEFFICIENTS = FLASH_PROFILE.hc_coefficients

#: The official default sampling temperature, as the released generation
#: configuration states it: binary32 one.  ABI 3.0's submission record carries
#: no temperature field (``runtime.abi3.records.Submission``), so a graph that
#: reads the temperature out of a *request* input reads an object no request
#: can ever write.  It is a deployment constant, and this is its value.
OFFICIAL_DEFAULT_TEMPERATURE_BINARY32 = 0x3F800000


def binary32_bits(value: float) -> int:
    """One real number as the binary32 bit pattern a NUMERIC descriptor holds.

    ``VECTOR.SCALE`` sub-case 0 multiplies by the numeric profile's
    ``scale_bits`` and by nothing else, and both backends fill that field from
    a fixed list of attribute spellings ending in ``_bits``/``_binary32`` or
    named ``scale``.  A constant stated under any other name -- ``factor``, as
    this export once spelled the route scale -- is not a missed optimisation:
    the field stays zero, the engine multiplies by binary32 zero, and every
    value the operation produces is zero without a trap.  So a scale this
    export emits is emitted as ``scale_bits`` and converted here.
    """
    return int.from_bytes(struct.pack("<f", float(value)), "little")


#: Grammar for ``execution_predicate``.  Two forms, both a plain string so the
#: attribute keeps one type:
#:
#: * a **value name** -- the ``kernel_id.output`` of an earlier kernel that
#:   declares a predicate output.  ``main.layerNN.compress_state.should_compress``
#:   is the only one this model produces, and it carries the released
#:   ``(start_pos + 1) % ratio == 0`` decode condition, which no comparison over
#:   the declared symbols can state.
#: * a **symbol comparison** -- ``"<symbol> <op> <integer>"`` over a declared
#:   runtime symbol, with ``<op>`` drawn from the frozen ``comparisons``
#:   registry (``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``).  It lowers to ABI
#:   3.0 predicate kind ``COMPARE_SYMBOL`` and needs no operand and no engine.
#:
#: Amendment A18 is what forces the second form: "an extent that floors to zero
#: is not a clamp ... ABI 3.0 has no zero-extent view -- the verifier refuses
#: one -- so 'the request has none of this axis' is a *predicate* question, and
#: the operator must be predicated off rather than issued against an empty
#: operand."  Four of this graph's ten runtime symbols floor to zero at a legal
#: request -- ``span_groups_ratio4``, ``span_groups_ratio128``,
#: ``context_groups_ratio4`` and ``context_groups_ratio128`` -- and every
#: kernel that leads with one of them is a kernel that must say when it is not
#: to be issued.  The exporter says it on **each** such kernel, including where
#: the condition repeats a neighbour's, because a repeated declaration is
#: checkable and an inference from a sibling's attribute is not.
SYMBOL_PREDICATE_OPERATORS = ("==", "!=", "<", "<=", ">", ">=")


def _nonempty(extent: Symbolic) -> str:
    """The ``execution_predicate`` for a kernel whose extent can floor to zero."""

    return f"{extent.symbol} > 0"

#: Dynamic activation quantization block used by ``inference/kernel.py``.
ACTIVATION_BLOCK = 128
#: Block used by the in-place attention KV quantize/dequantize round trip.
KV_QUANT_BLOCK = 64
#: Block used by the MXFP4 expert weights and the indexer FP4 round trip.
FP4_BLOCK = 32
#: Block used by the released 128x128 FP8 weight scales.
FP8_WEIGHT_BLOCK = 128


class DeepSeekV4KernelIRError(RuntimeError):
    """Raised when the pinned DeepSeek source cannot produce a neutral graph."""


# ---------------------------------------------------------------------------
# Source-kind to neutral-kind plan
# ---------------------------------------------------------------------------
#: Every source operator kind and the ordered neutral kinds it lowers to.  A
#: source kind with more than one entry needs several neutral kernels; none
#: invents an opcode.  ``QUANTIZE`` steps marked ``shared`` are emitted once per
#: distinct activation value, so a node that reuses an already quantized
#: activation contributes fewer kernels than this plan lists.
def lowering_plan(
    profile: DeepSeekV4Profile = FLASH_PROFILE,
) -> Mapping[str, tuple[str, ...]]:
    """One profile's source-kind to neutral-kind plan.

    Two entries are shaped by the released configuration: the grouped output
    projection emits one ``SELECT``/``MATMUL`` pair per output group and joins
    the results four views at a time, and the Markov loop repeats its five
    kernels once per draft-block step.  Everything else is the same lowering
    for either release, because both ship the same ``inference/model.py``.
    """

    return {
        "ATTENTION_KV_VIEW": ("CONCAT",),
        "BF16_LINEAR": ("MATMUL",),
        "BINARY32_TO_BF16": ("CONVERT",),
        "BIASED_TOPK_ROUTE": ("BIASED_TOPK",),
        # Amendment A20: the dense compressed index is ``ROUTE.INDEX_TOPK`` with
        # its score operand absent, not a window enumeration joined to a window.
        "COMPRESSED_DENSE_INDEX": ("INDEX_TOPK",),
        "COMPRESSED_KV_VALID_VIEW": ("STATE_READ",),
        "COMPRESS_KV_WRITE": ("KV_APPEND",),
        "COMPRESS_POOL": ("COMPRESS_POOL",),
        "COMPRESS_PROJECT": ("COMPRESS_PROJECT",),
        "COMPRESS_STATE_UPDATE": ("COMPRESS_STATE_UPDATE",),
        "CONFIDENCE_SCORE": ("CONCAT", "MATMUL"),
        "DSPARK_MAIN_PROJECT": ("CONCAT", "QUANTIZE", "MATMUL", "RMS_NORM"),
        "DSPARK_NOISE_EMBED": ("SCATTER", "EMBEDDING_LOOKUP", "BROADCAST"),
        "DSPARK_PREFILL_KV": (
            "QUANTIZE",
            "MATMUL",
            "RMS_NORM",
            "ROPE",
            "QUANTIZE",
            "DEQUANTIZE",
            "KV_APPEND",
        ),
        "DSPARK_WINDOW_INDEX": ("WINDOW_INDEX",),
        "EXPERT_DISPATCH": ("EXPERT_DISPATCH",),
        "EXPERT_REDUCE": ("EXPERT_REDUCE",),
        "FP4_QDQ": ("QUANTIZE", "DEQUANTIZE"),
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
        # Amendment A17.  The released projection is block diagonal over
        # features, which is one contraction per column block and a
        # feature-axis join, not one ``GROUPED_MATMUL`` over a row partition
        # that does not exist.  A join takes four input views, so eight blocks
        # are a tree of three ``CONCAT`` kernels and sixteen are a tree of
        # five.
        "GROUPED_OUTPUT_PROJECT": (
            ("COPY",)
            + ("SELECT", "MATMUL") * profile.o_groups
            + ("CONCAT",) * profile.output_join_levels
        ),
        "HADAMARD_ROTATE": ("HADAMARD",),
        "HASH_ROUTE": ("EMBEDDING_LOOKUP",),
        "HC_EXPAND": ("BROADCAST",),
        "HC_HEAD": ("HYPER_CONNECT_HEAD",),
        "HC_POST": ("HYPER_CONNECT_POST",),
        "HC_PRE": ("HYPER_CONNECT_PRE", "SELECT", "SELECT", "EXPERT_REDUCE"),
        "HEAD_RMS_NORM": ("HEAD_RMS_NORM",),
        "INDEX_SCORE": ("INDEX_SCORE",),
        "INDEX_TOPK": ("INDEX_TOPK", "CONCAT"),
        "KV_WINDOW_WRITE": ("KV_APPEND",),
        "LM_HEAD": ("LAST_TOKEN_SELECT", "VOCAB_PROJECT"),
        "MARKOV_AUTOREGRESSIVE_LOOP": (
            "EMBEDDING_LOOKUP",
            "VOCAB_PROJECT",
            "ADD",
            "ARGMAX",
            "TOKEN_APPEND",
        )
        * profile.draft_block
        + ("CONCAT", "CONCAT", "CONCAT", "CONCAT"),
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
        # The compressor rotates one row per pooled group and the released prefill
        # strides the coefficient table by the compression ratio, so its rows are
        # gathered under the rotation's own predicate; every other call site shares
        # one span-indexed gather emitted once for the whole graph.
        "ROPE_APPLY": ("GATHER", "ROPE"),
        "ROPE_INVERSE": ("ROPE_INVERSE",),
        "ROUTER_SCORE": ("ROUTER_SCORE",),
        "ROUTER_WEIGHT_NORMALIZE": ("GATHER", "WEIGHT_NORMALIZE", "SCALE"),
        "SAMPLE": ("SCALE", "ARGMAX", "TOKEN_APPEND"),
        "SPARSE_ATTENTION": ("ATTENTION_SPARSE",),
        "SQRT_SOFTPLUS": ("SQRT_SOFTPLUS",),
        "TARGET_HIDDEN_CAPTURE": ("PARTITION_SUM", "SCALE"),
        "TOKEN_EMBED": ("EMBEDDING_LOOKUP",),
        "WINDOW_INDEX": ("WINDOW_INDEX",),
    }


#: The release profile's plan, under the name the tests and the census import.
LOWERING_PLAN: Mapping[str, tuple[str, ...]] = lowering_plan(FLASH_PROFILE)


#: Canonical numeric-contract base per source operator kind.  ADR-003 section 15
#: forbids the neutral IR from naming an implementation location, so these are
#: opaque semantic identifiers, not module paths: renaming or moving anything
#: under ``runtime/reference/`` must not change a published ``graph_id``.  The
#: names were derived once from the qualified reference that owns each kind's
#: target-precision identity and are frozen here; they are deliberately *not*
#: recomputed from that module.  A kernel that implements only part of a
#: reference appends its sub-operation, so ``MXFP4_SWIGLU``'s gate contraction
#: is ``mxfp4_swiglu_bf16_gate_contraction_v1``.
#:
#: Several of these differ from the Qwen contract of the same name in kind, and
#: where the ABI has already frozen a name for that difference this table uses
#: *that* name rather than a second one of its own.  Amendment A8 names the two
#: RMSNorm contracts ``qwen3_rmsnorm_fp32_bf16_v1`` -- BF16 materialised before
#: the gain multiply -- and ``deepseek_rmsnorm_binary32_v1``, which stays in
#: binary32 through it; they disagree by one ulp on roughly 27 % of elements,
#: and the engine dispatches on the name.  This export previously wrote
#: ``normalization_rms_norm_bf16_v1``, which describes the same arithmetic under
#: a name no engine recognises, so every RMSNorm in the graph was refused at
#: execution.  A frozen contract identity is not an exporter's to restate.
CONTRACT_VERSION = 1

CONTRACT_BASE_BY_SOURCE_KIND: Mapping[str, str] = {
    "ATTENTION_KV_VIEW": "attention_kv_view_bf16",
    "BF16_LINEAR": "matrix_bf16_linear_bf16",
    "BIASED_TOPK_ROUTE": "selection_biased_topk_route_indices",
    "BINARY32_TO_BF16": "conversion_binary32_tensor_to_bf16_rne",
    "COMPRESSED_DENSE_INDEX": "indexing_compressed_dense_indices",
    "COMPRESSED_KV_VALID_VIEW": "compressed_kv_valid_view_bf16",
    "COMPRESS_KV_WRITE": "compressed_kv_write_bf16",
    "COMPRESS_POOL": "compression_pool_compress_pool_f32",
    "COMPRESS_PROJECT": "compression_compress_project_bf16",
    "COMPRESS_STATE_UPDATE": "compression_state_compress_state_update_f32",
    "CONFIDENCE_SCORE": "confidence_score_bf16",
    "DSPARK_MAIN_PROJECT": "dspark_main_project_bf16",
    "DSPARK_NOISE_EMBED": "structural_dspark_noise_embed_bf16",
    "DSPARK_PREFILL_KV": "dspark_prefill_kv_bf16",
    "DSPARK_WINDOW_INDEX": "indexing_dspark_window_indices",
    "EXPERT_DISPATCH": "dispatch_routed_experts_bf16",
    "EXPERT_REDUCE": "dispatch_reduce_expert_outputs_bf16",
    "FP4_QDQ": "quantization_fp4_qdq_bf16",
    "FP8_LINEAR": "matrix_dense_fp8_linear_bf16",
    "FP8_QDQ": "quantization_fp8_qdq_bf16",
    "FP8_SWIGLU": "fp8_swiglu_bf16",
    "GROUPED_OUTPUT_PROJECT": "grouped_output_project_bf16",
    "HADAMARD_ROTATE": "hadamard_rotate_128_bf16",
    "HASH_ROUTE": "lookup_hash_route_indices",
    "HC_EXPAND": "structural_hc_expand_bf16",
    "HC_HEAD": "hc_head_bf16",
    "HC_POST": "vector_hc_post_bf16",
    "HC_PRE": "hyper_connection_hc_pre_bf16",
    "HEAD_RMS_NORM": "normalization_head_rms_norm_bf16",
    "INDEX_SCORE": "index_score_bf16",
    "INDEX_TOPK": "selection_index_topk_indices",
    "KV_WINDOW_WRITE": "kv_window_write_bf16",
    "LM_HEAD": "lm_head_bf16",
    "MARKOV_AUTOREGRESSIVE_LOOP": "markov_loop_markov_autoregressive_loop_bf16",
    "MXFP4_SWIGLU": "mxfp4_swiglu_bf16",
    # Amendment A8's frozen identity for the binary32-through-the-gain-multiply
    # RMSNorm.  It names a contract, not a model's implementation location, and
    # the engine dispatches on it.
    "RMS_NORM": "deepseek_rmsnorm_binary32",
    "ROPE_APPLY": "rope_apply_bf16",
    "ROPE_INVERSE": "rope_inverse_bf16",
    "ROUTER_SCORE": "routing_router_score_bf16",
    "ROUTER_WEIGHT_NORMALIZE": "routing_normalize_routed_weight_codes",
    "SAMPLE": "sampling_deepseek_v4_sample_binary32",
    "SPARSE_ATTENTION": "sparse_attention_bf16",
    "SQRT_SOFTPLUS": "sqrt_softplus_router_binary32",
    "TARGET_HIDDEN_CAPTURE": "vector_target_hidden_capture_bf16",
    "TOKEN_EMBED": "lookup_bf16_token_embedding",
    "WINDOW_INDEX": "indexing_window_indices",
}

#: Counter namespace per neutral kind, named with the ABI 3.0 counter groups in
#: ``runtime.abi3.constants.CounterGroup`` rather than an engine instance.
COUNTER_CLASS_BY_KIND: Mapping[str, str] = {
    "ADD": "vector_reduction",
    "ARGMAX": "selection_eos",
    "ATTENTION_SPARSE": "attention",
    "BIASED_TOPK": "route_expert",
    "BROADCAST": "memory",
    "CONCAT": "vector_reduction",
    "COPY": "memory",
    "SCATTER": "memory",
    "CONVERT": "vector_reduction",
    "COMPRESS_POOL": "attention",
    "COMPRESS_PROJECT": "tensor",
    "COMPRESS_STATE_UPDATE": "state",
    "DEQUANTIZE": "vector_reduction",
    "EMBEDDING_LOOKUP": "tensor",
    "EXPERT_DISPATCH": "route_expert",
    "EXPERT_REDUCE": "route_expert",
    "GATHER": "memory",
    "GROUPED_MATMUL": "tensor",
    "HADAMARD": "vector_reduction",
    "HASH_ROUTE": "route_expert",
    "HEAD_RMS_NORM": "vector_reduction",
    "HYPER_CONNECT_HEAD": "vector_reduction",
    "HYPER_CONNECT_POST": "vector_reduction",
    "HYPER_CONNECT_PRE": "vector_reduction",
    "INDEX_SCORE": "attention",
    "INDEX_TOPK": "route_expert",
    "KV_APPEND": "state",
    "LAST_TOKEN_SELECT": "memory",
    "MATMUL": "tensor",
    "MUL": "vector_reduction",
    "PARTITION_SUM": "vector_reduction",
    "QUANTIZE": "vector_reduction",
    "RMS_NORM": "vector_reduction",
    "ROPE": "vector_reduction",
    "ROPE_INVERSE": "vector_reduction",
    "ROUTED_MATMUL": "tensor",
    "ROUTER_SCORE": "route_expert",
    "SCALE": "vector_reduction",
    "SELECT": "memory",
    "STATE_READ": "state",
    "SQRT_SOFTPLUS": "vector_reduction",
    "SWIGLU": "vector_reduction",
    "TOKEN_APPEND": "selection_eos",
    "VOCAB_PROJECT": "tensor",
    "WEIGHT_NORMALIZE": "route_expert",
    "WINDOW_INDEX": "route_expert",
}

#: Attribute keys of the source graph that carry a term ``check_neutral``
#: forbids.  Each is renamed, never dropped, so no source semantics are lost.
_NEUTRAL_ATTRIBUTE_KEY: Mapping[str, str] = {
    "cache_slot": "cache_row",
    "duplicate_slot_order": "duplicate_selection_order",
    "duplicate_slot_policy": "duplicate_selection_policy",
    "kv_read_bytes_per_valid_slot": "kv_read_bytes_per_valid_row",
    "stages": "butterfly_levels",
    "state_slots": "state_rows",
}

_STORAGE_DTYPE: Mapping[str, str] = {
    "BF16": "bf16",
    "F32": "fp32",
    "F8_E4M3": "fp8_e4m3fn",
    "F8_E8M0": "e8m0",
    "I8": "i8",
    "I64": "i64",
}


# ---------------------------------------------------------------------------
# Checkpoint bindings
# ---------------------------------------------------------------------------
def read_checkpoint_bindings(
    snapshot: Path, lock: Mapping[str, Any]
) -> dict[str, CheckpointBinding]:
    """Derive every weight's exact byte range from the real safetensors headers.

    A safetensors tensor payload starts at ``8 + header_length +
    data_offsets[0]``: eight bytes of little-endian header length, the JSON
    header itself, then the contiguous data segment.  Every header is re-read
    here and required to match the hash-locked header and tensor records, so a
    binding cannot drift from the locked checkpoint.
    """

    bindings: dict[str, CheckpointBinding] = {}
    for shard in lock["shards"]:
        relative = shard["path"]
        path = Path(snapshot) / relative
        try:
            with path.open("rb") as handle:
                prefix = handle.read(8)
                if len(prefix) != 8:
                    raise DeepSeekV4KernelIRError(
                        f"shard {relative!r} has no header length prefix"
                    )
                header_length = struct.unpack("<Q", prefix)[0]
                if header_length != shard["header_length_bytes"]:
                    raise DeepSeekV4KernelIRError(
                        f"shard {relative!r} header length differs from the lock"
                    )
                raw_header = handle.read(header_length)
        except OSError as exc:
            raise DeepSeekV4KernelIRError(
                f"cannot read shard {relative!r}: {exc}"
            ) from exc
        if len(raw_header) != header_length:
            raise DeepSeekV4KernelIRError(f"shard {relative!r} header is truncated")
        if hashlib.sha256(raw_header).hexdigest() != shard["header_sha256"]:
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header differs from the checkpoint lock"
            )
        try:
            header = json.loads(raw_header.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header is not valid JSON: {exc}"
            ) from exc
        payload_start = 8 + header_length
        entries = {
            name: value for name, value in header.items() if name != "__metadata__"
        }
        locked = {record["name"]: record for record in shard["tensors"]}
        if set(entries) != set(locked):
            raise DeepSeekV4KernelIRError(
                f"shard {relative!r} header tensors differ from the checkpoint lock"
            )
        for name in sorted(entries):
            entry = entries[name]
            record = locked[name]
            start, end = entry["data_offsets"]
            if (
                [start, end] != list(record["data_offsets"])
                or entry["dtype"] != record["dtype"]
                or list(entry["shape"]) != list(record["shape"])
                or end - start != record["size_bytes"]
            ):
                raise DeepSeekV4KernelIRError(
                    f"tensor {name!r} in {relative!r} differs from the checkpoint lock"
                )
            if name in bindings:
                raise DeepSeekV4KernelIRError(f"tensor {name!r} appears in two shards")
            bindings[name] = CheckpointBinding(
                source_name=name,
                path=relative,
                offset=payload_start + start,
                bytes=record["size_bytes"],
                sha256=record["payload_sha256"],
                transform="identity",
            )
    return bindings


def split_binding_by_leading_groups(
    snapshot: Path, binding: CheckpointBinding, groups: int, rows: int
) -> tuple[CheckpointBinding, ...]:
    """Split one contiguous binding into ``groups`` equal leading-axis ranges.

    A block-diagonal projection reads one group's rows of a stacked weight, and
    a group of a row-major ``[rows, ...]`` tensor is a *contiguous* byte range,
    so every group is an ordinary :class:`CheckpointBinding` -- same shard, same
    transform, its own offset and length.  What it does not have is a digest,
    because the checkpoint lock only knows the whole tensor.

    So the digests are derived here, in one sequential pass: each group's range
    is hashed as it is read and the whole tensor is hashed alongside it, and the
    split is accepted only when the whole-tensor digest reproduces the locked
    one.  That is what makes a per-group binding as authenticated as the tensor
    it comes from -- the group digests are not asserted, they are computed from
    the same bytes that reproduce a hash this repository did not choose.
    """
    if groups < 1 or rows % groups:
        raise DeepSeekV4KernelIRError(
            f"{binding.source_name!r}: {rows} rows do not divide into {groups} "
            "groups"
        )
    if binding.segments:
        raise DeepSeekV4KernelIRError(
            f"{binding.source_name!r}: a segmented binding has no single range "
            "to split"
        )
    if binding.bytes % groups:
        raise DeepSeekV4KernelIRError(
            f"{binding.source_name!r}: {binding.bytes} bytes do not divide into "
            f"{groups} groups"
        )
    extent = binding.bytes // groups
    whole = hashlib.sha256()
    parts: list[CheckpointBinding] = []
    path = Path(snapshot) / binding.path
    try:
        with path.open("rb") as handle:
            handle.seek(binding.offset)
            for group in range(groups):
                digest = hashlib.sha256()
                remaining = extent
                while remaining:
                    chunk = handle.read(min(remaining, 1 << 23))
                    if not chunk:
                        raise DeepSeekV4KernelIRError(
                            f"short read for {binding.source_name!r} group {group}"
                        )
                    digest.update(chunk)
                    whole.update(chunk)
                    remaining -= len(chunk)
                parts.append(
                    CheckpointBinding(
                        # The source name stays the checkpoint tensor's: these
                        # are ranges *of* it, not tensors the checkpoint has.
                        source_name=binding.source_name,
                        path=binding.path,
                        offset=binding.offset + group * extent,
                        bytes=extent,
                        sha256=digest.hexdigest(),
                        transform=binding.transform,
                    )
                )
    except OSError as exc:
        raise DeepSeekV4KernelIRError(
            f"cannot read {binding.source_name!r} from {binding.path!r}: {exc}"
        ) from exc
    if whole.hexdigest() != binding.sha256:
        raise DeepSeekV4KernelIRError(
            f"{binding.source_name!r}: the {groups} group ranges reassemble to "
            "a payload whose SHA-256 differs from the locked checkpoint's"
        )
    return tuple(parts)


def verify_checkpoint_bindings(
    snapshot: Path,
    graph: KernelGraph,
    *,
    sample: int = 8,
) -> list[dict[str, Any]]:
    """Re-read ``sample`` bound byte ranges and confirm the recorded SHA-256.

    The sample is deterministic: it is spread evenly across the bound tensors
    in declaration order, so the same graph always verifies the same ranges.
    """

    bound = [t for t in graph.tensors if t.binding is not None]
    if not bound:
        raise DeepSeekV4KernelIRError("graph declares no bound weight tensor")
    count = max(1, min(sample, len(bound)))
    step = max(1, len(bound) // count)
    records: list[dict[str, Any]] = []
    def _range_digest(path: Path, offset: int, length: int, label: str) -> str:
        digest = hashlib.sha256()
        remaining = length
        with path.open("rb") as handle:
            handle.seek(offset)
            while remaining:
                chunk = handle.read(min(remaining, 1 << 24))
                if not chunk:
                    raise DeepSeekV4KernelIRError(f"short read for {label!r}")
                digest.update(chunk)
                remaining -= len(chunk)
        return digest.hexdigest()

    for tensor in bound[:: step][:count]:
        binding = tensor.binding
        assert binding is not None
        if binding.segments:
            # A segmented binding has no single range to re-read: its payload is
            # the ordered concatenation of the segments and its own digest binds
            # their order, so each segment is verified against its own SHA-256
            # and the composite is recomputed from those.  Verifying the whole
            # assembled image instead would read the stack twice for no more
            # assurance.
            composite = hashlib.sha256()
            for segment in binding.segments:
                observed = _range_digest(
                    Path(snapshot) / segment.path,
                    segment.offset,
                    segment.bytes,
                    segment.source_name,
                )
                if observed != segment.sha256:
                    raise DeepSeekV4KernelIRError(
                        f"{segment.source_name!r} payload differs from its "
                        "recorded SHA-256"
                    )
                composite.update(bytes.fromhex(observed))
            observed = composite.hexdigest()
            if observed != binding.sha256:
                raise DeepSeekV4KernelIRError(
                    f"{binding.source_name!r} segment order differs from its "
                    "recorded composite SHA-256"
                )
            records.append(
                {
                    "bytes": binding.bytes,
                    "offset": binding.offset,
                    "path": binding.path,
                    "segments": len(binding.segments),
                    "sha256": observed,
                    "tensor_id": tensor.tensor_id,
                }
            )
            continue
        observed = _range_digest(
            Path(snapshot) / binding.path,
            binding.offset,
            binding.bytes,
            binding.source_name,
        )
        if observed != binding.sha256:
            raise DeepSeekV4KernelIRError(
                f"{binding.source_name!r} payload differs from its recorded SHA-256"
            )
        records.append(
            {
                "bytes": binding.bytes,
                "offset": binding.offset,
                "path": binding.path,
                "sha256": observed,
                "tensor_id": tensor.tensor_id,
            }
        )
    return records


def _neutral_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Rename the source attribute keys that carry a forbidden backend term."""

    out: dict[str, Any] = {}
    for key, value in attributes.items():
        out[_NEUTRAL_ATTRIBUTE_KEY.get(key, key)] = value
    return out


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------
class _Builder:
    """Accumulate tensors, states and kernels in emission order."""

    def __init__(self) -> None:
        self.tensors: list[Tensor] = []
        self.kernels: list[Kernel] = []
        self.states: list[StateResource] = []
        self._tensor_ids: set[str] = set()
        self._state_ids: set[str] = set()
        self.shape: dict[str, tuple[Any, ...]] = {}
        self.dtype: dict[str, str] = {}
        self.kernels_by_source_kind: Counter = Counter()
        self.kernels_by_kind: Counter = Counter()

    def tensor(
        self,
        tensor_id: str,
        dtype: str,
        shape: tuple[Any, ...],
        role: str,
        *,
        binding: CheckpointBinding | None = None,
        scale_tensor_id: str | None = None,
        scale_block_elements: int = 0,
        generator: str = "",
        generator_parameters: Mapping[str, Any] | None = None,
    ) -> str:
        if tensor_id in self._tensor_ids:
            raise DeepSeekV4KernelIRError(f"duplicate tensor {tensor_id!r}")
        self._tensor_ids.add(tensor_id)
        self.tensors.append(
            Tensor(
                tensor_id=tensor_id,
                dtype=dtype,
                shape=tuple(shape),
                role=role,
                binding=binding,
                scale_tensor_id=scale_tensor_id,
                scale_block_elements=scale_block_elements,
                generator=generator,
                generator_parameters=dict(generator_parameters or {}),
            )
        )
        self.shape[tensor_id] = tuple(shape)
        self.dtype[tensor_id] = dtype
        return tensor_id

    def has_tensor(self, tensor_id: str) -> bool:
        return tensor_id in self._tensor_ids

    def has_state(self, state_id: str) -> bool:
        return state_id in self._state_ids

    def state(self, resource: StateResource) -> str:
        if resource.state_id in self._state_ids:
            return resource.state_id
        self._state_ids.add(resource.state_id)
        self.states.append(resource)
        return resource.state_id

    def kernel(
        self,
        kernel_id: str,
        kind: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        *,
        numeric_contract: str,
        iteration_domain: Mapping[str, Any],
        attributes: Mapping[str, Any],
        source_operation_id: str,
        source_kind: str,
        phases: Sequence[str] = ("prefill", "decode"),
        layer: int | None = None,
        state_reads: Sequence[str] = (),
        state_writes: Sequence[str] = (),
    ) -> None:
        if kind not in KERNEL_TO_ENGINE:
            raise DeepSeekV4KernelIRError(
                f"kernel kind {kind!r} has no ABI 3.0 lowering; the shared table "
                "in compiler/ir/v3/lowering.py is the only place to add one"
            )
        if len(inputs) > 4:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r} declares {len(inputs)} inputs; an ABI 3.0 operator "
                "admits at most four input views"
            )
        if len(outputs) > 2:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r} declares {len(outputs)} outputs; an ABI 3.0 "
                "operator admits at most two output views"
            )
        if kind == "CONCAT":
            self._check_join(kernel_id, inputs, outputs, attributes)
        self.kernels.append(
            Kernel(
                index=len(self.kernels),
                kernel_id=kernel_id,
                kind=kind,
                inputs=tuple(inputs),
                outputs=tuple(outputs),
                numeric_contract=numeric_contract,
                iteration_domain=dict(iteration_domain),
                attributes=_neutral_attributes(attributes),
                phases=tuple(phases),
                state_reads=tuple(state_reads),
                state_writes=tuple(state_writes),
                counter_class=COUNTER_CLASS_BY_KIND[kind],
                source_operation_id=source_operation_id,
                layer=layer,
            )
        )
        self.kernels_by_kind[kind] += 1
        self.kernels_by_source_kind[source_kind] += 1


    def _check_join(
        self,
        kernel_id: str,
        inputs: Sequence[str],
        outputs: Sequence[str],
        attributes: Mapping[str, Any],
    ) -> None:
        """A ``CONCAT`` must state the axis it joins, and mean it.

        Amendment A17 makes the join axis an operand-row field, which a backend
        reads from the kernel's ``axis`` attribute and writes into ``aux_id_0``.
        Before it, a concatenation that omitted the attribute was silently read
        as a join of rows, and two sites in this export were doing exactly that
        -- one joining features and one that was a broadcast wearing a
        concatenation's name.  Neither was caught by anything until a device
        refused the shape, so the shape is checked here, where it is written.

        Symbolic extents are skipped rather than guessed: a span-sized axis is
        the request's, and comparing two of them is comparing two names.
        """
        axis = attributes.get("axis")
        if not isinstance(axis, int) or isinstance(axis, bool):
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r}: a CONCAT must declare an integer 'axis'; "
                "amendment A17 puts it in aux_id_0 and an unstated axis is read "
                "as a join of rows by every reader"
            )
        if len(outputs) != 1:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r}: a CONCAT writes exactly one result"
            )
        shapes = [self.shape[name] for name in inputs]
        result = self.shape[outputs[0]]
        for shape in shapes:
            if len(shape) != len(result):
                raise DeepSeekV4KernelIRError(
                    f"{kernel_id!r}: joins operands of rank {len(shape)} into a "
                    f"rank-{len(result)} result; a concatenation keeps the rank"
                )
        if not 0 <= axis < len(result):
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r}: join axis {axis} is outside the rank-"
                f"{len(result)} result"
            )
        if axis and len(result) != 2:
            raise DeepSeekV4KernelIRError(
                f"{kernel_id!r}: amendment A17 defines a join on axis {axis} "
                f"for rank-2 operands only, and this result is rank {len(result)}"
            )

        def _static(value: Any) -> int | None:
            return None if isinstance(value, Symbolic) else int(value)

        for index in range(len(result)):
            extents = [_static(shape[index]) for shape in shapes]
            declared = _static(result[index])
            if declared is None or any(e is None for e in extents):
                continue
            if index == axis:
                total = sum(extents)  # type: ignore[arg-type]
                if total != declared:
                    raise DeepSeekV4KernelIRError(
                        f"{kernel_id!r}: axis {axis} of the operands sums to "
                        f"{total}, the result declares {declared}"
                    )
            elif any(e != declared for e in extents):
                raise DeepSeekV4KernelIRError(
                    f"{kernel_id!r}: axis {index} is {extents} across the "
                    f"operands and {declared} in the result; a join on axis "
                    f"{axis} leaves every other axis alone"
                )


def _split_node_id(node_id: str) -> tuple[str, int | None, str]:
    """Return ``(scope, layer, leaf)`` for a source graph node identifier."""

    head, _, rest = node_id.partition(".")
    if rest.startswith("layer") and rest[5:7].isdigit():
        return head, int(rest[5:7]), rest[8:]
    return head, None, rest


def _contract(source_kind: str, step: str = "") -> str:
    """Return the canonical numeric-contract identity for one emitted kernel."""

    try:
        base = CONTRACT_BASE_BY_SOURCE_KIND[source_kind]
    except KeyError:
        raise DeepSeekV4KernelIRError(
            f"source kind {source_kind!r} has no frozen numeric contract"
        ) from None
    name = f"{base}_{step}_v{CONTRACT_VERSION}" if step else (
        f"{base}_v{CONTRACT_VERSION}"
    )
    if not CONTRACT_PATTERN.match(name):
        raise DeepSeekV4KernelIRError(
            f"numeric contract {name!r} is not a canonical identifier"
        )
    return name


_SOURCE_STATE_SUFFIX_TO_NEUTRAL: Mapping[str, tuple[str, ...]] = {
    "window_kv": ("attention_window",),
    "compressor": ("compressor_window_kv", "compressor_window_score"),
    "compressed_kv": ("compressed_key_value",),
    "index_compressor": (
        "index_compressor_window_kv",
        "index_compressor_window_score",
    ),
    "index_compressed_kv": ("index_compressed_key_value",),
}


def _neutral_state_ids(source_names: Iterable[str]) -> tuple[str, ...]:
    """Translate ``state.<scope>.layer<n>.<suffix>`` into neutral state IDs."""

    out: list[str] = []
    for name in source_names:
        parts = name.split(".")
        if len(parts) != 4 or parts[0] != "state" or not parts[2].startswith("layer"):
            raise DeepSeekV4KernelIRError(f"unrecognised source state {name!r}")
        scope = parts[1]
        layer = int(parts[2][len("layer") :])
        try:
            families = _SOURCE_STATE_SUFFIX_TO_NEUTRAL[parts[3]]
        except KeyError:
            raise DeepSeekV4KernelIRError(
                f"source state {name!r} has no neutral state class"
            ) from None
        out.extend(f"{family}.{scope}.layer.{layer}" for family in families)
    return tuple(out)


def _missing_checkpoint_artifacts(
    release: DeepSeekV4Release,
    snapshot: Path,
    checkpoint_lock_path: Path,
) -> list[str]:
    """Name every checkpoint artifact this build needs and does not have.

    A kernel IR document binds each weight to a byte range in a shard, so it
    cannot be produced from a configuration alone: it needs the complete
    snapshot, the registry-listing witness that authenticates it, and the lock
    that has read every byte.  Reporting all of them at once, each with the
    tool that produces it, is the difference between a build that stops and a
    build that stops somewhere.
    """

    missing: list[str] = []
    if not snapshot.is_dir():
        missing.append(
            f"snapshot {snapshot} is absent; download {release.repository} at "
            f"revision {release.revision}"
        )
    else:
        index = snapshot / "model.safetensors.index.json"
        if not index.is_file():
            shards = len(list(snapshot.glob("model-*-of-*.safetensors")))
            missing.append(
                f"checkpoint index {index} is absent ({shards} of "
                f"{release.shard_count} shards present); it arrives with the "
                f"rest of the {release.repository} snapshot at revision "
                f"{release.revision}"
            )
    if not release.checkpoint_source_path.is_file():
        missing.append(
            f"checkpoint source contract {release.checkpoint_source_path} is "
            "absent; produce it with tools/build_checkpoint_source.py against "
            "the complete snapshot and the committed registry listing"
        )
    if not checkpoint_lock_path.is_file():
        missing.append(
            f"checkpoint lock {checkpoint_lock_path} is absent; produce it with "
            "tools/build_checkpoint_lock.py, which reads all "
            f"{release.payload_bytes:,} payload bytes once"
        )
    elif not release.lock_identity_established:
        missing.append(
            f"no pinned lock identity for {release.model_id}; record the lock's "
            "lock_id and tensor_content_sha256 on its release in "
            "compiler/frontend/deepseek_v4_releases.py"
        )
    return missing


def export_deepseek_v4_kernel_graph(
    *,
    model: str | DeepSeekV4Profile | DeepSeekV4Release = MODEL_ID,
    snapshot: Path | None = None,
    checkpoint_lock_path: Path | None = None,
    config_path: Path | None = None,
    source_path: Path | None = None,
    context_tokens: int = DEFAULT_CONTEXT_TOKENS,
    maximum_new_tokens: int | None = None,
    include_speculative: bool = False,
) -> KernelGraph:
    """Export one pinned DeepSeek-V4 release as a neutral Tensor Kernel IR v3 graph.

    ``model`` names the release: ``deepseek-v4-flash-0731`` by default, or
    ``deepseek-v4-pro-0813``.  It selects the profile -- every width, layer
    count, expert count and identity below -- and the default snapshot,
    checkpoint lock, committed config and checkpoint source contract; any of
    those four paths may be given explicitly instead.

    ``include_speculative`` selects the emitted profile.  ``False`` -- the
    first release -- emits the ordinary target-model path: the main layers, the
    hyper-connection head, the final norm, the vocabulary head and greedy
    selection.  ``True`` additionally emits the three DSpark draft blocks, the
    DSpark conditioning projection, the Markov draft head and the confidence
    head, which ADR-003 section 18 sequences after ordinary generation and
    whose acceptance contract is still open (DSV4-SEM-001).
    """

    model_profile = resolve_model_profile(model)
    release = model_profile.release

    # The released widths for the model being built, taken from its profile and
    # each confronted with this release's own ``config.json`` a few lines below
    # before anything is emitted.  They deliberately shadow the module-level
    # constants of the same name, which are the DeepSeek-V4-Flash-0731
    # profile's: every expression in the body below reads the model being
    # built, and no expression in the body reads the release profile by
    # accident.  ``model_profile`` is spelled out because ``profile`` is this
    # function's word for a *rotary* profile and for the target/speculative
    # split.
    HIDDEN = model_profile.hidden
    HC_MULT = model_profile.hc_mult
    HEADS = model_profile.heads
    KV_HEADS = model_profile.kv_heads
    HEAD_DIM = model_profile.head_dim
    ROPE_DIM = model_profile.rope_dim
    NOPE_DIM = model_profile.nope_dim
    O_GROUPS = model_profile.o_groups
    O_RANK = model_profile.o_rank
    INDEX_HEADS = model_profile.index_heads
    INDEX_HEAD_DIM = model_profile.index_head_dim
    INDEX_TOPK = model_profile.index_topk
    VOCABULARY = model_profile.vocabulary
    ROUTED_EXPERTS = model_profile.routed_experts
    TOP_K = model_profile.top_k
    MOE_INTERMEDIATE = model_profile.moe_intermediate
    SLIDING_WINDOW = model_profile.sliding_window
    SWIGLU_LIMIT = model_profile.swiglu_limit
    ROUTE_SCALE = model_profile.route_scale
    DRAFT_BLOCK = model_profile.draft_block
    MARKOV_RANK = model_profile.markov_rank
    RMS_EPSILON = model_profile.rms_epsilon
    HC_MIX = model_profile.hc_mix
    HC_COEFFICIENTS = model_profile.hc_coefficients
    EOS_TOKEN_ID = model_profile.eos_token_id
    BOS_TOKEN_ID = model_profile.bos_token_id
    NUMERIC_PROFILE = model_profile.numeric_profile
    GENERATION_POLICY_ID = model_profile.generation_policy_id
    MODEL_ID = release.model_id
    REPOSITORY = release.repository
    REVISION = release.revision
    TENSOR_COUNT = release.tensor_count
    PAYLOAD_BYTES = release.payload_bytes
    TENSOR_STRUCTURE_SHA256 = release.tensor_structure_sha256
    INFERENCE_CONFIG_SHA256 = release.inference_config_sha256

    snapshot = release.snapshot if snapshot is None else Path(snapshot)
    checkpoint_lock_path = (
        release.checkpoint_lock
        if checkpoint_lock_path is None
        else Path(checkpoint_lock_path)
    )
    config_path = release.config_path if config_path is None else Path(config_path)
    source_path = (
        release.checkpoint_source_path if source_path is None else Path(source_path)
    )

    if context_tokens < 1 or context_tokens > ARCHITECTURAL_MAX_CONTEXT:
        raise DeepSeekV4KernelIRError(
            f"deployment context {context_tokens} is outside the architectural "
            f"capacity 1..{ARCHITECTURAL_MAX_CONTEXT}"
        )
    if context_tokens % SLIDING_WINDOW:
        raise DeepSeekV4KernelIRError(
            "deployment context must be a whole number of sliding windows"
        )
    if maximum_new_tokens is None:
        maximum_new_tokens = context_tokens
    if not 1 <= maximum_new_tokens <= context_tokens:
        raise DeepSeekV4KernelIRError(
            "maximum_new_tokens is outside the deployment context"
        )

    # The adapter and the graph module raise their own errors.  A caller of
    # this export gets one error type, so a build that stops says which model
    # and which artifact rather than which module.
    try:
        config = load_official_config(config_path, source_path, release)
        specs = build_official_tensor_specs(config, release)
    except DeepSeekV4AdapterError as exc:
        raise DeepSeekV4KernelIRError(
            f"{release.model_id} tensor contract is not available: {exc}"
        ) from exc
    # Confront the profile with the release it claims to describe.  Every width
    # this export sizes anything by is here, moving or not: a width that is not
    # checked against the config it came from is a width that can drift without
    # a symptom, and the route scale is the case with no downstream witness at
    # all -- 1.5 applied to a model whose released value is 2.5 is a finite
    # number either way.
    for key, expected in model_profile.architecture_pins:
        if key not in release.config_scalars and key != "compress_ratios":
            raise DeepSeekV4KernelIRError(
                f"{MODEL_ID} sizes the graph by {key}, which its release record "
                "does not pin"
            )
        if config[key] != expected:
            raise DeepSeekV4KernelIRError(
                f"released config {key}={config[key]} differs from the pinned {expected}"
            )

    missing = _missing_checkpoint_artifacts(release, snapshot, checkpoint_lock_path)
    if missing:
        raise DeepSeekV4KernelIRError(
            f"the {MODEL_ID} kernel IR needs "
            f"{len(missing)} artifact{'s' if len(missing) > 1 else ''} that "
            "this host does not have:\n  " + "\n  ".join(missing)
        )
    try:
        lock = load_checkpoint_lock(checkpoint_lock_path)
    except CheckpointError as exc:
        raise DeepSeekV4KernelIRError(
            f"invalid DeepSeek V4 checkpoint lock: {exc}"
        ) from exc
    try:
        validate_official_checkpoint_lock(lock, config, release)
    except DeepSeekV4AdapterError as exc:
        raise DeepSeekV4KernelIRError(
            f"{release.model_id} checkpoint lock is not usable: {exc}"
        ) from exc
    if (
        lock["lock_id"] != release.checkpoint_lock_id
        or lock["checkpoint"]["tensor_count"] != TENSOR_COUNT
        or lock["checkpoint"]["payload_bytes"] != PAYLOAD_BYTES
    ):
        raise DeepSeekV4KernelIRError(
            f"checkpoint lock is not the pinned {MODEL_ID} release"
        )
    bindings = read_checkpoint_bindings(snapshot, lock)
    if len(bindings) != TENSOR_COUNT:
        raise DeepSeekV4KernelIRError(
            f"checkpoint headers describe {len(bindings)} tensors, expected {TENSOR_COUNT}"
        )

    try:
        contract = build_official_graph_contract(release)
    except DeepSeekV4GraphError as exc:
        raise DeepSeekV4KernelIRError(
            f"{release.model_id} source graph contract is not available: {exc}"
        ) from exc
    nodes = contract["nodes"]

    #: The main layers' compression ratios, from the profile.  The released
    #: list is longer: its tail is the DSpark stages' own ratios, which the
    #: speculative blocks read separately.  ``validate_official_config`` has
    #: already refused a config whose list differs from this one.
    ratios = list(model_profile.main_compress_ratios)

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
    span = Symbolic("span_tokens", 1, context_tokens)
    dispatch_rows = Symbolic("span_tokens", TOP_K, TOP_K * context_tokens)
    groups = {
        4: Symbolic("span_groups_ratio4", 1, context_tokens // 4),
        128: Symbolic("span_groups_ratio128", 1, context_tokens // 128),
    }
    committed_groups = {
        4: Symbolic("context_groups_ratio4", 1, context_tokens // 4),
        128: Symbolic("context_groups_ratio128", 1, context_tokens // 128),
    }
    attention_rows = {
        0: Symbolic("attention_rows_window", 1, context_tokens),
        4: Symbolic(
            "attention_rows_ratio4",
            1,
            context_tokens + context_tokens // 4,
        ),
        128: Symbolic(
            "attention_rows_ratio128",
            1,
            context_tokens + context_tokens // 128,
        ),
    }
    # A derived symbol is declared where a layer of that compression ratio
    # exists, and not otherwise.  Flash has all three kinds -- two window-only
    # layers, 21 at ratio 4 and 20 at ratio 128 -- so it declares all nine
    # symbols.  Pro has no window-only layer, so ``attention_rows_window``
    # would be a symbol no tensor extent names; both backends still carry the
    # name in their frozen A5 registries, so declaring it would be legal and
    # inert, and leaving it out is the same choice made for the base rotary
    # table above and for the same reason.
    ratio_kinds = set(ratios)
    symbols = (
        RuntimeSymbol("span_tokens", 1, context_tokens, 1, "request"),
        RuntimeSymbol("context_length", 1, context_tokens, 1, "request"),
        *(
            (RuntimeSymbol("span_groups_ratio4", 0, context_tokens // 4, 1, "derived"),)
            if 4 in ratio_kinds
            else ()
        ),
        *(
            (
                RuntimeSymbol(
                    "span_groups_ratio128", 0, context_tokens // 128, 1, "derived"
                ),
            )
            if 128 in ratio_kinds
            else ()
        ),
        *(
            (
                RuntimeSymbol(
                    "context_groups_ratio4", 0, context_tokens // 4, 1, "derived"
                ),
            )
            if 4 in ratio_kinds
            else ()
        ),
        *(
            (
                RuntimeSymbol(
                    "context_groups_ratio128", 0, context_tokens // 128, 1, "derived"
                ),
            )
            if 128 in ratio_kinds
            else ()
        ),
        *(
            (RuntimeSymbol("attention_rows_window", 1, context_tokens, 1, "derived"),)
            if 0 in ratio_kinds
            else ()
        ),
        *(
            (
                RuntimeSymbol(
                    "attention_rows_ratio4",
                    1,
                    context_tokens + context_tokens // 4,
                    1,
                    "derived",
                ),
            )
            if 4 in ratio_kinds
            else ()
        ),
        *(
            (
                RuntimeSymbol(
                    "attention_rows_ratio128",
                    1,
                    context_tokens + context_tokens // 128,
                    1,
                    "derived",
                ),
            )
            if 128 in ratio_kinds
            else ()
        ),
    )

    # ------------------------------------------------------------------
    # Request inputs
    # ------------------------------------------------------------------
    token_ids = builder.tensor("input.token_ids", TOKEN_DTYPE, (span,), "input")
    position_offset = builder.tensor("input.position_offset", "i32", (1,), "input")
    session_ids = builder.tensor("input.session_ids", "u32", (1,), "input")
    entropy = builder.tensor("input.entropy_stream", "fp32", (1, VOCABULARY), "input")

    # The sampling temperature is *not* a request input.  It was declared as
    # one -- ``input.temperature`` -- and every backend therefore placed it as
    # a zero-filled host object, because ABI 3.0's submission record
    # (``runtime.abi3.records.Submission``) carries no temperature field and
    # the host driver has nothing to write it with.  ``main.sample.temperature``
    # then multiplied a healthy 129,280-wide logits vector by binary32 zero,
    # every logit tied, and ``greedy_lowest_token_id_argmax`` returned token 0
    # with no trap anywhere.  The released generation configuration pins the
    # default at binary32 one, so it is a deployment constant with a declared
    # generator and a bound digest, exactly like the rotary tables.
    #
    # The frozen graph contract still names ``request.temperature_binary32`` as
    # the ``SAMPLE`` node's second input, so this tensor is what that value
    # resolves to and it states the pinned number where a reader looks for it.
    # The *operator* does not read it as an operand: a scalar an ABI 3.0
    # operator scales by lives in the numeric descriptor, and the two backends
    # disagree about the shape of a scalar operand view -- one broadcasts it to
    # the logits row and one does not -- so an operand would be lane-dependent
    # where a numeric constant is not.  Both take the same pattern below.
    temperature = builder.tensor(
        "sample.temperature",
        "fp32",
        (1,),
        "constant",
        generator="constant_binary32_v1",
        generator_parameters={
            "bits": OFFICIAL_DEFAULT_TEMPERATURE_BINARY32,
            "count": 1,
        },
    )

    # ------------------------------------------------------------------
    # Rotary coefficient rows
    # ------------------------------------------------------------------
    # ``TA-ABI3-OPCONV-1`` section 3 gives ``VECTOR.ROPE``'s ``in1`` to the
    # coefficient rows and its ``aux_id_0`` to the rotary width.  This export
    # used to feed the position offset into that slot and carry the rotary
    # parameters as attributes, because amendment A9's derived-constant tensor
    # did not exist yet.  It does now, so the table is a declared constant with
    # a named generator, the deployment binds the SHA-256 of its output, and the
    # device re-derives and re-checks it at load.
    #
    # Two rotary profiles, because ``inference/model.py`` selects between them
    # per layer: ``if self.compress_ratio`` rotates at ``compress_rope_theta``
    # with the committed YaRN interpolation, and the ``else`` branch -- the
    # pure sliding-window layers -- disables YaRN and rotates at the base
    # ``rope_theta``.  Collapsing them onto one table would give whichever
    # layers did not get their own the wrong frequencies.
    #
    # A profile is declared only where some node reads it.  Flash reads both:
    # its layers 0 and 1 are the only ratio-0 layers either release has.
    # DeepSeek-V4-Pro-0813 has no window-only main layer at all, so its
    # target-only graph would otherwise declare a generated table, an
    # activation row block and a GATHER whose output nothing consumes.
    # ``check_neutral`` does not reject that -- an unread constant is legal --
    # which is exactly why it is decided here rather than left to a backend:
    # one lane that allocates for every declared tensor and one that prunes
    # would disagree about a document neither had rejected.  The base profile
    # comes back with the speculative profile, whose three DSpark stages carry
    # ratio 0.
    #
    # The rows are ``cos[rotary_width] || sin[rotary_width]``, not
    # ``cos[head_dim] || sin[head_dim]``: the rotation is partial.  Only the
    # final 64 channels of a 512- or 128-wide head move, and they move as 32
    # adjacent complex pairs, so the coefficient row spans the rotated channels
    # and repeats each pair's value across the two channels it multiplies.
    rope_tables: dict[str, str] = {}
    rope_rows: dict[str, str] = {}
    rope_ratios = set(ratios)
    if include_speculative:
        rope_ratios.update(release.dspark_compress_ratios)
    for profile, theta, scaling in (
        ("base", float(config["rope_theta"]), "none"),
        ("yarn", float(config["compress_rope_theta"]), "yarn"),
    ):
        reads_profile = any(
            ("yarn" if ratio else "base") == profile for ratio in rope_ratios
        )
        if not reads_profile:
            continue
        parameters: dict[str, Any] = {
            "maximum_position": context_tokens,
            "position_scaling": scaling,
            "rotary_width": ROPE_DIM,
            "theta": theta,
        }
        if scaling == "yarn":
            parameters.update(
                {
                    "beta_fast": int(config["rope_scaling"]["beta_fast"]),
                    "beta_slow": int(config["rope_scaling"]["beta_slow"]),
                    "factor": float(config["rope_scaling"]["factor"]),
                    "original_max_position": int(
                        config["rope_scaling"]["original_max_position_embeddings"]
                    ),
                }
            )
        rope_tables[profile] = builder.tensor(
            f"rope.coefficient_table.{profile}",
            "fp32",
            (context_tokens, 2 * ROPE_DIM),
            "constant",
            generator="deepseek_rope_coefficients_v1",
            generator_parameters=parameters,
        )
        rope_rows[profile] = builder.tensor(
            f"rope.coefficient_rows.{profile}",
            "fp32",
            (span, 2 * ROPE_DIM),
            "activation",
        )
        builder.kernel(
            f"rope.coefficient_gather.{profile}",
            "GATHER",
            (position_offset, rope_tables[profile]),
            (rope_rows[profile],),
            numeric_contract="exact_index_select_v1",
            iteration_domain={"rows": span, "width": 2 * ROPE_DIM},
            attributes={
                "coefficient_layout": "cos_rotary_width_then_sin_rotary_width",
                "pair_layout": "adjacent_complex",
                "position_scaling": scaling,
                "rotary_width": ROPE_DIM,
                "selector": "input.position_offset",
                "theta": theta,
            },
            source_operation_id=f"deepseek_v4.rotary_embedding.{profile}_rows",
            source_kind="ROPE_COEFFICIENT_ROWS",
        )

    # Amendment A19: ``ROUTE.INDEX_TOPK``'s compression ratio arrives in an
    # input view, because ``aux_id_0..3`` are spent on ``k``, the mask mode and
    # the two request symbols and an operator has no other channel for a
    # scalar.  It is a pinned property of the layer rather than of the request,
    # so it is a mask-programmed constant and one tensor serves every layer of
    # that ratio.
    def compression_ratio_constant(value: int) -> str:
        name = f"index.compression_ratio.{value}"
        if builder.has_tensor(name):
            return name
        return builder.tensor(
            name,
            "u32",
            (1,),
            "constant",
            generator="constant_u32_v1",
            generator_parameters={"value": value, "count": 1},
        )

    value_tensor: dict[str, str] = {
        "request.input_ids": token_ids,
        "request.start_pos": position_offset,
        "request.session_ids": session_ids,
        "request.temperature_binary32": temperature,
        "request.explicit_exponential_entropy": entropy,
    }
    predicate_values: set[str] = set()
    context_of: dict[str, dict[str, str]] = defaultdict(dict)

    role_any: dict[str, list[TensorSpec]] = defaultdict(list)
    for spec in specs:
        role_any[spec.semantic_role].append(spec)
    for group in role_any.values():
        group.sort(key=lambda s: (-1 if s.expert is None else s.expert, s.name))

    def declare_weight(spec: TensorSpec) -> str:
        if builder.has_tensor(spec.name):
            return spec.name
        binding = bindings.get(spec.name)
        if binding is None:
            raise DeepSeekV4KernelIRError(
                f"checkpoint has no payload for {spec.name!r}"
            )
        if binding.bytes != spec.size_bytes:
            raise DeepSeekV4KernelIRError(
                f"{spec.name!r} byte length differs from the derived contract"
            )
        dtype = _STORAGE_DTYPE[spec.storage_dtype]
        shape: tuple[int, ...] = tuple(spec.shape)
        if spec.logical_dtype == "MXFP4_E2M1_X2":
            # Two E2M1 elements share one stored byte; the neutral shape is the
            # architectural one and the binding still names the stored bytes.
            dtype = "mxfp4_e2m1"
            shape = (spec.shape[0], spec.shape[1] * 2)
        scale_spec = scale_of.get(spec.name)
        scale_id: str | None = None
        block = 0
        if scale_spec is not None:
            scale_id = declare_weight(scale_spec)
            block = FP4_BLOCK if dtype == "mxfp4_e2m1" else FP8_WEIGHT_BLOCK
        return builder.tensor(
            spec.name,
            dtype,
            shape,
            "weight",
            binding=binding,
            scale_tensor_id=scale_id,
            scale_block_elements=block,
        )

    group_weights: dict[tuple[str, int], str] = {}

    def group_weight(spec: TensorSpec, group: int, groups: int) -> str:
        """Declare one group's rows of a stacked weight as its own tensor.

        The released ``wo_a`` is ``[groups * rank, reduction]`` fp8 with a
        ``[groups * rank / 128, reduction / 128]`` E8M0 tile scale (amendment
        A15), and group ``g`` of a block-diagonal projection contracts against
        rows ``[g * rank, (g + 1) * rank)`` of it.  Those rows are a contiguous
        byte range and so are their scale rows, so each group is one ordinary
        binding whose digest :func:`split_binding_by_leading_groups` derives and
        checks against the locked whole-tensor SHA-256.

        The whole tensor stays declared: this adds names for its parts, it does
        not replace it.
        """
        key = (spec.name, group)
        if key in group_weights:
            return group_weights[key]
        binding = bindings.get(spec.name)
        if binding is None:
            raise DeepSeekV4KernelIRError(
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
                raise DeepSeekV4KernelIRError(
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
                block = FP8_WEIGHT_BLOCK
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

    def role_specs(role: str, scope: str, layer: int | None) -> list[TensorSpec]:
        for key in ((scope, layer, role), ("global", None, role)):
            if key in spec_index:
                return spec_index[key]
        if role in role_any:
            return role_any[role]
        raise DeepSeekV4KernelIRError(
            f"role {role!r} has no tensor in scope {scope!r} layer {layer!r}"
        )

    def role_weight(role: str, scope: str, layer: int | None) -> str:
        found = role_specs(role, scope, layer)
        if len(found) != 1:
            raise DeepSeekV4KernelIRError(
                f"role {role!r} resolves to {len(found)} tensors, expected one"
            )
        return declare_weight(found[0])

    def _stacked_id(spec: TensorSpec) -> str:
        """The family name with the expert index removed.

        ``layers.0.ffn.experts.7.w1.weight`` names one expert's matrix;
        ``layers.0.ffn.experts.w1.weight`` names the stacked ``[E, N, K]``
        tensor the routed contraction actually reads.
        """
        parts = spec.name.split(".")
        marker = str(spec.expert)
        for index in range(len(parts) - 1, -1, -1):
            if parts[index] == marker:
                del parts[index]
                break
        else:  # pragma: no cover - the family is expert-indexed by construction
            raise DeepSeekV4KernelIRError(
                f"{spec.name!r} carries no expert index to stack over"
            )
        return ".".join(parts)

    def _stack_binding(
        tensor_id: str, members: Sequence[TensorSpec]
    ) -> CheckpointBinding:
        """One segmented binding over an ordered family of checkpoint ranges.

        A stack of expert weights is an operand, not an attribute.  The
        released checkpoint interleaves a layer's experts, so no single
        range covers the stack, and until :class:`CheckpointBinding` grew
        ``segments`` the only way to name it was a list of tensor names in an
        attribute -- which is not an operand, so the mandatory ``[E, N, K]``
        slot of ``TENSOR.ROUTED_MATMUL`` went unfilled.  The segments are the same
        authenticated ranges the individual tensors had, in ascending logical
        expert order; each keeps its own digest so verification stays
        incremental, and the binding's own digest binds their order.
        """
        segments: list[BindingSegment] = []
        for member in members:
            binding = bindings.get(member.name)
            if binding is None:
                raise DeepSeekV4KernelIRError(
                    f"checkpoint has no payload for {member.name!r}"
                )
            if binding.bytes != member.size_bytes:
                raise DeepSeekV4KernelIRError(
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

    def role_weight_stack(role: str, scope: str, layer: int | None) -> str:
        """Declare the stacked ``[E, N, K]`` tensor one routed matmul reads."""
        members = role_specs(role, scope, layer)
        if len(members) < 2 or any(m.expert is None for m in members):
            raise DeepSeekV4KernelIRError(
                f"role {role!r} in scope {scope!r} layer {layer!r} is not an "
                "expert-indexed family and cannot be stacked"
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
            raise DeepSeekV4KernelIRError(
                f"expert family {tensor_id!r} is not uniformly shaped"
            )
        scale_id: str | None = None
        block = 0
        scale_members = [scale_of[m.name] for m in members if m.name in scale_of]
        if scale_members:
            if len(scale_members) != len(members):
                raise DeepSeekV4KernelIRError(
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
            block = FP4_BLOCK if dtype == "mxfp4_e2m1" else FP8_WEIGHT_BLOCK
        return builder.tensor(
            tensor_id,
            dtype,
            (len(members), *member_shape),
            "weight",
            binding=_stack_binding(tensor_id, members),
            scale_tensor_id=scale_id,
            scale_block_elements=block,
        )

    def ten(value: str) -> str:
        try:
            return value_tensor[value]
        except KeyError:
            raise DeepSeekV4KernelIRError(
                f"source value {value!r} has no neutral tensor"
            ) from None

    def bind(value: str, tensor_id: str) -> str:
        value_tensor[value] = tensor_id
        return tensor_id

    def act(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "activation")

    def view(tensor_id: str, dtype: str, shape: tuple[Any, ...]) -> str:
        return builder.tensor(tensor_id, dtype, shape, "state")

    def rows_of(tensor_id: str) -> Any:
        return builder.shape[tensor_id][0]

    quantized: dict[tuple[str, int, str, int], tuple[str, str]] = {}

    def quantize(
        source: str,
        *,
        block: int,
        dtype: str,
        width: int | None,
        source_operation_id: str,
        source_kind: str,
        contract: str,
        attributes: Mapping[str, Any],
        layer: int | None,
        phases: Sequence[str],
    ) -> tuple[str, str]:
        """Emit (or reuse) the dynamic quantization of one activation value."""

        shape = builder.shape[source]
        full_width = shape[-1]
        if width is None:
            width = int(full_width)
        key = (source, block, dtype, width)
        if key in quantized:
            return quantized[key]
        suffix = f"quantized_{dtype}_{block}"
        if width != full_width:
            suffix = f"{suffix}_{width}"
        if width % block:
            raise DeepSeekV4KernelIRError(
                f"{source!r} width {width} is not a whole number of {block}-blocks"
            )
        scale = act(
            f"{source}.{suffix}.scale", "e8m0", (*shape[:-1], width // block)
        )
        payload = builder.tensor(
            f"{source}.{suffix}",
            dtype,
            (*shape[:-1], width),
            "activation",
            scale_tensor_id=scale,
            scale_block_elements=block,
        )
        builder.kernel(
            f"{source}.{suffix}",
            "QUANTIZE",
            (source,),
            (payload, scale),
            numeric_contract=contract,
            iteration_domain={"rows": shape[0], "width": width, "block": block},
            attributes=dict(attributes),
            source_operation_id=source_operation_id,
            source_kind=source_kind,
            phases=phases,
            layer=layer,
        )
        quantized[key] = (payload, scale)
        return payload, scale

    def rope_attributes(ratio: int, *, inverse: bool) -> dict[str, Any]:
        if ratio:
            return {
                "beta_fast": int(config["rope_scaling"]["beta_fast"]),
                "beta_slow": int(config["rope_scaling"]["beta_slow"]),
                "factor": float(config["rope_scaling"]["factor"]),
                "inverse": inverse,
                "original_max_position": int(
                    config["rope_scaling"]["original_max_position_embeddings"]
                ),
                "position_scaling": "yarn",
                "rotary_width": ROPE_DIM,
                "theta": float(config["compress_rope_theta"]),
            }
        return {
            "inverse": inverse,
            "position_scaling": "none",
            "rotary_width": ROPE_DIM,
            "theta": float(config["rope_theta"]),
        }

    def ensure_state(state_id: str) -> str:
        if builder.has_state(state_id):
            return state_id
        family, state_scope, _, layer_text = state_id.split(".")
        state_layer = int(layer_text)
        state_ratio = ratios[state_layer] if state_scope == "main" else 0
        coefficient = 2 if state_ratio == 4 else 1
        if family == "attention_window":
            resource = StateResource(
                state_id=state_id,
                state_class="kv_window",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=SLIDING_WINDOW,
                initialization="zero",
            )
        elif family in {"compressor_window_kv", "compressor_window_score"}:
            resource = StateResource(
                state_id=state_id,
                state_class="compressor_window",
                dtype="fp32",
                row_elements=coefficient * HEAD_DIM,
                capacity_rows=coefficient * state_ratio,
                initialization=(
                    "zero"
                    if family.endswith("kv")
                    else "negative_infinity"
                ),
            )
        elif family == "compressed_key_value":
            resource = StateResource(
                state_id=state_id,
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=HEAD_DIM,
                capacity_rows=context_tokens // state_ratio,
                initialization="zero",
            )
        elif family in {
            "index_compressor_window_kv",
            "index_compressor_window_score",
        }:
            resource = StateResource(
                state_id=state_id,
                state_class="compressor_window",
                dtype="fp32",
                row_elements=2 * INDEX_HEAD_DIM,
                capacity_rows=2 * 4,
                initialization=(
                    "zero" if family.endswith("kv") else "negative_infinity"
                ),
            )
        elif family == "index_compressed_key_value":
            resource = StateResource(
                state_id=state_id,
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=INDEX_HEAD_DIM,
                capacity_rows=context_tokens // 4,
                initialization="zero",
            )
        else:  # pragma: no cover - the translation table is closed
            raise DeepSeekV4KernelIRError(f"unknown state family {family!r}")
        return builder.state(resource)

    def states_of(node: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
        reads = _neutral_state_ids(node["state_reads"])
        writes = _neutral_state_ids(node["state_writes"])
        for state_id in (*reads, *writes):
            ensure_state(state_id)
        return reads, writes

    def dedupe(items: Iterable[str]) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for item in items:
            seen.setdefault(item, None)
        return tuple(seen)

    # ------------------------------------------------------------------
    # Lower every source node
    # ------------------------------------------------------------------
    emitted_source_kinds: Counter = Counter()
    for node in nodes:
        node_id = node["id"]
        source_kind = node["kind"]
        speculative = node_id.startswith("dspark.") or source_kind == (
            "TARGET_HIDDEN_CAPTURE"
        )
        if speculative and not include_speculative:
            continue
        emitted_source_kinds[source_kind] += 1
        scope, layer, leaf = _split_node_id(node_id)
        root = f"{scope}.layer{layer:02d}" if layer is not None else scope
        ratio = ratios[layer] if scope == "main" and layer is not None else 0
        phases = tuple(node["phases"])
        attrs = dict(node["attributes"])
        attrs["source_operation_kind"] = source_kind
        source_inputs = list(node["inputs"])
        source_outputs = list(node["outputs"])
        roles = list(node["tensor_roles"])
        reads, writes = states_of(node)
        predicated = [v for v in source_inputs if v in predicate_values]
        if predicated:
            attrs["execution_predicate"] = predicated[0]
        if node["guard"] is not None:
            attrs["execution_predicate"] = node["guard"]
        operands = [ten(v) for v in source_inputs if v not in predicate_values]
        out0 = source_outputs[0]

        def emit(
            kernel_id: str,
            kind: str,
            inputs: Sequence[str],
            outputs: Sequence[str],
            *,
            step: str = "",
            iteration_domain: Mapping[str, Any],
            attributes: Mapping[str, Any] | None = None,
            state: bool = True,
        ) -> None:
            builder.kernel(
                kernel_id,
                kind,
                inputs,
                outputs,
                numeric_contract=_contract(source_kind, step),
                iteration_domain=iteration_domain,
                attributes=attrs if attributes is None else attributes,
                source_operation_id=node_id,
                source_kind=source_kind,
                phases=phases,
                layer=layer,
                state_reads=reads if state else (),
                state_writes=writes if state else (),
            )

        def concat_feature_axis(
            result_id: str,
            blocks: Sequence[str],
            rows: Any,
            width: int,
            *,
            prefix: str = "join",
        ) -> str:
            """Join equal-width column blocks into one row, four at a time.

            Amendment A17 gives ``REDUCTION.GROUPED_CONCAT`` a join axis, and
            this is the shape that needs it: ``N`` blocks of ``[rows, width]``
            becoming ``[rows, N * width]``, block ``i`` at columns
            ``[i * width, (i + 1) * width)``.

            An OPERATOR names four input views, so more than four blocks are a
            tree, and the tree is built so that every interior node is full:
            eight blocks are two joins of four and one of two, which is ten
            operands over three kernels and the fewest a four-slot record
            admits.  Each level's intermediate is itself a legal feature join,
            so the shape is checked at every step rather than only at the end.
            """
            # ``(tensor, width)`` rather than one width for the level: a level
            # whose last group is short carries a narrower member into the next
            # one, and a single running width would mis-state its segment.
            level: list[tuple[str, int]] = [(name, width) for name in blocks]
            if not level:
                raise DeepSeekV4KernelIRError(
                    f"{result_id!r}: a concatenation needs at least one block"
                )
            stage = 0
            while len(level) > 1:
                joined: list[tuple[str, int]] = []
                for index in range(0, len(level), 4):
                    members = level[index : index + 4]
                    if len(members) == 1:
                        joined.append(members[0])
                        continue
                    widths = [w for _, w in members]
                    out_width = sum(widths)
                    name = (
                        result_id
                        if len(level) <= 4
                        else f"{node_id}.{prefix}{stage}.{index // 4}"
                    )
                    tensor_id = act(name, "bf16", (rows, out_width))
                    emit(
                        f"{node_id}.{prefix}{stage}.{index // 4}",
                        "CONCAT",
                        tuple(member for member, _ in members),
                        (tensor_id,),
                        iteration_domain={"tokens": rows, "width": out_width},
                        attributes={
                            **attrs,
                            "axis": 1,
                            "segment_widths": widths,
                        },
                    )
                    joined.append((tensor_id, out_width))
                level = joined
                stage += 1
            return level[0][0]

        # -- movement, normalisation and dense contraction ---------------
        if source_kind == "TOKEN_EMBED":
            weight = role_weight(roles[0], scope, layer)
            output = act(out0, "bf16", (span, HIDDEN))
            emit(
                node_id,
                "EMBEDDING_LOOKUP",
                (operands[0], weight),
                (output,),
                iteration_domain={"tokens": span, "width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "HC_EXPAND":
            # ``unsqueeze(2).repeat(1, 1, hc_mult, 1)``: one hidden state read
            # once per hyper-connection stream.  Emitting it as four inputs to a
            # CONCAT said "join four tensors", which on axis 0 -- the only axis
            # REDUCTION.GROUPED_CONCAT has -- is ``[4 * tokens, width]``, four
            # consecutive tokens where four streams belong.  BROADCAST states
            # the inserted axis instead, so a backend reads the one source
            # through a stride-zero axis rather than materialising four copies.
            source = operands[0]
            output = act(out0, "bf16", (span, HC_MULT, HIDDEN))
            emit(
                node_id,
                "BROADCAST",
                (source,),
                (output,),
                iteration_domain={"tokens": span, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
                attributes={**attrs, "axis": 1, "extent": HC_MULT,
                            "source_replication": "single_embedding"},
            )
            bind(out0, output)

        elif source_kind == "HC_PRE":
            # TA-ABI3-OPCONV-1 section 3 gives ``VECTOR.MHC`` two output views
            # and the ``HYPER_CONNECT_PRE`` sub-case spends them on the packed
            # ``[tokens, 2, streams]`` pre/post coefficient block and the
            # ``[tokens, streams, streams]`` Sinkhorn combination matrix.  The
            # branch input the released ``Block.hc_pre`` returns is not one of
            # them: it is the weighted stream reduction
            # ``y[t,h] = sum_m pre[t,m] * x[t,m,h]``, which the frozen reference
            # states as four binary32 products reduced by a balanced tree and
            # converted once to BF16 -- exactly ``REDUCTION.EXPERT_SUM``.  This
            # export therefore says what the ABI says: one MHC operator for the
            # coefficients, one select per coefficient plane, and one reduction
            # for the branch.  Packing the branch into an MHC output slot, as
            # this export previously did, made the operand row a fiction and
            # left ``HYPER_CONNECT_POST`` reading three operands where its row
            # has four.
            hidden = operands[0]
            base = role_weight(roles[0], scope, layer)
            projection = role_weight(roles[1], scope, layer)
            scale = role_weight(roles[2], scope, layer)
            rows = rows_of(hidden)
            weight_planes = act(f"{node_id}.weights", "fp32", (rows, 2, HC_MULT))
            combination = act(
                source_outputs[2], "fp32", (rows, HC_MULT, HC_MULT)
            )
            emit(
                node_id,
                "HYPER_CONNECT_PRE",
                (hidden, projection, scale, base),
                (weight_planes, combination),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                    "mix_width": HC_MIX,
                },
                attributes={
                    **attrs,
                    "coefficient_layout": "pre_then_post",
                    "coefficient_width": HC_COEFFICIENTS,
                    "combination_width": HC_MULT * HC_MULT,
                    "epsilon": RMS_EPSILON,
                    "mix_width": HC_MIX,
                    "post_width": HC_MULT,
                    "sinkhorn_iterations": int(config["hc_sinkhorn_iters"]),
                },
            )
            pre = act(f"{node_id}.pre", "fp32", (rows, HC_MULT))
            emit(
                f"{node_id}.pre_plane",
                "SELECT",
                (weight_planes,),
                (pre,),
                iteration_domain={"tokens": rows, "hyper_streams": HC_MULT},
                attributes={
                    **attrs,
                    "axis": 1,
                    "index": 0,
                    "plane": "branch_weight",
                },
            )
            post = act(source_outputs[1], "fp32", (rows, HC_MULT))
            emit(
                f"{node_id}.post_plane",
                "SELECT",
                (weight_planes,),
                (post,),
                iteration_domain={"tokens": rows, "hyper_streams": HC_MULT},
                attributes={
                    **attrs,
                    "axis": 1,
                    "index": 1,
                    "plane": "residual_weight",
                },
            )
            branch = act(source_outputs[0], "bf16", (rows, HIDDEN))
            emit(
                f"{node_id}.branch_reduce",
                "EXPERT_REDUCE",
                (hidden, pre),
                (branch,),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
                attributes={
                    **attrs,
                    "contribution_row_order": "ascending_hyper_stream",
                    "reduction_axis": 1,
                    "reduction_order": "pairwise_tree",
                    "routing_weight_application": "applied_at_the_reduction",
                    "stream_count": HC_MULT,
                },
            )
            bind(source_outputs[0], branch)
            bind(source_outputs[1], post)
            bind(source_outputs[2], combination)
            bind(source_outputs[3], hidden)

        elif source_kind == "HC_POST":
            # Four operands, matching the frozen row: branch, residual streams,
            # post coefficients, combination matrix.  They were three only while
            # ``HYPER_CONNECT_PRE`` packed the post and combination coefficients
            # into one tensor.
            inputs = dedupe(operands)
            rows = rows_of(inputs[0])
            output = act(out0, "bf16", (rows, HC_MULT, HIDDEN))
            emit(
                node_id,
                "HYPER_CONNECT_POST",
                inputs,
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
                attributes={
                    **attrs,
                    "coefficient_layout": "post_and_combination_are_separate",
                    "combination_width": HC_MULT * HC_MULT,
                    "post_width": HC_MULT,
                },
            )
            bind(out0, output)

        elif source_kind == "HC_HEAD":
            hidden = operands[0]
            base = role_weight(roles[0], scope, layer)
            projection = role_weight(roles[1], scope, layer)
            scale = role_weight(roles[2], scope, layer)
            rows = rows_of(hidden)
            output = act(out0, "bf16", (rows, HIDDEN))
            emit(
                node_id,
                "HYPER_CONNECT_HEAD",
                (hidden, projection, scale, base),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "hyper_streams": HC_MULT,
                    "width": HIDDEN,
                },
            )
            bind(out0, output)

        elif source_kind == "RMS_NORM":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "RMS_NORM",
                (source, weight),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        elif source_kind == "HEAD_RMS_NORM":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "HEAD_RMS_NORM",
                (source,),
                (output,),
                iteration_domain={
                    "tokens": shape[0],
                    "heads": HEADS,
                    "width": HEAD_DIM,
                },
            )
            bind(out0, output)

        elif source_kind in {"FP8_LINEAR", "DSPARK_MAIN_PROJECT"}:
            if source_kind == "DSPARK_MAIN_PROJECT":
                rows = rows_of(operands[0])
                joined = act(
                    f"{node_id}.joined_target_hidden",
                    "bf16",
                    (rows, HIDDEN * len(operands)),
                )
                emit(
                    f"{node_id}.concat",
                    "CONCAT",
                    tuple(operands),
                    (joined,),
                    step="target_hidden_concat",
                    iteration_domain={"tokens": rows,
                                      "width": HIDDEN * len(operands)},
                    # ``[rows, hidden]`` blocks becoming one ``[rows, n*hidden]``
                    # row is a join on the *feature* axis.  This kernel named no
                    # axis at all, so every reader defaulted it to zero and read
                    # a join of rows -- a shape with a different extent and a
                    # different meaning.  Amendment A17 makes the axis an
                    # operand-row field, so it is stated here.
                    attributes={**attrs, "axis": 1,
                                "segment_widths": [HIDDEN] * len(operands)},
                )
                source = joined
                weight = role_weight(roles[0], scope, layer)
                norm_weight = role_weight(roles[2], scope, layer)
            else:
                source = operands[0]
                weight = role_weight(roles[0], scope, layer)
                norm_weight = None
            out_features, in_features = builder.shape[weight]
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "amax_floor_binary32": "0x38d1b717",
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "scale_selection": "bit_ceiling_power_of_two",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            rows = rows_of(source)
            if "heads" in attrs:
                shape = (rows, int(attrs["heads"]), int(attrs["head_dim"]))
            else:
                shape = (rows, out_features)
            product = f"{node_id}.projection" if norm_weight else out0
            output = act(product, "bf16", shape)
            emit(
                f"{node_id}.contract",
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
                    **attrs,
                    "accumulator_dtype": "fp32",
                    "activation_block_elements": ACTIVATION_BLOCK,
                    "input_dtype": "fp8_e4m3fn",
                    "output_dtype": "bf16",
                    "reduction_order": "increasing_reduction_index",
                    "transpose_weight": True,
                    "weight_block_elements": FP8_WEIGHT_BLOCK,
                },
            )
            if norm_weight is not None:
                normalized = act(out0, "bf16", shape)
                emit(
                    f"{node_id}.norm",
                    "RMS_NORM",
                    (output, norm_weight),
                    (normalized,),
                    step="conditioning_norm",
                    iteration_domain={"rows": rows, "width": HIDDEN},
                )
                output = normalized
            bind(out0, output)

        elif source_kind == "BF16_LINEAR":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            out_features, in_features = builder.shape[weight]
            rows = rows_of(source)
            output = act(out0, "bf16", (rows, out_features))
            emit(
                node_id,
                "MATMUL",
                (source, weight),
                (output,),
                iteration_domain={
                    "rows": rows,
                    "output_width": out_features,
                    "reduction_width": in_features,
                },
            )
            bind(out0, output)

        elif source_kind in {"ROPE_APPLY", "ROPE_INVERSE"}:
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            inverse = source_kind == "ROPE_INVERSE"
            profile = "yarn" if ratio else "base"
            if attrs.get("compressed"):
                # The compressor rotates one row per *group*, and the released
                # prefill slices the same table with the compression ratio as
                # its stride -- group ``g`` carries the position of the first
                # token it pools.  A shared span-indexed row block cannot say
                # that, so the compressor gathers its own rows, under the same
                # predicate as the rotation they feed.
                coefficients = act(
                    f"{node_id}.coefficients", "fp32", (shape[0], 2 * ROPE_DIM)
                )
                builder.kernel(
                    f"{node_id}.coefficient_gather",
                    "GATHER",
                    (ten("request.start_pos"), rope_tables[profile]),
                    (coefficients,),
                    numeric_contract="exact_index_select_v1",
                    iteration_domain={"rows": shape[0], "width": 2 * ROPE_DIM},
                    attributes={
                        **attrs,
                        "coefficient_layout": (
                            "cos_rotary_width_then_sin_rotary_width"
                        ),
                        "pair_layout": "adjacent_complex",
                        "position_stride": int(attrs["ratio"]),
                        "rotary_width": ROPE_DIM,
                        "selector": "input.position_offset",
                    },
                    source_operation_id=node_id,
                    source_kind=source_kind,
                    phases=phases,
                    layer=layer,
                )
            else:
                coefficients = rope_rows[profile]
            emit(
                node_id,
                "ROPE_INVERSE" if inverse else "ROPE",
                (source, coefficients),
                (output,),
                iteration_domain={"rows": shape[0], "width": ROPE_DIM},
                attributes={**attrs, **rope_attributes(ratio, inverse=inverse)},
            )
            bind(out0, output)

        elif source_kind in {"FP8_QDQ", "FP4_QDQ"}:
            source = operands[0]
            shape = builder.shape[source]
            if source_kind == "FP8_QDQ":
                width = int(attrs["quantized_width"])
                block = KV_QUANT_BLOCK
                payload_dtype = "fp8_e4m3fn"
            else:
                width = int(shape[-1])
                block = FP4_BLOCK
                payload_dtype = "mxfp4_e2m1"
            payload, scale = quantize(
                source,
                block=block,
                dtype=payload_dtype,
                width=width,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "quantize"),
                attributes={**attrs, "block_size": block,
                            "output_dtype": payload_dtype},
                layer=layer,
                phases=phases,
            )
            output = act(out0, "bf16", shape)
            carried = width != int(shape[-1])
            emit(
                node_id,
                "DEQUANTIZE",
                (payload, scale, source) if carried else (payload, scale),
                (output,),
                step="reconstruct",
                iteration_domain={"rows": shape[0], "width": int(shape[-1]),
                                  "block": block},
                attributes={
                    **attrs,
                    "block_size": block,
                    "carried_width": int(shape[-1]) - width,
                    "output_dtype": "bf16",
                    "reconstructed_width": width,
                },
            )
            bind(out0, output)

        elif source_kind == "HADAMARD_ROTATE":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "HADAMARD",
                (source,),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        # -- window and compression state --------------------------------
        elif source_kind == "WINDOW_INDEX":
            output = act(out0, "u32", (span, SLIDING_WINDOW))
            emit(
                node_id,
                "WINDOW_INDEX",
                (ten("request.start_pos"),),
                (output,),
                iteration_domain={"tokens": span, "width": SLIDING_WINDOW},
                attributes={**attrs, "index_family": "causal_circular_window",
                            "padding_index": -1},
            )
            bind(out0, output)
            context_of[root]["window_indices"] = output

        elif source_kind == "DSPARK_WINDOW_INDEX":
            width = SLIDING_WINDOW + DRAFT_BLOCK
            output = act(out0, "u32", (DRAFT_BLOCK, width))
            emit(
                node_id,
                "WINDOW_INDEX",
                (ten("request.start_pos"),),
                (output,),
                iteration_domain={"tokens": DRAFT_BLOCK, "width": width},
                attributes={
                    **attrs,
                    "index_family": "causal_window_then_current_draft",
                    "padding_index": -1,
                },
            )
            bind(out0, output)
            context_of[root]["window_indices"] = output

        elif source_kind == "KV_WINDOW_WRITE":
            source = operands[0]
            committed = view(out0, "bf16", (SLIDING_WINDOW, HEAD_DIM))
            emit(
                node_id,
                "KV_APPEND",
                (source, ten("request.start_pos")),
                (committed,),
                iteration_domain={"rows": rows_of(source), "width": HEAD_DIM,
                                  "capacity": SLIDING_WINDOW},
                attributes={
                    **attrs,
                    # The sliding-window cache is a *ring*: the released model
                    # writes ``start_pos % window`` on a decode step and rotates
                    # the prefill's final window into the same alignment, so
                    # absolute position p lives at row p mod window in both
                    # directions.  Saying so is what stops the append from
                    # addressing the window with an absolute position, which is
                    # a row the window does not have as soon as the context
                    # passes 128 tokens.
                    "cache_row": "absolute_position_mod_window",
                    "window_size": SLIDING_WINDOW,
                },
            )
            bind(out0, committed)

        elif source_kind == "COMPRESS_PROJECT":
            # One operator over *both* compressor matrices, which is what the
            # frozen ``VECTOR.COMPRESS`` project sub-case is: in0 hidden, in1 the
            # KV projection, in2 the gate projection, out0 the packed
            # ``[.., 2, N]`` binary32 result whose penultimate index 0 is the KV
            # row and 1 the learned pooling score -- the frozen
            # ``projection_order: kv_then_gate``.  This export used to emit two
            # kernels of two operands each, one projection and an unpacked
            # result apiece, which is not the operation the ABI names: the
            # operator would have carried NO_ID in its mandatory gate slot and
            # the state update downstream would have had no packed row to read.
            source = operands[0]
            key_value_weight = role_weight(roles[0], scope, layer)
            gate_weight = role_weight(roles[1], scope, layer)
            width = int(attrs["output_features"])
            rows = rows_of(source)
            packed = act(f"{node_id}.packed", "fp32", (rows, 2, width))
            emit(
                node_id,
                "COMPRESS_PROJECT",
                (source, key_value_weight, gate_weight),
                (packed,),
                iteration_domain={"tokens": rows, "output_width": width,
                                  "reduction_width": HIDDEN, "projections": 2},
            )
            # Both source values name the same packed row; which plane a reader
            # takes is the penultimate index the frozen order fixes.
            bind(source_outputs[0], packed)
            bind(source_outputs[1], packed)

        elif source_kind == "COMPRESS_STATE_UPDATE":
            # The frozen ``COMPRESS_STATE_UPDATE`` sub-case adds the absolute
            # position embedding *itself*: in0 is the packed projection, in1 is
            # NO_ID (a state update has no projection matrix) and in2 is the APE
            # table.  This export used to emit a separate ``VECTOR.ADD`` of the
            # same table first, so a backend honouring both would have added the
            # position twice -- and that ADD was unexecutable anyway, because
            # ``VECTOR.ADD`` implements ``bf16_add_rne_v1`` while this addition
            # is binary32 over a cyclic ``[ratio, W]`` table against
            # ``[span, W]``, which no stride presents.  The operator does it.
            packed = operands[0]
            position_weight = role_weight(roles[0], scope, layer)
            node_ratio = int(attrs["ratio"])
            head_width = int(attrs["head_dim"])
            candidates = 2 * node_ratio if attrs["overlap"] else node_ratio
            rows = rows_of(packed)
            group_rows = groups[node_ratio]
            pool_key_value = act(
                source_outputs[0], "fp32", (group_rows, candidates, head_width)
            )
            pool_score = act(
                source_outputs[1], "fp32", (group_rows, candidates, head_width)
            )
            emit(
                node_id,
                "COMPRESS_STATE_UPDATE",
                (packed, position_weight),
                (pool_key_value, pool_score),
                step="raw_window_transaction",
                iteration_domain={"tokens": rows, "groups": group_rows,
                                  "candidates": candidates,
                                  "width": head_width},
                # This is the one kernel in the graph that leads with a
                # zero-capable extent and is still issued unconditionally, and
                # it says why rather than leaving the exception to be noticed.
                # The released ``Compressor.forward`` writes its raw window on
                # every step -- the remainder branch at ``start_pos == 0`` and
                # the ring write at decode both run before the
                # ``if not should_compress: return`` -- and only the *pooled*
                # outputs are conditional.  So the operator is not predicated;
                # its two outputs are, on the predicate it computes here.
                #
                # That predicate cannot be a ``COMPARE_SYMBOL``: its prefill
                # form is ``span_tokens >= ratio``, which a comparison states,
                # but its decode form is ``(start_pos + 1) % ratio == 0``, and
                # the frozen ``comparisons`` registry has no modulus.  That is
                # why it is a computed predicate value and why every consumer
                # names it rather than a symbol.
                attributes={
                    **attrs,
                    "predicate_output": f"{node_id}.should_compress",
                    "conditional_outputs": {
                        "pool_kv": f"{node_id}.should_compress",
                        "pool_scores": f"{node_id}.should_compress",
                    },
                    "predicate_condition": {
                        "prefill": _nonempty(group_rows),
                        "decode": f"context_length % {node_ratio} == 0",
                    },
                },
            )
            bind(source_outputs[0], pool_key_value)
            bind(source_outputs[1], pool_score)
            predicate_values.add(source_outputs[2])

        elif source_kind == "COMPRESS_POOL":
            pool_key_value, pool_score = operands[0], operands[1]
            head_width = int(attrs["head_dim"])
            group_rows = rows_of(pool_key_value)
            output = act(out0, "fp32", (group_rows, head_width))
            emit(
                node_id,
                "COMPRESS_POOL",
                (pool_key_value, pool_score),
                (output,),
                iteration_domain={"groups": group_rows,
                                  "candidates": int(attrs["candidate_count"]),
                                  "width": head_width},
            )
            bind(out0, output)

        elif source_kind == "BINARY32_TO_BF16":
            source = operands[0]
            shape = builder.shape[source]
            output = act(out0, "bf16", shape)
            emit(
                node_id,
                "CONVERT",
                (source,),
                (output,),
                iteration_domain={"rows": shape[0], "width": int(attrs["width"])},
            )
            bind(out0, output)

        elif source_kind == "COMPRESS_KV_WRITE":
            source = operands[0]
            head_width = int(attrs["head_dim"])
            capacity = context_tokens // int(attrs["ratio"])
            committed = view(out0, "bf16", (capacity, head_width))
            emit(
                node_id,
                "KV_APPEND",
                (source, ten("request.start_pos")),
                (committed,),
                iteration_domain={"rows": rows_of(source), "width": head_width,
                                  "capacity": capacity},
            )
            bind(out0, committed)

        elif source_kind == "COMPRESSED_KV_VALID_VIEW":
            source = operands[0]
            head_width = int(attrs["head_dim"])
            node_ratio = int(attrs["ratio"])
            family = (
                "compressed_key_value"
                if attrs["projection_scope"] == "main"
                else "index_compressed_key_value"
            )
            reads = (ensure_state(f"{family}.{scope}.layer.{layer}"),)
            output = view(out0, "bf16", (committed_groups[node_ratio], head_width))
            emit(
                node_id,
                "STATE_READ",
                (source,),
                (output,),
                iteration_domain={"rows": committed_groups[node_ratio],
                                  "width": head_width},
                # A18: this view leads with ``context_groups_ratioN``, which is
                # zero until the context holds one whole group.  A zero-extent
                # view is refused, so the read states the condition under which
                # it must not be issued rather than leaving a backend to notice
                # that its extent resolved to nothing.
                attributes={
                    **attrs,
                    "execution_predicate": _nonempty(committed_groups[node_ratio]),
                },
            )
            bind(out0, output)

        # -- attention row space and selection ---------------------------
        elif source_kind == "ATTENTION_KV_VIEW":
            sources = tuple(operands[:-2])
            rows = (
                SLIDING_WINDOW + DRAFT_BLOCK
                if scope == "dspark"
                else attention_rows[ratio]
            )
            output = view(out0, "bf16", (rows, HEAD_DIM))
            if scope == "dspark":
                # DSpark is decode-only and the source puts the fixed main
                # window before the five current draft rows.
                sources = (sources[1], sources[0])
                join_attributes: dict[str, Any] = {
                    **attrs,
                    "axis": 0,
                    "segment_order": "committed_window_then_current_draft",
                }
            else:
                # The main sparse-KV row space is phase-dependent in the pinned
                # source.  Prefill consumes the complete current request and
                # never a duplicate window; decode consumes all 128 physical
                # circular-window slots and never a duplicate current row.
                # Both append the same valid compressed prefix when it exists.
                # ``phase_inputs`` is an ordered subset of this kernel's IR
                # inputs, checked once by neutral admission and lowered by both
                # ABI 3.0 backends.
                compressed = [2] if len(sources) == 3 else []
                join_attributes = {
                    **attrs,
                    "axis": 0,
                    "phase_inputs": {
                        "prefill": [0, *compressed],
                        "decode": [1, *compressed],
                    },
                    "phase_segment_order": {
                        "prefill": "current_then_valid_compressed_prefix",
                        "decode": "committed_window_then_valid_compressed_prefix",
                    },
                    # ABI 3.0 section 12.2 relates context, start and span.
                    # Pinning the source-defined phase facts collapses each
                    # selected input sum to one exact A18 extent: prefill is
                    # ``span + floor(span / ratio)`` (or just ``span``), while
                    # decode is ``128 + floor(context / ratio)`` (or 128).
                    "phase_symbol_binding": {
                        "prefill": {"position_start": 0},
                        "decode": {"span_tokens": 1},
                    },
                }
            # A compressed state view has no row until a complete group exists,
            # and ABI 3.0 deliberately refuses zero-extent views.  The operand
            # therefore remains conditional; each selected phase layout has a
            # base-only path and a base-plus-prefix path.
            if scope != "dspark" and len(sources) == 3:
                join_attributes["operand_present_predicate"] = {
                    "2": _nonempty(committed_groups[ratio]),
                }
            emit(
                node_id,
                "CONCAT",
                sources,
                (output,),
                iteration_domain={"rows": rows, "width": HEAD_DIM},
                attributes=join_attributes,
            )
            bind(out0, output)

        elif source_kind == "INDEX_SCORE":
            query, key_value, head_weights = operands[0], operands[1], operands[2]
            rows = rows_of(query)
            output = act(out0, "bf16", (rows, committed_groups[4]))
            emit(
                node_id,
                "INDEX_SCORE",
                (query, key_value, head_weights),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "candidates": committed_groups[4],
                    "heads": INDEX_HEADS,
                    "width": INDEX_HEAD_DIM,
                },
                # A18: the candidate axis is ``context_groups_ratio4`` and
                # floors to zero for a context shorter than one group.
                attributes={
                    **attrs,
                    "execution_predicate": _nonempty(committed_groups[4]),
                },
            )
            bind(out0, output)

        elif source_kind == "INDEX_TOPK":
            score = operands[0]
            window_indices = operands[1]
            rows = rows_of(score)
            width = SLIDING_WINDOW + INDEX_TOPK
            output = act(out0, "u32", (rows, width))
            # Amendment A19.  This used to be two kernels -- a selection whose
            # indices were columns of the *score view*, and a feature-axis
            # CONCAT that put a window block in front of them -- and the pair
            # produced an index array with three defects the device found in
            # order: interior padding where the window block ran short, no
            # rebase onto the KV rows the selection actually names, and a causal
            # horizon counted in tokens on an axis measured in compression
            # groups.  The released model does all three at one place
            # (``Attention.forward`` concatenates *after* ``Indexer.forward``
            # has already added its offset), so the export does too: one
            # operator, in0 the scores, in1 the window block, in2 the pinned
            # compression ratio of the candidate axis.
            emit(
                node_id,
                "INDEX_TOPK",
                (score, window_indices, compression_ratio_constant(ratio)),
                (output,),
                step="masked_topk",
                iteration_domain={
                    "tokens": rows,
                    "top_k": INDEX_TOPK,
                    "window": SLIDING_WINDOW,
                    "width": width,
                },
                attributes={
                    **attrs,
                    "causal_mask": "compressed_group_completed_before_position",
                    "order": "score_descending_then_index_ascending",
                    "padding_index": -1,
                    "compression_ratio": ratio,
                    # ``k`` is the selection width, not the operand width: the
                    # output is the join, so its last extent is
                    # ``window + k`` and a backend that reads ``k`` off the
                    # output would declare 640 where 512 belongs.
                    "k": INDEX_TOPK,
                    "segment_widths": [SLIDING_WINDOW, INDEX_TOPK],
                    "segment_order": "window_then_rebased_compressed",
                    # The join's own extents are static and its window operand
                    # is always present, so unlike the two kernels it replaces
                    # this one is issued for every request: below one whole
                    # compression group the causal rule selects nothing and the
                    # result is the window block alone, which is exactly what
                    # the released model computes when ``kv_compress`` is
                    # ``None`` and the compressed block is ``[seqlen, 0]``.
                    # What does vanish there is the score operand -- its
                    # candidate axis is ``context_groups_ratioN`` and floors --
                    # so the operator names it rather than being predicated off
                    # as its producer is.  That is the difference A19 buys: a
                    # branch that used to reach the join now stops at an
                    # operand.
                    "operand_present_predicate": {
                        "0": _nonempty(committed_groups[ratio]),
                    },
                },
            )
            bind(out0, output)

        elif source_kind == "COMPRESSED_DENSE_INDEX":
            window_indices = operands[0]
            node_ratio = int(attrs["ratio"])
            # Amendment A20.  This was a ``WINDOW_INDEX`` enumeration joined to
            # the sliding window by an axis-1 ``CONCAT``, and the enumeration
            # was a substitution: ``ROUTE.WINDOW_INDEX`` emits
            # ``arange(first, last + 1)`` over the *absolute positions* of a
            # causal window, which is a second copy of the sliding window and
            # not the completed compression groups this family names.  Nothing
            # downstream could refuse it -- every index it names is a legal KV
            # row -- so twenty ratio-128 layers would have attended their window
            # twice, fluently and wrongly.
            #
            # The operator that does name them is the one next door.
            # ``get_compress_topk_idxs`` and ``Indexer.forward`` count the same
            # horizon on the same axis in the same units, add the same
            # ``offset``, and end at the same concatenation in
            # ``Attention.forward``; the only difference is that one ranks the
            # admitted candidates and the other takes them all.  So the dense
            # family is ``ROUTE.INDEX_TOPK`` with ``in0`` absent, and the group
            # horizon, the rebase onto the joined KV rows, the compaction, the
            # ascending order and the zero-candidate case are the ones A19
            # already built.
            capacity = context_tokens // node_ratio
            width = SLIDING_WINDOW + capacity
            output = act(out0, "u32", (span, width))
            emit(
                node_id,
                "INDEX_TOPK",
                (window_indices, compression_ratio_constant(node_ratio)),
                (output,),
                iteration_domain={
                    "tokens": span,
                    "top_k": capacity,
                    "window": SLIDING_WINDOW,
                    "width": capacity,
                },
                attributes={
                    **attrs,
                    # ``in0`` is not conditionally present, it is not there.
                    # The operands are placed either side of the hole rather
                    # than packed down, so the window block stays in ``in1``
                    # and the ratio in ``in2``.
                    "absent_operands": [0],
                    "causal_mask": "compressed_group_completed_before_position",
                    "order": "index_ascending",
                    "padding_index": -1,
                    "compression_ratio": node_ratio,
                    # With ``in0`` absent ``aux0`` is the *capacity* of the
                    # compressed segment rather than a selection width, and the
                    # causal rule still bounds what is taken: a query at
                    # absolute position ``p`` admits ``(p + 1) // ratio`` groups
                    # and no more than this many can be named.  It is a
                    # constant, which is the point -- the output is
                    # ``[span, 128 + k]`` with one request-determined axis
                    # where the join it replaces had two.
                    "k": capacity,
                    "segment_widths": [SLIDING_WINDOW, capacity],
                    "segment_order": "window_then_rebased_compressed",
                    # No ``operand_present_predicate``.  The score operand that
                    # used to vanish below one whole compression group is gone
                    # for every request, not only for those, and the window
                    # operand is always present -- so unlike the pair it
                    # replaces this kernel is issued unconditionally and has no
                    # alternative operand path for a backend to get wrong.
                },
            )
            bind(out0, output)

        elif source_kind == "SPARSE_ATTENTION":
            query, key_value, indices = operands[0], operands[1], operands[2]
            sink = role_weight(roles[0], scope, layer)
            rows = rows_of(query)
            output = act(out0, "bf16", (rows, HEADS, HEAD_DIM))
            emit(
                node_id,
                "ATTENTION_SPARSE",
                # TA-ABI3-OPCONV-1 amendment A6 freezes q, kv, indices, sink.
                (query, key_value, indices, sink),
                (output,),
                iteration_domain={
                    "tokens": rows,
                    "heads": HEADS,
                    "key_value_heads": KV_HEADS,
                    "width": HEAD_DIM,
                    "candidates": builder.shape[indices][-1],
                },
                attributes={
                    **attrs,
                    # Amendment A6: DeepSeek attends one *fused* KV head, so the
                    # KV operand is ``[rows, 512]`` and its head count cannot be
                    # read off an axis -- axis 1 of a fused tensor is the head
                    # width, not a head count.  Every query head shares that one
                    # KV head, which is a group size of 64.  The graph states it
                    # rather than leaving a backend to divide 64 by 512.
                    "group_size": HEADS // KV_HEADS,
                    "key_value_heads": KV_HEADS,
                },
            )
            bind(out0, output)

        elif source_kind == "GROUPED_OUTPUT_PROJECT":
            # ``einsum("bsgd,grd->bsgr")`` is *block diagonal over features*:
            # group ``g`` reads its own 4,096-column block of the head-major
            # activation and writes its own 1,024-column block of the result,
            # and every token passes through every group.
            #
            # ``TENSOR.GROUPED_MATMUL`` is the other grouped contraction, and it
            # is not this one: ``in2`` is a per-group *row* count and its groups
            # partition the activation's rows in ascending order, so no row
            # partition of a token-major buffer presents the released operation.
            # Emitting it anyway left ``in2`` empty -- a mandatory slot naming
            # ``NO_ID``, which every backend's arity gate correctly refuses.
            #
            # The faithful form is the one below: one contraction per column
            # block, joined back into one token-major row.  That join is on the
            # *feature* axis, which amendment A17 is what makes sayable; before
            # it, ``REDUCTION.GROUPED_CONCAT`` joined on axis 0 only, and the
            # release profile's eight ``[tokens, 1024]`` blocks joined that way
            # are ``[8 * tokens, 1024]`` -- group major where token major
            # belongs.  No strided output view repairs that, because group
            # ``g`` of token ``t`` lives at ``t * o_groups * o_rank + g *
            # o_rank`` and a rank-2 view has one row stride; and one kernel per
            # group writing column ranges of one tensor is many producers of
            # one tensor, which single assignment forbids and should.
            #
            # The weight is split the same way the contraction is.  Group ``g``
            # contracts against rows ``[o_rank * g, o_rank * (g + 1))`` of the
            # released ``[o_groups * o_rank, heads * head_dim // o_groups]``
            # fp8 matrix -- ``[8192, 4096]`` on Flash, ``[16384, 4096]`` on Pro
            # -- and the matching rows of its tile scale; both are contiguous
            # byte ranges, so each group is one ordinary checkpoint binding
            # whose digest is derived from the checkpoint and accepted only
            # when all of them reassemble to the locked whole-tensor SHA-256.
            source = operands[0]
            spec = role_specs(roles[0], scope, layer)
            if len(spec) != 1:
                raise DeepSeekV4KernelIRError(
                    f"role {roles[0]!r} resolves to {len(spec)} tensors, expected one"
                )
            weight_spec = spec[0]
            rows = rows_of(source)
            reduction = HEADS * HEAD_DIM // O_GROUPS
            if int(weight_spec.shape[0]) != O_GROUPS * O_RANK or int(
                weight_spec.shape[1]
            ) != reduction:
                raise DeepSeekV4KernelIRError(
                    f"{weight_spec.name!r} is {tuple(weight_spec.shape)}, not the "
                    f"{(O_GROUPS * O_RANK, reduction)} the grouped projection reads"
                )

            # One movement that says where the group axis is.  ``SELECT`` names
            # one index of one *existing* axis, and the attention output is
            # ``[tokens, groups * reduction]``: the axis has to exist before a
            # group of it can be named.  A backend that can alias a reshape
            # moves nothing here -- the element order is unchanged.
            grouped = act(
                f"{node_id}.group_axis", "bf16", (rows, O_GROUPS, reduction)
            )
            emit(
                f"{node_id}.group_axis",
                "COPY",
                (source,),
                (grouped,),
                iteration_domain={
                    "tokens": rows,
                    "groups": O_GROUPS,
                    "reduction_width": reduction,
                },
                attributes={
                    **attrs,
                    "group_axis": 1,
                    "group_count": O_GROUPS,
                    "row_order": "token_major_group_minor",
                },
            )

            blocks: list[str] = []
            for group in range(O_GROUPS):
                columns = act(
                    f"{node_id}.group{group}.columns", "bf16", (rows, reduction)
                )
                emit(
                    f"{node_id}.group{group}.select",
                    "SELECT",
                    (grouped,),
                    (columns,),
                    iteration_domain={"tokens": rows, "reduction_width": reduction},
                    attributes={
                        **attrs,
                        "axis": 1,
                        "index": group,
                        "plane": "attention_output_group",
                    },
                )
                partial = act(
                    f"{node_id}.group{group}.projection", "bf16", (rows, O_RANK)
                )
                emit(
                    f"{node_id}.group{group}.project",
                    "MATMUL",
                    (columns, group_weight(weight_spec, group, O_GROUPS)),
                    (partial,),
                    iteration_domain={
                        "tokens": rows,
                        "output_width": O_RANK,
                        "reduction_width": reduction,
                    },
                    attributes={
                        **attrs,
                        "accumulator_dtype": "fp32",
                        "group_index": group,
                        "input_dtype": "bf16",
                        "output_dtype": "bf16",
                        "weight_dequantization": "block_scaled_fp8_to_bf16",
                    },
                )
                blocks.append(partial)

            # The join.  An OPERATOR names four input views, so eight blocks are
            # two joins of four and one of two -- ten operands over three
            # kernels, which is the fewest a four-slot record admits.  Every one
            # of them joins on the feature axis, and the column order is the
            # operand order.
            output = concat_feature_axis(out0, blocks, rows, O_RANK)
            bind(out0, output)

        elif source_kind == "ROUTER_SCORE":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            rows = rows_of(source)
            output = act(out0, "fp32", (rows, ROUTED_EXPERTS))
            emit(
                node_id,
                "ROUTER_SCORE",
                (source, weight),
                (output,),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS,
                                  "reduction_width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "SQRT_SOFTPLUS":
            source = operands[0]
            rows = rows_of(source)
            output = act(out0, "fp32", (rows, ROUTED_EXPERTS))
            emit(
                node_id,
                "SQRT_SOFTPLUS",
                (source,),
                (output,),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS},
            )
            bind(out0, output)

        elif source_kind == "HASH_ROUTE":
            # The released routing is a *table read*, not a hash.
            # ``src/opentallas/routing.py`` evaluates ``tid2eid[token_id]`` over
            # the shipped ``[129280, 6]`` int64 table and keeps all six rows; a
            # consistent-hash route computes ``table[mix32(key) % slots]`` and
            # returns one destination.  ``TENSOR.EMBED_LOOKUP`` is the exact row
            # gather from a table indexed by a 32-bit ID -- no arithmetic and
            # therefore no conversion -- which is the operation exactly, down to
            # the bound check on the ID.  The neutral kind is therefore
            # ``EMBEDDING_LOOKUP``; ``ROUTE.HASH_ROUTE`` named an operator that
            # does not do this and no amendment is needed to stop naming it.
            table = role_weight(roles[0], scope, layer)
            rows = rows_of(operands[0])
            output = act(out0, "u32", (rows, TOP_K))
            emit(
                node_id,
                "EMBEDDING_LOOKUP",
                (ten("request.input_ids"), table),
                (output,),
                iteration_domain={"tokens": rows, "top_k": TOP_K},
                attributes={
                    **attrs,
                    # Every entry is a logical expert ID in [0, 255] stored in
                    # the low word of a little-endian int64, so the gathered row
                    # is exact under a 32-bit reading of the table and the
                    # result is the U32 the rest of the routing path expects.
                    "table_dtype": "i64",
                    "table_element_reading": "low_u32_of_i64",
                    "table_rows": VOCABULARY,
                    "table_value_maximum": ROUTED_EXPERTS - 1,
                },
            )
            bind(out0, output)
            context_of[root]["expert_indices"] = output

        elif source_kind == "BIASED_TOPK_ROUTE":
            score = operands[0]
            bias = role_weight(roles[0], scope, layer)
            rows = rows_of(score)
            indices = act(out0, "u32", (rows, TOP_K))
            values = act(f"{node_id}.selected_score", "fp32", (rows, TOP_K))
            emit(
                node_id,
                "BIASED_TOPK",
                (score, bias),
                (indices, values),
                iteration_domain={"tokens": rows, "experts": ROUTED_EXPERTS,
                                  "top_k": TOP_K},
                attributes={
                    **attrs,
                    "bias_scope": "selection_only",
                    "order": "score_descending_then_index_ascending",
                    "selected_score_output": (
                        "unused_the_released_graph_regathers_unbiased_scores"
                    ),
                },
            )
            bind(out0, indices)
            context_of[root]["expert_indices"] = indices

        elif source_kind == "ROUTER_WEIGHT_NORMALIZE":
            score, indices = operands[0], operands[1]
            rows = rows_of(score)
            selected = act(f"{node_id}.gathered", "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.gather",
                "GATHER",
                (score, indices),
                (selected,),
                step="unbiased_score_gather",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
            )
            normalized = act(f"{node_id}.normalized", "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.normalize",
                "WEIGHT_NORMALIZE",
                (selected,),
                (normalized,),
                step="selected_sum_normalize",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
            )
            output = act(out0, "fp32", (rows, TOP_K))
            emit(
                f"{node_id}.scale",
                "SCALE",
                (normalized,),
                (output,),
                step="route_scale",
                iteration_domain={"tokens": rows, "top_k": TOP_K},
                # ``scale_bits``, not ``factor``: see :func:`binary32_bits`.
                # The frozen reference calls this the ``route_scale_code`` and
                # refuses a zero, which is exactly the value a backend read
                # here while the attribute was spelled ``factor``.
                attributes={**attrs, "scale_bits": binary32_bits(ROUTE_SCALE),
                            "scale_dtype": "fp32"},
            )
            bind(out0, output)
            context_of[root]["route_weights"] = output

        elif source_kind == "EXPERT_DISPATCH":
            source, indices = operands[0], operands[1]
            rows = rows_of(source)
            routed_rows = (
                dispatch_rows if isinstance(rows, Symbolic) else rows * TOP_K
            )
            output = act(out0, "bf16", (routed_rows, HIDDEN))
            expert_rows = act(f"{node_id}.expert_ids", "u32", (routed_rows,))
            emit(
                node_id,
                "EXPERT_DISPATCH",
                (source, indices),
                (output, expert_rows),
                iteration_domain={"tokens": rows, "top_k": TOP_K,
                                  "routed_rows": routed_rows, "width": HIDDEN},
                attributes={
                    **attrs,
                    "row_order": "ascending_token_then_ascending_selection",
                    "routed_row_expert_output": True,
                },
            )
            bind(out0, output)
            context_of[root]["expert_rows"] = expert_rows
            context_of[root]["dispatch"] = output

        elif source_kind in {"MXFP4_SWIGLU", "FP8_SWIGLU"}:
            routed = source_kind == "MXFP4_SWIGLU"
            source = operands[0]
            rows = rows_of(source)
            if routed:
                # TA-ABI3-OPCONV-1 section 2: ROUTED_MATMUL reads
                # (activations, routed weights, expert IDs, route weights).  The
                # routed weights are one stacked ``[E, N, K]`` tensor, not 256
                # names in an attribute.  An attribute is not an operand: while
                # the stack travelled as one, the engine's mandatory weight slot
                # was empty and the expert IDs sat in it.
                gate_stack = role_weight_stack(roles[0], scope, layer)
                down_stack = role_weight_stack(roles[2], scope, layer)
                up_stack = role_weight_stack(roles[4], scope, layer)
                expert_rows = context_of[root]["expert_rows"]
                route_weights = context_of[root]["route_weights"]
                weight_attributes = {
                    "expert_count": ROUTED_EXPERTS,
                    "expert_weight_block_elements": FP4_BLOCK,
                    "expert_weight_dtype": "mxfp4_e2m1",
                    "expert_weight_order": "ascending_logical_expert_id",
                }
            else:
                gate_weight = role_weight(roles[0], scope, layer)
                down_weight = role_weight(roles[2], scope, layer)
                up_weight = role_weight(roles[4], scope, layer)
                weight_attributes = {}
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            gate = act(f"{node_id}.gate", "bf16", (rows, MOE_INTERMEDIATE))
            up = act(f"{node_id}.up", "bf16", (rows, MOE_INTERMEDIATE))
            contraction = {
                "rows": rows,
                "output_width": MOE_INTERMEDIATE,
                "reduction_width": HIDDEN,
            }
            for name, output_id, family_key in (
                ("gate", gate, "gate"),
                ("up", up, "up"),
            ):
                if routed:
                    stack = gate_stack if family_key == "gate" else up_stack
                    emit(
                        f"{node_id}.{name}",
                        "ROUTED_MATMUL",
                        (payload, stack, expert_rows),
                        (output_id,),
                        step=f"{name}_contraction",
                        iteration_domain=contraction,
                        attributes={
                            **attrs,
                            **weight_attributes,
                            "projection": name,
                        },
                    )
                else:
                    emit(
                        f"{node_id}.{name}",
                        "MATMUL",
                        (payload, gate_weight if name == "gate" else up_weight),
                        (output_id,),
                        step=f"{name}_contraction",
                        iteration_domain=contraction,
                        attributes={**attrs, "projection": name,
                                    "weight_block_elements": FP8_WEIGHT_BLOCK},
                    )
            activated = act(f"{node_id}.activated", "bf16",
                            (rows, MOE_INTERMEDIATE))
            emit(
                f"{node_id}.activate",
                "SWIGLU",
                (gate, up),
                (activated,),
                step="clamped_silu_product",
                iteration_domain={"rows": rows, "width": MOE_INTERMEDIATE},
                attributes={
                    **attrs,
                    "clamp": "gate_upper_and_up_symmetric",
                    "compute_dtype": "fp32",
                    "swiglu_limit": SWIGLU_LIMIT,
                },
            )
            if routed:
                weighted = act(f"{node_id}.weighted", "bf16",
                               (rows, MOE_INTERMEDIATE))
                emit(
                    f"{node_id}.route_weight",
                    "MUL",
                    (activated, route_weights),
                    (weighted,),
                    step="routing_weight_product",
                    iteration_domain={"rows": rows, "width": MOE_INTERMEDIATE},
                    attributes={**attrs,
                                "broadcast": "routed_row_to_intermediate_width"},
                )
                activated = weighted
            down_payload, _ = quantize(
                activated,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={
                    "block_size": ACTIVATION_BLOCK,
                    "output_dtype": "fp8_e4m3fn",
                    "rounding": "rne",
                    "scale_format": "ue8m0",
                    "source_operation_kind": source_kind,
                },
                layer=layer,
                phases=phases,
            )
            output = act(out0, "bf16", (rows, HIDDEN))
            if routed:
                emit(
                    f"{node_id}.down",
                    "ROUTED_MATMUL",
                    (down_payload, down_stack, expert_rows),
                    (output,),
                    step="down_contraction",
                    iteration_domain={"rows": rows, "output_width": HIDDEN,
                                      "reduction_width": MOE_INTERMEDIATE},
                    attributes={
                        **attrs,
                        **weight_attributes,
                        "projection": "down",
                    },
                )
            else:
                emit(
                    f"{node_id}.down",
                    "MATMUL",
                    (down_payload, down_weight),
                    (output,),
                    step="down_contraction",
                    iteration_domain={"rows": rows, "output_width": HIDDEN,
                                      "reduction_width": MOE_INTERMEDIATE},
                    attributes={**attrs, "projection": "down",
                                "weight_block_elements": FP8_WEIGHT_BLOCK},
                )
            bind(out0, output)

        elif source_kind == "EXPERT_REDUCE":
            routed_output, shared_output = operands[1], operands[2]
            rows = rows_of(shared_output)
            output = act(out0, "bf16", (rows, HIDDEN))
            expert_rows = context_of[root]["expert_rows"]
            emit(
                node_id,
                "EXPERT_REDUCE",
                (routed_output, shared_output, expert_rows),
                (output,),
                iteration_domain={"tokens": rows, "top_k": TOP_K,
                                  "width": HIDDEN},
                attributes={
                    **attrs,
                    "base_operand_index": 1,
                    "contribution_row_order": (
                        "ascending_token_then_ascending_selection"
                    ),
                    # The reduction's association is the whole content of the
                    # operation, not an implementation detail of it.  The
                    # released reference reduces the six routed contributions
                    # with the NUM-6.1 balanced binary32 tree, which the source
                    # graph already records as ``reduction_tree``; saying it
                    # again in the frozen vocabulary is what makes it reach the
                    # numeric descriptor, because a kernel that states no order
                    # is encoded as sequential -- a different number.
                    "reduction_order": "pairwise_tree",
                    # The released expert multiplies by the routing weight
                    # before its down projection, so the reduction must not
                    # apply it again: runtime/reference/swiglu.py takes
                    # route_weight_binary32_codes and
                    # runtime/reference/dispatch.py:reduce_expert_outputs_bf16
                    # takes no weights.
                    "routing_weight_application": (
                        "already_applied_inside_the_expert_before_the_down_"
                        "projection"
                    ),
                    "top_k": TOP_K,
                },
            )
            bind(out0, output)

        # -- head and selection -----------------------------------------
        elif source_kind == "LM_HEAD":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            if attrs["full_logits"]:
                selected = source
                rows = rows_of(source)
            else:
                rows = 1
                selected = act(f"{node_id}.final_position", "bf16", (1, HIDDEN))
                emit(
                    f"{node_id}.select",
                    "LAST_TOKEN_SELECT",
                    (source, ten("request.start_pos")),
                    (selected,),
                    step="final_source_position",
                    iteration_domain={"rows": 1, "width": HIDDEN},
                )
            output = act(out0, "fp32", (rows, VOCABULARY))
            emit(
                f"{node_id}.project",
                "VOCAB_PROJECT",
                (selected, weight),
                (output,),
                step="vocabulary_projection",
                iteration_domain={"rows": rows, "output_width": VOCABULARY,
                                  "reduction_width": HIDDEN},
            )
            bind(out0, output)

        elif source_kind == "SAMPLE":
            logits = operands[0]
            rows = rows_of(logits)
            scaled = act(f"{node_id}.scaled_logits", "fp32", (rows, VOCABULARY))
            # One operand, and the temperature in the numeric profile.  It used
            # to be two, the second being ``request.temperature_binary32``
            # bound to a declared *input* tensor -- and ABI 3.0's submission
            # record (``runtime.abi3.records.Submission``) has no temperature
            # field, so no request could ever write it.  Every backend placed
            # it as a zero-filled object, this operator multiplied a healthy
            # 129,280-wide logits vector by binary32 zero, all 129,280 logits
            # tied at zero, and ``greedy_lowest_token_id_argmax`` returned
            # token 0 -- with no trap, because multiplying by zero is legal.
            # The temperature is a *deployment* constant pinned at the released
            # generation configuration's default, and ABI 3.0's home for an
            # operator's scalar constant is the numeric descriptor's
            # ``scale_bits``, which ``VECTOR.SCALE`` sub-case 0 reads.
            emit(
                f"{node_id}.temperature",
                "SCALE",
                (logits,),
                (scaled,),
                step="temperature",
                iteration_domain={"rows": rows, "width": VOCABULARY},
                attributes={
                    **attrs,
                    "operation": "reciprocal_temperature_product",
                    "scale_bits": OFFICIAL_DEFAULT_TEMPERATURE_BINARY32,
                    "scale_dtype": "fp32",
                    "temperature_source": (
                        "deployment_constant_official_default; ABI 3.0 carries "
                        "no per-request temperature field"
                    ),
                },
            )
            token = act(f"{node_id}.argmax", TOKEN_DTYPE, (rows,))
            emit(
                f"{node_id}.select",
                "ARGMAX",
                (scaled,),
                (token,),
                step="greedy_argmax",
                iteration_domain={"rows": rows, "width": VOCABULARY},
                attributes={**attrs, "tie_rule": "lowest_token_id"},
            )
            appended = act(source_outputs[0], TOKEN_DTYPE, (rows,))
            emit(
                f"{node_id}.append",
                "TOKEN_APPEND",
                (token,),
                (appended,),
                step="token_append",
                iteration_domain={"rows": rows},
                attributes={**attrs, "eos_token_id": EOS_TOKEN_ID},
            )
            bind(source_outputs[0], appended)
            bind(source_outputs[1], ten("request.explicit_exponential_entropy"))

        # -- speculative profile ----------------------------------------
        elif source_kind == "TARGET_HIDDEN_CAPTURE":
            source = operands[0]
            rows = rows_of(source)
            summed = act(f"{node_id}.stream_sum", "fp32", (rows, HIDDEN))
            emit(
                f"{node_id}.sum",
                "PARTITION_SUM",
                (source,),
                (summed,),
                step="hyper_stream_sum",
                iteration_domain={"tokens": rows, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
            )
            output = act(out0, "bf16", (rows, HIDDEN))
            emit(
                f"{node_id}.mean",
                "SCALE",
                (summed,),
                (output,),
                step="hyper_stream_mean",
                iteration_domain={"tokens": rows, "width": HIDDEN},
                attributes={**attrs,
                            "scale_bits": binary32_bits(1.0 / HC_MULT),
                            "scale_dtype": "fp32"},
            )
            bind(out0, output)

        elif source_kind == "DSPARK_NOISE_EMBED":
            weight = role_weight(roles[0], scope, layer)
            draft_ids = act(f"{node_id}.draft_token_ids", TOKEN_DTYPE, (DRAFT_BLOCK,))
            emit(
                f"{node_id}.compose",
                "SCATTER",
                (operands[0],),
                (draft_ids,),
                step="noise_block",
                iteration_domain={"rows": DRAFT_BLOCK},
                attributes={
                    **attrs,
                    "carried_position": 0,
                    "fill_token_id": int(config["dspark_noise_token_id"]),
                },
            )
            embedded = act(f"{node_id}.embedded", "bf16", (DRAFT_BLOCK, HIDDEN))
            emit(
                f"{node_id}.lookup",
                "EMBEDDING_LOOKUP",
                (draft_ids, weight),
                (embedded,),
                step="draft_embedding",
                iteration_domain={"rows": DRAFT_BLOCK, "width": HIDDEN},
            )
            output = act(out0, "bf16", (DRAFT_BLOCK, HC_MULT, HIDDEN))
            # One embedding read once per hyper-connection stream.  This was a
            # ``CONCAT`` of four copies with ``axis: 1``, which is neither what
            # it is nor a legal join: four ``[rows, hidden]`` inputs joined on
            # the feature axis are ``[rows, 4 * hidden]``, not the
            # ``[rows, 4, hidden]`` this writes, and amendment A17 refuses the
            # rank mismatch at admission rather than reshaping past it.  It is
            # the same operation ``HC_EXPAND`` already states correctly: an
            # inserted axis every element of which is shared, which a backend
            # reads through one stride-zero axis.
            emit(
                f"{node_id}.expand",
                "BROADCAST",
                (embedded,),
                (output,),
                step="hyper_stream_expand",
                iteration_domain={"rows": DRAFT_BLOCK, "hyper_streams": HC_MULT,
                                  "width": HIDDEN},
                attributes={**attrs, "axis": 1, "extent": HC_MULT,
                            "source_replication": "single_draft_embedding"},
            )
            bind(out0, output)

        elif source_kind == "DSPARK_PREFILL_KV":
            source = operands[0]
            weight = role_weight(roles[0], scope, layer)
            norm_weight = role_weight(roles[2], scope, layer)
            rows = rows_of(source)
            payload, scale = quantize(
                source,
                block=ACTIVATION_BLOCK,
                dtype="fp8_e4m3fn",
                width=None,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "activation_quantize"),
                attributes={"block_size": ACTIVATION_BLOCK,
                            "output_dtype": "fp8_e4m3fn",
                            "scale_format": "ue8m0",
                            "source_operation_kind": source_kind},
                layer=layer,
                phases=phases,
            )
            projected = act(f"{node_id}.projection", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.project",
                "MATMUL",
                (payload, weight),
                (projected,),
                step="key_value_projection",
                iteration_domain={"rows": rows, "output_width": HEAD_DIM,
                                  "reduction_width": HIDDEN},
                state=False,
            )
            normalized = act(f"{node_id}.normalized", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.norm",
                "RMS_NORM",
                (projected, norm_weight),
                (normalized,),
                step="key_value_norm",
                iteration_domain={"rows": rows, "width": HEAD_DIM},
                state=False,
            )
            rotated = act(f"{node_id}.rotated", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.rope",
                "ROPE",
                (normalized, rope_rows["base"]),
                (rotated,),
                step="key_value_rope",
                iteration_domain={"rows": rows, "width": ROPE_DIM},
                attributes={**attrs, **rope_attributes(0, inverse=False)},
                state=False,
            )
            kv_payload, kv_scale = quantize(
                rotated,
                block=KV_QUANT_BLOCK,
                dtype="fp8_e4m3fn",
                width=NOPE_DIM,
                source_operation_id=node_id,
                source_kind=source_kind,
                contract=_contract(source_kind, "quantize"),
                attributes={"block_size": KV_QUANT_BLOCK,
                            "output_dtype": "fp8_e4m3fn",
                            "quantized_width": NOPE_DIM,
                            "scale_format": "ue8m0",
                            "source_operation_kind": source_kind},
                layer=layer,
                phases=phases,
            )
            reconstructed = act(f"{node_id}.key_value", "bf16", (rows, HEAD_DIM))
            emit(
                f"{node_id}.reconstruct",
                "DEQUANTIZE",
                (kv_payload, kv_scale, rotated),
                (reconstructed,),
                step="reconstruct",
                iteration_domain={"rows": rows, "width": HEAD_DIM,
                                  "block": KV_QUANT_BLOCK},
                attributes={**attrs, "carried_width": ROPE_DIM,
                            "reconstructed_width": NOPE_DIM},
                state=False,
            )
            committed = view(out0, "bf16", (SLIDING_WINDOW, HEAD_DIM))
            emit(
                f"{node_id}.commit",
                "KV_APPEND",
                (reconstructed, ten("request.start_pos")),
                (committed,),
                step="window_commit",
                iteration_domain={"rows": rows, "width": HEAD_DIM,
                                  "capacity": SLIDING_WINDOW},
                attributes={**attrs, "cache_row": "absolute_position_mod_window",
                            "window_size": SLIDING_WINDOW},
            )
            bind(out0, committed)

        elif source_kind == "MARKOV_AUTOREGRESSIVE_LOOP":
            draft_logits = operands[0]
            embedding_weight = role_weight(roles[0], scope, layer)
            head_weight = role_weight(roles[1], scope, layer)
            carried = operands[1]
            embeds: list[str] = []
            adjusted: list[str] = []
            for step_index in range(DRAFT_BLOCK):
                embed = act(
                    f"{node_id}.step{step_index}.embedding", "bf16", (1, MARKOV_RANK)
                )
                emit(
                    f"{node_id}.step{step_index}.lookup",
                    "EMBEDDING_LOOKUP",
                    (carried, embedding_weight),
                    (embed,),
                    step=f"step{step_index}_lookup",
                    iteration_domain={"rows": 1, "width": MARKOV_RANK},
                )
                bias = act(
                    f"{node_id}.step{step_index}.bias", "fp32", (1, VOCABULARY)
                )
                emit(
                    f"{node_id}.step{step_index}.project",
                    "VOCAB_PROJECT",
                    (embed, head_weight),
                    (bias,),
                    step=f"step{step_index}_head",
                    iteration_domain={"rows": 1, "output_width": VOCABULARY,
                                      "reduction_width": MARKOV_RANK},
                )
                row = act(
                    f"{node_id}.step{step_index}.logits", "fp32", (1, VOCABULARY)
                )
                emit(
                    f"{node_id}.step{step_index}.add",
                    "ADD",
                    (draft_logits, bias),
                    (row,),
                    step=f"step{step_index}_logit_bias",
                    iteration_domain={"rows": 1, "width": VOCABULARY},
                    attributes={**attrs, "left_row_index": step_index},
                )
                token = act(f"{node_id}.step{step_index}.token", TOKEN_DTYPE, (1,))
                emit(
                    f"{node_id}.step{step_index}.select",
                    "ARGMAX",
                    (row,),
                    (token,),
                    step=f"step{step_index}_argmax",
                    iteration_domain={"rows": 1, "width": VOCABULARY},
                    attributes={**attrs, "tie_rule": "lowest_token_id"},
                )
                carried_next = act(
                    f"{node_id}.step{step_index}.carried", TOKEN_DTYPE, (1,)
                )
                emit(
                    f"{node_id}.step{step_index}.append",
                    "TOKEN_APPEND",
                    (token,),
                    (carried_next,),
                    step=f"step{step_index}_append",
                    iteration_domain={"rows": 1},
                    attributes={**attrs, "draft_token_ring_width": DRAFT_BLOCK + 1,
                                "draft_token_ring_position": step_index + 1},
                )
                carried = carried_next
                embeds.append(embed)
                adjusted.append(row)
            embed_head = act(f"{node_id}.embedding_head", "bf16", (4, MARKOV_RANK))
            emit(
                f"{node_id}.embedding_head",
                "CONCAT",
                tuple(embeds[:4]),
                (embed_head,),
                step="embedding_concat_head",
                iteration_domain={"rows": 4, "width": MARKOV_RANK},
                attributes={**attrs, "axis": 0},
            )
            embed_all = act(
                source_outputs[2], "bf16", (DRAFT_BLOCK, MARKOV_RANK)
            )
            emit(
                f"{node_id}.embedding_all",
                "CONCAT",
                (embed_head, embeds[4]),
                (embed_all,),
                step="embedding_concat_tail",
                iteration_domain={"rows": DRAFT_BLOCK, "width": MARKOV_RANK},
                attributes={**attrs, "axis": 0},
            )
            logit_head = act(f"{node_id}.logit_head", "fp32", (4, VOCABULARY))
            emit(
                f"{node_id}.logit_head",
                "CONCAT",
                tuple(adjusted[:4]),
                (logit_head,),
                step="logit_concat_head",
                iteration_domain={"rows": 4, "width": VOCABULARY},
                attributes={**attrs, "axis": 0},
            )
            logit_all = act(
                source_outputs[1], "fp32", (DRAFT_BLOCK, VOCABULARY)
            )
            emit(
                f"{node_id}.logit_all",
                "CONCAT",
                (logit_head, adjusted[4]),
                (logit_all,),
                step="logit_concat_tail",
                iteration_domain={"rows": DRAFT_BLOCK, "width": VOCABULARY},
                attributes={**attrs, "axis": 0},
            )
            bind(source_outputs[0], carried)
            bind(source_outputs[1], logit_all)
            bind(source_outputs[2], embed_all)
            bind(source_outputs[3], ten("request.explicit_exponential_entropy"))

        elif source_kind == "CONFIDENCE_SCORE":
            hidden_value, markov_value = operands[0], operands[1]
            weight = role_weight(roles[0], scope, layer)
            width = HIDDEN + MARKOV_RANK
            joined = act(f"{node_id}.joined", "bf16", (DRAFT_BLOCK, width))
            emit(
                f"{node_id}.concat",
                "CONCAT",
                (hidden_value, markov_value),
                (joined,),
                step="hidden_then_markov",
                iteration_domain={"rows": DRAFT_BLOCK, "width": width},
                attributes={**attrs, "axis": 1,
                            "segment_widths": [HIDDEN, MARKOV_RANK]},
            )
            output = act(out0, "fp32", (DRAFT_BLOCK, 1))
            emit(
                f"{node_id}.project",
                "MATMUL",
                (joined, weight),
                (output,),
                step="confidence_projection",
                iteration_domain={"rows": DRAFT_BLOCK, "output_width": 1,
                                  "reduction_width": width},
            )
            bind(out0, output)

        else:  # pragma: no cover - the catalogue is closed and covered
            raise DeepSeekV4KernelIRError(
                f"source operator kind {source_kind!r} has no neutral lowering; "
                "adding one requires a versioned change to "
                "compiler/ir/v3/kernel_ir.py and compiler/ir/v3/lowering.py"
            )

    # ------------------------------------------------------------------
    # Assemble
    # ------------------------------------------------------------------
    declared_symbols = {symbol.name for symbol in symbols}
    for tensor in builder.tensors:
        for extent in tensor.shape:
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV4KernelIRError(
                    f"tensor {tensor.tensor_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )
    for kernel in builder.kernels:
        for extent in kernel.iteration_domain.values():
            if isinstance(extent, Symbolic) and extent.symbol not in declared_symbols:
                raise DeepSeekV4KernelIRError(
                    f"kernel {kernel.kernel_id} uses undeclared symbol "
                    f"{extent.symbol!r}"
                )

    missing_kinds = sorted(set(OPERATOR_CATALOG) - set(emitted_source_kinds))
    if include_speculative and missing_kinds:
        raise DeepSeekV4KernelIRError(
            f"speculative export omitted source kinds {missing_kinds}"
        )

    outputs: list[str] = [
        value_tensor["main.sample.tokens"],
        value_tensor["main.lm_head.output"],
    ]
    if include_speculative:
        outputs.extend(
            (
                value_tensor["dspark.markov_loop.tokens"],
                value_tensor["dspark.markov_loop.adjusted_logits"],
                value_tensor["dspark.confidence.output"],
            )
        )
    # ``temperature`` is deliberately absent: it is a declared deployment
    # constant, not a request field the host can supply.  See its declaration.
    inputs = (token_ids, position_offset, session_ids, entropy)
    state_ids = tuple(resource.state_id for resource in builder.states)

    generation_policy = {
        "bos_token_id": BOS_TOKEN_ID,
        "eos_token_ids": [EOS_TOKEN_ID],
        "eos_source": "generation_config.json",
        "include_eos_in_output": True,
        "maximum_new_tokens": int(maximum_new_tokens),
        "policy_id": GENERATION_POLICY_ID,
        "selection_mode": "greedy_argmax_lowest_id",
        "speculative_profile": bool(include_speculative),
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

    graph = KernelGraph(
        model_id=MODEL_ID,
        source={
            "architectural_max_context": ARCHITECTURAL_MAX_CONTEXT,
            "checkpoint_lock_id": lock["lock_id"],
            "checkpoint_payload_bytes": PAYLOAD_BYTES,
            "checkpoint_tensor_count": TENSOR_COUNT,
            "deployment_context_tokens": context_tokens,
            "graph_contract_id": contract["graph_contract_id"],
            "inference_config_sha256": INFERENCE_CONFIG_SHA256,
            "kernel_source_sha256": KERNEL_SOURCE_SHA256,
            "model_source_sha256": MODEL_SOURCE_SHA256,
            "profile": (
                "target_and_speculative" if include_speculative else "target_only"
            ),
            "repository": REPOSITORY,
            "revision": REVISION,
            "source_node_count": len(nodes),
            "tensor_structure_sha256": TENSOR_STRUCTURE_SHA256,
        },
        symbols=symbols,
        tensors=tuple(builder.tensors),
        states=tuple(builder.states),
        kernels=tuple(builder.kernels),
        entrypoints=(
            Entrypoint(
                phase="prefill",
                inputs=inputs,
                outputs=tuple(outputs),
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
            Entrypoint(
                phase="decode",
                inputs=inputs,
                outputs=tuple(outputs),
                states=state_ids,
                generation_policy=GENERATION_POLICY_ID,
            ),
        ),
        numeric_profile=NUMERIC_PROFILE,
        generation_policy=generation_policy,
    )
    errors = check_neutral(graph)
    if errors:
        raise DeepSeekV4KernelIRError(
            "neutral IR rejected:\n  " + "\n  ".join(errors[:40])
        )
    return graph


def graph_census(graph: KernelGraph) -> dict[str, Any]:
    """Return the auditable census the release report quotes."""

    by_kind: Counter = Counter(kernel.kind for kernel in graph.kernels)
    by_source: Counter = Counter(
        kernel.source_operation_id.split(".")[0] for kernel in graph.kernels
    )
    roles: Counter = Counter(tensor.role for tensor in graph.tensors)
    dtypes: Counter = Counter(tensor.dtype for tensor in graph.tensors)
    bound = [t for t in graph.tensors if t.binding is not None]
    return {
        "bound_weight_bytes": sum(t.binding.bytes for t in bound),  # type: ignore[union-attr]
        "bound_weight_tensors": len(bound),
        "entrypoints": [e.phase for e in graph.entrypoints],
        "graph_id": graph.graph_id,
        "kernel_count": len(graph.kernels),
        "kernels_by_kind": dict(sorted(by_kind.items())),
        "kernels_by_scope": dict(sorted(by_source.items())),
        "model_id": graph.model_id,
        "state_count": len(graph.states),
        "states_by_class": dict(
            sorted(Counter(s.state_class for s in graph.states).items())
        ),
        "symbol_count": len(graph.symbols),
        "tensor_count": len(graph.tensors),
        "tensors_by_dtype": dict(sorted(dtypes.items())),
        "tensors_by_role": dict(sorted(roles.items())),
    }


__all__ = [
    "ARCHITECTURAL_MAX_CONTEXT",
    "DEFAULT_CHECKPOINT_LOCK",
    "DEFAULT_CONTEXT_TOKENS",
    "DEFAULT_SNAPSHOT",
    "DeepSeekV4KernelIRError",
    "DeepSeekV4Profile",
    "CONTRACT_BASE_BY_SOURCE_KIND",
    "FLASH_PROFILE",
    "LOWERING_PLAN",
    "MODEL_PROFILES",
    "NUMERIC_PROFILE",
    "PRO_PROFILE",
    "export_deepseek_v4_kernel_graph",
    "graph_census",
    "lowering_plan",
    "read_checkpoint_bindings",
    "resolve_model_profile",
    "verify_checkpoint_bindings",
]
