`timescale 1ps/1fs
module tb_hbm_svc_native_initial_descriptor;
reg clk=0;always #512 clk=~clk;
wire[31:0]pc_clk={32{clk}};reg rst_n=0;
reg[31:0]k_v=0,k_we=0;wire[31:0]k_rdy,k_wr_done,kr_v;
reg[959:0]k_addr=0;reg[127:0]k_len={32{4'd4}};reg[543:0]k_tag=0;
reg[8191:0]k_wdata=0;reg[1023:0]k_wstrb='1;reg[31:0]kr_rdy=0;
wire[543:0]kr_tag;wire[127:0]kr_beat;wire[8191:0]kr_data;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data;wire[1023:0]col_strb;wire[31:0]dram_rvalid;wire[8191:0]dram_rdata;wire fault;
ot_hbm_svc_native_sector_prefetch_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1)) dut(.*);
assign dram_rvalid=0;assign dram_rdata=0;
function automatic [29:0] sector(input [14:0] row);reg [29:0] s;begin s={row,15'b0};s[6:2]=s[11:7]^s[16:12];sector=s;end endfunction
 task tick;begin @(posedge clk);#1;end endtask
 task reset_dut;begin rst_n=0;k_v=0;tick;tick;rst_n=1;tick;end endtask
 initial begin
  reset_dut;@(negedge clk);k_v=1;k_addr[0+:30]=sector(15'h1234);k_len[0+:4]=1;
  #1;if(!k_rdy[0]||!dut.g_pc[0].initial_descriptor||!dut.g_pc[0].controller.desc_v||dut.g_pc[0].controller.desc_row!==19'h1234||!dut.g_pc[0].dr)$fatal(1,"initial descriptor not real accepted row");
  tick;k_v=0;if(dut.g_pc[0].state!==3||dut.g_pc[0].active_row!==19'h1234)$fatal(1,"initial accepted descriptor did not enter RUN");
  reset_dut;@(negedge clk);force dut.g_pc[0].dr=0;k_v=1;k_addr[0+:30]=sector(15'h2345);#1;
  if(!dut.g_pc[0].controller.desc_v||dut.g_pc[0].controller.desc_row!==19'h2345)$fatal(1,"fallback initial transaction missing row");
  tick;k_v=0;if(dut.g_pc[0].state!==1)$fatal(1,"dr0 did not preserve DESC fallback");release dut.g_pc[0].dr;
  reset_dut;@(negedge clk);
  force dut.g_pc[0].state=3;force dut.g_pc[0].active_row=19'h1234;force dut.g_pc[0].count=0;force dut.g_pc[0].read_reserved=0;
  k_v=1;k_addr[0+:30]=sector(15'h3456);#1;
  if(!k_rdy[0]||dut.g_pc[0].initial_descriptor||dut.g_pc[0].controller.desc_v)$fatal(1,"subsequent row improperly bypassed descriptor path");
  if(dut.g_pc[0].controller.desc_row!==19'h1234)$fatal(1,"subsequent row changed descriptor mux prematurely");
  release dut.g_pc[0].state;release dut.g_pc[0].active_row;release dut.g_pc[0].count;release dut.g_pc[0].read_reserved;
  tick;k_v=0;if(dut.g_pc[0].state!==1||dut.g_pc[0].active_row!==19'h3456)$fatal(1,"subsequent row change did not take original DESC path");
  $display("NATIVE_INITIAL_DESCRIPTOR PASS accepted_initial_row dr0_fallback subsequent_row_change_unchanged");$finish;
 end
endmodule
