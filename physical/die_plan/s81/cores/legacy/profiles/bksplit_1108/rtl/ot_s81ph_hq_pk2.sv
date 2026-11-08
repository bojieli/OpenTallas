`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// DIE-S81-80 2026-11-08: bksel SPLIT logic core (opt-in OT_BKQ_SPLIT, used only by ot_s81ph_hq_slice.sv).
// The ingest packer u_pi and the sweep packer u_ps of the hierarchical quarter slice, with their input registers
// (i1_p <= i0_lane, c3_p <= c2_p) and the kept per-plane select/valid copies (g_i1c from i1_s_d / i_ing / i0_last,
// g_c3c from c3_sel_d / c2_v / c2_fl), moved here verbatim.  Same registers, same D functions, same edges: the slice
// with OT_BKQ_SPLIT is cycle-for-cycle identical to the slice without it.  Faces: every input lands in a flop of
// this module; every output is a packer output register (ot_s81ph_native_sel_pack o_* are regs).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_hq_pk2 #(
    parameter integer W  = 16,
    parameter integer EW = 37,
    parameter integer NP = 6
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [W*EW-1:0] i0_lane,
    input  wire [W-1:0]    i1_s_d,
    input  wire            i_ing,
    input  wire            i0_last,
    input  wire [W*EW-1:0] c2_p,
    input  wire [W-1:0]    c3_sel_d,
    input  wire            c2_v,
    input  wire            c2_fl,
    output wire [NP-1:0]   pi_vp,
    output wire [W-1:0]    pi_lv,
    output wire [W*EW-1:0] pi_line,
    output wire            pi_bv,
    output wire            pi_fl,
    output wire [NP-1:0]   ps_vp,
    output wire [W-1:0]    ps_lv,
    output wire [W*EW-1:0] ps_line,
    output wire            ps_bv,
    output wire            ps_fl
);
    genvar gg;
    reg [W*EW-1:0] i1_p, c3_p;
    always @(posedge clk) begin i1_p <= i0_lane; c3_p <= c2_p; end
    wire [NP*W-1:0] i1_s_pl, i1_s_plg, i1_s_plh, c3_sel_pl, c3_sel_plg, c3_sel_plh;
    wire [NP-1:0]   i1_v_pl, i1_fl_pl, c3_v_pl, c3_fl_pl;
    generate
        for (gg = 0; gg < NP; gg = gg + 1) begin : g_i1c
            (* keep = "true" *) reg [W-1:0] s, sg, sh;
            (* keep = "true" *) reg v, f;
`ifdef OT_PK2_MUT_B   // bench mutant: plane 2 ingest prefix select copy takes the sweep select
            always @(posedge clk) begin s <= (gg == 2) ? c3_sel_d : i1_s_d; sg <= i1_s_d; sh <= i1_s_d; end
`else
            always @(posedge clk) begin s <= i1_s_d; sg <= i1_s_d; sh <= i1_s_d; end
`endif
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin v <= 1'b0; f <= 1'b0; end else begin v <= i_ing; f <= i_ing && i0_last; end
            assign i1_s_pl[W*gg +: W] = s; assign i1_s_plg[W*gg +: W] = sg; assign i1_s_plh[W*gg +: W] = sh; assign i1_v_pl[gg] = v; assign i1_fl_pl[gg] = f;
        end
        for (gg = 0; gg < NP; gg = gg + 1) begin : g_c3c
            (* keep = "true" *) reg [W-1:0] s, sg, sh;
            (* keep = "true" *) reg v, f;
            always @(posedge clk) begin s <= c3_sel_d; sg <= c3_sel_d; sh <= c3_sel_d; end
            always @(posedge clk or negedge rst_n)
`ifdef OT_PK2_MUT_A   // bench mutant: plane 0 sweep flush copy takes c2_v instead of c2_fl
                if (!rst_n) begin v <= 1'b0; f <= 1'b0; end else begin v <= c2_v; f <= (gg == 0) ? c2_v : c2_fl; end
`else
                if (!rst_n) begin v <= 1'b0; f <= 1'b0; end else begin v <= c2_v; f <= c2_fl; end
`endif
            assign c3_sel_pl[W*gg +: W] = s; assign c3_sel_plg[W*gg +: W] = sg; assign c3_sel_plh[W*gg +: W] = sh; assign c3_v_pl[gg] = v; assign c3_fl_pl[gg] = f;
        end
    endgenerate
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_pi (
        .clk(clk), .rst_n(rst_n), .i_v(i1_v_pl), .i_fl(i1_fl_pl), .i_sel(i1_s_pl), .i_selg(i1_s_plg), .i_selh(i1_s_plh), .i_p(i1_p),
        .o_v(pi_vp), .o_lv(pi_lv), .o_line(pi_line), .o_bv(pi_bv), .o_fl(pi_fl));
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_ps (
        .clk(clk), .rst_n(rst_n), .i_v(c3_v_pl), .i_fl(c3_fl_pl), .i_sel(c3_sel_pl), .i_selg(c3_sel_plg), .i_selh(c3_sel_plh), .i_p(c3_p),
        .o_v(ps_vp), .o_lv(ps_lv), .o_line(ps_line), .o_bv(ps_bv), .o_fl(ps_fl));
endmodule
