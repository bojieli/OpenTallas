`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_pkg_ctrl (stream ds-control, 2026-10-08): the package (die) controller of the DS-ROM S81 array, the S81
// successor of ot_rom_pkg_ctrl_x (rtl/rom/ot_rom_pkg_ctrl_x.sv, pinned and unchanged).  It keeps x's per-user
// context, position-order checks, cut-through HIDDEN receive into the vector memory, per-user SIDE staging and the
// SOURCE's token feedback / argmax reduction, and changes what the S81 geometry needs:
//
//   * header: ot_s81_hdr.svh (12-bit fabric ids and lengths, 21-bit positions / tokens, run stop configuration);
//   * the decode core is the stage program sequencer (ot_s81_stage_seq): a job is handed to it at the HIDDEN
//     HEADER (job_v), not at the last payload word, so the sequencer queues the stage's job descriptors at the
//     engines while the 640-flit payload lands; the engines start on their inputs (dataflow).  The payload is
//     written into the job's vector-memory slot (RXB + slot * RXW; slot = the sequencer's job slot, mirrored here:
//     it alternates on every accepted job), so the next user's payload lands while the current job still reads its
//     own slot (the sequencer frees a slot only on job_done: every job of the stage, every VM read included, done);
//   * outbound framing is NOT here: a stage's hand-off (HIDDEN / SIDE / RESULT) is a job of its own program (the
//     'hop' engine port, ot_s81_hop_tx), built from the job descriptor's context, so the hand-off starts on its
//     inputs like any engine job instead of after a core-done handshake;
//   * SOURCE (stage 0, the embedding die): RESULT_PARTS = 1 (the head dies' ordered root has reduced the vocabulary
//     parts already) and the STOP CONDITION: a user ends when (a) the head marks its token STOP (EOS when the run
//     enables it, or the next position reaching the maximum sequence length; ot_s81_stop) on a generated position,
//     (b) its next position reaches cfg_max_len (defensive copy of the head's rule), or (c) gen_len tokens have been
//     generated (the bound host_cq reserves completion space for).  Stopped users count in users_done.
//   * BOOT GATE: the SOURCE starts no new user while boot_ok = 0 (the boot tables, e.g. the HBM RoPE table, are not
//     loaded and verified: ot_s81_boot_seq).
//
// Inbound (in_* from ot_s81_stage_guard):
//   HIDDEN  (position == the user's next one, or 0: a new request for the user slot restarts its sequence)
//           header (job_v to the sequencer, taken only when it has a free job slot) + RXW payload flits written
//           at RXB + slot * RXW ..; the run configuration (EOSEN / EOS / MAXL) is latched from the header.
//   SIDE    header + payload into the user's staging slot (header ADDR + (user << SIDE_USH)); taken any time.
//   RESULT  (SOURCE) {user, pos, token, logit, STOP}: reduction, stop, token feedback; tok_* to the host queue.
// proto_fault (sticky, first code in fault_code): 1 HIDDEN out of position order, 2 HIDDEN/SIDE user >= MAXU,
//   3 framing (last early / late), 4 RESULT at a non-SOURCE die or out of order, 5 HIDDEN at the SOURCE,
//   6 SIDE outside the staging space, 7 cfg_users > MAXU, 8 RESULT_PARTS != 1 reduction overflow.
// ---------------------------------------------------------------------------
module ot_s81_pkg_ctrl #(
    parameter integer WINDOW_CONTEXT = 0,
    parameter integer TOKEN_TYPES = 0,
    parameter integer MY_ID      = 0,
    parameter integer FLIT       = 512,
    parameter integer NW         = 21,
    parameter integer USER_W     = 12,
    parameter integer MAXU       = 16,
    parameter integer VWA        = 14,       // vector-memory word address
    parameter integer RXB        = 0,
    parameter integer RXW        = 640,      // HIDDEN payload flits (S81 hop: 40,976 B / 64 B)
    parameter integer SOURCE     = 0,
    parameter integer SIDE_USH   = 6,
    parameter integer SIDE_BASE  = 0,        // staging region [SIDE_BASE, SIDE_BASE + MAXU << SIDE_USH)
    parameter integer MUT        = 0         // bench negative control: 1 = STOP ignored (fixed gen_len only)
) (
    input  wire               clk,
    input  wire               rst_n,
    // run configuration (SOURCE)
    input  wire [7:0]         cfg_users,
    input  wire [NW-1:0]      cfg_prompt_len,
    input  wire [NW-1:0]      cfg_gen_len,
    input  wire [NW:0]        cfg_max_len,
    input  wire               cfg_eos_en,
    input  wire [NW-1:0]      cfg_eos_id,
    input  wire               boot_ok,
    // inbound
    input  wire               in_valid,
    output reg                in_ready,
    input  wire [FLIT-1:0]    in_data,
    input  wire               in_last,
    // jobs to the stage sequencer
    output reg                job_v,
    input  wire               job_rdy,
    output reg  [USER_W-1:0]  job_user,
    output reg  [NW-1:0]      job_pos,
    output reg  [NW-1:0]      job_tok,
    output reg                job_win_v,
    output reg [67:0]         job_win_ids,
    output reg                job_win_dead,
    output reg [2:0] job_token_type,
    input  wire               job_done,
    // run stop configuration (to the hop framer / head sampler)
    output reg                run_eosen,
    output reg  [NW-1:0]      run_eos,
    output reg  [NW:0]        run_maxl,
    // vector memory write port
    output reg                vm_we,
    output reg  [VWA-1:0]     vm_waddr,
    output wire [FLIT-1:0]    vm_wdata,
    // prompt tokens (SOURCE), synchronous read
    output reg                pr_re,
    output reg  [7:0]         pr_user,
    output reg  [NW-1:0]      pr_pos,
    input  wire [NW-1:0]      pr_q,
    input wire [2:0] pr_token_type,
    // observation / host queue
    output reg                tok_valid,
    output reg  [7:0]         tok_user,
    output reg  [NW-1:0]      tok_pos,
    output reg  [NW-1:0]      tok_id,
    output reg                tok_stop,
    output reg  [7:0]         users_done,
    output reg  [31:0]        st_jobs_done,
    output reg                proto_fault,
    output reg  [3:0]         fault_code
);
// S81 header (ot_s81_hdr.svh, inlined so synthesis needs no include path)
localparam integer SH_DEST = 0, SH_SRC = 12, SH_TYPE = 24, SH_LEN = 28, SH_USER = 40, SH_POS = 52, SH_IDX = 73,
                   SH_VAL = 94, SH_TOK = 126, SH_ADDR = 147, SH_STOP = 163, SH_EOSEN = 164, SH_EOS = 165,
                   SH_MAXL = 186, SH_END = 208;
localparam integer SH_IDW = 12, SH_LENW = 12, SH_UW = 12, SH_NW = 21, SH_MLW = 22;
localparam [3:0] MT_HIDDEN = 4'd1, MT_RESULT = 4'd2, MT_SIDE = 4'd3;
    localparam integer UB = (MAXU > 1) ? $clog2(MAXU) : 1;
`ifndef SYNTHESIS
    initial begin
        if (USER_W > SH_UW || NW != SH_NW || FLIT < SH_END) $fatal(1, "ot_s81_pkg_ctrl: header widths");
        if (RXB + 2 * RXW > (1 << VWA) || SIDE_BASE + (MAXU << SIDE_USH) > (1 << VWA))
            $fatal(1, "ot_s81_pkg_ctrl: VM regions exceed the address space");
    end
`endif
    wire [3:0]        in_type = in_data[SH_TYPE +: 4];
    wire [USER_W-1:0] in_user = in_data[SH_USER +: USER_W];
    wire [NW-1:0]     in_pos  = in_data[SH_POS +: NW];
    wire [SH_LENW-1:0] in_len = in_data[SH_LEN +: SH_LENW];
    wire window_bad=WINDOW_CONTEXT && (!in_data[276] || in_data[208 +:17]>=17'd99092 ||
        in_data[225 +:17]>=17'd99092 || in_data[242 +:17]>=17'd99092 || in_data[259 +:17]>=17'd99092);
    assign vm_wdata = in_data;

    reg [NW-1:0] upos [0:MAXU-1];     // next expected position (SOURCE: the in-flight step)
    reg          wslot;               // VM slot of the next accepted HIDDEN job (mirrors the sequencer's slot)

    // ---- inbound FSM ----
    localparam [1:0] R_IDLE = 2'd0, R_DATA = 2'd1, R_SIDE = 2'd2, R_SKIP = 2'd3;
    reg [1:0]       rx_st;
    reg [11:0]      rx_j;
    reg             rx_slot;
    reg [USER_W-1:0] side_user;
    reg [15:0]      side_addr;
    reg [SH_LENW-1:0] side_len;

    // ---- SOURCE: reduction, feedback, scheduling ----
    reg             res_v, res_stop;
    reg [USER_W-1:0] res_u;
    reg [NW-1:0]    res_p, res_i;
    reg [NW-1:0]    ptok [0:MAXU-1];
    reg [2:0] ptype [0:MAXU-1];
    reg [7:0]       next_u;
    reg             nu_ok, nu_pend;
    reg [NW-1:0]    nu_tok;
    reg [2:0] nu_type;
    reg [1:0]       pr_t0, pr_t1;
    reg [7:0]       pr_u0, pr_u1;
    reg [USER_W-1:0] jq_u [0:MAXU-1];
    reg [NW-1:0]    jq_p [0:MAXU-1], jq_t [0:MAXU-1];
    reg [2:0] jq_type [0:MAXU-1];
    reg [UB-1:0]    jq_w, jq_r;
    reg [UB:0]      jq_n;
    // the registered RESULT
    wire [NW:0]     nxt_pos   = {1'b0, res_p} + 1'b1;
    wire            generated = nxt_pos >= {1'b0, cfg_prompt_len};
    wire            stop_hd   = (MUT == 1) ? 1'b0 : (res_stop && generated);
    wire            stop_ml   = (MUT == 1) ? 1'b0 : (nxt_pos >= cfg_max_len);
    wire            in_gen    = nxt_pos < ({1'b0, cfg_prompt_len} + {1'b0, cfg_gen_len} - 1'b1);
    wire            fb_v      = SOURCE && res_v;
    wire            fb_cont   = in_gen && !stop_hd && !stop_ml;
    wire [NW-1:0]   fb_tok    = (nxt_pos < {1'b0, cfg_prompt_len}) ? ptok[res_u[UB-1:0]] : res_i;
    wire [2:0] fb_type=(TOKEN_TYPES && nxt_pos<{1'b0,cfg_prompt_len})?ptype[res_u[UB-1:0]]:3'd7;

    reg  rx_hdr_h, rx_hdr_s, rx_hdr_r, rx_bad;
    reg  st_new, st_q, st_fb;
    always @(*) begin
        in_ready = 1'b0; rx_hdr_h = 1'b0; rx_hdr_s = 1'b0; rx_hdr_r = 1'b0; rx_bad = 1'b0;
        vm_we = 1'b0; vm_waddr = 0;
        job_v = 1'b0; job_user = 0; job_pos = 0; job_tok = 0;
        job_win_v=0;job_win_ids=0;job_win_dead=0;
        job_token_type=3'd7;
        st_new = 1'b0; st_q = 1'b0; st_fb = 1'b0;
        case (rx_st)
            R_IDLE: begin
                if (in_type == MT_HIDDEN && !SOURCE) begin
                    in_ready = window_bad ? 1'b1 : job_rdy;
                    rx_hdr_h = in_valid && job_rdy && !window_bad;
                    rx_bad = in_valid && window_bad;
                end else if (in_type == MT_SIDE) begin
                    in_ready = 1'b1; rx_hdr_s = in_valid;
                end else if (in_type == MT_RESULT && SOURCE) begin
                    in_ready = 1'b1; rx_hdr_r = in_valid;
                end else begin
                    in_ready = 1'b1; rx_bad = in_valid;
                end
            end
            R_DATA: begin
                in_ready = 1'b1;
                vm_we = in_valid;
                vm_waddr = VWA'(RXB) + (rx_slot ? VWA'(RXW) : {VWA{1'b0}}) + VWA'(rx_j);
            end
            R_SIDE: begin
                in_ready = 1'b1;
                vm_we = in_valid && side_user < MAXU &&
                        ({4'b0, side_addr} + rx_j + 1 <= 20'(1 << SIDE_USH));
                vm_waddr = VWA'(SIDE_BASE) + (VWA'(side_user) << SIDE_USH) + VWA'(side_addr) + VWA'(rx_j);
            end
            default: in_ready = 1'b1;        // R_SKIP: drain a refused message
        endcase
        if (rx_hdr_h) begin
            job_v = 1'b1; job_user = in_user; job_pos = in_pos; job_tok = in_data[SH_TOK +: NW];
            if(WINDOW_CONTEXT) begin
                job_win_v=in_data[276];job_win_ids=in_data[208 +:68];job_win_dead=in_data[277];
            end
        end
        if (SOURCE && job_rdy && boot_ok) begin
            if (nu_ok && next_u < cfg_users && next_u < MAXU) st_new = 1'b1;
            else if (jq_n != 0) st_q = 1'b1;
            else if (fb_v && fb_cont) st_fb = 1'b1;
            if (st_new) begin job_v = 1'b1; job_user = USER_W'(next_u); job_pos = 0; job_tok = nu_tok; end
            if (st_q)   begin job_v = 1'b1; job_user = jq_u[jq_r]; job_pos = jq_p[jq_r]; job_tok = jq_t[jq_r]; end
            if (st_fb)  begin job_v = 1'b1; job_user = res_u; job_pos = res_p + 1'b1; job_tok = fb_tok; end
            if(TOKEN_TYPES) begin
                if(st_new) job_token_type=nu_type;
                if(st_q) job_token_type=jq_type[jq_r];
                if(st_fb) job_token_type=fb_type;
            end
        end
    end

    task automatic flt(input [3:0] c);
        begin proto_fault <= 1'b1; if (fault_code == 4'd0) fault_code <= c; end
    endtask

    integer u;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_st <= R_IDLE; rx_j <= 0; rx_slot <= 1'b0; wslot <= 1'b0;
            side_user <= 0; side_addr <= 0; side_len <= 0;
            run_eosen <= 1'b0; run_eos <= 0; run_maxl <= 0;
            res_v <= 1'b0; res_stop <= 1'b0; res_u <= 0; res_p <= 0; res_i <= 0;
            next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; nu_tok <= 0;nu_type<=3'd7;
            pr_t0 <= 0; pr_t1 <= 0; pr_u0 <= 0; pr_u1 <= 0; pr_re <= 1'b0; pr_user <= 0; pr_pos <= 0;
            jq_w <= 0; jq_r <= 0; jq_n <= 0;
            tok_valid <= 1'b0; tok_user <= 0; tok_pos <= 0; tok_id <= 0; tok_stop <= 1'b0; users_done <= 0;
            st_jobs_done <= 0; proto_fault <= 1'b0; fault_code <= 4'd0;
            for (u = 0; u < MAXU; u = u + 1) begin upos[u] <= 0; ptok[u] <= 0; end
        end else begin
            tok_valid <= 1'b0;
            pr_re <= 1'b0;
            if (job_done) st_jobs_done <= st_jobs_done + 1;
            // ---- inbound ----
            if (rx_hdr_h) begin
                if (in_last || in_len != SH_LENW'(RXW)) flt(4'd3);
                if (in_user >= MAXU) flt(4'd2);
                else begin
                    if (upos[in_user[UB-1:0]] != in_pos && in_pos != 0) flt(4'd1);   // 0: a new request restarts
                    upos[in_user[UB-1:0]] <= in_pos + 1'b1;
                end
                run_eosen <= in_data[SH_EOSEN]; run_eos <= in_data[SH_EOS +: NW]; run_maxl <= in_data[SH_MAXL +: NW+1];
                rx_slot <= wslot; wslot <= ~wslot;
                rx_j <= 0; rx_st <= in_last ? R_IDLE : R_DATA;
            end
            if (rx_st == R_DATA && in_valid) begin
                if (in_last != (rx_j == 12'(RXW - 1))) flt(4'd3);
                rx_j <= rx_j + 1'b1;
                if (in_last) rx_st <= R_IDLE;
            end
            if (rx_hdr_s) begin
                if (in_last || in_data[SH_USER +: USER_W] >= MAXU) flt(4'd2);
                if ({4'b0, in_data[SH_ADDR +: 16]} + in_data[SH_LEN +: SH_LENW] > 20'(1 << SIDE_USH)) flt(4'd6);
                side_user <= in_user; side_addr <= in_data[SH_ADDR +: 16]; side_len <= in_len;
                rx_j <= 0; rx_st <= in_last ? R_IDLE : R_SIDE;
            end
            if (rx_st == R_SIDE && in_valid) begin
                if (in_last != (rx_j == 12'(side_len) - 1'b1)) flt(4'd3);
                rx_j <= rx_j + 1'b1;
                if (in_last) rx_st <= R_IDLE;
            end
            if (rx_bad) begin
                flt((in_type == MT_HIDDEN) ? (window_bad ? 4'd9 : 4'd5) : 4'd4);
                rx_st <= in_last ? R_IDLE : R_SKIP;
            end
            if (rx_st == R_SKIP && in_valid && in_last) rx_st <= R_IDLE;
            res_v <= 1'b0;
            if (rx_hdr_r) begin
                if (!in_last || in_user >= MAXU) flt(4'd4);
                res_v <= in_user < MAXU; res_u <= in_user; res_p <= in_pos;
                res_i <= in_data[SH_IDX +: NW]; res_stop <= in_data[SH_STOP];
            end
            // ---- SOURCE ----
            if (SOURCE) begin
                if (st_new || st_q || st_fb) wslot <= ~wslot;      // the sequencer takes a slot for this job
                if (res_v) begin
                    if (res_p != upos[res_u[UB-1:0]]) flt(4'd4);
                    tok_valid <= 1'b1; tok_user <= 8'(res_u); tok_pos <= res_p; tok_id <= res_i;
                    tok_stop <= !fb_cont;
                    if (!fb_cont) users_done <= users_done + 1'b1;
                end
                if (fb_v && fb_cont && !st_fb) begin
                    jq_u[jq_w] <= res_u; jq_p[jq_w] <= res_p + 1'b1; jq_t[jq_w] <= fb_tok;
                    if(TOKEN_TYPES) jq_type[jq_w]<=fb_type;
                    jq_w <= (jq_w == UB'(MAXU - 1)) ? {UB{1'b0}} : jq_w + 1'b1;
                end
                if (st_q) jq_r <= (jq_r == UB'(MAXU - 1)) ? {UB{1'b0}} : jq_r + 1'b1;
                jq_n <= jq_n + ((fb_v && fb_cont && !st_fb) ? 1'b1 : 1'b0) - (st_q ? 1'b1 : 1'b0);
                if (st_new || st_q || st_fb) begin
                    upos[job_user[UB-1:0]] <= job_pos;
                    pr_re <= 1'b1; pr_user <= 8'(job_user); pr_pos <= job_pos + 1'b1; pr_t0 <= 2; pr_u0 <= 8'(job_user);
                    if (st_new) begin next_u <= next_u + 1'b1; nu_ok <= 1'b0; end
                end else if (!nu_ok && !nu_pend && next_u < cfg_users && next_u < MAXU) begin
                    pr_re <= 1'b1; pr_user <= next_u; pr_pos <= 0; pr_t0 <= 1; nu_pend <= 1'b1;
                end else begin
                    pr_t0 <= 0;
                end
                pr_t1 <= pr_t0; pr_u1 <= pr_u0;
                if (pr_t1 == 1) begin nu_tok <= pr_q; nu_ok <= 1'b1; nu_pend <= 1'b0; end
                if (pr_t1 == 2) ptok[pr_u1[UB-1:0]] <= pr_q;
                if(TOKEN_TYPES && pr_t1==1) nu_type<=pr_token_type;
                if(TOKEN_TYPES && pr_t1==2) ptype[pr_u1[UB-1:0]]<=pr_token_type;
                if (cfg_users > MAXU) flt(4'd7);
                // a new run (cfg_users returns to 0 between runs): clear the user scheduler
                if (cfg_users == 0) begin next_u <= 0; nu_ok <= 1'b0; nu_pend <= 1'b0; users_done <= 0; end
                run_eosen <= cfg_eos_en; run_eos <= cfg_eos_id; run_maxl <= cfg_max_len;
            end
        end
    end
endmodule
