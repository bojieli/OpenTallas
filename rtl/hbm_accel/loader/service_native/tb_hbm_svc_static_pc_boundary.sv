`timescale 1ns/1ps
`default_nettype none
module tb_hbm_svc_static_pc_boundary;
 reg clk=0; always #5 clk=~clk;
 wire core_clk=clk;
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
 ot_hbm_svc_static_pc_boundary dut(.*);
 integer read_vectors=0,write_vectors=0,read_requests=0,overlap_cycles=0,fault_cases=0;
 function automatic [255:0] payload(input integer bank,input integer slot);
  integer j;begin for(j=0;j<8;j=j+1)payload[j*32+:32]=32'h8acf0123 ^ (bank*32'h13579000) ^ (slot*32'h10021) ^ (j*32'h1234567);end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask

 integer cycle=0;
 always @(posedge clk) cycle <= cycle+1;
 task quiet;begin open_v=0;fill_v=0;read_v=0;retire_v=0;cmd_v=0;k_rdy=0;k_wr_done=0;kr_v=0;end endtask
 task reset_dut;begin quiet;rst_n=0;tick;tick;rst_n=1;repeat(3)tick;
 if(fault||busy||block_ready||out_v||done||k_v)$fatal(1,"reset state");end endtask
 task open_block(input bit b,input integer n);begin
 open_v=1;open_bank=b;open_epoch=b?16'h4321:16'h1234;open_count=n;tick;open_v=0;repeat(2)tick;
 if(fault||!bank_owned[b])$fatal(1,"open ownership");end endtask
 task command(input bit b,input bit w,input [29:0] addr);begin
 cmd_v=1;cmd_bank=b;cmd_write=w;cmd_epoch=b?16'h4321:16'h1234;cmd_addr=addr;cmd_step=32;tick;cmd_v=0;
 repeat(2)tick;if(fault||!busy)$fatal(1,"command failed");end endtask
 task wait_req;integer guard;begin guard=0;while(!k_v)begin tick;guard=guard+1;if(guard>12)$fatal(1,"request timeout");end end endtask
 task request(input bit b,input bit w,input integer slot,input [29:0] base);integer d;reg [339:0] held;begin
 wait_req;
 if(k_we!==w||k_addr!==base+slot*32||k_tag!=={b,(b?16'h4321:16'h1234)}||k_len!==1||k_wstrb!==32'hffffffff)$fatal(1,"request mismatch");
 if(w&&k_wdata!==payload(b,slot))$fatal(1,"payload write mismatch");
 held={k_addr,k_len,k_tag,k_we,k_wdata,k_wstrb};
 for(d=0;d<slot%4;d=d+1)begin tick;if(!k_v||{k_addr,k_len,k_tag,k_we,k_wdata,k_wstrb}!==held)$fatal(1,"stalled request changed");end
 k_rdy=1;tick;k_rdy=0;if(k_v)$fatal(1,"request not consumed");end endtask
 task prefetch(input bit b,input integer n,input [29:0] base);integer j;begin
 command(b,0,base);
 for(j=0;j<n;j=j+1)begin
 request(b,0,j,base);repeat(j%3)tick;
 if(!kr_rdy)$fatal(1,"KR empty buffer not ready");
 kr_v=1;kr_tag={b,(b?16'h4321:16'h1234)};kr_beat=0;kr_data=payload(b,j);tick;kr_v=0;
 if(done||fault||kr_rdy)$fatal(1,"KR completed without transport stage");
 tick;if(done||fault)$fatal(1,"done missing status stage");
 tick;if(fault||done!==(j==n-1)||block_ready[b]!==(j==n-1))$fatal(1,"prefetch completion timing j=%0d",j);
 read_requests=read_requests+1;
 end
 tick;if(done||busy)$fatal(1,"prefetch done pulse");end endtask
 task writeback(input bit b,input integer n,input [29:0] base);integer j;begin
 command(b,1,base);
 for(j=0;j<n;j=j+1)begin
 request(b,1,j,base);repeat(j%5+1)tick;
 if(done||!busy||!bank_owned[b])$fatal(1,"retired before real write ACK");
 k_wr_done=1;tick;k_wr_done=0;if(done)$fatal(1,"write ACK ingress bypassed");
 tick;if(done)$fatal(1,"write ACK status bypassed");
 tick;if(fault||done!==(j==n-1))$fatal(1,"write completion timing");write_vectors=write_vectors+1;
 end
 if(busy||bank_owned[b])$fatal(1,"write retirement");tick;if(done)$fatal(1,"duplicate completion");end endtask
 task reads(input bit b,input integer n,input bit fill_other);integer j;begin
 for(j=0;j<n+2;j=j+1)begin
 read_v=j<n;read_bank=b;read_epoch=b?16'h4321:16'h1234;read_slot=j;
 fill_v=fill_other&&j<n;fill_bank=!b;fill_epoch=b?16'h1234:16'h4321;fill_slot=j;fill_data=payload(!b,j);
 tick;
 if(out_v!==(j>=2))$fatal(1,"read exact latency j=%0d out_v=%b",j,out_v);
 if(j>=2)begin if(out_data!==payload(b,j-2))$fatal(1,"payload read mismatch slot=%0d",j-2);read_vectors=read_vectors+1;end
 end
 tick;if(out_v||fault)$fatal(1,"extra output or overlap fault");end endtask
 task fill_block(input bit b,input integer n);integer j;begin
 for(j=0;j<n;j=j+1)begin fill_v=1;fill_bank=b;fill_epoch=b?16'h4321:16'h1234;fill_slot=j;fill_data=payload(b,j);tick;end
 fill_v=0;repeat(2)tick;if(fault||!block_ready[b])$fatal(1,"fill readiness");end endtask
 task fault_check;begin repeat(4)tick;if(!fault||k_v||kr_rdy||out_v)$fatal(1,"fault not closed");fault_cases=fault_cases+1;end endtask
 integer i;
 initial begin
 reset_dut;open_block(0,64);open_block(1,64);prefetch(0,64,30'h1000);
 reads(0,64,1);reads(1,64,0);writeback(0,64,30'h4000);writeback(1,64,30'h8000);
 reset_dut;open_block(0,1);command(0,0,30'h1000);request(0,0,0,30'h1000);
 kr_v=1;kr_tag=17'h01235;kr_beat=0;tick;kr_v=0;fault_check;
 reset_dut;open_block(0,1);fill_block(0,1);
 fill_v=1;fill_bank=0;fill_epoch=16'h1234;fill_slot=0;tick;fill_v=0;fault_check;
 reset_dut;open_block(0,1);read_v=1;read_bank=0;read_epoch=16'h1234;read_slot=0;tick;read_v=0;fault_check;
 reset_dut;open_v=1;open_count=0;tick;open_v=0;fault_check;
 reset_dut;open_block(0,1);retire_v=1;retire_bank=0;retire_epoch=16'hffff;tick;retire_v=0;fault_check;
 // The PHY is also allowed to complete on the actual request-accept edge.
 reset_dut;open_block(0,1);command(0,0,30'h1000);wait_req;
 k_rdy=1;kr_v=1;kr_tag=17'h01234;kr_beat=0;kr_data=payload(0,0);tick;k_rdy=0;kr_v=0;
 if(done||fault)$fatal(1,"zero wait response bypass");tick;if(done||fault)$fatal(1,"zero wait status bypass");tick;
 if(!done||fault||!block_ready[0])$fatal(1,"zero wait response lost");tick;reads(0,1,0);
 command(0,1,30'h2000);wait_req;
 if(k_wdata!==payload(0,0))$fatal(1,"zero wait write payload");
 k_rdy=1;k_wr_done=1;tick;k_rdy=0;k_wr_done=0;
 if(done||fault)$fatal(1,"zero wait write bypass");tick;if(done||fault)$fatal(1,"zero wait write status bypass");tick;
 if(!done||fault||bank_owned[0])$fatal(1,"zero wait write completion lost");
 // Queuing a write is not a real accepted PHY write.
 reset_dut;open_block(0,1);fill_block(0,1);command(0,1,30'h2000);wait_req;
 k_wr_done=1;tick;k_wr_done=0;fault_check;
 // Likewise, a read still stalled at k_rdy=0 cannot receive real data.
 reset_dut;open_block(0,1);command(0,0,30'h1000);wait_req;
 kr_v=1;kr_tag=17'h01234;kr_beat=0;tick;kr_v=0;fault_check;
 $display("STATIC_PC_BOUNDARY PASS read_vectors=%0d write_vectors=%0d prefetch_requests=%0d faults=%0d read_added_cycles=2 boundary_ff_declared=1313",read_vectors,write_vectors,read_requests,fault_cases);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
