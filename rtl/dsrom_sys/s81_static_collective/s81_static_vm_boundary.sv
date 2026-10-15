`timescale 1ns/1ps
// Actual VM-facing hardening boundary: registered request/write pins, explicit
// gather/reduce/raw ownership checks and fixed destination-row metadata pipe.
// This extraction preserves every edge of the combined 29-root component gate.
module s81_static_vm_boundary #(parameter integer MUT=0,parameter integer PINCAP=0)(
 input wire clk,rst_n,read_slot,input wire[13:0]read_row,
 output wire[14:0]t_crq,output wire[2203:0]t_vm,
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
 // PINCAP=1 (S-ELEM-B 10-15, CTS gate of the first kit: in->reg -62 ps through the pack/valid logic, pack_bad_out
 // in->out -219 ps, raw_sources[0]/hc_write_slot fanning out to 539-1087 loads, rst_n 2,220 loads): every WRITE-path
 // input is captured in a pin register, so t_vm leaves one edge later (+1 fixed edge collective->VM write; the VM read
 // request t_crq is unchanged: read_slot/read_row are already pin->flop and the read response timing must not move).
 // pack_bad_out is registered (+1, fault diagnosis only). Only valid bits / t_crq valid / fault carry the reset.
 wire c_commit_gather,c_hc_reduce_slot,c_hc_write_slot,c_reduced_valid,c_reduced_error,c_reduced_last,c_hc_expect_last;
 wire[3:0]c_gather_we;wire[59:0]c_gather_rows;wire[2047:0]c_gather_data;wire[31:0]c_gather_tag;
 wire[15:0]c_reduced_seq,c_hc_expect_seq;wire[511:0]c_reduced_data;wire[31:0]c_reduced_tag;wire[1101:0]c_raw_sources;
 wire[7:0]c_phy_rx_fault,c_phy_rx_valid,c_phy_rx_live;wire c_issue_slot,c_raw_capture,c_raw_capture_payload_slot,c_raw_capture_meta_slot;
 wire[2:0]c_raw_tx_count;wire[515:0]c_host_rx;
 localparam integer CW=1+1+1+1+1+1+1+4+60+2048+32+16+16+512+32+1102+8+8+8+1+1+1+1+3+516;
 wire[CW-1:0]cin={commit_gather,hc_reduce_slot,hc_write_slot,reduced_valid,reduced_error,reduced_last,hc_expect_last,
  gather_we,gather_rows,gather_data,gather_tag,reduced_seq,hc_expect_seq,reduced_data,reduced_tag,raw_sources,
  phy_rx_fault,phy_rx_valid,phy_rx_live,issue_slot,raw_capture,raw_capture_payload_slot,raw_capture_meta_slot,raw_tx_count,host_rx};
 wire[CW-1:0]cq;
 generate if(PINCAP)begin:g_cap reg[CW-1:0]q;always @(posedge clk)q<=cin;assign cq=q;end
 else begin:g_nocap assign cq=cin;end endgenerate
 assign {c_commit_gather,c_hc_reduce_slot,c_hc_write_slot,c_reduced_valid,c_reduced_error,c_reduced_last,c_hc_expect_last,
  c_gather_we,c_gather_rows,c_gather_data,c_gather_tag,c_reduced_seq,c_hc_expect_seq,c_reduced_data,c_reduced_tag,c_raw_sources,
  c_phy_rx_fault,c_phy_rx_valid,c_phy_rx_live,c_issue_slot,c_raw_capture,c_raw_capture_payload_slot,c_raw_capture_meta_slot,c_raw_tx_count,c_host_rx}=cq;
 // b7 (native audit of the CLOSED b6: rst_n capture 271.3 > 190 = the raw reset pin as recovery input of the reset
 // flops; t_crq launches up to 249.4 > 220 = DFFASRHQNx1 async-reset output registers): a registered local reset relay
 // (initialization +3 edges, never in a normal schedule) and plain output registers for the t_crq row bits.
 wire rst_l;
 generate if(PINCAP)begin:g_rr
  ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_l));
 end else begin:g_norr assign rst_l=rst_n; end endgenerate
 reg gather_mode_q;reg[13:0]reduce_row[0:17];integer p;
 always @(posedge clk)begin
  gather_mode_q<=c_commit_gather;reduce_row[0]<=c_gather_rows[13:0];
  for(p=1;p<18;p=p+1)reduce_row[p]<=reduce_row[p-1];
 end
 reg[2203:0]next_vm;reg pack_bad;reg[3:0]occupied;
 reg[550:0]word;integer k;
 reg pack_bad_q;
 always @(posedge clk or negedge rst_l) if(!rst_l) pack_bad_q<=1'b0; else pack_bad_q<=pack_bad;
 assign pack_bad_out=PINCAP ? pack_bad_q : pack_bad;
 always @*begin
  next_vm=0;pack_bad=0;occupied=0;word=0;
  if(|c_gather_we)begin
   if(gather_mode_q)begin
    for(integer j=0;j<4;j=j+1)if(c_gather_we[j])begin
     if(c_gather_rows[j*15+14])pack_bad=1;
     next_vm[j*551+:551]={c_gather_tag[7:0],c_gather_data[j*512+:512],16'hffff,c_gather_rows[j*15+:14],1'b1};occupied[j]=1;
    end
   end else if(!c_hc_reduce_slot)pack_bad=1;
  end
  if(c_hc_write_slot)begin
   if(occupied[0]||!c_reduced_valid||c_reduced_error||c_reduced_seq!=c_hc_expect_seq||c_reduced_last!=c_hc_expect_last)pack_bad=1;
   next_vm[0+:551]={c_reduced_tag[7:0],c_reduced_data,16'hffff,reduce_row[17],1'b1};occupied[0]=1;
  end
  if(c_reduced_valid!=c_hc_write_slot)pack_bad=1;
  for(integer j=0;j<2;j=j+1)begin
   word=c_raw_sources[j*551+:551];
   if(word[0])begin if(occupied[j])pack_bad=1;next_vm[j*551+:551]=word;occupied[j]=1;end
  end
  if(MUT==1 && c_hc_write_slot)next_vm[31]=~next_vm[31];
  if(pack_bad||fault)for(integer j=0;j<4;j=j+1)next_vm[j*551]=0;
 end
 // PINCAP: data bits carry no reset (only the four valid bits are reset)
 reg[2203:0]vm_q,vm_full;reg[3:0]vm_v;
 generate if(PINCAP)begin:g_data
  always @(posedge clk)vm_q<=next_vm;
  for(genvar j=0;j<4;j=j+1)begin:g_w assign t_vm[j*551+:551]={vm_q[j*551+1+:550],vm_v[j]};end
 end else begin:g_full
  assign t_vm=vm_full;
 end endgenerate
 reg crq_v;reg[13:0]crq_row_r,crq_row_p;
 always @(posedge clk)crq_row_p<=read_row;
 assign t_crq={PINCAP ? crq_row_p : crq_row_r,crq_v};
 always @(posedge clk or negedge rst_l)begin
  if(!rst_l)begin crq_v<=0;crq_row_r<=0;fault<=0;
   vm_v<=0;vm_full<=0;end
  else begin
   crq_v<=read_slot;crq_row_r<=read_row;
   for(integer j=0;j<4;j=j+1)vm_v[j]<=next_vm[j*551];
   vm_full<=next_vm;
   if(pack_bad||(|c_phy_rx_fault)||(c_issue_slot&&c_raw_capture)||
      (c_raw_capture_payload_slot&&c_raw_capture_meta_slot)||c_raw_tx_count>1||
      (c_host_rx[0]&&c_host_rx[515]))fault<=1;
   for(integer j=0;j<8;j=j+1)if(c_phy_rx_valid[j]&&!c_phy_rx_live[j])fault<=1;
  end
 end
endmodule
