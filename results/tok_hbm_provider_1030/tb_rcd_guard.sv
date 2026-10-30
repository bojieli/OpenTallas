`timescale 1ns/1ps
`default_nettype none
module tb_rcd_guard;
 reg clk=0,rst_n=0;always begin #0.416 clk=1;#0.417 clk=0;end
 integer edge_no=0,act_edge=-100000,reads=0;reg cfg_v=0;wire pc_rst_n,ready,ref_fault;wire[7:0]reload;
 ot_hbm_pc_refresh_cfg #(.NPC(1),.RMIN(144),.RMAX(252))refcfg(.clk(clk),.rst_n(rst_n),.clk_hbm(clk),.rst_hbm_n(rst_n),.tgt(8'd127),.cfg_v(cfg_v),.cfg_target(8'd127),.cfg_addr(12'h800),.cfg_data(256'd144),.refresh_reload(reload),.pc_rst_n(pc_rst_n),.ready(ready),.active(),.fault(ref_fault));
 reg kv=0;wire krdy,krv;wire[16:0]krtag;wire[3:0]krbeat;wire[255:0]krdata;wire fault;wire row_v,col_v,col_we;wire[2:0]row_op;wire[4:0]row_bank,col_bank,col_col;wire[18:0]row_row;
 reg dram_rvalid=0;reg[28:0]due=0;reg[255:0]dram_rdata=0;
 localparam[255:0]DATA=256'h3f8000073f8000063f8000053f8000043f8000033f8000023f8000013f800000;
 ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(.TIMING_833(1),.OREG(1),.KREG(1),.KRREG(1),.RREG(1),.WPAY(1),.QREG(1))pc(
 .clk(clk),.rst_n(pc_rst_n),.pc_id(5'd0),.refresh_reload(reload),.k_v(kv),.k_rdy(krdy),.k_we(1'b0),.k_addr(30'd0),.k_len(4'd1),.k_tag(17'h123),.k_wdata(256'd0),.k_wstrb(32'd0),.k_wr_done(),
 .kr_v(krv),.kr_rdy(1'b1),.kr_tag(krtag),.kr_beat(krbeat),.kr_data(krdata),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(),.col_strb(),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.pc_fault(fault),.owner_fault_split());
 task tick;begin @(negedge clk);end endtask
 always @(posedge clk)begin
 edge_no=edge_no+1;
 if(rst_n)begin
 if(fault||ref_fault)$fatal(1,"NATIVE_COMPONENT_FAULT");
 if(row_v&&row_op==1)act_edge=edge_no;
 if(col_v)begin
 if(col_we||col_bank!=0||col_col!=0)$fatal(1,"UNEXPECTED_READ_IDENTITY");
 if((edge_no-act_edge)*833<19375)$fatal(1,"LOCAL_NS_RCD_RD edge=%0d gap_edges=%0d observed_ps=%0d required_ps=19375",edge_no,edge_no-act_edge,(edge_no-act_edge)*833);
 reads=reads+1;due[0]<=1;
 end
 due<=due<<1;if(col_v)due[0]<=1;dram_rvalid<=due[28];dram_rdata<=DATA;
 if(krv)begin
 if(reads!=1||krtag!==17'h123||krbeat!==0||krdata!==DATA)$fatal(1,"REAL_COMPONENT_DATA");
 $display("PASS REAL_H9B_PROFILE833_ONE_READ RCD_ns_guard native_data read=%0d edge=%0d",reads,edge_no);$finish;
 end
 end end
 initial begin
 repeat(32)tick();rst_n=1;repeat(16)tick();cfg_v=1;tick();cfg_v=0;
 while(!pc_rst_n)tick();repeat(16)tick();while(!krdy)tick();kv=1;tick();kv=0;
 repeat(2000)tick();$fatal(1,"RCD_CONTROL_TIMEOUT");
 end
endmodule
`default_nettype wire
