`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-NEXT FUSED csum TREE + HUB (LEAD-HBM/LH-P3UNITS/FUSHUB, 2026-10-19; next-release P = 3 die, case f4c_t9p3).
//
// WHY.  ot_hnx_fused_top (ot_hnx_fused_eng.sv) takes all 32 lanes' chunk sums on ONE edge into a 1,024-b register and a
// 5-level pairwise tree, with RL = 4 relays per lane.  On the die the 32 lanes sit beside their VM bank pairs in 4
// quadrants (worst lane -> hub 14.5 mm); a 32 x 441 b star into one hub is not legal.  SAFE-DESIGN review (FUSED README):
// item 2/7 (single-edge star over mm) and item 5 (scb = 48 x 256 b runtime-indexed flop array).  This file replaces the
// top by a NEIGHBOUR-HOP TREE that follows the DIE graph (f4c_t9p3 plan_p4.fused_graph):
//   per quadrant q (lanes lid = 8 q + i, i = the bank index of its bank pair):
//     level 1  n1[g] at lane 2g      : a = lane 2g (abutted), b = lane 2g + 1 (stacked pair, 668 um)
//     level 2  n2L at group 0        : a = n1[0] (local), b = n1[1] (g1 -> g0, neighbour column)
//              n2R at group 3        : a = n1[2] (g2 -> g3), b = n1[3] (local)
//     level 3  n3  at group 3        : a = n2L (g0 -> g3), b = n2R (local)  = the quadrant node
//   hub (centre line): level 4 t4a = (Q0, Q1), t4b = (Q2, Q3); level 5 t5 = (t4a, t4b).
// Every link is a die lane: registered relay stations at <= 405 um (forwarded half-cycle hops) and, between clock
// regions (g1->g0, g2->g3, g0->g3, quadrant->hub: 16 crossings), a LANDED crossing (lanes/LANDING-CONTRACT.md: 4-slot
// ring, fixed latency, no backpressure).  The die binder inserts them; this RTL sees each link as a fixed latency.
//
// NUMERICS (DECISION LEAD-HBM/LH-P3UNITS 10-19): the golden sums chunk pairs (2c, 2c+1) level by level, left = even.
// Chunk u of a block is lane (u + ph) mod 32, ph = A's bank phase (VM word address bits [7:3]).  The fixed tree above
// IS the golden order exactly when ph = 0 (and lid = 8 q + i), so the compiler allocator bank-aligns every FUSED
// HC_PRE_NORM operand (ph = 0; image check tools/hbm_next/fused_phase_check.py) and the hub REFUSES (job fault, no lane
// activity) an HC_PRE_NORM record with ph != 0.  HC_POST has no cross-lane reduction: its ph stays free (lane-local rule
// only: A / B / O one phase).  No runtime reorder, no rotation hardware.
//
// STATIC SCHEDULE.  No credits, ready, FIFO admission or arbitration anywhere.
//   * Down (command bus + r channel): every node re-registers the parent bus into two KEPT copies (one per child,
//     2 edges a node).  Lanes are NOT padded to lockstep: lane L sees every hub command D(L) edges later, i.e. lane L's
//     whole calendar (VM accesses included) is offset by its fixed D(L) (handed to CMTP as a per-bank offset).
//   * Up: each node pads its EARLIER child (strap pad_b / pad_k, fixed per instance by the die binder) by the
//     difference of the two children's ROUND TRIPS, so both children's messages of one block meet on one edge (the
//     aligned pair is registered).  Then chunk sums are added (one registered FP32 add, ot_dsrom_qadd LA 6, a = lower
//     lanes) and scalars / fin / flt pass in one register.  Up latency a node: scalar 4 + pad, chunk LA + 3 + pad.  Sibling subtrees have equal depth, so one pad aligns chunk sums, scalars and fins.
//   * Every misalignment is a FAULT (fl bit): a chunk sum on one side only, two scalars on one edge, a chunk/scalar
//     output collision, an adder flag.
// Pad storage: up to 32 edges x 271 b = 8.7 kb -> SRAM (1R1W 128x256 data ring + 1R1W 32x64 control ring), with a
// post-reset fill mask (silicon SRAM powers up random).
//
// Bus formats.  UP (UW = 271): [270] v, [269] t (0 scalar, 1 chunk sum), [268:259] x, [258] fa (fin AND),
//   [257] fo (fin OR), [256] fl (fault OR), [255:0] d (chunk sum in [31:0]).
//   DOWN (DW = 173): [172] cv, [171:169] cop, [168:161] cx, [160:33] cd, [32] rv, [31:0] rd.
// MUT (bench negatives, rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv): 1..6 as ot_hnx_fused_top (lanes / heap); 7 the hub accepts ph != 0
//   for HC_PRE_NORM (run with ph != 0 vectors: the fixed tree is NOT the golden order -> mismatches); 8 lanes 2 and 4 of quadrant 0
//   swap tree positions (wrong tree order, timing still aligned -> mismatches); 9 quadrant 0's n2L pad one edge short
//   (misaligned chunk sums -> FAULT).
// ---------------------------------------------------------------------------------------------------------------------

// q = d delayed by k edges (k strap 0 .. 32).  k >= 2: SRAM rings (write slot wp, read slot wp - k + 1, registered read:
// the slot written at edge e is in q after edge e + k - 1 + 1 = the shift line's); k = 1: one register; k = 0: a wire.
module ot_hnx_fused_pad #(parameter integer WC = 15) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    k,
    input  wire [WC-1:0] dc,
    input  wire [255:0]  dd,
    output wire [WC-1:0] qc,
    output wire [255:0]  qd
);
    reg [4:0] wp; reg [5:0] fill; reg ok_q;
    wire [4:0] ra = 5'(wp - 5'(k) + 5'd1);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wp <= '0; fill <= '0; ok_q <= 1'b0; end
        else begin
            wp <= wp + 5'd1;
            if (fill != 6'd63) fill <= fill + 6'd1;
            ok_q <= (fill + 6'd1 >= k);                  // the slot read at this edge was written after reset
        end
    wire [255:0] rdd; wire [63:0] rdc;
    ot_sram_1r1w_128x256_m1_r2c2 u_d (.clk(clk), .r_ce_in(1'b1), .r_addr_in({2'b00, ra}), .rd_out(rdd),
        .w_ce_in(1'b1), .w_addr_in({2'b00, wp}), .wd_in(dd), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w2c_32x64_m1 u_c (.wclk(clk), .rclk(clk), .r_ce_in(1'b1), .r_addr_in(ra), .rd_out(rdc),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in({{(64 - WC){1'b0}}, dc}), .w_mask_in({64{1'b1}}));
    reg [WC-1:0] c1; reg [255:0] d1;
    always @(posedge clk or negedge rst_n) if (!rst_n) c1 <= '0; else c1 <= dc;
    always @(posedge clk) d1 <= dd;
    assign qc = (k == 6'd0) ? dc : (k == 6'd1) ? c1 : (ok_q ? rdc[WC-1:0] : {WC{1'b0}});
    assign qd = (k == 6'd0) ? dd : (k == 6'd1) ? d1 : rdd;
endmodule

// one tree node (hardened once: hnx_fused_tnode_1019, x28 on the die; straps tied by the die binder)
module ot_hnx_fused_tnode #(parameter integer LA = 6, parameter integer UW = 271, parameter integer DW = 173) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    pad_k,      // strap: pad depth (edges)
    input  wire          pad_b,      // strap: 1 pads child b, 0 child a
    input  wire [UW-1:0] ua,         // up from child a (lower lanes)
    input  wire [UW-1:0] ub,         // up from child b (upper lanes)
    output wire [UW-1:0] uo,         // up to the parent
    input  wire [DW-1:0] dn,         // down from the parent
    output wire [DW-1:0] da,         // down to child a
    output wire [DW-1:0] db          // down to child b
);
    wire [3:0] rl;
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    // ---- up: pin flops (control reset, data not)
    reg [14:0] iac, ibc; reg [255:0] iad, ibd;
    always @(posedge clk or negedge rl[0])
        if (!rl[0]) begin iac <= '0; ibc <= '0; end else begin iac <= ua[270:256]; ibc <= ub[270:256]; end
    always @(posedge clk) begin iad <= ua[255:0]; ibd <= ub[255:0]; end
    // ---- alignment pad on the earlier child (static strap select)
    // straps are die ties (case-analysed); registered once here so no tile-input net fans out into the muxes
    reg [5:0] pk_q; reg pb_q;
    always @(posedge clk) begin pk_q <= pad_k; pb_q <= pad_b; end
    wire [14:0] pc; wire [255:0] pd;
    ot_hnx_fused_pad #(.WC(15)) u_pad (.clk(clk), .rst_n(rl[1]), .k(pk_q), .dc(pb_q ? ibc : iac),
        .dd(pb_q ? ibd : iad), .qc(pc), .qd(pd));
    // aligned pair, registered (the SRAM read -> select path ends here; +1 edge on both sides of every node)
    reg [14:0] ac, bc; reg [255:0] ad, bd;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) begin ac <= '0; bc <= '0; end else begin ac <= pb_q ? iac : pc; bc <= pb_q ? pc : ibc; end
    always @(posedge clk) begin ad <= pb_q ? iad : pd; bd <= pb_q ? pd : ibd; end
    wire ach = ac[14] && ac[13], bch = bc[14] && bc[13], asc = ac[14] && !ac[13], bsc = bc[14] && !bc[13];
    // ---- chunk sums: one registered FP32 add in the golden order (a = lower lanes = even chunk)
    wire cgo = ach && bch;
    wire [LA:0] cvl; wire [31:0] s; wire sf;
    ot_hdc_vline #(.D(LA)) u_cv (.clk(clk), .rst_n(rl[1]), .v(cgo), .vd(cvl));
    ot_dsrom_qadd #(.LAT(LA)) u_add (clk, rl[1], cgo, ad[31:0], bd[31:0], s, sf);
    wire cout = cvl[LA];
    // ---- scalars / fins / faults: one register
    reg sv, sfa, sfo, sfl; reg [9:0] sx; reg [255:0] sd;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) begin sv <= 1'b0; sfa <= 1'b0; sfo <= 1'b0; sfl <= 1'b0; end
        else begin
            sv <= asc || bsc;
            sfa <= ac[2] && bc[2];
            sfo <= ac[1] || bc[1];
            sfl <= ac[0] || bc[0] || (ach != bch) || (asc && bsc);    // misaligned block / scalar collision
        end
    always @(posedge clk) begin sx <= asc ? ac[12:3] : bc[12:3]; sd <= asc ? ad : bd; end
    // ---- output register
    reg [14:0] oc; reg [255:0] od;
    always @(posedge clk or negedge rl[1])
        if (!rl[1]) oc <= '0;
        else oc <= {sv || cout, cout, cout ? 10'd0 : sx, sfa, sfo, sfl || (sv && cout) || sf};
    always @(posedge clk) od <= cout ? {224'd0, s} : sd;
    assign uo = {oc, od};
    // ---- down: pin flops, then one KEPT copy per child (2 edges a node)
    reg [1:0] idv; reg [DW-3:0] idd;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) idv <= '0; else idv <= {dn[172], dn[32]};
    always @(posedge clk) idd <= {dn[171:33], dn[31:0]};
    (* keep = "true" *) reg [1:0] av_q, bv_q;
    (* keep = "true" *) reg [DW-3:0] ad_q, bd_q;
    always @(posedge clk or negedge rl[3]) if (!rl[3]) begin av_q <= '0; bv_q <= '0; end else begin av_q <= idv; bv_q <= idv; end
    always @(posedge clk) begin ad_q <= idd; bd_q <= idd; end
    assign da = {av_q[1], ad_q[DW-3:32], av_q[0], ad_q[31:0]};
    assign db = {bv_q[1], bd_q[DW-3:32], bv_q[0], bd_q[31:0]};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// hub (hardened once: hnx_fused_hub_1019, the 432 x 432 fus_hub slot on the strip centre line).  ot_hnx_fused_top's own
// logic: job decode + checks (ph = 0 added), the scalar prologue with scb in a 1R1W 128x256 SRAM (registered read: the
// command bus gets one pipeline edge so the WGT beat takes the macro's data), the ROW-PIPELINED padded heap, / D, + eps,
// rsqrt, r broadcast; plus tree levels 4 and 5 (three ot_hnx_fused_tnode) and the 4 quadrant down buses.
// job word: as ot_hnx_fused_top.  Straps (die binder): wsc = last SCRD -> its scalar in scb (from the tree's round trip),
// pk*/pb* = the hub nodes' pads.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hnx_fused_hub #(
    parameter integer D    = 5120,
    parameter integer RR   = 10,
    parameter integer NMAX = 8,
    parameter integer MUT  = 0,
    parameter integer UW   = 271,
    parameter integer DW   = 173
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          job_v,
    input  wire [216:0]  job,
    output reg           done,
    output reg           fault,
    output wire          busy,
    input  wire [7:0]    wsc,
    input  wire [5:0]    pk4a,
    input  wire [5:0]    pk4b,
    input  wire [5:0]    pk5,
    input  wire          pb4a,
    input  wire          pb4b,
    input  wire          pb5,
    input  wire [UW-1:0] uq0,
    input  wire [UW-1:0] uq1,
    input  wire [UW-1:0] uq2,
    input  wire [UW-1:0] uq3,
    output wire [DW-1:0] dq0,
    output wire [DW-1:0] dq1,
    output wire [DW-1:0] dq2,
    output wire [DW-1:0] dq3
);
    localparam integer SD = D / 8, NM = D / 256, NB = NM;
    localparam integer NBP = (NB <= 1) ? 1 : (1 << $clog2(NB));
    localparam integer LG = $clog2(NBP);
    localparam integer LM = 5, LA = 6;
    function automatic integer tz(input integer x);
        integer t;
        begin t = 0; while (t < 31 && ((x >> t) & 1) == 0) t = t + 1; tz = t; end
    endfunction
    localparam integer DK = tz(D), DF = D >> DK;
    generate if (D % 256 != 0 || NM > 31 || NMAX > 16) begin : g_bad
        ot_hnx_fused_D_must_be_a_multiple_of_256 u_trap ();
    end endgenerate
    wire [3:0] rl;
    ot_rst_relay #(.REGIONS(4)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rl));
    wire rs = rl[0];

    // ---- tree levels 4 / 5 and the down fan-out
    wire [UW-1:0] u4a, u4b, ur; wire [DW-1:0] d5a, d5b, dtop;
    ot_hnx_fused_tnode u_t4a (.clk(clk), .rst_n(rl[3]), .pad_k(pk4a), .pad_b(pb4a), .ua(uq0), .ub(uq1), .uo(u4a),
        .dn(d5a), .da(dq0), .db(dq1));
    ot_hnx_fused_tnode u_t4b (.clk(clk), .rst_n(rl[3]), .pad_k(pk4b), .pad_b(pb4b), .ua(uq2), .ub(uq3), .uo(u4b),
        .dn(d5b), .da(dq2), .db(dq3));
    ot_hnx_fused_tnode u_t5 (.clk(clk), .rst_n(rl[3]), .pad_k(pk5), .pad_b(pb5), .ua(u4a), .ub(u4b), .uo(ur),
        .dn(dtop), .da(d5a), .db(d5b));
    wire r_v = ur[270], r_t = ur[269], r_fa = ur[258], r_fo = ur[257], r_fl = ur[256];
    wire [9:0] r_x = ur[268:259]; wire [255:0] r_d = ur[255:0];
    wire sc_in = r_v && !r_t, vsum_v = r_v && r_t; wire [31:0] vsum = r_d[31:0];

    // ---- job decode
    reg [216:0] jq;
    wire j_post = jq[0]; wire [3:0] j_nm1 = jq[4:1];
    wire [18:0] ja = jq[23:5], jb = jq[42:24], jc = jq[61:43], jo = jq[80:62];
    wire [23:0] rsA = jq[104:81], rsB = jq[128:105], rsC = jq[152:129], rsO = jq[176:153];
    wire [5:0] nsc_j = j_post ? 6'(3 * (32'(j_nm1) + 1)) : 6'(32'(j_nm1) + 1);
    wire job_ok = (ja[2:0] == 3'd0) && (jb[2:0] == 3'd0) && (jc[2:0] == 3'd0) && (jo[2:0] == 3'd0) &&
                  (ja[7:3] == jb[7:3]) && (ja[7:3] == jo[7:3]) &&                    // lane-local: one bank phase
                  (MUT == 7 || j_post || ja[7:3] == 5'd0) &&                         // PRE csum tree: ph = 0
                  (rsA[7:0] == 8'd0) && (rsB[7:0] == 8'd0) && (rsO[7:0] == 8'd0) && (rsC[2:0] == 3'd0) &&
                  (j_post || rsB == 24'd0) &&                                        // PRE: the gain is a broadcast
                  (32'(j_nm1) < NMAX);

    // ---- scalars (prologue): scb[x] = scalar sector x, a 1R1W SRAM (48 of 128 rows)
    reg cv, cw, ch; reg [2:0] cop; reg [7:0] cx; reg [127:0] cd;
    reg rbv; reg [31:0] rb;
    reg [5:0] scl;
    wire [255:0] scb_rd; wire [5:0] wsx;
    ot_sram_1r1w_128x256_m1_r2c2 u_scb (.clk(clk), .r_ce_in(1'b1), .r_addr_in({1'b0, wsx}), .rd_out(scb_rd),
        .w_ce_in(sc_in), .w_addr_in({1'b0, r_x[5:0]}), .wd_in(r_d), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    // command pipeline edge: a WGT beat takes the macro's registered read of the address set on its issue edge
    reg pv; reg [2:0] pop; reg [7:0] px; reg [127:0] pd; reg prv; reg [31:0] prb;
    always @(posedge clk or negedge rs) if (!rs) begin pv <= 1'b0; prv <= 1'b0; end else begin pv <= cv; prv <= rbv; end
    always @(posedge clk) begin
        pop <= cop; px <= cx; pd <= cw ? (ch ? scb_rd[255:128] : scb_rd[127:0]) : cd; prb <= rb;
    end
    assign dtop = {pv, pop, px, pd, prv, prb};

    // ROW-PIPELINED padded heap (ot_hnx_fused_top's, unchanged): leaves NBP + b, block b = the b-th tree sum of a row
    reg [5:0] bi;
    localparam integer LAV = (LA >= 5) ? LA : LA + 1;
    function automatic integer hgt(input integer x);
        integer h, y;
        begin h = LG; y = x; while (y > 1) begin y = y >> 1; h = h - 1; end hgt = h; end
    endfunction
    function automatic integer is_add(input integer x);
        is_add = (x >= 1 && x < NBP && ((((2 * x + 1) << (hgt(x) - 1)) - NBP) < NB)) ? 1 : 0;
    endfunction
    wire [31:0] nv [1:2*NBP-1]; wire nd [1:2*NBP-1]; wire cons [1:2*NBP-1]; wire fire [1:2*NBP-1];
    wire [2*NBP-1:0] ncol;
    assign ncol[0] = 1'b0;
    genvar n;
    generate
        for (n = NBP; n < 2 * NBP; n = n + 1) begin : g_leaf
            assign fire[n] = 1'b0;
            if (n - NBP < NB) begin : g_r
                reg [31:0] val; reg vld;
                wire hit = vsum_v && bi == 6'(n - NBP);
                always @(posedge clk or negedge rl[1])
                    if (!rl[1]) vld <= 1'b0;
                    else if (hit) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (hit) val <= vsum;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = hit && vld && !cons[n] && MUT != 4;
            end else begin : g_p
                assign nd[n] = 1'b0; assign nv[n] = 32'd0; assign ncol[n] = 1'b0;
            end
        end
        for (n = 1; n < NBP; n = n + 1) begin : g_vn
            if (is_add(n)) begin : g_add
                reg vld; reg [31:0] val; wire [LAV:0] av; wire [31:0] s; wire af;
                assign fire[n] = nd[2 * n] && nd[2 * n + 1];
                ot_hdc_vline #(.D(LAV)) u_v (.clk(clk), .rst_n(rl[1]), .v(fire[n]), .vd(av));
                ot_dsrom_qadd #(.LAT(LAV)) u_a (clk, rl[1], fire[n], nv[2 * n], nv[2 * n + 1], s, af);
                always @(posedge clk or negedge rl[1])
                    if (!rl[1]) vld <= 1'b0;
                    else if (av[LAV]) vld <= 1'b1;
                    else if (cons[n] && MUT != 4) vld <= 1'b0;
                always @(posedge clk) if (av[LAV]) val <= s;
                assign nd[n] = vld; assign nv[n] = val;
                assign ncol[n] = (av[LAV] && vld && !cons[n] && MUT != 4) || af;
            end else begin : g_pass
                assign fire[n] = 1'b0; assign nd[n] = nd[2 * n]; assign nv[n] = nv[2 * n]; assign ncol[n] = 1'b0;
            end
        end
        assign cons[1] = nd[1];
        for (n = 2; n < 2 * NBP; n = n + 1) begin : g_cons
            if (is_add(n >> 1)) begin : g_ca assign cons[n] = fire[n >> 1]; end
            else if ((n & 1) == 0) begin : g_cp assign cons[n] = cons[n >> 1]; end
            else begin : g_cz assign cons[n] = 1'b0; end
        end
    endgenerate
    wire ss_v = nd[1]; wire [31:0] ss = nv[1];
    // scalar tail: / D, + eps, rsqrt
    reg [31:0] eps_r;
    reg ssv_q; reg [31:0] ss_q;
    always @(posedge clk or negedge rl[2]) if (!rl[2]) ssv_q <= 1'b0; else ssv_q <= ss_v;
    always @(posedge clk) ss_q <= ss;
    wire [31:0] mq, me, rr; wire mq_v, rr_v2, f_div, f_eps, f_rsq;
    ot_dsrom_divc #(.F(DF), .K(DK)) u_div (.clk(clk), .rst_n(rl[2]), .v(ssv_q), .x(ss_q), .y(mq), .vo(mq_v), .fault(f_div));
    wire [LA:0] ve;
    ot_hdc_vline #(.D(LA)) u_ve (.clk(clk), .rst_n(rl[2]), .v(mq_v), .vd(ve));
    ot_dsrom_qadd #(.LAT(LA)) u_eps (clk, rl[2], mq_v, mq, eps_r, me, f_eps);
    ot_dsrom_rsqrt #(.LM(LM), .LA(LA)) u_rsq (.clk(clk), .rst_n(rl[2]), .v(ve[LA]), .x(me), .y(rr), .vo(rr_v2), .fault(f_rsq));

    // ---- sequencer (static calendar; ot_hnx_fused_top's, with the scb read issued on the beat's edge)
    localparam [2:0] S_IDLE = 0, S_SC = 1, S_SCW = 2, S_WG = 3, S_RUN = 4;
    reg [2:0] st; reg post; reg [3:0] nm1; reg [5:0] nsc, scs; reg [7:0] wt; reg sfault;
    reg [15:0] cs_r; reg [1:0] cj; reg [15:0] rsc_s;
    reg [3:0] wrow; reg [2:0] wb; reg [15:0] tg; reg [15:0] tw_next; reg [15:0] per; reg [4:0] gofs;
    reg [3:0] hr; reg dec; reg busy_q;
    assign busy = busy_q;                                        // registered output (1 edge after the state)
    always @(posedge clk or negedge rs) if (!rs) busy_q <= 1'b0; else busy_q <= (st != S_IDLE);
    wire [2:0] nbt = post ? 3'd5 : 3'd1;                         // WGT beats a row
    assign wsx = post ? 6'(3 * wrow + wb / 2) : 6'(wrow);       // scalar sector of beat wb of row wrow
    wire beat_wg = (st == S_WG) && wrow <= nm1 && wrow < 4'd2;
    wire beat_run = (st == S_RUN) && wrow <= nm1 && tg >= tw_next;
    always @(posedge clk or negedge rs) begin
        if (!rs) begin
            st <= S_IDLE; done <= 1'b0; fault <= 1'b0; cv <= 1'b0; cw <= 1'b0; ch <= 1'b0; cop <= '0; cx <= '0;
            cd <= '0; rbv <= 1'b0; rb <= '0; jq <= '0; post <= 1'b0; nm1 <= '0; nsc <= '0; scs <= '0; scl <= '0;
            wt <= '0; sfault <= 1'b0; cs_r <= '0; cj <= '0; rsc_s <= '0; wrow <= '0; wb <= '0; tg <= '0;
            tw_next <= '0; per <= '0; gofs <= '0; bi <= '0; hr <= '0; eps_r <= '0; dec <= 1'b0;
        end else begin
            done <= 1'b0; fault <= 1'b0; cv <= 1'b0; cw <= 1'b0; rbv <= 1'b0;
            if (sc_in) scl <= scl + 6'd1;
            if (vsum_v) bi <= (bi == 6'(NB - 1)) ? 6'd0 : bi + 6'd1;
            if (r_fl) sfault <= 1'b1;                                  // lane / tree-node faults
            if (|ncol) sfault <= 1'b1;
            if (f_div || f_eps || f_rsq) sfault <= 1'b1;
            if (rr_v2) begin rbv <= 1'b1; rb <= rr; hr <= hr + 4'd1; end
            if (r_fo && !r_fa) sfault <= 1'b1;                        // fins of one record on one edge
            if (job_v && st != S_IDLE) sfault <= 1'b1;                  // launch collision
            case (st)
                S_IDLE: if (job_v) begin
                    jq <= job; st <= S_SC; dec <= 1'b1;
                    scs <= '0; scl <= '0; sfault <= 1'b0; hr <= '0; bi <= '0;
                end
                S_SC: if (dec) begin
                    dec <= 1'b0;
                    if (!job_ok) begin fault <= 1'b1; st <= S_IDLE; end
                    else begin
                        post <= j_post; nm1 <= j_nm1; nsc <= nsc_j; eps_r <= jq[216:185];
                        cs_r <= jc[18:3]; cj <= '0; rsc_s <= rsC[18:3];
                        per <= j_post ? 16'(5 * NM) + 16'(jq[184:177]) : 16'(4 * NM) + 16'(jq[184:177]);
                        gofs <= j_post ? 5'd0 : 5'(NM);
                        cv <= 1'b1; cop <= 3'd0; cx <= '0;
                        cd <= {19'd0, jq[184:177], rsO[18:3], rsB[18:3], rsA[18:3], jo[18:3], jb[18:3], ja[18:3], j_nm1, j_post};
                    end
                end else begin                                          // one SCRD a cycle
                    cv <= 1'b1; cop <= 3'd2; cx <= 8'(scs); cd <= {112'd0, cs_r + 16'(cj)};
                    if (cj == (post ? 2'd2 : 2'd0)) begin cj <= '0; cs_r <= cs_r + rsc_s; end else cj <= cj + 2'd1;
                    scs <= scs + 6'd1;
                    if (scs + 6'd1 == nsc) begin st <= S_SCW; wt <= wsc; end
                end
                S_SCW: if (wt != 8'd0) wt <= wt - 8'd1;
                       else begin
                           if (scl != nsc) sfault <= 1'b1;               // a scalar missed its fixed return
                           st <= S_WG; wrow <= '0; wb <= '0;
                       end
                S_WG: begin                                             // rows 0 and 1 into slots 0 / 1, then GO
                    if (beat_wg) begin
                        cv <= 1'b1; cw <= 1'b1; ch <= wb[0]; cop <= 3'd1; cx <= {wrow, wrow[0], wb};
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; end else wb <= wb + 3'd1;
                    end else begin
                        cv <= 1'b1; cop <= 3'd3; st <= S_RUN; tg <= '0; wb <= '0;
                        tw_next <= 16'(gofs) + per + 16'(RR + 8);         // row p >= 2 beats RR + 8 after row p - 1 starts
                    end
                end
                S_RUN: begin
                    tg <= tg + 16'd1;
                    if (beat_run) begin
                        cv <= 1'b1; cw <= 1'b1; ch <= wb[0]; cop <= 3'd1; cx <= {wrow, wrow[0], wb};
                        if (wb == nbt - 3'd1) begin wb <= '0; wrow <= wrow + 4'd1; tw_next <= tw_next + per; end
                        else wb <= wb + 3'd1;
                    end
                    if (r_fa) begin
                        st <= S_IDLE;
                        if (sfault || r_fl || (!post && hr != nm1 + 4'd1)) fault <= 1'b1; else done <= 1'b1;
                    end
                end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule

`default_nettype wire
