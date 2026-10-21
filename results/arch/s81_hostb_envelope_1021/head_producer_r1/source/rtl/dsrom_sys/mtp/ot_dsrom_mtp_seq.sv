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
    parameter integer TOK_DEST = 0      // header DEST of the DRAFT flit (S0)
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
    wire e_push = st == S_EX && (ek == E_PASS || e_fwd0 || e_bad || e_acc || e_reld || e_relh
`ifdef OT_MTPSEQ_MUT_NOHOLD
                                 || e_close
`endif
                                 );
    wire [FLIT-1:0] e_flit = e_reld ? e_dflit : e_relh ? (rflit(eu, r_hh) | {{(FLIT-16){1'b0}}, hdr_ds}) : ef;
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
                r_hh <= u_hq[eu[UB-1:0] * HD + u_hr[eu[UB-1:0]]];
                st <= S_PRE;
            end
            S_PRE: begin
                x_i    <= ep_ - r_b;
                x_lo   <= ep_ < r_b;
                x_b1   <= ep_ + 1'b1;
                x_rem  <= steps_q - 1'b1 - (ep_ + 1'b1);                  // steps - 1 - b'
                x_fin1 <= (ep_ + 1'b1) >= steps_q;
                x_nrow <= ep_ + 1'b1 - r_lc;
                st <= S_EX;
            end
            S_WB:  st <= S_WB2;                          // the write-back reaches the registered release vector
            S_WB2: st <= S_SEL;
            S_EX: begin
                st <= S_WB;
                if (e_bad) fault <= 1'b1;
                if (e_sq) begin
                    // a squashed result (the WFC discards it): held behind the closing one
                    if (r_sqs == r_sqn || r_hn == HD[HB:0]) fault <= 1'b1;
                    u_hq[ei * HD + ((r_hr + r_hn[HB-1:0]) % HD)] <= e_h;
                    u_hn[ei] <= r_hn + 1'b1; u_sqs[ei] <= r_sqs + 1'b1;
                    if (ef[HDR_DEST +: 16] != hdr_ds || (ef & RMASK) != rflit(eu, e_h)) fault <= 1'b1;
                end
                if (e_close) begin
                    acc_v <= 1'b1; acc_u <= eu; acc_a <= x_i[2:0]; acc_c <= ep_; acc_y <= et_;
                    if (!hdr_ds_v) begin hdr_ds <= ef[HDR_DEST +: 16]; hdr_ds_v <= 1'b1; end
                    else if (ef[HDR_DEST +: 16] != hdr_ds) fault <= 1'b1;
                    if ((ef & RMASK) != rflit(eu, e_h)) fault <= 1'b1;
`ifdef OT_MTPSEQ_MUT_NOHOLD
                    u_hn[ei] <= 0;
`else
                    u_hq[ei * HD + r_hr] <= e_h;
                    u_hn[ei] <= 1;
`endif
                    u_pf[ei] <= 1'b0;
                    u_sqn[ei] <= r_g - x_i[2:0]; u_sqs[ei] <= 3'd0;
                    u_ep[ei] <= e_nep;
                    u_b[ei] <= x_b1; u_g[ei] <= e_gn; u_y[ei] <= et_; u_fin[ei] <= x_fin1;
                    u_j[ei] <= 3'd0; u_rw[ei] <= 1'b0; u_dr[ei] <= e_gn != 0;
                    if (e_gn != 0) begin
                        u_ph[ei] <= P_DRAFT;
                        sq_v <= 1'b1; sq_d <= {eu, ep_, x_nrow, et_, e_nep};
                        u_lc[ei] <= x_b1;
                    end else begin
                        u_ph[ei] <= P_REL;
                    end
                end
                if (ek == E_ROW) begin
                    if (eu >= MAXU || r_ph != P_DRAFT || r_rw) fault <= 1'b1;
                    else begin
                        u_rw[ei] <= 1'b1; u_j[ei] <= 3'd1;
                        hq_v <= 1'b1; hq_d <= {eu, 3'd1, r_y};
                    end
                end
                if (ek == E_DH) begin
                    if (eu >= MAXU || r_ph != P_DRAFT || !r_rw || ej != r_j) fault <= 1'b1;
                    else begin
                        u_d[ei][(ej - 1) * NW +: NW] <= et_;
                        if (ej < r_g) begin
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
                if (e_reld) u_dr[ei] <= 1'b0;
                if (e_relh) begin
                    u_hr[ei] <= (r_hr == HD - 1) ? 0 : r_hr + 1'b1; u_hn[ei] <= r_hn - 1'b1;
                    if (r_hn == 1) u_ph[ei] <= P_RUN;
                end
                if (ek == E_REL && !r_dr && r_hn == 0) begin u_ph[ei] <= P_RUN; fault <= 1'b1; end
            end
            endcase
        end
    end
endmodule
