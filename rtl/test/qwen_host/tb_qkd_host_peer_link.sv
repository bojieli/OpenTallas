`timescale 1ns/1ps
module tb_qkd_host_peer_link;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;reg rst_n=0;
 wire rx_v,rx_cr,tx_v,tx_cr;wire[527:0]rx_d,tx_d;
 wire normal_rx_v;wire[527:0]normal_rx_d;reg normal_rx_cr=0;
 wire peer_rx_valid;wire[511:0]peer_rx_data;reg peer_rx_ready=0;
 reg normal_tx_v=0;reg[527:0]normal_tx_d=0;wire normal_tx_cr;
 reg peer_tx_valid=0;reg[511:0]peer_tx_data=0;wire peer_tx_ready;
 wire drained,fault;
 qkd_host_peer_link #(.MUT(MUT))d(.*);
 // A digital loopback sink: physical reservation returns only when the actual
 // destination queue consumes its frame. This models no lifecycle ACK/result.
 assign rx_v=tx_v;assign rx_d=tx_d;assign tx_cr=rx_cr;
 reg peer_accepted=0;
 integer sent_n=0,sent_p=0,got_n=0,got_p=0,credit=4,cyc=0,ncr=0,pcr=0;
 function[511:0]payload(input integer i);payload={480'h123456789abcdef00112233445566778899aabbccddeeff,32'(i)};endfunction
 always @(posedge ck)if(rst_n)begin
  peer_accepted=peer_tx_valid&&peer_tx_ready;
  if(peer_accepted)sent_p=sent_p+1;
  if(normal_rx_v)begin
   if(normal_rx_d!={4'd1,12'd0,payload(got_n)})$fatal(1,"normal frame corruption/order %0d",got_n);
   got_n=got_n+1;
  end
  if(peer_rx_valid&&peer_rx_ready)begin
   if(peer_rx_data!=payload(got_p))$fatal(1,"peer frame corruption/order %0d",got_p);
   got_p=got_p+1;
  end
  if(rx_cr)pcr=pcr+1;
  if(fault)$fatal(1,"transport fault");
 end
 always @(negedge ck)if(rst_n)begin
  cyc=cyc+1;
  normal_rx_cr=normal_rx_v;peer_rx_ready=cyc%5==0;
  if(normal_tx_cr)begin credit=credit+1;ncr=ncr+1;end
  normal_tx_v=0;
  if(sent_n<100&&credit>0)begin normal_tx_v=1;normal_tx_d={4'd1,12'd0,payload(sent_n)};sent_n=sent_n+1;credit=credit-1;end
  // The held mailbox is accepted at the next rising edge. Count only that
  // acceptance before preparing a new word on a later falling edge.
  if(peer_accepted)peer_tx_valid=0;
  if(!peer_tx_valid&&sent_p<20&&cyc%3==0)begin peer_tx_valid=1;peer_tx_data=payload(sent_p);end
 end
 initial begin repeat(4)@(negedge ck);rst_n=1;
 wait(got_n==100&&got_p==20);repeat(30)@(negedge ck);
 if(pcr!=120||ncr!=100||credit!=4||!drained||fault)$fatal(1,"credit conservation n=%0d p=%0d c=%0d drained=%b",ncr,pcr,credit,drained);
 $display("PASS HOST_PEER_LINK normal=100 peer=20 physical_returns=120");$finish;end
 initial begin #50000;$fatal(1,"peer link timeout sent=%0d/%0d got=%0d/%0d",sent_n,sent_p,got_n,got_p);end
endmodule
