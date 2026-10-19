`timescale 1ns/1ps
module tb_hnx_pl_land_sram #(parameter integer PHASE=0,MUT=0);
 reg ck_w=0,ck_r=0,rsi_w=0,rsi_r=0;
 always #5 ck_w=~ck_w;
 initial begin #(5+PHASE);ck_r=1;forever #5 ck_r=~ck_r;end
 reg [2068:0] i=0;
 wire [2068:0] o,ref_o;
 wire [8275:0] bank;
 wire [11:0] epo;
 wire [3:0] vld;
 integer t,j,checks=0,errors=0,age=0;
 real last_write[0:15];
 real min_write_age=1e9;
 initial for(integer a=0;a<16;a=a+1) last_write[a]=-1e9;
 always @(posedge ck_w) if(dut.rq_w) last_write[dut.wa]=$realtime;
 always @(posedge ck_r) if(dut.read_enable && !(dut.warm&&dut.v[dut.sel])) $fatal(1,"HNXLAND invalid-read fault");
 always @(posedge ck_r) if(dut.warm && dut.v[dut.sel]) begin
  if($realtime-last_write[dut.ra]<min_write_age) min_write_age=$realtime-last_write[dut.ra];
 end
 hnx_pl_land_sram #(.MUT(MUT)) dut(.*);
 ot_pl_land_w #(.W(2069)) oldw(.ck(ck_w),.rsi(rsi_w),.i(i),.bank(bank),.epo(epo),.vld(vld));
 ot_pl_land_r #(.W(2069)) oldr(.ck(ck_r),.rsi(rsi_r),.bank(bank),.epo(epo),.vld(vld),.o(ref_o));
 always @(posedge ck_r) begin
  #1;
  age=age+1;
  if(age>20) begin checks=checks+1;if(o!==ref_o) errors=errors+1;end
 end
 initial begin
  for(t=0;t<1200;t=t+1) begin
   @(negedge ck_w);
   rsi_w=(t>5 && !(t>=600&&t<608));rsi_r=rsi_w;
   for(j=0;j<2069;j=j+1)i[j]=$urandom_range(0,1);
  end
  #30;
  $display("HNXLAND %s phase=%0d checks=%0d errors=%0d min_write_age_ns=%0.3f",errors?"FAIL":"PASS",PHASE,checks,errors,min_write_age);
  if(!MUT && min_write_age<17.99) $fatal(1,"HNXLAND collision guard violated");
  if(errors) $fatal(1,"HNXLAND mismatch");
  $finish;
 end
endmodule
