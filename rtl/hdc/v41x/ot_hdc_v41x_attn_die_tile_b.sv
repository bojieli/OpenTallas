`timescale 1ns/1ps
// hbm-phys-1010 [att]: the quad's CG parameter selects the gated RTL in simulation; in synthesis the quad is the hard
// macro whose view IS the gated (CG 1: quad_b_tc/c891a57cf_cg_hm10) or ungated quad (route_half_cl.sh pairs them), and a
// hard-macro cell has no parameters.
`ifndef OT_ATTN_QCG
`ifdef SYNTHESIS
`define OT_ATTN_QCG
`else
`define OT_ATTN_QCG #(.CG(CG))
`endif
`endif
// ---------------------------------------------------------------------------
// HBM attention DIE TILE, margin + option-B version (Claude HBM SU/attn, 2026-10-06): the die master hfd_attn_tile
// (exact r16h ports, faces and pin positions; the HBM-ABSTRACTS interim view physical/hbm_accel_die_views/attn_tile/rtl
// on claude/hbm-abstracts-20261006 defines the function) rebuilt from HARDENED PIPELINE BANKS (ot_attn_bank_sn544 /
// ot_attn_bank_ew544, rtl/hdc/v41x/ot_hdc_v41x_attn_bank.sv) placed along explicit routes in the tile's channels, and
// the four option-B quads ot_attn_tile_m6h1q (PG <= M7).  Every tile pin is a bank pin (flop-direct), every hop is
// bank -> wire -> bank, and the tile's clock tree has ~100 bank / quad clock pins instead of ~29,000 flops.
// Function (as the interim view): the local packet {rst, k[1037:0], q[579:0]} (corner tile), ci (column tile) or ri
// (row tile) -- ORed, an unbound role is tied 0 at the die -- reaches ROOT; ROOT -> PMID mid banks -> a ROW bank per
// quad -> the quad; ROOT -> NFC / NFR banks -> the cf / rf pin banks.  Results: each quad's {gov, oflt, oy} -> NL banks;
// i -> its pin bank -> NI banks; valid-priority merge (local first, same-cycle chain word dropped with oflt set) -> o.
// Stage counts (every hop <= 350 um: tools/hbm_attn_die_tile_place.py, physical/hbm_attn_tile_r/die_tile/floorplan_b.json):
// k and q NK (equal: one packet), ci NC, ri NR, ROOT -> cf NFC / rf NFR (+ the pin bank), results NL (two side-channel EW
// stages, then SN), the chain NI (+ its pin bank).  Cycles added vs the interim view (pin + NS 2 + ROOT + NF 1 + pin):
// a local packet reaches ROOT in 1 + NK, the forward in 1 + NK + 1 + NFC / NFR + 1, results NL + 1, the chain 1 + NI + 1.
// ---------------------------------------------------------------------------
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

// hbm-phys-1010 [att]: the quad-result pipe (<= 136 bits) on the right-sized ot_attn_bank_{sn,ew}136 banks.  In a 544
// bank it routed 408 dead spare wires every hop (the hi half's SE merge corner: 42.8 k of its 103 k GRT-overflow net
// mentions).  Same parameters and bank instance names (gn.g_s[s].g_c[0].g_{sn,ew}.u_b) as ot_attn_bpipe.
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
    initial if (W > 136) $fatal(1, "ot_attn_bpipe136: W <= 136");
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

// N kept flop banks in series (std cells, for the few bits that do not fill a bank: q[581:544] and rst)
module ot_attn_fpipe #(parameter integer W = 1, parameter integer N = 1) (
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
    ot_attn_bpipe #(.W(1041), .N(1 + NK)) u_pk (.clk(clk), .d(k), .q(k_s));
    // q[543:0] in banks (the E pin bank, then SN), q[581:544] and rst in std-cell flops at the corner
    ot_attn_bpipe #(.W(544), .N(1 + NK), .EW0(1)) u_pq (.clk(clk), .d(q[543:0]), .q(q_s[543:0]));
    ot_attn_fpipe #(.W(39), .N(1 + NK)) u_pqx (.clk(clk), .d({rst[0], q[581:544]}), .q(q_s[582:544]));
    ot_attn_bpipe #(.W(PK),   .N(1 + NC)) u_pc (.clk(clk), .d(ci), .q(ci_s));
    ot_attn_bpipe #(.W(PK),   .N(1 + NR), .EW0(1)) u_pr (.clk(clk), .d(ri), .q(ri_s));
    // ---- ROOT: the OR of the three packet sources (the k / q forwarded clocks k[1040:1038] / q[581:580] end here)
    wire [PW-1:0] pk = {q_s[582], k_s[1037:0], q_s[579:0]} | {1'b0, ci_s} | {1'b0, ri_s};
    wire [PW-1:0] root_q;
    ot_attn_bpipe #(.W(PW), .N(1)) u_root (.clk(clk), .d(pk), .q(root_q));
    // ---- forward: ROOT -> NFC / NFR banks -> the cf / rf pin banks
    ot_attn_bpipe #(.W(PK), .N(NFC + 1)) u_fc (.clk(clk), .d(root_q[PK-1:0]), .q(cf));
    ot_attn_bpipe #(.W(PK), .N(NFR + 1), .EWN(1)) u_fr (.clk(clk), .d(root_q[PK-1:0]), .q(rf));
    // ---- ROOT -> PMID banks (a copy per quad row) -> a ROW bank per quad -> the quad (ot_attn_tile_m6h1p's ROW, split)
    wire [15:0] gov, oflt;
    wire [511:0] oy;
    genvar y, x, l;
    generate for (y = 0; y < 2; y = y + 1) begin : g_y
        wire [PW-1:0] mid_q;
        ot_attn_bpipe #(.W(PW), .N(PMID)) u_mid (.clk(clk), .d(root_q), .q(mid_q));
        for (x = 0; x < 2; x = x + 1) begin : g_x
            localparam integer GB = 8 * y + 2 * x;
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
            ot_attn_tile_m6h1q `OT_ATTN_QCG u_q (.clk(clk), .rst_n(q_rst_n), .qgid(GB[7:0]), .ld_v(q_ld_v), .ld_mode(q_ld_mode),
                .ld_bank(q_ld_bank), .ld_grp(q_ld_grp), .ld_w(q_ld_w), .ld_w2v(q_ld_w2v), .iv(q_iv), .ibank(q_ibank),
                .ib(q_ib), .gov(qv0), .oy(qy0), .oflt(qf0));
            // the quad's results -> NL banks (every quad the same depth: one result word)
            ot_attn_bpipe136 #(.W(136), .N(NL), .EWM(3)) u_res (.clk(clk), .d({qv0, qf0, qy0}), .q({qv, qf, qy}));
            for (l = 0; l < 4; l = l + 1) begin : g_l
                localparam integer G = GB + 4 * (l / 2) + (l % 2);
                assign {gov[G], oflt[G], oy[G*32 +: 32]} = {qv[l], qf[l], qy[l*32 +: 32]};
            end
        end
    end endgenerate
    // ---- results: the chain word i -> pin bank -> NI banks; valid-priority merge into the o pin bank
    wire [RW-1:0] chn_r;
    ot_attn_bpipe #(.W(RW), .N(1 + NI), .EW0(1)) u_pi (.clk(clk), .d(i), .q(chn_r));
    // CG-qualified boundary: the fixed word represents all16 heads. A partial
    // arrival is an explicit transaction fault, never a stale head's arithmetic.
    // Idle oflt/oy are held by gated producers and are consumed only under valid.
    wire [RW-1:0] loc_r;
    ot_attn_res_guard #(.CG(CG)) u_guard (.gov(gov), .oy(oy), .oflt(oflt), .w(loc_r));
    wire loc_v = loc_r[RW-1], chn_v = chn_r[RW-1];
    wire [RW-1:0] mrg = loc_v ? {loc_r[RW-1:16], loc_r[15:0] | {16{chn_v}}} : chn_r;
    ot_attn_bpipe #(.W(RW), .N(1), .EW0(1), .EWN(1)) u_oo (.clk(clk), .d(mrg), .q(o));
endmodule

// ---------------------------------------------------------------------------
// hbm-phys-1010 [att] (hgi-e2e audit item 1): the one result-word boundary of the 16 heads, shared by hfd_attn_tile_b,
// hfd_attn_half_hi and the bench quad set ot_attn_tile_m6h1x.  CG 0 (ungated quads, every head registers its datapath
// every cycle): the word rides head 0's valid, as before.  CG 1 (gated quads hold oy / oflt while their valid is low):
// the word is valid when ANY head is valid; it carries the heads' oy / oflt only when ALL 16 are valid together
// (the quads wake on one broadcast, so a coherent result is the only legal one); a partial arrival (a quad late,
// early or masked) is a transaction FAULT -- every oflt set, oy zero -- never a held head's stale value.
// ---------------------------------------------------------------------------
module ot_attn_res_guard #(parameter integer CG = 0) (
    input  wire [15:0]  gov,
    input  wire [511:0] oy,
    input  wire [15:0]  oflt,
    output wire [528:0] w
);
    wire coherent_v = &gov;
    assign w = (CG != 0) ? {(|gov), coherent_v ? oy : 512'd0, coherent_v ? oflt : 16'hffff} : {gov[0], oy, oflt};
endmodule
