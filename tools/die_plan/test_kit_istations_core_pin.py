"""SUL0-PINFACE-1 (DIE-QC-97 11-10): kit_istations.core_pin_stations, per-hard-core pin-face station chains.

Two hard cores A and B share one face register per bus.  In bus x (4 b): A reads bits 0,1, B reads 1,2,3 (bit 1 is
broadcast); 1-bit in bus f is read BARE (f_q, a [0:0] wire) by both; out bus y (3 b): A drives bit 2, B bits 1,0.
Each core gets its own 2-station chain; must-fail mutants cover unequal depths, a read outside every chain, a
core_bits bit the core does not read, an out bit owned by no chain and a bare read of a multi-bit bus.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent

BOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [4:0] x, input wire [1:0] f, output wire [3:0] y);
    wire [3:0] x_q;
    wire x_eq;
    wire [0:0] f_q;
    wire f_eq;
    wire [0:0] a_o;
    wire [1:0] b_o;
    ot_dp_st #(.W(4)) u_bin_x (.clk(clk), .rst_n(rst_n), .d(x[3:0]), .ea(x[4]), .q(x_q), .eq(x_eq));
    ot_dp_st #(.W(1)) u_bin_f (.clk(clk), .rst_n(rst_n), .d(f[0:0]), .ea(f[1]), .q(f_q), .eq(f_eq));
    ot_dp_ste #(.W(3)) u_bout_y (.clk(clk), .rst_n(rst_n), .d({a_o[0], b_o[1:0]}), .ea(rst_n), .q(y[2:0]), .eq(y[3]));
    core_a A (.clk(clk), .c_i({x_q[1], x_q[0], f_q}), .c_o(a_o));
    core_b B (.clk(clk), .c_i({x_q[3], x_q[2], x_q[1], f_q}), .c_o(b_o));
endmodule
"""


def st(bus, core, bits, n=2, leaf=(50.0, 50.0)):
    return dict(conn="bus:" + bus, core=core, core_bits=bits, bit_route="per_bit", leaf_um=list(leaf),
                from_um=[0.0, 0.0], to_um=list(leaf), regs_um=[[10.0 * (j + 1), 0.0] for j in range(n)])


def plan(mut=None):
    ents = [st("x", "A", [0, 1]), st("x", "B", [1, 2, 3]), st("f", "A", [0]), st("f", "B", [0]),
            st("y", "A", [2]), st("y", "B", [0, 1])]
    if mut == "unequal_depth":
        ents[1] = st("x", "B", [1, 2, 3], n=3)
    if mut == "read_outside":
        ents[1] = st("x", "B", [2, 3])           # B still reads x_q[1] from the face register
    if mut == "bit_not_read":
        ents[0] = st("x", "A", [0, 1, 3])        # A does not read bit 3
    if mut == "out_unowned":
        ents[5] = st("y", "B", [0])              # y bit 1 has no chain
    if mut == "out_two_owners":
        ents[5] = st("y", "B", [0, 1, 2])
    buses = [dict(name="x", dir="in", width=4, kind="data", face="W"),
             dict(name="f", dir="in", width=1, kind="data", face="W"),
             dict(name="y", dir="out", width=3, kind="data", face="N")]
    if mut == "bare_multibit":
        buses[0]["width"] = 4
    return dict(partition_types=dict(t=dict(
        buses=buses, internal_stations=ents,
        hard_cores=[dict(inst="A", module="core_a", origin_um=[40, 40], outline_um=[20, 20]),
                    dict(inst="B", module="core_b", origin_um=[40, 80], outline_um=[20, 20])])))


def run(tmp_path, mut=None, bound=BOUND):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(plan(mut)))
    kd = tmp_path / "kit"
    kd.mkdir()
    bf = kd / "t_part_bound.sv"
    bf.write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bf)])))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), "--apply"],
                       capture_output=True, text=True)
    return r, bf, kd


def test_core_chains_in_out_and_one_bit(tmp_path):
    r, bf, kd = run(tmp_path)
    assert r.returncode == 0, r.stderr
    txt = bf.read_text()
    a = next(ln for ln in txt.splitlines() if re.match(r"\s*core_a A \(", ln))
    b = next(ln for ln in txt.splitlines() if re.match(r"\s*core_b B \(", ln))
    # in bus: each core reads the LAST station of ITS OWN chain, broadcast bit 1 on both chains
    assert "x__A_0_s1_q[1], x__A_0_s1_q[0]" in a and "x_q" not in a
    assert "x__B_1_s1_q[3], x__B_1_s1_q[2], x__B_1_s1_q[1]" in b and "x_q" not in b
    # 1-bit bus read bare (f_q): bit 0 of the core's own chain
    assert "f__A_0_s1_q[0]" in a and "f__B_1_s1_q[0]" in b
    assert not re.search(r"\bf_q\b(?!\[)", a + b)
    # chains are 2 deep and start at the face register output
    for c in ("x__A_0", "x__B_1", "f__A_0", "f__B_1", "y__A_0", "y__B_1"):
        assert len(re.findall(rf"\bu_ist_{c}_\d+ \(", txt)) == 2, c
    assert re.search(r"u_ist_x__A_0_0 \(.*\.d\(x_q\), \.ea\(x_eq\)", txt)
    # out bus: per-core chain inputs carry only that core's bits, the face register takes bit b from its owner
    assert re.search(r"u_ist_y__A_0_0 \(.*\.d\(\{a_o\[0\], 1'b0, 1'b0\}\)", txt)
    assert re.search(r"u_ist_y__B_1_0 \(.*\.d\(\{1'b0, b_o\[1\], b_o\[0\]\}\)", txt)
    bout = next(ln for ln in txt.splitlines() if "u_bout_y (" in ln)
    assert ".d({y__A_0_s1_q[2], y__B_1_s1_q[1], y__B_1_s1_q[0]})" in bout
    assert bout.lstrip().startswith("ot_dp_st ") and ".ea(y__A_0_s1_eq)" in bout
    tcl = (kd / "istations.tcl").read_text()
    assert len(re.findall(r"^is_bits u_ist_", tcl, re.M)) == 12
    assert "is_bits u_ist_y__B_1_0 y N 3 50.0 50.0 0 2 out" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert sorted((e["conn"], e["core"]) for e in rep if "core" in e) == sorted(
        [("bus:x", "A"), ("bus:x", "B"), ("bus:f", "A"), ("bus:f", "B"), ("bus:y", "A"), ("bus:y", "B")])


@pytest.mark.parametrize("mut,msg", [("unequal_depth", "unequal"), ("read_outside", "still read outside"),
                                     ("bit_not_read", "does not read bits"), ("out_unowned", "belong to no core chain"),
                                     ("out_two_owners", "in two core chains")])
def test_must_fail_mutants(tmp_path, mut, msg):
    r, bf, _ = run(tmp_path, mut)
    assert r.returncode != 0 and msg in (r.stderr + r.stdout), (mut, r.stderr[-400:])
    assert bf.read_text() == BOUND


def test_bare_read_of_multibit_bus_fails(tmp_path):
    r, bf, _ = run(tmp_path, bound=BOUND.replace("x_q[1], x_q[0], f_q", "x_q, f_q"))
    assert r.returncode != 0 and "bare whole-bus read" in r.stderr


def test_taps_sinks_only_core_bits():
    """taps.per_bit_station_sites: a per-core chain contributes its core_bits (+ epoch) only, a bus chain every bit"""
    sys.path.insert(0, str(HERE))
    import taps
    t = plan()["partition_types"]["t"]
    pins = [("x", b, "M4", 0.0, 10.0 + b, "W") for b in range(5)] + [("f", b, "M4", 0.0, 30.0 + b, "W") for b in range(2)] \
        + [("y", b, "M5", 10.0 + b, 100.0, "N") for b in range(4)]
    got = len(taps.per_bit_station_sites(t, pins))
    # x: A 2+1, B 3+1; f: A 1+1, B 1+1; y: A 1+1, B 2+1 (payload + epoch) -> 16 bit rows x 2 stations
    assert got == 2 * 16
    t2 = dict(t, internal_stations=[dict(e, core=None) for e in t["internal_stations"]])
    assert len(taps.per_bit_station_sites(t2, pins)) == 2 * (2 * 5 + 2 * 2 + 2 * 4)


def shared_plan(bits=(0, 1, 2, 3), cores=("A", "B")):
    p = plan()
    t = p["partition_types"]["t"]
    t["internal_stations"] = [st("x", list(cores), list(bits))] + [e for e in t["internal_stations"] if e["conn"] != "bus:x"]
    return p


def run_plan(tmp_path, p):
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(p))
    kd = tmp_path / "kit"
    kd.mkdir()
    bf = kd / "t_part_bound.sv"
    bf.write_text(BOUND)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bf)])))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), "--apply"],
                       capture_output=True, text=True)
    return r, bf, kd


def test_shared_chain_two_cores(tmp_path):
    """core: [A, B] -> ONE x chain; both cores read its last station (the broadcast bit 1 crosses once)"""
    r, bf, kd = run_plan(tmp_path, shared_plan())
    assert r.returncode == 0, r.stderr
    txt = bf.read_text()
    a = next(ln for ln in txt.splitlines() if re.match(r"\s*core_a A \(", ln))
    b = next(ln for ln in txt.splitlines() if re.match(r"\s*core_b B \(", ln))
    assert "x__A_B_0_s1_q[1], x__A_B_0_s1_q[0]" in a and "x_q" not in a
    assert "x__A_B_0_s1_q[3], x__A_B_0_s1_q[2], x__A_B_0_s1_q[1]" in b and "x_q" not in b
    assert len(re.findall(r"\bu_ist_x__\w+_\d+ \(", txt)) == 2          # one chain of 2, not two
    assert re.search(r"u_ist_x__A_B_0_0 \(.*\.d\(x_q\), \.ea\(x_eq\)", txt)
    tcl = (kd / "istations.tcl").read_text()
    assert "ist:x:A+B 0" in tcl
    rep = json.loads((kd / "kit_rtl.json").read_text())["kit_istations"]
    assert [e["core"] for e in rep if e.get("conn") == "bus:x"] == [["A", "B"]]


@pytest.mark.parametrize("bits,cores,msg", [((0, 1, 2), ("A", "B"), "still read outside"),     # B reads bit 3 direct
                                            ((0,), ("A", "B"), "reads none of its core_bits"),  # B reads no chain bit
                                            ((0, 1, 2, 3), ("A", "A"), "repeated hard core")])
def test_shared_chain_must_fail(tmp_path, bits, cores, msg):
    r, bf, _ = run_plan(tmp_path, shared_plan(bits, cores))
    assert r.returncode != 0 and msg in (r.stderr + r.stdout), r.stderr[-400:]
    assert bf.read_text() == BOUND


@pytest.mark.parametrize("old,new", [("x__A_B_0_s1_q[3]", "x__A_B_0_s0_q[3]"),     # B one stage early
                                     ("x__A_B_0_s1_q[2]", "x_q[2]")])               # B straight off the face reg
def test_shared_chain_consumer_wrong_delay_fails(tmp_path, old, new):
    """must-fail: one consumer of a shared chain at the wrong delay"""
    r, bf, _ = run_plan(tmp_path, shared_plan())
    assert r.returncode == 0, r.stderr
    sys.path.insert(0, str(HERE))
    import kit_istations as KI
    txt = bf.read_text()
    KI.check_core_delay("t", "x", txt, [("x__A_B_0", ["A", "B"])], 2, "x_q")       # the applied text passes
    lines = txt.split("\n")
    i = next(i for i, ln in enumerate(lines) if re.match(r"\s*core_b B \(", ln))
    assert old in lines[i]
    lines[i] = lines[i].replace(old, new)
    bad = "\n".join(lines)
    with pytest.raises(SystemExit, match="wrong delay"):
        KI.check_core_delay("t", "x", bad, [("x__A_B_0", ["A", "B"])], 2, "x_q")
    with pytest.raises(SystemExit, match="wrong delay"):     # B reading A's (unshared) chain is not its chain
        KI.check_core_delay("t", "x", txt, [("x__A_B_0", ["A"])], 2, "x_q")


def test_shared_core_schema():
    sys.path.insert(0, str(HERE))
    import schema
    sp = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["internal_stations"]
    assert {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 2,
            "uniqueItems": True} in sp["items"]["properties"]["core"]["oneOf"]


def test_taps_shared_chain_sinks():
    sys.path.insert(0, str(HERE))
    import taps
    t = shared_plan()["partition_types"]["t"]
    pins = [("x", b, "M4", 0.0, 10.0 + b, "W") for b in range(5)] + [("f", b, "M4", 0.0, 30.0 + b, "W") for b in range(2)] \
        + [("y", b, "M5", 10.0 + b, 100.0, "N") for b in range(4)]
    # x shared: 4+1 (was A 2+1 + B 3+1 = 7); f 4; y 5 -> 14 bit rows x 2 stations
    assert len(taps.per_bit_station_sites(t, pins)) == 2 * 14


# ---- SUL0-PINFACE-1 11-11: chain start at a landing macro's q pins + macro-clear geometry gate
LBOUND = """module t_part_bound (input wire clk, input wire rst_n, input wire [3:0] z, output wire [0:0] dummy);
    wire [3:0] zl;
    wire [2:0] z_q;
    wire z_eq;
    land_m L0 (
        .d(z), .q(zl));
    ot_dp_st #(.W(3)) u_bin_z (.clk(clk), .rst_n(rst_n), .d(zl[2:0]), .ea(zl[3]), .q(z_q), .eq(z_eq));
    core_a A (.clk(clk), .c_i({z_q[2], z_q[1], z_q[0]}), .c_o(dummy));
endmodule
"""


def lplan(qx=0.0, start=True):
    e = st("z", "A", [0, 1, 2], leaf=(62.0, 50.0))
    if start:
        e.update(start_core="LM", start_port="q")
    return dict(partition_types=dict(t=dict(
        buses=[dict(name="z", dir="in", width=3, kind="data", face="E")], internal_stations=[e],
        hard_cores=[dict(inst="A", module="core_a", origin_um=[40, 40], outline_um=[20, 20]),
                    dict(inst="LM", module="land_m", origin_um=[80, 10], outline_um=[10, 10],
                         pins_file="LM_pins.json")]))), [dict(name=f"q[{b}]", x=qx, y=2.0 + b) for b in range(4)]


def lrun(tmp_path, qx=0.0, bound=LBOUND):
    p, pins = lplan(qx)
    (tmp_path / "LM_pins.json").write_text(json.dumps(dict(pins=pins)))
    pf = tmp_path / "plan.json"
    pf.write_text(json.dumps(p))
    kd = tmp_path / "kit"
    kd.mkdir()
    bf = kd / "t_part_bound.sv"
    bf.write_text(bound)
    (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(bf)])))
    r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd), "--apply"],
                       capture_output=True, text=True)
    return r, bf, kd


def test_start_core_q_pins(tmp_path):
    r, bf, kd = lrun(tmp_path)
    assert r.returncode == 0, r.stderr
    tcl = (kd / "istations.tcl").read_text()
    rows = re.findall(r"^is_bits u_ist_z__A_0_\d+ .*$", tcl, re.M)
    assert len(rows) == 2
    for ln in rows:
        assert ln.endswith(" 0 {0 80.0000 12.0000 1 80.0000 13.0000 2 80.0000 14.0000 3 80.0000 15.0000}"), ln
    # a chain without start_core keeps the face BTerm (no starts list)
    sub = tmp_path / "plain"
    sub.mkdir()
    r2, _, kd2 = run(sub)
    assert r2.returncode == 0 and not re.search(r"^is_bits .*\}$", (kd2 / "istations.tcl").read_text(), re.M)


def test_start_not_on_source_edge_fails(tmp_path):
    """must-fail: the named start pin is 5 um inside the landing macro, not on its edge"""
    r, bf, _ = lrun(tmp_path, qx=5.0)
    assert r.returncode != 0 and "is not on the edge of start_core LM" in r.stderr, r.stderr[-300:]
    assert bf.read_text() == LBOUND


def test_start_core_not_the_source_fails(tmp_path):
    """must-fail: u_bin_z does not take the landing macro's q wire"""
    bad = LBOUND.replace(".d(zl[2:0]), .ea(zl[3])", ".d(z[2:0]), .ea(z[3])")
    r, bf, _ = lrun(tmp_path, bound=bad)
    assert r.returncode != 0 and "does not drive .q(z)" in r.stderr, r.stderr[-300:]      # z is the face port, not the landing output
    bad3 = LBOUND.replace(".d(zl[2:0]), .ea(zl[3])", ".d(zl[2:0]), .ea(z_eq)")
    sub3 = tmp_path / "c"
    sub3.mkdir()
    r, bf, _ = lrun(sub3, bound=bad3)
    assert r.returncode != 0 and "does not take one landed wire" in r.stderr, r.stderr[-300:]
    bad2 = LBOUND.replace(".d(z), .q(zl));", ".d(z), .q(zx));")
    sub = tmp_path / "b"
    sub.mkdir()
    r, bf, _ = lrun(sub, bound=bad2)
    assert r.returncode != 0 and "does not drive .q(zl)" in r.stderr, r.stderr[-300:]


def test_chain_macro_hits_gate():
    """an L route through a hard macro is flagged; touching within MACRO_TOL_UM is not"""
    sys.path.insert(0, str(HERE))
    import kit_istations as KI
    t = dict(hard_cores=[dict(inst="M", module="m", origin_um=[20.0, 0.0], outline_um=[10.0, 10.0])])
    b = dict(name="z", face="E")
    e = dict(leaf_um=[0.0, 30.0])
    # bit 0 row y=5 runs x 50 -> 0 straight through M; bit 1 row y=9.6 grazes M's top edge (0.4 um in)
    hits = KI.chain_macro_hits(t, e, b, {0: (50.0, 5.0), 1: (50.0, 9.6), 2: (50.0, 20.0)})
    assert hits == [(0, "M")]
    # the leaf column (x = 0) and rows above M are clear
    assert KI.chain_macro_hits(t, dict(leaf_um=[35.0, 30.0]), b, {0: (50.0, 5.0)}) == []


def test_knee_along_first_corner_tcl():
    """leg_order along_first: is_knee_site's corner sits at the pin column (W face: (px, ly)); default unchanged"""
    sys.path.insert(0, str(HERE))
    import kit_istations as I
    proc = I.TCL_HEAD[I.TCL_HEAD.index("proc is_knee_site"):I.TCL_HEAD.index("proc is_bits")]
    body = """
foreach k {1 2 3} { puts "A [is_knee_site 0 100 50 300 W $k 4 in {0 100 0 100} along]" }
foreach k {1 2 3} { puts "N [is_knee_site 0 100 50 300 W $k 4 in {0 100 0 100}]" }
if {[catch {is_knee_site 0 100 50 300 W 1 4 in {0 100 0 100} sideways} m]} { puts "E $m" }
"""
    p = subprocess.run(["tclsh"], input=proc + "\n" + body, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    rows = [l.split() for l in p.stdout.splitlines()]
    A = [tuple(map(float, r[1:])) for r in rows if r[0] == "A"]
    N = [tuple(map(float, r[1:])) for r in rows if r[0] == "N"]
    # along: legs (0,100)->(0,300)->(50,300); every site on x = 0 or y = 300
    assert all(abs(x) < 1e-9 or abs(y - 300) < 1e-9 for x, y in A) and any(abs(x) < 1e-9 and y > 100 for x, y in A)
    # normal (default): legs (0,100)->(50,100)->(50,300)
    assert all(abs(y - 100) < 1e-9 or abs(x - 50) < 1e-9 for x, y in N)
    assert any(r[0] == "E" and "knee order sideways" in " ".join(r) for r in rows)


def test_leg_order_gate_and_taps_corner():
    sys.path.insert(0, str(HERE))
    import kit_istations as KI
    import taps
    t = dict(hard_cores=[dict(inst="M", module="m", origin_um=[20.0, 0.0], outline_um=[10.0, 50.0])],
             buses=[dict(name="z", dir="in", width=1, face="E")])
    b = dict(name="z", face="E")
    # E face pin (50, 5) -> leaf (0, 80): normal-first runs y=5 through M, along-first goes up x=50 then west at y=80
    assert KI.chain_macro_hits(t, dict(leaf_um=[0.0, 80.0]), b, {0: (50.0, 5.0)}) == [(0, "M")]
    assert KI.chain_macro_hits(t, dict(leaf_um=[0.0, 80.0], leg_order="along_first"), b, {0: (50.0, 5.0)}) == []
    e = dict(conn="bus:z", bit_route="per_bit", leaf_um=[0.0, 80.0], regs_um=[[0, 0]], leg_order="along_first")
    s = taps.per_bit_station_sites(dict(t, internal_stations=[e]), [("z", 0, "M4", 50.0, 5.0, "E"), ("z", 1, "M4", 50.0, 6.0, "E")])
    assert all(not (20 < x < 30 and 0 < y < 50) for x, y, _ in s) and len(s) == 2
