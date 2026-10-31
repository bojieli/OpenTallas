"""S81-SERDES-PHY-1 10-31: one logical PHY content placed as its analog leaves; EW PMA views; macro black box wins."""
import json
import sys
from pathlib import Path

import bind
import gen_phys as G
import schema as S

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mem_compiler"))
import s81_pma_gen as PMA  # noqa: E402

LEF = "MACRO m\n PIN VDD\n PORT\n LAYER M5 ;\n END\n END VDD\n PIN VSS\n PORT\n LAYER M5 ;\n END\n END VSS\nEND m\n"


def _plan():
    raw = json.loads((Path(__file__).parent / "examples/tiny_plan.json").read_text())
    q = dict(lef="m.lef", lib="m_tt.lib", outline_um=[8.64, 2.16], orient="MX")
    c = dict(inst="u_phy", module="logical_phy", status="rework", origin_um=[17.28, 25.92], outline_um=[8.64, 8.64],
             physical_parts=[dict(q, physical_inst="u_bound.u_core.u_ptx", physical_master="txm", origin_um=[17.28, 32.4]),
                             dict(q, physical_inst="u_bound.u_core.u_prx", physical_master="rxm", origin_um=[17.28, 28.08])])
    raw["partition_types"]["src"]["contents"] = [c]
    p = S.Plan(raw)
    n = next(n for n, r in p.parts.items() if r["type"] == "src")
    a, b = p.to_die(n, (17.28, 25.92)), p.to_die(n, (25.92, 34.56))
    raw["die"]["pg"] = {"domains": [dict(name="phy", nets=["VDDPHY", "VSS"],
                                         rect_um=[min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])])]}
    return S.Plan(raw), c


def test_each_part_is_placed_and_powered_not_the_logical_lot(tmp_path):
    p, c = _plan()
    assert not [e for e in S.validate(p.raw) if "physical_" in e]
    macros = G.type_macros(p, "src")
    assert [m[:2] for m in macros] == [("u_bound.u_core.u_ptx", "txm"), ("u_bound.u_core.u_prx", "rxm")]
    assert macros[0][6] == "MX"
    doms = G.phy_pg_domains(p, "src")
    assert doms[0][4] == ["u_bound.u_core.u_prx", "u_bound.u_core.u_ptx"]      # no 'u_phy': no view-less macro in the domain
    (tmp_path / "m.lef").write_text(LEF)
    assert "-layers {M5 M6}" in G.phy_pg_pdn(p, "src", doms, macros, root=tmp_path)
    assert set(S.placed_macro_boxes(p.types["src"])) == {"u_bound.u_core.u_ptx", "u_bound.u_core.u_prx"}


def test_part_outside_the_domain_still_fails_closed():
    p, c = _plan()
    c["physical_parts"][0]["origin_um"] = [17.28, 33.48]
    try:
        G.phy_pg_domains(p, "src")
    except ValueError as e:
        assert "straddles" in str(e)
    else:
        raise AssertionError("straddling part accepted")


def test_view_less_content_keeps_failing_closed(tmp_path):
    p, c = _plan()
    del c["physical_parts"]
    doms = G.phy_pg_domains(p, "src")
    assert doms[0][4] == ["u_phy"]
    try:
        G.phy_pg_pdn(p, "src", doms, G.type_macros(p, "src"), root=tmp_path)
    except ValueError as e:
        assert "no macro view" in str(e)
    else:
        raise AssertionError("view-less PHY accepted")


def test_ew_form_rotates_footprint_only(tmp_path, monkeypatch):
    monkeypatch.setattr(PMA, "W_UM", PMA.H_UM)
    monkeypatch.setattr(PMA, "H_UM", 129.6)
    monkeypatch.setattr(PMA, "FORM", "ew")
    PMA.generate(tmp_path)
    for n, pins in (("ot_s81_pma_txm", 1091), ("ot_s81_pma_rxm", 1089)):
        lef = (tmp_path / n / f"{n}.lef").read_text()
        assert "SIZE 2246.400 BY 129.600 ;" in lef and "SYMMETRY X Y ;" in lef
        assert lef.count("    DIRECTION ") - 2 == pins        # all signal pins, VDD/VSS apart
        assert "parameter" not in (tmp_path / n / f"{n}_bb.v").read_text()


def test_macro_black_box_beats_behavioural_model_in_a_picked_file(tmp_path):
    r = tmp_path / "rtl"
    r.mkdir()
    (r / "col.sv").write_text("module col(input a); pma u(.a(a)); endmodule\n\nmodule pma(input a);\nreg q;\nendmodule\n")
    v = tmp_path / "views" / "pma"
    v.mkdir(parents=True)
    (v / "pma.lef").write_text("MACRO pma\nEND pma\n")
    (v / "pma_bb.v").write_text("(* blackbox *)\nmodule pma(input a);\nendmodule\n")
    idx = {"col": [str(r / "col.sv")], "pma": [str(r / "col.sv")]}
    picks = {}
    files, missing, macros = bind.kit_closure(["col"], idx, [], picks, views={"pma": v})
    assert not missing and "pma" in macros
    out, rec = bind.kit_strip_dups([Path(f) for f in files], tmp_path, picks)
    texts = {str(f): Path(f).read_text() for f in out}
    assert sum("reg q" in t for t in texts.values()) == 0                    # behavioural body gone
    assert sum("blackbox" in t for t in texts.values()) == 1


def test_macro_inside_a_clock_keepout_moves_no_grid_tap():
    """S81-SERDES-PHY-2: a part wholly inside the type's clock keepout adds no obstacle, so tap_clear keeps the
    keepout-only result (the PMA boxes had moved serdes__t16 clk_t25/clk_t31 and failed clk_t33 radius 268.7/200)."""
    t = {"outline_um": [400.0, 200.0], "clock": {"keepouts_um": [[0, 100.0, 400.0, 200.0]]}, "contents": []}
    base = S.tap_clear(t, 150.0, 150.0)
    t["contents"] = [dict(inst="u_phy", module="m", status="rework", physical_parts=[
        dict(physical_inst="u_p", physical_master="pm", lef="m.lef", origin_um=[37.0, 120.0], outline_um=[200.0, 60.0],
             orient="MX")])]
    assert S.tap_clear(t, 150.0, 150.0) == base
    t["contents"][0]["physical_parts"][0]["origin_um"] = [37.0, 60.0]     # sticks out of the keepout: a real obstacle
    assert S.tap_clear(t, 150.0, 80.0) != S.tap_clear({k: v for k, v in t.items() if k != "contents"}, 150.0, 80.0)


def test_kit_contract_resolves_physical_parts(tmp_path):
    import kit_contract as KC
    raw = {"partition_types": {"src": {"contents": [dict(inst="u_phy", module="m", status="rework", outline_um=[9.0, 9.0],
                                                          physical_parts=[dict(physical_inst="u_bound.u_core.u_ptx",
                                                                               physical_master="txm", lef="t.lef",
                                                                               origin_um=[1.0, 2.0], outline_um=[8.0, 2.0],
                                                                               orient="MX")])]}}}
    (tmp_path / "die_plan.json").write_text(json.dumps(raw))
    kd = tmp_path / "kit"
    kd.mkdir()
    (kd / "budget.json").write_text(json.dumps({"type": "src"}))
    got = KC._plan_contents(kd, tmp_path)
    assert got["u_bound.u_core.u_ptx"]["module"] == "txm" and got["u_bound.u_core.u_ptx"]["outline_um"] == [8.0, 2.0]


def test_mirrored_instance_minus_zero_domain_edge_is_the_same_domain():
    """S81-SERDES-PHY-3: serdes__t14 lk_EN3 (MY) mapped its PHY domain edge to -0.0, lk_WS2 to 0.0; the per-instance
    identity compared JSON text and failed on the sign of zero alone."""
    p, _ = _plan()
    doms = G.phy_pg_domains(p, "src")
    assert all(not str(v).startswith("-0.0") for d in doms for v in d[3])
    assert json.dumps(-0.0 + 0.0) == "0.0"


def _kp4_delta():
    import importlib.util
    p = Path(__file__).resolve().parents[2] / "physical/die_plan/s81/delta_kp4_srams_1031.py"
    spec = importlib.util.spec_from_file_location("delta_kp4", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_kp4_srams_sit_below_the_shore_off_ft_windows_and_taps():
    """S81-SERDES-PHY-3: the decoder SRAM leaves go to the highest free core band under the PHY keepout, off the ft pin
    windows and >= the tap clearance from every grid tap; a type with only ft bands falls back into one."""
    D = _kp4_delta()
    rx = dict(physical_inst="u_bound.u_core.u_prx", physical_master="ot_s81_pma_rxm", origin_um=[300.0, 900.0],
              outline_um=[2246.4, 129.6])
    t = {"outline_um": [2885.76, 1226.88], "clock": {"keepouts_um": [[0, 681.372, 2885.76, 1226.88]]},
         "ft_slots": [{"in_window_um": [570.048, 681.372]}, {"in_window_um": [456.96, 568.868]}],
         "contents": [{"physical_parts": [rx]}]}
    got = D.place(t, [(1443.0, 153.0)])
    assert got and all(y + D.H <= 456.96 - D.GAP and y >= 153.0 + D.CLEAR for *_, y in got)
    (_, _, w0, x0, _), (_, _, _, x1, _) = got
    assert x1 - (x0 + w0) >= D.GAP
    t["ft_slots"] = [{"in_window_um": [8.0, 681.0], "in_face": "E", "out_face": "W", "stations": 8}]
    assert D.place(t, []) is None
    got = D.place(t, [], ft_bands=False)                    # each SRAM in its own gap between the station columns
    cols = D._station_columns(t, got[0][4])
    assert len(cols) == 9 and all(not (x - D.CLEAR < c < x + w + D.CLEAR) for _, _, w, x, _ in got for c in cols)


def test_macro_pin_pads_become_bumps_on_the_placed_part(tmp_path):
    """S81-SERDES-PHY-3: a type pad with macro_pin is a bump of that placed physical part (no bind report needed), with
    the netlist port kind as dir; a kit-rtl wrapper must carry it as a bound-only pin; a clock pad cannot be one."""
    from types import SimpleNamespace
    import pytest
    import gen_phys as G
    import gen_rtl
    D = _kp4_delta()
    part = dict(physical_inst=D.TXM, physical_master="ot_s81_pma_txm", lef="x.lef", origin_um=[1.0, 2.0], orient="MX",
                outline_um=[2246.4, 129.6])
    rx = dict(part, physical_inst=D.RXM, physical_master="ot_s81_pma_rxm")
    t = {"pads": [dict(p) for p in D.PADS], "contents": [{"inst": "u_phy", "physical_parts": [part, rx]}]}
    P = SimpleNamespace(types={"t": t})
    got = G.pad_bumps(P, "t")
    assert [(b["port"], b["inst"], b["module"], b["pin"], b["dir"], b["width"]) for b in got] == [
        ("io_pma_tx", D.TXM, "ot_s81_pma_txm", "pma_tx", "output", 544),
        ("io_pma_tck", D.TXM, "ot_s81_pma_txm", "pma_tck", "output", 1),
        ("io_pma_rx", D.RXM, "ot_s81_pma_rxm", "pma_rx", "input", 544)]
    fl = tmp_path / "files.f"
    (tmp_path / "kit_rtl.json").write_text(json.dumps({"bound_only_pins": [
        dict(port="io_pma_tx", dir="output", width=544), dict(port="io_pma_tck", dir="output", width=1),
        dict(port="io_pma_rx", dir="input", width=543)]}))
    with pytest.raises(gen_rtl.GenError, match="io_pma_rx"):
        G.pad_bumps(P, "t", fl)
    t["pads"][0] = dict(t["pads"][0], clock=True)
    with pytest.raises(gen_rtl.GenError, match="not a clock pad"):
        G.pad_bumps(P, "t")
    assert G.pad_bumps(SimpleNamespace(types={"t": {"pads": [D.PADS[3]]}}), "t") == []
