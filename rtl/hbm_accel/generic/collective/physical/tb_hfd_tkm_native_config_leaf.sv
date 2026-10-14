`timescale 1ns/1ps
module tb_hfd_tkm_native_config_leaf;
 parameter MUT=0;
 reg clk=0;always #5 clk=~clk;reg rn=0,start=0;
 reg[11:0]n;reg[12:0]k,no;reg[7:0]g,gb;reg[15:0]pf;reg[39:0]ob,rb;reg hr;
 wire[39:0]cp;wire cb;reg[39:0]control=0;
 wire[39:0]packet=(cp[39:38]!=0)?((MUT==1&&cp[38]&&cp[37:32]==2)?40'd0:cp):control;
 wire rs,rf;wire[11:0]nn;wire[12:0]kk,nono;wire[7:0]gg,ggb;wire[15:0]pp;wire[39:0]oo,rr;wire hh;wire[3:0]res;
 integer checked=0;
 ot_hfd_tkm_cfg_tx tx(.clk(clk),.rst_n(rn),.start(start),.n(n),.k(k),.nout(no),.g(g),.gbase(gb),.pf(pf),.obase(ob),.rbase(rb),.has_r(hr),.packet(cp),.busy(cb));
 ot_hfd_tkm_native_config_leaf rx(.clk(clk),.rst_n(rn),.packet(packet),.start(rs),.fault(rf),.n(nn),.k(kk),.nout(nono),.g(gg),.gbase(ggb),.pf(pp),.obase(oo),.rbase(rr),.has_r(hh),.reservations(res));
 always @(posedge clk)if(rn&&rf)$fatal(1,"NATIVE_CFG FAIL missing/full frame");
 initial begin
  repeat(8)@(negedge clk);rn=1;repeat(12)@(negedge clk);
  for(integer c=0;c<64;c=c+1)begin
   n=12'(c*7919+7);k=13'(c*113+2);no=13'(c*71+1);g=8'(c*37+3);gb=8'(c*17+5);pf=16'(c*8191+7);
   ob=40'h95fffffff0+40'(c*32);rb=40'ha500000000+40'(c*48);hr=c%2;
   start=1;@(negedge clk);start=0;
   wait(rs);@(negedge clk);
   if({nn,kk,nono,gg,ggb,pp,oo,rr,hh}!=={n,k,no,g,gb,pf,ob,rb,hr})$fatal(1,"NATIVE_CFG FAIL full151 c=%0d",c);
   checked=checked+1;repeat(2)@(negedge clk);
  end
  for(integer mask_=0;mask_<16;mask_=mask_+1)begin
   control={2'b00,6'd62,23'd0,1'b1,4'd1,4'(mask_)};
   repeat(3)@(negedge clk);
   if(res!==4'(mask_))$fatal(1,"NATIVE_CFG FAIL reservation");
   if(rs||rf)$fatal(1,"NATIVE_CFG FAIL control62 corrupts config");
  end
  $display("NATIVE_CFG PASS full151 configurations=%0d reservation_bitmaps=16",checked);$finish;
 end
 initial begin #1000000;$fatal(1,"NATIVE_CFG FAIL timeout");end
endmodule
