`define OT_ATTN_QCG
module ot_attn_bpipe #(
    parameter integer W = 544,
    parameter integer N = 1,          // banks in series (0: a wire)
    parameter integer EW0 = 0,        // the first stage as EW banks (an E / W pin bank), else SN
    parameter integer EWN = 0,        // the last stage as EW banks (an E / W pin bank), else SN
    parameter integer EWM = 0         // bit s set: stage s as EW banks (side-channel stages)
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer NB = (W + 543) / 544;
    genvar s, c;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [NB*544-1:0] st [0:N];
        assign st[0] = {{(NB*544-W){1'b0}}, d};
        for (s = 0; s < N; s = s + 1) begin : g_s
            for (c = 0; c < NB; c = c + 1) begin : g_c
                if ((s == 0 && EW0 != 0) || (s == N - 1 && EWN != 0) || ((EWM >> s) & 1)) begin : g_ew
                    ot_attn_bank_ew544 u_b (.clk(clk), .d(st[s][c*544 +: 544]), .q(st[s+1][c*544 +: 544]));
                end else begin : g_sn
                    ot_attn_bank_sn544 u_b (.clk(clk), .d(st[s][c*544 +: 544]), .q(st[s+1][c*544 +: 544]));
                end
            end
        end
        assign q = st[N][W-1:0];
    end endgenerate
endmodule
module ot_attn_bpipe136 #(
    parameter integer W = 136,
    parameter integer N = 1,
    parameter integer EW0 = 0,
    parameter integer EWN = 0,
    parameter integer EWM = 0
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    
    genvar s, c;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [135:0] st [0:N];
        assign st[0] = {{(136-W){1'b0}}, d};
        for (s = 0; s < N; s = s + 1) begin : g_s
            for (c = 0; c < 1; c = c + 1) begin : g_c
                if ((s == 0 && EW0 != 0) || (s == N - 1 && EWN != 0) || ((EWM >> s) & 1)) begin : g_ew
                    ot_attn_bank_ew136 u_b (.clk(clk), .d(st[s]), .q(st[s+1]));
                end else begin : g_sn
                    ot_attn_bank_sn136 u_b (.clk(clk), .d(st[s]), .q(st[s+1]));
                end
            end
        end
        assign q = st[N][W-1:0];
    end endgenerate
endmodule

module ot_attn_fpipe #(parameter W=1, parameter N=1)
 (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
  // Same bank semantics, one edge per stage. Spare bits are tied low.
  ot_attn_bpipe136 #(.W(W),.N(N)) u_hard (.clk(clk),.d(d),.q(q));
endmodule
module hfd_attn_half_lo #(
    parameter integer CG = 0, // must match half_hi for gated successor
    parameter integer ROWEW = 0,   // hbm-phys-1010 [att]: 1 = EW row banks (floorplan half_v2); 0 = SN (half / half_ps)
    parameter integer NK = 4,
    parameter integer NC = 2,
    parameter integer NR = 3,
    parameter integer PMID = 2,
    parameter integer NXP = 0,   // el1011-hbm-attn v8: root -> xp pipe stages (0: xp = root_q, the root is the N pin bank).  The v8
                                 // floorplan puts the merge root at the BOTTOM (where ci / k / ks / q / ri land) and moves 2 stages from
                                 // every input pipe (NK/NC/NR -2) to every output pipe (NXP 2, PMID/NFR +2): same latency per path.
    parameter integer NFR = 3,
    parameter integer NLL = 3,      // result banks of quad row 0 in lo (2 side-channel EW + the N-face pin bank)
    parameter integer LDKR = 0      // el1011-hbm-attn v11: 0 = ldk pin drives the ld mux directly (2,076 loads behind a pin);
                                    // > 0 = ldk registered at the pin into LDKR replicated copies + 1 relay stage, each copy
                                    // selecting <= ceil(1038 / LDKR) mux bits.  ldk is a static strap: 2 cycles are exact after fill.
) (
    input  wire [1617:0] ci,
    input  wire [0:0]    ck,
    input  wire [1040:0] k,
    input  wire [1101:0] ks,       // hbm-forks RQ-HF-4: the svc PS row port of this tile's pair (entry tiles only; others
                                   // leave it unconnected at the die = 0): {fclk x3, meta64, row1024, rq10, v}, meta[32:20] =
                                   // the stream's load tag {ld_mode, ld_bank3, ld_grp8, ld_w2v} (compiler-supplied), meta[19] = idx
    input  wire [0:0]    ldk,      // hbm-forks 2026-10-09 (RQ-HF-4, 8 KV entry points a stack): STATIC die strap (by_design
                                   // tie, false path).  1: the ld half of the packet comes from this tile's own k port only
                                   // (the forward chains' ld field is ignored; they still carry the query); 0: today's OR
    output wire [1:0]    kq,       // hgi-1010/g2 2026-10-10 (audit N9): the PS row port's LINE CREDIT back to the svc group
                                   // unit, {forwarded clock, v}: one pulse per row consumed (the tile takes a row a cycle,
                                   // so every row that lands at the pin is consumed); entry tiles only (others: open)
    input  wire [581:0]  q,
    output wire [1617:0] rf,
    input  wire [1617:0] ri,
    input  wire [0:0]    rst,
    output wire [1618:0] xp,
    output wire [271:0]  xr
);
    localparam integer PK = 1618, PW = PK + 1;
    
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
    // the entry formatter: a PS row (KV rows only, idx = 0) becomes the ld packet {ld_v, ld_mode, ld_bank, ld_grp, ld_w,
    // ld_w2v}; the row rides the same 1 + NK pin pipe as k, so its packet reaches ROOT in the same cycle k would (0 added)
    wire [1101:0] ks_s;
    // el1011-hbm-attn-phys (two-level): the ks pin stage + the line credit (forwarded clock) are the hard leaf tile
    // ot_attn_ks_entry at the ks entry face; the remaining NK stages stay pipe banks.  Same latency (1 + NK).
    wire [1101:0] ks_e;
    ot_attn_ks_entry u_kse (.clk(clk), .rst(rst), .ks(ks), .ks_r(ks_e), .kq(kq));
    ot_attn_bpipe #(.W(1102), .N(NK)) u_pks (.clk(clk), .d(ks_e), .q(ks_s));
    wire [63:0] ks_meta = ks_s[1098:1035];
    wire [1037:0] ks_ld = {ks_s[0] & ~ks_meta[19], ks_meta[32], ks_meta[31:29], ks_meta[28:21], ks_s[1034:11], ks_meta[20]};
    wire [1037:0] ld_sel;                                    // per-bit ld select (replicated strap copies when LDKR > 0)
    generate if (LDKR == 0) begin : g_ldk0
        assign ld_sel = {1038{ldk_s}};
    end else begin : g_ldkr
        wire [LDKR-1:0] ldk_r;
        ot_attn_fpipe #(.W(LDKR), .N(2)) u_pldk (.clk(clk), .d({LDKR{ldk_s}}), .q(ldk_r));
        genvar li;
        for (li = 0; li < 1038; li = li + 1) begin : g_sel
            assign ld_sel[li] = ldk_r[(li * LDKR) / 1038];
        end
    end endgenerate
    wire [1037:0] ld_mux = (ld_sel & ks_ld) | (~ld_sel & (k_s[1037:0] | fw[PK-1:580]));
    wire [PW-1:0] pk = {q_s[582], ld_mux, q_s[579:0] | fw[579:0]};
    wire [PW-1:0] root_q;
    generate if (LDKR == 16) begin : g_rt
        // el1011-hbm-attn-phys (two-level): the formatter / ldk relay / OR / ld mux + the ROOT register are ONE hard
        // leaf tile (glue pushed into the tile; local clock tree), fed by the last stage of every input pipe bank
        ot_attn_lo_root u_rt (.clk(clk), .k_s(k_s), .q_s(q_s), .ci_s(ci_s), .ri_s(ri_s), .ks_s(ks_s), .ldk(ldk), .root_q(root_q));
    end else begin : g_rb
        // ROOT on the N face: its bank outputs are the xp pins
        ot_attn_bpipe #(.W(PW), .N(1)) u_root (.clk(clk), .d(pk), .q(root_q));
    end endgenerate
    generate if (NXP == 0) begin : g_xp0
        assign xp = root_q;
    end else begin : g_xpp
        ot_attn_bpipe #(.W(PW), .N(NXP)) u_xpp (.clk(clk), .d(root_q), .q(xp));
    end endgenerate
    ot_attn_bpipe #(.W(PK), .N(NFR + 1), .EWN(1)) u_fr (.clk(clk), .d(root_q[PK-1:0]), .q(rf));
    genvar x;
    generate if (1) begin : g_y0
        wire [PW-1:0] mid_q;
        ot_attn_bpipe #(.W(PW), .N(PMID)) u_mid (.clk(clk), .d(root_q), .q(mid_q));
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 2 * x;
            wire [PW-1:0] row_q;
            // hbm-phys-1010 [att]: ROWEW 1 = the ROW stage as EW banks (q facing the quad's M4 input edge; floorplan v2)
            ot_attn_bpipe #(.W(PW), .N(1), .EW0(ROWEW)) u_row (.clk(clk), .d(mid_q), .q(row_q));
            wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
            wire [2:0]    q_ld_bank, q_ibank;
            wire [7:0]    q_ld_grp;
            wire [1023:0] q_ld_w;
            wire [575:0]  q_ib;
            assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
            wire [3:0]   qv0, qf0;
            wire [127:0] qy0;
            ot_attn_tile_m6h1q `OT_ATTN_QCG u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            // the first NLL of the NL result banks: 2 side-channel EW, then SN up to the N-face pin bank
            ot_attn_bpipe136 #(.W(136), .N(NLL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q(xr[x*136 +: 136]));
        end
    end endgenerate
endmodule
module hfd_attn_half_hi #(
    parameter integer CG = 0, // must match half_lo; validates all16 required heads
    parameter integer ROWEW = 0,   // hbm-phys-1010 [att]: 1 = EW row banks (floorplan half_v2)
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
            // hbm-phys-1010 [att]: ROWEW 1 = the ROW stage as EW banks (q facing the quad's M4 input edge; floorplan v2)
            ot_attn_bpipe #(.W(PW), .N(1), .EW0(ROWEW)) u_row (.clk(clk), .d(mid_q), .q(row_q));
            wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
            wire [2:0]    q_ld_bank, q_ibank;
            wire [7:0]    q_ld_grp;
            wire [1023:0] q_ld_w;
            wire [575:0]  q_ib;
            assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
            wire [3:0]   qv0, qf0, qv, qf;
            wire [127:0] qy0, qy;
            ot_attn_tile_m6h1q `OT_ATTN_QCG u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            ot_attn_bpipe136 #(.W(136), .N(NL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q({qv, qf, qy}));
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
            // quad row 0's result words: the remaining NL - NLL banks (the first = the S-face xr pin bank)
            localparam integer GL = 2 * x;
            wire [3:0]   lv, lf;
            wire [127:0] ly;
            ot_attn_bpipe136 #(.W(136), .N(NL - NLL)) u_xr (.clk(clk), .d(xr[x*136 +: 136]), .q({lv, lf, ly}));
            for (l = 0; l < 4; l = l + 1) begin : g_ll
                localparam integer G = GL + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {lv[l], lf[l], ly[l*32 +: 32]};
            end
        end
    end endgenerate
    // the chain word i -> pin bank -> NI banks; valid-priority merge into the o pin bank (as hfd_attn_tile_b)
    wire [RW-1:0] chn_r;
    ot_attn_bpipe #(.W(RW), .N(1 + NI), .EW0(1)) u_pi (.clk(clk), .d(i), .q(chn_r));
    // CG-qualified boundary: the fixed word represents all16 heads. A partial
    // arrival is an explicit transaction fault, never a stale head's arithmetic.
    // Idle oflt/oy are held by gated producers and are consumed only under valid.
    generate if (CG != 0) begin : g_mt
        // el1011-hbm-attn-phys (two-level): the all-16-heads guard (&gov / |gov), the 529-bit merge mux and the o
        // register are ONE hard leaf tile placed where the result pipes and the chain end (v12 hi: this guard was
        // placed as soft glue in a macro-packed corner, preroute reg2reg -8.35 ns)
        ot_attn_hi_merge u_mt (.clk(clk), .gov(gov), .oy(oy), .oflt(oflt), .chn_r(chn_r), .o(o));
    end else begin : g_mb
        wire [RW-1:0] loc_r;
        ot_attn_res_guard #(.CG(CG)) u_guard (.gov(gov), .oy(oy), .oflt(oflt), .w(loc_r));
        wire loc_v = loc_r[RW-1], chn_v = chn_r[RW-1];
        wire [RW-1:0] mrg = loc_v ? {loc_r[RW-1:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
        ot_attn_bpipe #(.W(RW), .N(1), .EW0(1), .EWN(1)) u_oo (.clk(clk), .d(mrg), .q(o));
    end endgenerate
endmodule

module ot_attn_lo_root (
    input  wire          clk,
    input  wire [1040:0] k_s,
    input  wire [582:0]  q_s,
    input  wire [1617:0] ci_s,
    input  wire [1617:0] ri_s,
    input  wire [1101:0] ks_s,
    input  wire [0:0]    ldk,
    output reg  [1618:0] root_q
);
    localparam integer PK = 1618, PW = PK + 1, LDKR = 16;
`ifdef OT_ATTN_MUT_LDK
    wire ldk_s = 1'b0;                                       // NEGATIVE CONTROL: the strap ignored
`else
    wire ldk_s = ldk[0];
`endif
    wire [PK-1:0] fw = ci_s | ri_s;
    wire [63:0] ks_meta = ks_s[1098:1035];
    wire [1037:0] ks_ld = {ks_s[0] & ~ks_meta[19], ks_meta[32], ks_meta[31:29], ks_meta[28:21], ks_s[1034:11], ks_meta[20]};
    reg  [LDKR-1:0] ldk_p, ldk_r;                            // pin stage + relay stage (static strap: exact after fill)
    always @(posedge clk) begin ldk_p <= {LDKR{ldk_s}}; ldk_r <= ldk_p; end
    wire [1037:0] ld_sel;
    genvar li;
    generate for (li = 0; li < 1038; li = li + 1) begin : g_sel
        assign ld_sel[li] = ldk_r[(li * LDKR) / 1038];
    end endgenerate
    wire [1037:0] ld_mux = (ld_sel & ks_ld) | (~ld_sel & (k_s[1037:0] | fw[PK-1:580]));
    always @(posedge clk) root_q <= {q_s[582], ld_mux, q_s[579:0] | fw[579:0]};
endmodule
module ot_attn_hi_merge (
    input  wire         clk,
    input  wire [15:0]  gov,
    input  wire [511:0] oy,
    input  wire [15:0]  oflt,
    input  wire [528:0] chn_r,
    output reg  [528:0] o
);
    wire [528:0] loc_r;
    ot_attn_res_guard #(.CG(1)) u_guard (.gov(gov), .oy(oy), .oflt(oflt), .w(loc_r));
    wire loc_v = loc_r[528], chn_v = chn_r[528];
    always @(posedge clk) o <= loc_v ? {loc_r[528:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
endmodule
module ot_attn_ks_entry (
    input  wire          clk,
    input  wire [0:0]    rst,
    input  wire [1101:0] ks,
    output reg  [1101:0] ks_r,
    output wire [1:0]    kq
);
    always @(posedge clk) ks_r <= ks;
    ot_attn_ks_credit u_kq (.clk(clk), .rst_n(rst[0]), .ks_v(ks[0]), .kq(kq));
endmodule
module ot_attn_ks_credit (input wire clk, input wire rst_n, input wire ks_v, output wire [1:0] kq);
    reg v; reg [3:0] n;
    always @(posedge clk) begin
`ifdef OT_ATTN_MUT_KQ_DROP
        v <= ks_v && rst_n && n != 4'd15;
`elsif OT_ATTN_MUT_KQ_DUP
        v <= (ks_v || n == 4'd15) && rst_n;
`else
        v <= ks_v && rst_n;
`endif
        n <= !rst_n ? 4'd0 : n + (ks_v ? 4'd1 : 4'd0);
    end
    wire fck; ot_fwd_clk_inv u_fck (.a(clk), .y(fck));
    assign kq = {fck, v};
endmodule

module ot_attn_bpipe_reference #(
    parameter integer W = 544,
    parameter integer N = 1,          // banks in series (0: a wire)
    parameter integer EW0 = 0,        // the first stage as EW banks (an E / W pin bank), else SN
    parameter integer EWN = 0,        // the last stage as EW banks (an E / W pin bank), else SN
    parameter integer EWM = 0         // bit s set: stage s as EW banks (side-channel stages)
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer NB = (W + 543) / 544;
    genvar s, c;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [NB*544-1:0] st [0:N];
        assign st[0] = {{(NB*544-W){1'b0}}, d};
        for (s = 0; s < N; s = s + 1) begin : g_s
            for (c = 0; c < NB; c = c + 1) begin : g_c
                if ((s == 0 && EW0 != 0) || (s == N - 1 && EWN != 0) || ((EWM >> s) & 1)) begin : g_ew
                    ot_attn_bank_ew544 u_b (.clk(clk), .d(st[s][c*544 +: 544]), .q(st[s+1][c*544 +: 544]));
                end else begin : g_sn
                    ot_attn_bank_sn544 u_b (.clk(clk), .d(st[s][c*544 +: 544]), .q(st[s+1][c*544 +: 544]));
                end
            end
        end
        assign q = st[N][W-1:0];
    end endgenerate
endmodule
module ot_attn_bpipe136_reference #(
    parameter integer W = 136,
    parameter integer N = 1,
    parameter integer EW0 = 0,
    parameter integer EWN = 0,
    parameter integer EWM = 0
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    initial if (W > 136) $fatal(1, "ot_attn_bpipe136_reference: W <= 136");
    genvar s, c;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [135:0] st [0:N];
        assign st[0] = {{(136-W){1'b0}}, d};
        for (s = 0; s < N; s = s + 1) begin : g_s
            for (c = 0; c < 1; c = c + 1) begin : g_c
                if ((s == 0 && EW0 != 0) || (s == N - 1 && EWN != 0) || ((EWM >> s) & 1)) begin : g_ew
                    ot_attn_bank_ew136 u_b (.clk(clk), .d(st[s]), .q(st[s+1]));
                end else begin : g_sn
                    ot_attn_bank_sn136 u_b (.clk(clk), .d(st[s]), .q(st[s+1]));
                end
            end
        end
        assign q = st[N][W-1:0];
    end endgenerate
endmodule
module ot_attn_fpipe_reference #(parameter integer W = 1, parameter integer N = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    genvar s;
    generate if (N == 0) begin : g0
        assign q = d;
    end else begin : gn
        wire [W-1:0] st [0:N];
        assign st[0] = d;
        for (s = 0; s < N; s = s + 1) begin : g_s
            (* keep = "true" *) ot_attn_rp_reg #(.W(W)) u_r (.clk(clk), .d(st[s]), .q(st[s+1]));
        end
        assign q = st[N];
    end endgenerate
endmodule
module hfd_attn_tile_b #(
    parameter integer CG = 0, // gated quads and coherent-result guard, jointly opt-in
    parameter integer NK = 4,
    parameter integer NC = 2,
    parameter integer NR = 3,
    parameter integer PMID = 1,
    parameter integer NFC = 2,
    parameter integer NFR = 3,
    parameter integer NL = 6,
    parameter integer PMID1X = 0,  // el1011-hbm-attn v10: extra mid stages for quad row y=1 only (the split tile's lo->hi xp pipe
                                  // gained a stage on a taller lo; the reference mirrors it; 0 = unchanged)
    parameter integer NI = 4
) (
    output wire [1617:0] cf,
    input  wire [1617:0] ci,
    input  wire [0:0]    ck,
    input  wire [528:0]  i,
    input  wire [1040:0] k,
    output wire [528:0]  o,
    input  wire [581:0]  q,
    output wire [1617:0] rf,
    input  wire [1617:0] ri,
    input  wire [0:0]    rst
);
    localparam integer PK = 1618, PW = PK + 1, RW = 529;
    wire clk = ck[0];
    // ---- pin banks + the source pipes (k / q: the local packet halves; rst rides with q)
    wire [1040:0] k_s; wire [582:0] q_s; wire [PK-1:0] ci_s, ri_s;
    ot_attn_bpipe_reference #(.W(1041), .N(1 + NK)) u_pk (.clk(clk), .d(k), .q(k_s));
    // q[543:0] in banks (the E pin bank, then SN), q[581:544] and rst in std-cell flops at the corner
    ot_attn_bpipe_reference #(.W(544), .N(1 + NK), .EW0(1)) u_pq (.clk(clk), .d(q[543:0]), .q(q_s[543:0]));
    ot_attn_fpipe_reference #(.W(39), .N(1 + NK)) u_pqx (.clk(clk), .d({rst[0], q[581:544]}), .q(q_s[582:544]));
    ot_attn_bpipe_reference #(.W(PK),   .N(1 + NC)) u_pc (.clk(clk), .d(ci), .q(ci_s));
    ot_attn_bpipe_reference #(.W(PK),   .N(1 + NR), .EW0(1)) u_pr (.clk(clk), .d(ri), .q(ri_s));
    // ---- ROOT: the OR of the three packet sources (the k / q forwarded clocks k[1040:1038] / q[581:580] end here)
    wire [PW-1:0] pk = {q_s[582], k_s[1037:0], q_s[579:0]} | {1'b0, ci_s} | {1'b0, ri_s};
    wire [PW-1:0] root_q;
    ot_attn_bpipe_reference #(.W(PW), .N(1)) u_root (.clk(clk), .d(pk), .q(root_q));
    // ---- forward: ROOT -> NFC / NFR banks -> the cf / rf pin banks
    ot_attn_bpipe_reference #(.W(PK), .N(NFC + 1)) u_fc (.clk(clk), .d(root_q[PK-1:0]), .q(cf));
    ot_attn_bpipe_reference #(.W(PK), .N(NFR + 1), .EWN(1)) u_fr (.clk(clk), .d(root_q[PK-1:0]), .q(rf));
    // ---- ROOT -> PMID banks (a copy per quad row) -> a ROW bank per quad -> the quad (ot_attn_tile_m6h1p's ROW, split)
    wire [15:0] gov, oflt;
    wire [511:0] oy;
    genvar y, x, l;
    generate for (y = 0; y < 2; y = y + 1) begin : g_y
        wire [PW-1:0] mid_q;
        ot_attn_bpipe_reference #(.W(PW), .N(PMID + ((y == 1) ? PMID1X : 0))) u_mid (.clk(clk), .d(root_q), .q(mid_q));
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 8 * y + 2 * x;
            wire [PW-1:0] row_q;
            ot_attn_bpipe_reference #(.W(PW), .N(1)) u_row (.clk(clk), .d(mid_q), .q(row_q));
            wire          q_rst_n, q_ld_v, q_ld_mode, q_ld_w2v, q_iv;
            wire [2:0]    q_ld_bank, q_ibank;
            wire [7:0]    q_ld_grp;
            wire [1023:0] q_ld_w;
            wire [575:0]  q_ib;
            assign {q_rst_n, q_ld_v, q_ld_mode, q_ld_bank, q_ld_grp, q_ld_w, q_ld_w2v, q_iv, q_ibank, q_ib} = row_q;
            wire [3:0]   qv0, qf0, qv, qf;
            wire [127:0] qy0, qy;
            ot_attn_tile_m6h1q `OT_ATTN_QCG u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            // the quad's results -> NL banks (every quad the same depth: one result word)
            ot_attn_bpipe136_reference #(.W(136), .N(NL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q({qv, qf, qy}));
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
        end
    end endgenerate
    // ---- results: the chain word i -> pin bank -> NI banks; valid-priority merge into the o pin bank
    wire [RW-1:0] chn_r;
    ot_attn_bpipe_reference #(.W(RW), .N(1 + NI), .EW0(1)) u_pi (.clk(clk), .d(i), .q(chn_r));
    // CG-qualified boundary: the fixed word represents all16 heads. A partial
    // arrival is an explicit transaction fault, never a stale head's arithmetic.
    // Idle oflt/oy are held by gated producers and are consumed only under valid.
    wire [RW-1:0] loc_r;
    ot_attn_res_guard #(.CG(CG)) u_guard (.gov(gov), .oy(oy), .oflt(oflt), .w(loc_r));
    wire loc_v = loc_r[RW-1], chn_v = chn_r[RW-1];
    wire [RW-1:0] mrg = loc_v ? {loc_r[RW-1:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
    ot_attn_bpipe_reference #(.W(RW), .N(1), .EW0(1), .EWN(1)) u_oo (.clk(clk), .d(mrg), .q(o));
endmodule
