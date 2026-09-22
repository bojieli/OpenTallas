`timescale 1ns/1ps
// Pass-first weight schedule over the existing two-bank ownership service.
// Each bounded pass is fetched once and replayed across rows. Passes larger
// than 1024 words stream each row; the external coordinate service must use
// this same compact/fallback fetch order. Issue identities remain contiguous.
// scheduled means all tiles were handed off, not that compute/drain finished.
module ot_a3_weight_pass_scheduler #(
    parameter integer INTERLEAVE=3,
    parameter integer TILE_WORDS=32,
    parameter bit REUSE_PASSES=1
)(
    input wire clk,rst_n,clear,
    input wire command_valid,
    output wire command_ready,
    input wire [31:0] command_generation,command_base,
    input wire [15:0] command_rows,command_local_cols,command_depth_words,
    output wire active,
    output reg scheduled,command_error,
    output wire reserve_valid,
    input wire reserve_ready,
    output wire reserve_bank,
    output wire [63:0] reserve_tag,
    output wire [9:0] reserve_words,
    output wire fetch_valid,
    input wire fetch_ready,
    output wire [63:0] fetch_tag,
    output wire [31:0] fetch_address,
    output wire [9:0] fetch_words,
    input wire response_valid,
    output wire response_ready,response_mismatch,
    input wire [63:0] response_tag,
    input wire [9:0] response_index,
    input wire [127:0] response_data,
    output wire fill_valid,fill_bank,
    input wire fill_ready,
    output wire [63:0] fill_tag,
    output wire [127:0] fill_data,
    output wire tile_valid,
    input wire tile_ready,
    output wire tile_bank,
    output wire [63:0] tile_tag,
    output wire [63:0] tile_stream_tag,
    output wire tile_retain,
    output wire [9:0] tile_words
);
    localparam [2:0] IDLE=0,EXTENT=1,STREAM=2,CHECK=3,LAUNCH=4,RUN=5;
    reg [2:0] state;
    reg [31:0] generation,origin,fetch_base,issue_base;
    reg [15:0] rows,cols,cols_left,depth;
    reg [31:0] pass_words,row_words;
    reg [47:0] total_words,pass_stream_words;
    wire [15:0] pass_cols=cols_left<16'(INTERLEAVE)?cols_left:16'(INTERLEAVE);
    wire reuse_pass=REUSE_PASSES && rows>1 && pass_words<=1024;
    wire [31:0] fetched_words=reuse_pass?pass_words:pass_stream_words[31:0];
    wire enabled=rst_n && !clear;
    wire inner_ready,inner_scheduled,inner_error;
    wire command_fire=command_valid && command_ready;
    wire tile_fire=tile_valid && tile_ready;
    wire [32:0] range_end={1'b0,origin}+{1'b0,total_words[31:0]};
    assign command_ready=enabled && state==IDLE && !command_error;
    assign active=enabled && state!=IDLE;
    assign tile_stream_tag={generation,issue_base};
    // Bank-sized increments avoid placing the extent select before a full
    // 32-bit carry chain in the issue identity path.
    wire [10:0] issue_low={1'b0,issue_base[9:0]}+{1'b0,tile_words};
    wire [21:0] issue_high=issue_base[31:10]+22'd1;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin state<=IDLE;scheduled<=0;command_error<=0;end
        else if(clear)begin state<=IDLE;scheduled<=0;command_error<=0;end
        else begin
            scheduled<=0;
            case(state)
                IDLE:if(command_fire)begin
                    if(command_rows==0 || command_local_cols==0 || command_depth_words==0)
                        command_error<=1;
                    else state<=EXTENT;
                end
                EXTENT:state<=STREAM;
                STREAM:state<=CHECK;
                CHECK:begin
                    if(total_words[47:32]!=0 || pass_stream_words[47:32]!=0 || range_end>33'h100000000)begin
                        command_error<=1;state<=IDLE;
                    end else state<=LAUNCH;
                end
                LAUNCH:if(inner_ready)state<=RUN;
                RUN:if(inner_error)begin command_error<=1;state<=IDLE;end
                    else if(inner_scheduled)begin
                        if(cols_left<=16'(INTERLEAVE))begin state<=IDLE;scheduled<=1;end
                        else state<=EXTENT;
                    end
                default:state<=IDLE;
            endcase
        end
    end
    always @(posedge clk)begin
        if(command_fire)begin
            generation<=command_generation;origin<=command_base;
            fetch_base<=command_base;issue_base<=command_base;
            rows<=command_rows;cols<=command_local_cols;cols_left<=command_local_cols;
            depth<=command_depth_words;
        end else begin
            if(state==EXTENT)begin
                pass_words<=32'(pass_cols)*32'(depth);
                row_words<=32'(cols)*32'(depth);
            end
            if(state==STREAM)begin
                total_words<=48'(rows)*48'(row_words);
                pass_stream_words<=48'(rows)*48'(pass_words);
            end
            if(state==RUN && inner_scheduled && cols_left>16'(INTERLEAVE))begin
                cols_left<=cols_left-16'(INTERLEAVE);
                fetch_base<=fetch_base+fetched_words;
            end
            if(tile_fire)issue_base<={issue_low[10]?issue_high:issue_base[31:10],issue_low[9:0]};
        end
    end
    /* verilator lint_off PINCONNECTEMPTY */
    ot_a3_weight_tile_scheduler #(.TILE_WORDS(TILE_WORDS),.ROW_REUSE(REUSE_PASSES)) inner(
        .clk(clk),.rst_n(rst_n),.clear(clear),
        .command_valid(enabled && state==LAUNCH),.command_ready(inner_ready),
        .command_generation(generation),.command_base(fetch_base),
        .command_words(pass_stream_words[31:0]),.command_row_words(pass_words),
        .active(),.scheduled(inner_scheduled),.command_error(inner_error),
        .reserve_valid(reserve_valid),.reserve_ready(reserve_ready),.reserve_bank(reserve_bank),
        .reserve_tag(reserve_tag),.reserve_words(reserve_words),
        .fetch_valid(fetch_valid),.fetch_ready(fetch_ready),.fetch_tag(fetch_tag),
        .fetch_address(fetch_address),.fetch_words(fetch_words),
        .response_valid(response_valid),.response_ready(response_ready),.response_mismatch(response_mismatch),
        .response_tag(response_tag),.response_index(response_index),.response_data(response_data),
        .fill_valid(fill_valid),.fill_ready(fill_ready),.fill_bank(fill_bank),.fill_tag(fill_tag),.fill_data(fill_data),
        .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_bank(tile_bank),.tile_tag(tile_tag),
        .tile_stream_tag(),.tile_retain(tile_retain),.tile_words(tile_words));
    /* verilator lint_on PINCONNECTEMPTY */
    initial if(INTERLEAVE<1 || INTERLEAVE>65535)$fatal(1,"invalid pass width");
endmodule
