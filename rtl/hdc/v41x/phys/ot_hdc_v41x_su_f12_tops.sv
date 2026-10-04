`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL VEHICLE ONLY (hbm-fmax-su 2026-10-04): fixed-parameter tops of the stream unit's special-function pieces
// at the 1.2 GHz depths (MLAT 6 / ALAT 5), so a route needs no -chparam (yosys 0.68 asserts on a -chparam top that
// the sources also instantiate with parameters).
// ---------------------------------------------------------------------------
module ot_hdc_v41x_exp_m6a5 (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo,
                             output wire fault);
    ot_hdc_v41x_exp #(.LM(6), .LA(5)) u (.*);
endmodule
module ot_hdc_v41x_rsqrt_m6a5 (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo,
                               output wire fault);
    ot_hdc_v41x_rsqrt #(.LM(6), .LA(5)) u (.*);
endmodule
module ot_hdc_v41x_softplus_m6a5 (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] sp, r,
                                  output wire vo, output wire fault);
    ot_hdc_v41x_softplus #(.LM(6), .LA(5)) u (.*);
endmodule
module ot_hdc_v41x_vec_side_m6a5 (input wire clk, rst_n, v, input wire [2:0] fn, input wire [31:0] x,
                                  input wire [2:0] fn_out, output wire [31:0] y, output wire fault);
    ot_hdc_v41x_vec_side #(.MLAT(6), .ALAT(5)) u (.*);
endmodule
