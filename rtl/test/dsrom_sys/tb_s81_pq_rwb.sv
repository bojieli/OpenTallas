`timescale 1ns/1ps
// Exact bench of the S81 PQ RWB (ot_s81_pq_rwb11 / ot_s81_pq_rwb10) against the reference spine's T_RET group
// (ot_v41_pqc_ret, PIN 0 / RPT 2 as in ot_v41_spine_pqc_w17w10): the reference for N regions is two groups (8 + N-8)
// whose row popcounts add and whose group faults OR. Every cycle: w_we of every region; w_addr / w_data of every
// written region; ga (per tag); q2f. Random returns (valid ~50 %, rows / tags / positions / payloads random, rare e),
// configuration replica re-randomised every 64..1023 cycles. Then a directed root-fault check (DUT only: r_flt[k]
// must raise q2f two edges later and only then).  +define+NR11 selects the 11-region master (else 10).
module tb_s81_pq_rwb;
`ifdef NR11
    localparam integer N = 11;
`else
    localparam integer N = 10;
`endif
    localparam integer VAW = 19, GRW = 458, NB = N - 8, CYC = 40000;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [N-1:0] r_v, r_e, r_flt; reg [16*N-1:0] r_row, r_bf16; reg [3*N-1:0] r_pos; reg [32*N-1:0] r_fp32;
    reg [GRW-1:0] mdr;
    wire [N-1:0] d_we; wire [N*VAW-1:0] d_addr; wire [N*32-1:0] d_data; wire d_q2f; wire [15:0] d_ga;
`ifdef NR11
    ot_s81_pq_rwb11 dut (
`else
    ot_s81_pq_rwb10 dut (
`endif
        .clk(clk), .rst_n(rst_n), .r_v(r_v), .r_row(r_row), .r_pos(r_pos), .r_fp32(r_fp32), .r_bf16(r_bf16), .r_e(r_e),
        .r_flt(r_flt), .mdr(mdr), .w_we(d_we), .w_addr(d_addr), .w_data(d_data), .q2f(d_q2f), .ga(d_ga));
    wire [7:0] a_we; wire [8*VAW-1:0] a_addr; wire [8*32-1:0] a_data; wire a_q2f; wire [15:0] a_ga;
    wire [NB-1:0] b_we; wire [NB*VAW-1:0] b_addr; wire [NB*32-1:0] b_data; wire b_q2f; wire [15:0] b_ga;
    ot_v41_pqc_ret #(.NR(8), .VAW(VAW), .PQ(1), .RPT(2), .PIN(0)) ref_a (.clk(clk), .rst_n(rst_n),
        .r_v(r_v[7:0]), .r_row(r_row[127:0]), .r_pos(r_pos[23:0]), .r_fp32(r_fp32[255:0]), .r_bf16(r_bf16[127:0]),
        .r_e(r_e[7:0]), .mdr(mdr), .w_we(a_we), .w_addr(a_addr), .w_data(a_data), .q2f(a_q2f), .ga(a_ga));
    ot_v41_pqc_ret #(.NR(NB), .VAW(VAW), .PQ(1), .RPT(2), .PIN(0)) ref_b (.clk(clk), .rst_n(rst_n),
        .r_v(r_v[N-1:8]), .r_row(r_row[16*N-1:128]), .r_pos(r_pos[3*N-1:24]), .r_fp32(r_fp32[32*N-1:256]),
        .r_bf16(r_bf16[16*N-1:128]), .r_e(r_e[N-1:8]), .mdr(mdr), .w_we(b_we), .w_addr(b_addr), .w_data(b_data),
        .q2f(b_q2f), .ga(b_ga));
    wire [N-1:0] e_we = {b_we, a_we};
    wire [N*VAW-1:0] e_addr = {b_addr, a_addr};
    wire [N*32-1:0] e_data = {b_data, a_data};
    wire [15:0] e_ga;
    genvar t;
    generate for (t = 0; t < 4; t = t + 1) begin : g_t
        assign e_ga[4*t +: 4] = a_ga[4*t +: 4] + b_ga[4*t +: 4];
    end endgenerate
    integer cyc = 0, err = 0, nwr = 0, ncnt = 0, k, nxt = 100;
    function automatic [31:0] rnd32(); rnd32 = $urandom; endfunction
    task automatic randomise_cfg();
        integer i;
        for (i = 0; i < GRW; i = i + 32) mdr[i +: 32] = $urandom;
    endtask
    initial begin
        r_v = 0; r_e = 0; r_flt = 0; r_row = 0; r_bf16 = 0; r_pos = 0; r_fp32 = 0; randomise_cfg();
        repeat (5) @(posedge clk);
        rst_n = 1;
        repeat (6) @(posedge clk);
        for (cyc = 0; cyc < CYC; cyc = cyc + 1) begin
            @(negedge clk);
            if (cyc == nxt) begin randomise_cfg(); nxt = cyc + 64 + ($urandom % 960); end
            for (k = 0; k < N; k = k + 1) begin
                r_v[k] = $urandom % 2;
                r_e[k] = ($urandom % 64) == 0;
                r_row[16*k +: 16] = $urandom;
                r_pos[3*k +: 3] = $urandom;
                r_bf16[16*k +: 16] = $urandom;
                r_fp32[32*k +: 32] = $urandom;
            end
            @(posedge clk); #0.1;
            if (d_we !== e_we) begin err = err + 1; if (err < 10) $display("MISMATCH cyc %0d we %h exp %h", cyc, d_we, e_we); end
            for (k = 0; k < N; k = k + 1) if (e_we[k]) begin
                nwr = nwr + 1;
                if (d_addr[VAW*k +: VAW] !== e_addr[VAW*k +: VAW] || d_data[32*k +: 32] !== e_data[32*k +: 32]) begin
                    err = err + 1; if (err < 10) $display("MISMATCH cyc %0d region %0d addr %h/%h data %h/%h", cyc, k,
                        d_addr[VAW*k +: VAW], e_addr[VAW*k +: VAW], d_data[32*k +: 32], e_data[32*k +: 32]);
                end
            end
            if (d_ga !== e_ga) begin err = err + 1; if (err < 10) $display("MISMATCH cyc %0d ga %h exp %h", cyc, d_ga, e_ga); end
            if (d_ga != 0) ncnt = ncnt + 1;
            if (d_q2f !== (a_q2f | b_q2f)) begin err = err + 1; if (err < 10) $display("MISMATCH cyc %0d q2f %b exp %b", cyc, d_q2f, a_q2f | b_q2f); end
        end
        // directed root-fault check: all returns idle, no e, then r_flt[k] for one cycle
        r_v = 0; r_e = 0;
        repeat (12) @(posedge clk);
        for (k = 0; k < N; k = k + 1) begin
            @(negedge clk); r_flt = {{(N-1){1'b0}}, 1'b1} << k;
            @(negedge clk); r_flt = 0;
            if (d_q2f !== 1'b0) begin err = err + 1; $display("FLT early region %0d", k); end
            @(negedge clk);
            if (d_q2f !== 1'b1) begin err = err + 1; $display("FLT missed region %0d", k); end
            @(negedge clk);
            if (d_q2f !== 1'b0) begin err = err + 1; $display("FLT stuck region %0d", k); end
        end
        if (err == 0 && nwr > 1000 && ncnt > 1000) $display("RWB_EXACT PASS N=%0d cycles=%0d writes=%0d count_cycles=%0d", N, CYC, nwr, ncnt);
        else $display("RWB_EXACT FAIL N=%0d errors=%0d writes=%0d count_cycles=%0d", N, err, nwr, ncnt);
        $finish;
    end
endmodule
