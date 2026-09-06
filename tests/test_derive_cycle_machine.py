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
import pathlib
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
    DEFAULT_HBM_DESIGN,
    DEFAULT_ROM_DESIGN,
    DEFAULT_TECHNOLOGY,
    DEPLOYMENT_AUDIT_ALLOWLIST,
    FAMILIES,
    KV_PATH_ALLOWLIST,
    SCHEDULE_TILE_FIELDS,
    SHIPPED_DEPLOYMENTS,
    TECHNOLOGY_VIEW,
    WEIGHT_PATH_ALLOWLIST,
    allowlist_for,
    assert_comparable,
    audit_deployments,
    build,
    canonical,
    decode_request_symbols,
    load_anchor,
    survey_deployment,
    tensor_parity_band,
)

#: Taken from the generator, never re-typed.  These tests judge the files the
#: generator emits, and the emitted files live at the anchor's paths, so a
#: literal here can only ever disagree with the thing under test -- which is
#: how the anchor move of section 13 item 24 was caught by twelve red tests
#: rather than by one.  The anchor's own identity is checked against the
#: analytical artifact in ``test_the_anchor_is_the_published_headline_pair``.
ROM_DESIGN = DEFAULT_ROM_DESIGN
HBM_DESIGN = DEFAULT_HBM_DESIGN

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


def test_matrix_check_reads_the_files_the_c2_gate_reads(tmp_path):
    """--check must open the pair artifact, not only the emitted config files.

    Until this was pinned, ``--matrix --check`` compared the four emitted
    capability and cost-table files per cell and stopped.  A pair artifact
    whose ``deployment_audit.comparable`` no longer matched a fresh derivation
    passed the check untouched -- the check that vouches for gate C2's evidence
    never opened that evidence.  This test edits the verdict on disk, requires
    the check to fail, and restores the file.
    """
    path = next(
        p for p in PAIR_ARTIFACTS
        if json.loads(p.read_text())["deployment_audit"]["comparable"] is False
    )
    original = path.read_text()
    body = json.loads(original)
    body["deployment_audit"]["comparable"] = True
    try:
        path.write_text(json.dumps(body, indent=2))
        proc = subprocess.run(
            [sys.executable, "tools/derive_cycle_machine.py",
             "--matrix", "--check"],
            cwd=REPO, capture_output=True, text=True,
        )
        assert proc.returncode != 0, (
            "--matrix --check passed over a pair artifact whose verdict a "
            "fresh derivation does not produce"
        )
        assert path.name in proc.stderr, proc.stderr
    finally:
        path.write_text(original)


# ---------------------------------------------------------------------------
# 2.  D1: the two machines are one machine outside the weight path
# ---------------------------------------------------------------------------
def test_the_two_machines_differ_only_inside_the_weight_path(anchor, emitted):
    """...and inside the KV path exactly when the two points disagree on it.

    ``allowlist_for`` is the set the generator itself asserts against, and it
    is anchor-dependent: the weight-path entries always apply, the KV-path
    entries only when ``points[ROM].kv_store != points[GPU].kv_store``.  The
    test reads that function rather than a fixed set, because a fixed set is
    either too narrow (it fails on a legitimate anchor) or too wide (it hides
    a divergence on an anchor that cannot have one) -- and asserts the
    conditional itself, so the KV entries cannot be permitted on an anchor
    whose two points agree.
    """
    allowlist = allowlist_for(anchor)
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
        allowlist=allowlist,
    )
    assert report["parameters_compared"] == 114
    assert set(report["permitted_differences"]) <= set(allowlist)
    assert set(WEIGHT_PATH_ALLOWLIST) <= set(allowlist)
    kv_split = anchor.rom_kv_store != anchor.hbm_kv_store
    assert (set(KV_PATH_ALLOWLIST) <= set(allowlist)) is kv_split, (
        "the KV-path allowlist must apply exactly when the two design points "
        f"disagree on kv_store (rom {anchor.rom_kv_store!r}, hbm "
        f"{anchor.hbm_kv_store!r})"
    )
    # Every allowlist entry must actually be used.  An allowlist that permits
    # more than the emit needs is an allowlist that will one day hide a real
    # divergence.
    assert report["allowlist_unused"] == [], (
        "the allowlist permits differences the emit does not "
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


def test_shared_parameters_resolve_from_the_same_origin(anchor, emitted):
    """A value that agrees today but arrives from two places diverges tomorrow.

    The shipped pair has exactly this defect: ``rom_qwen3`` advertises no SRAM
    port count so it falls to its cost table's 1, while
    ``hbm_sram_single_chip`` advertises 2.
    """
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
        allowlist=allowlist_for(anchor),
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
    """Exact but for the one integer the cost table is allowed to round.

    ``rom.bytes_per_cycle_per_array`` must be a whole number of bytes per
    cycle, so the reproduction can only ever be exact to that rounding.  The
    band is COMPUTED from the rounding rather than typed: rounding to nearest
    moves the rate by at most half a byte per cycle per array, so the relative
    error is bounded by ``0.5 / exact_bytes_per_cycle_per_array``.  A typed
    tolerance is tuned to one anchor and silently either passes a real error or
    fails a legal rounding on the next one -- the previous 2e-5 was the first,
    and it failed on the anchor move of section 13 item 24 for no defect.
    """
    table = emitted["rom_cost_table"]
    arrays = _param(table, "rom.arrays.default")
    bpc = _param(table, "rom.bytes_per_cycle_per_array")
    clock = _param(table, "clock.frequency_hz")
    achieved = arrays * bpc * clock
    target = anchor.rom_weight_read_bytes_s
    exact_bpc = target / (arrays * clock)
    assert bpc == round(exact_bpc), (
        f"rom.bytes_per_cycle_per_array {bpc} is not {exact_bpc} rounded"
    )
    bound = 0.5 / exact_bpc
    assert abs(achieved - target) / target <= bound + 1e-15, (
        "the derived ROM array no longer delivers the design point's "
        f"peak_weight_read_bytes_s: {achieved} against {target}, relative "
        f"error {abs(achieved - target) / target:.3e} over the rounding bound "
        f"{bound:.3e}"
    )
    # ...and the rounding is declared, not silent.
    kinds = {(r["term"], r["kind"]) for r in emitted["artifact"]["residuals"]}
    assert ("weight_read", "integer_quantisation") in kinds
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
    assert _param(hbm_t, "hbm.channels.default") * bpc * clock == pytest.approx(
        anchor.hbm_memory_bytes_s, rel=1e-12
    )
    # The ROM side's KV rate is carried by whichever store the design point
    # says holds KV.  Asserting the HBM product unconditionally would pass only
    # on an HBMKV point and would say nothing at all on an SRAMKV one -- and
    # the anchor moved from one to the other (section 13 item 24).
    if anchor.rom_kv_store == "hbm":
        assert _param(rom_t, "hbm.channels.default") * bpc * clock == (
            pytest.approx(anchor.rom_kv_read_bytes_s, rel=1e-12)
        )
    else:
        assert anchor.rom_kv_store == "sram", anchor.rom_kv_store
        ports = (
            _param(rom_t, "sram.banks.default")
            * _param(rom_t, "sram.ports_per_bank.default")
        )
        rate = ports * _param(rom_t, "sram.bytes_per_cycle_per_port") * clock
        # The port rate is an integer number of bytes per cycle, so the
        # reproduction is exact only to that quantisation; the artifact
        # declares the residual and this is its band.
        assert rate == pytest.approx(anchor.rom_kv_read_bytes_s, rel=3e-3), (
            "the derived SRAM port pool no longer delivers the design point's "
            "KV read rate"
        )
        assert _param(rom_t, "hbm.channels.default") == 1, (
            "a design point that buys no HBM (area_fractions.hbm_phy 0.0) must "
            "declare the one inert channel the cost-table schema requires, not "
            "a provisioned pool"
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


def test_both_machines_report_an_assumed_provenance_class(anchor, emitted):
    report = assert_comparable(
        emitted["rom_capability"], ROM_TABLE,
        emitted["hbm_capability"], HBM_TABLE,
        allowlist=allowlist_for(anchor),
    )
    assert report["rom_provenance_classes"] == ["assumed"]
    assert report["hbm_provenance_classes"] == ["assumed"]


# ---------------------------------------------------------------------------
# 4.  D5: the anchor is the pair the headline comes from
# ---------------------------------------------------------------------------
def test_the_anchor_is_the_published_headline_pair(anchor, emitted):
    """The anchor is the study's own choice on both sides, not this repo's.

    Checked against ``analytical.json`` rather than against literals: the ROM
    side must be the study's batch-1 recommendation for the model, and the GPU
    side must be the artifact's OWN iso-area comparator for that ROM design.
    Gate G3's budget is frozen on the same pair, so a literal here would let
    the two drift apart silently -- which is exactly what section 13 item 24
    records happening.
    """
    body = json.loads((REPO / DEFAULT_ANALYTICAL).read_text())
    model = next(
        m for m in body["design_selection"]["models"] if m["model"] == "Qwen3-8B"
    )
    recommended = next(
        r["recommended"]["design"] for r in model["batch_regimes"]
        if int(r["batch_size"]) == 1
    )
    assert ROM_DESIGN == recommended, (
        f"the anchor's ROM side {ROM_DESIGN} is not the study's own batch-1 "
        f"recommendation {recommended}"
    )
    iso = next(
        c["iso_area_gpu_design"] for c in body["comparisons"]
        if int(c.get("batch_size", -1)) == 1 and c["rom_design"] == ROM_DESIGN
    )
    assert HBM_DESIGN == iso, (
        f"the anchor's GPU side {HBM_DESIGN} is not the artifact's own "
        f"iso-area comparator {iso} for that ROM design"
    )

    art = emitted["artifact"]["anchor"]
    assert art["rom_design"] == ROM_DESIGN
    assert art["hbm_design"] == HBM_DESIGN
    assert art["published_ratio"] == pytest.approx(
        anchor.rom["per_user_tokens_s"] / anchor.hbm["per_user_tokens_s"],
        rel=1e-12,
    )
    # The iso-area convention picks N GPU dies so the silicon MATCHES, and the
    # comparator is the artifact's own.  It does not always land within 2%: at
    # this anchor it is 4,800 mm2 against 4,075, so the study spends 17.8% MORE
    # silicon on the comparator than on the ROM part.  What must never happen
    # is the other direction -- a comparator with LESS silicon flatters the
    # thesis, and rule R14 says take the choice that costs the ROM side.  The
    # exact-iso flag is recorded either way and read here rather than asserted.
    assert art["iso_area"] is (abs(art["iso_area_ratio"] - 1) < 0.02)
    assert art["iso_area_ratio"] <= 1.0 + 1e-12, (
        f"the comparator has LESS silicon than the ROM part "
        f"({art['hbm_area_mm2']} against {art['rom_area_mm2']} mm2); the "
        "iso-area convention would then be applied FOR the thesis, which R14 "
        "forbids"
    )
    # The collapse of N devices into one logical device divides every RATE by
    # the point's own token_slots.  At one slot that division is the identity;
    # above one slot it is a real modelling step, and the artifact must DECLARE
    # it rather than let a reader assume the aggregate was carried whole.
    slots = anchor.rom["token_slots"]
    assert anchor.hbm["token_slots"] == 1.0
    if slots > 1.0:
        residual = next(
            (r for r in emitted["artifact"]["residuals"]
             if r["kind"] == "slot_serialisation"), None,
        )
        assert residual is not None, (
            f"the ROM point traverses {slots:g} slots, so the collapse divides "
            "its aggregate rates; the artifact must carry the "
            "slot_serialisation residual that says so"
        )
        assert f"{slots:g} slot" in residual["note"]
    assert anchor.rom_weight_read_bytes_s == pytest.approx(
        anchor.rom_peak_weight_read_bytes_s / slots, rel=1e-12
    )
    # ...and the collapse is checked against the point's own published times,
    # not assumed, by the generator itself.
    anchor.assert_collapse_is_exact()


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
# 6.  C2: the deployment-side half of the comparison
# ---------------------------------------------------------------------------
SHIPPED_ROM_DEPLOYMENT = REPO / "build/abi3/qwen3-8b-rom-rowfold-v1"
SHIPPED_HBM_DEPLOYMENT = REPO / "build/abi3/qwen3-8b-hbm-exact8k-b1-lane0"
SHIPPED_ROM_CYCLE_ARTIFACT = (
    REPO / "results/abi3/cycle/qwen3_rom_exact8k_b1_asap7_decode_pos8000_rowfold_depthfix_v1.json"
)
SHIPPED_HBM_CYCLE_ARTIFACT = (
    REPO / "results/abi3/cycle/qwen3_hbm_exact8k_b1_asap7_decode_pos8000_rowfold_v1.json"
)

needs_shipped_pair = pytest.mark.skipif(
    not (SHIPPED_ROM_DEPLOYMENT.exists() and SHIPPED_HBM_DEPLOYMENT.exists()),
    reason="the shipped Qwen deployments are not built in this tree",
)


def _shipped_machine(emitted):
    """The derived N5 machine, which both sides of the pair share (D1)."""
    from runtime.abi3.capability import Capability
    from runtime.cycle.machine import MachineModel, load_cost_table

    return MachineModel(
        Capability.from_dict(emitted["rom_capability"]), load_cost_table(ROM_TABLE)
    )


@pytest.fixture(scope="module")
def shipped_audit(emitted):
    if not (SHIPPED_ROM_DEPLOYMENT.exists() and SHIPPED_HBM_DEPLOYMENT.exists()):
        pytest.skip("the shipped Qwen deployments are not built in this tree")
    return audit_deployments(
        SHIPPED_ROM_DEPLOYMENT, SHIPPED_HBM_DEPLOYMENT,
        symbols=decode_request_symbols(1, 8192), machine=_shipped_machine(emitted),
    )


def _asymmetry(report, family, field):
    hits = [a for a in report["asymmetries"]
            if a["family"] == family and a["field"] == field]
    assert len(hits) == 1, f"{family}.{field}: {hits}"
    return hits[0]


REGISTRATIONS = [
    (base, entry)
    for base, entries in sorted(SHIPPED_DEPLOYMENTS.items())
    for entry in entries
]


@pytest.mark.parametrize(
    "base,entry", REGISTRATIONS,
    ids=[f"{pathlib.Path(b).stem}:{e['model_id']}" for b, e in REGISTRATIONS],
)
def test_every_registered_deployment_is_pinned_by_digest(base, entry):
    """The audit's subject is pinned by digest, not by directory name.

    One capability record can serve more than one model, so the table's value
    is a list and the model id selects within it.  Every registration must name
    a deployment that really carries the capability's own digest -- a
    registration pointing at a bundle lowered for a different target would make
    the gate pass on the wrong artifact -- and every cited evidence file must
    exist.
    """
    from runtime.abi3.capability import Capability

    root = REPO / entry["root"]
    if not (root / "deployment.json").exists():
        pytest.skip(f"{entry['root']} is not built in this tree")
    manifest = json.loads((root / "deployment.json").read_text())
    assert manifest["deployment_sha256"] == entry["deployment_sha256"], (
        f"{root.name} is not the deployment the cited evidence names; "
        "rebuild products go stale under evidence"
    )
    assert manifest["model_id"] == entry["model_id"]
    expected = Capability.from_dict(json.loads((REPO / base).read_text())).digest
    assert manifest["capability_digest"] == expected, (
        f"{root.name} is registered under {base} but was lowered against a "
        "different capability"
    )
    for path in entry["evidence"]:
        cited = REPO / path.split(" ")[0]
        if cited.suffix == ".json" or "/" in path.split(" ")[0]:
            assert cited.exists(), f"{path} is cited but absent"


def test_the_audit_catches_the_shipped_pairs_tile_shape_divergence(shipped_audit):
    """A machine file cannot fix a deployment-side compute advantage.

    Every field the cycle model's tile mapping reads is a SCHEDULE field.  The
    shipped pair differs in all four tile fields of the tensor family -- depth
    2048 against 128, rows 128 against 64, and a column group of 512 x 16
    against 128 x 4 -- and in the DMA tile shape, so a comparison run on those
    two deployments is not a comparison of machines however carefully the
    machines are matched.  The audit must say so, field by field, with the
    direction each difference favours.
    """
    report = shipped_audit
    assert report["comparable"] is False
    assert report["verdict"].startswith("NOT COMPARABLE")
    assert "tile_depth 2048 vs 128" in report["verdict"]
    assert "tile_rows 128 vs 64" in report["verdict"]
    assert report["allowlist"] == {} and DEPLOYMENT_AUDIT_ALLOWLIST == {}

    depth = _asymmetry(report, "tensor", "tile_depth")
    assert (depth["rom_value"], depth["hbm_value"]) == (2048, 128)
    assert depth["cost_bearing"] and not depth["allowlisted"]
    rows = _asymmetry(report, "tensor", "tile_rows")
    assert (rows["rom_value"], rows["hbm_value"]) == (128, 64)
    assert rows["favours"] == "neither", (
        "at batch-1 decode every tensor operator has one row; if tile_rows "
        "now moves the tensor charge the request or the lowering has changed"
    )
    cols = _asymmetry(report, "tensor", "tile_cols")
    assert (cols["rom_value"], cols["hbm_value"]) == (512, 128)
    window = _asymmetry(report, "tensor", "issue_window")
    assert (window["rom_value"], window["hbm_value"]) == (16, 4)
    # The column group is what caps the tensor engine at batch 1, and either
    # field alone would lift the HBM side's cap: both favour ROM by the same
    # 2x the effective width says.
    for a in (cols, window):
        assert a["favours"] == "rom"
        assert a["effect_x"] == pytest.approx(2.0, rel=1e-2)
    assert report["rom"]["effective_tensor_width_caps"] == [1024]
    assert report["hbm"]["effective_tensor_width_caps"] == [512]
    assert not report["column_group_spans_match"]
    tensor = report["families"]["tensor"]
    assert tensor["useful_work"]["rom"] == tensor["useful_work"]["hbm"]
    assert tensor["cycles"]["favours"] == "rom"
    # The total contraction advantage is the COMPOSITION of the two
    # cost-bearing tile differences: the column-group cap (the effective
    # tensor width) times the reduction-depth quantisation the parity band
    # reports.  Asserting the product rather than a number keeps the claim
    # true across an anchor move: at the superseded point the depth term was
    # exactly 1.0 by coincidence of the rate and the total was the width's
    # 2.0x; at this anchor the depth term is 1.091x and the total is 2.181x.
    depth_band = report["tensor_parity_band"]
    assert tensor["cycles"]["magnitude_x"] == pytest.approx(
        cols["effect_x"] * depth_band["magnitude_x"], rel=1e-9
    ), (
        "the contraction advantage is no longer the column-group cap times "
        "the depth quantisation; one of the two is being counted twice or not "
        "at all"
    )
    if depth_band["parity"]:
        assert depth["favours"] == "neither"
    else:
        assert depth["favours"] == depth_band["favours"] == "rom", (
            "the reduction depth now moves the charge and the direction is "
            "not the ROM side's: that is a bigger finding than this test"
        )
    for key in ("tensor.tile_depth", "tensor.tile_rows", "tensor.tile_cols",
                "tensor.issue_window"):
        assert key in report["unexplained_asymmetries"]
    # The ROM/HBM role is a deployment property, not a machine one:
    # StorageClass.ROM is 3.
    assert 3 in report["rom"]["storage_class_counts"]
    assert 3 not in report["hbm"]["storage_class_counts"]
    assert report["storage_classes_differ_as_expected"]
    assert report["operators_unmatched"] == {"rom": [], "hbm": []}
    assert report["rom"]["static_walk"] == "complete"
    assert report["hbm"]["static_walk"] == "complete"


def test_the_audit_names_the_shipped_pairs_dma_tile_count_asymmetry(shipped_audit):
    """A DMA operator is charged once per tile, so the tile count IS the charge.

    The two DMA tile shapes, 128 x 64 against 64 x 128, cover the same area
    and so tile the KV scatters alike; on the two gathers the ROM shape pays
    twice the tiles of the HBM shape for the same bytes.  Both facts have to
    be in the report: the per-step total and the per-operator asymmetry, with
    its direction.
    """
    report = shipped_audit
    rows = _asymmetry(report, "dma", "tile_rows")
    cols = _asymmetry(report, "dma", "tile_cols")
    assert (rows["rom_value"], rows["hbm_value"]) == (128, 64)
    assert (cols["rom_value"], cols["hbm_value"]) == (64, 128)
    # Counterfactually each field alone moves the DMA charge 2x -- in
    # opposite directions.  That is why the per-step totals nearly cancel.
    assert rows["favours"] == "rom" and rows["effect_x"] == pytest.approx(2.0, rel=1e-3)
    assert cols["favours"] == "hbm" and cols["effect_x"] == pytest.approx(2.0, rel=1e-3)
    dma = report["families"]["dma"]
    assert dma["useful_work"]["rom"] == dma["useful_work"]["hbm"]
    assert dma["tiles"]["rom"] > dma["tiles"]["hbm"]
    assert dma["tiles"]["favours"] == "hbm"
    assert dma["cycles"]["rom"] == dma["tiles"]["rom"], (
        "at the derived DMA rate every tile is at the one-cycle issue floor"
    )
    gathers = [
        o for o in report["operator_asymmetries"]
        if o["family"] == "dma" and o["metric"] == "tiles_per_issue"
    ]
    assert gathers, "no per-operator DMA tile-count asymmetry was reported"
    big = next(o for o in gathers if o["operator"].startswith("DMA.GATHER (1x4096x1)"))
    assert (big["rom"], big["hbm"]) == (64, 32)
    assert big["favours"] == "hbm" and big["magnitude_x"] == 2.0
    per_tile = next(
        o for o in report["operator_asymmetries"]
        if o["metric"] == "payload_bytes_per_tile"
        and o["operator"].startswith("DMA.GATHER (1x4096x1)")
    )
    assert (per_tile["rom"], per_tile["hbm"]) == (128.0, 256.0)
    assert f"DMA.GATHER (1x4096x1) 64 vs 32 tiles per issue" in report["verdict"]
    assert f"{dma['tiles']['rom']:,} vs {dma['tiles']['hbm']:,}" in report["verdict"]


def test_the_parity_band_is_reported_for_the_pairs_actual_depths(shipped_audit, emitted):
    """The tensor parity is a coincidence of the rate, and the audit says where.

    The audit must report the band for the PAIR'S OWN depths at the MACHINE'S
    OWN rate -- not a band recorded once and carried.  At the superseded
    HBMKV-array-tensor-x4 anchor the rate was 265.372 and the (2048, 128) pair
    sat inside [256.0, 273.067), so the two depths cost the same per unit of
    depth.  At the re-frozen SRAMKV-array-pipeline-x5-romfill anchor the rate
    is 93.193 and the band is [93.091, 95.256): parity is GONE and the shape
    now favours the ROM side by 44/2048 against 3/128 = 1.0909x.  That is the
    finding this test exists to surface, so it is asserted, not smoothed.
    """
    band = shipped_audit["tensor_parity_band"]
    assert (band["rom_tile_depth"], band["hbm_tile_depth"]) == (2048, 128)
    rate = emitted["rom_cost_table"]["parameters"][
        "engine.tensor.work_per_lane_cycle"
    ]["value"]
    assert band["work_per_lane_cycle"] == rate
    # The band is a fact about the two depths and the rate, recomputed here
    # from the same primitive the audit used, so a band carried from a
    # previous anchor cannot pass.
    fresh = tensor_parity_band(2048, 128, rate)
    assert band["band"] == pytest.approx(fresh["band"], rel=1e-12)
    assert rate >= band["band"][0] and rate < band["band"][1]
    k_rom = band["cycles_per_full_depth_tile"]["rom"]
    k_hbm = band["cycles_per_full_depth_tile"]["hbm"]
    assert k_rom == math.ceil(2048 * band["work_units_per_mac"] / rate)
    assert k_hbm == math.ceil(128 * band["work_units_per_mac"] / rate)
    assert band["parity"] is ((k_rom / 2048) == (k_hbm / 128))
    if not band["parity"]:
        assert band["favours"] == ("rom" if k_rom / 2048 < k_hbm / 128 else "hbm")
        assert band["magnitude_x"] == pytest.approx(
            max(k_rom / 2048, k_hbm / 128) / min(k_rom / 2048, k_hbm / 128)
        )
    # ...and the same function says which side wins outside the band.
    below = tensor_parity_band(2048, 128, 240.0)
    assert below["parity"] is False and below["favours"] == "rom"
    assert below["magnitude_x"] == pytest.approx(32 / 18)
    assert 240.0 >= below["band"][0] and 240.0 < below["band"][1]
    # Equal depths are at parity at ANY rate, which is what the pair the C2
    # gate actually binds (the AM-E9 v2 lowering, 128 against 128) relies on.
    same = tensor_parity_band(128, 128, rate)
    assert same["parity"] is True and same["favours"] == "neither"
    assert same["band"][0] <= rate < same["band"][1]


def _params_from_cycle_artifact(body):
    from runtime.cycle.machine import EngineParams

    engines = body["machine"]["engines"]

    def params_for(family):
        e = engines[family]
        return EngineParams(
            family=family, lanes=int(e["lanes"]), queues=int(e["queues"]),
            queue_depth=int(e["queue_depth"]),
            max_outstanding=int(e["max_outstanding"]),
            work_per_lane_cycle=float(e["work_per_lane_cycle"]),
            fixed_latency_cycles=int(e["fixed_latency_cycles"]),
            bytes_per_cycle=float(e["bytes_per_cycle"]),
            minimum_cycles=int(e["minimum_cycles"]),
            tile_issue_cycles=int(e["tile_issue_cycles"]),
            tile_pipeline_depth=int(e["tile_pipeline_depth_default"]),
        )
    return params_for


@needs_shipped_pair
@pytest.mark.parametrize("root,artifact", [
    (SHIPPED_ROM_DEPLOYMENT, SHIPPED_ROM_CYCLE_ARTIFACT),
    (SHIPPED_HBM_DEPLOYMENT, SHIPPED_HBM_CYCLE_ARTIFACT),
], ids=["rom", "hbm"])
def test_the_static_survey_reproduces_the_cycle_models_own_tiling(root, artifact):
    """The audit's tile counts are the cycle model's, not a restatement.

    ``survey_deployment`` decomposes each operator with ``tile_mapping`` and
    counts its issues by walking the control stream.  Against the shipped
    cycle artifacts -- which timed these exact deployments through the
    functional device -- every family's operation count, tile count, useful
    and issued work must come out identical at the artifact's own request and
    lane counts.
    """
    from runtime.abi3.descriptors import Symbol

    body = json.loads(artifact.read_text())
    manifest = json.loads((root / "deployment.json").read_text())
    assert body["inputs"]["deployment_digest"] == manifest["deployment_sha256"], (
        f"{artifact.name} timed a different deployment than {root.name} holds"
    )
    symbols = {
        int(Symbol[name]): int(value)
        for name, value in body["inputs"]["request"]["symbols"].items()
    }
    survey = survey_deployment(
        root, symbols=symbols, params_for=_params_from_cycle_artifact(body)
    )
    assert survey["static_walk"] == "complete"
    traced = body["tiling"]["by_family"]
    assert set(survey["families"]) == set(traced)
    for family, got in survey["families"].items():
        want = traced[family]
        for metric in ("operations", "tiles", "useful_work", "issued_work"):
            assert got[metric] == want[metric], (family, metric, got[metric], want[metric])
        assert got["padding_fraction"] == pytest.approx(want["padding_fraction"], abs=2e-6)
        shapes = {(s["tile_rows"], s["tile_cols"], s["tile_depth"]) for s in want["tile_shapes"]}
        surveyed = {
            (o["schedule"]["tile_rows"], o["schedule"]["tile_cols"], o["schedule"]["tile_depth"])
            for o in survey["operators"] if o["family"] == family
        }
        assert surveyed == shapes, (family, surveyed, shapes)


def test_a_synthetic_pair_with_identical_schedules_is_comparable(tmp_path):
    """The conformance fixture lowered through ROM and through HBM.

    The two builds differ only in the weight object's storage class; every
    SCHEDULE is byte-identical.  That is the property the comparison protocol
    depends on, and the audit must return ``comparable`` for it -- with no
    asymmetry, every operator matched and the storage classes differing as
    the roles require.
    """
    from runtime.abi3.constants import StorageClass
    from runtime.abi3.fixture import build_fixture

    rom = build_fixture(storage_class=StorageClass.ROM).write(tmp_path / "rom")
    hbm = build_fixture(storage_class=StorageClass.HBM).write(tmp_path / "hbm")
    report = audit_deployments(rom, hbm, lanes=8, symbols=decode_request_symbols(1, 4))
    assert report["comparable"] is True
    assert report["verdict"].startswith("COMPARABLE")
    assert report["asymmetries"] == []
    assert report["unexplained_asymmetries"] == []
    assert report["operator_asymmetries"] == []
    assert report["operators_unmatched"] == {"rom": [], "hbm": []}
    assert len(report["operators"]) == 4
    assert report["column_group_spans_match"]
    assert report["storage_classes_differ_as_expected"]
    for family, row in report["families"].items():
        assert row["tiles"]["rom"] == row["tiles"]["hbm"], family
        assert row["tiles"]["favours"] == "neither"


def test_a_synthetic_pair_with_one_field_changed_is_not_comparable(tmp_path, monkeypatch):
    """One SCHEDULE field is enough, and the audit names it with its direction."""
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.constants import Major, StorageClass
    from runtime.abi3.fixture import build_fixture

    rom = build_fixture(storage_class=StorageClass.ROM).write(tmp_path / "rom")
    original = DeploymentBuilder.schedule

    def halve_tensor_depth(self, **kwargs):
        if kwargs.get("engine_family") == Major.TENSOR:
            kwargs["tile_depth"] //= 2
        return original(self, **kwargs)

    monkeypatch.setattr(DeploymentBuilder, "schedule", halve_tensor_depth)
    hbm = build_fixture(storage_class=StorageClass.HBM).write(tmp_path / "hbm")
    report = audit_deployments(rom, hbm, lanes=8, symbols=decode_request_symbols(1, 4))
    assert report["comparable"] is False
    assert report["unexplained_asymmetries"] == ["tensor.tile_depth"]
    a = _asymmetry(report, "tensor", "tile_depth")
    assert (a["rom_value"], a["hbm_value"]) == (8, 4)
    assert a["favours"] == "rom", "half the depth is twice the depth tiles"
    assert a["effect_x"] == pytest.approx(2.0)
    assert "tile_depth 8 vs 4" in report["verdict"]
    tensor = report["families"]["tensor"]
    assert tensor["tiles"]["rom"] * 2 == tensor["tiles"]["hbm"]


# ---------------------------------------------------------------------------
# 6b.  Every pair artifact carries a C2 verdict; absence is a failure
# ---------------------------------------------------------------------------
PAIR_ARTIFACTS = sorted((REPO / "results/derived").glob("*_machine_pair.json"))


@pytest.mark.parametrize("path", PAIR_ARTIFACTS, ids=[p.stem for p in PAIR_ARTIFACTS])
def test_every_pair_artifact_carries_a_deployment_audit_verdict(path):
    body = json.loads(path.read_text())
    audit = body["deployment_audit"]
    assert isinstance(audit["comparable"], bool)
    assert isinstance(audit["verdict"], str) and audit["verdict"]
    standalone = path.with_name(path.name.replace("_machine_pair.json", "_deployment_audit.json"))
    assert standalone.exists(), f"{standalone.name} was not emitted beside {path.name}"
    assert audit["full_report"] == str(standalone.relative_to(REPO))
    full = json.loads(standalone.read_text())
    # The embedded audit is the standalone one minus the per-operator survey.
    for key, value in audit.items():
        if key == "full_report":
            continue
        if key in ("rom", "hbm"):
            assert {k: v for k, v in full[key].items() if k != "operators"} == value
        else:
            assert full[key] == value, (
                f"{standalone.name} disagrees with the audit embedded in {path.name} at {key}"
            )
    assert audit["pair_id"] == body["pair_id"]
    model = body["pair_id"].split("__", 1)[0]
    rom_e9 = REPO / "build/abi3/qwen3-8b-rom-e9"
    hbm_e9 = REPO / "build/abi3/qwen3-8b-hbm-e9"
    if model != "qwen3-8b":
        # DeepSeek is red on both rungs, and the artifact must say which kind
        # of red it is rather than go quiet.  The Flash ARRAY cells bind a real
        # pair (rom_deepseek_v4_array_32 against hbm_sram_cluster_32) and fail
        # on what the audit finds -- or, while the static walk still refuses
        # the DeepSeek control stream, on the audit being uncarriable.  The
        # Flash WAFER and every Pro cell fail on absence: no Pro deployment
        # exists in any storage class, and the wafer rung's single-node GPU
        # comparator cannot be built.  Absence and unreadability are both
        # recorded failures, never skipped cells.
        assert audit["comparable"] is False
        assert audit["verdict"].startswith("NOT COMPARABLE")
        assert audit["reason"] in (
            "no deployment built",
            "not comparable",
            "audit could not be carried out",
        ), audit["reason"]
        return
    if not (rom_e9.exists() and hbm_e9.exists()):
        assert audit["comparable"] is False
        assert audit["reason"] == "no deployment built"
        return
    # AM-E9 v2 (commit b7441e8) unified the activation-buffer placement, so the
    # Qwen pair the cells bind is comparable.  What is asserted here is that
    # the cells bind THAT pair -- the tile-shape divergence the shipped
    # pre-AM-E9 bundles carried is still pinned, on the shipped roots, by
    # test_the_audit_catches_the_shipped_pairs_tile_shape_divergence.
    assert audit["comparable"] is True, audit["verdict"]
    assert audit["reason"] == "comparable"
    assert audit["deployments"]["rom"]["status"] == "bound"
    assert audit["deployments"]["hbm"]["status"] == "bound"
    registered = {
        e["model_id"]: e
        for e in SHIPPED_DEPLOYMENTS[
            "configs/hardware/abi3_capability/rom_qwen3.json"]
    }["qwen3-8b"]
    assert audit["deployments"]["rom"]["deployment_sha256"] == registered[
        "deployment_sha256"]
    assert not [a for a in audit["asymmetries"] if a["cost_bearing"]]


def test_the_c2_gate_fails_on_the_audits_evidence_not_on_absence():
    """The board must quote the verdict, not report a missing key."""
    from tools.check_redesign_gates import evaluate

    gates = json.loads((REPO / "configs/gates/redesign_gates.json").read_text())
    c2 = next(g for g in gates["gates"] if g["id"] == "C2")
    assert c2["evaluator"]["reason_field"] == "deployment_audit.verdict"
    result = evaluate(c2)
    assert result["status"] == "fail"
    assert "none has deployment_audit.comparable" not in result["why"], (
        "C2 is failing on absence again: " + result["why"]
    )
    # a5463e8 made C2 require every audited pair; the failure now counts the
    # artifacts that fail and names them with their own verdicts.
    assert "fail deployment_audit.comparable == True" in result["why"]
    assert "NOT COMPARABLE" in result["why"]
    # Every Qwen cell is comparable since the registration moved to the AM-E9
    # v2 bundles, so what keeps C2 red is DeepSeek, and the reason quoted has
    # to be DeepSeek's own -- absence on the Pro and Flash-wafer rungs, and the
    # Flash-array pair's audit on the array rungs.  The board must never go red
    # on a missing key.
    assert "deepseek" in result["why"]
    assert "qwen3-8b__" not in result["why"], (
        "a Qwen cell is failing C2 again: " + result["why"]
    )
    # The why line is truncated, so the per-cell verdicts are read from the
    # artifacts themselves: every failing cell is DeepSeek, and every one of
    # them states a recorded reason rather than a missing key.
    failing = [
        json.loads(path.read_text())
        for path in PAIR_ARTIFACTS
        if json.loads(path.read_text())["deployment_audit"]["comparable"] is False
    ]
    assert failing, "C2 is green; this test pins that it fails on evidence"
    for body in failing:
        assert not body["pair_id"].startswith("qwen3-8b")
        assert body["deployment_audit"]["verdict"].startswith("NOT COMPARABLE")


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


#: The counters of the anchor's own committed ROM cycle run
#: (``results/derived/n5_design_target_cycle/qwen3_n5_design_target_rom_run.json``,
#: batch 1 at POSITION_START 8000).  They are read from the record rather than
#: typed so that a re-timed anchor cannot leave these tests asserting against a
#: run nobody took.
ANCHOR_ROM_RUN = (
    REPO / "results/derived/n5_design_target_cycle"
    / "qwen3_n5_design_target_rom_run.json"
)


def _anchor_run():
    body = json.loads(ANCHOR_ROM_RUN.read_text())
    arch = body["counters"]["architectural"]
    return _synthetic_run(
        cycles=body["timing"]["total_cycles"],
        clock=body["timing"]["clock_frequency_hz"],
        compute_cycles=body["timing"]["compute_cycles"],
        tensor_cycles=body["engines"]["tensor"]["compute_bound_cycles"],
        rom_busy=body["memory"]["rom"]["busy_cycles"],
        rom_units=body["memory"]["rom"]["structure"]["units"],
        hbm_busy=body["memory"]["hbm"]["busy_cycles"],
        hbm_units=body["memory"]["hbm"]["structure"]["units"],
        rom_bytes_read=arch["rom.bytes_read"],
        hbm_read=arch["hbm.bytes_read"],
        hbm_written=arch["hbm.bytes_written"],
        weight_bytes_touched=body["tiling"]["by_family"]["tensor"][
            "memory_traffic"]["bytes_touched"],
    )


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

    run = _anchor_run()
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

    run = _anchor_run()
    report = reconcile(anchor, run, run)
    head = report["headline"]
    assert head["analytical_ratio"] == pytest.approx(
        anchor.hbm["step_time_s"] / anchor.rom["step_time_s"], rel=1e-12
    )
    assert head["analytical_ratio"] == pytest.approx(
        anchor.rom["per_user_tokens_s"] / anchor.hbm["per_user_tokens_s"],
        rel=1e-12,
    )
    # Removing the link term from both analytical steps is the comparison the
    # cycle model can actually be held to.
    rom_link = anchor.rom["component_times_s"]["link_latency"]
    hbm_link = anchor.hbm["component_times_s"]["link_latency"]
    assert head["analytical_ratio_with_link_removed_from_both"] == pytest.approx(
        (anchor.hbm["step_time_s"] - hbm_link)
        / (anchor.rom["step_time_s"] - rom_link), rel=1e-12
    )


#: The three analytical terms the cycle model also expresses.  ``link_latency``
#: is structurally absent on a single chip and ``layer_fixed_latency`` reaches
#: the step only through WAIT dependencies, so neither may enter the comparison.
EXPRESSIBLE_TERMS = ("compute", "weight_read", "kv_read")


def test_binding_regime_is_compared_only_over_expressible_terms(anchor):
    """D6's headline test, made checkable.

    The cycle model has no link term on a single chip, so comparing the two
    binding constraints over all five analytical terms is a category error.
    The comparison is made over the three terms both models express, and this
    test computes that argmax from the anchor's own published component times
    rather than naming a term: at the superseded HBMKV-array-tensor-x4 point
    the two answers differed (link_latency over five terms, kv_read over
    three), and at the re-frozen SRAMKV-array-pipeline-x5-romfill point they
    coincide on weight_read.  A test that named either one would have to be
    re-typed on every anchor move, which is how it would come to be wrong.
    """
    from tools.derive_cycle_machine import reconcile

    run = _anchor_run()
    report = reconcile(anchor, run, run)
    for role, point in (("rom", anchor.rom), ("hbm", anchor.hbm)):
        regime = report["targets"][role]["binding_regime"]
        times = point["component_times_s"]
        assert regime["analytical_over_all_five_terms"] == max(
            times, key=lambda k: times[k]
        )
        assert regime["analytical_over_expressible_terms"] == max(
            EXPRESSIBLE_TERMS, key=lambda k: times[k]
        )
        assert "link_latency" not in {
            regime["analytical_over_expressible_terms"], regime["cycle"]
        }
        assert "layer_fixed_latency" not in {
            regime["analytical_over_expressible_terms"], regime["cycle"]
        }


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


#: The rate at which ``ceil(2048*2/w) == 16 * ceil(128*2/w)`` -- the two
#: shipped tile depths costing the same per unit of depth -- was true, and the
#: half-open band around it.  It is the SUPERSEDED anchor's rate, kept as a
#: fixed point of the arithmetic: the parity was a coincidence of that rate and
#: the anchor has since moved off it (section 13 item 24).  Nothing reads it as
#: the current machine's band.
SUPERSEDED_PARITY_RATE = 265.371881609201
SUPERSEDED_PARITY_BAND = (256.0, 4096.0 / 15.0)


def test_the_two_deployments_cost_the_same_tensor_work_only_inside_a_narrow_band(
    emitted,
):
    """The pair's tensor comparability was a coincidence, and it has expired.

    The shipped ROM deployment (``qwen3-8b-rom-rowfold-v1``) carries
    ``tile_depth`` 2,048 and the HBM one 128.  Per unit of contraction work
    those two shapes cost the same number of cycles only while
    ``ceil(2048 * work_units_per_mac / rate)`` equals
    ``16 * ceil(128 * work_units_per_mac / rate)``, which is true on a band
    about 6.7% wide around 265.372 -- the SUPERSEDED anchor's tensor rate.

    The anchor moved to the point gate G3's budget is frozen on, the derived
    rate fell to 93.193, and the pair LEFT that band.  This test therefore no
    longer asserts parity: it asserts that the loss of parity is quantified and
    directed, which is what the test was written for.  "The two deployments are
    NOT charged alike for identical arithmetic, and the direction is not
    neutral ... it must not be allowed to reappear from the deployment side
    unremarked."  It has reappeared; here is the number.
    """

    rate = emitted["rom_cost_table"]["parameters"][
        "engine.tensor.work_per_lane_cycle"
    ]["value"]
    depth = 4096
    rom = _tensor_cycles(depth, 2048, rate)
    hbm = _tensor_cycles(depth, 128, rate)
    band = tensor_parity_band(2048, 128, rate)
    assert (rom == hbm) is band["parity"], (
        "the parity band disagrees with the cycle arithmetic it describes"
    )
    if band["parity"]:
        assert rom == hbm, (rate, rom, hbm)
    else:
        assert band["favours"] == "rom" and rom < hbm, (
            f"at rate {rate} the {2048}/{128} depth pair favours "
            f"{band['favours']} by {band['magnitude_x']}x; a shape advantage "
            "that has changed direction is a bigger finding than this test"
        )
        assert hbm / rom == pytest.approx(band["magnitude_x"], rel=1e-12)

    # The superseded rate is still the fixed point of the arithmetic, and it
    # is checked so that "the band moved" can never be confused with "the
    # arithmetic moved".
    low, high = SUPERSEDED_PARITY_BAND
    old_band = tensor_parity_band(2048, 128, SUPERSEDED_PARITY_RATE)
    assert old_band["parity"] is True and old_band["favours"] == "neither"
    assert old_band["band"] == pytest.approx([low, high], rel=1e-12)
    assert (
        _tensor_cycles(depth, 2048, SUPERSEDED_PARITY_RATE)
        == _tensor_cycles(depth, 128, SUPERSEDED_PARITY_RATE)
    )

    # And the fragility itself, so nobody reads the equality as structural.
    outside = _tensor_cycles(depth, 2048, 240.0), _tensor_cycles(depth, 128, 240.0)
    assert outside[0] < outside[1], (
        "at a rate below the band the ROM deployment must be the cheaper side; "
        "if this ever fails the asymmetry has changed direction, which is a "
        "bigger finding than the one this test was written for"
    )
    assert outside[0] / outside[1] == pytest.approx(0.5625, rel=1e-6)
