`timescale 1ns/1ps
// Source-faithful projection of the sector decoder into four 64-bit leaves.
// Each leaf captures the SAME native packet and owns its own identical local
// pointer/decode state. Clocks come from one fixed-phase family; the die must
// deliver phi-R independently. No leaf consumes another leaf's pointer/reset.
// STATIC service never waits for a credit: an absent reserved credit faults.
module dsfd_host_sd_data64 #(
 parameter integer NS=1,KVS=1,ENG=-1,SLICE=0
)(input wire ck,rst_n,o_v,o_we,input wire[31:0]o_addr,
 input wire[63:0]o_d,input wire[1:0]marker_class,input wire[NS-1:0]hc_cr,
 output wire[64*NS-1:0]hw_data,output wire[NS-1:0]hw_valid,output wire fault);
 wire rn;
 ot_reset_sync rs(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 wire[255:0]full_data;
 for(genvar b=0;b<256;b=b+1)begin:g_input
  if(b>=64*SLICE && b<64*(SLICE+1))assign full_data[b]=o_d[b-64*SLICE];
  else if(b==64 || b==65)assign full_data[b]=marker_class[b-64];
  else assign full_data[b]=1'b0;
 end
 wire[9*NS-1:0]hc;wire[292*NS-1:0]hw;
 for(genvar s=0;s<NS;s=s+1)begin:g_stack
  assign hc[9*s+:9]={8'b0,hc_cr[s]};
  assign hw_data[64*s+:64]=hw[292*s+1+64*SLICE+:64];
  assign hw_valid[s]=hw[292*s];
 end
 // Unused projected datapaths are removed by synthesis; the queue, decoder
 // and all retained arithmetic remain actual source RTL.
 dsfd_host_sd #(.NS(NS),.KVS(KVS),.ENG(ENG),.STATIC(1))u_sd(
  .ck(ck),.rst_n(rn),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(full_data),
  .o_cr(),.hw(hw),.hc(hc),.host_ack_n(),.fault(fault));
endmodule

module dsfd_host_sd_control #(
 parameter integer NS=1,KVS=1,ENG=-1
)(input wire ck,rst_n,o_v,o_we,input wire[31:0]o_addr,
 input wire[1:0]marker_class,input wire[9*NS-1:0]hc,
 output wire[36*NS-1:0]hw_control,output wire o_cr,
 output wire[7:0]host_ack_n,output wire fault);
 wire rn;
 ot_reset_sync rs(.clk(ck),.async_rst_n(rst_n),.sync_rst_n(rn));
 wire[255:0]full_data={190'b0,marker_class,64'b0};
 wire[292*NS-1:0]hw;
 for(genvar s=0;s<NS;s=s+1)begin:g_stack
  assign hw_control[36*s+:36]={hw[292*s+257+:35],hw[292*s]};
 end
 dsfd_host_sd #(.NS(NS),.KVS(KVS),.ENG(ENG),.STATIC(1))u_sd(
  .ck(ck),.rst_n(rn),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(full_data),
  .o_cr(o_cr),.hw(hw),.hc(hc),.host_ack_n(host_ack_n),.fault(fault));
endmodule

// Wires-only parent. Raw assertion is common; each independent leaf performs
// its own conditioned release (2 edges + its existing 3-edge reset relay).
// At matched fixed-phase leaf clocks, zero service/calendar edges are added.
module dsfd_host_sd_sliced #(
 parameter integer NS=1,KVS=1,ENG=-1
)(input wire ck_control,input wire[3:0]ck_data,input wire rst_n,
 input wire o_v,o_we,input wire[31:0]o_addr,input wire[255:0]o_d,
 output wire o_cr,output wire[292*NS-1:0]hw,input wire[9*NS-1:0]hc,
 output wire[7:0]host_ack_n,output wire fault);
 wire[36*NS-1:0]ctrl;wire[NS-1:0]hc_cr;wire cf;wire[3:0]df;
 dsfd_host_sd_control #(.NS(NS),.KVS(KVS),.ENG(ENG))control(
  .ck(ck_control),.rst_n(rst_n),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),
  .marker_class(o_d[65:64]),.hc(hc),.hw_control(ctrl),.o_cr(o_cr),
  .host_ack_n(host_ack_n),.fault(cf));
 for(genvar s=0;s<NS;s=s+1)begin:g_rebuild
  assign hc_cr[s]=hc[9*s];
  // hw.valid is projected from the SW data leaf, beside its original pin.
  // The E control leaf therefore has no clock sink at the distant SW edge.
  assign hw[292*s+257+:35]=ctrl[36*s+1+:35];
 end
 for(genvar k=0;k<4;k=k+1)begin:g_data
  wire[64*NS-1:0]data;wire[NS-1:0]valid;
  dsfd_host_sd_data64 #(.NS(NS),.KVS(KVS),.ENG(ENG),.SLICE(k))leaf(
   .ck(ck_data[k]),.rst_n(rst_n),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),
   .o_d(o_d[64*k+:64]),.marker_class(o_d[65:64]),.hc_cr(hc_cr),
   .hw_data(data),.hw_valid(valid),.fault(df[k]));
  for(genvar s=0;s<NS;s=s+1)begin:g_stack
   assign hw[292*s+1+64*k+:64]=data[64*s+:64];
   if(k==0)assign hw[292*s]=valid[s];
  end
 end
 assign fault=cf|(|df);
endmodule
