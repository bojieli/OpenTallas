import copy
import pytest
import core_infra as CI
import core_infra_plan as CP
from test_core_infra import sample


def test_plan_legalization_freezes_legal_sites_before_build():
    s=sample();u=1000
    tech=dict(dbu=u,core=[0,0,864000,864000],
      rows=[dict(rect=[0,y,864000,y+270],site=54,orient='R0' if j%2==0 else 'MX')
            for j,y in enumerate(range(427680,436320,270))],
      masters={'BUFx16f_ASAP7_75t_R':[1188,270],'BUFx4_ASAP7_75t_R':[378,270]},
      obstacles=[dict(name='fixed_driver',kind='fixed',rect=[431000,432270,433000,432810])])
    a,report=CP.legalize_slice(s,tech)
    b,_=CP.legalize_slice(s,tech)
    assert a==b and report['cell_or_macro_overlaps']==0
    cells=CI.compile_slice(a)['cells']
    assert len(cells)==2 and all(c['origin_um'][0]*1000%54==pytest.approx(0) for c in cells)
    assert 'ot_ci_origin_assert' in CI.emit_tcl(a)
    mutant=copy.deepcopy(a);mutant['cell_placements']['mp_isl0_ck0']['master']='BUFx24_ASAP7_75t_R'
    with pytest.raises(CI.InfraError,match='master differs'):CI.compile_slice(mutant)


def test_predictor_detects_wire_load_imbalance_without_changing_plan():
    s=sample();s['core_tree']=dict(clock_port='clk',nodes=[
      dict(name='root',master='BUFx16f_ASAP7_75t_R',xy_um=[430,430],parent='port:clk'),
      dict(name='left',master='BUFx8_ASAP7_75t_R',xy_um=[200,430],parent='root'),
      dict(name='right',master='BUFx8_ASAP7_75t_R',xy_um=[660,430],parent='root')],
      leaves=[dict(node='left',sinks=['a/CLK','b/CLK']),dict(node='right',sinks=['c/CLK','d/CLK'])])
    lib=dict(delay=([10,100],[1,100],[[10,30],[20,40]]),trans=([10,100],[1,100],[[10,30],[20,40]]),cap=1.)
    libs={'TT':{n:lib for n in ('BUFx16f_ASAP7_75t_R','BUFx8_ASAP7_75t_R')}}
    pts={'a/CLK':[195,430],'b/CLK':[205,430],'c/CLK':[655,430],'d/CLK':[665,430]};caps={n:.5 for n in pts}
    saved=copy.deepcopy(s)
    balanced=CP.predict_tree(s,libs,pts,caps,.02,.1)
    assert balanced['corners']['TT']['window_ps']==pytest.approx(0)
    pts['d/CLK']=[800,430]
    imbalanced=CP.predict_tree(s,libs,pts,caps,.02,.1)
    assert imbalanced['corners']['TT']['window_ps']>1 and s==saved


def test_actual_corner_caps_and_declared_source_slew_propagate():
    from core_infra_search import Model
    s=sample();s['core_tree']=dict(clock_port='clk',nodes=[
      dict(name='root',master='BUFx16f_ASAP7_75t_R',xy_um=[430,430],parent='port:clk')],
      leaves=[dict(node='root',sinks=['a/CLK'])])
    lib=dict(delay=([0,100],[0,100],[[10,30],[20,40]]),trans=([0,100],[0,100],[[10,30],[20,40]]),cap=1.)
    libs={c:{'BUFx16f_ASAP7_75t_R':lib} for c in ('TT','FF')}
    pts={'a/CLK':[435,430]};caps={'a/CLK':{'TT':.5,'FF':.8}}
    result=CP.predict_tree(s,libs,pts,caps,.02,.1,input_slew_ps=0.)
    fast=Model(s,libs,pts,caps,.02,.1,input_slew_ps=0.).evaluate(['BUFx16f_ASAP7_75t_R'])
    for c in libs:assert fast[c]['mean']==pytest.approx(result['corners'][c]['mean_ps'])
    assert fast['FF']['mean']>fast['TT']['mean']
    slower=Model(s,libs,pts,caps,.02,.1,input_slew_ps=40.).evaluate(['BUFx16f_ASAP7_75t_R'])
    assert slower['TT']['mean']>fast['TT']['mean']
    with pytest.raises(KeyError):CP.sink_cap({'TT':.5},'FF')


def test_cached_rooted_model_matches_shared_predictor_after_driver_change():
    from core_infra_search import Model
    s=sample();s['core_tree']=dict(clock_port='clk',nodes=[
      dict(name='root',master='BUFx16f_ASAP7_75t_R',xy_um=[430,430],parent='port:clk'),
      dict(name='leaf',master='BUFx8_ASAP7_75t_R',xy_um=[440,440],parent='root')],
      leaves=[dict(node='leaf',sinks=['a/CLK','b/CLK'])])
    lib=dict(delay=([0,100],[0,100],[[10,30],[20,40]]),trans=([0,100],[0,100],[[10,30],[20,40]]),cap=1.)
    other={**lib,'cap':2.}
    libs={c:{'BUFx16f_ASAP7_75t_R':lib,'BUFx8_ASAP7_75t_R':other} for c in ('TT','FF')}
    pts={'a/CLK':[450,440],'b/CLK':[460,440]};caps={p:{'TT':.5,'FF':.8} for p in pts}
    profile=dict(horizontal_rc=[.1,.2],vertical_rc=[.2,.3],merge_collinear=True);routing=dict(nonleaf=profile,leaf=profile)
    model=Model(s,libs,pts,caps,0,0,input_slew_ps=0,routing_model=routing)
    for chosen in ('BUFx8_ASAP7_75t_R','BUFx16f_ASAP7_75t_R'):
        changed=copy.deepcopy(s);changed['core_tree']['nodes'][1]['master']=chosen
        detailed=CP.predict_tree(changed,libs,pts,caps,0,0,input_slew_ps=0,routing_model=routing)
        fast=model.evaluate(['BUFx16f_ASAP7_75t_R',chosen])
        for corner in libs:
            assert fast[corner]['mean']==pytest.approx(detailed['corners'][corner]['mean_ps'])
            assert fast[corner]['all_max']==pytest.approx(detailed['corners'][corner]['max_ps'])


def test_snapshot_tcl_list_parser_without_python_tk(tmp_path,monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules,'tkinter',None)
    p=tmp_path/'technology.tsv'
    p.write_text('DBU 1000\nCORE 0 0 100 100\nOBSTACLE {g_bank\\[0\\].u_m} macro 1 2 3 4\n')
    data=CP.read_technology(p)
    assert data['obstacles'][0]['name']==r'g_bank\[0\].u_m'
    assert data['obstacles'][0]['rect']==[1,2,3,4]


# ---- PLAN-ICG-MODEL: gated leaves + CTS-open subtrees -------------------------------------------------------------
import json
import math
from pathlib import Path
from test_core_infra import icg_tree

VALIDATION = Path(__file__).resolve().parents[2] / "results/plan_icg_model_1026/validation_points.json"


def _lin(cap):
    return dict(delay=([0, 100], [0, 100], [[10, 30], [20, 40]]), trans=([0, 100], [0, 100], [[10, 30], [20, 40]]), cap=cap)


def _icg_slice():
    s = icg_tree()
    s["core_tree"]["leaves"][0]["region_rect_um"] = [0, 216, 432, 648]
    s["core_tree"]["leaves"][1]["region_rect_um"] = [432, 216, 864, 648]
    return s


def _icg_inputs():
    libs = {c: {m: _lin(1.) for m in ("BUFx16f_ASAP7_75t_R", "BUFx12_ASAP7_75t_R", "BUFx8_ASAP7_75t_R",
                                      "ICGx1_ASAP7_75t_R", CP.CTS_ROOT_MASTER)} for c in ("TT", "FF")}
    pts = {"a/CLK": [200, 420], "b/CLK": [230, 440], "c/CLK": [634, 420], "d/CLK": [664, 440]}
    return libs, pts, {p: .5 for p in pts}


def test_gated_leaf_is_parent_plus_icg_arc_plus_open_subtree():
    s = _icg_slice(); libs, pts, caps = _icg_inputs()
    r = CP.predict_tree(s, libs, pts, caps, .02, .1, input_slew_ps=0.)
    tt = r["corners"]["TT"]
    leaf = {l["node"]: l for l in tt["leaf_means"]}
    g0 = leaf["u_e.g_cgr.u_cg_r0.u_icg"]
    assert g0["kind"] == "gated_domain" and g0["sinks"] == 6000 and g0["modelled_subtree"]
    sub = CP.open_subtree(6000, [0, 216, 432, 648], "TT", [216, 430])
    assert g0["mean_ps"] == pytest.approx(g0["driver_out_ps"] + sub["mean_ps"])
    assert g0["min_ps"] < g0["mean_ps"] < g0["max_ps"] and sub["levels"] == 3
    # the ICG is a timed stage: its net is in the report with the gate as driver
    icg_net = [n for n in tt["nets"] if n["driver"] == "u_e.g_cgr.u_cg_r0.u_icg"][0]
    assert icg_net["kind"] == "icg" and icg_net["input_arrival_ps"] > 0
    assert g0["driver_out_ps"] == pytest.approx(icg_net["input_arrival_ps"] + icg_net["cell_delay_ps"] +
                                                0, abs=1e-6)  # root buffer at the driver: zero wire
    # symmetric plan -> symmetric gated domains; cts_open ungated leaves are modelled too
    g1 = leaf["u_e.g_cgr.u_cg_r1.u_icg"]
    assert g1["mean_ps"] == pytest.approx(g0["mean_ps"] - (sub["mean_ps"] - CP.open_subtree(5800, [432, 216, 864, 648], "TT", [648, 430])["mean_ps"]))
    assert leaf["tw"]["kind"] == "cts_open" and leaf["tw"]["sinks"] == 1500
    assert tt["sinks"] == 6000 + 5800 + 1500 + 1500
    assert r["corners"]["FF"]["mean_ps"] < tt["mean_ps"]        # FF calibration is faster than TT
    assert "liberty CLK->GCLK" in r["basis"]


def test_gated_prediction_refuses_without_geometry_or_tables():
    libs, pts, caps = _icg_inputs()
    s = icg_tree()                                               # no region_rect_um / island on the gates
    with pytest.raises(CI.InfraError, match="region_rect_um"):
        CP.predict_tree(s, libs, pts, caps, .02, .1)
    s = _icg_slice(); bad = copy.deepcopy(libs); del bad["TT"]["ICGx1_ASAP7_75t_R"]
    with pytest.raises(CI.InfraError, match="liberty table for ICGx1"):
        CP.predict_tree(s, bad, pts, caps, .02, .1)
    bad = copy.deepcopy(libs); del bad["TT"][CP.CTS_ROOT_MASTER]
    with pytest.raises(CI.InfraError, match="CTS-open leaf"):
        CP.predict_tree(s, bad, pts, caps, .02, .1)


def test_open_subtree_grows_with_stages_and_region_and_is_plan_only():
    a = CP.open_subtree(500, [0, 0, 100, 100], "TT")
    assert a["levels"] == 2 and a["region_d_um"] == pytest.approx(100)
    assert CP.open_subtree(5000, [0, 0, 100, 100], "TT")["mean_ps"] > a["mean_ps"]
    assert CP.open_subtree(500, [0, 0, 200, 200], "TT")["mean_ps"] > a["mean_ps"]
    off = CP.open_subtree(500, [0, 0, 100, 100], "TT", [0, 0])           # driver at a corner reaches farther
    assert off["region_d_um"] == pytest.approx(200) and off["mean_ps"] > a["mean_ps"]
    assert CP.open_subtree(500, [0, 0, 100, 100], "FF")["mean_ps"] < a["mean_ps"]
    for c in ("TT", "FF"):
        assert set(CP.OPEN_SUBTREE_CAL[c]) == {"stage_ps", "region_ps_per_um", "lo_ps_per_um", "hi_ps_per_um"}


def test_icg_liberty_arc_parser(tmp_path):
    tab = 'index_1 ("5, 10");\n index_2 ("1, 2");\n values ( \\\n "10, 12", \\\n "14, 16");'
    lib = ("library (x) {\n  cell (ICGx1_ASAP7_75t_R) {\n    pin (GCLK) {\n      timing () {\n        related_pin : \"CLK\";\n"
           "        timing_type : combinational_fall;\n        cell_fall (t) {\n " + tab.replace("10, 12", "99, 99") + "\n }\n      }\n"
           "      timing () {\n        related_pin : \"CLK\";\n        cell_rise (t) {\n " + tab + "\n }\n"
           "        rise_transition (t) {\n " + tab + "\n }\n      }\n    }\n"
           "    pin (CLK) {\n      clock : true;\n      rise_capacitance : 2.13873;\n    }\n  }\n}\n")
    (tmp_path / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib").write_text(lib)
    c = CP.icg_lib_cells("TT", tmp_path)["ICGx1_ASAP7_75t_R"]
    assert c["cap"] == pytest.approx(2.13873) and c["delay"][2] == [[10, 12], [14, 16]]


def _measured_domain_prediction(p, libs, cal=None):
    """Same chain as predict_tree for one gated leaf, started from the MEASURED arrival/slew at the ICG CLK pin
    (the upstream tree of these cores is CTS-grown, not plan-built): ICG NLDM arc at one CTS root buffer + subtree."""
    import die_clock_128 as C128
    lib = libs[p["corner"]]
    icg = C128._bilin(lib[p["master"]]["delay"], p["clk_slew"], lib[CP.CTS_ROOT_MASTER]["cap"])
    sub = CP.open_subtree(p["n"], p["rect"], p["corner"], p["icg_xy"], cal=cal)
    return p["clk_arr"] + icg + sub["mean_ps"], p["clk_arr"] + icg + sub["max_ps"]


@pytest.mark.skipif(not VALIDATION.exists(), reason="validation fixture not in this checkout")
def test_validation_against_measured_gated_cores():
    """Residual of the calibrated model on routed signed-off gated cores (PLAN-ICG-MODEL 10-26 table)."""
    fx = json.loads(VALIDATION.read_text())
    libs = {c: {m: dict(delay=tuple(v["delay"]), trans=tuple(v["trans"]), cap=v["cap"]) for m, v in t.items()} for c, t in fx["libs"].items()}
    band = {("bfcol", "TT"): 16, ("bfcol", "FF"): 12, ("qxpq", "TT"): 3, ("qxpq", "FF"): 2}
    for (core, corner), lim in band.items():
        P = [p for p in fx["points"] if p["core"] == core and p["corner"] == corner]
        w = sum(p["n"] for p in P)
        pred = sum(_measured_domain_prediction(p, libs)[0] * p["n"] for p in P) / w
        meas = sum(p["mean"] * p["n"] for p in P) / w
        assert abs(pred - meas) <= lim, (core, corner, pred, meas)
        rms = math.sqrt(sum((_measured_domain_prediction(p, libs)[0] - p["mean"]) ** 2 for p in P) / len(P))
        assert rms <= (16 if core == "bfcol" else 3), (core, corner, rms)


def test_plan_sta_model_emits_icg_stage_and_combines_open_subtrees(tmp_path):
    import core_infra_sta as CS
    s = _icg_slice(); _, pts, _ = _icg_inputs()
    prof = dict(horizontal_rc=[.02, .1], vertical_rc=[.02, .1], merge_collinear=True)
    ff = [dict(name="CLK", direction="input", clock=True), dict(name="D", direction="input", clock=False),
          dict(name="QN", direction="output", clock=False)]
    icg = [dict(name="GCLK", direction="output", clock=False), dict(name="CLK", direction="input", clock=True),
           dict(name="ENA", direction="input", clock=False), dict(name="SE", direction="input", clock=False)]
    data = dict(routing_model=dict(nonleaf=prof, leaf=prof), points=pts,
                terminal_cells={p: dict(master="DFFHQNx1_ASAP7_75t_R", pin="CLK") for p in pts},
                master_pins={"DFFHQNx1_ASAP7_75t_R": ff, "ICGx1_ASAP7_75t_R": icg})
    meta = CS.emit_model(s, data, tmp_path)
    v = (tmp_path / "model.v").read_text()
    assert "ICGx1_ASAP7_75t_R g0 (.GCLK(gn0), .CLK(n1), .ENA(1'b1), .SE(1'b0));" in v
    assert f"{CP.CTS_ROOT_MASTER} r0 (.A(gn0), .Y(rn0));" in v
    # cts_open ungated leaves are not wired to their planned driver: no listed sink in the model netlist
    assert meta["sinks"] == [] and len(meta["open_domains"]) == 4
    spef = (tmp_path / "plan.spef").read_text()
    assert "*D_NET gn0 " in spef and "*I g0:CLK I" in spef
    tcl = (tmp_path / "model.tcl").read_text()
    assert "open:u_e.g_cgr.u_cg_r0.u_icg" in tcl and "get_pins {r0/A}" in tcl
    arr = {c: {"open:" + o["node"]: 100. for o in meta["open_domains"]} for c in ("TT", "FF")}
    out = CS.combine_arrivals(meta, arr)
    o0 = [o for o in meta["open_domains"] if o["node"] == "u_e.g_cgr.u_cg_r0.u_icg"][0]
    g0 = [g for g in out["TT"]["open_domains"] if g["node"] == o0["node"]][0]
    assert g0["mean_ps"] == pytest.approx(100 + o0["subtree"]["TT"]["mean_ps"]) and out["TT"]["sinks"] == 14800


# ---- COORD 10-26 condition: out-of-calibration (whole-core / multi-level) gated domains are INVALID for gating ----
OUTLINES = {"qxpq": [510.84, 221.4], "bfcol": [450.168, 198.72]}


@pytest.mark.skipif(not VALIDATION.exists(), reason="validation fixture not in this checkout")
def test_calibration_envelope_flags_exactly_the_whole_core_gates():
    fx = json.loads(VALIDATION.read_text())
    out = set()
    for p in fx["points"]:
        k = CI._cts_levels(dict(domain_sinks=p["n"], cts_fanout=CI.CTS_FANOUT), "x")
        why = CP.calibration_check(p["n"], k, CP.region_reach(p["rect"], p["icg_xy"]), p["rect"], OUTLINES[p["core"]])
        if why:
            out.add((p["core"], p["icg"]))
            assert any("whole-core" in w for w in why) and any("sinks" in w for w in why)
    # the two bf_col whole-core gates (16,213 / 13,994 sinks, under-predicted ~50 ps TT) and nothing else
    assert out == {("bfcol", "g_tcg.u_tc.u_cg.u_icg"), ("bfcol", "g_bf.g_fqt.u_bf.u_tt.u_cg.u_icg")}


def _regional_slice(n=1400, half=50):
    s = _icg_slice()
    for i, x in ((0, 216), (1, 648)):
        s["core_tree"]["leaves"][i].update(domain_sinks=n, region_rect_um=[x - half, 430 - half, x + half, 430 + half])
    for leaf in s["core_tree"]["leaves"][2:]:
        leaf["domain_sinks"] = n
    return s


def test_regional_one_level_gates_valid_whole_core_and_nested_invalid():
    libs, pts, caps = _icg_inputs()
    ok = CP.predict_tree(_regional_slice(), libs, pts, caps, .02, .1)["corners"]["TT"]
    assert ok["prediction"] == "VALID" and ok["valid_for_build_gating"] and not ok["out_of_calibration_leaves"]
    assert all(l["calibration"] == "IN" for l in ok["leaf_means"] if l.get("modelled_subtree"))
    whole = _regional_slice(); whole["core_tree"]["leaves"][0].update(domain_sinks=13800, region_rect_um=[0, 0, 864, 864])  # k=3: equal stages, still whole-core
    bad = CP.predict_tree(whole, libs, pts, caps, .02, .1)["corners"]["TT"]
    assert bad["prediction"] == "INVALID" and not bad["valid_for_build_gating"]
    assert bad["out_of_calibration_leaves"] == ["u_e.g_cgr.u_cg_r0.u_icg"]
    row = [l for l in bad["leaf_means"] if l["node"] == "u_e.g_cgr.u_cg_r0.u_icg"][0]
    assert row["calibration"] == "OUT" and any("whole-core" in w for w in row["out_of_calibration"])
    assert row["mean_ps"] > 0                                   # the number is still reported, only not gate-valid
    nested = _regional_slice(); nested["core_tree"]["leaves"][1]["nested_gates"] = 2
    n = CP.predict_tree(nested, libs, pts, caps, .02, .1)["corners"]["FF"]
    assert n["prediction"] == "INVALID" and any("multi-level" in w for l in n["leaf_means"] for w in l.get("out_of_calibration", []))


def test_plan_sta_combine_marks_out_of_calibration_invalid(tmp_path):
    import core_infra_sta as CS
    _, pts, _ = _icg_inputs()
    prof = dict(horizontal_rc=[.02, .1], vertical_rc=[.02, .1], merge_collinear=True)
    ff = [dict(name="CLK", direction="input", clock=True), dict(name="QN", direction="output", clock=False)]
    icg = [dict(name="GCLK", direction="output", clock=False), dict(name="CLK", direction="input", clock=True),
           dict(name="ENA", direction="input", clock=False), dict(name="SE", direction="input", clock=False)]
    data = dict(routing_model=dict(nonleaf=prof, leaf=prof), points=pts,
                terminal_cells={p: dict(master="DFFHQNx1_ASAP7_75t_R", pin="CLK") for p in pts},
                master_pins={"DFFHQNx1_ASAP7_75t_R": ff, "ICGx1_ASAP7_75t_R": icg})
    for s, verdict in ((_regional_slice(), "VALID"), (_icg_slice(), "INVALID")):
        meta = CS.emit_model(s, data, tmp_path / verdict)
        arr = {c: {"open:" + o["node"]: 100. for o in meta["open_domains"]} for c in ("TT", "FF")}
        res = CS.combine_arrivals(meta, arr)
        assert res["TT"]["prediction"] == verdict and res["FF"]["valid_for_build_gating"] == (verdict == "VALID")
