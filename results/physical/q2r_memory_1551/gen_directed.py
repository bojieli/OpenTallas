#!/usr/bin/env python3
"""gen_bench88.py RTL_PATCHED.sv OUTDIR: PART 58 (OT_Q2NF_RW) whole-core lock-step bench that EXERCISES THE MEMORIES.

DIE-HBM-88-Q2R 11-07.  The DIE-HBM-83-Q2R bench drove every input randomly and never loaded a programme, so the issuer
memories were never written, never read (issuer_read_en=0) and no uop ever reached a link (link_writes=0): all of its
mutants passed vacuously.  Here the testbench loads REAL programmes through the F20 programme target (target 52+qid,
7 frames per row, 55-edge drain gap, descriptor, ROWS+2 scan reserve, launch; ot_hgi_coll_static_program_target.sv),
so the issuer writes its 6 x 256x256 program banks, fetches (reads) them on launch, and the random uop payloads drive
link bank writes / reads through the upipe.  Every other input stays random under density modes.

Outputs written:
  old_w.sv  default (no define) branch of the patched file, modules renamed old_*  (= POR, byte-identical default text)
  n0.sv     OT_Q2NF_RW branch (right-width masters)
  nK.sv     mutants of the OT_Q2NF_RW branch, memory path only (see MUTS)
  tb.sv     testbench: old vs new in lock-step; EVERY output bit compared EVERY cycle (!==), and every one of the 14
            swapped macro sites' read data compared (old rd_out[W-1:0] vs new rd_out) every cycle; coverage counters per
            site: writes, reads, reads of an address written since reset (readback).
Pass criteria: n0 PASS with nonzero writes/reads/readback on every site class; every mutant FAIL.
"""
import re, sys, os
src, O = sys.argv[1], sys.argv[2]; os.makedirs(O, exist_ok=True)
s = open(src).read()
IF = re.compile(r"`ifdef OT_Q2NF_RW\n(.*?)`else\n(.*?)`endif\n", re.S)
assert len(IF.findall(s)) == 14
old = IF.sub(r"\2", s); new = IF.sub(r"\1", s)
old = re.sub(r"\bot_q2nf_rest_x\b", "old_ot_q2nf_rest_x", old).replace("module ot_q2nf_rest (", "module old_ot_q2nf_rest (")
open(O + "/old_w.sv", "w").write(old); open(O + "/n0.sv", "w").write(new)

# ---------------- sites ----------------
SITE = re.compile(r"^  (ot_sram_1r1w_\S+_r0c0_g(\d+)) (\\\S+)\s+\(\n(.*?)^  \);\n", re.M | re.S)
sites = [(m.group(3), int(m.group(2))) for m in SITE.finditer(new)]
assert len(sites) == 14, len(sites)


def inst(t, name):
    m = re.search(r"^  ot_sram_1r1w_\S+_r0c0_g\d+ " + re.escape(name) + r"\s+\(\n.*?^  \);\n", t, re.M | re.S); assert m, name; return m


def port(body, p):
    m = re.search(r"^    \." + p + r"\((.*)\),?$", body, re.M); assert m, p; return m


def setp(body, p, f):
    m = port(body, p); v = f(m.group(1)); assert v != m.group(1), p
    return body[:m.start(1)] + v + body[m.end(1):]


def bits(v):
    t = v.strip(); assert t[0] == "{" and t[-1] == "}"; return [x.strip() for x in t[1:-1].split(" , ")]


def cat(b): return "{ " + " , ".join(b) + " }"


def swap(i, j):  # i, j = bit indices (lsb = 0)
    def f(v):
        b = bits(v); n = len(b); b[n - 1 - i], b[n - 1 - j] = b[n - 1 - j], b[n - 1 - i]; return cat(b)
    return f


def flip(i):
    def f(v):
        b = bits(v); n = len(b); b[n - 1 - i] = "~" + b[n - 1 - i]; return cat(b)
    return f


def tie(i, c):
    def f(v):
        b = bits(v); n = len(b); b[n - 1 - i] = c; return cat(b)
    return f


L0B1 = r"\u_body.g_link[0].u_link.g_bank[1].u_store.u_native.u_sram"
L0B3 = r"\u_body.g_link[0].u_link.g_bank[3].u_store.u_native.u_sram"
L1B2 = r"\u_body.g_link[1].u_link.g_bank[2].u_store.u_native.u_sram"
I0H = r"\u_body.g_iss256.u_issuer.g_mem[0].u_bank.u_sram_hi"
I1L = r"\u_body.g_iss256.u_issuer.g_mem[1].u_bank.u_sram_lo"
I2H = r"\u_body.g_iss256.u_issuer.g_mem[2].u_bank.u_sram_hi"
I2L = r"\u_body.g_iss256.u_issuer.g_mem[2].u_bank.u_sram_lo"
MUTS = {
    1: ("link0 bank1 read address bit0 flipped", L0B1, "r_addr_in", flip(0)),
    2: ("link0 bank1 write mask 0 (write enable dead)", L0B1, "w_mask_in", lambda v: "1'h0"),
    3: ("issuer bank1 lo read data bits 0<->1 swapped", I1L, "rd_out", swap(0, 1)),
    4: ("link0 bank1 write data bits 0<->1 swapped", L0B1, "wd_in", swap(0, 1)),
    5: ("issuer bank1 lo write address bit0 flipped", I1L, "w_addr_in", flip(0)),
    6: ("issuer bank0 hi write enable tied 0", I0H, "w_ce_in", lambda v: "1'h0"),
    7: ("issuer bank2 hi read enable tied 0", I2H, "r_ce_in", lambda v: "1'h0"),
    8: ("link1 bank2 write data top bit 140 tied 0 (width edge)", L1B2, "wd_in", tie(140, "1'h0")),
    9: ("link0 bank3 read data bits 140<->139 swapped (width edge)", L0B3, "rd_out", swap(140, 139)),
    10: ("issuer bank2 lo read address bit7 flipped (row MSB)", I2L, "r_addr_in", flip(7)),
    11: ("link0 bank1 write address bit5 flipped (row MSB)", L0B1, "w_addr_in", flip(5)),
    12: ("issuer bank1 lo write data bits 254<->255 swapped (width edge)", I1L, "wd_in", swap(254, 255)),
}
with open(O + "/mutants.txt", "w") as fm:
    for k, (desc, name, p, f) in MUTS.items():
        m = inst(new, name); b = setp(m.group(0), p, f)
        open(f"{O}/n{k}.sv", "w").write(new[:m.start()] + b + new[m.end():])
        fm.write(f"m{k}\t{desc}\t{name}\t.{p}\n")

# ---------------- testbench ----------------
top = s[s.index("module ot_q2nf_rest ("):]; hdr = top[:top.index(");")]
ports = [(a, int(b or 0) + 1, c) for a, b, c in re.findall(r"^\s*(input|output)\s+wire\s+(?:\[(\d+):0\]\s+)?(\w+)\s*,?\s*$", hdr, re.M)]
assert len(ports) == hdr.count("input") + hdr.count("output")
ins = [p for p in ports if p[0] == "input"]; outs = [p for p in ports if p[0] == "output"]
clks = [p for p in ins if p[2].startswith("clk")]
CTRL = {"rst_n", "qid", "cfg_v", "cfg_target", "cfg_addr", "cfg_data", "desc_v", "desc_base", "desc_limit", "desc_loops", "launch_v"}
FAULTS = [p for p in ins if p[2].endswith("_fault")]
rnd = [p for p in ins if p not in clks and p[2] not in CTRL and p not in FAULTS]
L = ["`timescale 1ns/1ps", "module tb;", "  logic clk=0; always #1 clk=~clk;",
     "  logic rst_n=0; logic [1:0] qid=0; logic cfg_v=0; logic [7:0] cfg_target=0; logic [11:0] cfg_addr=0; logic [255:0] cfg_data=0;",
     "  logic desc_v=0; logic [11:0] desc_base=0; logic [12:0] desc_limit=0; logic [15:0] desc_loops=0; logic launch_v=0;"]
L += [f"  logic [{w-1}:0] i_{n} = 0;" for _, w, n in rnd + FAULTS] + [f"  wire [{w-1}:0] a_{n}, b_{n};" for _, w, n in outs]


def conn(pre):
    c = [f".{n}({{{w}{{clk}}}})" for _, w, n in clks] + [f".{n}({n})" for n in sorted(CTRL)]
    c += [f".{n}(i_{n})" for _, _, n in rnd + FAULTS] + [f".{n}({pre}_{n})" for _, _, n in outs]
    return ",\n    ".join(c)


L += ["  old_ot_q2nf_rest a(\n    " + conn("a") + ");", "  ot_q2nf_rest b(\n    " + conn("b") + ");"]
L += ["  integer rs = 1;", "  function automatic int unsigned ru(); ru = $random(rs); endfunction",
      "  integer mutcase=0; initial begin if (!$value$plusargs(\"MUT=%d\",mutcase))mutcase=0; end",
      "  initial begin if (!$value$plusargs(\"SEED=%d\", seed)) seed = 1; if (!$value$plusargs(\"NPROG=%d\", nprog)) nprog = 3; rs = seed * 7919 + 13; end"]
L += ["  integer cyc=0, errs=0, merrs=0, first_err=-1, first_merr=-1, mode=0, fmode=0, seed=1, nprog=3, nz=0;",
      "  integer rxen=0; integer prog_cfg=0, prog_fault=0, launches=0, dones=0;"]
# per-site coverage
for k, (name, w) in enumerate(sites):
    aw = 6 if w == 141 else 8
    A = f"a.u_x.{name} "; B = f"b.u_x.{name} "
    L += [f"  integer s{k}_w=0, s{k}_r=0, s{k}_rb=0, s{k}_mm=0; logic [{(1<<aw)-1}:0] s{k}_wr = 0; logic s{k}_rv = 0;",
          f"  always @(posedge clk) begin",
          f"    if (!rst_n) begin s{k}_wr <= 0; s{k}_rv <= 0; end else begin",
          f"      if ({B}.w_ce_in === 1'b1) begin s{k}_w = s{k}_w + 1; s{k}_wr[{B}.w_addr_in] <= 1'b1; end",
          f"      s{k}_rv <= ({B}.r_ce_in === 1'b1) && s{k}_wr[{B}.r_addr_in];",
          f"      if ({B}.r_ce_in === 1'b1) begin s{k}_r = s{k}_r + 1; if (s{k}_wr[{B}.r_addr_in]) s{k}_rb = s{k}_rb + 1; end",
          f"    end",
          f"  end",
          f"  always @(negedge clk) if (rst_n && ({A}.rd_out[{w-1}:0] !== {B}.rd_out)) begin s{k}_mm = s{k}_mm + 1; merrs = merrs + 1;"
          f" if (first_merr < 0) first_merr = cyc; end"]
for g in (0, 1):
    C = rf"b.u_x.\u_body.g_link[{g}].u_link.u_ctl.u"
    L += [f"  integer dbg{g}_wv=0, dbg{g}_eb=0, dbg{g}_ab=0, dbg{g}_ov=0, dbg{g}_miss=0, dbg{g}_extra=0, dbg{g}_pair=0;",
          f"  always @(posedge clk) if (rst_n) begin if ({C}.wr_observed_v_pin === 1'b1) dbg{g}_ov++; if ({C}.wr_v_pin && !{C}.wr_observed_v_pin)dbg{g}_miss++; if (!{C}.wr_v_pin && {C}.wr_observed_v_pin)dbg{g}_extra++; if ({C}.wr_v_pin && {C}.wr_observed_v_pin)dbg{g}_pair++; if ({C}.wr_v_pin  === 1'b1) dbg{g}_wv++; if ({C}.epoch_begin_pin  === 1'b1) dbg{g}_eb++; if ({C}.u_core.u_codec.epoch_abort  === 1'b1) dbg{g}_ab++; end"]
L += ["  // background inputs: random every cycle under 4 density modes (mode changes every 100 cycles); faults mostly 0",
      "  always @(negedge clk) begin",
      "    cyc <= cyc + 1;",
      "    if (cyc % 100 == 0) begin mode = ru() % 4; fmode = (ru() % 16 == 0); end"]
for _, w, n in rnd:
    if n == "rx_pin_v":
        L.append(f"    for (int k=0;k<{w};k+=1) i_{n}[k] = rxen ? 1'(ru()%4==0) : 1'b0;"); continue
    if n in ("phy_up", "rc_v", "u_body_g_qcap_8_u_cap_src_v"):
        L.append(f"    i_{n} = "+("\'1;" if n != "rc_v" else "\'0;")); continue
    L.append(f"    for (int k=0;k<{w};k+=1) i_{n}[k] = (mode==0)? 1'(ru()) : (mode==1)? 1'(ru()%4==0) : (mode==2)? 1'(ru()%4!=0) : 1'(ru()%16==0);")
for _, w, n in FAULTS:
    L.append(f"    for (int k=0;k<{w};k+=1) i_{n}[k] = 1'b0;")
L.append("    if (rst_n && (" + " || ".join(f"a_{n}!==b_{n}" for _, _, n in outs) + ")) begin errs++; if (first_err<0) first_err=cyc; if (errs<6) $display(\"MISMATCH cyc=%0d\", cyc); end")
L.append("    if (" + " || ".join(f"|b_{n}" for _, _, n in outs) + ") nz++;")
L += ["    if (b_program_configured && !a_program_configured) ; // compared above", "  end"]
L += ["  // ---- programme driver (F20 target 52+qid, ot_hgi_coll_static_program_target ROWS=256) ----",
      "  task automatic idle(input integer n); repeat (n) @(negedge clk); endtask",
      "  task automatic frame(input [11:0] addr, input [255:0] data);",
      "    @(negedge clk); cfg_v = 1; cfg_target = 8'd52 + qid; cfg_addr = addr; cfg_data = data;",
      "    @(negedge clk); cfg_v = 0; cfg_target = ru(); cfg_addr = ru(); cfg_data = {8{ru()}};",
      "  endtask",
      "  function automatic [255:0] rword(input integer dens);",
      "    logic [255:0] x; for (int k=0;k<256;k+=1) x[k] = (dens==0)? 1'(ru()) : (dens==1)? 1'(ru()%8==0) : (dens==2)? 1'(ru()%32==0) : 1'(ru()%4!=0);",
      "    return x;",
      "  endfunction",
      "  task automatic load_prog(input integer R, input integer dens);",
      "    logic [63:0] md; logic [1535:0] u; int ord[7]; int t, j, nx, tg;",
      "    for (int r=0; r<R; r+=1) begin",
      "      for (int k=0;k<7;k+=1) ord[k]=k;",
      "      for (int k=6;k>0;k-=1) begin j = ru() % (k+1); t = ord[k]; ord[k] = ord[j]; ord[j] = t; end",
      "      nx = r + 1; tg = ru() % (r + 1); md = 64'd0;",
      "      md[5:0] = nx[5:0]; md[51] = nx[6]; md[54] = nx[7]; md[11:6] = tg[5:0]; md[52] = tg[6]; md[55] = tg[7];",
      "      md[43:12] = 0;   // repeat: loop count 1..3 back to tg",
      "      md[49:45] = 0; md[44] = (r == R-1);           // halt on the last row",
      "      for (int k=0;k<6;k+=1) u[k*256+:256] = rword(dens);",
      "      // link fields (inst bit = uop_d1 bit, ot_hfd_coll_q_hard_v8g.sv:109): wr_v 350+k, rd_v 371+k, rx_expect 392+k, epoch_begin 413+k, epoch 423:416",
      "      u[0+:10]=0; u[10+:16]=0; u[26+:64]=0; for (int k=0;k<2;k+=1) begin u[10+k]=(r>=1 && r<=5); u[350+k]=(r>=3 && r<=7); u[371+k]=(r>=8); u[392+k]=0; u[413+k]=(r==0); end",
      "      if (r==0) u[423:416] = 8'(ru());",
      "      for (int k=0;k<7;k+=1) frame({1'b0, 8'(r), 3'(ord[k])}, ord[k]==6 ? {192'd0, md} : u[ord[k]*256+:256]);",
      "      idle(60);",
      "    end",
      "  endtask",
      "  initial begin",
      "    qid = ru() % 4;",
      "    for (int p=0; p<nprog; p+=1) begin",
      "      int R, dens; R = 12; dens = p % 4; rxen = (p % 4 == 3);",
      "      @(negedge clk); rst_n = 0; idle(10); rst_n = 1; idle(20);",
      "      load_prog(R, dens);",
      "      @(negedge clk); desc_v = 1; cfg_target = 8'd52 + qid; desc_base = 0; desc_limit = R; desc_loops = 1;",
      "      @(negedge clk); desc_v = 0; cfg_target = ru();",
      "      idle(300);",
      "      if (b_program_configured) prog_cfg++; if (b_program_fault) prog_fault++;",
      "      for (int l=0; l<1; l+=1) begin",
      "        @(negedge clk); launch_v = 1; @(negedge clk); launch_v = 0; launches++;",
      "        for (int w=0; w<160 && !b_done; w+=1) @(negedge clk);",
      "        if (b_done) dones++; idle(40);",
      "      end",
      "      $display(\"PROG %0d R=%0d dens=%0d configured=%b fault=%b done=%b cyc=%0d errs=%0d merrs=%0d\", p, R, dens, b_program_configured, b_program_fault, b_done, cyc, errs, merrs);",
      "    end",
      "    idle(50);"]
cov_w = " + ".join(f"s{k}_w" for k in range(14)); cov_r = " + ".join(f"s{k}_r" for k in range(14)); cov_rb = " + ".join(f"s{k}_rb" for k in range(14))
lk = [k for k, (n, w) in enumerate(sites) if w == 141]; ik = [k for k, (n, w) in enumerate(sites) if w == 256]
for k, (name, w) in enumerate(sites):
    L.append(f"    $display(\"SITE {k} {name.replace(chr(92), '')} w=%0d r=%0d readback=%0d rd_mismatch=%0d\", s{k}_w, s{k}_r, s{k}_rb, s{k}_mm);")
L.append("    $display(\"DBG link0 wr_v_pin=%0d epoch_begin=%0d abort_cycles=%0d link1 wr_v_pin=%0d epoch_begin=%0d abort_cycles=%0d\", dbg0_wv, dbg0_eb, dbg0_ab, dbg1_wv, dbg1_eb, dbg1_ab);")
L.append("    $display(\"Q2NF_RW88 LOCKSTEP %s seed=%0d qid=%0d cycles=%0d out_errs=%0d first_out_err=%0d mem_rd_mismatch=%0d first_mem_err=%0d "
         "link_writes=%0d link_readback=%0d issuer_writes=%0d issuer_reads=%0d issuer_readback=%0d progs_configured=%0d/%0d prog_fault=%0d launches=%0d dones=%0d nonzero=%0d\","
         " (errs||merrs)?\"FAIL\":\"PASS\", seed, qid, cyc, errs, first_err, merrs, first_merr, "
         + " + ".join(f"s{k}_w" for k in lk) + ", " + " + ".join(f"s{k}_rb" for k in lk) + ", "
         + " + ".join(f"s{k}_w" for k in ik) + ", " + " + ".join(f"s{k}_r" for k in ik) + ", " + " + ".join(f"s{k}_rb" for k in ik)
         + ", prog_cfg, nprog, prog_fault, launches, dones, nz);")
for g in (0,1):
    L.append(f"    $display(\"LINK_PROTOCOL g={g} wr=%0d observed=%0d missing=%0d extra=%0d paired=%0d abort=%0d\",dbg{g}_wv,dbg{g}_ov,dbg{g}_miss,dbg{g}_extra,dbg{g}_pair,dbg{g}_ab);")
coverage = " || ".join(f"s{k}_w==0 || s{k}_rb==0" for k in range(14))
L += [f"    if(mutcase==0 && ({coverage})) $fatal(1,\"BASELINE_MEMORY_COVERAGE_INCOMPLETE\");",
      "    if(mutcase==0 && (errs||merrs))$fatal(1,\"BASELINE_MISMATCH\");",
      "    if(mutcase!=0 && !(errs||merrs))$fatal(1,\"MUTANT_NOT_ACTIVATED\");",
      "    $display(\"MEMORY_CASE_ACCEPTED mut=%0d\",mutcase);", "    $finish;", "  end", "endmodule"]
open(O + "/tb.sv", "w").write("\n".join(L) + "\n")
print("sites", len(sites), "inputs", len(ins), "outputs", len(outs), "mutants", list(MUTS))
