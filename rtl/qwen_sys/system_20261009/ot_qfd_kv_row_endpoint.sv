`timescale 1ns/1ps
// Distributed held heads: consume each (PC,ID64,half) once locally, then
// return an explicit ID-tagged acknowledgment through the real reverse link.
// The PC FIFO may keep broadcasting the same head while the ack is in flight.
module ot_qfd_kv_row_endpoint #(
 parameter integer ENABLE=0,STACK=0,ROW=0,DEPTH=8
)(
 input wire clk,rst_n,input wire [6:0] rr,
 input wire [31:0] h_v,input wire [63:0] h_need,input wire [2047:0] h_id,
 input wire [8191:0] h_data,input wire [351:0] h_tile0,h_tile1,
 input wire [223:0] h_loc0,h_loc1,input wire [63:0] h_sel0,h_sel1,
 input wire [31:0] h_isk,h_tail,input wire [127:0] h_tail_lanes,
 input wire [31:0] tile_credit_return,
 output wire [2:0] row_v,output wire [842:0] row_data,
 output wire [2:0] ack_v,output wire [212:0] ack_data,output wire fault
);
 (* keep *) reg [63:0] last_id[0:2][0:31];
 (* keep *) reg [1:0] done[0:2][0:31];
 (* keep *) reg seen[0:2][0:31];
 reg bad;reg [63:0] eligible;integer p,c;
 always @*begin
  bad=0;eligible=h_need;
  for(integer n=0;n<32;n=n+1)begin
   if(last_id[0][n]!=last_id[1][n]||last_id[0][n]!=last_id[2][n]||
      done[0][n]!=done[1][n]||done[0][n]!=done[2][n]||
      seen[0][n]!=seen[1][n]||seen[0][n]!=seen[2][n])bad=1;
   if(h_v[n]&&seen[0][n]&&h_id[n*64+:64]<last_id[0][n])bad=1;
   if(seen[0][n]&&h_id[n*64+:64]==last_id[0][n])eligible[n*2+:2]=h_need[n*2+:2]&~done[0][n];
  end
 end
 reg poisoned;wire core_fault;wire [63:0] grants;
 wire safe=ENABLE&&!poisoned&&!bad&&!core_fault;
 wire [2:0] raw_v;wire[842:0]raw_data;
 ot_qfd_kv_row_arb #(.ENABLE(ENABLE),.STACK(STACK),.ROW(ROW),.DEPTH(DEPTH)) u_row(
  .clk(clk),.rst_n(rst_n),.rr(rr),.h_v(safe?h_v:32'd0),.h_need(eligible),
  .h_data(h_data),.h_tile0(h_tile0),.h_tile1(h_tile1),.h_loc0(h_loc0),.h_loc1(h_loc1),
  .h_sel0(h_sel0),.h_sel1(h_sel1),.h_isk(h_isk),.h_tail(h_tail),.h_tail_lanes(h_tail_lanes),
  .tile_credit_return(safe?tile_credit_return:32'd0),.h_grant(grants),
  .row_v(raw_v),.row_data(raw_data),.fault(core_fault));
 reg[2:0]av;reg[212:0]ad;reg[2:0] next_av;reg[212:0]next_ad;integer slot;
 always @*begin
  next_av=0;next_ad=0;slot=0;
  for(integer n=0;n<32;n=n+1)if(grants[n*2+:2]!=0&&slot<3)begin
   next_av[slot]=1;next_ad[slot*71+:71]={h_id[n*64+:64],5'(n),grants[n*2+:2]};slot=slot+1;
  end
 end
 assign row_v=safe?raw_v:3'd0;assign row_data=raw_data;
 assign ack_v=safe?av:3'd0;assign ack_data=ad;
 assign fault=poisoned||bad||core_fault;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   poisoned<=0;av<=0;ad<=0;
   for(c=0;c<3;c=c+1)for(p=0;p<32;p=p+1)begin last_id[c][p]<=0;done[c][p]<=0;seen[c][p]<=0;end
  end else begin
   poisoned<=poisoned||(ENABLE&&bad);av<=safe?next_av:3'd0;ad<=next_ad;
   if(safe)for(c=0;c<3;c=c+1)for(p=0;p<32;p=p+1)if(h_v[p])begin
    last_id[c][p]<=h_id[p*64+:64];seen[c][p]<=1;
    done[c][p]<=((seen[0][p]&&last_id[0][p]==h_id[p*64+:64])?done[0][p]:2'd0)|grants[p*2+:2];
   end
  end
 end
endmodule
