`timescale 1ns/1ps
module tb_hgi_coll_offdie_rx_block;
 parameter integer MUT=0;
 reg clk=0,rst_n=0,eb=0,wv=0,rv=0,arm=0,pv=0,release_v=0,sv=0;
 reg [6:0] nw=0;reg [15:0] ws=0,rs=0;reg [5:0] si=0;
 reg [611:0] pf=0;
 wire txv,ready,br,pinv,sfault,rxv,ab;
 wire [611:0] txf,pinf;wire [544:0] rxd;
 wire [4:0] cause;wire [10:0] rcause;
 reg [3:0] ep=0;reg [15:0] es[0:3];
 reg [611:0] frames[0:63];
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
 ot_hgi_coll_offdie_rx_block #(.MUT(MUT<=2?MUT:0)) stage(.clk(clk),.rst_n(rst_n),.arm_v(arm),.block_words(nw),
  .phy_v(pv),.phy_flit(pf),.phy_ready(ready),.block_ready(br),.release_v(release_v),
  .slot_v(sv),.slot_index(si),.pin_v(pinv),.pin_flit(pinf),.fault(sfault),.fault_cause(cause));
 ot_hgi_coll_static_link_capture rx(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(eb),.epoch(8'h3a),
  .wr_v(1'b0),.wr_observed_v(1'b0),.wr_seq(16'd0),.wr_flit(545'd0),.rd_v(1'b0),.rd_seq(16'd0),
  .rx_expect_v(ep[3]),.rx_expect_seq(es[3]),.phy_up(1'b1),.tx_pin_v(),.tx_pin_flit(),
  .rx_pin_v(pinv),.rx_pin_flit(pinf),.rx_v(rxv),.rx_flit(rxd),.epoch_abort(ab),.retry_requested(),.fault_cause(rcause));
 task tick;
  begin
   if(sv && MUT<3)begin expected[cyc+6]=base+si;expectedpin[cyc+3]=si;end
   #5;clk=1;
   ep<={ep[2:0],sv};es[0]<=16'(base+si);for(integer j=1;j<4;j=j+1)es[j]<=es[j-1];
   #1;
   if(txv)begin frames[seen]=txf;seen=seen+1;end
   if(pinv)begin streak=streak+1;if(streak>maxstreak)maxstreak=streak;end else streak=0;
   if(rst_n && MUT<3)begin
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
 task block_run(input integer n);
  integer fed,age;
  begin
   eb=0;wv=0;rv=0;arm=0;pv=0;sv=0;release_v=0;ep=0;seen=0;
   if(gen==0)begin rst_n=0;tick;tick;rst_n=1;tick;eb=1;tick;eb=0;tick;end
   for(integer t=0;t<n+20;t=t+1)begin
    wv=t<n;ws=16'(base+t);rv=t>=8 && t<n+8;rs=16'(base+t-8);tick;
   end
   wv=0;rv=0;
   if(seen!=n)$fatal(1,"actual TX capture count %0d/%0d",seen,n);
   nw=7'(n);arm=1;tick;arm=0;fed=0;
   while(fed<n)begin
    // Arbitrary elastic link gaps; each accepted payload came from real TX6.
    pv=(cyc%5!=0 && cyc%7!=0);pf=frames[fed];
    if(br)$fatal(1,"block-ready before all accepted/committed words");
    if(pv&&ready)fed=fed+1;
    tick;
   end
   pv=0;age=0;
   while(!br)begin tick;age=age+1;if(age>3)$fatal(1,"missing block-ready");end
   if(age!=2)$fatal(1,"seal latency %0d",age);
   // Full block applies real off-die backpressure. Held valid cannot overwrite.
   pv=1;pf=~frames[0];repeat(4)begin if(ready)$fatal(1,"full queue admitted extra frame");tick;end
   pv=0;release_v=1;tick;release_v=0;
   for(integer i=0;i<n;i=i+1)begin
    sv=1;si=6'(i);tick;
    if(i%3==0 && gen!=4)begin sv=0;tick;end
   end
   sv=0;repeat(10)tick;
   gen=gen+1;base=base+n;
  end
 endtask
 initial begin
  for(integer i=0;i<4096;i=i+1)begin expected[i]=-1;expectedpin[i]=-1;end
  if(MUT>=3)begin
   tick;rst_n=1;tick;
   if(MUT==3)begin nw=0;arm=1;tick;if(!sfault||!cause[0])$fatal(1,"invalid config undetected");end
   if(MUT==4)begin release_v=1;tick;if(!sfault||!cause[1])$fatal(1,"unavailable release undetected");end
   if(MUT==5)begin sv=1;tick;if(!sfault||!cause[2]||pinv)$fatal(1,"unavailable fixed slot undetected");end
   if(MUT==6)begin nw=65;arm=1;tick;if(!sfault||!cause[0])$fatal(1,"oversize overflow undetected");end
   $display("HCOLL_OFFDIE_RX_FAULT_PASS MUT%0d cause%h",MUT,cause);
  end else begin
   block_run(1);block_run(2);block_run(17);block_run(64);block_run(64);
   if(maxstreak!=64)$fatal(1,"missing sustained64 frame/cycle coverage %0d",maxstreak);
   if(checks!=148)$fatal(1,"bad total checks %0d",checks);
   $display("HCOLL_OFFDIE_RX_PASS native_TX6_SRAM2_RX2 frames%0d slot_to_native6 seal2",checks);
  end
  $finish;
 end
endmodule
