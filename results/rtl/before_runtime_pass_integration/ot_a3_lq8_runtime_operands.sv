`timescale 1ns/1ps
// Complete bounded operand service for an eight-lane LQ8. One command remains
// owned until clear, even if prefetch finishes first. clear must coincide with
// compute cancellation/completion and external generation drain/cancellation.
// The external services must honor ready/valid and echo request identities.
// Admission validates geometry; compute_admitted supplies the core's format
// verdict (its first operand_request is sufficient). Errors stay visible until
// clear; the parent must abort the operation rather than leave it stalled.
module ot_a3_lq8_runtime_operands #(
    parameter integer INTERLEAVE=3,
    parameter integer TILE_WORDS=32,
    parameter integer AUXILIARY_DEPTH=3,
    parameter bit REGISTER_AUXILIARY_REQUESTS=0,
    // Enable only when the transport stream repeats the same weights per row.
    parameter bit REUSE_WEIGHT_ROWS=0
)(
    input wire clk,rst_n,clear,
    input wire command_valid,
    output wire command_ready,
    input wire [31:0] cfg_generation,
    input wire [15:0] cfg_rows,cfg_cols,cfg_depth,
    input wire [7:0] cfg_group,
    input wire cfg_scale_a,cfg_scale_b,
    input wire [15:0] cfg_block_a,cfg_block_b,cfg_block_rows_a,
    input wire [31:0] cfg_a_base,cfg_s_base,cfg_ws_base,cfg_w_base,
    input wire compute_admitted,operand_request,operand_issue,
    input wire [31:0] operand_a,operand_s,operand_ws,operand_w,
    output wire operand_credit,
    output wire [63:0] a_data,ws_data,
    output wire [31:0] s_data,
    output wire [127:0] w_data,
    output reg busy,
    output wire geometry_error,
    output reg protocol_error,
    output wire weight_request_valid,
    input wire weight_request_ready,
    output wire [63:0] weight_request_tag,
    output wire [31:0] weight_request_address,
    output wire [9:0] weight_request_words,
    input wire weight_response_valid,
    output wire weight_response_ready,
    input wire [63:0] weight_response_tag,
    input wire [9:0] weight_response_index,
    input wire [127:0] weight_response_data,
    output wire auxiliary_request_valid,
    input wire auxiliary_request_ready,
    output wire [31:0] auxiliary_request_generation,auxiliary_request_a,
                       auxiliary_request_s,auxiliary_request_ws,auxiliary_request_w,
    output reg auxiliary_scale_a,auxiliary_scale_b,
    input wire auxiliary_response_valid,
    output wire auxiliary_response_ready,
    input wire [31:0] auxiliary_response_generation,auxiliary_response_w,
    input wire [63:0] auxiliary_response_a_data,auxiliary_response_ws_data,
    input wire [31:0] auxiliary_response_s_data
);
    // Clear revokes all bank/queue credits together. Physical reset-tree
    // implementation must preserve asynchronous assertion/safe deassertion.
    wire service_rst_n=rst_n && !clear;
    wire admission_ready,record_valid,record_error,scheduler_ready;
    reg launched;
    wire launch=record_valid && !record_error && compute_admitted && !launched && scheduler_ready;
    wire [31:0] generation,base_a,base_s,base_ws,base_w,stream_words;
    wire [15:0] rows,cols,depth_words,rpb,cpa,cpb,bwa,bwb;
    assign command_ready=service_rst_n && !busy && admission_ready;
    assign geometry_error=busy && record_valid && record_error;
    wire weight_mismatch,auxiliary_mismatch,join_mismatch,scheduler_error;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin busy<=0;launched<=0;protocol_error<=0;auxiliary_scale_a<=0;auxiliary_scale_b<=0;end
        else if(clear)begin busy<=0;launched<=0;protocol_error<=0;end
        else begin
            if(command_valid && command_ready)begin
                busy<=1;auxiliary_scale_a<=cfg_scale_a;auxiliary_scale_b<=cfg_scale_b;
            end
            if(launch)launched<=1;
            if(weight_mismatch || auxiliary_mismatch || join_mismatch || scheduler_error)protocol_error<=1;
        end
    end
    ot_a3_lq8_operand_admission admission(
        .clk(clk),.rst_n(service_rst_n),.clear(1'b0),
        .command_valid(command_valid && !busy),.command_ready(admission_ready),
        .cfg_generation(cfg_generation),.cfg_rows(cfg_rows),.cfg_cols(cfg_cols),.cfg_depth(cfg_depth),
        .cfg_group(cfg_group),.cfg_scale_a(cfg_scale_a),.cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a),.cfg_block_b(cfg_block_b),.cfg_block_rows_a(cfg_block_rows_a),
        .cfg_a_base(cfg_a_base),.cfg_s_base(cfg_s_base),.cfg_ws_base(cfg_ws_base),.cfg_w_base(cfg_w_base),
        .record_valid(record_valid),.record_ready(launch),.geometry_error(record_error),.stream_words(stream_words),
        .generation(generation),.a_base(base_a),.s_base(base_s),.ws_base(base_ws),.w_base(base_w),
        .rows(rows),.local_cols(cols),.depth_words(depth_words),.rows_per_scale_a(rpb),
        .scale_stride_a(cpa),.scale_stride_b(cpb),.groups_per_scale_a(bwa),.groups_per_scale_b(bwb));
    wire reserve_valid,reserve_ready,reserve_bank,fill_valid,fill_ready,fill_bank,tile_valid,tile_ready,tile_bank;
    wire [63:0] reserve_tag,fill_tag,tile_tag,tile_stream_tag;
    wire tile_retain;
    reg [31:0] row_words;
    always @(posedge clk)row_words<=32'(cols)*32'(depth_words);
    wire [9:0] reserve_words,tile_words;
    wire [127:0] fill_data;
    ot_a3_weight_tile_scheduler #(.TILE_WORDS(TILE_WORDS),.ROW_REUSE(REUSE_WEIGHT_ROWS)) scheduler(
        .clk(clk),.rst_n(service_rst_n),.clear(1'b0),
        .command_valid(launch),.command_ready(scheduler_ready),
        .command_generation(generation),.command_base(base_w),.command_words(stream_words),.command_row_words(row_words),
        .active(),.scheduled(),.command_error(scheduler_error),
        .reserve_valid(reserve_valid),.reserve_ready(reserve_ready),.reserve_bank(reserve_bank),
        .reserve_tag(reserve_tag),.reserve_words(reserve_words),
        .fetch_valid(weight_request_valid),.fetch_ready(weight_request_ready),.fetch_tag(weight_request_tag),
        .fetch_address(weight_request_address),.fetch_words(weight_request_words),
        .response_valid(weight_response_valid),.response_ready(weight_response_ready),.response_mismatch(weight_mismatch),
        .response_tag(weight_response_tag),.response_index(weight_response_index),.response_data(weight_response_data),
        .fill_valid(fill_valid),.fill_bank(fill_bank),.fill_ready(fill_ready),.fill_tag(fill_tag),.fill_data(fill_data),
        .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_bank(tile_bank),.tile_tag(tile_tag),.tile_stream_tag(tile_stream_tag),.tile_retain(tile_retain),.tile_words(tile_words));
    wire word_valid,word_ready;
    wire [127:0] word_data;
    wire [63:0] word_tag;

    ot_a3_weight_tile_prefetch #(.SEPARATE_STREAM_TAG(1),.ABSOLUTE_STREAM_ADDRESS(1),.SINGLE_GENERATION(1)) prefetch(
        .clk(clk),.rst_n(service_rst_n),.reserve_valid(reserve_valid),.reserve_bank(reserve_bank),
        .reserve_tag(reserve_tag),.reserve_words(reserve_words),.reserve_ready(reserve_ready),
        .fill_valid(fill_valid),.fill_bank(fill_bank),.fill_tag(fill_tag),.fill_data(fill_data),.fill_ready(fill_ready),
        .cancel_valid(1'b0),.cancel_bank(1'b0),.cancel_tag(64'b0),.cancel_ready(),
        .tile_valid(tile_valid),.tile_bank(tile_bank),.tile_retain(tile_retain),.tile_tag(tile_tag),.tile_stream_tag(tile_stream_tag),.tile_words(tile_words),.tile_ready(tile_ready),
        .word_valid(word_valid),.word_ready(word_ready),.word_data(word_data),.word_tag(word_tag),.word_index(),
        .word_last(),.tile_released(),.released_tag(),.ready_banks(),.active_banks(),.reserved_slots());
    wire future_valid,future_ready;
    wire [31:0] future_generation,future_a,future_s,future_ws,future_w;
    ot_a3_lq8_operand_cursor #(.INTERLEAVE(INTERLEAVE)) cursor(
        .clk(clk),.rst_n(service_rst_n),.clear(1'b0),.start(launch),
        .cfg_generation(generation),.cfg_rows(rows),.cfg_local_cols(cols),.cfg_depth_words(depth_words),
        .cfg_rows_per_scale_a(rpb),.cfg_scale_stride_a(cpa),.cfg_scale_stride_b(cpb),
        .cfg_groups_per_scale_a(bwa),.cfg_groups_per_scale_b(bwb),
        .cfg_a_base(base_a),.cfg_s_base(base_s),.cfg_ws_base(base_ws),.cfg_w_base(base_w),
        .request_valid(future_valid),.request_ready(future_ready),.generation(future_generation),
        .a_address(future_a),.s_address(future_s),.ws_address(future_ws),.w_address(future_w),.last(),.active(),.invalid_geometry());
    wire aux_valid,aux_ready;
    wire [31:0] aux_generation,aux_a,aux_s,aux_ws;
    wire [63:0] aux_a_data,aux_ws_data;
    wire [31:0] aux_s_data;
    ot_a3_lq8_auxiliary_prefetch #(.DEPTH(AUXILIARY_DEPTH),.REGISTER_REQUESTS(REGISTER_AUXILIARY_REQUESTS),.SINGLE_GENERATION(1)) auxiliary_queue(
        .clk(clk),.rst_n(service_rst_n),.clear(1'b0),
        .request_valid(future_valid),.request_ready(future_ready),
        .request_generation(future_generation),.request_a(future_a),.request_s(future_s),.request_ws(future_ws),.request_w(future_w),
        .service_valid(auxiliary_request_valid),.service_ready(auxiliary_request_ready),
        .service_generation(auxiliary_request_generation),.service_a(auxiliary_request_a),.service_s(auxiliary_request_s),
        .service_ws(auxiliary_request_ws),.service_w(auxiliary_request_w),
        .response_valid(auxiliary_response_valid),.response_ready(auxiliary_response_ready),.response_mismatch(auxiliary_mismatch),
        .response_generation(auxiliary_response_generation),.response_w(auxiliary_response_w),
        .response_a_data(auxiliary_response_a_data),.response_s_data(auxiliary_response_s_data),.response_ws_data(auxiliary_response_ws_data),
        .auxiliary_valid(aux_valid),.auxiliary_ready(aux_ready),.auxiliary_generation(aux_generation),
        .auxiliary_a(aux_a),.auxiliary_s(aux_s),.auxiliary_ws(aux_ws),.auxiliary_w(),
        .auxiliary_a_data(aux_a_data),.auxiliary_s_data(aux_s_data),.auxiliary_ws_data(aux_ws_data),.occupied());
    wire join_credit;
    assign operand_credit=join_credit && !protocol_error;
    ot_a3_lq8_operand_join joiner(
        .clk(clk),.rst_n(service_rst_n),.clear(1'b0),.generation(generation),
        .operand_request(operand_request),.operand_issue(operand_issue),
        .operand_a_addr(operand_a),.operand_s_addr(operand_s),.operand_ws_addr(operand_ws),.operand_w_addr(operand_w),
        .scale_a(auxiliary_scale_a),.scale_b(auxiliary_scale_b),.operand_credit(join_credit),.identity_mismatch(join_mismatch),
        .weight_valid(word_valid),.weight_ready(word_ready),.weight_generation(word_tag[63:32]),
        .weight_address(word_tag[31:0]),.weight_data(word_data),
        .auxiliary_valid(aux_valid),.auxiliary_ready(aux_ready),.auxiliary_generation(aux_generation),
        .auxiliary_a_addr(aux_a),.auxiliary_s_addr(aux_s),.auxiliary_ws_addr(aux_ws),
        .auxiliary_a_data(aux_a_data),.auxiliary_s_data(aux_s_data),.auxiliary_ws_data(aux_ws_data),
        .a_rd_data(a_data),.s_rd_data(s_data),.w_rd_data(w_data),.ws_rd_data(ws_data));
endmodule
