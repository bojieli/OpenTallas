`timescale 1ns/1ps
// Input is the die's delivered timed synchronous reset. This is a parallel
// local capture, never another asynchronous synchronizer. One edge both ways.
(* keep_hierarchy="yes", keep="yes" *)
module ot_s81hd_rst_capture #(parameter integer TAG=0) (
    input wire clk, rst_n_in,
    output wire rst_n_out
);
    (* keep="yes", dont_touch="yes" *) reg q;
`ifdef OT_S81HD_MUT_RST_ASYNC
    always @(posedge clk or negedge rst_n_in)
        if(!rst_n_in) q<=1'b0;else q<=rst_n_in;
`else
    always @(posedge clk) q <= rst_n_in;
`endif
    assign rst_n_out=q;
endmodule
