"""Every derived cell is ONE machine emitted twice, not two machines.

``tests/test_derive_cycle_machine.py`` pins the pair this generator was first
written around.  This module pins the whole matrix: the batch-1 pair the study
recommends for each of its three models, every entry of each published batch-1
frontier, the best array and best wafer topology the study names per model, and
the ROM design points the repository already has a capability shape for.

The tests exist to fail in these situations, for every cell and not just the
first one:

1.  A cell's two machines stop being the same machine outside the difference
    its own anchor licenses.  That is the defect the generator exists to
    prevent -- the shipped cycle comparison reported a ROM result that was
    partly a 2x lane advantage and a 16x tensor column-group advantage -- and
    it now has to be prevented fifteen times over, on three models, two KV
    stores and token-slot counts from 1 to 8.
2.  A cell acquires a permitted difference its anchor does NOT license.  The
    SRAM rate difference is licensed only where the two design points name
    different ``kv_store`` values; a cell whose points agree must not be able
    to acquire one.
3.  An emitted number stops reproducing the analytical value it claims.  Every
    cell's compute roof, ROM weight rate, HBM channel rate and lane count is
    checked against the artifact and the model's own IR, not against a copy of
    itself.
4.  A cell is emitted onto a multi-node capability, where the comparison would
    silently skip every ``fabric.*`` parameter.
5.  A cell quietly disappears from the matrix, or appears without a stated
    reason for being unreachable.
"""

from __future__ import annotations

import functools
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.derive_cycle_machine import (  # noqa: E402
    _resolve_all,
    DEFAULT_ANALYTICAL,
    DEFAULT_HBM_DESIGN,
    DEFAULT_ROM_DESIGN,
    DEFAULT_TECHNOLOGY,
    FAMILIES,
    KV_PATH_ALLOWLIST,
    TECHNOLOGY_VIEW,
    WEIGHT_PATH_ALLOWLIST,
    DerivationError,
    allowlist_for,
    assert_comparable,
    base_capabilities,
    build,
    canonical,
    emitted_paths,
    load_anchor,
    pair_id,
    tensor_operator_widths,
)

MATRIX = REPO / "results/derived/n5_design_target_matrix.json"
CONFIG_DIR = REPO / "configs/hardware"
ARTIFACT_DIR = REPO / "results/derived"

_BODY = json.loads(MATRIX.read_text())
EMITTED = {row["pair_id"]: row for row in _BODY["emitted"]}
PAIR_IDS = sorted(EMITTED)


@functools.lru_cache(maxsize=None)
def cell(pid: str):
    """Derive one cell fresh from the artifact.  Cached: the study is 88 MB."""
    row = EMITTED[pid]
    anchor = load_anchor(
        REPO / DEFAULT_ANALYTICAL, REPO / DEFAULT_TECHNOLOGY,
        rom_design=row["rom_design"], hbm_design=row["hbm_design"],
        batch_size=row["batch_size"], context_tokens=row["context_tokens"],
    )
    rom_base, hbm_base = (row["base_capabilities"]["rom"],
                          row["base_capabilities"]["hbm"])
    d, bodies = build(anchor, rom_base, hbm_base)
    paths = emitted_paths(anchor, CONFIG_DIR, ARTIFACT_DIR, rom_base, hbm_base)
    return anchor, d, bodies, paths, row


def _param(table, name):
    return table["parameters"][name]["value"]


# ---------------------------------------------------------------------------
# 1.  The matrix is the matrix
# ---------------------------------------------------------------------------
def test_the_matrix_covers_all_three_models():
    models = {row["model"] for row in _BODY["emitted"]}
    assert models == {
        "Qwen3-8B", "DeepSeek-V4-Flash-0731", "DeepSeek-V4-Pro-0813"
    }, f"the matrix must span the study's three models; got {sorted(models)}"


def test_every_considered_cell_is_either_emitted_or_blocked_with_a_reason():
    assert _BODY["cells_considered"] == (
        _BODY["cells_emitted"] + _BODY["cells_blocked"]
    ), "a cell was considered and then neither emitted nor recorded as blocked"
    for row in _BODY["blocked"]:
        assert row.get("blocked_by"), (
            f"{row['rom_design']} is reported unreachable with no stated "
            f"blocker; an unfilled cell must say what blocks it"
        )


def test_every_cell_carries_the_study_s_own_reason_for_being_in_the_matrix():
    for row in _BODY["emitted"] + _BODY["blocked"]:
        assert row["why_this_cell"], (
            f"{row['rom_design']} is in the matrix with no stated selection "
            f"rule; cells are chosen from the artifact, not from preference"
        )


def test_each_cell_is_priced_at_its_own_model_s_published_context():
    """The three models are priced at three different contexts and never one.

    Asking for a DeepSeek point at Qwen's 8,192 raises '0 analytical points
    match'.  The matrix must therefore record the context per cell, and a cell
    must not silently borrow another model's.
    """
    published = {
        "Qwen3-8B": 8192,
        "DeepSeek-V4-Flash-0731": 200000,
        "DeepSeek-V4-Pro-0813": 1000000,
    }
    for row in _BODY["emitted"]:
        assert row["context_tokens"] == published[row["model"]], (
            f"{row['rom_design']} is priced at context {row['context_tokens']}, "
            f"not its model's published {published[row['model']]}"
        )


def test_matrix_check_mode_agrees():
    proc = subprocess.run(
        [sys.executable, "tools/derive_cycle_machine.py", "--matrix", "--check"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------------------
# 2.  D1, for every cell: one machine emitted twice
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pid", PAIR_IDS)
def test_a_cells_two_machines_differ_only_inside_its_own_allowlist(pid):
    anchor, _d, bodies, paths, row = cell(pid)
    allow = allowlist_for(anchor)
    report = assert_comparable(
        bodies["rom_capability"], paths["rom_cost_table"],
        bodies["hbm_capability"], paths["hbm_cost_table"], allowlist=allow,
    )
    assert report["parameters_compared"] == row["comparability"][
        "parameters_compared"
    ]
    assert set(report["permitted_differences"]) <= set(allow)
    assert report["allowlist_unused"] == [], (
        f"{pid}: the allowlist permits differences the emit does not make: "
        f"{report['allowlist_unused']}.  An allowlist wider than the emit is "
        f"an allowlist that will one day hide a real divergence"
    )
    assert report["rom_provenance_classes"] == ["assumed"]
    assert report["hbm_provenance_classes"] == ["assumed"]


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_the_permitted_set_is_exactly_what_the_anchor_licenses(pid):
    """A KV-path difference is licensed by the ANCHOR, not by the tool.

    The two SRAM rate parameters may differ only where the two design points
    name different ``kv_store`` values.  Where they agree, the weight path is
    the whole licence and the emitted set must be exactly those five names.
    """
    anchor, _d, bodies, paths, _row = cell(pid)
    report = assert_comparable(
        bodies["rom_capability"], paths["rom_cost_table"],
        bodies["hbm_capability"], paths["hbm_cost_table"],
        allowlist=allowlist_for(anchor),
    )
    permitted = set(report["permitted_differences"])
    if anchor.rom_kv_store == anchor.hbm_kv_store:
        assert permitted == set(WEIGHT_PATH_ALLOWLIST), (
            f"{pid}: both design points hold KV in "
            f"{anchor.rom_kv_store!r}, so the ONLY licensed differences are "
            f"the weight path; got {sorted(permitted)}"
        )
    else:
        assert permitted == set(WEIGHT_PATH_ALLOWLIST) | set(KV_PATH_ALLOWLIST)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_a_divergent_compute_parameter_is_rejected_in_this_cell(pid, tmp_path):
    """THE test.  Halving one machine's arithmetic rate must fail the emit."""
    anchor, _d, bodies, paths, _row = cell(pid)
    rigged = json.loads(json.dumps(bodies["hbm_cost_table"]))
    rigged["parameters"]["engine.tensor.work_per_lane_cycle"]["value"] /= 2.0
    path = tmp_path / "abi3_cost_rigged_v1.json"
    path.write_text(canonical(rigged))
    with pytest.raises(DerivationError) as excinfo:
        assert_comparable(
            bodies["rom_capability"], paths["rom_cost_table"],
            bodies["hbm_capability"], path, allowlist=allowlist_for(anchor),
        )
    assert "outside the weight path" in str(excinfo.value)
    assert "engine.tensor.work_per_lane_cycle" in str(excinfo.value)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_a_lane_count_split_is_rejected_in_this_cell(pid):
    anchor, _d, bodies, paths, _row = cell(pid)
    rigged = json.loads(json.dumps(bodies["hbm_capability"]))
    rigged["engines"]["tensor"]["lanes"] = max(
        1, int(rigged["engines"]["tensor"]["lanes"]) // 2
    )
    with pytest.raises(DerivationError) as excinfo:
        assert_comparable(
            bodies["rom_capability"], paths["rom_cost_table"],
            rigged, paths["hbm_cost_table"], allowlist=allowlist_for(anchor),
        )
    assert "engine.tensor.lanes" in str(excinfo.value)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_an_unlicensed_memory_difference_is_rejected_in_this_cell(pid, tmp_path):
    """A difference on a path the anchor does not license must still fail.

    For a cell whose two points hold KV in the same store that is the SRAM
    rate; for a cell whose points differ it is the HBM burst, which no anchor
    ever licenses.
    """
    anchor, _d, bodies, paths, _row = cell(pid)
    same_store = anchor.rom_kv_store == anchor.hbm_kv_store
    name = ("sram.bytes_per_cycle_per_port" if same_store
            else "hbm.transaction_bytes")
    rigged = json.loads(json.dumps(bodies["hbm_cost_table"]))
    rigged["parameters"][name]["value"] = (
        float(rigged["parameters"][name]["value"]) * 2.0
    )
    path = tmp_path / "abi3_cost_rigged_v1.json"
    path.write_text(canonical(rigged))
    with pytest.raises(DerivationError) as excinfo:
        assert_comparable(
            bodies["rom_capability"], paths["rom_cost_table"],
            bodies["hbm_capability"], path, allowlist=allowlist_for(anchor),
        )
    assert "outside the weight path" in str(excinfo.value)
    assert name in str(excinfo.value)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cell_is_collapsed_to_one_logical_device(pid):
    """A cluster or wafer capability would put fabric.* outside the assertion."""
    _anchor, _d, bodies, _paths, _row = cell(pid)
    for role in ("rom_capability", "hbm_capability"):
        assert bodies[role]["topology_class"] == 0, (
            f"{pid}: {role} declares topology_class "
            f"{bodies[role]['topology_class']}; assert_comparable resolves no "
            f"fabric parameter, so the pair's biggest difference would go "
            f"unexamined"
        )
        assert bodies[role]["limits"]["max_nodes"] == 1


def test_a_multi_node_capability_is_refused_outright():
    """The fabric blind spot must be a hard failure, not a silent pass."""
    anchor, _d, bodies, paths, _row = cell(PAIR_IDS[0])
    rigged = json.loads(json.dumps(bodies["rom_capability"]))
    rigged["topology_class"] = 1
    with pytest.raises(DerivationError) as excinfo:
        assert_comparable(
            rigged, paths["rom_cost_table"],
            bodies["hbm_capability"], paths["hbm_cost_table"],
            allowlist=allowlist_for(anchor),
        )
    assert "fabric" in str(excinfo.value)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_capabilities_declare_one_engine_block(pid):
    _anchor, _d, bodies, _paths, _row = cell(pid)
    rom = bodies["rom_capability"]["engines"]
    hbm = bodies["hbm_capability"]["engines"]
    assert set(rom) == set(FAMILIES)
    assert rom == hbm, f"{pid}: the two capabilities must declare one engine block"
    assert len({spec["lanes"] for spec in rom.values()}) == 1


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_capabilities_can_be_asked_the_same_questions(pid):
    """The sharpest declared asymmetry the shipped pair carried.

    limits are not machine parameters, so nothing in the resolved comparison
    would notice one machine being legally askable for a position its partner
    cannot serve.  Both records carry the smaller of the two bases.
    """
    _anchor, _d, bodies, _paths, _row = cell(pid)
    rom = bodies["rom_capability"]["limits"]["max_context_positions"]
    hbm = bodies["hbm_capability"]["limits"]["max_context_positions"]
    assert rom == hbm, (
        f"{pid}: the ROM machine caps positions at {rom} and the GPU machine "
        f"at {hbm}; the pair could be exercised where only one of them can go"
    )


# ---------------------------------------------------------------------------
# 3.  Every derived number still reproduces the analytical value it cites
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_emitted_files_match_a_fresh_derivation(pid):
    _anchor, _d, bodies, paths, _row = cell(pid)
    for key in ("rom_cost_table", "hbm_cost_table",
                "rom_capability", "hbm_capability"):
        assert paths[key].exists(), f"{paths[key]} is missing"
        assert paths[key].read_text() == canonical(bodies[key]), (
            f"{pid}: {paths[key].name} has drifted from the anchor it claims; "
            f"re-run tools/derive_cycle_machine.py --matrix"
        )


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_compute_roof_reproduces_the_published_compute_term(pid):
    """Exact, and over every canonical format the point executes.

    A literal 'bf16' index raises on both DeepSeek models; a literal 'bf16'
    density silently prices a w4a8 point 2.7x too slow.  The roof is the
    point's own operations over the point's own published time, so the identity
    is exact by construction, and it is cross-checked against area x density.
    """
    anchor, _d, bodies, _paths, _row = cell(pid)
    table = bodies["rom_cost_table"]
    roof = (_param(table, "engine.tensor.lanes.default")
            * _param(table, "engine.tensor.work_per_lane_cycle")
            * _param(table, "clock.frequency_hz"))
    published = anchor.rom["component_times_s"]["compute"]
    assert anchor.operations / roof == pytest.approx(published, rel=1e-12)
    assert roof == pytest.approx(anchor.compute_roof_ops_s, rel=1e-12)
    # ...and the roof the study itself built the term from.
    assert anchor.compute_area_time_s == pytest.approx(published, rel=1e-9), (
        f"{pid}: the sum over formats of ops_f / (area x density_f x "
        f"efficiency) no longer reproduces the published compute term"
    )


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_every_family_in_this_cell_carries_the_one_arithmetic_roof(pid):
    _anchor, _d, bodies, _paths, _row = cell(pid)
    for table in (bodies["rom_cost_table"], bodies["hbm_cost_table"]):
        rates = {
            _param(table, f"engine.{f}.lanes.default")
            * _param(table, f"engine.{f}.work_per_lane_cycle")
            for f in FAMILIES
        }
        assert len(rates) == 1, (
            f"{pid}: the analytical model prices all arithmetic at one roof, "
            f"so every engine family must carry one rate; got {rates}"
        )


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_collapse_divides_the_aggregate_by_its_own_slots(pid):
    """The rule that generalises the derivation off its first anchor.

    The published component times already carry ``token_slots``, so the rate a
    token engages is the design's aggregate over its OWN slot count.  Taking
    the undivided aggregate on both sides would remove a different
    serialisation factor from each -- 4 against 2 on the Flash x32 cell -- and
    hand the more deeply pipelined side a speed-up the study never granted it.
    """
    anchor, _d, bodies, _paths, _row = cell(pid)
    exact = anchor.assert_collapse_is_exact()
    for role, rel in exact.items():
        assert abs(rel) <= 1e-9, f"{pid}: {role} collapse is off by {rel:+.3e}"
    table = bodies["rom_cost_table"]
    arrays = _param(table, "rom.arrays.default")
    clock = _param(table, "clock.frequency_hz")
    achieved = arrays * _param(table, "rom.bytes_per_cycle_per_array") * clock
    target = anchor.rom_peak_weight_read_bytes_s / anchor.rom_token_slots
    # The only licensed error is the integer B/cycle rounding, so the tolerance
    # is half a byte per cycle per array and nothing wider.
    tolerance = 0.5 / (target / (arrays * clock))
    assert abs(achieved / target - 1.0) <= tolerance, (
        f"{pid}: the derived ROM array delivers {achieved:.6e} B/s against the "
        f"collapsed rate {target:.6e} B/s, outside the "
        f"{tolerance:.3e} integer-quantisation bound"
    )
    assert _param(table, "rom.transaction_bytes") % _param(
        table, "rom.bytes_per_cycle_per_array"
    ) == 0


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_hbm_channel_is_shared_and_reproduces_the_gpu_point(pid):
    anchor, _d, bodies, _paths, _row = cell(pid)
    rom_t, hbm_t = bodies["rom_cost_table"], bodies["hbm_cost_table"]
    bpc = _param(rom_t, "hbm.bytes_per_cycle_per_channel")
    assert bpc == _param(hbm_t, "hbm.bytes_per_cycle_per_channel"), (
        f"{pid}: the two design points must buy the same HBM3E channel; only "
        f"the count may differ"
    )
    clock = _param(rom_t, "clock.frequency_hz")
    assert _param(hbm_t, "hbm.channels.default") * bpc * clock == pytest.approx(
        anchor.hbm_memory_bytes_s, rel=1e-12
    )
    if anchor.rom_kv_store == "hbm":
        assert _param(rom_t, "hbm.channels.default") * bpc * clock == (
            pytest.approx(anchor.rom_kv_read_bytes_s, rel=1e-12)
        )
    else:
        # KV lives in SRAM, so the ROM machine buys no HBM and its KV rate is
        # on the SRAM ports instead.
        assert _param(rom_t, "hbm.channels.default") == 1
        units = (_param(rom_t, "sram.banks.default")
                 * _param(rom_t, "sram.ports_per_bank.default"))
        sram = units * _param(rom_t, "sram.bytes_per_cycle_per_port") * clock
        target = anchor.rom_kv_read_bytes_s
        tolerance = 0.5 / (target / (units * clock))
        assert abs(sram / target - 1.0) <= tolerance, (
            f"{pid}: the ROM point holds KV in SRAM, so the derived SRAM ports "
            f"must reproduce its KV rate {target:.6e} B/s; they deliver "
            f"{sram:.6e} B/s, outside the {tolerance:.3e} rounding bound"
        )
    tx = _param(rom_t, "hbm.transaction_bytes")
    assert tx / bpc == int(tx / bpc)


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_lanes_are_the_narrowest_tensor_operator_width(pid):
    """Read from the model's own IR, so it holds for GQA, MLA and MoE alike."""
    anchor, _d, bodies, _paths, _row = cell(pid)
    ops = tensor_operator_widths(anchor)
    narrowest = min(int(o["output_width"]) for o in ops)
    assert _param(
        bodies["rom_cost_table"], "engine.tensor.lanes.default"
    ) == narrowest
    assert bodies["rom_capability"]["engines"]["tensor"]["lanes"] == narrowest
    assert bodies["hbm_capability"]["engines"]["tensor"]["lanes"] == narrowest


def test_the_qwen_lane_rule_still_agrees_with_the_gqa_formula_it_replaced():
    """The IR rule must reproduce the answer the GQA formula gave for Qwen3."""
    meta = json.loads(
        (REPO / "configs/models/qwen3-8b.json").read_text()
    )["metadata"]
    gqa = int(meta["num_key_value_heads"]) * int(meta["head_dim"])
    qwen = [p for p in PAIR_IDS if EMITTED[p]["model"] == "Qwen3-8B"]
    assert qwen
    for pid in qwen:
        assert EMITTED[pid]["tensor_lanes"] == gqa


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_no_parameter_in_this_cell_claims_measured_or_characterized_evidence(pid):
    _anchor, _d, bodies, _paths, _row = cell(pid)
    for key in ("rom_cost_table", "hbm_cost_table"):
        for name, entry in bodies[key]["parameters"].items():
            assert entry["provenance"] == "assumed", (
                f"{pid}:{key}:{name} claims provenance {entry['provenance']!r}"
            )
            assert entry["analytical_grade"] in {"derived", "assumed"}
            assert entry["note"], f"{pid}:{key}:{name} carries no derivation"
    for key in ("rom_capability", "hbm_capability"):
        assert bodies[key]["technology_view"] == TECHNOLOGY_VIEW


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cell_names_the_residuals_it_cannot_express(pid):
    _anchor, d, _bodies, _paths, _row = cell(pid)
    kinds = {(r["term"], r["kind"]) for r in d.residuals}
    for expected in (
        ("link_latency", "structurally_inexpressible"),
        ("step_time", "combination_rule"),
        ("weight_read", "slot_serialisation"),
        ("compute", "work_disagreement"),
        ("compute", "shared_roof_handicap"),
        ("weight_read", "sweep_versus_touched"),
        ("weight_read", "interleave_granularity"),
        ("layer_fixed_latency", "granularity"),
    ):
        assert expected in kinds, f"{pid} does not report {expected}"


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cell_reports_the_gpu_side_shared_roof_handicap(pid):
    """The GPU point cannot reproduce its own compute term and must say so."""
    _anchor, d, _bodies, _paths, _row = cell(pid)
    handicap = [r for r in d.residuals if r["kind"] == "shared_roof_handicap"]
    assert len(handicap) == 1
    row = handicap[0]
    assert row["ratio"] != pytest.approx(1.0, rel=1e-9), (
        "one shared roof cannot reproduce both points' compute terms; a ratio "
        "of exactly 1 would mean the residual is not being computed"
    )
    # The direction is NOT the same in every cell.  Where the ROM design buys
    # wafer-scale compute area the shared roof exceeds the GPU part's own, and
    # the derived GPU machine is CREDITED rather than handicapped -- which
    # favours the GPU side and has to be said, not assumed away.
    expected = "handicaps_the_gpu" if row["ratio"] > 1.0 else "credits_the_gpu"
    assert row["direction"] == expected
    assert ("HANDICAPPED" in row["note"]) == (expected == "handicaps_the_gpu")
    assert ("CREDITED" in row["note"]) == (expected == "credits_the_gpu")


# ---------------------------------------------------------------------------
# 4.  The shipped evidence is untouched
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("path", [
    "configs/hardware/abi3_cost_sky130_rom_v2.json",
    "configs/hardware/abi3_cost_asap7_v2.json",
    "configs/hardware/abi3_capability/rom_qwen3.json",
    "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    "configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json",
    "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
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


def test_every_published_capability_still_matches_the_profile_that_defines_it():
    """Including the new DeepSeek-V4-Pro array record."""
    proc = subprocess.run(
        [sys.executable, "tools/publish_abi3_capabilities.py", "--check"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "rom_deepseek_v4_pro_array_32" in proc.stdout


def test_no_emitted_cost_table_collides_with_a_shipped_one():
    shipped = {
        p.name for p in (REPO / "configs/hardware").glob("abi3_cost_*.json")
        if TECHNOLOGY_VIEW not in p.name
    }
    for pid in PAIR_IDS:
        _anchor, _d, _bodies, paths, _row = cell(pid)
        for key in ("rom_cost_table", "hbm_cost_table"):
            assert paths[key].name not in shipped
            assert paths[key].name.startswith("abi3_cost_"), (
                "load_cost_table refuses a file without the reserved prefix"
            )


def test_each_cell_has_its_own_four_files():
    """A second cell must not overwrite a first."""
    seen: dict[str, str] = {}
    for pid in PAIR_IDS:
        _anchor, _d, _bodies, paths, _row = cell(pid)
        for key, path in paths.items():
            name = str(path)
            assert name not in seen or seen[name] == pid, (
                f"{pid} and {seen[name]} would both write {name}"
            )
            seen[name] = pid


def test_the_default_pair_keeps_the_paths_it_was_published_at():
    anchor = load_anchor(
        REPO / DEFAULT_ANALYTICAL, REPO / DEFAULT_TECHNOLOGY,
        rom_design=DEFAULT_ROM_DESIGN,
        hbm_design=DEFAULT_HBM_DESIGN,
        batch_size=1, context_tokens=8192,
    )
    rom_base, hbm_base = base_capabilities(anchor)
    paths = emitted_paths(anchor, CONFIG_DIR, ARTIFACT_DIR, rom_base, hbm_base)
    assert paths["rom_cost_table"] == (
        CONFIG_DIR / f"abi3_cost_{TECHNOLOGY_VIEW}_rom_v1.json"
    )
    assert paths["rom_capability"].name == "rom_qwen3_n5_v1.json"
    assert pair_id(anchor) in EMITTED


# ---------------------------------------------------------------------------
# The collapsed device must HOLD what the devices it stands for hold
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pid", PAIR_IDS)
def test_this_cells_collapsed_device_holds_its_design_points_capacity(pid):
    """One logical device standing for N must declare N devices' capacity.

    The collapse divides every RATE by the design's own token_slots, but a
    capacity is not a rate: it decides only whether a deployment fits the
    device at all.  Leaving the base record's capacity alone declares a
    machine too small to host the design point it was derived from -- the
    DeepSeek-V4-Flash GPU comparator plans 229,845,618,692 bytes per node
    against the single-chip record's 103,079,215,104 and is refused before it
    can be timed.
    """
    anchor, _d, bodies, _paths, row = cell(pid)
    for role, base_key, devices_key, point, kv_store in (
        ("rom_capability", "rom", "rom_devices", anchor.rom, anchor.rom_kv_store),
        ("hbm_capability", "hbm", "hbm_devices", anchor.hbm, anchor.hbm_kv_store),
    ):
        base = json.loads(
            (REPO / row["base_capabilities"][base_key]).read_text()
        )
        devices = int(row[devices_key])
        emitted = bodies[role]["memory"]
        for klass in ("rom", "hbm", "sram"):
            if klass not in base.get("memory", {}):
                continue
            if "bytes" not in base["memory"][klass]:
                continue
            scaled = int(base["memory"][klass]["bytes"]) * devices
            # A KV arena is the one capacity the collapse does NOT scale: the
            # design point holds one of it for the session, and the base
            # record was never sized for it.  Where the point puts KV in SRAM
            # the arena is DECLARED SEPARATELY and added, and the next test
            # checks the arena itself.
            arena = int(emitted.get("sram_kv", {}).get("bytes", 0)) if (
                klass == "sram" and kv_store == "sram") else 0
            expected = scaled + arena
            assert emitted[klass]["bytes"] == expected, (
                f"{pid}: {role} memory.{klass}.bytes is "
                f"{emitted[klass]['bytes']}, but this cell collapses "
                f"{devices} devices whose aggregate is {scaled}"
                + (f" plus a {arena}-byte declared SRAM KV arena" if arena
                   else "")
            )


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_a_cell_that_puts_kv_in_sram_declares_sram_that_holds_it(pid):
    """Section 13 item 26: the derived SRAM must cover scratchpad AND KV.

    The collapse used to scale the base record's scratchpad by device_count
    and read ``kv_capacity_bytes`` nowhere, so the Qwen x5 SRAMKV point --
    which provisions 1,207,959,552 bytes of SRAM KV -- was derived onto a
    record declaring 671,088,640, exactly five copies of the base record's
    128 MiB scratchpad.  Every SRAMKV cell was short, and no SRAM KV
    placement could be admitted by any of them.

    A cell whose point holds KV in HBM must declare no arena at all: an
    unconditional arena would tell an HBMKV backend to move its KV.
    """
    anchor, _d, bodies, _paths, row = cell(pid)
    for role, point, kv_store, devices_key in (
        ("rom_capability", anchor.rom, anchor.rom_kv_store, "rom_devices"),
        ("hbm_capability", anchor.hbm, anchor.hbm_kv_store, "hbm_devices"),
    ):
        memory = bodies[role]["memory"]
        if kv_store != "sram":
            assert "sram_kv" not in memory, (
                f"{pid}: {role} holds KV in {kv_store!r} but declares an SRAM "
                f"KV arena"
            )
            continue
        provisioned = int(round(float(point["kv_capacity_bytes"])))
        arena = int(memory["sram_kv"]["bytes"])
        assert arena >= provisioned, (
            f"{pid}: {role} declares a {arena}-byte SRAM KV arena against a "
            f"design point that provisions {provisioned}"
        )
        base = json.loads(
            (REPO / row["base_capabilities"][
                "rom" if role == "rom_capability" else "hbm"]).read_text()
        )
        scratchpad = int(base["memory"]["sram"]["bytes"]) * int(row[devices_key])
        assert int(memory["sram"]["bytes"]) >= scratchpad + provisioned, (
            f"{pid}: {role} declares {memory['sram']['bytes']} bytes of SRAM "
            f"against a {scratchpad}-byte scratchpad and a {provisioned}-byte "
            f"KV store that must both fit in it"
        )
        # Every part is named, not just totalled.
        parts = bodies[role]["derived_from"]["memory_capacity_provenance"]
        kv = parts["parts"]["memory.sram.bytes"]["kv_arena"]
        assert kv["design_point_kv_capacity_bytes"] == provisioned
        assert kv["scratchpad_bytes"] == scratchpad
        assert kv["bytes"] == arena


@pytest.mark.parametrize("pid", PAIR_IDS)
def test_scaling_a_capacity_moves_no_machine_parameter(pid):
    """Capacity must stay outside the 114 compared parameters.

    If a capacity ever became a resolved machine parameter, scaling it would
    silently move a cycle count, and the collapse would be changing timing
    while claiming to change only what fits.
    """
    _anchor, _d, bodies, paths, _row = cell(pid)
    for role, table in (
        ("rom_capability", "rom_cost_table"),
        ("hbm_capability", "hbm_cost_table"),
    ):
        before = _resolve_all(bodies[role], paths[table])
        rigged = json.loads(json.dumps(bodies[role]))
        for klass in list(rigged.get("memory", {})):
            if "bytes" in rigged["memory"][klass]:
                rigged["memory"][klass]["bytes"] *= 7
        after = _resolve_all(rigged, paths[table])
        assert before == after, (
            f"{pid}: multiplying every declared capacity by 7 moved a "
            f"resolved machine parameter, so capacity is a rate here and the "
            f"collapse cannot scale it freely"
        )


@pytest.mark.parametrize("pid", [p for p in PAIR_IDS if "pro" in p])
def test_a_pro_cell_bases_on_the_only_pro_rom_product(pid):
    """Pro routes 384 experts and needs 85.9 GB of ROM; Flash shapes refuse it.

    Basing a Pro cell on a Flash record does not merely mis-cost it -- the
    deployment is refused at admission, because max_expert_ids 256 cannot
    address expert 256.
    """
    _anchor, _d, _bodies, _paths, row = cell(pid)
    assert row["base_capabilities"]["rom"].endswith(
        "rom_deepseek_v4_pro_array_32.json"
    ), (
        f"{pid}: Pro cell bases on {row['base_capabilities']['rom']}, which is "
        f"not the Pro ROM product"
    )
