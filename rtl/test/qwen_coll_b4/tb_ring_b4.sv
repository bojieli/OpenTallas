`timescale 1ns/1ps
module tb_ring_b4;
 reg clk=0,rs=0; always #5 clk=~clk;
 reg[545:0] p,r;wire[545:0] po,ro,pw,rw;
 ot_coll_static_ring #(.OFF(67),.NATIVE64(1),.USEFUL_W(546)) up(.clk(clk),.mem_ck({4{clk}}),.rs_n(rs),.wd(p),.rd(po));
 ot_coll_static_ring #(.OFF(67),.NATIVE64(1),.USEFUL_W(514)) ur(.clk(clk),.mem_ck({4{clk}}),.rs_n(rs),.wd(r),.rd(ro));
 ot_coll_static_ring #(.OFF(67)) wp(.clk(clk),.mem_ck({4{clk}}),.rs_n(rs),.wd(p),.rd(pw));
 ot_coll_static_ring #(.OFF(67)) wr(.clk(clk),.mem_ck({4{clk}}),.rs_n(rs),.wd(r),.rd(rw));
 reg[545:0] ph[0:1199],rh[0:1199];integer n,e,b,checks=0;
 initial begin
  p=0;r=0;
  for(e=0;e<4;e=e+1)begin
   @(negedge clk);rs=0;
   repeat(3)@(posedge clk);
   @(negedge clk);rs=1;
   for(n=0;n<1200;n=n+1)begin
    for(b=0;b<546;b=b+1)p[b]=((n*17+e*31+b*7)^(n>>(b%9)))&1;
    r=p;r[545:514]=0;r[513]=n[0]^e[0];
    ph[n]=p;rh[n]=r;
    @(posedge clk);#1;
    // Registered SRAM return after66 edge intervals; consumer samples it
    // on the next core edge, giving the source OFF67 contract.
    if(n>=66)begin
     if(po!==ph[n-66] || po!==pw)$fatal(1,"B4_P_DATA epoch%0d cycle%0d",e,n);
     if(ro!==rh[n-66] || ro!==rw)$fatal(1,"B4_R_DATA epoch%0d cycle%0d bit513actual%b expected%b",e,n,ro[513],rh[n-66][513]);
     checks=checks+1;
    end
    @(negedge clk);
   end
  end
  $display("B4_RING PASS checks=%0d resetepochs=4 cycles=4800 OFF67 nativeP546 R514 distinctbankaddress/wrap bit513",checks);
  $finish;
 end
endmodule
