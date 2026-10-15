`timescale 1ns/1ps
module tb_hgi_coll_static_link;
 parameter integer FW=545,CW=32,MUT=0;
 localparam integer PW=FW+19+CW, LAT=MUT==4?6:5;
 reg clk=0,rst_n=0,epoch_begin=0,wr_v=0,rd_v=0,ev=0;
 reg [5:0] ws=0,rs=0,es=0;
 wire atv,btv,arv,brv,aa,ba;
 wire [PW-1:0] atf,btf;
 wire [FW-1:0] ard,brd;
 wire [9:0] ac,bc; wire aretry,bretry;
 wire [7:0] ep=cyc>=190?8'h3b:8'h3a;
 wire [FW-1:0] aw, bw;
 reg [LAT-1:0] avpipe=0,bvpipe=0;
 reg [LAT*PW-1:0] afpipe=0,bfpipe=0;
 integer cyc,checks=0,errors=0,aborts=0;
 function automatic [FW-1:0] word(input integer endpoint,input integer slot,input integer gen);
   integer k; reg [31:0] mix; begin
    mix=32'h12345678 ^ (32'(slot)*32'h9e3779b9) ^ (32'(endpoint)*32'h37ab1091) ^ (32'(gen)*32'hba553388);
    for(k=0;k<FW;k=k+1)begin mix=mix^(mix<<13);mix=mix^(mix>>17);mix=mix^(mix<<5);word[k]=mix[0];end
   end
 endfunction
 function automatic [31:0] serial_crc(input [FW+18:0] data);
   reg [31:0] c;begin c=32'hffffffff;
    for(integer j=FW+18;j>=0;j=j-1)c={c[30:0],1'b0} ^ ((c[31]^data[j])?32'h04c11db7:32'd0);
    serial_crc=c;end
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
 ot_hgi_coll_static_link #(.MUT(MUT==3?3:0)) a(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(ep),
  .wr_v(wr_v),.wr_observed_v(wr_v && !(MUT==7 && cyc==207)),.wr_slot(ws),.wr_flit(aw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(MUT==2?es^6'd1:es),.phy_up(1'b1),
  .tx_pin_v(atv),.tx_pin_flit(atf),.rx_pin_v(bvpipe[LAT-1]),.rx_pin_flit(bfpipe[LAT*PW-1-:PW]),
  .rx_v(arv),.rx_flit(ard),.epoch_abort(aa),.retry_requested(aretry),.fault_cause(ac));
 ot_hgi_coll_static_link b(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(ep),
  .wr_v(wr_v),.wr_observed_v(wr_v),.wr_slot(ws),.wr_flit(bw),.rd_v(rd_v),.rd_slot(rs),
  .rx_expect_v(ev),.rx_expect_slot(es),.phy_up(1'b1),
  .tx_pin_v(btv),.tx_pin_flit(btf),.rx_pin_v(avpipe[LAT-1] && !(MUT==8 && afpipe[LAT*PW-PW+FW +:6]==6'd7)),.rx_pin_flit(afpipe[LAT*PW-1-:PW]),
  .rx_v(brv),.rx_flit(brd),.epoch_abort(ba),.retry_requested(bretry),.fault_cause(bc));
 initial begin
  for(cyc=0;cyc<380;cyc=cyc+1)begin
   rst_n=cyc>=4;epoch_begin=(cyc==6 || cyc==190);
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
    if(aretry!==aa || bretry!==ba)$fatal(1,"exceptional retry request inconsistent");
    if(atv && atf[PW-1-:32]!==serial_crc(atf[FW+18:0]))$fatal(1,"independent TX CRC mismatch");
    if(btv && btf[PW-1-:32]!==serial_crc(btf[FW+18:0]))$fatal(1,"independent TX CRC mismatch");
    if(MUT==0 && (aa!==1'b0 || ba!==1'b0 || ac!==10'd0 || bc!==10'd0))begin errors=errors+1;$display("ABORT cycle%0d a%h b%h",cyc,ac,bc);end
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
  if(errors==0 && aborts==0)$display("HBM_STATIC_LINK_PASS FW%0d CW%0d checks%0d TX3 RX1 PHY5",FW,CW,checks);
  else $display("HBM_STATIC_LINK_FAIL FW%0d CW%0d checks%0d errors%0d abort_cycles%0d causes%h/%h MUT%0d",FW,CW,checks,errors,aborts,ac,bc,MUT);
  $finish;
 end
endmodule
