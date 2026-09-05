"""Rung G1a: what the integrated vehicle is allowed to cover, and what it is not.

The integrated shipped-prefix campaign runs the real compiled program of four
deployments in ONE pass, so it cannot be described by a single ``target``.
``tools/build_abi3_g1a_operator_equivalence.py`` therefore derives what it drove
from the vector set the campaign binds by digest, and cross-checks that
derivation against the per-operation records the campaign emitted for itself.

These tests exercise the refusals rather than asserting them: a campaign whose
own record disagrees with the vector set it binds must cover NOTHING, and
coverage measured on one lowering must never be filed against the other.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"
DEPLOYMENT_DIR = ROOT / "testdata/compiler/abi3_deployment"


def _tool():
    spec = importlib.util.spec_from_file_location(
        "_g1a_tool", ROOT / "tools/build_abi3_g1a_operator_equivalence.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def tool():
    return _tool()


@pytest.fixture(scope="module")
def deployment(tool):
    manifest = json.loads(
        (DEPLOYMENT_DIR / "abi3_deployment_rtl_vectors.json").read_text()
    )
    images = {
        "descriptor": tool.read_hex(DEPLOYMENT_DIR / "a3_descriptor.hex"),
        "program": tool.read_hex(DEPLOYMENT_DIR / "a3_program.hex"),
        "issue": tool.read_hex(DEPLOYMENT_DIR / "a3_deployment_issue.hex"),
        "view": tool.read_hex(DEPLOYMENT_DIR / "a3_deployment_view.hex"),
    }
    return manifest, images


@pytest.fixture(scope="module")
def campaign_body():
    if not CAMPAIGN.is_file():
        pytest.skip("no integrated shipped-prefix campaign is retained")
    return json.loads(CAMPAIGN.read_text())


def test_a_campaign_with_no_vector_set_covers_nothing(tool, deployment):
    manifest, images = deployment
    result = tool.integrated_coverage({}, manifest, images)
    assert result["coverage_by_deployment"] == {}
    assert result["integrated_coverage_problems"]
    assert "vector set" in result["integrated_coverage_problems"][0]


def test_a_campaign_whose_own_record_disagrees_covers_nothing(
    tool, deployment, campaign_body
):
    """One wrong descriptor id in one section, and the whole campaign is refused.

    This is the failure the retained artifact actually had: it recorded the
    superseded lowering's descriptors while binding the promoted vector set.
    """

    manifest, images = deployment
    honest = tool.integrated_coverage(campaign_body, manifest, images)
    if not honest["coverage_by_deployment"]:
        pytest.skip("the retained campaign does not currently cover anything")

    for section in tool.INTEGRATED_OPERATION_SECTIONS:
        if campaign_body.get(section):
            break
    else:  # pragma: no cover - a campaign with no operation records
        pytest.skip("the retained campaign names no executed operation")

    tampered = copy.deepcopy(campaign_body)
    entry = tampered[section][0]
    entry["operator_descriptor_id"] = int(entry["operator_descriptor_id"]) + 1
    result = tool.integrated_coverage(tampered, manifest, images)
    assert result["coverage_by_deployment"] == {}
    assert any(
        "the campaign recorded operator descriptor" in problem
        for problem in result["integrated_coverage_problems"]
    )


def test_a_replay_that_did_not_pass_covers_nothing(tool, deployment, campaign_body):
    manifest, images = deployment
    tampered = copy.deepcopy(campaign_body)
    tampered["integrated_replay_passed"] = False
    result = tool.integrated_coverage(tampered, manifest, images)
    assert result["coverage_by_deployment"] == {}
    assert any(
        "integrated_replay_passed" in problem
        for problem in result["integrated_coverage_problems"]
    )


def test_each_lowering_is_filed_under_its_own_deployment_digest(
    tool, deployment, campaign_body
):
    manifest, images = deployment
    result = tool.integrated_coverage(campaign_body, manifest, images)
    coverage = result["coverage_by_deployment"]
    if not coverage:
        pytest.skip("the retained campaign does not currently cover anything")

    digests = {
        entry["key"]: entry["deployment_sha256"]
        for entry in manifest["deployments"]
    }
    rom = digests["qwen3-8b-rom-single-chip"]
    hbm = digests["qwen3-8b-hbm-single-chip"]
    if rom not in coverage or hbm not in coverage:
        pytest.skip("the retained campaign does not cover both Qwen lowerings")

    rom_ids = set(coverage[rom]["positive_operator_descriptor_ids"])
    hbm_ids = set(coverage[hbm]["positive_operator_descriptor_ids"])
    assert rom_ids and hbm_ids
    assert coverage[rom]["case"] != coverage[hbm]["case"]
    assert coverage[rom]["deployment"] != coverage[hbm]["deployment"]

    # A descriptor id means nothing outside its own deployment, and these two
    # prove it by colliding: the SAME number names different operations on the
    # two lowerings, and the two lowerings never agree on the number for the
    # same program counter.  That is why coverage is filed under a deployment
    # digest and never transferred.
    def by_pc(entry):
        return {
            op["program_counter"]: op["operator_descriptor_id"]
            for op in entry["operations"]
        }

    rom_by_pc, hbm_by_pc = by_pc(coverage[rom]), by_pc(coverage[hbm])
    shared_pcs = set(rom_by_pc) & set(hbm_by_pc)
    assert shared_pcs
    assert all(rom_by_pc[pc] != hbm_by_pc[pc] for pc in shared_pcs)

    collisions = {
        descriptor_id
        for descriptor_id in rom_ids & hbm_ids
        if [pc for pc, d in rom_by_pc.items() if d == descriptor_id]
        != [pc for pc, d in hbm_by_pc.items() if d == descriptor_id]
    }
    assert collisions, (
        "no descriptor id collides across the two lowerings in this prefix; "
        "the test's premise, that a bare id is meaningless, needs rechecking"
    )


def test_the_two_admission_vector_sets_describe_different_lowerings():
    """The operator-admission vehicle is built per lowering, not once.

    Bank and expected images are byte-identical -- same operands, same golden
    results -- while the descriptor records the bridge is driven with are not.
    """

    rom = ROOT / "testdata/rtl/a3_operator_admission"
    hbm = ROOT / "testdata/rtl/a3_operator_admission_hbm"
    if not hbm.is_dir():
        pytest.skip("the HBM admission vector set is not built")

    rom_index = json.loads((rom / "index.json").read_text())
    hbm_index = json.loads((hbm / "index.json").read_text())
    assert rom_index["target"] == "qwen3-8b-rom-single-chip"
    assert hbm_index["target"] == "qwen3-8b-hbm-single-chip"
    assert rom_index["deployment_sha256"] != hbm_index["deployment_sha256"]

    def positive_ids(index):
        return {
            int(case["operator_descriptor_id"])
            for case in index["cases"]
            if not case["expected"]["fault"]
            and case.get("operator_descriptor_id") is not None
        }

    assert not positive_ids(rom_index) & positive_ids(hbm_index)
    assert rom_index["governed_program_counters"] == (
        hbm_index["governed_program_counters"]
    )
    # Same operands and the same golden results; different records to drive
    # the bridge with.  The banks differ only because the HBM lowering's PC-72
    # output view resolves at the generated position, so its token ring needs
    # 17 more words than the ROM lowering's.
    assert (rom / "expected.hex").read_bytes() == (hbm / "expected.hex").read_bytes()
    for name in ("cases.hex", "views.hex", "descriptors.hex", "bank.hex"):
        assert (rom / name).read_bytes() != (hbm / name).read_bytes()
    rom_bank = rom_index["geometry"]["bank_words"]
    hbm_bank = hbm_index["geometry"]["bank_words"]
    assert hbm_bank > rom_bank
    assert (
        len((hbm / "bank.hex").read_text().split())
        - len((rom / "bank.hex").read_text().split())
        == hbm_bank - rom_bank
    )
