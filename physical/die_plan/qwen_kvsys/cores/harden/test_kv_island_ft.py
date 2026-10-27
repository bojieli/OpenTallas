"""KV-CORES-PV2 10-27: gen_core_kit_kv island ft arcs (12.2a1, CLOCK-KV-R25 island_ft) -- plan view parse, RTL ports +
kept cells, OpenROAD keep/place/check procs, ft_ports declaration + ft-safe SDC, kit netlist gate, face_guard skip."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[4] / "tools/die_plan"
sys.path.insert(0, str(TOOLS))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


gk = _load("gk_ft", HERE / "gen_core_kit_kv.py")
cp = _load("cp_ft", HERE / "core_preflight.py")

W, H = 380.16, 190.08


def view(**over):
    """r25 kv3_pv_pair-like view: node arc k0 (1 cell) + mesh-driver arc k1 (2 parallel cells)."""
    pins = [dict(name="s0__clk[0]", layer="M5", x=190.104, y=95.04), dict(name="d[0]", layer="M4", x=0.096, y=10.024),
            dict(name="ft_ck_i_0", layer="M5", x=267.0, y=43.335), dict(name="ft_ck_o_0", layer="M5", x=270.84, y=43.335),
            dict(name="ft_ck_i_1", layer="M5", x=106.344, y=138.375),
            dict(name="ft_ck_o_1", layer="M5", x=111.816, y=138.375)]
    arcs = [dict(source="ft_ck_i_0", sink="ft_ck_o_0", kind="clock", role="tree_node", cells=1,
                 master="BUFx24_ASAP7_75t_R", rect_um=[268.11, 43.2, 269.73, 43.47]),
            dict(source="ft_ck_i_1", sink="ft_ck_o_1", kind="clock", role="mesh_driver", cells=2,
                 master="BUFx24_ASAP7_75t_R", rect_um=[107.46, 138.24, 110.7, 138.51])]
    for k, v in over.items():
        if k == "pins":
            pins = v(pins)
        elif k == "arcs":
            arcs = v(arcs)
    return dict(pins=pins, island_ft=dict(arcs=arcs))


def test_arcs_from_plan_view():
    arcs, names = gk.island_ft_arcs(view(), W, H)
    assert names == {"ft_ck_i_0", "ft_ck_o_0", "ft_ck_i_1", "ft_ck_o_1"}
    assert [a["k"] for a in arcs] == [0, 1]
    assert [c["name"] for c in arcs[1]["cells"]] == ["mp_isl1_ck0", "mp_isl1_ck1"]
    assert [(c["x_um"], c["y_um"]) for c in arcs[1]["cells"]] == [(107.46, 138.24), (109.08, 138.24)]
    assert gk.island_ft_arcs(dict(pins=[]), W, H) == ([], set())


def _set_pin(name, **kv):
    def f(pins):
        return [dict(p, **kv) if p["name"] == name else p for p in pins]
    return f


@pytest.mark.parametrize("bad, msg", [
    (dict(pins=_set_pin("ft_ck_i_0", x=267.336)), "closer than"),                  # in-port too close to the cell
    (dict(pins=_set_pin("ft_ck_o_1", x=111.83)), "off the M5 tracks"),
    (dict(pins=_set_pin("ft_ck_i_1", y=140.0)), "not on the island row"),
    (dict(pins=_set_pin("ft_ck_o_0", layer="M4")), "interior M5"),
    (dict(pins=lambda p: [q for q in p if q["name"] != "ft_ck_o_0"]), "not in the pin view"),
    (dict(arcs=lambda a: [dict(a[0], sink="ft_ck_o_1")] + a[1:]), "ft_ck_i_<k> -> ft_ck_o_<k>"),
    (dict(arcs=lambda a: [dict(a[0], cells=2)] + a[1:]), "not 2 x"),
    (dict(arcs=lambda a: [dict(a[0], master="BUFx4_ASAP7_75t_R")] + a[1:]), "not supported"),
    (dict(arcs=lambda a: [dict(a[0], kind="reset")] + a[1:]), "only clock"),
    (dict(arcs=lambda a: [dict(a[0], rect_um=[268.12, 43.2, 269.74, 43.47])] + a[1:]), "off the site/row grid"),
])
def test_arcs_fail_closed(bad, msg):
    with pytest.raises(SystemExit) as e:
        gk.island_ft_arcs(view(**bad), W, H)
    assert msg in str(e.value)


RTL = """`default_nettype none
module kv3_pv_pair (
    input wire [0:0] s0__clk,
    output wire [0:0] s0__fault
);
    assign s0__fault = 1'b0;
endmodule
module other (input wire a); endmodule
"""


def test_rtl_ports_and_kept_cells():
    arcs, _ = gk.island_ft_arcs(view(), W, H)
    t = gk.island_ft_rtl(RTL, "kv3_pv_pair", arcs)
    head = t[:t.index("endmodule")]
    for p in ("input wire ft_ck_i_0,", "output wire ft_ck_o_0,", "input wire ft_ck_i_1,", "output wire ft_ck_o_1,"):
        assert p in head
    assert "(* keep = 1, dont_touch = 1 *) BUFx24_ASAP7_75t_R mp_isl1_ck1 (.A(ft_ck_i_1), .Y(ft_ck_o_1));" in head
    assert t.count("BUFx24_ASAP7_75t_R") == 3 and t.endswith("module other (input wire a); endmodule\n")
    with pytest.raises(SystemExit):                       # second application: names already used
        gk.island_ft_rtl(t, "kv3_pv_pair", arcs)
    with pytest.raises(SystemExit):                       # non-ANSI header
        gk.island_ft_rtl("module kv3_pv_pair (a, b);\ninput a;\nendmodule\n", "kv3_pv_pair", arcs)


def test_tcl_procs():
    arcs, _ = gk.island_ft_arcs(view(), W, H)
    t = gk.island_ft_tcl(arcs, "kv3_pv_pair__380.16x190.08")
    for p in ("proc ot_ft_keep", "proc ot_ft_place", "proc ot_ft_check", "setPlacementStatus FIRM", "setDoNotTouch 1"):
        assert p in t
    assert "{mp_isl1_ck1 BUFx24_ASAP7_75t_R 109.08 138.24 ft_ck_i_1 ft_ck_o_1}" in t
    assert "{ft_ck_i_1 ft_ck_o_1 2}" in t
    assert t.count("{") == t.count("}")


def test_ft_declaration_and_safe_sdc(tmp_path):
    import ft_ports as FTP
    import sdc_lint
    arcs, _ = gk.island_ft_arcs(view(), W, H)
    sdc = gk.sdc(833.0, 250.0, 40.0, ["s0__clk"], [], "t")
    ctx = dict(period_ps=833.0, insertion_ps=250.0, insertion_ff_ps=202.5, insertion_tol_ps=40.0, clock_ports=["s0__clk"],
               inputs=["d"], outputs=["s0__fault"], unc_setup_ps=sdc_lint.POLICY_SETUP_PS,
               unc_hold_ps=sdc_lint.POLICY_HOLD_PS, time_unit_ps=1.0, io_floor_ps={"d": 166.6, "s0__fault": 166.6},
               port_latency_ps={}, straps=[])
    assert not sdc_lint.lint(sdc, **ctx)
    (tmp_path / "constraint.sdc").write_text(sdc)
    (tmp_path / "sdc_lint.json").write_text(json.dumps(ctx))
    decl = FTP.declaration([dict(cell=c["name"], source=a["source"], sink=a["sink"], kind="clock")
                            for a in arcs for c in a["cells"]], "cores/x.json@t island_ft")
    assert [a["cells"] for a in decl["arcs"]] == [["mp_isl0_ck0"], ["mp_isl1_ck0", "mp_isl1_ck1"]]
    assert FTP.install(tmp_path, decl)
    new = (tmp_path / "constraint.sdc").read_text()
    assert "all_inputs" not in new and "all_outputs" not in new and "ft_ck" not in new
    assert json.loads((tmp_path / "sdc_lint.json").read_text())["ft_ports"]["sha256"] == decl["sha256"]
    assert not sdc_lint.lint_kit_files(tmp_path)


NET = """module kv3_pv_pair(s0__clk, d, q, ft_ck_i_0, ft_ck_o_0, ft_ck_i_1, ft_ck_o_1);
  input s0__clk; input d; output q;
  input ft_ck_i_0; output ft_ck_o_0; input ft_ck_i_1; output ft_ck_o_1;
  (* keep = 1 *)
  BUFx24_ASAP7_75t_R mp_isl0_ck0 (
    .A(ft_ck_i_0),
    .Y(ft_ck_o_0)
  );
  BUFx24_ASAP7_75t_R mp_isl1_ck0 (.A(ft_ck_i_1),
    .Y(ft_ck_o_1));
  BUFx24_ASAP7_75t_R mp_isl1_ck1 (.A(ft_ck_i_1),
    .Y(ft_ck_o_1));
  DFFHQNx1_ASAP7_75t_R r (.CLK(s0__clk), .D(d), .QN(q));
EXTRA
endmodule
"""


def test_netlist_gate(tmp_path):
    arcs, _ = gk.island_ft_arcs(view(), W, H)
    n = tmp_path / "n.v"
    n.write_text(NET.replace("EXTRA", ""))
    assert cp.island_ft_gate(n, "kv3_pv_pair", arcs)["verdict"] == "PASS"
    n.write_text(NET.replace("EXTRA", "  INVx1_ASAP7_75t_R spy (.A(ft_ck_i_1), .Y(x));"))      # core logic on an ft port
    r = cp.island_ft_gate(n, "kv3_pv_pair", arcs)
    assert r["verdict"] == "FAIL" and r["bad"][0][0] == "ft_ck_i_1"
    n.write_text(NET.replace("EXTRA", "").replace("mp_isl1_ck1 (.A(ft_ck_i_1)", "mp_isl1_ck1 (.A(s0__clk)"))
    assert cp.island_ft_gate(n, "kv3_pv_pair", arcs)["verdict"] == "FAIL"     # a parallel driver lost its input


def test_face_guard_skips_declared_ft_ports(tmp_path):
    import signoff
    net = tmp_path / "n.v"
    net.write_text(NET.replace("EXTRA", ""))
    pins = [dict(bus="d", bit=None, layer="M4", x=0.0, y=1.0, face="W"), dict(bus="q", bit=None, layer="M4", x=0.0, y=2.0, face="W")]
    pins += [dict(bus=f"ft_ck_{d}_{k}", bit=None, layer="M5", x=10.0, y=10.0, face="interior") for k in (0, 1) for d in "io"]
    (tmp_path / "pins.json").write_text(json.dumps(pins))
    disc = dict(kit=str(tmp_path), synth=str(net), pins=str(tmp_path / "pins.json"))
    before = signoff.run_face_guard(disc, clock_ports=["s0__clk"])
    import ft_ports as FTP
    decl = FTP.declaration([dict(cell="mp_isl0_ck0", source="ft_ck_i_0", sink="ft_ck_o_0", kind="clock"),
                            dict(cell="mp_isl1_ck0", source="ft_ck_i_1", sink="ft_ck_o_1", kind="clock"),
                            dict(cell="mp_isl1_ck1", source="ft_ck_i_1", sink="ft_ck_o_1", kind="clock")], "t")
    (tmp_path / "ft_ports.json").write_text(json.dumps(decl))
    after = signoff.run_face_guard(disc, clock_ports=["s0__clk"])
    # the declared ft ports leave the face-register set (only d / q are checked); without the declaration they are
    # checked (and fail) as face pins
    assert after["checked"] == 2 and "ft_ck" not in json.dumps(after.get("fails")), after
    assert before["checked"] > 2 and "ft_ck" in json.dumps(before.get("fails")), before
