`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of qkd_host_peer_link (same ports).  Class9 transport keeps its four reservation credits.
//  RX class9: normal_rx_d is also the no-reset register of the rx_d face; a peer word enters pq one edge after it (+1),
//    with its frame flags registered at the face, then moves through a head register phd (+1, full rate, valid/ready).
//    pn counts every held word (pq + phd), so the credit and overflow rules are the source's.  Credits conserved.
//  RX normal: cycle exact (normal_rx_v / normal_rx_d as the source).
//  TX normal: nhd head register on nq (+1 on the word and its reservation credit, full rate, valid/credit safe; nn counts
//    nq + nhd).  tx_d loads every edge, tx_v qualifies it.
//  Data registers (normal_rx_d, tx_d, peer_word, pq, nq, phd, nhd) carry no reset: every one is valid qualified.
module qkd_host_peer_link_r3 #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg normal_rx_v,output reg[527:0]normal_rx_d,input wire normal_rx_cr,
 output wire peer_rx_valid,output wire[511:0]peer_rx_data,input wire peer_rx_ready,
 input wire normal_tx_v,input wire[527:0]normal_tx_d,output reg normal_tx_cr,
 input wire peer_tx_valid,input wire[511:0]peer_tx_data,output wire peer_tx_ready,
 output reg tx_v,output reg[527:0]tx_d,input wire tx_cr,
 output wire drained,output reg fault);
 reg[527:0]nq[0:3];reg[511:0]pq[0:3];reg[1:0]nw,nr,pw,pr;
 reg[2:0]nn,pn,nf,pf;reg[2:0]physical;reg peer_pending,rr;
 reg[511:0]peer_word;reg[3:0]returns;
 reg rx_pk_q,rx_pk_bad_q;
 reg phd_v,nhd_v;reg[511:0]phd;reg[527:0]nhd;
 wire peer_frame=rx_d[527:524]==9;
 wire pq_wr=rx_pk_q&&!rx_pk_bad_q&&pn!=3'd4;
 wire peer_pop=peer_rx_valid&&peer_rx_ready;
 assign peer_rx_valid=phd_v&&!fault;assign peer_rx_data=phd;
 wire p_load=pf!=0&&(!phd_v||peer_pop);
 assign peer_tx_ready=!peer_pending&&!fault;
 wire take_peer=peer_tx_valid&&peer_tx_ready;
 wire emit=physical!=0&&!fault&&(nhd_v||peer_pending);
 wire choose_peer=peer_pending&&(!nhd_v||rr);
 wire normal_pop=emit&&!choose_peer;
 wire peer_send=emit&&choose_peer;
 wire n_load=nf!=0&&(!nhd_v||normal_pop);
 wire nq_wr=normal_tx_v&&nn!=3'd4;
 wire[4:0]next_returns={1'b0,returns}+5'(normal_rx_cr)+5'(peer_pop)-5'(returns!=0);
 assign drained=nn==0&&pn==0&&!peer_pending&&physical==4&&returns==0&&!rx_v&&!rx_pk_q&&!tx_v;
 always @(posedge ck)begin
  normal_rx_d<=rx_d;
  if(pq_wr)pq[pw]<=normal_rx_d[511:0];
  if(p_load)phd<=pq[pr];
  if(nq_wr)nq[nw]<=normal_tx_d;
  if(n_load)nhd<=nq[nr];
  if(take_peer)peer_word<=peer_tx_data;
  tx_d<=choose_peer?{4'd9,12'd0,peer_word ^ 512'(MUT==1)}:nhd;
 end
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin nw<=0;nr<=0;pw<=0;pr<=0;nn<=0;pn<=0;nf<=0;pf<=0;physical<=4;peer_pending<=0;rr<=0;returns<=0;rx_cr<=0;normal_rx_v<=0;normal_tx_cr<=0;tx_v<=0;fault<=0;rx_pk_q<=0;rx_pk_bad_q<=0;phd_v<=0;nhd_v<=0;end
  else begin
   rx_cr<=returns!=0;returns<=next_returns[3:0];if(next_returns[4])fault<=1;
   normal_rx_v<=rx_v&&!peer_frame&&!fault;
   rx_pk_q<=rx_v&&peer_frame;rx_pk_bad_q<=rx_d[523:512]!=0;
   normal_tx_cr<=normal_pop;tx_v<=emit;
   if(rx_pk_q&&(rx_pk_bad_q||pn==3'd4))fault<=1;
   if(pq_wr)pw<=pw+1'b1;
   if(p_load)begin pr<=pr+1'b1;phd_v<=1;end
   else if(peer_pop)phd_v<=0;
   pf<=pf+3'(pq_wr)-3'(p_load);
   pn<=pn+3'(pq_wr)-3'(peer_pop);
   if(normal_tx_v&&nn==3'd4)fault<=1;
   if(nq_wr)nw<=nw+1'b1;
   if(n_load)begin nr<=nr+1'b1;nhd_v<=1;end
   else if(normal_pop)nhd_v<=0;
   nf<=nf+3'(nq_wr)-3'(n_load);
   nn<=nn+3'(nq_wr)-3'(normal_pop);
   if(take_peer)peer_pending<=1;
   if(emit)begin
    rr<=!choose_peer;
    if(choose_peer)peer_pending<=0;
   end
   if(tx_cr&&physical==4&&!emit)fault<=1;
   else physical<=physical+3'(tx_cr)-3'(emit);
  end
 end
endmodule
