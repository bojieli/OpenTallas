`timescale 1ns/1ps
module tb_hgi_coll_static_link_capture;
 parameter integer FW=545,CW=32,MUT=0,N=1024;
 localparam integer PW=FW+16+19+CW, LAT=MUT==4?97:96;
 reg clk=0,rst_n=0,epoch_begin=0,wr_v=0,rd_v=0,ev=0;
 reg [15:0] ws=0,rs=0,es=0;
 wire atv,btv,arv,brv,aa,ba;
 wire [PW-1:0] atf,btf;
 wire [FW-1:0] ard,brd;
 wire [10:0] ac,bc; wire aretry,bretry;
 wire [7:0] ep=8'h3a;
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
 function automatic [31:0] serial_crc(input [FW+34:0] data);
   reg [31:0] c;begin c=32'hffffffff;
    for(integer j=FW+34;j>=0;j=j-1)c={c[30:0],1'b0} ^ ((c[31]^data[j])?32'h04c11db7:32'd0);
    serial_crc=c;end
 endfunction
 assign aw=word(0,ws,0);assign bw=word(1,ws,0);
 reg [PW-1:0] stale_frame;
 always @(posedge clk)if(atv && atf[560:545]==0)stale_frame<=atf;
 wire stale=MUT==9 && atv && atf[560:545]==64;
 wire corrupt= MUT==1 && atv && atf[FW+15:FW]==16'd7;
 always @(posedge clk)if(!rst_n)begin
   avpipe<=0;bvpipe<=0;afpipe<=0;bfpipe<=0;
 end else begin
   avpipe<={avpipe,atv};bvpipe<={bvpipe,btv};
   afpipe<={afpipe,(stale?stale_frame:atf) ^ (corrupt ? PW'(1):PW'(0))};
   bfpipe<={bfpipe,btf};
 end
 ot_hgi_coll_static_link_capture #(.MUT(MUT==3?3:MUT==11?11:0)) a(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(ep),
  .wr_v(wr_v),.wr_observed_v(wr_v && !(MUT==7 && cyc==15)),.wr_seq(ws),.wr_flit(aw),.rd_v(rd_v),.rd_seq(rs),
  .rx_expect_v(ev),.rx_expect_seq(MUT==2?es^16'd64:es),.phy_up(1'b1),
  .tx_pin_v(atv),.tx_pin_flit(atf),.rx_pin_v(bvpipe[LAT-1]),.rx_pin_flit(bfpipe[LAT*PW-1-:PW]),
  .rx_v(arv),.rx_flit(ard),.epoch_abort(aa),.retry_requested(aretry),.fault_cause(ac));
 ot_hgi_coll_static_link_capture b(
  .ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch(ep),
  .wr_v(wr_v),.wr_observed_v(wr_v),.wr_seq(ws),.wr_flit(bw),.rd_v(rd_v),.rd_seq(rs),
  .rx_expect_v(ev),.rx_expect_seq(es),.phy_up(1'b1),
  .tx_pin_v(btv),.tx_pin_flit(btf),.rx_pin_v(avpipe[LAT-1] && !(MUT==8 && afpipe[LAT*PW-PW+FW +:16]==16'd7)),.rx_pin_flit(afpipe[LAT*PW-1-:PW]),
  .rx_v(brv),.rx_flit(brd),.epoch_abort(ba),.retry_requested(bretry),.fault_cause(bc));
 initial begin
  for(cyc=0;cyc<N+140;cyc=cyc+1)begin
   rst_n=cyc>=4;epoch_begin=cyc==6;
   wr_v=cyc>=8 && cyc<N+8;ws=16'(cyc-8);
   if(MUT==5 && cyc==15)wr_v=0;
   // A second publication before its first reservation is consumed.
   if(MUT==10)wr_v=0;
   rd_v=cyc>=(MUT==6?80:16) && cyc<N+(MUT==6?80:16);rs=16'(cyc-(MUT==6?80:16));
   ev=cyc>=119 && cyc<N+119;es=16'(cyc-119);
   #5;clk=1;#1;
   if(rst_n)begin
    if(aa||ba)aborts=aborts+1;
    if(MUT==9 && cyc==185 && brv)$fatal(1,"stale RX published before full sequence check");
    if(MUT==11 && cyc==86 && atv)$fatal(1,"stale SRAM TX published before full sequence check");
    if(aretry!==aa || bretry!==ba)$fatal(1,"exceptional retry inconsistent");
    if(atv && atf[PW-1-:32]!==serial_crc(atf[FW+34:0]))$fatal(1,"independent TX CRC mismatch");
    if(btv && btf[PW-1-:32]!==serial_crc(btf[FW+34:0]))$fatal(1,"independent TX CRC mismatch");
    if(MUT==0 && (aa!==0 || ba!==0 || ac!==0 || bc!==0))begin errors=errors+1;$display("ABORT cycle%0d a%h b%h",cyc,ac,bc);end
    if(MUT==0 && (atv!==(cyc>=22&&cyc<N+22)||btv!==(cyc>=22&&cyc<N+22)))errors=errors+1;
    if(cyc>=121&&cyc<N+121)begin
     checks=checks+2;
     if(!arv || ard!==word(1,cyc-121,0))errors=errors+1;
     if(!brv || brd!==word(0,cyc-121,0))errors=errors+1;
    end else if(MUT==0 && (arv||brv))errors=errors+1;
   end
   #4;clk=0;
  end
  if(MUT==6 && !(ac[6]||bc[6]))$fatal(1,"overwrite not detected by native ownership");
  if(MUT==10 && !(ac[5]||bc[5]))$fatal(1,"unpublished slot not detected");
  if(MUT==9 && !bc[10])$fatal(1,"stale full sequence not detected at RX1");
  if(MUT==11 && !ac[8])$fatal(1,"stale SRAM full sequence not detected at TX3");
  if(errors==0 && aborts==0)$display("HBM_STATIC_LINK_CAPTURE_PASS FW545 CW32 checks%0d TX6 RX2 PHY96 wire612 sameepoch",checks);
  else $display("HBM_STATIC_LINK_CAPTURE_FAIL checks%0d errors%0d abort_cycles%0d causes%h/%h MUT%0d",checks,errors,aborts,ac,bc,MUT);
  $finish;
 end
endmodule
