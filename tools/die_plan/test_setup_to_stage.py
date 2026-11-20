"""tests for setup_to_stage.py (CBC rule 11)"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup_to_stage as S  # noqa: E402


def _pt(inst, cell, pin, x, y, t):
    return {"instance": inst, "cell": cell, "pin": pin, "x": x * 1e-6, "y": y * 1e-6, "arrival": t * 1e-12}


def _check(points, slack, se="rise", te="rise"):
    return {"startpoint": points[0]["pin"], "endpoint": points[-1]["pin"], "source_path": points, "slack": slack * 1e-12,
            "source_clock_edge": se, "target_clock_edge": te}


def test_bus_path_gets_stations_at_300um():
    c = _check([_pt("u_bin_x_i0", "DFF_ASAP7_75t_R", "u_bin_x_i0/Q", 0, 0, 50),
                _pt("u_g1", "BUFx4_ASAP7_75t_R", "u_g1/A", 300, 0, 300), _pt("u_g1", "BUFx4_ASAP7_75t_R", "u_g1/Y", 300, 0, 320),
                _pt("u_lpad_x_i0", "DFF_ASAP7_75t_R", "u_lpad_x_i0/D", 700, 0, 900)], -90)
    p = S.path_record(c)
    assert round(p["straight"]) == 700 and p["bufs"] == 1 and p["levels"] == 0
    rows, rtl = S.rows_from_paths([p], "s81", "t", {"buses": [{"name": "x_i0"}]})
    assert not rtl and len(rows) == 1
    r = rows[0]
    assert r["kind"] == "internal_stations_add" and r["conn"] == "bus:x_i0" and r["add_regs"] == 2 and len(r["sites_um"]) == 2


def test_core_path_relay_depth_takes_whole_bundle():
    c = _check([_pt("u_xr", "ot_s81sl_xrt1", "u_xr/eg_d[3]", 0, 0, 400), _pt("u_eg", "ot_s81sl_egg", "u_eg/g[3]", 900, 0, 1300)], -500)
    p = S.path_record(c)
    t = {"relay_depth": [{"inst": "u_xr", "port": "eg_v", "D": 1}, {"inst": "u_xr", "port": "eg_d", "D": 1}]}
    rows, _ = S.rows_from_paths([p], "s81", "t", t)
    assert {(r["port"], r["D"]) for r in rows} == {("eg_d", 3), ("eg_v", 3)}   # 900 um / 300 um -> +2 stages on D1


def test_half_cycle_cap_200():
    c = _check([_pt("u_a", "DFF_ASAP7_75t_R", "u_a/QN", 0, 0, 0), _pt("u_bout_y_o1", "DFF_ASAP7_75t_R", "u_bout_y_o1/D", 500, 0, 300)],
               -20, se="fall")
    rows, _ = S.rows_from_paths([S.path_record(c)], "qwen_compute", "t", None)
    assert rows[0]["hop_cap_um"] == 200.0 and rows[0]["add_regs"] == 2


def test_soft_logic_goes_to_rtl_request_not_a_row():
    pts = [_pt("u_m.u_a", "DFF_ASAP7_75t_R", "u_m.u_a/Q", 0, 0, 40)]
    for i in range(16):
        pts += [_pt(f"u_m.g{i}", "NAND2x1_ASAP7_75t_R", f"u_m.g{i}/A", 1, 1, 60 + 40 * i),
                _pt(f"u_m.g{i}", "NAND2x1_ASAP7_75t_R", f"u_m.g{i}/Y", 1, 1, 90 + 40 * i)]
    pts.append(_pt("u_m.u_b", "DFF_ASAP7_75t_R", "u_m.u_b/D", 2, 2, 800))
    rows, rtl = S.rows_from_paths([S.path_record(_check(pts, -60))], "s81_head", "t", None)
    assert not rows and rtl[0]["module"] == "u_m" and rtl[0]["levels"] == 16 and rtl[0]["ask"].startswith("split the cone")


def test_passing_paths_ignored_and_guard_is_not_relaxed():
    c = _check([_pt("u_bin_x_i0", "DFF_ASAP7_75t_R", "u_bin_x_i0/Q", 0, 0, 0), _pt("u_c", "DFF_ASAP7_75t_R", "u_c/D", 900, 0, 9)], 5)
    assert S.rows_from_paths([S.path_record(c)], "s81", "t", None) == ([], [])
    assert S.GUARD_PS == -42.0


def test_name_records_from_harvest_log(tmp_path):
    h = tmp_path / "H.tsv"
    h.write_text("die\ttype\thost\tkind\tbus_or_port_or_start\tend\tn_or_slack_ps\tworst_ps\tlogic_cells\tbuf_wire_cells\tmax_fanout\tarrival_ps\n"
                 "kv\tk1\te9\tworst_path:MAX\tft2_i[90]\tu_bound.u_cland_ft2_i/u_ring.sd_c[154]$_DFFE_NP_\t-62.7\t\t1\t4\t3\t653\n"
                 "head\th1\te10\tendpoint_group\tu_core.u_logic.u_xb1\tu_core.u_logic.u_xb1/wd_in[293]\t11\t-82.2\t\t\t\t\n"
                 "head\th1\te10\tworst_path:MAX\tu_core.u_seq.s_valid$_SDFF_PN0_\tu_core.u_seq.ef[40]$_SDFFE_PN0P_\t-99.5\t\t6\t3\t38\t1323\n"
                 "kv\tk1\te9\tworst_path:MAX\tu_bound.u_cland_ft3_i/q$_SDFF_PN0_\tu_bound.u_c/d$_DFF_P_\t-21.1\t\t6\t6\t13\t918\n")
    assert S.main(["harvest-rows", str(h), "--out", str(tmp_path / "o")]) == 0
    kv = json.loads((tmp_path / "o" / "rows_kv.json").read_text())
    assert [r["conn"] for r in kv["rows"]] == ["bus:ft2_i"] and kv["rows"][0]["add_regs"] == 1   # -21 passes the -42 guard
    hd = json.loads((tmp_path / "o" / "rows_head.json").read_text())
    assert [(r["kind"], r["inst"], r["port"], r.get("side")) for r in hd["rows"]] == [("relay_depth", "u_core.u_logic.u_xb1", "wd_in", "sink")]
    assert hd["rtl_requests"][0]["module"] == "u_core.u_seq"


def test_session_cut_and_dump_cmd():
    s = S.session_cut("read_db /base/6_final.odb\nread_spef x\nreport_checks -path_delay max -format full\nmore\n", -42, 100)
    assert "report_checks -path_delay max -group_path_count 100" in s and "-slack_max -42.0" in s and "more" not in s
    c = S.dump_cmd("docker run --rm --name so_1 -v /k/so/tt:/out -v /k:/work:ro img openroad -exit /out/session.tcl", "/d/o")
    assert "-v /d/o:/out " in c and "/out/sts_session.tcl" in c and "so_1" not in c
