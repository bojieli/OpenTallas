`timescale 1ns/1ps
// KV-ATTN4 2026-10-20: reset witness for qkd_attn_cal_gen_r17 (rv5 kit): with random power-up state (Verilator
// --x-initial unique, +verilator+rand+reset+2) every calendar data stage S1..S9 must read 0 after the landed reset, before
// any go.  MUT 8 (the r16 form, no data reset) must FAIL.  Then one legal command must still complete (done, no fault).
module tb_qkd_attn_cal_gen_r17_rst;
 parameter integer MUT=0;
 reg ck=0,rst_n=0,go=0; always #1 ck=~ck;
 wire [175:0] cal;wire [15:0] rx_cmd,tx_first,end_age,cal_epoch;wire done,valid,fault;
 qkd_attn_cal_gen_r17 #(.STATUS_DELAY(213),.MUT(MUT)) dut(.ck(ck),.rst_n(rst_n),.cfg_cal({8'd8,8'd0,8'd0}),.go(go),
  .ctx_t(14'd300),.epoch(16'h5a5a),.cal(cal),.rx_cmd(rx_cmd),.tx_first(tx_first),.end_age(end_age),.cal_epoch(cal_epoch),
  .done(done),.valid(valid),.fault(fault));
 integer nz=0,i;
 task chk(input [1023:0] v,input integer w,input [8*8-1:0] n);
  if(v!=0)begin nz=nz+1; $display("NONZERO %0s",n); end
 endtask
 initial begin
  repeat(4)@(posedge ck); #0.1;
  chk(dut.t1,14,"t1");chk(dut.e1,16,"e1");chk(dut.f2,1,"f2");chk(dut.e2,16,"e2");chk(dut.ns2,12,"ns2");chk(dut.p2,4,"p2");
  for(i=0;i<4;i=i+1)begin chk(dut.x2[i],13,"x2");chk(dut.a3[i],8,"a3");chk(dut.cnt3[i],4,"cnt3");chk(dut.xs3[i],10,"xs3");chk(dut.zv4[i],10,"zv4");end
  chk(dut.e3,16,"e3");chk(dut.m3,11,"m3");chk(dut.po0_3,12,"po0_3");chk(dut.e4,16,"e4");chk(dut.scan4,8,"scan4");chk(dut.adj4,9,"adj4");
  chk(dut.e5,16,"e5");chk(dut.lmax5,16,"lmax5");chk(dut.za5,10,"za5");chk(dut.e6,16,"e6");chk(dut.exp6,16,"exp6");chk(dut.zw6,10,"zw6");
  chk(dut.e7,16,"e7");chk(dut.z7,16,"z7");chk(dut.pvo7,16,"pvo7");chk(dut.e8,16,"e8");chk(dut.pv8,16,"pv8");chk(dut.hp8,16,"hp8");
  chk(dut.e9,16,"e9");chk(dut.r9,17,"r9");chk(dut.p09,16,"p09");chk(dut.cal9,176,"cal9");chk(dut.f9,1,"f9");
  rst_n=1; @(posedge ck); #0.1 go=1; @(posedge ck); #0.1 go=0;
  repeat(14)@(posedge ck);
  if(!valid)begin nz=nz+1;$display("COMMAND valid=%0d fault=%0d",valid,fault);end
  $display("CALRST %s mut=%0d nonzero=%0d tx_first=%0d end=%0d",nz==0?"PASS":"FAIL",MUT,nz,tx_first,end_age);
  $finish;
 end
endmodule
