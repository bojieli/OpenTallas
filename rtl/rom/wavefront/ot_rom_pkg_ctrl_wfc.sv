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
// Common to SOURCE 0 / 1: registered mirrors of the RX / SIDE / TX word
// addresses (no adder before the word-free compares or on vm_*addr), and a
// HIDDEN header's position check + upos update four cycles after the header
// (32-user groups, registered): a position fault latches proto_fault FOUR cycles
// later than the reference (RXWORDS >= 2); and a registered reset root (release one cycle
// after rst_n_in).  With the reference's reset released one cycle later,
// every other output is cycle-identical.
// WAVE = 0 is not implemented here (use ot_rom_pkg_ctrl_wf).
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
`ifndef OT_WFC_LOCAL_CONTROL
`define OT_WFC_LOCAL_CONTROL 0
`endif
`ifndef OT_WFC_DECODED_READ
`define OT_WFC_DECODED_READ 0
`endif
module ot_rom_pkg_ctrl_wfc #(
    parameter integer DECODED_READ = `OT_WFC_DECODED_READ,
    parameter integer LOCAL_CONTROL = `OT_WFC_LOCAL_CONTROL, // opt-in same-edge control locality
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
    // (closed) the per-user expected position lives in groups of 32 users (ot_rom_pkg_ctrl_wfc_upos)
    // (closed) internal reset: asserted asynchronously, released one cycle after rst_n on the clock
    // (a registered root for the reset tree; every flop below sees release one cycle later)
    (* keep *) reg rst_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    // A HIDDEN header's position check, pipelined (header at t; hdr_user / hdr_pos hold until the next
    // header, >= t + RXW + 1): t+1 each group latches the user's low bits, t+2 reads its entry
    // (registered), t+3 the group is selected (registered; hdr_pos, hdr_pos + 1 and the group copied),
    // t+4 compare -> proto_fault and write.  The next header's read (>= t + RXW + 3) sees the write
    // when RXW >= 2.
    reg          uchk, uchk2, uchk3, uchk4;
    reg [NW-1:0] upos_hr, hdr_pos1, pos_c;

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
    (* keep *) reg [TXQ-1:0] txq_bank; // same-edge one-hot mirror of txq_w
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
    // (closed) registered mirrors of the word addresses: rxw = RXB + rx_j, sww = the SIDE staging word,
    // txh = TXB + tx_k, txs = SIDE_TXB + tx_k -- updated with rx_j / tx_k, so no adder before a compare
    reg [VWA-1:0] rxw, sww, txs;
    reg [VWA:0]   txh;
    wire [VWA-1:0] rx_word = rxw;
    // (closed: the job_done select after the two compares, not before one)
    wire rx_word_free = !tx_reading || (job_done ? rx_word < TXB : rx_word < txh) || rx_word >= TXB + XWORDS;
    // a core start needs !running, so job_done = 0 there: the start terms use these job_done-free forms
    wire tx_hold_i = tx_st == T_DATA || tx_st == T_SHDR || tx_st == T_SDATA;
    wire rx_word_free_i = !(tx_st == T_DATA) || rx_word < txh || rx_word >= TXB + XWORDS;
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

    // -- WAVE (SOURCE): the wavefront engine (ot_rom_pkg_ctrl_wfc_src, closed implementation) -------
    localparam integer WF = WAVE && SOURCE;
    initial if (!WAVE) $fatal(1, "ot_rom_pkg_ctrl_wfc: WAVE = 0 is ot_rom_pkg_ctrl_wf (unchanged)");
    initial if (WF && (WIN > 7 || WIN < 1 || RESULT_PARTS != 1))
        $fatal(1, "ot_rom_pkg_ctrl_wfc: WAVE SOURCE needs 1 <= WIN <= 7 and RESULT_PARTS == 1");
    wire              e_go, e_rfull, e_pr_re, e_tok_v, e_done, e_fault, e_wfi, e_rej, e_sq;
    wire [NW-1:0]     e_tok, e_pos, e_pr_pos, e_tok_p, e_tok_i;
    wire [USER_W-1:0] e_user, e_pr_user, e_tok_u;
    wire [3:0]        e_pr_blk;
    wire              src_free = !running && !tx_hold_i && !pend && rx_st == R_IDLE;

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

    // upos groups
    localparam integer UGS = 32, UNG = (MAXU + UGS - 1) / UGS;
    initial if (RXW < 2) $fatal(1, "ot_rom_pkg_ctrl_wfc: the pipelined position check needs RXWORDS >= 2");
    wire [NW-1:0] ug_part [0:UNG-1];
    reg  [UNG-1:0] gsel_oh, gw_oh;      // the header user's group (t+2), and for the write (t+3)
    genvar ugi;
    generate for (ugi = 0; ugi < UNG; ugi = ugi + 1) begin : g_upos
        (* keep_hierarchy *)
        ot_rom_pkg_ctrl_wfc_upos #(.LOCAL_CONTROL(LOCAL_CONTROL), .NW(NW), .N((MAXU - ugi * UGS) < UGS ? (MAXU - ugi * UGS) : UGS)) ug (
            .clk(clk), .rst_n(rst_q), .lo(hdr_user[4:0]), .rd(uchk2), .rd_early(uchk),
            .wr(uchk4 && gw_oh[ugi]), .wdata(hdr_pos1), .part(ug_part[ugi]));
    end endgenerate
    reg [NW-1:0] upos_sel;
    integer usg;
    always @(*) begin
        upos_sel = 0;
        for (usg = 0; usg < UNG; usg = usg + 1) if (gsel_oh[usg]) upos_sel = upos_sel | ug_part[usg];
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
        // The reset root releases one edge after rst_n. Do not advertise an
        // accepted flit until this controller can retain it on that edge.
        // Otherwise the sender consumes the header while we are still reset,
        // and the next payload is decoded as a new header.
        if (!rst_q) begin
            in_ready = 1'b0;
        end else if (rx_st == R_IDLE) begin
            if (in_type == MT_HIDDEN) begin
                in_ready = !pend; rx_hdr = in_valid && !pend;
            end else if (in_type == MT_SIDE) begin
                in_ready = 1'b1; rx_side = in_valid;
            end else begin
                in_ready = !(WF && e_rfull); rx_res = in_valid && in_ready;   // RESULT (or a bad type)
            end
        end else if (rx_st == R_SIDE) begin
            in_ready = 1'b1;
            vm_we = in_valid && side_user < MAXU;
            vm_waddr = sww;
        end else begin
            in_ready = core_free && rx_word_free;
            vm_we = in_valid && in_ready;
        end
        rx_last_word = (rx_st == R_DATA) && vm_we && (rx_j == RXW - 1);
        rx_side_last = side_payload && in_last && side_user < MAXU;
        vm_re = (job_done && SEND_HIDDEN) || ((tx_st == T_DATA || tx_st == T_SDATA) && tx_space);
        vm_raddr = job_done ? TXB : (tx_st == T_SDATA) ? txs : txh[VWA-1:0];

        // core start: at most one source per cycle; the core samples it on this edge
        st_rx = (rx_last_word_i || pend) && !running && !tx_hold_i && side_ok && hdr_user < MAXU;
        st_new = 1'b0; st_q = 1'b0; st_fb = 1'b0; st_wk = 1'b0;
        if (SOURCE && !running && !tx_hold_i && !pend && rx_st == R_IDLE) begin
            st_new = !WF && nu_ok && next_u < MAXU;
            st_q   = !WAVE && !nu_ok && jq_n != 0;
            st_fb  = !WAVE && !nu_ok && jq_n == 0 && fb_v && fb_cont;
            // WAVE: never on a result's reduction cycle (no same-cycle issue/verify race)
            st_wk  = WF && e_go;      // the engine's start (a new user or a known-token position)
        end
        core_start = st_rx || st_new || st_q || st_fb || st_wk;
        core_token = FWD_TOKEN ? hdr_tok : {NW{1'b0}}; core_pos = hdr_pos; st_user = hdr_user;
        if (st_new) begin core_token = nu_tok; core_pos = 0; st_user = next_u; end
        if (st_q)   begin core_token = jq_t[jq_r]; core_pos = jq_p[jq_r]; st_user = jq_u[jq_r]; end
        if (st_fb)  begin core_token = fb_tok; core_pos = res_p + 1'b1; st_user = res_u; end
        if (st_wk)  begin core_token = e_tok; core_pos = e_pos; st_user = e_user; end
        // the registered reset root releases one cycle after rst_n: take nothing from the link and start
        // nothing until then (the reference releases with rst_n; a flit offered in that cycle must wait)
        if (!rst_q) begin
            in_ready = 1'b0; rx_hdr = 1'b0; rx_res = 1'b0; rx_side = 1'b0; vm_we = 1'b0;
            st_rx = 1'b0; st_new = 1'b0; st_q = 1'b0; st_fb = 1'b0; st_wk = 1'b0; core_start = 1'b0;
        end
    end

    // -- sequential ---------------------------------------------------------------------
    wire q_hdr_r = !job_done && tx_st == T_RHDR && tx_space && !rd_inflight;   // RESULT after a HIDDEN
    wire q_hdr_s = !job_done && tx_st == T_SHDR && tx_space && !rd_inflight;   // SIDE after a HIDDEN
    wire q_push  = (job_done && (SEND_HIDDEN || SEND_RESULT)) || q_hdr_r || q_hdr_s || rd_inflight;
    integer u, qbank;
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            running <= 1'b0; cur_user <= 0; cur_pos <= 0; cur_pa_idx <= 0; cur_pa_val <= 0; kv_base <= 0;
            cur_tok <= 0; hdr_tok <= 0; side_user <= 0; side_addr <= 0;
            pend <= 1'b0; hdr_user <= 0; hdr_pos <= 0; hdr_pa_idx <= 0; hdr_pa_val <= 0;
            txq_bank <= {{(TXQ-1){1'b0}}, 1'b1};
            tx_st <= T_IDLE; txq_w <= 0; txq_r <= 0; txq_n <= 0; rd_inflight <= 1'b0; rd_last <= 1'b0;
            tx_k <= 0; tx_user <= 0; tx_pos <= 0; tx_idx <= 0; tx_val <= 0; tx_tok <= 0;
            rx_st <= R_IDLE; rx_j <= 0;
            rxw <= RXB; sww <= 0; txh <= TXB; txs <= SIDE_TXB; uchk <= 1'b0; uchk2 <= 1'b0; uchk3 <= 1'b0; uchk4 <= 1'b0; upos_hr <= 0; hdr_pos1 <= 0; pos_c <= 0; gsel_oh <= 0; gw_oh <= 0;
            res_v <= 1'b0; res_u <= 0; res_p <= 0; res_i <= 0; res_val <= 0;
            next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; nu_tok <= 0;
            pr_t0 <= 0; pr_t1 <= 0; pr_u0 <= 0; pr_u1 <= 0;
            pr_re <= 1'b0; pr_user <= 0; pr_pos <= 0;
            jq_w <= 0; jq_r <= 0; jq_n <= 0;
            tok_valid <= 1'b0; tok_user <= 0; tok_pos <= 0; tok_id <= 0; users_done <= 0;
            proto_fault <= 1'b0;
            for (u = 0; u < MAXU; u = u + 1) begin
                rcnt[u] <= 0; rbi[u] <= 0; rbv[u] <= 0; ptok[u] <= 0; side_cnt[u] <= 0;
            end
            pr_blk <= 0;
            wf_issue <= 1'b0; wf_reject <= 1'b0; wf_squash <= 1'b0;
        end else begin
            tok_valid <= 1'b0;
            pr_re <= 1'b0;

            // ---- core finished: hand the job to the outbound side
            if (job_done) begin
                running <= 1'b0;
                tx_user <= cur_user; tx_pos <= cur_pos; tx_idx <= rep_idx; tx_val <= rep_val; tx_tok <= cur_tok;
                if (SEND_HIDDEN) begin
                    tx_k <= 1; txh <= TXB + 1; txs <= SIDE_TXB + 1;
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
                // (closed) the position check and the upos update run on the next cycle, from the
                // registered header and its one-hot user (a header is followed by >= 1 payload flit)
                uchk <= !(in_last || in_user >= MAXU);
                rx_j <= 0; rxw <= RXB; rx_st <= R_DATA;
            end
            if (rx_st == R_DATA && vm_we) begin
                if (in_last != (rx_j == RXW - 1)) proto_fault <= 1'b1;
                rx_j <= rx_j + 1'b1; rxw <= rxw + 1'b1;
                if (rx_last_word) rx_st <= R_IDLE;
            end
            // ---- SIDE: header, then the payload into the user's staging slot
            if (rx_side) begin
                if (SIDE_IN == 0 || in_last || in_user >= MAXU) proto_fault <= 1'b1;
                side_user <= in_user; side_addr <= in_data[HDR_ADDR +: 16];
                sww <= VWA'(in_data[HDR_ADDR +: 16]) + (VWA'(in_user) << SIDE_USH);
                rx_j <= 0; rxw <= RXB; rx_st <= R_SIDE;
            end
            if (side_payload) begin
                rx_j <= rx_j + 1'b1; rxw <= rxw + 1'b1; sww <= sww + 1'b1;
                if (in_last) rx_st <= R_IDLE;
            end
            if (rx_side_last && st_rx && side_user == hdr_user) begin
                side_cnt[side_user] <= side_cnt[side_user] + 4'd1 - SIDE_IN[3:0];
            end else begin
                if (rx_side_last) side_cnt[side_user] <= side_cnt[side_user] + 4'd1;
                if (st_rx) side_cnt[hdr_user] <= side_cnt[hdr_user] - SIDE_IN[3:0];
            end
            // header at t: read at t+1 (registered), compare and write at t+2 (the next header of a
            // user is >= 2 cycles later: it carries >= 1 payload flit; its read at >= t+3 sees the write)
            if (uchk) uchk <= 1'b0;
            uchk2 <= uchk; uchk3 <= uchk2; uchk4 <= uchk3;
            gsel_oh <= {{(UNG-1){1'b0}}, 1'b1} << (hdr_user >> 5);
            if (uchk3) begin upos_hr <= upos_sel; hdr_pos1 <= hdr_pos + 1'b1; pos_c <= hdr_pos; gw_oh <= gsel_oh; end
            if (uchk4 && (pos_c > upos_hr || pos_c + WIN < upos_hr)) proto_fault <= 1'b1;
            res_v <= 1'b0;
            if (rx_res) begin
                if (!SOURCE || in_type != MT_RESULT || !in_last || in_user >= MAXU) proto_fault <= 1'b1;
                res_v <= SOURCE && in_type == MT_RESULT && in_user < MAXU;
                res_u <= in_user; res_p <= in_pos;
                res_i <= in_data[HDR_IDX +: NW]; res_val <= in_data[HDR_VAL +: 32];
            end

            // (SOURCE && !WAVE: not implemented here -- ot_rom_pkg_ctrl_wf)
            // ---- SOURCE, WAVE: the engine's registered outputs
            if (SOURCE && WAVE) begin
                wf_issue <= e_wfi; wf_reject <= e_rej; wf_squash <= e_sq;
                pr_re <= e_pr_re;
                if (e_pr_re) begin pr_user <= e_pr_user; pr_pos <= e_pr_pos; pr_blk <= e_pr_blk; end
                if (e_tok_v) begin tok_valid <= 1'b1; tok_user <= e_tok_u; tok_pos <= e_tok_p; tok_id <= e_tok_i; end
                if (e_done) users_done <= users_done + 1'b1;
                if (e_fault) proto_fault <= 1'b1;
            end
            if (SOURCE && cfg_users > MAXU) proto_fault <= 1'b1;

            // ---- outbound framing
            if (vm_re && !job_done) begin
                tx_k <= tx_k + 1'b1; txh <= txh + 1'b1; txs <= txs + 1'b1;
                if (tx_st == T_DATA && tx_k == XWORDS - 1) tx_st <= T_AFTER_HID;
                if (tx_st == T_SDATA && tx_k == SIDE_WORDS - 1) tx_st <= SEND_RESULT ? T_RHDR : T_IDLE;
            end
            if (q_hdr_r) tx_st <= T_IDLE;
            if (q_hdr_s) begin tx_st <= T_SDATA; tx_k <= 0; txh <= TXB; txs <= SIDE_TXB; end
            rd_inflight <= vm_re;
            rd_last <= vm_re && (job_done ? (XWORDS == 1) :
                                 (tx_st == T_SDATA) ? (tx_k == SIDE_WORDS - 1) : (tx_k == XWORDS - 1));
            // Same queue, same priority, same write edge. The opt-in bank
            // mirror removes binary write-address decoding from the late
            // core_done enqueue control. Payload registers remain unreset.
            if (LOCAL_CONTROL) begin
                for (qbank = 0; qbank < TXQ; qbank = qbank + 1) begin
                    if (txq_bank[qbank]) begin
                        if (job_done) begin
                            if (SEND_HIDDEN) begin
                                txq_d[qbank] <= header(HID_D, MT_HIDDEN, XLEN, cur_user, cur_pos, rep_idx, rep_val,
                                                       FWD_TOKEN ? cur_tok : {NW{1'b0}}, 16'd0);
                                txq_l[qbank] <= 1'b0;
                            end else begin
                                txq_d[qbank] <= header(RES_D, MT_RESULT, 8'd0, cur_user, cur_pos, rep_idx, rep_val,
                                                       {NW{1'b0}}, 16'd0);
                                txq_l[qbank] <= 1'b1;
                            end
                        end else if (q_hdr_r) begin
                            txq_d[qbank] <= header(RES_D, MT_RESULT, 8'd0, tx_user, tx_pos, tx_idx, tx_val,
                                                   {NW{1'b0}}, 16'd0);
                            txq_l[qbank] <= 1'b1;
                        end else if (q_hdr_s) begin
                            txq_d[qbank] <= header(SIDE_D, MT_SIDE, SLEN, tx_user, tx_pos, {NW{1'b0}}, 32'd0,
                                                   {NW{1'b0}}, SIDE_A);
                            txq_l[qbank] <= 1'b0;
                        end else if (rd_inflight) begin
                            txq_d[qbank] <= vm_rq;
                            txq_l[qbank] <= rd_last;
                        end
                    end
                end
            end else begin
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
            end
            if (LOCAL_CONTROL && q_push)
                txq_bank <= (txq_bank << 1) | (txq_bank >> (TXQ - 1));
            if (q_push) txq_w <= (txq_w == TXQ - 1) ? {QB{1'b0}} : txq_w + 1'b1;
            if (tx_pop) txq_r <= (txq_r == TXQ - 1) ? {QB{1'b0}} : txq_r + 1'b1;
            txq_n <= txq_n + (q_push ? 1'b1 : 1'b0) - (tx_pop ? 1'b1 : 1'b0);
        end
    end

    generate if (WF) begin : g_wf
        ot_rom_pkg_ctrl_wfc_src #(.DECODED_READ(DECODED_READ), .NW(NW), .USER_W(USER_W), .UCW(UCW), .MAXU(MAXU), .WIN(WIN)) eng (
            .clk(clk), .rst_n(rst_q), .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len),
            .cfg_gen_len(cfg_gen_len), .core_free(src_free),
            .res_v(res_v), .res_u(res_u), .res_p(res_p), .res_i(res_i), .rfull(e_rfull),
            .pr_q(pr_q), .pr_qk(pr_qk),
            .go(e_go), .tok(e_tok), .pos(e_pos), .user(e_user),
            .pr_re(e_pr_re), .pr_user(e_pr_user), .pr_pos(e_pr_pos), .pr_blk(e_pr_blk),
            .tok_v(e_tok_v), .tok_u(e_tok_u), .tok_p(e_tok_p), .tok_i(e_tok_i), .done(e_done),
            .fault(e_fault), .wfi(e_wfi), .rej(e_rej), .sq(e_sq));
    end else begin : g_nowf
        assign e_go = 1'b0; assign e_rfull = 1'b0; assign e_pr_re = 1'b0; assign e_tok_v = 1'b0;
        assign e_done = 1'b0; assign e_fault = 1'b0; assign e_wfi = 1'b0; assign e_rej = 1'b0; assign e_sq = 1'b0;
        assign e_tok = 0; assign e_pos = 0; assign e_pr_pos = 0; assign e_tok_p = 0; assign e_tok_i = 0;
        assign e_user = 0; assign e_pr_user = 0; assign e_tok_u = 0; assign e_pr_blk = 0;
    end endgenerate
endmodule


// ---------------------------------------------------------------------------
// 32 users' expected HIDDEN positions (ot_rom_pkg_ctrl_wfc): `lo` is latched
// locally; a registered read of that entry (0 until written) and a write of it;
// its own reset copy (synchronous clear).
// ---------------------------------------------------------------------------
module ot_rom_pkg_ctrl_wfc_upos #(parameter integer LOCAL_CONTROL = 0, parameter integer NW = 16, parameter integer N = 32) (
    input  wire          clk, rst_n,
    input  wire [4:0]    lo,
    input  wire          rd, rd_early, wr,
    input  wire [NW-1:0] wdata,
    output reg  [NW-1:0] part
);
    // This local copy equals top-level uchk2 on every edge, including reset.
    // It is fed from uchk, not uchk2, so it adds no read/check/write edge.
    (* keep *) reg rd_local;
    generate if (LOCAL_CONTROL) begin : g_local_read_control
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rd_local <= 1'b0; else rd_local <= rd_early;
    end else begin : g_original_read_control
        always @(*) rd_local = rd;
    end endgenerate
    reg          rq;
    always @(posedge clk or negedge rst_n) if (!rst_n) rq <= 1'b0; else rq <= 1'b1;
    reg [4:0]    lo_r;                  // local copy of the user's low bits (one cycle later)
    reg [NW-1:0] upos [0:N-1];
    reg [N-1:0]  uval;
    always @(posedge clk) begin
        lo_r <= lo;
        if (!rq) uval <= 0; else if (wr && lo_r < N) uval[lo_r] <= 1'b1;   // synchronous clear
        if (wr && lo_r < N) upos[lo_r] <= wdata;
        if (rd_local) part <= (lo_r < N && uval[lo_r]) ? upos[lo_r] : {NW{1'b0}};
    end
endmodule

// ---------------------------------------------------------------------------
// ot_rom_pkg_ctrl_wfc_src: the SOURCE wavefront scheduler of
// ot_rom_pkg_ctrl_wfc for many users (MAXU 866) at 1.2 GHz.  Same per-user
// state machine as ot_rom_pkg_ctrl_wf (issue known-token positions back to
// back, up to WIN in flight; verify each result against the token issued at
// q + 1; reject -> squash + re-issue; feed the argmax back), but every event
// is a serial read-modify-write of ONE user's record, in 32-user groups:
//   RD0  every group latches ou[4:0]; the group of ou is decoded (registered)
//   RD1  every group reads that entry (registered)
//   RD2  the group is selected (registered)
//   EX   the record is updated (written back on the next cycle, registered);
//        a start / prompt read / committed token leaves on this cycle.
// Events, in priority order when idle: a queued RESULT, a queued prompt-read
// return, a new user's first position (single cycle, as the reference), the
// lowest eligible user's known-token issue, the lowest user needing a prompt
// read.  The lowest eligible user comes from per-group registered priority
// encoders and a registered group select, valid 3 cycles after the last
// record write (settle).  Cost against the reference: an issue, a commit or a
// verify happens a few cycles later (measured: +2.8 cycles an issue); a stage's job is thousands of cycles.
// RESULT messages queue (4 deep; in_ready drops at 3 queued).
// ---------------------------------------------------------------------------
module ot_rom_pkg_ctrl_wfc_src #(
    parameter integer DECODED_READ = 0,
    parameter integer NW = 16, parameter integer USER_W = 8, parameter integer UCW = 8,
    parameter integer MAXU = 16, parameter integer WIN = 6
) (
    input  wire              clk, rst_n,
    input  wire [UCW-1:0]    cfg_users,
    input  wire [NW-1:0]     cfg_prompt_len, cfg_gen_len,
    input  wire              core_free,
    input  wire              res_v,
    input  wire [USER_W-1:0] res_u,
    input  wire [NW-1:0]     res_p, res_i,
    output wire              rfull,
    input  wire [NW-1:0]     pr_q,
    input  wire              pr_qk,
    output wire              go,
    output wire [NW-1:0]     tok, pos,
    output wire [USER_W-1:0] user,
    output wire              pr_re,
    output wire [USER_W-1:0] pr_user,
    output wire [NW-1:0]     pr_pos,
    output wire [3:0]        pr_blk,
    output wire              tok_v,
    output wire [USER_W-1:0] tok_u,
    output wire [NW-1:0]     tok_p, tok_i,
    output wire              done, fault, wfi, rej, sq
);
    localparam integer GS = 32, NG = (MAXU + GS - 1) / GS, GW = (NG > 1) ? $clog2(NG) : 1;
    // record: [0] started, [1] lt (wnp < steps), [2] wkv, [3] wkp, [4] wkm, [7:5] wnf, [10:8] wsq,
    // [13:11] k0, [17:14] wblk, then wnp, wkt, er (NW each)
    localparam integer O_WNP = 18, O_WKT = 18 + NW, O_ER = 18 + 2 * NW, RW = 18 + 3 * NW;
    localparam [1:0] K_RES = 0, K_PRET = 1, K_ISS = 2, K_RD = 3;
    localparam [2:0] S_IDLE = 0, S_RD0 = 4, S_RD1 = 1, S_RD2 = 2, S_EX = 3;

    // run configuration (held while users are in flight)
    reg [NW-1:0] steps, steps_m1, plen;
    always @(posedge clk) begin
        steps <= cfg_prompt_len + cfg_gen_len - 1'b1; steps_m1 <= cfg_prompt_len + cfg_gen_len - 2'd2;
        plen <= cfg_prompt_len;
    end

    // ---- RESULT queue
    reg [USER_W-1:0] rq_u [0:3];
    reg [NW-1:0]     rq_p [0:3];
    reg [NW-1:0]     rq_i [0:3];
    reg [1:0] rq_w, rq_r; reg [2:0] rq_n;
    assign rfull = rq_n >= 3'd3;
    // ---- prompt-read return queue
    reg [USER_W-1:0] pq_u [0:3];
    reg [NW-1:0]     pq_pos [0:3];
    reg [3:0]        pq_blk [0:3];
    reg [NW-1:0]     pq_q [0:3];
    reg              pq_k [0:3];
    reg [1:0] pq_w, pq_r; reg [2:0] pq_n;
    // prompt reads: tag 1 = new user's first token, 3 = a known-token read
    reg [1:0] t0, t1; reg [USER_W-1:0] u0, u1; reg [NW-1:0] p0, p1; reg [3:0] b0, b1;
    // new users
    reg [UCW-1:0] next_u; reg nu_ok, nu_pend; reg [NW-1:0] nu_tok;

    // ---- groups
    reg  [2:0]        st;
    reg  [1:0]        kind;
    reg  [USER_W-1:0] ou;
    reg  [2:0]        oslot;
    reg  [NW-1:0]     o_p, o_i, o_q; reg [3:0] o_b; reg o_k;
    wire [RW-1:0]     g_rec  [0:NG-1];
    wire [NW-1:0]     g_ring [0:NG-1];
    wire [NG-1:0]     g_kany, g_fany;
    wire [4:0]        g_klo [0:NG-1];
    wire [4:0]        g_flo [0:NG-1];
    reg               w_en, w_ren; reg [USER_W-1:0] w_u; reg [RW-1:0] w_rec; reg [2:0] w_slot; reg [NW-1:0] w_data;
    // write-back one cycle after EX (registered); the next event's read is >= 2 cycles later
    reg               b_en, b_ren; reg [NG-1:0] b_oh; reg [4:0] b_lo; reg [RW-1:0] b_rec; reg [2:0] b_slot;
    reg [NW-1:0]      b_data; reg b_ek, b_ef;
    reg [NG-1:0]      o_oh;           // ou's group, one-hot (RD0 ->)
    genvar gi;
    generate for (gi = 0; gi < NG; gi = gi + 1) begin : g
        (* keep_hierarchy *)
        ot_rom_pkg_ctrl_wfc_grp #(.DECODED_READ(DECODED_READ), .RW(RW), .NW(NW), .N((MAXU - gi * GS) < GS ? (MAXU - gi * GS) : GS)) grp (
            .clk(clk), .rst_n(rst_n), .rd_lo(ou[4:0]), .rd_slot(oslot), .rec_q(g_rec[gi]), .ring_q(g_ring[gi]),
            .we(b_en && b_oh[gi]), .wlo(b_lo), .wrec(b_rec), .wek(b_ek), .wef(b_ef),
            .rwe(b_ren && b_oh[gi]), .rslot(b_slot), .rdata(b_data),
            .k_any(g_kany[gi]), .k_lo(g_klo[gi]), .f_any(g_fany[gi]), .f_lo(g_flo[gi]));
    end endgenerate
    // lowest eligible user: registered group select over the groups' registered encoders
    reg ck_v, cf_v; reg [USER_W-1:0] ck_u, cf_u;
    integer gg;
    always @(posedge clk) begin
        ck_v <= |g_kany; cf_v <= |g_fany; ck_u <= 0; cf_u <= 0;
        for (gg = NG - 1; gg >= 0; gg = gg - 1) begin
            if (g_kany[gg]) ck_u <= (gg << 5) | g_klo[gg];
            if (g_fany[gg]) cf_u <= (gg << 5) | g_flo[gg];
        end
    end
    // the record of ou (RD2 -> EX)
    reg [RW-1:0] rec; reg [NW-1:0] ring;
    reg [RW-1:0] rsel; reg [NW-1:0] rgsel;
    integer sg;
    always @(*) begin
        rsel = 0; rgsel = 0;
        for (sg = 0; sg < NG; sg = sg + 1) if (o_oh[sg]) begin rsel = rsel | g_rec[sg]; rgsel = rgsel | g_ring[sg]; end
    end
    always @(posedge clk) begin
        rec <= rsel; ring <= rgsel; o_oh <= {{(NG-1){1'b0}}, 1'b1} << (ou >> 5);
        b_en <= w_en; b_ren <= w_ren; b_oh <= {{(NG-1){1'b0}}, 1'b1} << (w_u >> 5); b_lo <= w_u[4:0];
        b_rec <= w_rec; b_slot <= w_slot; b_data <= w_data;
        b_ek <= w_rec[0] && w_rec[2] && w_rec[7:5] < WIN && w_rec[1];
        b_ef <= w_rec[0] && !w_rec[2] && !w_rec[3] && !w_rec[4] && w_rec[1];
    end
    wire          r_stv = rec[0], r_lt = rec[1], r_wkv = rec[2], r_wkp = rec[3], r_wkm = rec[4];
    wire [2:0]    r_wnf = rec[7:5], r_wsq = rec[10:8], r_k0 = rec[13:11];
    wire [3:0]    r_wblk = rec[17:14];
    wire [NW-1:0] r_wnp = rec[O_WNP +: NW], r_wkt = rec[O_WKT +: NW], r_er = rec[O_ER +: NW];
    function automatic [RW-1:0] pack(input stv, input lt, input wkv, input wkp, input wkm, input [2:0] wnf,
                                     input [2:0] wsq, input [2:0] k0, input [3:0] wblk, input [NW-1:0] wnp,
                                     input [NW-1:0] wkt, input [NW-1:0] er);
        pack = {er, wkt, wnp, wblk, k0, wsq, wnf, wkm, wkp, wkv, lt, stv};
    endfunction

    reg [2:0] settle;
    // ---- decisions
    wire nu_start = nu_ok && next_u < MAXU && core_free;           // a new user's first position
    wire fetch = !nu_ok && !nu_pend && next_u < cfg_users && next_u < MAXU;
    wire idle_new = st == S_IDLE && rq_n == 0 && pq_n == 0 && nu_start;
    wire ex = st == S_EX;
    wire ex_iss = ex && kind == K_ISS && core_free && r_stv && r_wkv && r_wnf < WIN && r_lt;
    wire ex_rd = ex && kind == K_RD;
    wire do_fetch = fetch && !ex_rd && !idle_new;
    assign go = idle_new || ex_iss;
    assign tok = idle_new ? nu_tok : r_wkt;
    assign pos = idle_new ? {NW{1'b0}} : r_wnp;
    assign user = idle_new ? USER_W'(next_u) : ou;
    assign pr_re = ex_rd || do_fetch;
    assign pr_user = ex_rd ? ou : USER_W'(next_u);
    assign pr_pos = ex_rd ? r_wnp : {NW{1'b0}};
    assign pr_blk = ex_rd ? r_wblk : 4'd0;
    // RESULT (EX): the reference's verify / reject / squash on the user's record
    wire          x_res = ex && kind == K_RES;
    wire          x_cont = (o_p + 1'b1) < steps;
    wire          x_gepl = (o_p + 1'b1) >= plen;
    wire          x_sq = r_wsq != 0;
    wire          x_rew = !x_sq && x_cont && r_wnf >= 3'd2 && x_gepl && ring != o_i;
    wire          x_blk = !x_sq && x_cont && r_wnf < 3'd2 && x_gepl;
    wire          x_rejb = x_blk && r_wkv && r_wkt != o_i;
    assign tok_v = x_res && !x_sq; assign tok_u = ou; assign tok_p = o_p; assign tok_i = o_i;
    assign done = x_res && !x_sq && !x_cont;
    assign fault = x_res && o_p != r_er;
    assign wfi = ex_iss; assign rej = x_res && (x_rew || x_rejb); assign sq = x_res && x_sq;

    always @(*) begin
        w_en = 1'b0; w_ren = 1'b0; w_u = ou; w_rec = rec; w_slot = r_wnp[2:0]; w_data = r_wkt;
        if (idle_new) begin
            w_en = 1'b1; w_ren = 1'b1; w_u = USER_W'(next_u); w_slot = 3'd0; w_data = nu_tok;
            w_rec = pack(1'b1, steps > 1, 1'b0, 1'b0, 1'b0, 3'd1, 3'd0, 3'd0, 4'd0, 1, {NW{1'b0}}, {NW{1'b0}});
        end else if (ex_iss) begin
            w_en = 1'b1; w_ren = 1'b1;
            w_rec = pack(1'b1, r_wnp != steps_m1, 1'b0, r_wkp, 1'b0, r_wnf + 3'd1, r_wsq, r_k0, r_wblk,
                         r_wnp + 1'b1, r_wkt, r_er);
        end else if (ex_rd) begin
            w_en = 1'b1; w_rec[3] = 1'b1;
        end else if (ex && kind == K_PRET) begin
            w_en = 1'b1; w_rec[3] = 1'b0;
            if (r_wnp == o_p && r_wblk == o_b && !r_wkv) begin
                if (o_k) begin w_rec[2] = 1'b1; w_rec[O_WKT +: NW] = o_q; end
                else w_rec[4] = 1'b1;
            end
        end else if (x_res) begin
            w_en = 1'b1;
            w_rec[7:5] = r_wnf - 3'd1;
            w_rec[O_ER +: NW] = o_p + 1'b1 - ((r_wsq == 3'd1) ? NW'(r_k0) : {NW{1'b0}});
            if (x_sq) w_rec[10:8] = r_wsq - 3'd1;
            else if (x_rew) begin
                w_rec[10:8] = r_wnf - 3'd1; w_rec[13:11] = r_wnf - 3'd1;
                w_rec[O_WNP +: NW] = o_p + 1'b1; w_rec[17:14] = r_wblk + 1'b1; w_rec[1] = 1'b1;
                w_rec[2] = 1'b1; w_rec[O_WKT +: NW] = o_i; w_rec[4] = 1'b0;
            end else if (x_blk) begin
                if (x_rejb) w_rec[17:14] = r_wblk + 1'b1;
                w_rec[2] = 1'b1; w_rec[O_WKT +: NW] = o_i; w_rec[4] = 1'b0;
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; kind <= K_RES; ou <= 0; oslot <= 0; o_p <= 0; o_i <= 0; o_q <= 0; o_b <= 0; o_k <= 1'b0;
            rq_w <= 0; rq_r <= 0; rq_n <= 0; pq_w <= 0; pq_r <= 0; pq_n <= 0;
            t0 <= 0; t1 <= 0; u0 <= 0; u1 <= 0; p0 <= 0; p1 <= 0; b0 <= 0; b1 <= 0;
            next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; nu_tok <= 0; settle <= 0;
        end else begin
            settle <= (w_en || b_en) ? 3'd0 : (settle == 3'd3 ? 3'd3 : settle + 1'b1);
            // RESULT queue
            if (res_v) begin rq_u[rq_w] <= res_u; rq_p[rq_w] <= res_p; rq_i[rq_w] <= res_i; rq_w <= rq_w + 1'b1; end
            // prompt reads in flight
            t0 <= ex_rd ? 2'd3 : do_fetch ? 2'd1 : 2'd0; u0 <= ou; p0 <= r_wnp; b0 <= r_wblk;
            t1 <= t0; u1 <= u0; p1 <= p0; b1 <= b0;
            if (do_fetch) nu_pend <= 1'b1;
            if (t1 == 2'd1) begin nu_tok <= pr_q; nu_ok <= 1'b1; nu_pend <= 1'b0; end
            if (t1 == 2'd3) begin
                pq_u[pq_w] <= u1; pq_pos[pq_w] <= p1; pq_blk[pq_w] <= b1; pq_q[pq_w] <= pr_q; pq_k[pq_w] <= pr_qk;
                pq_w <= pq_w + 1'b1;
            end
            if (idle_new) begin next_u <= next_u + 1'b1; nu_ok <= 1'b0; end
            // the event engine
            case (st)
                S_IDLE: begin
                    if (rq_n != 0) begin
                        st <= S_RD0; kind <= K_RES; ou <= rq_u[rq_r]; o_p <= rq_p[rq_r]; o_i <= rq_i[rq_r];
                        oslot <= rq_p[rq_r][2:0] + 3'd1; rq_r <= rq_r + 1'b1;
                    end else if (pq_n != 0) begin
                        st <= S_RD0; kind <= K_PRET; ou <= pq_u[pq_r]; o_p <= pq_pos[pq_r]; o_b <= pq_blk[pq_r];
                        o_q <= pq_q[pq_r]; o_k <= pq_k[pq_r]; pq_r <= pq_r + 1'b1;
                    end else if (idle_new) begin
                        st <= S_IDLE;
                    end else if (!nu_ok && settle == 3'd3 && ck_v && core_free) begin
                        st <= S_RD0; kind <= K_ISS; ou <= ck_u;
                    end else if (settle == 3'd3 && cf_v && !fetch) begin
                        st <= S_RD0; kind <= K_RD; ou <= cf_u;
                    end
                end
                S_RD0: st <= S_RD1;
                S_RD1: st <= S_RD2;
                S_RD2: st <= S_EX;
                default: st <= S_IDLE;
            endcase
            rq_n <= rq_n + (res_v ? 3'd1 : 3'd0) - ((st == S_IDLE && rq_n != 0) ? 3'd1 : 3'd0);
            pq_n <= pq_n + (t1 == 2'd3 ? 3'd1 : 3'd0) - ((st == S_IDLE && rq_n == 0 && pq_n != 0) ? 3'd1 : 3'd0);
        end
    end
endmodule

// ---------------------------------------------------------------------------
// 32 users' wavefront records + issued-token rings (ot_rom_pkg_ctrl_wfc_src):
// one read port (address latched locally, then a registered read of the record
// and ring entry), one write port, registered lowest-eligible encoders.  Only
// the started / eligibility bits are cleared (own reset copy, synchronous); a
// record is written whole when its user starts and read only after.
// ---------------------------------------------------------------------------
module ot_rom_pkg_ctrl_wfc_grp #(parameter integer DECODED_READ = 0, parameter integer RW = 64, parameter integer NW = 16, parameter integer N = 32) (
    input  wire          clk, rst_n,
    input  wire [4:0]    rd_lo,
    input  wire [2:0]    rd_slot,
    output reg  [RW-1:0] rec_q,
    output reg  [NW-1:0] ring_q,
    input  wire          we,
    input  wire [4:0]    wlo,
    input  wire [RW-1:0] wrec,
    input  wire          wek, wef,
    input  wire          rwe,
    input  wire [2:0]    rslot,
    input  wire [NW-1:0] rdata,
    output reg           k_any, f_any,
    output reg  [4:0]    k_lo, f_lo
);
    reg          rq;
    always @(posedge clk or negedge rst_n) if (!rst_n) rq <= 1'b0; else rq <= 1'b1;
    reg [4:0]    lo_r; reg [2:0] slot_r;   // local copies of the read address (one cycle later)
    reg [RW-1:1] recm [0:N-1];
    reg [NW-1:0] ringm [0:N*8-1];
    reg [N-1:0]  stv, ek, ef;
    always @(posedge clk) begin
        lo_r <= rd_lo; slot_r <= rd_slot;
        if (!rq) begin stv <= 0; ek <= 0; ef <= 0; end                    // synchronous clear
        else if (we && wlo < N) begin stv[wlo] <= wrec[0]; ek[wlo] <= wek; ef[wlo] <= wef; end
        if (we && wlo < N) recm[wlo] <= wrec[RW-1:1];
        if (rwe && wlo < N) ringm[{wlo, rslot}] <= rdata;
    end
    generate if (DECODED_READ) begin : g_decoded_read
        // Decode on the existing address-latch edge. The data is read on
        // the original following edge, including read-before-write behavior.
        reg [N-1:0] user_sel;
        reg [7:0] slot_sel;
        localparam integer LEAVES = 1 << $clog2(N);
        wire [RW-1:0] rec_tree [1:2*LEAVES-1];
        wire [NW-1:0] ring_tree [1:16*LEAVES-1];
        genvar u, s, t;
        for (u=0; u<N; u=u+1) begin : g_user
            always @(posedge clk) user_sel[u] <= rd_lo == u;
        end
        for (u=0; u<LEAVES; u=u+1) begin : g_leaf
            if (u<N) begin : g_live
                assign rec_tree[LEAVES+u] =
                    {RW{user_sel[u]}} & {recm[u],stv[u]};
                for (s=0; s<8; s=s+1) begin : g_slot
                    assign ring_tree[8*LEAVES+u*8+s] =
                        {NW{user_sel[u] && slot_sel[s]}} & ringm[u*8+s];
                end
            end else begin : g_padding
                assign rec_tree[LEAVES+u] = 0;
                for (s=0; s<8; s=s+1) begin : g_slot
                    assign ring_tree[8*LEAVES+u*8+s] = 0;
                end
            end
        end
        for (t=1; t<LEAVES; t=t+1) begin : g_rec_reduce
            assign rec_tree[t] = rec_tree[2*t] | rec_tree[2*t+1];
        end
        for (t=1; t<8*LEAVES; t=t+1) begin : g_ring_reduce
            assign ring_tree[t] = ring_tree[2*t] | ring_tree[2*t+1];
        end
        for (s=0; s<8; s=s+1) begin : g_slot_select
            always @(posedge clk) slot_sel[s] <= rd_slot == s;
        end
        always @(posedge clk) begin
            rec_q <= rec_tree[1];
            ring_q <= ring_tree[1];
        end
    end else begin : g_binary_read
        always @(posedge clk) begin
            rec_q <= (lo_r < N) ? {recm[lo_r], stv[lo_r]} : {RW{1'b0}};
            ring_q <= (lo_r < N) ? ringm[{lo_r, slot_r}] : {NW{1'b0}};
        end
    end endgenerate
    integer k;
    always @(posedge clk) begin
        k_any <= |ek; f_any <= |ef; k_lo <= 0; f_lo <= 0;
        for (k = N - 1; k >= 0; k = k - 1) begin
            if (ek[k]) k_lo <= k;
            if (ef[k]) f_lo <= k;
        end
    end
endmodule
