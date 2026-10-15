`timescale 1ns/1ps
// Exceptional class9 transport inserted on the real core W528 PHY boundary.
// Normal source retains its original four reservation credits. Peer producer
// uses a held valid/ready mailbox. The physical CDC owns four independent
// credits. Returning a normal credit means its packet left this queue, not
// that the remote lifecycle action completed; action ACK is a class9 event.
module qkd_host_peer_link #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg normal_rx_v,output reg[527:0]normal_rx_d,input wire normal_rx_cr,
 output wire peer_rx_valid,output wire[511:0]peer_rx_data,input wire peer_rx_ready,
 input wire normal_tx_v,input wire[527:0]normal_tx_d,output reg normal_tx_cr,
 input wire peer_tx_valid,input wire[511:0]peer_tx_data,output wire peer_tx_ready,
 output reg tx_v,output reg[527:0]tx_d,input wire tx_cr,
 output wire drained,output reg fault);
 reg[527:0]nq[0:3];reg[511:0]pq[0:3];reg[1:0]nw,nr,pw,pr;
 reg[2:0]nn,pn;reg[2:0]physical;reg peer_pending,rr;
 reg[511:0]peer_word;reg[3:0]returns;
 wire peer_frame=rx_d[527:524]==9;
 wire peer_pop=peer_rx_valid&&peer_rx_ready;
 assign peer_rx_valid=pn!=0&&!fault;assign peer_rx_data=pq[pr];
 assign peer_tx_ready=!peer_pending&&!fault;
 wire take_peer=peer_tx_valid&&peer_tx_ready;
 wire emit=physical!=0&&!fault&&(nn!=0||peer_pending);
 wire choose_peer=peer_pending&&(nn==0||rr);
 wire normal_pop=emit&&!choose_peer;
 wire peer_send=emit&&choose_peer;
 wire[4:0]next_returns={1'b0,returns}+5'(normal_rx_cr)+5'(peer_pop)-5'(returns!=0);
 assign drained=nn==0&&pn==0&&!peer_pending&&physical==4&&returns==0&&!rx_v&&!tx_v;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin nw<=0;nr<=0;pw<=0;pr<=0;nn<=0;pn<=0;physical<=4;peer_pending<=0;rr<=0;peer_word<=0;returns<=0;rx_cr<=0;normal_rx_v<=0;normal_rx_d<=0;normal_tx_cr<=0;tx_v<=0;tx_d<=0;fault<=0;end
  else begin
   rx_cr<=returns!=0;returns<=next_returns[3:0];if(next_returns[4])fault<=1;
   normal_rx_v<=rx_v&&!peer_frame&&!fault;normal_rx_d<=rx_d;
   normal_tx_cr<=normal_pop;tx_v<=emit;
   if(rx_v&&peer_frame)begin
    if(rx_d[523:512]!=0||pn==4)fault<=1;
    else begin pq[pw]<=rx_d[511:0];pw<=pw+1'b1;end
   end
   if(peer_pop)pr<=pr+1'b1;
   case({rx_v&&peer_frame&&rx_d[523:512]==0&&pn<4,peer_pop})
    2'b10:pn<=pn+1'b1;2'b01:pn<=pn-1'b1;default:;
   endcase
   if(normal_tx_v)begin
    if(nn==4)fault<=1;else begin nq[nw]<=normal_tx_d;nw<=nw+1'b1;end
   end
   if(normal_pop)nr<=nr+1'b1;
   case({normal_tx_v&&nn<4,normal_pop})2'b10:nn<=nn+1'b1;2'b01:nn<=nn-1'b1;default:;endcase
   if(take_peer)begin peer_pending<=1;peer_word<=peer_tx_data;end
   if(emit)begin
    rr<=!choose_peer;
    if(choose_peer)begin tx_d<={4'd9,12'd0,peer_word ^ 512'(MUT==1)};peer_pending<=0;end
    else tx_d<=nq[nr];
   end
   if(tx_cr&&physical==4&&!emit)fault<=1;
   else physical<=physical+3'(tx_cr)-3'(emit);
  end
 end
endmodule
