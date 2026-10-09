#!/usr/bin/env python3
"""struct-close 2026-10-09: exact bench + mutant for the registered-boundary (-cl) wrappers (physical/struct_close/regbound).
    python3 physical/struct_close/regbound/bench.py <key> pos|neg <workdir>
Each case runs the element's COMMITTED functional golden bench (unchanged except hierarchical references into the core:
dut.<x> -> dut.u_core.<x>) on the wrapper (+1 cycle per boundary crossing; the golden benches are transaction-level),
and the element's committed negative (a plusarg / define mutant, or an RTL mutant applied to the core).
pos prints RB_<key>_PASS (rc 0); neg prints RB_<key>_NEG_FAIL (rc 1) when the bench rejects the mutant; 2 = BENCH_ERROR.
"""
import importlib.util, re, subprocess, sys
from pathlib import Path
R = Path.cwd(); D = "physical/struct_close/regbound"
def const(tool, name):
    spec = importlib.util.spec_from_file_location("g", R / tool); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, name)
def tbfile(path): return (R / path).read_text()
CASES = {
 "cand_parse": dict(rtl=[f"{D}/ot_hbm_native_candidate_parse_rb.sv"], tb=lambda: const("tools/hbm_index_native_credit_gate.py", "PARSE"),
     top="tb", ok="PARSE_DONE", neg_mut=("assign quarter_last=held[511]&&slot==14;", "assign quarter_last=held[511]&&slot==13;"),
     neg_ok="PARSE_MISMATCH"),
}
def format_tb(w):
    """the committed format gate writes tb.sv + packets.mem + flits.mem before it builds: stub its build, keep the files."""
    import types
    spec = importlib.util.spec_from_file_location("fg", R / "tools/hbm_index_native_format_gate.py"); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); m.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=1), STDOUT=None)
    argv = sys.argv; sys.argv = ["g", "--work", str(w)]
    try: m.main()
    finally: sys.argv = argv
    return (w / "tb.sv").read_text()
CASES["cand_format"] = dict(rtl=[f"{D}/ot_hbm_native_candidate_format_rb.sv"], tb_w=format_tb, top="tb", ok="errors=0",
     neg_args=["+MUT_ID"], neg_ok="EXACT_MISMATCH", neg_allow_ok=True)
def hdisp_tb():
    t = tbfile("rtl/test/s81_native_ingest/tb_s81_host_dispatch.sv")
    a = "iv=0;cr=1;@(posedge ck);#0.05;if(!fault)"
    assert a in t
    # the registered boundary sees the phantom credit one edge later (fault +1 cycle, the priced boundary cost)
    return t.replace(a, "iv=0;cr=1;@(posedge ck);#0.05;cr=0;@(posedge ck);#0.05;if(!fault)")
CASES["s81_hdisp"] = dict(rtl=[f"{D}/ot_s81_host_dispatch_rb.sv"], tb=hdisp_tb, top="tb_s81_host_dispatch", ok="S81_HOST_DISPATCH PASS",
     neg_mut=("((i_d[65:64]==3)?3'b100:3'b010)", "((i_d[65:64]==3)?3'b010:3'b100)"), neg_ok="wrong branch/payload")
def ictl_tb():
    """the golden index-control bench; its two FAULT-VISIBILITY checks get +2 edges (input flop + output flop: the priced
    boundary cost; every functional check is unchanged)"""
    t = tbfile("rtl/test/hbm_accel/tb_hbm_native_index_control.sv")
    for a, b in (("tick();if(!fault||fs[0]||source_start_v)$fatal(1,\"wrong prefetch receipt accepted\");",
                  "tick();tick();tick();if(!fault||fs[0]||source_start_v)$fatal(1,\"wrong prefetch receipt accepted\");"),
                 ("command_rank=96;command_v=1;tick();command_v=0;tick();",
                  "command_rank=96;command_v=1;tick();command_v=0;tick();tick();tick();")):
        assert a in t, a
        t = t.replace(a, b)
    return t
CASES["index_control"] = dict(rtl=[f"{D}/ot_hbm_native_index_control_rb.sv"], tb=ictl_tb,
     top="tb_hbm_native_index_control", ok="PASS_NATIVE_INDEX_CONTROL", neg_mut=("desc[35:32],desc[31:0]", "4'b0,desc[31:0]"), neg_ok="dynamic frame metadata mismatch")
CASES["index_control_pf"] = dict(CASES["index_control"], params=["-Ptb_hbm_native_index_control.PREFETCH_CASE=1"])
def pco_tb():
    """the golden PC head-owner bench (PCO_CL build); its immediate STATUS checks get +2 edges (ack / input pin flop +
    output flop: the priced boundary cost).  Ordering, identity, payload, SECDED correction checks are unchanged."""
    t = tbfile("rtl/test/qwen_system/tb_qfd_pc_head_owner.sv")
    for a, b in (("for(n=1;n<=16;n=n+1)push(n);\n  if(dut.count[0]!=16)", "for(n=1;n<=16;n=n+1)push(n);\n  step;if(dut.count[0]!=16)"),
                 ("  if(credits!=16||dut.count[0]!=0)", "  step;step;if(credits!=16||dut.count[0]!=0)"),
                 ("acknowledge(n,2);repeat(2)step;", "acknowledge(n,2);repeat(4)step;"),
                 ("acknowledge(1,3);wait_head(2);", "acknowledge(1,3);step;step;wait_head(2);"),
                 ("push(n);if(!fault)$fatal(1,\"overflow escaped\")", "push(n);step;step;if(!fault)$fatal(1,\"overflow escaped\")"),
                 ("acknowledge(2,1);if(!fault||head_v)", "acknowledge(2,1);step;step;if(!fault||head_v)"),
                 ("monitor=0;acknowledge(1,1);if(!fault)", "monitor=0;acknowledge(1,1);step;step;if(!fault)")):
        assert a in t, a
        t = t.replace(a, b)
    return t
CASES["pc_head_owner"] = dict(rtl=[f"{D}/ot_qfd_pc_head_owner_cl_rb.sv", "rtl/common/ot_secded.sv"], tb=pco_tb, top="tb_qfd_pc_head_owner",
     defines=["PCO_CL"], ok="PASS pcowner UE", neg_params=["-Ptb_qfd_pc_head_owner.MUT=1"], neg_ok="NEG_DETECTED pcowner incorrect")
def sp_tb(fn, *a):
    """a golden bench builder of physical/strip_protect/bench.py (cmask_tb, gorder_tb)"""
    spec = importlib.util.spec_from_file_location("spb", R / "physical/strip_protect/bench.py"); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return getattr(m, fn)(*a)
CASES["query_credit"] = dict(rtl=[f"{D}/ot_hbm_native_index_query_credit_rb.sv"], tb=lambda: const("tools/hbm_index_native_credit_gate.py", "QUERY"),
     top="tb", ok="QUERY_DONE", neg_args=["+MUT_OWNER"], neg_ok="OWNER_REJECTED")
def cmask_rb_tb():
    """the golden causal-mask bench with the boundary latency: outputs are read once out_v rises (not on the accept
    edge), the 1-deep "in_rdy low while held" probe is dropped (the pin FIFO legally holds a second frame), and the
    fail-closed checks wait 4 edges.  Every value check is unchanged."""
    t = sp_tb("cmask_tb")
    for a, b in (("accept_frame(block_id*32,block_id);", "accept_frame(block_id*32,block_id);while(!out_v)@(negedge clk);"),
                 ("if(in_rdy||out_live!==held||!out_v)", "if(out_live!==held||!out_v)"),
                 ("accept_frame(8192,300);", "accept_frame(8192,300);while(!out_v)@(negedge clk);"),
                 ("accept_frame(8192,301);", "accept_frame(8192,301);repeat(4)@(negedge clk);"),
                 ("accept_frame(8192,302);", "accept_frame(8192,302);repeat(4)@(negedge clk);"),
                 ("accept_frame(8192,303);", "accept_frame(8192,303);repeat(4)@(negedge clk);")):
        assert a in t, a
        t = t.replace(a, b)
    return t
CASES["causal_mask"] = dict(rtl=[f"{D}/ot_qwen_r25_causal_mask_rb.sv"], tb=cmask_rb_tb, top="tb_qwen_r25_causal_mask",
     ok="PASS_QWEN_R25_P4_CAUSAL_MASK", neg_mut=("live[q*32+r]=(q<in_queries)&&(row<limit)&&(row<CAPACITY);",
                                               "live[q*32+r]=(q<in_queries)&&(row<=limit)&&(row<CAPACITY);"), neg_ok="")
CASES["global_order"] = dict(rtl=[f"{D}/ot_hbm_index_global_order_rb.sv"], tb=lambda: sp_tb("gorder_tb", 12288), top="tb_hbm_index_global_order",
     ok="PASS_GLOBAL_ORDER ranks=96 tuples=12288", neg_mut=("assign out_tuple=selected<96?head[selected]:34'd0;",
                                                            "assign out_tuple=selected<96?head[selected]^34'd2:34'd0;"), neg_ok="")
def tokloop(mode, w):
    """tools/hbm_token_loop_bench.py (independent Python reference, MUT=1 negative) on the wrapper"""
    import os, json as _j
    w = Path(w); w.mkdir(parents=True, exist_ok=True)
    t = tbfile("rtl/test/hbm_accel/tb_hbm_token_loop.sv").replace("dut.ls", "dut.u_core.ls")
    # the bench samples busy on the edge after the job handshake; the registered boundary shows busy 3 edges later
    a = "@(posedge clk); while (!job_rdy) @(posedge clk); job_v <= 0;"
    assert a in t
    t = t.replace(a, a + " repeat (3) @(posedge clk);")
    # the bench re-arms the next MTP commit on dut.ls == 4 a few edges after the last; the registered mtp_v reaches the
    # core one edge later, so the state probe waits 2 more edges (else a second batch is issued into the same state)
    b = "ib = ib + 1; mtp_v <= 1; @(posedge clk); mtp_v <= 0; host_stop <= 0;"
    assert b in t
    t = t.replace(b, b + " repeat (2) @(posedge clk);")
    (w / "tb_hbm_token_loop.sv").write_text(t)
    env = dict(os.environ, OT_TOKLOOP_SRC=" ".join([str(R / f"{D}/ot_hbm_token_loop_rb.sv"), str(R / "rtl/common/ot_sc_pfifo.sv"),
                                                    str(w / "tb_hbm_token_loop.sv")]))
    r = subprocess.run([sys.executable, str(R / "tools/hbm_token_loop_bench.py"), "--work", str(w / "g"), "--out", str(w / "g.json")],
                       capture_output=True, text=True, env=env)
    (w / "g.log").write_text(r.stdout + r.stderr); print((r.stdout + r.stderr)[-800:])
    try: rec = _j.loads((w / "g.json").read_text())
    except Exception: print("RB_token_loop_BENCH_ERROR no record"); return 2
    if mode == "pos":
        if r.returncode == 0 and any(l.startswith("PASS") for l in r.stdout.splitlines()): print("RB_token_loop_PASS"); return 0
        print("RB_token_loop_BENCH_ERROR positive"); return 2
    if rec.get("negative_mut1_no_eos", {}).get("verdict") == "FAIL": print("RB_token_loop_NEG_FAIL"); return 1
    print("RB_token_loop_BENCH_ERROR mutant escaped"); return 2
def mtpemit(mode, w):
    """tools/hbm_native_mtp_emit_gate.py (positive + constant-ready mutant) on the wrapper; the bench's final
    bad-index probe waits 4 edges for the registered fault/status (boundary cost); its token checks are unchanged"""
    import os, json as _j
    w = Path(w); w.mkdir(parents=True, exist_ok=True)
    t = tbfile("rtl/test/hbm_accel/tb_hbm_native_mtp_emit_queue.sv")
    a = "emit={20'd1,17'd4,1'b1};nd=1;@(negedge clk);emit=0;nd=0;"
    assert a in t
    (w / "tb.sv").write_text(t.replace(a, a + "repeat(4)@(negedge clk);"))
    env = dict(os.environ, OT_MTPEMIT_SRC=" ".join([str(R / f"{D}/ot_hbm_native_mtp_emit_queue_rb.sv"), str(w / "tb.sv"),
                                                    str(R / "rtl/common/ot_sc_pfifo.sv")]))
    r = subprocess.run([sys.executable, str(R / "tools/hbm_native_mtp_emit_gate.py"), "--work", str(w / "g"), "--out", str(w / "g.json")],
                       capture_output=True, text=True, env=env)
    (w / "g.log").write_text(r.stdout + r.stderr)
    try: c = _j.loads((w / "g.json").read_text())["cases"]
    except Exception: print((r.stdout + r.stderr)[-1500:]); print("RB_mtp_emit_queue_BENCH_ERROR no record"); return 2
    print(c[0]["output"][-400:])
    if mode == "pos":
        if c[0]["returncode"] == 0 and "PASS" in c[0]["output"]: print("RB_mtp_emit_queue_PASS"); return 0
        print("RB_mtp_emit_queue_BENCH_ERROR positive"); return 2
    if c[1]["mutant"] == 1 and c[1]["returncode"] != 0: print("RB_mtp_emit_queue_NEG_FAIL"); return 1
    print("RB_mtp_emit_queue_BENCH_ERROR mutant escaped"); return 2
def gorder_fast_tb(n):
    t = sp_tb("gorder_tb", n); a = ".STATIC_SCAN(SCAN_CASE))"; assert a in t
    return t.replace(a, ".STATIC_SCAN(SCAN_CASE),.FAST(1))")
# sys-takeover 2026-10-09: FAST=1 (shadow ordinal[rank], one-hot rank, digit-sum id%96), same bench / mutant
CASES["global_order_fast"] = dict(CASES["global_order"], tb=lambda: gorder_fast_tb(12288))
CASES["global_order_scan_fast"] = dict(CASES["global_order"], tb=lambda: gorder_fast_tb(4096),
     params=["-Ptb_hbm_index_global_order.SCAN_CASE=1"], ok="PASS_GLOBAL_ORDER ranks=96 tuples=4096")
def gorder_fast2_tb(n):
    t = sp_tb("gorder_tb", n); a = ".STATIC_SCAN(SCAN_CASE))"; assert a in t
    return t.replace(a, ".STATIC_SCAN(SCAN_CASE),.FAST(2))")
CASES["global_order_fast2"] = dict(CASES["global_order"], tb=lambda: gorder_fast2_tb(12288))
CASES["global_order_scan_fast2"] = dict(CASES["global_order"], tb=lambda: gorder_fast2_tb(4096),
     params=["-Ptb_hbm_index_global_order.SCAN_CASE=1"], ok="PASS_GLOBAL_ORDER ranks=96 tuples=4096")
CASES["global_order_scan"] = dict(CASES["global_order"], tb=lambda: sp_tb("gorder_tb", 4096),
     params=["-Ptb_hbm_index_global_order.SCAN_CASE=1"], ok="PASS_GLOBAL_ORDER ranks=96 tuples=4096")
def cvp_tb():
    """the golden VM-publication bench on the wrapper: the indexed read latency is 6 edges (4 + pin flop + output
    flop: the priced boundary cost) and the release / fault status probes wait 2 more edges; every data check is unchanged"""
    t = tbfile("rtl/hbm_accel/tu/link_retry_sram_20261008/tb_hbm_collective_vm_publication.sv")
    for a, b in (("if(cycles-expected_cycle[seen]!=4)", "if(cycles-expected_cycle[seen]!=6)"),
                 ("@(negedge clk);release_lease=1;tick;@(negedge clk);release_lease=0;tick;",
                  "@(negedge clk);release_lease=1;tick;@(negedge clk);release_lease=0;tick;tick;tick;"),
                 ("@(negedge clk);service_fault=1;tick;", "@(negedge clk);service_fault=1;tick;tick;tick;")):
        assert a in t, a
        t = t.replace(a, b)
    return t
L_ = "rtl/hbm_accel/tu/link_retry_sram_20261008"
CASES["coll_vm_pub"] = dict(rtl=[f"{D}/ot_hbm_collective_vm_publication_rb.sv", "rtl/common/ot_secded.sv", f"{L_}/ot_hbm_replay_sram.sv",
     "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"], tb=cvp_tb,
     top="tb_hbm_collective_vm_publication", ok="PASS_ALL", neg_defines=["OT_HBM_PUBLICATION_MUT_QID"], neg_ok="quarter read ownership lost")
def cvp_fix_tb():
    """sys-takeover PUBFIX=1: indexed read 7 edges on the wrapper (+1 MUXREG), everything else unchanged"""
    t = cvp_tb()
    for a, b in (("if(cycles-expected_cycle[seen]!=6)", "if(cycles-expected_cycle[seen]!=7)"),
                 ("ot_hbm_collective_vm_publication #(", "ot_hbm_collective_vm_publication #(.PUBFIX(1),")):
        assert t.count(a) == 1, a
        t = t.replace(a, b)
    return t
CASES["coll_vm_pub_fix"] = dict(CASES["coll_vm_pub"], tb=cvp_fix_tb)
def cvp_fix2_tb():
    """sys-takeover PUBFIX=2: same latency as PUBFIX=1 (7 edges indexed read); the header-change fault is +1 edge"""
    t = cvp_fix_tb(); a = "ot_hbm_collective_vm_publication #(.PUBFIX(1),"; assert t.count(a) == 1
    return t.replace(a, "ot_hbm_collective_vm_publication #(.PUBFIX(2),")
CASES["coll_vm_pub_fix2"] = dict(CASES["coll_vm_pub"], tb=cvp_fix2_tb)
CASES["coll_vm_pub_fix2_qoh"] = dict(CASES["coll_vm_pub"], tb=cvp_fix2_tb, neg_defines=["OT_HBM_PUBLICATION_MUT_QOH"],
     neg_ok="published FP32 order")
def artok(mode, w):
    """tools/hbm_native_ar_token_join_gate.py (4 positive vectors, MUT and owner-17 truncation mutants) on the wrapper"""
    import os, json as _j
    w = Path(w); w.mkdir(parents=True, exist_ok=True)
    src = ["rtl/hbm_accel/control/ot_hbm_token_loop.sv", f"{D}/ot_hbm_native_ar_token_join_rb.sv", "rtl/hbm_accel/qwen/r25/ot_qwen_r25_cmdproc18.sv",
           "rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv", "rtl/common/ot_sc_pfifo.sv", "rtl/test/hbm_accel/tb_hbm_native_ar_token_join.sv"]
    env = dict(os.environ, OT_ARTOK_SRC=" ".join(src))
    r = subprocess.run([sys.executable, str(R / "tools/hbm_native_ar_token_join_gate.py"), "--work", str(w / "g"), "--out", str(w / "g.json")],
                       capture_output=True, text=True, env=env, cwd=R)
    (w / "g.log").write_text(r.stdout + r.stderr)
    try: c = _j.loads((w / "g.json").read_text())["cases"]
    except Exception: print((r.stdout + r.stderr)[-1200:]); print("RB_ar_token_join_BENCH_ERROR no record"); return 2
    pos = [x for x in c if not x["mutant"]]; neg = [x for x in c if x["mutant"]]
    for x in c: print(x["mutant"], x["returncode"], x["output"][-160:].strip())
    if mode == "pos":
        if pos and all(x["returncode"] == 0 for x in pos): print("RB_ar_token_join_PASS"); return 0
        print("RB_ar_token_join_BENCH_ERROR positive"); return 2
    if neg and all(x["returncode"] != 0 for x in neg): print("RB_ar_token_join_NEG_FAIL"); return 1
    print("RB_ar_token_join_BENCH_ERROR mutant escaped"); return 2
def pco_n_tb():
    t = tbfile("rtl/test/qwen_system/tb_qfd_pc_head_owner_n.sv")
    for a, b in (("for(n=1;n<=16;n=n+1)push(n);\n  if(dut.count[0]!=16)", "for(n=1;n<=16;n=n+1)push(n);\n  step;if(dut.count[0]!=16)"),
                 ("  if(credits!=16||dut.count[0]!=0)", "  step;step;if(credits!=16||dut.count[0]!=0)"),
                 ("acknowledge(n,2);repeat(2)step;", "acknowledge(n,2);repeat(4)step;"),
                 ("acknowledge(1,3);wait_head(2);", "acknowledge(1,3);step;step;wait_head(2);"),
                 ("push(n);if(!fault)$fatal(1,\"overflow escaped\")", "push(n);step;step;if(!fault)$fatal(1,\"overflow escaped\")"),
                 ("monitor=0;acknowledge(1,1);step;if(!fault||head_v)", "monitor=0;acknowledge(1,1);step;step;step;if(!fault||head_v)"),
                 ("monitor=0;acknowledge(1,1);if(!fault)", "monitor=0;acknowledge(1,1);step;step;if(!fault)")):
        assert a in t, a
        t = t.replace(a, b)
    return t
CASES["pc_head_owner_n"] = dict(rtl=[f"{D}/ot_qfd_pc_head_owner_n_rb.sv", "rtl/common/ot_secded.sv"], tb=pco_n_tb, top="tb_qfd_pc_head_owner_n",
     ok="PASS pcowner UE", neg_params=["-Ptb_qfd_pc_head_owner_n.MUT=1"], neg_ok="NEG_DETECTED pcowner incorrect")
def run(key, mode, w):
    if key == "ar_token_join": return artok(mode, w)
    if key == "token_loop": return tokloop(mode, w)
    if key == "mtp_emit_queue": return mtpemit(mode, w)
    c = CASES[key]; w = Path(w); w.mkdir(parents=True, exist_ok=True)
    tb = c["tb_w"](w) if "tb_w" in c else c["tb"]()
    tb = re.sub(r"\bdut\.(?!u_core\b)", "dut.u_core.", tb)
    (w / "tb.sv").write_text(tb)
    rtl = [str(R / f) for f in c["rtl"]] + [str(R / "rtl/common/ot_sc_pfifo.sv")] + [str(R / f) for f in c.get("shared", [])]
    if mode == "neg" and "neg_mut" in c:   # RTL mutant applied to the core (inside the wrapper file)
        a, b_ = c["neg_mut"]; t = Path(rtl[0]).read_text()
        if a not in t: print(f"RB_{key}_BENCH_ERROR mutant needle missing"); return 2
        (w / "mut.sv").write_text(t.replace(a, b_, 1)); rtl[0] = str(w / "mut.sv")
    defs = [f"-D{d}" for d in c.get("defines", []) + (c.get("neg_defines", []) if mode == "neg" else [])] + c.get("params", []) + (c.get("neg_params", []) if mode == "neg" else [])
    b = subprocess.run(["iverilog", "-g2012", "-I", str(R / "rtl/common"), *defs, "-s", c["top"], "-o", str(w / "sim.vvp"), *rtl, str(w / "tb.sv")],
                       capture_output=True, text=True)
    (w / "build.log").write_text(b.stdout + b.stderr)
    if b.returncode: print(b.stdout + b.stderr); print(f"RB_{key}_BENCH_ERROR build"); return 2
    args = c.get("neg_args", []) if mode == "neg" else c.get("pos_args", [])
    r = subprocess.run(["vvp", "-n", str(w / "sim.vvp"), *args], capture_output=True, text=True, cwd=w)
    out = r.stdout + r.stderr; (w / "run.log").write_text(out); print(out[-1500:])
    if mode == "pos":
        if c["ok"] in out and "FATAL" not in out.upper().replace("FATAL: 0", ""): print(f"RB_{key}_PASS"); return 0
        print(f"RB_{key}_BENCH_ERROR positive"); return 2
    if c["neg_ok"] in out and (c.get("neg_allow_ok") or c["ok"] not in out): print(f"RB_{key}_NEG_FAIL"); return 1
    print(f"RB_{key}_BENCH_ERROR mutant escaped"); return 2
if __name__ == "__main__":
    sys.exit(run(sys.argv[1], sys.argv[2], sys.argv[3]))
