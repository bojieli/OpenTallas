// stand-in pin source: header of ot_s81sl_xgt_xo from rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xgt_xo.sv with default parameters {}
module ot_s81sl_xgt_xo (
input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [1103:0]   ri_w, input wire [1103:0] ri_e, output wire [1103:0] ro_e, output wire [1103:0] ro_w,
    input  wire [275:0]    vi,   output wire [275:0] vo,
    input  wire [4:0]      xf_v, input wire [4:0] xf_s, input wire [5*276-1:0] xf,
    output wire [172:0]    nx_wi, output wire [172:0] nx_ei, input wire [172:0] nx_eo, input wire [172:0] nx_wo,
    output wire            dl_ev, output wire [1103:0] dl_e, output wire dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir, input wire [1103:0] ci_b,
    input  wire            is_v,  input wire [159:0] is_d,
    output wire            xw_v,  output wire [1100:0] xw_d,
    output wire            fault
);
endmodule
