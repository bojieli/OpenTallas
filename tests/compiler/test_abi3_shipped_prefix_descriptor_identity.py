"""The shipped-prefix builder must resolve descriptors by identity, not number.

A descriptor ID is a table index, so it moves whenever the lowering changes
without anything about the operation changing.  It has moved three times in
this repository, and the hand-written tables this builder used to carry were
left behind by every move -- silently, because a stale number is a valid
number.  These checks hold the replacement to a harder standard than "it
builds today":

* the derivation must reproduce, for each PRESERVED bundle, exactly the IDs
  that bundle itself assigned.  That is what distinguishes a derivation from a
  table: a table can only be right about the lowering it was typed against.
* it must refuse when its identity selects no descriptor, and refuse when it
  selects more than one.  Both refusals are the feature.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from runtime.abi3.deployment import Deployment
from tools import build_abi3_shipped_prefix_vectors as generator


ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "build/abi3"
VECTOR_JSON = (
    ROOT / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"
)

# Each preserved bundle, the shipped target whose certified Kernel IR it was
# lowered from, its own deployment digest (so a re-lowered archive cannot pass
# these checks by accident), and the governed descriptor IDs THAT BUNDLE
# assigns.  The IDs are written down here on purpose: in a test they are the
# falsifier.  In the builder they were the defect.
PRESERVED_LOWERINGS = (
    (
        "qwen3-8b-rom-pre-am-e9",
        "qwen3-8b-rom-single-chip",
        "d8a6f8edaaac8617",
        {
            "embed": 41,
            "rms": 50,
            "matmul.0": 59,
            "matmul.1": 67,
            "matmul.2": 74,
            "head_rms.0": 81,
            "head_rms.1": 89,
            "rope.0": 98,
            "rope.1": 106,
        },
    ),
    (
        "qwen3-8b-hbm-tokens-pre-am-e9",
        "qwen3-8b-hbm-single-chip",
        "0d7897457e14666f",
        {
            "embed": 54,
            "rms": 64,
            "matmul.0": 72,
            "matmul.1": 78,
            "matmul.2": 83,
            "head_rms.0": 88,
            "head_rms.1": 94,
            "rope.0": 101,
            "rope.1": 107,
        },
    ),
    (
        # The third lowering.  The ROM column of every table this builder used
        # to carry was bound to THIS bundle's numbering, not to the pre-AM-E9
        # pair beside it -- which is why the tables matched neither the
        # promoted pair nor the bundle they were supposed to describe.
        "qwen3-8b-rom-rowfold-v1",
        "qwen3-8b-rom-single-chip",
        "5940e5b6b5c50749",
        {
            "embed": 41,
            "rms": 50,
            "matmul.0": 59,
            "matmul.1": 67,
            "matmul.2": 74,
            "head_rms.0": 80,
            "head_rms.1": 88,
            "rope.0": 96,
            "rope.1": 103,
        },
    ),
    (
        "deepseek-v4-flash-rom-pre-am-e9",
        "deepseek-v4-flash-rom-wafer",
        None,
        {"embed": 356, "transfer": 363},
    ),
    (
        "deepseek-v4-flash-hbm-tokens-pre-am-e9",
        "deepseek-v4-flash-hbm-cluster",
        None,
        {"embed": 526, "transfer": 531},
    ),
)


def _resolve(bundle: str, target_key: str) -> dict[str, generator.Resolution]:
    index, target = next(
        (index, target)
        for index, target in enumerate(generator.TARGETS)
        if target.key == target_key
    )
    identity = generator.certified_deployment_identity(target)
    deployment = Deployment.read(BUNDLES / bundle)
    kernel_ir = generator._kernel_ir_index(target, identity)
    return deployment, generator.resolve_governed_descriptors(
        deployment,
        kernel_ir,
        target_key=f"{target_key}@{bundle}",
        target_index=index,
    )


@pytest.mark.parametrize(
    ("bundle", "target_key", "deployment_prefix", "expected"),
    PRESERVED_LOWERINGS,
    ids=[entry[0] for entry in PRESERVED_LOWERINGS],
)
def test_derivation_reproduces_each_preserved_lowerings_own_numbering(
    bundle: str, target_key: str, deployment_prefix: str | None, expected: dict
) -> None:
    deployment, derived = _resolve(bundle, target_key)
    if deployment_prefix is not None:
        assert deployment.deployment_digest.hex().startswith(deployment_prefix)
    assert {slot: item.descriptor_id for slot, item in derived.items()} == expected
    assert all(item.resolution == "unique" for item in derived.values())


def test_derivation_matches_the_shipped_vector_sets_own_record() -> None:
    vectors = json.loads(VECTOR_JSON.read_text(encoding="utf-8"))
    for case in vectors["cases"]:
        recorded = {
            entry["slot"]: entry["derived_descriptor_id"]
            for entry in case["descriptor_derivation"]["operations"]
            if entry["slot"] != "boundary"
        }
        _, derived = _resolve(
            Path(
                next(
                    target.deployment
                    for target in generator.TARGETS
                    if target.key == case["deployment"]
                )
            ).name,
            case["deployment"],
        )
        assert {slot: item.descriptor_id for slot, item in derived.items()} == recorded


def test_the_two_qwen_lowerings_are_not_interchangeable() -> None:
    _, rom = _resolve("qwen3-8b-rom", "qwen3-8b-rom-single-chip")
    _, hbm = _resolve("qwen3-8b-hbm-tokens", "qwen3-8b-hbm-single-chip")
    assert set(rom) == set(hbm)
    # Not one governed operation shares a descriptor ID across the two
    # lowerings.  A builder bound to one of them has no evidence about the
    # other, which is why the vector set is built per lowering.
    assert all(rom[slot].descriptor_id != hbm[slot].descriptor_id for slot in rom)


def test_an_identity_that_selects_nothing_is_refused() -> None:
    index, target = next(
        (index, target)
        for index, target in enumerate(generator.TARGETS)
        if target.key == "qwen3-8b-rom-single-chip"
    )
    identity = generator.certified_deployment_identity(target)
    kernel_ir = generator._kernel_ir_index(target, identity)
    # A Qwen identity against a bundle that holds no Qwen kernel.
    deployment = Deployment.read(BUNDLES / "deepseek-v4-flash-rom")
    with pytest.raises(SystemExit) as excinfo:
        generator.resolve_operator(
            deployment,
            kernel_ir,
            generator.MATMUL_IDENTITIES[0],
            target_key="absent",
        )
    message = str(excinfo.value)
    assert "selects 0 of" in message
    assert "absence of a derivation is a refusal, not a pass" in message
    assert "layer.0.attention.query_projection" in message


def test_an_identity_that_selects_two_descriptors_is_refused() -> None:
    deployment, derived = _resolve("qwen3-8b-rom", "qwen3-8b-rom-single-chip")
    index, target = next(
        (index, target)
        for index, target in enumerate(generator.TARGETS)
        if target.key == "qwen3-8b-rom-single-chip"
    )
    identity = generator.certified_deployment_identity(target)
    kernel_ir = generator._kernel_ir_index(target, identity)
    original = derived["matmul.0"].descriptor_id
    # A second descriptor that IS the same operation under every field the
    # identity can read.  The derivation must refuse rather than pick one.
    duplicate = deployment.table.add(copy.deepcopy(deployment.table[original]))
    with pytest.raises(SystemExit) as excinfo:
        generator.resolve_operator(
            deployment,
            kernel_ir,
            generator.MATMUL_IDENTITIES[0],
            target_key="ambiguous",
        )
    message = str(excinfo.value)
    assert "selects 2 of" in message
    assert str(original) in message and str(duplicate) in message
    assert "not evidence about either" in message


def test_the_builder_writes_no_descriptor_id_of_its_own() -> None:
    """No integer in the identity tables may be a descriptor ID.

    The identities name kernels by string, opcodes and dtypes by enum, and
    head counts by the model's own geometry.  If a descriptor number reappears
    here, this file has grown a seventh table.
    """
    identities = (
        *generator.EMBED_IDENTITIES,
        generator.RMS_IDENTITY,
        generator.TRANSFER_IDENTITY,
        *generator.MATMUL_IDENTITIES,
        *generator.HEAD_RMS_IDENTITIES,
        *generator.ROPE_IDENTITIES,
    )
    for identity in identities:
        assert isinstance(identity.kernel, str) and identity.kernel
        assert identity.aux_0 in (None, generator.Q_HEADS, generator.KV_HEADS)
    for boundary in generator.BOUNDARY_IDENTITIES:
        assert boundary.kernel is None or isinstance(boundary.kernel, str)
        assert isinstance(boundary.pc, int)
