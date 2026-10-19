`timescale 1ns/1ps
// ot_link_credit_tx_rc (S81-COLL bank64 safe3, 10-19): ot_link_credit_tx DFREE 1 with the "credit in hand" flag
// (cnt != 0) held as NR kept REGISTERED copies computed from the next count, so the caller's ready fans out from
// several flops (one per consumer group) instead of one compare net (the lane's out_ready drove the endpoint FIFO's
// 18 read groups + drain logic).  l_data loads every cycle (DFREE 1): the receiver samples l_data only with l_valid,
// so a non-send cycle's data is a don't-care and send reaches only l_valid / cnt (the 1,108-load send-gated
// l_data enable is gone).  Same l_valid / l_credit / ready cycle behaviour as ot_link_credit_tx.
module ot_link_credit_tx_rc #(parameter integer W=8, CRED=8, NR=3)(
    input wire clk, rst_n,
    input wire i_valid, output wire [NR-1:0] i_ready, input wire [W-1:0] i_data,
    (* keep *) output reg l_valid, output reg [W-1:0] l_data, input wire l_credit
);
    localparam integer CW = $clog2(CRED + 1);
    reg cr_q;
    reg [CW-1:0] cnt;
    (* keep = "true" *) reg [NR-1:0] nz;          // copies of (cnt != 0)
    (* keep = "true" *) reg nz_s;                 // copy used by send
    assign i_ready = nz;
    wire send = i_valid && nz_s;
    wire [CW-1:0] cnt_n = cnt + CW'(cr_q) - CW'(send);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin cr_q <= 1'b0; cnt <= CW'(CRED); l_valid <= 1'b0; nz <= {NR{CRED != 0}}; nz_s <= (CRED != 0); end
        else begin
            cr_q <= l_credit;
            cnt <= cnt_n;
            l_valid <= send;
            nz <= {NR{cnt_n != 0}};
            nz_s <= cnt_n != 0;
        end
    always @(posedge clk) l_data <= i_data;
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && (nz !== {NR{cnt != 0}} || nz_s !== (cnt != 0))) $fatal(1, "ot_link_credit_tx_rc: ready copy differs");
`endif
endmodule
