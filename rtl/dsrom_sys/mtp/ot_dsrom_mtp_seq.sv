`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_mtp_seq: the DS-ROM S81 head-die MTP sequencer (stream mtp-rom, 2026-10-08; MTP_AUDIT gap G2).
//
// Where it sits.  The head stage's package controller frames one RESULT flit per verified position
// ({user, pos, argmax token, logit}, the WFC header layout).  This block sits on that RESULT stream between
// the head controller and the token-return link to stage 0 (S0, the SOURCE WFC), and drives the DSpark draft
// chain: the seed to the draft dies, the 5 serial draft-head steps on the head die's lm_head bundles, and the
// DRAFT-block write into S0's token store (ot_dsrom_wfc_tok).
//
// Division of labour with the WFC (exactness by construction).  S0's WFC (ot_rom_pkg_ctrl_wfc, WAVE 1) is the
// only place that verifies: every issued token is compared with the previous position's argmax there, a
// mismatch squashes and re-issues.  Whatever this block does, the emitted token stream is the greedy stream.
// This block only decides WHEN drafts exist and WHAT they are: it mirrors the WFC's accept (the greedy
// prefix accept of ot_hdc_accept / hdc_golden_v41.generate_spec, streamed on the arriving results, dataflow
// level 3), and so knows a step's accepted count a, its bonus t_a and the WFC's draft-block epoch (wblk: +1 on
// every rejection).
//
// The step protocol (one user; results return in issue order):
//   block (b, g, d_1..d_g): y issued at position b, drafts at b+1 .. b+g.  The result at position b+i
//   (target t_i) accepts while i < g and t_i == d_{i+1}.  The CLOSING result is the first mismatch (a = i,
//   a rejection: epoch + 1) or i == g (a = g, all accepted).  The closing result and every result of that
//   user behind it (the g - a squashed positions, which the WFC discards) are HELD here; the seed goes to the
//   draft dies at once; when the drafter's 5 rows are on the head die (rows_in) the 5 draft-head steps run
//   serially (dh_out / dh_in: lm_head sweep + Markov row of the previous token + bias + argmax); then the
//   DRAFT flit {user, epoch, base b'+1, g', d'_1..d'_g'} is sent, followed by the held results in order.  S0's
//   link shim writes the DRAFT flit into the token store before the closing result reaches the WFC, so the
//   WFC's re-issue of y = t_a at b' = b+a+1 finds d'_1.. known and issues the next 6-position wavefront back to
//   back -- exactly the composition's step: verify + draft + seed, serial (dsrom_1m_allmeasured MTP block).
//   Prefill: positions < plen-1 are forwarded untouched; the result at plen-1 closes block (plen-1, 0).
//   End: g' = min(G, steps-1-b') with steps = plen + glen - 1 (the WFC never issues a position >= steps);
//   g' = 0 releases at once (no draft); a user whose b' >= steps is finished.
// Squashed-count invariant: the release waits until all g - a squashed results are back.  The WFC has issued
// every position of a block before the block's first result returns (AR walk > (G+1) stage intervals on any
// array of >= 7 stages), so exactly g - a results are squashed.
// Users >= MAXU pass straight through (no drafts: the WFC runs them autoregressively, still exact).
//
// Interfaces: valid/ready here; the physical wrapper dsfd_mtp_seq puts every port behind the WFC's registered
// LINK_REG pair (pin flops, grant protocol).  Internally one event at a time through a registered 4-step
// pipeline (SEL -> RD -> PRE -> EX -> WB -> WB2), each step ~1 compare / mux level group (safe-margin RTL, ~700 ps).
// Cycles: a forwarded RESULT +7 (event) + the wrapper's pins; a release 6 cycles per emitted flit.
//
// Mutants (negative controls, never in a real build):
//   OT_MTPSEQ_MUT_OFF1     accept compares t_i with d_i (off by one)
//   OT_MTPSEQ_MUT_NOEPOCH  the epoch is not advanced on a rejection
//   OT_MTPSEQ_MUT_NOHOLD   the closing result is forwarded before the DRAFT flit
//   OT_MTPSEQ_MUT_PREV     the draft-head step j > 1 is given y instead of d_{j-1}
// ---------------------------------------------------------------------------
module ot_dsrom_mtp_seq #(
    parameter integer FLIT   = 512,
    parameter integer NW     = 21,      // token / position bits (WFC full shape)
    parameter integer USER_W = 10,
    parameter integer MAXU   = 8,       // users with MTP state (others pass through)
    parameter integer G      = 5,       // gamma (DSpark block 5)
    parameter integer SRC_ID = 0,       // header SRC of the DRAFT flit
    parameter integer TOK_DEST = 0,     // header DEST of the DRAFT flit (S0)
    parameter integer WB_STAGE = 0      // 1: EX decisions are registered and every write and push applies one cycle
                                        // later, in S_WB; state seen at the next S_RD and relv seen at S_SEL are
                                        // unchanged, t / s / h / acc / fault leave one cycle later (DIE-HEAD-63)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NW-1:0]     cfg_plen,
    input  wire [NW-1:0]     cfg_glen,
    // RESULT flits from the head stage controller
    input  wire              r_valid,
    output wire              r_ready,
    input  wire [FLIT-1:0]   r_data,
    // to the token-return link (S0): RESULT + DRAFT flits
    output wire              t_valid,
    input  wire              t_ready,
    output wire [FLIT-1:0]   t_data,
    // seed to the draft primary: {user, anchor, nrows, y, epoch}
    output wire              s_valid,
    input  wire              s_ready,
    output wire [USER_W+3*NW+4-1:0] s_data,
    // the drafter's rows for a user are on the head die
    input  wire              w_valid,
    output wire              w_ready,
    input  wire [USER_W-1:0] w_user,
    // draft-head step: {user, j, prev token}
    output wire              h_valid,
    input  wire              h_ready,
    output wire [USER_W+3+NW-1:0] h_data,
    // draft-head result: {user, j, token}
    input  wire              q_valid,
    output wire              q_ready,
    input  wire [USER_W+3+NW-1:0] q_data,
    // observation
    output reg               acc_v,          // a step closed
    output reg  [USER_W-1:0] acc_u,
    output reg  [2:0]        acc_a,
    output reg  [NW-1:0]     acc_c,          // closing position (= the committed anchor)
    output reg  [NW-1:0]     acc_y,          // bonus
    output reg               fault
);
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32,
                       HDR_POS = 40, HDR_IDX = HDR_POS + NW, HDR_VAL = HDR_IDX + NW,
                       HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW, HDR_USER_HI = HDR_ADDR + 16;
    localparam integer UHIW = (USER_W > 8) ? USER_W - 8 : 1;
    localparam integer DR_N = 248, DR_D = 256;               // DRAFT flit: count, drafts
    localparam [3:0] MT_RESULT = 4'd2, MT_DRAFT = 4'd4;
    localparam integer HD = G + 1;                           // hold depth: closing + G squashed
    localparam integer HW = 2 * NW + 32;                     // held result: pos, idx, val
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer HB = $clog2(HD);
    localparam integer SW = USER_W + 3 * NW + 4, DW = USER_W + 3 + NW;
    localparam [1:0] P_RUN = 2'd0, P_DRAFT = 2'd1, P_REL = 2'd2;
    initial if (G < 1 || G > 6 || DR_D + G * NW > FLIT || HDR_USER_HI + UHIW > DR_N)
        $fatal(1, "ot_dsrom_mtp_seq: G / flit layout");

    // ---------------------------------------------------------------- reset root (registered)
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;              // rst_n is synchronous (released by the top's synchroniser)
    reg [NW-1:0] plen_q, steps_q, plm1_q;
    always @(posedge clk) begin                       // static configuration, settles during reset
        plen_q  <= cfg_plen;
        plm1_q  <= cfg_plen - 1'b1;
        steps_q <= cfg_plen + cfg_glen - 1'b1;
    end

    // ---------------------------------------------------------------- per-user records (flops)
    reg [1:0]    u_ph  [0:MAXU-1];
    reg          u_pf  [0:MAXU-1];                    // prefill (positions < b are prompt results)
    reg          u_fin [0:MAXU-1];
    reg [NW-1:0] u_b   [0:MAXU-1];
    reg [2:0]    u_g   [0:MAXU-1];
    reg [NW*G-1:0] u_d [0:MAXU-1];
    reg [3:0]    u_ep  [0:MAXU-1];
    reg [NW-1:0] u_lc  [0:MAXU-1];                    // positions already seeded (rows sent)
    reg [NW-1:0] u_y   [0:MAXU-1];
    reg [2:0]    u_j   [0:MAXU-1];                    // draft-head steps done
    reg          u_rw  [0:MAXU-1];                    // rows on the head die
    reg [2:0]    u_sqn [0:MAXU-1], u_sqs [0:MAXU-1];  // squashed needed / seen
    reg          u_dr  [0:MAXU-1];                    // DRAFT flit still to send in this release
    reg [HW-1:0] u_hq  [0:MAXU*HD-1];                 // hold queues
    reg [HB:0]   u_hn  [0:MAXU-1];                    // held entries
    reg [HB-1:0] u_hr  [0:MAXU-1];

    // ---------------------------------------------------------------- output queues (2-deep, registered)
    reg [FLIT-1:0] tq [0:3]; reg [1:0] tq_r, tq_w; reg [2:0] tq_n;
    assign t_valid = tq_n != 0; assign t_data = tq[tq_r];
    reg [SW-1:0] sq_d; reg sq_v;
    assign s_valid = sq_v; assign s_data = sq_d;
    reg [DW-1:0] hq_d; reg hq_v;
    assign h_valid = hq_v; assign h_data = hq_d;

    // ---------------------------------------------------------------- event pipeline
    localparam [2:0] E_RES = 3'd1, E_ROW = 3'd2, E_DH = 3'd3, E_REL = 3'd4, E_PASS = 3'd5;
    localparam [2:0] S_SEL = 3'd0, S_RD = 3'd1, S_PRE = 3'd2, S_EX = 3'd3, S_WB = 3'd4, S_WB2 = 3'd5;
    reg [2:0]  st;
    reg [2:0]  ek;
    reg [USER_W-1:0] eu;
    reg [UB-1:0] ei;
    reg [FLIT-1:0] ef;                                // the RESULT flit of a result event
    reg [NW-1:0] ep_, et_;                            // event position / token (or dh token)
    reg [2:0]  ej;
    // the selected user's record (RD)
    reg [1:0]  r_ph; reg r_pf, r_fin, r_rw, r_dr; reg [NW-1:0] r_b, r_lc, r_y; reg [2:0] r_g, r_j, r_sqn, r_sqs;
    reg [NW*G-1:0] r_d; reg [3:0] r_ep; reg [HB:0] r_hn; reg [HB-1:0] r_hr; reg [HW-1:0] r_hh;
    // precomputed (PRE)
    reg [NW-1:0] x_i;  reg x_lo, x_ilt, x_ieq, x_igt, x_dm, x_last, x_pl; reg [NW-1:0] x_b1, x_rem; reg x_fin1;
    reg [NW-1:0] x_nrow;
    // WB_STAGE: hold-queue addresses, precomputed from the registered record
    localparam integer HQA = $clog2(MAXU * HD);
    reg [HQA-1:0] x_hwa, x_hra;                       // write slot behind the held entries / read slot

    // release candidates: users in P_REL with every squashed result back (registered vector)
    reg [MAXU-1:0] relv;
    integer k;
    always @(posedge clk) for (k = 0; k < MAXU; k = k + 1)
        relv[k] <= rst_q && u_ph[k] == P_REL && u_sqs[k] == u_sqn[k];
    reg [UB-1:0] rel_i; reg rel_any;
    always @(*) begin
        rel_any = 1'b0; rel_i = 0;
        for (k = MAXU - 1; k >= 0; k = k - 1) if (relv[k]) begin rel_any = 1'b1; rel_i = k[UB-1:0]; end
    end
    wire [USER_W-1:0] r_user = USER_W'(r_data[HDR_USER +: 8]) | (USER_W'(r_data[HDR_USER_HI +: UHIW]) << 8);
    wire [USER_W-1:0] q_user = q_data[DW-1 -: USER_W];
    wire room = tq_n <= 3'd1 && !sq_v && !hq_v;       // an event may push <= 2 flits + a seed or a dh step
    wire sel_q = st == S_SEL && rst_q && room && q_valid;
    wire sel_w = st == S_SEL && rst_q && room && !q_valid && w_valid;
    wire sel_r = st == S_SEL && rst_q && room && !q_valid && !w_valid && r_valid;
    wire sel_l = st == S_SEL && rst_q && room && !q_valid && !w_valid && !r_valid && rel_any;
    assign q_ready = sel_q; assign w_ready = sel_w; assign r_ready = sel_r;

    function automatic [FLIT-1:0] rflit(input [USER_W-1:0] u, input [HW-1:0] h);
        begin
            rflit = {FLIT{1'b0}};
            rflit[HDR_TYPE +: 4] = MT_RESULT;
            rflit[HDR_USER +: 8] = u[7:0];
            if (USER_W > 8) rflit[HDR_USER_HI +: UHIW] = u >> 8;
            rflit[HDR_POS +: NW] = h[HW-1 -: NW];
            rflit[HDR_IDX +: NW] = h[32 +: NW];
            rflit[HDR_VAL +: 32] = h[31:0];
        end
    endfunction
    // a held RESULT is regenerated from {pos, idx, val} plus the flit's DEST / SRC: the rest must be zero
    function automatic [FLIT-1:0] rmask(input integer dummy);
        begin
            rmask = {FLIT{1'b1}};
            rmask[HDR_DEST +: 16] = 16'd0;
        end
    endfunction
    localparam [FLIT-1:0] RMASK = rmask(0);
    reg [15:0] hdr_ds;                                 // DEST / SRC of the head controller's RESULTs
    reg        hdr_ds_v;

    // ---------------------------------------------------------------- EX decisions (combinational on registers)
    reg [NW-1:0] dsel;
    integer s2;
    always @(*) begin
        dsel = 0;
        for (s2 = 0; s2 < G; s2 = s2 + 1)
`ifdef OT_MTPSEQ_MUT_OFF1
            if (x_i[2:0] == s2[2:0] && s2 > 0) dsel = r_d[(s2 - 1) * NW +: NW];
`else
            if (x_i[2:0] == s2[2:0]) dsel = r_d[s2 * NW +: NW];
`endif
    end
    wire [HW-1:0] e_h   = {ep_, et_, ef[HDR_VAL +: 32]};
    wire e_run   = ek == E_RES && r_ph == P_RUN;
    wire e_sq    = ek == E_RES && r_ph != P_RUN;                       // squashed (held)
    wire e_fwd0  = e_run && (r_fin || (x_lo && r_pf));                 // prompt result / finished user
    wire e_bad   = e_run && !e_fwd0 && (x_lo || x_i > r_g);
    wire e_ver   = e_run && !e_fwd0 && !e_bad;
    wire e_acc   = e_ver && (x_i < r_g) && dsel == et_;
    wire e_close = e_ver && !e_acc;
    wire e_rej   = x_i < r_g;                                          // the closing is a rejection
    wire [3:0] e_nep =
`ifdef OT_MTPSEQ_MUT_NOEPOCH
                       r_ep;
`else
                       e_rej ? r_ep + 1'b1 : r_ep;
`endif
    wire [2:0] e_gn  = x_fin1 ? 3'd0 : (x_rem >= G) ? G[2:0] : x_rem[2:0];
    wire e_reld  = ek == E_REL && r_dr;
    wire e_relh  = ek == E_REL && !r_dr && r_hn != 0;
    wire [FLIT-1:0] e_dflit;
    function automatic [FLIT-1:0] dflit(input [USER_W-1:0] u, input [NW-1:0] base, input [3:0] ep, input [2:0] n,
                                        input [NW*G-1:0] d);
        begin
            dflit = {FLIT{1'b0}};
            dflit[HDR_DEST +: 8] = TOK_DEST; dflit[HDR_SRC +: 8] = SRC_ID; dflit[HDR_TYPE +: 4] = MT_DRAFT;
            dflit[HDR_USER +: 8] = u[7:0];
            if (USER_W > 8) dflit[HDR_USER_HI +: UHIW] = u >> 8;
            dflit[HDR_POS +: NW] = base;
            dflit[HDR_ADDR +: 4] = ep;
            dflit[DR_N +: 3] = n;
            dflit[DR_D +: NW * G] = d;
        end
    endfunction
    assign e_dflit = dflit(eu, r_b + 1'b1, r_ep, r_g, r_d);
    wire e_push_d = ek == E_PASS || e_fwd0 || e_bad || e_acc || e_reld || e_relh
`ifdef OT_MTPSEQ_MUT_NOHOLD
                                 || e_close
`endif
                                 ;
    // ---------------------------------------------------------------- apply stage
    // WB_STAGE = 0 applies in S_EX on the combinational decisions.  WB_STAGE = 1 registers those decisions at the end
    // of S_EX and applies in S_WB.  ek, eu, ei, ef, ep_, et_, ej, r_* and x_* only change in S_SEL / S_RD / S_PRE, so
    // the data they carry is the same in both states.
    localparam [2:0] S_APPLY = (WB_STAGE != 0) ? S_WB : S_EX;
    wire e_cmp   = (ef & RMASK) != rflit(eu, e_h);
    wire e_dsne  = ef[HDR_DEST +: 16] != hdr_ds;
    wire e_sqf   = r_sqs == r_sqn || r_hn == HD[HB:0];
    wire e_rowb  = eu >= MAXU || r_ph != P_DRAFT || r_rw;
    wire e_dhb   = eu >= MAXU || r_ph != P_DRAFT || !r_rw || ej != r_j;
    wire e_dhm   = ej < r_g;
    wire e_rel0  = ek == E_REL && !r_dr && r_hn == 0;
    wire e_rell  = r_hn == 1;
    wire e_isrow = ek == E_ROW;
    wire e_isdh  = ek == E_DH;
    reg  w_push, w_bad, w_sq, w_close, w_reld, w_relh, w_cmp, w_dsne, w_sqf, w_rowb, w_dhb, w_dhm, w_rel0, w_rell, w_isrow, w_isdh;
    reg  [3:0] w_nep; reg [2:0] w_gn;
    always @(posedge clk) if (st == S_EX) begin
        w_push <= e_push_d; w_bad <= e_bad; w_sq <= e_sq; w_close <= e_close; w_reld <= e_reld; w_relh <= e_relh;
        w_cmp <= e_cmp; w_dsne <= e_dsne; w_sqf <= e_sqf; w_rowb <= e_rowb; w_dhb <= e_dhb; w_dhm <= e_dhm;
        w_rel0 <= e_rel0; w_rell <= e_rell; w_isrow <= e_isrow; w_isdh <= e_isdh; w_nep <= e_nep; w_gn <= e_gn;
    end
    wire a_ws    = WB_STAGE != 0;
    wire a_bad   = a_ws ? w_bad   : e_bad;
    wire a_sq    = a_ws ? w_sq    : e_sq;
    wire a_close = a_ws ? w_close : e_close;
    wire a_reld  = a_ws ? w_reld  : e_reld;
    wire a_relh  = a_ws ? w_relh  : e_relh;
    wire a_cmp   = a_ws ? w_cmp   : e_cmp;
    wire a_dsne  = a_ws ? w_dsne  : e_dsne;
    wire a_sqf   = a_ws ? w_sqf   : e_sqf;
    wire a_rowb  = a_ws ? w_rowb  : e_rowb;
    wire a_dhb   = a_ws ? w_dhb   : e_dhb;
    wire a_dhm   = a_ws ? w_dhm   : e_dhm;
    wire a_rel0  = a_ws ? w_rel0  : e_rel0;
    wire a_rell  = a_ws ? w_rell  : e_rell;
    wire a_isrow = a_ws ? w_isrow : e_isrow;
    wire a_isdh  = a_ws ? w_isdh  : e_isdh;
    wire [3:0] a_nep = a_ws ? w_nep : e_nep;
    wire [2:0] a_gn  = a_ws ? w_gn  : e_gn;
    wire e_push = st == S_APPLY && (a_ws ? w_push : e_push_d);
    wire [FLIT-1:0] e_flit = a_reld ? e_dflit : a_relh ? (rflit(eu, r_hh) | {{(FLIT-16){1'b0}}, hdr_ds}) : ef;
    wire e_pop = t_valid && t_ready;

    integer i;
    always @(posedge clk) begin
        acc_v <= 1'b0;
        if (!rst_q) begin
            st <= S_SEL; tq_r <= 0; tq_w <= 0; tq_n <= 0; sq_v <= 1'b0; hq_v <= 1'b0; fault <= 1'b0;
            hdr_ds_v <= 1'b0; hdr_ds <= 16'd0;
            for (i = 0; i < MAXU; i = i + 1) begin
                u_ph[i] <= P_RUN; u_pf[i] <= 1'b1; u_fin[i] <= 1'b0; u_b[i] <= plm1_q; u_g[i] <= 3'd0;
                u_ep[i] <= 4'd0; u_lc[i] <= 0; u_j[i] <= 3'd0; u_rw[i] <= 1'b0; u_sqn[i] <= 3'd0; u_sqs[i] <= 3'd0;
                u_dr[i] <= 1'b0; u_hn[i] <= 0; u_hr[i] <= 0; u_y[i] <= 0; u_d[i] <= 0;
            end
        end else begin
            if (e_pop) tq_r <= tq_r + 1'b1;
            if (e_push) begin tq[tq_w] <= e_flit; tq_w <= tq_w + 1'b1; end
            tq_n <= tq_n + (e_push ? 3'd1 : 3'd0) - (e_pop ? 3'd1 : 3'd0);
            if (s_valid && s_ready) sq_v <= 1'b0;
            if (h_valid && h_ready) hq_v <= 1'b0;
            case (st)
            default: st <= S_SEL;
            S_SEL: begin
                if (sel_q) begin
                    ek <= E_DH; eu <= q_user; ej <= q_data[NW +: 3]; et_ <= q_data[NW-1:0]; st <= S_RD;
                end else if (sel_w) begin
                    ek <= E_ROW; eu <= w_user; st <= S_RD;
                end else if (sel_r) begin
                    ek <= (r_user < MAXU) ? E_RES : E_PASS; eu <= r_user; ef <= r_data;
                    ep_ <= r_data[HDR_POS +: NW]; et_ <= r_data[HDR_IDX +: NW]; st <= S_RD;
                    if (r_data[HDR_TYPE +: 4] != MT_RESULT) fault <= 1'b1;
                end else if (sel_l) begin
                    ek <= E_REL; eu <= USER_W'(rel_i); st <= S_RD;
                end
            end
            S_RD: begin
                ei <= eu[UB-1:0];
                r_ph <= u_ph[eu[UB-1:0]]; r_pf <= u_pf[eu[UB-1:0]]; r_fin <= u_fin[eu[UB-1:0]];
                r_b <= u_b[eu[UB-1:0]]; r_g <= u_g[eu[UB-1:0]]; r_d <= u_d[eu[UB-1:0]]; r_ep <= u_ep[eu[UB-1:0]];
                r_lc <= u_lc[eu[UB-1:0]]; r_y <= u_y[eu[UB-1:0]]; r_j <= u_j[eu[UB-1:0]]; r_rw <= u_rw[eu[UB-1:0]];
                r_sqn <= u_sqn[eu[UB-1:0]]; r_sqs <= u_sqs[eu[UB-1:0]]; r_dr <= u_dr[eu[UB-1:0]];
                r_hn <= u_hn[eu[UB-1:0]]; r_hr <= u_hr[eu[UB-1:0]];
                if (WB_STAGE == 0) r_hh <= u_hq[eu[UB-1:0] * HD + u_hr[eu[UB-1:0]]];
                st <= S_PRE;
            end
            S_PRE: begin
                x_i    <= ep_ - r_b;
                x_lo   <= ep_ < r_b;
                x_b1   <= ep_ + 1'b1;
                x_rem  <= steps_q - 1'b1 - (ep_ + 1'b1);                  // steps - 1 - b'
                x_fin1 <= (ep_ + 1'b1) >= steps_q;
                x_nrow <= ep_ + 1'b1 - r_lc;
                if (WB_STAGE != 0) r_hh <= u_hq[ei * HD + r_hr];   // no write between S_RD and here
                x_hwa  <= HQA'(ei * HD + ((r_hr + r_hn[HB-1:0]) % HD));
                x_hra  <= HQA'(ei * HD + r_hr);
                st <= S_EX;
            end
            S_WB:  st <= S_WB2;                          // the write-back reaches the registered release vector
            S_WB2: st <= S_SEL;
            S_EX: st <= S_WB;
            endcase
            if (st == S_APPLY) begin
                if (a_bad) fault <= 1'b1;
                if (a_sq) begin
                    // a squashed result (the WFC discards it): held behind the closing one
                    if (a_sqf) fault <= 1'b1;
                    if (WB_STAGE != 0) u_hq[x_hwa] <= e_h; else u_hq[ei * HD + ((r_hr + r_hn[HB-1:0]) % HD)] <= e_h;
                    u_hn[ei] <= r_hn + 1'b1; u_sqs[ei] <= r_sqs + 1'b1;
                    if (a_dsne || a_cmp) fault <= 1'b1;
                end
                if (a_close) begin
                    acc_v <= 1'b1; acc_u <= eu; acc_a <= x_i[2:0]; acc_c <= ep_; acc_y <= et_;
                    if (!hdr_ds_v) begin hdr_ds <= ef[HDR_DEST +: 16]; hdr_ds_v <= 1'b1; end
                    else if (a_dsne) fault <= 1'b1;
                    if (a_cmp) fault <= 1'b1;
`ifdef OT_MTPSEQ_MUT_NOHOLD
                    u_hn[ei] <= 0;
`else
                    if (WB_STAGE != 0) u_hq[x_hra] <= e_h; else u_hq[ei * HD + r_hr] <= e_h;
                    u_hn[ei] <= 1;
`endif
                    u_pf[ei] <= 1'b0;
                    u_sqn[ei] <= r_g - x_i[2:0]; u_sqs[ei] <= 3'd0;
                    u_ep[ei] <= a_nep;
                    u_b[ei] <= x_b1; u_g[ei] <= a_gn; u_y[ei] <= et_; u_fin[ei] <= x_fin1;
                    u_j[ei] <= 3'd0; u_rw[ei] <= 1'b0; u_dr[ei] <= a_gn != 0;
                    if (a_gn != 0) begin
                        u_ph[ei] <= P_DRAFT;
                        sq_v <= 1'b1; sq_d <= {eu, ep_, x_nrow, et_, a_nep};
                        u_lc[ei] <= x_b1;
                    end else begin
                        u_ph[ei] <= P_REL;
                    end
                end
                if (a_isrow) begin
                    if (a_rowb) fault <= 1'b1;
                    else begin
                        u_rw[ei] <= 1'b1; u_j[ei] <= 3'd1;
                        hq_v <= 1'b1; hq_d <= {eu, 3'd1, r_y};
                    end
                end
                if (a_isdh) begin
                    if (a_dhb) fault <= 1'b1;
                    else begin
                        u_d[ei][(ej - 1) * NW +: NW] <= et_;
                        if (a_dhm) begin
                            u_j[ei] <= ej + 1'b1;
                            hq_v <= 1'b1;
`ifdef OT_MTPSEQ_MUT_PREV
                            hq_d <= {eu, ej + 3'd1, r_y};
`else
                            hq_d <= {eu, ej + 3'd1, et_};
`endif
                        end else begin
                            u_ph[ei] <= P_REL;
                        end
                    end
                end
                if (a_reld) u_dr[ei] <= 1'b0;
                if (a_relh) begin
                    u_hr[ei] <= (r_hr == HD - 1) ? 0 : r_hr + 1'b1; u_hn[ei] <= r_hn - 1'b1;
                    if (a_rell) u_ph[ei] <= P_RUN;
                end
                if (a_rel0) begin u_ph[ei] <= P_RUN; fault <= 1'b1; end
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_mtp_seq_fan: ot_dsrom_mtp_seq at WB_STAGE = 1 with its broadcast nets cut (DIE-HEAD-65, hd_ctl physical form):
// reset partitioned into registered copies, a new S_RD0 state (one-hot user select, record read as an AND-OR), and
// every write in S_WB enabled by a flop set at the end of S_EX.  Same event order and same flits as the base module;
// each event takes one more cycle than WB_STAGE = 1, reset releases one cycle later.  Unused by any other design.
// ---------------------------------------------------------------------------
module ot_dsrom_mtp_seq_fan #(
    parameter integer FLIT   = 512,
    parameter integer NW     = 21,      // token / position bits (WFC full shape)
    parameter integer USER_W = 10,
    parameter integer MAXU   = 8,       // users with MTP state (others pass through)
    parameter integer G      = 5,       // gamma (DSpark block 5)
    parameter integer SRC_ID = 0,       // header SRC of the DRAFT flit
    parameter integer TOK_DEST = 0,    // header DEST of the DRAFT flit (S0)
    // DIE-HEAD-71 11-05 (hd_ctl LEC, 0 cycles): opt-in, default 0 = unchanged.  1: the event flit ef, the event position
    // ep_ and the token queue tq are cleared by the control reset (rst_c) like st / tq_n.  Each is read only after the
    // event / push that loads it (ef / ep_ from S_SEL of a result event, tq[i] while tq_n counts it), so flits, faults
    // and timing are identical; bits that only ever load a structural constant hold it from reset instead of X.
    parameter integer DATA_RST = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NW-1:0]     cfg_plen,
    input  wire [NW-1:0]     cfg_glen,
    // RESULT flits from the head stage controller
    input  wire              r_valid,
    output wire              r_ready,
    input  wire [FLIT-1:0]   r_data,
    // to the token-return link (S0): RESULT + DRAFT flits
    output wire              t_valid,
    input  wire              t_ready,
    output wire [FLIT-1:0]   t_data,
    // seed to the draft primary: {user, anchor, nrows, y, epoch}
    output wire              s_valid,
    input  wire              s_ready,
    output wire [USER_W+3*NW+4-1:0] s_data,
    // the drafter's rows for a user are on the head die
    input  wire              w_valid,
    output wire              w_ready,
    input  wire [USER_W-1:0] w_user,
    // draft-head step: {user, j, prev token}
    output wire              h_valid,
    input  wire              h_ready,
    output wire [USER_W+3+NW-1:0] h_data,
    // draft-head result: {user, j, token}
    input  wire              q_valid,
    output wire              q_ready,
    input  wire [USER_W+3+NW-1:0] q_data,
    // observation
    output reg               acc_v,          // a step closed
    output reg  [USER_W-1:0] acc_u,
    output reg  [2:0]        acc_a,
    output reg  [NW-1:0]     acc_c,          // closing position (= the committed anchor)
    output reg  [NW-1:0]     acc_y,          // bonus
    output reg               fault
);
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32,
                       HDR_POS = 40, HDR_IDX = HDR_POS + NW, HDR_VAL = HDR_IDX + NW,
                       HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW, HDR_USER_HI = HDR_ADDR + 16;
    localparam integer UHIW = (USER_W > 8) ? USER_W - 8 : 1;
    localparam integer DR_N = 248, DR_D = 256;               // DRAFT flit: count, drafts
    localparam [3:0] MT_RESULT = 4'd2, MT_DRAFT = 4'd4;
    localparam integer HD = G + 1;                           // hold depth: closing + G squashed
    localparam integer HW = 2 * NW + 32;                     // held result: pos, idx, val
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer HB = $clog2(HD);
    localparam integer SW = USER_W + 3 * NW + 4, DW = USER_W + 3 + NW;
    localparam [1:0] P_RUN = 2'd0, P_DRAFT = 2'd1, P_REL = 2'd2;
    initial if (G < 1 || G > 6 || DR_D + G * NW > FLIT || HDR_USER_HI + UHIW > DR_N)
        $fatal(1, "ot_dsrom_mtp_seq: G / flit layout");

    // ---------------------------------------------------------------- reset root (registered)
    reg rst_q;
    always @(posedge clk) rst_q <= rst_n;              // rst_n is synchronous (released by the top's synchroniser)
    // Reset partition: one registered copy per user record, one per user's draft store, one for the control state.
    // Everything below sees reset one cycle after rst_q, and all at the same cycle.  keep: identical flops would
    // otherwise merge back into one net with thousands of loads (DIE-HEAD-65: 720 ps of buffers before the first gate).
    wire [MAXU-1:0] rst_u, rst_d;
    (* keep="true",dont_touch="true" *) reg rst_c;
    always @(posedge clk) rst_c <= rst_q;
    genvar gr;
    generate for (gr = 0; gr < MAXU; gr = gr + 1) begin : g_rp
        (* keep="true",dont_touch="true" *) reg rst_ur;
        (* keep="true",dont_touch="true" *) reg rst_dr;
        always @(posedge clk) begin rst_ur <= rst_q; rst_dr <= rst_q; end
        assign rst_u[gr] = rst_ur; assign rst_d[gr] = rst_dr;
    end endgenerate
    reg [NW-1:0] plen_q, steps_q, plm1_q;
    always @(posedge clk) begin                       // static configuration, settles during reset
        plen_q  <= cfg_plen;
        plm1_q  <= cfg_plen - 1'b1;
        steps_q <= cfg_plen + cfg_glen - 1'b1;
    end

    // ---------------------------------------------------------------- per-user records (flops)
    reg [1:0]    u_ph  [0:MAXU-1];
    reg          u_pf  [0:MAXU-1];                    // prefill (positions < b are prompt results)
    reg          u_fin [0:MAXU-1];
    reg [NW-1:0] u_b   [0:MAXU-1];
    reg [2:0]    u_g   [0:MAXU-1];
    reg [NW*G-1:0] u_d [0:MAXU-1];
    reg [3:0]    u_ep  [0:MAXU-1];
    reg [NW-1:0] u_lc  [0:MAXU-1];                    // positions already seeded (rows sent)
    reg [NW-1:0] u_y   [0:MAXU-1];
    reg [2:0]    u_j   [0:MAXU-1];                    // draft-head steps done
    reg          u_rw  [0:MAXU-1];                    // rows on the head die
    reg [2:0]    u_sqn [0:MAXU-1], u_sqs [0:MAXU-1];  // squashed needed / seen
    reg          u_dr  [0:MAXU-1];                    // DRAFT flit still to send in this release
    reg [HW-1:0] u_hq  [0:MAXU*HD-1];                 // hold queues
    reg [HB:0]   u_hn  [0:MAXU-1];                    // held entries
    reg [HB-1:0] u_hr  [0:MAXU-1];

    // ---------------------------------------------------------------- output queues (2-deep, registered)
    reg [FLIT-1:0] tq [0:3]; reg [1:0] tq_r, tq_w; reg [2:0] tq_n;
    assign t_valid = tq_n != 0; assign t_data = tq[tq_r];
    reg [SW-1:0] sq_d; reg sq_v;
    assign s_valid = sq_v; assign s_data = sq_d;
    reg [DW-1:0] hq_d; reg hq_v;
    assign h_valid = hq_v; assign h_data = hq_d;

    // ---------------------------------------------------------------- event pipeline
    localparam [2:0] E_RES = 3'd1, E_ROW = 3'd2, E_DH = 3'd3, E_REL = 3'd4, E_PASS = 3'd5;
    localparam [2:0] S_SEL = 3'd0, S_RD = 3'd1, S_PRE = 3'd2, S_EX = 3'd3, S_WB = 3'd4, S_WB2 = 3'd5, S_RD0 = 3'd6;
    reg [2:0]  st;
    reg [2:0]  ek;
    reg [USER_W-1:0] eu;
    reg [UB-1:0] ei;
    reg [FLIT-1:0] ef;                                // the RESULT flit of a result event
    reg [NW-1:0] ep_, et_;                            // event position / token (or dh token)
    reg [2:0]  ej;
    // the selected user's record (RD)
    reg [1:0]  r_ph; reg r_pf, r_fin, r_rw, r_dr; reg [NW-1:0] r_b, r_lc, r_y; reg [2:0] r_g, r_j, r_sqn, r_sqs;
    reg [NW*G-1:0] r_d; reg [3:0] r_ep; reg [HB:0] r_hn; reg [HB-1:0] r_hr; reg [HW-1:0] r_hh;
    // precomputed (PRE)
    reg [NW-1:0] x_i;  reg x_lo, x_ilt, x_ieq, x_igt, x_dm, x_last, x_pl; reg [NW-1:0] x_b1, x_rem; reg x_fin1;
    reg [NW-1:0] x_nrow;
    // WB_STAGE: hold-queue addresses, precomputed from the registered record
    localparam integer HQA = $clog2(MAXU * HD);
    reg [HQA-1:0] x_hwa;                              // write slot behind the held entries
    reg [MAXU*HD-1:0] x_hrs;                          // one-hot read slot of the hold queues
    reg [HW-1:0] m_hh; integer mh;
    always @(*) begin
        m_hh = 0;
        for (mh = 0; mh < MAXU * HD; mh = mh + 1) m_hh = m_hh | (u_hq[mh] & {HW{x_hrs[mh]}});
    end
    reg [MAXU-1:0] x_u;                               // one-hot selected user, from S_RD0
    // the selected record as an AND-OR of the one-hot select
    reg [1:0] m_ph; reg m_pf, m_fin, m_rw, m_dr; reg [NW-1:0] m_b, m_lc, m_y; reg [2:0] m_g, m_j, m_sqn, m_sqs;
    reg [NW*G-1:0] m_d; reg [3:0] m_ep; reg [HB:0] m_hn; reg [HB-1:0] m_hr;
    integer mk;
    always @(*) begin
        m_ph = 0; m_pf = 0; m_fin = 0; m_rw = 0; m_dr = 0; m_b = 0; m_lc = 0; m_y = 0; m_g = 0; m_j = 0; m_sqn = 0;
        m_sqs = 0; m_d = 0; m_ep = 0; m_hn = 0; m_hr = 0;
        for (mk = 0; mk < MAXU; mk = mk + 1) begin
            m_ph  = m_ph  | (u_ph[mk]  & {2{x_u[mk]}});      m_pf  = m_pf  | (u_pf[mk]  & x_u[mk]);
            m_fin = m_fin | (u_fin[mk] & x_u[mk]);           m_rw  = m_rw  | (u_rw[mk]  & x_u[mk]);
            m_dr  = m_dr  | (u_dr[mk]  & x_u[mk]);           m_b   = m_b   | (u_b[mk]   & {NW{x_u[mk]}});
            m_lc  = m_lc  | (u_lc[mk]  & {NW{x_u[mk]}});     m_y   = m_y   | (u_y[mk]   & {NW{x_u[mk]}});
            m_g   = m_g   | (u_g[mk]   & {3{x_u[mk]}});      m_j   = m_j   | (u_j[mk]   & {3{x_u[mk]}});
            m_sqn = m_sqn | (u_sqn[mk] & {3{x_u[mk]}});      m_sqs = m_sqs | (u_sqs[mk] & {3{x_u[mk]}});
            m_d   = m_d   | (u_d[mk]   & {(NW*G){x_u[mk]}}); m_ep  = m_ep  | (u_ep[mk]  & {4{x_u[mk]}});
            m_hn  = m_hn  | (u_hn[mk]  & {(HB+1){x_u[mk]}}); m_hr  = m_hr  | (u_hr[mk]  & {HB{x_u[mk]}});
        end
    end

    // release candidates: users in P_REL with every squashed result back (registered vector)
    reg [MAXU-1:0] relv;
    integer k;
    always @(posedge clk) for (k = 0; k < MAXU; k = k + 1)
        relv[k] <= rst_c && u_ph[k] == P_REL && u_sqs[k] == u_sqn[k];
    reg [UB-1:0] rel_i; reg rel_any;
    always @(*) begin
        rel_any = 1'b0; rel_i = 0;
        for (k = MAXU - 1; k >= 0; k = k - 1) if (relv[k]) begin rel_any = 1'b1; rel_i = k[UB-1:0]; end
    end
    wire [USER_W-1:0] r_user = USER_W'(r_data[HDR_USER +: 8]) | (USER_W'(r_data[HDR_USER_HI +: UHIW]) << 8);
    wire [USER_W-1:0] q_user = q_data[DW-1 -: USER_W];
    wire room = tq_n <= 3'd1 && !sq_v && !hq_v;       // an event may push <= 2 flits + a seed or a dh step
    wire sel_q = st == S_SEL && rst_c && room && q_valid;
    wire sel_w = st == S_SEL && rst_c && room && !q_valid && w_valid;
    wire sel_r = st == S_SEL && rst_c && room && !q_valid && !w_valid && r_valid;
    wire sel_l = st == S_SEL && rst_c && room && !q_valid && !w_valid && !r_valid && rel_any;
    assign q_ready = sel_q; assign w_ready = sel_w; assign r_ready = sel_r;

    function automatic [FLIT-1:0] rflit(input [USER_W-1:0] u, input [HW-1:0] h);
        begin
            rflit = {FLIT{1'b0}};
            rflit[HDR_TYPE +: 4] = MT_RESULT;
            rflit[HDR_USER +: 8] = u[7:0];
            if (USER_W > 8) rflit[HDR_USER_HI +: UHIW] = u >> 8;
            rflit[HDR_POS +: NW] = h[HW-1 -: NW];
            rflit[HDR_IDX +: NW] = h[32 +: NW];
            rflit[HDR_VAL +: 32] = h[31:0];
        end
    endfunction
    // a held RESULT is regenerated from {pos, idx, val} plus the flit's DEST / SRC: the rest must be zero
    function automatic [FLIT-1:0] rmask(input integer dummy);
        begin
            rmask = {FLIT{1'b1}};
            rmask[HDR_DEST +: 16] = 16'd0;
        end
    endfunction
    localparam [FLIT-1:0] RMASK = rmask(0);
    reg [15:0] hdr_ds;                                 // DEST / SRC of the head controller's RESULTs
    reg        hdr_ds_v;

    // ---------------------------------------------------------------- EX decisions (combinational on registers)
    reg [NW-1:0] dsel;
    integer s2;
    always @(*) begin
        dsel = 0;
        for (s2 = 0; s2 < G; s2 = s2 + 1)
`ifdef OT_MTPSEQ_MUT_OFF1
            if (x_i[2:0] == s2[2:0] && s2 > 0) dsel = r_d[(s2 - 1) * NW +: NW];
`else
            if (x_i[2:0] == s2[2:0]) dsel = r_d[s2 * NW +: NW];
`endif
    end
    wire [HW-1:0] e_h   = {ep_, et_, ef[HDR_VAL +: 32]};
    wire e_run   = ek == E_RES && r_ph == P_RUN;
    wire e_sq    = ek == E_RES && r_ph != P_RUN;                       // squashed (held)
    wire e_fwd0  = e_run && (r_fin || (x_lo && r_pf));                 // prompt result / finished user
    wire e_bad   = e_run && !e_fwd0 && (x_lo || x_i > r_g);
    wire e_ver   = e_run && !e_fwd0 && !e_bad;
    wire e_acc   = e_ver && (x_i < r_g) && dsel == et_;
    wire e_close = e_ver && !e_acc;
    wire e_rej   = x_i < r_g;                                          // the closing is a rejection
    wire [3:0] e_nep =
`ifdef OT_MTPSEQ_MUT_NOEPOCH
                       r_ep;
`else
                       e_rej ? r_ep + 1'b1 : r_ep;
`endif
    wire [2:0] e_gn  = x_fin1 ? 3'd0 : (x_rem >= G) ? G[2:0] : x_rem[2:0];
    wire e_reld  = ek == E_REL && r_dr;
    wire e_relh  = ek == E_REL && !r_dr && r_hn != 0;
    wire [FLIT-1:0] e_dflit;
    function automatic [FLIT-1:0] dflit(input [USER_W-1:0] u, input [NW-1:0] base, input [3:0] ep, input [2:0] n,
                                        input [NW*G-1:0] d);
        begin
            dflit = {FLIT{1'b0}};
            dflit[HDR_DEST +: 8] = TOK_DEST; dflit[HDR_SRC +: 8] = SRC_ID; dflit[HDR_TYPE +: 4] = MT_DRAFT;
            dflit[HDR_USER +: 8] = u[7:0];
            if (USER_W > 8) dflit[HDR_USER_HI +: UHIW] = u >> 8;
            dflit[HDR_POS +: NW] = base;
            dflit[HDR_ADDR +: 4] = ep;
            dflit[DR_N +: 3] = n;
            dflit[DR_D +: NW * G] = d;
        end
    endfunction
    assign e_dflit = dflit(eu, r_b + 1'b1, r_ep, r_g, r_d);
    wire e_push_d = ek == E_PASS || e_fwd0 || e_bad || e_acc || e_reld || e_relh
`ifdef OT_MTPSEQ_MUT_NOHOLD
                                 || e_close
`endif
                                 ;
    // ---------------------------------------------------------------- apply stage
    // WB_STAGE = 0 applies in S_EX on the combinational decisions.  WB_STAGE = 1 registers those decisions at the end
    // of S_EX and applies in S_WB.  ek, eu, ei, ef, ep_, et_, ej, r_* and x_* only change in S_SEL / S_RD / S_PRE, so
    // the data they carry is the same in both states.
    wire e_cmp   = (ef & RMASK) != rflit(eu, e_h);
    wire e_dsne  = ef[HDR_DEST +: 16] != hdr_ds;
    wire e_sqf   = r_sqs == r_sqn || r_hn == HD[HB:0];
    wire e_rowb  = eu >= MAXU || r_ph != P_DRAFT || r_rw;
    wire e_dhb   = eu >= MAXU || r_ph != P_DRAFT || !r_rw || ej != r_j;
    wire e_dhm   = ej < r_g;
    wire e_rel0  = ek == E_REL && !r_dr && r_hn == 0;
    wire e_rell  = r_hn == 1;
    wire e_isrow = ek == E_ROW;
    wire e_isdh  = ek == E_DH;
    reg  w_push, w_bad, w_sq, w_close, w_reld, w_relh, w_cmp, w_dsne, w_sqf, w_rowb, w_dhb, w_dhm, w_rel0, w_rell, w_isrow, w_isdh;
    reg  [3:0] w_nep; reg [2:0] w_gn;
    always @(posedge clk) if (st == S_EX) begin
        w_push <= e_push_d; w_bad <= e_bad; w_sq <= e_sq; w_close <= e_close; w_reld <= e_reld; w_relh <= e_relh;
        w_cmp <= e_cmp; w_dsne <= e_dsne; w_sqf <= e_sqf; w_rowb <= e_rowb; w_dhb <= e_dhb; w_dhm <= e_dhm;
        w_rel0 <= e_rel0; w_rell <= e_rell; w_isrow <= e_isrow; w_isdh <= e_isdh; w_nep <= e_nep; w_gn <= e_gn;
    end
    wire a_bad = w_bad, a_sq = w_sq, a_close = w_close, a_reld = w_reld, a_relh = w_relh, a_cmp = w_cmp, a_dsne = w_dsne;
    wire a_sqf = w_sqf, a_rowb = w_rowb, a_dhb = w_dhb, a_dhm = w_dhm, a_rel0 = w_rel0, a_rell = w_rell;
    wire a_isrow = w_isrow, a_isdh = w_isdh;
    wire [3:0] a_nep = w_nep;
    wire [2:0] a_gn  = w_gn;
    // Registered write enables, set at the end of S_EX for exactly the S_WB cycle.  w_any / w_app replace st and ei at
    // the apply, w_dw / w_hw / w_tq the address decoders of the draft store, the hold queues and the token queue.
    reg w_any; reg [MAXU-1:0] w_app; reg [MAXU*G-1:0] w_dw; reg [MAXU*HD-1:0] w_hw; reg [3:0] w_tq;
    integer wk;
    always @(posedge clk) begin
        w_any <= st == S_EX;
        w_app <= (st == S_EX) ? x_u : {MAXU{1'b0}};
        for (wk = 0; wk < MAXU * G; wk = wk + 1)
            w_dw[wk] <= st == S_EX && x_u[wk / G] && e_isdh && !e_dhb && (ej - 3'd1) == 3'(wk % G);
        for (wk = 0; wk < MAXU * HD; wk = wk + 1)
            w_hw[wk] <= st == S_EX && ((e_sq && x_hwa == HQA'(wk))
`ifndef OT_MTPSEQ_MUT_NOHOLD
                                       || (e_close && x_hrs[wk])
`endif
                                      );
        for (wk = 0; wk < 4; wk = wk + 1) w_tq[wk] <= st == S_EX && e_push_d && tq_w == 2'(wk);
    end
    wire e_push = w_any && w_push;
    wire [FLIT-1:0] e_flit = a_reld ? e_dflit : a_relh ? (rflit(eu, r_hh) | {{(FLIT-16){1'b0}}, hdr_ds}) : ef;
    wire e_pop = t_valid && t_ready;

    integer i;
    always @(posedge clk) begin
        acc_v <= 1'b0;
        if (!rst_c) begin
            st <= S_SEL; tq_r <= 0; tq_w <= 0; tq_n <= 0; sq_v <= 1'b0; hq_v <= 1'b0; fault <= 1'b0;
            hdr_ds_v <= 1'b0; hdr_ds <= 16'd0;
            if (DATA_RST != 0) begin ef <= {FLIT{1'b0}}; ep_ <= {NW{1'b0}}; end
        end else begin
            if (e_pop) tq_r <= tq_r + 1'b1;
            if (e_push) tq_w <= tq_w + 1'b1;
            tq_n <= tq_n + (e_push ? 3'd1 : 3'd0) - (e_pop ? 3'd1 : 3'd0);
            if (s_valid && s_ready) sq_v <= 1'b0;
            if (h_valid && h_ready) hq_v <= 1'b0;
            case (st)
            default: st <= S_SEL;
            S_SEL: begin
                if (sel_q) begin
                    ek <= E_DH; eu <= q_user; ej <= q_data[NW +: 3]; et_ <= q_data[NW-1:0]; st <= S_RD0;
                end else if (sel_w) begin
                    ek <= E_ROW; eu <= w_user; st <= S_RD0;
                end else if (sel_r) begin
                    ek <= (r_user < MAXU) ? E_RES : E_PASS; eu <= r_user; ef <= r_data;
                    ep_ <= r_data[HDR_POS +: NW]; et_ <= r_data[HDR_IDX +: NW]; st <= S_RD0;
                    if (r_data[HDR_TYPE +: 4] != MT_RESULT) fault <= 1'b1;
                end else if (sel_l) begin
                    ek <= E_REL; eu <= USER_W'(rel_i); st <= S_RD0;
                end
            end
            S_RD0: begin
                ei <= eu[UB-1:0];
                for (i = 0; i < MAXU; i = i + 1) x_u[i] <= eu[UB-1:0] == UB'(i);
                st <= S_RD;
            end
            S_RD: begin
                r_ph <= m_ph; r_pf <= m_pf; r_fin <= m_fin;
                r_b <= m_b; r_g <= m_g; r_d <= m_d; r_ep <= m_ep;
                r_lc <= m_lc; r_y <= m_y; r_j <= m_j; r_rw <= m_rw;
                r_sqn <= m_sqn; r_sqs <= m_sqs; r_dr <= m_dr;
                r_hn <= m_hn; r_hr <= m_hr;
                st <= S_PRE;
            end
            S_PRE: begin
                x_i    <= ep_ - r_b;
                x_lo   <= ep_ < r_b;
                x_b1   <= ep_ + 1'b1;
                x_rem  <= steps_q - 1'b1 - (ep_ + 1'b1);                  // steps - 1 - b'
                x_fin1 <= (ep_ + 1'b1) >= steps_q;
                x_nrow <= ep_ + 1'b1 - r_lc;
                x_hwa  <= HQA'(ei * HD + ((r_hr + r_hn[HB-1:0]) % HD));
                for (i = 0; i < MAXU * HD; i = i + 1) x_hrs[i] <= x_u[i / HD] && r_hr == HB'(i % HD);
                st <= S_EX;
            end
            S_EX: begin
                r_hh <= m_hh;                                            // no write between S_RD and S_WB
                st <= S_WB;
            end
            S_WB:  st <= S_WB2;                          // the write-back reaches the registered release vector
            S_WB2: st <= S_SEL;
            endcase
            if (w_any) begin
                if (a_bad) fault <= 1'b1;
                if (a_sq) begin
                    // a squashed result (the WFC discards it): held behind the closing one
                    if (a_sqf) fault <= 1'b1;
                    if (a_dsne || a_cmp) fault <= 1'b1;
                end
                if (a_close) begin
                    acc_v <= 1'b1; acc_u <= eu; acc_a <= x_i[2:0]; acc_c <= ep_; acc_y <= et_;
                    if (!hdr_ds_v) begin hdr_ds <= ef[HDR_DEST +: 16]; hdr_ds_v <= 1'b1; end
                    else if (a_dsne) fault <= 1'b1;
                    if (a_cmp) fault <= 1'b1;
                    if (a_gn != 0) begin
                        sq_v <= 1'b1; sq_d <= {eu, ep_, x_nrow, et_, a_nep};
                    end
                end
                if (a_isrow) begin
                    if (a_rowb) fault <= 1'b1;
                    else begin
                        hq_v <= 1'b1; hq_d <= {eu, 3'd1, r_y};
                    end
                end
                if (a_isdh) begin
                    if (a_dhb) fault <= 1'b1;
                    else if (a_dhm) begin
                        hq_v <= 1'b1;
`ifdef OT_MTPSEQ_MUT_PREV
                        hq_d <= {eu, ej + 3'd1, r_y};
`else
                        hq_d <= {eu, ej + 3'd1, et_};
`endif
                    end
                end
                if (a_rel0) fault <= 1'b1;
            end
        end
    end
    // the token queue and the hold queues have no reset, as in the base form
    integer q;
    always @(posedge clk) begin
        for (q = 0; q < 4; q = q + 1) if (DATA_RST != 0 && !rst_c) tq[q] <= {FLIT{1'b0}}; else if (w_tq[q]) tq[q] <= e_flit;
        for (q = 0; q < MAXU * HD; q = q + 1) if (w_hw[q]) u_hq[q] <= e_h;
    end
    // per-user records: same writes in the same order as the base form, enabled by w_app[u]
    integer u;
    always @(posedge clk) for (u = 0; u < MAXU; u = u + 1) begin
        if (!rst_u[u]) begin
            u_ph[u] <= P_RUN; u_pf[u] <= 1'b1; u_fin[u] <= 1'b0; u_b[u] <= plm1_q; u_g[u] <= 3'd0;
            u_ep[u] <= 4'd0; u_lc[u] <= 0; u_j[u] <= 3'd0; u_rw[u] <= 1'b0; u_sqn[u] <= 3'd0; u_sqs[u] <= 3'd0;
            u_dr[u] <= 1'b0; u_hn[u] <= 0; u_hr[u] <= 0; u_y[u] <= 0;
        end else if (w_app[u]) begin
            if (a_sq) begin
                u_hn[u] <= r_hn + 1'b1; u_sqs[u] <= r_sqs + 1'b1;
            end
            if (a_close) begin
`ifdef OT_MTPSEQ_MUT_NOHOLD
                u_hn[u] <= 0;
`else
                u_hn[u] <= 1;
`endif
                u_pf[u] <= 1'b0;
                u_sqn[u] <= r_g - x_i[2:0]; u_sqs[u] <= 3'd0;
                u_ep[u] <= a_nep;
                u_b[u] <= x_b1; u_g[u] <= a_gn; u_y[u] <= et_; u_fin[u] <= x_fin1;
                u_j[u] <= 3'd0; u_rw[u] <= 1'b0; u_dr[u] <= a_gn != 0;
                if (a_gn != 0) begin
                    u_ph[u] <= P_DRAFT;
                    u_lc[u] <= x_b1;
                end else begin
                    u_ph[u] <= P_REL;
                end
            end
            if (a_isrow && !a_rowb) begin
                u_rw[u] <= 1'b1; u_j[u] <= 3'd1;
            end
            if (a_isdh && !a_dhb) begin
                if (a_dhm) u_j[u] <= ej + 1'b1;
                else u_ph[u] <= P_REL;
            end
            if (a_reld) u_dr[u] <= 1'b0;
            if (a_relh) begin
                u_hr[u] <= (r_hr == HD - 1) ? 0 : r_hr + 1'b1; u_hn[u] <= r_hn - 1'b1;
                if (a_rell) u_ph[u] <= P_RUN;
            end
            if (a_rel0) u_ph[u] <= P_RUN;
        end
    end
    // draft store, one enable per slot of each user
    integer du, ds;
    always @(posedge clk) for (du = 0; du < MAXU; du = du + 1) begin
        if (!rst_d[du]) u_d[du] <= 0;
        else for (ds = 0; ds < G; ds = ds + 1) if (w_dw[du * G + ds]) u_d[du][ds * NW +: NW] <= et_;
    end
endmodule

// ---------------------------------------------------------------------------
// ot_dsrom_mtp_lrx_qr (DIE-HEAD-71 11-05, hd_ctl LEC, 0 cycles): ot_dsrom_mtp_lrx with one opt-in, Q_RST (default 0 = the
// lrx function).  1: the receive slots q are cleared while the link is held in reset (!live).  A slot is read only after
// a push wrote it (cnt != 0 selects qh), so flits, order and timing are identical; slot bits whose data is a structural
// constant of the sender hold it from reset instead of X until the first flit.  A separate module because
// rtl/dsrom_sys/mtp/closed_snap/manifest.json pins the ot_dsrom_mtp_lrx module text.  Used only by dsfd_mtp_seq_fan.
// ---------------------------------------------------------------------------
module ot_dsrom_mtp_lrx_qr #(parameter integer W = 513, parameter integer D = 4, parameter integer SEL = 0,
                             parameter integer Q_RST = 0) (
    input  wire         clk, rst_n,
    input  wire         l_valid,
    output wire         l_ready,
    input  wire [W-1:0] l_data,
    output wire         c_valid,
    input  wire         c_ready,
    output wire [W-1:0] c_data
);
    localparam integer CB = $clog2(D + 1) + 2;
    reg live;
    always @(posedge clk) live <= rst_n;
    reg pv; reg [W-1:0] pd;
    always @(posedge clk) begin pv <= l_valid; pd <= l_data; end   // pin flops
    wire pvl = pv && live;
    reg [W-1:0] q [0:D-1];
    reg [D-1:0] wp, rp;                  // one-hot write / read slot
    reg [CB-1:0] cnt;
    reg rdy, r1, r2;
    assign l_ready = rdy;
    wire ne = cnt != 0;
    reg [W-1:0] qh;
    integer i, j;   // one loop variable per always block
    always @(*) begin
        qh = {W{1'b0}};
        for (j = 0; j < D; j = j + 1) if (rp[j]) qh = qh | q[j];
    end
    assign c_valid = ne || pvl;
    assign c_data = ne ? qh : pd;
    wire pop  = c_valid && c_ready;
    wire popq = pop && ne;
    wire push = pvl && (ne || !c_ready);  // the pin flit, unless taken straight from the pin flop
    wire [CB-1:0] cnt_n = cnt + {{(CB-1){1'b0}}, push} - {{(CB-1){1'b0}}, popq};
    always @(posedge clk)                // the slot write is enabled from registers only
        for (i = 0; i < D; i = i + 1) if (Q_RST != 0 && !live) q[i] <= {W{1'b0}}; else if (pvl && wp[i]) q[i] <= pd;
    // SEL: next state for c_ready = 0 (push = pvl, no pop) and c_ready = 1 (push = pvl && ne, pop = ne), from
    // registers only; c_ready selects.  Identical function to the cnt_n form.
`ifdef OT_MTP_NEG_LINK
    wire [CB-1:0] infl = {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1};                                  // negative control
`else
    wire [CB-1:0] infl = {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1} + {{(CB-1){1'b0}}, r2};
`endif
    wire [CB-1:0] cnt_s0 = cnt + {{(CB-1){1'b0}}, pvl};
    wire [CB-1:0] cnt_s1 = cnt + {{(CB-1){1'b0}}, pvl && ne} - {{(CB-1){1'b0}}, ne};
    wire rdy_s0 = (cnt_s0 + infl) <= CB'(D - 1);
    wire rdy_s1 = (cnt_s1 + infl) <= CB'(D - 1);
    wire [D-1:0] wp_s0 = pvl ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] wp_s1 = (pvl && ne) ? {wp[D-2:0], wp[D-1]} : wp;
    wire [D-1:0] rp_s1 = ne ? {rp[D-2:0], rp[D-1]} : rp;
    always @(posedge clk)
        if (!live) begin
            cnt <= 0; rdy <= 1'b0; r1 <= 1'b0; r2 <= 1'b0;
            wp <= {{(D-1){1'b0}}, 1'b1}; rp <= {{(D-1){1'b0}}, 1'b1};
        end else if (SEL) begin
            cnt <= c_ready ? cnt_s1 : cnt_s0;
            rdy <= c_ready ? rdy_s1 : rdy_s0;
            wp  <= c_ready ? wp_s1 : wp_s0;
            rp  <= c_ready ? rp_s1 : rp;
            r1 <= rdy; r2 <= r1;
        end else begin
            cnt <= cnt_n;
`ifdef OT_MTP_NEG_LINK
            rdy <= (cnt_n + {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1}) <= CB'(D - 1);   // negative control: forgets a grant in flight
`else
            rdy <= (cnt_n + {{(CB-1){1'b0}}, rdy} + {{(CB-1){1'b0}}, r1} + {{(CB-1){1'b0}}, r2}) <= CB'(D - 1);
`endif
            r1 <= rdy; r2 <= r1;
            if (push) wp <= {wp[D-2:0], wp[D-1]};
            if (popq) rp <= {rp[D-2:0], rp[D-1]};
        end
`ifndef SYNTHESIS
    always @(posedge clk) if (live && push && cnt == CB'(D)) begin
        $display("LINK_REG FAIL: receive FIFO overflow (a flit arrived without a grant)");
        $fatal(1, "LINK_REG overflow");
    end
`endif
endmodule
