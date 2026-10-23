`timescale 1ns/1ps
module tb_hostprog #(parameter integer CASE=0, CMUT=0, IMUT=0, N=462, LINES=125);
reg clk=0, clk_s=0, rst_n=0;
always #5 clk=~clk;
always #6.666667 clk_s=~clk_s;
reg [0:0] s_awvalid = 0;
wire [0:0] s_awready;
reg [11:0] s_awaddr = 0;
reg [0:0] s_wvalid = 0;
wire [0:0] s_wready;
reg [31:0] s_wdata = 0;
reg [3:0] s_wstrb = 0;
wire [0:0] s_bvalid;
reg [0:0] s_bready = 0;
wire [1:0] s_bresp;
reg [0:0] s_arvalid = 0;
wire [0:0] s_arready;
reg [11:0] s_araddr = 0;
wire [0:0] s_rvalid;
reg [0:0] s_rready = 0;
wire [31:0] s_rdata;
wire [0:0] cfg_v;
wire [7:0] cfg_target;
wire [11:0] cfg_addr;
wire [255:0] cfg_data;
wire [0:0] desc_v;
wire [11:0] desc_base;
wire [12:0] desc_limit;
wire [15:0] desc_loops;
wire [0:0] launch_v;
wire [0:0] fault;
wire [0:0] obs_q_v;
wire [7:0] obs_q_idx;
wire [31:0] obs_q_d;
reg [0:0] obs_r_v = 0;
reg [7:0] obs_r_idx = 0;
reg [31:0] obs_r_d = 0;
ot_hbm_host_static_ingress_obs #(.MUT(IMUT),.TARGET_MASK(256'hffffffff000f003f000000f3e1f1ffffffffffff0ff1000000000000)) ingress(.clk(clk),.rst_n(rst_n),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.block_ready(1'b1),.program_active(1'b0),.program_fault(1'b0),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.fault(fault),.obs_q_v(obs_q_v),.obs_q_idx(obs_q_idx),.obs_q_d(obs_q_d),.obs_r_v(obs_r_v),.obs_r_idx(obs_r_idx),.obs_r_d(obs_r_d));

wire pw_we;wire[22:0]pw_addr;wire[255:0]pw_data;wire collar_fault;wire ready,start_v;wire[255:0]prm;
ot_hbm_static_cfg_collar #(.MUT(CMUT),.SU_DICT_CAP({32'd1,32'd1,32'd1,32'd1,32'd1,32'd2,32'd13,32'd9,32'd10,32'd3}),.SPARSE_SU(1),.PAGE_W(12),.NS(1),.NPR(1),.NREC(0),.NGO(1),.NB(2),.NF(1),.XSER(1)) collar(
.clk(clk_s),.clk_in(clk),.rst_n(rst_n),.tgt(8'd112),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.c_busy({pgp_valid,pgp_busy}),.c_done(pgp_done),.c_fault(root_fault),.pw_we(pw_we),.pw_addr(pw_addr),.pw_data(pw_data),.prm(prm),.start_v(start_v),.go(),.rec(),.ready(ready),.active(),.fault(collar_fault));

reg[278:0] image[0:N-1];integer writes=0,starts=0;
always @(posedge clk_s) if(pw_we)begin
if(writes<N && (pw_addr!==image[writes][278:256] || pw_data!==image[writes][255:0]))$fatal(1,"HOSTPROG_DATA_FAIL index=%d address=%d",writes,pw_addr);
if(!(CASE==6 && writes==N))writes=writes+1;end
always @(posedge clk_s) if(start_v)starts=starts+1;
task write32(input[11:0]a,input[31:0]v);
begin
@(negedge clk);s_awvalid=1;s_awaddr=a;s_wvalid=1;s_wdata=v;s_wstrb=15;s_bready=1;
fork
begin do @(posedge clk);while(!s_awready);@(negedge clk);s_awvalid=0;end
begin do @(posedge clk);while(!s_wready);@(negedge clk);s_wvalid=0;end
join
while(!s_bvalid)@(negedge clk);
if(s_bresp!=0)$fatal(1,"HOSTPROG_AXI_FAIL address=%h resp=%d",a,s_bresp);
@(negedge clk);while(s_bvalid)@(negedge clk);
end endtask
task row(input[11:0]a,input[255:0]d);integer k;begin write32(12'hf20,{12'd0,a,8'd112});for(k=0;k<8;k=k+1)write32(12'hf24,d[k*32+:32]);repeat(30)@(negedge clk);end endtask
wire r_start;wire[15:0]r_len;wire[3:0]r_we;wire[63:0]r_bank;wire[6:0]r_row;wire[255:0]r_data;wire root_fault;
wire pgp_busy,pgp_valid,pgp_done,pgp_fault;wire[15:0]edge_index;wire[2469:0]command;
ot_hbm_su_programme_root_h5 root(.clk(clk_s),.rst_n(rst_n),.cfg_we(pw_we),.cfg_bank(pw_addr[22:7]),.cfg_row(pw_addr[6:0]),.cfg_data(pw_data),.start(start_v),.length(prm[15:0]),.p_fault({3'b0,pgp_fault}),.r_start(r_start),.r_len(r_len),.r_we(r_we),.r_bank(r_bank),.r_row(r_row),.r_data(r_data),.fault(root_fault));
ot_hbm_su_programme_pslice_c5 #(.SB(2470)) producer(.clk(clk_s),.rst_n(rst_n),.cfg_we(r_we[0]),.cfg_bank(r_bank[15:0]),.cfg_row(r_row),.cfg_data(r_data),.start(r_start),.length(r_len),.busy(pgp_busy),.valid(pgp_valid),.done(pgp_done),.fault(pgp_fault),.edge_index(edge_index),.command(command));
reg[2469:0]expected[0:LINES-1];integer checked=0;
always @(posedge clk_s)if(pgp_valid)begin
if(edge_index!==checked || command!==expected[checked])$fatal(1,"HOSTPROG_COMMAND_MISMATCH index=%d edge=%d",checked,edge_index);
checked=checked+1;end
integer i,page,last_page,count;
initial begin
$readmemh("image.mem",image);$readmemh("quarter.mem",expected);
#200;rst_n=1;repeat(30)@(negedge clk);
last_page=-1;count=(CASE==2)?N-1:((CASE==7)?0:N);
for(i=0;i<count;i=i+1)begin
page=image[i][278:267];
if(page!=last_page)begin row(12'he00,256'(page<<8));last_page=page;end
row({1'b0,image[i][266:256]},image[i][255:0]);
end
if(CASE==3)begin row(12'he00,256'd4864);row(12'd1920,256'd0);end // local bank31 absent
if(CASE==4)row({1'b0,image[N-1][266:256]},image[N-1][255:0]); // duplicate
if(CASE==5)begin row(12'he00,256'd5120);row(12'd1,256'd0);end // legal bank8? invalid first row plus absentbank
// exact expected sparse write count and the current programme length operand
row(12'he01,(CASE==7)?256'd0:256'(N));row(12'h800,256'(LINES));
write32(12'hf28,32'h00001000);write32(12'hf2c,32'd1);repeat(40)@(negedge clk);
if(CASE==6)begin row(12'he00,0);row(12'd0,image[0][255:0]);repeat(40)@(negedge clk);end
if(CASE==0)begin
if(collar_fault || !ready || writes!=N)$fatal(1,"HOSTPROG_POSITIVE_FAIL fault=%d ready=%d writes=%d",collar_fault,ready,writes);
write32(12'hf30,1);repeat(2*LINES+100)@(negedge clk);
if(starts!=1 || collar_fault || root_fault || pgp_fault || checked!=LINES)$fatal(1,"HOSTPROG_LAUNCH_FAIL starts=%d fault=%d",starts,collar_fault);
$display("HOSTPROG_SPARSE_PASS exact_actual_words=%0d launch=%0d executed_commands=%0d",writes,starts,checked);
end else begin
if(ready || starts!=0 || (CASE!=2 && CASE!=6 && CASE!=7 && !collar_fault))$fatal(1,"HOSTPROG_NEGATIVE_ESCAPED case=%d ready=%d fault=%d starts=%d",CASE,ready,collar_fault,starts);
$display("HOSTPROG_NEGATIVE_CAUGHT case=%d ready=%d fault=%d writes=%d",CASE,ready,collar_fault,writes);
end
$finish;end
initial begin #2000000;$fatal(1,"HOSTPROG_DEADLOCK");end
endmodule
