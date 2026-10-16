`timescale 1ns/1ps
// Calendar tile boundary proof only. Compiler literals are expected controls;
// no arithmetic/result stimulus exists inside this DUT.
module tb_qkd_cal_pin;
 `include "d2d_cal_image.svh"
 parameter integer MUT=0;
 reg ck=0,rst_n=0,reload=0,epoch_go=0,halt=0;always #5 ck=~ck;
 wire tw,rw,cs,sg,ready,running,ad,ts,fault;wire[5:0] addr,layer;wire[31:0] data;
 qkd_d2d_cal_seq_pin #(.EP_SKEW(MUT?2:3)) u(.ck(ck),.rst_n(rst_n),.reload(reload),.tok_go(1'b0),
  .epoch_go(epoch_go),.halt(halt),.cfg_tx_we(tw),.cfg_rx_we(rw),.cfg_addr(addr),.cfg_data(data),
  .cal_start(cs),.cal_seg(sg),.cal_ready(ready),.running(running),.layer(layer),.adm_done(ad),.tok_start(ts),.fault(fault));
 integer cyc=0,release_c=0,init_words=0,starts=0,origin=0,next_c=0,li=63,tok=0;
 reg check_init=0,check_calendar=0;reg[31:0] expected_data;integer ix;
 always @(posedge ck)begin
  cyc=cyc+1;
  #1;
  if(rst_n&&check_init)begin
   if(tw||rw)begin
    ix=init_words/2;
    expected_data=init_words<64 ? (init_words[0]?D2D_CAL_K_RX_IMG[32*ix+:32]:D2D_CAL_K_TX_IMG[32*ix+:32]) :
                                      (init_words[0]?D2D_CAL_K_RX_SEG2:D2D_CAL_K_TX_SEG2);
    if(cyc-release_c!=init_words+3 || tw!==!init_words[0] || rw!==init_words[0] ||
       addr!==(init_words<64?6'(ix):6'd32) || data!==expected_data)
     $fatal(1,"CALPIN_FAIL boot control word%0d cycle%0d expected%0d",init_words,cyc-release_c,init_words+3);
    init_words=init_words+1;
   end
   if(cyc-release_c==68 && (!ready||init_words!=66))$fatal(1,"CALPIN_FAIL fixed68edge init deadline");
  end
  if(rst_n&&check_calendar)begin
   if(fault)$fatal(1,"CALPIN_FAIL unexpected source fault cycle%0d",cyc);
   if(cs!==(cyc==next_c))$fatal(1,"CALPIN_FAIL compiled start cycle%0d expected%0d layer%0d",cyc,next_c,layer);
   if(cs)begin
    if(layer!==6'(li)||sg!==(li==0||li==63))$fatal(1,"CALPIN_FAIL layer/segment identity");
    starts=starts+1;
    if(li==63)begin li=0;next_c=origin+3+D2D_FIRST_TOKEN;end
    else if(li==35)begin tok=tok+1;li=0;next_c=origin+3+D2D_FIRST_TOKEN+tok*D2D_TOKEN_PERIOD;end
    else begin li=li+1;next_c=origin+3+D2D_FIRST_TOKEN+tok*D2D_TOKEN_PERIOD+20'(D2D_CAL_START[20*li+:20]);end
   end
  end
 end
 task edge;begin @(posedge ck);#2;end endtask
 initial begin
  repeat(4)@(negedge ck);release_c=cyc;check_init=1;rst_n=1;
  repeat(70)@(negedge ck);check_init=0;
  if(!ready||init_words!=66)$fatal(1,"CALPIN_FAIL init count");
  repeat(30)@(negedge ck);epoch_go=1;origin=cyc+1;li=63;tok=0;next_c=origin+3+D2D_ADM_OFS;check_calendar=1;
  @(negedge ck);epoch_go=0;
  // Two complete36layer token programmes, then token3 L0 tests halt while active.
  wait(starts==74);@(negedge ck);check_calendar=0;
  if(!running)$fatal(1,"CALPIN_FAIL halt test did not reach active programme");
  halt=1;edge();if(!running)$fatal(1,"CALPIN_FAIL halt bypassed declared input capture");
  edge();if(running)$fatal(1,"CALPIN_FAIL halt missed fixed1edge observation");
  @(negedge ck);halt=0;edge();@(negedge ck);reload=1;
  edge();if(!ready)$fatal(1,"CALPIN_FAIL reload bypassed input capture");
  edge();if(ready)$fatal(1,"CALPIN_FAIL reload missed fixed1edge observation");
  @(negedge ck);reload=0;repeat(66)edge();if(!ready||fault)$fatal(1,"CALPIN_FAIL reload66write completion");
  @(negedge ck);rst_n=0;#2;if(ready||running||fault)$fatal(1,"CALPIN_FAIL asynchronous reset not observed");
  @(negedge ck);init_words=0;release_c=cyc;check_init=1;rst_n=1;
  repeat(70)@(negedge ck);check_init=0;if(!ready||init_words!=66)$fatal(1,"CALPIN_FAIL reset/reinit deadline");
  $display("CALPIN_PASS starts%0d layers72 token3start1 bootwords66 reloadwords66 resetwords66 halt_capture1 reset_release2",starts);
  $finish;
 end
 initial begin #9000000;$fatal(1,"CALPIN_FAIL fixed proof timeout");end
endmodule
