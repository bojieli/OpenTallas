`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// S81-SVC8 (10-20): structurally safe successor of the S81 attention HEAD GROUP ot_hdc_v41x_attn_hgrp_s81
// (= ot_hdc_v41x_attn_hgrp_s #(H16 HG4 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6 F12 1 PCOLP1)).  SAME ports, SAME cycles
// (DELTA 0 edges: group 45 = R0 1 + D1 1 + core 42 + out 1), SAME arithmetic modules (bmul_s ML6, qaddf F12 LAT4,
// deq_a/deq_b), so the golden rounding and reduction order are the old group's by construction.
//
// What changes (SAFE-DESIGN item 5: delay lines >= 3 deep become SRAM rings; no flop->flop hold chains):
//   * operand/bank skew: the k operand and the bank select are SHARED by the 4 heads (chunk c of every head reads
//     lanes 8c..8c+7), so the skew is built ONCE: one ring per lane position p = 2..7 (D = FPL*(p-1) = 4..24)
//     holding the 4 lanes p, p+8, p+16, p+24 (4 x 18 b) + the bank (3 b) = 75 b -> 2 x ot_sram_1r1w_32x64_m1 each
//     (the 32x128 macro's E/W pin faces would be ~9.6 pins/um).
//     (old: 32 lanes x 18 b + 8 bank lines as flop chains, 2,148 bit-stages x up to 24.)
//   * dequant-fault delay (FML 6, per lane, identical in the 4 heads) -> one shared 33 b ring (32 lanes + valid).
//   * per head: the 28 chunk-chain and 3 tree fault delays (FPL 4) -> one 31 b ring per head; head 0's ring also
//     carries the valid through the 9 sequential FPL stages (6 + 9 x 4 = 42 = LAT_CORE), so ov follows the data
//     pipeline; no 42-deep valid chain.  Total 17 x ot_sram_1r1w_32x64_m1 per group (12 skew + 1 dequant-fault + 4 fault).
//   * fanout: every driver is bounded to <= 32 loads after synthesis by the SCC-aware mapped-graph replicator
//     (tools/s81_dv/svc_rs/svc7_bound_graph.py, same input functions/clock/reset per copy); reset: the kit lands
//     rst_n in 2 stages at the face and the replicator builds the equal-age leaf copies.
// Reset contract (landed-reset standard, S81-SVC8 decision): rst_n asserted >= 4 edges; no iv / ld_v while
// asserted or in the first 6 edges after release (source landing 2 + ring landing 2); outputs compared outside that
// window.  Stationary weights are written before first use (compiler contract).
// SVC8_HGRP_MUT (bench mutants): 1 = gid ignored, 2 = head-0 fault dropped (the old group's OT_HGRP_MUT codes);
// SVC8_MUT_BANK: chunk position 3 reads the bank of position 2; SVC8_RING_MUT_ADDR: ring read offset D-1.
// ---------------------------------------------------------------------------
module ot_s81svc8_hgrp_s81 #(
`ifdef SVC8_WRITE_PREDECODE
    parameter integer WRITE_PREDECODE = 1
`else
    parameter integer WRITE_PREDECODE = 0
`endif
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [7:0]        gid,
    input  wire              ld_v,
    input  wire              ld_mode,
    input  wire [2:0]        ld_bank,
    input  wire [7:0]        ld_grp,
    input  wire [2*32*16-1:0] ld_w,
    input  wire [4*2*2*16-1:0] ld_wp,
    input  wire              ld_w2v,
    input  wire              iv,
    input  wire [2:0]        ibank,
    input  wire [32*18-1:0]  ib,
    output reg               ov,
    output reg  [4*32-1:0]   oy,
    output wire [3:0]        oflt
);
`ifdef SVC8_HGRP_MUT
    localparam integer MUT = `SVC8_HGRP_MUT;
`else
    localparam integer MUT = 0;
`endif
    localparam integer H = 16, HG = 4, TD = 32, NBANK = 5, BW = 3, PWORDS = 2, FPL = 4, FML = 6, F12 = 1;
    localparam integer NC = TD / 8;          // 4 chunks per head
    localparam integer R = TD / H;           // 2
    localparam integer NFH = 7 * NC + NC - 1;   // 31 fault delays per head
    localparam integer NVS = 7 + 2;          // sequential FPL stages after the product: 7 chain + 2 tree levels
    wire [7:0] gid_m = (MUT == 1) ? 8'd0 : gid;
    reg  [3:0] of_r;
    assign oflt = (MUT == 2) ? {of_r[3:1], 1'b0} : of_r;

    // -- reset: 2-stage landing in the source (the kit's flow landing sits in front of it); every reset load below
    //    takes rst_l, whose equal-age leaf copies (<= 32 loads each) the mapped-graph replicator builds
    (* keep *) reg rl0, rl1;
    always @(posedge clk) begin rl0 <= rst_n; rl1 <= rl0; end
    wire rst_l = rl1;

    // -- R0: boundary registers
    reg              r_iv;
    reg [BW-1:0]     r_ibank;
    reg [TD*18-1:0]  r_ib;
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) r_iv <= 1'b0;
        else r_iv <= iv;
    end
    always @(posedge clk) begin
        r_ibank <= ibank; r_ib <= ib;
    end

    // -- D1: dequantise across the D1 register (deq_a | D1 | deq_b), as the old group
    genvar gh, gk, gp;
    wire [TD*18-1:0] dq_b;
    reg  [TD*21-1:0] d1_a;
    reg  [BW-1:0]    d1_bank;
    reg              d1_v;
    generate
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_dq
            wire [20:0] da;
            ot_hdc_v41x_attn_deq_a u_da (.e(r_ib[gk*18 +: 18]), .d(da));
            always @(posedge clk) d1_a[gk*21 +: 21] <= da;
            wire [15:0] y;
            wire f;
            ot_hdc_v41x_attn_deq_b u_db (.d(d1_a[gk*21 +: 21]), .y(y), .flt(f));
            assign dq_b[gk*18 +: 18] = {d1_a[gk*21 + 20], f, y};
        end
    endgenerate
    always @(posedge clk) d1_bank <= r_ibank;
    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) d1_v <= 1'b0;
        else d1_v <= r_iv;
    end

    // -- shared skew: lane position p issues FPL*(p-1) cycles after position 0 (p = 0, 1: no delay)
    wire [TD*18-1:0] sk_b;
    wire [8*BW-1:0]  sk_bank;
    generate
        for (gp = 0; gp < 8; gp = gp + 1) begin : g_sk
            wire [4*18-1:0] li, lo;
            for (gk = 0; gk < 4; gk = gk + 1) begin : g_l
                assign li[gk*18 +: 18] = dq_b[(gk*8 + gp)*18 +: 18];
                assign sk_b[(gk*8 + gp)*18 +: 18] = lo[gk*18 +: 18];
            end
            if (gp < 2) begin : g_0
                assign lo = li;
                assign sk_bank[gp*BW +: BW] = d1_bank;
            end else begin : g_r
                // two 32x64 rings per position (32x128 E/W faces would carry ~9.6 pins/um > 6): lanes p, p+8 + bank
                // (39 b) and lanes p+16, p+24 (36 b), same D
                wire [BW-1:0] bo;
                ot_s81svc8_ring #(.W(2*18 + BW), .D(FPL * (gp - 1)), .M(64)) u_ra (
                    .clk(clk), .rst_n(rst_l), .i({d1_bank, li[0 +: 36]}), .o({bo, lo[0 +: 36]}));
                ot_s81svc8_ring #(.W(2*18), .D(FPL * (gp - 1)), .M(64)) u_rb (
                    .clk(clk), .rst_n(rst_l), .i(li[36 +: 36]), .o(lo[36 +: 36]));
`ifdef SVC8_MUT_BANK
                if (gp == 3) begin : g_mb
                    assign sk_bank[gp*BW +: BW] = sk_bank[2*BW +: BW];
                end else begin : g_nb
                    assign sk_bank[gp*BW +: BW] = bo;
                end
`else
                assign sk_bank[gp*BW +: BW] = bo;
`endif
            end
        end
    endgenerate

    // -- shared dequant-fault delay (FML) + the valid's product stage: one ring
    wire [TD-1:0] dfq;
    wire          v_p;                       // d1_v + FML
    generate
        wire [TD-1:0] dfi;
        for (gk = 0; gk < TD; gk = gk + 1) begin : g_dfi
            assign dfi[gk] = sk_b[gk*18 + 16] & ~sk_b[gk*18 + 17];
        end
        ot_s81svc8_ring #(.W(TD + 1), .D(FML), .M(64)) u_dfring (
            .clk(clk), .rst_n(rst_l), .i({d1_v, dfi}), .o({v_p, dfq}));
    endgenerate

    // -- heads
    wire [NVS:0] vst;                        // vst[0] = v_p; vst[j] = v_p + FPL*j (carried by head 0's ring)
    assign vst[0] = v_p;
    generate
        for (gh = 0; gh < HG; gh = gh + 1) begin : g_h
            // this head's kept copies of the stationary-load R0 registers (as the old group)
            wire [BW-1:0] r_ld_bank;
            wire [PWORDS*TD*16-1:0] r_ld_w;
            wire [R*16-1:0] pcol, pcol2;
            wire [TD-1:0] we;
            wire [TD*16-1:0] wd;
            if (WRITE_PREDECODE != 0) begin : g_predecode
            ot_hdc_v41x_kreg #(.W(BW), .R(0)) u_rc (.clk(clk), .rst_n(rst_l),
                .d(ld_bank), .q(r_ld_bank));
            ot_hdc_v41x_kreg #(.W(PWORDS*TD*16), .R(0)) u_rw (.clk(clk), .rst_n(rst_l), .d(ld_w), .q(r_ld_w));
            wire [PWORDS*R*16-1:0] r_ld_wp;
            ot_hdc_v41x_kreg #(.W(PWORDS*R*16), .R(0)) u_rp (.clk(clk), .rst_n(rst_l),
                .d(ld_wp[gh*PWORDS*R*16 +: PWORDS*R*16]), .q(r_ld_wp));
            assign pcol = r_ld_wp[0 +: R*16];
            assign pcol2 = r_ld_wp[R*16 +: R*16];
            // Decode stationary write classes before the existing R0 edge.
            // The old raw mode R0 drove 512 data-mux bits/head; graph copies
            // exposed 132 D loads on the raw mode port. Register the actual
            // normal/low/high write predicates instead. Data and bank still
            // cross precisely the same R0 edge and ab captures at R0+1.
            wire write_normal;
            wire [7:0] head_id = gid_m * HG + gh;
            wire n_raw = ld_v && !ld_mode && (ld_grp == head_id);
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_wn (.clk(clk), .rst_n(rst_l),
                .d(n_raw), .q(write_normal));
            wire [TD/R-1:0] write_low, write_high;
            for (gk = 0; gk < TD/R; gk = gk + 1) begin : g_wdecode
                wire lo_raw = ld_v && ld_mode && (ld_grp == gk);
                wire hi_raw = ld_v && ld_mode && ld_w2v && ((ld_grp + 8'd1) == gk);
                ot_hdc_v41x_kreg #(.W(2), .R(1)) u_wc (.clk(clk), .rst_n(rst_l),
                    .d({hi_raw, lo_raw}), .q({write_high[gk], write_low[gk]}));
            end

                assign we = {TD{1'b0}};
                assign wd = {TD*16{1'b0}};
            end else begin : g_original
            wire             r_ld_v, r_ld_mode;
            wire [7:0]       r_ld_grp;
            wire             r_ld_w2v;
            ot_hdc_v41x_kreg #(.W(1), .R(1)) u_rv (.clk(clk), .rst_n(rst_l), .d(ld_v), .q(r_ld_v));
            ot_hdc_v41x_kreg #(.W(1 + BW + 8 + 1), .R(0)) u_rc (.clk(clk), .rst_n(rst_l),
                .d({ld_mode, ld_bank, ld_grp, ld_w2v}), .q({r_ld_mode, r_ld_bank, r_ld_grp, r_ld_w2v}));
            ot_hdc_v41x_kreg #(.W(PWORDS*TD*16), .R(0)) u_rw (.clk(clk), .rst_n(rst_l), .d(ld_w), .q(r_ld_w));
            reg [7:0] hh;
            always @(posedge clk) hh <= gid_m * HG + gh;
            wire [PWORDS*R*16-1:0] r_ld_wp;
            ot_hdc_v41x_kreg #(.W(PWORDS*R*16), .R(0)) u_rp (.clk(clk), .rst_n(rst_l),
                .d(ld_wp[gh*PWORDS*R*16 +: PWORDS*R*16]), .q(r_ld_wp));
            assign pcol = r_ld_wp[0 +: R*16];
            assign pcol2 = r_ld_wp[R*16 +: R*16];
            for (gk = 0; gk < TD; gk = gk + 1) begin : g_w
                wire lo = (r_ld_grp == (gk / R));
                wire hi = r_ld_w2v && ((r_ld_grp + 8'd1) == (gk / R));
                assign wd[gk*16 +: 16] = !r_ld_mode ? r_ld_w[gk * 16 +: 16] :
                                         hi ? pcol2[(gk % R) * 16 +: 16] : pcol[(gk % R) * 16 +: 16];
                assign we[gk] = r_ld_v && (r_ld_mode ? (lo || hi) : (r_ld_grp == hh));
            end

            end

            // products (old hdp_s g_m), dequant fault from the shared ring
            wire [TD*32-1:0] p;
            wire [TD-1:0]    pf;
            for (gk = 0; gk < TD; gk = gk + 1) begin : g_m
                reg [NBANK*16-1:0] ab;
                integer bb;
                if (WRITE_PREDECODE != 0) begin : g_prewrite
                always @(posedge clk)
                    for (bb = 0; bb < NBANK; bb = bb + 1)
                        if (r_ld_bank == bb) begin
                            if (g_predecode.write_normal) ab[bb*16 +: 16] <= r_ld_w[gk*16 +: 16];
                            else if (g_predecode.write_high[gk/R]) ab[bb*16 +: 16] <= pcol2[(gk%R)*16 +: 16];
                            else if (g_predecode.write_low[gk/R]) ab[bb*16 +: 16] <= pcol[(gk%R)*16 +: 16];
                        end
                end else begin : g_oldwrite
                    always @(posedge clk)
                        for (bb = 0; bb < NBANK; bb = bb + 1)
                            if (we[gk] && (r_ld_bank == bb)) ab[bb*16 +: 16] <= wd[gk*16 +: 16];
                end
                wire [BW-1:0] bk = sk_bank[(gk % 8)*BW +: BW];
                wire [15:0] av = ab[bk*16 +: 16];
                wire [17:0] be = sk_b[gk*18 +: 18];
                wire mf;
                ot_hdc_v41x_attn_bmul_s #(.ML(FML)) u_m (.clk(clk), .a(av), .b(be[15:0]), .pad(be[17]),
                                                         .y(p[gk*32 +: 32]), .flt(mf));
                assign pf[gk] = mf | dfq[gk];
            end

            // fault delays of this head: one ring (chunk chains: 7 per chunk; tree: 3); head 0 adds the valid
            localparam integer WV = (gh == 0) ? NVS : 0;
            wire [NFH-1:0] fdi, fdo;
            wire [NVS-1:0] vdi, vdo;
            if (gh == 0) begin : g_rv
                ot_s81svc8_ring #(.W(NFH + NVS), .D(FPL), .M(64)) u_fring (
                    .clk(clk), .rst_n(rst_l), .i({vdi, fdi}), .o({vdo, fdo}));
                for (gk = 0; gk < NVS; gk = gk + 1) begin : g_v
                    assign vdi[gk] = vst[gk];
                    assign vst[gk + 1] = vdo[gk];
                end
            end else begin : g_rn
                ot_s81svc8_ring #(.W(NFH), .D(FPL), .M(64)) u_fring (
                    .clk(clk), .rst_n(rst_l), .i(fdi), .o(fdo));
                assign vdi = {NVS{1'b0}};
                assign vdo = {NVS{1'b0}};
            end

            // chunks: 8 products, sequential sum (old chunk_s), add qaddf F12 LAT4
            wire [(2*NC-1)*32-1:0] tn;           // heap order: leaves (chunk sums) at NC-1 .. 2NC-2
            wire [2*NC-2:0]        tf;
            for (gp = 0; gp < NC; gp = gp + 1) begin : g_c
                wire [8*32-1:0] acc;
                wire [7:0]      af;
                assign acc[31:0] = p[gp*256 +: 32];
                assign af[0] = pf[gp*8];
                for (gk = 1; gk < 8; gk = gk + 1) begin : g_a
                    wire [31:0] s;
                    wire sf;
                    ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_l), .v(1'b1),
                        .a(acc[(gk-1)*32 +: 32]), .b(p[gp*256 + gk*32 +: 32]), .y(s), .fault(sf));
                    assign fdi[gp*7 + gk - 1] = af[gk-1] | pf[gp*8 + gk];
                    assign acc[gk*32 +: 32] = s;
                    assign af[gk] = fdo[gp*7 + gk - 1] | sf;
                end
                assign tn[(NC-1+gp)*32 +: 32] = acc[7*32 +: 32];
                assign tf[NC-1+gp] = af[7];
            end
            for (gp = 0; gp < NC - 1; gp = gp + 1) begin : g_node
                wire [31:0] s;
                wire sf;
                ot_hdc_v41x_qaddf #(.LAT(FPL), .F12(F12)) u_a (.clk(clk), .rst_n(rst_l), .v(1'b1),
                    .a(tn[(2*gp+1)*32 +: 32]), .b(tn[(2*gp+2)*32 +: 32]), .y(s), .fault(sf));
                assign fdi[7*NC + gp] = tf[2*gp+1] | tf[2*gp+2];
                assign tn[gp*32 +: 32] = s;
                assign tf[gp] = fdo[7*NC + gp] | sf;
            end
            always @(posedge clk) begin
                oy[gh*32 +: 32] <= tn[31:0];
                of_r[gh] <= tf[0];
            end
        end
    endgenerate

    always @(posedge clk or negedge rst_l) begin
        if (!rst_l) ov <= 1'b0;
        else ov <= vst[NVS];
    end
endmodule
