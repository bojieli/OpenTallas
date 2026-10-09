`timescale 1ns/1ps
// cont-takeover 2026-10-09 (REVIEW ~11:30, structural rule "pin stations + credits die-wide"): the credit-relay boundary
// for a die-link channel.  Every pin is a flop: the link carries {valid, data} forward from sender flops into receiver
// pin flops, and one credit pulse backward from a receiver flop into a sender pin flop.  No pin fans out into logic
// (the valid/ready skid it replaces let out_ready fan out to the 600-bit pop enables: HC join TT -120 ps under the
// die-link budget).
//   ot_link_credit_tx : core valid/ready (internal) -> link.  CRED = the receiver's landing depth; a beat leaves only
//                       with a credit in hand, so the receiver can never overflow.  l_credit is a one-cycle pulse per
//                       freed landing slot.
//   ot_link_credit_rx : link -> landing FIFO (DEPTH) -> core valid/ready (internal); a credit pulse per core pop.
//                       A beat that lands with the FIFO full is a protocol fault (sticky; the beat is dropped).
// Full throughput needs DEPTH >= the credit round trip (2 x link latency + 4 cycles of pin/landing flops).
module ot_link_credit_tx #(parameter integer W=8, CRED=8)(
    input wire clk, rst_n,
    input wire i_valid, output wire i_ready, input wire [W-1:0] i_data,
    output reg l_valid, output reg [W-1:0] l_data, input wire l_credit
);
    localparam integer CW = $clog2(CRED + 1);
    reg cr_q;
    reg [CW-1:0] cnt;
    assign i_ready = cnt != 0;
    wire send = i_valid && cnt != 0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_q <= 1'b0; cnt <= CW'(CRED); l_valid <= 1'b0; end
        else begin
            cr_q <= l_credit;
            cnt <= cnt + CW'(cr_q) - CW'(send);
            l_valid <= send;
        end
    always @(posedge clk) if (send) l_data <= i_data;
endmodule

module ot_link_credit_rx #(parameter integer W=8, DEPTH=8)(
    input wire clk, rst_n,
    input wire l_valid, input wire [W-1:0] l_data, output reg l_credit,
    output wire o_valid, input wire o_ready, output wire [W-1:0] o_data,
    output reg fault
);
    localparam integer AW = (DEPTH > 1) ? $clog2(DEPTH) : 1, CW = $clog2(DEPTH + 1);
    reg v_q;
    reg [W-1:0] d_q;
    reg [W-1:0] mem [0:DEPTH-1];
    reg [AW-1:0] wp, rp;
    reg [CW-1:0] n;
    assign o_valid = n != 0;
    assign o_data = mem[rp];
    wire pop = o_valid && o_ready;
    wire full = n == CW'(DEPTH);
    wire wr = v_q && (!full || pop);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v_q <= 1'b0; wp <= 0; rp <= 0; n <= 0; l_credit <= 1'b0; fault <= 1'b0; end
        else begin
            v_q <= l_valid;
            l_credit <= pop;
            if (v_q && full && !pop) fault <= 1'b1;
            if (wr) wp <= (wp == AW'(DEPTH - 1)) ? '0 : wp + 1'b1;
            if (pop) rp <= (rp == AW'(DEPTH - 1)) ? '0 : rp + 1'b1;
            n <= n + CW'(wr) - CW'(pop);
        end
    always @(posedge clk) begin
        d_q <= l_data;
        if (wr) mem[wp] <= d_q;
    end
endmodule

// Testbench-side link model (not for synthesis in a block): a valid/ready producer or consumer reaches a credit port of a
// DUT through LAT cycles of link flops each way.  DIR=0: TB producer -> DUT receiver (TB holds a tx with CRED = the
// DUT's DEPTH); DIR=1: DUT sender -> TB consumer (TB holds an rx with DEPTH = the DUT tx's CRED).
// LEAK > 0 (DIR 0): the TB sender discards the first LEAK returned credits (a lost-credit negative: the channel stalls).
module ot_link_credit_tb_chan #(parameter integer W=8, DIR=0, DEPTH=8, LAT=2, CRED_BIAS=0, LEAK=0)(
    input wire clk, rst_n,
    // TB side
    input wire t_valid, output wire t_ready, input wire [W-1:0] t_data,     // DIR 0
    output wire r_valid, input wire r_ready, output wire [W-1:0] r_data,    // DIR 1
    output wire fault,
    // DUT side
    output wire d_valid, output wire [W-1:0] d_data, input wire d_credit,  // DIR 0: into the DUT rx
    input wire u_valid, input wire [W-1:0] u_data, output wire u_credit    // DIR 1: from the DUT tx
);
    reg [LAT-1:0] vd; reg [W-1:0] dd [0:LAT-1]; reg [LAT-1:0] cd;
    wire sv, sc; wire [W-1:0] sd;
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin vd <= 0; cd <= 0; end
        else begin vd <= {vd[LAT-2:0], sv}; cd <= {cd[LAT-2:0], sc}; end
    always @(posedge clk) begin dd[0] <= sd; for (i = 1; i < LAT; i = i + 1) dd[i] <= dd[i-1]; end
    generate if (DIR == 0) begin : g_in
        wire lv; wire [W-1:0] ld;
        integer lost;
        always @(posedge clk or negedge rst_n) if (!rst_n) lost <= 0; else if (cd[LAT-1] && lost < LEAK) lost <= lost + 1;
        ot_link_credit_tx #(.W(W), .CRED(DEPTH + CRED_BIAS)) tx(.clk(clk), .rst_n(rst_n), .i_valid(t_valid), .i_ready(t_ready),
            .i_data(t_data), .l_valid(lv), .l_data(ld), .l_credit(cd[LAT-1] && lost >= LEAK));
        assign sv = lv; assign sd = ld; assign sc = d_credit;
        assign d_valid = vd[LAT-1]; assign d_data = dd[LAT-1];
        assign r_valid = 1'b0; assign r_data = '0; assign u_credit = 1'b0; assign fault = 1'b0;
    end else begin : g_out
        wire lc;
        ot_link_credit_rx #(.W(W), .DEPTH(DEPTH)) rx(.clk(clk), .rst_n(rst_n), .l_valid(vd[LAT-1]), .l_data(dd[LAT-1]),
            .l_credit(lc), .o_valid(r_valid), .o_ready(r_ready), .o_data(r_data), .fault(fault));
        assign sv = u_valid; assign sd = u_data; assign sc = lc; assign u_credit = cd[LAT-1];
        assign t_ready = 1'b0; assign d_valid = 1'b0; assign d_data = '0;
    end endgenerate
endmodule
