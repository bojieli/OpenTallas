`timescale 1ns/1ps
// Existing VPRM accept loader and host-priority KV commit mux extracted intact.
module ot_qwen_combined_dspark_accept #(
    parameter integer SNW = 18,
    parameter integer ACCEPT_COMMIT = 0
) (
    input wire clk, rst_n,
    input wire s_done,
    input wire [8*SNW-1:0] seq_tok_vec,
    input wire [3:0] seq_n_tok,
    input wire h_commit_v,
    input wire [3:0] h_commit_n,
    input wire acc_start_v,
    input wire [SNW-1:0] acc_start_tok,
    input wire acc_tokx_v,
    input wire [2:0] acc_tokx_slot,
    input wire [SNW-1:0] acc_tokx_tok,
    input wire acc_arm, acc_commit_en,
    output wire acc_done,
    output wire [2:0] a,
    output wire [3:0] n_emit,
    output wire [SNW-1:0] bonus,
    output wire kv_commit_v,
    output wire [3:0] kv_commit_n
);
    assign kv_commit_v = h_commit_v | ((ACCEPT_COMMIT != 0) && acc_commit_en && acc_done);
    assign kv_commit_n = h_commit_v ? h_commit_n : n_emit;

    reg        acc_armed, acc_load, acc_go;
    reg [3:0]  acc_i, acc_n;
    reg        s_done_q;
    wire       amax_v = acc_load;
    wire [2:0] amax_slot = acc_i[2:0];
    wire [SNW-1:0] amax_tok = seq_tok_vec[acc_i[2:0]*SNW +: SNW];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin acc_armed <= 1'b0; acc_load <= 1'b0; acc_go <= 1'b0; acc_i <= 0; acc_n <= 0; s_done_q <= 1'b0; end
        else begin
            s_done_q <= s_done;
            acc_go <= 1'b0;
            if (acc_arm) acc_armed <= 1'b1;
            //: the head stage's done with n_tok records: load them as targets, one slot a cycle, then ACCEPT
            if (acc_armed && s_done && !s_done_q && seq_n_tok != 0) begin
                acc_armed <= 1'b0; acc_load <= 1'b1; acc_i <= 0; acc_n <= seq_n_tok;
            end else if (acc_load) begin
                if (acc_i + 1'b1 == acc_n) begin acc_load <= 1'b0; acc_go <= 1'b1; end
                acc_i <= acc_i + 1'b1;
            end
        end
    end
    wire [2:0] acc_g = acc_n[2:0] - 3'd1;      // drafts verified: block positions - 1
    ot_hdc_accept #(.NSLOT(8), .NW(SNW)) u_acc (
        .clk(clk), .rst_n(rst_n), .start_v(acc_start_v), .start_tok(acc_start_tok),
        .tokx_v(acc_tokx_v), .tokx_slot(acc_tokx_slot), .tokx_tok(acc_tokx_tok),
        .amax_v(amax_v), .amax_slot(amax_slot), .amax_tok(amax_tok),
        .acc_v(acc_go), .acc_g(acc_g), .stok(), .ttok(), .acc_done(acc_done), .acc_any(),
        .acc_a(a), .n_emit(n_emit), .bonus(bonus));

endmodule
