`timescale 1ns/1ps
// Actual shared sequencer with selected1124-edge admission duration. Source-bound
// component edge ledger; synthetic fixed lists, no die-clock/production image claim.
module tb_ovl_admission_launch;
 parameter integer EARLY=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,ep=0;
 wire[11:0]ta,ra;reg[31:0]tq=0,rq=0,tc=0,rc=0;
 wire cs,rs,ad,ready,fault;wire[5:0]a;wire[31:0]d;
 // Both words execute a start after4edges; second waits100edges thenwraps.
 always @(posedge ck)begin
  tq<=ta==0 ? (32'd4<<12)|(1<<11)|(1<<10) : (32'd100<<12)|(1<<7);
  rq<=ra==0 ? (32'd4<<12)|(1<<11)|(1<<10) : (32'd100<<12)|(1<<7);
  tc<=tq;rc<=rq;
 end
 ot_qwen_d2d_ovl_seq #(.AW(12),.ADM(1),.ADM_OFS(72),.ADM_LEN(1124),.FIRST_OFS(EARLY?1197:1198)) dut(
 .ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(ep),.halt(1'b0),
 .cfg_tx_we(),.cfg_rx_we(),.cfg_addr(a),.cfg_data(d),.cal_start(cs),.cal_seg(),.cal_start_rx(rs),.cal_seg_rx(),
 .cal_user_tx(),.cal_user_rx(),.tx_rom_addr(ta),.tx_rom_q(tc),.rx_rom_addr(ra),.rx_rom_q(rc),.cal_ready(ready),.adm_done(ad),.running(),.fault(fault));
 integer e=0,E=-1,A=-1,G=-1,S=-1;
 always @(posedge ck)begin
  e<=e+1;
  if(ep && E<0)E=e;
  if(ad && A<0)begin A=e;$display("ADMLAUNCH adm_done_sample%0d rel%0d",e,e-E);end
  if(dut.go)begin G=e;$display("ADMLAUNCH go_sample%0d rel%0d adm_preedge%b",e,e-E,ad);end
  if(dut.t_start && S<0)begin S=e;$display("ADMLAUNCH core_start_pin_sample%0d rel%0d",e,e-E);end
 end
 initial begin
  repeat(5)@(negedge ck);rst_n=1;repeat(100)@(negedge ck);ep=1;@(negedge ck);ep=0;
  repeat(1230)@(negedge ck);
  if(EARLY)begin
   if(!fault || G!=A-1)$fatal(1,"ADMLAUNCH mutant did not catch earlygo G%0d A%0d f%b",G,A,fault);
   $display("ADMLAUNCH_PASS EARLY1 rejected go one edge before adm_done");
  end else begin
   if(fault || G!=A || A-E!=1198 || S-G!=5)$fatal(1,"ADMLAUNCH G%0d A%0d E%0d S%0d f%b",G,A,E,S,fault);
   $display("ADMLAUNCH_PASS EARLY0 same-edge adm_done/go accepted, MIN_DT4 corepublicationgo+4/samplego+5");
  end
  $finish;
 end
endmodule
