"""tests for die_sta.py: netlist parse, ILM extraction, SPEF filter, seam discovery, flat == ilm on a tiny pair."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_sta as D  # noqa: E402

TD = HERE / "testdata" / "die_sta"

# a liberty stand-in for the cells of testdata/die_sta (directions, clock pins, sequential)
FAKE = {
    "BUFx2_ASAP7_75t_R": dict(pins={"A": "input", "Y": "output"}, clock=set(), seq=False),
    "INVx1_ASAP7_75t_R": dict(pins={"A": "input", "Y": "output"}, clock=set(), seq=False),
    "NAND2xp33_ASAP7_75t_R": dict(pins={"A": "input", "B": "input", "Y": "output"}, clock=set(), seq=False),
    "DFFHQNx1_ASAP7_75t_R": dict(pins={"CLK": "input", "D": "input", "QN": "output"}, clock={"CLK"}, seq=True),
}


def _part():
    return D.read_verilog(TD / "part_a.v")["part_a"]


def test_read_verilog():
    nl = _part()
    assert [p[1] for p in nl.ports] == ["clk", "a_i", "a_o", "x_i", "x_o"]
    assert ("input", "a_i", 1, 0) in nl.ports
    assert len(nl.insts) == 14 and nl.assigns == [("x_o", "x_i")]
    top = D.read_verilog(TD / "die_top.v")["pair_top"]
    conns = dict(top.insts[0][2])
    assert conns["a_o"] == ["w_a[1]", "w_a[0]"]          # whole-bus reference expanded msb first


def test_ilm_cones():
    red, kept, wires, st = D.extract_ilm(_part(), FAKE, {"clk"})
    keep = {i for _, i, c in red.insts if len(c) > 1 or i in ("ckb1", "g1")}
    names = {i: c for _, i, c in red.insts}
    # interface registers + output buffers + the clock buffer of the interface registers
    for i in ("s0_0", "s0_1", "s2_0", "s2_1", "ob0", "ob1", "ckb1", "g1"):
        assert i in names
    # internal register stage and its logic are gone, except as side loads (one input pin)
    assert "mid_0" not in names and "i0" not in names
    assert [p for p, _ in names["b0"]] == ["A"] and [p for p, _ in names["ckb2"]] == ["A"]
    # a kept gate's input from removed logic is left open
    assert [p for p, _ in names["g1"]] == ["B", "Y"]
    assert [p for p, _ in names["s2_0"]] == ["CLK", "QN"]
    assert red.assigns == [("x_o", "x_i")]
    assert {"s1q[0]", "ck1", "m1[1]"} <= kept and "m0[0]" not in kept and "n_int" not in kept
    assert st["ilm_cells"] == 8 and st["cells"] == 14 and keep


def test_filter_spef(tmp_path):
    _, kept, _, _ = D.extract_ilm(_part(), FAKE, {"clk"})
    n, tot = D.filter_spef(TD / "part_a.spef", tmp_path / "f.spef", kept)
    assert (n, tot) == (1, 3)
    t = (tmp_path / "f.spef").read_text()
    assert "*D_NET *2 " in t and "*D_NET *1 " not in t and "*4 mid_0" not in t and "*5 s2_0" in t


def test_seams(tmp_path):
    p = tmp_path / "parts" / "a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    top = D.read_verilog(TD / "die_top.v")["pair_top"]
    s = D.die_seams(top, D.find_parts(tmp_path / "parts"))
    got = sorted((x["src"], x["dst"], x["dst_pin"]) for x in s)
    assert got == [("u0", "u1", "a_i[0]"), ("u0", "u1", "a_i[1]"), ("u0", "u1", "x_i")]


def test_liberty_parse(tmp_path):
    lib = tmp_path / "x.lib"
    lib.write_text('library (x) { cell (DFF) { ff (IQ, IQN) { next_state : "D"; } pin (CLK) { direction : input; '
                   'clock : true; } pin (D) { direction : input; } pin (Q) { direction : output; } } '
                   'cell (BUF) { pin (A) { direction : input; } pin (Y) { direction : output; } } }')
    c = D.read_liberty_cells([lib])
    assert c["DFF"]["seq"] and c["DFF"]["clock"] == {"CLK"} and not c["BUF"]["seq"]
    assert c["BUF"]["pins"] == {"A": "input", "Y": "output"}


def _have_sta():
    try:
        D._sta_bin()
        D.lib_dir(None) if any(Path(x).expanduser().is_dir() for x in D.LIB_DIRS) else (_ for _ in ()).throw(SystemExit)
        return True
    except SystemExit:
        return False


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_flat_equals_ilm(tmp_path):
    p = tmp_path / "parts" / "part_a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    shutil.copy(TD / "part_a.spef", p / "6_final.spef")
    res = {}
    for mode in ("flat", "ilm"):
        D.main(["run", "--top", str(TD / "die_top.v"), "--parts", str(tmp_path / "parts"), "--out",
                str(tmp_path / mode), "--mode", mode, "--corner", "TT", "--corner", "FF", "--period-ps", "300"])
        res[mode] = json.loads((tmp_path / mode / "die_sta.json").read_text())
    seam = "u0->u1/a_i"
    for corner, dly in (("TT", "max"), ("FF", "min")):
        f = res["flat"]["corners"][corner]["seams"][seam][dly]
        i = res["ilm"]["corners"][corner]["seams"][seam][dly]
        assert f["paths"] == i["paths"] == 2
        assert abs(f["worst"] - i["worst"]) < 0.01
    assert res["flat"]["verdict"]["status"] in ("PASS", "FAIL")
    # intra-partition related pairs: flat times part_a's internal reg-to-reg paths (s0 -> mid -> s2), ilm does not
    intra = res["flat"]["corners"]["TT"]["intra"]["u0"]
    assert intra["max"]["n"] == 4 and intra["min"]["n"] == 4 and abs(intra["max"]["worst"]) < 80
    assert "intra" not in res["ilm"]["corners"]["TT"] and res["flat"]["verdict"]["pairskew_TT_pairs"] >= 8 + 2
    assert D.main(["compare", str(tmp_path / "flat" / "die_sta.json"), str(tmp_path / "ilm" / "die_sta.json")]) == 0


def test_verdict_tt_ff():
    seams = {"a": {"max": dict(worst=5.0, neg=0), "min": dict(worst=3.0, neg=0)}}
    ps = {"a": dict(n=4, max=30.0, min=-20.0, max_pair=["l", "c"], min_pair=["l", "c"], p99=30.0, over=0,
                    max_cppr=30.0, min_cppr=-20.0)}
    res = dict(mode="ilm", corners={"TT": dict(exit=0, seams=seams, ffspread={"u0": dict(spread=140.0)}, pairskew=ps),
                                    "FF": dict(exit=0, seams=seams, ffspread={"u0": dict(spread=30.0)}, pairskew=ps),
                                    "SS": dict(exit=0, seams={"a": {"max": dict(worst=-100.0, neg=3)}})})
    v = D.verdict(res)
    assert v["status"] == "PASS"                          # SS never gates; spread > 80 is INFO only
    assert v["ffspread_TT_info"] == 140.0 and "ffspread_TT" not in v
    assert v["pairskew_TT"] == 30.0 and v["pairskew_TT_pairs"] == 4
    ps["a"]["min_cppr"] = -81.0                           # setup-side related pair skew beyond 80 ps
    assert D.verdict(res)["status"] == "FAIL"
    ps["a"]["min_cppr"] = -20.0
    res["corners"]["FF"]["intra"] = {"u0": {"min": dict(n=3, worst=85.0, start="a", end="b", crpr=0.0, p99=85.0,
                                                        over=1)}}
    v = D.verdict(res)
    assert v["status"] == "FAIL" and v["pairskew_FF"] == 85.0 and v["pairskew_FF_over"] == 1
    del res["corners"]["FF"]["intra"]
    del res["corners"]["FF"]
    assert D.verdict(res)["status"].startswith("NOT RUN")


def test_parse_pairskew(tmp_path):
    t = tmp_path / "s.txt"
    t.write_text("mode flat corner TT\n"
                 "PAIRSKEW g1 n 3 max 12.00 maxl u0/a/CLK maxc u1/b/D min -40.00 minl u0/c/CLK minc u1/d/D p99 40.00 over 0\n"
                 "CRPR g1 hold 2.000\nCRPR g1 setup 5.000\n"
                 "INTRA u0 max n 2 worst -30.00 from u0/x/QN to u0/y/D crpr 1.000 p99 30.00 over 0\nINTRA u1 min n 0\n")
    r = D.parse_sta(t)
    g = r["pairskew"]["g1"]
    assert (g["max_cppr"], g["min_cppr"]) == (10.0, -35.0)
    p = r["pair_skew"]
    assert p["seam_worst_abs"] == 35.0 and p["intra_worst_abs"] == 30.0 and p["worst_abs"] == 35.0
    assert p["intra_pairs"] == 2 and p["seam_pairs"] == 3


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_spine_models_agree(tmp_path):
    p = tmp_path / "parts" / "part_a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    sp = tmp_path / "spine_TT.json"
    sp.write_text(json.dumps({"parts": {"u0": {"taps": {"clk": {"offset_ps": 20.0}}},
                                        "u1": {"taps": {"clk": {"offset_ps": 0.0}}}}}))
    w = {}
    for m in ("ports", "gclk"):
        D.main(["run", "--top", str(TD / "die_top.v"), "--parts", str(tmp_path / "parts"), "--out", str(tmp_path / m),
                "--mode", "flat", "--corner", "TT", "--spine-branch", str(tmp_path / "spine_{c}.json"),
                "--spine-model", m])
        w[m] = json.loads((tmp_path / m / "die_sta.json").read_text())["corners"]["TT"]["seams"]["u0->u1/a_i"]
    assert abs(w["ports"]["max"]["worst"] - w["gclk"]["max"]["worst"]) < 0.01
    assert abs(w["ports"]["min"]["worst"] - w["gclk"]["min"]["worst"]) < 0.01


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_large_tap_offset_not_wrapped(tmp_path):
    """a tap offset beyond period/2 must show up in the clock arrivals (no half-period wrap)."""
    p = tmp_path / "parts" / "part_a"
    p.mkdir(parents=True)
    shutil.copy(TD / "part_a.v", p / "6_final.v")
    sp = tmp_path / "spine.json"
    sp.write_text(json.dumps({"parts": {"u0": {"taps": {"clk": {"offset_ps": 440.0}}},
                                        "u1": {"taps": {"clk": {"offset_ps": 0.0}}}}}))
    D.main(["run", "--top", str(TD / "die_top.v"), "--parts", str(tmp_path / "parts"), "--out", str(tmp_path / "o"),
            "--mode", "flat", "--corner", "TT", "--spine-branch", str(sp)])
    sp_u0 = json.loads((tmp_path / "o" / "die_sta.json").read_text())["corners"]["TT"]["ffspread"]["u0"]
    assert sp_u0["min"] > 440.0


# ---------------------------------------------------------------------------------------------- SPEF stitch / die tree
# two instances of one partition whose PORT nets carry long RC (clock tap wire, both halves of the seam), against the
# same circuit flattened into one netlist + one SPEF.  OpenSTA drops the port nets of `read_spef -path` (2.6.0 and
# be771a0): tap wire 16.7 ps -> 0 and seam slack 140.3 -> 190.5 ps without the stitch.
_HDR = """*SPEF "ieee 1481-1999"
*DESIGN "X"
*DATE "x"
*VENDOR "x"
*PROGRAM "x"
*VERSION "x"
*DESIGN_FLOW "NAME_SCOPE LOCAL" "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER []
*T_UNIT 1 NS
*C_UNIT 1 PF
*R_UNIT 1 OHM
*L_UNIT 1 HENRY
"""
_PART_V = """module part (clk, a_i, a_o);
 input clk;
 input a_i;
 output a_o;
 wire ck;
 wire n1;
 wire n2;
 BUFx2_ASAP7_75t_R ckb (.A(clk), .Y(ck));
 BUFx2_ASAP7_75t_R ib (.A(a_i), .Y(n1));
 DFFHQNx1_ASAP7_75t_R f (.CLK(ck), .D(n1), .QN(n2));
 BUFx2_ASAP7_75t_R ob (.A(n2), .Y(a_o));
endmodule
"""


def _dnet(name, conn, caps, res):
    return (f"*D_NET {name} {sum(c[-1] for c in caps):.6g}\n*CONN\n" + "".join(x + "\n" for x in conn) + "*CAP\n"
            + "".join(f"{k + 1} {' '.join(map(str, c))}\n" for k, c in enumerate(caps)) + "*RES\n"
            + "".join(f"{k + 1} {' '.join(map(str, r))}\n" for k, r in enumerate(res)) + "*END\n\n")


def _seg(net, a, b, r, c, p=""):
    """two-resistor wire a -> net:1 -> b (r ohm each), c pF on net:1 and on b"""
    return [(f"{net}:1{p}", c), (b, c)], [(a, f"{net}:1{p}", r), (f"{net}:1{p}", b, r)]


_PART_SPEF = (_HDR + "*PORTS\nclk I\na_i I\na_o O\n\n"
              + _dnet("clk", ["*P clk I", "*I ckb:A I"], *_seg("clk", "clk", "ckb:A", 1500, 0.005))
              + _dnet("a_i", ["*P a_i I", "*I ib:A I"], *_seg("a_i", "a_i", "ib:A", 1000, 0.004))
              + _dnet("a_o", ["*I ob:Y O", "*P a_o O"], *_seg("a_o", "ob:Y", "a_o", 800, 0.003))
              + _dnet("ck", ["*I ckb:Y O", "*I f:CLK I"], [("f:CLK", 0.002)], [("ckb:Y", "f:CLK", 200)]))
_TOP_V = """module top (clk, a_i, a_o);
 input clk;
 input a_i;
 output a_o;
 wire w;
 part u0 (.clk(clk), .a_i(a_i), .a_o(w));
 part u1 (.clk(clk), .a_i(w), .a_o(a_o));
endmodule
"""
# die clock tree: root -> b0 -> n0 -> b1 -> t_u0__clk (400+400) and b2 -> t_u1__clk (2000+2000): unequal taps
_CTREE_V = """module die_ctree (root, t_u0__clk, t_u1__clk);
 input root;
 output t_u0__clk;
 output t_u1__clk;
 wire n0;
 BUFx2_ASAP7_75t_R b0 (.A(root), .Y(n0));
 BUFx2_ASAP7_75t_R b1 (.A(n0), .Y(t_u0__clk));
 BUFx2_ASAP7_75t_R b2 (.A(n0), .Y(t_u1__clk));
endmodule
"""
_N0 = (["*I b0:Y O", "*I b1:A I", "*I b2:A I"], [("n0:1", 0.004), ("b1:A", 0.001), ("b2:A", 0.001)],
       [("b0:Y", "n0:1", 200), ("n0:1", "b1:A", 100), ("n0:1", "b2:A", 900)])
_CTREE_SPEF = (_HDR + "*PORTS\nroot I\nt_u0__clk O\nt_u1__clk O\n\n"
               + _dnet("root", ["*P root I", "*I b0:A I"], *_seg("root", "root", "b0:A", 300, 0.002))
               + _dnet("n0", *_N0)
               + _dnet("t_u0__clk", ["*I b1:Y O", "*P t_u0__clk O"], *_seg("t_u0__clk", "b1:Y", "t_u0__clk", 400, 0.003))
               + _dnet("t_u1__clk", ["*I b2:Y O", "*P t_u1__clk O"], *_seg("t_u1__clk", "b2:Y", "t_u1__clk", 2000, 0.003)))


def _flat_ref(tree, die_seg=False):
    """hand-flattened reference netlist + SPEF (instances u0_*, u1_*, ct_*; every port junction an internal node);
    die_seg: the seam has a routed die-level segment u0:a_o -500- w:1 (2 fF) -500- u1:a_i"""
    cells = []
    for u in ("u0", "u1"):
        ck = (f"c{u[1]}" if tree else "clk")
        ai = "a_i" if u == "u0" else "w"
        ao = "w" if u == "u0" else "a_o"
        cells += [f" BUFx2_ASAP7_75t_R {u}_ckb (.A({ck}), .Y({u}_ck));", f" BUFx2_ASAP7_75t_R {u}_ib (.A({ai}), .Y({u}_n1));",
                  f" DFFHQNx1_ASAP7_75t_R {u}_f (.CLK({u}_ck), .D({u}_n1), .QN({u}_n2));",
                  f" BUFx2_ASAP7_75t_R {u}_ob (.A({u}_n2), .Y({ao}));"]
    wires = ["w", "u0_ck", "u0_n1", "u0_n2", "u1_ck", "u1_n1", "u1_n2"]
    if tree:
        cells += [" BUFx2_ASAP7_75t_R ct_b0 (.A(clk), .Y(ct_n0));", " BUFx2_ASAP7_75t_R ct_b1 (.A(ct_n0), .Y(c0));",
                  " BUFx2_ASAP7_75t_R ct_b2 (.A(ct_n0), .Y(c1));"]
        wires += ["ct_n0", "c0", "c1"]
    v = ("module top (clk, a_i, a_o);\n input clk;\n input a_i;\n output a_o;\n" + "".join(f" wire {w};\n" for w in wires)
         + "\n".join(cells) + "\nendmodule\n")
    sp = _HDR + "*PORTS\nclk I\na_i I\na_o O\n\n"
    # seam w: u0 a_o half (800+800) -> junction w:3 -> u1 a_i half (1000+1000)
    if die_seg:
        sp += _dnet("w", ["*I u0_ob:Y O", "*I u1_ib:A I"],
                    [("w:1", 0.003), ("w:3", 0.003), ("w:4", 0.002), ("w:2", 0.004), ("u1_ib:A", 0.004)],
                    [("u0_ob:Y", "w:1", 800), ("w:1", "w:3", 800), ("w:3", "w:4", 500), ("w:4", "w:5", 500),
                     ("w:5", "w:2", 1000), ("w:2", "u1_ib:A", 1000)])
    else:
        sp += _dnet("w", ["*I u0_ob:Y O", "*I u1_ib:A I"], [("w:1", 0.003), ("w:3", 0.003), ("w:2", 0.004), ("u1_ib:A", 0.004)],
                    [("u0_ob:Y", "w:1", 800), ("w:1", "w:3", 800), ("w:3", "w:2", 1000), ("w:2", "u1_ib:A", 1000)])
    sp += _dnet("a_i", ["*P a_i I", "*I u0_ib:A I"], *_seg("a_i", "a_i", "u0_ib:A", 1000, 0.004))
    sp += _dnet("a_o", ["*I u1_ob:Y O", "*P a_o O"], *_seg("a_o", "u1_ob:Y", "a_o", 800, 0.003))
    for u in ("u0", "u1"):
        sp += _dnet(f"{u}_ck", [f"*I {u}_ckb:Y O", f"*I {u}_f:CLK I"], [(f"{u}_f:CLK", 0.002)], [(f"{u}_ckb:Y", f"{u}_f:CLK", 200)])
    if not tree:
        sp += _dnet("clk", ["*P clk I", "*I u0_ckb:A I", "*I u1_ckb:A I"],
                    [("clk:1", 0.005), ("u0_ckb:A", 0.005), ("clk:2", 0.005), ("u1_ckb:A", 0.005)],
                    [("clk", "clk:1", 1500), ("clk:1", "u0_ckb:A", 1500), ("clk", "clk:2", 1500), ("clk:2", "u1_ckb:A", 1500)])
    else:
        sp += _dnet("clk", ["*P clk I", "*I ct_b0:A I"], *_seg("clk", "clk", "ct_b0:A", 300, 0.002))
        conn, caps, res = _N0
        sp += _dnet("ct_n0", [c.replace("*I b", "*I ct_b") for c in conn], [("ct_" + a, c) for a, c in caps],
                    [("ct_" + a, "ct_" + b, r) for a, b, r in res])
        for k, u, r in (("0", "u0", 400), ("1", "u1", 2000)):
            n = f"c{k}"
            # ctree output half (r + r, 3 fF + 3 fF on the port node = junction c:2) + partition tap half (1500 + 1500)
            sp += _dnet(n, [f"*I ct_b{int(k) + 1}:Y O", f"*I {u}_ckb:A I"],
                        [(f"{n}:1", 0.003), (f"{n}:2", 0.003), (f"{n}:3", 0.005), (f"{u}_ckb:A", 0.005)],
                        [(f"ct_b{1 if k == '0' else 2}:Y", f"{n}:1", r), (f"{n}:1", f"{n}:2", r), (f"{n}:2", f"{n}:3", 1500),
                         (f"{n}:3", f"{u}_ckb:A", 1500)])
    return v, sp


def _ref_numbers(tmp_path, tree, corner, die_seg=False):
    v, sp = _flat_ref(tree, die_seg)
    (tmp_path / "ref.v").write_text(v)
    (tmp_path / "ref.spef").write_text(sp)
    T = [f"read_liberty {x}" for x in D.corner_libs(corner)]
    T += [f"read_verilog {tmp_path / 'ref.v'}", "link_design top", f"read_spef {tmp_path / 'ref.spef'}",
          "create_clock -name clk -period 300 [get_ports clk]", "set_propagated_clock [all_clocks]",
          f"set_clock_uncertainty {D.UNC_SETUP_PS} -setup [all_clocks]", f"set_clock_uncertainty {D.UNC_HOLD_PS} -hold [all_clocks]",
          "set ot_w [sta::worst_slack_cmd max]",
          f"set fh [open {tmp_path / 'ref.txt'} w]",
          "puts $fh \"max [get_property [get_pins u1_ib/A] slack_max] min [get_property [get_pins u1_ib/A] slack_min] "
          "l [get_property [get_pins u0_f/CLK] arrival_max_rise] c [get_property [get_pins u1_f/CLK] arrival_max_rise]\"",
          "close $fh"]
    (tmp_path / "ref.tcl").write_text("\n".join(T) + "\n")
    rc, _, _ = D.run_sta(tmp_path / "ref.tcl", tmp_path / "ref.log")
    assert rc == 0, (tmp_path / "ref.log").read_text()[-2000:]
    f = (tmp_path / "ref.txt").read_text().split()
    return {k: float(x) for k, x in zip(f[::2], f[1::2])}


def _die(tmp_path, mode, tree=False, extra=()):
    p = tmp_path / "parts" / "part"
    p.mkdir(parents=True, exist_ok=True)
    (p / "6_final.v").write_text(_PART_V)
    (p / "6_final.spef").write_text(_PART_SPEF)
    (tmp_path / "top.v").write_text(_TOP_V)
    args = ["run", "--top", str(tmp_path / "top.v"), "--parts", str(tmp_path / "parts"), "--out",
            str(tmp_path / f"o_{mode}_{tree}_{len(extra)}"), "--mode", mode, "--corner", "TT", "--corner", "FF",
            "--period-ps", "300"] + list(extra)
    if tree:
        td = tmp_path / "ctree"
        td.mkdir(exist_ok=True)
        (td / "ctree.v").write_text(_CTREE_V)
        (td / "ctree.spef").write_text(_CTREE_SPEF)
        args += ["--spine-tree", str(td)]
    D.main(args)
    return json.loads((tmp_path / f"o_{mode}_{tree}_{len(extra)}" / "die_sta.json").read_text())


def test_spef_split_and_esc(tmp_path):
    (tmp_path / "p.spef").write_text(_PART_SPEF)
    pn, st = D.spef_split(tmp_path / "p.spef", tmp_path / "core.spef")
    assert st["port_nets"] == 3 and st["core_nets"] == 1
    assert set(pn) == {"clk", "a_i", "a_o"} and pn["clk"].res[0] == ("clk", "clk:1", 1500.0)
    core = (tmp_path / "core.spef").read_text()
    assert "*D_NET ck " in core and "*D_NET clk" not in core and "*PORTS" not in core
    assert D.spef_esc("w_a[3]") == "w_a[3]" and D.spef_esc("a.b[1]/c") == r"a\.b\[1\]\/c"


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
@pytest.mark.parametrize("mode", ["flat", "ilm"])
def test_stitch_equals_flattened(tmp_path, mode):
    """die run with the stitch == the hand-flattened netlist + SPEF within 0.01 ps (seam slacks, tap arrivals)."""
    res = _die(tmp_path, mode)
    assert res["stitch"]["nets"] == 4                     # clk, w, a_i, a_o
    for corner in ("TT", "FF"):
        ref = _ref_numbers(tmp_path, False, corner)
        s = res["corners"][corner]["seams"]["u0->u1/a_i"]
        assert abs(s["max"]["worst"] - ref["max"]) < 0.01 and abs(s["min"]["worst"] - ref["min"]) < 0.01
        assert abs(float(s["max"]["launch"]) - ref["l"]) < 0.01 and abs(float(s["max"]["capture"]) - ref["c"]) < 0.01
    # without the stitch the port nets lose their RC (the gap): seam setup slack is optimistic by > 40 ps at TT
    old = _die(tmp_path, mode, extra=["--no-stitch"])
    d = old["corners"]["TT"]["seams"]["u0->u1/a_i"]["max"]["worst"] - res["corners"]["TT"]["seams"]["u0->u1/a_i"]["max"]["worst"]
    assert d > 40.0


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_spine_tree_equals_flattened(tmp_path):
    """--spine-tree: die_ctree as u_dieclk, ctree output nets stitched with the partition tap-port nets; seam slacks
    and tap arrivals == the flattened reference; related pair skew = capture - launch arrival."""
    res = _die(tmp_path, "flat", tree=True)
    assert res["spine"] == "tree" and res["spine_tree"]["unused_outputs"] == []
    for corner in ("TT", "FF"):
        ref = _ref_numbers(tmp_path, True, corner)
        c = res["corners"][corner]
        s = c["seams"]["u0->u1/a_i"]
        assert abs(s["max"]["worst"] - ref["max"]) < 0.01 and abs(s["min"]["worst"] - ref["min"]) < 0.01
        assert abs(float(s["max"]["launch"]) - ref["l"]) < 0.01 and abs(float(s["max"]["capture"]) - ref["c"]) < 0.01
        ps = c["pairskew"]["u0->u1/a_i"]
        # late capture - early launch >= late - late (min/max arrival spread of the ~0.5 ps per stage)
        assert ps["n"] == 1 and 0.0 <= ps["max"] - (ref["c"] - ref["l"]) < 3.0
        assert ps["crpr_hold"] is not None and ps["crpr_hold"] >= 0.0
        assert c["pair_skew"]["seam_worst_abs"] > 20.0                         # the 2 k-ohm tap is late
    assert res["verdict"]["pairskew_TT"] == res["corners"]["TT"]["pair_skew"]["worst_abs"]


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_spine_tree_missing_tap(tmp_path):
    td = tmp_path / "ctree"
    td.mkdir()
    (td / "ctree.v").write_text(_CTREE_V.replace(", t_u1__clk);", ");").replace(" output t_u1__clk;\n", "")
                                .replace(" BUFx2_ASAP7_75t_R b2 (.A(n0), .Y(t_u1__clk));\n", ""))
    p = tmp_path / "parts" / "part"
    p.mkdir(parents=True)
    (p / "6_final.v").write_text(_PART_V)
    (tmp_path / "top.v").write_text(_TOP_V)
    with pytest.raises(SystemExit, match="u1/clk"):
        D.main(["run", "--top", str(tmp_path / "top.v"), "--parts", str(tmp_path / "parts"), "--out", str(tmp_path / "o"),
                "--mode", "flat", "--corner", "TT", "--spine-tree", str(td)])


@pytest.mark.skipif(not _have_sta(), reason="needs OpenSTA `sta` and the ASAP7 NLDM libs")
def test_stitch_die_spef_segment(tmp_path):
    """--die-spef: the routed die-level segment of a seam joins the two partition halves at their port junctions."""
    die = tmp_path / "die.spef"
    die.write_text(_HDR + "\n" + _dnet("w", ["*I u0:a_o O", "*I u1:a_i I"], [("w:1", 0.002)],
                                        [("u0:a_o", "w:1", 500), ("w:1", "u1:a_i", 500)]))
    res = _die(tmp_path, "flat", extra=["--die-spef", str(die)])
    assert res["stitch"]["merged_die_nets"] == 1
    for corner in ("TT", "FF"):
        ref = _ref_numbers(tmp_path, False, corner, die_seg=True)
        s = res["corners"][corner]["seams"]["u0->u1/a_i"]
        assert abs(s["max"]["worst"] - ref["max"]) < 0.01 and abs(s["min"]["worst"] - ref["min"]) < 0.01
