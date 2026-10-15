`timescale 1ns/1ps
// s81-die-rtl-bind r3 2026-10-14: exact gate of the count-only PQ return leaf ot_s81_pq_rwbc_core against the count
// outputs of the CLOSED RWB ot_s81_pq_rwb_core (= the reference T_RET group, bit / cycle exact per its own bench) fed the
// SAME root words: ga and q2f equal on EVERY cycle, NR 15 and NR 2 (the die's two masters), random valid / tag / e /
// fault / live streams incl. bursts on every region and every tag, mdr live bits changing.  +RWBC_CYCLES=n
module tb_ot_s81_pq_rwbc;
    localparam integer VAW = 19, CFW = 5 * VAW + 18, GRW = 4 * CFW + 4 + 2;
    reg clk = 0, rst_n = 0;
    always #0.4166 clk = ~clk;
    integer cyc = 0, errs = 0, n_cnt = 0, n_q2f = 0, ncyc = 200000;
    reg [GRW-1:0] mdr = '0;
    // NR 15 pair
    reg  [14:0] v15, e15, f15; reg [29:0] t15; reg [16*15-1:0] row15; reg [3*15-1:0] pos15; reg [32*15-1:0] f32_15; reg [16*15-1:0] bf15;
    wire [15:0] ga_r15, ga_c15; wire q_r15, q_c15;
    ot_s81_pq_rwb_core #(.NR(15)) u_r15 (.clk(clk), .rst_n(rst_n), .r_v(v15), .r_row(row15), .r_pos(pos15), .r_fp32(f32_15),
        .r_bf16(bf15), .r_e(e15), .mdr(mdr), .r_flt({14'd0, f15[0]}), .w_we(), .w_addr(), .w_data(), .q2f(q_r15), .ga(ga_r15));
    ot_s81_pq_rwbc_core #(.NR(15)) u_c15 (.clk(clk), .rst_n(rst_n), .r_v(v15), .r_tag(t15), .r_e(e15), .g_flt(f15[0]), .mdr(mdr),
        .q2f(q_c15), .ga(ga_c15));
    // NR 2 pair
    reg  [1:0] v2, e2, f2; reg [3:0] t2; reg [31:0] row2; reg [5:0] pos2; reg [63:0] f32_2; reg [31:0] bf2;
    wire [15:0] ga_r2, ga_c2; wire q_r2, q_c2;
    ot_s81_pq_rwb_core #(.NR(2)) u_r2 (.clk(clk), .rst_n(rst_n), .r_v(v2), .r_row(row2), .r_pos(pos2), .r_fp32(f32_2),
        .r_bf16(bf2), .r_e(e2), .mdr(mdr), .r_flt({1'b0, f2[0]}), .w_we(), .w_addr(), .w_data(), .q2f(q_r2), .ga(ga_r2));
    ot_s81_pq_rwbc_core #(.NR(2)) u_c2 (.clk(clk), .rst_n(rst_n), .r_v(v2), .r_tag(t2), .r_e(e2), .g_flt(f2[0]), .mdr(mdr),
        .q2f(q_c2), .ga(ga_c2));
    integer i, mode;
    initial begin
        if ($value$plusargs("RWBC_CYCLES=%d", ncyc)) ;
        v15 = 0; e15 = 0; f15 = 0; t15 = 0; row15 = 0; pos15 = 0; f32_15 = 0; bf15 = 0;
        v2 = 0; e2 = 0; f2 = 0; t2 = 0; row2 = 0; pos2 = 0; f32_2 = 0; bf2 = 0;
        repeat (8) @(posedge clk);
        rst_n = 1;
    end
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        mode = (cyc / 5000) % 4;                          // 0 sparse, 1 dense, 2 all-valid bursts, 3 single-tag storms
        if (cyc % 997 == 0) mdr[4*CFW +: 4] = $urandom;    // live bits change
        for (i = 0; i < 15; i = i + 1) begin
            v15[i] = (mode == 2) ? 1'b1 : (mode == 1) ? ($urandom % 4 != 0) : ($urandom % 8 == 0);
            e15[i] = ($urandom % 64 == 0);
            t15[2*i +: 2] = (mode == 3) ? (cyc / 200) % 4 : $urandom;
            row15[16*i +: 16] = {t15[2*i +: 2], 14'($urandom)};
            pos15[3*i +: 3] = $urandom; f32_15[32*i +: 32] = $urandom; bf15[16*i +: 16] = $urandom;
        end
        for (i = 0; i < 2; i = i + 1) begin
            v2[i] = (mode == 2) ? 1'b1 : ($urandom % 3 == 0); e2[i] = ($urandom % 64 == 0);
            t2[2*i +: 2] = $urandom; row2[16*i +: 16] = {t2[2*i +: 2], 14'($urandom)};
            pos2[3*i +: 3] = $urandom; f32_2[32*i +: 32] = $urandom; bf2[16*i +: 16] = $urandom;
        end
        f15 = ($urandom % 20000 == 0); f2 = ($urandom % 20000 == 0);
    end
    always @(posedge clk) if (rst_n && cyc > 4) begin
        if (ga_r15 !== ga_c15 || q_r15 !== q_c15 || ga_r2 !== ga_c2 || q_r2 !== q_c2) begin
            errs = errs + 1;
            if (errs <= 5) $display("RWBC MISMATCH cyc=%0d ga15 %h/%h q2f15 %b/%b ga2 %h/%h q2f2 %b/%b", cyc, ga_r15, ga_c15, q_r15, q_c15,
                                    ga_r2, ga_c2, q_r2, q_c2);
        end
        if (ga_r15 != 0) n_cnt = n_cnt + 1;
        if (q_r15) n_q2f = n_q2f + 1;
        if (cyc >= ncyc) begin
            if (errs == 0 && n_cnt > 1000 && n_q2f > 10) $display("RWBC_GATE PASS cycles=%0d count_cycles=%0d q2f_cycles=%0d", cyc, n_cnt, n_q2f);
            else $display("RWBC_GATE FAIL errs=%0d count_cycles=%0d q2f_cycles=%0d", errs, n_cnt, n_q2f);
            $finish;
        end
    end
endmodule
