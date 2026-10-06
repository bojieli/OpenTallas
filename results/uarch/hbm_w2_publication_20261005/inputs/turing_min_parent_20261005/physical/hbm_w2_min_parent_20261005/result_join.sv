`timescale 1ns/1ps
// Caller identity FIFO, enqueued atomically with actual public start acceptance.
// Covers CHD7 posted operations +NOUT4 outstanding. No payload buffering/ready
// fiction: data follows the existing pin response edge. Bound descriptors live
// until every distinct row arrives; no release based on expected latency.
module ot_hbm_w2_parent_result_join #(
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
        wire [31:0] qa[0:NCTX-1],qb[0:NCTX-1];
        reg [31:0] qa_next[0:NCTX-1],qb_next[0:NCTX-1];
        wire [RW:0] qrows[0:NCTX-1];
        reg [RW:0] qrows_next[0:NCTX-1];
        wire [NCTX-1:0] qpair,qbound;
        reg [NCTX-1:0] qpair_next,qbound_next;
        wire [PW-1:0] wp,rp;
        reg [PW-1:0] wp_next,rp_next;
        wire [CW-1:0] cnt;
        reg [CW-1:0] cnt_next;
        wire [RW:0] next_row;
        reg [RW:0] next_row_next;
        wire [3:0] seen;
        reg [3:0] seen_next;
        wire failed;
        reg failed_next;
        wire config_ok=ctx_bound && ctx_rows!=0 && (!ctx_pair||ctx_rows==4);
        assign ctx_ready=cnt<NCTX && config_ok && (!failed && !view_fault);
        wire push=ctx_valid && ctx_ready;
        wire have=cnt!=0;
        wire pair=have && qpair[rp];
        wire in_range=have && qbound[rp] && {1'b0,rsp_row}<qrows[rp];
        wire in_order={1'b0,rsp_row}==next_row;
        wire unique_row=!pair || (rsp_row<4 && !seen[rsp_row[1:0]]);
        wire good=in_range && in_order && unique_row && (!failed && !view_fault);
        assign out_v=rsp_v && good;
        assign out_row=pair && rsp_row>=2?rsp_row-2:rsp_row;
        assign out_operation=pair && rsp_row>=2?qb[rp]:qa[rp];
        wire last=out_v && next_row+1'b1==qrows[rp];
        assign pair_complete=last && pair && seen==4'b0111 && rsp_row==3;
        assign fault=view_fault || failed || (rsp_v && !good);
        localparam MW=NCTX*(RW+67), CTW=PW*2+CW+RW+6, SW=MW+CTW;
        wire [SW-1:0] state_view,state_next;wire view_fault;
        assign {wp,rp,cnt,next_row,seen,failed}=state_view[MW+:CTW];
        assign state_next[MW+:CTW]={wp_next,rp_next,cnt_next,next_row_next,seen_next,failed_next};
        for(genvar k=0;k<NCTX;k=k+1)begin:metadata
          assign {qa[k],qb[k],qrows[k],qpair[k],qbound[k]}=state_view[k*(RW+67)+:RW+67];
          assign state_next[k*(RW+67)+:RW+67]={qa_next[k],qb_next[k],qrows_next[k],qpair_next[k],qbound_next[k]};
        end
        (* keep_hierarchy = 1 *) ot_hbm_w2_parent_protected_view #(.WIDTH(SW)) u_state(
         .clk(clk),.por_n(rst_n),.we(1'b1),.next_data(state_next),.data(state_view),.fault(view_fault));
        always @* begin
         wp_next=wp;rp_next=rp;cnt_next=cnt;next_row_next=next_row;seen_next=seen;failed_next=failed;
         qpair_next=qpair;qbound_next=qbound;
         for(integer k=0;k<NCTX;k=k+1)begin qa_next[k]=qa[k];qb_next[k]=qb[k];qrows_next[k]=qrows[k];end

                if ((ctx_valid && !config_ok)||(rsp_v && !good)) failed_next=1;
                case ({push,last})
                    2'b10:cnt_next=cnt+1'b1;
                    2'b01:cnt_next=cnt-1'b1;
                    default:;
                endcase
                if (push) wp_next=wp==NCTX-1?0:wp+1'b1;
                if (last) begin rp_next=rp==NCTX-1?0:rp+1'b1;next_row_next=0;seen_next=0;end
                else if (out_v) begin
                    next_row_next=next_row+1'b1;
                    if (pair) seen_next[rsp_row[1:0]]=1'b1;
                end

            if(push)begin
            qa_next[wp]=ctx_op_a;qb_next[wp]=ctx_op_b;qrows_next[wp]=ctx_rows;
            qpair_next[wp]=ctx_pair;qbound_next[wp]=ctx_bound;
            end
        end
    end endgenerate
endmodule
