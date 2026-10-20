`timescale 1ns/1ps
module tb_pvfin_calendar;
 reg [15:0] a=0,b=0,r=0;wire [15:0] y,ym;
 ot_qkd_pvfin_calendar_value #(.C(9)) dut(.p0(a),.p1(b),.r(r),.y(y));
 ot_qkd_pvfin_calendar_value #(.C(9),.IGNORE_R(1)) mut3(.p0(a),.p1(b),.r(r),.y(ym));
 wire [15:0] ya,ys;
 ot_qkd_pvfin_calendar_value #(.C(1),.IGNORE_R(1)) adddate(.p0(a),.p1(b),.r(r),.y(ya));
 ot_qkd_pvfin_calendar_value #(.C(8),.IGNORE_R(1)) sumdate(.p0(a),.p1(b),.r(r),.y(ys));
 integer checked=0,seed=1;reg [15:0] lastp,last,expect_y,expect_m;
 task check(input [15:0] x0,x1,xr);
  begin
   a=x0;b=x1;r=xr;#1;
   lastp=(a>b)?a:b;last=(lastp>r)?lastp:r;
   expect_y=last+16'd9;expect_m=lastp+16'd9;
   if(y!==expect_y||ym!==expect_m)$fatal(1,"PVFIN_CALENDAR FAIL a=%h b=%h r=%h y=%h/%h ym=%h/%h",a,b,r,y,expect_y,ym,expect_m);
   if(ya!==(lastp+16'd1)||ys!==(lastp+16'd8))$fatal(1,"COMMAND_DATE FAIL a=%h b=%h r=%h",a,b,r);
   checked=checked+1;
  end
 endtask
 initial begin
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
