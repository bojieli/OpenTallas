"""contract_v1 pilot (TYPE-CONTRACT-SPEC, FABLE-RC-ALL 51358d36 five changes): report-only type contract, kit content hash, census."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import type_contract as TC  # noqa: E402


def _plan():
    return {
        "clock": {
            "common_latency_ps": 250,
            "tap_offset": {"per_port_ps": {}, "source": "historical provenance: /x/plan.json"},
            "tap_window": {"window_ps": 180.0, "per_type_ps": {"A": 60}, "per_port_ps": {"A": {"clk": 20, "clk_t1": 40, "clk_c0": 30}}},
        },
        "partition_types": {
            "A": {
                "module": "m_a", "outline_um": [100, 100], "note": "free text",
                "verilog_defines": ["OT_X=1"],
                "ft_slots": [{"name": "ft0", "stations": 4, "width": 8}],
                "internal_stations": [{"regs_um": [[1, 1], [2, 2], [3, 3]]}],
                "relay_depth": [{"D": 2, "stages_existing": 1, "inst": "u_r"}],
                "relay_sites": {"u_r": [[5, 5]]},
                "reset": {"sync_stages": 2},
                "clock": {
                    "core_taps": "early", "insertion_ps": 450, "layer": "M9", "tap_mode": "explicit",
                    "taps": [{"name": "clk", "xy": [10.0, 10.0]}, {"name": "clk_t1", "xy": [50.0, 50.0]},
                             {"name": "u_c.ck", "xy": [70.0, 20.0], "kind": "core", "insertion_ps": 700.0,
                              "insertion_ff_ps": 560.0, "budget_owner": "signed /x/y.json"}],
                    "landing_reader_start": {"depth": 5, "branches": {"ft0_i": {"stages": [{"raw_reset": "rst_n_t17", "xy_um": [1, 2]}]}}},
                },
            },
        },
    }


def test_entries_keyed_by_site_and_core_pin_not_tap_name():
    c = TC.contract(_plan(), "A")
    assert set(c["entries"]) == {"site:10.0,10.0", "site:50.0,50.0", "core:u_c.ck"}
    assert c["entries"]["core:u_c.ck"]["port"] == "clk_c0"


def test_renaming_die_taps_keeps_the_contract():
    p = _plan()
    q = copy.deepcopy(p)
    q["partition_types"]["A"]["clock"]["taps"][1]["name"] = "clk_t9"
    q["clock"]["tap_window"]["per_port_ps"]["A"] = {"clk": 20, "clk_t9": 40, "clk_c0": 30}
    q["partition_types"]["A"]["clock"]["landing_reader_start"]["branches"]["ft0_i"]["stages"][0]["raw_reset"] = "rst_n_t3"
    assert TC.contract(p, "A")["sha"] == TC.contract(q, "A")["sha"]


def test_moved_site_or_window_changes_the_contract():
    p = _plan()
    q = copy.deepcopy(p)
    q["partition_types"]["A"]["clock"]["taps"][1]["xy"] = [60.0, 50.0]
    assert TC.contract(p, "A")["sha"] != TC.contract(q, "A")["sha"]
    r = copy.deepcopy(p)
    r["clock"]["tap_window"]["per_port_ps"]["A"]["clk_t1"] = 41
    assert TC.contract(p, "A")["sha"] != TC.contract(r, "A")["sha"]


def test_provenance_text_and_die_relay_sites_are_not_contract():
    p = _plan()
    q = copy.deepcopy(p)
    q["partition_types"]["A"]["note"] = "other"
    q["partition_types"]["A"]["relay_sites"] = {"u_r": [[9, 9]]}
    q["partition_types"]["A"]["clock"]["taps"][2]["budget_owner"] = "other"
    q["clock"]["tap_offset"]["source"] = "other"
    assert TC.contract(p, "A")["sha"] == TC.contract(q, "A")["sha"]


def test_relative_offsets_and_core_schedule_in_contract():
    p = _plan()
    p["clock"]["tap_offset"]["per_port_ps"]["A"] = {"clk": {"TT": 30, "FF": 20}, "clk_t1": {"TT": 50, "FF": 25}}
    c = TC.contract(p, "A")
    assert c["entries"]["site:10.0,10.0"]["rel"] == {"TT": 0, "FF": 0}
    assert c["entries"]["site:50.0,50.0"]["rel"] == {"TT": 20, "FF": 5}
    core = c["entries"]["core:u_c.ck"]
    assert core["schedule_ps"] == {"TT": 700.0, "FF": 560.0} and core["lead_ps"] == 250.0
    # a common die shift of every offset is die side: same contract
    q = copy.deepcopy(p)
    q["clock"]["tap_offset"]["per_port_ps"]["A"] = {"clk": {"TT": 80, "FF": 70}, "clk_t1": {"TT": 100, "FF": 75}}
    assert TC.contract(q, "A")["sha"] == c["sha"]
    # a relative move or a core schedule change is a contract change
    q["clock"]["tap_offset"]["per_port_ps"]["A"]["clk_t1"]["TT"] = 101
    assert TC.contract(q, "A")["sha"] != c["sha"]
    r = copy.deepcopy(p)
    r["partition_types"]["A"]["clock"]["taps"][2]["insertion_ps"] = 710.0
    assert TC.contract(r, "A")["sha"] != c["sha"]


def test_reset_entry_depths():
    rst = TC.reset_entry(_plan(), "A")
    assert rst["sync_stages"] == 2 and rst["in_type_depth"] == 2 + 5     # landing start depth 5 > relay 3
    assert rst["flush_depth"] == 4                                         # ft0 stations 4 > internal 3 regs
    assert rst["required_hold_cycles"] == 11 and rst["parts"]["basis"] == "plan"


def test_window_ops_become_the_contract_window():
    p = _plan()
    ops = {"ops": [{"op": "replace", "path": "/clock/tap_window/per_port_ps/A", "old": p["clock"]["tap_window"]["per_port_ps"]["A"],
                    "value": {"clk": 40, "clk_t1": 40, "clk_c0": 40}},
                   {"op": "replace", "path": "/clock/tap_window/per_type_ps/A", "old": 999, "value": 1}]}
    tw, ok, bad = TC.apply_window_ops(p, ops)
    assert (ok, bad) == (1, 1)                                             # the stale-old op is refused
    assert p["clock"]["tap_window"]["per_port_ps"]["A"]["clk"] == 20       # the plan itself is never written
    c = TC.contract(p, "A", tw=tw)
    assert {e["window_ps"] for e in c["entries"].values() if "window_ps" in e} == {40.0}


def test_census_inside_outside_unmodelled():
    c = TC.contract(_plan(), "A")
    need, lost = TC.need_by_key(_plan(), "A", {"clk": 25, "clk_c0": 10, "clk_gone": 99})
    assert need == {"site:10.0,10.0": 25.0, "core:u_c.ck": 10.0} and lost == ["clk_gone"]
    rows = TC.census_type(c, need, core_model={"core:u_c.ck": 720.0})
    st = {r["key"]: r["status"] for r in rows}
    assert st["site:10.0,10.0"] == "OUTSIDE"            # need 25 > window 20
    assert st["site:50.0,50.0"] == "UNMODELLED"
    assert st["core:u_c.ck"] == "INSIDE"                # |720 - 700| = 20 <= 30
    assert st["core:u_c.ck#win"] == "INSIDE"


def _kit(d, sdc="create_clock -period 833 clk\n", define="-DOT_X=1", env_line="", rtl="module m_a; endmodule\n"):
    g = d / "A" / "gen" / "A"
    g.mkdir(parents=True)
    r = d / "A" / "rtl"
    r.mkdir()
    (r / "m_a.sv").write_text(rtl)
    (r / "kit_rtl.f").write_text(str(r / "m_a.sv") + "\n")
    for f in TC.KIT_FILES:
        (g / f).write_text("x %s\n" % g)
    (g / "constraint.sdc").write_text(sdc)
    (g / "config.mk").write_text("export VERILOG_DEFINES = %s\nexport DESIGN_HOME = %s\n" % (define, g))
    return g, r


def test_kit_hash_covers_netlist_sdc_defines_env_and_ignores_paths(tmp_path):
    g1, r1 = _kit(tmp_path / "a")
    g2, r2 = _kit(tmp_path / "b")
    env = {"OT_PGCAP": "1", "OT_LANE": "X"}
    h1 = TC.kit_hash(g1, "A", r1, env)[0]
    assert h1 == TC.kit_hash(g2, "A", r2, dict(env, OT_LANE="Y"))[0]          # paths + bookkeeping env ignored
    assert h1 != TC.kit_hash(g2, "A", r2, dict(env, OT_PGCAP="0"))[0]         # build env counts
    g3, r3 = _kit(tmp_path / "c", define="-DOT_X=2")
    assert h1 != TC.kit_hash(g3, "A", r3, env)[0]                             # effective defines count
    g4, r4 = _kit(tmp_path / "d", rtl="module m_a; wire w; endmodule\n")
    assert h1 != TC.kit_hash(g4, "A", r4, env)[0]                             # netlist counts
    g5, r5 = _kit(tmp_path / "e", sdc="create_clock -period 833 clk\nset_clock_latency -source -early -10 [get_ports clk_t1]\n")
    assert h1 != TC.kit_hash(g5, "A", r5, env)[0]                             # SDC counts
    assert h1 != TC.kit_hash(g1, "A", r1, env, plan_defines=["OT_Y"])[0]      # plan verilog_defines count


def test_credit_only_by_kit_hash():
    p = _plan()
    c = TC.contract(p, "A")
    assert TC.credit_row(c, c, "h1", "h1") == "CREDIT"
    assert TC.credit_row(c, c, "h1", "h2") == "KIT-CHANGED"                   # same contract, different kit: no credit
    assert TC.credit_row(c, c, None, None) == "SCHEDULE-SAME"                 # no kit pair: never credit
    q = copy.deepcopy(p)
    q["partition_types"]["A"]["outline_um"] = [100, 110]
    assert TC.credit_row(c, TC.contract(q, "A"), None, "h1") == "REISSUE"


def test_model_rows_follow_sites_not_tap_names():
    """the model was measured on a plan where the tap at (50,50) was called clk_t7: it must land on that SITE in the new plan"""
    old = _plan()
    old["partition_types"]["A"]["clock"]["taps"][1]["name"] = "clk_t7"
    need, _ = TC.need_by_key(old, "A", {"clk_t7": 45})
    rows = {r["key"]: r for r in TC.census_type(TC.contract(_plan(), "A"), need)}
    assert rows["site:50.0,50.0"]["model_ps"] == 45.0 and rows["site:50.0,50.0"]["status"] == "OUTSIDE"


def test_cli_census_and_credit(tmp_path):
    p = _plan()
    (tmp_path / "p.json").write_text(json.dumps(p))
    (tmp_path / "need.json").write_text(json.dumps({"per_port_ps": {"A": {"clk": 10, "clk_t1": 50}}}))
    assert TC.main(["census", str(tmp_path / "p.json"), "--out", str(tmp_path / "c.json"), "--arrivals", str(tmp_path / "need.json"),
                    "--tsv", str(tmp_path / "c.tsv"), "--tools", str(tmp_path / "none")]) == 0
    s = json.loads((tmp_path / "c.json").read_text())["summary"]
    assert s["entries"] == {"INSIDE": 1, "OUTSIDE": 1, "UNMODELLED": 1} and s["types_outside"] == 1 and s["report_only"] == "r703"
    assert TC.main(["credit", "--base", str(tmp_path / "p.json"), "--new", str(tmp_path / "p.json"), "--out", str(tmp_path / "k.json"),
                    "--tools", str(tmp_path / "none")]) == 0
    assert json.loads((tmp_path / "k.json").read_text())["summary"]["verdicts"] == {"SCHEDULE-SAME": 1}
