`timescale 1ps/1fs
module tb_mif_group #(parameter integer MUT=0);
reg ck=0; always #416.5 ck=~ck;
integer cyc=0,checks=0,nonzero=0;
reg  rst_n=0;
reg [7:0] a_re=0;
reg [7:0] b_re=0;
reg [7:0] c_re=0;
reg [8*24-1:0] a_addr=0;
reg [8*24-1:0] b_addr=0;
reg [8*24-1:0] c_addr=0;
wire [8*32-1:0] g_a_q,d_a_q; reg [8*32-1:0] prev_a_q=0;
wire [8*32-1:0] g_b_q,d_b_q; reg [8*32-1:0] prev_b_q=0;
wire [8*32-1:0] g_c_q,d_c_q; reg [8*32-1:0] prev_c_q=0;
reg [7:0] cr_re=0;
reg [8*24-1:0] cr_addr=0;
wire [8*64-1:0] g_cr_q,d_cr_q; reg [8*64-1:0] prev_cr_q=0;
reg  bs_re=0;
reg [23:0] bs_addr=0;
wire [255:0] g_bs_q,d_bs_q; reg [255:0] prev_bs_q=0;
reg  p_re=0;
reg [8:0] p_idx=0;
wire [456:0] g_p_q,d_p_q; reg [456:0] prev_p_q=0;
reg [7:0] vm_we=0;
reg [8*24-1:0] vm_waddr=0;
reg [8*32-1:0] vm_wdata=0;
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
wire  g_f_va,d_f_va; reg  prev_f_va=0;
wire  g_f_vb,d_f_vb; reg  prev_f_vb=0;
wire  g_f_vc,d_f_vc; reg  prev_f_vc=0;
wire  g_f_crl,d_f_crl; reg  prev_f_crl=0;
wire  g_f_crh,d_f_crh; reg  prev_f_crh=0;
wire  g_f_bt,d_f_bt; reg  prev_f_bt=0;
qfd_dv_s8_vm8q_rp1 #(.MIF(0)) g(
.ck(ck),
.rst_n(rst_n),
.a_re(a_re),
.b_re(b_re),
.c_re(c_re),
.a_addr(a_addr),
.b_addr(b_addr),
.c_addr(c_addr),
.a_q(g_a_q),
.b_q(g_b_q),
.c_q(g_c_q),
.cr_re(cr_re),
.cr_addr(cr_addr),
.cr_q(g_cr_q),
.bs_re(bs_re),
.bs_addr(bs_addr),
.bs_q(g_bs_q),
.p_re(p_re),
.p_idx(p_idx),
.p_q(g_p_q),
.vm_we(vm_we),
.vm_waddr(vm_waddr),
.vm_wdata(vm_wdata),
.w16_we(w16_we),
.w16_addr(w16_addr),
.w16_data(w16_data),
.w1_we(w1_we),
.w1_addr(w1_addr),
.w1_data(w1_data),
.tw_we(tw_we),
.tw_kind(tw_kind),
.tw_addr(tw_addr),
.tw_data(tw_data),
.f_va(g_f_va),
.f_vb(g_f_vb),
.f_vc(g_f_vc),
.f_crl(g_f_crl),
.f_crh(g_f_crh),
.f_bt(g_f_bt));
qfd_dv_s8_vm8q_rp1 #(.MIF(((MUT==1)?0:1))) d(
.ck(ck),
.rst_n(rst_n),
.a_re(a_re),
.b_re(b_re),
.c_re(c_re),
.a_addr(a_addr),
.b_addr(b_addr),
.c_addr(c_addr),
.a_q(d_a_q),
.b_q(d_b_q),
.c_q(d_c_q),
.cr_re(cr_re),
.cr_addr(cr_addr),
.cr_q(d_cr_q),
.bs_re(bs_re),
.bs_addr(bs_addr),
.bs_q(d_bs_q),
.p_re(p_re),
.p_idx(p_idx),
.p_q(d_p_q),
.vm_we(vm_we),
.vm_waddr(vm_waddr),
.vm_wdata(vm_wdata),
.w16_we(w16_we),
.w16_addr(w16_addr),
.w16_data(w16_data),
.w1_we(w1_we),
.w1_addr(w1_addr),
.w1_data(w1_data),
.tw_we(tw_we),
.tw_kind(tw_kind),
.tw_addr(tw_addr),
.tw_data(tw_data),
.f_va(d_f_va),
.f_vb(d_f_vb),
.f_vc(d_f_vc),
.f_crl(d_f_crl),
.f_crh(d_f_crh),
.f_bt(d_f_bt));
always @(negedge ck) begin
cyc=cyc+1;
rst_n=cyc>8;
if(cyc>32) begin
if(d_a_q !== prev_a_q) begin $display("MIF_GROUP FAIL cyc%0d a_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_a_q!=0)nonzero++;
if(d_b_q !== prev_b_q) begin $display("MIF_GROUP FAIL cyc%0d b_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_b_q!=0)nonzero++;
if(d_c_q !== prev_c_q) begin $display("MIF_GROUP FAIL cyc%0d c_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_c_q!=0)nonzero++;
if(d_cr_q !== prev_cr_q) begin $display("MIF_GROUP FAIL cyc%0d cr_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_cr_q!=0)nonzero++;
if(d_bs_q !== prev_bs_q) begin $display("MIF_GROUP FAIL cyc%0d bs_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_bs_q!=0)nonzero++;
if(d_p_q !== prev_p_q) begin $display("MIF_GROUP FAIL cyc%0d p_q",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_p_q!=0)nonzero++;
if(d_f_va !== g_f_va) begin $display("MIF_GROUP FAIL cyc%0d f_va",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_f_vb !== g_f_vb) begin $display("MIF_GROUP FAIL cyc%0d f_vb",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_f_vc !== g_f_vc) begin $display("MIF_GROUP FAIL cyc%0d f_vc",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_f_crl !== g_f_crl) begin $display("MIF_GROUP FAIL cyc%0d f_crl",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_f_crh !== g_f_crh) begin $display("MIF_GROUP FAIL cyc%0d f_crh",cyc); $fatal(1,"age/content mismatch"); end checks++;
if(d_f_bt !== g_f_bt) begin $display("MIF_GROUP FAIL cyc%0d f_bt",cyc); $fatal(1,"age/content mismatch"); end checks++;
end
prev_a_q=g_a_q;
prev_b_q=g_b_q;
prev_c_q=g_c_q;
prev_cr_q=g_cr_q;
prev_bs_q=g_bs_q;
prev_p_q=g_p_q;
prev_f_va=g_f_va;
prev_f_vb=g_f_vb;
prev_f_vc=g_f_vc;
prev_f_crl=g_f_crl;
prev_f_crh=g_f_crh;
prev_f_bt=g_f_bt;
a_re=255;b_re=255;c_re=255;cr_re=255;bs_re=1;p_re=1;
bs_addr=((cyc%64)<<2);p_idx=cyc%64;
vm_we=255;w16_we=(cyc%7==0);w1_we=(cyc%11==0);
w16_addr=((cyc%128)<<4);w1_addr=((cyc%128)<<4);w1_data=cyc*32'h01010101;
tw_we=(cyc%4!=0);tw_kind=cyc%3;tw_addr=(cyc%64)<<2;
for(integer k=0;k<8;k++)begin
a_addr[k*24+:24]=(((cyc+k)%128)<<4)|k;b_addr[k*24+:24]=(((cyc+3+k)%128)<<4)|k;c_addr[k*24+:24]=(((cyc+7+k)%128)<<4)|k;cr_addr[k*24+:24]=(((cyc+k)%64)<<4)|k;
vm_waddr[k*24+:24]=(((cyc+k)%128)<<4)|k;vm_wdata[k*32+:32]=(cyc*32'h9e3779b9)^k;end
for(integer k=0;k<16;k++)begin w16_data[k*32+:32]=cyc^k;end
for(integer k=0;k<32;k++)begin tw_data[k*32+:32]=(cyc*32'h01020304)^k;end
if(cyc==4096)begin if(nonzero==0)$fatal(1,"no dynamic memory output exercised");$display("MIF_GROUP PASS cycles%0d checks%0d nonzero%0d",cyc,checks,nonzero);$finish;end
end
endmodule
