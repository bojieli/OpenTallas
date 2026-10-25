`timescale 1ns/1ps
// KV-CORES 10-25 (COORD ruling 5): lockstep miter ot_qkh_lane8 LT_COPY=1 (DUT) vs the unchanged leaf (ot_qkh_lane8_ref =
// origin/main ot_qkh_subtiles.sv, KVD_HMUT stripped).  Same random stimulus every edge (reset, c_in, row, e, lt, q beats,
// hid / bsel straps fixed per run), all outputs compared every cycle.  Mutant: +define+KVD_HMUT shifts the DUT decision
// word one edge (must FAIL).
module tb_lane8_ltcopy;
    reg clk = 0, rst_n = 0;
    reg [3:0] c_in; reg [63:0] row_in; reg [15:0] e_in; reg [11:0] lt_in; reg [1:0] hid, bsel;
    reg qv; reg [5:0] qb; reg [127:0] qd;
    wire [31:0] kp_r, kp_d; wire kpv_r, kpv_d, gf_r, gf_d; wire [63:0] nb_r, nb_d;
    ot_qkh_lane8_ref r (.clk(clk), .rst_n(rst_n), .c_in(c_in), .row_in(row_in), .e_in(e_in), .lt_in(lt_in), .hid(hid),
        .bsel(bsel), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .kp(kp_r), .kpv(kpv_r), .nb(nb_r), .gf(gf_r));
    ot_qkh_lane8 #(.LT_COPY(1)) d (.clk(clk), .rst_n(rst_n), .c_in(c_in), .row_in(row_in), .e_in(e_in), .lt_in(lt_in),
        .hid(hid), .bsel(bsel), .q_valid_in(qv), .q_beat_in(qb), .q_data_in(qd), .kp(kp_d), .kpv(kpv_d), .nb(nb_d), .gf(gf_d));
    integer cyc = 0, mism = 0, nbu = 0, kpvn = 0, N;
    reg [63:0] nb_prev;
    function [15:0] bf(input integer s); bf = {s[0], 4'b0111 + s[5:4], s[3:1], s[15:8]}; endfunction  // finite bf16-ish
    always #1 clk = ~clk;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 6000;
        hid = 2'd1; bsel = 2'd2;
        {c_in, row_in, e_in, lt_in, qv, qb, qd} = 0;
        repeat (8) @(posedge clk);
        rst_n = 1;
    end
    always @(negedge clk) begin
        c_in <= $random; row_in <= {$random, $random}; e_in <= bf($random); lt_in <= $random;
        qv <= $random; qb <= {$random} % 64; qd <= {bf($random), bf($random), bf($random), bf($random), bf($random),
            bf($random), bf($random), bf($random)};
        if (cyc == 3000) rst_n <= 0;             // mid-run reset pulse (reset copies of the lane flops)
        if (cyc == 3006) rst_n <= 1;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > 0 && {kp_r, kpv_r, nb_r, gf_r} !== {kp_d, kpv_d, nb_d, gf_d}) begin
            if (mism < 5) $display("MISMATCH cyc %0d kp %h/%h kpv %b/%b nb %h/%h gf %b/%b", cyc, kp_r, kp_d, kpv_r, kpv_d,
                                   nb_r, nb_d, gf_r, gf_d);
            mism <= mism + 1;
        end
        nb_prev <= nb_r;
        if (nb_r != nb_prev) nbu <= nbu + 1;
        if (kpv_r) kpvn <= kpvn + 1;
        if (cyc == N) begin
            $display("MITER %s edges %0d mismatches %0d (activity: nb updates %0d, kpv %0d)", mism ? "FAIL" : "PASS",
                     cyc, mism, nbu, kpvn);
            $finish;
        end
    end
endmodule
