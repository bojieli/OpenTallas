`timescale 1ns/1ps
`default_nettype none
module ot_hgi_dma_vm_transport8 #(parameter integer MUT=0)(
 input wire [3:0] source_clk,input wire vm_clk,rst_n,input wire [3:0] lease_grant,producer_busy,
 input wire [31:0] issue_v,input wire [32*281-1:0] source_packet,
 output wire [31:0] source_credit,source_done,queue_fault,output reg [3:0] drained,lease_fault,
 output wire [32*281-1:0] dma_q,input wire [31:0] dma_done,output wire [7:0] router_fault);
 wire [32*8-1:0] hv,he,ae;wire [32*8*280-1:0] hd;
 wire [31:0] vm_source_done;
 for(genvar s=0;s<4;s++)begin: src
 reg [7:0] outstanding[0:7],capacity[0:7];reg zero;
 always @*begin zero=!producer_busy[s];for(integer b=0;b<8;b++)zero=zero&&(outstanding[b]==0)&&(capacity[b]==0);end
 always @(posedge source_clk[s] or negedge rst_n)if(!rst_n)begin
 drained[s]<=1;lease_fault[s]<=0;for(integer b=0;b<8;b++)begin outstanding[b]<=0;capacity[b]<=0;end
 end else begin
 drained[s]<=zero;
 if(!lease_grant[s]&&!zero)lease_fault[s]<=1;
 for(integer b=0;b<8;b++)begin
 outstanding[b]<=outstanding[b]+{7'd0,issue_v[s*8+b]}-{7'd0,source_done[s*8+b]};
 capacity[b]<=capacity[b]+{7'd0,issue_v[s*8+b]}-{7'd0,source_credit[s*8+b]};
 if(source_done[s*8+b]&&outstanding[b]==0&&!issue_v[s*8+b])lease_fault[s]<=1;
 if(source_credit[s*8+b]&&capacity[b]==0&&!issue_v[s*8+b])lease_fault[s]<=1;
 end
 end
 for(genvar b=0;b<8;b++)begin: bank
 localparam integer I=s*8+b;
 ot_hgi_dma_vm_queue32 q(.wclk(source_clk[s]),.rclk(vm_clk),.rst_n(rst_n),
  .in_v(source_packet[I*281+280]),.in_d(source_packet[I*281+:280]),.credit(source_credit[I]),.fault(queue_fault[I]),
  .head_v(hv[I*8+:8]),.head_epoch(he[I*8+:8]),.head_d(hd[I*8*280+:8*280]),.ack_epoch(ae[I*8+:8]));
 ot_hgi_dma_vm_events32 e(.vclk(vm_clk),.sclk(source_clk[s]),.rst_n(rst_n),.events({2'd0,vm_source_done[I]}),.pulse(source_done[I]));
 end
 end
 for(genvar b=0;b<8;b++)begin: dstbank
 wire [31:0] bv,be,ba;wire [32*280-1:0] bd;wire [4*281-1:0] dpack;wire [3:0] dcommit,sd;
 for(genvar s=0;s<4;s++)begin: port_map
 assign bv[s*8+:8]=hv[(s*8+b)*8+:8];assign be[s*8+:8]=he[(s*8+b)*8+:8];
 assign bd[s*8*280+:8*280]=hd[(s*8+b)*8*280+:8*280];assign ae[(s*8+b)*8+:8]=ba[s*8+:8];
 assign dma_q[(s*8+b)*281+:281]=dpack[s*281+:281];assign dcommit[s]=dma_done[s*8+b];assign vm_source_done[s*8+b]=sd[s];
 end
 ot_hgi_dma_vm_router #(.MUT(MUT)) r(.clk(vm_clk),.rst_n(rst_n),.head_v(bv),.head_epoch(be),.head_d(bd),.ack_epoch(ba),
  .dma_q(dpack),.dma_done(dcommit),.source_done(sd),.fault(router_fault[b]));
 end
endmodule
`default_nettype wire
