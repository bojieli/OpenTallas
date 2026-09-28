`timescale 1ns/1ps
// Retire the five final-slot result vectors from one shared matrix sweep.
// result_last must be aligned to the post-scale result_valid beat. This
// boundary serializes five argmax tokens for ot_hdc_qwen_dflash_step_ctrl.
// A production lm_head also needs a running maximum across vocabulary chunks;
// this block is only the final-chunk boundary and does not replace that scan.
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
    wire [5*NW-1:0] winners;
    function automatic [31:0] ordered_key(input [31:0] v);
        ordered_key = v[31] ? ~v : {1'b1,v[30:0]};
    endfunction
    genvar s;
    generate for (s=0;s<5;s=s+1) begin : g_slot
        reg [31:0] best;
        reg [NW-1:0] winner;
        integer j;
        always @* begin
            best=ordered_key(result[(s*NL)*32 +: 32]);
            winner=row_base;
            for (j=1;j<NL;j=j+1)
                if (ordered_key(result[(s*NL+j)*32 +: 32]) > best) begin
                    best=ordered_key(result[(s*NL+j)*32 +: 32]);
                    winner=row_base+j;
                end
        end
        assign winners[s*NW +: NW]=winner;
    end endgenerate
    assign busy=armed || sending;
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
            if (result_valid && result_last) begin
                if (!armed || sending) fault<=1;
                else begin
                    tokens<=winners; index<=0; sending<=1; armed<=0;
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
