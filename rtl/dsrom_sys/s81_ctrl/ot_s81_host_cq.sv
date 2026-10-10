`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_s81_host_cq (stream ds-control, 2026-10-08): the S81 successor of ot_dsrom_host_cq (pinned, unchanged), placed
// with the SOURCE controller on the stage-0 (embedding) die.  Changes, everything else as the original below:
//   * NW = 21 (1M positions, 129,280-entry vocabulary);
//   * CMD_CFG (op 3) {user[0] = EOS enable, pos = maximum sequence length (0 = 2^NW), token = EOS id}: the stop
//     configuration of the NEXT run (cfg_eos_en / cfg_eos_id / cfg_max_len, latched at LAUNCH and held for the run;
//     the SOURCE forwards it in every HIDDEN header to the head die's sampler, ot_s81_stop);
//   * LAUNCH is refused (ERROR, cause R_MAXLEN 7) when prompt_len > max_len, and (cause R_BOOT 8) while boot_ok = 0:
//     the boot tables (HBM RoPE table, ot_s81_boot_seq) are not loaded and verified;
//   * a run may end early (EOS / max_len): the controller counts a stopped user in users_done, so DONE is posted
//     when every user has stopped; the completion reservation keeps the gen_len bound (never exceeded).
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// ot_dsrom_host_cq -- host command / completion queue of the DeepSeek-V4.1 ROM
// array (gap X5/R1 of /tmp/claude-review-20261003/rombridge: "start ready,
// tagged done {cmd_tag,user,pos}, tok_valid ready, hardware progress watchdog
// with exported cause").  New module, default-off by construction: no existing
// bench instantiates it; the system top (rtl/test/dsrom_sys/tb_dsrom_system.sv)
// binds it to the SOURCE package controller (ot_rom_pkg_ctrl_x) instead of the
// bench-held prompt array and run configuration.
//
// Host side (valid/ready, one command a cycle):
//   CMD_PROMPT  {user, pos, token}: write one prompt token into the prompt
//               store (MAXU x PMAX words).  Address-bound checked: a write
//               outside the store is refused with an ERROR completion.
//   CMD_LAUNCH  {tag, users, prompt_len, gen_len}: start a run.  Admitted only
//               when (a) no run is active, (b) every user < users has
//               prompt_len prompt tokens written, (c) the completion queue has
//               room for EVERY completion the run can produce
//               (users * (prompt_len + gen_len - 1) TOKEN entries + 1 DONE).
//               The reservation is what makes the token path lossless: the
//               package controller's tok_valid has no ready, so space is
//               reserved before the run starts instead of back-pressuring a
//               token that is already reduced.  A refused LAUNCH returns an
//               ERROR completion with the reason; the command port never
//               blocks forever.
// Device side: cfg_users/cfg_prompt_len/cfg_gen_len are held 0 until a LAUNCH
//   is admitted (the controller issues nothing while cfg_users = 0) and stable
//   for the whole run; the controller's synchronous prompt read port is served
//   from the store (a read at pos >= prompt_len is the controller's speculative
//   prefetch and returns 0, counted; a read for user >= users faults).
// Completions (valid/ready to the host, FIFO of CQ_DEPTH entries):
//   {kind[1:0], tag[TAGW-1:0], user[7:0], pos[NW-1:0], token[NW-1:0], stamp[31:0]}
//   kind 1 TOKEN (every reduced token: prompt positions and generated ones),
//   kind 2 DONE  (the run's users_done reached users),
//   kind 3 ERROR (refused command, identity fault, watchdog; token = cause).
//   Identity: every TOKEN must carry the user's next expected position, else
//   fault (a duplicate or skipped completion is never silent).
// Watchdog: while a run is active, a counter of cycles since the last TOKEN;
//   at WDOG cycles it latches `wdog`, captures `stall_cause` (the OR of the
//   packages' exported stall snapshots, ot_dsrom_stall_export) into
//   wdog_cause, and posts an ERROR completion (a reserved slot is kept for
//   it).
// ---------------------------------------------------------------------------
module ot_s81_host_cq #(
    parameter integer MAXU     = 16,
    parameter integer PMAX     = 8,       // prompt tokens stored per user
    parameter integer NW       = 16,
    parameter integer TAGW     = 8,
    parameter integer CQ_DEPTH = 64,
    parameter integer CAUSEW   = 32,
    parameter integer WDOG     = 2000000, // cycles without a TOKEN while active
    parameter integer UCW      = 8        // cfg_users width of the controller
) (
    input  wire                clk,
    input  wire                rst_n,
    // host command port
    input  wire                cmd_valid,
    output wire                cmd_ready,
    input  wire [1:0]          cmd_op,      // 1 PROMPT, 2 LAUNCH
    input  wire [TAGW-1:0]     cmd_tag,
    input  wire [7:0]          cmd_user,    // PROMPT: user; LAUNCH: users
    input  wire [NW-1:0]       cmd_pos,     // PROMPT: pos;  LAUNCH: prompt_len
    input  wire [NW-1:0]       cmd_token,   // PROMPT: token; LAUNCH: gen_len
    // host completion port
    output wire                cpl_valid,
    input  wire                cpl_ready,
    output wire [2+TAGW+8+NW+NW+32-1:0] cpl_data,
    // device: run configuration and prompt read port of the SOURCE controller
    output reg  [UCW-1:0]      cfg_users,
    output reg  [NW-1:0]       cfg_prompt_len,
    output reg  [NW-1:0]       cfg_gen_len,
    output reg  [NW:0]         cfg_max_len,
    output reg                 cfg_eos_en,
    output reg  [NW-1:0]       cfg_eos_id,
    input  wire                boot_ok,
    input  wire                pr_re,
    input  wire [7:0]          pr_user,
    input  wire [NW-1:0]       pr_pos,
    output reg  [NW-1:0]       pr_q,
    // device: reduced tokens and run completion
    input  wire                tok_valid,
    input  wire [7:0]          tok_user,
    input  wire [NW-1:0]       tok_pos,
    input  wire [NW-1:0]       tok_id,
    input  wire [UCW-1:0]      users_done,
    // watchdog cause input and status
    input  wire [CAUSEW-1:0]   stall_cause,
    output reg                 active,
    output reg                 wdog,
    output reg  [CAUSEW-1:0]   wdog_cause,
    output reg                 fault,
    output reg  [3:0]          fault_code,
    output reg  [31:0]         st_tokens,
    output reg  [31:0]         st_spec_reads,
    output reg  [31:0]         st_cpl_stall,
    output reg  [31:0]         st_cq_high
);
    localparam [1:0] OP_PROMPT = 2'd1, OP_LAUNCH = 2'd2, OP_CFG = 2'd3;
    localparam [1:0] K_TOKEN = 2'd1, K_DONE = 2'd2, K_ERROR = 2'd3;
    localparam integer CW = 2 + TAGW + 8 + NW + NW + 32;
    localparam integer QB = $clog2(CQ_DEPTH);
    localparam [3:0] F_NONE = 0, F_OVERFLOW = 1, F_PR_USER = 2, F_TOK_ID = 3, F_TOK_IDLE = 4, F_WDOG = 5;
    // refusal causes carried in the ERROR completion's token field
    localparam [NW-1:0] R_BOUND = 1, R_ACTIVE = 2, R_PROMPT = 3, R_SPACE = 4, R_OP = 5, R_ZERO = 6, R_MAXLEN = 7, R_BOOT = 8;
    reg [NW:0] nx_max_len; reg nx_eos_en; reg [NW-1:0] nx_eos_id;      // CMD_CFG, applied at the next LAUNCH

    `ifndef SYNTHESIS
    initial if (MAXU > 256 || PMAX < 1 || CQ_DEPTH < 4 || (1 << QB) != CQ_DEPTH)
        $fatal(1, "ot_s81_host_cq: MAXU<=256, PMAX>=1, CQ_DEPTH a power of two >= 4");
`endif

    // -- prompt store and per-user written counts -------------------------------------
    reg [NW-1:0] pmem [0:MAXU*PMAX-1];
    reg [PMAX-1:0] pwritten [0:MAXU-1];
    reg [NW-1:0] exp_pos [0:MAXU-1];      // next expected TOKEN position per user
    reg [TAGW-1:0] run_tag;

    // -- completion FIFO ----------------------------------------------------------------
    reg [CW-1:0] cq [0:CQ_DEPTH-1];
    reg [QB-1:0] cq_w, cq_r;
    reg [QB:0]   cq_n;
    reg [QB+NW+8:0] reserved;             // entries reserved by the active run, not yet pushed
    assign cpl_valid = (cq_n != 0);
    assign cpl_data  = cq[cq_r];
    wire cq_pop = cpl_valid && cpl_ready;

    // -- command decode -----------------------------------------------------------------
    // One push source a cycle has priority order TOKEN > DONE > WDOG ERROR > command
    // ERROR; the command port is ready only when the command's own completion (if
    // any) can be pushed this cycle, i.e. no device-side push this cycle and room.
    reg [31:0] stamp;
    reg [31:0] since_tok;
    reg done_posted;
    reg wdog_post_pending;
    wire dev_push = tok_valid || (active && !done_posted && users_done == cfg_users && cfg_users != 0);
    wire [QB:0] free_now = CQ_DEPTH - cq_n;
    // a refused/acknowledged command needs one free slot beyond the run's reservation
    assign cmd_ready = !dev_push && !(active && wdog_post_pending) && (free_now > reserved);
    wire cmd_go = cmd_valid && cmd_ready;

    // admission check for LAUNCH
    reg  prompts_ok;
    integer ui;
    always @(*) begin
        prompts_ok = 1'b1;
        for (ui = 0; ui < MAXU; ui = ui + 1)
            if (ui < cmd_user)
                if (cmd_pos == 0 || cmd_pos > PMAX ||
                    (pwritten[ui] & ((cmd_pos >= PMAX) ? {PMAX{1'b1}} : ((PMAX'(1) << cmd_pos) - 1'b1)))
                    != ((cmd_pos >= PMAX) ? {PMAX{1'b1}} : ((PMAX'(1) << cmd_pos) - 1'b1)))
                    prompts_ok = 1'b0;
    end
    // completions a run produces: users * (prompt_len + gen_len - 1) TOKENs + 1 DONE + 1 spare for WDOG
    wire [QB+NW+8:0] need = cmd_user * (cmd_pos + cmd_token - 1'b1) + 2;

    function automatic [CW-1:0] cpl(input [1:0] k, input [TAGW-1:0] t, input [7:0] u, input [NW-1:0] p,
                                    input [NW-1:0] tk, input [31:0] s);
        cpl = {k, t, u, p, tk, s};
    endfunction

    integer i;
    reg [CW-1:0] push_d;
    reg          push_v;
    reg          push_rsv;                // the push consumes a reserved slot
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cq_w <= 0; cq_r <= 0; cq_n <= 0; reserved <= 0;
            cfg_users <= 0; cfg_prompt_len <= 0; cfg_gen_len <= 0;
            cfg_max_len <= 0; cfg_eos_en <= 1'b0; cfg_eos_id <= 0;
            nx_max_len <= {1'b1, {NW{1'b0}}}; nx_eos_en <= 1'b0; nx_eos_id <= 0;
            active <= 1'b0; wdog <= 1'b0; wdog_cause <= 0; fault <= 1'b0; fault_code <= F_NONE;
            st_tokens <= 0; st_spec_reads <= 0; st_cpl_stall <= 0; st_cq_high <= 0;
            stamp <= 0; since_tok <= 0; done_posted <= 1'b0; run_tag <= 0; pr_q <= 0;
            wdog_post_pending <= 1'b0;
            for (i = 0; i < MAXU; i = i + 1) begin pwritten[i] <= 0; exp_pos[i] <= 0; end
        end else begin
            stamp <= stamp + 1;
            push_v = 1'b0; push_rsv = 1'b0; push_d = 0;
            // ---- device-side pushes (reserved slots) ----
            if (tok_valid) begin
                push_v = 1'b1; push_rsv = 1'b1;
                push_d = cpl(K_TOKEN, run_tag, tok_user, tok_pos, tok_id, stamp);
                st_tokens <= st_tokens + 1;
                since_tok <= 0;
                if (!active) begin fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_TOK_IDLE; end
                else if (tok_user >= cfg_users || tok_pos != exp_pos[tok_user[$clog2(MAXU>1?MAXU:2)-1:0]]) begin
                    fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_TOK_ID;
                end else exp_pos[tok_user[$clog2(MAXU>1?MAXU:2)-1:0]] <= tok_pos + 1'b1;
            end else if (active && !done_posted && users_done == cfg_users && cfg_users != 0) begin
                push_v = 1'b1; push_rsv = 1'b1;
                push_d = cpl(K_DONE, run_tag, 8'(users_done), 0, 0, stamp);
                done_posted <= 1'b1;
            end else if (wdog_post_pending) begin
                push_v = 1'b1; push_rsv = 1'b1;
                push_d = cpl(K_ERROR, run_tag, 8'hFF, 0, NW'(F_WDOG), stamp);
                wdog_post_pending <= 1'b0;
            end else if (cmd_go) begin
                // ---- host commands ----
                case (cmd_op)
                    OP_PROMPT: begin
                        if (cmd_user >= MAXU || cmd_pos >= PMAX) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, cmd_pos, R_BOUND, stamp);
                        end else begin
                            pmem[cmd_user * PMAX + cmd_pos] <= cmd_token;
                            pwritten[cmd_user][cmd_pos] <= 1'b1;
                        end
                    end
                    OP_LAUNCH: begin
                        if (active) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_ACTIVE, stamp);
                        end else if (cmd_user == 0 || cmd_user > MAXU || cmd_pos == 0 || cmd_token == 0) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_ZERO, stamp);
                        end else if (!boot_ok) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_BOOT, stamp);
                        end else if ({1'b0, cmd_pos} > nx_max_len) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_MAXLEN, stamp);
                        end else if (!prompts_ok) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_PROMPT, stamp);
`ifndef DSROM_CQ_MUTANT_NORSV
                        end else if (need > free_now) begin
`else
                        end else if (1'b0) begin                    // mutant: no completion reservation
`endif
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_SPACE, stamp);
                        end else begin
                            active <= 1'b1; run_tag <= cmd_tag; done_posted <= 1'b0; since_tok <= 0;
                            cfg_users <= UCW'(cmd_user); cfg_prompt_len <= cmd_pos; cfg_gen_len <= cmd_token;
                            cfg_max_len <= nx_max_len; cfg_eos_en <= nx_eos_en; cfg_eos_id <= nx_eos_id;
                            reserved <= need;
                            for (i = 0; i < MAXU; i = i + 1) exp_pos[i] <= 0;
                        end
                    end
                    OP_CFG: begin
                        if (active) begin
                            push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_ACTIVE, stamp);
                        end else begin
                            nx_eos_en <= cmd_user[0]; nx_eos_id <= cmd_token;
                            nx_max_len <= (cmd_pos == 0) ? {1'b1, {NW{1'b0}}} : {1'b0, cmd_pos};
                        end
                    end
                    default: begin
                        push_v = 1'b1; push_d = cpl(K_ERROR, cmd_tag, cmd_user, 0, R_OP, stamp);
                    end
                endcase
            end
            // ---- FIFO ----
            if (push_v) begin
                if (cq_n == CQ_DEPTH && !cq_pop) begin
                    fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_OVERFLOW;
                end else begin
                    cq[cq_w] <= push_d; cq_w <= cq_w + 1'b1;
                end
            end
            if (push_rsv) begin
                if (reserved == 0) begin fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_OVERFLOW; end
                else reserved <= reserved - 1'b1;
            end
            if (cq_pop) cq_r <= cq_r + 1'b1;
            cq_n <= cq_n + (push_v && !(cq_n == CQ_DEPTH && !cq_pop) ? 1 : 0) - (cq_pop ? 1 : 0);
            if (cq_n > st_cq_high[QB:0]) st_cq_high <= cq_n;
            if (cpl_valid && !cpl_ready) st_cpl_stall <= st_cpl_stall + 1;
            // ---- run end: DONE posted and drained of reserved WDOG spare ----
            if (active && done_posted && !tok_valid && !wdog_post_pending) begin
                active <= 1'b0; cfg_users <= 0; reserved <= 0;   // releases the spare WDOG slot
            end
            // ---- watchdog ----
            if (active && !done_posted && !tok_valid) begin
                if (since_tok != 32'hFFFFFFFF) since_tok <= since_tok + 1;
                if (since_tok == WDOG - 1 && !wdog) begin
                    wdog <= 1'b1; wdog_cause <= stall_cause; wdog_post_pending <= 1'b1;
                    fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_WDOG;
                end
            end
            // ---- prompt read port (synchronous, as the bench memory it replaces) ----
            if (pr_re) begin
                if (pr_user >= cfg_users || pr_user >= MAXU) begin
                    pr_q <= 0;
                    fault <= 1'b1; if (fault_code == F_NONE) fault_code <= F_PR_USER;
                end else if (pr_pos >= cfg_prompt_len || pr_pos >= PMAX) begin
                    pr_q <= 0; st_spec_reads <= st_spec_reads + 1;
                end else pr_q <= pmem[pr_user * PMAX + pr_pos];
            end
        end
    end
endmodule
