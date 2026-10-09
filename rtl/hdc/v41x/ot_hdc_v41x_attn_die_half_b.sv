`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM attention die tile SPLIT into two half-tile die blocks (OWNER 2026-10-08 18:10 PT, stream attn-split): the
// bank-built tile hfd_attn_tile_b (rtl/hdc/v41x/ot_hdc_v41x_attn_die_tile_b.sv; ot_attn_bpipe / ot_attn_fpipe come
// from that file) cut TOP / BOTTOM between its two quad rows.  The two halves are separate die masters, stacked in the
// tile slot with their seam faces abutting; the only buses that cross the cut are die-level links, one direction:
//   xp[1618:0]  lo -> hi  the ROOT packet {rst, ld, query}: lo's ROOT bank IS the N-face pin bank (flop -> pin), hi's
//                         S-face pin bank is the first of quad row 1's PMID banks (pin -> flop)
//   xr[271:0]   lo -> hi  quad row 0's result words {gov, oflt, oy} x 2 quads: NLL banks in lo (the last = the N-face
//                         pin bank), NL - NLL in hi (the first = the S-face pin bank), then the merge into o (in hi)
// Both are register-to-register across an abutting seam (pins face to face, last segment ~0 um <= 100 um); no ready /
// valid handshake crosses (the tile is a fixed-latency broadcast pipe), so no credits are needed.
// Cut choice (bits across the cut, attn-split.log): TOP/BOTTOM 1,619 + 272 = 1,891 (every source, ROOT, rf and quad
// row 0 in lo; quad row 1, cf and the i -> o chain + merge in hi).  LEFT/RIGHT (by quad column) >= 2,420: ROOT -> the
// other column's quads + its row-chain face 1,619, and the o (E) / i (W) chain plus one column's results 529 + 272.
// Latency: every port-to-port delay equals hfd_attn_tile_b's with the same parameters (rows 0 / 1 get the packet in
// the same cycle, cf in 1 + NFC, rf in 1 + NFR, every result word in NL + 1, the chain in 2 + NI): ZERO added cycles.
// Lock-stepped against hfd_attn_tile_b by rtl/test/tb_hfd_attn_half_b.sv (physical/hbm_attn_tile_r/half/run_lockh.sh).
// ---------------------------------------------------------------------------
module hfd_attn_half_lo #(
    parameter integer NK = 4,
    parameter integer NC = 2,
    parameter integer NR = 3,
    parameter integer PMID = 2,
    parameter integer NFR = 3,
    parameter integer NLL = 3       // result banks of quad row 0 in lo (2 side-channel EW + the N-face pin bank)
) (
    input  wire [1617:0] ci,
    input  wire [0:0]    ck,
    input  wire [1040:0] k,
    input  wire [0:0]    ldk,      // hbm-forks 2026-10-09 (RQ-HF-4, 8 KV entry points a stack): STATIC die strap (by_design
                                   // tie, false path).  1: the ld half of the packet comes from this tile's own k port only
                                   // (the forward chains' ld field is ignored; they still carry the query); 0: today's OR
    input  wire [581:0]  q,
    output wire [1617:0] rf,
    input  wire [1617:0] ri,
    input  wire [0:0]    rst,
    output wire [1618:0] xp,
    output wire [271:0]  xr
);
    localparam integer PK = 1618, PW = PK + 1;
    initial if (NLL < 3 || PMID < 1) $fatal(1, "hfd_attn_half_lo: NLL >= 3 and PMID >= 1");
    wire clk = ck[0];
    wire [1040:0] k_s; wire [582:0] q_s; wire [PK-1:0] ci_s, ri_s;
    ot_attn_bpipe #(.W(1041), .N(1 + NK)) u_pk (.clk(clk), .d(k), .q(k_s));
    ot_attn_bpipe #(.W(544), .N(1 + NK), .EW0(1)) u_pq (.clk(clk), .d(q[543:0]), .q(q_s[543:0]));
    ot_attn_fpipe #(.W(39), .N(1 + NK)) u_pqx (.clk(clk), .d({rst[0], q[581:544]}), .q(q_s[582:544]));
    ot_attn_bpipe #(.W(PK),   .N(1 + NC)) u_pc (.clk(clk), .d(ci), .q(ci_s));
    ot_attn_bpipe #(.W(PK),   .N(1 + NR), .EW0(1)) u_pr (.clk(clk), .d(ri), .q(ri_s));
`ifdef OT_ATTN_MUT_LDK
    wire ldk_s = 1'b0;                                       // NEGATIVE CONTROL: the strap ignored
`else
    wire ldk_s = ldk[0];
`endif
    wire [PK-1:0] fw = ci_s | ri_s;                          // forward-chain packet (ld 1,038 | query 580)
    wire [PW-1:0] pk = {q_s[582], k_s[1037:0] | (ldk_s ? 1038'd0 : fw[PK-1:580]), q_s[579:0] | fw[579:0]};
    wire [PW-1:0] root_q;
    // ROOT on the N face: its bank outputs are the xp pins
    ot_attn_bpipe #(.W(PW), .N(1)) u_root (.clk(clk), .d(pk), .q(root_q));
    assign xp = root_q;
    ot_attn_bpipe #(.W(PK), .N(NFR + 1), .EWN(1)) u_fr (.clk(clk), .d(root_q[PK-1:0]), .q(rf));
    genvar x;
    generate if (1) begin : g_y0
        wire [PW-1:0] mid_q;
        ot_attn_bpipe #(.W(PW), .N(PMID)) u_mid (.clk(clk), .d(root_q), .q(mid_q));
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 2 * x;
            wire [PW-1:0] row_q;
            ot_attn_bpipe #(.W(PW), .N(1)) u_row (.clk(clk), .d(mid_q), .q(row_q));
            wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
            wire [2:0]    q_ld_bank, q_ibank;
            wire [7:0]    q_ld_grp;
            wire [1023:0] q_ld_w;
            wire [575:0]  q_ib;
            assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
            wire [3:0]   qv0, qf0;
            wire [127:0] qy0;
            ot_attn_tile_m6h1q u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            // the first NLL of the NL result banks: 2 side-channel EW, then SN up to the N-face pin bank
            ot_attn_bpipe #(.W(136), .N(NLL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q(xr[x*136 +: 136]));
        end
    end endgenerate
endmodule

module hfd_attn_half_hi #(
    parameter integer PMID = 2,
    parameter integer NFC = 2,
    parameter integer NL = 8,
    parameter integer NLL = 3,
    parameter integer NI = 6
) (
    output wire [1617:0] cf,
    input  wire [0:0]    ck,
    input  wire [528:0]  i,
    output wire [528:0]  o,
    input  wire [1618:0] xp,
    input  wire [271:0]  xr
);
    localparam integer PK = 1618, PW = PK + 1, RW = 529;
    initial if (NL - NLL < 1 || PMID < 1 || NFC < 1) $fatal(1, "hfd_attn_half_hi: NL > NLL, PMID >= 1, NFC >= 1");
    wire clk = ck[0];
    // the S-face xp pin bank = quad row 1's first PMID bank and the first cf bank (tile: ROOT -> NFC + 1 banks -> cf)
    wire [PW-1:0] xin_q;
    ot_attn_bpipe #(.W(PW), .N(1)) u_xin (.clk(clk), .d(xp), .q(xin_q));
    ot_attn_bpipe #(.W(PK), .N(NFC)) u_fc (.clk(clk), .d(xin_q[PK-1:0]), .q(cf));
    wire [15:0] gov, oflt;
    wire [511:0] oy;
    genvar x, l;
    generate if (1) begin : g_y1
        wire [PW-1:0] mid_q;
        ot_attn_bpipe #(.W(PW), .N(PMID - 1)) u_mid (.clk(clk), .d(xin_q), .q(mid_q));
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 8 + 2 * x;
            wire [PW-1:0] row_q;
            ot_attn_bpipe #(.W(PW), .N(1)) u_row (.clk(clk), .d(mid_q), .q(row_q));
            wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
            wire [2:0]    q_ld_bank, q_ibank;
            wire [7:0]    q_ld_grp;
            wire [1023:0] q_ld_w;
            wire [575:0]  q_ib;
            assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
            wire [3:0]   qv0, qf0, qv, qf;
            wire [127:0] qy0, qy;
            ot_attn_tile_m6h1q u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            ot_attn_bpipe #(.W(136), .N(NL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q({qv, qf, qy}));
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
            // quad row 0's result words: the remaining NL - NLL banks (the first = the S-face xr pin bank)
            localparam integer GL = 2 * x;
            wire [3:0]   lv, lf;
            wire [127:0] ly;
            ot_attn_bpipe #(.W(136), .N(NL - NLL)) u_xr (.clk(clk), .d(xr[x*136 +: 136]), .q({lv, lf, ly}));
            for (l = 0; l < 4; l = l + 1) begin : g_ll
                localparam integer G = GL + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {lv[l], lf[l], ly[l*32 +: 32]};
            end
        end
    end endgenerate
    // the chain word i -> pin bank -> NI banks; valid-priority merge into the o pin bank (as hfd_attn_tile_b)
    wire [RW-1:0] chn_r;
    ot_attn_bpipe #(.W(RW), .N(1 + NI), .EW0(1)) u_pi (.clk(clk), .d(i), .q(chn_r));
    wire [RW-1:0] loc_r = {gov[0], oy, oflt};
    wire loc_v = loc_r[RW-1], chn_v = chn_r[RW-1];
    wire [RW-1:0] mrg = loc_v ? {loc_r[RW-1:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
    ot_attn_bpipe #(.W(RW), .N(1), .EW0(1), .EWN(1)) u_oo (.clk(clk), .d(mrg), .q(o));
endmodule
