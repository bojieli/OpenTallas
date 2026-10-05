`timescale 1ps/1ps
module ha5_cp20_runtime(input wire por_n,clk_host,clk_sm,clk_mem,clk_link,
 input wire [1:0] cmd_we, input wire [15:0] cmd_addr,
 input wire [127:0] cmd_wdata, input wire [1:0] db_v,
 output wire [1:0] db_rdy, input wire [63:0] db_token,db_pos,db_job,
 input wire [7:0] db_generation, output wire [1:0] cpl_v,
 input wire [1:0] cpl_rdy, output wire [217:0] cpl_data,
 input wire [3:0] im_we,input wire [13:0] im_addr,input wire [63:0] im_data,
 output wire rst_sm_n,sys_fault,
 input wire [1:0] probe_sel,input wire [31:0] probe_sector,
 output reg [255:0] probe_data,
 output wire [55:0] probe_pc,output wire [3:0] probe_issue,
 output wire [3:0] probe_fetch_request,probe_fetch_line);
ot_ds_hbm_source_entry20 #(.ENABLE(1),.MEM_WORDS(2097152)) dut(
.por_n(por_n),.clk_host(clk_host),.clk_sm(clk_sm),.clk_mem(clk_mem),.clk_link(clk_link),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),.db_v(db_v),.db_rdy(db_rdy),.db_token(db_token),.db_pos(db_pos),.db_job(db_job),.db_generation(db_generation),.cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_data(cpl_data),.im_we(im_we),.im_addr(im_addr),.im_data(im_data),.rst_sm_n(rst_sm_n),.fault(sys_fault));
initial begin : source_images
 string pfx; #1;
if ($value$plusargs("ha5_native_mem_prefix=%s",pfx)) begin
$readmemh($sformatf("%s_d0_p0.hex",pfx),dut.u_cluster.g_on.g_die[0].u_mem.u_ms.g_on.g_s[0].u_part.g_on.u_model.mem);
$readmemh($sformatf("%s_d0_p1.hex",pfx),dut.u_cluster.g_on.g_die[0].u_mem.u_ms.g_on.g_s[1].u_part.g_on.u_model.mem);
$readmemh($sformatf("%s_d1_p0.hex",pfx),dut.u_cluster.g_on.g_die[1].u_mem.u_ms.g_on.g_s[0].u_part.g_on.u_model.mem);
$readmemh($sformatf("%s_d1_p1.hex",pfx),dut.u_cluster.g_on.g_die[1].u_mem.u_ms.g_on.g_s[1].u_part.g_on.u_model.mem);
end else $fatal(1,"source-native images required"); end
always @* begin probe_data=0; case(probe_sel)
0: if(probe_sector<2097152) probe_data=dut.u_cluster.g_on.g_die[0].u_mem.u_ms.g_on.g_s[0].u_part.g_on.u_model.mem[probe_sector];
1: if(probe_sector<2097152) probe_data=dut.u_cluster.g_on.g_die[0].u_mem.u_ms.g_on.g_s[1].u_part.g_on.u_model.mem[probe_sector];
2: if(probe_sector<2097152) probe_data=dut.u_cluster.g_on.g_die[1].u_mem.u_ms.g_on.g_s[0].u_part.g_on.u_model.mem[probe_sector];
3: if(probe_sector<2097152) probe_data=dut.u_cluster.g_on.g_die[1].u_mem.u_ms.g_on.g_s[1].u_part.g_on.u_model.mem[probe_sector];
endcase end
assign probe_pc[0+:14]=dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.g_on.pc;
assign probe_issue[0]=dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.g_on.can_issue;
assign probe_fetch_request[0]=dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.treq_v && dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.treq_rdy;
assign probe_fetch_line[0]=dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.trsp_v && dut.u_cluster.g_on.g_die[0].g_sm[0].u_sm.trsp_rdy;
assign probe_pc[14+:14]=dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.g_on.pc;
assign probe_issue[1]=dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.g_on.can_issue;
assign probe_fetch_request[1]=dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.treq_v && dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.treq_rdy;
assign probe_fetch_line[1]=dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.trsp_v && dut.u_cluster.g_on.g_die[0].g_sm[1].u_sm.trsp_rdy;
assign probe_pc[28+:14]=dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.g_on.pc;
assign probe_issue[2]=dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.g_on.can_issue;
assign probe_fetch_request[2]=dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.treq_v && dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.treq_rdy;
assign probe_fetch_line[2]=dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.trsp_v && dut.u_cluster.g_on.g_die[1].g_sm[0].u_sm.trsp_rdy;
assign probe_pc[42+:14]=dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.g_on.pc;
assign probe_issue[3]=dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.g_on.can_issue;
assign probe_fetch_request[3]=dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.treq_v && dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.treq_rdy;
assign probe_fetch_line[3]=dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.trsp_v && dut.u_cluster.g_on.g_die[1].g_sm[1].u_sm.trsp_rdy;
endmodule
