"""Fast checks of the committed V4.1 die engine profile (no re-elaboration: the full run takes ~3 min)."""
import json
from pathlib import Path

import pytest

from tools import v41_rtl_engine_profile as P

ROOT = Path(__file__).resolve().parents[1]
REC = json.loads(P.OUT.read_text())


def test_source_and_record_pins_are_current():
    assert P.check() == []


def test_source_closure_is_reproducible():
    srcs, incs = P.resolve_sources()
    assert srcs + incs == REC["source_files"]
    assert P.TOP_FILE in srcs


def test_elaboration_identity():
    e = REC["elaboration"]
    assert "5.050" in e["tool"] and "--json-only" in e["command"]
    assert REC["parameter_overrides"] == {"FULL_SHAPE": 1}
    assert REC["top_parameters_resolved"]["FULL_SHAPE"] == 1


def test_counts_are_consistent():
    s = REC["summary"]
    assert s["instances_total"] == sum(m["instances"] for m in REC["modules"])
    assert s["instances_total"] == sum(p["instances"] for p in REC["instance_paths"])
    assert s["instances_total"] == sum(r["instances"] for r in REC["regions"].values())
    for m in REC["modules"]:
        assert m["instances"] == sum(x["instances"] for x in m["specialisations"])
    assert s["memory_arrays"] == len(REC["memories"])
    assert s["behavioural_memory_bytes_total"] == sum(m["total_bits"] for m in REC["memories"]) // 8
    for m in REC["memories"]:
        assert m["bits"] == m["word_bits"] * m["words"]
        assert sum(m["regions"].values()) == m["instances"]
    assert set(P.REGIONS) <= set(REC["regions"])


def test_engine_lanes_follow_leaf_counts():
    for e in REC["engines"]:
        assert e["mac_lanes_per_cycle_as_instantiated"] == e["leaf_instances"] * e["macs_per_leaf_per_cycle"]
        assert e["region"] in P.REGIONS
    s = REC["summary"]
    lanes = s["mac_lanes_per_cycle"]
    assert s["block_dot_macs_per_cycle_dispatched"] == lanes["qe_blockdot"] + lanes["idx_blockdot_fp4"]
    assert s["sram_or_rom_macro_instances"] == 0
    assert (s["collective_engines"], s["package_controllers"], s["fabric_routers"]) == (1, 1, 1)


def test_ledger_gaps_are_listed_not_substituted():
    by = {r["block"]: r for r in REC["analytical_comparison"]}
    inv = json.loads((ROOT / P.INVENTORY).read_text())
    assert set(by) == {r["block"] for r in inv["analytical_assembly_reference"]["rows"]}
    gaps = {g["block"] for g in REC["gaps_analytical_without_rtl_instance"]}
    assert gaps == {b for b, r in by.items() if r["status"] == "gap_no_rtl_instance"}
    assert "package link endpoint" in gaps
    assert by["one-shot collective engine (128 lanes)"]["rtl_instances"] == 1
    assert by["block-dot pool (FP8/FP4 weights + FP4 indexer)"]["analytical_lanes_per_cycle"] == 1059840


def test_inventory_cross_checks_present():
    xs = REC["inventory_rtl_instances_cross_check"]
    inv = json.loads((ROOT / P.INVENTORY).read_text())
    assert [x["inventory_path"] for x in xs] == [r["path"] for r in inv["rtl_instances"]]
    assert not next(x for x in xs if x["inventory_path"] == "u_kv")["agrees"]
    assert len(REC["inventory_memories_cross_check"]) == len(inv["rtl_behavioral_memories"])


def test_d1_proposal_has_options_and_awaits_root():
    d = REC["d1_decision_proposal"]
    assert d["status"] == "proposal_awaiting_root_decision"
    assert {o["id"] for o in d["options"]} >= {"A", "B", "C", "D"}
    for o in d["options"]:
        assert {"counts", "layer0_collective_cycles", "area_um2", "verdict"} <= set(o)
    dec = d["schedule_need"]["layer0_decomposition_cycles"]
    assert sum(dec.values()) == d["schedule_need"]["layer0_measured_blocked_cycles"]
    assert d["schedule_need"]["concurrently_outstanding_collectives"] == 1
    rec = d["recommendation"]
    assert (rec["collective_engines"], rec["package_controllers"], rec["fabric_routers"]) == (1, 1, 1)


@pytest.mark.parametrize("key", ["sequence", "oneshot_d32", "pkg_ctrl", "fabric_router"])
def test_d1_records_pinned(key):
    assert P.D1_RECORDS[key] in REC["d1_decision_proposal"]["records_sha256"]
