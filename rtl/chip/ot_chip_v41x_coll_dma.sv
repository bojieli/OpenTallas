`timescale 1ns/1ps
// Blocking V4.1 collective DMA. Addresses and n here are VM words; the die
// checks the ISA's element alignment and shifts by four before issuing.
module ot_chip_v41x_coll_dma #(
    parameter integer WA = 12,
    parameter integer FW = 512,
    parameter integer TAGW = 32,
    parameter integer N = 4,
    parameter integer GW = 1,
    parameter integer RB = (N > 1) ? $clog2(N) : 1
) (
    input wire clk, rst_n,
    input wire go, mode, rnd,
    input wire [TAGW-1:0] tag,
    input wire [WA-1:0] src, n, dst,
    output reg busy, fault,
    output reg [31:0] words_out, words_in,
    output wire vm_re,
    output wire [WA-1:0] vm_raddr,
    input wire [FW-1:0] vm_rq,
    output wire vm_we,
    output wire [WA-1:0] vm_waddr,
    output wire [FW-1:0] vm_wdata,
    // Four-bank full-shape write port. GW=1 mirrors the scalar port in lane 0.
    input wire vm_ready4,
    output wire [3:0] vm_we4,
    output wire [4*WA-1:0] vm_waddr4,
    output wire [4*FW-1:0] vm_wdata4,
    output wire e_valid,
    input wire e_ready,
    output wire [FW-1:0] e_data,
    output wire e_last,
    output reg e_mode,
    output reg [TAGW-1:0] e_tag,
    input wire o_valid,
    output wire o_ready,
    input wire [GW*FW-1:0] o_data,
    input wire o_last,
    input wire [RB-1:0] o_rank,
    input wire o_err, engine_fault
);
    localparam integer LANES = FW / 32;
    localparam integer CW = WA + 3;
    localparam [CW-1:0] N_C = CW'(N);
    reg [WA-1:0] rd_k, n_r, src_r, dst_r;
    reg [WA+2:0] wr_k;
    reg rnd_r, rd_q;
    reg [WA-1:0] rd_qk;
    reg [FW-1:0] sk_d [0:1];
    reg sk_l [0:1], sk_h;
    reg [1:0] sk_n;
    reg [1:0] commit_wait;
    wire pop = e_valid && e_ready;
    wire [2:0] held = {1'b0, sk_n} + {2'b0, rd_q} - {2'b0, pop};
    wire [CW-1:0] limit = (CW'(1) << WA);
    wire [CW-1:0] src_start = CW'(src), dst_start = CW'(dst), n_ext = CW'(n);
    wire [CW-1:0] src_end = src_start + n_ext;
    wire [CW-1:0] dst_end = dst_start + (mode ? (n_ext * N_C) : n_ext);
    wire bad_command = (n == 0) || (src_end > limit) || (dst_end > limit) ||
                       ((src_start < dst_end) && (dst_start < src_end));
    assign vm_re = busy && !fault && rd_k != n_r && held < 3'd2;
    assign vm_raddr = src_r + rd_k;
    assign e_valid = sk_n != 0 && !fault;
    assign e_data = sk_d[sk_h];
    assign e_last = sk_l[sk_h];
    wire [CW-1:0] gather_addr = CW'(dst_r) + (CW'(n_r) * CW'(o_rank)) + (wr_k / N_C);
    assign vm_we = busy && o_valid && (!e_mode || GW == 1) &&
                   !fault && !o_err && !engine_fault;
    assign vm_waddr = e_mode ? gather_addr[WA-1:0] : dst_r + wr_k[WA-1:0];

    function automatic [31:0] bf16_rne(input [31:0] x);
        reg [32:0] tmp;
        begin
            tmp = {1'b0, x} + 33'h000007fff + 33'(x[16]);
            bf16_rne = {tmp[31:16], 16'h0000};
            if (x[30:0] == 0) bf16_rne = 32'h00000000;
        end
    endfunction
    genvar lane;
    generate for (lane = 0; lane < LANES; lane = lane + 1) begin : g_round
        assign vm_wdata[32*lane +: 32] =
            (!e_mode && rnd_r) ? bf16_rne(o_data[32*lane +: 32]) :
                                 o_data[32*lane +: 32];
    end endgenerate

    wire tr_ready, tr_done, tr_fault;
    wire [3:0] tr_we;
    wire [4*WA-1:0] tr_addr;
    wire [4*FW-1:0] tr_data;
    wire tr_valid, tr_last;
    generate if (GW == 4) begin : g_transpose
        ot_chip_v41x_coll_transpose #(.WA(WA), .FW(FW)) u_tr (
            .clk(clk), .rst_n(rst_n),
            .start(go && !busy && mode && !bad_command && !fault),
            .dst(dst), .n(n),
            .in_ready(tr_ready), .in_valid(busy && e_mode && o_valid && !fault && !o_err && !engine_fault),
            .in_data(o_data), .in_last(o_last),
            .out_ready(vm_ready4), .out_valid(tr_valid), .out_we(tr_we),
            .out_addr(tr_addr), .out_data(tr_data), .out_last(tr_last),
            .done(tr_done), .fault(tr_fault));
    end else begin : g_scalar
        assign tr_ready = 1'b1;
        assign tr_done = 1'b0;
        assign tr_fault = 1'b0;
        assign tr_we = 4'b0;
        assign tr_addr = {4*WA{1'b0}};
        assign tr_data = {4*FW{1'b0}};
        assign tr_valid = 1'b0;
        assign tr_last = 1'b0;
    end endgenerate
    assign o_ready = (GW == 4 && e_mode) ? tr_ready : 1'b1;
    assign vm_we4 = (GW == 4 && e_mode) ? tr_we : {3'b000, vm_we};
    assign vm_waddr4 = (GW == 4 && e_mode) ? tr_addr : {{3*WA{1'b0}}, vm_waddr};
    assign vm_wdata4 = (GW == 4 && e_mode) ? tr_data : {{3*FW{1'b0}}, vm_wdata};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 0; fault <= 0; rd_k <= 0; n_r <= 0; src_r <= 0;
            dst_r <= 0; wr_k <= 0; rnd_r <= 0; rd_q <= 0; rd_qk <= 0;
            sk_n <= 0; sk_h <= 0; e_mode <= 0; e_tag <= 0;
            commit_wait <= 0;
            words_out <= 0; words_in <= 0;
            sk_d[0] <= 0; sk_d[1] <= 0; sk_l[0] <= 0; sk_l[1] <= 0;
        end else begin
            if (o_err || engine_fault || tr_fault || (go && busy)) fault <= 1;
            if (go && !busy) begin
                if (bad_command || fault) fault <= 1;
                else begin
                    busy <= 1; rd_k <= 0; n_r <= n; src_r <= src;
                    dst_r <= dst; wr_k <= 0; rnd_r <= rnd;
                    rd_q <= 0; sk_n <= 0; sk_h <= 0;
                    e_mode <= mode; e_tag <= tag;
                    commit_wait <= 0;
                end
            end else if (busy) begin
                rd_q <= vm_re;
                rd_qk <= rd_k;
                if (vm_re) rd_k <= rd_k + 1'b1;
                if (rd_q) begin
                    sk_d[sk_h ^ sk_n[0]] <= vm_rq;
                    sk_l[sk_h ^ sk_n[0]] <= (rd_qk == n_r - 1'b1);
                end
                if (pop) begin sk_h <= ~sk_h; words_out <= words_out + 1; end
                sk_n <= sk_n + {1'b0, rd_q} - {1'b0, pop};
                commit_wait <= {commit_wait[0], tr_done};
                if (GW == 4 && e_mode && commit_wait[1]) busy <= 0;
                if (GW == 4 && e_mode && o_valid && o_ready && !fault && !o_err && !engine_fault) begin
                    wr_k <= wr_k + CW'(N);
                    words_in <= words_in + 32'(N);
                    if (o_rank != 0) fault <= 1;
                    if (o_last && wr_k != CW'(n_r) * N_C - N_C) fault <= 1;
                end
                if (vm_we) begin
                    wr_k <= wr_k + 1'b1;
                    words_in <= words_in + 1;
                    if (e_mode && integer'(o_rank) >= N) fault <= 1;
                    if (o_last) begin
                        if (wr_k != (e_mode ? (CW'(n_r) * N_C - CW'(1)) : (CW'(n_r) - CW'(1))))
                            fault <= 1;
                        busy <= 0;
                    end
                end
            end
        end
    end
endmodule
