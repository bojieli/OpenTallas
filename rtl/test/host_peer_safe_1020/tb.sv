`timescale 1ns/1ps
module tb;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rx_v=0,normal_rx_cr=0,peer_rx_ready=0,normal_tx_v=0,peer_tx_valid=0,tx_cr=0;
 reg[527:0]rx_d=0,normal_tx_d=0;reg[511:0]peer_tx_data=0;
 wire[0:0]a_rx_cr,b_rx_cr;
 wire[0:0]a_normal_rx_v,b_normal_rx_v;
 wire[527:0]a_normal_rx_d,b_normal_rx_d;
 wire[0:0]a_peer_rx_valid,b_peer_rx_valid;
 wire[511:0]a_peer_rx_data,b_peer_rx_data;
 wire[0:0]a_normal_tx_cr,b_normal_tx_cr;
 wire[0:0]a_peer_tx_ready,b_peer_tx_ready;
 wire[0:0]a_tx_v,b_tx_v;
 wire[527:0]a_tx_d,b_tx_d;
 wire[0:0]a_drained,b_drained;
 wire[0:0]a_fault,b_fault;
 qkd_host_peer_link_original  u_a(.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.normal_rx_cr(normal_rx_cr),.peer_rx_ready(peer_rx_ready),.normal_tx_v(normal_tx_v),.normal_tx_d(normal_tx_d),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.tx_cr(tx_cr),.rx_cr(a_rx_cr),.normal_rx_v(a_normal_rx_v),.normal_rx_d(a_normal_rx_d),.peer_rx_valid(a_peer_rx_valid),.peer_rx_data(a_peer_rx_data),.normal_tx_cr(a_normal_tx_cr),.peer_tx_ready(a_peer_tx_ready),.tx_v(a_tx_v),.tx_d(a_tx_d),.drained(a_drained),.fault(a_fault));
 qkd_host_peer_link #(.SAFE_SRAM(1)) u_b(.ck(ck),.rst_n(rst_n),.rx_v(rx_v),.rx_d(rx_d),.normal_rx_cr(normal_rx_cr),.peer_rx_ready(peer_rx_ready),.normal_tx_v(normal_tx_v),.normal_tx_d(normal_tx_d),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.tx_cr(tx_cr),.rx_cr(b_rx_cr),.normal_rx_v(b_normal_rx_v),.normal_rx_d(b_normal_rx_d),.peer_rx_valid(b_peer_rx_valid),.peer_rx_data(b_peer_rx_data),.normal_tx_cr(b_normal_tx_cr),.peer_tx_ready(b_peer_tx_ready),.tx_v(b_tx_v),.tx_d(b_tx_d),.drained(b_drained),.fault(b_fault));
 integer cycle=0,checks=0,ntokens=4,rtokens=4,normalwords=0,peerwords=0,peerout=0;
 reg[6:0]crpipe=0;integer seed=1234,rv;
 task fail(input string what);$display("FAIL cycle=%0d %s",cycle,what);$fatal(1);endtask
 initial begin
  for(cycle=0;cycle<100000;cycle=cycle+1)begin
   @(negedge ck);
   rst_n=(cycle%1024>=4);
   if(!rst_n)begin ntokens=4;rtokens=4;crpipe=0;end
   else begin
    ntokens=ntokens+int'(a_normal_tx_cr);rtokens=rtokens+int'(a_rx_cr);
   end
   rv=$urandom(seed);
   normal_tx_v=rst_n&&ntokens>0&&(rv%5!=0);
   rx_v=rst_n&&rtokens>0&&(rv%7!=0);
   peer_tx_valid=rst_n&&(rv%3!=0);peer_rx_ready=rv[4];
   normal_rx_cr=a_normal_rx_v;tx_cr=crpipe[6];crpipe={crpipe[5:0],a_tx_v};
   if(normal_tx_v)ntokens=ntokens-1;if(rx_v)rtokens=rtokens-1;
   for(int j=0;j<16;j++)begin
    normal_tx_d[j*32+:32]=$urandom(seed);rx_d[j*32+:32]=$urandom(seed);peer_tx_data[j*32+:32]=$urandom(seed);
   end
   normal_tx_d[527:512]=16'h4321;rx_d[527:512]=rv[8]?16'h9000:16'h1234;
   // Every fourth epoch injects overcredit/malformed traffic; reset clears fault.
   if(cycle%4096==204)rx_d[527:512]=16'h9001;
   if(cycle%4096==2220)tx_cr=1;
   @(posedge ck);#1;
   if(a_rx_cr!==b_rx_cr)fail("rx_cr");
   if(a_normal_rx_v!==b_normal_rx_v)fail("normal_rx_v");
   if(a_normal_rx_v&&a_normal_rx_d!==b_normal_rx_d)fail("normal_rx_d");
   if(a_peer_rx_valid!==b_peer_rx_valid)fail("peer_rx_valid");
   if(a_peer_rx_valid&&a_peer_rx_data!==b_peer_rx_data)fail("peer_rx_data");
   if(a_normal_tx_cr!==b_normal_tx_cr)fail("normal_tx_cr");
   if(a_peer_tx_ready!==b_peer_tx_ready)fail("peer_tx_ready");
   if(a_tx_v!==b_tx_v)fail("tx_v");
   if(a_tx_v&&a_tx_d!==b_tx_d)fail("tx_d");
   if(a_drained!==b_drained)fail("drained");
   if(a_fault!==b_fault)fail("fault");
   checks=checks+1;normalwords=normalwords+int'(a_normal_tx_cr);peerwords=peerwords+int'(a_peer_rx_valid&&peer_rx_ready);peerout=peerout+int'(a_tx_v&&a_tx_d[527:524]==9);
  end
  if(normalwords<1000||peerwords<1000||peerout<1000)fail("coverage");
  $display("PASS samecycle checks=%0d normal=%0d peer_rx=%0d peer_tx=%0d",checks,normalwords,peerwords,peerout);$finish;
 end
endmodule
