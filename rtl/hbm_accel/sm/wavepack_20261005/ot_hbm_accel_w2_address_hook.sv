`timescale 1ns/1ps
// Delta is compiler-bound descriptor metadata carried in the SAME op channel
// and captured only at actual issue launch. No allocation/span claim is made.
module ot_hbm_accel_w2_address_hook #(
    parameter integer ENABLE=0,
    parameter integer RW=12
) (
    input wire pair_active,
    input wire pair_shape_bound,
    input wire [6:0] pair_delta,
    input wire issue_v,
    input wire issue_row_ok,
    input wire [RW:0] virtual_row,
    input wire [6:0] absolute_xa,
    output wire [6:0] selected_xa,
    output wire fault
);
    wire [6:0] b_xa=absolute_xa+pair_delta;
    assign selected_xa=(ENABLE && pair_active && virtual_row>=2)?b_xa:absolute_xa;
    assign fault=ENABLE && pair_active && issue_v && issue_row_ok &&
                 (!pair_shape_bound || virtual_row>=4);
endmodule
