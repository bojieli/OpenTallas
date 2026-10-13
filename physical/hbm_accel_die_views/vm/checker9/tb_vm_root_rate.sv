`timescale 1ns/1ps
module tb_vm_root_rate;
 reg clk=0;always #0.4166665 clk=~clk;
 reg por_n=0,wr_v=0,wr_bank=0,rd_v=0,rd_bank=0,wr_ACK_ready=1;
 reg [6:0] wr_addr=0,rd_addr=0;
 reg [2062:0] wr_data=0;reg [191:0] wr_owner=0,rd_owner=0;
 reg [3:0] tap_ready=15,tap_ACK_v=0;reg [767:0] tap_ACK_owner=0;
 wire wr_ready,rd_ready,wr_ACK_v,drained,fault,native_release;
 wire [191:0] wr_ACK_owner;wire [3:0] tap_v;wire [8251:0] tap_data;wire [767:0] tap_owner;
 wire mem_cmd_v,mem_cmd_we,mem_cmd_bank;wire [6:0] mem_cmd_addr;wire [2815:0] mem_wd;
 reg mem_rd_v=0;reg [2815:0] mem_rd;
 reg [2815:0] rows[0:255];
 integer cycles=0,start_cycle,write_cycles,read_cycles,owner_checks=0;
`ifdef VM_CK_BASELINE
 ot_hfd_vm_root_x #(.ENABLE(1),.SEATP(1),.FREG(1)) dut(.*);
`else
 vm_root_ck9 #(.ENABLE(1)) dut(.*);
`endif
 always @(posedge clk)begin
  cycles<=cycles+1;mem_rd_v<=mem_cmd_v&&!mem_cmd_we;
  if(mem_cmd_v)begin
   if(mem_cmd_we)rows[{mem_cmd_bank,mem_cmd_addr}]<=mem_wd;
   else mem_rd<=rows[{mem_cmd_bank,mem_cmd_addr}];
  end
 end
 task tick;begin @(posedge clk);#0.001;if(fault)$fatal(1,"rate root fault cycle=%0d",cycles);end endtask
 task step;begin @(negedge clk);end endtask
 function [2062:0] payload(input integer row);
  reg [2062:0] p;
  begin
   for(integer k=0;k<2063;k=k+1)p[k]=((k*13+row*7)%19)<9;
   payload=p;
  end
 endfunction
 function [191:0] owner(input integer row);begin owner=192'h123456789abcdef00123456789abcdef+row;end endfunction
 initial begin
  repeat(3)@(negedge clk);por_n=1;tick();start_cycle=cycles;
  for(integer r=0;r<256;r=r+1)begin
   step();wr_bank=r/128;wr_addr=r%128;wr_owner=owner(r);wr_data=payload(r);wr_v=1;#0.001;
   if(!wr_ready)$fatal(1,"production write not admitted at idle");tick();step();wr_v=0;
   while(!wr_ACK_v)tick();if(wr_ACK_owner!==owner(r))$fatal(1,"production write owner");owner_checks=owner_checks+1;
   tick();if(!drained)$fatal(1,"production write commit not drained");
  end
  write_cycles=cycles-start_cycle;start_cycle=cycles;
  for(integer r=0;r<256;r=r+1)begin
   step();rd_bank=r/128;rd_addr=r%128;rd_owner=owner(r);rd_v=1;#0.001;
   if(!rd_ready)$fatal(1,"production read not admitted at idle");tick();step();rd_v=0;
   while(tap_v==0)tick();
   for(integer t=0;t<4;t=t+1)begin
    if(tap_data[t*2063+:2063]!==payload(r)||tap_owner[t*192+:192]!==owner(r))$fatal(1,"production tap identity/payload");
    owner_checks=owner_checks+1;
   end
   tick(); // Actual sampling edge for all four ready sinks precedes the reverse ACK.
   step();tap_ACK_owner={4{owner(r)}};tap_ACK_v=15;tick();step();tap_ACK_v=0;
   if(!native_release)$fatal(1,"production reverse ACK did not release");tick();if(!drained)$fatal(1,"production read not drained");
  end
  read_cycles=cycles-start_cycle;
  $display("VM_ROOT_RATE PASS writes=256 reads=256 banks=2 depth=128 owner_checks=%0d write_cycles=%0d read_cycles=%0d total_cycles=%0d cycles_per_write_read=%f",owner_checks,write_cycles,read_cycles,write_cycles+read_cycles,(write_cycles+read_cycles)/256.0);
  $display("NATIVE_PRODUCTION_QUALIFICATION OPEN: external memory timing abstract; measured unchanged xload1664beats/2042cycles budget must be applied, no reprice");$finish;
 end
 initial begin #20000;$fatal(1,"production root deadlock");end
endmodule
