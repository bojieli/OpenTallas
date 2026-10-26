"""START bootstrap / mission roles (reset fix 2026-10-25, KV/QC START bootstrap deadlock).

A START-broadcast plan gates every consumer tap by START (decision 13c).  A block that must boot BEFORE the one global
START (KV host program load, PC cold boot, PHY calibration) then deadlocks: START waits for its boot, its boot waits for
START.  reset.start_role "bootstrap" gives such a type the registered RAW delivered wavefront reset (same depth, same
published release) plus ONE local registered START tap start_t<leaf> (reset AND run) for its declared mission-admission
input.  Mission types are unchanged.

Lockstep on the generated tiny die: the bench raises the die start pin only after it observes the bootstrap block's
boot witness (the host's rule: START after native boot), so
  - good: boot completes at release[pa] + BOOT, START follows, mission admission at S + release[pa], every mission tap
    at S + release[p];
  - mutant A (the bootstrap block declared mission): boot never completes before START -> deadlock detected;
  - mutant B (a mission type declared bootstrap): its taps release before START -> caught;
  - mutant C (admission bound to the raw reset, not the START tap): admission before START -> caught.
"""
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_rtl  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
BOOT = 5

LEAVES = (HERE / "examples" / "tiny_leaves.sv").read_text().replace(
    """module tiny_src_core (input wire clk, input wire rst_n, input wire [31:0] din, input wire [15:0] r,
                      output reg [63:0] x, output reg [7:0] cfg);""",
    f"""module tiny_src_core (input wire clk, input wire rst_n, input wire mission_start, input wire [31:0] din,
                      input wire [15:0] r, output reg [63:0] x, output reg [7:0] cfg);
    // bootstrap witness: a {BOOT}-cycle boot sequence under the delivered reset, then mission admission on START
    reg [3:0] boot_cnt;
    reg boot_done, admitted;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin boot_cnt <= 4'd0; boot_done <= 1'b0; admitted <= 1'b0; end
        else begin
            if (!boot_done) begin boot_cnt <= boot_cnt + 4'd1; boot_done <= (boot_cnt == 4'd{BOOT - 1}); end
            if (boot_done && mission_start) admitted <= 1'b1;
        end""")


def plan(src_role="bootstrap", sink_role=None, admit="start"):
    raw = copy.deepcopy(TINY)
    raw["reset"].update(release="wavefront", start="broadcast")
    for ty in raw["partition_types"].values():
        ty.pop("sources", None)
    src = raw["partition_types"]["src"]
    src["reset"]["start_role"] = src_role
    src["contents"][0]["bind"]["mission_start"] = admit
    if sink_role:
        raw["partition_types"]["sink"]["reset"]["start_role"] = sink_role
    assert schema.validate(raw) == []
    return raw


def test_roles_published_and_emitted():
    raw = plan()
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    assert W["start"]["bootstrap_types"] == ["src"]
    assert W["types"]["src"]["start_role"] == "bootstrap" and W["types"]["mid"]["start_role"] == "mission"
    T = RT.for_type(P, "src")
    rel = RT.start_relays(T)
    roles = {r["q"]: r["role"] for r in rel}
    nck = T["n_clock_taps"]
    assert all(roles[f"rst_n_t{i}"] == "boot" for i in range(nck))
    assert roles[f"start_t{T['start_tap']}"] == "gated"
    # same flop count to every consumer tap: the bootstrap release offset is the published one
    body = "\n".join(RT.rtl_lines(T))
    assert f"ot_dp_rgate u_rrl_" in body and f".q(start_t{T['start_tap']})" in body
    Tm = RT.for_type(P, "mid")
    assert all(r["role"] in ("gated", "raw", "run") for r in RT.start_relays(Tm)) and Tm["start_tap"] is None


def test_role_needs_broadcast_and_known_cores():
    raw = plan()
    raw["reset"]["start"] = "none"
    with pytest.raises(RT.ResetError, match="start = broadcast"):
        RT.for_type(schema.Plan(raw), "src")
    raw = plan()
    raw["partition_types"]["src"]["reset"]["core_start_roles"] = {"u_nope": "mission"}
    with pytest.raises(RT.ResetError, match="core_start_roles"):
        RT.for_type(schema.Plan(raw), "src")


def test_mission_type_has_no_start_signal():
    raw = plan()
    raw["partition_types"]["sink"]["contents"][0]["bind"]["x_ep"] = "start"
    with tempfile.TemporaryDirectory() as d, pytest.raises(gen_rtl.GenError, match="not a signal"):
        gen_rtl.write_rtl(copy.deepcopy(raw), d)


def simulate(raw, S_GAP=2, tmo=200, ref=None):
    """ref: the plan whose roles define the expected tap releases (default raw).  Returns dict(boot=cycle, start=cycle, admit=cycle, bad=mismatching tap checks) (-1 = never)."""
    if not shutil.which("iverilog"):
        pytest.skip("iverilog missing")
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    PR = schema.Plan(ref or raw)
    checks = []
    for part, p in P.parts.items():
        T = RT.for_type(PR, p["type"])
        rel = W["parts"][part]["release"]
        boot = T.get("start_role") == "bootstrap"
        for i in range(T["n_clock_taps"]):
            n = f"u_top.{gen_rtl.sv_id(part)}.rst_n_t{i}"
            want = f"(cyc + 1 >= {rel})" if boot else f"(S >= 0 && cyc + 1 >= S + {rel})"
            checks.append(f"if ({n} !== {want}) bad = bad + 1;")
    with tempfile.TemporaryDirectory() as d:
        files = [str(f) for f in gen_rtl.write_rtl(copy.deepcopy(raw), d)]
        lv = Path(d) / "leaves.sv"
        lv.write_text(LEAVES)
        tb = Path(d) / "tb.sv"
        tb.write_text(f"""`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0, start = 0;
    always #0.5 clk = ~clk;
    reg [31:0] din = 0;
    wire [31:0] dout;
    tiny_top u_top (.clk(clk), .rst_n(rst_n), .start(start), .din(din), .dout(dout));
    integer cyc = -20, S = -1, boot = -1, admit = -1, bad = 0, ask = 1000000;
    always @(posedge clk) begin
        #0.1;
        if (cyc >= 0) begin
            {' '.join(checks)}
        end
        if (u_top.pa.u_core.boot_done === 1'b1 && boot < 0) begin boot = cyc + 1; ask = cyc + {S_GAP}; end
        if (u_top.pa.u_core.admitted === 1'b1 && admit < 0) admit = cyc + 1;
        if (cyc == -1) rst_n = 1;
        if (cyc == ask) begin start = 1; S = cyc + 1; end   // the host raises START only after native boot
        cyc = cyc + 1;
    end
    initial begin
        repeat ({tmo}) @(posedge clk);
        $display("RES boot=%0d start=%0d admit=%0d bad=%0d", boot, S, admit, bad);
        $finish;
    end
endmodule
""")
        exe = str(Path(d) / "a.out")
        subprocess.run(["iverilog", "-g2012", "-o", exe, str(tb), str(lv)] + files, check=True)
        out = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True).stdout
        m = re.search(r"RES boot=(-?\d+) start=(-?\d+) admit=(-?\d+) bad=(\d+)", out)
        assert m, out[-1500:]
        res = dict(zip(("boot", "start", "admit", "bad"), map(int, m.groups())))
        res["release_pa"] = W["parts"]["pa"]["release"]
        return res


def test_bootstrap_boots_before_start_and_admits_on_start():
    r = simulate(plan())
    assert r["boot"] == r["release_pa"] + BOOT, r          # boot under the raw delivered wavefront reset
    assert r["start"] > r["boot"]
    # START tap releases at S + release[pa]; the admission flop samples it one clock later
    assert r["admit"] == r["start"] + r["release_pa"] + 1, r
    assert r["bad"] == 0, r                                 # every mission tap at S + release, bootstrap at release


def test_mutant_bootstrap_declared_mission_deadlocks():
    r = simulate(plan(src_role="mission", admit="rst_n"), ref=plan())
    assert r["boot"] == -1 and r["start"] == -1 and r["admit"] == -1, r


def test_mutant_mission_type_without_start_gate_caught():
    r = simulate(plan(sink_role="bootstrap"), ref=plan())
    assert r["bad"] > 0, r


def test_mutant_admission_on_raw_reset_caught():
    r = simulate(plan(admit="rst_n"))
    assert r["admit"] >= 0 and (r["start"] < 0 or r["admit"] <= r["start"]), r
