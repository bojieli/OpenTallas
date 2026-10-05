"""The package lane split (tools/arch_lanes_v41.py): per-peer link bytes cost the rack's split real time, the adopted
split is never slower than the rack's at batch 1, and SerDes static power is on both machines."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/arch/v41_lanes.json"


@pytest.fixture(scope="module")
def rec():
    return json.loads(REC.read_text())


def test_every_split_uses_the_package_lanes(rec):
    for r in rec["grid"]:
        assert r["tp"] + 2 * r["stage"] + r["switch"] + r["spare"] == rec["lanes_per_package"]


def test_rack_split_is_slower_than_the_overlap_assumption(rec):
    ref, rack = rec["ladder_top_overlap_assumed"]["1048576"], rec["rack_split_result"]["1048576"]
    assert rack["ar"] < ref["ar"] and rack["mtp"] < ref["mtp"]


def test_adopted_split_not_slower_than_rack(rec):
    assert rec["best_adopted"]
    for c in ("1048576", "200000"):
        for k in ("ar", "mtp"):
            assert rec["best_split"][c][k] >= rec["rack_split_result"][c][k] * (1 - 1e-4)


def test_serdes_static_on_both_machines(rec):
    s = rec["static_w"]
    assert s["rom_serdes"] > 3000 and s["rom_switch_w"] > 0   # the HBM side is in v41_hbm_switched.json
    for c, rows in rec["energy"].items():
        for k, v in rows.items():
            assert v["ratio_energy_with_static"] > 1.5, (c, k)


def test_headline_is_the_measured_collective_exposure_with_the_levers(rec):
    """Gate C7 measured NOT MET: design_point_no_levers (the ablation) prices the RTL stage bench's exposed tails and
    sits below the overlap-assumed (conditional) point at both contexts, with and without MTP; design_point (the
    headline) re-prices it with the adopted levers' bench tails and recovers part of the loss without MTP."""
    cx = rec["collective_exposure"]
    assert cx["status"].startswith("NOT MET")
    assert set(cx["terms"]) == {"all_reduce", "all_gather_small", "all_gather_select", "all_gather_rows", "hop"}
    assert set(cx["levers"]["terms"]) == set(cx["terms"]) | {"hop_mtp"} and cx["levers"]["consumers"] == ["hc_post"]
    for c in ("1048576", "200000"):
        d, n, o = rec["design_point"][c], rec["design_point_no_levers"][c], rec["design_point_overlap_assumed"][c]
        assert n["ar"] < o["ar"] and n["mtp"] < o["mtp"]
        assert n["ar"] < d["ar"] < o["ar"] and d["mtp"] > n["mtp"]
        assert 0.05 < cx["loss_no_levers"][c]["ar"] < 0.25
        assert 0.0 < cx["recovered_share"][c]["ar"] < 1.0
        assert o["ar"] == rec["best_split"][c]["ar"]            # the conditional point is the adopted split's row


def test_energy_rows_are_at_the_headline(rec):
    for c in ("1048576", "200000"):
        assert abs(rec["energy"][c]["b1"]["rom"]["tokens_s_per_user"] - rec["design_point"][c]["ar"]) < 1e-6
        assert abs(rec["energy"][c]["b1_mtp"]["rom"]["tokens_s_per_user"] - rec["design_point"][c]["mtp"]) < 1e-6


def test_exposure_record_agrees_with_the_ablation(rec):
    x = json.loads((ROOT / "results/arch/v41_collective_exposure.json").read_text())
    assert x["terms"] == rec["collective_exposure"]["terms"]
    for c in ("1048576", "200000"):
        assert abs(x["design_point_rates"][c]["measured_exposure"]["ar"] - rec["design_point_no_levers"][c]["ar"]) < 1e-6
        assert abs(x["design_point_rates"][c]["overlap_assumed"]["ar"]
                   - rec["design_point_overlap_assumed"][c]["ar"]) < 1e-6


def test_lever_record_agrees_with_the_headline(rec):
    lv = json.loads((ROOT / "results/arch/v41_collective_levers.json").read_text())
    for c in ("1048576", "200000"):
        for k in ("ar", "mtp", "T_us"):
            assert abs(lv["scenarios"]["recommended"]["rates"][c][k] - rec["design_point"][c][k]) < 1e-6
            if k != "T_us":
                assert abs(lv["scenarios"]["measured_baseline"]["rates"][c][k]
                           - rec["design_point_no_levers"][c][k]) < 1e-6
                assert abs(lv["recovered_share_of_overlap_loss"][c][k]
                           - rec["collective_exposure"]["recovered_share"][c][k]) < 1e-9


def test_campaign_record_binds_the_sources_on_disk(rec):
    b = rec["collective_exposure"]["campaign_binding"]
    assert b["pinned"] and b["current"], b["stale"]
    b = rec["collective_exposure"]["levers"]["campaign_binding"]
    assert b["pinned"] and b["current"], b["stale"]


def test_mtp_carries_the_draft_conditioning_transfer(rec):
    dc = rec["draft_conditioning"]
    assert dc["bytes_per_verify"] == 3 * 5120 * 2 * 6
    assert abs(dc["seconds"] - (dc["bytes_per_verify"] / dc["link_Bps"] + dc["bytes_per_verify"] / dc["ucie_Bps"])) < 1e-15
    for c in ("1048576", "200000"):
        assert abs(rec["energy"][c]["b1_mtp"]["draft_conditioning_us"] - dc["seconds"] * 1e6) < 1e-9
        assert rec["energy"][c]["b1"]["draft_conditioning_us"] == 0.0


def test_fill_drafts_share_the_head_group(rec):
    for c in ("1048576", "200000"):
        f = rec["energy"][c]["fill28_mtp"]
        dc = f["draft_contention"]
        assert dc["drafts_in_flight"] > 1.0 and dc["contended_draft_s"] > dc["isolated_draft_s"]
        assert max(dc["head_unit_load"].values()) < 1.0 and dc["throughput_cap"] == 1.0
        # a filled pipeline with contended drafts is slower per user than one user alone
        assert f["rom"]["tokens_s_per_user"] < rec["design_point"][c]["mtp"]
        assert rec["energy"][c]["b1_mtp"]["draft_contention"] is None


def test_every_aggregate_is_capped_at_its_busiest_link(rec):
    for c in ("1048576", "200000"):
        for k, v in rec["energy"][c].items():
            lk = v["link_cap"]
            assert max(lk["utilisation"].values()) <= 1.0 + 1e-9, (c, k)
            assert abs(v["rom"]["aggregate_tokens_s"] - lk["aggregate_tokens_s_uncapped"] * lk["cap"]) < 1e-6
        # the saturated MTP point is bound by its busiest pipeline STAGE before any package link
        # (arch_budget_v41.stage_bound): the link cap no longer binds there
        sat = rec["energy"][c]["sat1024_mtp"]["link_cap"]
        assert not sat["binds"] and max(sat["utilisation"].values()) < 1.0


def test_on_die_wire_is_charged_on_the_dag(rec):
    """The headline carries the registered on-die traversals of the layer die's floorplan (ASAP7 routed-wire
    model); the pre-wire point is the one ablation; 150 / 250 ps/mm are sensitivities between the two."""
    ow = rec["on_die_wire"]
    assert ow["model"] == "asap7_routed_fit"
    for c in ("1048576", "200000"):
        d, pre = rec["design_point"][c], ow["design_point_pre_wire"][c]
        s150, s250 = ow["sensitivities"]["tech_global_wire"][c], ow["sensitivities"]["tech_global_wire_high"][c]
        assert d["ar"] < s250["ar"] < s150["ar"] < pre["ar"]
        assert d["mtp"] < s250["mtp"] < s150["mtp"] < pre["mtp"]
        att = ow["attribution"][c]["ar"]
        assert att["exposed_us"] > 0 and att["exposed_us"] <= att["charged_in_full_us"] + 1e-9
        assert abs(d["breakdown_us"]["on_die_wire"] - att["exposed_us"]) < 1e-3       # breakdown rounds to ns
        # the cycles follow the distances at the reach
        cyc = ow["cycles"]["asap7_routed_fit"]
        assert cyc["far_tile"] >= cyc["hbm_to_tile"] and cyc["far_tile"] > cyc["in_tile"]


def test_mtp_hop_split_is_bench_measured(rec):
    import sys
    """Lever 5: the verify pass's hop carries the shortest MEASURED 6-position tail at fill 1 (no interpolation);
    the one-position hop keeps split20."""
    t = rec["mtp_hop_split"]["term"]
    assert t["scheme"] in t["tails_measured"] and t["measured_tail_cycles"] == min(t["tails_measured"].values())
    assert t["measured_tail_cycles"] < t["proportional_tail_cycles"] < t["full_payload_tail_cycles"]
    assert rec["collective_exposure"]["levers"]["terms"]["hop_mtp"]["scheme"] == t["scheme"]
    sys.path.insert(0, str(ROOT / "tools"))
    import v41_collective_exposure as VX
    b = VX.campaign_binding(None, VX.HOP_BATCH_CAMPAIGN)
    assert b["current"], b["stale"]


def test_saturated_points_hold_only_the_users_held(rec):
    import sys
    sys.path.insert(0, str(ROOT / "tools"))
    import arch_budget_v41 as A
    for c in ("1048576", "200000"):
        for k in ("sat1024", "sat1024_mtp"):
            e = rec["energy"][c][k]
            assert e["batch"] == min(1024, e["users_held"]) == A.point_batch(k, 1024, int(c))
        assert not rec["energy"][c]["fill28_mtp"]["link_cap"]["binds"]
