"""The DSpark draft stack separates from a speculative graph, or it does not.

``tools/build_dspark_draft_graph.py`` exists so that ``T_draft`` in DFlash's
cost model can be *measured* rather than estimated from a byte count.  The whole
speculative graph cannot be lowered -- the ROM loop compressor admits one
layered span and that graph has two, the target's and the draft's -- but the
draft stack alone is one contiguous span and compresses under the rule that
already exists.

What the slice must never do is quietly become a different model.  It reads
five values the target produces, and exactly those may be promoted to inputs;
anything else crossing the boundary is a refusal, because a slice that invents
an input is no longer the draft the released implementation runs.  These tests
pin the boundary, not the arithmetic.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from compiler.ir.v3.kernel_ir import KernelGraph, check_neutral
from tools.build_dspark_draft_graph import (
    DERIVED_MAXIMA,
    DraftSliceError,
    slice_draft,
)

ROOT = Path(__file__).resolve().parents[2]
SPECULATIVE = (
    ROOT / "build" / "ir-v3" / "deepseek-v4-flash-0731-speculative" / "kernel_ir.v3.json"
)

#: The conditioning DSpark reads from the target, and nothing else.  Three
#: hidden states named by ``dspark_target_layer_ids``, the anchor token the
#: block is built around, and a rope table that is a generated constant either
#: way.
EXPECTED_PROMOTIONS = {
    "main.layer40.target_hidden.output",
    "main.layer41.target_hidden.output",
    "main.layer42.target_hidden.output",
    "main.sample.tokens",
    "rope.coefficient_rows.base",
}


@pytest.fixture(scope="module")
def speculative() -> KernelGraph:
    if not SPECULATIVE.exists():
        pytest.skip(
            f"{SPECULATIVE} is not built "
            "(tools/build_deepseek_v4_kernel_ir_v3.py --include-speculative)"
        )
    return KernelGraph.read(SPECULATIVE)


def test_the_slice_promotes_exactly_the_target_conditioning(speculative) -> None:
    draft = slice_draft(speculative, model_id="draft-under-test")
    promoted = set(draft.source["derived_from"]["promoted_to_input"])
    assert promoted == EXPECTED_PROMOTIONS, promoted
    # Every promoted tensor really is an input now, and nothing else changed role.
    by_id = {t.tensor_id: t for t in draft.tensors}
    for name in EXPECTED_PROMOTIONS:
        if name in by_id:
            assert by_id[name].role in {"input", "activation"}, name


def test_the_slice_is_neutral_and_self_contained(speculative) -> None:
    """No kernel may read a tensor the slice does not declare."""
    draft = slice_draft(speculative, model_id="draft-under-test")
    assert check_neutral(draft) == []
    declared = {t.tensor_id for t in draft.tensors}
    for kernel in draft.kernels:
        for name in kernel.inputs:
            assert name in declared, f"{kernel.kernel_id} reads undeclared {name}"


def test_the_draft_is_one_contiguous_layered_span(speculative) -> None:
    """This is the property that makes the slice lowerable at all."""
    draft = slice_draft(speculative, model_id="draft-under-test")
    layers = sorted({k.layer for k in draft.kernels if k.layer is not None})
    assert layers == list(range(len(layers)))
    assert len(layers) == 3, layers
    indices = [i for i, k in enumerate(draft.kernels) if k.layer is not None]
    assert indices == list(range(indices[0], indices[-1] + 1))


def test_the_derived_graph_carries_its_own_identity(speculative) -> None:
    """A derived artifact must never be mistaken for a released model."""
    draft = slice_draft(speculative, model_id="draft-under-test")
    assert draft.model_id == "draft-under-test"
    assert draft.graph_id != speculative.graph_id
    derived = draft.source["derived_from"]
    assert derived["graph_id"] == speculative.graph_id
    assert derived["model_id"] == speculative.model_id


def test_two_slices_of_one_graph_agree(speculative) -> None:
    first = slice_draft(speculative, model_id="draft-under-test")
    second = slice_draft(speculative, model_id="draft-under-test")
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(
        second.to_dict(), sort_keys=True
    )


def test_a_declared_horizon_rescales_every_derived_symbol(speculative) -> None:
    """The draft reads one target position; it need not carry the target's horizon."""
    draft = slice_draft(speculative, model_id="draft-under-test", horizon=512)
    maxima = {s.name: s.maximum for s in draft.symbols}
    for name, rule in DERIVED_MAXIMA.items():
        if name in maxima:
            assert maxima[name] == rule(512), name
    assert draft.source["deployment_context_tokens"] == 512
    assert draft.source["derived_from"]["request_horizon_tokens"] == 512


def test_a_graph_with_no_draft_stack_is_refused(speculative) -> None:
    ordinary = dataclasses.replace(
        speculative,
        kernels=tuple(
            k for k in speculative.kernels if not k.kernel_id.startswith("dspark.")
        ),
    )
    with pytest.raises(DraftSliceError, match="no dspark"):
        slice_draft(ordinary, model_id="draft-under-test")


def test_a_draft_reading_an_undeclared_tensor_is_refused(speculative) -> None:
    """A slice that invents an input is no longer the released draft."""
    kernels = []
    for kernel in speculative.kernels:
        if kernel.kernel_id.startswith("dspark.") and kernel.inputs:
            kernel = dataclasses.replace(
                kernel, inputs=(*kernel.inputs, "main.not.a.real.tensor")
            )
        kernels.append(kernel)
    broken = dataclasses.replace(speculative, kernels=tuple(kernels))
    with pytest.raises(DraftSliceError, match="does not declare"):
        slice_draft(broken, model_id="draft-under-test")
