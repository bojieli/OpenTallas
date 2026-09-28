`timescale 1ns/1ps
// Parameter-free route tops of the blocks multi-token prediction changes
// (Yosys cannot re-derive a parameter-overridden top whose children are
// derived after it).  MP: the lane multiplier.
module ot_mtp_me_g2_m1 #(parameter integer MP = 1) (
    input wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input wire [15:0] i_nout, i_tiles, i_k, input wire i_wsrc, input wire [23:0] i_wbase, i_ts, i_ks, i_js,
    i_xbase, i_xks, i_xjs, i_xcs, input wire [2:0] i_jsh, input wire [1:0] i_split, i_hg, input wire [23:0] i_ogs,
    input wire i_round, input wire [23:0] i_obase, i_ots, i_ojs, input wire i_mmode, i_oen, i_amax,
    input wire [2:0] i_m, input wire [23:0] i_xps, i_ops,
    output wire wrom_re, output wire [23:0] wrom_addr, input wire [2*16*16-1:0] wrom_q,
    output wire kv_re, output wire [2*24-1:0] kv_addr, input wire [2*16*32-1:0] kv_q,
    output wire [MP*2-1:0] x_re, output wire [MP*2*24-1:0] x_addr, input wire [MP*2*32-1:0] x_q,
    output wire ov, output wire [MP*2-1:0] o_we, output wire [MP*2*24-1:0] o_addr, output wire [MP*2*16-1:0] o_mask,
    output wire [MP*2*16*32-1:0] o_data, output wire [MP*16-1:0] am_idx, output wire [MP*32-1:0] am_val,
    output wire [MP-1:0] am_any, output wire [15:0] progress, output wire fault);
    ot_hdc_v41_matvec #(.W(16), .G(2), .IL(8), .AW(24), .NW(16), .MP(MP)) u (.*);
endmodule

module ot_mtp_me_g2_m4 (
    input wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input wire [15:0] i_nout, i_tiles, i_k, input wire i_wsrc, input wire [23:0] i_wbase, i_ts, i_ks, i_js,
    i_xbase, i_xks, i_xjs, i_xcs, input wire [2:0] i_jsh, input wire [1:0] i_split, i_hg, input wire [23:0] i_ogs,
    input wire i_round, input wire [23:0] i_obase, i_ots, i_ojs, input wire i_mmode, i_oen, i_amax,
    input wire [2:0] i_m, input wire [23:0] i_xps, i_ops,
    output wire wrom_re, output wire [23:0] wrom_addr, input wire [2*16*16-1:0] wrom_q,
    output wire kv_re, output wire [2*24-1:0] kv_addr, input wire [2*16*32-1:0] kv_q,
    output wire [4*2-1:0] x_re, output wire [4*2*24-1:0] x_addr, input wire [4*2*32-1:0] x_q,
    output wire ov, output wire [4*2-1:0] o_we, output wire [4*2*24-1:0] o_addr, output wire [4*2*16-1:0] o_mask,
    output wire [4*2*16*32-1:0] o_data, output wire [4*16-1:0] am_idx, output wire [4*32-1:0] am_val,
    output wire [4-1:0] am_any, output wire [15:0] progress, output wire fault);
    ot_hdc_v41_matvec #(.W(16), .G(2), .IL(8), .AW(24), .NW(16), .MP(4)) u (.*);
endmodule

module ot_mtp_qe_m4 (
    input wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input wire [1:0] i_mode, input wire i_fp4, input wire [23:0] i_xbase, input wire [7:0] i_nb,
    input wire [15:0] i_nout, i_tiles, input wire [23:0] i_wbase, input wire i_ind, input wire [23:0] i_ibase,
    i_istride, i_obase, input wire [2:0] i_m, input wire [23:0] i_xps, i_ops,
    output wire vi_re, output wire [23:0] vi_addr, input wire [31:0] vi_q,
    output wire xr_re, output wire [23:0] xr_addr, input wire [1023:0] xr_q,
    output wire [3:0] w_we, output wire [4*24-1:0] w_addr, output wire [4*32-1:0] w_mask,
    output wire [4*1024-1:0] w_data, output wire qr_re, output wire [23:0] qr_addr, input wire [16*272-1:0] qr_q,
    output wire fault);
    wire i_unrounded = 1'b0;
    ot_hdc_v41_qe #(.MP(4)) u (.*);
endmodule

module ot_mtp_he_m4 (
    input wire clk, input wire rst_n, input wire go, output wire ready, output wire idle,
    input wire [15:0] i_nout, i_k, input wire [23:0] i_wbase, i_xbase, i_obase,
    input wire [2:0] i_m, input wire [23:0] i_xps, i_ops,
    output wire hr_re, output wire [23:0] hr_addr, input wire [8*3*32-1:0] hr_q,
    output wire [4*8-1:0] x_re, output wire [4*8*24-1:0] x_addr, input wire [4*8*32-1:0] x_q,
    output wire [3:0] o_we, output wire [4*24-1:0] o_addr, output wire [4*32-1:0] o_mask,
    output wire [4*1024-1:0] o_data, output wire fault);
    ot_hdc_v41_hcproj #(.MP(4)) u (.*);
endmodule

module ot_mtp_accept8 (
    input wire clk, input wire rst_n, input wire start_v, input wire [15:0] start_tok,
    input wire tokx_v, input wire [2:0] tokx_slot, input wire [15:0] tokx_tok,
    input wire amax_v, input wire [2:0] amax_slot, input wire [15:0] amax_tok,
    input wire acc_v, input wire [2:0] acc_g, output wire [8*16-1:0] stok, output wire [8*16-1:0] ttok,
    output wire acc_done, output wire acc_any, output wire [2:0] acc_a, output wire [3:0] n_emit,
    output wire [15:0] bonus);
    ot_hdc_accept #(.NSLOT(8), .NW(16)) u (.*);
endmodule
