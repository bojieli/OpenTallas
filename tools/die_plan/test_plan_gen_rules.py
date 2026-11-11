"""PLAN-GEN-RULES-1 (OWNER 11-10): rule A (planned core insertion -> core taps + core kit vclk), rule B (taps from
sink count), rule C (cell check after first synthesis) and the kit-wave hook."""
import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import cell_check as CC  # noqa: E402
import master_plan as M  # noqa: E402
import plan_gen_rules as R  # noqa: E402
import schema as S  # noqa: E402


def _core_tap(inst, tt=250.0, ff=202.5, **kw):
    return dict(name=f"{inst}.clk", kind="core", xy=[10.0, 10.0], insertion_ps=tt, insertion_ff_ps=ff, **kw)


def _plan():
    T = {
        # 1200 x 800 grid type at the 400 pitch: 3 x 2 = 6 taps
        "g": dict(outline_um=[1200.0, 800.0], clock=dict(tap_um=[600.0, 400.0])),
        "d": dict(outline_um=[800.0, 800.0], clock=dict(tap_mode="density", tap_radius_um=150.0)),
        "p": dict(outline_um=[900.0, 900.0], clock=dict(tap_um=[450.0, 450.0], core_taps="early",
                  taps=[_core_tap("u_a"), _core_tap("u_b"), _core_tap("u_m", 300.0, 243.0), _core_tap("u_big"),
                        _core_tap("u_s")]),
                  hard_cores=[dict(inst="u_a", module="core_a", origin_um=[0, 0], outline_um=[300.0, 380.0]),
                              dict(inst="u_b", module="core_a", origin_um=[400, 0], outline_um=[300.0, 380.0]),
                              dict(inst="u_m", module="core_m", origin_um=[0, 400], outline_um=[300.0, 300.0]),
                              dict(inst="u_big", module="core_big", origin_um=[0, 0], outline_um=[700.0, 600.0]),
                              dict(inst="u_s", module="core_s", origin_um=[800, 800], outline_um=[100.0, 100.0])]),
        # a type with core taps but no 'early' mode: its kit never reads them
        "q": dict(outline_um=[400.0, 400.0], clock=dict(tap_um=[200.0, 200.0], taps=[_core_tap("u_c")]),
                  hard_cores=[dict(inst="u_c", module="core_c", origin_um=[0, 0], outline_um=[300.0, 380.0])]),
    }
    return dict(die=dict(name="t", outline_um=[5000.0, 5000.0], reach_um=405.0, period_ps=833.0),
                partition_types=T, partitions=[], ports=[], lanes=[], clock=dict(insertion_ps=250.0), budgets={})


# ------------------------------------------------------------------ rule A
def test_model_is_master_plan_12_9d():
    for L in (181.44, 259.2, 340.0):
        assert R.model_insertion(L) == (round(M.CAL_A + M.CAL_B * L, 1), round(0.81 * round(M.CAL_A + M.CAL_B * L, 1), 1))
    assert R.model_error_ps() == M.CAL_LOO_MAX_PS


def test_rule_a_plans_default_core_taps_only():
    P0 = _plan()
    Q, rec = R.apply(P0, rules=("A",))
    taps = {tp["name"]: tp for tp in Q["partition_types"]["p"]["clock"]["taps"]}
    tt, ff = R.model_insertion((300 + 380) / 2)
    assert (taps["u_a.clk"]["insertion_ps"], taps["u_a.clk"]["insertion_ff_ps"]) == (tt, ff)
    assert taps["u_a.clk"]["insertion_basis"].startswith(R.RULE)
    assert taps["u_m.clk"] == _core_tap("u_m", 300.0, 243.0)                  # measured value stands
    assert taps["u_big.clk"]["insertion_ps"] == 250.0                          # reach 650 > R4 400: listed
    assert "core_big" in rec["A"]["listed"]
    assert taps["u_s.clk"]["insertion_ps"] == 250.0                            # model 167 < default: no change
    assert Q["partition_types"]["q"] == P0["partition_types"]["q"]             # no core_taps 'early'
    assert rec["A"]["cores"]["core_a"]["taps"] == 2 and rec["A"]["types"] == {}
    assert R.affected_types(P0, Q) == ["p"]
    # the core kit reads the same value; a measured module reads its own; unplanned modules -> None
    PQ = S.Plan(Q)
    assert R.core_io_insertion(PQ, "core_a")[:2] == (tt, ff)
    assert R.core_io_insertion(PQ, "core_m")[:2] == (300.0, 243.0)
    assert R.core_io_insertion(PQ, "core_s") is None and R.core_io_insertion(S.Plan(P0), "core_a") is None


def test_rule_a_idempotent_and_disagreement_fails_closed():
    Q, _ = R.apply(_plan(), rules=("A",))
    Q2, rec2 = R.apply(Q, rules=("A",))
    assert Q2 == Q and rec2["A"]["cores"] == {}
    Q["partition_types"]["p"]["clock"]["taps"][1]["insertion_ps"] = 333.0
    with pytest.raises(ValueError):
        R.core_io_insertion(S.Plan(Q), "core_a")


def test_rule_a_measured_and_excluded_cores(tmp_path):
    f = tmp_path / "ci.json"
    f.write_text(json.dumps(dict(views=[dict(view="v1", module="core_a", status="MEASURED", insertion_mean_ps=331.0,
                                             insertion_ff_mean_ps=270.0),
                                        dict(view="v2", module="core_s", status="NO KIT")])))
    mc = R.load_measured_cores(f)
    assert mc == {"core_a": (331.0, 270.0, "measured view v1 (ci.json)")}
    Q, rec = R.apply(_plan(), rules=("A",), measured=mc)
    tp = Q["partition_types"]["p"]["clock"]["taps"][0]
    assert (tp["insertion_ps"], tp["insertion_ff_ps"]) == (331.0, 270.0) and rec["A"]["cores"]["core_a"]["basis"] == "measured"
    Q, rec = R.apply(_plan(), rules=("A",), measured={"core_a": (900.0, 729.0, "x")})
    assert Q["partition_types"]["p"]["clock"]["taps"][0]["insertion_ps"] == 250.0 and "T/2" in rec["A"]["listed"]["core_a"]["why"]
    Q, rec = R.apply(_plan(), rules=("A",), exclude=("core_a",))
    assert Q["partition_types"]["p"] == _plan()["partition_types"]["p"] and "core_a" in rec["A"]["listed"]


def test_rule_at_types_opt_in():
    P0 = _plan()
    Q, rec = R.apply(P0, rules=("AT",))
    g = Q["partition_types"]["g"]["clock"]
    L = (1200 / 3 + 800 / 2) / 2
    assert g["insertion_ps"] == R.model_insertion(L)[0] and "insertion_ff_ps" not in g
    assert "g" in rec["A"]["types"]
    Qa, _ = R.apply(P0, rules=("A",))
    assert "insertion_ps" not in Qa["partition_types"]["g"]["clock"]          # default rule A leaves types alone


# ------------------------------------------------------------------ rule B
def test_pitch_for_is_largest_reaching_the_count():
    for w, h, need in ((1200.0, 800.0, 7), (457.92, 4320.0, 37), (700.0, 700.0, 2), (1000.0, 300.0, 11)):
        p = R.pitch_for(w, h, need, 400.0)
        n = R.grid_taps(w, h, p)
        assert n >= need
        # brute force: no pitch <= 400 gives a grid with fewer taps that still reaches the count
        assert all(R.grid_taps(w, h, q / 4) >= n or R.grid_taps(w, h, q / 4) < need for q in range(40, 1601))
    assert R.pitch_for(1200.0, 800.0, 6, 400.0) == 400.0


def test_rule_b_grid_pitch_density_listed():
    P0 = _plan()
    sinks = {"g": dict(sinks=30000, basis="test"), "d": dict(sinks=90000, basis="test"),
             "p": dict(sinks=100, basis="test")}
    Q, rec = R.apply(P0, rules=("B",), sinks=sinks)
    B = rec["B"]
    assert B["g"]["action"] == "tap_pitch_um" and B["g"]["need"] == 10
    p = Q["partition_types"]["g"]["clock"]["tap_pitch_um"]
    assert len(S.tap_grid(S.Plan(Q), "g")) >= 10 and p == B["g"]["to_um"]
    assert "p" not in B                                                      # enough taps already
    assert B["d"]["action"] == "list" and "sink_bins" in B["d"]["why"]
    assert "tap_pitch_um" not in Q["partition_types"]["d"]["clock"]


def test_rule_b_keeps_named_taps():
    P0 = _plan()
    P0["partition_types"]["g"]["clock"]["landing_contract"] = dict(pins=[dict(name="fclk_out_x", source_clock_port="clk_t4")])
    Q, rec = R.apply(P0, rules=("B",), sinks={"g": dict(sinks=30000, basis="test")})
    assert Q == P0 and rec["B"]["g"]["action"] == "list" and "clk_t4" in rec["B"]["g"]["why"]
    assert rec["B"]["g"]["proposed_um"] and rec["B"]["g"]["taps_proposed"] >= 10


def test_event_cli_keeps_base_bytes_and_style(tmp_path):
    P0 = _plan()
    for txt in (json.dumps(P0, indent=1), json.dumps(P0, indent=1) + "\n", json.dumps(P0, separators=(",", ":")) + "\n"):
        b = tmp_path / "base.json"
        b.write_text(txt)
        R.main(["event", str(b), str(tmp_path / "o.json"), str(tmp_path / "r.json"), "--rules", "B"])
        assert (tmp_path / "o.json").read_text() == txt                      # no change: the base bytes
        R.main(["event", str(b), str(tmp_path / "o.json"), str(tmp_path / "r.json"), "--rules", "A"])
        out = (tmp_path / "o.json").read_text()
        assert out != txt and out.endswith("\n") == txt.endswith("\n") and ("\n " in out) == ("\n " in txt)
        assert json.loads((tmp_path / "r.json").read_text())["affected_types"] == ["p"]


def test_no_rules_no_sinks_byte_identical():
    P0 = _plan()
    Q, rec = R.apply(P0, rules=(), sinks={})
    assert json.dumps(Q, sort_keys=True) == json.dumps(P0, sort_keys=True) and rec == {}
    Q, rec = R.apply(P0, rules=("B",), sinks={})
    assert Q == P0


def test_parse_stat_hierarchy_and_flat():
    hier = """=== top ===
   Number of cells: 9
=== design hierarchy ===

     5000  1.0E+03   4000  9.0E+02 top
   111        -   99        - wires
     5000  1.0E+03   4000  9.0E+02 cells
      100   29.1      90   26.2   DFFHQNx1_ASAP7_75t_R
       20    5.8      20    5.8   DFFLQNx1_ASAP7_75t_R
        3    1.1       3    1.1   ICGx1_ASAP7_75t_R
     4877   900.0   3887   800.0   INVx1_ASAP7_75t_R

   Chip area for top module '\\top': 1000.5
"""
    assert R.parse_stat(hier) == dict(cells=5000, flops=123, area_um2=1000.5)
    flat = """=== top ===
   Number of cells:               1234
     DFFHQNx1_ASAP7_75t_R          200
     NAND2x1_ASAP7_75t_R          1034
   Chip area for module '\\top': 55.5
"""
    assert R.parse_stat(flat) == dict(cells=1234, flops=200, area_um2=55.5)


def test_sinks_table_measured_base_then_estimate():
    P0 = _plan()
    P0["partition_types"]["g__cl0123abcd"] = dict(P0["partition_types"]["g"])
    P0["partition_types"]["d"]["cells"] = 10000
    meas = {"t": {"g": dict(flops=5000, cells=20000, src="h:/k")}}
    tab = R.sinks_table(P0, "t", meas)
    assert tab["g"]["sinks"] == 5000 and "base of" in tab["g__cl0123abcd"]["basis"]
    assert tab["d"]["sinks"] == 2500 and tab["d"]["basis"].startswith("ESTIMATE")
    assert "p" not in tab                                                    # hard cores: flat estimate not used


# ------------------------------------------------------------------ rule C
def test_union_and_soft_area():
    assert CC.union_area([(0, 0, 10, 10), (5, 5, 15, 15)]) == 175.0
    t = _plan()["partition_types"]["p"]
    # union: u_big 700 x 600 holds u_a / u_b and u_m up to y 600; + u_m above it (300 x 100) + u_s (100 x 100)
    assert CC.soft_area(t) == pytest.approx(900 * 900 - (700 * 600 + 300 * 100 + 100 * 100))


def test_cell_check_flags():
    raw = _plan()
    raw["partition_types"]["g"]["cells"] = 100000
    ok = CC.check(raw, "g", 120000)
    assert ok["flags"] == [] and ok["ratio"] == 1.2 and ok["plan_change"] is None
    hi = CC.check(raw, "g", 420000)
    assert any("density" in f for f in hi["flags"]) and any("measured/plan" in f for f in hi["flags"])
    assert hi["plan_change"].startswith("PLAN-CHANGE g")
    core = CC.check(raw, "p", 1000)
    assert core["ratio"] is None and "hard cores" in core["plan_cells_basis"]


def test_cell_check_cli_core_item(tmp_path, capsys):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(_plan()))
    assert CC.main(["--plan", str(p), "--type", "not_a_type", "--cells", "5"]) == 0
    assert "skipped" in capsys.readouterr().out


# ------------------------------------------------------------------ kit-wave hook + core gens (opt-in, default unchanged)
def test_kit_wave_cell_check_note_once():
    import kit_wave as KW

    class AP:
        lines = []

        @staticmethod
        def coord_append(rel, line):
            AP.lines.append((rel, line))
    st, notices = {}, {}
    rec = dict(die="t", event="e1", item="g")
    res = dict(cell_check=dict(type="g", flags=["density 0.5 cells/um2 >= 0.42"], density=0.5, density_flag=0.42,
                               ratio=None, ratio_flag=1.5, plan_change="PLAN-CHANGE g: ..."))
    KW.cell_check_note(AP, st, rec, res, notices)
    KW.cell_check_note(AP, st, rec, res, notices)
    assert len(notices["t"]) == 1 and "PLAN-CHANGE" in notices["t"][0]
    assert len(AP.lines) == 1 and AP.lines[0][0] == KW.CELL_FLAGS_REL and len(AP.lines[0][1].split("\t")) == 16
    KW.cell_check_note(AP, st, dict(rec, item="h"), dict(cell_check=dict(flags=[])), notices)
    assert len(AP.lines) == 1


def test_kit_wave_spec_has_no_cell_check_key_by_default():
    src = (HERE.parent / "autopilot" / "kit_wave.py").read_text()
    assert '**({"cell_check": True} if d.get("cell_check") and kind == "type" else {})' in src
    assert 'if sp.get("cell_check") and res["cells"]:' in src


@pytest.mark.parametrize("gen", ["physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py",
                                 "physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py"])
def test_core_gens_io_insertion_opt_in(gen):
    s = (HERE.parents[1] / gen).read_text()
    assert 'ap.add_argument("--io-insertion", choices=("default", "plan"), default="default"' in s
    assert 'a.io_insertion == "plan" and a.io_tt_ps is None' in s
    assert "PGR.core_io_insertion(PSC.Plan(plan)" in s
