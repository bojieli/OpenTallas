"""die_sta_related.py kit-contract hold bound (INFRA-FIRST-R3b): bound = declared window - hold damage, CPPR at the
last common tree node; zero-logic numbers unchanged."""
import die_sta_related as R

REG = dict(clkq_max_wire_ps=68.0, clkq_min_nowire_ps=46.5, setup_ps=5.6, hold_ps=22.2)


def _taps():
    # region root "h0" range 10 ps; a/b in one partition, c in a neighbour; all in region h0
    return {"a": dict(late_ps=1000.0, early_ps=990.0, cppr_node="h0"),
            "b": dict(late_ps=1050.0, early_ps=1040.0, cppr_node="h0"),
            "c": dict(late_ps=1020.0, early_ps=1010.0, cppr_node="h0")}


def test_contract_bound_intra_and_seam():
    taps, rng = _taps(), {"h0": 10.0, "h": 30.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, hold_window=dict(ps=0.0, basis="t"))
    kc = r["kit_contract_hold"]
    # a -> b: damage = b.late - a.early - credit(10) = 1050 - 990 - 10 = 50
    assert kc["window_needed_ps"] == 50.0 and kc["worst_hold_bound_ps"] == -50.0 and kc["verdict"] == "FAIL"
    assert kc["neg_pairs"] == 1
    # zero-logic hold unchanged: 990 + 46.5 - (1050 + 22.2) - 25 + 10
    assert r["worst_hold_slack_ps"] == round(990 + 46.5 - 1050 - 22.2 - 25 + 10, 2)
    r2 = R.time_class([("a", "c", "p->q")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0,
                      hold_window=dict(ps=40.0, basis="legacy"))
    assert r2["kit_contract_hold"]["worst_hold_bound_ps"] == 20.0 and r2["kit_contract_hold"]["verdict"] == "PASS"


def test_no_window_no_contract_block():
    r = R.time_class([("a", "b", "p")], _taps(), {"h0": 10.0}, REG, 20.0, 833.333, 60.0, 25.0)
    assert "kit_contract_hold" not in r


def test_windows_read_from_plan():
    legacy = R.kit_windows(dict(insertion_tol_ps=40))
    assert legacy["intra"]["ps"] == 0.0 and legacy["seam"]["ps"] == 40.0
    w = R.kit_windows(dict(insertion_tol_ps=40, seam_hold=dict(sender_ps=25, seam_ps=80), tap_window=dict(window_ps=80)))
    assert w["intra"]["ps"] == 80.0 and w["seam"]["ps"] == 80.0 and "clock.tap_window" in w["intra"]["basis"]
    wi = R.kit_windows(dict(tap_window=dict(window_ps=80)), 120.0)
    assert wi["intra"]["ps"] == 120.0 and "WHAT-IF" in wi["intra"]["basis"]


# ---- REAL VIEWS (CLOCK-KV-R16, opt-in)
ETM = """library (t) {
  cell ("c") {
    bus("ck") {
    pin("ck[0]") {
      direction : input;
      clock : true;
      timing() {
        timing_type : min_clock_tree_path;
        cell_rise(scalar) {
          values("260.0");
        }
      }
      timing() {
        timing_type : max_clock_tree_path;
        cell_rise(scalar) {
          values("300.0");
        }
      }
    }
    }
    pin("d[0]") {
      direction : input;
      timing() {
        related_pin : "ck[0]";
        timing_type : hold_rising;
        rise_constraint(scalar) {
          values("120.0");
        }
        fall_constraint(scalar) {
          values("125.0");
        }
      }
      timing() {
        related_pin : "ck[0]";
        timing_type : setup_rising;
        rise_constraint(scalar) {
          values("-90.0");
        }
      }
    }
    pin("q[0]") {
      direction : output;
      timing() {
        related_pin : "ck[0]";
        timing_type : rising_edge;
        cell_rise(template_1) {
          index_1("2.0, 10.0");
          values("370.0,390.0");
        }
        cell_fall(template_1) {
          index_1("2.0, 10.0");
          values("360.0,380.0");
        }
      }
    }
  }
}
"""


def test_parse_etm(tmp_path):
    f = tmp_path / "c_tt.lib"
    f.write_text(ETM)
    e = R.parse_etm(f, 6.0)
    assert e["clock_pin"] == "ck[0]" and e["clock_tree_path_ps"] == {"min_clock_tree_path": 260.0,
                                                                     "max_clock_tree_path": 300.0}
    assert e["out_max_ps"] == 380.0 and e["out_min_ps"] == 370.0      # interpolated at 6 fF
    assert e["in_setup_ps"] == -90.0 and e["in_hold_ps"] == 125.0


def test_budget_views_reproduce_declared_formula():
    taps, rng = _taps(), {"h0": 10.0}
    pairs = [("a", "b", "p"), ("b", "a", "p")]
    base = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0)
    v = {p: [R.budget_model(REG, 250.0)] for p in taps}
    r = R.time_class(pairs, taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=v)
    assert r["worst_setup_slack_ps"] == base["worst_setup_slack_ps"]
    assert r["worst_hold_slack_ps"] == base["worst_hold_slack_ps"]
    assert r["real_view"]["pairs_with_real_endpoint"] == 0


def test_core_view_pair_uses_etm_arcs():
    taps, rng = _taps(), {"h0": 10.0}
    core = dict(name="core:c", real=True, lat_late=0.0, lat_early=0.0, clkq_max=380.0, clkq_min=370.0, setup=-90.0,
                hold=125.0)
    v = {"a": [R.budget_model(REG, 250.0)], "b": [R.budget_model(REG, 250.0), core]}
    r = R.time_class([("a", "b", "p")], taps, rng, REG, 20.0, 833.333, 60.0, 25.0, views=v)
    rv = r["real_view"]
    assert rv["pairs_with_real_endpoint"] == 1 and rv["pairs_both_real"] == 0
    # budget a -> core b hold: (990 + 250 + 46.5) - (1050 + 0 + 125) - 25 + credit 10
    assert rv["worst_hold_slack_ps"] == round(990 + 250 + 46.5 - 1050 - 125 - 25 + 10, 2)
    # setup: (1040 + 0 + 833.333 + 90) - (1000 + 250 + 68) - 60 + 10
    assert rv["worst_setup_slack_ps"] == round(1040 + 833.333 + 90 - 1000 - 250 - 68 - 60 + 10, 2)
    assert rv["worst_hold"]["capture_model"] == "core:c"
    assert r["worst_hold_slack_ps"] <= rv["worst_hold_slack_ps"]


def test_cppr_lca_opt_in():
    """PATH-S81-PD6 --cppr-lca: node = longest common tree_path prefix; default keeps the region/die-root form."""
    import die_sta_related as D
    A = dict(cppr_node="h01", tree_path="h0110")
    B = dict(cppr_node="h00", tree_path="h0011")
    C = dict(cppr_node="h01", tree_path="h0101")
    old = D.CPPR_LCA
    try:
        D.CPPR_LCA = False
        assert D.pair_node(A, B) == "h" and D.pair_node(A, C) == "h01"
        D.CPPR_LCA = True
        assert D.pair_node(A, B) == "h0" and D.pair_node(A, C) == "h01" and D.pair_node(A, A) == "h0110"
        assert D.pair_node(dict(cppr_node="x"), dict(cppr_node="x")) == "x"   # no tree_path -> default form
    finally:
        D.CPPR_LCA = old


# ---- DROOP REGION + SIGNED MESH (CLOCK-KV-R17)
def _ocv_taps():
    t = {"a": dict(late_ps=4700.0, early_ps=4660.0, cppr_node="h", stages_from_root=46, xy_um=[1000.0, 1000.0]),
         "b": dict(late_ps=4710.0, early_ps=4670.0, cppr_node="h", stages_from_root=46, xy_um=[1300.0, 1000.0])}
    meta = dict(corner="FF", node_stages={"h": 1}, node_xy_um={"h": [5000.0, 13000.0]}, node_late_ps={"h": 40.0},
                node_early_ps={"h": 39.6})
    return t, meta


def test_droop_region_mesh_shares_droop():
    t, meta = _ocv_taps()
    old = R.clock_ocv_fn("table", "shared", meta, t, 250.0)                           # pre-R17: region = tree node
    same = R.clock_ocv_fn("table", "shared", meta, t, 250.0, region={"a": "mesh:0", "b": "mesh:0"})
    diff = R.clock_ocv_fn("table", "shared", meta, t, 250.0, region={"a": "mesh:0", "b": "mesh:1"})
    stated = R.clock_ocv_fn("table", "stated", meta, t, 250.0)
    # one mesh region: no droop charge; different regions: the full one-sided droop (= the old / stated value)
    assert same("a", "b", "hold") < old("a", "b", "hold")
    assert abs(diff("a", "b", "hold") - old("a", "b", "hold")) < 1e-9
    assert abs(stated("a", "b", "hold") - old("a", "b", "hold")) < 1e-9


def test_droop_regions_from_mesh_json(tmp_path):
    import json
    (tmp_path / "mesh.json").write_text(json.dumps({"taps": [{"port": "a"}, {"port": "b"}]}))
    reg = R.droop_regions(tmp_path, {"a": {}, "b": {}, "c": {}}, "mesh")
    assert reg == {"a": "mesh:0", "b": "mesh:0"}
    assert R.droop_regions(tmp_path, {"a": {}}, "tree") is None
    (tmp_path / "pdn.json").write_text(json.dumps({"b": "pdn:1"}))
    assert R.droop_regions(tmp_path, {"a": {}, "b": {}}, "mesh", tmp_path / "pdn.json") == {"a": "mesh:0", "b": "pdn:1"}


def test_mesh_signoff_rereference_and_unc(tmp_path):
    import json
    M = {"taps": [{"port": "a", "stub": "s1"}, {"port": "b", "stub": "s2"}, {"port": "c", "stub": "s3", "mesh_in": "br0"}]}
    (tmp_path / "mesh.json").write_text(json.dumps(M))
    rt = {"s1": dict(late=4600.0, early=4560.0), "s2": dict(late=4610.0, early=4570.0), "s3": dict(late=1, early=1),
          "br0": dict(late=4550.0, early=4510.0)}
    (tmp_path / "mesh_TT.json").write_text(json.dumps({"stubs": rt}))
    # loads s1, s2, br0; sample 0 = nominal (sim 5 ps below routed for s1, 3 below for s2), 2 MC samples
    so = dict(corner="TT", loads=["br0", "s1", "s2"], arr=[[4550.0, 4595.0, 4607.0], [4552.0, 4596.0, 4610.0],
                                                           [4549.0, 4594.0, 4603.0]],
              grad_vec_ps=[[0.0, 0.0], [3.0, 0.0], [0.0, 4.0]], summary={}, checked="UNCHECKED")
    (tmp_path / "so.json").write_text(json.dumps(so))
    taps = {"a": dict(late_ps=4650.0, early_ps=4600.0, cppr_node="h"),
            "b": dict(late_ps=4655.0, early_ps=4610.0, cppr_node="h"),
            "c": dict(late_ps=4700.0, early_ps=4650.0, cppr_node="h")}
    meta = {"cppr_node_range_ps": {"h": 0.4}}
    U, rec = R.mesh_signoff(tmp_path, taps, meta, "TT", tmp_path / "so.json", "tree")
    m0 = 4610.0                                                   # median routed late of the mesh loads s1, s2
    assert rec["M0_ps"] == m0 and rec["taps_on_mesh"] == 2
    assert taps["a"]["late_ps"] == m0 + 50.0 and taps["a"]["early_ps"] == m0 + 40.0 and taps["a"]["cppr_node"] == "m"
    assert taps["a"]["abs_late_ps"] == 4650.0 and taps["c"]["cppr_node"] == "h"        # band strict: not on the mesh
    # d = s1 - s2 over samples: -12, -14, -9; MC mean -11.5 sd 3.5355 -> mu+3sd 22.11; max|d| 14 -> 22.11
    # gap: (4600-4595) - (4610-4607) = 2; gradient |(3,0)-(0,4)| = 5
    assert abs(U("a", "b") - (11.5 + 3 * 3.5355339 + 2 + 5)) < 1e-4
    assert U("a", "c") == 0.0 and U("a", "a") == 0.0
    # strict band pair uses absolute arrivals and the die root
    la, ea, lc, ec = R.arr4(taps["a"], taps["c"], "h")
    assert (la, ea, lc, ec) == (4650.0, 4600.0, 4700.0, 4650.0)
    t2 = {k: dict(late_ps=v["abs_late_ps"] if "abs_late_ps" in v else v["late_ps"],
                  early_ps=v["abs_early_ps"] if "abs_early_ps" in v else v["early_ps"], cppr_node="h") for k, v in taps.items()}
    U2, rec2 = R.mesh_signoff(tmp_path, t2, {"cppr_node_range_ps": {}}, "TT", tmp_path / "so.json", "sim")
    assert rec2["taps_on_mesh"] == 3 and t2["c"]["cppr_node"] == "m" and t2["c"]["late_ps"] == 4610.0 + 150.0


def test_default_aocv_table_is_approved_021():
    """CLOCK-KV-R18: the default clock AOCV table must be the approved 0.21 %/mm table; fails on the 0.42 draft."""
    import clk_aocv as CA
    from pathlib import Path
    here = Path(R.__file__).resolve().parent
    T = CA.load(here / R.APPROVED_AOCV_TABLE)
    g = T["systematic"]["g_per_mm"]
    assert abs(g - 0.0021) < 1e-12, f"default AOCV table g={g} is not the approved 0.21 %/mm (0.004163 = DRAFT)"
    assert R.APPROVED_G_PER_MM == g and not T["status"].startswith("DRAFT")
    # the table the tool actually loads when --clock-aocv-table is omitted: pin it via the resolved default
    t, meta = _ocv_taps()
    f_def = R.clock_ocv_fn("table", "shared", meta, t, 250.0)
    f_021 = R.clock_ocv_fn("table", "shared", meta, t, 250.0, table_path=here / R.APPROVED_AOCV_TABLE)
    f_dft = R.clock_ocv_fn("table", "shared", meta, t, 250.0, table_path=here / "clk_aocv_table.json")
    assert f_def("a", "b", "hold") == f_021("a", "b", "hold")
    assert f_def("a", "b", "hold") != f_dft("a", "b", "hold")


def test_hold_buffer_model_hb4():
    """CLOCK-KV-R18 HB4 model: k = ceil(-hold / 44.6), hold += k 44.6, setup -= k 83.0; cells from bits."""
    tt = {("a", "b", "p"): (300.0, 0, True, False), ("c", "d", "q"): (100.0, 0, False, False),
          ("e", "f", "r"): (50.0, 0, False, False)}
    ff = {("a", "b", "p"): (0, -100.0, True, False), ("c", "d", "q"): (0, -10.0, False, False),
          ("e", "f", "r"): (0, 5.0, False, False)}
    r = R.hold_buffer_model(tt, ff, bits={("a", "b"): 4, ("c", "d"): 2})
    assert r["cells_per_pair_hist"] == {0: 1, 1: 1, 3: 1} and r["pairs_needing_hb"] == 2
    assert r["hb4_cells"] == 3 * 4 + 1 * 2 and r["bits_needing_hb"] == 6
    assert r["all"]["ff_hold_after_ps"] == round(min(-100 + 3 * 44.6, -10 + 44.6, 5.0), 2)
    assert r["all"]["tt_setup_after_ps"] == round(min(300 - 3 * 83.0, 100 - 83.0, 50.0), 2)
    assert r["real_view"]["pairs"] == 1 and r["real_view"]["tt_setup_after_ps"] == round(300 - 249.0, 2)


def test_pair_unc_exclusive_flags(tmp_path):
    """ROOT-MERGE-29 shared model: --pair-unc never combines with --clock-ocv or --mesh-signoff (one variation model
    per segment); --cppr-lca is not refused with any of them (it only picks the CPPR node)."""
    import pytest
    base = [str(tmp_path), "--plan", "p.json", "--out", str(tmp_path / "o"), "--pair-unc", "x.json"]
    for extra in (["--mesh-signoff", "TT=a,FF=b"], ["--clock-ocv", "table"]):
        with pytest.raises(SystemExit) as e:
            R.main(base + extra)
        assert "exclusive" in str(e.value)


def test_cppr_lca_signed_mesh_pair():
    """PATH-S81-PD7: two signed-mesh taps keep node m (re-referenced arrivals) even with --cppr-lca; any other node
    uses the absolute arrivals."""
    import die_sta_related as D
    A = dict(cppr_node="m", tree_path="h0110", late_ps=10.0, early_ps=9.0, abs_late_ps=510.0, abs_early_ps=509.0)
    B = dict(cppr_node="m", tree_path="h0011", late_ps=12.0, early_ps=11.0, abs_late_ps=512.0, abs_early_ps=511.0)
    C = dict(cppr_node="h01", tree_path="h0101", late_ps=600.0, early_ps=590.0)
    old = D.CPPR_LCA
    try:
        D.CPPR_LCA = True
        assert D.pair_node(A, B) == "m" and D.arr4(A, B, "m") == (10.0, 9.0, 12.0, 11.0)
        n = D.pair_node(A, C)
        assert n == "h01" and D.arr4(A, C, n) == (510.0, 509.0, 600.0, 590.0)
    finally:
        D.CPPR_LCA = old
