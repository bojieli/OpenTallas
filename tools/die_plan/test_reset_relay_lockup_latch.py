"""RLK-1108 (DIE-HBM-92-RLK 11-08): opt-in reset.relay_lockup {"form": "latch"}, the hop LOCKUP LATCH reset form.

Invariants: absent / negedge trees emit no hop latch (byte-identical RTL and placement); in the latch form every relay
stays a plain posedge ot_dp_rrelay and exactly the internal relay -> relay hops (launch q = rst_rl_*) get one ot_dp_lk
u_fl_rst<k> in front of the capture relay's d, placed at the planned hop midpoint; the release cycle is unchanged.
The lock-step bench runs the latch tree with a launch/capture clock skew of 0.3 T on every other depth (the cross-tap
hold race of the HBM transit types) against the plain zero-skew tree, and catches the mutants latch -> flop, missing
latch, wrong latch phase and latch clocked from the capture tap."""
import re
import shutil
import subprocess
import types

import pytest

import bind
import gen_rtl
import kit_rsync as K
import reset_consumers as RC
import reset_tree as R


def tree(form):
    t = R.build([("a", 100, 0), ("b", 900, 0), ("c", 900, 800), ("out", 1300, 0)], (0, 0), depth=6)
    t.update(taps=["a", "b", "c", "out"], n_clock_taps=3, outs=[[1300, 0]], entry="relayed", sync_stages=2)
    if form:
        t["relay_lockup"] = form
    return t


def plan(reset, tns=("ta", "tb")):
    return types.SimpleNamespace(reset=reset, types={t: {} for t in tns})


def test_absent_and_negedge_emit_no_hop_latch():
    for form in (None, "negedge"):
        t = tree(form)
        assert R.lockup_hops(t) == []
        rtl = "\n".join(R.rtl_lines(t))
        tcl = R.tcl_text(t)
        assert "ot_dp_lk" not in rtl and "u_fl_rst" not in rtl and "rtr_place_lk" not in tcl
    # the negedge form keeps its ot_dp_rrelay_nl cells and LOCKUP_CELLS (CLK form #7 unchanged)
    assert "ot_dp_rrelay_nl" in "\n".join(R.rtl_lines(tree("negedge")))
    assert gen_rtl.uses_relay_lockup({"reset": {"relay_lockup": {"form": "negedge", "types": []}}}, "negedge")
    assert not gen_rtl.uses_relay_lockup({"reset": {"relay_lockup": {"form": "latch", "types": []}}}, "negedge")
    assert not gen_rtl.uses_relay_lockup({"reset": {}})


def test_latch_form_scope_and_cells():
    t = tree("latch")
    by_q = {r["q"]: r for r in t["relays"]}
    hops = R.lockup_hops(t)
    internal = {r["q"] for r in t["relays"] if not r["q"].startswith("rst_n_t")}
    assert hops and {r["name"] for r in hops} == {r["name"] for r in t["relays"] if r["d"] in internal}
    assert all(r["d"] != "rst_root_n" for r in hops)          # first hop after the entry pin register stays plain
    assert all(R.relay_cell(t, r) == "ot_dp_rrelay" for r in t["relays"])   # every relay stays one posedge flop
    rtl = "\n".join(R.rtl_lines(t))
    assert "ot_dp_rrelay_nl" not in rtl and "ot_dp_rrelay u_rst_in " in rtl
    assert rtl.count("ot_dp_lk #(.W(1)) u_fl_rst_") == len(hops)
    for r in hops:
        li, lq = R.lockup_latch_names(r["name"])
        assert f"ot_dp_lk #(.W(1)) {li} (.clk(clk), .d({r['d']}), .q({lq}));" in rtl
        assert re.search(rf"ot_dp_rrelay {r['name']}(?:_t)? \(\.clk\(clk\), \.d\({lq}\), ", rtl)
        assert by_q[r["d"]]["name"] != r["name"]
    # the out relay and its tap-net copy share one latch (same d, same site)
    assert re.search(r"ot_dp_rrelay u_rrl_\d+ \(\.clk\(clk\), \.d\(rst_lk_\d+\), \.q\(rst_o_0\)\)", rtl)
    # names never collide with the relay placement patterns / clock_taps follower regex
    for r in t["relays"]:
        li, _ = R.lockup_latch_names(r["name"])
        assert li.startswith("u_fl_") and "u_rrl_" not in li
        assert not re.search(r"(?:^|[/.])(u_rrl_[0-9]+)[/.]", li + "/x")


def test_latch_placement_at_hop_midpoint():
    t = tree("latch")
    xy = {r["q"]: r["xy"] for r in t["relays"]}
    tcl = R.tcl_text(t)
    assert "proc rtr_place_lk" in tcl and 'string match "DLLx*"' in tcl
    for r in R.lockup_hops(t):
        li, lq = R.lockup_latch_names(r["name"])
        mx, my = (xy[r["d"]][0] + r["xy"][0]) / 2, (xy[r["d"]][1] + r["xy"][1]) / 2
        assert f"rtr_place_lk {lq} {{*{li}[./]*}} {mx:.3f} {my:.3f} " in tcl
    # the planned relay sites and the hop check are those of the plain tree
    plain = R.tcl_text(tree(None))
    strip = "".join(ln for ln in tcl.splitlines(keepends=True) if not ln.startswith("rtr_place_lk "))
    strip = strip.replace(R.LOCKUP_PLACE_TCL + "\n", "")
    assert strip == plain
    with pytest.raises(R.ResetError):
        R.tcl_text(t, native_paths={}, native_nodes=[])


def test_latch_placement_on_native_contract():
    """bind kit-rtl (native reset export): the verified latch hierarchy and the native relay sites drive placement."""
    t = tree("latch")
    nodes = [dict(r, xy=[r["xy"][0] + 1.0, r["xy"][1]]) for r in t["relays"]]
    paths = {r["name"]: "u_bound." + r["name"] for r in t["relays"]}
    paths.update({"u_rst_in": "u_bound.u_rst_in"})
    with pytest.raises(R.ResetError):            # a hop latch without a verified hierarchy is refused
        R.tcl_text(t, native_paths=dict(paths), native_nodes=nodes)
    paths.update({R.lockup_latch_names(r["name"])[0]: "u_bound." + R.lockup_latch_names(r["name"])[0]
                  for r in R.lockup_hops(t)})
    tcl = R.tcl_text(t, native_paths=paths, native_nodes=nodes)
    by_q = {r["q"]: r for r in nodes}
    for r in R.lockup_hops(t):
        li, lq = R.lockup_latch_names(r["name"])
        a, b = by_q[r["d"]]["xy"], r["xy"][0] + 1.0
        assert f"rtr_place_lk {lq} {{u_bound[./]{li}[./]*}} {(a[0] + b) / 2:.3f} {(a[1] + r['xy'][1]) / 2:.3f} " in tcl
    assert "{*u_fl_rst" not in tcl


def test_plan_option_accepts_latch(monkeypatch):
    monkeypatch.setattr(R, "start_broadcast", lambda P: bool(P.reset.get("start")))
    ok = {"relay_lockup": {"form": "latch", "types": ["ta"]}}
    assert R.relay_lockup(plan(ok), "ta") is True and R.relay_lockup(plan(ok), "tb") is False
    assert R.relay_lockup_form(plan(ok)) == "latch" and R.relay_lockup_form(plan({})) is None
    for bad in ({"relay_lockup": {"form": "pulse", "types": ["ta"]}}, dict(ok, relay_driver=True), dict(ok, start=True)):
        with pytest.raises(R.ResetError):
            R.relay_lockup(plan(bad), "ta")


def test_schema_enum():
    import json
    import schema as S
    from pathlib import Path
    assert S.SCHEMA["properties"]["reset"]["properties"]["relay_lockup"]["properties"]["form"]["enum"] == ["negedge", "latch"]
    j = json.loads(Path(S.__file__).with_name("die_plan.schema.json").read_text())
    assert j["properties"]["reset"]["properties"]["relay_lockup"]["properties"]["form"]["enum"] == ["negedge", "latch"]


def test_kit_and_bind_cells():
    text = K.cells_text(lockup="latch")
    assert "module ot_dp_lk " in text and "ot_dp_rrelay_nl" not in text
    assert "ot_dp_rrelay_nl" in K.cells_text(lockup="negedge") and "ot_dp_rrelay_nl" in K.cells_text(lockup=True)
    assert "module ot_dp_lk " not in K.cells_text(lockup="negedge")
    assert "module ot_dp_lk " in bind.wavefront_cells_text(lockup="latch")
    assert "ot_dp_rrelay_nl" not in bind.wavefront_cells_text(lockup="latch")
    # a re-run of kit_rsync recognises (and re-plans) every latch-form line
    for ln in R.rtl_lines(tree("latch")):
        if "u_fl_rst" in ln or "rst_lk_" in ln.split("//")[0]:
            if ln.strip().startswith(("ot_dp_lk", "wire rst_lk")):
                assert K.TREE.match(ln), ln


def test_reset_consumers_lineage_through_latch():
    def localize(t, rtl=None):
        text = "module m(input wire clk, input wire arst_n);\n" + (rtl or "\n".join(R.rtl_lines(t))) + \
            "\n    ot_dp_st #(.W(1)) u_x (.clk(clk), .rst_n(rst_n_t0), .d(1'b0), .ea(1'b0), .q(), .eq());\nendmodule\n"
        decl = [dict(instance="u_x", pin="rst_n", old_reset="rst_n_t0", new_reset="rst_n_t2", clock_net="clk")]
        return RC.localize(text, decl, t)
    for form in (None, "latch"):
        new, rec = localize(tree(form))
        assert ".rst_n(rst_n_t2)" in new and rec[0]["depth"] == 6 and rec[0]["cycles_added"] == 0
    # a latch on another clock is not a 0-cycle wire of this reset domain
    t = tree("latch")
    bad = "\n".join(R.rtl_lines(t)).replace("u_fl_rst_23 (.clk(clk)", "u_fl_rst_23 (.clk(clk2)")
    with pytest.raises(RC.ResetConsumerError):
        localize(t, bad)


SKEW_NS, T_NS = 3, 10


def bench_module(name, t, lk_clock="launch", skew=SKEW_NS):
    """the tree as a module: depth-even relays (u_rst_in = depth 0) on clk delayed by 0.3 T (cross-tap skew), each latch on its launch
    relay's clock (clock_taps.tcl follow-D) or, for the mutant, the capture relay's."""
    by_q = {r["q"]: r for r in t["relays"]}
    by_n = {r["name"]: r for r in t["relays"]}
    lk_of = {R.lockup_latch_names(r["name"])[0]: r for r in R.lockup_hops(t)}

    def ck(depth):               # the entry pin register u_rst_in is depth 0 (its hop to depth 1 stays plain)
        return "clk" if depth % 2 else "ck_d"
    out = [f"module {name} (input wire clk, input wire arst_n, output wire [3:0] taps, output wire rst_o_0);",
           f"    wire ck_d; assign #{skew} ck_d = clk;" if skew else "    wire ck_d = clk;  // reference: no skew"]
    for ln in R.rtl_lines(t):
        if "u_rst_in (.clk(clk)" in ln:
            ln = ln.replace(".clk(clk)", f".clk({ck(0)})", 1)
        m = re.search(r"\b(u_rrl_\d+)(_t)? \(\.clk\(clk\)", ln)
        if m:
            ln = ln.replace(".clk(clk)", f".clk({ck(by_n[m.group(1)]['depth'])})", 1)
        m = re.search(r"\b(u_fl_rst_\d+) \(\.clk\(clk\)", ln)
        if m:
            cap = lk_of[m.group(1)]
            src = by_q[cap["d"]] if lk_clock == "launch" else cap
            ln = ln.replace(".clk(clk)", f".clk({ck(src['depth'])})", 1)
        out.append(ln)
    out += ["    assign taps = {rst_n_t3, rst_n_t2, rst_n_t1, rst_n_t0};", "endmodule"]
    return "\n".join(out) + "\n"


TB = f'''`timescale 1ns/1ps
module tb;
  reg clk = 0; always #{T_NS // 2} clk = ~clk;
  reg arst_n = 0; wire [3:0] tr, td; wire orf, od;
  ref_tree r (.clk(clk), .arst_n(arst_n), .taps(tr), .rst_o_0(orf));
  dut_tree d (.clk(clk), .arst_n(arst_n), .taps(td), .rst_o_0(od));
  integer i, bad, seen; reg [3:0] prev;
  initial begin
    bad = 0; seen = 0; prev = 4'b0000;
    for (i = 0; i < 200; i = i + 1) begin
      @(negedge clk); arst_n = (i < 12) ? (i > 3) : $random;
      @(posedge clk); #{T_NS - 2};
      if (i > 10) begin
        if (tr !== td || orf !== od) bad = bad + 1;
        if (tr !== prev) seen = seen + 1;
        prev = tr;
      end
    end
    $display("BAD=%0d SEEN=%0d", bad, seen);
    $finish;
  end
endmodule
'''


def cell(name, src=gen_rtl.CELLS):
    return re.search(r"\(\* keep_hierarchy, keep \*\)\nmodule " + name + r"\b.*?endmodule\n", src, re.S).group(0)


LK = cell("ot_dp_lk")
MUTANTS = {
    "latch_to_flop": LK.replace("always @(*) if (!clk) q = d;", "always @(posedge clk) q <= d;"),
    "missing_latch": LK.replace("always @(*) if (!clk) q = d;", "always @(*) q = d;"),
    "wrong_phase": LK.replace("always @(*) if (!clk) q = d;", "always @(*) if (clk) q = d;"),
}


def run_bench(tmp_path, lk_text, lk_clock="launch", dut_form="latch"):
    """number of sampled cycles where the DUT tree's taps / reset out differ from the zero-skew plain reference."""
    global _N
    _N += 1
    src = tmp_path / f"tb{_N}.v"
    src.write_text("`timescale 1ns/1ps\n" + cell("ot_dp_rrelay") + lk_text + bench_module("ref_tree", tree(None), skew=0) +
                   bench_module("dut_tree", tree(dut_form), lk_clock) + TB)
    exe = tmp_path / f"tb{_N}.out"
    subprocess.run(["iverilog", "-o", str(exe), str(src)], check=True)
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True, check=True).stdout
    m = re.search(r"BAD=(\d+) SEEN=(\d+)", out)
    assert m and int(m.group(2)) > 20, out       # the stimulus really toggles the taps
    return int(m.group(1))


_N = 0


@pytest.mark.skipif(not shutil.which("iverilog"), reason="iverilog not installed")
def test_lockstep_bench_latch_form_and_mutants(tmp_path):
    # the latch form under a 0.3 T launch -> capture skew releases on exactly the zero-skew plain tree's cycles
    assert run_bench(tmp_path, LK) == 0
    # positive control: the plain tree under the same skew fails (the cross-tap hold race is real in the bench)
    assert run_bench(tmp_path, LK, dut_form=None) > 0
    for name, text in MUTANTS.items():
        assert run_bench(tmp_path, text) > 0, name
    # latch clocked from the CAPTURE relay's tap (no follow-D) does not close the race
    assert run_bench(tmp_path, LK, lk_clock="capture") > 0
