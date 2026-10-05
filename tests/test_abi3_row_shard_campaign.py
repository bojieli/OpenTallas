"""The retained row-shard campaign, checked against its own sources.

A campaign artifact is evidence only while the sources it binds are the
sources on disk, so this refuses a drifted, missing or failing artifact rather
than skipping.  Absence of evidence is a failure here, not "not evaluable".
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results/rtl/abi3_row_shard_campaign.json"


@pytest.fixture(scope="module")
def campaign() -> dict:
    if not ARTIFACT.is_file():
        pytest.fail(f"{ARTIFACT.relative_to(ROOT)} is missing")
    return json.loads(ARTIFACT.read_text())


def test_the_artifact_binds_the_sources_on_disk(campaign: dict) -> None:
    drifted = []
    for name, digest in campaign["bound_sources"].items():
        path = ROOT / name
        if not path.is_file():
            drifted.append(f"{name}: missing")
            continue
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != digest:
            drifted.append(f"{name}: {observed[:12]} against {digest[:12]}")
    assert drifted == []


def test_the_campaign_passed_and_nothing_mismatched(campaign: dict) -> None:
    assert campaign["status"] == "pass", campaign["problems"]
    assert campaign["problems"] == []
    assert campaign["totals"]["mismatched_words"] == 0
    assert campaign["totals"]["compared_words"] > 0
    assert campaign["totals"]["simulated_cycles"] > 0
    assert campaign["git"]["worktree_dirty"] is False


def test_every_composition_is_an_exact_partition(campaign: dict) -> None:
    composed = 0
    for leg in campaign["legs"]:
        composition = leg["composition"]
        if not composition.get("composed"):
            # A leg whose every shard the design refused composes nothing, and
            # that refusal is the measurement.  It must still carry a reason.
            assert composition.get("reason")
            continue
        proof = composition["partition_proof"]
        assert proof["gaps"] == 0
        assert proof["overlaps"] == 0
        assert proof["covers_every_row_exactly_once"] is True
        assert proof["sum_of_shard_extents"] == leg["declared_output_rows"]
        assert proof["first_row_of_first_shard"] == 0
        assert proof["end_row_of_last_shard"] == leg["declared_output_rows"]
        assert composition["equals_whole_operator_golden"] is True
        composed += 1
    assert composed > 0


def test_the_composer_refused_every_falsification(campaign: dict) -> None:
    probes = 0
    for leg in campaign["legs"]:
        for probe in leg.get("composer_falsification", []):
            assert probe["refused"] is True, probe
            assert probe["reason"]
            probes += 1
    assert probes > 0


def test_the_whole_run_and_the_sharded_run_are_byte_identical(
    campaign: dict,
) -> None:
    assert campaign["equivalence"], "no equivalence pair was measured"
    for item in campaign["equivalence"]:
        assert item["byte_identical"] is True, item
        assert item["both_equal_the_golden"] is True, item
        assert item["sharded_run_shard_count"] > 1
        assert item["whole_run_shard_count"] == 1


def test_every_write_lands_in_its_own_shard_exactly_once(campaign: dict) -> None:
    for leg in campaign["legs"]:
        for shard in leg["shards"]:
            stream = shard.get("write_stream")
            if stream is None:
                continue
            assert stream["problems"] == [], (leg["name"], shard["index"])
            if shard["admitted_by_the_bridge_predicate"]:
                assert stream["beats"] == shard["row_count"]
                assert stream["distinct_addresses"] == shard["row_count"]
                assert stream["mismatched_against_golden"] == 0
            else:
                assert stream["beats"] == 0


def test_a_refused_shape_traps_with_the_class_the_abi_names(campaign: dict) -> None:
    refusals = 0
    for leg in campaign["legs"]:
        if leg["role"] != "refusal":
            continue
        for shard in leg["shards"]:
            observed = shard["observed"]
            assert observed is not None
            assert observed["fault"] == 1
            assert observed["trap"] == 3  # ot_a3_pkg::A3_TRAP_DESCRIPTOR
            assert observed["work"] == 0
            assert observed["writes"] == 0
            refusals += 1
    assert refusals > 0


def test_g1a_coverage_is_reported_under_g1a_s_own_rule(campaign: dict) -> None:
    impact = campaign["g1a_impact"]
    assert impact["readable"] is True
    for storage_class, record in impact["per_storage_class"].items():
        assert (
            record["covered_class_count_after_under_g1a_unchanged_rule"]
            >= record["covered_class_count_before"]
        ), storage_class
        assert (
            record["covered_class_count_after_under_g1a_unchanged_rule"]
            <= record["issued_class_count"]
        )
