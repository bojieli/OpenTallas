`timescale 1ns/1ps
// One continuous bulk-copy descriptor, real global result/scale offsets,
// and a single whole-operation barrier after actual L2 commits.
// Backend waits are unbounded here and must be measured in the token gate.
module ot_gpu_qwen_row_tiles #(
    parameter integer ENABLE_ROW_TILES=0,
    parameter integer ROWW=18
) (
    input wire clk,rst_n,start,
    input wire [ROWW-1:0] rows_total,global_base,
    input wire [31:0] weight_base,
    input wire [23:0] weight_lines,
    input wire [15:0] epoch,
    output wire bulk_valid,input wire bulk_ready,
    output wire [31:0] bulk_base,output wire [23:0] bulk_lines,
    output wire tile_valid,input wire tile_ready,
    output wire [8:0] tile_rows,
    output wire [ROWW-1:0] tile_global_base,
    output wire [11:0] tile_scale_base,
    output wire [15:0] tile_epoch,
    input wire l2_commit,
    input wire [15:0] commit_epoch,
    input wire [ROWW-1:0] commit_base,
    input wire [8:0] commit_rows,
    output wire arrive,output wire barrier_pending,input wire release_in,
    output reg done,output wire busy,output reg fault
);
    localparam IDLE=0,BULK=1,ISSUE=2,COMMIT=3,ADVANCE=4,BARRIER=5;
    reg [2:0] state;
    reg [ROWW-1:0] total_q,base_q,offset;
    reg [31:0] wb;
    reg [23:0] wl;
    reg [15:0] ep;
    reg arrive_sense;
    wire [ROWW:0] end_row={1'b0,global_base}+{1'b0,rows_total};
    wire [ROWW-1:0] remain=total_q-offset;
    assign tile_rows=(remain>256) ? 9'd256 : remain[8:0];
    assign tile_global_base=base_q+offset;
    // Scale SRAM addresses are partition-local; result addresses are global.
    assign tile_scale_base=offset[11:0];
    assign tile_epoch=ep;
    assign bulk_base=wb; assign bulk_lines=wl;
    assign bulk_valid=ENABLE_ROW_TILES && state==BULK;
    assign tile_valid=ENABLE_ROW_TILES && state==ISSUE;
    // Existing GPU tree is a sense-reversing barrier. Hold the new sense
    // through release and idle; do not emit an unqualified level pulse.
    assign arrive=arrive_sense;
    assign barrier_pending=ENABLE_ROW_TILES && state==BARRIER;
    assign busy=state!=IDLE;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            state<=IDLE;done<=0;fault<=0;offset<=0;total_q<=0;
            base_q<=0;ep<=0;wb<=0;wl<=0;arrive_sense<=0;
        end else begin
            done<=0;
            if(start && busy) fault<=1;
            if(l2_commit && state!=COMMIT) fault<=1;
            case(state)
                IDLE: if(start) begin
                    if(!ENABLE_ROW_TILES || rows_total==0 || rows_total>4096 ||
                       weight_lines==0 || end_row[ROWW]) fault<=1;
                    else begin
                        total_q<=rows_total;base_q<=global_base;offset<=0;
                        ep<=epoch;wb<=weight_base;wl<=weight_lines;
                        state<=BULK;
                    end
                end
                BULK: if(bulk_ready) state<=ISSUE;
                ISSUE: if(tile_ready) state<=COMMIT;
                COMMIT: if(l2_commit) begin
                    if(commit_epoch!=ep || commit_base!=tile_global_base ||
                       commit_rows!=tile_rows) fault<=1;
                    else if(remain<=256) begin
                        arrive_sense<=~arrive_sense;state<=BARRIER;
                    end
                    else begin offset<=offset+256;state<=ADVANCE;end
                end
                ADVANCE: state<=ISSUE;
                BARRIER: if(release_in==arrive_sense) begin state<=IDLE;done<=1;end
                default: begin state<=IDLE;fault<=1;end
            endcase
        end
    end
endmodule
