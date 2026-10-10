`timescale 1ns/1ps
// kv-die 2026-10-09: credit bridge.  A producer holding D credits pushes words (in_v, captured at the pin flop) into a
// D-word buffer; a word leaves (out_v registered) only with a consumer credit in hand (OC initial, out_cr returns one,
// captured at the pin); in_cr is one registered pulse per word that leaves.  An arrival into a full buffer is a sticky
// fault (the producer ignored its credits).
module ot_qkvd_cbridge #(
    parameter integer W  = 528,
    parameter integer D  = 4,
    parameter integer OC = 4
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    input  wire [W-1:0] in_d,
    output reg          in_cr,
    output reg          out_v,
    output reg  [W-1:0] out_d,
    input  wire         out_cr,
    output reg          fault
);
    reg         iv, cq;
    reg [W-1:0] id;
    always @(posedge clk) id <= in_d;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin iv <= 1'b0; cq <= 1'b0; end else begin iv <= in_v; cq <= out_cr; end
    wire         empty, full;
    wire [W-1:0] head;
    wire [$clog2(D+1)-1:0] cnt;
    reg  [7:0]   oc;
    wire         pop = !empty && (oc != 0);
    ot_qkvd_fifo #(.W(W), .D(D)) u_q (.clk(clk), .rst_n(rst_n), .push(iv), .din(id), .pop(pop), .dout(head),
                                      .empty(empty), .full(full), .count(cnt));
    always @(posedge clk) if (pop) out_d <= head;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin out_v <= 1'b0; in_cr <= 1'b0; oc <= 8'(OC); fault <= 1'b0; end
        else begin
            out_v <= pop;
            in_cr <= pop;
            oc <= oc - (pop ? 8'd1 : 8'd0) + (cq ? 8'd1 : 8'd0);
            if (iv && full && !pop) fault <= 1'b1;
        end
endmodule
