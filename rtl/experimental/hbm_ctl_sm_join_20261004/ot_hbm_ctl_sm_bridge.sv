`timescale 1ns/1ps
// Native control-command -> existing SM pass sequencer. One command may own several passes.
// The caller supplies source-compiled descriptors and reserves the entire no-ready result burst.
// No golden callback, synthetic eng_done, memory arithmetic, or automatic barrier release.
module ot_hbm_ctl_sm_bridge #(
    parameter integer SM_ENABLE=0, NC=8, RMAX=4096, XD=128
) (
    input wire clk, rst_n, cmd_v,
    output wire cmd_ready, output reg eng_done,
    input wire [3:0] cmd_op, cmd_ncol,
    input wire [7:0] cmd_idx, input wire [31:0] cmd_pos,
    input wire plan_v, output wire plan_ready,
    input wire [3:0] plan_cmd_op, input wire [7:0] plan_cmd_idx,
    input wire [31:0] plan_cmd_pos,
    input wire [$clog2(RMAX):0] plan_rows,
    input wire [7:0] plan_g, input wire plan_gs, input wire [1:0] plan_fmt,
    input wire [31:0] plan_base, input wire [23:0] plan_lines,
    input wire plan_last, result_reserved,
    output wire req_v, input wire req_ready, output wire [31:0] req_addr,
    output wire [9:0] req_tag, input wire rsp_v, input wire [9:0] rsp_tag,
    input wire [1087:0] rsp_data,
    input wire xw_en, input wire [$clog2(XD)-1:0] xw_addr,
    input wire [6:0] xw_grp, input wire [2047:0] xw_data,
    output wire rv, output wire [$clog2(RMAX)-1:0] rrow,
    output wire [NC*32-1:0] rdata, output wire sm_busy, output reg fault,
    output wire arrive, input wire release_in, output wire released
);
    localparam integer RW=$clog2(RMAX);
    localparam [2:0] IDLE=0, DESC=1, START=2, RUN=3, NEXT=4;
    reg [2:0] state;
    reg [RW:0] rows_q, rows_seen;
    reg [15:0] columns_q;
    reg [7:0] groups_q;
    reg gs_q, last_q, arrive_q;
    reg [1:0] fmt_q;
    reg [31:0] base_q;
    reg [23:0] lines_q;
    wire d_ready, sm_fault;
    wire matched = plan_cmd_op==cmd_op && plan_cmd_idx==cmd_idx && plan_cmd_pos==cmd_pos;
    wire legal = matched && plan_rows>0 && plan_rows<=RMAX && plan_g>0 && plan_lines>0 &&
                 plan_fmt<=2 && cmd_ncol>0 && cmd_ncol<=NC;
    wire available = !fault && !sm_fault && !sm_busy && released && result_reserved && legal;
    assign cmd_ready = state==IDLE && plan_v && available;
    assign plan_ready = ((state==IDLE && cmd_v) || state==NEXT) && available;
    wire take = plan_v && plan_ready;
    ot_hbm_accel_sm_v #(.ENABLE(SM_ENABLE),.SUB(4),.LBS(2),.LSB(16),.NC(NC),.IL(8),
      .RMAX(RMAX),.LEV(4),.XD(XD),.MAX_OUT(512)) u_sm (
      .clk(clk),.rst_n(rst_n),.start(state==START && !fault),
      .op_rows(rows_q),.op_c(columns_q),.op_g(groups_q),.op_gs(gs_q),.op_fmt(fmt_q),
      .busy(sm_busy),.d_valid(state==DESC && !fault),.d_ready(d_ready),
      .d_base(base_q),.d_lines(lines_q),.req_v(req_v),.req_ready(req_ready),
      .req_addr(req_addr),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
      .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
      .rv(rv),.rrow(rrow),.rdata(rdata),.fault(sm_fault),
      .arrive(arrive),.release_in(release_in),.released(released));
    always @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
        state<=IDLE; eng_done<=0; fault<=0; rows_seen<=0;
        rows_q<=0; columns_q<=0; groups_q<=0; gs_q<=0; fmt_q<=0;
        base_q<=0; lines_q<=0; last_q<=0; arrive_q<=0;
      end else begin
        eng_done<=0;
        if (sm_fault) fault<=1;
        if (take) begin
          rows_q<=plan_rows; columns_q<={12'd0,cmd_ncol}; groups_q<=plan_g;
          gs_q<=plan_gs; fmt_q<=plan_fmt; base_q<=plan_base; lines_q<=plan_lines;
          last_q<=plan_last; arrive_q<=arrive; rows_seen<=0; state<=DESC;
        end else if (!fault && !sm_fault) begin
          case(state)
            DESC: if(d_ready) state<=START;
            START: state<=RUN;
            RUN: begin
              if(rv) begin
                if(rows_seen>=rows_q || rrow>=rows_q) fault<=1;
                else rows_seen<=rows_seen+1'b1;
              end
              // released is initially true: changed arrive plus exact result count prevents early completion.
              // The real barrier owner must drive release_in after its own publication/consumer fence.
              if(rows_seen==rows_q && !rv && arrive!=arrive_q && released && !sm_busy) begin
                if(last_q) begin eng_done<=1; state<=IDLE; end
                else state<=NEXT;
              end
            end
            default: ;
          endcase
        end
      end
    end
endmodule
