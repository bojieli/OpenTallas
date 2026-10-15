`timescale 1ns/1ps
`default_nettype none
module tb_hbm_svc_pc_boundary_cost;
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
`ifdef BOUNDARY
 ot_hbm_svc_static_pc_boundary dut(.*);
`else
 ot_hbm_svc_static_pc dut(.*);
`endif
 integer read_vectors=0,write_vectors=0,read_requests=0,overlap_cycles=0,fault_cases=0;
 function automatic [255:0] payload(input integer bank,input integer slot);
  integer j;begin for(j=0;j<8;j=j+1)payload[j*32+:32]=32'h8acf0123 ^ (bank*32'h13579000) ^ (slot*32'h10021) ^ (j*32'h1234567);end
 endfunction
 task tick;begin @(posedge clk);#1;end endtask

 integer cycle=0;
 always @(posedge clk) cycle <= cycle+1;
 task quiet;begin open_v=0;fill_v=0;read_v=0;retire_v=0;cmd_v=0;k_rdy=0;k_wr_done=0;kr_v=0;end endtask

 integer i,started,read_elapsed,write_elapsed,guard;
 task wait_request;begin guard=0;while(!k_v)begin tick;guard=guard+1;if(guard>20)$fatal(1,"request timeout");end end endtask
 task wait_done;begin guard=0;while(!done)begin tick;guard=guard+1;if(guard>20)$fatal(1,"done timeout");end end endtask
 initial begin
 quiet;rst_n=0;tick;tick;rst_n=1;repeat(4)tick;
 open_v=1;open_bank=0;open_epoch=16'h1234;open_count=64;tick;open_v=0;repeat(3)tick;
 cmd_v=1;cmd_write=0;cmd_bank=0;cmd_epoch=16'h1234;cmd_addr=30'h1000;cmd_step=32;tick;cmd_v=0;started=cycle;
 for(i=0;i<64;i=i+1)begin
 wait_request;if(k_addr!==30'h1000+i*32||k_we)$fatal(1,"prefetch request");
 k_rdy=1;tick;k_rdy=0;
 kr_v=1;kr_tag=17'h01234;kr_beat=0;kr_data=payload(0,i);tick;kr_v=0;
 end
 wait_done;read_elapsed=cycle-started;tick;repeat(2)tick;
 cmd_v=1;cmd_write=1;cmd_addr=30'h2000;tick;cmd_v=0;started=cycle;
 for(i=0;i<64;i=i+1)begin
 wait_request;if(k_wdata!==payload(0,i)||!k_we||k_addr!==30'h2000+i*32)$fatal(1,"write request");
 k_rdy=1;tick;k_rdy=0;k_wr_done=1;tick;k_wr_done=0;
 end
 wait_done;write_elapsed=cycle-started;
 if(fault||bank_owned||busy)$fatal(1,"final state");
 $display("LATENCY_COST sectors=64 prefetch_elapsed=%0d writeback_elapsed=%0d",read_elapsed,write_elapsed);$finish;
 end
 initial begin #1000000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
