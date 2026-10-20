#!/bin/bash
# Station-hosted reset-forest carrier bench (L2H-RSTFB 10-19, Verilator 5.050) for hbfd_rly_<W>_<flow>_rfc / _rrfc.
#   usage: bench_rly_rfc.sh <pass|land1mut|combmut|nogatemut|datamut> <master> <W> <work dir> [REL] [RR 0|1] [TRIALS]
# NS = 6 instances of <master> are chained as a hosted forest path (rfi of station k = rfo of station k-1, head rfi driven
# by the bench); every station also carries its own random data stream (o = previous i, REL-aware as bench_rly.sh) and, for
# _rrfc (RR=1), the row-reset rso (release exactly 1 edge after rs).  Checks against an exact edge model:
#   rfc_errors   : every rfo against the model (2 landing flops async-cleared by rfi, q sync-cleared while land[1] low,
#                  rfo = land[1] & q) at every negedge and 1 ns after every head change;
#   assert_errors: 1 ns after the head rfi falls (sub-cycle, no clock edge in between) EVERY rfo of the chain is 0;
#   age_errors   : after each held release, station k (1..NS) first shows rfo = 1 exactly 3k edges after the head rise
#                  (fixed release age 3 per hosted carrier stage);
#   errors / rso_errors: the station's data stage and row reset are unchanged and independent of rfi (trial 0 runs the
#                  whole chain release with rs LOW; rs is cleared and re-released mid-stream; rfi pulses never touch o).
# Trials: random head assertions at random sub-cycle offsets, held low 0 (a 2 ns glitch) .. 8 cycles, then held high
# either long enough for a full age check (3*NS + 4 edges) or a random short time (re-assertion during the release).
# Mutants (expected FAIL):  land1mut OT_HBM_RLY_RFC_MUT_1LAND (age 2)  combmut OT_HBM_RLY_RFC_MUT_COMB (age 0)
#                           nogatemut OT_HBM_RLY_RFC_MUT_NOGATE (assertion waits for a clock edge)
#                           datamut OT_HBM_RLY_MUT (stage bit 0 inverted: data path check is live)
set -u
mode=$1; M=$2; W=$3; O=$4; REL=${5:-0}; RR=${6:-0}; TRIALS=${7:-400}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
if [ "$RR" = 1 ]; then RSO_PORT=", .rso(rso[k])"; else RSO_PORT=""; fi
cat > "$O/tb.sv" <<'EOT'
`timescale 1ns/1ps
module tb;
  localparam int W = @W@, REL = @REL@, RR = @RR@, NS = 6, T = @TRIALS@;
  reg ck = 0, rs = 0, hrf = 0;
  reg  [W-1:0] i [0:NS-1];
  wire [W-1:0] o [0:NS-1];
  wire [NS-1:0] rso, rfo;
  wire [NS-1:0] rfi = {rfo[NS-2:0], hrf};
  genvar k;
  generate for (k = 0; k < NS; k = k + 1) begin : g_st
    @M@ dut(.ck(ck), .rs(rs), .i(i[k]), .o(o[k])@RSO@, .rfi(rfi[k]), .rfo(rfo[k]));
  end endgenerate
  always #5 ck = ~ck;
  // exact model
  reg [W-1:0] ex [0:NS-1]; reg sq; integer scnt;
  reg ml0 [0:NS-1]; reg ml1 [0:NS-1]; reg mq [0:NS-1]; reg mrfo [0:NS-1];
  reg n0 [0:NS-1]; reg n1 [0:NS-1]; reg nq [0:NS-1]; reg ri;
  integer err = 0, rerr = 0, ferr = 0, aerr = 0, gerr = 0, win = 0, j = 0, t = 0, lo = 0, hi = 0, e = 0, ages = 0;
  integer first [0:NS-1];
  integer rel_count = 0;   // posedges since the last head rise (head high throughout)
  task settle;             // asynchronous clears along the chain
    for (j = 0; j < NS; j = j + 1) begin
      ri = (j == 0) ? hrf : mrfo[j - 1];
      if (!ri) begin ml0[j] = 1'b0; ml1[j] = 1'b0; end
      mrfo[j] = ml1[j] & mq[j];
    end
  endtask
  task edge_model;         // at a posedge, from the pre-edge values
    for (j = 0; j < NS; j = j + 1) begin
      ri = (j == 0) ? hrf : mrfo[j - 1];
      n0[j] = ri; n1[j] = ri ? ml0[j] : 1'b0; nq[j] = ml1[j];
    end
    for (j = 0; j < NS; j = j + 1) begin ml0[j] = n0[j]; ml1[j] = n1[j]; mq[j] = nq[j]; end
    settle;
    if (rs) begin
      scnt = scnt + 1; sq = 1'b1;
      for (j = 0; j < NS; j = j + 1)
        if (scnt > REL) ex[j] = i[j]; else begin if (i[j] !== '0) win = win + 1; ex[j] = '0; end
    end
    if (hrf) rel_count = rel_count + 1;
  endtask
  task cmp_rfc;
    for (j = 0; j < NS; j = j + 1) if (rfo[j] !== mrfo[j]) ferr = ferr + 1;
  endtask
  task check;              // at a negedge
    cmp_rfc;
    for (j = 0; j < NS; j = j + 1) begin
      if (o[j] !== ex[j]) err = err + 1;
      if (RR && rso[j] !== sq) rerr = rerr + 1;
      if (hrf && rfo[j] === 1'b1 && first[j] < 0) first[j] = rel_count;
    end
  endtask
  task new_data;
    for (j = 0; j < NS; j = j + 1) for (int b = 0; b < W; b++) i[j][b] = $urandom;
  endtask
  task cycle;              // negedge -> new data -> posedge (model) -> negedge (check)
    new_data;
    @(posedge ck); edge_model;
    @(negedge ck); check;
  endtask
  task head_fall;          // sub-cycle assertion (between edges)
    #($urandom_range(1, 2)) hrf = 0;
    #0.5 settle;
    #0.5 cmp_rfc;
    for (j = 0; j < NS; j = j + 1) if (rfo[j] !== 1'b0) aerr = aerr + 1;
  endtask
  task head_rise;
    #1 hrf = 1; settle; rel_count = 0;
    for (j = 0; j < NS; j = j + 1) first[j] = -1;
    #0.5 cmp_rfc;
    for (j = 0; j < NS; j = j + 1) if (rfo[j] !== 1'b0) gerr = gerr + 1;   // no release before an edge
  endtask
  task age_check;
    ages = ages + 1;
    for (j = 0; j < NS; j = j + 1) if (first[j] != 3 * (j + 1)) begin
      gerr = gerr + 1;
      if (gerr < 6) $display("AGE station %0d released after %0d edges (expected %0d)", j + 1, first[j], 3 * (j + 1));
    end
  endtask
  initial begin
    for (j = 0; j < NS; j = j + 1) begin ex[j] = '0; ml0[j] = 0; ml1[j] = 0; mq[j] = 0; mrfo[j] = 0; i[j] = '0; first[j] = -1; end
    sq = 0; scnt = 0;
    repeat (2) @(negedge ck);
    check;
    // trial 0: the whole chain releases with the station data reset rs LOW (independence)
    head_rise;
    repeat (3 * NS + 4) cycle;
    age_check;
    rs = 1;
    for (t = 0; t < T; t = t + 1) begin
      repeat ($urandom_range(0, 3)) cycle;
      if (t == T / 2) begin          // mid-stream asynchronous clear of the data stages (at a negedge), re-release
        rs = 0; #0.5;
        for (j = 0; j < NS; j = j + 1) begin ex[j] = '0; if (o[j] !== '0) err = err + 1; if (RR && rso[j] !== 1'b0) rerr = rerr + 1; end
        sq = 0; scnt = 0;
        #0.5 rs = 1;
        cmp_rfc;                     // the carrier chain is untouched by rs
        cycle;
      end
      head_fall;
      lo = $urandom_range(0, 8);
      if (lo == 0) begin
        head_rise;                   // 2 ns glitch, no edge while low
      end else begin
        repeat (lo) cycle;
        head_rise;
      end
      if ($urandom_range(0, 2) != 0) begin
        repeat (3 * NS + 4) cycle;
        age_check;
      end else begin
        repeat ($urandom_range(1, 3 * NS)) cycle;   // re-assert during the release
      end
    end
    repeat (4) cycle;
    if (win < REL) err = err + 1;
    $display("RLY_RFC_BENCH %s %0d errors %0d rso_errors %0d rfc_errors %0d assert_errors %0d age_errors trials=%0d ages_checked=%0d (%s W=%0d) rfc_age=3 release_edges=%0d window_words=%0d",
             (err || rerr || ferr || aerr || gerr) ? "FAIL" : "PASS", err, rerr, ferr, aerr, gerr, T + 1, ages, "@M@", W, REL, win);
    $finish;
  end
endmodule
EOT
sed -i "s/@M@/$M/g; s/@W@/$W/g; s/@REL@/$REL/g; s/@RR@/$RR/g; s/@TRIALS@/$TRIALS/g; s/@RSO@/$RSO_PORT/g" "$O/tb.sv"
DEF=""
case "$mode" in
  pass) ;;
  land1mut) DEF="-DOT_HBM_RLY_RFC_MUT_1LAND" ;;
  combmut) DEF="-DOT_HBM_RLY_RFC_MUT_COMB" ;;
  nogatemut) DEF="-DOT_HBM_RLY_RFC_MUT_NOGATE" ;;
  datamut) DEF="-DOT_HBM_RLY_MUT" ;;
  *) echo "bench_rly_rfc.sh: unknown mode $mode"; exit 2 ;;
esac
verilator --version > "$O/build.log" 2>&1
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv \
  rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv >> "$O/build.log" 2>&1 \
  || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
head -1 "$O/build.log"
"$O/obj/tb" | tee "$O/bench.log" | grep -E 'RLY_RFC_BENCH|^AGE'
grep -q 'RLY_RFC_BENCH PASS' "$O/bench.log"
