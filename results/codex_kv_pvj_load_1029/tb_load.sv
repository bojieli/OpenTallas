`timescale 1ns/1ps
module tb;
 reg clk=0,rst_n=0; always #5 clk=~clk;
 reg[1023:0]t0=0,t1=0,t2=0,t3=0;reg go=0;reg[7:0]sf=0;
 wire[511:0]a,b,c,z;wire av,bv,cv,zv,af,bf,cf,zf;
 pvj_reference #(.RESET_PIN(1)) ref_dut(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(a),.y_valid(av),.fault(af));
 ot_qwen_tp8_pv_join_t #(.RESET_PIN(1),.OUTPUT_LOAD_LOCAL(1)) dut(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(b),.y_valid(bv),.fault(bf));
 ot_qwen_tp8_pv_join_t #(.RESET_PIN(1)) def_dut(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(z),.y_valid(zv),.fault(zf));
 pvj_mutant #(.RESET_PIN(1),.OUTPUT_LOAD_LOCAL(1)) mutant(.clk(clk),.rst_n(rst_n),.ts0(t0),.ts1(t1),.ts2(t2),.ts3(t3),.join_go(go),.sf(sf),.y(c),.y_valid(cv),.fault(cf));
 integer i,k,checks=0,valids=0,mutdiff=0;reg seen=0;
 initial begin
  repeat(5)@(negedge clk);rst_n=1;
  for(i=0;i<6400;i=i+1)begin
   @(negedge clk);
   if(av)begin seen=1;valids=valids+1;end
   if(i>8)begin
    checks=checks+1;
    if({av,af}!={bv,bf}||{av,af}!={zv,zf}||(seen&&(a!==b||a!==z)))$fatal(1,"LOAD_MISMATCH cycle%0d",i);
    if(seen&&(a!==c||av!==cv||af!==cf))mutdiff=mutdiff+1;
   end
   for(k=0;k<32;k=k+1)begin t0[32*k+:32]=$urandom;t1[32*k+:32]=$urandom;t2[32*k+:32]=$urandom;t3[32*k+:32]=$urandom;end
   go=(i%40)==0;
   if(i>4800)go=(i%11)==0;
   sf=(i==4300)?8'h20:8'h00;
   if(i==2100||i==4200)rst_n=0;
   if(i==2104||i==4204)rst_n=1;
  end
  if(valids<100||mutdiff<100)$fatal(1,"LOAD_COVERAGE_FAIL valid%0d mut%0d",valids,mutdiff);
  $display("LOAD_PASS checks=%0d valid=%0d mutant_mismatches=%0d cycles_added=0",checks,valids,mutdiff);$finish;
 end
endmodule
