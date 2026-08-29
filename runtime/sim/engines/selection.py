"""SELECTION engine family: ``ARGMAX`` and ``TOKEN_APPEND``.

ADR-003 section 8.7 makes token selection a *device* operation: the host may
read a token ID back, it may not compute one.  These two engines are therefore
the only place a token comes into existence, and both do real work on real
device memory rather than reporting a decision taken elsewhere.

``SELECTION.ARGMAX``
    ``input_view_0`` is the logits vector, BF16 architectural bit patterns (or
    binary32 when a vocabulary partition already produced binary32).  Widened
    to binary32, the frozen ``greedy_lowest_token_id_argmax`` rule selects the
    lowest token ID among the maxima.  ``output_view_0`` is a single U32
    element receiving the selected ID.  A non-finite logit is a numeric fault,
    not a value to be ignored.

``SELECTION.TOKEN_APPEND``
    ``input_view_0`` is the single U32 token ID produced by a preceding
    selection, read back out of device memory.  It is validated against the
    bound GENERATION_POLICY descriptor, appended to the transaction's produced
    token list, and tested against the policy's EOS set; membership sets
    ``EosReason.OFFICIAL_EOS``, which stops the session.  ``output_view_0`` is
    optional: when present it is a single U32 element, normally a token-ring
    view whose dynamic term is bound to ``GENERATION_INDEX``.

``SELECTION.SAMPLE`` is deliberately absent.  It is a frozen subopcode with no
governed sampling contract yet, and :func:`runtime.sim.engine.dispatch` already
fails closed on an unimplemented operation.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import DType, Major, NO_ID, Selection
from runtime.abi3.descriptors import (
    Descriptor,
    ExtendedDescriptorType,
    MAX_EOS_TOKENS,
    SelectionMode,
)
from runtime.abi3.records import EosReason
from runtime.sim import formats
from runtime.sim.engine import EngineContext, EngineError, register
from runtime.sim.memory import ResolvedView


def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _check_operator(descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.SELECTION)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"SELECTION.{Selection(sub).name}",
    )


def _widen(ctx: EngineContext, view: ResolvedView) -> np.ndarray:
    """Read a logits view as binary32, failing closed on an exceptional value."""
    codes = ctx.read(view)
    if view.dtype not in (int(DType.BF16), int(DType.FP32)):
        raise EngineError(
            f"selection logits view {view.descriptor_id} is dtype "
            f"{view.dtype:#04x}; on-device selection reads BF16 or binary32",
            trap_class=3,
        )
    values = formats.widen(view.dtype, codes).reshape(-1)
    if not bool(np.all(np.isfinite(values))):
        raise EngineError(
            f"selection logits view {view.descriptor_id} contains a NaN or "
            "infinite value; a token may not be selected from it",
            trap_class=6,
        )
    return values


def _single_u32(view: ResolvedView, label: str) -> None:
    _require(
        view.dtype == int(DType.U32),
        f"selection {label} view {view.descriptor_id} is dtype "
        f"{view.dtype:#04x}, expected U32",
    )
    _require(
        view.element_count == 1,
        f"selection {label} view {view.descriptor_id} holds "
        f"{view.element_count} elements; a token ID is exactly one element",
    )


@register(Major.SELECTION, Selection.ARGMAX)
def argmax(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Greedy on-device selection: lowest token ID among the maxima."""
    _check_operator(descriptor, int(Selection.ARGMAX))
    logits_view = ctx.input_view(descriptor, 0)
    out_view = ctx.output_view(descriptor, 0)
    _single_u32(out_view, "token")

    values = _widen(ctx, logits_view)
    vocabulary = int(values.size)
    _require(
        vocabulary > 0,
        f"selection logits view {logits_view.descriptor_id} is empty",
    )
    maximum = np.max(values)
    ties = int(np.count_nonzero(values == maximum))
    token = int(np.argmax(values))  # first occurrence: the lowest tied token ID

    ctx.write(out_view, np.array([token], dtype=np.uint32).reshape(out_view.dims))
    ctx.counters.add("selection.vocabulary_elements", vocabulary)
    ctx.counters.add("selection.tie_multiplicity", ties)
    ctx.counters.add("selection.tokens_selected")
    selection = ctx.notes.setdefault("selection", {})
    selection["token"] = token
    selection["tie_multiplicity"] = ties


@register(Major.SELECTION, Selection.TOKEN_APPEND)
def token_append(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Validate the selected ID against the policy and append it."""
    _check_operator(descriptor, int(Selection.TOKEN_APPEND))
    policy_id = int(ctx.notes.get("generation_policy_id", NO_ID))
    _require(
        policy_id != NO_ID,
        "SELECTION.TOKEN_APPEND without a bound generation policy; the "
        "entrypoint or submission must name one",
    )
    policy = ctx.table.get(policy_id, ExtendedDescriptorType.GENERATION_POLICY)
    payload = policy.payload
    _require(
        int(payload["selection_mode"]) == int(SelectionMode.GREEDY_ARGMAX_LOWEST_ID),
        f"generation policy {policy_id} declares selection mode "
        f"{payload['selection_mode']}, which this device does not implement",
        trap_class=4,
    )

    token_view = ctx.input_view(descriptor, 0)
    _single_u32(token_view, "token")
    token = int(np.asarray(ctx.read(token_view)).reshape(-1)[0])

    vocabulary = int(payload["vocabulary_size"])
    if not 0 <= token < vocabulary:
        ctx.counters.add("selection.invalid_tokens")
        raise EngineError(
            f"SELECTION.TOKEN_APPEND: token {token} is outside the "
            f"{vocabulary}-entry vocabulary of generation policy {policy_id}",
            trap_class=6,
        )

    produced = ctx.notes.setdefault("produced_tokens", [])
    produced.append(token)
    ctx.counters.add("selection.tokens_appended")

    ring_view_id = descriptor.payload["output_view_0"]
    if ring_view_id != NO_ID:
        ring = ctx.view(ring_view_id)
        _single_u32(ring, "token ring")
        ctx.write(ring, np.array([token], dtype=np.uint32).reshape(ring.dims))

    selection = ctx.notes.setdefault("selection", {})
    selection["token"] = token

    eos_count = int(payload["eos_count"])
    _require(
        0 <= eos_count <= MAX_EOS_TOKENS,
        f"generation policy {policy_id} declares {eos_count} EOS tokens",
    )
    eos_tokens = [int(payload[f"eos_token_{slot}"]) for slot in range(eos_count)]
    if token in eos_tokens:
        selection["eos_reason"] = int(EosReason.OFFICIAL_EOS)
        return

    limit = int(payload["max_new_tokens"])
    if limit:
        already = len(getattr(ctx.session, "generated", ()) or ())
        if already + len(produced) >= limit:
            ctx.counters.add("selection.length_stops")
            selection.setdefault("eos_reason", int(EosReason.MAX_NEW_TOKENS))


__all__ = ["argmax", "token_append"]
