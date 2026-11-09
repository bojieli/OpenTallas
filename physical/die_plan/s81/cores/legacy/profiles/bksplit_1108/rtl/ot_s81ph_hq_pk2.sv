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
    // PINCOPY (face_guard: one pin per capture flop, as OT_HB_PINCOPY on the hist banks): the slice multicasts each
    // select/valid D to one pin per kept copy (0 cycles); copy k of plane p = bits [W*(3*p+k)] (k 0 s / 1 sg / 2 sh)
    input  wire [3*NP*W-1:0] i1_s_dc,
    input  wire [NP-1:0]   i_ingc,
    input  wire [NP-1:0]   i_flc,       // = i_ing && i0_last, formed in the slice (no logic before a P face flop)
    input  wire [W*EW-1:0] c2_p,
    input  wire [3*NP*W-1:0] c3_sel_dc,
    input  wire [NP-1:0]   c2_vc,
    input  wire [NP-1:0]   c2_flc,
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
    // DIE-S81-81 2026-11-08 (reset tree redesign): rst_n port drives only this relay; assertion stays asynchronous,
    // release is 3 edges later (2 sync + 1 tree).  Region 0 = u_pi, 1 = u_ps, 2 = the kept select/valid copies.  Fixes the
    // rst_n recovery misses (port -> 1996 async clears through a BUFx2 chain, TT -23.68 after the one ECO).
    wire [2:0] rst_q;
    ot_s81ph_hq_pk2_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rst_q));
`ifdef OT_PK2_MUT_C   // bench mutant: sweep packer never leaves reset
    wire rst_ps = 1'b0;
`else
    wire rst_ps = rst_q[1];
`endif
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
            always @(posedge clk) begin s <= (gg == 2) ? c3_sel_dc[W*(3*gg) +: W] : i1_s_dc[W*(3*gg) +: W]; sg <= i1_s_dc[W*(3*gg+1) +: W]; sh <= i1_s_dc[W*(3*gg+2) +: W]; end
`else
            always @(posedge clk) begin s <= i1_s_dc[W*(3*gg) +: W]; sg <= i1_s_dc[W*(3*gg+1) +: W]; sh <= i1_s_dc[W*(3*gg+2) +: W]; end
`endif
            always @(posedge clk or negedge rst_q[2])
                if (!rst_q[2]) begin v <= 1'b0; f <= 1'b0; end else begin v <= i_ingc[gg]; f <= i_flc[gg]; end
            assign i1_s_pl[W*gg +: W] = s; assign i1_s_plg[W*gg +: W] = sg; assign i1_s_plh[W*gg +: W] = sh; assign i1_v_pl[gg] = v; assign i1_fl_pl[gg] = f;
        end
        for (gg = 0; gg < NP; gg = gg + 1) begin : g_c3c
            (* keep = "true" *) reg [W-1:0] s, sg, sh;
            (* keep = "true" *) reg v, f;
            always @(posedge clk) begin s <= c3_sel_dc[W*(3*gg) +: W]; sg <= c3_sel_dc[W*(3*gg+1) +: W]; sh <= c3_sel_dc[W*(3*gg+2) +: W]; end
            always @(posedge clk or negedge rst_q[2])
`ifdef OT_PK2_MUT_A   // bench mutant: plane 0 sweep flush copy takes c2_v instead of c2_fl
                if (!rst_q[2]) begin v <= 1'b0; f <= 1'b0; end else begin v <= c2_vc[gg]; f <= (gg == 0) ? c2_vc[gg] : c2_flc[gg]; end
`else
                if (!rst_q[2]) begin v <= 1'b0; f <= 1'b0; end else begin v <= c2_vc[gg]; f <= c2_flc[gg]; end
`endif
            assign c3_sel_pl[W*gg +: W] = s; assign c3_sel_plg[W*gg +: W] = sg; assign c3_sel_plh[W*gg +: W] = sh; assign c3_v_pl[gg] = v; assign c3_fl_pl[gg] = f;
        end
    endgenerate
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_pi (
        .clk(clk), .rst_n(rst_q[0]), .i_v(i1_v_pl), .i_fl(i1_fl_pl), .i_sel(i1_s_pl), .i_selg(i1_s_plg), .i_selh(i1_s_plh), .i_p(i1_p),
        .o_v(pi_vp), .o_lv(pi_lv), .o_line(pi_line), .o_bv(pi_bv), .o_fl(pi_fl));
    ot_s81ph_hq_pack #(.W(W), .PW(EW), .NP(NP)) u_ps (
        .clk(clk), .rst_n(rst_ps), .i_v(c3_v_pl), .i_fl(c3_fl_pl), .i_sel(c3_sel_pl), .i_selg(c3_sel_plg), .i_selh(c3_sel_plh), .i_p(c3_p),
        .o_v(ps_vp), .o_lv(ps_lv), .o_line(ps_line), .o_bv(ps_bv), .o_fl(ps_fl));
endmodule

// Reset relay for P: repo rtl/lib/ot_rst_relay.sv inlined (the legacy kit generator resolves only the profile's own
// modules), renamed so it cannot collide.  Registered, replicated, synchronous-release reset tree.
module ot_s81ph_hq_pk2_rst_relay #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

    // relay tree: stage t, region r.  Every stage is replicated per region so each copy drives only its own region.
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

    assign rst_n = relay_q[TREE_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (SYNC_STAGES < 2) $error("ot_s81ph_hq_pk2_rst_relay: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_s81ph_hq_pk2_rst_relay: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_s81ph_hq_pk2_rst_relay: REGIONS must be >= 1");
    end
`endif
endmodule
