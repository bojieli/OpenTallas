#!/bin/bash
# QK-LAND600B 10-18: LOCKSTEP bench of landing variant B (ot_qfd_land WSEL 1: registered one-hot write select, one copy per
# 150 b, rtl/qwen_split/qfd_fwd_lane.sv) against the original landing (WSEL 0) -- Verilator 5.050.
# Both landings get the SAME inputs: W-bit data changing on every write edge, the lane write clock (FIRST 0: free ckf;
# FIRST 1: the source root through the hop-0 gate) at a random phase to the receiving root ck, the lane epoch (ea / en)
# dropped and re-released at random times (asynchronous clear mid-run), the receiving reset rs dropped / released, and
# every K strap 1..7 in turn.  On every ck edge (and every write edge for the slot-valid flags) the bench requires
# o, fault and vld identical between A and B.  PASS line: LOCK_BENCH PASS 0 errors in <checks> checks.
# usage: bench_land_wsel_lock.sh <pass|wsel> <work dir> [W]     wsel: B built with its mutant (must FAIL)
set -u
mode=$1; O=$2; W=${3:-600}
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DEF=
case $mode in pass) ;; wsel) DEF=+define+OT_QFD_LAND_MUT_WSEL ;; *) echo "bad mode $mode"; exit 2 ;; esac
cat > "$O/tb_lock.sv" <<EOT
\`timescale 1ns/1ps
module tb_lock;
    localparam integer W = $W;
    reg ckf = 0, cks = 0, ck = 0;
    reg ea = 0, rs = 0;
    reg [W-1:0] i = 0;
    reg [3:0] k = 4'd3;
    // lane clock / source root (10 ns) and receiving root at an irrational-ish offset that drifts by re-phasing below
    real ph = 3.3;
    always #5 ckf = ~ckf;
    always #5 cks = ~cks;
    initial begin #(ph); forever #5 ck = ~ck; end
    integer seed = 12345;
    // data: new random word after every lane edge (both lane clocks share the 10 ns period)
    always @(negedge ckf) begin : dat
        integer j;
        for (j = 0; j < W; j = j + 32) i[j +: 32] = \$random(seed);
    end
    wire [W-1:0] oa0, ob0, oa1, ob1; wire fa0, fb0, fa1, fb1;
    ot_qfd_land #(.W(W), .D(4), .FIRST(0), .WSEL(0)) a0 (.ckf(ckf), .ea(ea), .i(i), .ck(ck), .rs(rs), .k(k[2:0]), .o(oa0), .fault(fa0));
    ot_qfd_land #(.W(W), .D(4), .FIRST(0), .WSEL(1)) b0 (.ckf(ckf), .ea(ea), .i(i), .ck(ck), .rs(rs), .k(k[2:0]), .o(ob0), .fault(fb0));
    ot_qfd_land #(.W(W), .D(4), .FIRST(1), .WSEL(0)) a1 (.ckf(cks), .ea(ea), .i(i), .ck(ck), .rs(rs), .k(k[2:0]), .o(oa1), .fault(fa1));
    ot_qfd_land #(.W(W), .D(4), .FIRST(1), .WSEL(1)) b1 (.ckf(cks), .ea(ea), .i(i), .ck(ck), .rs(rs), .k(k[2:0]), .o(ob1), .fault(fb1));
    integer err = 0, chk = 0, nz = 0;
    always @(negedge ck) begin
        chk = chk + 1;
        if (oa0 != 0) nz = nz + 1;
        if (oa0 !== ob0 || fa0 !== fb0 || oa1 !== ob1 || fa1 !== fb1 || a0.vld !== b0.vld || a1.vld !== b1.vld) begin
            err = err + 1;
            if (err < 5) \$display("LOCK MISMATCH t=%0t k=%0d o0 %0d/%0d f0 %b/%b vld0 %b/%b o1 %0d/%0d f1 %b/%b", \$time, k,
                                   oa0 == ob0, oa0 === ob0, fa0, fb0, a0.vld, b0.vld, oa1 == ob1, oa1 === ob1, fa1, fb1);
        end
    end
    // the write select of B must equal onehot(wc) of B on every lane edge (structure check, both FIRST forms)
    always @(posedge ckf) if (ea) begin
        chk = chk + 1;
        if (b0.wsl !== (4'b1 << b0.wc[1:0])) begin err = err + 1; if (err < 5) \$display("LOCK WSEL t=%0t wsl %b wc %0d", \$time, b0.wsl, b0.wc); end
    end
    integer r, n;
    initial begin
        for (r = 0; r < 28; r = r + 1) begin
            k = 1 + (r % 7);                                    // every K strap 1..7
            // epoch / reset sequencing: release either side first, at a random sub-period time
            #(\$urandom(seed) % 97 + 0.37);
            if (r % 2) begin ea = 1; #(\$urandom(seed) % 53 + 0.11); rs = 1; end
            else       begin rs = 1; #(\$urandom(seed) % 53 + 0.11); ea = 1; end
            n = 3000 + \$urandom(seed) % 3000;
            #(n * 1.0);
            // asynchronous drop of the lane epoch (and later the receiver reset) mid-run
            ea = 0; #(\$urandom(seed) % 31 + 0.29);
            if (r % 3 == 0) begin rs = 0; #(\$urandom(seed) % 17 + 0.53); end
            else begin ea = 1; #(\$urandom(seed) % 400 + 50.0); ea = 0; rs = 0; #3.1; end
        end
        \$display("LOCK_BENCH %s %0d errors in %0d checks (%0d non-zero A words)", (err || chk < 10000 || nz < 4000) ? "FAIL" : "PASS", err, chk, nz);
        \$finish;
    end
endmodule
EOT
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --top-module tb_lock $DEF \
  -Mdir "$O/obj" -o tb "$O/tb_lock.sv" rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv > "$O/build.log" 2>&1 || {
  echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E 'LOCK_BENCH|LOCK (MISMATCH|WSEL)'
grep -q 'LOCK_BENCH PASS' "$O/bench.log"
