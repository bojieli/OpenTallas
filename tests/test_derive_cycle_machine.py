"""The derived N5 design-target machine pair must stay tied to its anchor.

These tests exist to fail in three specific situations:

1.  The two emitted machines stop being the same machine outside the weight
    path.  That is the defect the generator exists to prevent -- the shipped
    cycle comparison reported a ROM result that was partly a 2x lane advantage
    and a 16x tensor column-group advantage -- so it gets the loudest test.
2.  An emitted number stops reproducing the analytical value it claims to come
    from.  Every parameter that traces to the artifact is pinned here against
    the artifact, not against a copy of itself.
3.  Somebody edits a shipped characterized table or capability while doing it.
    Those files carry RTL and physical evidence and this work must not touch
    them.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.derive_cycle_machine import (  # noqa: E402
    DEFAULT_ANALYTICAL,
    DEFAULT_TECHNOLOGY,
    FAMILIES,
    TECHNOLOGY_VIEW,
    WEIGHT_PATH_ALLOWLIST,
    assert_comparable,
    audit_deployments,
    build,
    canonical,
    load_anchor,
)

ROM_DESIGN = "Qwen3-8B/ROM-N5-native-HBMKV-array-tensor-x4"
HBM_DESIGN = "Qwen3-8B/b200_sxm-x2-tensor"

ROM_TABLE = REPO / f"configs/hardware/abi3_cost_{TECHNOLOGY_VIEW}_rom_v1.json"
HBM_TABLE = REPO / f"configs/hardware/abi3_cost_{TECHNOLOGY_VIEW}_hbm_v1.json"
CAP_DIR = REPO / "configs/hardware/abi3_capability" / TECHNOLOGY_VIEW
ROM_CAP = CAP_DIR / "rom_qwen3_n5_v1.json"
HBM_CAP = CAP_DIR / "hbm_sram_single_chip_n5_v1.json"
ARTIFACT = REPO / "results/derived/qwen3_n5_design_target_machine_pair.json"


@pytest.fixture(scope="module")
def anchor():
    return load_anchor(
        REPO / DEFAULT_ANALYTICAL, REPO / DEFAULT_TECHNOLOGY,
        rom_design=ROM_DESIGN, hbm_design=HBM_DESIGN,
        batch_size=1, context_tokens=8192,
    )


@pytest.fixture(scope="module")
def derived(anchor):
    return build(anchor)


@pytest.fixture(scope="module")
def emitted():
    return {
        "rom_cost_table": json.loads(ROM_TABLE.read_text()),
        "hbm_cost_table": json.loads(HBM_TABLE.read_text()),
        "rom_capability": json.loads(ROM_CAP.read_text()),
        "hbm_capability": json.loads(HBM_CAP.read_text()),
        "artifact": json.loads(ARTIFACT.read_text()),
    }


# ---------------------------------------------------------------------------
# 1.  The emitted files are what the anchor says they are
# ---------------------------------------------------------------------------
def test_emitted_files_match_a_fresh_derivation(derived):
    _, bodies = derived
    for key, path in (
        ("rom_cost_table", ROM_TABLE), ("hbm_cost_table", HBM_TABLE),
        ("rom_capability", ROM_CAP), ("hbm_capability", HBM_CAP),
    ):
        assert path.exists(), f"{path} is missing"
        assert path.read_text() == canonical(bodies[key]), (
            f"{path.relative_to(REPO)} has drifted from the anchor it claims; "
            f"re-run tools/derive_cycle_machine.py"
        )


def test_check_mode_agrees():
    proc = subprocess.run(
        [sys.executable, "tools/derive_cycle_machine.py", "--check"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------------------
# 2.  D1: the two machines are one machine outside the weight path
# ---------------------------------------------------------------------------
def test_the_two_machines_differ_only_inside_the_weight_path(emitted):
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
    )
    assert report["parameters_compared"] == 114
    assert set(report["permitted_differences"]) <= set(WEIGHT_PATH_ALLOWLIST)
    # Every allowlist entry must actually be used.  An allowlist that permits
    # more than the emit needs is an allowlist that will one day hide a real
    # divergence.
    assert report["allowlist_unused"] == [], (
        "the weight-path allowlist permits differences the emit does not "
        f"make: {report['allowlist_unused']}"
    )


def test_a_divergent_compute_parameter_is_rejected(derived, tmp_path):
    """The assertion must actually fail when the machines stop matching."""
    _, bodies = derived
    rigged = json.loads(json.dumps(bodies["hbm_cost_table"]))
    rigged["parameters"]["engine.tensor.work_per_lane_cycle"]["value"] /= 2.0
    path = tmp_path / "abi3_cost_rigged_v1.json"
    path.write_text(canonical(rigged))
    with pytest.raises(Exception) as excinfo:
        assert_comparable(bodies["rom_capability"], ROM_TABLE,
                          bodies["hbm_capability"], path)
    assert "outside the weight path" in str(excinfo.value)
    assert "engine.tensor.work_per_lane_cycle" in str(excinfo.value)


def test_a_lane_count_split_between_the_two_machines_is_rejected(derived, tmp_path):
    _, bodies = derived
    rigged = json.loads(json.dumps(bodies["hbm_capability"]))
    rigged["engines"]["tensor"]["lanes"] //= 2
    with pytest.raises(Exception) as excinfo:
        assert_comparable(bodies["rom_capability"], ROM_TABLE, rigged, HBM_TABLE)
    assert "engine.tensor.lanes" in str(excinfo.value)


def test_the_capabilities_declare_identical_engine_blocks(emitted):
    rom = emitted["rom_capability"]["engines"]
    hbm = emitted["hbm_capability"]["engines"]
    assert set(rom) == set(FAMILIES), sorted(rom)
    assert rom == hbm, "the two capabilities must declare one engine block"
    lanes = {spec["lanes"] for spec in rom.values()}
    assert len(lanes) == 1, f"every family must carry one lane count, got {lanes}"


def test_shared_parameters_resolve_from_the_same_origin(emitted):
    """A value that agrees today but arrives from two places diverges tomorrow.

    The shipped pair has exactly this defect: ``rom_qwen3`` advertises no SRAM
    port count so it falls to its cost table's 1, while
    ``hbm_sram_single_chip`` advertises 2.
    """
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
    )
    # assert_comparable raises on a split origin; reaching here proves none.
    assert report["identical"], "no parameters were compared"


# ---------------------------------------------------------------------------
# 3.  D2: every derived number reproduces the analytical value it cites
# ---------------------------------------------------------------------------
def _param(table, name):
    return table["parameters"][name]["value"]


def test_clock_is_the_analytical_sequencer_latency_over_three_front_end_cycles(
    anchor, emitted
):
    table = emitted["rom_cost_table"]
    front_end = sum(
        _param(table, n) for n in
        ("sequencer.fetch_cycles", "sequencer.decode_cycles", "sequencer.issue_cycles")
    )
    assert front_end == 3
    assert _param(table, "clock.frequency_hz") == pytest.approx(
        front_end / anchor.latency("sequencer_issue_decode_s"), rel=0, abs=0
    )


def test_compute_roof_reproduces_the_published_compute_term_exactly(anchor, emitted):
    """The whole derivation stands on this identity, so it is pinned exactly."""
    table = emitted["rom_cost_table"]
    lanes = _param(table, "engine.tensor.lanes.default")
    wplc = _param(table, "engine.tensor.work_per_lane_cycle")
    clock = _param(table, "clock.frequency_hz")
    roof_ops_s = lanes * wplc * clock
    published = anchor.rom["component_times_s"]["compute"]
    ops = anchor.rom["operations_by_canonical_format"]["bf16"]
    assert ops / roof_ops_s == pytest.approx(published, rel=1e-12), (
        "the derived compute roof no longer reproduces the analytical compute "
        "term; the anchor or the derivation has moved"
    )
    # ...and the roof is the design point's own area times its own density.
    assert roof_ops_s == pytest.approx(anchor.compute_roof_ops_s, rel=1e-12)


def test_lanes_is_the_narrowest_tensor_operator_width(emitted):
    """Any wider lane array is masked on the GQA projections and misses the roof."""
    meta = json.loads((REPO / "configs/models/qwen3-8b.json").read_text())["metadata"]
    narrowest = int(meta["num_key_value_heads"]) * int(meta["head_dim"])
    assert _param(emitted["rom_cost_table"], "engine.tensor.lanes.default") == narrowest
    assert emitted["rom_capability"]["engines"]["tensor"]["lanes"] == narrowest


def test_every_family_carries_the_one_analytical_arithmetic_roof(emitted):
    table = emitted["rom_cost_table"]
    rates = {
        _param(table, f"engine.{f}.lanes.default")
        * _param(table, f"engine.{f}.work_per_lane_cycle")
        for f in FAMILIES
    }
    assert len(rates) == 1, (
        "the analytical model prices all arithmetic at one roof, so every "
        f"engine family must carry one rate; got {rates}"
    )


def test_rom_weight_path_reproduces_the_analytical_rom_bandwidth(anchor, emitted):
    table = emitted["rom_cost_table"]
    arrays = _param(table, "rom.arrays.default")
    bpc = _param(table, "rom.bytes_per_cycle_per_array")
    clock = _param(table, "clock.frequency_hz")
    achieved = arrays * bpc * clock
    assert achieved == pytest.approx(anchor.rom_weight_read_bytes_s, rel=2e-5), (
        "the derived ROM array no longer delivers the design point's "
        "peak_weight_read_bytes_s"
    )
    # The burst must be an exact multiple of the per-cycle rate, or the cycle
    # model's ceil() silently throws bandwidth away.
    assert _param(table, "rom.transaction_bytes") % bpc == 0


def test_hbm_channel_rate_is_shared_and_reproduces_both_design_points(
    anchor, emitted
):
    rom_t, hbm_t = emitted["rom_cost_table"], emitted["hbm_cost_table"]
    bpc = _param(rom_t, "hbm.bytes_per_cycle_per_channel")
    assert bpc == _param(hbm_t, "hbm.bytes_per_cycle_per_channel"), (
        "the two design points buy the same HBM3E channel; only the count may "
        "differ"
    )
    clock = _param(rom_t, "clock.frequency_hz")
    assert _param(rom_t, "hbm.channels.default") * bpc * clock == pytest.approx(
        anchor.rom_kv_read_bytes_s, rel=1e-12
    )
    assert _param(hbm_t, "hbm.channels.default") * bpc * clock == pytest.approx(
        anchor.hbm_memory_bytes_s, rel=1e-12
    )
    tx = _param(rom_t, "hbm.transaction_bytes")
    assert tx / bpc == int(tx / bpc), "the HBM burst must quantise losslessly"


def test_memory_latencies_trace_to_the_analytical_latency_primitives(
    anchor, emitted
):
    table = emitted["rom_cost_table"]
    clock = _param(table, "clock.frequency_hz")
    assert _param(table, "sram.read_latency_cycles") == round(
        anchor.latency("sram_access_s") * clock
    )
    assert _param(table, "hbm.read_latency_cycles") == round(
        anchor.kv_round_trip_s * clock
    )
    assert _param(table, "rom.read_latency_cycles") == round(
        anchor.global_traversal_s * clock
    )
    for family in FAMILIES:
        assert _param(table, f"engine.{family}.fixed_latency_cycles") == round(
            anchor.array_pass_boundary_s * clock
        )


def test_no_emitted_parameter_claims_measured_or_characterized_evidence(emitted):
    """D2: nothing derived may be graded characterized or measured."""
    for key in ("rom_cost_table", "hbm_cost_table"):
        for name, entry in emitted[key]["parameters"].items():
            assert entry["provenance"] == "assumed", (
                f"{key}:{name} claims provenance {entry['provenance']!r}; a "
                f"derived machine may not claim measured evidence"
            )
            assert entry["analytical_grade"] in {"derived", "assumed"}, (
                f"{key}:{name} carries grade {entry['analytical_grade']!r}"
            )
            assert entry["note"], f"{key}:{name} carries no derivation"


def test_capability_technology_view_is_outside_the_characterized_set(emitted):
    """So every structural count is graded `assumed` with no code change."""
    from runtime.cycle.machine import CHARACTERIZED_TECHNOLOGY_VIEWS

    for key in ("rom_capability", "hbm_capability"):
        view = emitted[key]["technology_view"]
        assert view == TECHNOLOGY_VIEW
        assert view not in CHARACTERIZED_TECHNOLOGY_VIEWS


def test_both_machines_report_an_assumed_provenance_class(emitted):
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
    )
    assert report["rom_provenance_classes"] == ["assumed"]
    assert report["hbm_provenance_classes"] == ["assumed"]


# ---------------------------------------------------------------------------
# 4.  D5: the anchor is the pair the headline comes from
# ---------------------------------------------------------------------------
def test_the_anchor_is_the_published_headline_pair(anchor, emitted):
    art = emitted["artifact"]["anchor"]
    assert art["rom_design"] == ROM_DESIGN
    assert art["hbm_design"] == HBM_DESIGN
    assert art["published_ratio"] == pytest.approx(5.6392842689793605, rel=1e-12)
    assert art["iso_area"], "the anchor must be within 2 percent of iso-area"
    assert anchor.rom["token_slots"] == 1.0 and anchor.hbm["token_slots"] == 1.0, (
        "the aggregation to one logical device is only exact at token_slots = 1"
    )


def test_the_artifact_names_every_inexpressible_term(emitted):
    kinds = {(r["term"], r["kind"]) for r in emitted["artifact"]["residuals"]}
    assert ("link_latency", "structurally_inexpressible") in kinds, (
        "the cycle model builds no fabric on SINGLE_CHIP; the artifact must "
        "say so rather than approximate the analytical link term"
    )
    assert ("compute", "work_disagreement") in kinds
    assert ("weight_read", "sweep_versus_touched") in kinds
    assert ("step_time", "combination_rule") in kinds


# ---------------------------------------------------------------------------
# 5.  D3: the measured evidence is untouched
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", [
    "configs/hardware/abi3_cost_sky130_rom_v2.json",
    "configs/hardware/abi3_cost_asap7_v2.json",
    "configs/hardware/abi3_capability/rom_qwen3.json",
    "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
])
def test_shipped_characterized_evidence_is_byte_identical_to_head(path):
    committed = subprocess.run(
        ["git", "show", f"HEAD:{path}"], cwd=REPO, capture_output=True,
    )
    assert committed.returncode == 0, committed.stderr.decode()
    on_disk = (REPO / path).read_bytes()
    assert hashlib.sha256(on_disk).hexdigest() == hashlib.sha256(
        committed.stdout
    ).hexdigest(), (
        f"{path} carries characterized RTL or physical evidence and must "
        f"survive the derived-machine work untouched"
    )


def test_the_emitted_tables_do_not_collide_with_a_shipped_one():
    shipped = {
        p.name for p in (REPO / "configs/hardware").glob("abi3_cost_*.json")
        if TECHNOLOGY_VIEW not in p.name
    }
    assert ROM_TABLE.name not in shipped and HBM_TABLE.name not in shipped
    assert ROM_TABLE.name.startswith("abi3_cost_"), (
        "load_cost_table refuses a file without the reserved prefix"
    )


# ---------------------------------------------------------------------------
# 6.  The deployment-side half of the comparison
# ---------------------------------------------------------------------------
SHIPPED_ROM_DEPLOYMENT = REPO / "build/abi3/qwen3-8b-rom-rowfold-v1"
SHIPPED_HBM_DEPLOYMENT = REPO / "build/abi3/qwen3-8b-hbm-exact8k-b1-lane0"


@pytest.mark.skipif(
    not (SHIPPED_ROM_DEPLOYMENT.exists() and SHIPPED_HBM_DEPLOYMENT.exists()),
    reason="the shipped Qwen deployments are not built in this tree",
)
def test_the_audit_catches_the_shipped_pairs_tile_shape_divergence(emitted):
    """A machine file cannot fix a deployment-side compute advantage.

    tile_cols and issue_window are SCHEDULE fields.  The shipped pair caps the
    tensor engine at 8192 columns on the ROM side and 512 on the HBM side, so
    a comparison run on those two deployments is not a comparison of machines
    however carefully the machines are matched.  The audit must say so.
    """
    lanes = emitted["rom_capability"]["engines"]["tensor"]["lanes"]
    report = audit_deployments(SHIPPED_ROM_DEPLOYMENT, SHIPPED_HBM_DEPLOYMENT,
                               lanes=lanes)
    assert not report["column_group_spans_match"]
    assert (report["rom"]["max_column_group_span"]
            > report["hbm"]["max_column_group_span"])
    assert "NOT COMPARABLE" in report["verdict"]
    # The ROM/HBM role is a deployment property, not a machine one:
    # StorageClass.ROM is 3.
    assert 3 in report["rom"]["storage_class_counts"]
    assert 3 not in report["hbm"]["storage_class_counts"]
    assert report["storage_classes_differ_as_expected"]


# ---------------------------------------------------------------------------
# 7.  D6: the reconciliation arithmetic
# ---------------------------------------------------------------------------
def _synthetic_run(*, cycles, clock, compute_cycles, tensor_cycles,
                   rom_busy, rom_units, hbm_busy, hbm_units,
                   rom_bytes_read, hbm_read, hbm_written, weight_bytes_touched):
    return {
        "timing": {
            "total_cycles": cycles, "clock_frequency_hz": clock,
            "seconds": cycles / clock, "compute_cycles": compute_cycles,
            "link_cycles": 0,
        },
        "engines": {"tensor": {"compute_bound_cycles": tensor_cycles}},
        "memory": {
            "rom": {"busy_cycles": rom_busy,
                    "structure": {"units": rom_units, "ports_per_unit": 1}},
            "hbm": {"busy_cycles": hbm_busy,
                    "structure": {"units": hbm_units, "ports_per_unit": 1}},
        },
        "counters": {"architectural": {
            "rom.bytes_read": rom_bytes_read, "hbm.bytes_read": hbm_read,
            "hbm.bytes_written": hbm_written, "instructions.retired": 2104,
        }},
        "tiling": {"by_family": {"tensor": {
            "memory_traffic": {"bytes_touched": weight_bytes_touched}}}},
    }


def test_store_wall_time_divides_busy_cycles_by_units_and_ports():
    """busy_cycles is summed over units, so a per-term wall clock must divide."""
    from tools.derive_cycle_machine import _store_wall_seconds

    run = _synthetic_run(
        cycles=1000, clock=1e9, compute_cycles=100, tensor_cycles=50,
        rom_busy=552088, rom_units=16, hbm_busy=33271977, hbm_units=160,
        rom_bytes_read=1, hbm_read=1, hbm_written=1, weight_bytes_touched=1,
    )
    assert _store_wall_seconds(run, "rom") == pytest.approx(552088 / 16 / 1e9)
    assert _store_wall_seconds(run, "hbm") == pytest.approx(33271977 / 160 / 1e9)


def test_reconciliation_reports_a_structurally_zero_link_term(anchor):
    from tools.derive_cycle_machine import reconcile

    run = _synthetic_run(
        cycles=359850, clock=1e9, compute_cycles=105308, tensor_cycles=57764,
        rom_busy=552088, rom_units=16, hbm_busy=33271977, hbm_units=160,
        rom_bytes_read=15145273784, hbm_read=2508914688,
        hbm_written=1222713344, weight_bytes_touched=16386630404,
    )
    report = reconcile(anchor, run, run)
    rom = report["targets"]["rom"]
    assert rom["terms"]["link_latency"]["cycle_s"] == 0.0
    assert rom["terms"]["link_latency"]["analytical_s"] > 0
    assert "STRUCTURALLY ZERO" in rom["terms"]["link_latency"]["note"]
    # The ROM weight path is two separate unit pools, so its occupancy is read
    # off the ROM class directly and must reproduce the analytical term.
    assert rom["terms"]["weight_read"]["cycle_s"] == pytest.approx(
        anchor.rom["component_times_s"]["weight_read"], rel=2e-3
    ), "the derived ROM array no longer reproduces the analytical weight_read term"


def test_headline_offers_the_like_for_like_ratio_pair(anchor):
    from tools.derive_cycle_machine import reconcile

    run = _synthetic_run(
        cycles=359850, clock=1e9, compute_cycles=105308, tensor_cycles=57764,
        rom_busy=552088, rom_units=16, hbm_busy=33271977, hbm_units=160,
        rom_bytes_read=15145273784, hbm_read=2508914688,
        hbm_written=1222713344, weight_bytes_touched=16386630404,
    )
    report = reconcile(anchor, run, run)
    head = report["headline"]
    assert head["analytical_ratio"] == pytest.approx(5.6392842689793605, rel=1e-12)
    # Removing the link term from both analytical steps is the comparison the
    # cycle model can actually be held to.
    rom_link = anchor.rom["component_times_s"]["link_latency"]
    hbm_link = anchor.hbm["component_times_s"]["link_latency"]
    assert head["analytical_ratio_with_link_removed_from_both"] == pytest.approx(
        (anchor.hbm["step_time_s"] - hbm_link)
        / (anchor.rom["step_time_s"] - rom_link), rel=1e-12
    )


def test_binding_regime_is_compared_only_over_expressible_terms(anchor):
    """D6's headline test, made checkable.

    The analytical ROM point is link_latency-bound and the cycle model has no
    link term on a single chip, so comparing the two binding constraints
    directly is a category error.  Over the three terms both models express,
    the analytical ROM point is kv_read-bound and the analytical GPU point is
    weight_read-bound; those are the claims the cycle model can be held to.
    """
    from tools.derive_cycle_machine import reconcile

    run = _synthetic_run(
        cycles=359850, clock=1e9, compute_cycles=105308, tensor_cycles=57764,
        rom_busy=552088, rom_units=16, hbm_busy=33271977, hbm_units=160,
        rom_bytes_read=15145273784, hbm_read=2508914688,
        hbm_written=1222713344, weight_bytes_touched=16386630404,
    )
    report = reconcile(anchor, run, run)
    rom = report["targets"]["rom"]["binding_regime"]
    assert rom["analytical_over_all_five_terms"] == "link_latency"
    assert rom["analytical_over_expressible_terms"] == "kv_read"
    assert "link_latency" not in {rom["analytical_over_expressible_terms"],
                                  rom["cycle"]}
    hbm = report["targets"]["hbm"]["binding_regime"]
    assert hbm["analytical_over_expressible_terms"] == "weight_read"


def _tensor_cycles(depth: int, tile_depth: int, rate: float,
                   scale: float = 2.0, tile_issue: int = 1) -> int:
    """Mirror of the tensor branch of ``runtime.cycle.model._compute_cycles``.

    Kept as a local mirror deliberately: this test is about the QUANTISATION,
    and reading the quantisation out of the model under test would make the
    test agree with whatever the model does.
    """

    full, tail = divmod(depth, tile_depth)
    cycles = full * max(math.ceil(tile_depth * scale / rate), tile_issue)
    if tail:
        cycles += max(math.ceil(tail * scale / rate), tile_issue)
    return cycles


#: ``ceil(2048*2/w) == 16 * ceil(128*2/w)`` holds only on this half-open
#: interval.  Below it the two deployments cost the same for a different
#: reason; above it they diverge and the ROM side is always the cheaper.
TENSOR_PARITY_BAND = (256.0, 4096.0 / 15.0)


def test_the_two_deployments_cost_the_same_tensor_work_only_inside_a_narrow_band(
    emitted,
):
    """The pair's tensor comparability is a coincidence, and it is a fragile one.

    The compiled ROM deployment carries ``tile_depth`` 2,048 and the HBM one
    128.  Per unit of contraction work those two shapes cost the same number of
    cycles only while ``ceil(2048 * work_units_per_mac / rate)`` equals
    ``16 * ceil(128 * work_units_per_mac / rate)``, which is true on a band
    about 6.7% wide.  The derived machine happens to sit inside it.

    Outside the band the two deployments are NOT charged alike for identical
    arithmetic, and the direction is not neutral: at rate 240 the ROM
    deployment costs 0.5625x the HBM one for the same work.  That is a 1.78x
    advantage handed to the ROM side by a schedule shape, exactly the class of
    defect ``assert_comparable`` exists to remove from the machine files -- so
    it must not be allowed to reappear from the deployment side unremarked.
    """

    rate = emitted["rom_cost_table"]["parameters"][
        "engine.tensor.work_per_lane_cycle"
    ]["value"]
    low, high = TENSOR_PARITY_BAND
    assert low <= rate < high, (
        f"the derived tensor rate {rate} has left the parity band "
        f"[{low}, {high}); the ROM and HBM deployments no longer cost the same "
        "for identical tensor work, and the audit does not test tile_depth"
    )

    depth = 4096
    rom = _tensor_cycles(depth, 2048, rate)
    hbm = _tensor_cycles(depth, 128, rate)
    assert rom == hbm, (rate, rom, hbm)

    # And the fragility itself, so nobody reads the equality as structural.
    outside = _tensor_cycles(depth, 2048, 240.0), _tensor_cycles(depth, 128, 240.0)
    assert outside[0] < outside[1], (
        "at a rate below the band the ROM deployment must be the cheaper side; "
        "if this ever fails the asymmetry has changed direction, which is a "
        "bigger finding than the one this test was written for"
    )
    assert outside[0] / outside[1] == pytest.approx(0.5625, rel=1e-6)
