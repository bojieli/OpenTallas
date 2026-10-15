`timescale 1ns/1fs
module tb_core_fec_word_window;
 parameter integer PHASE=0,PPM=0,MUT=0;
 localparam real TICK=0.0520833333333333;
 reg core_clk=0,fec_clk=0,rst_n=0;
 always #(8*TICK)core_clk=~core_clk;
 initial begin #(8.5*TICK*(1.0+PPM/1000000.0)+PHASE*TICK);fec_clk=1;
  forever #(8.5*TICK*(1.0+PPM/1000000.0))fec_clk=~fec_clk;
 end
 integer cc=0,fc=0,txchecks=0,rxchecks=0,errors=0,tf=0,rf=0;
 reg cs=0,ct=0,cl=0,fs=0,ft=0,fl=0,ws=0,wt=0,wl=0,rs=0,rt=0,rl=0;
 reg cv=0,fv=0;reg[486:0]cw=0,fw=0;
 wire txv,rxv,tc,tr,rw,rr;wire[486:0]txword,rxword;
 function automatic integer ce(input integer base,k);ce=base+17*k/16;endfunction
 function automatic [486:0]word(input integer d,k);
  reg[31:0]x;begin x=32'hb0174a55^(k*32'h9e3779b9)^(d*32'h71fb1249);
   for(integer i=0;i<487;i=i+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);word[i]=x[0];end
  end
 endfunction
 ot_hbm_core_fec_word_window #(.TX_MUT(MUT==1?1:0),.RX_MUT(MUT==2?2:0)) d(
 .core_clk(core_clk),.fec_clk(fec_clk),.rst_n(rst_n),
 .ctx_start(cs),.ctx_take(ct),.ctx_last(cl),.core_tx_v(cv),.core_tx_word(cw),
 .ftx_start(fs),.ftx_take(ft),.ftx_last(fl),.fec_tx_v(txv),.fec_tx_word(txword),
 .frx_start(ws),.frx_take(wt),.frx_last(wl),.fec_rx_v(fv),.fec_rx_word(fw),
 .crx_start(rs),.crx_take(rt),.crx_last(rl),.core_rx_v(rxv),.core_rx_word(rxword),
 .tx_core_fault(tc),.tx_fec_fault(tr),.rx_fec_fault(rw),.rx_core_fault(rr));
 always @(negedge core_clk)begin
  cs=cc+1==511;ct=0;cl=0;cv=0;rs=cc+1==696;rt=0;rl=0;
  for(integer k=0;k<2048;k=k+1)begin
   if(cc+1==ce(512,k))begin ct=1;cv=1;cl=k==2047;cw=word(0,k);end
   if(cc+1==ce(697,k))begin rt=1;rl=k==2047;end
  end
 end
 always @(negedge fec_clk)begin
  fs=fc+1==487;ft=fc+1>=488&&fc+1<=2535;fl=fc+1==2535;
  ws=fc+1==648;wt=fc+1>=649&&fc+1<=2696;wl=fc+1==2696;
  fv=wt;fw=word(1,fc+1-649);
 end
 always @(posedge core_clk)begin
  cc=cc+1;#0.000001;
  if(rst_n&&(tc||rr))rf=rf+1;
  for(integer k=0;k<2048;k=k+1)if(cc==ce(697,k))begin
   rxchecks=rxchecks+1;if(!rxv||rxword!==word(1,k))errors=errors+1;
  end
  if(cc==2900)begin
   if(PPM==10000||PPM==-10000)begin
    if(tf+rf==0)$fatal(1,"unsafe drift not diagnosed");
    $display("CORE_FEC_CDC_DRIFT_REJECTED ppm%0d txfault%0d rxfault%0d",PPM,tf,rf);
   end else if(MUT!=0)begin
    if(errors==0)$fatal(1,"payload mutant escaped");
    $display("CORE_FEC_CDC_MUTANT_REJECTED m%0d errors%0d",MUT,errors);
   end else begin
    if(errors||tf||rf||txchecks!=2048||rxchecks!=2048)$fatal(1,"CDC_FAIL checks%0d/%0d errors%0d fault%0d/%0d phase%0d ppm%0d",txchecks,rxchecks,errors,tf,rf,PHASE,PPM);
    $display("CORE_FEC_CDC_PASS actual487words4096 core1.2 FEC16:17 phase%0d ppm%0d",PHASE,PPM);
   end
   $finish;
  end
 end
 always @(posedge fec_clk)begin
  fc=fc+1;#0.000001;
  if(rst_n&&(tr||rw))tf=tf+1;
  if(fc>=488&&fc<=2535)begin txchecks=txchecks+1;if(!txv||txword!==word(0,fc-488))errors=errors+1;end
 end
 initial begin repeat(8)@(negedge fec_clk);rst_n=1;end
endmodule
