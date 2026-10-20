`timescale 1ns/1ps
// Exceptional class9 transport inserted on the real core W528 PHY boundary.
// Normal source retains its original four reservation credits. Peer producer
// uses a held valid/ready mailbox. The physical CDC owns four independent
// credits. Returning a normal credit means its packet left this queue, not
// that the remote lifecycle action completed; action ACK is a class9 event.
module qkd_host_peer_link #(parameter integer MUT=0, parameter integer SAFE_SRAM=0)(
 input wire ck,rst_n,
 input wire rx_v,input wire[527:0]rx_d,output reg rx_cr,
 output reg normal_rx_v,output reg[527:0]normal_rx_d,input wire normal_rx_cr,
 output wire peer_rx_valid,output wire[511:0]peer_rx_data,input wire peer_rx_ready,
 input wire normal_tx_v,input wire[527:0]normal_tx_d,output reg normal_tx_cr,
 input wire peer_tx_valid,input wire[511:0]peer_tx_data,output wire peer_tx_ready,
 output reg tx_v,output reg[527:0]tx_d,input wire tx_cr,
 output wire drained,output reg fault);
 reg[1:0]nw,nr,pw,pr;
 wire[527:0]nhead;wire[511:0]phead;
 generate if(SAFE_SRAM)begin:g_sram
  qkd_host_peer_sram_head #(.W(528)) u_n(.ck(ck),.rst_n(rst_n),.put(normal_tx_v),.pop(normal_pop),.head(nhead),.data(normal_tx_d));
  qkd_host_peer_sram_head #(.W(512)) u_p(.ck(ck),.rst_n(rst_n),.put(rx_v&&peer_frame&&rx_d[523:512]==0),.pop(peer_pop),.head(phead),.data(rx_d[511:0]));
 end else begin:g_flops
  reg[527:0]nq[0:3];reg[511:0]pq[0:3];
  always @(posedge ck)if(rst_n)begin
   if(normal_tx_v&&nn<4)nq[nw]<=normal_tx_d;
   if(rx_v&&peer_frame&&rx_d[523:512]==0&&pn<4)pq[pw]<=rx_d[511:0];
  end
  assign nhead=nq[nr];assign phead=pq[pr];
 end endgenerate
 reg[2:0]nn,pn;reg[2:0]physical;reg peer_pending,rr;
 wire[511:0]peer_word;reg[3:0]returns;
 wire peer_frame=rx_d[527:524]==9;
 wire peer_pop=peer_rx_valid&&peer_rx_ready;
 assign peer_rx_valid=pn!=0&&!fault;assign peer_rx_data=phead;
 assign peer_tx_ready=!peer_pending&&!fault;
 wire take_peer=peer_tx_valid&&peer_tx_ready;
 wire emit=physical!=0&&!fault&&(nn!=0||peer_pending);
 wire choose_peer=peer_pending&&(nn==0||rr);
 wire normal_pop=emit&&!choose_peer;
 wire peer_send=emit&&choose_peer;
 wire[4:0]next_returns={1'b0,returns}+5'(normal_rx_cr)+5'(peer_pop)-5'(returns!=0);
 assign drained=nn==0&&pn==0&&!peer_pending&&physical==4&&returns==0&&!rx_v&&!tx_v;
 generate if(SAFE_SRAM)begin:g_payload_safe
  // Mailbox occupancy is at most one; the same SRAM-head mechanism removes
  // the 512-bit capture enable and payload reset without changing visibility.
  qkd_host_peer_sram_head #(.W(512)) u_mail(.ck(ck),.rst_n(rst_n),.put(take_peer),.pop(peer_send),.head(peer_word),.data(peer_tx_data));
  (* keep *)reg[2:0]nn_source;
  (* keep *)reg pending_source,rr_source;
  (* keep *)reg[32:0]choice;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin nn_source<=0;pending_source<=0;rr_source<=0;end
   else begin
    case({normal_tx_v&&nn_source<4,normal_pop})2'b10:nn_source<=nn_source+1'b1;2'b01:nn_source<=nn_source-1'b1;default:;endcase
    if(take_peer)pending_source<=1;
    if(peer_send)pending_source<=0;
    if(emit)rr_source<=!choose_peer;
   end
  for(genvar g=0;g<2;g=g+1)begin:g_pred
   wire[2:0]n=g==0?nn:nn_source;
   wire pending=g==0?peer_pending:pending_source;
   wire rotation=g==0?rr:rr_source;
   wire wr=normal_tx_v&&n<4;
   wire[2:0]next_n=n+3'(wr)-3'(normal_pop);
   wire next_pending=(pending||take_peer)&&!peer_send;
   wire next_rotation=emit?!choose_peer:rotation;
   wire next_choice=next_pending&&(next_n==0||next_rotation);
   for(genvar c=g*17;c<33&&c<(g+1)*17;c=c+1)begin:g_copy
    always @(posedge ck or negedge rst_n)if(!rst_n)choice[c]<=0;else choice[c]<=next_choice;
   end
  end
  // Consumers qualify both payloads with their valid signals. Capturing while
  // invalid removes broad data hold enables; the qualified transfer is exact.
  always @(posedge ck)normal_rx_d<=rx_d;
  for(genvar c=0;c<33;c=c+1)begin:g_out
   localparam integer LO=16*c;
   wire[527:0]pframe={4'd9,12'd0,peer_word ^ 512'(MUT==1)};
   always @(posedge ck)tx_d[LO+:16]<=choice[c]?pframe[LO+:16]:nhead[LO+:16];
  end
 end else begin:g_payload_legacy
  reg[511:0]word_q;
  assign peer_word=word_q;
  always @(posedge ck or negedge rst_n)
   if(!rst_n)begin word_q<=0;normal_rx_d<=0;tx_d<=0;end
   else begin
    normal_rx_d<=rx_d;
    if(take_peer)word_q<=peer_tx_data;
    if(emit)begin
     if(choose_peer)tx_d<={4'd9,12'd0,peer_word ^ 512'(MUT==1)};
     else tx_d<=nhead;
    end
   end
 end endgenerate
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin nw<=0;nr<=0;pw<=0;pr<=0;nn<=0;pn<=0;physical<=4;peer_pending<=0;rr<=0;returns<=0;rx_cr<=0;normal_rx_v<=0;normal_tx_cr<=0;tx_v<=0;fault<=0;end
  else begin
   rx_cr<=returns!=0;returns<=next_returns[3:0];if(next_returns[4])fault<=1;
   normal_rx_v<=rx_v&&!peer_frame&&!fault;
   normal_tx_cr<=normal_pop;tx_v<=emit;
   if(rx_v&&peer_frame)begin
    if(rx_d[523:512]!=0||pn==4)fault<=1;
    else begin pw<=pw+1'b1;end
   end
   if(peer_pop)pr<=pr+1'b1;
   case({rx_v&&peer_frame&&rx_d[523:512]==0&&pn<4,peer_pop})
    2'b10:pn<=pn+1'b1;2'b01:pn<=pn-1'b1;default:;
   endcase
   if(normal_tx_v)begin
    if(nn==4)fault<=1;else begin nw<=nw+1'b1;end
   end
   if(normal_pop)nr<=nr+1'b1;
   case({normal_tx_v&&nn<4,normal_pop})2'b10:nn<=nn+1'b1;2'b01:nn<=nn-1'b1;default:;endcase
   if(take_peer)begin peer_pending<=1;end
   if(emit)begin
    rr<=!choose_peer;
    if(choose_peer)peer_pending<=0;
   end
   if(tx_cr&&physical==4&&!emit)fault<=1;
   else physical<=physical+3'(tx_cr)-3'(emit);
  end
 end
endmodule
