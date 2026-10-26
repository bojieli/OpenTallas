`timescale 1ps/1fs
module tb_native_mission_gate #(parameter integer MUT=0);
 reg clk=0;always #416.5 clk=~clk;
 reg rst_n=0,request=0,static_setup_ready=0,program_ready=0,mission_start=0;
 wire old_default,patched_default,mission_event;
 integer cyc=0,images=0,events=0;
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) gold(clk,rst_n,request,static_setup_ready&&program_ready,old_default);
 qkd_d2d_boot_event_bridge #(.ENABLE(1)) def(clk,rst_n,request,static_setup_ready&&program_ready&&(!0||mission_start),patched_default);
 // Exact production HOST installed expression is used by the generated wrapper.
 kv_native_mission_gate #(.MUT(MUT)) dut(clk,rst_n,request,static_setup_ready,program_ready,mission_start,mission_event);
 always @(posedge clk)if(rst_n)begin
   cyc++;
   if(old_default!==patched_default)$fatal(1,"DEFAULT_LOCKSTEP");
   if(mission_event)begin
     if(!mission_start||images!=13)$fatal(1,"MISSION_GATE_EARLY");
     events++;
   end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;
  repeat(2)@(negedge clk);request=1;
  @(negedge clk);request=0;
  // The installed inputs can become true while mission remains stopped.
  for(integer i=0;i<13;i++)begin repeat(2)@(negedge clk);images++;end
  static_setup_ready=1;program_ready=1;
  repeat(8)@(negedge clk);
  if(events!=0)$fatal(1,"MISSION_GATE_EARLY");
  mission_start=1;
  repeat(8)@(negedge clk);
  if(events!=1)$fatal(1,"MISSION_GATE_LOST count%0d",events);
  $display("PASS 13images beforemission; oneeventafterSTART; defaultlockstep cycles%0d",cyc);$finish;
 end
endmodule
