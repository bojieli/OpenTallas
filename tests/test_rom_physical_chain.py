"""The ROM physical chain: bitcell -> read energy -> routed macro.

Three runners in this repository measure every physical ROM number the model
has, each one consuming the artifact of the one before it. Nothing read those
artifacts back. This file does, and every assertion here exists because the
thing it checks can go wrong SILENTLY -- legal values, no crash, nothing
refused, a stale number in a report that reads exactly like a fresh one.

The chain and its epistemics are written up in `docs/ROM_PHYSICAL_METHODOLOGY.md`.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]

BITCELL = "results/spice/ihp_sg13g2_bitcell/bitcell.json"
READ_ENERGY = "results/spice/ihp_sg13g2_rom_read_energy/read_energy.json"
MACRO = "results/spice/ihp_sg13g2_rom_macro/macro_route.json"
GENERATOR = "spice/ihp_sg13g2/bitcell/rom_bitarray.tcl"
TECHNOLOGY = "configs/hardware/technology.json"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha256(relative: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / relative).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(document: dict, dotted: str) -> object:
    node = document
    for part in dotted.split("."):
        node = node[part]
    return node


# ---------------------------------------------------------------------------
# The drift that has no symptom: a constant moves, the reports do not
# ---------------------------------------------------------------------------

CITED_CONSTANTS = (
    (BITCELL, "ratio.assumed", "ratio.assumed_source"),
    (MACRO, "comparison.assumed", "comparison.assumed_source"),
    (READ_ENERGY, "reference.assumed_j_per_byte", "reference.assumed_source"),
    (BITCELL, "array_efficiency_reference.assumed", "array_efficiency_reference.assumed_source"),
)


def check_reference(document: dict, technology: dict, value_path: str, source_path: str) -> None:
    """One artifact's recorded reference against the live constant it cites."""
    recorded = float(resolve(document, value_path))
    source = str(resolve(document, source_path))
    path, _, pointer = source.partition("#")
    assert path == TECHNOLOGY, f"{source_path} cites {path}, not the technology file"
    live = float(resolve(technology, pointer)["value"])
    assert recorded == pytest.approx(live, rel=1e-12), (
        f"the run was measured against {pointer} = {recorded}, but that constant is now "
        f"{live}. Re-run the experiment; do not edit the artifact."
    )


def test_every_assumed_reference_still_matches_the_constant_it_cites() -> None:
    """Each artifact records the model constant it was measured against, by
    path. Another agent moving that constant leaves the artifact and its
    REPORT.md quoting a value the model no longer holds, with nothing to say
    so: the report still says PASS, the ratio it prints is still real, and only
    the comparison is wrong. This is the defect that reaches a reader.
    """
    technology = load(TECHNOLOGY)
    for artifact, value_path, source_path in CITED_CONSTANTS:
        check_reference(load(artifact), technology, value_path, source_path)


def test_the_drift_check_fires_when_the_constant_moves() -> None:
    """A check nobody has seen fire is a check nobody has.

    This is the whole mechanism above, run against a technology file in which
    one constant has moved and the artifact has not been re-run -- which is what
    actually happens when a concurrent edit lands.
    """
    import copy

    technology = copy.deepcopy(load(TECHNOLOGY))
    artifact, value_path, source_path = CITED_CONSTANTS[0]
    document = load(artifact)
    _, _, pointer = str(resolve(document, source_path)).partition("#")
    node = technology
    for part in pointer.split("."):
        node = node[part]
    node["value"] = float(node["value"]) * 1.5
    with pytest.raises(AssertionError, match="Re-run the experiment"):
        check_reference(document, technology, value_path, source_path)


def test_every_assumed_reference_records_the_grade_it_was_measured_against() -> None:
    technology = load(TECHNOLOGY)
    for artifact, grade_path, source_path in (
        (BITCELL, "array_efficiency_reference.assumed_grade",
         "array_efficiency_reference.assumed_source"),
        (MACRO, "comparison.assumed_grade", "comparison.assumed_source"),
        (READ_ENERGY, "reference.assumed_grade", "reference.assumed_source"),
    ):
        document = load(artifact)
        _, _, pointer = str(resolve(document, source_path)).partition("#")
        assert resolve(document, grade_path) == resolve(technology, pointer)["grade"], (
            f"{artifact}:{grade_path} disagrees with the live grade of {pointer}"
        )


# ---------------------------------------------------------------------------
# The chain: each run consumes the one before it, and says so
# ---------------------------------------------------------------------------

def test_all_three_runs_drew_with_the_generator_that_is_on_disk() -> None:
    """A layout generator edited after a run leaves three artifacts describing
    a cell that no longer exists. The runners record the generator hash; this
    is what compares it with the file.
    """
    current = sha256(GENERATOR)
    for artifact in (BITCELL, READ_ENERGY):
        recorded = load(artifact)["inputs"]["generator"]["sha256"]
        assert recorded == current, (
            f"{artifact} was produced by generator {recorded} but {GENERATOR} is now "
            f"{current}; the artifact describes a different cell"
        )


def test_the_macro_reads_the_bitcell_area_rather_than_restating_it() -> None:
    macro = load(MACRO)
    bitcell = load(BITCELL)
    measured = macro["measured_inputs"]["rom_bitcell_area"]
    assert measured["cell_area_um2"] == pytest.approx(
        bitcell["rom_bitcell"]["cell_area_um2"], rel=1e-12
    )
    assert measured["generator_sha256"] == bitcell["inputs"]["generator"]["sha256"]
    assert measured["generator_sha256"] == sha256(GENERATOR)
    for entry in macro["macros"]:
        assert entry["bit_array_area_um2"] == pytest.approx(
            entry["bits"] * measured["cell_area_um2"], rel=1e-9
        )


def test_the_macro_reads_the_wordline_load_rather_than_declaring_it() -> None:
    macro = load(MACRO)
    energy = load(READ_ENERGY)
    used = macro["measured_inputs"]["wordline_capacitance"]["ff_per_column"]
    assert used == pytest.approx(
        energy["wordline_capacitance"]["ff_per_column"], rel=1e-12
    )


def test_the_wordline_load_handed_on_is_the_larger_of_the_two_windows() -> None:
    """Two measurement windows give two numbers. The larger sizes the wordline
    drivers UP, which makes the periphery bigger and the array efficiency this
    chain reports LOWER. Taking the smaller would improve every number in the
    macro report, which is exactly why the choice is pinned here.
    """
    block = load(READ_ENERGY)["wordline_capacitance"]
    assert block["ff_per_column"] == pytest.approx(
        max(block["ff_per_column_transition_only"], block["ff_per_column_including_hold"]),
        rel=1e-12,
    )


def test_the_extracted_interconnect_alone_would_have_understated_the_load() -> None:
    """`ext2spice` writes wiring parasitics; the row transistors' gate
    capacitance is inside the device model. Counting the wordline load out of
    the parasitic netlist -- the obvious thing to do -- understates it, in the
    direction that flatters the macro area. If that gap ever closes, the
    measurement method changed and the report's explanation is stale.
    """
    block = load(READ_ENERGY)["wordline_capacitance"]
    assert block["extracted_interconnect_only_ff_per_column"] < block["ff_per_column"] / 5


# ---------------------------------------------------------------------------
# The findings themselves, pinned so they cannot be quietly erased
# ---------------------------------------------------------------------------

def test_read_energy_per_bit_is_affine_in_column_height_not_constant() -> None:
    sweep = {entry["rows"]: entry["read_energy_fj_per_bit"] for entry in load(READ_ENERGY)["height_sweep"]}
    assert len(sweep) >= 4, "the column-height finding needs the sweep it was measured on"
    heights = sorted(sweep)
    assert sweep[heights[-1]] > 4 * sweep[heights[0]], (
        "read energy per bit no longer varies strongly with column height; the finding "
        "that a scalar J/byte silently names a column height would no longer hold"
    )
    fit = load(READ_ENERGY)["height_fit"]
    assert fit["slope_fj_per_row"] > 0 and fit["r2"] > 0.99


def test_the_two_macro_efficiency_boundaries_are_reported_apart() -> None:
    """`rom.array_efficiency` does not say which boundary it means and the two
    differ by more than a factor of two. Collapsing them into one number is the
    defect this run exists to name.
    """
    comparison = load(MACRO)["comparison"]
    internal = comparison["macro_internal_range"]
    whole = comparison["whole_macro_range"]
    assert internal[0] > whole[1] * 2, (
        "the macro-internal and whole-macro efficiencies no longer differ by more than "
        "2x; the report's central claim would need re-deriving"
    )


def test_the_die_floor_is_not_a_floor_at_a_constant_in_the_runner() -> None:
    """The die-floor probe replaced one chosen constant (`utilization`) with
    another (the placer's target density, written in the runner). Every refusal
    arrived as OpenROAD's GPL-0302 -- *Use a higher -density* -- naming that
    constant as the remedy, and the report called it a measured cell-area
    floor. A refusal must now survive the contract's density ladder, and a
    refusal that does not is recorded as conditional rather than measured.
    """
    macro = load(MACRO)
    ladder = macro["comparison"]["place_density_ladder"]
    assert ladder, "the contract's placement-density escalation ladder is not recorded"
    for entry in macro["macros"]:
        probe = entry["die_floor_probe"]
        assert probe["place_density_ladder"] == ladder
        for step in probe["steps"]:
            attempts = step["density_attempts"]
            assert attempts, f"{entry['name']}: a probe step recorded no density attempt"
            if step["closed_clean"]:
                continue
            if step["failure_blames_place_density"]:
                assert [a["place_density"] for a in attempts][1:] == list(ladder), (
                    f"{entry['name']}: a refusal still blaming the target density did not "
                    f"walk the whole ladder {ladder}; the floor is the runner's, not the "
                    "design's"
                )
                assert step["floor_limited_by_place_density"] is True
    assert macro["comparison"]["die_floor_limited_by_place_density"] == any(
        step["floor_limited_by_place_density"]
        for entry in macro["macros"]
        for step in entry["die_floor_probe"]["steps"]
    )


def test_the_tapless_control_actually_failed_on_the_latch_up_rule() -> None:
    """Tap bands are area. Their necessity is shown by drawing the array
    without them and requiring the deck to refuse it -- not asserted.
    """
    controls = [
        entry["tapless_control"]
        for entry in load(MACRO)["macros"]
        if entry.get("tapless_control")
    ]
    assert controls, "no tapless control was run; the tap-band area is then asserted"
    for control in controls:
        assert control["drc_errors"] > 0
        assert control["latch_up_rules"], control["violated_rules"]
        assert all("LU." in rule for rule in control["latch_up_rules"])


def test_every_bitcell_dimension_was_refused_one_step_smaller() -> None:
    probes = load(BITCELL)["rom_bitcell"]["floor_probes"]
    assert len(probes) >= 6
    for probe in probes:
        assert probe["drc_errors"] > 0, f"{probe['dimension']} shrank without a violation"
        assert probe["violated_rules"], f"{probe['dimension']} failed without naming a rule"


# ---------------------------------------------------------------------------
# The node wall
# ---------------------------------------------------------------------------

def test_no_run_in_the_chain_permits_target_node_scaling() -> None:
    for artifact in (BITCELL, READ_ENERGY, MACRO):
        boundary = load(artifact)["claim_boundary"]
        assert boundary["target_node_scaling_status"] == "prohibited"
        assert boundary["target_node_scaling_rule"] is None
        forbidden = " ".join(boundary["forbidden_inferences"])
        assert "N7" in forbidden and "silicon" in forbidden


def test_the_quantised_ratio_ladder_comes_from_the_siblings_own_quanta() -> None:
    """At the FinFET node both cells land on integer multiples of one CPP x one
    fin pitch, so the ratio is a quotient of small integers and a continuous
    sweep of it samples values no drawn cell can have. The ladder must be
    generated from the sibling's recorded quanta, not written by hand.
    """
    ladder = load(BITCELL)["node_sensitivity"]["admissible_ratio_ladder"]
    sibling = load("results/asap7_physical/bitcell_density/bitcell_density.json")["measurement"]
    assert ladder["rom_units_measured"] == sibling["rom_via_area_in_cpp_x_finpitch_units"]
    assert ladder["sram_units_measured"] == sibling["sram_area_in_cpp_x_finpitch_units"]
    assert ladder["measured_rung"] == pytest.approx(
        sibling["ratio_via_programmed_rom_to_sram"], rel=1e-12
    )
    down, up = ladder["gap_to_next_rung_down"], ladder["gap_to_next_rung_up"]
    assert down > 0 and up > 0
    assert down != pytest.approx(up, rel=1e-6), (
        "the rungs either side of the measurement are equally spaced, which would make an "
        "evenly-spaced sweep defensible; they are not, and that is the point"
    )


def test_the_two_measured_nodes_are_reported_apart_and_never_blended() -> None:
    bitcell = load(BITCELL)
    here = bitcell["ratio"]["measured"]
    there = bitcell["node_sensitivity"]["ratio"]
    assert abs(there - here) / here > 0.5, (
        "the two measured node ratios no longer disagree; the node-transfer finding "
        "that governs this whole chain would need re-deriving"
    )
    assert "never" in bitcell["node_sensitivity"]


# ---------------------------------------------------------------------------
# The refusals themselves. A check nobody has seen fire is a check nobody has.
# ---------------------------------------------------------------------------

def _runner(stem: str):
    """Import one of the runners without leaving `tools/` on `sys.path`.

    The runners insert their own directory into `sys.path` at import time so
    they can import each other. Executing one from a test therefore mutates a
    process global that every later test in the session sees, and this
    repository has already shipped one defect of exactly that shape. So the
    path is restored.
    """
    import importlib.util
    import sys

    before = list(sys.path)
    spec = importlib.util.spec_from_file_location(f"ot_{stem}", ROOT / "tools" / f"{stem}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = before
    return module


def _macro_runner():
    return _runner("run_ihp_rom_macro_route")


def test_rom_service_physical_uses_the_supported_openroad_database_accessor() -> None:
    """Keep report extraction compatible with the pinned OpenROAD build.

    ``ord::get_db`` returns an odb::dbDatabase, whose API has no ``getChain``
    method in the installed toolchain.  The failure occurs only after detailed
    routing, so a regression here otherwise wastes the entire physical run
    before refusing to write its DEF.
    """
    template = _runner("run_rom_service_physical").PNR_TEMPLATE
    assert "set block [ord::get_db_block]" in template
    assert "getChain" not in template


def test_rom_service_physical_parser_retains_timing_sections_and_path() -> None:
    """OpenROAD labels max and min identically; section markers disambiguate them."""

    runner = _runner("run_rom_service_physical")
    log = f"""prefix
{runner.RESULT_BEGIN}
Design area 1221010 u^2 33% utilization.
--- worst setup ---
worst slack -2.90
--- worst hold ---
worst slack -0.07
--- tns ---
tns -3517.61
period_ns 10.0
--- worst setup path ---
Startpoint: req_valid (input port clocked by clk)
Endpoint: state_q (rising edge-triggered flip-flop clocked by clk)
slack (VIOLATED) -2.900
die_um 1931.09 1931.09
core_um 1920.48 1916.46
instances 754990
nets 67132
{runner.RESULT_END}
suffix
"""

    parsed = runner.parse_results(log)
    assert parsed["worst_setup_slack_ns"] == -2.90
    assert parsed["worst_hold_slack_ns"] == -0.07
    assert parsed["total_negative_slack_ns"] == -3517.61
    assert "Startpoint: req_valid" in parsed["worst_setup_path"]
    assert "slack_parse_failed" not in parsed


def test_rom_service_physical_verdict_requires_clean_route_and_timing() -> None:
    """Neither a dirty DEF nor an unclosed clock may be promoted to PASS."""

    verdict = _runner("run_rom_service_physical").implementation_verdict
    failing_metrics = {
        "design_area_um2": 1.0,
        "worst_setup_slack_ns": -2.90,
        "worst_hold_slack_ns": -0.07,
    }

    dirty = verdict(
        pnr_returncode=0,
        metrics=failing_metrics,
        routed_def_written=True,
        drc_violations=337,
    )
    assert dirty["status"] == "fail"
    assert dirty["route_completed"]
    assert not dirty["drc_clean_route"]
    assert not dirty["timing_closed_at_target_period"]

    timing_only = verdict(
        pnr_returncode=0,
        metrics=failing_metrics,
        routed_def_written=True,
        drc_violations=0,
    )
    assert timing_only["status"] == "routed_timing_not_closed"
    assert timing_only["drc_clean_route"]
    assert not timing_only["converged"]

    passed = verdict(
        pnr_returncode=0,
        metrics={
            "design_area_um2": 1.0,
            "worst_setup_slack_ns": 0.01,
            "worst_hold_slack_ns": 0.02,
        },
        routed_def_written=True,
        drc_violations=0,
    )
    assert passed["status"] == "pass"
    assert passed["converged"]


def test_rom_service_physical_flow_models_wires_and_exposes_route_effort() -> None:
    """The retry controls and timing reports must stay in the generated Tcl."""

    template = _runner("run_rom_service_physical").PNR_TEMPLATE
    assert "set_wire_rc -signal -layer Metal2" in template
    assert "set_wire_rc -clock -layer Metal5" in template
    assert "set_routing_layers -signal Metal2-Metal5 -clock Metal2-Metal5" in template
    assert "-bottom_routing_layer Metal2 -top_routing_layer Metal5" in template
    assert "-congestion_iterations {congestion_iterations}" in template
    assert "-droute_end_iter {droute_end_iter}" in template
    assert 'puts "--- worst setup path ---"' in template
    assert "report_checks -path_delay max" in template


def test_rom_service_physical_make_target_reproduces_the_canonical_effort() -> None:
    """The documented Make target must not silently regenerate an older flow."""

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    recipe = makefile.split("rom-service-physical:", 1)[1].split("\n\n", 1)[0]
    for option in (
        "--period-ns 20",
        "--utilization 25",
        "--density 0.45",
        "--threads 8",
        "--congestion-iterations 80",
        "--droute-end-iter 64",
        "--repair-timing",
    ):
        assert option in recipe


def test_rom_service_physical_artifact_is_source_locked_and_closed() -> None:
    """The canonical pass must be current, routed, timed, and narrowly scoped."""

    artifact = load("results/rtl/rom_service_physical.json")
    assert artifact["schema"] == "opentallas.rtl.rom_service_physical.v1"
    assert artifact["status"] == "pass"
    for source, digest in artifact["source_sha256"].items():
        assert digest == sha256(source), f"stale ROM-service physical source: {source}"

    implementation = artifact["implementation"]
    assert implementation["returncode"] == 0
    assert implementation["route_completed"]
    assert implementation["routed_def_written"]
    assert implementation["detailed_route_drc_violations"] == 0
    assert implementation["drc_clean_route"]
    assert implementation["timing_closed_at_target_period"]

    metrics = artifact["metrics"]
    assert metrics["period_ns"] == 20
    assert metrics["worst_setup_slack_ns"] >= 0.0
    assert metrics["worst_hold_slack_ns"] >= 0.0
    assert metrics["total_negative_slack_ns"] == 0.0
    assert metrics["worst_setup_path"]

    boundary = artifact["claim_boundary"]
    assert boundary["open_pdk_rtl_to_routed_feasibility"]
    assert boundary["routed_not_only_synthesised"]
    assert boundary["timing_closed_at_target_period"]
    for excluded in (
        "contains_rom_array_or_macro",
        "rom_cell_area_or_density",
        "rom_read_energy_or_sense_margin",
        "target_node_area_or_delay",
        "signoff_drc_or_lvs",
        "foundry_drc",
        "gds_generated",
        "feature_size_scaling_permitted",
        "enters_iso_node_or_roofline_comparison",
    ):
        assert not boundary[excluded]


def test_the_macro_contract_refuses_a_missing_or_useless_density_ladder() -> None:
    """Demonstrates the refusal rather than asserting it exists.

    The die-floor probe's whole purpose is to remove a chosen constant from the
    reported efficiency. It replaced `utilization` with the placer's target
    density and nothing noticed, so the contract must now carry an escalation
    ladder, that ladder must ascend, and every rung must lie above the runner's
    own cap -- a ladder at or below the cap escalates nothing while looking
    exactly like one that does.
    """
    import copy

    module = _macro_runner()
    contract = json.loads(
        (ROOT / "physical/ihp_sg13g2_rom_macro/macro_contract.json").read_text(encoding="utf-8")
    )
    lock = json.loads(
        (ROOT / "configs/pdk/ihp_sg13g2_physical_lock.json").read_text(encoding="utf-8")
    )
    module.validate_contract(contract, lock)

    cap = module.PLACE_DENSITY_NOMINAL_CAP
    mutations = {
        "no ladder at all": lambda c: c.pop("die_floor_probe_place_densities"),
        "a rung at or below the runner's own cap": (
            lambda c: c.__setitem__("die_floor_probe_place_densities", [cap, 0.95])
        ),
        "a ladder that descends": (
            lambda c: c.__setitem__("die_floor_probe_place_densities", [0.99, 0.90])
        ),
        "a rung above 1.0": (
            lambda c: c.__setitem__("die_floor_probe_place_densities", [0.90, 1.10])
        ),
    }
    for label, mutate in mutations.items():
        broken = copy.deepcopy(contract)
        mutate(broken)
        with pytest.raises(module.MacroRouteError):
            module.validate_contract(broken, lock)


def test_the_macro_claim_boundary_must_name_the_placement_density() -> None:
    import copy

    module = _macro_runner()
    contract = json.loads(
        (ROOT / "physical/ihp_sg13g2_rom_macro/macro_contract.json").read_text(encoding="utf-8")
    )
    lock = json.loads(
        (ROOT / "configs/pdk/ihp_sg13g2_physical_lock.json").read_text(encoding="utf-8")
    )
    broken = copy.deepcopy(contract)
    broken["claim_boundary"]["forbidden_inferences"] = [
        item
        for item in broken["claim_boundary"]["forbidden_inferences"]
        if "placement density" not in item
    ]
    with pytest.raises(module.MacroRouteError):
        module.validate_contract(broken, lock)


def test_a_named_but_disconnected_ground_port_is_refused() -> None:
    """The port check used to compare names only.

    The array's ground pin is a drawn pad with a via down to the tap strip. If
    that via lands on nothing, Magic still names the pad `VSS`, still writes it
    as the first port of the `.subckt`, and the netlist still simulates -- with
    every transistor source on a node the testbench is not driving. A name check
    passes that netlist. This is the check that does not.
    """
    import tempfile

    module = _runner("run_ihp_bitcell_density")

    netlist = ROOT / "results/spice/ihp_sg13g2_bitcell/artifacts/ihp_rom_bitarray.pex.spice"
    module.check_ports(netlist, 8, 4, module.BitcellError)

    # Two ways to lose the ground while keeping the port. The second is the one
    # a bulk-accepting check would wave through: every nMOS shares the substrate,
    # so the bulk terminal stays on VSS even when the source rail is broken.
    for label, terminals in (("whole cell disconnected", (1, 2, 3, 4)), ("source rail broken", (1, 3))):
        broken_lines = []
        for line in netlist.read_text(encoding="utf-8").splitlines():
            if line.startswith("X") and "nmos" in line:
                fields = line.split()
                for index in terminals:
                    if fields[index] == "VSS":
                        fields[index] = "a_floating#"
                line = " ".join(fields)
            broken_lines.append(line)
        with tempfile.NamedTemporaryFile("w", suffix=".spice", delete=False) as handle:
            handle.write("\n".join(broken_lines))
            broken = Path(handle.name)
        try:
            module.check_ports(broken, 8, 4, module.BitcellError)
        except module.BitcellError as exc:
            assert "floating ground" in str(exc), (label, str(exc))
        else:
            raise AssertionError(f"{label}: check_ports accepted a netlist with no ground")
        finally:
            broken.unlink()


def test_the_recorded_deck_digest_is_one_a_rerun_can_reproduce() -> None:
    """`deck_sha256` looks like a reproducibility anchor and is not one.

    Every simulation deck carries the absolute path of that run's temporary
    build directory in its `.include` and `.lib` lines, so its hash changes on
    every run of an unchanged experiment -- the same trap the bitcell runner
    found in Magic's clock-stamped `.mag`. A hash a reader cannot reproduce on
    a correct run proves nothing whether they check it or not.
    """
    import tempfile

    module = _runner("run_ihp_rom_read_energy")
    deck = (
        '.title x\n'
        '.lib "/pdk/root/models.lib" mos_tt\n'
        '.include "/build/run.AbC123/array_64/ihp_rom_bitarray.pex.spice"\n'
        '.end\n'
    )
    moved = deck.replace("AbC123", "ZzZ999").replace("/build/", "/elsewhere/")
    digests = []
    for text in (deck, moved):
        with tempfile.NamedTemporaryFile("w", suffix=".sp", delete=False) as handle:
            handle.write(text)
            path = Path(handle.name)
        digests.append(module.canonical_deck_digest(path, module.ReadEnergyError))
        path.unlink()
    assert digests[0] == digests[1], (
        "the canonical deck digest still depends on the build directory, so it is no more "
        "reproducible than the raw hash it replaces"
    )

    # And it refuses to record a digest that would inherit the defect it fixes.
    with tempfile.NamedTemporaryFile("w", suffix=".sp", delete=False) as handle:
        handle.write(deck)
        path = Path(handle.name)
    saved = module.canonical_deck
    module.canonical_deck = lambda text: text
    try:
        with pytest.raises(module.ReadEnergyError, match="absolute path"):
            module.canonical_deck_digest(path, module.ReadEnergyError)
    finally:
        module.canonical_deck = saved
        path.unlink()


def test_every_case_records_a_canonical_deck_digest() -> None:
    energy = load(READ_ENERGY)
    for case in energy["cases"] + energy["height_sweep"]:
        assert case.get("canonical_deck_sha256"), (
            f"{case['case_id']} records no reproducible deck digest"
        )
    assert "ARCHIVAL IDENTITY ONLY" in energy["case_hash_stability"]
