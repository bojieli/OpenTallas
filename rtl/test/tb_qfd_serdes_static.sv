`timescale 1ns/1ps
module tb_qfd_serdes_static;
 parameter integer FW=546,CW=32,MUT=0,N=512;
 localparam integer PW=FW+19+CW, LAT=MUT==4?340:339;
 localparam integer RS=32, EV=RS+3+339+1, OUT=EV+1;
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
 function automatic [FW-1:0] word(input integer endpoint,input integer slot);
   integer k;begin
    for(k=0;k<FW;k=k+1)word[k]=((k*13+slot*17+endpoint*29)^(slot>>(k%13)))&1;
   end
 endfunction
 wire missing_producer=MUT==5 && cyc==8+64+7;
 assign aw=word(0,missing_producer?7:cyc-8);assign bw=word(1,cyc-8);
 wire corrupt= MUT==1 && atv && atf[FW+5:FW]==6'd7;
 always @(posedge clk)begin
   // The digital PHY pipeline has the same explicit reset as its endpoints.
   // Otherwise the first reset edge captures a pre-NBA X valid and delivers
   // it339 cycles later after the compiled epoch has already begun.
   if(!rst_n) begin avpipe<=0;bvpipe<=0;afpipe<=0;bfpipe<=0;end
   else begin
    avpipe<={avpipe,atv};bvpipe<={bvpipe,btv};
    afpipe<={afpipe,atf ^ (corrupt ? PW'(1):PW'(0))};
    bfpipe<={bfpipe,btf};
   end
 end
 qfd_io_serdes_static #(.MUT(MUT==3?3:0)) a(
  .ck(clk),.ckb0(clk),.ckb1(clk),.ckb2(clk),.ckb3(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h3a),
  .wr_v(wr_v),.wr_observed_v(wr_v && !missing_producer),.wr_slot(ws),.wr_word(aw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(MUT==2?es^6'd1:es),.phy_up(1'b1),
  .phy_tx_v(atv),.phy_tx(atf),.phy_rx_v(bvpipe[LAT-1]),.phy_rx(bfpipe[LAT*PW-1-:PW]),
  .rx_v(arv),.rx_word(ard),.epoch_abort(aa),.fault_cause(ac));
 qfd_io_serdes_static b(
  .ck(clk),.ckb0(clk),.ckb1(clk),.ckb2(clk),.ckb3(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(8'h3a),
  .wr_v(wr_v),.wr_observed_v(wr_v),.wr_slot(ws),.wr_word(bw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(es),.phy_up(1'b1),
  .phy_tx_v(btv),.phy_tx(btf),.phy_rx_v(avpipe[LAT-1]),.phy_rx(afpipe[LAT*PW-1-:PW]),
  .rx_v(brv),.rx_word(brd),.epoch_abort(ba),.fault_cause(bc));
 initial begin
  for(cyc=0;cyc<OUT+N+20;cyc=cyc+1)begin
   rst_n=cyc>=4;epoch_begin=cyc==6;
   wr_v=cyc>=8&&cyc<8+N;ws=6'(cyc-8);
   rd_v=cyc>=RS&&cyc<RS+N;rs=6'(cyc-RS);
   ev=cyc>=EV&&cyc<EV+N;es=6'(cyc-EV);
   #5;clk=1;#1;
   if(rst_n)begin
    if(aa||ba)aborts=aborts+1;
    if(MUT==0 && (aa!==1'b0 || ba!==1'b0 || ac!==8'b0 || bc!==8'b0))begin errors=errors+1;if(errors<10)$display("BAD_FAULT cycle%0d abort%h/%h causes%h/%h",cyc,aa,ba,ac,bc);end
    // These are compiler constants, not observed-output driven expectations.
    if(MUT==0 && (atv!==(cyc>=RS+3&&cyc<RS+3+N)||btv!==(cyc>=RS+3&&cyc<RS+3+N)))errors=errors+1;
    if(cyc>=OUT&&cyc<OUT+N)begin
      checks=checks+2;
      if(!arv || ard!==word(1,cyc-OUT))errors=errors+1;
      if(!brv || brd!==word(0,cyc-OUT))errors=errors+1;
    end else if(MUT==0 && (arv||brv))errors=errors+1;
   end
   #4;clk=0;
  end
  if(MUT==5 && ac!==8'h80) $display("WRONG_MISSING_PRODUCER_CAUSE actual%h expected80",ac);
  if(errors==0 && aborts==0)$display("STATIC_BOARD_PASS FW%0d CW%0d checks%0d TX3 RX1 PHY339",FW,CW,checks);
  else $display("STATIC_BOARD_FAIL FW%0d CW%0d checks%0d errors%0d abort_cycles%0d causes%h/%h MUT%0d",FW,CW,checks,errors,aborts,ac,bc,MUT);
  $finish;
 end
endmodule
