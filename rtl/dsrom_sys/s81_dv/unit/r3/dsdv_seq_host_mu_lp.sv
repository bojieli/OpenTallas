`timescale 1ns/1ps
// STW-S81c-COLLA3 10-22, STEWARD-S81c decision (b): the hardened sequencer parent for the die's u_seq.  It presents EXACTLY
// the ports of dsdv_seq_host_mu (one ck, one rst_n, f_mc / t_mf, MU t_kd) so the die binds it with no interface change.
//   * u_core = dsdv_seq_host_c_r3_lp, the landed three-region cluster (hard children u_l0/u_l1/u_l2 + bands u_blk/u_bvc).
//     Its three regional clock roots are INTERNAL: ck_lk / ck_sq / ck_vc are all fed from the one ck port (same PLL,
//     zero phase, as clock_relationship same_pll_fixed_phase already assumed); each region keeps its own tree inside.
//   * u_hs  = dsdv_mu_hslot NSLOT 47, the MU host slot table (CLOSED view dsdv_mu_hslot-adb53b6fe), exactly as in
//     dsdv_seq_host_mu: it taps f_ks and the core's t_kd, and t_kd = {kd[53:32], ku[30:0], 1'b0}.
//   * reset: rst_n lands in registered relays (ot_rst_relay, async assert / synchronous release, one kept copy per
//     destination).  The core's regions release SYNC+TREE = 4 edges after rst_n.  The core adds its own regional reset
//     depth RB = 4 (r3_lp record reset_release_added_edges), so the hslot copy releases 4 edges later (8 total).  That
//     keeps the hslot on the same epoch as the core's units, as dsdv_seq_host_mu's shared rst_n did.
// Function = dsdv_seq_host_mu with the r3_lp compiler re-schedule (record "compiler": port offsets 0, +2 edges per landed
// crossing) and reset release +10 (rev2: +2 face landing), hslot outputs (t_kd, t_mf) +1 edge (rev2 hslot relay): tb_dsdv_seq_host_mu_lp.sv locksteps it against dsdv_seq_host_c_r3_rsref + dsdv_mu_hslot.
// MU_LP_MUT (bench only): 1 = hslot reset on the core-region copy (epoch slip), 2 = t_kd without the hslot slot word.
module dsdv_seq_host_mu_lp #(parameter integer V = 276, parameter integer STAGE = 0, parameter integer MUT = 0,
                             parameter integer NSLOT = 47, parameter integer MU_MUT = 0,
                             parameter integer CHILD_MUT = 0, parameter integer RL = 1, parameter integer MU_LP_MUT = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [V-1:0]  vi_s, output wire [V-1:0] vo_s,
    input  wire [V-1:0]  vi_n, output wire [V-1:0] vo_n,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    input  wire [25:0]   f_mc,   output wire [3:0]  t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d
);
    // rev2 (gate 15:57 textbook.reset_landing): rst_n lands at the face in TWO registered stages (rst_l0 -> rst_l1, the
    // only rst_n sinks), then the relays fan out from rst_l1 (assert still asynchronous through rst_l's clear).  +2 edges
    // on every region and on the hslot alike, so the epochs are unchanged.
    (* keep = "true", dont_touch = "true" *) reg rst_l0, rst_l1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rst_l0 <= 1'b0; rst_l1 <= 1'b0; end
        else        begin rst_l0 <= 1'b1; rst_l1 <= rst_l0; end
    wire [2:0] rr;   // region reset copies: lk, sq, vc
    wire [0:0] rh;   // hslot reset copy (+RB = 4 more edges, +1 for the hslot relay stage below)
    ot_rst_relay #(.REGIONS(3), .SYNC_STAGES(2), .TREE_STAGES(2)) u_rr (.clk(ck), .rst_n_in(rst_l1), .rst_n(rr));
    ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(7)) u_rh (.clk(ck), .rst_n_in(rst_l1), .rst_n(rh));
    wire [53:0] kd;
    dsdv_seq_host_c_r3_lp
`ifndef SYNTHESIS
    #(.V(V), .STAGE(STAGE), .CHILD_MUT(CHILD_MUT), .RL(RL), .MUT(MUT))
`endif
    u_core (.ck_lk(ck), .ck_sq(ck), .ck_vc(ck), .rst_n_lk(rr[0]), .rst_n_sq(rr[1]), .rst_n_vc(rr[2]),
        .tap_k(tap_k), .sink_k(sink_k), .vi_s(vi_s), .vo_s(vo_s), .vi_n(vi_n), .vo_n(vo_n), .f_host(f_host),
        .t_host(t_host), .f_lf(f_lf), .f_ks(f_ks), .t_kd(kd), .s_j(s_j), .s_jd_w(s_jd_w), .s_jd_e(s_jd_e),
        .s_hw_w(s_hw_w), .s_hw_e(s_hw_e), .s_hc_w(s_hc_w), .s_hc_e(s_hc_e), .st_rg_w(st_rg_w), .st_rg_e(st_rg_e),
        .cw_v(cw_v), .cw_a(cw_a), .cw_d(cw_d));
    wire [31:0] ku;
    // rev2 (gate 15:57 textbook.wire_reach, kd 0.7-0.8 mm from u_l0's top face to the hslot under it): ONE registered
    // relay stage on every hslot input (f_ks, kd, f_mc), with its reset release +1 (u_rh TREE 7) -- the whole hslot
    // timeline moves +1 edge, so t_kd (kd part from the same kd_r) and t_mf leave 1 edge later than dsdv_seq_host_mu
    // (static schedule constant; every other port unchanged).  The relays are kept so placement can put them mid-hop.
    (* keep = "true", dont_touch = "true" *) reg [52:0] ks_r;
    (* keep = "true", dont_touch = "true" *) reg [53:0] kd_r;
    (* keep = "true", dont_touch = "true" *) reg [25:0] mc_r;
    always @(posedge ck) begin ks_r <= f_ks; kd_r <= kd; mc_r <= f_mc; end
    dsdv_mu_hslot
`ifndef SYNTHESIS
    #(.NSLOT(NSLOT), .MUT(MU_MUT))
`endif
    u_hs (.ck(ck), .rst_n((MU_LP_MUT == 1) ? rr[0] : rh[0]), .f_ks(ks_r), .f_kd(kd_r), .f_mc(mc_r), .t_ku(ku), .t_mf(t_mf));
    // kd[31:0] = 0 by the unit's contract (sh_sq kd_o): the slot word rides those bits
    assign t_kd = (MU_LP_MUT == 2) ? kd : {kd_r[53:32], ku[30:0], 1'b0};
endmodule
