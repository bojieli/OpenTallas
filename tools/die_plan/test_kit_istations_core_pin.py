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
