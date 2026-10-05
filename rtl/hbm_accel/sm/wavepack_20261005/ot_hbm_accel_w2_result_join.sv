`timescale 1ns/1ps
// Caller identity FIFO, enqueued atomically with actual public start acceptance.
// Covers CHD7 posted operations +NOUT4 outstanding. No payload buffering/ready
// fiction: data follows the existing pin response edge. Bound descriptors live
// until every distinct row arrives; no release based on expected latency.
module ot_hbm_accel_w2_result_join #(
    parameter integer ENABLE=0,
    parameter integer RW=12,
    parameter integer NCTX=11
) (
    input wire clk,rst_n,
    input wire ctx_valid,
    output wire ctx_ready,
    input wire ctx_pair,ctx_bound,
    input wire [RW:0] ctx_rows,
    input wire [31:0] ctx_op_a,ctx_op_b,
    input wire rsp_v,
    input wire [RW-1:0] rsp_row,
    output wire out_v,
    output wire [RW-1:0] out_row,
    output wire [31:0] out_operation,
    output wire pair_complete,
    output wire fault
);
    generate if (!ENABLE) begin:g_off
        assign ctx_ready=1'b1;
        assign out_v=rsp_v;assign out_row=rsp_row;assign out_operation=ctx_op_a;
        assign pair_complete=1'b0;assign fault=1'b0;
    end else begin:g_restore
        localparam integer PW=$clog2(NCTX);
        localparam integer CW=$clog2(NCTX+1);
        reg [31:0] qa[0:NCTX-1],qb[0:NCTX-1];
        reg [RW:0] qrows[0:NCTX-1];
        reg [NCTX-1:0] qpair,qbound;
        reg [PW-1:0] wp,rp;
        reg [CW-1:0] cnt;
        reg [RW:0] next_row;
        reg [3:0] seen;
        reg failed;
        wire config_ok=ctx_bound && ctx_rows!=0 && (!ctx_pair||ctx_rows==4);
        assign ctx_ready=cnt<NCTX && config_ok && !failed;
        wire push=ctx_valid && ctx_ready;
        wire have=cnt!=0;
        wire pair=have && qpair[rp];
        wire in_range=have && qbound[rp] && {1'b0,rsp_row}<qrows[rp];
        wire in_order={1'b0,rsp_row}==next_row;
        wire unique_row=!pair || (rsp_row<4 && !seen[rsp_row[1:0]]);
        wire good=in_range && in_order && unique_row && !failed;
        assign out_v=rsp_v && good;
        assign out_row=pair && rsp_row>=2?rsp_row-2:rsp_row;
        assign out_operation=pair && rsp_row>=2?qb[rp]:qa[rp];
        wire last=out_v && next_row+1'b1==qrows[rp];
        assign pair_complete=last && pair && seen==4'b0111 && rsp_row==3;
        assign fault=failed || (rsp_v && !good);
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin wp<=0;rp<=0;cnt<=0;next_row<=0;seen<=0;failed<=0;end
            else begin
                if ((ctx_valid && !config_ok)||(rsp_v && !good)) failed<=1;
                case ({push,last})
                    2'b10:cnt<=cnt+1'b1;
                    2'b01:cnt<=cnt-1'b1;
                    default:;
                endcase
                if (push) wp<=wp==NCTX-1?0:wp+1'b1;
                if (last) begin rp<=rp==NCTX-1?0:rp+1'b1;next_row<=0;seen<=0;end
                else if (out_v) begin
                    next_row<=next_row+1'b1;
                    if (pair) seen[rsp_row[1:0]]<=1'b1;
                end
            end
        end
        always @(posedge clk) if (push) begin
            qa[wp]<=ctx_op_a;qb[wp]<=ctx_op_b;qrows[wp]<=ctx_rows;
            qpair[wp]<=ctx_pair;qbound[wp]<=ctx_bound;
        end
    end endgenerate
endmodule
