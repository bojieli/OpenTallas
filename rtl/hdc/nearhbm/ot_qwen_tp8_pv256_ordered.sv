`timescale 1ns/1ps
// Candidate only: instantiate explicitly. The accepted PV512 stack body is untouched.
// Merge PRODUCTS, not completed partial sums. Physical stacks pair (0,2)/(1,3).
// One invocation is one query head, dimension block and canonical residue.
// The controller requests t=c,c+256,...; each source retains ownership and epoch.
// Each accepted product vector lands in a register before the FP32 RNE adder.
module ot_qwen_tp8_pv256_ordered #(
    parameter integer LANES=16,
    parameter integer LAT=3
) (
    input wire clk, rst_n,
    input wire start,
    input wire [13:0] context_len,
    input wire [7:0] residue,
    input wire [15:0] epoch,
    input wire [1:0] head,
    input wire [2:0] block_id,
    output wire busy,
    output wire [13:0] expected_t,
    output wire expected_upper,
    input wire lo_valid, hi_valid,
    output wire lo_ready, hi_ready,
    input wire [13:0] lo_t, hi_t,
    input wire [15:0] lo_epoch, hi_epoch,
    input wire [1:0] lo_head, hi_head,
    input wire [2:0] lo_block, hi_block,
    input wire [LANES*32-1:0] lo_product, hi_product,
    output reg out_valid,
    input wire out_ready,
    output reg [LANES*32-1:0] out_partial,
    output reg [7:0] out_residue,
    output reg [15:0] out_epoch,
    output reg [1:0] out_head,
    output reg [2:0] out_block,
    output reg fault
);
    localparam IDLE=0, TAKE=1, ISSUE=2, WAIT_ADD=3, DONE=4, BAD=5;
    reg [2:0] state;
    reg [13:0] t, limit;
    reg [15:0] ep;
    reg [1:0] hd;
    reg [2:0] blk;
    reg [LANES*32-1:0] acc, product;
    wire upper=t[8]; // t mod512 bit8 selects the second physical stack in a pair.
    wire selected_valid=upper ? hi_valid : lo_valid;
    wire [13:0] selected_t=upper ? hi_t : lo_t;
    wire [15:0] selected_epoch=upper ? hi_epoch : lo_epoch;
    wire [1:0] selected_head=upper ? hi_head : lo_head;
    wire [2:0] selected_block=upper ? hi_block : lo_block;
    wire [LANES*32-1:0] selected_product=upper ? hi_product : lo_product;
    wire [LANES*32-1:0] sum;
    wire [LANES-1:0] sum_valid;
    wire [LANES*2-1:0] sum_err;
    assign busy=state!=IDLE;
    assign expected_t=t;
    assign expected_upper=upper;
    assign lo_ready=state==TAKE && !upper;
    assign hi_ready=state==TAKE && upper;
    genvar l;
    generate for(l=0;l<LANES;l=l+1) begin: g_add
        ot_hdc_fp32_add_lat #(.LAT(LAT)) u_add (
            .clk(clk),.rst_n(rst_n),.valid_in(state==ISSUE),
            .a(acc[32*l+:32]),.b(product[32*l+:32]),
            .y(sum[32*l+:32]),.err(sum_err[2*l+:2]),.valid_out(sum_valid[l]));
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE; t<=0; limit<=0; ep<=0; hd<=0; blk<=0;
            acc<=0; product<=0; out_valid<=0; out_partial<=0;
            out_residue<=0; out_epoch<=0; out_head<=0; out_block<=0; fault<=0;
        end else begin
            if(start && state!=IDLE) begin fault<=1; state<=BAD; out_valid<=0; end
            else case(state)
                IDLE: if(start) begin
                    t<={6'd0,residue}; limit<=context_len;
                    ep<=epoch; hd<=head; blk<=block_id; acc<=0;
                    out_residue<=residue; out_epoch<=epoch; out_head<=head; out_block<=block_id;
                    if(context_len>8192) begin fault<=1; state<=BAD; end
                    else if({6'd0,residue}>=context_len) begin out_partial<=0; out_valid<=1; state<=DONE; end
                    else state<=TAKE;
                end
                TAKE: if(selected_valid) begin
                    if(selected_t!=t || selected_epoch!=ep || selected_head!=hd || selected_block!=blk) begin
                        fault<=1; state<=BAD;
                    end else begin product<=selected_product; state<=ISSUE; end
                end
                ISSUE: state<=WAIT_ADD;
                WAIT_ADD: if(&sum_valid) begin
                    if(|sum_err) begin fault<=1; state<=BAD; end
                    else begin
                        acc<=sum;
                        if(t+14'd256>=limit) begin out_partial<=sum; out_valid<=1; state<=DONE; end
                        else begin t<=t+14'd256; state<=TAKE; end
                    end
                end
                DONE: if(out_ready) begin out_valid<=0; state<=IDLE; end
                BAD: begin out_valid<=0; end
                default: begin fault<=1; state<=BAD; end
            endcase
        end
    end
endmodule
