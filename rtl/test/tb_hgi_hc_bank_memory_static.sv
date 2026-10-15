`timescale 1ns/1ps
module tb_hgi_hc_bank_memory_static;
 parameter integer MUT=0;
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0;reg [277:0] ap=0;
 reg xv=0;reg[9:0] xword=0;reg[511:0] xdata=0;
 reg wr=0,xr=0,slot=0;reg[6:0] row=0;reg[9:0] xaddr=0;
 wire done,rv,fault;wire[1023:0] wd;wire[511:0] xd;
 ot_hgi_hc_bank_memory_static #(.BANK_ID(3),.MUT_SLOT(MUT)) dut(
 .clk(clk),.rst_n(rst_n),.weight_ap(ap),.x_write_v(xv),.x_write_word(xword),.x_write_data(xdata),
 .w_read_v(wr),.x_read_v(xr),.read_slot(slot),.w_read_row(row),.x_read_word(xaddr),
 .write_done(done),.read_valid(rv),.fault(fault),.weight_data(wd),.residual_data(xd));
 reg[1023:0] golden_w[0:255];reg[511:0] golden_x[0:639];
 reg[1023:0] ew[0:2];reg[511:0] ex[0:2];reg[2:0] ev=0;
 reg check_enable=0;
 integer checks=0;integer n,s,r,q,l;
 function automatic[31:0] pattern(input integer a,b);pattern=32'h3f800000^(a*32'h1a0101)^(b*32'h220011);endfunction
 always @(posedge clk)begin
  ew[2]=ew[1];ew[1]=ew[0];ew[0]=golden_w[{slot,row}];
  ex[2]=ex[1];ex[1]=ex[0];ex[0]=golden_x[xaddr];
  ev={ev[1:0],wr&xr&check_enable};
  #0.01;
  if(rst_n&&ev[2])begin
   if(wd!==ew[2]||xd!==ex[2]||!rv)$fatal(1,"BANK_MEMORY mismatch checks=%0d wd=%h expected=%h",checks,wd,ew[2]);
   checks=checks+1;
  end
 end
 initial begin
  for(n=0;n<256;n=n+1)golden_w[n]=0;
  for(n=0;n<640;n=n+1)begin
   for(l=0;l<16;l=l+1)golden_x[n][l*32+:32]=pattern(n,l);
  end
  repeat(3)@(negedge clk);rst_n=1;
  for(s=0;s<2;s=s+1)for(r=0;r<128;r=r+1)for(q=0;q<4;q=q+1)begin
   @(negedge clk);ap=0;ap[277]=1;ap[276]=1'(s);ap[273+:3]=3;ap[266+:7]=7'(r);ap[264+:2]=2'(q);ap[7:0]=255;
   for(l=0;l<8;l=l+1)begin ap[8+l*32+:32]=pattern(s*512+r*4+q,l);golden_w[s*128+r][q*256+l*32+:32]=ap[8+l*32+:32];end
  end
  @(negedge clk);ap=0;repeat(3)@(negedge clk);
  for(n=0;n<32;n=n+1)begin
   ap=0;ap[277]=1;ap[276]=1'(n);ap[273+:3]=3;ap[266+:7]=7'(n*3);ap[264+:2]=2'(n/2);ap[7:0]=8'h55;
   for(l=0;l<8;l=l+1)begin
    ap[8+l*32+:32]=pattern(9000+n,l);
    if(ap[l])golden_w[(n%2)*128+((n*3)%128)][((n/2)%4)*256+l*32+:32]=ap[8+l*32+:32];
   end
   @(negedge clk);
  end
  ap=0;repeat(3)@(negedge clk);
  for(n=0;n<640;n=n+1)begin xv=1;xword=10'(n);xdata=golden_x[n];@(negedge clk);end
  xv=0;repeat(3)@(negedge clk);
  for(n=0;n<8;n=n+1)begin wr=1;xr=1;slot=1'(n);row=0;xaddr=0;@(negedge clk);end
  check_enable=1;
  for(n=0;n<1280;n=n+1)begin wr=1;xr=1;slot=1'(n);row=7'(n/2);xaddr=10'(n%640);@(negedge clk);end
  check_enable=0;wr=0;xr=0;repeat(4)@(negedge clk);
  if(fault||checks!=1280)$fatal(1,"BANK_MEMORY fault=%b checks=%0d",fault,checks);
  $display("BANK_MEMORY PASS checks=%0d macros=10 weight_writes=1056 residual_writes=640 memory_latency=3",checks);$finish;
 end
endmodule
