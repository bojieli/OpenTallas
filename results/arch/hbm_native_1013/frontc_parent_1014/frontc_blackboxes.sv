(* blackbox *) module ot_hbm_accel_smh_fc_b #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [554+TAGW-1:0] li, input wire [2:0] fi, input wire [2068:0] xi,
    output wire [2068:0] bout, output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r3a
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_bc #(parameter integer MAX_OUT = 512, parameter integer PIO = 2, parameter integer TAGW = 16) (
    input  wire          clk, rst_a,
    input  wire          fd_v,  input wire [55:0] fd_d, output wire fd_ret,
    output wire          fq_v,  output wire [41:0] fq_d, input wire fq_ret,
    input  wire          fp_v,  input wire [1097:0] fp_d,
    input  wire          fsv,   output wire sv_o,
    output wire [35:0]   k0_mv, output wire [1087:0] k0_d, input wire [35:0] k1_sr,
    input  wire [802+TAGW-1:0] r3a, output wire [802+TAGW-1:0] fo_row3
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_is #(
    parameter integer ENABLE_INT8 = 1, parameter integer PIPE_INT8 = 2, parameter integer IL = 8,
    parameter integer RMAX = 4096, parameter integer XD = 128, parameter integer PIO = 2, parameter integer HAZ = 1,
    parameter integer NOUT = 4
) (
    input  wire          clk, rst_a,
    input  wire [35:0]   k0_mv, input wire [1087:0] k0_d, output wire [35:0] k1_sr,
    input  wire          fs_v,  input wire [$clog2(RMAX)+1+16+8+1+2+$clog2(XD)-1:0] fs_d, output wire fs_ret,
    input  wire          fr_rl, output wire [2:0] fo_pbz,
    input  wire          sv_i,
    output wire [3+$clog2(RMAX)+1+$clog2(IL)+$clog2(XD)+1056-1:0] lt0, lt1,
    output wire [3+$clog2(RMAX)+1+$clog2(IL)+$clog2(XD)+544-1:0]  lb0, lb1,
    output wire [11:0]   fm
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_t #(parameter integer ENABLE_INT8 = 1, parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [1066+TAGW-1:0] li, input wire [2:0] fi,
    output wire [802+TAGW-1:0] rout, output wire [802+TAGW-1:0] r0a
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_xl #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] fx_b, output wire [2068:0] xw_w, xw_e,
    input  wire [802+TAGW-1:0] r0a, output wire [802+TAGW-1:0] fo_row0
);
endmodule
(* blackbox *) module ot_hbm_accel_smh_fc_xr #(parameter integer TAGW = 16) (
    input  wire clk, rst_a,
    input  wire [2068:0] xi, output wire [2068:0] xo,
    input  wire [554+TAGW-1:0] li, output wire [554+TAGW-1:0] lo,
    input  wire [2:0]    fi, output wire [2:0]    fo
);
endmodule
