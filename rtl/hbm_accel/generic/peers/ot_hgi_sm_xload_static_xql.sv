`timescale 1ns/1ps
`default_nettype none
// =====================================================================================================================
// XQL (H-SM 2026-10-16, coordinator decision after the H-DIE d4b relay pass): QUADRANT-LOCAL x read.
// d4b: hb_vms_<Q> -> xl_<Q>_ctl -> xw_data (2048 b) broadcast to the 8 SMs of the quadrant = 63 bit-weighted relay
// stages (SM_X), -17.2 % DS AR.  XQL keeps ONE x-load control per quadrant (issue, rq/rr beside hb_vms, landing,
// quantise) and replicates the x-STORE + EGRESS per SM PAIR (NP = 4 per quadrant): each pair cluster (4 BF quarters,
// the BD ring and a pair-egress leaf) sits between its two SMs, so the 2048-b xw beats travel < 1 mm.
// The ctl -> pair streams (BF16 write words c_d + write/read controls, quantiser words + ring controls, egress controls,
// leaf reset) cross an EQUAL-AGE registered tree of depth T (die relay stages, compiler constant; the ctl pin registers
// and the pair-leaf pin registers are its first / last stage): every pair runs EXACTLY the cl2 schedule T edges later.
// Each x is written once per pair; the PMAX re-reads and the xw beats stay inside the pair.
// Static fixed-cycle: no ready / credit anywhere; rq (VM issue) is unchanged; every xw beat / x_done of every pair is
// T edges after the cl2 (ctl egress) beat.  Compiler: XW_ADD_CL2 + T.
// Bench mutants (XQL_MUT): 1 = pair 1 write dropped, 2 = pair 2 tree one edge deeper (skew), 3 = pair 3 quarters 0/1
// read words swapped (pair-internal mapping).
// =====================================================================================================================

// Equal-age tree: T register stages (T = 0: wire).  Physically the die relay chain of one ctl -> pair route.
module ot_hgi_sm_xload_xq_tree #(
    parameter integer W = 1,
    parameter integer T = 1
) (
    input  wire          clk,
    input  wire [W-1:0]  d,
    output wire [W-1:0]  q
);
    generate if (T == 0) begin : g_wire
        assign q = d;
    end else begin : g_reg
        reg [W-1:0] s [0:T-1];
        always @(posedge clk) begin
            s[0] <= d;
            for (integer i = 1; i < T; i = i + 1) s[i] <= s[i-1];
        end
        assign q = s[T-1];
    end endgenerate
endmodule

// Pair-egress leaf: the ctl egress (cl2 ctl clk_eg stage) moved next to the pair's store.  Every input lands in a pin
// register (owner rule 19:50), exactly as inside the ctl: rw <= rwq, e5r <= {ok, b} (ctl ed[RDP-3]), e6 <= ctl ed[RDP-2],
// bc_* <= bq_*, bq_c <= bq_d; then the replicated beat select and the xw pins.  Same edges as the ctl egress.
module ot_hgi_sm_xload_xq_pegress #(
    parameter integer PMAX = 8,
    parameter integer NR   = 32
) (
    input  wire               clk,
    input  wire               rn,          // leaf reset (ctl relay output through the tree)
    input  wire [7:0]         ed5,         // {ok, b} of the ctl emission tag ed[RDP-3]
    input  wire [16:0]        ede,         // ctl emission tag ed[RDP-2] = {en, ok, last, addr7, grp7}
    input  wire               bq_v, bq_last,
    input  wire [6:0]         bq_addr, bq_b,
    input  wire [1023:0]      rwq,         // the pair's 4 BF quarter rw registers
    input  wire [2047:0]      bq_d,        // the pair's BD ring beat register
    output reg                x_done,
    output reg                xw_en,
    output reg                xw_last,
    output reg  [6:0]         xw_addr,
    output reg  [6:0]         xw_grp,
    output reg  [2047:0]      xw_data
);
    localparam integer XC = 3152, XOFF = 2128;
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    localparam integer RB = 2048 / NR;
    localparam integer EW = 17;
    function automatic integer bslot(input integer bb);
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    reg [1023:0] rw;
    always @(posedge clk) rw <= rwq;
    wire [2047:0] beats [0:NBMAX-1];
    genvar gb;
    generate for (gb = 0; gb < NBMAX; gb = gb + 1) begin : g_beat
        localparam integer PS = bslot(gb);
        localparam integer OFF = (PS < 0) ? 0 : PS * XC + XOFF - gb * 2048;
        if (PS < 0) begin : g_none
            assign beats[gb] = 2048'd0;
        end else if (OFF >= 0) begin : g_pos
            wire [4095:0] sh = {3072'd0, rw} << OFF;
            assign beats[gb] = sh[2047:0];
        end else begin : g_neg
            wire [1023:0] sh = rw >> (-OFF);
            assign beats[gb] = {1024'd0, sh};
        end
    end endgenerate
    // Regional SYNCHRONOUS reset (owner die standard 10-16; x5): rn is captured by NRR kept relay flops (D pins only,
    // no async RESETN anywhere in the leaf); each relay copy synchronously clears one quarter of the VALID/control flops.
    // Data/field flops the static schedule overwrites before use carry no reset (e6 fields, e5 beat index, bc_addr/b,
    // bq_c, rw, xbeat, xw_data/addr/grp).  Assert and release are both +1 edge (transaction-level; the controls are idle
    // for many cycles around reset).
    localparam integer NRR = 4;
    (* keep = 1 *) reg [NRR-1:0] rnr;
    always @(posedge clk) rnr <= {NRR{rn}};
    reg e6v; reg [EW-2:0] e6f;
    always @(posedge clk) begin e6v <= rnr[0] ? ede[EW-1] : 1'b0; e6f <= ede[EW-2:0]; end
    wire [EW-1:0] e6 = {e6v, e6f};
    wire [7:0] e5r [0:NR-1];   // replicas kept (gate: merged bqvr drove 4,125 loads)
    wire [NR-1:0] bqvr;
    genvar gr;
    generate for (gr = 0; gr < NR; gr = gr + 1) begin : g_rep
        (* keep = 1 *) reg e5v;
        (* keep = 1 *) reg [6:0] e5b;
        (* keep = 1 *) reg bqq;
        always @(posedge clk) begin
            e5v <= rnr[gr * NRR / NR] ? ed5[7] : 1'b0;
            bqq <= rnr[gr * NRR / NR] ? bq_v : 1'b0;
            e5b <= ed5[6:0];
        end
        assign e5r[gr] = {e5v, e5b};
        assign bqvr[gr] = bqq;
    end endgenerate
    reg [2047:0] xbeat;
    always @(posedge clk) for (integer k = 0; k < NR; k = k + 1) begin
        xbeat[k*RB +: RB] <= {RB{1'b0}};
        if (e5r[k][7]) for (integer x = 0; x < NBMAX; x = x + 1) if (e5r[k][6:0] == 7'(x)) xbeat[k*RB +: RB] <= beats[x][k*RB +: RB];
    end
    reg bc_v, bc_last; reg [6:0] bc_addr, bc_b; reg [2047:0] bq_c;
    always @(posedge clk) begin
        if (!rnr[1]) begin bc_v <= 1'b0; bc_last <= 1'b0; end
        else begin bc_v <= bq_v; bc_last <= bq_last; end
    end
    always @(posedge clk) begin bc_addr <= bq_addr; bc_b <= bq_b; bq_c <= bq_d; end
    always @(posedge clk) begin
        if (!rnr[2]) begin xw_en <= 1'b0; xw_last <= 1'b0; x_done <= 1'b0; end
        else begin
            xw_en <= e6[EW-1] || bc_v; xw_last <= (e6[EW-1] && e6[EW-3]) || bc_last;
            x_done <= xw_en && xw_last;
        end
    end
    always @(posedge clk) begin
        if (bc_v) begin xw_addr <= bc_addr; xw_grp <= bc_b; end
        else begin xw_addr <= e6[13:7]; xw_grp <= e6[6:0]; end
        for (integer k = 0; k < NR; k = k + 1) xw_data[k*RB +: RB] <= bqvr[k] ? bq_c[k*RB +: RB] : xbeat[k*RB +: RB];
    end
endmodule

// One SM-pair x-store cluster: 4 BF quarters + the BD ring + the pair egress (hard leaves; wires only here).
module ot_hgi_sm_xload_xq_pair #(
    parameter integer PMAX = 8,
    parameter integer MAPMUT = 0           // bench mutant: swap the read words of quarters 0 / 1
) (
    input  wire [3:0]         clk_bf,
    input  wire               clk_bd,
    input  wire               clk_eg,
    input  wire               rn,
    input  wire [1023:0]      c_d,
    input  wire [3:0]         c_wce,
    input  wire               c_mhi, c_mlo,
    input  wire [6:0]         c_wa,
    input  wire [7:0]         r_ce,
    input  wire [6:0]         r_a,
    input  wire [15:0]        r_wsel,
    input  wire               zlo, zhi,
    input  wire [255:0]       qq_lo, qq_hi,
    input  wire signed [9:0]  qe_lo, qe_hi,
    input  wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,
    input  wire [PMAX*8-1:0]  lane_en,
    input  wire [7:0]         ed5,
    input  wire [16:0]        ede,
    input  wire               bq_v, bq_last,
    input  wire [6:0]         bq_addr, bq_b,
    output wire               x_done,
    output wire               xw_en,
    output wire               xw_last,
    output wire [6:0]         xw_addr,
    output wire [6:0]         xw_grp,
    output wire [2047:0]      xw_data
);
    wire [1023:0] rwq, rwq_m; wire [2047:0] bq_d;
    genvar gq;
    generate for (gq = 0; gq < 4; gq = gq + 1) begin : g_q
        ot_hgi_sm_xload_cl2_bfq u_bfq (.clk(clk_bf[gq]), .rst_n(rn), .c_d(c_d), .wce(c_wce[gq]), .mhi(c_mhi), .mlo(c_mlo),
            .wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(rwq[256*gq +: 256]));
    end endgenerate
    assign rwq_m = (MAPMUT != 0) ? {rwq[1023:512], rwq[255:0], rwq[511:256]} : rwq;
    ot_hgi_sm_xload_cl2_bdring #(.PMAX(PMAX)) u_bd (.clk(clk_bd), .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .qq_lo(qq_lo),
        .qq_hi(qq_hi), .qe_lo(qe_lo), .qe_hi(qe_hi), .bsel(bsel), .lane_en_i(lane_en), .bq_d(bq_d));
    ot_hgi_sm_xload_xq_pegress #(.PMAX(PMAX)) u_eg (.clk(clk_eg), .rn(rn), .ed5(ed5), .ede(ede), .bq_v(bq_v),
        .bq_last(bq_last), .bq_addr(bq_addr), .bq_b(bq_b), .rwq(rwq_m), .bq_d(bq_d), .x_done(x_done), .xw_en(xw_en),
        .xw_last(xw_last), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data));
endmodule

// XQL quadrant x-load: F20-faced control (ctlw, EGRESS_SPLIT) + 2 quantisers beside hb_vms, NP pair clusters behind
// equal-age trees of depth T.  Pair p drives SMs 2p / 2p + 1.
module ot_hgi_sm_xload_static_xql #(
    parameter integer PMAX   = 8,
    parameter integer RD_LAT = 6,
    parameter integer MUT    = 0,
    parameter integer NP     = 4,
    parameter integer T      = 2,
    parameter integer XQL_MUT = 0
) (
    input  wire               clk,
    input  wire               clk_cal,
    input  wire               clk_qlo,
    input  wire               clk_qhi,
    input  wire [NP*4-1:0]    clk_bf,
    input  wire [NP-1:0]      clk_bd,
    input  wire [NP-1:0]      clk_eg,
    input  wire               rst_n,
    input  wire [7:0]         tgt,
    input  wire               cfg_v,
    input  wire [7:0]         cfg_target,
    input  wire [11:0]        cfg_addr,
    input  wire [255:0]       cfg_data,
    input  wire               desc_v,
    input  wire [11:0]        desc_base,
    input  wire [12:0]        desc_limit,
    input  wire [15:0]        desc_loops,
    input  wire               launch_v,
    output wire               configured,
    output wire               fault,
    output wire               active,
    output wire [NP-1:0]      x_done,
    output wire [NP-1:0]      xw_en,
    output wire [NP-1:0]      xw_last,
    output wire [NP*7-1:0]    xw_addr,
    output wire [NP*7-1:0]    xw_grp,
    output wire [NP*2048-1:0] xw_data,
    output wire [8*17-1:0]    rq,
    input  wire [8*257-1:0]   rr
);
    localparam integer NBQ2 = 2 * ((PMAX * 3152 + 2047) / 2048);
    wire rn;
    wire [1023:0] c_d; wire [3:0] c_wce; wire c_mhi, c_mlo; wire [6:0] c_wa; wire [7:0] r_ce; wire [6:0] r_a;
    wire [2047:0] l_d; wire qv_lo, qv_hi, qo_lo, qo_hi, qf_lo, qf_hi; wire [255:0] qq_lo, qq_hi; wire signed [9:0] qe_lo, qe_hi;
    wire [15:0] r_wsel; wire zlo, zhi; wire [NBQ2-1:0] bsel; wire [PMAX*8-1:0] lane_en;
    wire [7:0] eg_ed5; wire [16:0] eg_ede; wire eg_bqv, eg_bqlast; wire [6:0] eg_bqaddr, eg_bqb;
    ot_hgi_sm_xload_cl2_ctlw #(.PMAX(PMAX), .RD_LAT(RD_LAT), .MUT(MUT), .EGRESS_SPLIT(1)) u_ctl (
        .clk(clk), .clk_eg(clk), .clk_cal(clk_cal), .rst_n(rst_n), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target),
        .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit),
        .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .fault(fault), .active(active),
        .x_done(), .xw_en(), .xw_last(), .xw_addr(), .xw_grp(), .xw_data(), .rq(rq), .rr(rr), .rn_o(rn),
        .c_d(c_d), .c_wce(c_wce), .c_mhi(c_mhi), .c_mlo(c_mlo), .c_wa(c_wa), .r_ce(r_ce), .r_a(r_a), .rwq(1024'd0),
        .l_d_o(l_d), .qv_lo(qv_lo), .qv_hi(qv_hi), .qo_lo(qo_lo), .qo_hi(qo_hi), .qf_lo(qf_lo), .qf_hi(qf_hi),
        .r_wsel(r_wsel), .zlo(zlo), .zhi(zhi), .bsel(bsel), .lane_en(lane_en), .bq_d(2048'd0),
        .eg_ed5(eg_ed5), .eg_ede(eg_ede), .eg_bqv(eg_bqv), .eg_bqlast(eg_bqlast), .eg_bqaddr(eg_bqaddr), .eg_bqb(eg_bqb));
    ot_hbm_xp_aq_tree13 u_aq_lo (.clk(clk_qlo), .rst_n(rn), .v(qv_lo), .fp4(1'b0), .x(l_d[1023:0]), .vo(qo_lo), .q(qq_lo),
                             .e(qe_lo), .y(), .fault(qf_lo));
    ot_hbm_xp_aq_tree13 u_aq_hi (.clk(clk_qhi), .rst_n(rn), .v(qv_hi), .fp4(1'b0), .x(l_d[2047:1024]), .vo(qo_hi), .q(qq_hi),
                             .e(qe_hi), .y(), .fault(qf_hi));
    // the ctl -> pair bundle (one equal-age tree per pair)
    localparam integer BW = 1 + 1024 + 4 + 2 + 7 + 8 + 7 + 16 + 2 + 512 + 20 + NBQ2 + PMAX*8 + 8 + 17 + 2 + 14;
    wire [BW-1:0] bun = {rn, c_d, c_wce, c_mhi, c_mlo, c_wa, r_ce, r_a, r_wsel, zlo, zhi, qq_lo, qq_hi, qe_lo, qe_hi, bsel,
                         lane_en, eg_ed5, eg_ede, eg_bqv, eg_bqlast, eg_bqaddr, eg_bqb};
    genvar gp;
    generate for (gp = 0; gp < NP; gp = gp + 1) begin : g_p
        localparam integer TP = T + ((XQL_MUT == 2 && gp == 2) ? 1 : 0);
        wire [BW-1:0] b;
        ot_hgi_sm_xload_xq_tree #(.W(BW), .T(TP)) u_tree (.clk(clk), .d(bun), .q(b));
        wire p_rn; wire [1023:0] p_cd; wire [3:0] p_wce; wire p_mhi, p_mlo; wire [6:0] p_wa; wire [7:0] p_rce; wire [6:0] p_ra;
        wire [15:0] p_wsel; wire p_zlo, p_zhi; wire [255:0] p_qlo, p_qhi; wire signed [9:0] p_elo, p_ehi; wire [NBQ2-1:0] p_bsel;
        wire [PMAX*8-1:0] p_len; wire [7:0] p_ed5; wire [16:0] p_ede; wire p_bqv, p_bql; wire [6:0] p_bqa, p_bqb;
        assign {p_rn, p_cd, p_wce, p_mhi, p_mlo, p_wa, p_rce, p_ra, p_wsel, p_zlo, p_zhi, p_qlo, p_qhi, p_elo, p_ehi, p_bsel,
                p_len, p_ed5, p_ede, p_bqv, p_bql, p_bqa, p_bqb} = b;
        ot_hgi_sm_xload_xq_pair #(.PMAX(PMAX), .MAPMUT((XQL_MUT == 3 && gp == 3) ? 1 : 0)) u_pair (
            .clk_bf(clk_bf[gp*4 +: 4]), .clk_bd(clk_bd[gp]), .clk_eg(clk_eg[gp]), .rn(p_rn), .c_d(p_cd),
            .c_wce((XQL_MUT == 1 && gp == 1) ? 4'd0 : p_wce), .c_mhi(p_mhi), .c_mlo(p_mlo), .c_wa(p_wa),
            .r_ce(p_rce), .r_a(p_ra), .r_wsel(p_wsel), .zlo(p_zlo), .zhi(p_zhi), .qq_lo(p_qlo), .qq_hi(p_qhi),
            .qe_lo(p_elo), .qe_hi(p_ehi), .bsel(p_bsel), .lane_en(p_len), .ed5(p_ed5), .ede(p_ede), .bq_v(p_bqv),
            .bq_last(p_bql), .bq_addr(p_bqa), .bq_b(p_bqb), .x_done(x_done[gp]), .xw_en(xw_en[gp]), .xw_last(xw_last[gp]),
            .xw_addr(xw_addr[gp*7 +: 7]), .xw_grp(xw_grp[gp*7 +: 7]), .xw_data(xw_data[gp*2048 +: 2048]));
    end endgenerate
endmodule
`default_nettype wire
