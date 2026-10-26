module tb_qkd_host_rst_role;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 parameter NL=6;     // link ends the sequencer waits for (KV die v1.4.1: 2 = static D2D + host SerDes)
 localparam [NL-1:0] ALL=~0, PART=~(1<<(NL-1));
 reg clk=0;always #0.4165 clk=~clk;
 reg por_n=0,soft_rst=0;reg[2:0]die_id=0;reg[NL-1:0]link_up=0;reg[7:0]boot_done=0,boot_ok=0;
 wire host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,boot_fault;
 wire[3:0]boot_state,boot_err;wire[31:0]boot_cycles;
 qkd_host_rst_role_pins #(.NL(NL),.T_LINK(16),.T_HBM(32))dut(.*);
 integer d,checks=0,n;
 task tick;begin @(negedge clk);end endtask
 task reset(input[2:0]role);begin
  por_n=0;die_id=role;link_up=0;boot_done=0;boot_ok=0;soft_rst=0;
  repeat(4)tick;por_n=1;repeat(8)tick;
  if(!host_rst_n||sys_ready||die_rst_n)$fatal(1,"host/boot early release");
 end endtask
 task waitready;begin
 n=0;while(!sys_ready&&n<30)begin tick;n=n+1;end
 if(!sys_ready||!die_rst_n||boot_fault)$fatal(1,"genuine local/package release failed role%d",die_id);
 checks=checks+1;
 end endtask
 task waitfault(input[3:0]e);begin
 n=0;while(!boot_fault&&n<70)begin tick;n=n+1;end
 if(!boot_fault||boot_err!=e||sys_ready||die_rst_n)$fatal(1,"wrong selected boot fault role%d got%d expected%d",die_id,boot_err,e);
 checks=checks+1;
 end endtask
 initial if(MUT==1)force dut.peer=1'b0;else if(MUT==2)force dut.peer=1'b1;
 initial begin
 for(d=0;d<8;d=d+1)begin
  reset(3'(d));link_up=ALL;repeat(9)tick;
  if(d==0)begin boot_done=1;boot_ok=255;repeat(10)tick;if(sys_ready)$fatal(1,"package fabricated globalready");boot_done=255;end
  else begin boot_done=8'(1<<d);boot_ok=8'(1<<d);end
  waitready;repeat(50)tick;if(!sys_ready||boot_fault)$fatal(1,"unselected checker leaked into role");
  boot_done=0;soft_rst=1;tick;soft_rst=0;repeat(10)tick;
  if(sys_ready||!host_rst_n)$fatal(1,"soft-reset selection/host semantics");waitfault(2);
  reset(3'(d));waitfault(1);
  reset(3'(d));link_up=PART;waitfault(1);           // one link end missing: link timeout, never a release
  reset(3'(d));link_up=ALL;repeat(10)tick;boot_done=(d==0)?255:8'(1<<d);boot_ok=0;waitfault(3);
  reset(3'(d));link_up=ALL;boot_done=(d==0)?255:8'(1<<d);boot_ok=255;waitready;
  die_id=3'(d^1);repeat(5)tick;waitfault(4);
  soft_rst=1;tick;soft_rst=0;repeat(10)tick;
  if(!boot_fault||boot_err!=4||sys_ready)$fatal(1,"strap mutation not sticky");
 end
 $display("PASS NL%0d reset role0 ND8 peer1..7 genuineLOCAL ND1 all roles release/linktimeout/HBMtimeout/bootfail/softreset/strapmutation checks%d",NL,checks);$finish;
 end
 initial begin #10000;$fatal(1,"timeout");end
endmodule
