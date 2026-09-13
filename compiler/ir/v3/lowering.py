"""Frozen map from neutral kernel kinds to ABI 3.0 engine operations.

This table is the contract between three independently written components: the
model exporters that emit neutral kernels, the backends that emit ABI 3.0
operator descriptors, and the simulator engines that execute them.  Because all
three read this one table, a kernel kind cannot mean one thing in the Qwen lane
and another in the DeepSeek lane, and a backend cannot invent a private opcode.

A kind that is not in this table is a compile error.  ADR-003 section 15:
"unknown, generic-callback, unpriced, or framework-owned operations are compile
errors".
"""

from __future__ import annotations

from typing import Mapping, NamedTuple, Sequence

from runtime.abi3.constants import (
    Attention,
    Dma,
    Major,
    Reduction,
    Route,
    Selection,
    State,
    Tensor as TensorOp,
    Vector,
)


class EngineOp(NamedTuple):
    """One ABI 3.0 engine operation plus its operand arity."""

    family: int
    sub: int
    inputs: int
    outputs: int


#: Neutral kernel kind -> ABI 3.0 engine operation.
KERNEL_TO_ENGINE: Mapping[str, EngineOp] = {
    # movement and lookup
    "EMBEDDING_LOOKUP": EngineOp(Major.TENSOR, TensorOp.EMBED_LOOKUP, 2, 1),
    "GATHER": EngineOp(Major.DMA, Dma.GATHER, 2, 1),
    "SCATTER": EngineOp(Major.DMA, Dma.SCATTER, 2, 1),
    "COPY": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    "CONCAT": EngineOp(Major.REDUCTION, Reduction.GROUPED_CONCAT, 4, 1),
    # A broadcast is not a concatenation.  ``REDUCTION.GROUPED_CONCAT`` joins
    # along axis 0, so four copies of ``[tokens, width]`` become
    # ``[4 * tokens, width]`` -- four consecutive *tokens* where four *streams*
    # belong.  What ``unsqueeze(axis).repeat(extent)`` actually is, on a machine
    # whose operands are strided views, is one source read through an axis of
    # stride zero.  That is a movement, so it lowers to ``DMA.TRANSFER`` with
    # in0 the stride-zero reading of the source and out0 the materialised
    # result; a backend that can alias the destination need not move anything
    # at all.
    "BROADCAST": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    # A select is a broadcast read backwards.  ``unsqueeze(axis).repeat(extent)``
    # is one source read through a stride-zero axis; ``t[..., index, ...]`` is
    # one source read through an element offset with that axis dropped.  Neither
    # needs an opcode: both are a movement whose whole content is the view, so
    # both lower to ``DMA.TRANSFER`` and a backend that can alias the
    # destination need move nothing at all.  The frozen ``VECTOR.MHC`` row is
    # what asks for it -- ``HYPER_CONNECT_PRE`` packs its pre and post
    # coefficients into one ``[tokens, 2, streams]`` output because the ABI
    # gives the second output view to the combination matrix, and the two
    # planes are then read by two different later operations.
    "SELECT": EngineOp(Major.DMA, Dma.TRANSFER, 1, 1),
    # contraction
    "MATMUL": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "GROUPED_MATMUL": EngineOp(Major.TENSOR, TensorOp.GROUPED_MATMUL, 3, 1),
    "ROUTED_MATMUL": EngineOp(Major.TENSOR, TensorOp.ROUTED_MATMUL, 4, 1),
    # normalisation and elementwise
    "RMS_NORM": EngineOp(Major.VECTOR, Vector.RMS_NORM, 2, 1),
    "HEAD_RMS_NORM": EngineOp(Major.VECTOR, Vector.HEAD_RMS_NORM, 2, 1),
    "ROPE": EngineOp(Major.VECTOR, Vector.ROPE, 2, 1),
    "ROPE_INVERSE": EngineOp(Major.VECTOR, Vector.ROPE, 2, 1),
    "ADD": EngineOp(Major.VECTOR, Vector.ADD, 2, 1),
    "MUL": EngineOp(Major.VECTOR, Vector.SCALE, 2, 1),
    "SCALE": EngineOp(Major.VECTOR, Vector.SCALE, 2, 1),
    "SILU_MUL": EngineOp(Major.VECTOR, Vector.SILU_MUL, 2, 1),
    "SWIGLU": EngineOp(Major.VECTOR, Vector.SILU_MUL, 2, 1),
    "CONVERT": EngineOp(Major.VECTOR, Vector.CONVERT, 1, 1),
    "QUANTIZE": EngineOp(Major.VECTOR, Vector.CONVERT, 1, 2),
    # Three inputs, because DeepSeek's FP8 QDQ is *partial*: it quantises the
    # non-rotary channels and passes the rotary channels through untouched, so
    # the third operand is the passthrough source. A two-operand dequantize
    # cannot express that without a separate concat.
    "DEQUANTIZE": EngineOp(Major.VECTOR, Vector.CONVERT, 3, 1),
    "HADAMARD": EngineOp(Major.VECTOR, Vector.HADAMARD, 1, 1),
    "SOFTMAX": EngineOp(Major.VECTOR, Vector.SOFTMAX, 1, 1),
    "SQRT_SOFTPLUS": EngineOp(Major.VECTOR, Vector.SQRT_SOFTPLUS, 1, 1),
    "SIGMOID": EngineOp(Major.VECTOR, Vector.SCALE, 1, 1),
    # attention
    "ATTENTION_DENSE": EngineOp(Major.ATTENTION, Attention.DENSE, 4, 1),
    "ATTENTION_GQA": EngineOp(Major.ATTENTION, Attention.GQA, 4, 1),
    "ATTENTION_SPARSE": EngineOp(Major.ATTENTION, Attention.SPARSE, 4, 1),
    "INDEX_SCORE": EngineOp(Major.VECTOR, Vector.INDEX_SCORE, 3, 1),
    "WINDOW_INDEX": EngineOp(Major.ROUTE, Route.WINDOW_INDEX, 1, 1),
    # Amendment A30.  Same operand row as ``WINDOW_INDEX`` -- one position
    # vector in, one index block out -- and a different operator, because
    # the row it writes is broadcast across the draft block, spans two
    # disjoint address ranges and slides not at all.  The distinct
    # subopcode is what welds the declaration to the behaviour.
    "DSPARK_WINDOW_INDEX": EngineOp(
        Major.ROUTE, Route.DSPARK_WINDOW_INDEX, 1, 1
    ),
    # compression and hyper-connections
    "COMPRESS_PROJECT": EngineOp(Major.VECTOR, Vector.COMPRESS, 3, 1),
    # AM-E10.  h, key, value, q, k in; the gated residual out.  Fused so one
    # numeric contract covers the normalised dot, signed sqrt, sigmoid and add.
    "ENGRAM_GATE": EngineOp(Major.VECTOR, Vector.ENGRAM_GATE, 5, 1),
    "COMPRESS_POOL": EngineOp(Major.VECTOR, Vector.COMPRESS, 2, 1),
    "COMPRESS_STATE_UPDATE": EngineOp(Major.VECTOR, Vector.COMPRESS, 2, 2),
    "HYPER_CONNECT_PRE": EngineOp(Major.VECTOR, Vector.MHC, 4, 2),
    "HYPER_CONNECT_POST": EngineOp(Major.VECTOR, Vector.MHC, 4, 1),
    "HYPER_CONNECT_HEAD": EngineOp(Major.VECTOR, Vector.MHC, 4, 1),
    # routing
    "ROUTER_SCORE": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "TOPK": EngineOp(Major.ROUTE, Route.TOPK, 1, 2),
    "BIASED_TOPK": EngineOp(Major.ROUTE, Route.BIASED_TOPK, 2, 2),
    "HASH_ROUTE": EngineOp(Major.ROUTE, Route.HASH_ROUTE, 2, 1),
    # AM-E10.  BLOCK_MAX takes the score row and emits one score per block;
    # CANDIDATE_MASK takes the chosen block ids and emits the per-position
    # mask INDEX_TOPK now accepts in slot 3.
    "BLOCK_MAX": EngineOp(Major.ROUTE, Route.BLOCK_MAX, 1, 1),
    "CANDIDATE_MASK": EngineOp(Major.ROUTE, Route.CANDIDATE_MASK, 1, 1),
    # AM-E10.  Token ids in, Engram row ids out: integer multiply-modulo,
    # one row id per hash head and n-gram order.
    "NGRAM_HASH": EngineOp(Major.DMA, Dma.NGRAM_HASH, 1, 1),
    # Amendment A19: INDEX_TOPK selects, rebases and joins.  in0 the index
    # scores, in1 the sliding-window index block it is joined to, in2 the
    # one-element compression ratio of the candidate axis.  Amendment A20 makes
    # in0 optional -- see ``OPTIONAL_INPUT_SLOTS`` -- so the same operator, with
    # the ranking removed, is the dense compressed-index family.
    "INDEX_TOPK": EngineOp(Major.ROUTE, Route.INDEX_TOPK, 3, 1),
    "WEIGHT_NORMALIZE": EngineOp(Major.ROUTE, Route.WEIGHT_NORMALIZE, 1, 1),
    # Two outputs: the dispatched activations and the expert IDs they were
    # dispatched under. Re-emitting the IDs keeps the dataflow into
    # ROUTED_MATMUL explicit rather than implied by ordering.
    "EXPERT_DISPATCH": EngineOp(Major.ROUTE, Route.EXPERT_DISPATCH, 2, 2),
    "EXPERT_REDUCE": EngineOp(Major.REDUCTION, Reduction.EXPERT_SUM, 3, 1),
    # reduction and selection
    "ORDERED_SUM": EngineOp(Major.REDUCTION, Reduction.ORDERED_SUM, 2, 1),
    "PARTITION_SUM": EngineOp(Major.REDUCTION, Reduction.PARTITION_SUM, 2, 1),
    "LAST_TOKEN_SELECT": EngineOp(Major.DMA, Dma.GATHER, 2, 1),
    "VOCAB_PROJECT": EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1),
    "ARGMAX": EngineOp(Major.SELECTION, Selection.ARGMAX, 1, 1),
    "TOKEN_APPEND": EngineOp(Major.SELECTION, Selection.TOKEN_APPEND, 1, 1),
    # state
    # STATE_READ names the state view it reads and the activation it produces;
    # STATE_PREPARE and STATE_COMMIT are pure transitions over the resource
    # named by the instruction's descriptor and carry no operands.
    "STATE_READ": EngineOp(Major.STATE, State.READ, 1, 1),
    "STATE_PREPARE": EngineOp(Major.STATE, State.PREPARE, 0, 0),
    "STATE_COMMIT": EngineOp(Major.STATE, State.COMMIT, 0, 0),
    # A KV append is a movement, not a conversion. Mapping it to VECTOR.CONVERT
    # made the engine read it as a dequantize and compare the wrong shapes.
    # It is a scatter: one source plane written at the positions the request
    # names. Operand row, frozen in TA-ABI3-OPCONV-1: in0 source, in1
    # destination positions. That is the reverse of DMA.SCATTER's own row, so
    # the backend permutes the two when it binds the operator -- a lowering
    # detail, not a semantic one. Both models already emit (source, index),
    # and rewriting either exporter to match the engine's slot order would put
    # a backend concern into the neutral IR.
    "KV_APPEND": EngineOp(Major.DMA, Dma.SCATTER, 2, 1),
}


#: Attribute naming the ABI **input slots** a kernel leaves ``NO_ID``.
#:
#: The static counterpart of ``operand_present_predicate``.  That attribute says
#: an operand is present under a condition; this one says an operand is not
#: there at all, so a backend places the remaining operands *either side* of the
#: hole rather than packing them down.  The values are ABI slot numbers, not IR
#: input indices, because the operand this names is absent from ``inputs`` and
#: an index into a list it is not in would mean nothing.
ABSENT_OPERANDS = "absent_operands"

#: Attribute describing a phase-dependent ordered subset of a neutral
#: kernel's IR inputs.  It is intentionally an IR-input map rather than an ABI
#: operand row: the model owns which semantic segments exist in each phase,
#: while each backend remains responsible for placing those inputs into the
#: frozen ABI 3.0 slots.
PHASE_INPUTS = "phase_inputs"


#: ABI input slots a neutral kind may declare statically absent, by kind.
#:
#: Frozen, and deliberately short.  A slot is in this table only because the
#: wire format says the operator reads it optionally and an exporter has a real
#: reason to leave it empty; a kind that is not here may not declare
#: ``absent_operands`` at all.  Growing it is an amendment, not a backend's
#: private decision -- which is the whole difference between this table and a
#: hole table each backend keeps for itself.
#:
#: ``INDEX_TOPK`` is the only entry.  Amendment A19 made ``in1`` (the joined
#: window block) and ``in2`` (the compression ratio) optional -- ``NO_ID`` in
#: both is the un-joined, ratio-one operator ``ROUTE.INDEX_TOPK`` has always
#: been.  Amendment A20 made ``in0`` (the index scores) optional: with no score
#: view there is no ranking, and the operator emits every candidate the causal
#: rule admits in ascending group order, which is the released
#: ``get_compress_topk_idxs``.
OPTIONAL_INPUT_SLOTS: Mapping[str, frozenset[int]] = {
    #: AM-E10 adds slot 3, the candidate mask.  A mask OPERAND keeps the
    #: top-k engine unchanged: the reference masks scores to -inf inside the
    #: candidate blocks, which is an input to selection, not a new selector.
    "INDEX_TOPK": frozenset({0, 1, 2, 3}),
}


#: The index families each neutral kind's frozen operator actually produces.
#:
#: A gate, not a label.  ``index_family`` began as a comment -- it named which
#: released helper a kernel reproduces, and no engine, verifier or backend read
#: it -- and that is precisely the shape that let twenty ratio-128 layers
#: declare ``causal_compressed_dense`` while lowering to an operator that emits
#: a sliding-window position list.  Every index the substitution named was a
#: legal KV row, so the operand checks passed, the bound checks passed and the
#: numeric checks passed; the layers would have attended their window twice and
#: never a compressed group, fluently and wrongly.
#:
#: So the attribute either had to be refused where it is not implemented or
#: cease to exist, and it is refused -- **here**, at neutral admission, so that
#: it is one rule both backends inherit rather than two backends each
#: remembering.  ``ROUTE.WINDOW_INDEX`` writes the causal window in source
#: order and tail-pads it.  In prefill its values are absolute rows in the
#: current request; in decode they are physical circular-buffer slots.  That
#: phase-dependent representation is the whole of what it produces, and
#: ``causal_circular_window`` is the whole of what may be claimed for it.
#:
#: Two families are therefore refused **on** ``WINDOW_INDEX`` and both refusals
#: are load-bearing.  Neither is refused because it is unimplementable; each is
#: refused because the operator next to it is the one that produces it, and a
#: family that can be claimed on two operators is a family no check can read
#: back out of a lowered program.
#:
#: * ``causal_compressed_dense`` -- ``arange(0, context // ratio) + offset``,
#:   counted in compression groups and rebased onto the joined KV rows.  After
#:   amendment A20 nothing emits it against ``WINDOW_INDEX``: it is
#:   ``ROUTE.INDEX_TOPK`` with ``in0`` absent, where the group horizon, the
#:   rebase and the compaction already live.
#: * ``causal_window_then_current_draft`` -- the released
#:   ``get_dspark_topk_idxs``, ``arange(0, min(window, p + 1))`` followed by the
#:   draft block at ``window + arange(block)``.  Two segments in a disjoint
#:   address range, identical for every draft query, with no sliding.
#:   ``WINDOW_INDEX`` produces a *sliding* window ending at each query and pads
#:   the rest, so the substitution would be the same defect a second time.
#:   Amendment A30 makes it an operator rather than a refusal --
#:   ``ROUTE.DSPARK_WINDOW_INDEX``, below -- and ``WINDOW_INDEX`` still refuses
#:   it, for the reason just given and unchanged by A30.
#:
#: ``DSPARK_WINDOW_INDEX`` is therefore the mirror entry, and what it produces
#: is worth stating in this file's own terms rather than by reference.  The
#: request cursor ``p`` fixes one row: the populated physical slots of the main
#: circular window, ``arange(0, min(window, p + 1))``, followed by the draft
#: block at ``window + arange(0, block)`` -- a second segment in an address
#: range the window operator cannot reach, because those rows are appended
#: *after* the window's capacity rather than stored in it.  That single row is
#: written to all ``block`` draft queries **unchanged**.  The broadcast is the
#: semantics: attention within the draft block is bidirectional, every draft
#: query seeing every draft key, which is the only thing that makes one
#: parallel block pass worth running.  Nothing slides, nothing reduces modulo
#: the window, and no row carries a per-query limit.
#:
#: So the two families differ in four independent ways at the same operand row
#: -- sliding versus fixed, per-row versus broadcast, one segment versus two,
#: modulo-reduced versus slot-enumerated -- and every index either of them
#: names is a legal row of the same fused KV operand.  That is exactly why the
#: distinction cannot live in an attribute alone: the operand checks, the bound
#: checks and the numeric checks all pass either way, and ``ATTENTION.SPARSE``
#: reads the row as a set, so a wrong-but-legal row yields a full, finite,
#: fluent softmax over the wrong keys.  A substitution between them now has to
#: change the **subopcode**, which the engine, both backends' aux builders and
#: the microcode step table each check.
INDEX_FAMILIES: Mapping[str, frozenset[str]] = {
    "WINDOW_INDEX": frozenset({"causal_circular_window"}),
    "DSPARK_WINDOW_INDEX": frozenset({"causal_window_then_current_draft"}),
}


def check_operand_slots(
    kind: str, inputs: Sequence[str], attributes: Mapping[str, object]
) -> list[str]:
    """Check a kernel's ``absent_operands`` against the frozen operand row."""
    declared = attributes.get(ABSENT_OPERANDS)
    if declared is None:
        return []
    if not isinstance(declared, (list, tuple)) or not all(
        isinstance(slot, int) and not isinstance(slot, bool) for slot in declared
    ):
        return [f"{ABSENT_OPERANDS} must be a list of ABI input slot numbers"]
    slots = tuple(int(slot) for slot in declared)
    errors: list[str] = []
    if len(set(slots)) != len(slots):
        errors.append(f"{ABSENT_OPERANDS} names a slot twice: {list(slots)}")
    optional = OPTIONAL_INPUT_SLOTS.get(kind, frozenset())
    unstated = sorted(set(slots) - optional)
    if unstated:
        errors.append(
            f"{ABSENT_OPERANDS} leaves input slot(s) {unstated} of {kind} empty, "
            "and the frozen operand row does not make them optional; the slots "
            f"that may be absent are {sorted(optional) or 'none'}"
        )
    engine = KERNEL_TO_ENGINE.get(kind)
    if engine is not None and len(inputs) + len(slots) > engine.inputs:
        errors.append(
            f"{kind} takes {engine.inputs} input slots and this kernel accounts "
            f"for {len(inputs) + len(slots)}: {len(inputs)} operand(s) and "
            f"{len(slots)} declared absent"
        )
    return errors


def check_phase_inputs(
    kind: str,
    inputs: Sequence[str],
    phases: Sequence[str],
    attributes: Mapping[str, object],
) -> list[str]:
    """Validate a phase-dependent ordered input subset.

    This contract currently exists for axis-zero ``CONCAT``.  It is the exact
    distinction DeepSeek's sparse KV view needs: prefill joins current rows and
    an optional compressed prefix, while decode joins the fixed circular-window
    rows and that prefix.  Treating the attribute as a backend comment would
    recreate the original defect, so neutral admission checks it once for both
    lanes.
    """

    declared = attributes.get(PHASE_INPUTS)
    if declared is None:
        return []
    if kind != "CONCAT":
        return [f"{PHASE_INPUTS} is defined only for CONCAT, not {kind}"]
    axis = attributes.get("axis", 0)
    if type(axis) is not int:
        return [f"{PHASE_INPUTS} CONCAT axis must be a non-boolean integer"]
    if axis != 0:
        return [f"{PHASE_INPUTS} requires an axis-0 CONCAT"]
    if not isinstance(declared, Mapping):
        return [f"{PHASE_INPUTS} must map each kernel phase to IR input indices"]
    expected = {str(phase) for phase in phases}
    observed = {str(phase) for phase in declared}
    errors: list[str] = []
    if observed != expected:
        errors.append(
            f"{PHASE_INPUTS} covers phases {sorted(observed)}, expected "
            f"{sorted(expected)}"
        )
    used: set[int] = set()
    for phase, raw in declared.items():
        if not isinstance(raw, (list, tuple)) or not raw:
            errors.append(
                f"{PHASE_INPUTS}[{str(phase)!r}] must be a non-empty list of "
                "IR input indices"
            )
            continue
        if not all(isinstance(index, int) and not isinstance(index, bool) for index in raw):
            errors.append(
                f"{PHASE_INPUTS}[{str(phase)!r}] must contain only IR input indices"
            )
            continue
        row = [int(index) for index in raw]
        if len(set(row)) != len(row):
            errors.append(
                f"{PHASE_INPUTS}[{str(phase)!r}] names an input twice: {row}"
            )
        outside = sorted(index for index in set(row) if not 0 <= index < len(inputs))
        if outside:
            errors.append(
                f"{PHASE_INPUTS}[{str(phase)!r}] names input indices {outside} "
                f"outside the {len(inputs)} CONCAT inputs"
            )
        used.update(index for index in row if 0 <= index < len(inputs))
    unused = sorted(set(range(len(inputs))) - used)
    if unused:
        errors.append(
            f"{PHASE_INPUTS} never selects CONCAT input indices {unused}"
        )
    binding = attributes.get("phase_symbol_binding")
    if not isinstance(binding, Mapping) or {str(phase) for phase in binding} != expected:
        errors.append(
            f"{PHASE_INPUTS} requires phase_symbol_binding for exactly "
            f"{sorted(expected)}"
        )
    return errors


def phase_inputs(
    inputs: Sequence[str], attributes: Mapping[str, object]
) -> dict[str, tuple[int, ...]] | None:
    """Return the admitted phase input map in canonical integer form."""

    declared = attributes.get(PHASE_INPUTS)
    if declared is None:
        return None
    # ``check_phase_inputs`` runs during neutral admission.  Backends still use
    # an explicit conversion here so a direct caller that skipped admission
    # fails visibly rather than carrying arbitrary JSON values into lowering.
    if not isinstance(declared, Mapping):
        raise ValueError(f"{PHASE_INPUTS} is not a phase mapping")
    result: dict[str, tuple[int, ...]] = {}
    for phase, raw in declared.items():
        if not isinstance(raw, (list, tuple)):
            raise ValueError(f"{PHASE_INPUTS}[{str(phase)!r}] is not a list")
        result[str(phase)] = tuple(int(index) for index in raw)
    return result


def abi_input_slots(
    kind: str, inputs: Sequence[str], attributes: Mapping[str, object]
) -> list[str | None]:
    """The IR input each ABI input slot carries; ``None`` for a declared hole.

    One function so that a hole is placed identically on both lanes.  A slot a
    kernel declares absent is not a missing operand, it is a stated one, and the
    remaining operands go *either side* of it: the compressed-dense index leaves
    ``ROUTE.INDEX_TOPK``'s ``in0`` empty and keeps the window block in ``in1``
    and the compression ratio in ``in2``.  A backend that packed them down would
    hand the engine a window block where the scores belong -- which is exactly
    what the engine then says:

        ROUTE.INDEX_TOPK window view 2084 covers 1 query rows, expected 104

    ``check_operand_slots`` has already refused a declaration the frozen row
    does not allow, so this only has to place what it is given.
    """
    declared = attributes.get(ABSENT_OPERANDS) or ()
    holes = {int(slot) for slot in declared}  # type: ignore[union-attr]
    if not holes:
        return list(inputs)
    slots: list[str | None] = []
    remaining = list(inputs)
    position = 0
    while remaining or position in holes:
        if position in holes:
            slots.append(None)
            holes.discard(position)
        else:
            slots.append(remaining.pop(0))
        position += 1
    return slots


def check_index_family(kind: str, attributes: Mapping[str, object]) -> list[str]:
    """Refuse an ``index_family`` the frozen operator does not produce."""
    family = attributes.get("index_family")
    if family is None:
        return []
    implemented = INDEX_FAMILIES.get(kind)
    if implemented is None:
        return [
            f"{kind} declares index_family {family!r}, and no index family is "
            "frozen for this kind; the attribute names what an operator "
            "produces and only an operator that produces index families may "
            "carry it"
        ]
    if family not in implemented:
        return [
            f"index_family {str(family)!r} is not one this ABI implements for "
            f"{kind}. No engine, verifier or backend can read the difference "
            "back out of a lowered operator -- every index a substitution "
            "names is a legal KV row -- so the graph is refused here rather "
            "than executed as something it does not say. The frozen families "
            f"are {', '.join(sorted(implemented))}"
        ]
    return []


def engine_for(kind: str) -> EngineOp:
    """Return the frozen engine operation for ``kind``, or raise."""
    try:
        return KERNEL_TO_ENGINE[kind]
    except KeyError:
        raise KeyError(
            f"neutral kernel kind {kind!r} has no ABI 3.0 lowering; add it to the "
            "shared table through a versioned contract change, never privately"
        ) from None


def check_table_complete() -> list[str]:
    """Every registered neutral kind must have a lowering."""
    from compiler.ir.v3.kernel_ir import OPERATION_KINDS

    return sorted(OPERATION_KINDS - set(KERNEL_TO_ENGINE))
