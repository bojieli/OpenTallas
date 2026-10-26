`timescale 1ns/1ps
// FP32 lane (owner decision 16, 2026-10-24): every LAT-4 / LAT-5 binary32 add (and the serial-chain multiply) that a
// 1.2 GHz single-clock serial chain would use, cycle-aligned against the LAT-3 adder / multiplier
// (ot_hdc_fp32_add_fast / ot_hdc_fp32_mul_fast, rtl/hdc/ot_hdc_fastfp.sv), every output bit {valid_out, err, y}.
// Driver: tb_fp32_lat4_eq.cpp (directed special-value cross product, then biased random).
module tb_fp32_lat4_eq (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                        output wire [15:0] mism);
    wire [31:0] ya, ym; wire [1:0] ea, em; wire va, vm;
    ot_hdc_fp32_add_fast u_ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya), .err(ea), .valid_out(va));
    ot_hdc_fp32_mul_fast u_rm (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ym), .err(em), .valid_out(vm));
    reg [34:0] da [1:4];
    reg [34:0] dm [1:4];
    integer i;
    always @(posedge clk) begin
        da[1] <= {va, ea, ya}; dm[1] <= {vm, em, ym};
        for (i = 2; i <= 4; i = i + 1) begin da[i] <= da[i-1]; dm[i] <= dm[i-1]; end
    end
    `define ADUT(idx, L, INST) \
        wire [31:0] y``idx; wire [1:0] e``idx; wire v``idx; \
        INST u``idx (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y``idx), .err(e``idx), .valid_out(v``idx)); \
        assign mism[idx] = rst_n && ({v``idx, e``idx, y``idx} != da[L - 3]);
    `define MDUT(idx, L, INST) \
        wire [31:0] y``idx; wire [1:0] e``idx; wire v``idx; \
        INST u``idx (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y``idx), .err(e``idx), .valid_out(v``idx)); \
        assign mism[idx] = rst_n && ({v``idx, e``idx, y``idx} != dm[L - 3]);
    // adders
    `ADUT(0, 4, ot_hdc_fp32_add_lat4_pooln_sh)     // add_lat LAT 4 (cut C_B)
    `ADUT(1, 4, ot_hdc_fp32_add_lat4i_sh)          // add_lat LAT 4 input cut (C_A)
    `ADUT(2, 5, ot_hdc_fp32_add_lat5_sh)           // add_lat LAT 5
    `ADUT(3, 4, ot_hdc_fp32_add_f12_l4)            // f12 LAT 4 (CUTS 101010)
    `ADUT(4, 5, ot_hdc_fp32_add_f12_l5)            // f12 LAT 5 (101011)
    `ADUT(5, 5, ot_hdc_fp32_add_f12_l5x)           // f12 LAT 5 (1101010)
    `ADUT(6, 5, ot_hdc_fp32_add_f12_l5s)           // f12 LAT 5 (101110)
    // S81 ve native-32 adder (LAT 4) and multiplier (LAT 5): second operand copies tied to the first
    wire [31:0] y7, y7b; wire [1:0] e7; wire v7;
    ot_s81sl_ve_fadd u7 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a), .b(b), .b2(b), .y(y7), .y2(y7b), .err(e7), .valid_out(v7));
    assign mism[7] = rst_n && (({v7, e7, y7} != da[1]) || (y7b != y7));
    // multipliers
    `MDUT(8, 5, ot_hdc_fp32_mul_f12_l5)            // f12 LAT 5
    `MDUT(9, 6, ot_hdc_fp32_mul_f12_l6)            // f12 LAT 6
    `MDUT(10, 4, ot_hdc_fp32_mul_lat4_sh)          // mul_lat LAT 4
    `MDUT(11, 5, ot_hdc_fp32_mul_lat5_sh)          // mul_lat LAT 5
    wire [31:0] y12, y12b; wire [1:0] e12; wire v12;
    ot_s81sl_ve_fmul u12 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .a2(a), .b(b), .b2(b), .y(y12), .y2(y12b), .err(e12), .valid_out(v12));
    assign mism[12] = rst_n && (({v12, e12, y12} != dm[2]) || (y12b != y12));
    `ADUT(13, 6, ot_hdc_fp32_add_lat6_sh)          // add_lat LAT 6 (reference point)
    assign mism[15:14] = 2'b0;
endmodule

// fixed-parameter shells (the timing tops of fp32_lat4_sta.sh use the same shells)
module ot_hdc_fp32_add_lat4_pooln_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                      output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_add_lat4i_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                 output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(4), .CUTS(1)) u (.*);
endmodule
module ot_hdc_fp32_add_lat5_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(5)) u (.*);
endmodule
module ot_hdc_fp32_add_lat6_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(6)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat4_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(4)) u (.*);
endmodule
module ot_hdc_fp32_mul_lat5_sh (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                                output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5)) u (.*);
endmodule
