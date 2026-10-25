"""Canary regression verdict vs recorded baseline (COORD CANARY GATING RULING 2026-10-25 14:38).
    python3 -m pytest -q tools/flow_canary/test_baseline.py"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "autopilot"), str(HERE.parent / "die_plan")]
import baseline as B  # noqa: E402
import canary as C  # noqa: E402
import canary_gate as G  # noqa: E402

GRT_LOG = """[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Congestion
Total        263418652       1541603            0.59%             {h} /  {v} /  {t}
"""


def mkrun(root, name, die="s81", item="t12", src="abc123456789", verdict="FAIL", ins=(226.5, 183.4), bound=(250.0, 202.5),
          hold=(-76.7, 691, "PASS"), ovf=0, drv=(0, 0), signoff=None, postcts_fail=False, stages=None, mtime=None):
    run = Path(root) / name
    kit = run / "gen" / item
    (kit / "run/logs/asap7/d/base").mkdir(parents=True)
    (run / "canary_meta.json").write_text(json.dumps({"spec": {"die": die, "item": item}, "src_commit": src,
                                                      "kit": str(kit)}))
    st = {k: {"verdict": "PASS"} for k in B.FLOW_STAGES}
    st.update({k: {"verdict": v} for k, v in (stages or {}).items()})
    (run / "canary.json").write_text(json.dumps({"verdict": verdict, "src": src, "die": die, "item": item, "stages": st}))
    if ins:
        for c, m, b in (("tt", ins[0], bound[0]), ("ff", ins[1], bound[1])):
            (kit / f"postcts_gate_{c}.json").write_text(json.dumps({"pinreg_mean_ps": m, "bound_ps": b}))
    if hold:
        (kit / "hold_gate.log").write_text(f"OT_HOLD_GATE {hold[2]} FF wns_ps {hold[0]} endpoints {hold[1]} (true negative slack)\n")
    if ovf is not None:
        (kit / "run/logs/asap7/d/base/5_1_grt.log").write_text(GRT_LOG.format(h=0, v=0, t=ovf))
        (kit / "run/logs/asap7/d/base/5_1_grt.json").write_text(json.dumps(
            {"globalroute__timing__drv__max_slew": drv[0], "globalroute__timing__drv__max_cap": drv[1]}))
    if postcts_fail:
        (kit / "FAIL_POSTCTS").write_text("FAIL_POSTCTS pre-route insertion gate: OT_POSTCTS_GATE TT ... FAIL\n")
    if signoff:
        (kit / "signoff").mkdir()
        (kit / "signoff/signoff.json").write_text(json.dumps(signoff))
    if mtime:
        os.utime(run / "canary_meta.json", ns=(mtime, mtime))
    return run


def so(tt, ff, ep, slew=0):
    return {"checks": {"setup_tt": {"wns_ps": tt}, "hold_ff": {"wns_ps": ff, "violators": ep},
                       "drv": {"by_corner": {"tt": {"slew": slew, "cap": 0}, "ff": {"slew": 0, "cap": 0}}}}}


def test_first_run_sets_baseline_info_then_regression_by_tolerance(tmp_path):
    r0 = mkrun(tmp_path, "r0")
    v = B.verdict(r0, tmp_path)
    assert v["verdict"] == "INFO" and v["baseline"]["source"]["kind"] == "canary-run-info"
    rec = B.load(tmp_path, "s81", "t12")
    assert rec["contexts"]["grt"]["ins_tt"] == 226.5 and rec["contexts"]["grt"]["overflow"] == 0
    assert rec["contexts"]["grt"]["hold_ff_ep"] == 691 and rec["contexts"]["grt"]["from"]["run"] == str(r0)
    assert B.verdict(r0, tmp_path)["verdict"] == "INFO"                               # the baseline run itself
    # absolute FAIL of the reference (insertion 226 vs 250) is not a regression
    assert B.verdict(mkrun(tmp_path, "same", ins=(229.0, 181.0)), tmp_path)["verdict"] == "NO-REGRESSION"
    # insertion 6 ps further from the bound -> REGRESSION; 20 ps closer -> fine (a fix must never be held)
    assert B.verdict(mkrun(tmp_path, "ins_bad", ins=(220.4, 183.4)), tmp_path)["verdict"] == "REGRESSION"
    assert B.verdict(mkrun(tmp_path, "ins_fix", ins=(246.5, 199.0)), tmp_path)["verdict"] == "NO-REGRESSION"
    # hold endpoints +5 % tolerance, WNS 10 ps
    assert B.verdict(mkrun(tmp_path, "ep_ok", hold=(-80.0, 725, "PASS")), tmp_path)["verdict"] == "NO-REGRESSION"
    assert B.verdict(mkrun(tmp_path, "ep_bad", hold=(-76.7, 726, "PASS")), tmp_path)["verdict"] == "REGRESSION"
    assert B.verdict(mkrun(tmp_path, "wns_bad", hold=(-87.0, 600, "PASS")), tmp_path)["verdict"] == "REGRESSION"
    # overflow / DRV: 0 new
    assert B.verdict(mkrun(tmp_path, "ovf", ovf=1), tmp_path)["verdict"] == "REGRESSION"
    assert B.verdict(mkrun(tmp_path, "drv", drv=(1, 0)), tmp_path)["verdict"] == "REGRESSION"


def test_store_is_write_once(tmp_path):
    B.verdict(mkrun(tmp_path, "a"), tmp_path)
    b = mkrun(tmp_path, "b", ins=(200.0, 150.0))
    wrote, rec = B.write(tmp_path, B.make_record(B.run_metrics(b), "canary-run-info"))
    assert not wrote and rec["source"]["run"].endswith("/a")
    assert B.main(["set", "--root", str(tmp_path), "--run", str(b), "--kind", "canary-passed-main"]) == 1
    assert B.main(["set", "--root", str(tmp_path), "--run", str(b), "--kind", "canary-passed-main", "--force"]) == 0
    assert B.load(tmp_path, "s81", "t12")["source"] == {"kind": "canary-passed-main", "run": str(b), "src": "abc123456789",
                                                       "note": ""}


def test_design_stop_at_insertion_gate_vs_reference_run_signoff(tmp_path):
    """s81 t12 shape: baseline sign-off context from the golden reference run, GRT context from a main canary run;
    main stops at the post-CTS insertion gate -> sign-off NOT REACHED (design stop), gate metrics within tolerance."""
    ref = tmp_path / "golden_signoff.json"
    ref.write_text(json.dumps(so(18.24, 8.62, 0)))
    r0 = mkrun(tmp_path, "r0", postcts_fail=True)
    assert B.main(["set", "--root", str(tmp_path), "--run", str(r0), "--kind", "canary-run-info",
                   "--signoff-ref", str(ref)]) == 0
    rec = B.load(tmp_path, "s81", "t12")
    assert rec["contexts"]["signoff"]["from"]["kind"] == "reference-run" and rec["contexts"]["signoff"]["setup_tt_wns"] == 18.24
    v = B.verdict(mkrun(tmp_path, "r1", ins=(227.0, 183.0), postcts_fail=True), tmp_path)
    assert v["verdict"] == "NO-REGRESSION", v
    assert {r["metric"] for r in v["rows"] if r["verdict"] == "NOT REACHED"} == {"setup_tt_wns", "hold_ff_wns",
                                                                                 "hold_ff_ep", "drv"}
    assert any("design stop" in n for n in v["notes"])
    # the same stop with a gate metric out of tolerance is a REGRESSION
    assert B.verdict(mkrun(tmp_path, "r2", ins=(215.0, 183.0), postcts_fail=True), tmp_path)["verdict"] == "REGRESSION"


def test_kv_core_setup_collapse_is_regression(tmp_path):
    """KV core canary c0e2df27a: TT -222.85 vs reference run +36.61 (async reset recovery) stays REGRESSION."""
    ref = tmp_path / "golden.json"
    ref.write_text(json.dumps(so(36.61, -5.92, 378)))
    r0 = mkrun(tmp_path, "kv0", die="qwen_kvsys_core", item="e1", ins=None, hold=None, signoff=so(-222.85, -5.42, 6, 14))
    assert B.main(["set", "--root", str(tmp_path), "--run", str(r0), "--kind", "canary-run-info", "--signoff-ref",
                   str(ref)]) == 0
    v = B.verdict(r0, tmp_path)
    assert v["verdict"] == "REGRESSION"               # its own baseline run, but the sign-off context is the ref run
    # auto-seed (no baseline) also prefers the golden reference run's sign-off over the regressed run's own
    auto = tmp_path / "auto"
    auto.mkdir()
    assert B.verdict(r0, auto, spec={"golden": {"source": "x", "setup_tt_wns": 36.61}})["verdict"] == "REGRESSION"
    assert B.load(auto, "qwen_kvsys_core", "e1")["contexts"]["signoff"]["from"]["kind"] == "reference-run"
    kv = mkrun(tmp_path, "kv1", die="qwen_kvsys_core", item="e1", ins=None, hold=None, signoff=so(-222.85, -5.42, 6, 14))
    v = B.verdict(kv, tmp_path)
    assert v["verdict"] == "REGRESSION" and "setup_tt_wns" in v["why"] and "drv" in v["why"]


def test_crash_cannot_seed_and_lost_reach_or_stage_is_regression(tmp_path):
    crash = mkrun(tmp_path, "crash", stages={"tcl_errors": "FAIL"})
    assert B.verdict(crash, tmp_path)["verdict"] == "NO-BASELINE" and B.load(tmp_path, "s81", "t12") is None
    B.verdict(mkrun(tmp_path, "good"), tmp_path)
    # flow stopped before GRT (no metric, no design stop) where the baseline measured -> REGRESSION
    v = B.verdict(mkrun(tmp_path, "early", ins=None, hold=None, ovf=None), tmp_path)
    assert v["verdict"] == "REGRESSION"
    # a flow-correctness stage that PASSed in the baseline run now FAILs -> REGRESSION
    v = B.verdict(mkrun(tmp_path, "lec", stages={"lec": "FAIL"}), tmp_path)
    assert v["verdict"] == "REGRESSION" and "lec" in v["why"]
    # design stages are judged by metrics only: grt_gate FAIL with metrics in tolerance is no regression
    assert B.verdict(mkrun(tmp_path, "gate", stages={"grt_gate": "FAIL", "vclk_basis": "FAIL"}), tmp_path)["verdict"] == \
        "NO-REGRESSION"


def test_autopilot_gate_releases_on_no_regression_and_holds_regression(tmp_path):
    repo = tmp_path / "repo"
    (repo / "tools/flow_canary").mkdir(parents=True)
    (repo / "tools/flow_canary/canaries.json").write_text(json.dumps(
        {"watch": ["tools/die_plan/*"], "canaries": [{"die": "s81", "item": "t12"}]}))
    (repo / "tools/flow_canary/baseline.py").write_text((HERE / "baseline.py").read_text())
    root = tmp_path / "runs"
    root.mkdir()
    row = {"die": "s81", "mode": "submit", "src": "x@abc123456789"}
    git = lambda *a, **kw: (0, "", "")  # noqa: E731
    mkrun(root, "r0", mtime=10**9 + 1)
    ok, why = G.assess(row, root, repo, git)
    assert ok and "INFO" in why                            # the first run sets the baseline, non-gating
    mkrun(root, "r1", ins=(228.0, 182.0), mtime=10**9 + 2)
    ok, why = G.assess(row, root, repo, git)
    assert ok and "NO-REGRESSION" in why and "/r1/" in why
    mkrun(root, "r2", hold=(-120.0, 900, "PASS"), mtime=10**9 + 3)
    ok, why = G.assess(row, root, repo, git)
    assert not ok and "REGRESSION" in why and "--canary-fix" in why
    row["canary_fix"] = "x@" + str(root / "r2/canary.json")
    ok, why = G.assess(row, root, repo, git)
    assert ok and "REGRESSION" in why


def test_face_cover_kit_declared_subblock_clock_and_reset_ports(tmp_path):
    """KV core c0e2df27a false positive: merged sub-block clock ports (core.json 'clk_unused', no load) were counted
    as dropped data pins and sub-block async resets into their synchroniser as shared."""
    net = r"""
module top(g_l8__clk, g_stin__clk, g_stin__rst_n, a, o);
input g_l8__clk; input g_stin__clk; input g_stin__rst_n; input a; output o;
wire q; wire s1; wire s2;
DFFHQNx1_ASAP7_75t_R f0 (.CLK(g_l8__clk), .D(a), .QN(q));
DFFHQNx1_ASAP7_75t_R f1 (.CLK(g_l8__clk), .D(q), .QN(o));
DFFASRHQNx1_ASAP7_75t_R r0 (.CLK(g_l8__clk), .D(1'b1), .RESETN(g_stin__rst_n), .SETN(1'b1), .QN(s1));
DFFASRHQNx1_ASAP7_75t_R r1 (.CLK(g_l8__clk), .D(s1), .RESETN(g_stin__rst_n), .SETN(1'b1), .QN(s2));
endmodule
"""
    (tmp_path / "n.v").write_text(net)
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps([{"bus": x, "bit": None} for x in ("g_l8__clk", "g_stin__clk", "g_stin__rst_n", "a", "o")]))
    sdc_clk = C.configured_clock_ports("create_clock -name clk -period 833 [get_ports {g_l8__clk}]\n")
    bad = C.face_cover(tmp_path / "n.v", pins, clock_ports=sdc_clk)
    assert bad["verdict"] == "FAIL" and "dropped" in bad["fails"]
    (tmp_path / "core.json").write_text(json.dumps({"boundary_role": {
        "g_l8__clk": "clk", "g_stin__clk": "clk_unused", "g_stin__rst_n": "reset", "a": "in", "o": "out"}}))
    kclk, krst = C.kit_declared_ports(tmp_path)
    assert kclk == ["g_l8__clk", "g_stin__clk"] and krst == ["g_stin__rst_n"]
    good = C.face_cover(tmp_path / "n.v", pins, clock_ports=sorted(set(sdc_clk) | set(kclk)), reset_ports=krst)
    assert good["verdict"] == "PASS", good
    # a data port labelled as anything else stays checked: drop the face register on 'a' -> still FAIL
    (tmp_path / "d.v").write_text(net.replace(".D(a)", ".D(1'b0)"))
    assert C.face_cover(tmp_path / "d.v", pins, clock_ports=kclk, reset_ports=krst)["verdict"] == "FAIL"


def test_vector_clock_bit_in_sdc_names_its_bus():
    assert C.configured_clock_ports("create_clock -name c -period 1 [get_ports {g_t_2_u_l8__clk[0]}]") == ["g_t_2_u_l8__clk"]
    assert C.configured_clock_ports("create_clock -name c [get_ports clk_x[0]]") == ["clk_x"]
    assert C.configured_clock_ports("create_clock -name c [get_ports {clk[*] d[1:0]}]") == []
