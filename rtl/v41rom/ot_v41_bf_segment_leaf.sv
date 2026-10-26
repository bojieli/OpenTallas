`timescale 1ns/1ps
// Generated from ot_v41_bf_col's actual segment reduction and output registers.
module ot_v41_bf_segment_leaf #(
 parameter integer NSEG=8,LV=5,MTP=1,EARLY=1,
 parameter [8:0] CUT=9'b1_0111_1011,
 parameter integer SW=$clog2(NSEG),TRW=SW+(MTP!=0?1:0)
)(input wire fclk,rst_pin,ze_d,in_v,
 input wire [TRW-1:0] in_tree,input wire [2:0] in_pos,
 input wire [31:0] in_val,input wire in_final,in_err,
 input wire [16*NSEG-1:0] rows,input wire [5*NSEG-1:0] indices,counts,
 output reg pv,output reg[31:0] pval,output reg[15:0] prow,
 output reg[4:0] pseg,pnseg,output reg[2:0] ppos,output reg perr,
 output wire fault);
 wire clk,rst_n;
 ot_v41_tile_clk u_tc(.fclk(fclk),.rst_pin(rst_pin),.ze_d(ze_d),.gclk(clk),.rst_n(rst_n));
 wire tv,te;wire[TRW-1:0] tt;wire[2:0] tp;wire[31:0] tq;
 ot_v41_segtree5 #(.CUT(CUT),.NT(NSEG<<(MTP!=0?1:0)),.LV(LV),.EARLY(EARLY),.QD(8)) u_tree
 (.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_tree(in_tree),.in_pos(in_pos),.in_val(in_val),
  .in_final(in_final),.in_err(in_err),.ov(tv),.otree(tt),.opos(tp),.oval(tq),.oerr(te),.fault(fault));
 wire[SW-1:0] seg=tt[SW-1:0];
 always @(posedge clk or negedge rst_n) if(!rst_n)pv<=1'b0;else pv<=tv&&!rows[16*seg+15];
 always @(posedge clk) begin
  pval<=tq;perr<=te;prow<=rows[16*seg +:16];pseg<=indices[5*seg +:5];pnseg<=counts[5*seg +:5];
  ppos<=MTP!=0?tp:3'd0;
 end
endmodule
