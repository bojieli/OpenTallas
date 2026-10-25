`timescale 1ps/1fs
module tb_mif_fetch; reg ck=0;always #416.5 ck=~ck;integer cyc,checks=0,active=0;
reg  rst_n=0;
reg [9:0] su_cmd=0;
wire [499:0] g_gb,d_gb;
wire [2:0] g_gv,d_gv;
wire [7:0] g_lv1,d_lv1;
wire [8*96-1:0] g_pd1,d_pd1;
reg [7:0] va_re=0;
reg [8*24-1:0] va_addr=0;
reg [8*32-1:0] vm_wdata=0;
wire [8*32-1:0] g_va_q,d_va_q;
wire [8*64-1:0] g_cr_q,d_cr_q;
reg  rd_v=0;
reg  red_busy=0;
reg  red_fault=0;
reg  w16_we=0;
reg [23:0] w16_addr=0;
reg [511:0] w16_data=0;
reg  w1_we=0;
reg [23:0] w1_addr=0;
reg [31:0] w1_data=0;
reg  tw_we=0;
reg [1:0] tw_kind=0;
reg [23:0] tw_addr=0;
reg [1023:0] tw_data=0;
wire  g_su_nr,d_su_nr;
wire  g_su_idle,d_su_idle;
wire  g_su_fault,d_su_fault;
wire [15:0] g_su_prog,d_su_prog;
wire [15:0] g_su_rows,d_su_rows;
wire  g_vm_fault,d_vm_fault;
qfd_dv_s8_suvm_rp1 #(.MIF(0)) g(.ck(ck),.rst_n(rst_n),.su_cmd(su_cmd),.gb(g_gb),.gv(g_gv),.lv1(g_lv1),.pd1(g_pd1),.va_re(va_re),.va_addr(va_addr),.vm_wdata(vm_wdata),.va_q(g_va_q),.cr_q(g_cr_q),.rd_v(rd_v),.red_busy(red_busy),.red_fault(red_fault),.w16_we(w16_we),.w16_addr(w16_addr),.w16_data(w16_data),.w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),.su_nr(g_su_nr),.su_idle(g_su_idle),.su_fault(g_su_fault),.su_prog(g_su_prog),.su_rows(g_su_rows),.vm_fault(g_vm_fault));
qfd_dv_s8_suvm_rp1 #(.MIF(1)) d(.ck(ck),.rst_n(rst_n),.su_cmd(su_cmd),.gb(d_gb),.gv(d_gv),.lv1(d_lv1),.pd1(d_pd1),.va_re(va_re),.va_addr(va_addr),.vm_wdata(vm_wdata),.va_q(d_va_q),.cr_q(d_cr_q),.rd_v(rd_v),.red_busy(red_busy),.red_fault(red_fault),.w16_we(w16_we),.w16_addr(w16_addr),.w16_data(w16_data),.w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.tw_we(tw_we),.tw_kind(tw_kind),.tw_addr(tw_addr),.tw_data(tw_data),.su_nr(d_su_nr),.su_idle(d_su_idle),.su_fault(d_su_fault),.su_prog(d_su_prog),.su_rows(d_su_rows),.vm_fault(d_vm_fault));
wire [1313:0] ga={g_gb,g_gv,g_lv1,g_pd1,g_su_nr,g_su_idle,g_su_fault,g_su_prog,g_su_rows};
wire [1313:0] da={d_gb,d_gv,d_lv1,d_pd1,d_su_nr,d_su_idle,d_su_fault,d_su_prog,d_su_rows};
reg [1313:0] prev=0;always @(posedge ck)prev<=ga;
initial begin
l_retire=255;l_last=255;rd_v=1;tw_kind=3;
for(cyc=0;cyc<1400;cyc=cyc+1)begin
@(negedge ck);rst_n=(cyc>15);tw_we=(cyc>=32&&cyc<48);tw_addr=(cyc-32)*4;
tw_data=0;tw_data[18:1]=1;tw_data[36:19]=8;tw_data[512+18:513]=2;tw_data[512+36:512+19]=16;
su_cmd=0;if(cyc>=96&&cyc%128==96)su_cmd={1'b1,9'(2*((cyc/128)%8))};
@(posedge ck);#1;
if(cyc>64)begin checks=checks+1;if(da!==prev)begin $display("MIF_FETCH FAIL cyc=%0d diff=%h",cyc,da^prev);$fatal;end if(d_lv1!=0)active=active+1;end
end
if(checks<1000||active<10)$fatal(1,"insufficient active fetches %0d",active);
$display("MIF_FETCH PASS checks=%0d live=%0d",checks,active);$finish;end endmodule
