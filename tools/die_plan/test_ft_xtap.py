"""HBM-VSN-XTAP 11-11 (COORD 04:18 ruling): cross-tap ft hops get a full-cycle hop flop u_fx_* (+1 cycle) in place of
the ft_hop_lockup latch; same-tap hops keep the latch.  Covers: the plan map + lane latency (schema), the hop
prediction (ft_xtap), the bound RTL + strict bind proof with the latency table, the REAL face_flops.tcl walkers and
mid-hop placement, the REAL clock_taps.tcl launch-tap pass, and an iverilog lock-step bench (hop flop == one more
station) with mutants."""
import json
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import ft_xtap  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402
import test_ft_hop_lockup as T  # noqa: E402

EX = HERE / "examples" / "bind_tiny"


def _raw(xt):
    return {"clock": {"ft_hop_lockup": {"types": ["T"], "xtap_flop": xt}}}


def test_helper_reads_map():
    assert S.ft_hop_xtap({}, "T", "ft5") == []
    assert S.ft_hop_xtap({"clock": {"ft_hop_lockup": {"types": ["T"]}}}, "T", "ft5") == []
    assert S.ft_hop_xtap(_raw({"T": {"ft5": [3, 0, 3]}}), "T", "ft5") == [0, 3]
    assert S.ft_hop_xtap(_raw({"T": {"ft5": [1]}}), "T", "ft6") == [] and S.ft_hop_xtap(_raw({"T": {"ft5": [1]}}), "U", "ft5") == []
    assert bind.ft_hop_xtap(_raw({"T": {"ft5": [2]}}), "T", "ft5") == [2]


def _stub(raw):
    p = types.SimpleNamespace(raw=raw, _lane_clock_landing_cycles={}, lanes={"l": {"ports": ["a", "b"]}},
                              ports={"a": {"src": {"part": "x"}}, "b": {"dst": {"part": "y"}}}, parts={"m": {"type": "T"}})
    p.lane_crossings = lambda _lid: [("m", "ft5", None, None)]
    p.slot = lambda _part, _slot: {"stations": 6}
    return p


def test_lane_latency_counts_hop_flops():
    assert S.Plan.lane_natural(_stub({}), "l")["cycles"] == 8
    d = S.Plan.lane_natural(_stub(_raw({"T": {"ft5": [0, 2, 4]}})), "l")
    assert (d["stations"], d["cycles"]) == (9, 11)


def test_predict_slot_nearest_tap():
    taps = [("clk", 50.0, 50.0), ("clk_t1", 50.0, 250.0)]
    t = {"outline_um": [100.0, 300.0]}
    P = types.SimpleNamespace(types={"T": t}, parts={}, ports={})
    # stations at y = 0 (in face S, projected), 90, 140, 290: taps clk, clk, t1, t1 -> only hop 1 crosses
    s = {"name": "z", "in_face": "S", "out_face": "N", "width": 2, "stations": 4,
         "bit_sites_um": [[[40, 90], [60, 90]], [[40, 160], [60, 160]], [[40, 290], [60, 290]]]}
    assert ft_xtap.predict_slot(P, "T", s, taps) == [1]
    # one bit of station 1 over the tap boundary -> the hop is cross-tap (any bit)
    s["bit_sites_um"][0][1] = [60, 151]
    assert ft_xtap.predict_slot(P, "T", s, taps) == [0, 1]
    # unknown sites count as cross-tap (safe direction)
    s2 = {"name": "z", "in_face": "S", "width": 2, "stations": 3}
    assert ft_xtap.predict_slot(P, "T", s2, taps) == [0, 1]


# ------------------------------------------------------------------ bind end to end (needs Yosys like test_bind.py)
@pytest.mark.skipif(not T.HAVE_YOSYS, reason="no Yosys")
def test_bind_xtap_flop_and_latch_prove(tmp_path):
    P = json.loads((EX / "die_plan_lanes.json").read_text())
    P["partition_types"]["tf"]["ft_slots"][0]["stations"] = 3
    P.setdefault("clock", {})["ft_hop_lockup"] = {"types": ["tf"], "xtap_flop": {"tf": {"y": [0]}}}
    P["latency"]["lanes"]["a0y"].update(cycles=6, stations=4)   # 3 stations + 1 hop flop
    P["asbuilt"]["base"] = str(EX)
    pf = tmp_path / "p.json"
    pf.write_text(json.dumps(P))
    out = tmp_path / "o"
    for c in ("elab", "bind", "verify"):
        rc = bind.main([c, str(pf), "--out", str(out), "--mem", "4"])
        if rc:
            break
    ft = (out / "rtl" / "bt_tf.sv").read_text()
    assert "u_fx_y_o_0" in ft and "u_fl_y_o_0" not in ft, ft    # cross-tap hop 0: flop, no latch
    assert "u_fl_y_o_1" in ft and "u_fx_y_o_1" not in ft         # same-tap hop 1: latch kept
    assert "u_fl_y_o_2" not in ft and "u_fx_y_o_2" not in ft
    assert ft.count("ot_dp_st #(.W(8))") == 4 and ft.count("ot_dp_lk #(.W(9))") == 1
    v = json.loads((out / "verify_report.json").read_text())
    assert rc == 0 and v["verdict"] == "PASS" and v["counts"]["mismatched"] == 0, v.get("mismatches", [])[:3]


def test_gen_rtl_emits_hop_flop():
    src = (HERE / "gen_rtl.py").read_text()
    assert "S.ft_hop_xtap(P.raw, tn, s[\"name\"])" in src and "u_fx_{n}_s{j}" in src


# ------------------------------------------------------------------ face_flops.tcl: walk through + mid-hop site
MOCK_FX = T.MOCK.replace(
    'if {$latched} { cell "${pfx}u_fl_tx_s0/q\\[0\\]\\$_DLATCH_N_" mlat {D n_s0b CLK clk} {Q n_l0}; set d1 n_l0 } else { set d1 n_s0b }',
    'if {$latched} { cell "${pfx}u_fx_tx_s0/q\\[0\\]\\$_DFF_P_" mff {D n_s0b CLK clk} {QN n_x0}; cell invx minv {A n_x0} {Y n_l0}; set d1 n_l0 } else { set d1 n_s0b }')


def test_mock_patched():
    assert MOCK_FX != T.MOCK and "u_fx_tx_s0" in MOCK_FX


def _ff_run_fx():
    FF = T.FF
    a = FF.index("set ff_st 0; set ff_st_miss 0")
    body = (MOCK_FX + T._procs(FF) + "\n"
            + "proc ff_put_near {f x y} { dict set ::props($f) getLocation [list [expr {round($x)}] [expr {round($y)}]]; "
              "return [list [expr {round($x)}] [expr {round($y)}]] }\n"
            + "design 1 {}\nset ff_done {}\nset ff_ft [dict create tx [list 3 W E {}]]\n"
            + FF[a:FF.index("close $ff_out", a)]
            + '\nputs "RESULT st=$ff_st miss=$ff_st_miss hl=$ff_hl hlmiss=$ff_hl_miss"\n')
    r = subprocess.run(["tclsh"], input=body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_face_flops_walks_through_hop_flop_and_places_it_mid_hop():
    out = _ff_run_fx()
    # hop 0 = flop u_fx_ (cross-tap), hop 1 = latch u_fl_ (same tap): stations stay 1/3, 2/3; both hop cells mid-hop
    assert "RESULT st=2 miss=0 hl=2 hlmiss=0" in out, out
    st = {r[1]: float(r[2]) for r in (ln.split("\t") for ln in out.splitlines()) if r[1:2] and r[1].startswith("st")}
    assert st == {"st1": 100.0, "st2": 200.0}, out
    hl = sorted((r[0].split("/")[0], float(r[2])) for r in (ln.split("\t") for ln in out.splitlines()) if r[1:2] == ["hl"])
    assert hl == [("u_fl_tx_s1", 150.0), ("u_fx_tx_s0", 50.0)], hl


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_landed_backward_walk_passes_the_hop_flop():
    tcl = (MOCK_FX + T._procs(T.FF) + "\ndesign 1 {}\n"
           + "set f [ff_d_driver {u_ft_tx_s1/q[0]$_DFF_P_}]\nputs \"D1=$f\"\n")
    r = subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True)
    assert "D1=u_ft_tx_s0/q[0]$_DFF_P_" in r.stdout, r.stdout + r.stderr


def test_clock_taps_hop_pass_takes_hop_flops():
    src = (HERE / "clock_taps.tcl").read_text()
    assert "u_f[lx]_" in src and "set ct_hf" in src and '!$ct_hf} continue' in src


# ------------------------------------------------------------------ iverilog: hop flop == one more station
def _xchain(name, k, xt, mutant=None):
    W = 8
    s = [f"module {name} (input wire clk, input wire rst_n, input wire [{W}:0] i, output wire [{W}:0] o);"]
    prev = "i"
    for j in range(k):
        nxt = "o" if j == k - 1 else f"s{j}"
        if j < k - 1:
            s.append(f"  wire [{W}:0] {nxt};")
        s.append(f"  ot_dp_st #(.W({W})) u_ft_{j} (.clk(clk), .rst_n(rst_n), .d({prev}[{W - 1}:0]), .ea({prev}[{W}]), "
                 f".q({nxt}[{W - 1}:0]), .eq({nxt}[{W}]));")
        prev = nxt
        if j < k - 1 and j in xt:
            s.append(f"  wire [{W}:0] {nxt}_x;")
            if mutant == "latch":
                s.append(f"  ot_dp_lk #(.W({W + 1})) u_fx_{j} (.clk(clk), .d({nxt}), .q({nxt}_x));")
            elif mutant == "noepoch":
                s.append(f"  ot_dp_st #(.W({W})) u_fx_{j} (.clk(clk), .rst_n(1'b1), .d({nxt}[{W - 1}:0]), .ea(1'b0), "
                         f".q({nxt}_x[{W - 1}:0]), .eq({nxt}_x[{W}]));")
            else:
                s.append(f"  ot_dp_st #(.W({W})) u_fx_{j} (.clk(clk), .rst_n(1'b1), .d({nxt}[{W - 1}:0]), .ea({nxt}[{W}]), "
                         f".q({nxt}_x[{W - 1}:0]), .eq({nxt}_x[{W}]));")
            prev = f"{nxt}_x"
        elif j < k - 1:
            s.append(f"  wire [{W}:0] {nxt}_l;")
            s.append(f"  ot_dp_lk #(.W({W + 1})) u_fl_{j} (.clk(clk), .d({nxt}), .q({nxt}_l));")
            prev = f"{nxt}_l"
    s.append("endmodule")
    return "\n".join(s) + "\n"


@pytest.mark.skipif(not shutil.which("iverilog"), reason="no iverilog")
@pytest.mark.parametrize("mutant,expect", [(None, "LOCKSTEP PASS"), ("latch", "MISMATCH"), ("noepoch", "MISMATCH")])
def test_lockstep_hop_flop_is_one_more_station(tmp_path, mutant, expect):
    # gold: 6 plain stations (4 plan + 2 pin cycles); dut: 4 stations, flops on hops 0 and 2, latch on hop 1
    gold = T._chain("gold", 6, False)
    src = tmp_path / "t.v"
    src.write_text("`timescale 1ns/1ps\n" + T._cells().replace("`default_nettype none", "") + gold
                   + _xchain("dut", 4, {0, 2}, mutant) + T.BENCH)
    r = subprocess.run(["iverilog", "-o", str(tmp_path / "a.out"), str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    r = subprocess.run(["vvp", str(tmp_path / "a.out")], capture_output=True, text=True)
    assert expect in r.stdout, r.stdout + r.stderr
