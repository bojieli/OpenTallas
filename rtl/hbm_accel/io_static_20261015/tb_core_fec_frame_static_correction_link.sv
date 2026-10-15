// OPT-IN static correction profile; frozen151 baseline preserved.
`timescale 1ns/1fs
module tb_core_fec_frame_static_correction_link;
 parameter integer DMUT=0,N=300;
 localparam real TICK=0.0520833333333333;
 reg core_clk=0,fec_clk=0,rst_n=0;
 always #(8*TICK)core_clk=~core_clk;
 always #(8.5*TICK)fec_clk=~fec_clk;
 integer cc=0,fc=0,MUT=0,checks=0,errors=0,wordchecks=0,decodedchecks=0,aborts=0,gfaults=0;
 reg epoch_begin=0,wr=0,rd=0,expect_v=0;reg[15:0]ws=0,rs=0,es=0;reg[544:0]wd=0;
 wire tv,rv,aa,ba;wire[611:0]tf,rxframe;wire[544:0]payload_out;wire[10:0]ac,bc;
 reg frame_flip=0;reg txstart=0,rxstart=0,txstep=0,rxstep=0,slot=0,valid_flip=0,word_flip=0,word_drop=0,phy_up=1;
 wire twv,rxpinv,txdue,gtf,grf;wire[486:0]tw;
 reg ctxs=0,ctxt=0,ctxl=0,ftxs=0,ftxt=0,ftxl=0,frxs=0,frxt=0,frxl=0,crxs=0,crxt=0,crxl=0;
 wire ftxv,crxv,txcf,txff;
 wire rx_fec_fault,rx_core_fault;wire[486:0]ftxword,crxword;
 wire[486:0]phyword;wire phyv,pad;wire[1:0]status;wire[511:0]pma;wire[3:0]pmaf;
 reg sers=0,serr=0,dess=0,desr=0,cap_s=0,cap_t=0,cap_l=0,read_s=0,read_t=0,read_l=0;
 reg want_v=0;reg[544:0]want_data=0;
 reg[486:0]input_history[0:3000];reg[486:0]sampled,decoded;reg decoded_v;
 function automatic integer C(input integer base,k);C=base+17*k/16;endfunction
 function automatic integer A(input integer j);A=C(511,613*j/487);endfunction
 function automatic integer lastword(input integer j);lastword=(613*(j+1)+486)/487-1;endfunction
 function automatic integer live_slot(input integer j);live_slot=(j%7!=3&&j%11!=8);endfunction
 function automatic[544:0]word(input integer seq);
  reg[31:0]x;begin x=32'h471abd09^(seq*32'h9e3779b9);
  for(integer i=0;i<545;i=i+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);word[i]=x[0];end end
 endfunction
 ot_hgi_coll_static_link_capture txep(.ck({5{core_clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h72),
 .wr_v(wr),.wr_observed_v(wr),.wr_seq(ws),.wr_flit(wd),.rd_v(rd),.rd_seq(rs),
 .rx_expect_v(1'b0),.rx_expect_seq(16'b0),.phy_up(phy_up),.tx_pin_v(tv),.tx_pin_flit(tf),
 .rx_pin_v(1'b0),.rx_pin_flit(612'b0),.rx_v(),.rx_flit(),.epoch_abort(aa),.retry_requested(),.fault_cause(ac));
 wire[3:0]cf;wire[1:0]ff;
 assign gtf=cf[0];assign grf=cf[1];assign txcf=cf[2];assign rx_core_fault=cf[3];assign txff=ff[0];assign rx_fec_fault=ff[1];
 assign ftxword=link.fec_tx_word;assign phyword=link.fec_rx_word;assign phyv=link.fec_rx_v;
 ot_hbm_core_fec_frame_static_correction_link #(.DMUT(DMUT)) link(
 .core_clk(core_clk),.rst_n(rst_n),.fec_clks({16{fec_clk}}),.phy_clks({6{core_clk}}),
 .tx_start(txstart),.rx_start(rxstart),.tx_word_step(txstep),.rx_word_step(rxstep),.tx_slot_v(slot),
 .endpoint_tx_v(tv^valid_flip),.endpoint_tx_frame(tf^(frame_flip?612'd1:612'd0)),
 .expected_tx_slot(txdue),.endpoint_rx_v(rxpinv),.endpoint_rx_frame(rxframe),
 .ctx_start(ctxs),.ctx_take(ctxt),.ctx_last(ctxl),.ftx_start(ftxs),.ftx_take(ftxt),.ftx_last(ftxl),
 .frx_start(frxs),.frx_take(frxt),.frx_last(frxl),.crx_start(crxs),.crx_take(crxt),.crx_last(crxl),
 .capture_start(cap_s),.capture_take(cap_t),.capture_last(cap_l),.read_start(read_s),.read_take(read_t),.read_last(read_l),
 .ser_write_start(sers),.ser_read_start(serr),.des_write_start(dess),.des_read_start(desr),
 .pma_tx(pma),.pma_rx(pma^((cc%3==0)?512'd1<<101:512'd0)),.fault_core(cf),.crossing_fault_fec(ff),.pma_fault(pmaf),.status(status),.padding_fault(pad));
 ot_hgi_coll_static_link_capture rxep(.ck({5{core_clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h72),
 .wr_v(1'b0),.wr_observed_v(1'b0),.wr_seq(16'b0),.wr_flit(545'b0),.rd_v(1'b0),.rd_seq(16'b0),
 .rx_expect_v(expect_v),.rx_expect_seq(es),.phy_up(1'b1),.tx_pin_v(),.tx_pin_flit(),
 .rx_pin_v(rxpinv),.rx_pin_flit(rxframe),.rx_v(rv),.rx_flit(payload_out),.epoch_abort(ba),.retry_requested(),.fault_cause(bc));
 always @(negedge core_clk)begin:core_program
  integer seq;
  epoch_begin=cc+1==400;wr=0;rd=0;expect_v=0;want_v=0;txstart=cc+1==510;rxstart=cc+1==697;
  ctxs=cc+1==511;ctxt=0;ctxl=0;crxs=cc+1==696;crxt=0;crxl=0;txstep=0;rxstep=0;slot=0;
  frame_flip=MUT==3&&cc+1==511;valid_flip=MUT==1&&cc+1==517;word_flip=MUT==3&&cc+1==512;word_drop=MUT==2&&cc+1==698;phy_up=!(MUT==4&&cc+1==509);
  serr=cc+1==40;dess=cc+1==41;
  for(integer k=0;k<2048;k=k+1)begin
   if(cc+1==C(511,k))txstep=1;
   if(cc+1==C(512,k))begin ctxt=1;ctxl=k==2047;end
   if(cc+1==C(697,k))begin crxt=1;crxl=k==2047;end
   if(cc+1==C(698,k))rxstep=1;
  end
  for(integer j=0;j<1628;j=j+1)if(cc+1==A(j))slot=1;
  seq=0;
  for(integer j=0;j<N;j=j+1)if(live_slot(j))begin
   if(cc+1==A(j)-11)begin wr=1;ws=16'(seq);wd=word(seq);end
   if(cc+1==A(j)-7)begin rd=1;rs=16'(seq);end
   if(cc+1==C(700,lastword(j)))begin expect_v=1;es=16'(seq);end
   if(cc+1==C(702,lastword(j)))begin want_v=1;want_data=word(seq);end
   seq=seq+1;
  end
 end
 always @(negedge fec_clk)begin
  ftxs=fc+1==487;ftxt=fc+1>=488&&fc+1<=2535;ftxl=fc+1==2535;
  frxs=fc+1==648;frxt=fc+1>=649&&fc+1<=2696;frxl=fc+1==2696;
  sers=fc+1==16;desr=fc+1==64;
  cap_s=fc+1==639;cap_t=fc+1>=640&&fc+1<=2687;cap_l=fc+1==2687;
  read_s=fc+1==647;read_t=fc+1>=648&&fc+1<=2695;read_l=fc+1==2695;
 end
 always @(posedge core_clk)begin
  cc=cc+1;#0.000001;
  if(rst_n)begin
   if(aa||ba)aborts=aborts+1;if(gtf||grf)gfaults=gfaults+1;
   if(rv!==want_v)errors=errors+1;
   if(want_v)begin checks=checks+1;if(payload_out!==want_data)errors=errors+1;end
   if(txcf||rx_core_fault)$fatal(1,"CORE_CDC_FAULT c%0d %b%b",cc,txcf,rx_core_fault);
  end
  if(cc==2900)begin
   if(MUT==0)begin
    if(errors||aborts||gfaults||checks!=234||decodedchecks!=2048||wordchecks!=2048||!status[1])$fatal(1,"CORE_FEC_FRAME_LINK_FAIL checks%0d dec%0d words%0d errors%0d abort%0d gf%0d causes%h/%h",checks,decodedchecks,wordchecks,errors,aborts,gfaults,ac,bc);
    $display("CORE_FEC_FRAME_LINK_PASS payloads234 idle66 decoded2048 CDCwords2048 core1.2 FEC16:17 age151FEC TX6 RX2 actual512PMA stopcore2900");
   end else begin
    if(MUT==1&&!bc[2])$fatal(1,"validflip notdetected");
    if(MUT==2&&!grf)$fatal(1,"missingword notdetected");
    if(MUT==3&&!bc[0])$fatal(1,"CRCcorruption notdetected");
    if(MUT==4&&!ac[4])$fatal(1,"TXabort notdetected");
    $display("CORE_FEC_FRAME_LINK_MUTANT_PASS m%0d errors%0d causes%h/%h gf%0d",MUT,errors,ac,bc,gfaults);
   end
   $finish;
  end
 end
 always @(posedge fec_clk)begin
  sampled=ftxword;decoded=link.u_phy.u_fec.qd[486:0];decoded_v=link.u_phy.u_fec.qv;fc=fc+1;
  input_history[fc]=sampled;
  if(fc>=640&&fc<=2687)begin
   decodedchecks=decodedchecks+1;if(!decoded_v||decoded!==input_history[fc-151])$fatal(1,"ACTUAL_FEC_DECODE_ERROR F%0d age151",fc);
  end
  #0.000001;
  if(rst_n&&(txff||rx_fec_fault||pad||status[0]||(|pmaf)))$fatal(1,"FEC_CDC_PHY_FAULT F%0d crossing%b%b status%b pma%b",fc,txff,rx_fec_fault,status,pmaf);
  if(fc>=648&&fc<=2695)begin
   wordchecks=wordchecks+1;if(!phyv||phyword!==input_history[fc-159])$fatal(1,"ACTUAL_FEC_WINDOW_ERROR F%0d",fc);
  end
 end
 initial begin
  wait(MUT==2);wait(cc==697);@(negedge core_clk);force link.transport_rx_v=1'b0;
  @(posedge core_clk);#0.000002;release link.transport_rx_v;
 end
 initial begin if($value$plusargs("mut=%d",MUT))begin end repeat(8)@(negedge fec_clk);rst_n=1;end
 initial begin #5000;$fatal(1,"timeout");end
endmodule
