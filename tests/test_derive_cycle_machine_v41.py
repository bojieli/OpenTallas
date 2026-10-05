"""The DeepSeek-V4.1-Flash cells of the cycle-model generator, and what blocks them.

Plan ``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` sections 8 and 13
WP-J, gate DS41-C2.  ``tests/test_derive_cycle_machine.py`` pins the anchor pair
and ``tests/test_derive_cycle_machine_matrix.py`` pins the fifteen cells of the
main study.  This module pins the five V4.1 cells, which differ from every cell
before them in three ways and are tested on exactly those three:

1.  They live in CANDIDATE studies, one per Engram placement, not in
    ``results/roofline/n5_vs_b200/analytical.json``.  Their GPU side must still
    come from the artifact's own ``iso_area_gpu_design`` -- and plan section 8's
    own text names a comparator that belongs to a different design point, so the
    arithmetic that shows it is wrong is pinned here rather than argued once in a
    comment.
2.  Their model name carries a dot and, for two of the three, a placement
    variant.  The kernel-IR directory of a model is the model registry's stem;
    the rule that produced it before looked for a directory no builder writes.
    The three models that existed before V4.1 must not move.
3.  They cannot be derived yet.  The tests therefore assert the SHAPE of a
    blocked cell -- every input it waits for, named with what produces it -- and
    become assertions about a derived machine the moment those inputs land,
    without an edit here and without a skip.

The Engram pricing is the one part of WP-J that runs to a number today, so it is
tested as a measurement: the quantum is the measured one, the identity the row
count rests on closes, and the verdict is taken on the worse of two bounds.
"""

from __future__ import annotations

import json
import math
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.derive_cycle_machine import (  # noqa: E402
    BASE_CAPABILITY_PRODUCERS,
    CHANNELS_PER_STACK,
    DEFAULT_TECHNOLOGY,
    ENGRAM_MEASURED_COST_TABLE,
    ENGRAM_STEP_FRACTION_BAR,
    ROM_BASE_CAPABILITY,
    SHIPPED_DEPLOYMENTS_MANIFEST,
    V41_CELLS,
    V41_CELLS_OUT,
    DerivationError,
    analytical_body,
    base_capabilities,
    derived_clock_hz,
    engram_lookup_shape,
    ir_model_slug,
    load_anchor,
    matrix_cells,
    model_registry,
    price_engram_on_hbm,
    registered_base_capabilities,
)

MANIFEST = json.loads((REPO / V41_CELLS_OUT).read_text())
ROWS = MANIFEST["cells"]
CELL_IDS = [c["cell_id"] for c in V41_CELLS]

#: The three V4.1 analytical model names, and the one kernel IR they share.
V41_MODELS = (
    "DeepSeek-V4.1-Flash",
    "DeepSeek-V4.1-Flash-engram-host",
    "DeepSeek-V4.1-Flash-engram-hbm",
)


def _anchor(row):
    return load_anchor(
        REPO / row["analytical_artifact"], REPO / DEFAULT_TECHNOLOGY,
        rom_design=row["rom_design"], hbm_design=row["hbm_design"],
        batch_size=row["batch_size"], context_tokens=row["context_tokens"],
    )


# ---------------------------------------------------------------------------
# 1.  The IR directory of a model is read, not spelled
# ---------------------------------------------------------------------------
def test_the_v41_models_resolve_to_the_one_ir_the_front_end_writes():
    """One IR for three placements, at the name the builder uses.

    ``compiler.frontends.v3.deepseek_v41.MODEL_ID`` is what
    ``tools/build_deepseek_v4_kernel_ir_v3.py`` writes ``build/ir-v3/<id>/`` for,
    so that string -- not a lower-cased display name -- is the directory the lane
    rule has to read.
    """
    from compiler.frontends.v3.deepseek_v41 import MODEL_ID

    for model in V41_MODELS:
        assert ir_model_slug(model) == MODEL_ID == "deepseek-v4.1-flash", model
    assert (REPO / "build/ir-v3" / MODEL_ID).is_dir(), (
        "the V4.1 IR directory is not even present; the slug is right but "
        "nothing has been built into it"
    )


@pytest.mark.parametrize(
    "model", ["Qwen3-8B", "DeepSeek-V4-Flash-0731", "DeepSeek-V4-Pro-0813"]
)
def test_no_pre_v41_model_slug_moved(model):
    """The rule changed; its answers for every existing cell must not have.

    The previous rule was ``name.lower().replace('.', '-')``.  No model that
    existed before V4.1 carries a dot, so both rules agree on all three, and
    every emitted V4, Pro and Qwen cell is derived from the same IR as before.
    """
    assert ir_model_slug(model) == model.lower().replace(".", "-")
    assert (REPO / "build/ir-v3" / ir_model_slug(model)
            / "kernel_ir.v3.json").exists()


def test_the_registry_is_what_names_the_placement_variants():
    """The variant suffix is stripped from the registry field, not from a list."""
    registry = model_registry()
    for model in V41_MODELS:
        assert model in registry, model
    assert registry["DeepSeek-V4.1-Flash"]["variant"] == ""
    assert registry["DeepSeek-V4.1-Flash-engram-hbm"]["variant"] == "engram_hbm"
    assert registry["DeepSeek-V4.1-Flash-engram-host"]["variant"] == "engram_host"


# ---------------------------------------------------------------------------
# 2.  The cells, and the comparator this tool is not allowed to choose
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cell", V41_CELLS, ids=CELL_IDS)
def test_every_v41_cell_is_selected_by_its_own_artifacts_rule(cell):
    """A cell is in the matrix because the artifact selects it, and its GPU side
    is the artifact's own iso-area comparator."""
    body = analytical_body(cell["analytical"])
    selected = {c["rom_design"]: c for c in matrix_cells(body)}
    assert cell["rom_design"] in selected, (
        f"{cell['cell_id']} is not selected from {cell['analytical']}; a cell "
        "the artifact does not select has no comparator this tool may use"
    )
    chosen = selected[cell["rom_design"]]
    own = {
        c.get("iso_area_gpu_design")
        for c in body["comparisons"]
        if c.get("rom_design") == cell["rom_design"]
        and int(c.get("batch_size", -1)) == 1
    }
    assert chosen["hbm_design"] in own, (
        f"{cell['cell_id']}'s GPU side is not this artifact's own batch-1 "
        f"iso_area_gpu_design"
    )
    assert chosen["why"], "a cell with no stated reason for being in the matrix"


def test_the_51_node_array_is_not_paired_with_the_x43_comparator():
    """Plan section 8's array comparator belongs to the 84-node design point.

    This is the one place the plan's text cannot be followed.  ``x43-tensor`` is
    43 x 1,600 mm2 and is the iso-area comparator of the Engram-in-ROM class's
    84-node array; the 51-node array is 41,565 mm2 and its own artifact pairs it
    with ``x26-tensor``.  Pinned as arithmetic so it cannot be "fixed" by
    writing the pairing the plan names.
    """
    rom_body = analytical_body(
        "results/roofline/candidates/deepseek-v41-flash/n5_vs_b200/"
        "analytical.json"
    )
    host_body = analytical_body(
        "results/roofline/candidates/deepseek-v41-flash-engram-host/n5_vs_b200/"
        "analytical.json"
    )
    reticle = json.loads((REPO / DEFAULT_TECHNOLOGY).read_text())
    reticle_mm2 = float(reticle["reticle"]["area_mm2"]["value"])

    def area(body, design, batch=1):
        return next(
            float(p["silicon_area_mm2"]) for p in body["points"]
            if p["design"] == design and int(p["batch_size"]) == batch
        )

    x43 = "DeepSeek-V4.1-Flash/b200_sxm-x43-tensor"
    x84 = "DeepSeek-V4.1-Flash/ROM-N5-native-SRAMKV-array-hybrid-x84"
    x51 = ("DeepSeek-V4.1-Flash-engram-host/"
           "ROM-N5-native-SRAMKV-array-hybrid-x51")
    x26 = "DeepSeek-V4.1-Flash-engram-host/b200_sxm-x26-tensor"

    # the x43 comparator is iso-area to EIGHTY-FOUR reticles, not to 51
    assert area(rom_body, x84) == pytest.approx(84 * reticle_mm2)
    assert abs(area(rom_body, x84) / area(rom_body, x43) - 1) < 0.01
    # and the artifact says so itself
    assert x43 in {
        c.get("iso_area_gpu_design") for c in rom_body["comparisons"]
        if c.get("rom_design") == x84 and int(c.get("batch_size", -1)) == 1
    }
    # the 51-node array is iso-area to x26 and no V4.1 artifact pairs it with x43
    assert area(host_body, x51) == pytest.approx(51 * reticle_mm2)
    assert abs(area(host_body, x51) / area(host_body, x26) - 1) < 0.01
    pairings = {
        c.get("iso_area_gpu_design") for c in host_body["comparisons"]
        if c.get("rom_design") == x51
    }
    assert not any("x43" in str(g) for g in pairings), pairings
    # what following the plan's sentence literally would cost
    ratio = area(rom_body, x43) / area(host_body, x51)
    assert ratio > 1.6, (
        "the x43 comparator is no longer 1.6x the 51-node array's silicon; "
        "re-read the plan sentence against the artifacts before trusting this"
    )


@pytest.mark.parametrize("cell", V41_CELLS, ids=CELL_IDS)
def test_every_v41_cell_has_a_registered_rom_base(cell):
    """A cell whose base capability is unregistered cannot derive at all.

    Registration is a source-level decision and is testable now; whether the
    record exists is not, so both branches are asserted: registered and present
    means ``base_capabilities`` returns it, registered and absent means it
    refuses with the work package that produces it.
    """
    row = next(r for r in ROWS if r["cell_id"] == cell["cell_id"]
               and "hbm_design" in r)
    anchor = _anchor(row)
    model = str(anchor.rom["model"])
    kind = str(anchor.rom.get("topology_kind", "array"))
    assert (model, kind) in ROM_BASE_CAPABILITY, (
        f"{cell['cell_id']} is a {kind} of {model} and no ROM base capability "
        "is registered for that shape"
    )
    rom_base, hbm_base = registered_base_capabilities(anchor)
    if (REPO / rom_base).exists() and (REPO / hbm_base).exists():
        assert base_capabilities(anchor) == (rom_base, hbm_base)
        return
    with pytest.raises(DerivationError) as excinfo:
        base_capabilities(anchor)
    message = str(excinfo.value)
    assert "not in this tree" in message
    missing = rom_base if not (REPO / rom_base).exists() else hbm_base
    assert missing in message
    if missing in BASE_CAPABILITY_PRODUCERS:
        assert "WP-" in message, (
            "the refusal must name the work package that produces the record"
        )


# ---------------------------------------------------------------------------
# 3.  A blocked cell is recorded, never skipped
# ---------------------------------------------------------------------------
def test_the_manifest_covers_every_cell_at_every_batch():
    expected = {
        (cell["cell_id"], batch)
        for cell in V41_CELLS for batch in cell["batch_sizes"]
    }
    assert {(r["cell_id"], r["batch_size"]) for r in ROWS} == expected
    assert MANIFEST["cells_considered"] == len(expected)


@pytest.mark.parametrize(
    "row", ROWS, ids=[f"{r['cell_id']}-b{r['batch_size']}" for r in ROWS]
)
def test_a_cell_is_either_emitted_or_names_every_input_it_waits_for(row):
    """Absence is a failure with a reason, not a gap.

    A blocked cell must name each missing input, why the derivation needs it and
    what produces it.  An emitted cell must carry its comparability result with
    zero unexpected differences -- the property the whole generator exists for.
    """
    assert row["status"] in ("emitted", "blocked")
    if row["status"] == "blocked":
        assert row["blockers"], row["cell_id"]
        for blocker in row["blockers"]:
            assert blocker["input"], blocker
            assert blocker["why_needed"], blocker
            assert blocker["produced_by"], blocker
        return
    assert row["blockers"] == []
    assert row["comparability"]["unexpected_differences"] == 0
    assert row["comparability"]["parameters_compared"] > 0
    for emitted in row["emitted"].values():
        assert (REPO / emitted).exists(), emitted


def test_the_manifest_reproduces_from_its_inputs():
    """The artifact is a walk of committed inputs, not a snapshot."""
    done = subprocess.run(
        [sys.executable, "tools/derive_cycle_machine.py", "--v41-cells",
         "--check"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_the_c2_state_of_every_cell_is_a_verdict_and_not_a_missing_key():
    """Gate C2's half of WP-J: a cell with no deployment says so, per side."""
    for row in ROWS:
        if "c2" not in row:
            continue
        c2 = row["c2"]
        for role in ("rom", "hbm"):
            side = c2["deployments"][role]
            assert side["status"], row["cell_id"]
            if side["status"] != "bound":
                assert side["why"], (row["cell_id"], role)
        if c2.get("comparable") is False:
            assert c2.get("verdict") or any(
                c2["deployments"][r]["status"] != "bound" for r in ("rom", "hbm")
            )


# ---------------------------------------------------------------------------
# 4.  The Engram lookup, priced on the HBM path (plan sections 3.4 and 4.4)
# ---------------------------------------------------------------------------
PRICED = MANIFEST["engram_hbm_pricing"]


@pytest.mark.parametrize("model", V41_MODELS)
def test_the_engram_row_arithmetic_closes(model):
    """The byte total and the row count must be the same statement."""
    shape = engram_lookup_shape(model)
    assert (shape["modules"] * shape["rows_read_per_token_per_module"]
            * shape["row_bytes_packed"]) == shape["lookup_bytes_per_token"]
    assert shape["rows_read_per_token"] == 48
    assert shape["modules"] == 2 == len(shape["module_layer_ids"])


def test_a_registry_whose_engram_block_does_not_close_is_refused(
        tmp_path, monkeypatch):
    """The identity is checked, not trusted."""
    registry = dict(model_registry())
    config = tmp_path / "broken.json"
    body = json.loads(
        (REPO / registry["DeepSeek-V4.1-Flash-engram-hbm"]["config"]).read_text()
    )
    body["metadata"]["engram"]["rows_read_per_token_per_module"] = 25
    config.write_text(json.dumps(body))
    import tools.derive_cycle_machine as dcm

    monkeypatch.setitem(
        dcm._MODEL_REGISTRY, "Broken-V41",
        {"stem": "broken", "variant": "", "config": str(config)},
    )
    with pytest.raises(DerivationError) as excinfo:
        engram_lookup_shape("Broken-V41")
    assert "does not close" in str(excinfo.value)


def test_the_lookup_is_priced_at_the_measured_transaction_size():
    """Plan section 8: the quantum comes from the measured table.

    64 bytes, provenance ``characterized``, from the DMA campaign's own
    ``correlation.hbm_burst_bytes``.  A 264-byte row is five of them, and the
    fifth carries 8 useful bytes -- 1.21x the useful traffic, which is the cost
    of putting a 264-byte row on a 64-byte burst and is charged here rather than
    quantised away.
    """
    assert PRICED, "no cell priced the Engram lookup"
    table = json.loads((REPO / ENGRAM_MEASURED_COST_TABLE).read_text())
    quantum = table["parameters"]["hbm.transaction_bytes"]
    assert quantum["value"] == 64
    assert quantum["provenance"] == "characterized"
    for priced in PRICED:
        measured = priced["measured_inputs"]["parameters"]
        assert measured["hbm.transaction_bytes"]["value"] == quantum["value"]
        assert measured["hbm.transaction_bytes"]["provenance"] == "characterized"
        assert measured["hbm.transaction_bytes"]["source"] == quantum["source"]
        # the assumed input is labelled as one wherever it is carried
        assert measured["hbm.read_latency_cycles"]["provenance"] == "assumed"
        row_bytes = priced["lookup"]["row_bytes_packed"]
        assert priced["transactions_per_row"] == math.ceil(row_bytes / 64) == 5
        assert priced["burst_bytes_per_token"] == 48 * 5 * 64
        assert priced["burst_bytes_over_useful_bytes"] == pytest.approx(
            15360 / 12672
        )
        for label, bound in priced["bounds"].items():
            assert bound["transactions"] == bound["rows"] * 5, label
            assert bound["seconds"] == pytest.approx(
                bound["finish_cycles"] / priced["machine"]["clock_hz"]
            )
            # the charge splits into the assumed latency and the serialisation
            # the measured quantum causes; a reader must be able to see which
            assert (bound["finish_cycles"]
                    == bound["read_latency_cycles"] + bound["serialised_cycles"])
            assert bound["read_latency_cycles"] == measured[
                "hbm.read_latency_cycles"]["value"]
        worst = priced["bounds"][priced["worst_bound"]]
        assert priced["cost_is_dominated_by"] == (
            "the assumed hbm.read_latency_cycles"
            if worst["read_latency_cycles"] >= worst["serialised_cycles"]
            else "channel serialisation at the measured burst size"
        )
        # bandwidth is not the cost at this provisioning, and the record says so
        assert priced["bandwidth_floor_seconds"] < priced["read_latency_seconds"]


def test_the_verdict_is_taken_on_the_worse_of_two_bounds():
    """One number would be a guess about an n-gram hash."""
    for priced in PRICED:
        labels = set(priced["bounds"])
        assert labels == {
            "per_token_distributed", "per_token_collided",
            "per_module_distributed", "per_module_collided",
        }
        # a collided bound must cost at least as much as a distributed one
        assert (priced["bounds"]["per_token_collided"]["finish_cycles"]
                >= priced["bounds"]["per_token_distributed"]["finish_cycles"])
        assert priced["bar"] == ENGRAM_STEP_FRACTION_BAR
        worst = max(priced["fraction_of_step"].values())
        assert priced["worst_fraction_of_step"] == pytest.approx(worst)
        assert priced["below_bar"] is (worst < priced["bar"])
        assert priced["step"]["used_s"] == min(
            v for v in priced["step"]["candidates_s"].values() if v
        )
        for label, fraction in priced["fraction_of_step"].items():
            assert fraction == pytest.approx(
                priced["bounds"][label]["seconds"] / priced["step"]["used_s"]
            )
        assert priced["decision"] == (
            "section 3.4 CONFIRMED" if priced["below_bar"]
            else "section 3.4 FALLBACK FIRED"
        )


def test_the_section_3_4_decision_is_recorded_for_the_primary_target():
    """Gate DS41-C2 asks for the decision, confirmed or fired."""
    primary = [p for p in PRICED
               if "wafer-hybrid-x2-romfill" in p["rom_design"]]
    assert primary, "the primary two-wafer target was not priced"
    for priced in primary:
        assert priced["gate"] == "DS41-C2"
        assert priced["below_bar"] is True, (
            "the lookup is at or above 1% of the step, so plan section 3.4's "
            "fallback -- the ROM placement -- has fired and the placement "
            "decision has to be re-taken, not recorded as confirmed"
        )
        assert priced["decision"] == "section 3.4 CONFIRMED"
        assert priced["refusals"], "a priced result with no stated boundary"


def test_the_reserved_hbm_region_is_exactly_the_engram_tables():
    """The built wafer record reserves the tables to the byte.

    ``sum(metadata.engram.num_embeddings) x row_bytes_packed`` is
    202,758,032,400 B and ``rom_deepseek_v41_wafer.json`` declares exactly that
    as ``memory.hbm.resident_region_bytes``.  It is the one identity that ties
    the model registry to a compiled product, so it is pinned: a record that
    reserved less would be a record built for a different placement.
    """
    primary = [p for p in PRICED
               if "wafer-hybrid-x2-romfill" in p["rom_design"]]
    assert primary
    for priced in primary:
        region = priced["resident_region"]
        assert region["required_region_bytes"] == 202_758_032_400
        assert (sum(region["module_rows"]) * region["row_bytes_packed"]
                == region["required_region_bytes"])
        assert region["declared"] == region["required_region_bytes"]
        assert region["exact_as_whole_machine"] is True
        assert region["covers_as_whole_machine"] is True
        # and the tables the lookup reads are rows of that same region
        assert priced["lookup"]["row_bytes_packed"] == region["row_bytes_packed"]


def test_a_reserved_region_too_small_for_the_tables_is_refused(
        tmp_path, monkeypatch):
    """"Resident in HBM" has to be checkable, and it is checked."""
    import tools.derive_cycle_machine as dcm

    row = next(r for r in ROWS if r["cell_id"] == "TA-DS41-ROM-WAFER"
               and r["batch_size"] == 1)
    anchor = _anchor(row)
    real = json.loads(
        (REPO / "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json")
        .read_text()
    )
    real["memory"]["hbm"]["resident_region_bytes"] = 1024
    shrunk = tmp_path / "shrunk.json"
    shrunk.write_text(json.dumps(real))
    monkeypatch.setattr(
        dcm, "registered_base_capabilities",
        lambda a, rom_base=None, hbm_base=None: (
            str(shrunk), "configs/hardware/abi3_capability/hbm_sram_single_chip.json"
        ),
    )
    with pytest.raises(DerivationError) as excinfo:
        dcm.engram_resident_region(anchor, engram_lookup_shape(
            str(anchor.rom["model"])))
    assert "does not hold them" in str(excinfo.value)


def test_the_channels_priced_are_the_ones_the_machine_would_resolve():
    """``hbm.channels`` is structural: the capability wins over the table.

    A record that declares ``memory.hbm.channels`` is what
    ``runtime/cycle/machine.py`` would resolve, so pricing the derived count
    instead would price a machine nobody builds.
    """
    for priced in PRICED:
        declared = priced["machine"]["channels_declared_by_capability"]
        if declared:
            assert priced["machine"]["channels_priced"] == int(declared)
            assert "memory.hbm.channels" in priced["machine"]["channels_source"]
        else:
            assert (priced["machine"]["channels_priced"]
                    == priced["machine"]["rom_role_hbm_channels"])
        assert (priced["bounds"]["per_token_collided"]["address_stride_bytes"]
                == priced["measured_inputs"]["parameters"][
                    "hbm.interleave_bytes"]["value"]
                * priced["machine"]["channels_priced"])


def test_a_base_record_whose_node_count_is_not_the_cells_says_so():
    """The built array record is 64 nodes; no study prices a 64-node array.

    The base contributes capacities and limits only, so a 51- or 55-node design
    point still derives against it -- but the divergence has to be in the
    artifact, because a deployment lowered for one and costed as the other is
    the class of defect gate C2 exists for.
    """
    seen = 0
    for row in ROWS:
        facts = row.get("base_capability_facts")
        if not facts or not facts.get("present"):
            continue
        seen += 1
        assert isinstance(facts["node_counts_agree"], bool)
        if not facts["node_counts_agree"]:
            assert facts["node_count_note"], row["cell_id"]
            assert str(facts["max_nodes"]) in facts["node_count_note"]
        assert facts["weights_fit_declared_rom_per_node"] is True, (
            f"{row['cell_id']}: {facts['stored_weight_bytes_per_node']} B of "
            f"weights per node against {facts['rom_bytes_per_node_declared']} B "
            "of declared ROM -- the cell's placement does not fit its record"
        )
    assert seen, "no cell has a base capability record on disk to check"
    arrays = [
        r["base_capability_facts"] for r in ROWS
        if r.get("base_capability_facts", {}).get("present")
        and r.get("topology_kind") == "array"
    ]
    assert arrays, "no array cell"
    assert all(f["max_nodes"] == 64 for f in arrays), (
        "the V4.1 array record's node count moved; re-read it against the "
        "design points the studies publish before trusting the array cell"
    )
    assert all(not f["node_counts_agree"] for f in arrays), (
        "an array cell now agrees with the record's node count -- either the "
        "study gained a 64-node rung or the product was rebuilt; the plan's "
        "N = 51 and this record have to be reconciled either way"
    )


def test_the_pricing_refuses_a_design_point_that_buys_no_hbm():
    """The 51-node array holds KV in SRAM: there is no HBM path to price on."""
    row = next(r for r in ROWS
               if r["cell_id"] == "TA-DS41-ROM-ARRAY" and r["batch_size"] == 1)
    anchor = _anchor(row)
    assert anchor.rom_kv_store == "sram"
    with pytest.raises(DerivationError) as excinfo:
        price_engram_on_hbm(anchor)
    assert "no HBM" in str(excinfo.value)


def test_the_priced_channels_come_from_the_one_hbm_derivation():
    """The pricing reads the generator's own channel split, not a second one."""
    from tools.derive_cycle_machine import _hbm_split

    for priced in PRICED:
        row = next(
            r for r in ROWS
            if r.get("pair_id") == priced["pair_id"]
            and r["batch_size"] == priced["batch_size"]
        )
        anchor = _anchor(row)
        clock = derived_clock_hz(anchor)
        rom_channels, gpu_channels, per_channel = _hbm_split(
            anchor, clock, CHANNELS_PER_STACK
        )
        assert priced["machine"]["clock_hz"] == clock
        assert priced["machine"]["rom_role_hbm_channels"] == rom_channels
        assert priced["machine"]["gpu_role_hbm_channels"] == gpu_channels
        assert priced["machine"]["hbm_bytes_per_cycle_per_channel"] == per_channel


# ---------------------------------------------------------------------------
# 5.  The pins WP-J asks for, and the cost-table entries it may not add yet
# ---------------------------------------------------------------------------
def test_the_planned_pins_cover_every_registration_the_cells_require():
    """WP-J's three registrations cannot be written; what they must say can."""
    manifest = json.loads(SHIPPED_DEPLOYMENTS_MANIFEST.read_text())
    planned = manifest["planned_registrations"]
    covered = {
        (row["base_capability"], model)
        for row in planned for model in row["model_ids"]
    }
    required = {
        (req["base_capability"], req["model_id"])
        for row in ROWS for req in row.get("c2", {}).get(
            "required_registrations", [])
    }
    assert required, "no cell states the registration it would need"
    assert required <= covered, sorted(required - covered)
    registered = {
        (r["base_capability"], r["model_id"]) for r in manifest["registrations"]
    }
    for row in planned:
        assert "deployment_sha256" not in row, (
            f"{row['planned_registration_id']} carries a digest; a planned pin "
            "has no bundle and inventing one is the defect this block avoids"
        )
        assert row["pin_kind"] == "live"
        assert "PLANNED" in row["build_command_status"]
        assert row["absent_because"]
    # a planned pin that has become real must move out of the planned block
    assert not (covered & registered), sorted(covered & registered)


def test_the_five_new_blocks_are_declared_pending_and_priced_nowhere():
    """An absent cost-table entry is honest; a guessed one corrupts the table."""
    from tools.build_abi3_cost_tables import (
        DERIVED, PENDING_ROUTED_BLOCKS, ROUTED_BLOCKS, pending_report,
    )

    blocks = {
        "vector_fp4kv_dequant", "route_block_max", "route_candidate_mask",
        "dma_ngram_hash", "vector_engram_gate",
    }
    declared = {(e["view"], e["block"]) for e in PENDING_ROUTED_BLOCKS}
    assert declared == {(v, b) for v in ("asap7", "sky130") for b in blocks}
    routed = {e["block"] for e in ROUTED_BLOCKS}
    assert not (blocks & routed), (
        "a V4.1 block is in ROUTED_BLOCKS: it may only be there with a "
        "post-route fmax, and adding it moves the view's core clock"
    )
    for entry in PENDING_ROUTED_BLOCKS:
        assert (REPO / entry["rtl"]).exists(), entry["rtl"]
        assert entry["family"] in ("vector", "route", "dma")
    # and no generated table cites one of their records
    for plan in DERIVED.values():
        table = json.loads((REPO / "configs/hardware" / plan["out"]).read_text())
        text = json.dumps(table)
        for entry in PENDING_ROUTED_BLOCKS:
            for record in entry["records"]:
                assert record not in text, (
                    f"{plan['out']} cites {record}, which is still declared "
                    "pending; the two must not disagree"
                )
    for row in pending_report():
        assert row["state"] in (
            "absent", "no_post_route_fmax", "flow_incomplete", "routed",
            "routed_not_closed",
        ), row


def test_the_two_gates_this_package_must_not_break_are_green():
    """C1 and the cost-table check, run as the gates run them."""
    for argv in (
        ["tools/derive_cycle_machine.py", "--check"],
        ["tools/build_abi3_cost_tables.py", "--check"],
    ):
        done = subprocess.run(
            [sys.executable, *argv], cwd=REPO, capture_output=True, text=True,
            check=False, env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        )
        assert done.returncode == 0, (argv, done.stdout, done.stderr)
