"""C-LEG405 cover (P-FALSE-GREEN, HEAD hd_host_w 11-26): LEG405-STAGED must not pass vacuously on a landing_reader_start type with no relay_depth."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_fpconv as F  # noqa: E402


def host_w():
    return {"partition_types": {"hd_host_w": {
        "outline_um": [740.0, 570.0],
        "hard_cores": [{"inst": "u_core.sf.u_m", "module": "m", "origin_um": [300.0, 300.0], "outline_um": [30.0, 40.0]}],
        "relay_sites": {"u_core.a": [400.0, 300.0], "u_core.b": [10.0, 10.0]},
        "clock": {
            "landing_contract": {
                "pins": [{"name": "cland_fstart_in_coll_i0", "xy_um": [2.0, 231.0]},
                         {"name": "cland_dn_ready_l1_rx_i", "xy_um": [732.0, 290.0]}],
                "collector_children": [{"bus": "l1_rx_i", "xy": [734.0, 286.0], "seam": False}]},
            "landing_reader_start": {"depth": 1, "origin_rect_um": [440.0, 550.0, 460.0, 570.0],
                                     "branches": {"coll_i0": {"stages": [{"xy_um": [300.0, 450.0]}, {"xy_um": [131.0, 307.0]}]}}},
            "landing_status_anchors": {"u_cland_agg_1": [40.0, 210.0]}}}}}


def lines(raw):
    return F.findings_by_check["LEG405-STAGED"](raw, "p.json")


def old_staged(t):          # the pre-cover body: relay_depth rows + cland_reader_legs only
    return [(r.get("inst"), r.get("port"), r.get("path_um"), r.get("D"), F.staged_short(r)) for r in t.get("relay_depth") or []
            if isinstance(r, dict) and F.staged_short(r)] + [h + (1,) for h in F.cland_reader_legs(t)]


def reports_status_leg(raw, staged=F.leg405_staged):
    return any(h[0].startswith("status:") and h[2] > 405 for h in staged(raw["partition_types"]["hd_host_w"]))


def test_host_w_like_reports_unstaged_status_leg_and_unchecked_kinds():
    raw = host_w()
    out = lines(raw)
    assert any("status:agg/l1_rx_i(unstaged)" in x and "772" in x for x in out), out
    unc = [x for x in out if x.startswith("WARN LEG405-STAGED-UNCHECKED hd_host_w:")]
    assert len(unc) == 1 and "macro-pin-to-pin" in unc[0] and "relay_sites" in unc[0]
    summ = [x for x in out if "summary" in x][0]
    assert "reader_start=3" in summ and "status_stage=1" in summ and "1 type(s) carry legs" in summ


def test_staged_status_leg_measured_and_clean_when_hops_short():
    raw = host_w()
    ck = raw["partition_types"]["hd_host_w"]["clock"]
    ck["landing_status_input_stages"] = {"agg": {"l1_rx_i": [{"xy_um": [604.0, 312.0]}, {"xy_um": [324.0, 274.0]}]}}
    assert not reports_status_leg(raw)
    flagged = [x for x in lines(raw) if "LEG405-STAGED hd_host_w" in x]
    assert flagged == []                         # 150 + 318 + 349 um hops
    ck["landing_status_input_stages"]["agg"]["l1_rx_i"] = [{"xy_um": [604.0, 312.0]}]   # last stage 564 um from agg
    assert reports_status_leg(raw)


def test_start_chain_hops_measured():
    raw = host_w()
    st = raw["partition_types"]["hd_host_w"]["clock"]["landing_reader_start"]["branches"]["coll_i0"]["stages"]
    st[:] = [{"xy_um": [20.0, 450.0]}]          # origin (450,560) -> stage 540 um, stage -> pin 220 um
    h = [x for x in F.leg405_staged(raw["partition_types"]["hd_host_w"]) if x[0].startswith("reader_start:")]
    assert len(h) == 1 and h[0][2] > 405 and h[0][4] == 1


def test_macro_pin_pair_over_810_with_one_stage_is_impossible_and_bare_pair_flagged():
    t = {"internal_stations": [{"conn": "reg:a|reg:b", "from_um": [0, 0], "to_um": [900, 0], "regs_um": [[450, 0]]},
                               {"conn": "reg:c|reg:d", "from_um": [0, 0], "to_um": [420, 0], "regs_um": []},
                               {"conn": "reg:e|reg:f", "from_um": [0, 0], "to_um": [700, 0], "regs_um": [[350, 0]]}]}
    f = F.leg405_staged(t)
    assert any("IMPOSSIBLE" in x[0] for x in f) and any("reg:c|reg:d" in x[0] for x in f)
    assert not any("reg:e|reg:f" in x[0] for x in f)


def test_relay_depth_behaviour_unchanged():
    t = {"relay_depth": [{"inst": "u", "port": "o", "path_um": 700.0, "stages_existing": 0, "D": 1},
                         {"inst": "v", "port": "o", "path_um": 898.5, "stages_existing": 0, "D": 1}]}
    assert [x[0] for x in F.leg405_staged(t)] == ["v"]
    assert F.leg405_unchecked(t, {}) == []


def test_mutant_old_vacuous_code_fails_the_new_check():
    raw = host_w()
    assert reports_status_leg(raw)                                   # new code sees the 771 um status leg
    assert old_staged(raw["partition_types"]["hd_host_w"]) == []     # old code: vacuous pass ...
    assert not reports_status_leg(copy.deepcopy(raw), staged=old_staged)   # ... so this very assertion fails on the mutant


def test_transit_local_status_follows_emitted_collector_stages():
    t = {"clock": {
        "landing_contract": {"pins": [{"name": "cland_up_ready_d_o", "xy_um": [2.144, 354.016]}]},
        "landing_status_input_stages": {"d_o": {"d_i": [{"xy_um": [1215, 320]}, {"xy_um": [1050, 275]}]}},
        "landing_status_anchors": {
            "u_cland_loc_d_o_1": [720, 300],
            "u_cland_loc_d_o_2": [490, 320],
            "u_cland_loc_d_o_3": [250, 340],
        },
    }}
    findings, count = F.leg405_measure(t)
    assert findings == []
    assert count["status_stage"] == 5

    t["clock"]["landing_status_anchors"]["u_cland_loc_d_o_1"] = [600, 300]
    assert ("status:d_o/d_i.s1", "d_o", 475, 0, 1) in F.leg405_staged(t)


def test_aggregate_face_uses_first_stage_even_if_second_stage_is_closer():
    raw = host_w()
    ck = raw["partition_types"]["hd_host_w"]["clock"]
    ck["landing_status_anchors"]["u_cland_agg_2"] = [700, 280]
    assert reports_status_leg(raw)


def test_writer_first_leg_lower_bound_uses_both_window_edges():
    t = {"outline_um": [1071.36, 1408.32], "clock": {
        "landing_reader_start": {"origin_rect_um": [221.36, 591.36, 238.64, 608.64], "branches": {}},
        "landing_writer_start": {"branches": {
            "fault_o0": {"stages": [{"xy_um": [639.08, 618.66]}]},
            "lw_o": {"stages": [{"xy_um": [646.65, 618.66]}]},
        }},
    }}
    assert F.writer_start_firm_lower_bounds(t) == [("fault_o0", 406.14), ("lw_o", 413.71)]
    t["clock"]["landing_writer_start"]["branches"]["fault_o0"]["stages"][0]["xy_um"][0] -= 10
    assert F.writer_start_firm_lower_bounds(t) == [("lw_o", 413.71)]
