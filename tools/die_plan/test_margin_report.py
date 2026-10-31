"""MARGIN-REPORT (FLOW-13, OWNER 12.24c): NOMINAL vs MARGINS Tcl, parsing, TSV, min period, die-clock argv (no EDA)."""
import json
import re
import subprocess

import margin_report as MR

SDC = """create_clock -name clk -period 833.0000 [get_ports {clk}]
create_clock -name vclk -period 833.0000
set_clock_uncertainty 60.0000 -setup [all_clocks]
set_clock_uncertainty 25.0000 -hold [all_clocks]
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000
set_clock_uncertainty -from [get_clocks clk] -to [get_clocks vclk] -setup 30.0000
set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -hold 12.5000
"""


def _split(tcl):
    i = tcl.index("# ==== RUN NOMINAL")
    j = tcl.index("# ==== RUN MARGINS")
    return tcl[i:j], tcl[j:]


def _session(corner):
    pairs = MR.sdc_inter_clock_pairs(SDC)
    ms = MR.margin_set(corner, stages=6, extent_um=1000.0)
    return MR.session_tcl(corner, ms, pairs), ms


def test_sdc_reading():
    assert MR.sdc_inter_clock_pairs(SDC) == [("vclk", "clk"), ("clk", "vclk")]
    assert MR.sdc_period_ps(SDC) == 833.0


def test_margin_values_come_from_shared_models():
    ms = MR.margin_set("TT", stages=6, extent_um=1000.0)
    assert ms["spice_clock_cal"] == 1.0485 and MR.margin_set("FF")["spice_clock_cal"] == 1.0552
    assert ms["data_cell_late"] == 1.10 and ms["data_net_late"] == 1.05          # data_droop class TT
    o = ms["ocv"]
    assert o["table"] == "clk_aocv_table_g021.json" and o["g_per_mm"] == 0.0021
    assert abs(o["sys_frac"] - 0.0021 * 1.0 / 2) < 1e-9                          # g d / 2 at d = 1 mm
    # the flat equivalent at (N = 6, d = 0) reproduces the approved table row A_TT depth 6 (1.0476)
    assert abs(MR.clock_ocv("TT", 6, 0.0)["cell_late"] - 1.0476) < 5e-5
    assert abs(ms["clock_cell_late"] - 1.0485 * o["cell_late"]) < 1e-4
    assert abs(ms["clock_net_late"] - 1.0485 * 1.03) < 1e-4
    # FF: no data droop (setup only)
    ff = MR.margin_set("FF", stages=6, extent_um=1000.0)
    assert ff["data_droop"] == {"logic": 0.0, "wire": 0.0}


def test_tcl_margins_only_in_margins_run():
    tcl, ms = _session("TT")
    nom, mar = _split(tcl)
    # NOMINAL: setup uncertainty 0 everywhere, no derate at all
    assert "set_clock_uncertainty -setup 0 [all_clocks]" in nom
    assert "-to [get_clocks {clk}] -setup 0" in nom and "-to [get_clocks {vclk}] -setup 0" in nom
    assert not re.search(r"^set_timing_derate", nom, re.M) and "unset_timing_derate" in nom and "-setup 60" not in nom
    # MARGINS: 60 ps setup (30 on the seam pairs), clock spice x OCV on cells + nets, data droop
    assert "set_clock_uncertainty -setup 60 [all_clocks]" in mar
    assert "-to [get_clocks {clk}] -setup 30" in mar
    for k, flag in (("clock_cell_late", "-clock -cell_delay -late"), ("clock_cell_early", "-clock -cell_delay -early"),
                    ("clock_net_late", "-clock -net_delay -late"), ("clock_net_early", "-clock -net_delay -early"),
                    ("data_cell_late", "-data -cell_delay -late"), ("data_net_late", "-data -net_delay -late")):
        assert f"set_timing_derate {flag} {ms[k]:.5f}" in mar, flag
    assert "set_timing_derate -data -cell_delay -late 1.10000" in mar
    assert "set_timing_derate -data -net_delay -late 1.05000" in mar
    assert "1.0485" in mar
    # FF session: clock derates but no data droop
    _nf, mf = _split(_session("FF")[0])
    assert "-clock -cell_delay -late" in mf and "-data -" not in mf


def test_hold_uncertainty_25_both_runs_and_corners():
    for c in ("TT", "FF"):
        nom, mar = _split(_session(c)[0])
        for t in (nom, mar):
            assert "set_clock_uncertainty -hold 25 [all_clocks]" in t
            assert re.findall(r"-hold (\S+)", t) == ["25"]


def test_session_loads_routed_db_spef_sdc_exact_libs():
    tcl = _session("TT")[0]
    assert "ot_lib_load TT /out/libraries_tt.json" in tcl and "proc ot_lib_resolve" in tcl
    assert "read_db /base/6_final.odb" in tcl and "read_spef /base/6_final.spef" in tcl
    assert "read_sdc /sdc/golden.sdc" in tcl and "set_propagated_clock [all_clocks]" in tcl
    rcx = MR.session_tcl("FF", MR.margin_set("FF"), [], odb="5_route.odb", spef=False)
    assert "extract_parasitics" in rcx and "read_db /base/5_route.odb" in rcx


LOG_TT = """noise
MR CORNER TT
MR NOMINAL_WNS_MAX -8.92
MR NOMINAL_WNS_MIN 23.98
MR NOMINAL_TNS_MAX -357.37
MR NOMINAL_TNS_MIN 0.00
MR NOMINAL_NVIOL_MAX 60
MR NOMINAL_NVIOL_MIN 0
MR MARGINS_WNS_MAX -51.56
MR MARGINS_WNS_MIN 3.57
MR MARGINS_TNS_MAX -16558.71
MR MARGINS_TNS_MIN 0.00
MR MARGINS_NVIOL_MAX 566
MR MARGINS_NVIOL_MIN 0
MR DONE 1
"""
LOG_FF = """MR CORNER FF
MR NOMINAL_WNS_MAX -20.55
MR NOMINAL_WNS_MIN 6.51
MR NOMINAL_TNS_MIN 0.00
MR MARGINS_WNS_MAX -49.45
MR MARGINS_WNS_MIN -0.16
MR MARGINS_TNS_MIN -0.16
MR DONE 1
"""


def test_parse_canned_report_to_json_and_tsv(tmp_path):
    tt, ff = MR.parse_log(LOG_TT), MR.parse_log(LOG_FF)
    assert tt["done"] and tt["NOMINAL"]["wns_max"] == -8.92 and ff["MARGINS"]["wns_min"] == -0.16
    rec = MR.core_result(tt, ff, 833.0, dict(design="dp_x", db_path="/b/6_final.odb", out=str(tmp_path)))
    json.dumps(rec)
    n, m = rec["runs"]["nominal"], rec["runs"]["margins"]
    assert (n["setup_wns_ps"], n["hold_wns_ps"], n["verdict"]) == (-8.92, 6.51, "FAIL")
    assert (m["setup_wns_ps"], m["hold_wns_ps"], m["verdict"]) == (-51.56, -0.16, "FAIL")
    assert rec["min_period_ps"] == 884.56 and rec["margin_cost_setup_ps"] == 42.64
    p = MR.append_tsv(tmp_path / "MARGIN-REPORT-X.tsv", MR.tsv_row(rec, "dp_x", "h:/b/6_final.odb", "core", "n"))
    MR.append_tsv(p, MR.tsv_row(rec, "dp_x", "h:/b/6_final.odb", "core", "n"))
    lines = p.read_text().splitlines()
    assert lines[0].split("\t") == list(MR.TSV_COLS) and len(lines) == 3          # header once
    row = dict(zip(MR.TSV_COLS, lines[1].split("\t")))
    assert row["mode"] == "core" and row["nominal_setup_wns"] == "-8.92" and row["margins_hold_wns"] == "-0.16"
    assert row["margins_pass"] == "FAIL" and row["min_period_ps"] == "884.56" and row["design"] == "dp_x"


def test_min_period_math():
    assert MR.min_period_ps(833.0, -51.56) == 884.56
    assert MR.min_period_ps(833.0, 20.0) == 813.0
    assert MR.min_period_ps(833.0, None) is None
    tt = MR.parse_log(LOG_TT.replace("MARGINS_WNS_MAX -51.56", "MARGINS_WNS_MAX 5.00"))
    ff = MR.parse_log(LOG_FF.replace("MARGINS_WNS_MIN -0.16", "MARGINS_WNS_MIN 1.00"))
    rec = MR.core_result(tt, ff, 833.0, {})
    assert rec["runs"]["margins"]["verdict"] == "PASS" and rec["min_period_ps"] == 828.0


def test_def_extent(tmp_path):
    d = tmp_path / "6_final.def"
    d.write_text("VERSION 5.8 ;\nUNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( 300000 400000 ) ;\n")
    assert MR.def_extent_um(d) == 500.0
    assert MR.def_extent_um(tmp_path / "none.def") is None


ARGS = ["proof", "--plan", "plan.json", "--out", "o", "--clock-cal", "spice_cell", "--data-droop=flat", "--count-align",
        "ca.json", "--pair-unc", "u.json"]


def test_die_clock_argv_with_margin_policy():
    nom, mar, notes = MR.die_clock_argv(ARGS, "R", True)
    assert nom == ["proof", "--plan", "plan.json", "--clock-cal", "spice_cell", "--data-droop=flat", "--count-align",
                   "ca.json", "--pair-unc", "u.json", "--out", "R/nominal"]           # as given (policy nominal)
    assert mar == ["proof", "--plan", "plan.json", "--count-align", "ca.json", "--margin-policy", "legacy",
                   "--clock-cal", "spice", "--clock-ocv", "table", "--clock-droop", "shared", "--data-droop", "class",
                   "--out", "R/margins"]
    assert any("--pair-unc" in n for n in notes)


def test_die_clock_argv_without_margin_policy():
    nom, mar, notes = MR.die_clock_argv(ARGS[:5], "R", False)
    assert nom == ["proof", "--plan", "plan.json", "--clock-cal", "none", "--clock-ocv", "none", "--data-droop", "none",
                   "--out", "R/nominal"]
    assert "--margin-policy" not in mar and mar[-2:] == ["--out", "R/margins"]
    assert mar[3:11] == MR.LEGACY_EXPLICIT


def _gate(setup, hold, v):
    return dict(tt_setup_ps=setup, ff_hold_margin_ps=hold, verdict=v)


def test_die_clock_run_mocked(tmp_path, monkeypatch):
    script = tmp_path / "die_sta_related.py"
    script.write_text("# fake with --margin-policy\n")
    calls = []

    def fake_call(cmd):
        calls.append(cmd)
        out = cmd[cmd.index("--out") + 1]
        nominal = out.endswith("nominal")
        s = dict(intra=_gate(40.0 if nominal else -12.5, 9.0 if nominal else 3.0, "PASS" if nominal else "FAIL"),
                 seam=_gate(55.0 if nominal else 20.0, 15.0, "PASS"),
                 landed=dict(tt_setup_margin_ps=None, ff_hold_margin_ps=None, verdict="N/A"),
                 period_policy=dict(verdict="PASS"))
        (tmp_path / "R" / out.split("/")[-1]).mkdir(parents=True, exist_ok=True)
        (tmp_path / "R" / out.split("/")[-1] / "die_sta_related.json").write_text(json.dumps(dict(summary=s)))
        return 0

    monkeypatch.setattr(subprocess, "call", fake_call)
    tsv = tmp_path / "t.tsv"
    rc = MR.main(["die-clock", "--die", "S81", "--die-sta", str(script), "--out", str(tmp_path / "R"),
                  "--tsv", str(tsv), "--", "proof", "--plan", "p.json", "--out", "ignored"])
    assert rc == 0 and len(calls) == 2
    assert "--margin-policy" in calls[1] and "legacy" in calls[1] and "--margin-policy" not in calls[0]
    rec = json.loads((tmp_path / "R" / "margin_report.json").read_text())
    assert rec["runs"]["nominal"]["setup_wns_ps"] == 40.0 and rec["runs"]["nominal"]["verdict"] == "PASS"
    assert rec["runs"]["margins"]["setup_wns_ps"] == -12.5 and rec["runs"]["margins"]["verdict"] == "FAIL"
    assert rec["runs"]["margins"]["hold_wns_ps"] == 3.0
    assert rec["min_period_ps"] == 845.5
    row = dict(zip(MR.TSV_COLS, tsv.read_text().splitlines()[1].split("\t")))
    assert row["mode"] == "die_clock" and row["margins_pass"] == "FAIL" and row["min_period_ps"] == "845.50"
    assert row["db_path"] == "proof" and row["design"] == "S81"


def test_core_emit_only_local(tmp_path, monkeypatch):
    kit = tmp_path / "kit"
    base = kit / "run" / "results" / "asap7" / "dp_x" / "base"
    base.mkdir(parents=True)
    (kit / "config.mk").write_text("export DESIGN_NAME = x\n")
    (kit / "constraint.sdc").write_text(SDC)
    for n in ("6_final.odb", "6_final.spef"):
        (base / n).write_text("")
    (base / "6_final.def").write_text("UNITS DISTANCE MICRONS 1000 ;\nDIEAREA ( 0 0 ) ( 600000 800000 ) ;\n")
    called = []
    monkeypatch.setattr(subprocess, "call", lambda *a, **k: called.append(a) or 0)
    rc = MR.main(["core", "--run-dir", str(kit / "run"), "--die", "X", "--host", "local", "--emit-only",
                  "--out", str(tmp_path / "o"), "--no-tsv"])
    assert rc == 0 and not called
    tt = (tmp_path / "o" / "margin_tt.tcl").read_text()
    assert "d=1000.0 um" in tt and "-setup 30" in tt
    cmd = (tmp_path / "o" / "cmd_tt.sh").read_text()
    assert "--memory 16g" in cmd and "openroad/orfs:asap7lock" in cmd and ":/work/config.mk:ro" in cmd
