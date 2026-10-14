`timescale 1ns/1ps
`default_nettype none
// A real five-clock hard-leaf candidate: four protected source FIFO16 writers,
// shared VM head registers/router/tickets, and direct serialized commit Gray publication.
// Queue held heads are internal registered storage; no redundant 8960-bit pin shadow.
module ot_hgi_dma_vm_bank10 #(parameter integer MUT=0)(
 input wire [3:0] source_clk,input wire vm_clk,rst_n,
 input wire [3:0] source_v,input wire [4*280-1:0] source_d,
 output wire [3:0] source_credit,source_done,queue_fault,
 output wire [4*281-1:0] dma_q,input wire [3:0] dma_done,output wire router_fault,output wire [3:0] source_ready,output wire vm_ready);
 wire [4:0] vr;
 ot_rst_relay #(.REGIONS(5),.SYNC_STAGES(2),.TREE_STAGES(1)) vm_reset(.clk(vm_clk),.rst_n_in(rst_n),.rst_n(vr));
 assign vm_ready=vr[4];
 wire [31:0] hv,he,ae,gray;wire [32*280-1:0] hd;
 for(genvar s=0;s<4;s++)begin:src
  wire [1:0] sr;
  ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) source_reset(.clk(source_clk[s]),.rst_n_in(rst_n),.rst_n(sr));
  (* async_reg="true" *) reg vm_ready1,vm_ready2;
  always @(posedge source_clk[s] or negedge sr[1]) if(!sr[1])begin vm_ready1<=0;vm_ready2<=0;end else begin vm_ready1<=vm_ready;vm_ready2<=vm_ready1;end
  assign source_ready[s]=sr[0]&&vm_ready2;
  ot_hgi_dma_vm_queue10 q(.wclk(source_clk[s]),.rclk(vm_clk),.w_rst_n(sr[0]),.r_rst_n(vr[s]),
   .in_v(source_v[s]),.in_d(source_d[s*280+:280]),.credit(source_credit[s]),.fault(queue_fault[s]),
   .head_v(hv[s*8+:8]),.head_epoch(he[s*8+:8]),.head_d(hd[s*8*280+:8*280]),.ack_epoch(ae[s*8+:8]));
  ot_hgi_dma_vm_grayrecv10 #(.MUT(MUT)) e(.clk(source_clk[s]),.rst_n(sr[1]),.gray(gray[s*8+:8]),.pulse(source_done[s]));
 end
 ot_hgi_dma_vm_router9 #(.MUT(MUT)) r(.clk(vm_clk),.rst_n(vr[4]),.head_v(hv),.head_epoch(he),.head_d(hd),.ack_epoch(ae),
  .dma_q(dma_q),.dma_done(dma_done),.source_gray(gray),.fault(router_fault));
endmodule
module ot_hgi_dma_vm_grayrecv10 #(parameter integer MUT=0)(input wire clk,rst_n,input wire [7:0] gray,output reg pulse);
 (* async_reg="true" *)reg [7:0] g1,g2;reg [7:0] cursor;
 function automatic [7:0] ungray(input [7:0] g);begin ungray[7]=g[7];for(integer i=6;i>=0;i--)ungray[i]=ungray[i+1]^g[i];end endfunction
 wire available=ungray(g2)!=cursor;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin g1<=0;g2<=0;cursor<=((MUT==10)?8'd1:8'd0);pulse<=0;end
 else begin g1<=gray;g2<=g1;pulse<=available;if(available)cursor<=cursor+1'b1;end
endmodule
`default_nettype wire
