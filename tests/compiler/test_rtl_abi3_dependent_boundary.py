"""The two blocks the dependent chain was missing, and the boundary they let us measure.

``results/rtl/abi3_boundary_chain.json`` established -- by elaboration, not by
reading source -- that two of section 3.6's five terms had no RTL at all.  These
tests pin the three records that answer it:

* ``results/rtl/abi3_partial_collector.json`` and
  ``results/rtl/abi3_operand_receiver.json``, the two blocks, each qualified on
  both simulators with distinct fail-closed modes;
* ``results/rtl/abi3_boundary_chain_measured.json``, the two-tile chain built
  out of those blocks plus T64 and RE8, and the span it measures.

The one thing the chain record must NOT become by accident is the boundary of
section 13 item 13: ``tools/derive_cycle_machine.py`` reads
``boundary.is_the_section_13_item_13_boundary``, and a record that started
claiming to be that boundary would move gate G4 on a span that leaves three of
the five terms outside it.  That is pinned here, in both directions: the flag is
false, and the calibration's own reader refuses it.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
COLLECTOR = ROOT / "results/rtl/abi3_partial_collector.json"
RECEIVER = ROOT / "results/rtl/abi3_operand_receiver.json"
CHAIN = ROOT / "results/rtl/abi3_boundary_chain_measured.json"
SIMULATORS = ["iverilog", "verilator"]


def _load(path: Path) -> dict:
    if not path.exists():
        pytest.skip(f"{path} has not been produced")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def collector() -> dict:
    return _load(COLLECTOR)


@pytest.fixture(scope="module")
def receiver() -> dict:
    return _load(RECEIVER)


@pytest.fixture(scope="module")
def chain() -> dict:
    return _load(CHAIN)


# -- the two blocks -----------------------------------------------------------------
@pytest.mark.parametrize("name", ["collector", "receiver"])
def test_block_ran_on_both_simulators(request: pytest.FixtureRequest, name: str) -> None:
    record = request.getfixturevalue(name)
    assert record["status"] == "pass"
    assert sorted(record["simulators_counted"]) == SIMULATORS
    agreement = record["cross_simulator_agreement"]
    assert agreement["simulators_observed_the_same_cases"] is True
    assert agreement["check_counts_agree"] is True
    assert not record["divergences"]
    counts = {sim["checks"] for sim in record["simulators"]}
    assert len(counts) == 1 and counts.pop() > 0


@pytest.mark.parametrize("name,least", [("collector", 6), ("receiver", 6)])
def test_block_fails_closed_distinctly(request: pytest.FixtureRequest, name: str,
                                       least: int) -> None:
    """Every refusal the campaign exercises must be a DIFFERENT detail."""
    record = request.getfixturevalue(name)
    modes = record["block"]["distinct_fault_modes"]
    details = [m["detail"] for m in modes]
    assert len(details) == len(set(details)), modes
    assert len(details) >= least, modes


def test_the_collector_is_bounded_by_the_endpoint_buffer(collector: dict) -> None:
    """Section 4.4's 4 KiB per endpoint is a sized resource, not a convenience."""
    assert collector["block"]["leaf_buffer_bytes"] == 4096
    assert "4 KiB" in collector["block"]["leaf_buffer_basis"]


def test_the_receiver_readiness_delay_is_measured_and_invariant(receiver: dict) -> None:
    delay = receiver["readiness_delay"]
    assert delay["observed"], "a campaign that stamped no readiness measured nothing"
    assert len(delay["observed"]) == 1, delay["observed"]
    assert delay["cycles"] == delay["observed"][0] > 0


# -- the chain ----------------------------------------------------------------------
def test_chain_ran_on_both_simulators_and_they_agree(chain: dict) -> None:
    assert chain["status"] == "pass"
    assert sorted(chain["simulators_counted"]) == SIMULATORS
    for build in chain["builds"]:
        assert build["status"] == "pass", build["label"]
        assert build["simulators_agree"] is True, build["label"]
        assert build["check_counts_agree"] is True, build["label"]
        assert not build["divergences"], build["label"]


def test_the_span_is_positive_and_the_legs_account_for_all_of_it(chain: dict) -> None:
    boundary = chain["boundary"]
    assert isinstance(boundary["cycles"], int) and boundary["cycles"] > 0
    assert boundary["simulators_agree"] is True
    reported = {entry["cycles"] for entry in boundary["per_simulator"]}
    assert reported == {boundary["cycles"]}
    legs = boundary["decomposition"]
    total = 0
    for name, values in legs.items():
        assert len(values) == 1, (name, values)
        total += values[0]
    assert total == boundary["cycles"], legs


def test_every_leg_names_the_module_that_owns_it(chain: dict) -> None:
    rule = chain["boundary"]["decomposition_rule"]
    assert set(rule) == set(chain["boundary"]["decomposition"])
    for name, text in rule.items():
        assert text.strip(), name


def test_the_chain_is_design_rtl_end_to_end(chain: dict) -> None:
    assert chain["chain"]["every_cycle_of_the_span_is_design_rtl"] is True
    modules = chain["chain"]["modules"]
    for module in ("ot_a3_partial_collector", "ot_a3_operand_receiver",
                   "ot_a3_tree_endpoint_fp32", "ot_a3_tile64"):
        assert any(module in m for m in modules), module


def test_the_boundary_does_not_scale_with_the_reduction_depth(chain: dict) -> None:
    """The finding: it is a service term, not a latency term."""
    build = next(b for b in chain["builds"] if b["adder_stages"] == 3)
    assert len(build["leaves_swept"]) >= 3, build["leaves_swept"]
    assert build["boundary_cycles_observed"] == [build["boundary_cycles"]]


def test_the_headline_is_the_routed_adder_depth(chain: dict) -> None:
    """R13: the deeper, worse figure is the headline, not the L = 1 one."""
    depth = chain["boundary"]["adder_depth"]
    assert depth["headline_stages"] == 3
    per = {int(k): v for k, v in depth["per_stages"].items()}
    assert per[3] == chain["boundary"]["cycles"]
    for stages, value in per.items():
        if stages < 3:
            assert value < per[3], per


def test_it_does_not_claim_to_be_the_item_13_boundary(chain: dict) -> None:
    boundary = chain["boundary"]
    assert boundary["is_the_section_13_item_13_boundary"] is False
    assert boundary["why_not"].strip()
    for term in ("mesh transfer", "queue admission", "acknowledged completion"):
        assert term in boundary["why_not"], term


def test_the_calibration_reader_refuses_it(chain: dict) -> None:
    """The consumer's own reader, not a restatement of what it should say."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.derive_cycle_machine import _boundary_measurement

    verdict = _boundary_measurement(chain)
    assert verdict["measured"] is False
    assert verdict["rtl_measured_boundary_cycles"] is None
    assert chain["boundary"]["why_not"] in verdict["why"]


def test_the_composition_is_a_sum_of_two_records_and_says_so(chain: dict) -> None:
    comp = chain["composition"]
    if comp["control_half_cycles"] is None:
        pytest.skip("the control-half record is absent or failing")
    assert comp["node_local_total_cycles"] == (comp["datapath_half_cycles"]
                                               + comp["control_half_cycles"])
    assert "not a third measurement" in comp["rule"]


def test_the_model_comparison_is_read_from_the_model(chain: dict) -> None:
    against = chain["against_the_cycle_model"]
    if against["model_exposed_chain_cycles"] is None:
        pytest.skip("the calibration artifact is absent")
    assert against["model_source"].startswith("results/derived/")
    decomposition = against["model_decomposition"]
    assert sum(decomposition.values()) == against["model_exposed_chain_cycles"]
    assert against["measured_datapath_over_model_fixed_latency"] > 1.0
