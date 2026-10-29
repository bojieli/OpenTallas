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
    # d = s1 - s2 over samples: -12, -14, -9; gap (4600-4595) - (4610-4607) = 2 folded into every sample (PD11 ruling 3)
    # -> d' = -10, -12, -7; MC mean -9.5 sd 3.5355 -> mu+3sd 20.107 > max|d'| 12; gradient |(3,0)-(0,4)| = 5
    assert abs(U("a", "b") - (9.5 + 3 * 3.5355339 + 5)) < 1e-4
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


def test_count_align_key_cli_flag_parses(tmp_path):
    """DIE-QC-5: --count-align-key {part,region} reaches main (parse passes; the run then stops on the exclusive-flag
    check, before any file is read); an unknown key is an argparse error."""
    import pytest
    base = [str(tmp_path), "--plan", "p.json", "--out", str(tmp_path / "o"), "--pair-unc", "x.json", "--clock-ocv", "table"]
    for k in ("part", "region"):
        with pytest.raises(SystemExit) as e:
            R.main(base + ["--count-align-key", k])
        assert "exclusive" in str(e.value)
    with pytest.raises(SystemExit) as e:
        R.main(base + ["--count-align-key", "bogus"])
    assert e.value.code == 2


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


def test_hold_buffer_model_per_endpoint_path():
    """CLOCK-KV-R19 (NUMBER-CHECK-KV-R18): HB4 sized per endpoint path.  One tap pair, two endpoint paths: a declared
    budget->budget path (hold -160 -> 4 HB4, setup 400) and a budget->real-core path (hold -50 -> 2 HB4, setup 200).
    The R18 artefact (4 cells sized from the budget path, charged to the core path setup: 200 - 332 < 0) is gone."""
    k1, k2 = ("a", "b", "p", "budget", "budget"), ("a", "b", "p", "budget", "core:x")
    tt = {k1: (400.0, 0, False, False), k2: (200.0, 0, True, False)}
    ff = {k1: (0, -160.0, False, False), k2: (0, -50.0, True, False)}
    r = R.hold_buffer_model(tt, ff, bits={("a", "b"): 3})
    assert r["all"]["setup_neg_pairs_after"] == 0
    assert r["all"]["tt_setup_after_ps"] == round(min(400 - 4 * 83.0, 200 - 2 * 83.0), 2)
    assert r["real_view"]["tt_setup_after_ps"] == round(200 - 2 * 83.0, 2)
    assert r["cells_per_pair_hist"] == {2: 1, 4: 1} and r["pairs_needing_hb"] == 1 and r["paths_needing_hb"] == 2
    assert r["hb4_cells"] == 4 * 3      # cell-count bound: pair bits at the pair's worst endpoint-path k


def test_time_class_records_every_endpoint_path():
    """time_class rec holds one entry per (launch model, capture model) combo, each with its own setup/hold."""
    taps = {p: dict(late_ps=100.0, early_ps=100.0, cppr_node="m", slew_ps=20.0) for p in ("a", "b")}
    reg = dict(clkq_max_wire_ps=50.0, clkq_min_nowire_ps=40.0, setup_ps=10.0, hold_ps=20.0)
    bud = dict(name="budget", real=False, lat_late=250.0, lat_early=250.0, clkq_max=50.0, clkq_min=40.0, setup=10.0,
               hold=20.0)
    core = dict(name="core:x", real=True, lat_late=0.0, lat_early=0.0, clkq_max=330.0, clkq_min=300.0, setup=-260.0,
                hold=300.0)
    rec = {}
    R.time_class([("a", "b", "p")], taps, {"m": 0.0}, reg, 20.0, 833.0, 0.0, 0.0,
                 views={"a": [bud], "b": [bud, core]}, rec=rec)
    assert set(rec) == {("a", "b", "p", "budget", "budget"), ("a", "b", "p", "budget", "core:x")}
    assert rec[("a", "b", "p", "budget", "budget")][1] == 40.0 - 20.0
    assert rec[("a", "b", "p", "budget", "core:x")][1] == 250.0 + 40.0 - 300.0


def test_core_view_match_pins_compares_content(tmp_path):
    """CLOCK-KV-R24 (NUMBER-CHECK-KV-R23): a view signed on a 544-pin file must NOT apply to a same-NAME 546-pin
    plan file (added strap_bsel); match = sha256 of the plan pins_file == view provenance kit.pins_sha256."""
    import hashlib
    import json as _j
    (tmp_path / "cores").mkdir()
    old = _j.dumps(dict(pins=[dict(name=f"p{i}") for i in range(544)]))
    new = _j.dumps(dict(pins=[dict(name=f"p{i}") for i in range(544)] + [dict(name="strap_bsel[0]"), dict(name="strap_bsel[1]")]))
    (tmp_path / "cores" / "e1_pins.json").write_text(new)
    meta_old = dict(pins_file="cores/e1_pins.json", pins_sha256=hashlib.sha256(old.encode()).hexdigest())
    meta_new = dict(pins_file="cores/e1_pins.json", pins_sha256=hashlib.sha256(new.encode()).hexdigest())
    assert R.pins_match(meta_old, "cores/e1_pins.json", tmp_path) == "pins content differs"
    assert R.pins_match(meta_new, "cores/e1_pins.json", tmp_path) is None
    # a differently named file with the signed content matches; missing sha / missing file never match
    (tmp_path / "cores" / "e1_copy.json").write_text(new)
    assert R.pins_match(meta_new, "cores/e1_copy.json", tmp_path) is None
    assert R.pins_match(dict(pins_file="cores/e1_pins.json"), "cores/e1_pins.json", tmp_path) == "view has no pins_sha256"
    assert R.pins_match(meta_new, "cores/nope.json", tmp_path) == "plan pins_file missing"
    assert R.pins_match(meta_new, None, tmp_path) == "no plan pins_file"


def test_hb4_intra_bound_and_abutted_model():
    """CLOCK-KV-R24: intra HB4 cells = per partition worst k x its hard-core data pins; abutted model sizes k at 37.41."""
    tt = {("a", "b", "P"): (300.0, 0, False, False), ("b", "a", "P"): (300.0, 0, False, False),
          ("c", "d", "Q"): (300.0, 0, False, False)}
    ff = {("a", "b", "P"): (0, -80.0, False, False), ("b", "a", "P"): (0, -10.0, False, False),
          ("c", "d", "Q"): (0, 5.0, False, False)}
    r = R.hold_buffer_model(tt, ff, part_bits={"P": 100, "Q": 50})
    assert r["k_by_part"] == {"P": 2} and r["hb4_cells"] == 200 and r["bits_needing_hb"] == 100
    r2 = R.hold_buffer_model(tt, ff, hb=R.HB4_ABUTTED, part_bits={"P": 100, "Q": 50})
    assert r2["k_by_part"] == {"P": 3} and r2["hb4_cells"] == 300
    assert r2["all"]["tt_setup_after_ps"] == round(300.0 - 3 * 67.67, 2)
    assert R._DATA_PIN_SKIP.search("g_t_10_u_l8__clk[0]") and R._DATA_PIN_SKIP.search("strap_bsel[1]")
    assert R._DATA_PIN_SKIP.search("g_t_11_u_stk__rst_n[0]") and not R._DATA_PIN_SKIP.search("i_ck_data[3]")


def test_mesh_signoff_gap_folded_per_sample_and_stats(tmp_path):
    """PD11 ruling 3: the routed-vs-sim gap is folded into every MC sample (opposite-sign gap reduces U instead of
    adding to it), and stats() reports per-pair percentiles + the die-wide bound over the evaluated pairs."""
    import json
    M = {"taps": [{"port": p, "stub": s} for p, s in (("a", "s1"), ("b", "s2"), ("c", "s3"))]}
    (tmp_path / "mesh.json").write_text(json.dumps(M))
    # gaps routed - sim nominal: s1 +10, s2 0, s3 0 (sim nominal s1 100, s2 110, s3 100)
    rt = {"s1": dict(late=110.0, early=100.0), "s2": dict(late=110.0, early=100.0), "s3": dict(late=100.0, early=90.0)}
    (tmp_path / "mesh_TT.json").write_text(json.dumps({"stubs": rt}))
    # sim: s1 is 10 ps EARLY of s2 in every sample -> routed difference s1-s2 = 0: folded U = 0 (+ gradient 0);
    # old form would give max|d| 10 + |gap diff| 10 = 20
    so = dict(corner="TT", loads=["s1", "s2", "s3"], arr=[[100.0, 110.0, 100.0], [100.0, 110.0, 104.0],
                                                           [100.0, 110.0, 96.0]],
              grad_vec_ps=[[0.0, 0.0]] * 3, summary={}, checked="UNCHECKED")
    (tmp_path / "so.json").write_text(json.dumps(so))
    taps = {p: dict(late_ps=200.0, early_ps=190.0, cppr_node="h") for p in "abc"}
    U, rec = R.mesh_signoff(tmp_path, taps, {"cppr_node_range_ps": {"h": 0.0}}, "TT", tmp_path / "so.json", "tree")
    assert abs(U("a", "b")) < 1e-9
    # s1 - s3 + gap 10: d' = 10, 6, 14 -> MC mean 10 sd 5.657 -> 26.97 > max 14
    assert abs(U("a", "c") - (10 + 3 * 32 ** 0.5)) < 1e-4
    st = U.stats()
    assert st["pairs"] == 2 and st["max_ps"] == st["die_wide_bound_ps"] == round(10 + 3 * 32 ** 0.5, 2)
    assert st["p50_ps"] in (0.0, round(10 + 3 * 32 ** 0.5, 2))


def _gp2_core(tmp_path, name, pins, source="gen A", outline=(10.0, 8.0)):
    import json as _j
    (tmp_path / "cores").mkdir(exist_ok=True)
    d = dict(schema="opentallas.die_plan.core_pins.v1", core="c", source=source,
             frame=f"core R0, origin (0,0), outline {outline[0]} x {outline[1]}", pins=pins)
    (tmp_path / "cores" / name).write_text(_j.dumps(d))
    return f"cores/{name}"


def _gp2_signed(tmp_path, rel, outline=(10.0, 8.0)):
    import hashlib
    return dict(pins_file=rel, pins_sha256=hashlib.sha256((tmp_path / rel).read_bytes()).hexdigest(),
                outline_um=list(outline))


_GP2_PINS = [dict(name="clk", layer="M5", x=5.0, y=4.0), dict(name="a[0]", layer="M4", x=0.096, y=1.5),
             dict(name="a[1]", layer="M4", x=0.096, y=2.5), dict(name="z", layer="M3", x=9.0, y=7.904)]


def test_gate_pins2_free_text_change_same_hash(tmp_path):
    """GATE-PINS-2 (COORD ruling 1): only physical/logical pin content is hashed; 'source'/'frame' text and pin
    order never change it."""
    s = _gp2_core(tmp_path, "s_pins.json", _GP2_PINS, source="gen A")
    p = _gp2_core(tmp_path, "p_pins.json", list(reversed(_GP2_PINS)), source="gen A | R3 write-through note")
    a, b = (R.canon_pins(__import__("json").loads((tmp_path / f).read_text()), (10.0, 8.0)) for f in (s, p))
    assert R.canon_sha256(a) == R.canon_sha256(b)
    assert R.pins_relation(_gp2_signed(tmp_path, s), p, tmp_path, (10.0, 8.0), [s, p]) == ("canonical", None)
    # a view that records the canonical sha matches without any copy of the signed file
    meta = dict(pins_sha256="0" * 64, pins_canon_sha256=R.canon_sha256(a), outline_um=[10.0, 8.0])
    assert R.pins_match(meta, p, tmp_path, (10.0, 8.0)) is None


def test_gate_pins2_one_nm_move_different_hash(tmp_path):
    s = _gp2_core(tmp_path, "s_pins.json", _GP2_PINS)
    moved = [dict(q) for q in _GP2_PINS]
    moved[1]["y"] = 1.501
    p = _gp2_core(tmp_path, "p_pins.json", moved)
    J = __import__("json")
    assert R.canon_sha256(R.canon_pins(J.loads((tmp_path / s).read_text()))) != \
        R.canon_sha256(R.canon_pins(J.loads((tmp_path / p).read_text())))
    how, why = R.pins_relation(_gp2_signed(tmp_path, s), p, tmp_path, (10.0, 8.0), [s, p])
    assert how is None and why.startswith("pins differ")
    # outline change alone is a different core
    assert R.pins_match(_gp2_signed(tmp_path, s), s, tmp_path, (10.0, 8.0)) is None
    assert R.canon_sha256(R.canon_pins({"pins": _GP2_PINS}, (10.0, 8.0))) != \
        R.canon_sha256(R.canon_pins({"pins": _GP2_PINS}, (10.0, 8.001)))


def _gp2_mx(pins, H=8.0):
    return [dict(q, y=round(H - q["y"], 6)) for q in pins]


def test_gate_pins2_exact_mirror_accepted(tmp_path):
    """COORD ruling 2: an exact MX/MY/R180 image (every pin, same names and layers) is the same signed core."""
    s = _gp2_core(tmp_path, "s_pins.json", _GP2_PINS)
    mx = _gp2_core(tmp_path, "s_pins_fMX.json", _gp2_mx(_GP2_PINS), source="mirrored MX")
    my = _gp2_core(tmp_path, "s_pins_fMY.json", [dict(q, x=round(10.0 - q["x"], 6)) for q in _GP2_PINS])
    r180 = _gp2_core(tmp_path, "s_pins_fR180.json",
                     [dict(q, x=round(10.0 - q["x"], 6), y=round(8.0 - q["y"], 6)) for q in _GP2_PINS])
    v = _gp2_signed(tmp_path, s)
    ex = [s, mx, my, r180]
    assert R.pins_relation(v, mx, tmp_path, (10.0, 8.0), ex) == ("mirror:MX", None)
    assert R.pins_relation(v, my, tmp_path, (10.0, 8.0), ex) == ("mirror:MY", None)
    assert R.pins_relation(v, r180, tmp_path, (10.0, 8.0), ex) == ("mirror:R180", None)
    # signed content found as a verified copy in the view dir (plan no longer has the R0 file)
    vd = tmp_path / "view"
    vd.mkdir()
    (vd / "pins.json").write_bytes((tmp_path / s).read_bytes())
    v2 = dict(v, pins_file="cores/gone.json", view_dir=str(vd))
    assert R.pins_relation(v2, mx, tmp_path, (10.0, 8.0), [mx]) == ("mirror:MX", None)


def test_gate_pins2_mirror_one_pin_off_rejected(tmp_path):
    """an image with one pin not mapped (e.g. a kept reset pin, KV pv_pair fMX s0/s1 rst_n) is a different core."""
    s = _gp2_core(tmp_path, "s_pins.json", _GP2_PINS)
    bad = _gp2_mx(_GP2_PINS)
    bad[3]["y"] = _GP2_PINS[3]["y"]          # z kept, not mirrored
    p = _gp2_core(tmp_path, "s_pins_fMX.json", bad)
    how, why = R.pins_relation(_gp2_signed(tmp_path, s), p, tmp_path, (10.0, 8.0), [s, p])
    assert how is None and "no exact MX/MY/R180 image" in why
    # a renamed / missing pin is never an image either
    ren = _gp2_mx(_GP2_PINS)
    ren[2]["name"] = "a[2]"
    q = _gp2_core(tmp_path, "s_pins_fMX2.json", ren)
    assert R.pins_relation(_gp2_signed(tmp_path, s), q, tmp_path, (10.0, 8.0), [s, q])[0] is None


def test_gate_pins2_layer_change_rejected(tmp_path):
    s = _gp2_core(tmp_path, "s_pins.json", _GP2_PINS)
    lay = [dict(q) for q in _GP2_PINS]
    lay[1]["layer"] = "M6"
    p = _gp2_core(tmp_path, "p_pins.json", lay)
    assert R.pins_relation(_gp2_signed(tmp_path, s), p, tmp_path, (10.0, 8.0), [s, p])[0] is None
    mxl = _gp2_mx(_GP2_PINS)
    mxl[1]["layer"] = "M6"
    q = _gp2_core(tmp_path, "s_pins_fMX.json", mxl)
    assert R.pins_relation(_gp2_signed(tmp_path, s), q, tmp_path, (10.0, 8.0), [s, q])[0] is None


def test_landed_gate_empty_class_is_na():
    corners = {"TT": {"classes": {"landed": dict(pairs=0)}}, "FF": {"classes": {"landed": dict(pairs=0)}}}
    g = R.landed_gate(corners)
    assert g["verdict"] == "N/A" and g["pairs"] == 0
    assert g["tt_setup_margin_ps"] is None and g["ff_hold_margin_ps"] is None
    assert R.landed_gate({"TT": {"classes": {}}, "FF": {"classes": {}}})["verdict"] == "N/A"


def test_landed_gate_pairs_with_pass_landing():
    pl = dict(setup_margin_ps=12.5, hold_margin_ps=7.25, verdict="PASS")
    corners = {c: {"classes": {"landed": dict(pairs=4, plan_landing=pl)}} for c in ("TT", "FF")}
    g = R.landed_gate(corners)
    assert g == dict(tt_setup_margin_ps=12.5, ff_hold_margin_ps=7.25, verdict="PASS")


def test_landed_gate_pairs_without_landing_fails_closed():
    pl = dict(setup_margin_ps=12.5, hold_margin_ps=7.25, verdict="PASS")
    corners = {"TT": {"classes": {"landed": dict(pairs=4, plan_landing=pl)}},
               "FF": {"classes": {"landed": dict(pairs=4)}}}
    assert R.landed_gate(corners)["verdict"] == "FAIL"
    corners = {"TT": {"classes": {"landed": dict(pairs=0)}}, "FF": {"classes": {"landed": dict(pairs=3)}}}
    assert R.landed_gate(corners)["verdict"] == "FAIL"


def _ca_tap(part, late, early):
    return dict(part=part, cppr_node=part, late_ps=late, early_ps=early)


CA_REG = dict(clkq_max_wire_ps=48.0, clkq_min_nowire_ps=30.0)


def _ca_bind(T):
    # x: non-tree A->B, plan d [200, 250], L = 1T + d (+-0 wander); t: clean tree B->A (rise, sync_dist 150 -> limit
    # 123.5), plan d [-260, -240], L = 2T + d
    return {"sync_aperture_ps": 26.5, "ports": {
        "x": dict(src="A", dst="B", K=1, depth=4, sched_lat=2, tree=False, L_lo_ps=T + 200.0, L_hi_ps=T + 250.0,
                  d_lo_ps=200.0, d_hi_ps=250.0, wander_ps=0.0),
        "t": dict(src="B", dst="A", K=0, depth=4, sched_lat=3, tree=True, L_lo_ps=2 * T - 260.0, L_hi_ps=2 * T - 240.0,
                  d_lo_ps=-260.0, d_hi_ps=-240.0, wander_ps=0.0)},
        "regions": {"B": dict(parent=None, tree_port=None), "A": dict(parent="B", tree_port="t", edge_fall=False,
                                                                       sync_values=1, start_skew_limit_ps=123.5)}}


def test_count_align_landed_rows_lag_slot_guard_start():
    """MESO-RECONCILE-1: lag re-derived from the STA's own d (tree and non-tree), margins to the guards >= 100 ps,
    slot->read (L_lo - T/2 >= 0), guard (margin_hi >= T/8), start skew per tree edge vs the plan limit."""
    T = 833.0
    taps = {"a0": _ca_tap("A", 300.0, 280.0), "b0": _ca_tap("B", 520.0, 500.0)}
    landed = [("a0", "b0", "A->B"), ("b0", "a0", "B->A")]
    bind = _ca_bind(T)
    r = R.count_align_landed(landed, taps, bind, T, CA_REG)
    x = {o["port"]: o for o in r["rows"]}
    # STA d A->B = [500 - 300, 520 - 280] = [200, 240]
    assert x["x"]["source"] == "sta" and x["x"]["L_lo_ps"] == round(T + 200, 1) and x["x"]["L_hi_ps"] == round(T + 240, 1)
    assert x["x"]["margin_lo_ps"] == round(T + 200 - 0.5 * T, 1) and x["x"]["margin_hi_ps"] == round(3.5 * T - T - 240, 1)
    assert x["x"]["slot_read_ps"] == x["x"]["margin_lo_ps"] and x["x"]["guard_hi_slack_ps"] == round(x["x"]["margin_hi_ps"] - T / 8, 1)
    # clean tree crossing is STA-shifted too: d B->A = [280 - 520, 300 - 500] = [-240, -200]
    assert x["t"]["source"] == "sta" and x["t"]["L_lo_ps"] == round(2 * T - 240, 1)
    st = r["start_skew"]
    assert st["tree_ports"] == 1 and st["fail"] == 0 and st["rows"][0]["skew_hi_ps"] == 48.0
    assert st["rows"][0]["source"] == "model-coroute" and st["rows"][0]["sta_sync_dist_ps"] >= 26.5
    assert r["verdict"] == "PASS"
    # routed start wire 100 ps longer than the fclk wire -> skew 148 > 123.5 -> start row FAIL
    r = R.count_align_landed(landed, taps, bind, T, CA_REG, start_wire={"t": [90.0, 100.0]})
    assert r["start_skew"]["fail"] == 1 and r["verdict"] == "FAIL"
    # STA d much later than the plan on x: high margin under T/8 -> guard FAIL (and lag FAIL)
    taps2 = dict(taps, b0=_ca_tap("B", 2500.0, 2480.0))
    r = R.count_align_landed([("a0", "b0", "A->B"), ("b0", "a0", "B->A")], taps2, bind, T, CA_REG)
    xx = {o["port"]: o for o in r["rows"]}
    assert not xx["x"]["guard_ok"] and r["guard"]["fail"] >= 1 and r["verdict"] == "FAIL"
    # STA d earlier than the plan by 700 ps: lag under the low guard -> slot_read + lag FAIL
    taps3 = dict(taps, a0=_ca_tap("A", 1000.0, 980.0))
    r = R.count_align_landed([("a0", "b0", "A->B"), ("b0", "a0", "B->A")], taps3, bind, T, CA_REG)
    assert r["slot_read"]["fail"] >= 1 and r["fail"] >= 1 and r["verdict"] == "FAIL"


def test_count_align_key_region_times_every_partition_of_the_region_pair_and_fails_unbound():
    """DIE-QC-5 opt-in --count-align-key region: the bind keys crossings by REGION (bind parts[p].region; QC grp map:
    sl_E0_hc0 sits in region sl_E0_st_a).  Default 'part' leaves the A2->B tap pairs untimed and the region bind port
    without taps (QC K2: 631 no-taps ports, 231 untimed partition pairs); 'region' times all of them, and a landed
    region pair no bind crossing covers fails closed."""
    T = 833.0
    taps = {"a0": dict(_ca_tap("A", 300.0, 280.0), cppr_node="A"), "a2": dict(_ca_tap("A2", 320.0, 290.0), cppr_node="A"),
            "b0": _ca_tap("B", 520.0, 500.0)}
    landed = [("a0", "b0", "A->B"), ("a2", "b0", "A2->B"), ("b0", "a0", "B->A"), ("b0", "a2", "B->A2")]
    bind = _ca_bind(T)
    bind["parts"] = {"A": dict(region="A"), "A2": dict(region="A"), "B": dict(region="B")}
    old = R.count_align_landed(landed, taps, bind, T, CA_REG)
    assert old["key"] == "part" and old["unbound"] == 0 and old["landed_tags"] == 4      # A2 pairs silently untimed
    r = R.count_align_landed(landed, taps, bind, T, CA_REG, key="region")
    x = {o["port"]: o for o in r["rows"]}
    # region d A->B over a0 AND a2: [500 - 320, 520 - 280] = [180, 240] (part key: [200, 240])
    assert r["landed_tags"] == 2 and r["unbound"] == 0 and x["x"]["L_lo_ps"] == round(T + 180, 1)
    assert {o["port"]: o for o in old["rows"]}["x"]["L_lo_ps"] == round(T + 200, 1)
    assert r["verdict"] == "PASS"
    # a landed region pair without a bind crossing -> unbound, fail closed (default key never reports it)
    taps["c0"] = _ca_tap("C", 400.0, 380.0)
    bind["parts"]["C"] = dict(region="C")
    r = R.count_align_landed(landed + [("c0", "b0", "C->B")], taps, bind, T, CA_REG, key="region")
    assert r["unbound"] == 1 and r["unbound_tags"] == ["C->B"] and r["verdict"] == "FAIL"
    # a landed partition missing from the bind map refuses
    del bind["parts"]["C"]
    try:
        R.count_align_landed(landed + [("c0", "b0", "C->B")], taps, bind, T, CA_REG, key="region")
        raise AssertionError("expected SystemExit")
    except SystemExit as e:
        assert "lacks a region" in str(e)


def test_count_align_landed_ambiguous_tree_keeps_plan_window_and_no_taps_fails():
    T = 833.0
    taps = {"a0": _ca_tap("A", 300.0, 280.0), "b0": _ca_tap("B", 520.0, 500.0)}
    bind = _ca_bind(T)
    bind["regions"]["A"].update(sync_values=2, start_skew_limit_ps=60.0)
    r = R.count_align_landed([("a0", "b0", "A->B"), ("b0", "a0", "B->A")], taps, bind, T, CA_REG)
    x = {o["port"]: o for o in r["rows"]}
    assert x["t"]["source"] == "plan-sync" and x["t"]["L_lo_ps"] == round(2 * T - 260, 1)
    assert "sta_sync_dist_ps" not in r["start_skew"]["rows"][0] and r["start_skew"]["fail"] == 0
    bind["ports"]["y"] = dict(bind["ports"]["x"], src="C", dst="B")
    r = R.count_align_landed([("a0", "b0", "A->B"), ("b0", "a0", "B->A")], taps, bind, T, CA_REG)
    assert r["no_taps"] == 1 and r["verdict"] == "FAIL"


def test_count_align_ss_info_scales_tt_taps_and_never_gates():
    """MESO-RECONCILE: SS row = TT taps x SS/TT scale against the fixed plan; info only (SS never gates)."""
    T = 833.0
    taps = {"a0": _ca_tap("A", 300.0, 280.0), "b0": _ca_tap("B", 520.0, 500.0)}
    landed = [("a0", "b0", "A->B"), ("b0", "a0", "B->A")]
    bind = _ca_bind(T)
    r1 = R.count_align_ss_info(landed, taps, bind, T, CA_REG, 1.0)
    r0 = R.count_align_landed(landed, taps, bind, T, CA_REG)
    assert r1["rows"] == r0["rows"] and r1["info_only"] and not r1["gates"]
    r = R.count_align_ss_info(landed, taps, bind, T, CA_REG, 1.27)
    x = {o["port"]: o for o in r["rows"]}
    # d A->B scales to [1.27 * 500 - 1.27 * 300, 1.27 * 520 - 1.27 * 280] = [254, 304.8]
    assert x["x"]["L_lo_ps"] == round(T + 254.0, 1) and x["x"]["L_hi_ps"] == round(T + 304.8, 1)
    assert r["start_skew"]["rows"][0]["skew_hi_ps"] == round(48.0 * 1.27, 1)
    assert taps["a0"]["late_ps"] == 300.0   # input not mutated


def test_clock_cal_spice_scales_taps_and_ranges():
    """METHODOLOGY 12.15 b: clock arrivals x1.0485 TT / x1.0552 FF; inputs untouched; factor 1 = identity."""
    taps = {"a0": dict(_ca_tap("A", 300.0, 280.0), abs_late_ps=310.0)}
    meta = dict(cppr_node_range_ps={"h": 10.0})
    m, t = R.scale_clock(meta, taps, R.SPICE_CLOCK_CAL["TT"])
    assert abs(t["a0"]["late_ps"] - 300.0 * 1.0485) < 1e-9 and abs(t["a0"]["abs_late_ps"] - 310.0 * 1.0485) < 1e-9
    assert abs(m["cppr_node_range_ps"]["h"] - 10.485) < 1e-9 and taps["a0"]["late_ps"] == 300.0
    assert R.SPICE_CLOCK_CAL == {"TT": 1.0485, "FF": 1.0552}
    assert R.scale_clock(meta, taps, 1.0) == (meta, taps)


def test_clock_cal_spice_scales_node_arrivals_so_ocv_branch_matches_prescaled():
    """DIE-QC-5: tree node arrivals scale with the taps, so clock_ocv_fn branches (tap - node) of an in-STA
    --clock-cal spice run equal those of a proof scaled before export; inputs untouched."""
    f = R.SPICE_CLOCK_CAL["FF"]
    meta = dict(cppr_node_range_ps={"h": 2.0, "h0": 5.0}, node_late_ps={"h": 20.0, "h0": 3000.0, "m": None},
                node_early_ps={"h": 19.0, "h0": 2950.0, "m": None})
    taps = {"a": dict(_ca_tap("A", 3500.0, 3440.0)), "b": dict(_ca_tap("A", 3520.0, 3460.0))}
    m, t = R.scale_clock(meta, taps, f)
    assert abs(m["node_late_ps"]["h0"] - 3000.0 * f) < 1e-9 and abs(m["node_early_ps"]["h0"] - 2950.0 * f) < 1e-9
    assert m["node_late_ps"]["m"] is None and meta["node_late_ps"]["h0"] == 3000.0
    # branch below h0 scales by f (pre-scaled export), not by f plus (f - 1) x node insertion
    br = t["a"]["late_ps"] - m["node_late_ps"]["h0"]
    assert abs(br - (3500.0 - 3000.0) * f) < 1e-9


def test_intra_bits_reads_both_pins_file_forms(tmp_path, monkeypatch):
    """FLOW-GEN-1 10-28 (DIE-QC-10 K2b): --hold-buffers HB4 crashed in intra_bits on a run pins.json (a list of
    {bus, bit, ...}); both that form and the core-view {"pins": [{name}]} form count data pins, clock/reset skipped."""
    import json
    import types
    import schema as S
    (tmp_path / "view.json").write_text(json.dumps({"pins": [{"name": "d[0]"}, {"name": "d[1]"}, {"name": "clk"}]}))
    (tmp_path / "run.json").write_text(json.dumps([dict(bus="q", bit=0, layer="M4", x=0, y=1, face="W"),
                                                   dict(bus="q", bit=1, layer="M4", x=0, y=2, face="W"),
                                                   dict(bus="rst_n", bit=None, layer="M4", x=0, y=3, face="W")]))
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    P = types.SimpleNamespace(parts={"p0": {"type": "t"}}, types={"t": {"hard_cores": [
        {"inst": "a", "pins_file": "view.json"}, {"inst": "b", "pins_file": "run.json"}, {"inst": "c"}]}})
    monkeypatch.setattr(S, "load", lambda path: {})
    monkeypatch.setattr(S, "Plan", lambda raw: P)
    assert R._pin_names(json.loads((tmp_path / "run.json").read_text())) == ["q[0]", "q[1]", "rst_n"]
    assert R.intra_bits(plan) == {"p0": 4}


def test_start_stage_taps_form_no_intra_pairs():
    # DIE-HEAD-13: die-level start-stage taps (part None) are not one partition; partition taps keep their pairs
    taps = {"a": dict(part="p", cppr_node="p"), "b": dict(part="p", cppr_node="p"),
            "__st__h0": dict(part=None, cppr_node="h"), "__st__h1": dict(part=None, cppr_node="h"),
            "__st__h2": dict(part=None, cppr_node="h")}
    pairs, cov = R.build_pairs({"ports": []}, taps)
    assert sorted(pairs["intra"]) == [("a", "b", "p"), ("b", "a", "p")]
    assert not pairs["intra_cross_region"] and not pairs["seam"] and not pairs["landed"]
    assert cov["start_stage_taps_no_pairs"] == 3 and cov["partitions_with_taps"] == 1
    _, cov0 = R.build_pairs({"ports": []}, {k: v for k, v in taps.items() if v["part"]})
    assert "start_stage_taps_no_pairs" not in cov0


def test_source_root_is_not_an_implicit_droop_region(monkeypatch):
    taps, meta = _ocv_taps()
    for tap in taps.values():
        tap.update(cppr_node='__source__', tree_path='__source__', clock_source_root=True)
    for field in ('node_stages', 'node_late_ps', 'node_early_ps'):
        meta[field]['__source__'] = 0
    meta['node_xy_um']['__source__'] = None
    monkeypatch.setattr(R, 'CPPR_LCA', True)
    base = R.clock_ocv_fn('table', 'shared', meta, taps, 250.0)
    empty = R.clock_ocv_fn('table', 'shared', meta, taps, 250.0, region={})
    partial = R.clock_ocv_fn('table', 'shared', meta, taps, 250.0, region={'a': 'mesh:0'})
    explicit = R.clock_ocv_fn('table', 'shared', meta, taps, 250.0,
                            region={'a': 'mesh:0', 'b': 'mesh:0'})
    assert empty('a', 'b', 'hold') == base('a', 'b', 'hold')
    assert partial('a', 'b', 'hold') == base('a', 'b', 'hold')
    # A separately provided physical PDN-region binding may legitimately establish shared droop.
    assert explicit('a', 'b', 'hold') < base('a', 'b', 'hold')
