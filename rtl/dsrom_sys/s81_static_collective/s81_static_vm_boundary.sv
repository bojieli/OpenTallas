`timescale 1ns/1ps
// Actual VM-facing hardening boundary: registered request/write pins, explicit
// gather/reduce/raw ownership checks and fixed destination-row metadata pipe.
// This extraction preserves every edge of the combined 29-root component gate.
module s81_static_vm_boundary #(parameter integer MUT=0)(
 input wire clk,rst_n,read_slot,input wire[13:0]read_row,
 output reg[14:0]t_crq,output reg[2203:0]t_vm,
 input wire commit_gather,hc_reduce_slot,
 input wire[3:0]gather_we,input wire[59:0]gather_rows,input wire[2047:0]gather_data,input wire[31:0]gather_tag,
 input wire hc_write_slot,reduced_valid,reduced_error,reduced_last,
 input wire[15:0]reduced_seq,hc_expect_seq,input wire hc_expect_last,
 input wire[511:0]reduced_data,input wire[31:0]reduced_tag,input wire[1101:0]raw_sources,
 input wire[7:0]phy_rx_fault,phy_rx_valid,phy_rx_live,
 input wire issue_slot,raw_capture,raw_capture_payload_slot,raw_capture_meta_slot,
 input wire[2:0]raw_tx_count,input wire[515:0]host_rx,
 output wire pack_bad_out,output reg fault
);
 reg gather_mode_q;reg[13:0]reduce_row[0:17];integer p;
 always @(posedge clk)begin
  gather_mode_q<=commit_gather;reduce_row[0]<=gather_rows[13:0];
  for(p=1;p<18;p=p+1)reduce_row[p]<=reduce_row[p-1];
 end
 reg[2203:0]next_vm;reg pack_bad;reg[3:0]occupied;
 reg[550:0]word;integer k;
 assign pack_bad_out=pack_bad;
 always @*begin
  next_vm=0;pack_bad=0;occupied=0;word=0;
  if(|gather_we)begin
   if(gather_mode_q)begin
    for(integer j=0;j<4;j=j+1)if(gather_we[j])begin
     if(gather_rows[j*15+14])pack_bad=1;
     next_vm[j*551+:551]={gather_tag[7:0],gather_data[j*512+:512],16'hffff,gather_rows[j*15+:14],1'b1};occupied[j]=1;
    end
   end else if(!hc_reduce_slot)pack_bad=1;
  end
  if(hc_write_slot)begin
   if(occupied[0]||!reduced_valid||reduced_error||reduced_seq!=hc_expect_seq||reduced_last!=hc_expect_last)pack_bad=1;
   next_vm[0+:551]={reduced_tag[7:0],reduced_data,16'hffff,reduce_row[17],1'b1};occupied[0]=1;
  end
  if(reduced_valid!=hc_write_slot)pack_bad=1;
  for(integer j=0;j<2;j=j+1)begin
   word=raw_sources[j*551+:551];
   if(word[0])begin if(occupied[j])pack_bad=1;next_vm[j*551+:551]=word;occupied[j]=1;end
  end
  if(MUT==1 && hc_write_slot)next_vm[31]=~next_vm[31];
  if(pack_bad||fault)for(integer j=0;j<4;j=j+1)next_vm[j*551]=0;
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin t_crq<=0;t_vm<=0;fault<=0;end
  else begin
   t_crq<={read_row,read_slot};t_vm<=next_vm;
   if(pack_bad||(|phy_rx_fault)||(issue_slot&&raw_capture)||
      (raw_capture_payload_slot&&raw_capture_meta_slot)||raw_tx_count>1||
      (host_rx[0]&&host_rx[515]))fault<=1;
   for(integer j=0;j<8;j=j+1)if(phy_rx_valid[j]&&!phy_rx_live[j])fault<=1;
  end
 end
endmodule
