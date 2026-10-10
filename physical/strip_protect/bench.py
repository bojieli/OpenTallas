#!/usr/bin/env python3
"""strip-protect 2026-10-09: exact bench + negative mutant for the unprotected successors (REVIEW_20261009 S4/X2/X3:
no mirrors / complement copies / TMR / parity on control; SECDED on SRAM/HBM payloads only) and the TA15 collar
successor.  Run from the source snapshot root (the closure loop's {SRC} cwd):

    python3 physical/strip_protect/bench.py <key> pos|neg|pos1 <workdir>

Every case compiles a LOCK-STEP PAIR in place of the element's top module: the ORIGINAL (frozen copy of the source
before this stream, physical/strip_protect/orig/, modules renamed orig_*) and the SUCCESSOR from rtl/ (modules
renamed new_*, PROTECT=0) see the same inputs; the wrapper drives the bench from the successor and $fatal's on any
output difference that persists 1 ps once reset is released (STRIP_EQUIV_MISMATCH).  The element's committed
functional golden bench runs on top of the pair unchanged except for its fault-injection cases (they test the
rejected protection itself) and hierarchical references (dut. -> dut.n.).
  pos   prints STRIP_<key>_PASS (rc 0): golden PASS line, STRIP_EQUIV_ARMED, no mismatch, no fatal.
  neg   applies the element's RTL mutant to the SUCCESSOR, prints STRIP_<key>_NEG_FAIL (rc 1) when the golden or the
        equivalence check rejects it.
  pos1  (local) the successor at PROTECT=1 against the original: the protected variant stays the original.
Simulator: Icarus (-g2012).  Exit 2 = BENCH_ERROR (build failure, positive failed, or mutant escaped).
"""
import importlib.util, re, subprocess, sys, types
from pathlib import Path

R = Path.cwd()
ORIG = R / "physical/strip_protect/orig"
SECDED = "rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv"
HOST_RTL = ["rtl/lib/ot_reset_sync.sv", "rtl/link/ot_link_afifo.sv", "rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv",
            "rtl/hdc/ingest/ot_hdc_kv_ingest.sv", "rtl/hdc/ingest/ot_rom_host_ingest.sv",
            "physical/rom_host_ingest/rtl/dsfd_host.sv"]


def gate_const(tool, name):
    spec = importlib.util.spec_from_file_location("g", R / tool)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, name)


def format_tb(w):
    """tools/hbm_index_native_format_gate.py writes tb.sv + packets.mem + flits.mem before it builds; stub the build."""
    spec = importlib.util.spec_from_file_location("g", R / "tools/hbm_index_native_format_gate.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    m.subprocess = types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(returncode=1), STDOUT=None)
    g = w / "gate"; argv = sys.argv; sys.argv = ["gate", "--work", str(g)]
    try: m.main()
    finally: sys.argv = argv
    for f in ("packets.mem", "flits.mem"): (w / f).write_text((g / f).read_text())
    return (g / "tb.sv").read_text()


def gorder_tb(n):
    """Committed full-shape order bench at a reduced literal count n (the full 131,072 run is ~2M edges per DUT)."""
    t = (R / "rtl/test/hbm_accel/tb_hbm_index_global_order.sv").read_text()
    assert t.count("131072") == 2 and t.count("131264") == 1
    return t.replace("131264", str(n + 192)).replace("131072", str(n))


CMASK_FAULT = ("  // Correctable mutable-mask upset preserves every output bit.",
               "$fatal(1,\"UE mask admitted\");\n")


def cmask_tb():
    t = (R / "rtl/qwen_r25_su_dispatch/tb_qwen_r25_causal_mask.sv").read_text()
    a, b = t.index(CMASK_FAULT[0]), t.index(CMASK_FAULT[1]) + len(CMASK_FAULT[1])
    # CE/UE injection into the SECDED seats tests the rejected protection: replaced by an equivalent held-frame check.
    return t[:a] + "  accept_frame(8192,300);\n  held=out_live;\n  @(negedge clk);if(fault||out_live!==held||!out_v)$fatal(1,\"held frame lost\");\n" + t[b:]


def host_tb(w):
    """tb_rom_host_ingest (the ROM host block's exact HBM-image bench) around dsfd_host_native: host_ack_n = the
    fabric's actual sector writes, so fenced completions wait for physical visibility."""
    t = (R / "rtl/test/tb_rom_host_ingest.sv").read_text()
    a = t.index("    ot_rom_host_ingest #(")
    b = t.index(".fault(fault));", a) + len(".fault(fault));")
    t = t[:a] + ("    reg [7:0] host_ack_n = 8'd0;\n    dsfd_host_native #(.ENABLE(1)) dut (\n"
                 "        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d),\n"
                 "        .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),\n"
                 "        .i_rv(i_rv), .i_rd(i_rd), .host_ack_n(host_ack_n), .fault(fault));") + t[b:]
    for x, y in (("o_cr <= 1'b0; i_rv <= 1'b0;", "o_cr <= 1'b0; i_rv <= 1'b0; host_ack_n <= 8'd0;"),
                 ("hbm[fq_a[fr % OCRED]] <= fq_d[fr % OCRED]; sectors <= sectors + 1;",
                  "hbm[fq_a[fr % OCRED]] <= fq_d[fr % OCRED]; sectors <= sectors + 1; host_ack_n <= 8'd1;"),
                 ("dut.share_c", "0")):
        assert t.count(x) == 1, x
        t = t.replace(x, y)
    sys.path.insert(0, str(R / "tools"))
    import numpy as np  # noqa: F401
    import rtl_hdc_kv_ingest_campaign as C
    rng = np.random.default_rng(20261009)
    cases = {"raw": C.case_raw(rng, 300), "v41_win": C.case_rows(rng, "win", 200, first=0)}
    for name, c in cases.items():
        c["nb"] = [(d >> 240) & 0xFFFF for d in c["descs"]]
        memw = C.pow2(max(c["exp"].size // 32 + 1, 1024 + 64))
        d = w / name
        C.write_case(d, c, memw)
        (d / "nb.mem").write_text("".join(f"{x:08x}\n" for x in c["nb"]))
        c["memw"] = memw
    return t, cases


HING = re.compile(r"HING descs=(\d+) beats=(\d+)/(\d+) sectors=(\d+) reads=(\d+) errors=(\d+) oob=(\d+) dones=(\d+)/(\d+) "
                  r"tag_err=(\d+) fault_words=(\d+) fault=(\d+) ck_cycles=(\d+) timeout=(\d+)")


def hing_ok(out):
    m = HING.search(out)
    if not m: return False
    d, b, nb, s, rd, e, oob, dn, nf, te, fw, f, cyc, to = map(int, m.groups())
    return e == 0 and oob == 0 and to == 0 and b == nb and dn == nf and nf > 0 and te == 0 and fw == 0 and f == 0 and s > 0


IDX = "rtl/hbm_accel/index/"
E = {
 "cand_format": dict(top="ot_hbm_native_candidate_format", files=[IDX + "ot_hbm_native_candidate_format.sv"], params="ENABLE=0",
     clocks=["clk"], reset="por_n", tb=lambda w: format_tb(w), tbtop="tb", runs=[[]], ok=lambda o: re.search(r"FORMAT_DONE .*errors=0", o),
     mutant=("{packet[54:38],packet[21:6],packet[4]}", "{packet[54:38],packet[21:6],packet[5]}")),
 "cand_parse": dict(top="ot_hbm_native_candidate_parse", files=[IDX + "ot_hbm_native_candidate_parse.sv"], params="ENABLE=0",
     clocks=["clk"], reset="por_n", tb=lambda w: gate_const("tools/hbm_index_native_credit_gate.py", "PARSE"), tbtop="tb", runs=[[]],
     ok=lambda o: "PARSE_DONE" in o, mutant=("assign quarter_last=held[511]&&slot==14;", "assign quarter_last=held[511]&&slot==13;")),
 "query_credit": dict(top="ot_hbm_native_index_query_credit", files=[IDX + "ot_hbm_native_index_query_credit.sv"], params="ENABLE=0",
     clocks=["clk"], reset="por_n", tb=lambda w: gate_const("tools/hbm_index_native_credit_gate.py", "QUERY"), tbtop="tb", runs=[[]],
     ok=lambda o: "QUERY_DONE" in o, mutant=("qb_hold[1047:1]<={head_weight,block_data,", "qb_hold[1047:1]<={head_weight,~block_data,")),
 "index_control": dict(top="ot_hbm_native_index_control", files=["rtl/hbm_accel/control/ot_hbm_native_index_control.sv"],
     params="ENABLE=0,PREFETCH=0", clocks=["clk"], reset="por_n",
     tb=lambda w: (R / "rtl/test/hbm_accel/tb_hbm_native_index_control.sv").read_text(), tbtop="tb_hbm_native_index_control",
     runs=[[], ["-Ptb_hbm_native_index_control.PREFETCH_CASE=1"]], ok=lambda o: "PASS_NATIVE_INDEX_CONTROL" in o,
     mutant=("desc[35:32],desc[31:0]", "4'b0,desc[31:0]")),
 "global_order": dict(top="ot_hbm_index_global_order", files=[IDX + "ot_hbm_index_global_order.sv"], params="ENABLE=0,STATIC_SCAN=0",
     clocks=["clk"], reset="por_n", tb=lambda w: gorder_tb(12288), tbtop="tb_hbm_index_global_order", runs=[[]],
     ok=lambda o: "PASS_GLOBAL_ORDER ranks=96 tuples=12288 actual_reads=12480" in o,
     mutant=("assign out_tuple=selected<96?head[selected]:34'd0;", "assign out_tuple=selected<96?head[selected]^34'd2:34'd0;")),
 "global_order_scan": dict(top="ot_hbm_index_global_order", files=[IDX + "ot_hbm_index_global_order.sv"], params="ENABLE=0,STATIC_SCAN=0",
     clocks=["clk"], reset="por_n", tb=lambda w: gorder_tb(4096), tbtop="tb_hbm_index_global_order",
     runs=[["-Ptb_hbm_index_global_order.SCAN_CASE=1"]], ok=lambda o: "PASS_GLOBAL_ORDER ranks=96 tuples=4096 actual_reads=4288" in o,
     mutant=("assign out_tuple=selected<96?head[selected]:34'd0;", "assign out_tuple=selected<96?head[selected]^34'd2:34'd0;")),
 "vis_fence": dict(top="ot_s81_ingest_visibility_fence", files=["rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv"],
     shared=[SECDED], params="ENABLE=0", clocks=["ck", "clk_h"], reset="rst_n",
     tb=lambda w: (R / "rtl/test/s81_native_ingest/tb_s81_ingest_visibility.sv").read_text(), tbtop="tb_s81_ingest_visibility",
     runs=[[]], ok=lambda o: "S81_VISIBILITY PASS" in o,
     mutant=("out_v<=1;out_d<=head;in_cr<=1;", "out_v<=1;out_d<=head^64'h0000100000000000;in_cr<=1;")),
 "host_native": dict(top="dsfd_host_native", files=["rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv",
     "rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv"], shared=[SECDED] + HOST_RTL, params="ENABLE=0",
     clocks=["clk_h", "ck"], reset="rst_n", host=True, ok=hing_ok,
     mutant=("out_v<=1;out_d<=head;in_cr<=1;", "out_v<=1;out_d<=head^64'h0000100000000000;in_cr<=1;"),
     mutant_file="rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv"),
 "causal_mask": dict(top="ot_qwen_r25_causal_mask", files=["rtl/qwen_r25_su_dispatch/ot_qwen_r25_causal_mask_flat.sv"],
     params="ENABLE=0,CAPACITY=8224", clocks=["clk"], reset="rst_n", tb=lambda w: cmask_tb(), tbtop="tb_qwen_r25_causal_mask",
     runs=[[]], ok=lambda o: "PASS_QWEN_R25_P4_CAUSAL_MASK" in o,
     mutant=("live[q*32+r]=(q<in_queries)&&(row<limit)&&(row<CAPACITY);", "live[q*32+r]=(q<in_queries)&&(row<=limit)&&(row<CAPACITY);")),
 "host_dispatch": dict(top="ot_s81_host_dispatch", files=["rtl/dsrom_sys/s81_ingest/ot_s81_host_dispatch.sv"], params="ENABLE=0",
     clocks=["ck"], reset="rst_n", tb=lambda w: (R / "rtl/test/s81_native_ingest/tb_s81_host_dispatch.sv").read_text(),
     tbtop="tb_s81_host_dispatch", runs=[[]], ok=lambda o: "S81_HOST_DISPATCH PASS" in o,
     mutant=("((i_d[65:64]==3)?3'b100:3'b010)", "((i_d[65:64]==3)?3'b010:3'b100)")),
 "ta15_rs": dict(ta15=True, ok=lambda o: "PASS clock/reset boundary" in o,
     mutant=("   if(!up[k]) q<=1'b0;", "   if(1'b0) q<=1'b0;"), mutant_file="rtl/hbm_accel/control/ot_hbm_clock_reset_collars_rs.sv"),
}


def strip_comments(s):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", s, flags=re.S))


def ports_of(text, top):
    s = strip_comments(text)
    i = re.search(r"\bmodule\s+%s\b" % top, s).end()
    j = s.index("(", i)
    if s[i:j].strip() == "#":          # parameter list
        depth, k = 0, j
        while True:
            depth += {"(": 1, ")": -1}.get(s[k], 0); k += 1
            if depth == 0: break
        j = s.index("(", k)
    depth, k = 0, j
    while True:
        depth += {"(": 1, ")": -1}.get(s[k], 0); k += 1
        if depth == 0: break
    out, cur = [], None
    for item in s[j + 1:k - 1].split(","):
        item = " ".join(item.split())
        m = re.match(r"^(input|output|inout)\s*(?:wire|reg|logic)?\s*(?:signed)?\s*(\[[^\]]+\])?\s*(\w+)$", item)
        if m: cur = (m.group(1), m.group(2) or ""); out.append((cur[0], cur[1], m.group(3)))
        elif re.match(r"^\w+$", item): out.append((cur[0], cur[1], item))
        else: raise SystemExit(f"STRIP port parse: {item!r}")
    return out


def wrapper(top, ports, params, reset, protect):
    pdecl = ",".join(f"parameter integer {p}" for p in params.split(","))
    pmap = ",".join(f".{p.split('=')[0]}({p.split('=')[0]})" for p in params.split(","))
    hdr = ",\n ".join(f"{d} wire {r} {n}".replace("  ", " ") for d, r, n in ports)
    outs = [(r, n) for d, r, n in ports if d == "output"]
    L = ["`timescale 1ps/1fs", f"module {top} #({pdecl})(\n {hdr}\n);"]
    L += [f" wire {r} o_{n};" for r, n in outs]
    L.append(f" orig_{top} #({pmap}) o(" + ",".join(f".{n}({'o_' if d == 'output' else ''}{n})" for d, r, n in ports) + ");")
    L.append(f" new_{top} #({pmap},.PROTECT({protect})) n(" + ",".join(f".{n}({n})" for d, r, n in ports) + ");")
    L.append(f" wire strip_diff=({reset}===1'b1)&&({{{','.join(n for r, n in outs)}}}!=={{{','.join('o_' + n for r, n in outs)}}});")
    L.append(f" always @(posedge {reset}) $display(\"STRIP_EQUIV_ARMED\");")
    L.append(" always @(posedge strip_diff) begin #1; if(strip_diff) begin")
    L += [f"  if({n}!==o_{n}) $display(\"STRIP_EQUIV_MISMATCH port={n} t=%0t new=%h orig=%h\",$time,{n},o_{n});" for r, n in outs]
    L.append("  $fatal(1,\"STRIP_EQUIV_MISMATCH\"); end end\nendmodule\n")
    return "\n".join(L)


TA15_WRAP = """`timescale 1ps/1fs
module ot_hbm_clock_reset_collars #(parameter integer LINK_PORTS=9)(
 input wire clk_stream, clk_serial, clk_hbm, clk_link, por_n, pll_reset_n, pll_lock,
 input wire [3:0] phy_reset_intent_n, input wire [LINK_PORTS-1:0] link_reset_intent_n,
 input wire coll_reset_intent_n, cmd_reset_intent_n,
 output wire [3:0] phy_reset_n, output wire [LINK_PORTS-1:0] link_reset_n,
 output wire coll_reset_stream_n, coll_reset_serial_n, cmd_reset_stream_n, cmd_reset_serial_n);
 wire [3:0] o_phy; wire [LINK_PORTS-1:0] o_link; wire o_cs, o_cse, o_ms, o_mse;
 orig_ot_hbm_clock_reset_collars #(.LINK_PORTS(LINK_PORTS)) o(.clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.por_n(por_n),.pll_reset_n(pll_reset_n),.pll_lock(pll_lock),.phy_reset_intent_n(phy_reset_intent_n),
  .link_reset_intent_n(link_reset_intent_n),.coll_reset_intent_n(coll_reset_intent_n),.cmd_reset_intent_n(cmd_reset_intent_n),
  .phy_reset_n(o_phy),.link_reset_n(o_link),.coll_reset_stream_n(o_cs),.coll_reset_serial_n(o_cse),.cmd_reset_stream_n(o_ms),.cmd_reset_serial_n(o_mse));
 ot_hbm_clock_reset_collars_rs #(.LINK_PORTS(LINK_PORTS)) n(.clk_stream(clk_stream),.clk_serial(clk_serial),.clk_hbm(clk_hbm),
  .clk_link(clk_link),.por_n(por_n),.pll_reset_n(pll_reset_n),.pll_lock(pll_lock),.phy_reset_intent_n(phy_reset_intent_n),
  .link_reset_intent_n(link_reset_intent_n),.coll_reset_intent_n(coll_reset_intent_n),.cmd_reset_intent_n(cmd_reset_intent_n),
  .phy_reset_n(phy_reset_n),.link_reset_n(link_reset_n),.coll_reset_stream_n(coll_reset_stream_n),.coll_reset_serial_n(coll_reset_serial_n),
  .cmd_reset_stream_n(cmd_reset_stream_n),.cmd_reset_serial_n(cmd_reset_serial_n));
 // Asynchronous assertion: compared continuously (any difference persisting 1 ps), not on clock edges.
 reg armed=0; initial begin #1000; armed=1; $display("STRIP_EQUIV_ARMED"); end
 wire strip_diff=armed&&({phy_reset_n,link_reset_n,coll_reset_stream_n,coll_reset_serial_n,cmd_reset_stream_n,cmd_reset_serial_n}!==
                         {o_phy,o_link,o_cs,o_cse,o_ms,o_mse});
 always @(posedge strip_diff) begin #1; if(strip_diff) begin
  $display("STRIP_EQUIV_MISMATCH t=%0t new=%h orig=%h",$time,{phy_reset_n,link_reset_n},{o_phy,o_link});
  $fatal(1,"STRIP_EQUIV_MISMATCH"); end end
endmodule
"""


def rename(text, mods, prefix, inst=True):
    for m in mods:
        text = re.sub(r"\bmodule\s+%s\b" % m, f"module {prefix}{m}", text)
        if inst: text = re.sub(r"(^|\s)%s(\s*(#|\w+\s*\())" % m, r"\1%s%s\2" % (prefix, m), text, flags=re.M)
    return text


def mutate(text, frm, to):
    if text.count(frm) != 1: bench_error(f"mutant needle count {text.count(frm)}: {frm}")
    return text.replace(frm, to)


def bench_error(msg):
    print(f"STRIP_{KEY}_BENCH_ERROR: {msg}"); sys.exit(2)


def sim(w, srcs, top, extra, plus=()):
    vvp = w / f"{top}_{abs(hash(tuple(extra))) % 9973}.vvp"
    b = subprocess.run(["iverilog", "-g2012", "-I", "rtl/common", "-s", top, "-o", str(vvp), *extra, *map(str, srcs)],
                       capture_output=True, text=True)
    (w / "build.log").open("a").write(" ".join(b.args) + "\n" + b.stdout + b.stderr)
    if b.returncode: print(b.stdout + b.stderr); bench_error("iverilog build")
    r = subprocess.run(["vvp", "-n", str(vvp), *plus], cwd=w, capture_output=True, text=True, timeout=6 * 3600)
    return r.returncode, r.stdout + r.stderr


def main():
    global KEY
    KEY, mode, w = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    w.mkdir(parents=True, exist_ok=True); w = w.resolve()
    e = E.get(KEY) or bench_error("unknown element")
    neg, protect = mode == "neg", 1 if mode == "pos1" else 0
    srcs = [R / s for s in e.get("shared", [])]
    if e.get("ta15"):
        succ = (R / "rtl/hbm_accel/control/ot_hbm_clock_reset_collars_rs.sv").read_text()
        if neg: succ = mutate(succ, *e["mutant"])
        files = {"new_collars_rs.sv": succ, "wrap.sv": TA15_WRAP,
                 "orig_boundary.sv": rename((ORIG / "ot_hbm_clock_reset_boundary.sv").read_text(), ["ot_hbm_clock_reset_collars"], "orig_", inst=False)}
        for n, t in files.items(): (w / n).write_text(t); srcs.append(w / n)
        srcs += [ORIG / "ot_hbm_reset_seq.sv", R / "tests/rtl/tb_hbm_clock_reset_boundary.sv"]
        runs, tbtop = [[]], "tb"
    else:
        mods = [re.search(r"\bmodule\s+(\w+)", (R / f).read_text()).group(1) for f in e["files"]]
        mf = e.get("mutant_file", e["files"][0])
        for f in e["files"]:
            o = rename((ORIG / Path(f).name).read_text(), mods, "orig_")
            s = (R / f).read_text()
            if neg and f == mf: s = mutate(s, *e["mutant"])
            s = rename(s, mods, "new_")
            (w / ("orig_" + Path(f).name)).write_text(o); (w / ("new_" + Path(f).name)).write_text(s)
            srcs += [w / ("orig_" + Path(f).name), w / ("new_" + Path(f).name)]
        top = e["top"]
        wr = wrapper(top, ports_of((ORIG / Path(e["files"][0]).name).read_text(), top), e["params"], e["reset"], protect)
        (w / "pair.sv").write_text(wr); srcs.insert(0, w / "pair.sv")
        if e.get("host"):
            tb, cases = host_tb(w)
            (w / "tb.sv").write_text(tb); srcs.append(w / "tb.sv")
            outs = []
            for name, c in cases.items():
                ex = [f"-Ptb_rom_host_ingest.{k}={v}" for k, v in dict(MEMW=c["memw"], ND=16, NP=1 << max(4, (len(c["beats"]) - 1).bit_length()),
                                                                     HDMAX=16, KVHMAX=1, QKV_EN=0, RMW_EN=0).items()]
                rc, out = sim(w / name, srcs, "tb_rom_host_ingest", ex, [f"+ND={len(c['descs'])}", f"+NP={len(c['beats'])}", "+MSTALL=30", "+SEED=5"])
                (w / f"{name}.log").write_text(out); outs.append((rc, out)); print(name, out.strip().splitlines()[-1:] if out.strip() else "")
            return verdict(e, outs, neg)
        tb = e["tb"](w).replace("dut.", "dut.n.")
        (w / "tb.sv").write_text(tb); srcs.append(w / "tb.sv")
        runs, tbtop = e["runs"], e["tbtop"]
    outs = []
    for i, extra in enumerate(runs):
        rc, out = sim(w, srcs, tbtop, extra)
        (w / f"run{i}.log").write_text(out); outs.append((rc, out))
        print(f"run{i} rc={rc}", "\n".join(out.strip().splitlines()[-3:]))
    return verdict(e, outs, neg)


def verdict(e, outs, neg):
    good = [rc == 0 and bool(e["ok"](o)) and "STRIP_EQUIV_ARMED" in o and "STRIP_EQUIV_MISMATCH" not in o
            and not re.search(r"\bFATAL\b|\$fatal|^ERROR", o, re.M) for rc, o in outs]
    if not neg:
        if all(good): print(f"STRIP_{KEY}_PASS"); return 0
        bench_error("positive failed")
    rejected = [not g and (rc != 0 or "MISMATCH" in o or re.search(r"fatal|FATAL|mismatch", o)) for g, (rc, o) in zip(good, outs)]
    if any(rejected): print(f"STRIP_{KEY}_NEG_FAIL"); return 1
    bench_error("mutant escaped")


if __name__ == "__main__":
    sys.exit(main())
