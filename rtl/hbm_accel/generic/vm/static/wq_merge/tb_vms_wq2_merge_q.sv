`timescale 1ns/1ps
`default_nettype none
// HBM-P4-QUANT 2026-10-23 (COORD R6(3)): per-quadrant / per-bank form of tb_vms_wq2_merge (pinned, untouched): the
// replicated vmm_Q<k> merges sit beside every bank of every quadrant, so the equivalence (q2 bank with wq2 inside vs
// merge leaf + q0 bank) is run for each quadrant slice id SID 0..3 and each bank BID 0..7.  SIDMUT (bench): DUT bank
// strapped with the wrong quadrant id SID^1 -> must FAIL.
// Equivalence bench: REF = the q2 bank master (hfd_vms_bank_native_q2_faces, WG=3, wq2 in the bank) vs
// DUT = hfd_vms_wq2_merge + the exact q0 bank master (hfd_vms_bank_native_q0_faces, WG=2).
// Same random static schedule (one write owner + one read owner per edge, real SRAM vehicle, sid=2).  DUT differences
// by construction: wq1/wq2 are issued two edges earlier into the leaf (+2 edges), the q2 owner codes are remapped
// (2 -> 1, k>=3 -> k-1, compiler table), wq_done1/wq_done2 arrive one edge later.  Every other bank output must be
// identical on every edge: rr0..rr4, eg, pr, dq_done, kq/xq/xq2_done, wq_done0, status.
module tb_vms_wq2_merge_q;
    parameter integer N = 6000, SEED = 1, LEAF_MUT = 0, DONE_LAT = 5, SID = 2, BID = 5, SIDMUT = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    // schedule entries (cycle-indexed)
    reg [280:0] s_wq0 [0:N+6], s_wq1 [0:N+6], s_wq2 [0:N+6], s_dq [0:N+6];
    reg [16:0]  s_rq  [0:N+6][0:4];
    reg         s_wv  [0:N+6], s_rv [0:N+6];
    reg [2:0]   s_ws  [0:N+6], s_rs [0:N+6];
    // REF drive
    reg [280:0] r_wq0 = 0, r_wq1 = 0, r_wq2 = 0, r_dq = 0; reg [16:0] r_rq [0:4];
    reg r_wv = 0, r_rv = 0; reg [2:0] r_ws = 0, r_rs = 0;
    // DUT drive (bank gets remapped code; leaf gets wq1/wq2 two edges early)
    reg [280:0] d_wq1 = 0, d_wq2 = 0; reg [2:0] d_ws = 0;
    wire [256:0] rr_r [0:4], rr_d [0:4];
    wire [275:0] eg_r, eg_d; wire [265:0] pr_r, pr_d; wire [17:0] st_r, st_d;
    wire dqd_r, dqd_d, kqd_r, kqd_d, xqd_r, xqd_d, x2d_r, x2d_d, w0_r, w0_d, w1_r, w1_d, w2_r, w2_d;
    wire [280:0] wq_m; wire done_m, flt;
    hfd_vms_bank_native_q2_faces ref_bank(
      .bid(3'(BID)), .sid(2'(SID)), .clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk),
      .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .rst_n(rst_n),
      .rslot_v(r_rv), .rslot(r_rs), .wslot_v(r_wv), .wslot(r_ws), .dq(r_dq), .dq_done(dqd_r),
      .kq(281'd0), .kq_done(kqd_r), .xq(276'd0), .xq_done(xqd_r), .xq2(276'd0), .xq2_done(x2d_r), .eg(eg_r),
      .pq(285'd0), .pr(pr_r), .status(st_r),
      .rq0(r_rq[0]), .rr0(rr_r[0]), .rq1(r_rq[1]), .rr1(rr_r[1]), .rq2(r_rq[2]), .rr2(rr_r[2]),
      .rq3(r_rq[3]), .rr3(rr_r[3]), .rq4(r_rq[4]), .rr4(rr_r[4]),
      .wq0(r_wq0), .wq_done0(w0_r), .wq1(r_wq1), .wq_done1(w1_r), .wq2(r_wq2), .wq_done2(w2_r));
    hfd_vms_wq2_merge #(.DONE_LAT(DONE_LAT), .MUT(LEAF_MUT)) leaf(
      .clk(clk), .rst_n(rst_n), .wq1(d_wq1), .wq2(d_wq2), .wq_m(wq_m), .done_m(done_m),
      .wq_done1(w1_d), .wq_done2(w2_d), .flt(flt));
    hfd_vms_bank_native_q0_faces dut_bank(
      .bid(3'(BID)), .sid(2'(SIDMUT ? SID ^ 1 : SID)), .clk(clk), .clk_n(clk), .clk_s(clk), .clk_e(clk), .clk_w(clk),
      .clk_macro0(clk), .clk_macro1(clk), .clk_macro2(clk), .rst_n(rst_n),
      .rslot_v(r_rv), .rslot(r_rs), .wslot_v(r_wv), .wslot(d_ws), .dq(r_dq), .dq_done(dqd_d),
      .kq(281'd0), .kq_done(kqd_d), .xq(276'd0), .xq_done(xqd_d), .xq2(276'd0), .xq2_done(x2d_d), .eg(eg_d),
      .pq(285'd0), .pr(pr_d), .status(st_d),
      .rq0(r_rq[0]), .rr0(rr_d[0]), .rq1(r_rq[1]), .rr1(rr_d[1]), .rq2(r_rq[2]), .rr2(rr_d[2]),
      .rq3(r_rq[3]), .rr3(rr_d[3]), .rq4(r_rq[4]), .rr4(rr_d[4]),
      .wq0(r_wq0), .wq_done0(w0_d), .wq1(wq_m), .wq_done1(done_m));
    function automatic [15:0] sector(input integer row, input bit mir);
        sector = mir ? {1'b1, 2'b00, 10'(row), 3'(BID)} : {1'b0, 2'(SID), 10'(row), 3'(BID)};
    endfunction
    integer seed = SEED, t, k, mism = 0, w_cnt [0:3], r_cnt = 0, done_cnt = 0;
    reg w1_r_q = 0, w2_r_q = 0;
    reg [280:0] p;
    initial begin
        for (k = 0; k < 4; k = k + 1) w_cnt[k] = 0;
        for (t = 0; t <= N + 6; t = t + 1) begin
            s_wq0[t] = 0; s_wq1[t] = 0; s_wq2[t] = 0; s_dq[t] = 0; s_wv[t] = 0; s_rv[t] = 0; s_ws[t] = 0; s_rs[t] = 0;
            for (k = 0; k < 5; k = k + 1) s_rq[t][k] = 0;
            if (t >= 20 && t < N) begin
                // one write owner per edge: 0 wq0, 1 wq1, 2 wq2, 7 dq (q2 code); ~70% busy
                k = $urandom(seed) % 10; seed = seed + 1;
                p = {1'b1, 1'($urandom(seed)), 16'h0, 8'($urandom(seed)), {8{32'($urandom(seed))}}}; seed = seed + 3;
                p[279] = $urandom(seed) % 2; seed = seed + 1;
                p[264 +: 16] = sector($urandom(seed) % 64, $urandom(seed) % 2); seed = seed + 2;
                if (k < 2)      begin s_wq0[t] = p; s_wv[t] = 1; s_ws[t] = 0; w_cnt[0]++; end
                else if (k < 4) begin s_wq1[t] = p; s_wv[t] = 1; s_ws[t] = 1; w_cnt[1]++; end
                else if (k < 6) begin s_wq2[t] = p; s_wv[t] = 1; s_ws[t] = 2; w_cnt[2]++; end
                else if (k < 7) begin s_dq[t] = p;  s_wv[t] = 1; s_ws[t] = 7; w_cnt[3]++; end
                // one read owner per edge (groups 0..4), ~60%
                k = $urandom(seed) % 8; seed = seed + 1;
                if (k < 5) begin
                    s_rq[t][k] = {1'b1, sector($urandom(seed) % 64, $urandom(seed) % 2)}; seed = seed + 2;
                    s_rv[t] = 1; s_rs[t] = 3'(k); r_cnt++;
                end
            end
        end
        repeat (8) @(posedge clk); #1 rst_n = 1;
        for (t = 0; t < N + 4; t = t + 1) begin
            @(posedge clk); #1;
            r_wq0 = s_wq0[t]; r_wq1 = s_wq1[t]; r_wq2 = s_wq2[t]; r_dq = s_dq[t];
            for (k = 0; k < 5; k = k + 1) r_rq[k] = s_rq[t][k];
            r_wv = s_wv[t]; r_ws = s_ws[t]; r_rv = s_rv[t]; r_rs = s_rs[t];
            d_ws = (s_ws[t] >= 3) ? s_ws[t] - 1 : (s_ws[t] == 2 ? 3'd1 : s_ws[t]);
            d_wq1 = s_wq1[t + 2]; d_wq2 = s_wq2[t + 2];
        end
        repeat (30) @(posedge clk);
        $display("WQ2_MERGE writes wq0=%0d wq1=%0d wq2=%0d dq=%0d reads=%0d done=%0d mismatches=%0d flt=%0d",
                 w_cnt[0], w_cnt[1], w_cnt[2], w_cnt[3], r_cnt, done_cnt, mism, flt);
        if (mism == 0 && flt == 0 && w_cnt[2] > 100 && done_cnt > 100) $display("WQ2_MERGE BENCH PASS");
        else begin $display("WQ2_MERGE BENCH FAIL"); $fatal(1, "FATAL mismatch"); end
        $finish;
    end
    // compare on the negative edge (all outputs settled)
    always @(negedge clk) if (rst_n) begin
        for (k = 0; k < 5; k = k + 1) if (rr_r[k] !== rr_d[k]) begin mism++; if (mism < 5) $display("MISMATCH rr%0d @%0t", k, $time); end
        if (eg_r !== eg_d) begin mism++; if (mism < 5) $display("MISMATCH eg @%0t", $time); end
        if (pr_r !== pr_d) begin mism++; if (mism < 5) $display("MISMATCH pr @%0t", $time); end
        if ({dqd_r, kqd_r, xqd_r, x2d_r, w0_r} !== {dqd_d, kqd_d, xqd_d, x2d_d, w0_d}) begin mism++; if (mism < 5) $display("MISMATCH done @%0t", $time); end
        if ({w1_r_q, w2_r_q} !== {w1_d, w2_d}) begin mism++; if (mism < 5) $display("MISMATCH wq_done1/2 ref(+1)=%b%b dut=%b%b @%0t", w1_r_q, w2_r_q, w1_d, w2_d, $time); end
        if (st_r !== st_d) begin mism++; if (mism < 5) $display("MISMATCH status %h %h @%0t", st_r, st_d, $time); end
    end
    always @(posedge clk) begin w1_r_q <= w1_r; w2_r_q <= w2_r; if (w2_r) done_cnt++; end
endmodule
`default_nettype wire
