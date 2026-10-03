`timescale 1ns/1ps
// Reuses two ranks x32 ACTUAL 64B shared services. No SRAM/CDC replication.
// Caller and service share the streaming clock. Warm reset must drain first;
// por_n is cold POR only. A paused interface preserves all accepted ownership.
module ot_gpu_qwen_kv_shared_router #(parameter ENABLE=0)(
 input wire clk, por_n, run_enable,
 input wire kv_valid, kv_write, input wire kv_rank, input wire [4:0] kv_SM,
 input wire [9:0] kv_addr, input wire [511:0] kv_wdata,
 output reg kv_ready, kv_done, input wire kv_done_ready,
 output reg [511:0] kv_rdata,
 input wire [63:0] native_valid, native_write,
 input wire [639:0] native_addr, input wire [32767:0] native_wdata,
 output reg [63:0] native_ready, native_done, input wire [63:0] native_done_ready,
 output reg [32767:0] native_rdata,
 output reg [63:0] service_valid, service_write,
 output reg [639:0] service_addr, output reg [32767:0] service_wdata,
 input wire [63:0] service_ready, service_done,
 input wire [32767:0] service_rdata, output reg [63:0] service_done_ready,
 output reg fault, output wire drained
);
 reg [63:0] live, KV_owner, prefer_KV;
 reg KV_live; reg [5:0] KV_destination;
 wire active=ENABLE && por_n && run_enable && !fault;
 wire [5:0] requested={kv_rank,kv_SM};
 assign drained=(live==0) && !KV_live;
 integer i;
 reg choose_KV;
 always @* begin
  kv_ready=0;kv_done=0;kv_rdata=0;
  native_ready=0;native_done=0;native_rdata=0;
  service_valid=0;service_write=0;service_addr=0;service_wdata=0;service_done_ready=0;
  choose_KV=0;
  if(active) for(i=0;i<64;i=i+1) begin
   if(live[i]) begin
    if(KV_owner[i]) begin
     if(KV_live && KV_destination==i) begin
      kv_done=service_done[i]; kv_rdata=service_rdata[i*512+:512];
      service_done_ready[i]=kv_done_ready;
     end
    end else begin
     native_done[i]=service_done[i]; native_rdata[i*512+:512]=service_rdata[i*512+:512];
     service_done_ready[i]=native_done_ready[i];
    end
   end else begin
    choose_KV=kv_valid && !KV_live && requested==i && (!native_valid[i] || prefer_KV[i]);
    service_valid[i]=choose_KV || native_valid[i];
    service_write[i]=choose_KV ? kv_write : native_write[i];
    service_addr[i*10+:10]=choose_KV ? kv_addr : native_addr[i*10+:10];
    service_wdata[i*512+:512]=choose_KV ? kv_wdata : native_wdata[i*512+:512];
    if(choose_KV) kv_ready=service_ready[i];
    else native_ready[i]=service_ready[i];
   end
  end
 end
 integer j;
 always @(posedge clk or negedge por_n) begin
  if(!por_n) begin live<=0; KV_owner<=0; prefer_KV<=0;
    KV_live<=0; KV_destination<=0; fault<=0; end
  else if(active) for(j=0;j<64;j=j+1) begin
   if(service_done[j] && !live[j]) fault<=1; // stale/unowned response cannot retire.
   if(service_valid[j] && service_ready[j]) begin
    live[j]<=1;
    if(kv_valid && kv_ready && requested==j) begin
     KV_owner[j]<=1; prefer_KV[j]<=0; KV_live<=1; KV_destination<=requested;
    end else begin KV_owner[j]<=0; prefer_KV[j]<=1; end
   end
   if(service_done[j] && service_done_ready[j] && live[j]) begin
    live[j]<=0;
    if(KV_owner[j]) KV_live<=0;
   end
  end
 end
endmodule
