`timescale 1ns/1ps
module tb_qkd_embgw_fresh_boot;
 parameter MUT=0;
 reg ck=0;always #5 ck=~ck;reg rn=0,bend=0;reg[63:0]expected=0;
 reg[3:0]ev=0;reg[2091:0]ed=0;wire[3:0]take;wire ready,fault;
 ot_qfd_emb_gw_splitboot #(.MUT(MUT))dut(.ck(ck),.rn(rn),.ea_v(1'b0),.ea_kind(1'b0),.ea_addr(24'b0),.ea_cr(),.eq_v(),.eq_d(),.e_v(ev),.e_d(ed),.e_take(take),.g_v(),.g_tag(),.g_d(),.g_rdy(1'b0),.bend_v(bend),.bend_d(expected),.emb_ready(ready),.fault(fault),.fault_code(),.fetches());
 task status;
  for(integer i=0;i<4;i++)begin
   @(negedge ck);ev=1<<i;ed[i*523+:523]={1'b1,2'd2,1'b0,3'd0,4'd0,416'd0,32'd0,32'd25,32'd1};
   @(negedge ck);ev=0;repeat(3)@(negedge ck);
  end
 endtask
 task begin_check(input[31:0]sum);
  @(negedge ck);bend=1;expected={sum,32'd4};@(negedge ck);bend=0;
 endtask
 initial begin
  repeat(3)@(negedge ck);rn=1;
  begin_check(100);status();wait(ready);if(fault)$fatal(1,"good first checksum rejected");
  begin_check(101);if(ready)$fatal(1,"new BOOT_END retained stale image readiness");
  status();wait(fault);if(ready)$fatal(1,"bad reload retained ready");
  $display("PASS fresh embedding image certificate good then bad reload");$finish;
 end
 initial begin #3000;$fatal(1,"watchdog");end
endmodule
