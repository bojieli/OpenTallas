`timescale 1ns/1ps
`default_nettype none
// A real five-clock hard-leaf candidate: four protected source FIFO16 writers,
// shared VM head registers/router/tickets, and direct serialized commit Gray publication.
// Queue held heads are internal registered storage; no redundant 8960-bit pin shadow.
module ot_hgi_dma_vm_bank9 #(parameter integer MUT=0)(
 input wire [3:0] source_clk,input wire vm_clk,rst_n,
 input wire [3:0] source_v,input wire [4*280-1:0] source_d,
 output wire [3:0] source_credit,source_done,queue_fault,
 output wire [4*281-1:0] dma_q,input wire [3:0] dma_done,output wire router_fault);
 wire [31:0] hv,he,ae,gray;wire [32*280-1:0] hd;
 for(genvar s=0;s<4;s++)begin:src
  ot_hgi_dma_vm_queue q(.wclk(source_clk[s]),.rclk(vm_clk),.rst_n(rst_n),
   .in_v(source_v[s]),.in_d(source_d[s*280+:280]),.credit(source_credit[s]),.fault(queue_fault[s]),
   .head_v(hv[s*8+:8]),.head_epoch(he[s*8+:8]),.head_d(hd[s*8*280+:8*280]),.ack_epoch(ae[s*8+:8]));
  ot_hgi_dma_vm_grayrecv e(.clk(source_clk[s]),.rst_n(rst_n),.gray(gray[s*8+:8]),.pulse(source_done[s]));
 end
 ot_hgi_dma_vm_router9 #(.MUT(MUT)) r(.clk(vm_clk),.rst_n(rst_n),.head_v(hv),.head_epoch(he),.head_d(hd),.ack_epoch(ae),
  .dma_q(dma_q),.dma_done(dma_done),.source_gray(gray),.fault(router_fault));
endmodule
module ot_hgi_dma_vm_grayrecv(input wire clk,rst_n,input wire [7:0] gray,output reg pulse);
 (* async_reg="true" *)reg [7:0] g1,g2;reg [7:0] cursor;
 function automatic [7:0] ungray(input [7:0] g);begin ungray[7]=g[7];for(integer i=6;i>=0;i--)ungray[i]=ungray[i+1]^g[i];end endfunction
 wire available=ungray(g2)!=cursor;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin g1<=0;g2<=0;cursor<=0;pulse<=0;end
 else begin g1<=gray;g2<=g1;pulse<=available;if(available)cursor<=cursor+1'b1;end
endmodule
`default_nettype wire
