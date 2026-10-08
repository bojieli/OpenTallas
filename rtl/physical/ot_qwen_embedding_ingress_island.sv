`timescale 1ns/1ps
// Separately harden the existing input capture state at the leaf's request pins.
// This is not an extra pipeline stage. No input/reset timing exception is used.
module ot_qwen_embedding_ingress_island #(parameter integer AW=18)(
    input wire clk, rst_n,
    input wire [AW-1:0] address,
    input wire valid, credit,
    (* keep="true", dont_touch="true" *) output reg [AW-1:0] address_q, address_n,
    (* keep="true", dont_touch="true" *) output reg valid_q, valid_n, credit_q, credit_n
);
    (* keep="true", dont_touch="true" *) always @(posedge clk) begin
        address_q<=address;address_n<=~address;
    end
    (* keep="true", dont_touch="true" *) always @(posedge clk or negedge rst_n)
        if(!rst_n) begin valid_q<=0;valid_n<=1;credit_q<=0;credit_n<=1;end
        else begin valid_q<=valid;valid_n<=~valid;credit_q<=credit;credit_n<=~credit;end
endmodule
