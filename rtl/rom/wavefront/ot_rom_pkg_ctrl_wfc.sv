`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_rom_pkg_ctrl_wfc: the timing-closed implementation of ot_rom_pkg_ctrl_wf
// (claude/dsrom-wf-close-20261004).  Same ports, same parameters, and -- for
// well-formed traffic with the run configuration (cfg_*) held while users are
// in flight -- the same output on every cycle (tb_wf_ctrl_equiv.sv, lockstep).
// Only the SOURCE && WAVE implementation differs (zero added cycles):
//   * the per-user issue / read eligibility is kept as two registered vectors
//     (ewk, ewf) computed from each user's next state; the lowest eligible user
//     is a one-hot (two-level prefix) and every per-user read is an AND-OR
//     with it -- no 866-way binary scan / index decode;
//   * the issued-token ring is 8 deep (WIN <= 7), the issue-order queue is
//     replaced by the expected next result position (er, k0) it implies;
//   * the RESULT's ring slot is read on the header cycle (pre-read, with a
//     same-cycle-write bypass); the in-flight test wnp > q + 1 is wnf >= 2;
//   * RESULT_PARTS must be 1 (one chained-argmax RESULT per step).
// WAVE = 0 and SOURCE = 0 are the reference's code, unchanged.
// ---------------------------------------------------------------------------
// ot_rom_pkg_ctrl_wf: ot_rom_pkg_ctrl_x plus a default-off WAVEFRONT mode
// (DS-ROM wavefront verify, claude/dsrom-wavefront-rtl-20261004).  With
// WAVE = 0 every port added here is ignored and the module behaves exactly as
// ot_rom_pkg_ctrl_x (pinned, unchanged).  With WAVE = 1:
//   * SOURCE: a user's positions whose input token is KNOWN (prompt tokens and
//     the current draft block, read from the prompt port with pr_blk / pr_qk)
//     are issued back to back, up to WIN in flight, instead of one step per
//     returned token: positions of the same user flow through the stage
//     pipeline one stage apart.  Results return in issue order.  The result of
//     position q verifies the token issued at q + 1 (q + 1 >= prompt length):
//     a mismatch REJECTS it -- the in-flight positions q + 1 .. are squashed
//     (their results discarded), the draft block advances, and q + 1 is
//     re-issued with the argmax (the corrected token).  When nothing is known
//     for q + 1 the argmax is fed back (autoregressive).  KV rows the squashed
//     positions wrote are dead: every one is rewritten, in pipeline order, by
//     the re-issued position before any later position reads it.
//   * every package: a HIDDEN position may rewind by up to WIN (re-issue after
//     a rejection) instead of latching proto_fault.
// ---------------------------------------------------------------------------
// Package controller of the ROM array (docs/ROM_ARRAY_FABRIC_RTL.md), the
// extended superset: ot_rom_pkg_ctrl plus the token in HIDDEN headers
// (FWD_TOKEN), a received-payload length of its own (RXWORDS) and SIDE
// messages (SEND_SIDE / SIDE_IN), which the DeepSeek-V4.1 array
// (rtl/test/tb_hdc_v41_array.sv) uses.  With every new parameter at its
// default it behaves as ot_rom_pkg_ctrl, whose routed and campaign records
// stay pinned to that file.
//
// One package of the layer-per-package array is a hardwired decode core
// (ot_hdc_core) with its memories and this controller.  The controller talks
// to the core only through its start/done handshake and to the core's vector
// memory through one word write port and one word read port (a word is one
// flit: 16 FP32 elements), so the core is an external port bundle here.
//
// Messages (flit 0 is the header; see HDR_* below):
//   HIDDEN  header + XWORDS payload flits: a user's hidden state for the next
//           stage.  The payload is written into vector-memory words RXB.. as
//           the flits arrive (cut-through), and the core samples `core_start`
//           on the same edge that writes the last one.  The header carries the
//           running argmax of earlier vocabulary parts (chained lm_head).
//   RESULT  header only: {user, position, token, logit} from an lm_head part.
//           Only the SOURCE package takes it: it reduces RESULT_PARTS results
//           of a (user, position) to one token and schedules that user's next
//           step (token feedback).
//   SIDE    header + payload flits: state a producing package shares with
//           later packages (DeepSeek-V4.1's compressed-KV rows, index keys and
//           index selections), usually sent to a multicast group.  The payload
//           is written at the header's word address plus the user's staging
//           stride (user << SIDE_USH), so every user has its own slot, and a
//           step starts only once SIDE_IN SIDE messages of that user have
//           arrived (a per-user count).  SIDE is taken even while a received
//           HIDDEN job waits, so it can never deadlock behind one.
//
// After the core finishes, the controller frames what the package sends:
// a HIDDEN message to HID_DEST (payload read from vector-memory words TXB..),
// a SIDE message to SIDE_DEST (SEND_SIDE; payload from words SIDE_TXB..)
// and/or a RESULT message to RES_DEST.  With FWD_TOKEN the HIDDEN header
// carries the step's token, which a receiving package's core starts with (a
// core that hashes the token history needs it).  Destinations are fabric ids (a
// package, or a multicast group the router expands).
//
// Per-user context: the expected next position of every user (a message out
// of order latches `proto_fault`) and, at the SOURCE, the in-flight step, the
// partial argmax reduction and the prefetched next prompt token.  The KV
// slice of the running user is `kv_base` (user * KVW), added to the core's KV
// addresses by the memory wrapper.
//
// Back-pressure: a HIDDEN header is taken while the core is busy, but its
// payload stays in the link buffer (`in_ready` low) until the core finishes;
// RESULT messages are always taken, so reductions never wait on computation.
// `out_ready` (the link's credits) stalls the outbound queue; a stalled send
// delays the next core start but never a RESULT reduction.  A payload word is
// written only after the outbound message still reading that word has read
// it, so receiving the next user overlaps sending the previous one, and the
// first payload word can land on the cycle the finished job is taken.
//
// Ports are timed for a registered core boundary: `core_start`, `core_token`
// and `core_pos` are combinational (the start costs no extra cycle); the
// memory and link ports are driven from state and the link-side inputs.
// ---------------------------------------------------------------------------
module ot_rom_pkg_ctrl_wfc #(
    parameter integer PKG_ID       = 0,
    parameter integer FLIT         = 512,    // bits; one vector-memory word
    parameter integer NW           = 16,     // token / position bits
    parameter integer AW           = 24,     // KV address bits
    parameter integer VWA          = 8,      // vector-memory word address bits
    parameter integer MAXU         = 16,     // user contexts
    parameter integer USER_W       = 8,      // 10 for the full-shape 866-user namespace
    parameter integer KVW          = 1024,   // KV words per user
    parameter integer XWORDS       = 8,      // payload flits of a HIDDEN message
    parameter integer RXB          = 0,      // vector-memory word of received payload flit 0
    parameter integer TXB          = 0,      // vector-memory word of sent payload flit 0
    parameter integer SOURCE       = 0,      // 1: issues steps (embedding package), reduces RESULTs
    parameter integer RESULT_PARTS = 1,      // RESULTs per step reduced at the SOURCE
    parameter integer SEND_HIDDEN  = 1,
    parameter integer HID_DEST     = 1,
    parameter integer SEND_RESULT  = 0,
    parameter integer RES_DEST     = 0,
    parameter integer COMBINE_IN   = 0,      // fold the header's running argmax into ours
    parameter integer ROW0         = 0,      // vocabulary row of our lm_head part's row 0
    parameter integer TXQ          = 4,      // outbound queue, flits
    parameter integer RXWORDS      = 0,      // payload flits of a received HIDDEN message (0: XWORDS)
    parameter integer FWD_TOKEN    = 0,      // HIDDEN headers carry the token to the next core
    parameter integer SEND_SIDE    = 0,      // after HIDDEN, send a SIDE message
    parameter integer SIDE_DEST    = 0,
    parameter integer SIDE_WORDS   = 1,      // its payload flits, read from words SIDE_TXB..
    parameter integer SIDE_TXB     = 0,
    parameter integer SIDE_RXB     = 0,      // word address the receivers write it at (in the header)
    parameter integer SIDE_IN      = 0,      // SIDE messages each step waits for
    parameter integer SIDE_USH     = 10,     // per-user staging stride, log2 words
    parameter integer WAVE         = 0,      // 1: wavefront issue of known-token positions (SOURCE), rewind (all)
    parameter integer WIN          = 6       // WAVE: positions of one user in flight
) (
    input  wire               clk,
    input  wire               rst_n,
    // run configuration (SOURCE)
    input  wire [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] cfg_users,
    input  wire [NW-1:0]      cfg_prompt_len,
    input  wire [NW-1:0]      cfg_gen_len,
    // inbound link
    input  wire               in_valid,
    output reg                in_ready,
    input  wire [FLIT-1:0]    in_data,
    input  wire               in_last,
    // outbound link
    output wire               out_valid,
    input  wire               out_ready,
    output wire [FLIT-1:0]    out_data,
    output wire               out_last,
    // decode core
    output reg                core_start,
    output reg  [NW-1:0]      core_token,
    output reg  [NW-1:0]      core_pos,
    output wire [USER_W-1:0]  core_user,
    input  wire               core_done,
    input  wire [NW-1:0]      core_next_token,
    input  wire [31:0]        core_next_val,
    output reg  [AW-1:0]      kv_base,
    // vector memory, one word per access, synchronous read
    output reg                vm_we,
    output reg  [VWA-1:0]     vm_waddr,
    output wire [FLIT-1:0]    vm_wdata,
    output reg                vm_re,
    output reg  [VWA-1:0]     vm_raddr,
    input  wire [FLIT-1:0]    vm_rq,
    // prompt tokens (SOURCE), synchronous read
    output reg                pr_re,
    output reg  [USER_W-1:0]  pr_user,
    output reg  [NW-1:0]      pr_pos,
    input  wire [NW-1:0]      pr_q,
    output reg  [3:0]         pr_blk,         // WAVE: draft block of the read
    input  wire               pr_qk,          // WAVE: the read position's token is known
    // observation
    output wire               core_busy,
    output reg                tok_valid,      // SOURCE: a step's reduced token
    output reg  [USER_W-1:0]  tok_user,
    output reg  [NW-1:0]      tok_pos,
    output reg  [NW-1:0]      tok_id,
    output reg  [((MAXU > 255) ? $clog2(MAXU+1) : 8)-1:0] users_done,
    output reg                proto_fault,
    output reg                wf_issue,       // WAVE observation: a known-token issue this cycle
    output reg                wf_reject,      // a verified token was rejected
    output reg                wf_squash       // a squashed result was discarded
);
    // -- header ----------------------------------------------------------------------
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32,
                       HDR_POS = 40, HDR_IDX = HDR_POS + NW, HDR_VAL = HDR_IDX + NW,
                       HDR_TOK = HDR_VAL + 32, HDR_ADDR = HDR_TOK + NW,
                       HDR_USER_HI = HDR_ADDR + 16;
    localparam [3:0] MT_HIDDEN = 4'd1, MT_RESULT = 4'd2, MT_SIDE = 4'd3;
    localparam integer RXW = (RXWORDS > 0) ? RXWORDS : XWORDS;
    localparam [7:0] SIDE_D = SIDE_DEST, SLEN = SIDE_WORDS;
    localparam [15:0] SIDE_A = SIDE_RXB;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam integer UCW = (MAXU > 255) ? $clog2(MAXU+1) : 8;
    localparam integer UHIW = (USER_W > 8) ? USER_W - 8 : 1;
    initial begin
        if (USER_W < 8 || USER_W > 16 || MAXU > (1 << USER_W) ||
            FLIT < HDR_USER_HI + USER_W - 8)
            $fatal(1, "ot_rom_pkg_ctrl_x: user/header widths cannot represent MAXU");
        if (SIDE_IN != 0 && (64'(MAXU-1) << SIDE_USH) + SIDE_RXB + SIDE_WORDS > (64'd1 << VWA))
            $fatal(1, "ot_rom_pkg_ctrl_x: per-user SIDE staging exceeds VM address space");
        if (64'(MAXU-1) * KVW > (64'd1 << AW) - 1)
            $fatal(1, "ot_rom_pkg_ctrl_x: per-user KV base exceeds address space");
    end
    localparam [7:0] SRC_ID = PKG_ID, HID_D = HID_DEST, RES_D = RES_DEST, XLEN = XWORDS;

    function automatic [FLIT-1:0] header(input [7:0] dest, input [3:0] typ, input [7:0] len,
                                         input [USER_W-1:0] user, input [NW-1:0] pos,
                                         input [NW-1:0] idx, input [31:0] val,
                                         input [NW-1:0] tok, input [15:0] addr);
        begin
            header = {FLIT{1'b0}};
            header[HDR_DEST +: 8] = dest;
            header[HDR_SRC +: 8]  = SRC_ID;
            header[HDR_TYPE +: 4] = typ;
            header[HDR_LEN +: 8]  = len;
            header[HDR_USER +: 8] = user[7:0];
            if (USER_W > 8) header[HDR_USER_HI +: UHIW] = user >> 8;
            header[HDR_POS +: NW] = pos;
            header[HDR_IDX +: NW] = idx;
            header[HDR_VAL +: 32] = val;
            header[HDR_TOK +: NW] = tok;
            header[HDR_ADDR +: 16] = addr;
        end
    endfunction

    // argmax order: larger logit wins, equal logits keep the lower row (numpy)
    function automatic [31:0] okey(input [31:0] v);
        okey = v[31] ? ~v : {1'b1, v[30:0]};
    endfunction
    function automatic better(input [NW-1:0] ai, input [31:0] av, input [NW-1:0] bi, input [31:0] bv);
        better = (okey(av) > okey(bv)) || ((okey(av) == okey(bv)) && (ai < bi));
    endfunction

    wire [3:0]    in_type = in_data[HDR_TYPE +: 4];
    wire [USER_W-1:0] in_user = USER_W'(in_data[HDR_USER +: 8]) |
                                  (USER_W'(in_data[HDR_USER_HI +: UHIW]) << 8);
    wire [NW-1:0] in_pos  = in_data[HDR_POS +: NW];

    // -- per-user context --------------------------------------------------------------
    reg [NW-1:0] upos [0:MAXU-1];      // next expected position (SOURCE: in-flight step)

    // -- core -------------------------------------------------------------------------
    reg          running;              // from the start edge until the job is handed to TX
    reg [USER_W-1:0] cur_user;
    assign core_user = cur_user;
    reg [NW-1:0] cur_pos, cur_pa_idx, cur_tok;
    reg [31:0]   cur_pa_val;
    assign core_busy = running;

    // -- outbound ---------------------------------------------------------------------
    // The HIDDEN (or RESULT) header is queued on the cycle the job is taken, and
    // payload word 0 is read on the same cycle; words 1.. follow one per cycle
    // while the queue has room.  A RESULT after a HIDDEN message follows its
    // last payload flit.
    localparam integer QB = (TXQ > 1) ? $clog2(TXQ) : 1;
    localparam [2:0] T_IDLE = 0, T_DATA = 1, T_RHDR = 2, T_SHDR = 3, T_SDATA = 4;
    localparam [2:0] T_AFTER_HID = SEND_SIDE ? T_SHDR : (SEND_RESULT ? T_RHDR : T_IDLE);
    reg [2:0]      tx_st;
    reg [FLIT-1:0] txq_d [0:TXQ-1];
    reg            txq_l [0:TXQ-1];
    reg [QB-1:0]   txq_w, txq_r;
    reg [QB:0]     txq_n;
    reg            rd_inflight, rd_last;
    reg [VWA-1:0]  tx_k;
    reg [USER_W-1:0] tx_user;
    reg [NW-1:0]   tx_pos, tx_idx, tx_tok;
    reg [31:0]     tx_val;
    assign out_valid = (txq_n != 0);
    assign out_data  = txq_d[txq_r];
    assign out_last  = txq_l[txq_r];
    wire tx_pop   = out_valid && out_ready;
    wire tx_space = (txq_n + rd_inflight) < TXQ;
    // the finished job is taken once the previous one's messages are queued
    wire job_done = running && core_done && tx_st == T_IDLE && !rd_inflight && (txq_n + 2 <= TXQ);
    // argmax this package reports: its own part's, or the running one if better
    wire [NW-1:0] own_idx = core_next_token + ROW0;
    wire          keep_pa = COMBINE_IN && !better(own_idx, core_next_val, cur_pa_idx, cur_pa_val);
    wire [NW-1:0] rep_idx = keep_pa ? cur_pa_idx : own_idx;
    wire [31:0]   rep_val = keep_pa ? cur_pa_val : core_next_val;
    // payload words still to be read: [tx_lo, TXB + XWORDS)
    wire           tx_reading = (tx_st == T_DATA) || (job_done && SEND_HIDDEN);
    wire [VWA-1:0] tx_lo = job_done ? TXB : TXB + tx_k;
    // the next job may not start while the SIDE payload is still to be read
    wire           tx_hold = tx_reading || tx_st == T_SHDR || tx_st == T_SDATA;

    // -- inbound ----------------------------------------------------------------------
    // A HIDDEN header is taken whenever no received job is waiting (even while
    // the core runs); its payload flits are written once the core has finished
    // (from the cycle its job is taken) and the outbound message has read the
    // word they overwrite.
    localparam [1:0] R_IDLE = 2'd0, R_DATA = 2'd1, R_SIDE = 2'd2;
    reg [1:0]    rx_st;
    reg [VWA-1:0] rx_j;
    reg [USER_W-1:0] hdr_user, side_user;
    reg [15:0]   side_addr;
    reg [3:0]    side_cnt [0:MAXU-1];   // SIDE messages received and not yet consumed, per user
    reg [NW-1:0] hdr_pos, hdr_pa_idx, hdr_tok;
    reg [31:0]   hdr_pa_val;
    reg          pend;                   // a received job waits for the outbound reads
    wire [VWA-1:0] rx_word = RXB + rx_j;
    // (closed: the job_done select after the two compares, not before one)
    wire rx_word_free = !tx_reading || (job_done ? rx_word < TXB : rx_word < TXB + tx_k) || rx_word >= TXB + XWORDS;
    // a core start needs !running, so job_done = 0 there: the start terms use these job_done-free forms
    wire tx_hold_i = tx_st == T_DATA || tx_st == T_SHDR || tx_st == T_SDATA;
    wire rx_word_free_i = !(tx_st == T_DATA) || rx_word < TXB + tx_k || rx_word >= TXB + XWORDS;
    wire rx_last_word_i = (rx_st == R_DATA) && in_valid && rx_word_free_i && (rx_j == RXW - 1);
    wire core_free = !running || job_done;
    assign vm_wdata = in_data;

    // -- SOURCE: step scheduling and argmax reduction ------------------------------------
    reg          res_v;                  // registered RESULT header
    reg [USER_W-1:0] res_u;
    reg [NW-1:0] res_p, res_i;
    reg [31:0]   res_val;
    reg [3:0]    rcnt [0:MAXU-1];
    reg [NW-1:0] rbi  [0:MAXU-1];
    reg [31:0]   rbv  [0:MAXU-1];
    reg [NW-1:0] ptok [0:MAXU-1];        // prompt token of the user's next position
    reg [UCW-1:0] next_u;
    reg          nu_ok;                  // next new user's first token fetched
    reg [NW-1:0] nu_tok;
    reg          nu_pend;                // ... being fetched
    // prompt reads: issued (registered port) at t, performed at t+1, data at t+2;
    // tag 1: new-user fetch, 2: prefetch of the next token of user pr_u*
    reg [1:0]    pr_t0, pr_t1;
    reg [USER_W-1:0] pr_u0, pr_u1;
    // ready-job queue
    reg [USER_W-1:0] jq_u [0:MAXU-1];
    reg [NW-1:0] jq_p [0:MAXU-1];
    reg [NW-1:0] jq_t [0:MAXU-1];
    reg [UB-1:0] jq_w, jq_r;
    reg [UB:0]   jq_n;

    // -- WAVE (SOURCE): per-user wavefront state (closed implementation) ----------------------
    localparam integer WQ = 8;                   // issued-token ring (> WIN - 1 live positions)
    localparam integer WF = WAVE && SOURCE;
    initial if (WF && (WIN > 7 || WIN < 1 || RESULT_PARTS != 1))
        $fatal(1, "ot_rom_pkg_ctrl_wfc: WAVE SOURCE needs 1 <= WIN <= 7 and RESULT_PARTS == 1");
    wire [NW-1:0] w_steps = cfg_prompt_len + cfg_gen_len - 1'b1;
    wire [NW-1:0] w_steps_m1 = w_steps - 1'b1;
    reg  [NW-1:0] pr_pos0, pr_pos1;
    reg  [3:0]    pr_blk0, pr_blk1;
    reg  [MAXU-1:0] pr0_oh, pr1_oh;              // user of the tag-3 read in flight (one-hot)
    reg  [MAXU-1:0] res_oh;                      // user of the registered RESULT (one-hot)
    reg  [NW-1:0] wpre;                          // RESULT's ring slot, read on the header cycle
    reg           wwr_r;                         // the ring was written on the previous cycle
    // per-user state, read out
    wire [NW-1:0] wnp_q  [0:MAXU-1];
    wire [NW-1:0] wkt_q  [0:MAXU-1];
    wire [NW-1:0] er_q   [0:MAXU-1];
    wire [3:0]    wblk_q [0:MAXU-1];
    wire [2:0]    wnf_q  [0:MAXU-1];
    wire [2:0]    k0_q   [0:MAXU-1];
    wire [MAXU-1:0] ewk, ewf, kv_v, sqnz_v, sq1_v, nf2_v, kteq_v;
    wire [NW-1:0] slot_tok [0:MAXU-1];           // ring entry at the header's slot
    // lowest eligible user: two-level prefix (groups of 32) -> one-hot
    localparam integer GS = 32, NG = (MAXU + GS - 1) / GS;
    function automatic [MAXU-1:0] lowest(input [MAXU-1:0] e);
        reg [NG-1:0] ga, gb;
        reg [GS-1:0] w, m;
        integer gg, k;
        begin
            ga = 0;
            for (gg = 0; gg < NG; gg = gg + 1) begin
                w = 0;
                for (k = 0; k < GS; k = k + 1) if (gg * GS + k < MAXU) w[k] = e[gg * GS + k];
                ga[gg] = |w;
            end
            gb[0] = 1'b0;
            for (gg = 1; gg < NG; gg = gg + 1) gb[gg] = |(ga & ((NG'(1) << gg) - 1'b1));
            lowest = 0;
            for (gg = 0; gg < NG; gg = gg + 1) begin
                w = 0;
                for (k = 0; k < GS; k = k + 1) if (gg * GS + k < MAXU) w[k] = e[gg * GS + k];
                m = w & ~(w - 1'b1);             // lowest set bit of the group
                for (k = 0; k < GS; k = k + 1) if (gg * GS + k < MAXU) lowest[gg * GS + k] = m[k] && !gb[gg];
            end
        end
    endfunction
    function automatic [USER_W-1:0] enc(input [MAXU-1:0] oh);
        integer k, b;
        reg [MAXU-1:0] t;
        begin
            enc = 0;
            for (b = 0; b < USER_W; b = b + 1) begin
                t = 0;
                for (k = 0; k < MAXU; k = k + 1) t[k] = oh[k] && ((k >> b) & 1);
                enc[b] = |t;
            end
        end
    endfunction
    wire [MAXU-1:0] ohwk = WF ? lowest(ewk) : {MAXU{1'b0}};
    wire [MAXU-1:0] ohwf = WF ? lowest(ewf) : {MAXU{1'b0}};
    wire st_wk_c = |ewk;
    wire wf_v = |ewf;
    wire [USER_W-1:0] wk_u = WF ? enc(ohwk) : {USER_W{1'b0}};
    wire [USER_W-1:0] wf_u = WF ? enc(ohwf) : {USER_W{1'b0}};
    // AND-OR reads by a one-hot
    reg [NW-1:0] tok_wk, pos_wk, pos_wf, r_er, r_prp;
    reg [3:0]    blk_wf, r_prb;
    reg [2:0]    r_k0, r_wnf;
    reg          r_kv, r_sq, r_sq1, r_nf2, r_kteq, r_prkv;
    integer bi, ui;
    reg [MAXU-1:0] tv;
    always @(*) begin
        tok_wk = 0; pos_wk = 0; pos_wf = 0; r_er = 0; r_prp = 0; blk_wf = 0; r_prb = 0; r_k0 = 0; r_wnf = 0;
        r_kv = 0; r_sq = 0; r_sq1 = 0; r_nf2 = 0; r_kteq = 0; r_prkv = 0;
        if (WF) begin
        for (bi = 0; bi < NW; bi = bi + 1) begin
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = ohwk[ui] && wkt_q[ui][bi];  tok_wk[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = ohwk[ui] && wnp_q[ui][bi];  pos_wk[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = ohwf[ui] && wnp_q[ui][bi];  pos_wf[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = res_oh[ui] && er_q[ui][bi]; r_er[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = pr1_oh[ui] && wnp_q[ui][bi]; r_prp[bi] = |tv;
        end
        for (bi = 0; bi < 4; bi = bi + 1) begin
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = ohwf[ui] && wblk_q[ui][bi];  blk_wf[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = pr1_oh[ui] && wblk_q[ui][bi]; r_prb[bi] = |tv;
        end
        for (bi = 0; bi < 3; bi = bi + 1) begin
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = res_oh[ui] && k0_q[ui][bi];  r_k0[bi] = |tv;
            for (ui = 0; ui < MAXU; ui = ui + 1) tv[ui] = res_oh[ui] && wnf_q[ui][bi]; r_wnf[bi] = |tv;
        end
        r_kv = |(res_oh & kv_v); r_sq = |(res_oh & sqnz_v); r_sq1 = |(res_oh & sq1_v);
        r_nf2 = |(res_oh & nf2_v); r_kteq = |(res_oh & kteq_v); r_prkv = |(pr1_oh & kv_v);
        end
    end

    // reduction of the registered RESULT (combinational)
    reg          fb_v, fb_cont;
    reg [NW-1:0] fb_tok, fb_idx;
    reg [31:0]   fb_val;
    reg [3:0]    red_n;
    always @(*) begin
        red_n = rcnt[res_u[UB-1:0]] + 1'b1;
        if (WF) begin
            red_n = 4'd1; fb_idx = res_i; fb_val = res_val;
        end else if (rcnt[res_u[UB-1:0]] == 0 || better(res_i, res_val, rbi[res_u[UB-1:0]], rbv[res_u[UB-1:0]])) begin
            fb_idx = res_i; fb_val = res_val;
        end else begin
            fb_idx = rbi[res_u[UB-1:0]]; fb_val = rbv[res_u[UB-1:0]];
        end
        fb_v = SOURCE && res_v && (red_n == RESULT_PARTS);
        fb_cont = (res_p + 1'b1) < (cfg_prompt_len + cfg_gen_len - 1'b1);
        fb_tok = ((res_p + 1'b1) < cfg_prompt_len) ? ptok[res_u[UB-1:0]] : fb_idx;
    end

    // -- combinational port control -------------------------------------------------------
    reg rx_hdr, rx_res, rx_last_word, rx_side, rx_side_last;
    wire side_ok = (SIDE_IN == 0) ||
                   ((hdr_user < MAXU) && (side_cnt[hdr_user[UB-1:0]] >= SIDE_IN));
    wire side_payload = (rx_st == R_SIDE) && in_valid && in_ready;
    reg st_rx, st_new, st_q, st_fb, st_wk;
    reg [USER_W-1:0] st_user;
    always @(*) begin
        in_ready = 1'b0; rx_hdr = 1'b0; rx_res = 1'b0; rx_side = 1'b0;
        vm_we = 1'b0; vm_waddr = rx_word;
        if (rx_st == R_IDLE) begin
            if (in_type == MT_HIDDEN) begin
                in_ready = !pend; rx_hdr = in_valid && !pend;
            end else if (in_type == MT_SIDE) begin
                in_ready = 1'b1; rx_side = in_valid;
            end else begin
                in_ready = 1'b1; rx_res = in_valid;          // RESULT (or a bad type)
            end
        end else if (rx_st == R_SIDE) begin
            in_ready = 1'b1;
            vm_we = in_valid && side_user < MAXU;
            vm_waddr = VWA'(side_addr) + rx_j + (VWA'(side_user) << SIDE_USH);
        end else begin
            in_ready = core_free && rx_word_free;
            vm_we = in_valid && in_ready;
        end
        rx_last_word = (rx_st == R_DATA) && vm_we && (rx_j == RXW - 1);
        rx_side_last = side_payload && in_last && side_user < MAXU;
        vm_re = (job_done && SEND_HIDDEN) || ((tx_st == T_DATA || tx_st == T_SDATA) && tx_space);
        vm_raddr = job_done ? TXB : (tx_st == T_SDATA) ? SIDE_TXB + tx_k : TXB + tx_k;

        // core start: at most one source per cycle; the core samples it on this edge
        st_rx = (rx_last_word_i || pend) && !running && !tx_hold_i && side_ok && hdr_user < MAXU;
        st_new = 1'b0; st_q = 1'b0; st_fb = 1'b0; st_wk = 1'b0;
        if (SOURCE && !running && !tx_hold_i && !pend && rx_st == R_IDLE) begin
            st_new = nu_ok && next_u < MAXU;
            st_q   = !WAVE && !nu_ok && jq_n != 0;
            st_fb  = !WAVE && !nu_ok && jq_n == 0 && fb_v && fb_cont;
            // WAVE: never on a result's reduction cycle (no same-cycle issue/verify race)
            st_wk  = WAVE && !nu_ok && st_wk_c && !res_v;
        end
        core_start = st_rx || st_new || st_q || st_fb || st_wk;
        core_token = FWD_TOKEN ? hdr_tok : {NW{1'b0}}; core_pos = hdr_pos; st_user = hdr_user;
        if (st_new) begin core_token = nu_tok; core_pos = 0; st_user = next_u; end
        if (st_q)   begin core_token = jq_t[jq_r]; core_pos = jq_p[jq_r]; st_user = jq_u[jq_r]; end
        if (st_fb)  begin core_token = fb_tok; core_pos = res_p + 1'b1; st_user = res_u; end
        if (st_wk)  begin core_token = tok_wk; core_pos = pos_wk; st_user = wk_u; end
    end

    // -- sequential ---------------------------------------------------------------------
    wire q_hdr_r = !job_done && tx_st == T_RHDR && tx_space && !rd_inflight;   // RESULT after a HIDDEN
    wire q_hdr_s = !job_done && tx_st == T_SHDR && tx_space && !rd_inflight;   // SIDE after a HIDDEN
    wire q_push  = (job_done && (SEND_HIDDEN || SEND_RESULT)) || q_hdr_r || q_hdr_s || rd_inflight;
    integer u;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; cur_user <= 0; cur_pos <= 0; cur_pa_idx <= 0; cur_pa_val <= 0; kv_base <= 0;
            cur_tok <= 0; hdr_tok <= 0; side_user <= 0; side_addr <= 0;
            pend <= 1'b0; hdr_user <= 0; hdr_pos <= 0; hdr_pa_idx <= 0; hdr_pa_val <= 0;
            tx_st <= T_IDLE; txq_w <= 0; txq_r <= 0; txq_n <= 0; rd_inflight <= 1'b0; rd_last <= 1'b0;
            tx_k <= 0; tx_user <= 0; tx_pos <= 0; tx_idx <= 0; tx_val <= 0; tx_tok <= 0;
            rx_st <= R_IDLE; rx_j <= 0;
            res_v <= 1'b0; res_u <= 0; res_p <= 0; res_i <= 0; res_val <= 0;
            next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; nu_tok <= 0;
            pr_t0 <= 0; pr_t1 <= 0; pr_u0 <= 0; pr_u1 <= 0;
            pr_re <= 1'b0; pr_user <= 0; pr_pos <= 0;
            jq_w <= 0; jq_r <= 0; jq_n <= 0;
            tok_valid <= 1'b0; tok_user <= 0; tok_pos <= 0; tok_id <= 0; users_done <= 0;
            proto_fault <= 1'b0;
            for (u = 0; u < MAXU; u = u + 1) begin
                upos[u] <= 0; rcnt[u] <= 0; rbi[u] <= 0; rbv[u] <= 0; ptok[u] <= 0; side_cnt[u] <= 0;
            end
            pr_blk <= 0; pr_pos0 <= 0; pr_pos1 <= 0; pr_blk0 <= 0; pr_blk1 <= 0;
            wf_issue <= 1'b0; wf_reject <= 1'b0; wf_squash <= 1'b0;
            pr0_oh <= 0; pr1_oh <= 0; res_oh <= 0; wpre <= 0; wwr_r <= 1'b0;
        end else begin
            tok_valid <= 1'b0;
            pr_re <= 1'b0;

            // ---- core finished: hand the job to the outbound side
            if (job_done) begin
                running <= 1'b0;
                tx_user <= cur_user; tx_pos <= cur_pos; tx_idx <= rep_idx; tx_val <= rep_val; tx_tok <= cur_tok;
                if (SEND_HIDDEN) begin
                    tx_k <= 1;
                    tx_st <= (XWORDS > 1) ? T_DATA : T_AFTER_HID;
                end else begin
                    tx_st <= T_IDLE;
                end
            end

            // ---- core start
            if (core_start) begin
                running <= 1'b1;
                cur_user <= st_user; cur_pos <= core_pos;
                cur_pa_idx <= hdr_pa_idx; cur_pa_val <= hdr_pa_val;
                kv_base <= st_user * KVW;
                cur_tok <= core_token;
            end
            if (st_rx) pend <= 1'b0;
            else if (rx_last_word) pend <= 1'b1;

            // ---- inbound
            if (rx_hdr) begin
                hdr_user <= in_user; hdr_pos <= in_pos;
                hdr_pa_idx <= in_data[HDR_IDX +: NW]; hdr_pa_val <= in_data[HDR_VAL +: 32];
                hdr_tok <= in_data[HDR_TOK +: NW];
                if (in_last || in_user >= MAXU) proto_fault <= 1'b1;
                else begin
                    if (WAVE ? (in_pos > upos[in_user[UB-1:0]] || in_pos + WIN < upos[in_user[UB-1:0]])
                             : (upos[in_user[UB-1:0]] != in_pos)) proto_fault <= 1'b1;
                    upos[in_user[UB-1:0]] <= in_pos + 1'b1;
                end
                rx_j <= 0; rx_st <= R_DATA;
            end
            if (rx_st == R_DATA && vm_we) begin
                if (in_last != (rx_j == RXW - 1)) proto_fault <= 1'b1;
                rx_j <= rx_j + 1'b1;
                if (rx_last_word) rx_st <= R_IDLE;
            end
            // ---- SIDE: header, then the payload into the user's staging slot
            if (rx_side) begin
                if (SIDE_IN == 0 || in_last || in_user >= MAXU) proto_fault <= 1'b1;
                side_user <= in_user; side_addr <= in_data[HDR_ADDR +: 16];
                rx_j <= 0; rx_st <= R_SIDE;
            end
            if (side_payload) begin
                rx_j <= rx_j + 1'b1;
                if (in_last) rx_st <= R_IDLE;
            end
            if (rx_side_last && st_rx && side_user == hdr_user) begin
                side_cnt[side_user] <= side_cnt[side_user] + 4'd1 - SIDE_IN[3:0];
            end else begin
                if (rx_side_last) side_cnt[side_user] <= side_cnt[side_user] + 4'd1;
                if (st_rx) side_cnt[hdr_user] <= side_cnt[hdr_user] - SIDE_IN[3:0];
            end
            res_v <= 1'b0;
            if (rx_res) begin
                if (!SOURCE || in_type != MT_RESULT || !in_last || in_user >= MAXU) proto_fault <= 1'b1;
                res_v <= SOURCE && in_type == MT_RESULT && in_user < MAXU;
                res_u <= in_user; res_p <= in_pos;
                res_i <= in_data[HDR_IDX +: NW]; res_val <= in_data[HDR_VAL +: 32];
            end

            // ---- SOURCE: reduction, token feedback, step scheduling
            if (SOURCE && !WAVE) begin
                if (res_v) begin
                    if (res_p != upos[res_u[UB-1:0]]) proto_fault <= 1'b1;
                    if (red_n == RESULT_PARTS) begin
                        rcnt[res_u[UB-1:0]] <= 0;
                        tok_valid <= 1'b1; tok_user <= res_u; tok_pos <= res_p; tok_id <= fb_idx;
                        if (!fb_cont) users_done <= users_done + 1'b1;
                    end else begin
                        rcnt[res_u[UB-1:0]] <= red_n;
                    end
                    rbi[res_u[UB-1:0]] <= fb_idx; rbv[res_u[UB-1:0]] <= fb_val;
                end
                if (fb_v && fb_cont && !st_fb) begin
                    jq_u[jq_w] <= res_u; jq_p[jq_w] <= res_p + 1'b1; jq_t[jq_w] <= fb_tok;
                    jq_w <= (jq_w == MAXU - 1) ? {UB{1'b0}} : jq_w + 1'b1;
                end
                if (st_q) jq_r <= (jq_r == MAXU - 1) ? {UB{1'b0}} : jq_r + 1'b1;
                jq_n <= jq_n + ((fb_v && fb_cont && !st_fb) ? 1'b1 : 1'b0) - (st_q ? 1'b1 : 1'b0);
                if (st_new || st_q || st_fb) begin
                    upos[st_user[UB-1:0]] <= core_pos;
                    // prefetch the prompt token of the step after this one
                    pr_re <= 1'b1; pr_user <= st_user; pr_pos <= core_pos + 1'b1; pr_t0 <= 2; pr_u0 <= st_user;
                    if (st_new) begin next_u <= next_u + 1'b1; nu_ok <= 1'b0; end
                end else if (!nu_ok && !nu_pend && next_u < cfg_users && next_u < MAXU) begin
                    // fetch the next new user's first prompt token
                    pr_re <= 1'b1; pr_user <= next_u; pr_pos <= 0; pr_t0 <= 1; nu_pend <= 1'b1;
                end else begin
                    pr_t0 <= 0;
                end
                // a read issued two cycles ago returns now
                pr_t1 <= pr_t0; pr_u1 <= pr_u0;
                if (pr_t1 == 1) begin nu_tok <= pr_q; nu_ok <= 1'b1; nu_pend <= 1'b0; end
                if (pr_t1 == 2) ptok[pr_u1[UB-1:0]] <= pr_q;
            end
            // ---- SOURCE, WAVE: wavefront issue, in-order results, verify / reject / squash
            //      (global part; the per-user state updates itself in g_wu below)
            if (SOURCE && WAVE) begin
                wf_issue <= st_wk; wf_reject <= 1'b0; wf_squash <= 1'b0;
                wwr_r <= st_wk || st_new;
                if (rx_res) begin
                    res_oh <= 0;
                    if (in_user < MAXU) res_oh[in_user[UB-1:0]] <= 1'b1;
                    wpre <= w_pre_c;
                end
                if (st_new) begin next_u <= next_u + 1'b1; nu_ok <= 1'b0; end
                // token reads: a new user's first token (tag 1), else the next known token (tag 3)
                if (!st_new && !nu_ok && !nu_pend && next_u < cfg_users && next_u < MAXU) begin
                    pr_re <= 1'b1; pr_user <= next_u; pr_pos <= 0; pr_blk <= 0; pr_t0 <= 1; nu_pend <= 1'b1;
                end else if (wf_v) begin
                    pr_re <= 1'b1; pr_user <= wf_u; pr_pos <= pos_wf; pr_blk <= blk_wf;
                    pr_t0 <= 3; pr_u0 <= wf_u; pr0_oh <= ohwf; pr_pos0 <= pos_wf; pr_blk0 <= blk_wf;
                end else begin
                    pr_t0 <= 0;
                end
                pr_t1 <= pr_t0; pr_u1 <= pr_u0; pr1_oh <= pr0_oh; pr_pos1 <= pr_pos0; pr_blk1 <= pr_blk0;
                if (pr_t1 == 1) begin nu_tok <= pr_q; nu_ok <= 1'b1; nu_pend <= 1'b0; end
                if (res_v) begin
                    if (res_p != r_er) proto_fault <= 1'b1;
                    if (r_sq) wf_squash <= 1'b1;
                    else begin
                        tok_valid <= 1'b1; tok_user <= res_u; tok_pos <= res_p; tok_id <= fb_idx;
                        if (!fb_cont) users_done <= users_done + 1'b1;
                        if (w_rewind || w_rejb) wf_reject <= 1'b1;
                    end
                end
            end
            if (SOURCE && cfg_users > MAXU) proto_fault <= 1'b1;

            // ---- outbound framing
            if (vm_re && !job_done) begin
                tx_k <= tx_k + 1'b1;
                if (tx_st == T_DATA && tx_k == XWORDS - 1) tx_st <= T_AFTER_HID;
                if (tx_st == T_SDATA && tx_k == SIDE_WORDS - 1) tx_st <= SEND_RESULT ? T_RHDR : T_IDLE;
            end
            if (q_hdr_r) tx_st <= T_IDLE;
            if (q_hdr_s) begin tx_st <= T_SDATA; tx_k <= 0; end
            rd_inflight <= vm_re;
            rd_last <= vm_re && (job_done ? (XWORDS == 1) :
                                 (tx_st == T_SDATA) ? (tx_k == SIDE_WORDS - 1) : (tx_k == XWORDS - 1));
            if (job_done) begin
                if (SEND_HIDDEN) begin
                    txq_d[txq_w] <= header(HID_D, MT_HIDDEN, XLEN, cur_user, cur_pos, rep_idx, rep_val,
                                           FWD_TOKEN ? cur_tok : {NW{1'b0}}, 16'd0);
                    txq_l[txq_w] <= 1'b0;
                end else begin
                    txq_d[txq_w] <= header(RES_D, MT_RESULT, 8'd0, cur_user, cur_pos, rep_idx, rep_val,
                                           {NW{1'b0}}, 16'd0);
                    txq_l[txq_w] <= 1'b1;
                end
            end else if (q_hdr_r) begin
                txq_d[txq_w] <= header(RES_D, MT_RESULT, 8'd0, tx_user, tx_pos, tx_idx, tx_val,
                                       {NW{1'b0}}, 16'd0);
                txq_l[txq_w] <= 1'b1;
            end else if (q_hdr_s) begin
                txq_d[txq_w] <= header(SIDE_D, MT_SIDE, SLEN, tx_user, tx_pos, {NW{1'b0}}, 32'd0,
                                       {NW{1'b0}}, SIDE_A);
                txq_l[txq_w] <= 1'b0;
            end else if (rd_inflight) begin
                txq_d[txq_w] <= vm_rq;
                txq_l[txq_w] <= rd_last;
            end
            if (q_push) txq_w <= (txq_w == TXQ - 1) ? {QB{1'b0}} : txq_w + 1'b1;
            if (tx_pop) txq_r <= (txq_r == TXQ - 1) ? {QB{1'b0}} : txq_r + 1'b1;
            txq_n <= txq_n + (q_push ? 1'b1 : 1'b0) - (tx_pop ? 1'b1 : 1'b0);
        end
    end

    // -- SOURCE && WAVE: global decisions of the registered RESULT ---------------------------
    wire [2:0] res_slot = res_p[2:0] + 3'd1;
    wire       w_byp = wwr_r && cur_user == res_u && cur_pos[2:0] == res_slot;
    wire [NW-1:0] w_tok = w_byp ? cur_tok : wpre;          // token issued at q + 1
    wire       w_gepl = (res_p + 1'b1) >= cfg_prompt_len;
    wire       w_live = res_v && !r_sq;
    wire       w_rewind = w_live && fb_cont && r_nf2 && w_gepl && (w_tok != fb_idx);
    wire       w_blkb = w_live && fb_cont && !r_nf2 && w_gepl;
    wire       w_rejb = w_blkb && r_kv && !r_kteq;
    wire [NW-1:0] w_er_new = res_p + 1'b1 - ((res_v && r_sq && r_sq1) ? NW'(r_k0) : {NW{1'b0}});
    wire [NW-1:0] w_q1 = res_p + 1'b1;
    wire       w_g1 = w_steps > 1;                         // (wnp = 1) < steps
    wire       w_prok = r_prp == pr_pos1 && r_prb == pr_blk1 && !r_prkv;
    wire       rd_wf = !(!st_new && !nu_ok && !nu_pend && next_u < cfg_users && next_u < MAXU) && wf_v;
    // header-cycle pre-read of the RESULT's ring slot (in_user, in_pos + 1)
    wire [UB-1:0] in_ub = in_user[UB-1:0];
    wire [2:0]    in_slot = in_pos[2:0] + 3'd1;
    reg  [NW-1:0] w_pre_c;
    reg  [MAXU-1:0] in_dec;
    integer pb, pu;
    reg [MAXU-1:0] pv;
    always @(*) begin
        in_dec = 0;
        w_pre_c = 0;
        if (WF) begin
            in_dec[in_ub] = 1'b1;
            for (pb = 0; pb < NW; pb = pb + 1) begin
                for (pu = 0; pu < MAXU; pu = pu + 1) pv[pu] = in_dec[pu] && slot_tok[pu][pb];
                w_pre_c[pb] = |pv;
            end
        end
    end

    genvar gu;
    generate if (WF) begin : g_wf
        for (gu = 0; gu < MAXU; gu = gu + 1) begin : g_wu
            reg [NW-1:0] wnp, wkt, er;
            reg [NW-1:0] ring [0:WQ-1];
            reg [3:0]    wblk;
            reg [2:0]    wnf, wsq, k0;
            reg          wkv, wkp, wkm, stv, lt, e_wk, e_wf;
            assign wnp_q[gu] = wnp; assign wkt_q[gu] = wkt; assign er_q[gu] = er; assign wblk_q[gu] = wblk;
            assign wnf_q[gu] = wnf; assign k0_q[gu] = k0;
            assign ewk[gu] = e_wk; assign ewf[gu] = e_wf; assign kv_v[gu] = wkv;
            assign sqnz_v[gu] = wsq != 0; assign sq1_v[gu] = wsq == 3'd1; assign nf2_v[gu] = wnf >= 3'd2;
            assign kteq_v[gu] = wkt == fb_idx;
            assign slot_tok[gu] = ring[in_slot];
            wire isn = st_new && next_u == gu;
            wire isw = st_wk && ohwk[gu];
            wire isr = rd_wf && ohwf[gu];
            wire isp = (pr_t1 == 3) && pr1_oh[gu];
            wire isr_res = res_v && res_oh[gu];
            reg [NW-1:0] n_wnp, n_wkt, n_er;
            reg [3:0]    n_wblk;
            reg [2:0]    n_wnf, n_wsq, n_k0;
            reg          n_wkv, n_wkp, n_wkm, n_stv, n_lt;
            always @(*) begin
                n_wnp = wnp; n_wkt = wkt; n_er = er; n_wblk = wblk; n_wsq = wsq; n_k0 = k0;
                n_wkv = wkv; n_wkp = wkp; n_wkm = wkm; n_stv = stv || isn; n_lt = lt;
                n_wnf = wnf + ((isw || isn) ? 3'd1 : 3'd0) - (isr_res ? 3'd1 : 3'd0);
                if (isn) begin
                    n_wnp = 1; n_wblk = 0; n_wkv = 1'b0; n_wkp = 1'b0; n_wkm = 1'b0; n_wsq = 0; n_er = 0; n_lt = w_g1;
                end
                if (isw) begin
                    n_wnp = wnp + 1'b1; n_wkv = 1'b0; n_wkm = 1'b0; n_lt = wnp != w_steps_m1;
                end
                if (isr) n_wkp = 1'b1;
                if (isp) begin
                    n_wkp = 1'b0;
                    if (w_prok) begin
                        if (pr_qk) begin n_wkv = 1'b1; n_wkt = pr_q; end
                        else n_wkm = 1'b1;
                    end
                end
                if (isr_res) begin
                    n_er = w_er_new;
                    if (wsq != 0) n_wsq = wsq - 1'b1;
                    else if (w_rewind) begin
                        n_wsq = wnf - 1'b1; n_k0 = wnf - 1'b1;
                        n_wnp = w_q1; n_wblk = wblk + 1'b1; n_lt = 1'b1;
                        n_wkv = 1'b1; n_wkt = fb_idx; n_wkm = 1'b0;
                    end else if (w_blkb) begin
                        if (w_rejb) n_wblk = wblk + 1'b1;
                        n_wkv = 1'b1; n_wkt = fb_idx; n_wkm = 1'b0;
                    end
                end
            end
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin
                    wnp <= 0; wkt <= 0; er <= 0; wblk <= 0; wnf <= 0; wsq <= 0; k0 <= 0;
                    wkv <= 1'b0; wkp <= 1'b0; wkm <= 1'b0; stv <= 1'b0; lt <= 1'b0; e_wk <= 1'b0; e_wf <= 1'b0;
                end else begin
                    wnp <= n_wnp; wkt <= n_wkt; er <= n_er; wblk <= n_wblk; wnf <= n_wnf; wsq <= n_wsq; k0 <= n_k0;
                    wkv <= n_wkv; wkp <= n_wkp; wkm <= n_wkm; stv <= n_stv; lt <= n_lt;
                    e_wk <= n_stv && n_wkv && (n_wnf < WIN) && n_lt;
                    e_wf <= n_stv && !n_wkv && !n_wkp && !n_wkm && n_lt;
                end
            end
            // ring: written on issue (slot wnp mod WQ) and on the user's first issue (slot 0)
            always @(posedge clk) begin
                if (isn) ring[0] <= nu_tok;
                if (isw) ring[wnp[2:0]] <= wkt;
            end
        end
    end else begin : g_nowf
        for (gu = 0; gu < MAXU; gu = gu + 1) begin : g_wu
            assign wnp_q[gu] = 0; assign wkt_q[gu] = 0; assign er_q[gu] = 0; assign wblk_q[gu] = 0;
            assign wnf_q[gu] = 0; assign k0_q[gu] = 0; assign ewk[gu] = 1'b0; assign ewf[gu] = 1'b0;
            assign kv_v[gu] = 1'b0; assign sqnz_v[gu] = 1'b0; assign sq1_v[gu] = 1'b0; assign nf2_v[gu] = 1'b0;
            assign kteq_v[gu] = 1'b0; assign slot_tok[gu] = 0;
        end
    end endgenerate
endmodule
