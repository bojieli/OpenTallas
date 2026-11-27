import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seat_match as SM  # noqa: E402
import strap_bank_seats as SB  # noqa: E402
from type_relay_seat_io import style_of  # noqa: E402

TEXT = """module t_part (input wire clk);
  wire [7:0] x_fw_i_q;
  ot_dp_dly #(.W(8), .D(3)) u_lpad_x_fw_i (.clk(clk), .d(x_fw_i), .q(x_fw_i_q));
  ot_dp_dly #(.W(8), .D(4)) u_r8b_strap_a_f (.clk(clk), .d(x_fw_i_q[7:0]), .q(aq));
  ot_dp_dly_cnt #(.W(8), .DMAX(3)) u_r8b_strap_a (.clk(clk), .strap_cnt(s), .d(aq), .q(ao));
  other_leaf u_leaf (.clk(clk));
endmodule
"""


def _v(keys, **kw):
    return SM.judge(keys if isinstance(keys, dict) else {k: [1.0, 2.0] for k in keys}, TEXT, **kw)


def test_verdicts():
    v = _v(["u_lpad_x_fw_i.r[1][7]", "u_lpad_x_fw_i.q[0]", "u_lpad_x_fw_i.r[2][0]", "u_lpad_x_fw_i.q[8]", "u_pd5_x_fw_i_3.q",
            "u_leaf/u.q[0]", "u_r8b_strap_a.q[1]", "u_r8b_strap_a/r[2][1]", "u_r8b_strap_a/r[3][1]"])
    assert [v[k] for k in v] == ["OK", "OK", "DEAD-REG", "DEAD-REG", "DEAD-INST", "UNKNOWN", "OK-CNT", "OK", "DEAD-REG"]


def test_station_buses_and_conflict():
    v = _v(["u_ist_b_0/q[1]", "u_ist_b_2/q[1]"], ist_buses={"b": 2})
    assert list(v.values()) == ["UNKNOWN", "DEAD-INST"]
    v = _v({"u_lpad_x_fw_i.q[1]": [1, 2], "u_lpad_x_fw_i/q[1]": [1, 2], "u_lpad_x_fw_i.q[2]": [1, 2], "u_lpad_x_fw_i/q[2]": [9, 2]})
    assert list(v.values()) == ["OK", "OK", "CONFLICT", "CONFLICT"]


def test_hint_names_the_bank():
    assert SM.hint(["u_pd5_x_fw_i_3.q"], TEXT) == {"x_fw_i": ["u_r8b_strap_a_f"]}


def test_prune_drops_dead_only_and_keeps_byte_style(tmp_path):
    plan = {"partition_types": {"t": {"relay_sites": {"u_lpad_x_fw_i.q[0]": [1, 2], "u_pd5_x_fw_i_3.q": [3, 4], "u_leaf/u.q": [5, 6]}}}}
    p, out, led = tmp_path / "p.json", tmp_path / "o.json", tmp_path / "l.json"
    p.write_text(json.dumps(plan, indent=1) + "\n")
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_part.sv").write_text(TEXT)
    assert SM.main(["prune", str(p), str(tmp_path / "rtl"), str(out), str(led)]) == 0
    assert sorted(json.loads(out.read_text())["partition_types"]["t"]["relay_sites"]) == ["u_leaf/u.q", "u_lpad_x_fw_i.q[0]"]
    assert out.read_text() == json.dumps(json.loads(out.read_text()), indent=1) + "\n"
    assert json.loads(led.read_text())["dropped"]["t"]["u_pd5_x_fw_i_3.q"] == {"verdict": "DEAD-INST", "site": [3, 4]}


def test_kit_lines(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_bound.sv").write_text(TEXT)
    (tmp_path / "istations.tcl").write_text("rs_place_all {{u_lpad_x_fw_i.q[0]} {1.0 2.0} {u_pd5_x_fw_i_3.q} {3.0 4.0}}\n")
    ln = SM.kit_lines(tmp_path)
    assert len(ln) == 1 and "SEAT-MISS WARN 1 of 2" in ln[0] and "u_r8b_strap_a_f" in ln[0]
    (tmp_path / "istations.tcl").write_text("rs_place_all {{u_lpad_x_fw_i.q[0]} {1.0 2.0}}\n")
    assert SM.kit_lines(tmp_path) == []


def test_bank_keys_and_path():
    assert SB.split_key("u_r8b_strap_a_f.r[2][5]") == ("u_r8b_strap_a", True, "r", 2, 5)
    assert SB.split_key("u_r8b_strap_a_f.q[5]") == ("u_r8b_strap_a", True, "q", None, 5)
    assert SB.split_key("u_r8b_strap_a/r[2][5]") == ("u_r8b_strap_a", False, "r", 2, 5)
    assert SB.split_key("u_lpad_x.q[5]") is None
    p = SB.lay([(0.0, 0.0), (400.0, 0.0)], 3, 2, 40.0)
    assert [a[0] for a in p] == [120.0, 240.0, 360.0, 380.0, 400.0]
    assert SB.lay([(5.0, 5.0)], 2, 2) == [(5.0, 5.0)] * 4
    assert SB.lay([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)], 3, 0) == [(50.0, 0.0), (100.0, 0.0), (100.0, 50.0)]


def test_route_goes_around_a_macro():
    die, m = (0.0, 0.0, 100.0, 100.0), (30.0, 10.0, 60.0, 90.0)
    pts = SB.route((10.0, 50.0), (80.0, 40.0), [m], die)
    assert pts[0] == (10.0, 50.0) and pts[-1] == (80.0, 40.0) and any(p[1] == 10.0 for p in pts)
    assert sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])) == 140.0
    assert SB.route((10.0, 50.0), (80.0, 40.0), [(30.0, -1.0, 60.0, 101.0)], die) is None
    assert SB.outside((31.0, 50.0), [m], die) == (30.0, 50.0)


def test_style_round_trip():
    for txt in ('{"a":1}\n', '{"a": 1}', '{\n "a": 1\n}\n'):
        assert style_of(txt.encode())(json.loads(txt)) == txt


def test_emitter_on_small_dump(tmp_path):
    """launch flop -> f chain (3) -> count bank (2) -> sink flop; seats run launch -> sink and the dead u_pd rows are dropped with their reach"""
    cells = [("1", "S", "u_lpad_x_fw_i.q[0]$_DFF_P_", 10), ("2", "S", "u_bound.u_r8b_strap_a_f.r[0][0]$_DFF_P_", 50), ("3", "S", "u_bound.u_r8b_strap_a_f.q[0]$_DFF_P_", 60),
             ("4", "S", "u_bound.u_r8b_strap_a/r[0][0]$_DFF_P_", 70), ("5", "S", "u_bound.u_r8b_strap_a/r[1][0]$_DFF_P_", 80), ("6", "S", "snk$_DFF_P_", 310)]

    class D:
        die = (0.0, 0.0, 400.0, 400.0)
        pin_by_k = {}
        def __init__(self, path):
            self.cells = {c: (k, "DFF", x - 0.1, 99.9, x + 0.1, 100.1, nm) for c, k, nm, x in cells}
            chain = [c[0] for c in cells]
            self.nets = [("s", ("i", a, False), [("i", b, False)]) for a, b in zip(chain, chain[1:])]
            self.drives = {a: [i] for i, a in enumerate(chain[:-1])}
            self.cell_in = {b: [(i, False)] for i, b in enumerate(chain[1:])}
            self.nets[3] = ("s", ("i", "4", False), [("i", "5", False), ("i", "6", False)])      # the mux may take r[0]
    (tmp_path / "tools" / "autopilot").mkdir(parents=True)
    import types
    G = types.ModuleType("geom_rules")
    G.Design, G.ctr = D, lambda c: ((c[2] + c[4]) / 2, (c[3] + c[5]) / 2)
    old = sys.modules.get("geom_rules")
    sys.modules["geom_rules"] = G
    try:
        base = tmp_path / "p.json"
        base.write_text(json.dumps({"partition_types": {"t": {"relay_sites": {"u_pd5_x_fw_i_0.q": [1, 2], "u_lpad_x_fw_i.q[0]": [10, 100]}}}}))
        (tmp_path / "rtl").mkdir()
        (tmp_path / "rtl" / "t_part.sv").write_text(TEXT)
        assert SB.main([str(tmp_path), "x", str(base), "t", str(tmp_path / "o.json"), str(tmp_path / "r.json"),
                        "--bound-rtl", str(tmp_path / "rtl"), "--drop"]) == 0
    finally:
        if old is None:
            sys.modules.pop("geom_rules", None)
        else:
            sys.modules["geom_rules"] = old
    rs = json.loads((tmp_path / "o.json").read_text())["partition_types"]["t"]["relay_sites"]
    rep = json.loads((tmp_path / "r.json").read_text())
    assert "u_pd5_x_fw_i_0.q" not in rs and rs["u_lpad_x_fw_i.q[0]"] == [10, 100]
    assert rs["u_r8b_strap_a/r[1][0]"][0] == 310.0 and rs["u_r8b_strap_a/r[0][0]"][0] >= 270.0
    assert rep["banks"]["u_r8b_strap_a"]["hop_um"] <= 130.5 and rep["banks"]["u_r8b_strap_a"]["placed_hop_um"] == 240.0
    assert rep["dropped"]["x_fw_i"]["rows"] == 1 and rep["dropped"]["x_fw_i"]["new_hop_um"] <= 130.5


def test_findings_warn_only(tmp_path):
    (tmp_path / "t_part.sv").write_text(TEXT)
    plan = {"partition_types": {"t": {"relay_sites": {"u_pd5_x_fw_i_3.q": [3, 4], "u_lpad_x_fw_i.q[0]": [1, 2]}}}}
    ln = SM.findings(plan, tmp_path, {"partition_types": {"t": {"relay_sites": {}}}})
    assert len(ln) == 1 and ln[0].startswith("WARN SEATMATCH t: 1 of 2") and "1 NEW" in ln[0] and "u_r8b_strap_a_f" in ln[0]
    plan["partition_types"]["t"]["relay_sites"].pop("u_pd5_x_fw_i_3.q")
    assert SM.findings(plan, tmp_path) == []


def test_kit_lines_unknown_is_failing(tmp_path):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "t_bound.sv").write_text(TEXT)
    (tmp_path / "istations.tcl").write_text("rs_place_all {{u_leaf/u.q[0]} {1.0 2.0}}\n")
    assert SM.judge({"u_leaf/u.q[0]": [1, 2]}, TEXT) == {"u_leaf/u.q[0]": "UNKNOWN"}
    assert "UNKNOWN" in SM.FAILING and "UNKNOWN" not in SM.DEAD          # prune keeps DEAD only
    out = SM.kit_lines(tmp_path)
    assert out and "1 UNKNOWN key(s) not judged" in out[0]
    (tmp_path / "istations.tcl").write_text("rs_place_all {{u_lpad_x_fw_i.q[0]} {1.0 2.0}}\n")
    assert SM.kit_lines(tmp_path) == []                                 # clean control


def test_child_module_resolves_unknown():
    mods = {"child": "module child (input clk);\n  reg [3:0] b;\n  gc u_in (.clk(clk));\nendmodule\n", "gc": "module gc (input clk);\n  reg q;\nendmodule\n"}
    t = "module top (input clk);\n  child u_c (.clk(clk));\n  hardmac u_h (.clk(clk));\nendmodule\n"
    v = SM.judge({"u_c.b[0]": [1, 2], "u_c/u_in.q": [1, 2], "u_c.nope[0]": [1, 2], "u_h.x[0]": [1, 2]}, t, modules=mods)
    assert v == {"u_c.b[0]": "OK", "u_c/u_in.q": "OK", "u_c.nope[0]": "UNKNOWN", "u_h.x[0]": "UNKNOWN"}      # unresolved / black box stays UNKNOWN (fails)
