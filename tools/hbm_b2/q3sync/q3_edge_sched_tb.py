#!/usr/bin/env python3
"""Realistic-schedule lockstep bench for the q3 EDGE core: legacy async-reset
ot_hfd_coll_q3_edge_core vs its mechanical __q3sync copy.

Why: the random-stimulus lockstep (q3_lockstep_tb.py) found 18 warm-reset diffs,
all on arg_out_flit with arg_out_v=0 or arg_fault=1.  Random stimulus faults the
ARGMAX at once, so it cannot show whether a stale non-reset datapath value
(amerge acca/acci, out_flit, captured) could ever be PUBLISHED under a legal
compiled schedule.  This bench drives the ARG pins with the compiled ARGMAX
schedule the HGI compiler emits (ot_hgi_coll_argmax_static contract, +1 edge
pin registers of ot_hgi_coll_argmax_m_tp192_pr):
  start pulse with cfg_g in {1,2,4,8,96,192}, gbase+g<=256, rank;
  lanes from start+2 on, in_slot == in_v (full 4-lane reservations, gaps allowed),
  each group source exactly once, meta = {1, 8'x, src, 16'h0};
  flush_slot on the last delivery cycle, publish_slot = flush + 6;
  next start no earlier than publish + GAP.
Warm resets are injected at controlled phases (mid-delivery, flush->publish,
on publish, after publish, idle, on start, and back-to-back reset) with random
hold; the run in flight is abandoned (the compiler re-issues it after reset)
and the first start after release waits >= POSTREL cycles.

Checks (every negedge outside reset windows, both cores):
  * every output except arg_out_flit bit-exact (FAIL otherwise);
  * arg_out_flit bit-exact whenever arg_out_v is 1 in either core (FAIL);
    a diff with arg_out_v=0 in both is counted as don't-care (consumer
    ot_hgi_coll_qslots_capture_pin_v2 samples it only on its compiled
    capture_slot, and faults if src_v != capture_slot);
  * arg_fault must stay 0 in both under the legal schedule (FAIL);
  * every arg_out_v=1 flit equals the independent golden
    {1, 8'hFF, rank, 16'h0, 480'h0, winner_id} (larger value first, -0==+0,
    NaN after numbers, ties -> lower id) (FAIL);
  * number of publishes == number of completed runs.
Plusargs: none. Defines: -DILLEGAL_EMPTY (negative control: one publish with no
deliveries after a warm reset -> must fault), golden mutant via
+define+OT_COLL_AMX_MUT_MIN on the RTL (both cores pick the min -> golden FAIL).
Usage: q3_edge_sched_tb.py <edge_core.sv> --out tb.sv [--runs N --seed S]
"""
import argparse, re

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--module", default="ot_hfd_coll_q3_edge_core")
ap.add_argument("--out", required=True)
ap.add_argument("--runs", type=int, default=400)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--hold0", type=int, default=64, help="cold reset cycles")
a = ap.parse_args()

txt = open(a.src).read()
m = re.search(r"module\s+" + re.escape(a.module) + r"\s*\((.*?)\);", txt, re.S)
ports = []
for pm in re.finditer(r"(input|output)\s+(?:wire|logic|reg)?\s*(\[\s*(\d+)\s*:\s*0\s*\])?\s*(\w+)", m.group(1)):
    ports.append((pm.group(1), int(pm.group(3)) + 1 if pm.group(3) else 1, pm.group(4)))
names = [p[2] for p in ports]
ARG_IN = {"arg_start", "arg_mode", "arg_cfg_g", "arg_cfg_gbase", "arg_cfg_rank", "arg_in_slot", "arg_in_v",
          "arg_in_key", "arg_in_meta", "arg_flush_slot", "arg_publish_slot"}
for n in ARG_IN | {"arg_clk", "arg_rst_n", "arg_out_v", "arg_out_flit", "arg_fault"}:
    assert n in names, n
isclk = lambda n: re.search(r"(^|_)(clk|ck)(_|$|\d)", n) is not None
isrst = lambda n: "rst" in n
outs = [(w, n) for d, w, n in ports if d == "output"]

L = []
P = L.append
P("`timescale 1ns/1ps")
P("module tb;")
P("  reg clk = 0; reg rst_n = 0; integer cyc = 0;")
P("  always #1 clk = ~clk;")
for d, w, n in ports:
    if d == "input" and not isclk(n) and not isrst(n):
        P("  reg [%d:0] i_%s = 0;" % (w - 1, n))
for w, n in outs:
    P("  wire [%d:0] o_%s_L, o_%s_S;" % (w - 1, n, n))
for suf, mod in (("L", a.module), ("S", a.module + "__q3sync")):
    conns = []
    for d, w, n in ports:
        if d == "input":
            e = ("{%d{clk}}" % w) if isclk(n) else ("{%d{rst_n}}" % w) if isrst(n) else "i_" + n
        else:
            e = "o_%s_%s" % (n, suf)
        conns.append("    .%s(%s)" % (n, e))
    P("  %s u_%s (\n%s);" % (mod, suf, ",\n".join(conns)))
P(r"""
  // ---------------- independent golden order (HGI machine.py lexsort(ids, -value)) -------------
  function automatic is_nan(input [31:0] v); is_nan = (v[30:23] == 8'hFF) && (v[22:0] != 0); endfunction
  // signed-magnitude -> monotone; -0 and +0 equal
  function automatic [32:0] mono(input [31:0] v);
    if (v[30:0] == 0) mono = 33'h1_0000_0000;
    else if (v[31]) mono = 33'h1_0000_0000 - {2'b0, v[30:0]};
    else mono = 33'h1_0000_0000 + {2'b0, v[30:0]};
  endfunction
  function automatic beats(input [31:0] a, input [31:0] ai, input [31:0] b, input [31:0] bi); // a strictly first
    if (is_nan(a) != is_nan(b)) beats = is_nan(b);
    else if (is_nan(a)) beats = ai < bi;
    else if (mono(a) != mono(b)) beats = mono(a) > mono(b);
    else beats = ai < bi;
  endfunction
  function automatic [31:0] pick_val(input integer r);
    reg [31:0] p [0:7];
    p[0]=32'h0000_0000; p[1]=32'h8000_0000; p[2]=32'h7FC0_0001; p[3]=32'hFF80_0000;
    p[4]=32'h7F80_0000; p[5]=32'h3F80_0000; p[6]=32'hBF80_0000; p[7]=32'h7FFF_FFFF;
    case (r) 0,1: pick_val = $urandom; 2: pick_val = p[$urandom % 8]; default: pick_val = {1'b0, 8'h7E, 23'($urandom % 4)}; endcase
  endfunction

  // ---------------- schedule state --------------------------------------------------------------
  localparam integer S_GAP=0, S_START=1, S_WAIT=2, S_DLV=3, S_PUB=4;
  integer st = S_GAP, gap = 8, remaining = 0, pubcnt = 0, runs_done = 0, runs_started = 0, aborted = 0;
  integer g, gbase, rank_r, k, l, nl, idx;
  reg [7:0] perm [0:255];
  reg [31:0] best_v, best_i; reg best_ok;
  // expected publications (in order)
  reg [31:0] exp_id [0:4095]; reg [7:0] exp_rank [0:4095]; integer exp_wr = 0, exp_rd = 0;
  // reset control
  integer rst_left = 0, postrel = 0, nreset = 0, phase_target = 0, next_reset_run = 3;
  reg pending_reset = 0;
  integer seed_dummy;
  integer mism = 0, dontcare = 0, dontcare_v0f1 = 0, cmpc = 0, gold_ok = 0, gold_bad = 0, fault_seen = 0, rmism = 0;
  integer illegal_done = 0; integer relc = 0; integer sel_idx = 0; integer since_pub = 1000, pend_age = 0; integer phase_hits [0:8];
  initial for (int q = 0; q < 9; q++) phase_hits[q] = 0;
  reg [31:0] vv, ii;
  initial seed_dummy = $urandom(%SEED%);
  function automatic [4095:0] rnd(input integer w); integer q; begin rnd = 0; for (q = 0; q < 4096; q = q + 32) rnd[q +: 32] = $urandom; end endfunction

  task automatic do_reset(input integer hold);
    begin rst_left = hold; nreset = nreset + 1; phase_hits[phase_target] = phase_hits[phase_target] + 1; aborted = aborted + ((st == S_GAP) ? 0 : 1);
      // the run in flight is abandoned; nothing of it may be published
      aborted = aborted + (exp_wr - exp_rd); runs_done = runs_done - (exp_wr - exp_rd); exp_wr = exp_rd; st = S_GAP; gap = 0; pending_reset = 0;
      $display("WARM_RESET n=%0d cyc=%0d phase_target=%0d hold=%0d", nreset, cyc, phase_target, hold); end
  endtask

  wire in_rst = !rst_n;
  always @(negedge clk) begin
    cyc <= cyc + 1;
    since_pub = since_pub + 1;
    if (pending_reset) begin pend_age = pend_age + 1; if (pend_age > 3000) begin $display("EDGE_SCHED FAIL phase %0d never reached", phase_target); $finish; end end
    // ---- compare (outputs of the previous edge; before this cycle's schedule/reset decisions) ----
    if (in_rst) begin
      if ({%OUTS_L%} !== {%OUTS_S%}) rmism = rmism + 1;
    end else begin
      cmpc = cmpc + 1;
%NONFLIT%
      if (o_arg_out_flit_L !== o_arg_out_flit_S) begin
        if (o_arg_out_v_L || o_arg_out_v_S) begin mism = mism + 1; if (mism < 20) $display("MISMATCH_PUBLISHED cyc=%0d arg_out_flit", cyc); end
        else begin dontcare = dontcare + 1; if (o_arg_fault_L) dontcare_v0f1 = dontcare_v0f1 + 1; if (dontcare < 40) $display("DONTCARE cyc=%0d arg_out_flit v=0 fault=%0d nreset=%0d", cyc, o_arg_fault_L, nreset); end
      end
      if (o_arg_fault_L || o_arg_fault_S) begin fault_seen = fault_seen + 1; if (fault_seen < 5) $display("FAULT cyc=%0d L=%0d S=%0d", cyc, o_arg_fault_L, o_arg_fault_S); end
      if (o_arg_out_v_L) begin
        if (exp_rd >= exp_wr) begin gold_bad = gold_bad + 1; if (gold_bad < 10) $display("GOLDEN_UNEXPECTED_PUBLISH cyc=%0d id=%h", cyc, o_arg_out_flit_L[31:0]); end
        else begin
          if (o_arg_out_flit_L === {1'b1, 8'hFF, exp_rank[exp_rd %% 4096], 16'h0, 480'h0, exp_id[exp_rd %% 4096]} &&
              o_arg_out_flit_S === o_arg_out_flit_L) gold_ok = gold_ok + 1;
          else begin gold_bad = gold_bad + 1; if (gold_bad < 10) $display("GOLDEN_MISMATCH cyc=%0d got=%h exp=%h", cyc, o_arg_out_flit_L[31:0], exp_id[exp_rd %% 4096]); end
          exp_rd = exp_rd + 1;
        end
      end
    end
    // ---- link pins: identical random traffic to both cores (link lockstep already PASS) ----
""".replace("%SEED%", str(a.seed)))
for d, w, n in ports:
    if d == "input" and not isclk(n) and not isrst(n) and n not in ARG_IN:
        P("    i_%s <= %s;" % (n, "(($urandom % 4) == 0)" if w == 1 else "rnd(%d)" % w))
P(r"""
    // ---- ARG pins: compiled schedule ----
    i_arg_mode <= 1; i_arg_start <= 0; i_arg_in_v <= 0; i_arg_in_slot <= 0; i_arg_flush_slot <= 0; i_arg_publish_slot <= 0;
    i_arg_in_key <= rnd(256); i_arg_in_meta <= rnd(132);   // lane payload is don't-care when its lane is idle
    if (cyc < %HOLD0%) rst_n <= 0;
    else if (rst_left > 0) begin rst_n <= 0; relc = 0; rst_left = rst_left - 1; if (rst_left == 0) postrel = 6 + ($urandom % 4); end
    else begin
      rst_n <= 1; relc = relc + 1;
      if (pending_reset && phase_target == 7 && relc >= 2) begin
        // back-to-back: second reset in the first cycle after release (inside the post-release wait)
        do_reset(1 + ($urandom % 3));
        rst_n <= 0; relc = 0; rst_left = rst_left - 1; if (rst_left == 0) postrel = 6 + ($urandom % 4);
      end
      else if (postrel > 0) postrel = postrel - 1;
      else if (pending_reset && (
            (phase_target == 0 && st == S_DLV && remaining > 1) ||
            (phase_target == 1 && st == S_PUB && gap >= 2) ||
            (phase_target == 2 && st == S_PUB && gap == 1) ||   // reset replaces the publish-pin cycle
            (phase_target == 3 && since_pub == 1) ||              // publish in the pin register
            (phase_target == 8 && since_pub == 2) ||              // publish in the fold / out_v register

            (phase_target == 4 && st == S_GAP && gap >= 3) ||
            (phase_target == 5 && st == S_WAIT) ||                  // start in the pin / START_REG registers
            (phase_target == 6 && st == S_GAP))) begin
        // phase 6 = back-to-back: very short hold, then another reset right after release
        do_reset(phase_target == 6 ? 1 + ($urandom % 3) : 3 + ($urandom % 40));
        rst_n <= 0; relc = 0; rst_left = rst_left - 1; if (rst_left == 0) postrel = 6 + ($urandom % 4);
        if (phase_target == 6) begin pending_reset = 1; phase_target = 7; end
      end else begin
        case (st)
          S_GAP: if (gap > 0) gap = gap - 1; else if (runs_started < %RUNS%) st = S_START;
          default: ;
        endcase
        case (st)
          S_START: begin
`ifdef ILLEGAL_EMPTY
            if (nreset == 1 && !illegal_done) begin
              // negative control: publish a run that received no lane (illegal schedule)
              illegal_done = 1; i_arg_start <= 1; i_arg_cfg_g <= 1; i_arg_cfg_gbase <= 0; i_arg_cfg_rank <= 8'h5A;
              st = S_PUB; gap = 9; remaining = -1;
            end else
`endif
            begin
            case ($urandom % 10) 0: g = 1; 1: g = 2; 2,3: g = 4; 4,5: g = 8; 6,7: g = 96; default: g = 192; endcase
            gbase = $urandom % (257 - g); rank_r = $urandom % 256;
            for (k = 0; k < g; k = k + 1) perm[k] = 8'(gbase + k);
            for (k = g - 1; k > 0; k = k - 1) begin idx = $urandom % (k + 1); {perm[k], perm[idx]} = {perm[idx], perm[k]}; end
            i_arg_start <= 1; i_arg_cfg_g <= 8'(g); i_arg_cfg_gbase <= 8'(gbase); i_arg_cfg_rank <= 8'(rank_r);
            best_ok = 0; remaining = g; st = S_WAIT; runs_started = runs_started + 1;
            if (runs_started >= next_reset_run && !pending_reset) begin pending_reset = 1; phase_target = (sel_idx %% 8 == 7) ? 8 : (sel_idx %% 8); sel_idx = sel_idx + 1; pend_age = 0; next_reset_run = runs_started + 2 + ($urandom % 6); end
            end
          end
          S_WAIT: st = S_DLV;     // lanes no earlier than start + 2 (start pin -> start_qq is 2 edges, lanes 1 edge)
          S_DLV: begin
            if (($urandom % 4) == 0) ;   // compiled bubble: no reservation this cycle
            else begin
              nl = 1 + ($urandom % 4); if (nl > remaining) nl = remaining;
              begin : lanes
                reg [3:0] msk; reg [255:0] key; reg [131:0] meta; integer c;
                msk = 0; key = rnd(256); meta = rnd(132); c = 0;
                while (c < nl) begin l = $urandom % 4; if (!msk[l]) begin msk[l] = 1; c = c + 1; end end
                for (l = 0; l < 4; l = l + 1) if (msk[l]) begin
                  remaining = remaining - 1;
                  vv = pick_val($urandom % 4); ii = $urandom % 64;   // narrow ids -> ties on equal values
                  ii = {ii[5:0], 18'($urandom), perm[remaining]};  // unique id (low byte = unique src)
                  key[l*64 +: 64] = {ii, vv};
                  meta[l*33 +: 33] = {1'b1, 8'($urandom), perm[remaining], 16'h0};
                  if (!best_ok || beats(vv, ii, best_v, best_i)) begin best_v = vv; best_i = ii; best_ok = 1; end
                end
                i_arg_in_v <= msk; i_arg_in_slot <= msk; i_arg_in_key <= key; i_arg_in_meta <= meta;
              end
              if (remaining == 0) begin i_arg_flush_slot <= 1; st = S_PUB; gap = 6; end
            end
          end
          S_PUB: begin
            if (gap > 0) gap = gap - 1;
            if (gap == 0) begin
              i_arg_publish_slot <= 1; since_pub = 0;
              if (remaining == 0) begin exp_id[exp_wr %% 4096] = best_i; exp_rank[exp_wr %% 4096] = 8'(rank_r); exp_wr = exp_wr + 1; runs_done = runs_done + 1; end
              st = S_GAP; gap = 1 + ($urandom % 5);
            end
          end
          default: ;
        endcase
      end
    end
    if (runs_started >= %RUNS% && st == S_GAP && gap == 0 && rst_left == 0 && postrel == 0 && cyc > 50) begin : fin
      integer pend; pend = exp_wr - exp_rd;
      if (pend == 0 || cyc > 2000000) begin
        $display("EDGE_SCHED runs_started=%0d runs_published=%0d aborted_by_reset=%0d warm_resets=%0d compared=%0d mismatches=%0d dontcare_flit_v0=%0d (of which fault=1: %0d) golden_ok=%0d golden_bad=%0d fault_cycles=%0d in_reset_diff=%0d pending=%0d",
                 runs_started, runs_done, aborted, nreset, cmpc, mism, dontcare, dontcare_v0f1, gold_ok, gold_bad, fault_seen, rmism, pend);
        $display("EDGE_SCHED warm_reset_phase_hits dlv=%0d flush_pub=%0d on_pub=%0d pub+1=%0d idle=%0d on_start=%0d b2b_first=%0d b2b_second=%0d pub+2=%0d",
                 phase_hits[0], phase_hits[1], phase_hits[2], phase_hits[3], phase_hits[4], phase_hits[5], phase_hits[6], phase_hits[7], phase_hits[8]);
        if (mism == 0 && gold_bad == 0 && fault_seen == 0 && gold_ok == runs_done && pend == 0) $display("EDGE_SCHED PASS");
        else $display("EDGE_SCHED FAIL");
        $finish;
      end
    end
  end
endmodule
""".replace("%HOLD0%", str(a.hold0)).replace("%RUNS%", str(a.runs))
  .replace("%OUTS_L%", ",".join("o_%s_L" % n for w, n in outs))
  .replace("%OUTS_S%", ",".join("o_%s_S" % n for w, n in outs))
  .replace("%NONFLIT%", "\n".join(
      "      if (o_%s_L !== o_%s_S) begin mism = mism + 1; if (mism < 20) $display(\"MISMATCH cyc=%%0d %s\", cyc); end" % (n, n, n)
      for w, n in outs if n != "arg_out_flit"))
  .replace("%%", "%"))
open(a.out, "w").write("\n".join(L) + "\n")
print("ports", len(ports), "outputs", len(outs))
