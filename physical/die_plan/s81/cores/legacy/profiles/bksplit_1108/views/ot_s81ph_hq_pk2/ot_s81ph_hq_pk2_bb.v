// DIE-S81-80 11-08: blackbox of the bksel SPLIT logic child (hard macro, view profiles/bksplit_1108/views/ot_s81ph_hq_pk2)
(* blackbox *)
module ot_s81ph_hq_pk2 (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [591:0] i0_lane,
    input  wire [15:0]    i1_s_d,
    input  wire            i_ing,
    input  wire            i0_last,
    input  wire [591:0] c2_p,
    input  wire [15:0]    c3_sel_d,
    input  wire            c2_v,
    input  wire            c2_fl,
    output wire [5:0]   pi_vp,
    output wire [15:0]    pi_lv,
    output wire [591:0] pi_line,
    output wire            pi_bv,
    output wire            pi_fl,
    output wire [5:0]   ps_vp,
    output wire [15:0]    ps_lv,
    output wire [591:0] ps_line,
    output wire            ps_bv,
    output wire            ps_fl
);
endmodule
