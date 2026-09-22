`timescale 1ns/1ps
// Join a prefetched weight stream and a complete activation/scale response.
// Both producers hold valid, identity and data until accepted. Auxiliary valid
// promises activation plus every enabled scale plane. Disabled scales are ignored.
// Tags identify the operation generation; addresses identify its issue bundle.
// The caller converts each tile-local weight index to an absolute stream address.
// Clear/reset must flush both producers and the associated compute operation.
module ot_a3_lq8_operand_join #(
    parameter integer LANES=8,
    parameter integer GENERATION_BITS=32
)(
    input wire clk,rst_n,clear,
    input wire [GENERATION_BITS-1:0] generation,
    input wire operand_request,operand_issue,
    input wire [31:0] operand_a_addr,operand_s_addr,operand_ws_addr,operand_w_addr,
    input wire scale_a,scale_b,
    output wire operand_credit,
    output wire identity_mismatch,
    input wire weight_valid,
    output wire weight_ready,
    input wire [GENERATION_BITS-1:0] weight_generation,
    input wire [31:0] weight_address,
    input wire [16*LANES-1:0] weight_data,
    input wire auxiliary_valid,
    output wire auxiliary_ready,
    input wire [GENERATION_BITS-1:0] auxiliary_generation,
    input wire [31:0] auxiliary_a_addr,auxiliary_s_addr,auxiliary_ws_addr,
    input wire [63:0] auxiliary_a_data,
    input wire [31:0] auxiliary_s_data,
    input wire [8*LANES-1:0] auxiliary_ws_data,
    output wire [63:0] a_rd_data,
    output wire [31:0] s_rd_data,
    output wire [16*LANES-1:0] w_rd_data,
    output wire [8*LANES-1:0] ws_rd_data
);
    localparam integer BUNDLE_BITS=96+24*LANES;
    wire weight_matches=weight_generation==generation && weight_address==operand_w_addr;
    wire auxiliary_matches=auxiliary_generation==generation &&
        auxiliary_a_addr==operand_a_addr &&
        (!scale_a || auxiliary_s_addr==operand_s_addr) &&
        (!scale_b || auxiliary_ws_addr==operand_ws_addr);
    wire enabled=rst_n && !clear;
    assign identity_mismatch=enabled && operand_request &&
        ((weight_valid && !weight_matches) || (auxiliary_valid && !auxiliary_matches));
    assign operand_credit=enabled && operand_request && weight_valid && auxiliary_valid &&
        weight_matches && auxiliary_matches;
    wire consume=operand_issue && operand_credit;
    assign weight_ready=consume;
    assign auxiliary_ready=consume;
    // Issue registers the lane read request. Deliver on the following edge,
    // exactly as a synchronous SRAM responding to that registered request.
    reg pending;
    reg [BUNDLE_BITS-1:0] reserved_bundle,delivered_bundle;
    assign {ws_rd_data,w_rd_data,s_rd_data,a_rd_data}=delivered_bundle;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            pending<=0;reserved_bundle<=0;delivered_bundle<=0;
        end else if(clear)begin
            pending<=0;reserved_bundle<=0;delivered_bundle<=0;
        end else begin
            pending<=consume;
            if(consume)reserved_bundle<={scale_b?auxiliary_ws_data:{8*LANES{1'b0}},
                weight_data,scale_a?auxiliary_s_data:32'b0,auxiliary_a_data};
            if(pending)delivered_bundle<=reserved_bundle;
        end
    end
endmodule
