`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Package controller of the ROM array (docs/ROM_ARRAY_FABRIC_RTL.md).
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
//
// After the core finishes, the controller frames what the package sends:
// a HIDDEN message to HID_DEST (payload read from vector-memory words TXB..)
// and/or a RESULT message to RES_DEST.  Destinations are fabric ids (a
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
module ot_rom_pkg_ctrl #(
    parameter integer PKG_ID       = 0,
    parameter integer FLIT         = 512,    // bits; one vector-memory word
    parameter integer NW           = 16,     // token / position bits
    parameter integer AW           = 24,     // KV address bits
    parameter integer VWA          = 8,      // vector-memory word address bits
    parameter integer MAXU         = 16,     // user contexts
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
    parameter integer TXQ          = 4       // outbound queue, flits
) (
    input  wire               clk,
    input  wire               rst_n,
    // run configuration (SOURCE)
    input  wire [7:0]         cfg_users,
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
    output reg  [7:0]         pr_user,
    output reg  [NW-1:0]      pr_pos,
    input  wire [NW-1:0]      pr_q,
    // observation
    output wire               core_busy,
    output reg                tok_valid,      // SOURCE: a step's reduced token
    output reg  [7:0]         tok_user,
    output reg  [NW-1:0]      tok_pos,
    output reg  [NW-1:0]      tok_id,
    output reg  [7:0]         users_done,
    output reg                proto_fault
);
    // -- header ----------------------------------------------------------------------
    localparam integer HDR_DEST = 0, HDR_SRC = 8, HDR_TYPE = 16, HDR_LEN = 24, HDR_USER = 32,
                       HDR_POS = 40, HDR_IDX = 56, HDR_VAL = 72;
    localparam [3:0] MT_HIDDEN = 4'd1, MT_RESULT = 4'd2;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
    localparam [7:0] SRC_ID = PKG_ID, HID_D = HID_DEST, RES_D = RES_DEST, XLEN = XWORDS;

    function automatic [FLIT-1:0] header(input [7:0] dest, input [3:0] typ, input [7:0] len,
                                         input [7:0] user, input [NW-1:0] pos,
                                         input [NW-1:0] idx, input [31:0] val);
        begin
            header = {FLIT{1'b0}};
            header[HDR_DEST +: 8] = dest;
            header[HDR_SRC +: 8]  = SRC_ID;
            header[HDR_TYPE +: 4] = typ;
            header[HDR_LEN +: 8]  = len;
            header[HDR_USER +: 8] = user;
            header[HDR_POS +: NW] = pos;
            header[HDR_IDX +: NW] = idx;
            header[HDR_VAL +: 32] = val;
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
    wire [7:0]    in_user = in_data[HDR_USER +: 8];
    wire [NW-1:0] in_pos  = in_data[HDR_POS +: NW];

    // -- per-user context --------------------------------------------------------------
    reg [NW-1:0] upos [0:MAXU-1];      // next expected position (SOURCE: in-flight step)

    // -- core -------------------------------------------------------------------------
    reg          running;              // from the start edge until the job is handed to TX
    reg [7:0]    cur_user;
    reg [NW-1:0] cur_pos, cur_pa_idx;
    reg [31:0]   cur_pa_val;
    assign core_busy = running;

    // -- outbound ---------------------------------------------------------------------
    // The HIDDEN (or RESULT) header is queued on the cycle the job is taken, and
    // payload word 0 is read on the same cycle; words 1.. follow one per cycle
    // while the queue has room.  A RESULT after a HIDDEN message follows its
    // last payload flit.
    localparam integer QB = (TXQ > 1) ? $clog2(TXQ) : 1;
    localparam [1:0] T_IDLE = 0, T_DATA = 1, T_RHDR = 2;
    reg [1:0]      tx_st;
    reg [FLIT-1:0] txq_d [0:TXQ-1];
    reg            txq_l [0:TXQ-1];
    reg [QB-1:0]   txq_w, txq_r;
    reg [QB:0]     txq_n;
    reg            rd_inflight, rd_last;
    reg [VWA-1:0]  tx_k;
    reg [7:0]      tx_user;
    reg [NW-1:0]   tx_pos, tx_idx;
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

    // -- inbound ----------------------------------------------------------------------
    // A HIDDEN header is taken whenever no received job is waiting (even while
    // the core runs); its payload flits are written once the core has finished
    // (from the cycle its job is taken) and the outbound message has read the
    // word they overwrite.
    localparam R_IDLE = 1'b0, R_DATA = 1'b1;
    reg          rx_st;
    reg [VWA-1:0] rx_j;
    reg [7:0]    hdr_user;
    reg [NW-1:0] hdr_pos, hdr_pa_idx;
    reg [31:0]   hdr_pa_val;
    reg          pend;                   // a received job waits for the outbound reads
    wire [VWA-1:0] rx_word = RXB + rx_j;
    wire rx_word_free = !tx_reading || rx_word < tx_lo || rx_word >= TXB + XWORDS;
    wire core_free = !running || job_done;
    assign vm_wdata = in_data;

    // -- SOURCE: step scheduling and argmax reduction ------------------------------------
    reg          res_v;                  // registered RESULT header
    reg [7:0]    res_u;
    reg [NW-1:0] res_p, res_i;
    reg [31:0]   res_val;
    reg [3:0]    rcnt [0:MAXU-1];
    reg [NW-1:0] rbi  [0:MAXU-1];
    reg [31:0]   rbv  [0:MAXU-1];
    reg [NW-1:0] ptok [0:MAXU-1];        // prompt token of the user's next position
    reg [7:0]    next_u;
    reg          nu_ok;                  // next new user's first token fetched
    reg [NW-1:0] nu_tok;
    reg          nu_pend;                // ... being fetched
    // prompt reads: issued (registered port) at t, performed at t+1, data at t+2;
    // tag 1: new-user fetch, 2: prefetch of the next token of user pr_u*
    reg [1:0]    pr_t0, pr_t1;
    reg [7:0]    pr_u0, pr_u1;
    // ready-job queue
    reg [7:0]    jq_u [0:MAXU-1];
    reg [NW-1:0] jq_p [0:MAXU-1];
    reg [NW-1:0] jq_t [0:MAXU-1];
    reg [UB-1:0] jq_w, jq_r;
    reg [UB:0]   jq_n;

    // reduction of the registered RESULT (combinational)
    reg          fb_v, fb_cont;
    reg [NW-1:0] fb_tok, fb_idx;
    reg [31:0]   fb_val;
    reg [3:0]    red_n;
    always @(*) begin
        red_n = rcnt[res_u[UB-1:0]] + 1'b1;
        if (rcnt[res_u[UB-1:0]] == 0 || better(res_i, res_val, rbi[res_u[UB-1:0]], rbv[res_u[UB-1:0]])) begin
            fb_idx = res_i; fb_val = res_val;
        end else begin
            fb_idx = rbi[res_u[UB-1:0]]; fb_val = rbv[res_u[UB-1:0]];
        end
        fb_v = SOURCE && res_v && (red_n == RESULT_PARTS);
        fb_cont = (res_p + 1'b1) < (cfg_prompt_len + cfg_gen_len - 1'b1);
        fb_tok = ((res_p + 1'b1) < cfg_prompt_len) ? ptok[res_u[UB-1:0]] : fb_idx;
    end

    // -- combinational port control -------------------------------------------------------
    reg rx_hdr, rx_res, rx_last_word;
    reg st_rx, st_new, st_q, st_fb;
    reg [7:0] st_user;
    always @(*) begin
        in_ready = 1'b0; rx_hdr = 1'b0; rx_res = 1'b0;
        vm_we = 1'b0; vm_waddr = rx_word;
        if (rx_st == R_IDLE) begin
            if (in_type == MT_HIDDEN) begin
                in_ready = !pend; rx_hdr = in_valid && !pend;
            end else begin
                in_ready = 1'b1; rx_res = in_valid;          // RESULT (or a bad type)
            end
        end else begin
            in_ready = core_free && rx_word_free;
            vm_we = in_valid && in_ready;
        end
        rx_last_word = (rx_st == R_DATA) && vm_we && (rx_j == XWORDS - 1);
        vm_re = (job_done && SEND_HIDDEN) || ((tx_st == T_DATA) && tx_space);
        vm_raddr = job_done ? TXB : TXB + tx_k;

        // core start: at most one source per cycle; the core samples it on this edge
        st_rx = (rx_last_word || pend) && !running && !tx_reading;
        st_new = 1'b0; st_q = 1'b0; st_fb = 1'b0;
        if (SOURCE && !running && !tx_reading && !pend && rx_st == R_IDLE) begin
            st_new = nu_ok;
            st_q   = !nu_ok && jq_n != 0;
            st_fb  = !nu_ok && jq_n == 0 && fb_v && fb_cont;
        end
        core_start = st_rx || st_new || st_q || st_fb;
        core_token = 0; core_pos = hdr_pos; st_user = hdr_user;
        if (st_new) begin core_token = nu_tok; core_pos = 0; st_user = next_u; end
        if (st_q)   begin core_token = jq_t[jq_r]; core_pos = jq_p[jq_r]; st_user = jq_u[jq_r]; end
        if (st_fb)  begin core_token = fb_tok; core_pos = res_p + 1'b1; st_user = res_u; end
    end

    // -- sequential ---------------------------------------------------------------------
    wire q_hdr_r = !job_done && tx_st == T_RHDR && tx_space && !rd_inflight;   // RESULT after a HIDDEN
    wire q_push  = (job_done && (SEND_HIDDEN || SEND_RESULT)) || q_hdr_r || rd_inflight;
    integer u;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 1'b0; cur_user <= 0; cur_pos <= 0; cur_pa_idx <= 0; cur_pa_val <= 0; kv_base <= 0;
            pend <= 1'b0; hdr_user <= 0; hdr_pos <= 0; hdr_pa_idx <= 0; hdr_pa_val <= 0;
            tx_st <= T_IDLE; txq_w <= 0; txq_r <= 0; txq_n <= 0; rd_inflight <= 1'b0; rd_last <= 1'b0;
            tx_k <= 0; tx_user <= 0; tx_pos <= 0; tx_idx <= 0; tx_val <= 0;
            rx_st <= R_IDLE; rx_j <= 0;
            res_v <= 1'b0; res_u <= 0; res_p <= 0; res_i <= 0; res_val <= 0;
            next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; nu_tok <= 0;
            pr_t0 <= 0; pr_t1 <= 0; pr_u0 <= 0; pr_u1 <= 0;
            pr_re <= 1'b0; pr_user <= 0; pr_pos <= 0;
            jq_w <= 0; jq_r <= 0; jq_n <= 0;
            tok_valid <= 1'b0; tok_user <= 0; tok_pos <= 0; tok_id <= 0; users_done <= 0;
            proto_fault <= 1'b0;
            for (u = 0; u < MAXU; u = u + 1) begin
                upos[u] <= 0; rcnt[u] <= 0; rbi[u] <= 0; rbv[u] <= 0; ptok[u] <= 0;
            end
        end else begin
            tok_valid <= 1'b0;
            pr_re <= 1'b0;

            // ---- core finished: hand the job to the outbound side
            if (job_done) begin
                running <= 1'b0;
                tx_user <= cur_user; tx_pos <= cur_pos; tx_idx <= rep_idx; tx_val <= rep_val;
                if (SEND_HIDDEN) begin
                    tx_k <= 1;
                    tx_st <= (XWORDS > 1) ? T_DATA : (SEND_RESULT ? T_RHDR : T_IDLE);
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
            end
            if (st_rx) pend <= 1'b0;
            else if (rx_last_word) pend <= 1'b1;

            // ---- inbound
            if (rx_hdr) begin
                hdr_user <= in_user; hdr_pos <= in_pos;
                hdr_pa_idx <= in_data[HDR_IDX +: NW]; hdr_pa_val <= in_data[HDR_VAL +: 32];
                if (upos[in_user[UB-1:0]] != in_pos || in_last || in_user >= MAXU) proto_fault <= 1'b1;
                upos[in_user[UB-1:0]] <= in_pos + 1'b1;
                rx_j <= 0; rx_st <= R_DATA;
            end
            if (rx_st == R_DATA && vm_we) begin
                if (in_last != (rx_j == XWORDS - 1)) proto_fault <= 1'b1;
                rx_j <= rx_j + 1'b1;
                if (rx_last_word) rx_st <= R_IDLE;
            end
            res_v <= 1'b0;
            if (rx_res) begin
                if (!SOURCE || in_type != MT_RESULT || !in_last || in_user >= MAXU) proto_fault <= 1'b1;
                res_v <= SOURCE && in_type == MT_RESULT;
                res_u <= in_user; res_p <= in_pos;
                res_i <= in_data[HDR_IDX +: NW]; res_val <= in_data[HDR_VAL +: 32];
            end

            // ---- SOURCE: reduction, token feedback, step scheduling
            if (SOURCE) begin
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
                end else if (!nu_ok && !nu_pend && next_u < cfg_users) begin
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

            // ---- outbound framing
            if (vm_re && !job_done) begin
                tx_k <= tx_k + 1'b1;
                if (tx_k == XWORDS - 1) tx_st <= SEND_RESULT ? T_RHDR : T_IDLE;
            end
            if (q_hdr_r) tx_st <= T_IDLE;
            rd_inflight <= vm_re;
            rd_last <= vm_re && (job_done ? (XWORDS == 1) : (tx_k == XWORDS - 1));
            if (job_done) begin
                if (SEND_HIDDEN) begin
                    txq_d[txq_w] <= header(HID_D, MT_HIDDEN, XLEN, cur_user, cur_pos, rep_idx, rep_val);
                    txq_l[txq_w] <= 1'b0;
                end else begin
                    txq_d[txq_w] <= header(RES_D, MT_RESULT, 8'd0, cur_user, cur_pos, rep_idx, rep_val);
                    txq_l[txq_w] <= 1'b1;
                end
            end else if (q_hdr_r) begin
                txq_d[txq_w] <= header(RES_D, MT_RESULT, 8'd0, tx_user, tx_pos, tx_idx, tx_val);
                txq_l[txq_w] <= 1'b1;
            end else if (rd_inflight) begin
                txq_d[txq_w] <= vm_rq;
                txq_l[txq_w] <= rd_last;
            end
            if (q_push) txq_w <= (txq_w == TXQ - 1) ? {QB{1'b0}} : txq_w + 1'b1;
            if (tx_pop) txq_r <= (txq_r == TXQ - 1) ? {QB{1'b0}} : txq_r + 1'b1;
            txq_n <= txq_n + (q_push ? 1'b1 : 1'b0) - (tx_pop ? 1'b1 : 1'b0);
        end
    end
endmodule
