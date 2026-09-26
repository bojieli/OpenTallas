"""Scan insertion, ATPG and gate-level confirmation on a toy ASAP7 netlist.

The toy has every case the scan inserter must handle: plain positive-edge
flops (swapped for SDFH), an asynchronous set/reset flop (kept, with a scan
multiplexer), a negative-edge flop (swapped for SDFL, ordered first in a mixed
chain), a second clock domain (a lock-up latch where a mixed chain crosses
into it), and an asynchronous reset driven by logic rather than a port (forced
inactive by the added test_mode input).  The end-to-end test runs the ATPG
engine and then confirms the patterns and a sample of faults on the netlist
itself in Icarus.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dft import liberty as lib  # noqa: E402
from dft import netlist as nl  # noqa: E402
from dft import scan_insert  # noqa: E402

LIBERTY = lib.default_asap7_liberty()
pytestmark = pytest.mark.skipif(
    not all(p.is_file() for p in LIBERTY), reason="needs the local ASAP7 liberty mirror"
)

TOY = """
module toy(clk, clk2, rst_n, a, b, c, y, z, w);
  input clk; input clk2; input rst_n; input a; input b; input c;
  output y; output z; output w;
  wire q0n, q1n, q2n, q3n, q4n, q5n, d1, one, rloc, x1;
  DFFHQNx1_ASAP7_75t_R r0 (.CLK(clk), .D(a), .QN(q0n));
  DFFHQNx1_ASAP7_75t_R r1 (.CLK(clk), .D(d1), .QN(q1n));
  NAND2xp5_ASAP7_75t_R g0 (.A(q0n), .B(b), .Y(d1));
  TIEHIx1_ASAP7_75t_R t0 (.H(one));
  DFFASRHQNx1_ASAP7_75t_R r2 (.CLK(clk), .D(q1n), .QN(q2n), .RESETN(rst_n), .SETN(one));
  DFFLQNx1_ASAP7_75t_R r3 (.CLK(clk), .D(c), .QN(q3n));
  DFFHQNx1_ASAP7_75t_R r4 (.CLK(clk2), .D(q3n), .QN(q4n));
  AND2x2_ASAP7_75t_R g3 (.A(rst_n), .B(q0n), .Y(rloc));
  DFFASRHQNx1_ASAP7_75t_R r5 (.CLK(clk2), .D(x1), .QN(q5n), .RESETN(rloc), .SETN(one));
  XOR2xp5_ASAP7_75t_R g1 (.A(q2n), .B(q4n), .Y(y));
  INVx1_ASAP7_75t_R g2 (.A(q3n), .Y(z));
  OR2x2_ASAP7_75t_R g4 (.A(q5n), .B(q1n), .Y(x1));
  BUFx2_ASAP7_75t_R g5 (.A(q5n), .Y(w));
endmodule
"""


@pytest.fixture(scope="module")
def cells(tmp_path_factory):
    return lib.load_cells(LIBERTY, tmp_path_factory.mktemp("libcache"))


def _insert(cells, **kw):
    mod = nl.parse_netlist(TOY)[0]
    return scan_insert.insert_scan(mod, cells, **kw)


def test_liberty_functions(cells):
    sdfh = cells["SDFHx1_ASAP7_75t_R"]
    expr = lib.parse_function(sdfh["ff"]["next_state"])
    # SE=0 -> !D, SE=1 -> !SI
    for d in (0, 1):
        for si in (0, 1):
            assert lib.evaluate(expr, {"D": d, "SE": 0, "SI": si}) == 1 - d
            assert lib.evaluate(expr, {"D": d, "SE": 1, "SI": si}) == 1 - si
    assert lib.parse_function("A B + !C") == ("or", [("and", [("var", "A"), ("var", "B")]), ("not", ("var", "C"))])


def test_no_mix_gives_one_chain_per_domain(cells):
    text, rep = _insert(cells, chains=1)
    doms = {(d["clock"], d["edge"]): d["flops"] for d in rep["clock_domains"]}
    assert doms == {("clk", "pos"): 3, ("clk", "neg"): 1, ("clk2", "pos"): 2}
    assert rep["chain_count"] == 3
    assert rep["lockup_latches"] == 0
    assert rep["scan_cells"] == 4 and rep["scan_mux_cells"] == 2
    for chain in rep["chains"]:
        assert len({(c["clock"], c["edge"]) for c in chain["cells"]}) == 1
    # the logic-driven reset of r5 is forced inactive by test_mode
    assert rep["ports"]["test_mode"] == "test_mode"
    assert rep["async_set_reset_fixes"] == [{"inactive_value": 1, "net": "rloc", "pins": 1}]
    assert rep["capture_constraints"] == {"scan_en": 0, "test_mode": 1, "rst_n": 1}
    # the result parses and every flop is a scan cell or has a mux in front
    mod = nl.parse_netlist(text)[0]
    kinds = {i.name: i.cell for i in mod.instances}
    assert kinds["r0"] == "SDFHx1_ASAP7_75t_R" and kinds["r3"] == "SDFLx1_ASAP7_75t_R"
    assert kinds["r2"] == "DFFASRHQNx1_ASAP7_75t_R"
    assert sum(1 for i in mod.instances if i.name.startswith("dft_scan_mux_")) == 2
    assert "scan_en" in mod.ports and mod.ranges["scan_in"] == (2, 0)


def test_mix_orders_negative_edge_first_and_adds_lockup(cells):
    text, rep = _insert(cells, chains=1, clock_mixing="mix")
    assert rep["chain_count"] == 1
    order = [c["instance"] for c in rep["chains"][0]["cells"]]
    assert order[0] == "r3"                      # negative edge first
    assert set(order[1:4]) == {"r0", "r1", "r2"}  # then clk positive edge
    assert set(order[4:]) == {"r4", "r5"}         # then clk2
    # neg->pos on one clock needs no latch; clk->clk2 needs one
    latches = rep["chains"][0]["lockup_latches"]
    assert len(latches) == 1 and latches[0]["clock"] == "clk"
    assert latches[0]["cell"] == "DLLx1_ASAP7_75t_R"   # transparent while clk is low
    assert "DLLx1_ASAP7_75t_R dft_lockup_latch_0" in text


def test_chain_count_and_length(cells):
    _, rep = _insert(cells, chains=1, max_length=1, clock_mixing="mix")
    assert rep["chain_count"] == 6 and rep["chain_length_max"] == 1
    _, rep = _insert(cells, chains=2, clock_mixing="mix")
    assert sorted(c["length"] for c in rep["chains"]) == [3, 3]


def test_refuses_double_insertion(cells):
    text, _ = _insert(cells, chains=1)
    mod = nl.parse_netlist(text)[0]
    with pytest.raises(scan_insert.DftError):
        scan_insert.insert_scan(mod, cells, chains=1)


@pytest.mark.skipif(not (shutil.which("iverilog") and shutil.which("g++")), reason="needs iverilog and g++")
@pytest.mark.parametrize("mixing", ["no_mix", "mix"])
def test_atpg_end_to_end_on_the_gates(tmp_path, cells, mixing):
    from dft import run_atpg

    text, rep = _insert(cells, chains=2, clock_mixing=mixing)
    (tmp_path / "scan.v").write_text(text)
    (tmp_path / "scan.json").write_text(json.dumps(rep))
    out = tmp_path / "atpg.json"
    rc = run_atpg.main([
        "--netlist", str(tmp_path / "scan.v"), "--scan", str(tmp_path / "scan.json"),
        "--work", str(tmp_path / "w"), "--output", str(out), "--threads", "2",
        "--sample-patterns", "64", "--sample-faults", "40", "--sample-chain-faults", "12",
        "--simulator", "icarus" if mixing == "mix" else "verilator",   # both simulators exercised
        *([] if mixing == "mix" else ["--lean-build"]),   # the low-memory Verilator build too
    ])
    assert rc == 0
    res = json.loads(out.read_text())
    assert res["classes"]["AU"] == 0
    assert res["engine"]["capture"]["untestable_but_detected"] == 0
    assert res["engine"]["capture"]["podem_unconfirmed"] == 0
    assert res["test_coverage"] == 1.0
    assert res["fault_coverage"] > 0.8   # the toy is small: tie cell and reset-constrained pins are a large share
    gl = res["gate_level"]
    assert gl["good_machine_mismatches"] == 0
    assert gl["capture_faults_confirmed"] == gl["capture_faults_injected"] > 0
    assert gl["chain_faults_confirmed"] == gl["chain_faults_injected"] > 0


YOSYS = Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"


@pytest.mark.skipif(not YOSYS.is_file(), reason="needs the pinned Yosys")
@pytest.mark.parametrize("mixing", ["no_mix", "mix"])
def test_scan_off_is_formally_equivalent(tmp_path, cells, mixing):
    from dft import check_scan_equivalence as eq

    text, rep = _insert(cells, chains=2, clock_mixing=mixing)
    (tmp_path / "pre.v").write_text(TOY)
    (tmp_path / "scan.v").write_text(text)
    res = eq.check(tmp_path / "pre.v", tmp_path / "scan.v", rep, tmp_path / "ok", cells, YOSYS)
    assert res["proven"] and res["unproven_cells"] == 0
    assert res["equiv_cells"] >= 6 + 3   # every flop state and every output
    # negative control: a changed gate must not prove
    (tmp_path / "bad.v").write_text(text.replace("NAND2xp5_ASAP7_75t_R g0", "NOR2xp33_ASAP7_75t_R g0"))
    res = eq.check(tmp_path / "pre.v", tmp_path / "bad.v", rep, tmp_path / "bad", cells, YOSYS)
    assert not res["proven"]


def test_mixed_edge_capture_is_refused(tmp_path, cells):
    """A falling-edge cell fed by a rising-edge cell of the same clock sees the new
    value within one capture pulse; the single-frame model must refuse it."""
    from dft import atpg_model

    toy = """
module mixed(clk, a, y);
  input clk; input a; output y;
  wire q0n, q1n;
  DFFHQNx1_ASAP7_75t_R p0 (.CLK(clk), .D(a), .QN(q0n));
  DFFLQNx1_ASAP7_75t_R n0 (.CLK(clk), .D(q0n), .QN(q1n));
  INVx1_ASAP7_75t_R g (.A(q1n), .Y(y));
endmodule
"""
    text, rep = scan_insert.insert_scan(nl.parse_netlist(toy)[0], cells, chains=1)
    (tmp_path / "scan.v").write_text(text)
    with pytest.raises(scan_insert.DftError, match="falling-edge"):
        atpg_model.build_models(tmp_path / "scan.v", rep, cells, tmp_path / "m")
