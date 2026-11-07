# lock-step bench generator: ref (original) vs dut (vA) ot_hgi_coll_gqi_issue, internal programme target outputs forced
import re, sys
src = re.sub(r"//[^\n]*", "", open(sys.argv[1]).read())
hdr = src[src.index("module ot_hgi_coll_gqi_issue"):]
hdr = hdr[hdr.index(")(")+2: hdr.index(");")]
ports = []
for l in hdr.split("\n"):
    l = l.split("//")[0]
    m = re.match(r"\s*(input|output)\s+(?:wire|reg)?\s*(\[[^\]]*\])?\s*(.*)", l)
    if m:
        ports += [(m[1], m[2] or "", p.strip()) for p in m[3].split(",") if p.strip()]
ins = [p for p in ports if p[0] == "input" and p[2] not in ("clk", "rst_n")]
outs = [p for p in ports if p[0] == "output"]
L = ["`timescale 1ns/1ps", "module tb;", "  reg clk = 0, rst_n = 0; always #1 clk = ~clk;",
     "  integer wr = 0, starts = 0, rstp = 0, dirty = 1, masked = 0, ovb = 0, ovnb = 0, legal = 0, legalq = 0, resets = 0; integer lastx = 0; integer seed, cyc = 0, errs = 0, checks = 0, fires = 0, qfires = 0, exw = 0, skips = 0, xonly = 0;"]
for d, w, n in ins: L.append(f"  reg {w} {n};")
for d, w, n in outs: L.append(f"  wire {w} r_{n}, d_{n};")
L.append("  ot_hgi_coll_gqi_issue_ref #(.MUT(`RMUT)) u_r (.clk(clk), .rst_n(rst_n && rstp == 0), " + ", ".join(f".{n}({n})" for d, w, n in ins) + ", " + ", ".join(f".{n}(r_{n})" for d, w, n in outs) + ");")
L.append("  ot_hgi_coll_gqi_issue #(.MUT(`DMUT)) u_d (.clk(clk), .rst_n(rst_n && rstp == 0), " + ", ".join(f".{n}({n})" for d, w, n in ins) + ", " + ", ".join(f".{n}(d_{n})" for d, w, n in outs) + ");")
L.append("  reg f_we, f_sv; reg [7:0] f_wa, f_sb; reg [255:0] f_wd; reg [8:0] f_sl; reg [15:0] f_lp;")
for inst in ("u_r", "u_d"):
    for a, b in (("p_we", "f_we"), ("p_wa", "f_wa"), ("p_wd", "f_wd"), ("p_sv", "f_sv"), ("p_sb", "f_sb"), ("p_sl", "f_sl"), ("p_lp", "f_lp")):
        L.append(f"  initial force {inst}.{a} = {b};")
L.append("""  function [255:0] rrow; input integer k; reg [255:0] x; begin
    x = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
    x[18:3] = 16'(k) * 16'd80 + 16'd4;  x[100:85] = 16'd1400; x[28:19] = ($urandom(seed) % 8 == 0) ? 0 : 1 + $urandom(seed) % 24;
    x[36:29] = $urandom(seed) % 40; if ($urandom(seed) % 4 == 0) x[36:29] = (x[28:19] * 32) / 33;
    x[71:69] = ($urandom(seed) % 10 == 0) ? 1 : 0;
    rrow = x; end endfunction""")
L.append("  always @(posedge clk) begin")
L.append("    #0.2;")
for d, w, n in ins:
    W = 1
    m = re.match(r"\[(\d+):0\]", w)
    if m: W = int(m[1]) + 1
    if n in ("qid", "tgt"): continue
    if n in ("cfg_v", "desc_v", "launch_v"): L.append(f"    {n} = 0;"); continue
    words = (W + 31) // 32
    L.append(f"    {n} = {{" + ", ".join(["$random(seed)"] * words) + "};")
L.append("""    f_we = 0; f_sv = 0;
    if (u_r.run || u_r.busy || !rst_n || rstp != 0) wr = 0;
    else if (wr < 16) begin f_we = 1; f_wa = wr; f_wd = rrow(wr); wr = wr + 1; end
    else begin f_sv = 1; f_sb = 0; f_sl = 16; f_lp = 1; wr = 0; end
    if ($urandom(seed) % 3 != 0) begin aq0_vo = 0; aq1_vo = 0; end
  end""")
L.append("  always @(negedge clk) if (rst_n && rstp == 0 && cyc > 4) begin checks = checks + 1;")
for d, w, n in outs:
    if n in ("ld_p_d","rb_lp_data","ra_lp_data"): L.append(f"    if (dirty != 0) masked = masked + 1; else")
    L.append(f"    if (^r_{n} === 1'bx) skips = skips + 1; else if (^d_{n} === 1'bx) begin xonly = xonly + 1; lastx = cyc; end else if (r_{n} !== d_{n}) begin errs = errs + 1; if (errs < 6) $display(\"MISMATCH cyc=%0d {n}\", cyc); end")
L.append("  end")
L.append("""  always @(posedge clk) begin
    if (rstp > 0) rstp = rstp - 1;
    if (rst_n && u_r.fire && u_r.ev_v[u_r.S_P-2]) begin if (u_r.busy) ovb = ovb + 1; else ovnb = ovnb + 1; end
    if (rst_n && u_r.fire && u_r.busy) begin rstp = 6; dirty = 1; resets = resets + 1; end
    else if (rst_n && rstp == 0 && u_r.fire) begin dirty = 0; legal = legal + 1; if (u_r.rc[0]) legalq = legalq + 1; end
  end
  always @(posedge clk) begin cyc <= cyc + 1; if (u_r.fire) fires <= fires + 1; if (u_r.p_sv) starts <= starts + 1; if (u_r.fire && u_r.rc[0]) qfires <= qfires + 1; if (|u_r.ex_n) exw <= exw + 1; end
  initial begin
    seed = `SEED; qid = $urandom(seed) % 4; tgt = 8'hff;
    repeat (6) @(posedge clk); rst_n = 1;
    repeat (`NCYC) @(posedge clk);
    if ($urandom(seed) % 2) begin rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (`NCYC) @(posedge clk); end
    $display("LOCKSTEP seed=%0d checks=%0d errs=%0d fires=%0d qbg_fires=%0d ex_live=%0d skips=%0d xonly=%0d lastx=%0d masked=%0d starts=%0d legal=%0d legalq=%0d resets=%0d fire_ev_busy=%0d fire_ev_notbusy=%0d", seed, checks, errs, fires, qfires, exw, skips, xonly, lastx, masked, starts, legal, legalq, resets, ovb, ovnb);
    $finish;
  end
endmodule""")
open(sys.argv[2], "w").write("\n".join(L) + "\n")
