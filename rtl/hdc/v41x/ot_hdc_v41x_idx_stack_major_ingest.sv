`timescale 1ns/1ps
// Bounded ingress between one contiguous-stack key reader and four score lanes.
// The four lanes receive four consecutive local keys each, atomically. The
// reader may keep its 16-key beat until every score lane has room; no key-image
// buffer proportional to context length is needed here.
//
// This does NOT make the existing quarter selector usable on its own: stacks
// interleave globally. A following exact selector must retain local top-K per
// stack and merge the four survivor lists with score/index tie ordering.
module ot_hdc_v41x_idx_stack_major_ingest #(
    parameter integer IW=30,
    parameter integer KW=544
) (
    input wire clk,
    input wire rst_n,
    input wire cmd_v,
    input wire [1:0] cmd_stack,
    input wire [IW-1:0] cmd_first_local,
    input wire [IW-1:0] cmd_count,
    input wire [IW-1:0] cmd_nkeys,
    input wire i_valid,
    output wire i_ready,
    input wire [15:0] i_kv,
    input wire [16*KW-1:0] i_key,
    output wire [3:0] lane_valid,
    input wire [3:0] lane_ready,
    output wire [15:0] lane_kv,
    output wire [16*KW-1:0] lane_key,
    output wire [4*IW-1:0] lane_first_local,
    output wire [7:0] lane_stack,
    output wire [IW-1:0] quarter_size,
    output reg fault
);
    reg [1:0] stack;
    reg [IW-1:0] rank, remaining, nkeys;
    assign quarter_size=(nkeys>>5)<<3;
    wire all_ready=&lane_ready;
    assign i_ready=all_ready && !cmd_v;
    assign lane_valid={4{ i_valid && i_ready }};
    assign lane_kv=i_kv;
    assign lane_key=i_key;
    function automatic [4:0] pop16(input [15:0] mask);
        integer b;
        begin
            pop16=0;
            for(b=0;b<16;b=b+1) pop16=pop16+{4'd0,mask[b]};
        end
    endfunction
    wire [4:0] consumed=pop16(i_kv);
    genvar g;
    generate for(g=0;g<4;g=g+1) begin:g_lane
        localparam [IW-1:0] OFFSET=4*g;
        assign lane_first_local[IW*g +: IW]=rank+OFFSET;
        assign lane_stack[2*g +: 2]=stack;
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin stack<=0;rank<=0;remaining<=0;nkeys<=0;fault<=0;end
        else if(cmd_v) begin
            stack<=cmd_stack;rank<=cmd_first_local;remaining<=cmd_count;nkeys<=cmd_nkeys;fault<=0;
        end else if(i_valid && i_ready) begin
            rank<=rank+{{(IW-5){1'b0}},consumed};
            remaining<=remaining-{{(IW-5){1'b0}},consumed};
            // The range streamer emits a valid prefix on its final beat.
            if(i_kv != (16'hffff >> (16-consumed))) fault<=1;
            if(remaining<{{(IW-5){1'b0}},consumed}) fault<=1;
            // Global range checking is done after each lane's ordinal is
            // restored at its score output. Only the prefix contract is
            // checked here, so this stage stays small and off the score path.
        end
    end
endmodule
