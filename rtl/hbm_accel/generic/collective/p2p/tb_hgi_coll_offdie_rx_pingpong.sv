`timescale 1ns/1ps
module tb_hgi_coll_offdie_rx_pingpong;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,eb=0,wv=0,rv=0,arm=0,pv=0,release_v=0,sv=0;
 reg [6:0] nw=0;reg [15:0] ws=0,rs=0;reg [5:0] si=0;
 reg [611:0] pf=0;
 wire txv,ready,br,pinv,sfault,rxv,ab;
 wire [611:0] txf,pinf;wire [544:0] rxd;
 wire [6:0] cause;wire [10:0] rcause;
 reg [4:0] ep=0;reg [15:0] es[0:4];
 reg arm_bank=0,release_bank=0,slot_bank=0;
 wire [1:0] br2;
 integer overlap=0;
 reg [611:0] frames[0:255];
 integer expected[0:4095];integer expectedpin[0:4095];integer cyc=0,checks=0,seen=0,gen=0,base=0,streak=0,maxstreak=0;
 function automatic [544:0] data(input integer n,input integer g);
  reg [31:0] x;begin x=32'h12345678 ^ 32'(n*134775813) ^ 32'(g*951);
   for(integer k=0;k<545;k=k+1)begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);data[k]=x[0];end
  end
 endfunction
 ot_hgi_coll_static_link_capture tx(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(eb),.epoch(8'h3a),
  .wr_v(wv),.wr_observed_v(wv),.wr_seq(ws),.wr_flit(data(ws,gen)),.rd_v(rv),.rd_seq(rs),
  .rx_expect_v(1'b0),.rx_expect_seq(16'd0),.phy_up(1'b1),.tx_pin_v(txv),.tx_pin_flit(txf),
  .rx_pin_v(1'b0),.rx_pin_flit(612'd0),.rx_v(),.rx_flit(),.epoch_abort(),.retry_requested(),.fault_cause());
 ot_hgi_coll_offdie_rx_pingpong #(.MUT(MUT)) stage(.clk(clk),.rst_n(rst_n),.arm_v(arm),.arm_bank(arm_bank),.block_words(nw),
  .phy_v(pv),.phy_flit(pf),.phy_ready(ready),.block_ready(br2),.release_v(release_v),.release_bank(release_bank),
  .slot_v(sv),.slot_bank(slot_bank),.slot_index(si),.pin_v(pinv),.pin_flit(pinf),.fault(sfault),.fault_cause(cause));
 ot_hgi_coll_static_link_capture rx(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(eb),.epoch(8'h3a),
  .wr_v(1'b0),.wr_observed_v(1'b0),.wr_seq(16'd0),.wr_flit(545'd0),.rd_v(1'b0),.rd_seq(16'd0),
  .rx_expect_v(ep[4]),.rx_expect_seq(es[4]),.phy_up(1'b1),.tx_pin_v(),.tx_pin_flit(),
  .rx_pin_v(pinv),.rx_pin_flit(pinf),.rx_v(rxv),.rx_flit(rxd),.epoch_abort(ab),.retry_requested(),.fault_cause(rcause));
 task tick;
  begin
   if(sv)begin expected[cyc+7]=base+si;expectedpin[cyc+4]=base+si;end
   if(sv && pv && ready)overlap=overlap+1;
   #5;clk=1;
   ep<={ep[3:0],sv};es[0]<=16'(base+si);for(integer j=1;j<5;j=j+1)es[j]<=es[j-1];
   #1;
   if(txv)begin frames[seen]=txf;seen=seen+1;end
   if(pinv)begin streak=streak+1;if(streak>maxstreak)maxstreak=streak;end else streak=0;
   if(rst_n)begin
    if(expectedpin[cyc]>=0)begin
     if(!pinv || pinf!==frames[expectedpin[cyc]])$fatal(1,"612-bit SRAM release mismatch cycle%0d",cyc);
    end else if(pinv)$fatal(1,"unscheduled raw RX release");
    if(expected[cyc]>=0)begin
     if(!rxv || rxd!==data(expected[cyc],gen))$fatal(1,"native payload/calendar mismatch cyc%0d expected%0d rxv%b cause%h",cyc,expected[cyc],rxv,rcause);
     checks=checks+1;
    end else if(rxv)$fatal(1,"unscheduled native publication %0d",cyc);
    if(sfault || ab)$fatal(1,"unexpected boundary/native fault %h/%h",cause,rcause);
   end
   #4;clk=0;cyc=cyc+1;
  end
 endtask

 initial begin
  for(integer i=0;i<4096;i=i+1)begin expected[i]=-1;expectedpin[i]=-1;end
  tick;tick;rst_n=1;tick;eb=1;tick;eb=0;tick;
  // All off-die frames are emitted by actual TX6 with a continuous epoch/seq.
  for(integer t=0;t<276;t=t+1)begin
   wv=t<256;ws=16'(t);rv=t>=8 && t<264;rs=16'(t-8);tick;
  end
  wv=0;rv=0;
  if(seen!=256)$fatal(1,"TX6 full-sequence generation count%0d",seen);
  nw=64;arm_bank=0;arm=1;tick;arm=0;
  for(integer i=0;i<64;i=i+1)begin
   pv=1;pf=frames[i];if(!ready)$fatal(1,"first-bank overflow/early ready loss");tick;
  end
  pv=0;tick;tick;
  if(br2!==2'b01)$fatal(1,"first block not sealed%h",br2);
  for(integer blockid=0;blockid<4;blockid=blockid+1)begin
   base=blockid*64;release_bank=1'(blockid);slot_bank=1'(blockid);
   release_v=1;
   // Previous read bank is free before its next arm. Incoming source may fill
   // the other physical SRAM pair while every fixed output slot is active.
   if(blockid<3)begin arm=1;arm_bank=~release_bank;end
   tick;release_v=0;arm=0;
   for(integer i=0;i<64;i=i+1)begin
    sv=1;si=6'(i);
    if(blockid<3)begin
     pv=1;pf=frames[(blockid+1)*64+i];
     if(!ready)$fatal(1,"overlap fill bank unavailable at block%0d index%0d",blockid,i);
    end
    tick;
   end
   sv=0;pv=0;repeat(6)tick;
   if(blockid<3 && !br2[~release_bank])$fatal(1,"overlapped block missing/overwritten");
  end
  repeat(10)tick;
  if(checks!=256 || overlap!=192 || maxstreak!=64)$fatal(1,"coverage frames%0d overlap%0d burst%0d",checks,overlap,maxstreak);
  $display("HCOLL_OFFDIE_RX_PINGPONG_PASS frames256 overlapping_accept_slots192 burst64 SRAM4 slot_to_pin4 native7 block_period71");
  $finish;
 end
endmodule
