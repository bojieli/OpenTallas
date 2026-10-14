`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// el1011-q-kvd-head 2026-10-11 (owner textbook audit): HIERARCHICAL successor of ot_qwen_nearhbm_head_h (one q head of a
// near-HBM row engine), opt-in through `KVD_HSUB in ot_qwen_nearhbm_row_engine_h (default off).
//
// Why (route evidence): every flat head route put one clock root over 198,881-207,978 sinks on a 531-648 um outline
// (class 1), and qkd_rhead-fpb-82039e347 failed post-CTS TT -794 ps with 12,805 endpoints on boundary paths: the hid strap
// compare from the input pin straight into the 1,024 q-row capture enables (class 3 / 5, -604 ps), the 1,024-b nb_d
// register to a far output pin (-563 ps), and rst_n -> reset leaves (-170 ps).
//
// Structure (same arithmetic, same order, same lane schedule):
//   ot_qkh_lane8   HARDENED SUB-TILE x16: lanes 8t .. 8t + 7 (product unit, lane adder + loop, local P.V lanes, their q
//                  row slices), its own copy of the group control (S3 pin flops, PLAT / K-level delay lines), its own
//                  reset relay, registered outputs.  K levels 1-3 inside (lanes 0 2 4 6: level 1; 1 5: level 2; 3: level
//                  3) = the tree nodes covering products 8t .. 8t + 7 in the original tree order; the q capture compare
//                  works on the tile's pin flops (16 + 16 enables a tile instead of 1,024 from a pin).
//   ot_qkh_ktree   HARDENED SUB-TILE x1: K levels 4-7 (8 + 4 + 2 + 1 dedicated adders, original pairing) + the scale
//                  multiply + the fault OR.  Levels 4-7 used to share the lane adders of lanes 97 .. 125; those lanes now
//                  hold only levels 1-3, all inside the K drain window (KDRAIN unchanged), so the V schedule is unchanged.
//   ot_qwen_nearhbm_head_hs  parent: pin flops (S2), NRI relay stages per sub-tile (kept copies), NRK relay stages on the
//                  K partials, NRN on the node slice, one output relay on the score / faults.  The parent only holds
//                  flops; a relay hop is <= ~350 um on the 4 x 4 floorplan.
// Sub-tile RTL: rtl/hdc/nearhbm/ot_qkh_subtiles.sv.
// Latency: inputs + NRS + NRI, score + NRS + NRI + NRK + 3, node slice + NRS + NRI + NRN (the control tile's HXK / HXN, stack_h_gen.hsub).
// ---------------------------------------------------------------------------------------------------------------------

// a registered relay of D stages, kept as its own instance (copies for different sub-tiles are never merged)
module ot_qkh_relay #(parameter integer W = 1, parameter integer D = 1, parameter integer RST = 0) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    reg [W-1:0] r [0:D-1];
    integer i;
    generate if (RST != 0) begin : g_r
        always @(posedge clk or negedge rst_n)
            if (!rst_n) for (i = 0; i < D; i = i + 1) r[i] <= {W{1'b0}};
            else begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    end else begin : g_n
        always @(posedge clk) begin r[0] <= d; for (i = 1; i < D; i = i + 1) r[i] <= r[i-1]; end
    end endgenerate
    assign q = r[D-1];
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qwen_nearhbm_head_hs: the head tile as 16 ot_qkh_lane8 + 1 ot_qkh_ktree (ports = ot_qwen_nearhbm_head_h)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_nearhbm_head_hs #(
    parameter integer HD = 128,
    parameter integer H = 0,
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer LFB = 4,
    parameter integer LTW = 12,
    parameter integer NRS = 1,           // q13-rhead r2: SHARED mid-floor relay stages S2 -> S2b (one copy for all 16 sub-tiles)
    parameter integer NRI = 2,           // relay stages S2b -> sub-tile pins (one kept copy a sub-tile)
    parameter integer NRK = 2,           // relay stages sub-tile K partial -> K-tree pins
    parameter integer NRN = 2            // relay stages sub-tile node slice -> nb_d pins
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [3:0]           c_in,
    input  wire [HD*8-1:0]      row_in,
    input  wire [15:0]          e_in,
    input  wire [LTW-1:0]       lt_in,
    input  wire [1:0]           hid,
    input  wire                 q_valid_in,
    input  wire [5:0]           q_beat_in,
    input  wire [511:0]         q_data_in,
    output wire [31:0]          sc_d,
    output wire                 sc_f,
    output wire                 g_f,
    output wire [HD*32/LFB-1:0] nb_d
);
    localparam integer NT = HD / 8;
    // the sub-tiles are hardened at their defaults (ADD_LAT 7, MUL_LAT 6, SCALE 1 / sqrt(128), LTW 12)
    generate if (HD != 128 || LFB != 4 || LTW != 12 || ADD_LAT != 7 || MUL_LAT != 6 || SCALE != 32'h3DB504F3) begin : g_bad
        ot_qwen_nearhbm_head_hs_needs_HD128_LFB4 u_trap ();
    end endgenerate
    // ---- reset relay: one region a sub-tile, the K tree, the parent's own control flops ---------------------------------
    wire [NT+1:0] rr;
    ot_rst_relay #(.REGIONS(NT + 2), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rp = rr[NT + 1];
    // ---- S2: the tile pins -----------------------------------------------------------------------------------------------
    reg  [3:0]       c2;
    reg  [HD*8-1:0]  row2;
    reg  [15:0]      e2;
    reg  [LTW-1:0]   lt2;
    reg              qv2;
    reg  [5:0]       qb2;
    reg  [511:0]     qd2;
    reg  [1:0]       hid2;
    always @(posedge clk or negedge rp)
        if (!rp) begin c2[3:1] <= 3'd0; lt2 <= {LTW{1'b0}}; qv2 <= 1'b0; end
        else begin c2[3:1] <= c_in[3:1]; lt2 <= lt_in; qv2 <= q_valid_in; end
    always @(posedge clk) begin c2[0] <= c_in[0]; row2 <= row_in; e2 <= e_in; qb2 <= q_beat_in; qd2 <= q_data_in; hid2 <= hid; end
    // ---- S2b (q13-rhead r2, structural): the S-face pin flops no longer drive the 16 per-sub-tile relays directly.
    // Route evidence qkh_head_hs_ref-q13a-75e0349aa: qd2[392] (S face, y = 0) -> g_t[15].u_rid/r[0] (row 3 of the 4 x 4
    // floor, y > 560 um) = 765 ps of data path through 7 wire repeaters in ONE cycle (TT -41.92 ps; 11 endpoints, all rows
    // 2 / 3).  NRS shared stages carry every pin bit to the floor centre first, so each hop is pin -> centre (<= ~430 um)
    // and centre -> sub-tile relay (<= ~350 um).  Shared (1,577 flops a stage), not one copy a sub-tile (3,728): the
    // parent stays under 15k sinks on its clock root.  Latency + NRS on every input (HXK / HXN of the control tile).
    wire [3+LTW:0]  cs_o;                     // reset part: {c[3:1], lt, qv}
    wire [HD*8+16+6+512+2:0] ds_o;            // plain part: {c[0], row, e, qb, qd, hid}
    (* keep_hierarchy *) ot_qkh_relay #(.W(4 + LTW), .D(NRS), .RST(1)) u_rsc (.clk(clk), .rst_n(rp), .d({c2[3:1], lt2, qv2}), .q(cs_o));
    (* keep_hierarchy *) ot_qkh_relay #(.W(1 + HD*8 + 16 + 6 + 512 + 2), .D(NRS)) u_rsd (.clk(clk), .rst_n(rp),
                                                                                    .d({c2[0], row2, e2, qb2, qd2, hid2}), .q(ds_o));
    wire [3:0]       c3   = {cs_o[3+LTW:1+LTW], ds_o[HD*8+16+6+512+2]};
    wire [LTW-1:0]   lt3  = cs_o[LTW:1];
    wire             qv3  = cs_o[0];
    wire [HD*8-1:0]  row3 = ds_o[16+6+512+2 +: HD*8];
    wire [15:0]      e3   = ds_o[6+512+2 +: 16];
    wire [5:0]       qb3  = ds_o[512+2 +: 6];
    wire [511:0]     qd3  = ds_o[2 +: 512];
    wire [1:0]       hid3 = ds_o[1:0];
    // ---- per sub-tile: input relays, the sub-tile, K-partial relay, node-slice relay ----------------------------------
    wire [32*NT-1:0] kp_t, kp_k;
    wire [NT-1:0]    kpv_t, kpv_k, gf_t, gf_k_w;
    wire [64*NT-1:0] nb_t;
    genvar t;
    generate for (t = 0; t < NT; t = t + 1) begin : g_t
        wire [3+LTW:0]  cr_i, cr_o;           // reset part: {c[3:1], lt, qv}
        wire [216:0]    dr_i, dr_o;           // plain part: {c[0], row, e, qb, qd, hid}
        assign cr_i = {c3[3:1], lt3, qv3};
        assign dr_i = {c3[0], row3[64*t +: 64], e3, qb3, qd3[128*(t % 4) +: 128], hid3};
        (* keep_hierarchy *) ot_qkh_relay #(.W(4 + LTW), .D(NRI), .RST(1)) u_ric (.clk(clk), .rst_n(rr[t]), .d(cr_i), .q(cr_o));
        (* keep_hierarchy *) ot_qkh_relay #(.W(1 + 64 + 16 + 6 + 128 + 2), .D(NRI)) u_rid (.clk(clk), .rst_n(rr[t]), .d(dr_i), .q(dr_o));
        wire [3:0]     c_s  = {cr_o[3+LTW:1+LTW], dr_o[216]};
        wire [LTW-1:0] lt_s = cr_o[LTW:1];
        wire           qv_s = cr_o[0];
        wire [63:0]    row_s = dr_o[215:152];
        wire [15:0]    e_s  = dr_o[151:136];
        wire [5:0]     qb_s = dr_o[135:130];
        wire [127:0]   qd_s = dr_o[129:2];
        wire [1:0]     hid_s = dr_o[1:0];
        ot_qkh_lane8 u_l8 (.clk(clk), .rst_n(rr[t]), .c_in(c_s), .row_in(row_s),
            .e_in(e_s), .lt_in(lt_s), .hid(hid_s), .bsel(2'(t / 4)), .q_valid_in(qv_s), .q_beat_in(qb_s), .q_data_in(qd_s),
            .kp(kp_t[32*t +: 32]), .kpv(kpv_t[t]), .nb(nb_t[64*t +: 64]), .gf(gf_t[t]));
        (* keep_hierarchy *) ot_qkh_relay #(.W(32), .D(NRK)) u_rkd (.clk(clk), .rst_n(rr[t]), .d(kp_t[32*t +: 32]), .q(kp_k[32*t +: 32]));
        (* keep_hierarchy *) ot_qkh_relay #(.W(2), .D(NRK), .RST(1)) u_rkv (.clk(clk), .rst_n(rr[t]), .d({kpv_t[t], gf_t[t]}),
                                                                             .q({kpv_k[t], gf_k_w[t]}));
        (* keep_hierarchy *) ot_qkh_relay #(.W(64), .D(NRN)) u_rn (.clk(clk), .rst_n(rr[t]), .d(nb_t[64*t +: 64]), .q(nb_d[64*t +: 64]));
    end endgenerate
    // ---- the K tree tile + the output relay ------------------------------------------------------------------------------
    wire [31:0] sc_k;
    wire        sf_k, gf_kt;
    ot_qkh_ktree u_kt (.clk(clk), .rst_n(rr[NT]), .kp_in(kp_k),
        .kpv_in(kpv_k[0]), .gf_in(gf_k_w), .sc_d(sc_k), .sc_f(sf_k), .g_f(gf_kt));
    (* keep_hierarchy *) ot_qkh_relay #(.W(32), .D(1)) u_ros (.clk(clk), .rst_n(rp), .d(sc_k), .q(sc_d));
    (* keep_hierarchy *) ot_qkh_relay #(.W(2), .D(1), .RST(1)) u_rof (.clk(clk), .rst_n(rp), .d({sf_k, gf_kt}), .q({sc_f, g_f}));
endmodule
