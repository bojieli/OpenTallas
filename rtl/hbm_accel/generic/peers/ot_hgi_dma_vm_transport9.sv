`timescale 1ns/1ps
`default_nettype none
module ot_hgi_dma_vm_transport9 #(parameter integer MUT=0)(
 input wire [3:0] source_clk,input wire vm_clk,rst_n,input wire [3:0] lease_grant,producer_busy,
 input wire [31:0] issue_v,input wire [32*281-1:0] source_packet,
 output wire [31:0] source_credit,source_done,queue_fault,output reg [3:0] drained,lease_fault,
 output wire [32*281-1:0] dma_q,input wire [31:0] dma_done,output wire [7:0] router_fault);
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
 end
 for(genvar b=0;b<8;b++)begin:dstbank
  wire [3:0] v,credit,done,fault,dcommit;wire [4*280-1:0] data;wire [4*281-1:0] packet;
  for(genvar s=0;s<4;s++)begin:map
   localparam integer I=s*8+b;
   assign v[s]=source_packet[I*281+280];assign data[s*280+:280]=source_packet[I*281+:280];
   assign source_credit[I]=credit[s];assign source_done[I]=done[s];assign queue_fault[I]=fault[s];
   assign dma_q[I*281+:281]=packet[s*281+:281];assign dcommit[s]=dma_done[I];
  end
  ot_hgi_dma_vm_bank9 #(.MUT(MUT)) f(.source_clk(source_clk),.vm_clk(vm_clk),.rst_n(rst_n),
   .source_v(v),.source_d(data),.source_credit(credit),.source_done(done),.queue_fault(fault),
   .dma_q(packet),.dma_done(dcommit),.router_fault(router_fault[b]));
 end
endmodule
`default_nettype wire
