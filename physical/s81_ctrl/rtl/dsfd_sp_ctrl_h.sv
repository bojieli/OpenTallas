`timescale 1ns/1ps
// dsfd_sp_ctrl_h (stream ds-control, 2026-10-08): S81 die control plane master, head-root die (ROLE 2); ports of dsfd_sp_ctrl_core.
module dsfd_sp_ctrl_h #(parameter integer USE_VM_RVALID=0, OUT_DEPTH=4, MY_ID=0, SRC_LO=0, SRC_HI=4094,
 parameter [15:0] TYPE_MASK=16'h000A) (
    input wire ck, input wire rs,
    input wire pw_v, input wire [6:0] pw_a, input wire [27:0] pw_d, input wire [7:0] prog_len, input wire [11:0] cfg_users,
    input wire i_v, output wire i_r, input wire [511:0] i_d, input wire i_l,
    output wire o_v, input wire o_r, output wire [511:0] o_d, output wire o_l,
    output wire [11:0] cv, output wire [12*84-1:0] cd, input wire [11:0] dv, input wire [12*8-1:0] dt, input wire hop_go,
    output wire vwe, output wire [13:0] vwa, output wire [511:0] vwd, output wire vre, output wire [13:0] vra, input wire [511:0] vrq, input wire vrv,
    input wire am_v, input wire [20:0] am_pos, input wire [20:0] am_tok, input wire [31:0] am_val, input wire boot_ok,
    input wire hc_v, output wire hc_r, input wire [1:0] hc_op, input wire [7:0] hc_tag, input wire [7:0] hc_user,
    input wire [20:0] hc_pos, input wire [20:0] hc_tok, output wire cpl_v, input wire cpl_r, output wire [113:0] cpl_d,
    output wire flt, output wire [15:0] fvec, output wire stk, output wire [15:0] snap
);
    dsfd_sp_ctrl_core #(.USE_VM_RVALID(USE_VM_RVALID), .OUT_DEPTH(OUT_DEPTH), .ROLE(2), .MY_ID(MY_ID), .SRC_LO(SRC_LO), .SRC_HI(SRC_HI), .TYPE_MASK(TYPE_MASK)) u (.*);
endmodule
