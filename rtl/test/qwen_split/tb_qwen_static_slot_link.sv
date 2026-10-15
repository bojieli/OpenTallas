`timescale 1ns/1ps
module tb_qwen_static_slot_link;
 parameter integer FW=548,CW=16,MUT=0;
 localparam integer PW=FW+19+CW, LAT=MUT==4?6:5;
 reg clk=0,rst_n=0,epoch_begin=0,wr_v=0,rd_v=0,ev=0;
 reg [5:0] ws=0,rs=0,es=0;
 wire atv,btv,arv,brv,aa,ba;
 wire [PW-1:0] atf,btf;
 wire [FW-1:0] ard,brd;
 wire [7:0] ac,bc;
 wire [FW-1:0] aw, bw;
 reg [LAT-1:0] avpipe=0,bvpipe=0;
 reg [LAT*PW-1:0] afpipe=0,bfpipe=0;
 integer cyc,checks=0,errors=0,aborts=0;
 function automatic [FW-1:0] word(input integer endpoint,input integer slot,input integer gen);
   integer k;begin
    for(k=0;k<FW;k=k+1)word[k]=((k*13+slot*17+endpoint*29+gen*33)^(slot>>(k%6)))&1;
   end
 endfunction
 assign aw=word(0,MUT==7 && cyc==207?6:ws,cyc>=200);assign bw=word(1,ws,cyc>=200);
 wire corrupt= MUT==1 && atv && atf[FW+5:FW]==6'd7;
 always @(posedge clk)if(!rst_n)begin
   avpipe<=0;bvpipe<=0;afpipe<=0;bfpipe<=0;
 end else begin
   avpipe<={avpipe,atv};bvpipe<={bvpipe,btv};
   afpipe<={afpipe,atf ^ (corrupt ? PW'(1):PW'(0))};
   bfpipe<={bfpipe,btf};
 end
 ot_qwen_static_slot_link #(.FW(FW),.CW(CW),.MUT(MUT==3?3:0)) a(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h3a),
  .wr_v(wr_v),.wr_observed_v(wr_v && !(MUT==7 && cyc==207)),.wr_slot(ws),.wr_flit(aw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(MUT==2?es^6'd1:es),.p_tx_up(1'b1),
  .p_tx_v(atv),.p_tx_flit(atf),.p_rx_v(bvpipe[LAT-1]),.p_rx_flit(bfpipe[LAT*PW-1-:PW]),
  .rx_v(arv),.rx_flit(ard),.epoch_abort(aa),.fault_cause(ac));
 ot_qwen_static_slot_link #(.FW(FW),.CW(CW)) b(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h3a),
  .wr_v(wr_v),.wr_observed_v(wr_v),.wr_slot(ws),.wr_flit(bw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(es),.p_tx_up(1'b1),
  .p_tx_v(btv),.p_tx_flit(btf),.p_rx_v(avpipe[LAT-1]),.p_rx_flit(afpipe[LAT*PW-1-:PW]),
  .rx_v(brv),.rx_flit(brd),.epoch_abort(ba),.fault_cause(bc));
 initial begin
  for(cyc=0;cyc<380;cyc=cyc+1)begin
   rst_n=cyc>=4;epoch_begin=cyc==6;
   wr_v=(cyc>=8&&cyc<72)||(cyc>=200&&cyc<264);
   if(MUT==5 && cyc==207)wr_v=0;
   ws=6'(cyc>=200?cyc-200:cyc-8);
   if(MUT==6 && cyc==108)begin wr_v=1;ws=7;end
   rd_v=(cyc>=100&&cyc<164)||(cyc>=292&&cyc<356);
   rs=6'(cyc>=292?cyc-292:cyc-100);
   ev=(cyc>=109&&cyc<173)||(cyc>=301&&cyc<365);
   es=6'(cyc>=301?cyc-301:cyc-109);
   #5;clk=1;#1;
   if(rst_n)begin
    if(aa||ba)aborts=aborts+1;
    if(MUT==0 && (aa!==1'b0 || ba!==1'b0 || ac!==8'd0 || bc!==8'd0))begin errors=errors+1;$display("ABORT cycle%0d a%h b%h",cyc,ac,bc);end
    // These are compiler constants, not observed-output driven expectations.
    if(MUT==0 && (atv!==((cyc>=103&&cyc<167)||(cyc>=295&&cyc<359))||btv!==((cyc>=103&&cyc<167)||(cyc>=295&&cyc<359))))errors=errors+1;
    if((cyc>=110&&cyc<174)||(cyc>=302&&cyc<366))begin
      checks=checks+2;
      if(!arv || ard!==word(1,cyc>=302?cyc-302:cyc-110,cyc>=302))errors=errors+1;
      if(!brv || brd!==word(0,cyc>=302?cyc-302:cyc-110,cyc>=302))errors=errors+1;
    end else if(MUT==0 && (arv||brv))errors=errors+1;
   end
   #4;clk=0;
  end
  if(errors==0 && aborts==0)$display("STATIC_SLOT_PASS FW%0d CW%0d checks%0d TX3 RX1 PHY5",FW,CW,checks);
  else $display("STATIC_SLOT_FAIL FW%0d CW%0d checks%0d errors%0d abort_cycles%0d causes%h/%h MUT%0d",FW,CW,checks,errors,aborts,ac,bc,MUT);
  $finish;
 end
endmodule
