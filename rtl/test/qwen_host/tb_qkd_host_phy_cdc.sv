`timescale 1ns/1ps
module tb_qkd_host_phy_cdc;
 parameter integer MUT=0;
 reg cp=0,cc=0;always #7 cp=~cp;always #5 cc=~cc;
 reg rst_n=0,phy_rx_v=0,core_tx_v=0,core_rx_cr=0,phy_tx_cr=0;
 reg[1023:0]phy_rx_d=0;reg[527:0]core_tx_d=0;
 wire phy_rx_cr,core_tx_cr,core_rx_v,phy_tx_v;wire[527:0]core_rx_d;wire[1023:0]phy_tx_d;wire[4:0]faults;
 qkd_host_phy_cdc #(.MUT(MUT))dut(.ck_pad(cp),.rx_wck(cp),.rx_rck(cc),.tx_wck(cc),.tx_rck(cp),.rst_n(rst_n),
 .phy_rx_v(phy_rx_v),.phy_rx_d(phy_rx_d),.phy_rx_cr(phy_rx_cr),.phy_tx_v(phy_tx_v),.phy_tx_d(phy_tx_d),.phy_tx_cr(phy_tx_cr),
 .core_rx_v(core_rx_v),.core_rx_d(core_rx_d),.core_rx_cr(core_rx_cr),.core_tx_v(core_tx_v),.core_tx_d(core_tx_d),.core_tx_cr(core_tx_cr),.faults(faults));
 integer ri=0,ti=0,rc=4,tc=4,ro=0,to=0,rpend=0,tpend=0,rsteps=0,tsteps=0;reg begun=0;
 function[527:0]word(input integer n);word={16'h97ac,{15{32'hc19a547e}},n[31:0]};endfunction
 always @(posedge cp)if(begun)begin
  if(phy_rx_cr)rc=rc+1;
  if(phy_tx_v)begin if(phy_tx_d!=={496'd0,word(to+1000)})$fatal(1,"TX exact W1043 DATA1024 padding/order %0d",to);to=to+1;tpend=tpend+1;end
 end
 always @(posedge cc)if(begun)begin
  if(core_tx_cr)tc=tc+1;
  if(core_rx_v)begin if(core_rx_d!==word(ro))$fatal(1,"RX528 exact/order %0d",ro);ro=ro+1;rpend=rpend+1;end
 end
 always @(negedge cp)if(begun)begin
  phy_rx_v=0;phy_tx_cr=0;tsteps=tsteps+1;
  if(tsteps>40&&tpend>0&&tsteps%3!=0)begin phy_tx_cr=1;tpend=tpend-1;end
  if(ri<96&&rc>0&&($time%3!=0))begin phy_rx_v=1;phy_rx_d={496'd0,word(ri)};ri=ri+1;rc=rc-1;end
 end
 always @(negedge cc)if(begun)begin
  core_tx_v=0;core_rx_cr=0;rsteps=rsteps+1;
  if(rsteps>50&&rpend>0&&rsteps%4!=0)begin core_rx_cr=1;rpend=rpend-1;end
  if(ti<96&&tc>0&&($time%7!=0))begin core_tx_v=1;core_tx_d=word(ti+1000);ti=ti+1;tc=tc-1;end
 end
 initial begin repeat(8)@(posedge cp);rst_n=1;repeat(16)@(posedge cp);begun=1;
 wait(ro==96&&to==96);repeat(40)@(posedge cp);if(faults)$fatal(1,"CDC faults %b",faults);
 $display("PASS HOST_PHY_CDC RX=%0d TX=%0d clocks=10ns/14ns",ro,to);$finish;end
 initial begin #1000000;$fatal(1,"timeout ri=%0d ro=%0d ti=%0d to=%0d faults=%b",ri,ro,ti,to,faults);end
endmodule
