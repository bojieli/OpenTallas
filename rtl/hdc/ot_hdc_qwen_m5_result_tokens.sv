`timescale 1ns/1ps
// Keep a running argmax for five slots across all lm_head result beats.
// result_last must mark the final post-scale result_valid beat. The five
// winners then serialize into ot_hdc_qwen_dflash_step_ctrl.
module ot_hdc_qwen_m5_result_tokens #(
    parameter integer G=2, W=2, NW=16
) (
    input wire clk, rst_n, arm,
    input wire result_valid, result_last,
    input wire [5*G*W*32-1:0] result,
    input wire [NW-1:0] row_base,
    output reg tok_valid,
    output reg [2:0] tok_slot,
    output reg [NW-1:0] tok,
    output reg done,
    output reg fault,
    output wire busy
);
    localparam integer NL=G*W;
    reg armed, sending, done_pending;
    reg [2:0] index;
    reg [5*NW-1:0] tokens;
    wire [5*NW-1:0] selected_winners;
    function automatic [31:0] ordered_key(input [31:0] v);
        ordered_key = v[31] ? ~v : {1'b1,v[30:0]};
    endfunction
    genvar s;
    generate for (s=0;s<5;s=s+1) begin : g_slot
        reg [31:0] beat_key, best_key;
        reg [NW-1:0] beat_row, best_row;
        reg seen;
        wire beat_wins = !seen || beat_key>best_key ||
                         (beat_key==best_key && beat_row<best_row);
        integer j;
        always @* begin
            beat_key=ordered_key(result[(s*NL)*32 +: 32]);
            beat_row=row_base;
            for (j=1;j<NL;j=j+1)
                if (ordered_key(result[(s*NL+j)*32 +: 32]) > beat_key) begin
                    beat_key=ordered_key(result[(s*NL+j)*32 +: 32]);
                    beat_row=row_base+j;
                end
        end
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin seen<=0; best_key<=0; best_row<=0; end
            else if (arm && !busy && !fault) seen<=0;
            else if (result_valid && armed && beat_wins) begin
                seen<=1; best_key<=beat_key; best_row<=beat_row;
            end
        end
        assign selected_winners[s*NW +: NW]=beat_wins ? beat_row : best_row;
    end endgenerate
    assign busy=armed || sending || done_pending;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            armed<=0; sending<=0; done_pending<=0; index<=0; tokens<=0;
            tok_valid<=0; tok_slot<=0; tok<=0; done<=0; fault<=0;
        end else begin
            tok_valid<=0; done<=0;
            if (done_pending) begin done<=1; done_pending<=0; end
            if (arm) begin
                if (busy || fault) fault<=1;
                else armed<=1;
            end
            if (result_last && !result_valid) fault<=1;
            if (result_valid && !armed) fault<=1;
            if (result_valid && result_last) begin
                if (!armed || sending) fault<=1;
                else begin
                    tokens<=selected_winners; index<=0; sending<=1; armed<=0;
                end
            end
            if (sending) begin
                tok_valid<=1; tok_slot<=index; tok<=tokens[index*NW +: NW];
                if (index==4) begin sending<=0; done_pending<=1; end
                else index<=index+1'b1;
            end
        end
    end
endmodule
