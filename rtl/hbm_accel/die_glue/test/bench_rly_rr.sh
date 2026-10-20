#!/bin/bash
# Bit-exact + row-reset bench of one HBM die row-reset relay master hbfd_rly_<W>_<flow>_rr (Verilator 5.050).
#   usage: bench_rly_rr.sh <pass|mut|combmut|rr2mut> <master> <W> <work dir> [REL]
# HBM-RSTROW 2026-10-19 (coordinator 0jp Proposal A): the master = the ot_hbm_rly stage (unchanged) + rso, one row-reset
# flop (async clear by rs, release exactly 1 edge after rs).  The bench checks, on 20,000 random words with a mid-stream
# asynchronous clear (both releases checked):
#   words  (errors):     o = the previous cycle's i, REL-aware as bench_rly.sh (REL = 3 for a master whose stage goes
#                        through the registered reset relay: o stays 0 for the first REL edges after rs; random words
#                        also under both releases, >= REL in-window non-zero words must have been dropped);
#   rso    (rso_errors): rso = 0 while rs is low and immediately on the asynchronous assert; still 0 after rs rises and
#                        before the next posedge; 1 from the first posedge after rs (release exactly 1 edge after rs);
#   row    (row_errors): 4 instances chained as a relay row (o -> next i, rso -> next rs) fed at the head with rs: every
#                        station's o and rso against an exact cycle model; station k's rso releases k+1 edges after the
#                        head rs (both releases); the row output = the head input delayed 4 cycles once released.
# mut:     OT_HBM_RLY_MUT          (bit 0 of the stage register inverted)     -> FAIL (errors, row_errors)
# combmut: OT_HBM_RLY_RR_MUT_COMB  (rso = rs, no row-reset flop)              -> FAIL (rso_errors)
# rr2mut:  OT_HBM_RLY_RR_MUT_2     (two row-reset flops: release 2 edges)     -> FAIL (rso_errors)
set -u
mode=$1; M=$2; W=$3; O=$4; REL=${5:-0}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<'EOT'
module tb;
  localparam int W = @W@, REL = @REL@, N = 20000;
  reg ck = 0, rs = 0, rrs = 0;
  reg [W-1:0] i = 0, ri = 0;
  wire [W-1:0] o, o0, o1, o2, o3;
  wire rso, q0, q1, q2, q3;
  @M@ dut(.ck(ck), .rs(rs), .i(i), .o(o), .rso(rso));
  // the row: o -> next i, rso -> next rs; only the head takes the reset (rrs)
  @M@ s0(.ck(ck), .rs(rrs), .i(ri), .o(o0), .rso(q0));
  @M@ s1(.ck(ck), .rs(q0), .i(o0), .o(o1), .rso(q1));
  @M@ s2(.ck(ck), .rs(q1), .i(o1), .o(o2), .rso(q2));
  @M@ s3(.ck(ck), .rs(q2), .i(o2), .o(o3), .rso(q3));
  always #5 ck = ~ck;
  // single-instance model
  reg [W-1:0] ex = 0; reg sq = 0; integer scnt = 0;
  // row model: per station expected o / rso, edges seen with its rs high
  reg [W-1:0] mo [0:3]; reg mq [0:3]; integer mcnt [0:3]; integer rel_e [0:3];
  reg [W-1:0] hist [0:3];        // head input sampled at the last 4 edges (hist[j] = edge e - j)
  reg [W-1:0] ink; reg rsk;
  integer err = 0, rerr = 0, rowerr = 0, win = 0, rwin = 0, n = 0, k = 0, j = 0, e = 0, rels = 0, relchk = 0, dchk = 0;
  task row_reset_model;
    for (k = 0; k < 4; k = k + 1) begin mo[k] = '0; mq[k] = 1'b0; mcnt[k] = 0; rel_e[k] = -1; end
    e = 0; relchk = 0;
  endtask
  task row_zero_check;   // everything of the row cleared (asynchronously along the rso chain)
    if (o0 !== '0 || o1 !== '0 || o2 !== '0 || o3 !== '0) rowerr = rowerr + 1;
    if (q0 !== 1'b0 || q1 !== 1'b0 || q2 !== 1'b0 || q3 !== 1'b0) rowerr = rowerr + 1;
  endtask
  task check;            // at a negedge
    if (o !== ex) err = err + 1;
    if (rso !== sq) rerr = rerr + 1;
    if (o0 !== mo[0] || o1 !== mo[1] || o2 !== mo[2] || o3 !== mo[3]) rowerr = rowerr + 1;
    if (q0 !== mq[0] || q1 !== mq[1] || q2 !== mq[2] || q3 !== mq[3]) rowerr = rowerr + 1;
    if (rrs) begin
      if (q0 === 1'b1 && rel_e[0] < 0) rel_e[0] = e;
      if (q1 === 1'b1 && rel_e[1] < 0) rel_e[1] = e;
      if (q2 === 1'b1 && rel_e[2] < 0) rel_e[2] = e;
      if (q3 === 1'b1 && rel_e[3] < 0) rel_e[3] = e;
      // station k's rso releases exactly k+1 edges after the head rs
      if (e == 6 && !relchk) begin
        relchk = 1; rels = rels + 1;
        for (k = 0; k < 4; k = k + 1) if (rel_e[k] != k + 1) rowerr = rowerr + 1;
      end
      // once released: the row output is the head input delayed 4 cycles
      if (e >= REL + 4) begin dchk = dchk + 1; if (o3 !== hist[3]) rowerr = rowerr + 1; end
    end
  endtask
  task edge_update;      // the models at a posedge (inputs stable since the negedge)
    if (rs) begin
      scnt = scnt + 1; sq = 1'b1;
      if (scnt > REL) ex = i; else begin ex = '0; if (i !== '0) win = win + 1; end
    end
    // row model: descending so a station sees its upstream's values before this edge
    if (rrs) e = e + 1;
    for (k = 3; k >= 0; k = k - 1) begin
      rsk = (k == 0) ? rrs : mq[k - 1];
      ink = (k == 0) ? ri : mo[k - 1];
      if (rsk) begin
        mcnt[k] = mcnt[k] + 1; mq[k] = 1'b1;
        if (mcnt[k] > REL) mo[k] = ink; else begin mo[k] = '0; if (ink !== '0) rwin = rwin + 1; end
      end
    end
    for (j = 3; j > 0; j = j - 1) hist[j] = hist[j - 1];
    hist[0] = ri;
  endtask
  initial begin
    row_reset_model;
    for (j = 0; j < 4; j = j + 1) hist[j] = '0;
    repeat (3) @(negedge ck);
    if (o !== '0) err = err + 1;
    if (rso !== 1'b0) rerr = rerr + 1;
    row_zero_check;
    rs = 1; rrs = 1;
    #1 if (rso !== 1'b0) rerr = rerr + 1;          // no release before the first posedge after rs
    if (q0 !== 1'b0) rowerr = rowerr + 1;
    @(posedge ck); edge_update;                    // release edge 1 (inputs 0)
    for (n = 0; n < N; n = n + 1) begin
      @(negedge ck);
      check;
      if (n == 9000) begin
        // mid-stream asynchronous clear of the single instance and of the row head
        rs = 0; rrs = 0;
        #1 if (o !== '0) err = err + 1;
        if (rso !== 1'b0) rerr = rerr + 1;          // assert immediate
        row_zero_check;
        ex = '0; sq = 0; scnt = 0; row_reset_model;
        #1 rs = 1; rrs = 1;
        #1 if (rso !== 1'b0) rerr = rerr + 1;       // release not before the next posedge
        if (q0 !== 1'b0) rowerr = rowerr + 1;
      end
      for (int b = 0; b < W; b++) begin i[b] = $urandom; ri[b] = $urandom; end
      @(posedge ck);
      edge_update;
    end
    // non-vacuous: the stage release windows dropped real words (REL > 0), both row releases checked, delay checked
    if (win < REL) err = err + 1;
    if (rwin < REL || rels != 2 || dchk == 0) rowerr = rowerr + 1;
    $display("RLY_RR_BENCH %s %0d errors %0d rso_errors %0d row_errors in %0d words (%s W=%0d) release_edges=%0d window_words=%0d row_window_words=%0d row_releases=%0d delay4_checks=%0d",
             (err || rerr || rowerr) ? "FAIL" : "PASS", err, rerr, rowerr, n, "@M@", W, REL, win, rwin, rels, dchk);
    $finish;
  end
endmodule
EOT
sed -i "s/@M@/$M/g; s/@W@/$W/g; s/@REL@/$REL/g" "$O/tb.sv"
DEF=""
case "$mode" in
  pass) ;;
  mut) DEF="-DOT_HBM_RLY_MUT" ;;
  combmut) DEF="-DOT_HBM_RLY_RR_MUT_COMB" ;;
  rr2mut) DEF="-DOT_HBM_RLY_RR_MUT_2" ;;
  *) echo "bench_rly_rr.sh: unknown mode $mode"; exit 2 ;;
esac
verilator --version > "$O/build.log" 2>&1
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv \
  rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv >> "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
head -1 "$O/build.log"
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_RR_BENCH
grep -q 'RLY_RR_BENCH PASS' "$O/bench.log"
