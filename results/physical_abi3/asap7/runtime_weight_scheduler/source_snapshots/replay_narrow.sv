`timescale 1ns/1ps
// Two-bank stream scheduler with optional bounded resident-row replay.
// ROW_REUSE requires identical packed weights in every row of the stream.
// Rows of at most 1024 words use one/two 512-word banks, filled once. Larger
// rows and single-row commands retain TILE_WORDS streaming. Ownership tags
// identify resident data; tile_stream_tag separately names each issue range.
// Admission supplies the complete word
// count; the scheduler captures it and never restarts compute at a tile edge.
// Reserve SRAM before requesting an external burst. Only matching, ordered
// beats advance fill state. Bank ownership independently stalls reuse/acquire.
// clear cancels local state; caller must reset banks/compute and cancel or drain
// external requests of that generation. scheduled is NOT compute completion.
module ot_a3_weight_tile_scheduler #(
    parameter integer TILE_WORDS=32,
    parameter bit ROW_REUSE=0
)(
    input wire clk,rst_n,clear,
    input wire command_valid,
    output wire command_ready,
    input wire [31:0] command_generation,command_base,command_words,
    input wire [31:0] command_row_words,
    output reg active,scheduled,command_error,
    output wire reserve_valid,
    input wire reserve_ready,
    output reg reserve_bank,
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
    output reg tile_bank,
    output wire [63:0] tile_tag,
    output wire [63:0] tile_stream_tag,
    output wire tile_retain,
    output wire [9:0] tile_words
);
    localparam [1:0] RESERVE=0,FETCH=1,FILL=2;
    reg [1:0] state;
    reg [31:0] generation,fill_base,tile_base,fill_left,tile_left;
    reg [9:0] index;
    reg replay;
    reg [31:0] row_base,stream_base;
    // Replay is admitted only for rows <=1024 words. These counters never
    // represent a whole stream; keep that full-width count in tile_left.
    reg [10:0] row_words,row_left;
    wire reuse_command=ROW_REUSE && command_row_words!=0 &&
        command_row_words<=1024 && command_words>command_row_words;
    wire [31:0] chunk_limit=replay?32'd512:32'(TILE_WORDS);
    wire [31:0] issue_left=replay && {21'b0,row_left}<tile_left?{21'b0,row_left}:tile_left;
    wire enabled=rst_n && !clear;
    wire [32:0] range_end={1'b0,command_base}+{1'b0,command_words};
    assign command_ready=enabled && !active;
    assign reserve_words=fill_left<chunk_limit?fill_left[9:0]:chunk_limit[9:0];
    assign tile_words=issue_left<chunk_limit?issue_left[9:0]:chunk_limit[9:0];
    assign reserve_tag={generation,fill_base};
    assign fetch_tag=reserve_tag;
    assign fetch_address=fill_base;
    assign fetch_words=reserve_words;
    assign reserve_valid=enabled && active && fill_left!=0 && state==RESERVE;
    assign fetch_valid=enabled && active && state==FETCH;
    wire response_matches=response_tag==reserve_tag && response_index==index;
    assign fill_valid=enabled && active && state==FILL && response_valid && response_matches;
    assign response_ready=enabled && active && state==FILL && response_matches && fill_ready;
    assign response_mismatch=enabled && response_valid &&
        (!active || state!=FILL || !response_matches);
    assign fill_bank=reserve_bank;
    assign fill_tag=reserve_tag;
    assign fill_data=response_data;
    assign tile_valid=enabled && active && tile_left!=0;
    assign tile_tag={generation,tile_base};
    assign tile_stream_tag={generation,stream_base};
    assign tile_retain=replay && tile_left>{21'b0,row_left};
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            active<=0;scheduled<=0;command_error<=0;state<=RESERVE;
            generation<=0;fill_base<=0;tile_base<=0;fill_left<=0;tile_left<=0;
            index<=0;reserve_bank<=0;tile_bank<=0;
            replay<=0;row_base<=0;row_words<=0;row_left<=0;stream_base<=0;
        end else if(clear)begin active<=0;scheduled<=0;command_error<=0;state<=RESERVE;end
        else begin
            scheduled<=0;command_error<=0;
            if(command_valid && command_ready)begin
                if(command_words==0 || range_end>33'h100000000)command_error<=1;
                else begin
                    active<=1;state<=RESERVE;generation<=command_generation;
                    fill_base<=command_base;tile_base<=command_base;
                    replay<=reuse_command;row_base<=command_base;
                    row_words<=command_row_words[10:0];row_left<=command_row_words[10:0];stream_base<=command_base;
                    fill_left<=reuse_command?command_row_words:command_words;tile_left<=command_words;
                    index<=0;reserve_bank<=0;tile_bank<=0;
                end
            end else if(active)begin
                if(reserve_valid && reserve_ready)begin state<=FETCH;index<=0;end
                if(fetch_valid && fetch_ready)state<=FILL;
                if(fill_valid && fill_ready)begin
                    if(index==reserve_words-1'b1)begin
                        fill_base<=fill_base+{22'b0,reserve_words};
                        fill_left<=fill_left-{22'b0,reserve_words};
                        reserve_bank<=!reserve_bank;state<=RESERVE;index<=0;
                    end else index<=index+1'b1;
                end
                if(tile_valid && tile_ready)begin
                    stream_base<=stream_base+{22'b0,tile_words};
                    tile_left<=tile_left-{22'b0,tile_words};
                    if(replay && row_left=={1'b0,tile_words})begin
                        tile_base<=row_base;row_left<=row_words;tile_bank<=0;
                    end else begin
                        tile_base<=tile_base+{22'b0,tile_words};tile_bank<=!tile_bank;
                        if(replay)row_left<=row_left-{1'b0,tile_words};
                    end
                end
                if(fill_left==0 && tile_left==0)begin active<=0;scheduled<=1;end
            end
        end
    end
    generate if(TILE_WORDS<1 || TILE_WORDS>512)begin : bad_tile_size
        initial $error("TILE_WORDS must be in 1..512");
    end endgenerate
endmodule
