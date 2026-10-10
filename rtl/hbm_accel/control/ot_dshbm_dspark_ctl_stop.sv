// Additive native full-context stop-aware controller. Historical source unchanged.
// STOP_EN gates altered EOS/length committed-state semantics, mirrored by a separate stop-aware reference.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DSpark speculative decode control loop of the V4.1 HBM comparator (default-off build).
//
// The loop a GPU runtime runs for V4.1's built-in MTP (DSpark: mtp.0-2 are ONE block
// drafter), as one persistent control kernel issuing the SM cluster's passes.  It
// reproduces tools/hdc_golden_v41.py Model.generate_spec step for step:
//
//   prefill   one position a pass: tokens written to the history ring, the 40 layers
//             (VLAYER, 1 column), the head (VHEAD -> argmax), the DSpark seed (SEED:
//             each DSpark stage's window row of the position), n <- p + 1;
//             y <- argmax of the last position; emit y;
//   step      q = n - 1, g = min(gamma, MAXPOS - 2 - q) (positions stay < max_seq_len);
//     draft   (g > 0) DSTAGE 0..NST-1 over the block [y, noise x (B-1)] at anchor q
//             (the engine's draft stages: B MMA columns, the DSpark window gathered in
//             ring-slot order from the spec-state rings), DHEAD (the shared LM head on
//             the B block rows), then g serial MARKOV steps: the engine streams block
//             row i's logits with the Markov head's bias for d_i (d_0 = y) through the
//             argmax epilogue -> d_{i+1};  (cfg_force: the g drafts come from the host
//             instead -- a bench drafter that exercises every accept length);
//     verify  y, d_1 .. d_g written to the history ring at n .. n+g; VLAYER 0..NL-1
//             with g+1 columns (layer-major: one weight pass serves every position; the
//             routed experts are the union of the positions' selections), VHEAD (g+1
//             argmaxes -> t_0 .. t_g), SEED (g+1 DSpark rows);
//     accept  a = longest prefix with d_{i+1} == t_i (ot_hdc_accept, the core-agnostic
//             greedy accept unit); emit t_0 .. t_a (cap cfg_ngen);
//     commit  n <- n + 1 + a (= q + 2 + a): the ONLY rollback action -- every rejected
//             row lies at a position >= n and the spec-state rings are sized so no read
//             reaches it (ot_dshbm_spec_state); y <- t_a.
//
// MUT (bench mutations, must be DETECTED): 1 commit one position too many (n + 2 + a),
// 2 next pending token t_{a+1} instead of t_a, 3 accept ignores the last draft's match.
// ---------------------------------------------------------------------------
module ot_dshbm_dspark_ctl_stop #(
    parameter integer STOP_EN = 0, CW = 21, PW = 20, FW = 23, PRL = 0,
    parameter integer B      = 5,
    parameter integer PMAX   = 8,
    parameter integer TW     = 17,
    parameter integer NL     = 40,
    parameter integer NST    = 3,
    parameter integer MAXPOS = 1048576,
    parameter integer MUT    = 0,
    parameter integer NREG   = 1,          // mtp-lead 2026-10-09 (hfd-mtp x-stop hm0 TT -76.8, SS -506: spec-state n ->
                                           //   q/room/g_new -> S_STEP issue enables, 23-24 levels): q, g_new and the
                                           //   stop-room (maxpos - n) come from registers; S_STEP waits one cycle after an
                                           //   n_set (+1 cycle per MTP step). 0 = the original combinational form.
    parameter integer ACCEPT_LEAF = 0,     // 0: ot_hdc_accept, 1: Codex's protected DS MTP accept leaf
    parameter integer FAST   = 0           // 1: 1.2 GHz SS successor: keep-prefix observation counters and an
                                           //    incrementally kept forced-draft address (same values, same cycles)
) (
    input  wire               clk,
    input  wire               rst_n,
    // host
    input  wire               start,
    input  wire [3:0]         cfg_gamma,
    input  wire               cfg_force,
    input  wire [CW-1:0]      cfg_ngen,
    input  wire [CW-1:0]      cfg_plen,
    output wire [PW-1:0]      p_addr,
    input  wire [TW-1:0]      p_tok,
    output wire [FW-1:0]      f_addr,
    input  wire [TW-1:0]      f_tok,
    output reg                e_v,
    output reg  [TW-1:0]      e_tok,
    output reg  [PW-1:0]      e_idx,
    input wire e_ready, cfg_eos_en,
    input wire [TW-1:0] cfg_eos,
    input wire [PW:0] cfg_maxpos,
    output reg [2:0] stop_status,
    output reg                done,
    // engine (the SM cluster's pass sequencer)
    output reg                cmd_v,
    input  wire               cmd_ready,
    output reg  [3:0]         cmd_op,
    output reg  [7:0]         cmd_idx,
    output reg  [3:0]         cmd_ncol,
    output reg  [31:0]        cmd_pos,
    output reg  [TW-1:0]      cmd_tok1,
    output wire [PMAX*TW-1:0] cmd_toks,
    input  wire               eng_done,
    // argmax epilogue results (row order)
    input  wire               am_v,
    input  wire [TW-1:0]      am_idx,
    // spec state
    input  wire [31:0]        n,
    output reg                n_set,
    output reg  [31:0]        n_val,
    output reg                tw_v,
    output reg  [31:0]        tw_pos,
    output reg  [TW-1:0]      tw_tok,
    // observation
    output reg                step_v,         // a step committed (acc_a / g valid)
    output wire [2:0]         step_a,
    output reg  [3:0]         step_g,
    output reg  [CW-1:0]      steps,
    output reg  [31:0]        cyc_total,
    output reg  [31:0]        cyc_engine,     // cycles a command was outstanding at the engine
    output reg  [31:0]        cyc_markov      // cycles inside MARKOV commands (serial draft tail)
);
    localparam [3:0] C_VLAYER = 0, C_VHEAD = 1, C_SEED = 2, C_DSTAGE = 3, C_DHEAD = 4, C_MARKOV = 5;
    localparam [4:0] S_IDLE = 0, S_PF_TOK = 1, S_ISSUE = 2, S_WAIT = 3, S_AFTER = 4, S_STEP = 5, S_FLOAD = 6,
                     S_VTOK = 7, S_ACC = 8, S_ACCW = 9, S_EMIT = 10, S_COMMIT = 11, S_DONE = 12, S_PF_EMIT = 13, S_CWAIT = 14, S_PF_ACK = 15, S_EMIT_ACK = 16;
    localparam integer SLW = $clog2(PMAX);
    reg [4:0]  s;
    reg        pf;                       // prefill pass
    reg [PW-1:0] pp;                       // prefill position
    reg [TW-1:0] y;
    reg [TW-1:0] d [0:PMAX-1];           // drafts d_1 .. d_g at d[0 .. g-1]
    reg [3:0]  g;
    reg [3:0]  j;
    reg [CW-1:0] emitted;
    reg [3:0]  am_need, am_got;
    reg        done_seen;
    reg [TW-1:0] t_last;
    // accept unit
    reg  acc_start, acc_tokx, acc_amax, acc_go;
    reg  [SLW-1:0] tokx_slot, amax_slot;
    reg  [TW-1:0]  tokx_tok, amax_tok;
    wire [PMAX*TW-1:0] stok, ttok;
    wire acc_done, acc_any;
    wire [SLW-1:0] acc_a;
    wire [SLW:0]   n_emit;
    wire [TW-1:0]  bonus;
    reg  acc_rel;
    wire acc_fault;
    ot_dshbm_accept_port #(.LEAF(ACCEPT_LEAF), .TW(TW)) u_acc (
        .clk(clk), .rst_n(rst_n), .start_v(acc_start), .start_pos(n), .start_tok(y), .start_g(g[2:0]),
        .tokx_v(acc_tokx), .tokx_slot(tokx_slot), .tokx_tok(tokx_tok),
        .amax_v(acc_amax), .amax_slot(amax_slot), .amax_tok(amax_tok),
        .acc_v(acc_go), .acc_g((MUT == 3 && g > 0) ? g[2:0] - 1'b1 : g[2:0]), .release_v(acc_rel),
        .acc_done(acc_done), .acc_a(acc_a), .bonus(bonus), .ttok(ttok), .fault(acc_fault));
    reg [2:0] effective_n;
    reg [TW-1:0] effective_bonus;
    reg stop_latched;
    assign step_a = STOP_EN ? (effective_n - 1'b1) : acc_a;
    // the pass's tokens: column 0 = y, column c = d_c
    genvar gc;
    generate
        for (gc = 0; gc < PMAX; gc = gc + 1) begin : g_ct
            if (gc == 0) assign cmd_toks[0 +: TW] = pf ? p_tok : y;
            else assign cmd_toks[gc*TW +: TW] = (gc <= g) ? d[gc-1] : {TW{1'b0}};
        end
    endgenerate
    assign p_addr = pp;
    generate if (FAST == 0) begin : g_fa0
        assign f_addr = steps * B + j;
    end else begin : g_fa1
        // fbase = steps * B (mod 2^16), kept with steps: no multiplier on the port
        reg [FW-1:0] fbase;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) fbase <= 0;
            else if (s == S_IDLE && start) fbase <= 0;
            else if (s == S_COMMIT) fbase <= fbase + B;
        // ctl_f1 SS output miss was this mapped ripple, not the counters.
        // Existing keep-prefix adder preserves the W16 modulo result/cycle.
        ot_hdc_ksadd_k #(.W(FW)) u_faddr (
            .a(fbase), .b({{(FW-4){1'b0}}, j}), .cin(1'b0), .s(f_addr), .cout());
    end endgenerate
    wire [31:0] q = n - 1;
    wire [31:0] context_limit = (STOP_EN && MUT!=2) ? {{(31-PW){1'b0}},cfg_maxpos} : MAXPOS;
    wire [31:0] room = (context_limit >= 2 && context_limit - 2 > q) ? context_limit - 2 - q : 0;
    wire [3:0]  g_new = (room < cfg_gamma) ? room[3:0] : cfg_gamma;
    // NREG: n-derived values from registers. n changes only on the edge that ends an n_set cycle, so a value
    // registered from n is current in cycle X iff n_set was low in X-1 (nd_ok).
    wire [31:0] mp32 = {{(31-PW){1'b0}},cfg_maxpos};
    reg  [31:0] q_r, rem_r;
    reg  [3:0]  g_new_r;
    reg         n_set_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin q_r <= 0; rem_r <= 0; g_new_r <= 0; n_set_d <= 1'b0; end
        else begin
            q_r <= q; g_new_r <= g_new; n_set_d <= n_set;
            rem_r <= (n >= mp32) ? 32'd0 : mp32 - n;
        end
    wire        nd_ok   = !n_set_d;
    wire [31:0] q_u     = (NREG != 0) ? q_r : q;
    wire [3:0]  g_new_u = (NREG != 0) ? g_new_r : g_new;
    task issue(input [3:0] op, input [7:0] idx, input [3:0] ncol, input [31:0] pos, input [TW-1:0] t1,
               input [3:0] need);
        begin
            cmd_op <= op; cmd_idx <= idx; cmd_ncol <= ncol; cmd_pos <= pos; cmd_tok1 <= t1;
            am_need <= need; am_got <= 0; done_seen <= 1'b0;
            cmd_v <= 1'b1; s <= S_ISSUE;
        end
    endtask
    // observation counters through keep-prefix incrementers (FAST = 1; ABC re-ripples a plain + 1)
    wire [31:0] ct_n, ce_n, cm_n;
    wire        c_eng = (s == S_ISSUE || s == S_WAIT);
    generate if (FAST != 0) begin : g_cnt1
        ot_hdc_inc_k #(.W(32)) u_ct (.a(cyc_total),  .inc(s != S_IDLE && s != S_DONE), .y(ct_n), .co());
        ot_hdc_inc_k #(.W(32)) u_ce (.a(cyc_engine), .inc(c_eng), .y(ce_n), .co());
        ot_hdc_inc_k #(.W(32)) u_cm (.a(cyc_markov), .inc(c_eng && cmd_op == C_MARKOV), .y(cm_n), .co());
    end else begin : g_cnt0
        assign ct_n = 32'd0; assign ce_n = 32'd0; assign cm_n = 32'd0;
    end endgenerate
    reg [3:0] rw;
    wire rd_ok = (PRL==0) || (rw>=PRL);
    always @(posedge clk or negedge rst_n)
        if(!rst_n) rw<=0;
        else if((s==S_PF_TOK || s==S_FLOAD) && !rd_ok) rw<=rw+1'b1;
        else rw<=0;
    integer k;
`ifndef SYNTHESIS
    // NREG contract: the registered n-derived values are only consumed when current
    always @(posedge clk) if (rst_n && NREG != 0 && s == S_EMIT_ACK && e_v && e_ready && !nd_ok)
        $error("ot_dshbm_dspark_ctl_stop: NREG rem_r consumed one cycle after n_set");
`endif
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            effective_n <= 0; effective_bonus <= 0; stop_latched <= 0; stop_status <= 0;
            s <= S_IDLE; cmd_v <= 1'b0; done <= 1'b0; e_v <= 1'b0; n_set <= 1'b0; tw_v <= 1'b0;
            acc_start <= 1'b0; acc_tokx <= 1'b0; acc_amax <= 1'b0; acc_go <= 1'b0; step_v <= 1'b0;
            steps <= 0; emitted <= 0; cyc_total <= 0; cyc_engine <= 0; cyc_markov <= 0; pf <= 1'b0; pp <= 0;
            g <= 0; j <= 0; y <= 0; am_need <= 0; am_got <= 0; done_seen <= 1'b0; step_g <= 0;
        end else begin
            if (!STOP_EN || !e_v || e_ready) e_v <= 1'b0; n_set <= 1'b0; tw_v <= 1'b0; acc_start <= 1'b0; acc_tokx <= 1'b0; acc_amax <= 1'b0;
            acc_go <= 1'b0; step_v <= 1'b0; acc_rel <= 1'b0;
            if (FAST == 0) begin
                if (s != S_IDLE && s != S_DONE) cyc_total <= cyc_total + 1;
                if (s == S_ISSUE || s == S_WAIT) begin
                    cyc_engine <= cyc_engine + 1;
                    if (cmd_op == C_MARKOV) cyc_markov <= cyc_markov + 1;
                end
            end else begin
                cyc_total <= ct_n; cyc_engine <= ce_n; cyc_markov <= cm_n;
            end
            // argmax results, routed by the command they belong to
            if (am_v && (s == S_ISSUE || s == S_WAIT)) begin
                am_got <= am_got + 1;
                if (cmd_op == C_VHEAD) begin
                    t_last <= am_idx;
                    if (!pf) begin acc_amax <= 1'b1; amax_slot <= am_got[SLW-1:0]; amax_tok <= am_idx; end
                end else if (cmd_op == C_MARKOV) begin
                    d[cmd_idx] <= am_idx;
                end
            end
            if (eng_done && (s == S_ISSUE || s == S_WAIT)) done_seen <= 1'b1;
            case (s)
                S_IDLE: if (start) begin
                    stop_latched <= 0; stop_status <= 0; effective_n <= 0;
                    pf <= 1'b1; pp <= 0; emitted <= 0; steps <= 0;
                    n_set <= 1'b1; n_val <= 0; s <= S_PF_TOK;
                    if (STOP_EN && (cfg_ngen==0 || cfg_plen==0 || cfg_plen>cfg_maxpos || cfg_maxpos>MAXPOS || cfg_gamma>B || B>=PMAX)) begin
                        s <= S_DONE; stop_latched <= 1; stop_status <= cfg_ngen==0 ? 3'd2 : 3'd4;
                    end
                end
                S_PF_TOK: if(rd_ok) begin                      // the prompt token of position pp
                    tw_v <= 1'b1; tw_pos <= pp; tw_tok <= p_tok;
                    g <= 0;
                    issue(C_VLAYER, 0, 1, pp, 0, 0);
                end
                S_ISSUE: if (cmd_ready) begin cmd_v <= 1'b0; s <= S_WAIT; end
                S_WAIT: if ((done_seen || eng_done) && am_got == am_need) s <= S_AFTER;
                S_AFTER: case (cmd_op)
                    C_VLAYER: if (cmd_idx < NL - 1) issue(C_VLAYER, cmd_idx + 1, cmd_ncol, cmd_pos, 0, 0);
                              else issue(C_VHEAD, 0, cmd_ncol, cmd_pos, 0, cmd_ncol);
                    C_VHEAD:  issue(C_SEED, 0, cmd_ncol, cmd_pos, 0, 0);
                    C_SEED: if (pf) begin
                                n_set <= 1'b1; n_val <= pp + 1;
                                if (pp + 1 < cfg_plen) begin pp <= pp + 1; s <= S_PF_TOK; end
                                else s <= S_PF_EMIT;
                            end else s <= S_ACC;
                    C_DSTAGE: if (cmd_idx < NST - 1) issue(C_DSTAGE, cmd_idx + 1, B, cmd_pos, y, 0);
                              else issue(C_DHEAD, 0, B, cmd_pos, y, 0);
                    C_DHEAD:  issue(C_MARKOV, 0, 1, cmd_pos, y, 1);
                    C_MARKOV: if (cmd_idx + 1 < g) issue(C_MARKOV, cmd_idx + 1, 1, cmd_pos, d[cmd_idx], 1);
                              else begin j <= 0; s <= S_VTOK; end
                    default:  s <= S_DONE;
                endcase
                S_PF_EMIT: begin
                    pf <= 1'b0;
                    y <= t_last;
                    e_v <= 1'b1; e_tok <= t_last; e_idx <= 0; emitted <= 1;
                    s <= STOP_EN ? S_PF_ACK : ((cfg_ngen <= 1) ? S_DONE : S_STEP);
                end
                S_STEP: if (NREG == 0 || nd_ok) begin
                    g <= g_new_u; j <= 0;
                    acc_start <= 1'b1;
                    if (g_new_u == 0) s <= S_VTOK;
                    else if (cfg_force) s <= S_FLOAD;
                    else issue(C_DSTAGE, 0, B, q_u, y, 0);
                end
                S_FLOAD: if(rd_ok) begin                       // host drafts (bench drafter)
                    d[j] <= f_tok;
                    if (j + 1 == g) begin j <= 0; s <= S_VTOK; end
                    else j <= j + 1;
                end
                S_VTOK: begin                        // the pass's tokens into the history ring (and the accept unit)
                    tw_v <= 1'b1; tw_pos <= n + j; tw_tok <= (j == 0) ? y : d[j-1];
                    if (j != 0) begin acc_tokx <= 1'b1; tokx_slot <= j[SLW-1:0]; tokx_tok <= d[j-1]; end
                    if (j == g) issue(C_VLAYER, 0, g + 1, n, 0, 0);
                    else j <= j + 1;
                end
                S_ACC: begin acc_go <= 1'b1; s <= S_ACCW; end
                S_ACCW: if (acc_done) begin j <= 0; s <= S_EMIT; end
                S_PF_ACK: if(e_v && e_ready) begin
                    e_v <= 0;
                    if((cfg_eos_en && e_tok==cfg_eos) || cfg_ngen<=1 || n>=cfg_maxpos) begin
                        stop_latched<=1;
                        stop_status <= (cfg_eos_en && e_tok==cfg_eos)?3'd1:(cfg_ngen<=1?3'd2:3'd3);
                        s<=S_DONE;
                    end else s<=S_STEP;
                end
                S_EMIT: if(STOP_EN) begin
                    e_v<=1; e_tok<=ttok[j*TW+:TW]; e_idx<=emitted;
                    s<=S_EMIT_ACK;
                end else begin
                    if (emitted < cfg_ngen) begin
                        e_v <= 1'b1; e_tok <= ttok[j*TW +: TW]; e_idx <= emitted; emitted <= emitted + 1;
                    end
                    if (j == acc_a) s <= S_COMMIT;
                    else j <= j + 1;
                end
                S_EMIT_ACK: if(e_v && e_ready) begin
                    e_v<=0; emitted<=emitted+1;
                    effective_n<=j+1; effective_bonus<=e_tok;
                    if((cfg_eos_en && e_tok==cfg_eos) || emitted+1>=cfg_ngen ||
                       ((NREG != 0) ? ({{28{1'b0}}, j} + 32'd1 >= rem_r) : (n+j+1>=cfg_maxpos))) begin
                        stop_latched<=1;
                        stop_status <= (cfg_eos_en && e_tok==cfg_eos)?3'd1:(emitted+1>=cfg_ngen?3'd2:3'd3);
                        s<=S_COMMIT;
                    end else if(j==acc_a) s<=S_COMMIT;
                    else begin j<=j+1; s<=S_EMIT; end
                end
                S_COMMIT: begin
                    n_set <= 1'b1;
                    n_val <= n + (STOP_EN ? effective_n : (1 + acc_a)) + (MUT == 1 ? 1 : 0);
                    y <= (MUT == 2 && acc_a + 1 <= g) ? ttok[(acc_a + 1)*TW +: TW] : (STOP_EN ? effective_bonus : bonus);
                    step_v <= 1'b1; step_g <= g;
                    steps <= steps + 1;
                    s <= ((STOP_EN && stop_latched) || emitted >= cfg_ngen) ? S_DONE : S_CWAIT;
                end
                S_CWAIT: begin s <= S_STEP; acc_rel <= 1'b1; end   // spec state takes n; the accept unit is released
                S_DONE: done <= 1'b1;
                default: s <= S_DONE;
            endcase
        end
    end
endmodule
