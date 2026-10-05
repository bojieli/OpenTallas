"""The HBM/SRAM backend's state resources: how many, of what class, and why.

Three properties, each of which was false and silent until the DeepSeek HBM
lane was asked to produce a token:

1. **The whole deployment's state-descriptor count is bounded, not the band's.**
   Amendment A22's ``max_state_resources`` counts ``STATE`` descriptors across
   the deployment because the sequencer holds a slot per declared resource for
   the life of a transaction.  The planner merged a band's resources and stopped
   there, so shape-identical resources in different bands stayed separate
   descriptors: DeepSeek-V4-Flash declared nineteen against a sixteen-slot file
   and was refused at admission, while the ROM backend -- which groups by shape
   over the whole graph -- declared ten from the same graph.

2. **A resource's initial value is part of its identity.**  DeepSeek's
   compressor keeps its pooled keys at zero and its pooled scores at negative
   infinity.  Pooling on shape alone would put both in one descriptor.

3. **An unknown state class is refused, not silently called SCRATCH.**  The
   lookup defaulted, so ``kv_window`` and ``compressor_window`` -- fifteen of
   DeepSeek's nineteen HBM resources -- were declared ``SCRATCH`` on the HBM
   side of a comparison whose ROM side declared them ``KV_CACHE`` and
   ``COMPRESSED_KV``.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from compiler.backends.hbm_sram.capability import single_chip_capability
from compiler.backends.hbm_sram.lower import (
    _STATE_CLASS,
    _STATE_CLASS_ALIASES,
    LoweringError,
    lower_to_abi3,
)
from compiler.backends.hbm_sram.plan import StatePlacement, _pool_states
from compiler.backends.rom.common.program import (
    STATE_CLASS_ALIASES,
    STATE_CLASS_BY_NAME,
)
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.descriptors import ExtendedDescriptorType

from test_hbm_sram_backend import dense_graph

#: The published DeepSeek graph, when `make abi3-ir` has been run.  It is the
#: only graph in this repository that reaches the bound at all, so the check
#: that it is admitted has to read it rather than a synthetic stand-in.
REAL_DEEPSEEK_IR = Path("build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json")
DEEPSEEK_CAPABILITY = Path(
    "configs/hardware/abi3_capability/hbm_sram_cluster_32.json"
)


def _placement(physical_id: str, band: int | None, **kw) -> StatePlacement:
    body = {
        "state_class": "kv_window",
        "members": (physical_id + ".m0",),
        "row_elements": 512,
        "row_bytes": 1024,
        "capacity_rows": 128,
        "dtype": "bf16",
        "initialization": "zero",
    }
    body.update(kw)
    return StatePlacement(physical_id=physical_id, band_id=band, **body)


def test_shape_identical_resources_in_different_bands_become_one_descriptor():
    first = _placement("state.b0.r0", 0, members=("a0", "a1"))
    second = _placement("state.b1.r0", 1, members=("b0",))
    mapping = {"a0": ["state.b0.r0", 0], "a1": ["state.b0.r0", 1], "b0": ["state.b1.r0", 0]}
    pooled = _pool_states([first, second], mapping)
    assert len(pooled) == 1
    assert pooled[0].members == ("a0", "a1", "b0")
    # A band's members stay contiguous and in order, because the layer loop
    # walks them by adding one window per iteration to the band's base.
    assert mapping["a0"][1] == 0
    assert mapping["a1"][1] == 1
    assert mapping["b0"][1] == 2
    assert {m[0] for m in mapping.values()} == {pooled[0].physical_id}
    # A pool that spans bands belongs to no single one.
    assert pooled[0].band_id is None


def test_resources_that_differ_only_in_initial_value_are_never_pooled():
    keys = _placement("state.b1.r1", 1, state_class="compressor_window")
    scores = _placement(
        "state.b1.r2",
        1,
        state_class="compressor_window",
        initialization="negative_infinity",
    )
    mapping = {"state.b1.r1.m0": ["state.b1.r1", 0], "state.b1.r2.m0": ["state.b1.r2", 0]}
    pooled = _pool_states([keys, scores], mapping)
    assert len(pooled) == 2
    assert {p.initialization for p in pooled} == {"zero", "negative_infinity"}


def test_pooling_conserves_every_declared_member_exactly_once():
    placements = [
        _placement("state.b0.r0", 0, members=("a0", "a1")),
        _placement("state.b1.r0", 1, members=("b0",)),
        _placement("state.b2.r0", 2, members=("c0", "c1", "c2")),
        _placement("state.b2.r1", 2, capacity_rows=8, members=("d0",)),
    ]
    mapping = {
        member: [p.physical_id, index]
        for p in placements
        for index, member in enumerate(p.members)
    }
    pooled = _pool_states(list(placements), mapping)
    before = [m for p in placements for m in p.members]
    after = [m for p in pooled for m in p.members]
    assert sorted(after) == sorted(before)
    assert len(after) == len(set(after))
    # No member may be lost from the mapping, and every mapping entry must
    # name a member of the resource it points at.
    for member, (physical_id, index) in mapping.items():
        resource = next(p for p in pooled if p.physical_id == physical_id)
        assert resource.members[index] == member


def test_the_two_backends_name_state_classes_identically():
    """One graph, two backends, one answer about what a resource *is*."""
    assert dict(_STATE_CLASS) == dict(STATE_CLASS_BY_NAME)
    assert dict(_STATE_CLASS_ALIASES) == dict(STATE_CLASS_ALIASES)


def test_an_unknown_state_class_is_refused_rather_than_called_scratch():
    graph = dense_graph(layers=2)
    graph = dataclasses.replace(
        graph,
        states=tuple(
            dataclasses.replace(state, state_class="invented_by_a_backend")
            for state in graph.states
        ),
    )
    with pytest.raises(LoweringError, match="frozen ABI 3.0 registry"):
        lower_to_abi3(graph, single_chip_capability())


@pytest.mark.skipif(
    not REAL_DEEPSEEK_IR.exists(), reason="run `make abi3-ir` to build the graph"
)
def test_the_published_deepseek_graph_fits_the_declared_state_slot_file():
    """The check that would have refused the nineteen-descriptor deployment.

    Nothing anywhere lowered the published DeepSeek graph on the HBM capability
    and asserted the result was admitted, so A22's bound -- whose margin was
    chosen from a survey of the ROM lane alone, "the largest real demand is
    DeepSeek's ten" -- was three short for the other lane and nobody knew.
    """
    from runtime.abi3.capability import Capability
    from runtime.abi3.verifier import verify_deployment

    capability = Capability.from_dict(json.loads(DEEPSEEK_CAPABILITY.read_text()))
    graph = KernelGraph.read(REAL_DEEPSEEK_IR)
    deployment = lower_to_abi3(graph, capability)
    states = deployment.table.ids_of_type(int(ExtendedDescriptorType.STATE))
    assert len(states) <= capability.limits["max_state_resources"]
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors


@pytest.mark.skipif(
    not REAL_DEEPSEEK_IR.exists(), reason="run `make abi3-ir` to build the graph"
)
def test_both_backends_declare_the_same_state_resources_for_one_graph():
    """A ROM-versus-HBM comparison starts with the two agreeing what is there."""
    from compiler.backends.rom.deepseek_v4 import lower_to_abi3 as rom_lower
    from runtime.abi3.capability import Capability

    graph = KernelGraph.read(REAL_DEEPSEEK_IR)
    hbm = lower_to_abi3(
        graph, Capability.from_dict(json.loads(DEEPSEEK_CAPABILITY.read_text()))
    )
    rom_capability = Path("configs/hardware/abi3_capability/rom_deepseek_v4.json")
    rom = rom_lower(graph, Capability.from_dict(json.loads(rom_capability.read_text())))

    def kinds(deployment):
        """What resources this deployment says the graph has.

        Not how many descriptors carry them: the two backends pool at different
        granularities (ROM groups by shape over the whole graph, HBM pools a
        band's replicas), and the number of descriptors is a compiler choice.
        What may not differ is the *kind* of each resource -- its frozen state
        class, its A21 commit policy, its element type and its row -- because
        that is a property of the graph, and a resource that is a KV cache on
        one side of a comparison and a scratch buffer on the other makes the
        comparison meaningless.  It was: the HBM lookup defaulted to SCRATCH.
        """
        return {
            (
                payload["state_class"],
                payload["commit_policy"],
                payload["element_dtype"],
                payload["row_bytes"],
            )
            for payload in (
                deployment.table.get(descriptor_id).payload
                for descriptor_id in deployment.table.ids_of_type(
                    int(ExtendedDescriptorType.STATE)
                )
            )
        }

    assert kinds(hbm) == kinds(rom)
    # And no resource may be called SCRATCH by either side: every class this
    # graph declares has an exact frozen class or a documented alias.
    assert 5 not in {kind[0] for kind in kinds(hbm) | kinds(rom)}
