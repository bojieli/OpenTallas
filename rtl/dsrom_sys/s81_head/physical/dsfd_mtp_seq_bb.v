// Exact port shell for CLOSED dsfd_mtp_seq_c (c67a71fe5), route only.
(* blackbox *) module dsfd_mtp_seq #(
    parameter integer FLIT = 512, parameter integer NW = 21, parameter integer USER_W = 10,
    parameter integer MAXU = 8, parameter integer G = 5,
    parameter integer SW = USER_W + 3 * NW + 4, parameter integer DW = USER_W + 3 + NW
) (
    input  wire [0:0]        ck,
    input  wire [0:0]        rst,
    input  wire [2*NW-1:0]   f_cfg,          // {glen, plen} (static)
    input  wire [0:0]        f_rv,  input  wire [FLIT-1:0] f_rd,  output wire [0:0] t_rg,   // RESULT in
    output wire [0:0]        t_tv,  output wire [FLIT-1:0] t_td,  input  wire [0:0] f_tg,   // token return out
    output wire [0:0]        t_sv,  output wire [SW-1:0]   t_sd,  input  wire [0:0] f_sg,   // seed out
    input  wire [0:0]        f_wv,  input  wire [USER_W-1:0] f_wd, output wire [0:0] t_wg,  // rows ready in
    output wire [0:0]        t_hv,  output wire [DW-1:0]   t_hd,  input  wire [0:0] f_hg,   // draft-head step out
    input  wire [0:0]        f_qv,  input  wire [DW-1:0]   f_qd,  output wire [0:0] t_qg,   // draft-head result in
    output wire [2*NW+USER_W+4:0] t_acc      // {fault, acc_v, acc_u, acc_a, acc_c, acc_y} (from flops)
);
endmodule
