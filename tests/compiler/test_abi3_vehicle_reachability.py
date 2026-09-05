"""The vehicle reachability derivation, and the RTL measurement that checks it.

The standing plan proposed reaching the six mapped operator families with
"one case per family entering at that family's own PC".  These tests pin the
derivation that says why that cannot work, in both directions: the shape it
refuses must stay refused, and the shape it admits must stay admitted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.abi3.constants import InstructionFlag
from tools import build_abi3_vehicle_reachability as reach
from tools.build_abi3_shipped_prefix_vectors import TARGETS, _deployment_vectors

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "results/rtl/abi3_vehicle_reachability.json"
PROBE_ARTIFACT = ROOT / "results/rtl/abi3_vehicle_entry_probe.json"
TRAP_INTERNAL = 13


@pytest.fixture(scope="module")
def qwen_rom() -> reach.Program:
    deployment_vectors, _ = _deployment_vectors()
    target = TARGETS[0]
    case = next(
        entry
        for entry in deployment_vectors["cases"]
        if entry["name"] == f"{target.key}/decode"
    )
    symbols = {int(key): int(value) for key, value in case["symbols"].items()}
    return reach.Program(target, symbols)


def test_every_mapped_family_is_issued_by_the_governed_decode(qwen_rom):
    families = reach.family_report(qwen_rom)
    named = {entry["family"] for entry in families}
    assert named == {name for name, _, _ in reach.MAPPED_FAMILIES}
    # Each one is actually in the program: a family with no issue site would
    # make every claim about it vacuous.
    for entry in families:
        assert entry["issue_sites"], entry["family"]


def test_entering_at_the_family_own_pc_is_refused_before_dispatch(qwen_rom):
    """The shape the plan proposed, evaluated exactly as proposed."""

    for entry in reach.family_report(qwen_rom):
        for site in entry["issue_sites"]:
            own = site["own_pc_entry"]
            assert own["entry_pc"] == site["pc"]
            assert own["derivable"], own
            assert own["dispatches_the_site"] is False, (entry["family"], site["pc"])
            assert own["trap_class"] == TRAP_INTERNAL
            assert own["trap_pc"] == site["pc"]
            assert "never issued" in own["reason"]


def test_a_mid_program_entry_that_does_dispatch_exists(qwen_rom):
    """Otherwise the refusal above would only say "entry PCs do not work"."""

    control = reach.positive_control(qwen_rom)
    assert control is not None
    assert control["entry_pc"] > qwen_rom.entry_pc
    assert control["predicted_dispatches_the_site"] is True


def test_the_three_cheapest_families_cost_the_prefix_and_nothing_more(qwen_rom):
    """Scatter and attention sit before the layer's second MATMUL group."""

    by_family = {entry["family"]: entry for entry in reach.family_report(qwen_rom)}
    prefix_macs = by_family["DMA.SCATTER"]["min_macs"]
    assert prefix_macs == 25_165_824  # the query/key/value projections
    assert by_family["ATTENTION.GQA"]["min_macs"] == prefix_macs
    assert by_family["VECTOR.ADD"]["min_macs"] > prefix_macs
    assert by_family["VECTOR.SILU_MUL"]["min_macs"] > by_family["VECTOR.ADD"]["min_macs"]


def test_token_append_costs_a_whole_decode_step(qwen_rom):
    """It needs an event from before the layer loop and one from after it."""

    families = reach.family_report(qwen_rom)
    by_family = {entry["family"]: entry for entry in families}
    whole = reach.simulate(qwen_rom, qwen_rom.entry_pc, len(qwen_rom.instructions))
    assert by_family["SELECTION.TOKEN_APPEND"]["min_macs"] == whole["macs"]
    # and that is two orders of magnitude past the next family's cost
    assert by_family["SELECTION.TOKEN_APPEND"]["min_macs"] > 30 * (
        by_family["VECTOR.ADD"]["min_macs"]
    )
    plan = reach.case_plan(families)
    entry_zero = next(item for item in plan if item["entry_pc"] == 0)
    step = next(
        item
        for item in entry_zero["cost_curve"]
        if item["family"] == "SELECTION.TOKEN_APPEND"
    )
    assert step["marginal_macs"] > 7_000_000_000


def test_argmax_needs_its_own_transaction_after_the_layer_loop(qwen_rom):
    by_family = {entry["family"]: entry for entry in reach.family_report(qwen_rom)}
    site = by_family["SELECTION.ARGMAX"]["issue_sites"][0]
    assert site["reachable"]
    entry = site["cheapest_entry"]["entry_pc"]
    assert entry > qwen_rom.entry_pc
    assert site["cheapest_entry"]["macs"] == 622_329_856  # the LM head


def test_a_predicated_path_is_underived_rather_than_guessed(qwen_rom, monkeypatch):
    """Falsification: splice the flag in and the machine must stop answering."""

    site = reach.family_report(qwen_rom)[0]["issue_sites"][0]["pc"]
    original = qwen_rom.instructions[site]

    class Predicated:
        major = original.major
        sub = original.sub
        flags = int(original.flags) | int(InstructionFlag.PREDICATED)
        descriptor_id = original.descriptor_id
        control_id = getattr(original, "control_id", 0)
        wait_set_id = original.wait_set_id
        signal_event_id = original.signal_event_id

    spliced = list(qwen_rom.instructions)
    spliced[site] = Predicated()
    monkeypatch.setattr(qwen_rom, "instructions", spliced)
    run = reach.simulate(qwen_rom, site, site + 1)
    assert run["outcome"] == "underivable"
    assert "PREDICATED" in run["reason"]


def test_the_kv_bank_is_sized_from_the_workload_not_the_policy(qwen_rom):
    rows = reach.workload_context_rows()
    assert rows["kv_plane_rows"] == rows["prompt_token_count"] + rows[
        "generated_token_count"
    ]
    demand = reach.bank_demand(
        qwen_rom, reach.family_report(qwen_rom), rows["kv_plane_rows"]
    )
    assert not demand["unresolved_views"]
    kv = [entry for entry in demand["objects"] if entry["is_kv_cache"]]
    assert len(kv) == 1
    # the shipped object declares 8,256 rows of capacity; the vehicle holds
    # the rows this workload reaches, and the two must not be confused
    assert kv[0]["vehicle_words"] == 2 * rows["kv_plane_rows"] * 1024
    assert kv[0]["declared_words"] > kv[0]["vehicle_words"]
    # the selected-token object is written by the device: it is a result-bank
    # plane, not an index-bank operand
    index_objects = [entry for entry in demand["objects"] if entry["bank"] == "index"]
    assert len(index_objects) == 1
    assert {
        record["family"] for record in index_objects[0]["named_by"]
    } == {"DMA.SCATTER", "ATTENTION.GQA"}


@pytest.mark.skipif(not ARTIFACT.is_file(), reason="derivation artifact absent")
def test_the_committed_derivation_names_its_own_program():
    record = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert record["schema"] == reach.SCHEMA
    assert record["targets"]
    for target in record["targets"]:
        # A derivation about a bundle no vector set certifies is a derivation
        # about a program nothing binds, and the record has to say which it is.
        assert "deployment_matches_vector_set" in target


@pytest.mark.skipif(not PROBE_ARTIFACT.is_file(), reason="probe artifact absent")
def test_the_probe_measured_the_refusal_rather_than_asserting_it():
    record = json.loads(PROBE_ARTIFACT.read_text(encoding="utf-8"))
    assert record["measured_probe_count"] == record["probe_count"]
    assert record["own_pc_entry_probe_count"] > 0
    assert record["own_pc_entries_that_dispatched"] == 0
    assert record["positive_control_count"] > 0
    assert record["disagreement_count"] == 0
    assert record["simulated_cycles"] > 0
    qwen = [
        entry
        for entry in record["comparisons"]
        if entry["target"].startswith("qwen3-8b")
        and entry["kind"] == "own_pc_entry"
    ]
    # both stores, all six families, every site
    assert {entry["family"] for entry in qwen} == {
        name for name, _, _ in reach.MAPPED_FAMILIES
    }
    for entry in qwen:
        assert entry["measured"]["trap_class"] == TRAP_INTERNAL
        assert entry["measured"]["issued"] == 0
        assert entry["measured"]["engine_launches"] == 0
