`timescale 1ns/1ps
// SVC7 arithmetic experiment, not a released hgrp implementation.
// Each kept bit-cone independently retains only the requested golden output.
// Native mapped census must pass for EVERY cone before a layout gate.
(* keep_hierarchy *)
module ot_s81svc7_add_bit #(parameter integer BIT = 0) (
    input wire clk, rst_n,
    input wire [64:0] d,
    output wire q
);
    reg r0, r1;
    always @(posedge clk) begin r0 <= rst_n; r1 <= r0; end
    wire [64:0] pin_q;
    ot_hdc_v41x_kreg #(.W(65), .R(0)) u_pin (
        .clk(clk), .rst_n(r1), .d(d), .q(pin_q));
    wire [31:0] y;
    wire [1:0] err;
    wire valid_out;
    ot_hdc_fp32_add_f12_l4 u_add (
        .clk(clk), .rst_n(r1), .valid_in(pin_q[64]),
        .a(pin_q[63:32]), .b(pin_q[31:0]),
        .y(y), .err(err), .valid_out(valid_out));
    wire [34:0] result = {valid_out, err, y};
    assign q = result[BIT];
endmodule

module ot_s81svc7_add (
    input wire clk, rst_n, valid_in,
    input wire [31:0] a, b,
    output wire [31:0] y,
    output wire [1:0] err,
    output wire valid_out
);
    reg rst0, rst1;
    always @(posedge clk) begin rst0 <= rst_n; rst1 <= rst0; end
    wire [64:0] pins [0:1];
    wire [1:0] region_rst;
    genvar g, bit_i;
    generate for (g=0; g<2; g=g+1) begin : g_region
        ot_hdc_v41x_kreg #(.W(1), .R(0)) u_reset (
            .clk(clk), .rst_n(rst1), .d(rst1), .q(region_rst[g]));
        ot_hdc_v41x_kreg #(.W(65), .R(0)) u_pins (
            .clk(clk), .rst_n(region_rst[g]), .d({valid_in,a,b}), .q(pins[g]));
    end endgenerate
    wire [34:0] result;
    generate for (bit_i=0; bit_i<35; bit_i=bit_i+1) begin : g_bit
        ot_s81svc7_add_bit #(.BIT(bit_i)) u_bit (
            .clk(clk), .rst_n(region_rst[bit_i/18]),
            .d(pins[bit_i/18]), .q(result[bit_i]));
    end endgenerate
    assign {valid_out,err,y}=result;
endmodule
