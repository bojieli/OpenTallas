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
def run(key, mode, w):
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
