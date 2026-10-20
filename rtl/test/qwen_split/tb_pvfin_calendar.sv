`timescale 1ns/1ps
module tb_pvfin_calendar;
 reg [15:0] a=0,b=0,r=0;wire [15:0] y,ym;
 ot_qkd_pvfin_calendar_value #(.C(9)) dut(.p0(a),.p1(b),.r(r),.y(y));
 ot_qkd_pvfin_calendar_value #(.C(9),.IGNORE_R(1)) mut3(.p0(a),.p1(b),.r(r),.y(ym));
 wire bad,badm;reg expect_bad,expect_badm;reg [15:0] skew;
 ot_qkd_pvfin_calendar_check #(.SKEW(1)) ck0(.p0(a),.p1(b),.r(r),.bad(bad));
 ot_qkd_pvfin_calendar_check #(.SKEW(1),.IGNORE_R(1)) ck1(.p0(a),.p1(b),.r(r),.bad(badm));
 integer checked=0,seed=1;reg [15:0] lastp,last,expect_y,expect_m;
 task check(input [15:0] x0,x1,xr);
  begin
   a=x0;b=x1;r=xr;#1;
   lastp=(a>b)?a:b;last=(lastp>r)?lastp:r;
   expect_y=last+16'd9;expect_m=lastp+16'd9;
   if(y!==expect_y||ym!==expect_m)$fatal(1,"PVFIN_CALENDAR FAIL a=%h b=%h r=%h y=%h/%h ym=%h/%h",a,b,r,y,expect_y,ym,expect_m);
   skew=(a>b)?a-b:b-a;
   expect_bad=(a<1)||(b<1)||(r<1)||(skew>1)||({1'b0,last}+17'd77>17'hffff);
   expect_badm=(a<1)||(b<1)||(r<1)||(skew>1)||({1'b0,lastp}+17'd77>17'hffff);
   if(bad!==expect_bad||badm!==expect_badm)$fatal(1,"PVFIN_CHECK FAIL a=%h b=%h r=%h bad=%b/%b mut=%b/%b",a,b,r,bad,expect_bad,badm,expect_badm);
   checked=checked+1;
  end
 endtask
 initial begin
  for(integer i=65456;i<=65460;i=i+1)for(integer j=65456;j<=65460;j=j+1)for(integer k=65456;k<=65460;k=k+1)check(16'(i),16'(j),16'(k));
  check(0,65535,1);check(65535,0,1);check(1,65535,1);check(65535,1,1);
  for(integer i=65527;i<=65535;i=i+1)for(integer j=65527;j<=65535;j=j+1)for(integer k=65527;k<=65535;k=k+1)check(16'(i),16'(j),16'(k));
  for(integer i=0;i<65536;i=i+1)begin
   check(16'(i),16'(i),16'(~i));
   check(16'(i),16'(i+1),16'(i));
   check(16'(i-1),16'(i),16'(i));
  end
  for(integer i=0;i<4096;i=i+1)check(16'($random(seed)),16'($random(seed)),16'($random(seed)));
  $display("PVFIN_CALENDAR PASS checked=%0d overflow triples65527..65535 + all16bit ties + random",checked);$finish;
 end
endmodule
