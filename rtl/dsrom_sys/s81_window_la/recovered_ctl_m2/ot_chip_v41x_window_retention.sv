`timescale 1ns/1ps
// Opt-in, one-use L0 QK->PV content retention decision. This is not the
// descriptor lifecycle. Caller validates exact L0 signatures and supplies a
// normalized physical-content key, never raw transposed ME descriptor fields.
// A hit suppresses prefetch itself and publishes STAGE for a NEW generation.
module ot_chip_v41x_window_retention #(
    parameter integer KEYW=320, GENW=16,
    parameter bit ENABLE=0
) (
    input wire clk, rst_n,
    input wire invalidate, // ANY accepted mutation/prime/config/step/fault
    input wire drained, mutation_pending,
    input wire qk_complete, qk_cacheable, all_rows_valid,
    input wire [KEYW-1:0] qk_content_key,
    input wire [GENW-1:0] qk_generation,
    input wire pv_request, pv_cacheable,
    input wire [KEYW-1:0] pv_content_key,
    input wire [GENW-1:0] pv_generation,
    input wire generation_wrap, // wrap always misses; caller drains lifecycle
    output wire response_valid,
    output wire retained_hit,
    output wire [GENW-1:0] response_generation,
    output wire armed
);
    reg valid_q, response_q, hit_q;
    reg [KEYW-1:0] key_q;
    reg [GENW-1:0] gen_q, response_gen_q;
    assign armed = ENABLE && valid_q && !invalidate && !mutation_pending;
    assign response_valid = response_q;
    // Mutation on the response cycle also kills a previously computed hit.
    assign retained_hit = ENABLE && response_q && hit_q && !invalidate &&
                          !mutation_pending && drained && !generation_wrap;
    assign response_generation = response_gen_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            valid_q<=0; response_q<=0; hit_q<=0;
            key_q<='0; gen_q<='0; response_gen_q<='0;
        end else begin
            response_q<=pv_request; hit_q<=0;
            if (pv_request) response_gen_q<=pv_generation;
            if (!ENABLE || invalidate || mutation_pending || generation_wrap) valid_q<=0;
            else if (pv_request) begin
                hit_q<=valid_q && pv_cacheable && drained &&
                       pv_content_key==key_q && pv_generation!='0 &&
                       pv_generation!=gen_q;
                valid_q<=0;
            end else if (qk_complete) begin
                valid_q<=qk_cacheable && all_rows_valid && drained && qk_generation!='0;
                key_q<=qk_content_key; gen_q<=qk_generation;
            end
        end
    end
endmodule
