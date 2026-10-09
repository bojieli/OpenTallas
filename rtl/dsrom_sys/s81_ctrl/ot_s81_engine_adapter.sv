`timescale 1ns/1ps
// Native S81 command pulses need buffering before a ready/valid CDC FIFO.
// Both queues have depth8; the sequencer's8 outstanding credits cover queued,
// executing and completed-but-not-returned descriptors together. Neither FIFO
// capacity nor a buffered command returns a credit: only a validated done does.
module ot_s81_pulse_cdc #(parameter integer W=84, QD=8)(
 input wire s_clk,s_rst_n, input wire i_v,input wire[W-1:0] i_d,
 output wire i_accept,output reg fault,
 input wire d_clk,d_rst_n,output wire o_v,input wire o_r,output wire[W-1:0] o_d
);
 localparam integer AW=$clog2(QD);
 reg[W-1:0] q[0:QD-1]; reg[AW-1:0] wp,rp;reg[AW:0] count;
 wire fready;wire pop=(count!=0)&&fready;
 assign i_accept=(count<QD)||pop;
 wire push=i_v&&i_accept;
 wire unused_over,unused_under;
 ot_async_fifo #(.WIDTH(W),.DEPTH(QD)) u_fifo(
 .wr_clk(s_clk),.wr_rst_n(s_rst_n),.wr_valid(count!=0),.wr_ready(fready),.wr_data(q[rp]),.wr_overflow(unused_over),
 .rd_clk(d_clk),.rd_rst_n(d_rst_n),.rd_valid(o_v),.rd_ready(o_r),.rd_data(o_d),.rd_underflow(unused_under));
 always @(posedge s_clk or negedge s_rst_n) begin
  if(!s_rst_n) begin wp<=0;rp<=0;count<=0;fault<=0;end
  else begin
   if(i_v&&!i_accept) fault<=1;
   if(push) begin q[wp]<=i_d;wp<=wp+1'b1;end
   if(pop) rp<=rp+1'b1;
   case({push,pop}) 2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:count<=count;endcase
  end
 end
endmodule

module ot_s81_engine_adapter #(parameter integer QD=8, MUT=0)(
 input wire c_clk,c_rst_n,input wire c_cmd_v,input wire[83:0] c_cmd_d,
 output reg c_done_v,output reg[7:0] c_done_tag,output wire fault,output wire online,
 input wire e_clk,e_rst_n,output wire e_cmd_v,output wire[83:0] e_cmd_d,
 input wire e_cmd_ready,input wire e_inputs_present,
 input wire e_done_v,input wire[7:0] e_done_tag
);
 localparam integer CW=$clog2(QD+1);
 wire arst_n=c_rst_n&&e_rst_n;
 wire c_run,e_run;
 ot_reset_sync u_cr(.clk(c_clk),.async_rst_n(arst_n),.sync_rst_n(c_run));
 ot_reset_sync u_er(.clk(e_clk),.async_rst_n(arst_n),.sync_rst_n(e_run));
 reg[255:0] cpending,epending;reg[CW-1:0] cused,eused;
 reg cf,ef;
 (* async_reg="true" *) reg ef_c1,ef_c2,eonline_c1,eonline_c2;
 assign online=c_run&&eonline_c2;
 assign fault=cf||ef_c2;
 wire[7:0] ctag={c_cmd_d[83],c_cmd_d[6:0]};
 wire cv,cr;wire[83:0] cd;wire cmd_accept,cmd_fault;
 wire dv,dr;wire[7:0] dt;wire done_accept,done_fault;
 wire return_ok=dv&&cpending[dt]&&(cused!=0);
 wire admit=c_cmd_v&&cmd_accept&&!cpending[ctag]&&((cused<QD)||return_ok);
 wire[83:0] payload=(MUT==1)?(c_cmd_d^(84'd1<<73)):c_cmd_d;
 ot_s81_pulse_cdc #(.W(84),.QD(QD)) u_cmd(
 .s_clk(c_clk),.s_rst_n(c_run),.i_v(admit),.i_d(payload),.i_accept(cmd_accept),.fault(cmd_fault),
 .d_clk(e_clk),.d_rst_n(e_run),.o_v(cv),.o_r(cr),.o_d(cd));
 wire[7:0] etag={cd[83],cd[6:0]};
 assign e_cmd_d=cd;
 assign e_cmd_v=cv&&e_inputs_present&&!epending[etag]&&(eused<QD);
 assign cr=e_cmd_v&&e_cmd_ready;
 wire complete=e_done_v&&epending[e_done_tag]&&(eused!=0)&&done_accept;
 wire[7:0] completion=(MUT==2)?(e_done_tag^8'h80):e_done_tag;
 ot_s81_pulse_cdc #(.W(8),.QD(QD)) u_done(
 .s_clk(e_clk),.s_rst_n(e_run),.i_v(complete),.i_d(completion),.i_accept(done_accept),.fault(done_fault),
 .d_clk(c_clk),.d_rst_n(c_run),.o_v(dv),.o_r(dr),.o_d(dt));
 assign dr=1'b1;
 always @(posedge c_clk or negedge c_run) begin
  if(!c_run) begin cpending<=0;cused<=0;cf<=0;c_done_v<=0;c_done_tag<=0;ef_c1<=0;ef_c2<=0;eonline_c1<=0;eonline_c2<=0;end
  else begin
   ef_c1<=ef;ef_c2<=ef_c1;eonline_c1<=e_run;eonline_c2<=eonline_c1;
   c_done_v<=return_ok;
   if(return_ok) begin c_done_tag<=dt;cpending[dt]<=0;end
   if(admit) cpending[ctag]<=1;
   case({admit,return_ok}) 2'b10:cused<=cused+1'b1;2'b01:cused<=cused-1'b1;default:cused<=cused;endcase
   if((c_cmd_v&&!admit)||(dv&&!return_ok)||cmd_fault) cf<=1;
  end
 end
 always @(posedge e_clk or negedge e_run) begin
  if(!e_run) begin epending<=0;eused<=0;ef<=0;end
  else begin
   if(complete) epending[e_done_tag]<=0;
   if(cr) epending[etag]<=1;
   case({cr,complete}) 2'b10:eused<=eused+1'b1;2'b01:eused<=eused-1'b1;default:eused<=eused;endcase
   if((e_done_v&&!complete)||(cv&&epending[etag])||done_fault) ef<=1;
  end
 end
endmodule
