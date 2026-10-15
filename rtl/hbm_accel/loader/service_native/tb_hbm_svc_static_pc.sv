`timescale 1ns/1ps
`default_nettype none
module tb_hbm_svc_static_pc;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,open_v=0,open_bank=0,fill_v=0,fill_bank=0,read_v=0,read_bank=0;
 reg [15:0] open_epoch=0,fill_epoch=0,read_epoch=0;
 reg [6:0] open_count=0; reg [5:0] fill_slot=0,read_slot=0;
 reg [255:0] fill_data=0;
 wire out_v;wire [255:0] out_data;
 reg retire_v=0,retire_bank=0;reg [15:0] retire_epoch=0;
 reg cmd_v=0,cmd_write=0,cmd_bank=0;reg [15:0] cmd_epoch=0;
 reg [29:0] cmd_addr=0,cmd_step=32;
 wire [1:0] block_ready,bank_owned;wire busy,done,fault,k_v,k_we,kr_rdy;
 reg k_rdy=0,k_wr_done=0,kr_v=0;
 wire [29:0] k_addr;wire [3:0] k_len;wire [16:0] k_tag;
 wire [255:0] k_wdata;wire [31:0] k_wstrb;
 reg [16:0] kr_tag=0;reg [3:0] kr_beat=0;reg [255:0] kr_data=0;
 ot_hbm_svc_static_pc dut(.*);
 integer read_vectors=0,write_vectors=0,read_requests=0,overlap_cycles=0,fault_cases=0;
 function automatic [255:0] payload(input integer bank,input integer slot);
  integer j;begin for(j=0;j<8;j=j+1)payload[j*32+:32]=32'h8acf0123 ^ (bank*32'h13579000) ^ (slot*32'h10021) ^ (j*32'h1234567);end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task reset_dut;begin
  rst_n=0;open_v=0;fill_v=0;read_v=0;retire_v=0;cmd_v=0;k_rdy=0;k_wr_done=0;kr_v=0;
  tick;tick;rst_n=1;tick;
  if(fault||busy||block_ready||out_v||done)$fatal(1,"reset state");
 end endtask
 task open_block(input bit b,input integer n);begin
  open_v=1;open_bank=b;open_epoch=b?16'h4321:16'h1234;open_count=n;tick;open_v=0;
  if(fault)$fatal(1,"open fault");
 end endtask
 task command(input bit b,input bit w,input [29:0] base);begin
  cmd_v=1;cmd_bank=b;cmd_write=w;cmd_epoch=b?16'h4321:16'h1234;cmd_addr=base;cmd_step=32;tick;cmd_v=0;
  if(!busy||fault)$fatal(1,"command not started");
 end endtask
 task check_request(input bit b,input bit w,input integer slot,input [29:0] base);begin
  if(!k_v||k_we!==w||k_addr!==base+slot*32||k_len!==1||k_tag!=={b,(b?16'h4321:16'h1234)}||k_wstrb!==32'hffffffff)
   $fatal(1,"request mismatch b=%0d w=%0d slot=%0d addr=%h tag=%h",b,w,slot,k_addr,k_tag);
  if(w && k_wdata!==payload(b,slot))$fatal(1,"payload write mismatch bank=%0d slot=%0d",b,slot);
 end endtask
 task prefetch(input bit b,input integer n,input [29:0] base);integer s,d;begin
  command(b,0,base);
  for(s=0;s<n;s=s+1)begin
   for(d=0;d<(s%3)+1;d=d+1)begin check_request(b,0,s,base);tick;end
   check_request(b,0,s,base);k_rdy=1;tick;k_rdy=0;read_requests=read_requests+1;
   for(d=0;d<(s%4)+1;d=d+1)begin
    if(k_v||!busy||!kr_rdy||done)$fatal(1,"prefetch outstanding/early completion");tick;
   end
   kr_v=1;kr_tag={b,(b?16'h4321:16'h1234)};kr_beat=0;kr_data=payload(b,s);tick;kr_v=0;
   if(fault||done!==(s==n-1)||block_ready[b]!==(s==n-1))$fatal(1,"prefetch completion slot=%0d",s);
  end
  if(busy||!block_ready[b])$fatal(1,"prefetch ready state");tick;
 end endtask
 task writeback(input bit b,input integer n,input [29:0] base);integer s,d,guard;begin
  command(b,1,base);
  for(s=0;s<n;s=s+1)begin
   guard=0;while(!k_v)begin tick;guard=guard+1;if(guard>5)$fatal(1,"write SRAM staging timeout");end
   for(d=0;d<(s%3)+1;d=d+1)begin check_request(b,1,s,base);tick;end
   check_request(b,1,s,base);k_rdy=1;tick;k_rdy=0;
   if(done||!busy||!block_ready[b])$fatal(1,"write retired on accept");
   for(d=0;d<(s%5)+1;d=d+1)begin
    if(k_v||done||!busy||!block_ready[b])$fatal(1,"write did not wait for real completion");tick;
   end
   k_wr_done=1;tick;k_wr_done=0;write_vectors=write_vectors+1;
   if(fault||done!==(s==n-1))$fatal(1,"write done mismatch b=%0d slot=%0d",b,s);
  end
  if(busy||block_ready[b]||bank_owned[b])$fatal(1,"write retirement missing");tick;
  if(done)$fatal(1,"completion pulse exceeded one cycle");
 end endtask
 task expect_fault(input integer id);begin
  tick;if(!fault)$fatal(1,"fault case %0d not detected",id);
  fill_v=0;read_v=0;kr_v=0;k_wr_done=0;tick;
  if(!fault||k_v||out_v||kr_rdy)$fatal(1,"fault case %0d did not fail closed",id);
  fault_cases=fault_cases+1;
 end endtask
 integer i;
 initial begin
  reset_dut;open_block(0,20);open_block(1,64);prefetch(0,20,30'h1040);
  // Every pulse is scheduled in advance; unrelated-bank SRAM fills overlap.
  for(i=0;i<64;i=i+1)begin
   read_v=1;read_bank=0;read_epoch=16'h1234;read_slot=i%20;
   fill_v=1;fill_bank=1;fill_epoch=16'h4321;fill_slot=i;fill_data=payload(1,i);
   tick;if(!out_v||out_data!==payload(0,i%20))$fatal(1,"payload read mismatch slot=%0d",i%20);
   if(fault)$fatal(1,"overlap fault");read_vectors=read_vectors+1;overlap_cycles=overlap_cycles+1;
  end
  fill_v=0;read_v=0;tick;if(out_v||block_ready!==3)$fatal(1,"fixed pulse termination/readiness");
  for(i=0;i<64;i=i+1)begin
   read_v=1;read_bank=1;read_epoch=16'h4321;read_slot=i;tick;
   if(!out_v||out_data!==payload(1,i))$fatal(1,"payload read mismatch bank=1 slot=%0d",i);
   read_vectors=read_vectors+1;
  end
  read_v=0;tick;if(out_v)$fatal(1,"extra read pulse");
  writeback(1,64,30'h2000);writeback(0,20,30'h4000);
  reset_dut;open_block(1,64);prefetch(1,64,30'h8020);
  for(i=0;i<64;i=i+1)begin
   read_v=1;read_bank=1;read_epoch=16'h4321;read_slot=i;tick;
   if(!out_v||out_data!==payload(1,i))$fatal(1,"payload read mismatch prefetch64 slot=%0d",i);
   read_vectors=read_vectors+1;
  end
  read_v=0;tick;writeback(1,64,30'h10000);
  // Independent fault injections, each from clean ownership state.
  reset_dut;open_block(0,20);command(0,0,30'h1000);k_rdy=1;tick;k_rdy=0;
  kr_v=1;kr_tag=17'h01235;kr_beat=0;kr_data=payload(0,0);expect_fault(1);
  reset_dut;open_block(0,20);fill_v=1;fill_bank=0;fill_epoch=16'h1234;fill_slot=0;fill_data=payload(0,0);tick;
  expect_fault(2); // Duplicate fixed fill, unchanged slot.
  reset_dut;open_block(0,20);read_v=1;read_bank=0;read_epoch=16'h1234;read_slot=0;expect_fault(3);
  // The physical SRAM has only one write port: PHY response plus static fill conflicts.
  reset_dut;open_block(0,20);open_block(1,64);command(0,0,30'h1000);k_rdy=1;tick;k_rdy=0;
  kr_v=1;kr_tag=17'h01234;kr_data=payload(0,0);
  fill_v=1;fill_bank=1;fill_epoch=16'h4321;fill_slot=0;fill_data=payload(1,0);expect_fault(4);
  reset_dut;open_block(0,1);fill_v=1;fill_bank=0;fill_epoch=16'h1234;fill_slot=0;fill_data=payload(0,0);tick;fill_v=0;
  command(0,1,30'h1000);read_v=1;read_bank=0;read_epoch=16'h1234;read_slot=0;expect_fault(5);
  $display("STATIC_PC PASS read_vectors=%0d write_vectors=%0d prefetch_requests=%0d simultaneous_read_fill=%0d faults=%0d",read_vectors,write_vectors,read_requests,overlap_cycles,fault_cases);
  $finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
