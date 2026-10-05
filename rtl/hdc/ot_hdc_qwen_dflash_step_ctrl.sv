`timescale 1ns/1ps
// Qwen DFlash block-5 phase and commit controller. The drafter supplies four
// proposed tokens, the target verifies five causal positions, and the shared
// ot_hdc_accept emits the greedy accepted prefix plus bonus token. Physical
// KV writes for all five slots may remain in memory; only the committed
// position pointer advances. A new block cannot start before all verify KV
// writes drain and the previous commit has retired.
module ot_hdc_qwen_dflash_step_ctrl #(
    parameter integer NW = 16,
    parameter integer CTX_MAX = 8192
) (
    input  wire clk, rst_n,
    input  wire step_start,
    input  wire [NW-1:0] start_token, start_pos,
    output reg  draft_start,
    input  wire draft_tok_v,
    input  wire [2:0] draft_slot,
    input  wire [NW-1:0] draft_token,
    input  wire draft_done,
    output reg  verify_start,
    input  wire verify_tok_v,
    input  wire [2:0] verify_slot,
    input  wire [NW-1:0] verify_token,
    input  wire verify_done,
    input  wire verify_kv_drained,
    output reg  kv_commit_v,
    output reg  [NW-1:0] kv_commit_pos,
    output reg  step_done,
    output reg  [NW-1:0] next_token, next_pos,
    output reg  [2:0] accepted_drafts, emitted_tokens,
    output reg  fault,
    output wire busy
);
    localparam [2:0] S_IDLE=0, S_DRAFT=1, S_VERIFY=2, S_KV=3,
                     S_ACCEPT=4, S_RETIRE=5;
    reg [2:0] state;
    reg [4:0] draft_seen, verify_seen;
    reg [NW-1:0] base_pos;
    wire [5*NW-1:0] stok, ttok;
    wire acc_done, acc_any;
    wire [2:0] acc_a;
    wire [3:0] n_emit;
    wire [NW-1:0] bonus;
    wire draft_write = state==S_DRAFT && draft_tok_v && draft_slot>0 && draft_slot<5 && !fault;
    wire verify_write = state==S_VERIFY && verify_tok_v && verify_slot<5 && !fault;
    ot_hdc_accept #(.NSLOT(5), .NW(NW)) u_accept (
        .clk(clk), .rst_n(rst_n),
        .start_v(state==S_IDLE && step_start && !fault), .start_tok(start_token),
        .tokx_v(draft_write), .tokx_slot(draft_slot), .tokx_tok(draft_token),
        .amax_v(verify_write), .amax_slot(verify_slot), .amax_tok(verify_token),
        .acc_v(state==S_ACCEPT && !fault), .acc_g(3'd4),
        .stok(stok), .ttok(ttok), .acc_done(acc_done), .acc_any(acc_any),
        .acc_a(acc_a), .n_emit(n_emit), .bonus(bonus)
    );
    assign busy = state != S_IDLE;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state<=S_IDLE; draft_seen<=0; verify_seen<=0; base_pos<=0;
            draft_start<=0; verify_start<=0; kv_commit_v<=0; kv_commit_pos<=0;
            step_done<=0; next_token<=0; next_pos<=0;
            accepted_drafts<=0; emitted_tokens<=0; fault<=0;
        end else begin
            draft_start<=0; verify_start<=0; kv_commit_v<=0; step_done<=0;
            if (step_start && state!=S_IDLE) fault<=1;
            if (draft_tok_v && !draft_write) fault<=1;
            if (verify_tok_v && !verify_write) fault<=1;
            case (state)
                S_IDLE: if (step_start && !fault) begin
                    if (start_pos > CTX_MAX-5) fault<=1;
                    else begin
                        base_pos<=start_pos; draft_seen<=0; verify_seen<=0;
                        draft_start<=1; state<=S_DRAFT;
                    end
                end
                S_DRAFT: begin
                    if (draft_write) begin
                        if (draft_seen[draft_slot]) fault<=1;
                        draft_seen[draft_slot]<=1;
                    end
                    if (draft_done) begin
                        if (draft_seen != 5'b11110 || draft_tok_v) fault<=1;
                        else begin verify_start<=1; state<=S_VERIFY; end
                    end
                end
                S_VERIFY: begin
                    if (verify_write) begin
                        if (verify_seen[verify_slot]) fault<=1;
                        verify_seen[verify_slot]<=1;
                    end
                    if (verify_done) begin
                        if (verify_seen != 5'b11111 || verify_tok_v) fault<=1;
                        else state<=S_KV;
                    end
                end
                S_KV: if (verify_kv_drained) state<=S_ACCEPT;
                S_ACCEPT: state<=S_RETIRE;
                S_RETIRE: if (acc_done && !fault) begin
                    accepted_drafts<=acc_a; emitted_tokens<=n_emit;
                    next_token<=bonus; next_pos<=base_pos+n_emit;
                    kv_commit_pos<=base_pos+n_emit; kv_commit_v<=1;
                    step_done<=1; state<=S_IDLE;
                end
                default: begin fault<=1; state<=S_IDLE; end
            endcase
        end
    end
endmodule
