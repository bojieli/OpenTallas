`timescale 1ns/1ps
// Exclusive per-PC ownership keeps the complete legacy 17-bit tag namespace.
// normal_quiescent includes ALL read/write/held-response/relay debt. DMA claims
// only after that drain and relinquishes only after every tagged lease drains.
module ot_hbm_svc_dma_pc_owner #(
 parameter integer MUT_BYPASS_DRAIN=0,MUT_PREFIX_ROUTE=0,MUT_EARLY_RELEASE=0
) (
 input wire clk,rst,input wire dma_session,normal_quiescent,dma_outstanding,
 output reg dma_owner,
 input wire n_v,output wire n_rdy,input wire[29:0] n_addr,input wire[3:0] n_len,input wire[16:0] n_tag,
 input wire d_v,output wire d_rdy,input wire[29:0] d_addr,input wire[3:0] d_len,input wire[16:0] d_tag,
 output wire k_v,input wire k_rdy,output wire[29:0] k_addr,output wire[3:0] k_len,output wire[16:0] k_tag,
 input wire kr_v,output wire kr_rdy,input wire[16:0] kr_tag,input wire[3:0] kr_beat,input wire[255:0] kr_data,
 output wire n_rs_v,input wire n_rs_rdy,output wire[16:0] n_rs_tag,output wire[3:0] n_rs_beat,output wire[255:0] n_rs_data,
 output wire d_rs_v,input wire d_rs_rdy,output wire[16:0] d_rs_tag,output wire[3:0] d_rs_beat,output wire[255:0] d_rs_data
);
 wire claiming=dma_session && (normal_quiescent || MUT_BYPASS_DRAIN);
 assign n_rdy=!dma_owner && !claiming && k_rdy;
 assign d_rdy=dma_owner && k_rdy;
 assign k_v=dma_owner?d_v:(n_v && !claiming);
 assign k_addr=dma_owner?d_addr:n_addr;
 assign k_len=dma_owner?d_len:n_len;
 assign k_tag=dma_owner?d_tag:n_tag;
 wire response_owner=MUT_PREFIX_ROUTE?kr_tag[16]:dma_owner;
 assign n_rs_v=kr_v && !response_owner;assign d_rs_v=kr_v && response_owner;
 assign kr_rdy=dma_owner?d_rs_rdy:n_rs_rdy;
 assign n_rs_tag=kr_tag;assign d_rs_tag=kr_tag;
 assign n_rs_beat=kr_beat;assign d_rs_beat=kr_beat;
 assign n_rs_data=kr_data;assign d_rs_data=kr_data;
 always @(posedge clk)begin
   if(rst)dma_owner<=0;
   else if(!dma_owner && claiming)dma_owner<=1;
   else if(dma_owner && !dma_session && (!dma_outstanding || MUT_EARLY_RELEASE) && !d_v && !kr_v)dma_owner<=0;
`ifndef SYNTHESIS
   if(!rst && !dma_owner && claiming && kr_v)$fatal(1,"DMA ownership claimed before normal response drain");
`endif
 end
endmodule
