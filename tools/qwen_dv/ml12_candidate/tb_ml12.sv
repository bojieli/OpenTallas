`timescale 1ns/1ps
module tb_ml12;
reg clk=0; always #5 clk=~clk;
reg  rst_n=0;
reg  emit0=0;
reg  live=0;
reg [17:0] i=0;
reg [18:0] fin_th=0;
reg  i_last_r=0;
reg [23:0] cura0=0;
reg [23:0] curb0=0;
reg [23:0] curc0=0;
reg [23:0] curd0=0;
reg [23:0] rrow=0;
reg [23:0] asi=0;
reg [23:0] bsi=0;
reg [23:0] csi=0;
reg [23:0] dsi=0;
reg  asrc=0;
reg  bsrc=0;
reg  csrc=0;
reg  mc=0;
reg  md=0;
reg  redsq=0;
reg [1:0] ma=0;
reg [1:0] mb=0;
reg [1:0] dst=0;
reg [1:0] red=0;
reg [2:0] ad=0;
reg [31:0] imm1=0;
reg [31:0] imm2=0;
reg [2:0] cls=0;
reg  accept=0;
reg [2:0] i_sfu=0;
wire ref_va_re;
wire [23:0] ref_va_addr;
reg [31:0] va_q=0;
wire ref_vb_re;
wire [23:0] ref_vb_addr;
reg [31:0] vb_q=0;
wire ref_vc_re;
wire [23:0] ref_vc_addr;
reg [31:0] vc_q=0;
wire ref_wrom_re;
wire [23:0] ref_wrom_addr;
reg [255:0] wrom_q=0;
wire ref_crom_re;
wire [23:0] ref_crom_addr;
reg [63:0] crom_q=0;
wire ref_vm_we;
wire [23:0] ref_vm_waddr;
wire [31:0] ref_vm_wdata;
wire ref_kv_we;
wire [23:0] ref_kv_waddr;
wire [31:0] ref_kv_wdata;
wire ref_l_ov;
wire [31:0] ref_l_out;
wire [1:0] ref_l_red;
wire ref_l_redsq;
wire [23:0] ref_l_raddr;
wire ref_l_last;
wire ref_retire;
wire ref_l_fault;
wire ref_sx_exp_v;
wire [31:0] ref_sx_exp_x;
reg [31:0] sy_exp_y=0;
reg  sy_exp_vo=0;
reg  sy_exp_f=0;
wire ref_sx_rcp_v;
wire [31:0] ref_sx_rcp_x;
reg [31:0] sy_rcp_y=0;
reg  sy_rcp_f=0;
wire ref_sx_rsq_v;
wire [31:0] ref_sx_rsq_x;
reg [31:0] sy_rsq_y=0;
reg  sy_rsq_f=0;
reg [31:0] vd[0:2], bd[0:2], cd[0:2];
reg [63:0] crd[0:3]; reg [255:0] wrd[0:2];
reg[31:0] va1,vb1,vc1;

qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3)) u_ref (.clk(clk),
.rst_n(rst_n),
.emit0(emit0),
.live(live),
.i(i),
.fin_th(fin_th),
.i_last_r(i_last_r),
.cura0(cura0),
.curb0(curb0),
.curc0(curc0),
.curd0(curd0),
.rrow(rrow),
.asi(asi),
.bsi(bsi),
.csi(csi),
.dsi(dsi),
.asrc(asrc),
.bsrc(bsrc),
.csrc(csrc),
.mc(mc),
.md(md),
.redsq(redsq),
.ma(ma),
.mb(mb),
.dst(dst),
.red(red),
.ad(ad),
.imm1(imm1),
.imm2(imm2),
.cls(cls),
.accept(accept),
.i_sfu(i_sfu),
.va_re(ref_va_re),
.va_addr(ref_va_addr),
.va_q(va_q),
.vb_re(ref_vb_re),
.vb_addr(ref_vb_addr),
.vb_q(vb_q),
.vc_re(ref_vc_re),
.vc_addr(ref_vc_addr),
.vc_q(vc_q),
.wrom_re(ref_wrom_re),
.wrom_addr(ref_wrom_addr),
.wrom_q(wrom_q),
.crom_re(ref_crom_re),
.crom_addr(ref_crom_addr),
.crom_q(crom_q),
.vm_we(ref_vm_we),
.vm_waddr(ref_vm_waddr),
.vm_wdata(ref_vm_wdata),
.kv_we(ref_kv_we),
.kv_waddr(ref_kv_waddr),
.kv_wdata(ref_kv_wdata),
.l_ov(ref_l_ov),
.l_out(ref_l_out),
.l_red(ref_l_red),
.l_redsq(ref_l_redsq),
.l_raddr(ref_l_raddr),
.l_last(ref_l_last),
.retire(ref_retire),
.l_fault(ref_l_fault),
.sx_exp_v(ref_sx_exp_v),
.sx_exp_x(ref_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(ref_sx_rcp_v),
.sx_rcp_x(ref_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(ref_sx_rsq_v),
.sx_rsq_x(ref_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

function automatic [31:0] fp(input [23:0] a,input integer p); fp=32'h3f000000 | ((a*32'd131+p*32'd197)&32'h007fffff); endfunction
function automatic [255:0] fw(input [23:0] a); integer j;begin for(j=0;j<16;j=j+1)fw[j*16+:16]=16'h3f00|((a+j)&16'h007f);end endfunction
wire p4_va_re;
wire [23:0] p4_va_addr;
wire p4_vb_re;
wire [23:0] p4_vb_addr;
wire p4_vc_re;
wire [23:0] p4_vc_addr;
wire p4_wrom_re;
wire [23:0] p4_wrom_addr;
wire p4_crom_re;
wire [23:0] p4_crom_addr;
wire p4_vm_we;
wire [23:0] p4_vm_waddr;
wire [31:0] p4_vm_wdata;
wire p4_kv_we;
wire [23:0] p4_kv_waddr;
wire [31:0] p4_kv_wdata;
wire p4_l_ov;
wire [31:0] p4_l_out;
wire [1:0] p4_l_red;
wire p4_l_redsq;
wire [23:0] p4_l_raddr;
wire p4_l_last;
wire p4_retire;
wire p4_l_fault;
wire p4_sx_exp_v;
wire [31:0] p4_sx_exp_x;
wire p4_sx_rcp_v;
wire [31:0] p4_sx_rcp_x;
wire p4_sx_rsq_v;
wire [31:0] p4_sx_rsq_x;
wire [31:0] p4_va_q;
wire [31:0] p4_vb_q;
wire [31:0] p4_vc_q;
wire [255:0] p4_wrom_q;
wire [63:0] p4_crom_q;
qfd_dv_lane_h_ml12_candidate #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(4)) u_p4 (.clk(clk),
.rst_n(rst_n),
.emit0(emit0),
.live(live),
.i(i),
.fin_th(fin_th),
.i_last_r(i_last_r),
.cura0(cura0),
.curb0(curb0),
.curc0(curc0),
.curd0(curd0),
.rrow(rrow),
.asi(asi),
.bsi(bsi),
.csi(csi),
.dsi(dsi),
.asrc(asrc),
.bsrc(bsrc),
.csrc(csrc),
.mc(mc),
.md(md),
.redsq(redsq),
.ma(ma),
.mb(mb),
.dst(dst),
.red(red),
.ad(ad),
.imm1(imm1),
.imm2(imm2),
.cls(cls),
.accept(accept),
.i_sfu(i_sfu),
.va_re(p4_va_re),
.va_addr(p4_va_addr),
.va_q(p4_va_q),
.vb_re(p4_vb_re),
.vb_addr(p4_vb_addr),
.vb_q(p4_vb_q),
.vc_re(p4_vc_re),
.vc_addr(p4_vc_addr),
.vc_q(p4_vc_q),
.wrom_re(p4_wrom_re),
.wrom_addr(p4_wrom_addr),
.wrom_q(p4_wrom_q),
.crom_re(p4_crom_re),
.crom_addr(p4_crom_addr),
.crom_q(p4_crom_q),
.vm_we(p4_vm_we),
.vm_waddr(p4_vm_waddr),
.vm_wdata(p4_vm_wdata),
.kv_we(p4_kv_we),
.kv_waddr(p4_kv_waddr),
.kv_wdata(p4_kv_wdata),
.l_ov(p4_l_ov),
.l_out(p4_l_out),
.l_red(p4_l_red),
.l_redsq(p4_l_redsq),
.l_raddr(p4_l_raddr),
.l_last(p4_l_last),
.retire(p4_retire),
.l_fault(p4_l_fault),
.sx_exp_v(p4_sx_exp_v),
.sx_exp_x(p4_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(p4_sx_rcp_v),
.sx_rcp_x(p4_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(p4_sx_rsq_v),
.sx_rsq_x(p4_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

reg [24:0] p4_va_rq[0:3]; integer p4_va_ri;
always @(posedge clk) begin p4_va_rq[0]<={ p4_va_re,p4_va_addr }; for(p4_va_ri=1;p4_va_ri<4;p4_va_ri=p4_va_ri+1)p4_va_rq[p4_va_ri]<=p4_va_rq[p4_va_ri-1];end
wire ext_p4_va_re=p4_va_rq[3][24]; wire [23:0] ext_p4_va_addr=p4_va_rq[3][23:0];
reg [31:0] p4_va_mem[0:0]; integer p4_va_mi;
always @(posedge clk) begin if(ext_p4_va_re)p4_va_mem[0]<=fp(ext_p4_va_addr,0); for(p4_va_mi=1;p4_va_mi<1;p4_va_mi=p4_va_mi+1)p4_va_mem[p4_va_mi]<=p4_va_mem[p4_va_mi-1];end
assign p4_va_q=p4_va_mem[0];
reg [24:0] p4_vb_rq[0:3]; integer p4_vb_ri;
always @(posedge clk) begin p4_vb_rq[0]<={ p4_vb_re,p4_vb_addr }; for(p4_vb_ri=1;p4_vb_ri<4;p4_vb_ri=p4_vb_ri+1)p4_vb_rq[p4_vb_ri]<=p4_vb_rq[p4_vb_ri-1];end
wire ext_p4_vb_re=p4_vb_rq[3][24]; wire [23:0] ext_p4_vb_addr=p4_vb_rq[3][23:0];
reg [31:0] p4_vb_mem[0:0]; integer p4_vb_mi;
always @(posedge clk) begin if(ext_p4_vb_re)p4_vb_mem[0]<=fp(ext_p4_vb_addr,1); for(p4_vb_mi=1;p4_vb_mi<1;p4_vb_mi=p4_vb_mi+1)p4_vb_mem[p4_vb_mi]<=p4_vb_mem[p4_vb_mi-1];end
assign p4_vb_q=p4_vb_mem[0];
reg [24:0] p4_vc_rq[0:3]; integer p4_vc_ri;
always @(posedge clk) begin p4_vc_rq[0]<={ p4_vc_re,p4_vc_addr }; for(p4_vc_ri=1;p4_vc_ri<4;p4_vc_ri=p4_vc_ri+1)p4_vc_rq[p4_vc_ri]<=p4_vc_rq[p4_vc_ri-1];end
wire ext_p4_vc_re=p4_vc_rq[3][24]; wire [23:0] ext_p4_vc_addr=p4_vc_rq[3][23:0];
reg [31:0] p4_vc_mem[0:0]; integer p4_vc_mi;
always @(posedge clk) begin if(ext_p4_vc_re)p4_vc_mem[0]<=fp(ext_p4_vc_addr,2); for(p4_vc_mi=1;p4_vc_mi<1;p4_vc_mi=p4_vc_mi+1)p4_vc_mem[p4_vc_mi]<=p4_vc_mem[p4_vc_mi-1];end
assign p4_vc_q=p4_vc_mem[0];
reg [24:0] p4_wrom_rq[0:3]; integer p4_wrom_ri;
always @(posedge clk) begin p4_wrom_rq[0]<={ p4_wrom_re,p4_wrom_addr }; for(p4_wrom_ri=1;p4_wrom_ri<4;p4_wrom_ri=p4_wrom_ri+1)p4_wrom_rq[p4_wrom_ri]<=p4_wrom_rq[p4_wrom_ri-1];end
wire ext_p4_wrom_re=p4_wrom_rq[3][24]; wire [23:0] ext_p4_wrom_addr=p4_wrom_rq[3][23:0];
reg [255:0] p4_wrom_mem[0:2]; integer p4_wrom_mi;
always @(posedge clk) begin if(ext_p4_wrom_re)p4_wrom_mem[0]<=fw(ext_p4_wrom_addr); for(p4_wrom_mi=1;p4_wrom_mi<3;p4_wrom_mi=p4_wrom_mi+1)p4_wrom_mem[p4_wrom_mi]<=p4_wrom_mem[p4_wrom_mi-1];end
assign p4_wrom_q=p4_wrom_mem[2];
reg [24:0] p4_crom_rq[0:3]; integer p4_crom_ri;
always @(posedge clk) begin p4_crom_rq[0]<={ p4_crom_re,p4_crom_addr }; for(p4_crom_ri=1;p4_crom_ri<4;p4_crom_ri=p4_crom_ri+1)p4_crom_rq[p4_crom_ri]<=p4_crom_rq[p4_crom_ri-1];end
wire ext_p4_crom_re=p4_crom_rq[3][24]; wire [23:0] ext_p4_crom_addr=p4_crom_rq[3][23:0];
reg [63:0] p4_crom_mem[0:3]; integer p4_crom_mi;
always @(posedge clk) begin if(ext_p4_crom_re)p4_crom_mem[0]<={fp(ext_p4_crom_addr,5),fp(ext_p4_crom_addr,6)}; for(p4_crom_mi=1;p4_crom_mi<4;p4_crom_mi=p4_crom_mi+1)p4_crom_mem[p4_crom_mi]<=p4_crom_mem[p4_crom_mi-1];end
assign p4_crom_q=p4_crom_mem[3];
wire m3_va_re;
wire [23:0] m3_va_addr;
wire m3_vb_re;
wire [23:0] m3_vb_addr;
wire m3_vc_re;
wire [23:0] m3_vc_addr;
wire m3_wrom_re;
wire [23:0] m3_wrom_addr;
wire m3_crom_re;
wire [23:0] m3_crom_addr;
wire m3_vm_we;
wire [23:0] m3_vm_waddr;
wire [31:0] m3_vm_wdata;
wire m3_kv_we;
wire [23:0] m3_kv_waddr;
wire [31:0] m3_kv_wdata;
wire m3_l_ov;
wire [31:0] m3_l_out;
wire [1:0] m3_l_red;
wire m3_l_redsq;
wire [23:0] m3_l_raddr;
wire m3_l_last;
wire m3_retire;
wire m3_l_fault;
wire m3_sx_exp_v;
wire [31:0] m3_sx_exp_x;
wire m3_sx_rcp_v;
wire [31:0] m3_sx_rcp_x;
wire m3_sx_rsq_v;
wire [31:0] m3_sx_rsq_x;
wire [31:0] m3_va_q;
wire [31:0] m3_vb_q;
wire [31:0] m3_vc_q;
wire [255:0] m3_wrom_q;
wire [63:0] m3_crom_q;
qfd_dv_lane_h_ml12_candidate #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(3)) u_m3 (.clk(clk),
.rst_n(rst_n),
.emit0(emit0),
.live(live),
.i(i),
.fin_th(fin_th),
.i_last_r(i_last_r),
.cura0(cura0),
.curb0(curb0),
.curc0(curc0),
.curd0(curd0),
.rrow(rrow),
.asi(asi),
.bsi(bsi),
.csi(csi),
.dsi(dsi),
.asrc(asrc),
.bsrc(bsrc),
.csrc(csrc),
.mc(mc),
.md(md),
.redsq(redsq),
.ma(ma),
.mb(mb),
.dst(dst),
.red(red),
.ad(ad),
.imm1(imm1),
.imm2(imm2),
.cls(cls),
.accept(accept),
.i_sfu(i_sfu),
.va_re(m3_va_re),
.va_addr(m3_va_addr),
.va_q(m3_va_q),
.vb_re(m3_vb_re),
.vb_addr(m3_vb_addr),
.vb_q(m3_vb_q),
.vc_re(m3_vc_re),
.vc_addr(m3_vc_addr),
.vc_q(m3_vc_q),
.wrom_re(m3_wrom_re),
.wrom_addr(m3_wrom_addr),
.wrom_q(m3_wrom_q),
.crom_re(m3_crom_re),
.crom_addr(m3_crom_addr),
.crom_q(m3_crom_q),
.vm_we(m3_vm_we),
.vm_waddr(m3_vm_waddr),
.vm_wdata(m3_vm_wdata),
.kv_we(m3_kv_we),
.kv_waddr(m3_kv_waddr),
.kv_wdata(m3_kv_wdata),
.l_ov(m3_l_ov),
.l_out(m3_l_out),
.l_red(m3_l_red),
.l_redsq(m3_l_redsq),
.l_raddr(m3_l_raddr),
.l_last(m3_l_last),
.retire(m3_retire),
.l_fault(m3_l_fault),
.sx_exp_v(m3_sx_exp_v),
.sx_exp_x(m3_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(m3_sx_rcp_v),
.sx_rcp_x(m3_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(m3_sx_rsq_v),
.sx_rsq_x(m3_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

reg [24:0] m3_va_rq[0:3]; integer m3_va_ri;
always @(posedge clk) begin m3_va_rq[0]<={ m3_va_re,m3_va_addr }; for(m3_va_ri=1;m3_va_ri<4;m3_va_ri=m3_va_ri+1)m3_va_rq[m3_va_ri]<=m3_va_rq[m3_va_ri-1];end
wire ext_m3_va_re=m3_va_rq[3][24]; wire [23:0] ext_m3_va_addr=m3_va_rq[3][23:0];
reg [31:0] m3_va_mem[0:0]; integer m3_va_mi;
always @(posedge clk) begin if(ext_m3_va_re)m3_va_mem[0]<=fp(ext_m3_va_addr,0); for(m3_va_mi=1;m3_va_mi<1;m3_va_mi=m3_va_mi+1)m3_va_mem[m3_va_mi]<=m3_va_mem[m3_va_mi-1];end
assign m3_va_q=m3_va_mem[0];
reg [24:0] m3_vb_rq[0:3]; integer m3_vb_ri;
always @(posedge clk) begin m3_vb_rq[0]<={ m3_vb_re,m3_vb_addr }; for(m3_vb_ri=1;m3_vb_ri<4;m3_vb_ri=m3_vb_ri+1)m3_vb_rq[m3_vb_ri]<=m3_vb_rq[m3_vb_ri-1];end
wire ext_m3_vb_re=m3_vb_rq[3][24]; wire [23:0] ext_m3_vb_addr=m3_vb_rq[3][23:0];
reg [31:0] m3_vb_mem[0:0]; integer m3_vb_mi;
always @(posedge clk) begin if(ext_m3_vb_re)m3_vb_mem[0]<=fp(ext_m3_vb_addr,1); for(m3_vb_mi=1;m3_vb_mi<1;m3_vb_mi=m3_vb_mi+1)m3_vb_mem[m3_vb_mi]<=m3_vb_mem[m3_vb_mi-1];end
assign m3_vb_q=m3_vb_mem[0];
reg [24:0] m3_vc_rq[0:3]; integer m3_vc_ri;
always @(posedge clk) begin m3_vc_rq[0]<={ m3_vc_re,m3_vc_addr }; for(m3_vc_ri=1;m3_vc_ri<4;m3_vc_ri=m3_vc_ri+1)m3_vc_rq[m3_vc_ri]<=m3_vc_rq[m3_vc_ri-1];end
wire ext_m3_vc_re=m3_vc_rq[3][24]; wire [23:0] ext_m3_vc_addr=m3_vc_rq[3][23:0];
reg [31:0] m3_vc_mem[0:0]; integer m3_vc_mi;
always @(posedge clk) begin if(ext_m3_vc_re)m3_vc_mem[0]<=fp(ext_m3_vc_addr,2); for(m3_vc_mi=1;m3_vc_mi<1;m3_vc_mi=m3_vc_mi+1)m3_vc_mem[m3_vc_mi]<=m3_vc_mem[m3_vc_mi-1];end
assign m3_vc_q=m3_vc_mem[0];
reg [24:0] m3_wrom_rq[0:3]; integer m3_wrom_ri;
always @(posedge clk) begin m3_wrom_rq[0]<={ m3_wrom_re,m3_wrom_addr }; for(m3_wrom_ri=1;m3_wrom_ri<4;m3_wrom_ri=m3_wrom_ri+1)m3_wrom_rq[m3_wrom_ri]<=m3_wrom_rq[m3_wrom_ri-1];end
wire ext_m3_wrom_re=m3_wrom_rq[3][24]; wire [23:0] ext_m3_wrom_addr=m3_wrom_rq[3][23:0];
reg [255:0] m3_wrom_mem[0:2]; integer m3_wrom_mi;
always @(posedge clk) begin if(ext_m3_wrom_re)m3_wrom_mem[0]<=fw(ext_m3_wrom_addr); for(m3_wrom_mi=1;m3_wrom_mi<3;m3_wrom_mi=m3_wrom_mi+1)m3_wrom_mem[m3_wrom_mi]<=m3_wrom_mem[m3_wrom_mi-1];end
assign m3_wrom_q=m3_wrom_mem[2];
reg [24:0] m3_crom_rq[0:3]; integer m3_crom_ri;
always @(posedge clk) begin m3_crom_rq[0]<={ m3_crom_re,m3_crom_addr }; for(m3_crom_ri=1;m3_crom_ri<4;m3_crom_ri=m3_crom_ri+1)m3_crom_rq[m3_crom_ri]<=m3_crom_rq[m3_crom_ri-1];end
wire ext_m3_crom_re=m3_crom_rq[3][24]; wire [23:0] ext_m3_crom_addr=m3_crom_rq[3][23:0];
reg [63:0] m3_crom_mem[0:3]; integer m3_crom_mi;
always @(posedge clk) begin if(ext_m3_crom_re)m3_crom_mem[0]<={fp(ext_m3_crom_addr,5),fp(ext_m3_crom_addr,6)}; for(m3_crom_mi=1;m3_crom_mi<4;m3_crom_mi=m3_crom_mi+1)m3_crom_mem[m3_crom_mi]<=m3_crom_mem[m3_crom_mi-1];end
assign m3_crom_q=m3_crom_mem[3];
wire r3_va_re;
wire [23:0] r3_va_addr;
wire r3_vb_re;
wire [23:0] r3_vb_addr;
wire r3_vc_re;
wire [23:0] r3_vc_addr;
wire r3_wrom_re;
wire [23:0] r3_wrom_addr;
wire r3_crom_re;
wire [23:0] r3_crom_addr;
wire r3_vm_we;
wire [23:0] r3_vm_waddr;
wire [31:0] r3_vm_wdata;
wire r3_kv_we;
wire [23:0] r3_kv_waddr;
wire [31:0] r3_kv_wdata;
wire r3_l_ov;
wire [31:0] r3_l_out;
wire [1:0] r3_l_red;
wire r3_l_redsq;
wire [23:0] r3_l_raddr;
wire r3_l_last;
wire r3_retire;
wire r3_l_fault;
wire r3_sx_exp_v;
wire [31:0] r3_sx_exp_x;
wire r3_sx_rcp_v;
wire [31:0] r3_sx_rcp_x;
wire r3_sx_rsq_v;
wire [31:0] r3_sx_rsq_x;
wire [31:0] r3_va_q;
wire [31:0] r3_vb_q;
wire [31:0] r3_vc_q;
wire [255:0] r3_wrom_q;
wire [63:0] r3_crom_q;
qfd_dv_lane_h_ml12_candidate #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(4)) u_r3 (.clk(clk),
.rst_n(rst_n),
.emit0(emit0),
.live(live),
.i(i),
.fin_th(fin_th),
.i_last_r(i_last_r),
.cura0(cura0),
.curb0(curb0),
.curc0(curc0),
.curd0(curd0),
.rrow(rrow),
.asi(asi),
.bsi(bsi),
.csi(csi),
.dsi(dsi),
.asrc(asrc),
.bsrc(bsrc),
.csrc(csrc),
.mc(mc),
.md(md),
.redsq(redsq),
.ma(ma),
.mb(mb),
.dst(dst),
.red(red),
.ad(ad),
.imm1(imm1),
.imm2(imm2),
.cls(cls),
.accept(accept),
.i_sfu(i_sfu),
.va_re(r3_va_re),
.va_addr(r3_va_addr),
.va_q(r3_va_q),
.vb_re(r3_vb_re),
.vb_addr(r3_vb_addr),
.vb_q(r3_vb_q),
.vc_re(r3_vc_re),
.vc_addr(r3_vc_addr),
.vc_q(r3_vc_q),
.wrom_re(r3_wrom_re),
.wrom_addr(r3_wrom_addr),
.wrom_q(r3_wrom_q),
.crom_re(r3_crom_re),
.crom_addr(r3_crom_addr),
.crom_q(r3_crom_q),
.vm_we(r3_vm_we),
.vm_waddr(r3_vm_waddr),
.vm_wdata(r3_vm_wdata),
.kv_we(r3_kv_we),
.kv_waddr(r3_kv_waddr),
.kv_wdata(r3_kv_wdata),
.l_ov(r3_l_ov),
.l_out(r3_l_out),
.l_red(r3_l_red),
.l_redsq(r3_l_redsq),
.l_raddr(r3_l_raddr),
.l_last(r3_l_last),
.retire(r3_retire),
.l_fault(r3_l_fault),
.sx_exp_v(r3_sx_exp_v),
.sx_exp_x(r3_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(r3_sx_rcp_v),
.sx_rcp_x(r3_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(r3_sx_rsq_v),
.sx_rsq_x(r3_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

reg [24:0] r3_va_rq[0:2]; integer r3_va_ri;
always @(posedge clk) begin r3_va_rq[0]<={ r3_va_re,r3_va_addr }; for(r3_va_ri=1;r3_va_ri<3;r3_va_ri=r3_va_ri+1)r3_va_rq[r3_va_ri]<=r3_va_rq[r3_va_ri-1];end
wire ext_r3_va_re=r3_va_rq[2][24]; wire [23:0] ext_r3_va_addr=r3_va_rq[2][23:0];
reg [31:0] r3_va_mem[0:0]; integer r3_va_mi;
always @(posedge clk) begin if(ext_r3_va_re)r3_va_mem[0]<=fp(ext_r3_va_addr,0); for(r3_va_mi=1;r3_va_mi<1;r3_va_mi=r3_va_mi+1)r3_va_mem[r3_va_mi]<=r3_va_mem[r3_va_mi-1];end
assign r3_va_q=r3_va_mem[0];
reg [24:0] r3_vb_rq[0:2]; integer r3_vb_ri;
always @(posedge clk) begin r3_vb_rq[0]<={ r3_vb_re,r3_vb_addr }; for(r3_vb_ri=1;r3_vb_ri<3;r3_vb_ri=r3_vb_ri+1)r3_vb_rq[r3_vb_ri]<=r3_vb_rq[r3_vb_ri-1];end
wire ext_r3_vb_re=r3_vb_rq[2][24]; wire [23:0] ext_r3_vb_addr=r3_vb_rq[2][23:0];
reg [31:0] r3_vb_mem[0:0]; integer r3_vb_mi;
always @(posedge clk) begin if(ext_r3_vb_re)r3_vb_mem[0]<=fp(ext_r3_vb_addr,1); for(r3_vb_mi=1;r3_vb_mi<1;r3_vb_mi=r3_vb_mi+1)r3_vb_mem[r3_vb_mi]<=r3_vb_mem[r3_vb_mi-1];end
assign r3_vb_q=r3_vb_mem[0];
reg [24:0] r3_vc_rq[0:2]; integer r3_vc_ri;
always @(posedge clk) begin r3_vc_rq[0]<={ r3_vc_re,r3_vc_addr }; for(r3_vc_ri=1;r3_vc_ri<3;r3_vc_ri=r3_vc_ri+1)r3_vc_rq[r3_vc_ri]<=r3_vc_rq[r3_vc_ri-1];end
wire ext_r3_vc_re=r3_vc_rq[2][24]; wire [23:0] ext_r3_vc_addr=r3_vc_rq[2][23:0];
reg [31:0] r3_vc_mem[0:0]; integer r3_vc_mi;
always @(posedge clk) begin if(ext_r3_vc_re)r3_vc_mem[0]<=fp(ext_r3_vc_addr,2); for(r3_vc_mi=1;r3_vc_mi<1;r3_vc_mi=r3_vc_mi+1)r3_vc_mem[r3_vc_mi]<=r3_vc_mem[r3_vc_mi-1];end
assign r3_vc_q=r3_vc_mem[0];
reg [24:0] r3_wrom_rq[0:2]; integer r3_wrom_ri;
always @(posedge clk) begin r3_wrom_rq[0]<={ r3_wrom_re,r3_wrom_addr }; for(r3_wrom_ri=1;r3_wrom_ri<3;r3_wrom_ri=r3_wrom_ri+1)r3_wrom_rq[r3_wrom_ri]<=r3_wrom_rq[r3_wrom_ri-1];end
wire ext_r3_wrom_re=r3_wrom_rq[2][24]; wire [23:0] ext_r3_wrom_addr=r3_wrom_rq[2][23:0];
reg [255:0] r3_wrom_mem[0:2]; integer r3_wrom_mi;
always @(posedge clk) begin if(ext_r3_wrom_re)r3_wrom_mem[0]<=fw(ext_r3_wrom_addr); for(r3_wrom_mi=1;r3_wrom_mi<3;r3_wrom_mi=r3_wrom_mi+1)r3_wrom_mem[r3_wrom_mi]<=r3_wrom_mem[r3_wrom_mi-1];end
assign r3_wrom_q=r3_wrom_mem[2];
reg [24:0] r3_crom_rq[0:2]; integer r3_crom_ri;
always @(posedge clk) begin r3_crom_rq[0]<={ r3_crom_re,r3_crom_addr }; for(r3_crom_ri=1;r3_crom_ri<3;r3_crom_ri=r3_crom_ri+1)r3_crom_rq[r3_crom_ri]<=r3_crom_rq[r3_crom_ri-1];end
wire ext_r3_crom_re=r3_crom_rq[2][24]; wire [23:0] ext_r3_crom_addr=r3_crom_rq[2][23:0];
reg [63:0] r3_crom_mem[0:3]; integer r3_crom_mi;
always @(posedge clk) begin if(ext_r3_crom_re)r3_crom_mem[0]<={fp(ext_r3_crom_addr,5),fp(ext_r3_crom_addr,6)}; for(r3_crom_mi=1;r3_crom_mi<4;r3_crom_mi=r3_crom_mi+1)r3_crom_mem[r3_crom_mi]<=r3_crom_mem[r3_crom_mi-1];end
assign r3_crom_q=r3_crom_mem[3];
wire a7_va_re;
wire [23:0] a7_va_addr;
wire a7_vb_re;
wire [23:0] a7_vb_addr;
wire a7_vc_re;
wire [23:0] a7_vc_addr;
wire a7_wrom_re;
wire [23:0] a7_wrom_addr;
wire a7_crom_re;
wire [23:0] a7_crom_addr;
wire a7_vm_we;
wire [23:0] a7_vm_waddr;
wire [31:0] a7_vm_wdata;
wire a7_kv_we;
wire [23:0] a7_kv_waddr;
wire [31:0] a7_kv_wdata;
wire a7_l_ov;
wire [31:0] a7_l_out;
wire [1:0] a7_l_red;
wire a7_l_redsq;
wire [23:0] a7_l_raddr;
wire a7_l_last;
wire a7_retire;
wire a7_l_fault;
wire a7_sx_exp_v;
wire [31:0] a7_sx_exp_x;
wire a7_sx_rcp_v;
wire [31:0] a7_sx_rcp_x;
wire a7_sx_rsq_v;
wire [31:0] a7_sx_rsq_x;
wire [31:0] a7_va_q;
wire [31:0] a7_vb_q;
wire [31:0] a7_vc_q;
wire [255:0] a7_wrom_q;
wire [63:0] a7_crom_q;
qfd_dv_lane_h_ma7_probe #(.MEMORY_ALIGNMENT(7),.MEMORY_READ_EXTRA(0)) u_a7 (.clk(clk),
.rst_n(rst_n),
.emit0(emit0),
.live(live),
.i(i),
.fin_th(fin_th),
.i_last_r(i_last_r),
.cura0(cura0),
.curb0(curb0),
.curc0(curc0),
.curd0(curd0),
.rrow(rrow),
.asi(asi),
.bsi(bsi),
.csi(csi),
.dsi(dsi),
.asrc(asrc),
.bsrc(bsrc),
.csrc(csrc),
.mc(mc),
.md(md),
.redsq(redsq),
.ma(ma),
.mb(mb),
.dst(dst),
.red(red),
.ad(ad),
.imm1(imm1),
.imm2(imm2),
.cls(cls),
.accept(accept),
.i_sfu(i_sfu),
.va_re(a7_va_re),
.va_addr(a7_va_addr),
.va_q(a7_va_q),
.vb_re(a7_vb_re),
.vb_addr(a7_vb_addr),
.vb_q(a7_vb_q),
.vc_re(a7_vc_re),
.vc_addr(a7_vc_addr),
.vc_q(a7_vc_q),
.wrom_re(a7_wrom_re),
.wrom_addr(a7_wrom_addr),
.wrom_q(a7_wrom_q),
.crom_re(a7_crom_re),
.crom_addr(a7_crom_addr),
.crom_q(a7_crom_q),
.vm_we(a7_vm_we),
.vm_waddr(a7_vm_waddr),
.vm_wdata(a7_vm_wdata),
.kv_we(a7_kv_we),
.kv_waddr(a7_kv_waddr),
.kv_wdata(a7_kv_wdata),
.l_ov(a7_l_ov),
.l_out(a7_l_out),
.l_red(a7_l_red),
.l_redsq(a7_l_redsq),
.l_raddr(a7_l_raddr),
.l_last(a7_l_last),
.retire(a7_retire),
.l_fault(a7_l_fault),
.sx_exp_v(a7_sx_exp_v),
.sx_exp_x(a7_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(a7_sx_rcp_v),
.sx_rcp_x(a7_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(a7_sx_rsq_v),
.sx_rsq_x(a7_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

reg [24:0] a7_va_rq[0:3]; integer a7_va_ri;
always @(posedge clk) begin a7_va_rq[0]<={ a7_va_re,a7_va_addr }; for(a7_va_ri=1;a7_va_ri<4;a7_va_ri=a7_va_ri+1)a7_va_rq[a7_va_ri]<=a7_va_rq[a7_va_ri-1];end
wire ext_a7_va_re=a7_va_rq[3][24]; wire [23:0] ext_a7_va_addr=a7_va_rq[3][23:0];
reg [31:0] a7_va_mem[0:0]; integer a7_va_mi;
always @(posedge clk) begin if(ext_a7_va_re)a7_va_mem[0]<=fp(ext_a7_va_addr,0); for(a7_va_mi=1;a7_va_mi<1;a7_va_mi=a7_va_mi+1)a7_va_mem[a7_va_mi]<=a7_va_mem[a7_va_mi-1];end
assign a7_va_q=a7_va_mem[0];
reg [24:0] a7_vb_rq[0:3]; integer a7_vb_ri;
always @(posedge clk) begin a7_vb_rq[0]<={ a7_vb_re,a7_vb_addr }; for(a7_vb_ri=1;a7_vb_ri<4;a7_vb_ri=a7_vb_ri+1)a7_vb_rq[a7_vb_ri]<=a7_vb_rq[a7_vb_ri-1];end
wire ext_a7_vb_re=a7_vb_rq[3][24]; wire [23:0] ext_a7_vb_addr=a7_vb_rq[3][23:0];
reg [31:0] a7_vb_mem[0:0]; integer a7_vb_mi;
always @(posedge clk) begin if(ext_a7_vb_re)a7_vb_mem[0]<=fp(ext_a7_vb_addr,1); for(a7_vb_mi=1;a7_vb_mi<1;a7_vb_mi=a7_vb_mi+1)a7_vb_mem[a7_vb_mi]<=a7_vb_mem[a7_vb_mi-1];end
assign a7_vb_q=a7_vb_mem[0];
reg [24:0] a7_vc_rq[0:3]; integer a7_vc_ri;
always @(posedge clk) begin a7_vc_rq[0]<={ a7_vc_re,a7_vc_addr }; for(a7_vc_ri=1;a7_vc_ri<4;a7_vc_ri=a7_vc_ri+1)a7_vc_rq[a7_vc_ri]<=a7_vc_rq[a7_vc_ri-1];end
wire ext_a7_vc_re=a7_vc_rq[3][24]; wire [23:0] ext_a7_vc_addr=a7_vc_rq[3][23:0];
reg [31:0] a7_vc_mem[0:0]; integer a7_vc_mi;
always @(posedge clk) begin if(ext_a7_vc_re)a7_vc_mem[0]<=fp(ext_a7_vc_addr,2); for(a7_vc_mi=1;a7_vc_mi<1;a7_vc_mi=a7_vc_mi+1)a7_vc_mem[a7_vc_mi]<=a7_vc_mem[a7_vc_mi-1];end
assign a7_vc_q=a7_vc_mem[0];
reg [24:0] a7_wrom_rq[0:3]; integer a7_wrom_ri;
always @(posedge clk) begin a7_wrom_rq[0]<={ a7_wrom_re,a7_wrom_addr }; for(a7_wrom_ri=1;a7_wrom_ri<4;a7_wrom_ri=a7_wrom_ri+1)a7_wrom_rq[a7_wrom_ri]<=a7_wrom_rq[a7_wrom_ri-1];end
wire ext_a7_wrom_re=a7_wrom_rq[3][24]; wire [23:0] ext_a7_wrom_addr=a7_wrom_rq[3][23:0];
reg [255:0] a7_wrom_mem[0:2]; integer a7_wrom_mi;
always @(posedge clk) begin if(ext_a7_wrom_re)a7_wrom_mem[0]<=fw(ext_a7_wrom_addr); for(a7_wrom_mi=1;a7_wrom_mi<3;a7_wrom_mi=a7_wrom_mi+1)a7_wrom_mem[a7_wrom_mi]<=a7_wrom_mem[a7_wrom_mi-1];end
assign a7_wrom_q=a7_wrom_mem[2];
reg [24:0] a7_crom_rq[0:3]; integer a7_crom_ri;
always @(posedge clk) begin a7_crom_rq[0]<={ a7_crom_re,a7_crom_addr }; for(a7_crom_ri=1;a7_crom_ri<4;a7_crom_ri=a7_crom_ri+1)a7_crom_rq[a7_crom_ri]<=a7_crom_rq[a7_crom_ri-1];end
wire ext_a7_crom_re=a7_crom_rq[3][24]; wire [23:0] ext_a7_crom_addr=a7_crom_rq[3][23:0];
reg [63:0] a7_crom_mem[0:3]; integer a7_crom_mi;
always @(posedge clk) begin if(ext_a7_crom_re)a7_crom_mem[0]<={fp(ext_a7_crom_addr,5),fp(ext_a7_crom_addr,6)}; for(a7_crom_mi=1;a7_crom_mi<4;a7_crom_mi=a7_crom_mi+1)a7_crom_mem[a7_crom_mi]<=a7_crom_mem[a7_crom_mi-1];end
assign a7_crom_q=a7_crom_mem[3];
reg [31:0] ref_va_mem[0:0]; integer ref_va_mi;
always @(posedge clk) begin if(ref_va_re)ref_va_mem[0]<=fp(ref_va_addr,0);for(ref_va_mi=1;ref_va_mi<1;ref_va_mi=ref_va_mi+1)ref_va_mem[ref_va_mi]<=ref_va_mem[ref_va_mi-1];end
always @* va_q=ref_va_mem[0];
reg [31:0] ref_vb_mem[0:0]; integer ref_vb_mi;
always @(posedge clk) begin if(ref_vb_re)ref_vb_mem[0]<=fp(ref_vb_addr,1);for(ref_vb_mi=1;ref_vb_mi<1;ref_vb_mi=ref_vb_mi+1)ref_vb_mem[ref_vb_mi]<=ref_vb_mem[ref_vb_mi-1];end
always @* vb_q=ref_vb_mem[0];
reg [31:0] ref_vc_mem[0:0]; integer ref_vc_mi;
always @(posedge clk) begin if(ref_vc_re)ref_vc_mem[0]<=fp(ref_vc_addr,2);for(ref_vc_mi=1;ref_vc_mi<1;ref_vc_mi=ref_vc_mi+1)ref_vc_mem[ref_vc_mi]<=ref_vc_mem[ref_vc_mi-1];end
always @* vc_q=ref_vc_mem[0];
reg [255:0] ref_wrom_mem[0:2]; integer ref_wrom_mi;
always @(posedge clk) begin if(ref_wrom_re)ref_wrom_mem[0]<=fw(ref_wrom_addr);for(ref_wrom_mi=1;ref_wrom_mi<3;ref_wrom_mi=ref_wrom_mi+1)ref_wrom_mem[ref_wrom_mi]<=ref_wrom_mem[ref_wrom_mi-1];end
always @* wrom_q=ref_wrom_mem[2];
reg [63:0] ref_crom_mem[0:3]; integer ref_crom_mi;
always @(posedge clk) begin if(ref_crom_re)ref_crom_mem[0]<={fp(ref_crom_addr,5),fp(ref_crom_addr,6)};for(ref_crom_mi=1;ref_crom_mi<4;ref_crom_mi=ref_crom_mi+1)ref_crom_mem[ref_crom_mi]<=ref_crom_mem[ref_crom_mi-1];end
always @* crom_q=ref_crom_mem[3];
integer cycle=0;integer lag,j;integer seen[0:4];
wire [56:0] ref_vm_word={ref_vm_we,{ref_vm_waddr,ref_vm_wdata}};
reg [56:0] hist_vm[0:15]; integer hi_vm;
always @(posedge clk) begin hist_vm[0]<=ref_vm_word;for(hi_vm=1;hi_vm<16;hi_vm=hi_vm+1)hist_vm[hi_vm]<=hist_vm[hi_vm-1];end
wire [56:0] p4_vm_word={p4_vm_we,{p4_vm_waddr,p4_vm_wdata}};
reg [56:0] wrap_p4_vm[0:3]; integer wh_p4_vm;
always @(posedge clk)begin wrap_p4_vm[0]<=p4_vm_word;for(wh_p4_vm=1;wh_p4_vm<4;wh_p4_vm=wh_p4_vm+1)wrap_p4_vm[wh_p4_vm]<=wrap_p4_vm[wh_p4_vm-1];end
integer err_p4_vm[0:16],wer_p4_vm[0:16];
wire [56:0] m3_vm_word={m3_vm_we,{m3_vm_waddr,m3_vm_wdata}};
reg [56:0] wrap_m3_vm[0:3]; integer wh_m3_vm;
always @(posedge clk)begin wrap_m3_vm[0]<=m3_vm_word;for(wh_m3_vm=1;wh_m3_vm<4;wh_m3_vm=wh_m3_vm+1)wrap_m3_vm[wh_m3_vm]<=wrap_m3_vm[wh_m3_vm-1];end
integer err_m3_vm[0:16],wer_m3_vm[0:16];
wire [56:0] r3_vm_word={r3_vm_we,{r3_vm_waddr,r3_vm_wdata}};
reg [56:0] wrap_r3_vm[0:3]; integer wh_r3_vm;
always @(posedge clk)begin wrap_r3_vm[0]<=r3_vm_word;for(wh_r3_vm=1;wh_r3_vm<4;wh_r3_vm=wh_r3_vm+1)wrap_r3_vm[wh_r3_vm]<=wrap_r3_vm[wh_r3_vm-1];end
integer err_r3_vm[0:16],wer_r3_vm[0:16];
wire [56:0] a7_vm_word={a7_vm_we,{a7_vm_waddr,a7_vm_wdata}};
reg [56:0] wrap_a7_vm[0:3]; integer wh_a7_vm;
always @(posedge clk)begin wrap_a7_vm[0]<=a7_vm_word;for(wh_a7_vm=1;wh_a7_vm<4;wh_a7_vm=wh_a7_vm+1)wrap_a7_vm[wh_a7_vm]<=wrap_a7_vm[wh_a7_vm-1];end
integer err_a7_vm[0:16],wer_a7_vm[0:16];
wire [56:0] ref_kv_word={ref_kv_we,{ref_kv_waddr,ref_kv_wdata}};
reg [56:0] hist_kv[0:15]; integer hi_kv;
always @(posedge clk) begin hist_kv[0]<=ref_kv_word;for(hi_kv=1;hi_kv<16;hi_kv=hi_kv+1)hist_kv[hi_kv]<=hist_kv[hi_kv-1];end
wire [56:0] p4_kv_word={p4_kv_we,{p4_kv_waddr,p4_kv_wdata}};
reg [56:0] wrap_p4_kv[0:3]; integer wh_p4_kv;
always @(posedge clk)begin wrap_p4_kv[0]<=p4_kv_word;for(wh_p4_kv=1;wh_p4_kv<4;wh_p4_kv=wh_p4_kv+1)wrap_p4_kv[wh_p4_kv]<=wrap_p4_kv[wh_p4_kv-1];end
integer err_p4_kv[0:16],wer_p4_kv[0:16];
wire [56:0] m3_kv_word={m3_kv_we,{m3_kv_waddr,m3_kv_wdata}};
reg [56:0] wrap_m3_kv[0:3]; integer wh_m3_kv;
always @(posedge clk)begin wrap_m3_kv[0]<=m3_kv_word;for(wh_m3_kv=1;wh_m3_kv<4;wh_m3_kv=wh_m3_kv+1)wrap_m3_kv[wh_m3_kv]<=wrap_m3_kv[wh_m3_kv-1];end
integer err_m3_kv[0:16],wer_m3_kv[0:16];
wire [56:0] r3_kv_word={r3_kv_we,{r3_kv_waddr,r3_kv_wdata}};
reg [56:0] wrap_r3_kv[0:3]; integer wh_r3_kv;
always @(posedge clk)begin wrap_r3_kv[0]<=r3_kv_word;for(wh_r3_kv=1;wh_r3_kv<4;wh_r3_kv=wh_r3_kv+1)wrap_r3_kv[wh_r3_kv]<=wrap_r3_kv[wh_r3_kv-1];end
integer err_r3_kv[0:16],wer_r3_kv[0:16];
wire [56:0] a7_kv_word={a7_kv_we,{a7_kv_waddr,a7_kv_wdata}};
reg [56:0] wrap_a7_kv[0:3]; integer wh_a7_kv;
always @(posedge clk)begin wrap_a7_kv[0]<=a7_kv_word;for(wh_a7_kv=1;wh_a7_kv<4;wh_a7_kv=wh_a7_kv+1)wrap_a7_kv[wh_a7_kv]<=wrap_a7_kv[wh_a7_kv-1];end
integer err_a7_kv[0:16],wer_a7_kv[0:16];
wire [60:0] ref_result_word={ref_l_ov,{ref_l_out,ref_l_red,ref_l_redsq,ref_l_raddr,ref_l_last}};
reg [60:0] hist_result[0:15]; integer hi_result;
always @(posedge clk) begin hist_result[0]<=ref_result_word;for(hi_result=1;hi_result<16;hi_result=hi_result+1)hist_result[hi_result]<=hist_result[hi_result-1];end
wire [60:0] p4_result_word={p4_l_ov,{p4_l_out,p4_l_red,p4_l_redsq,p4_l_raddr,p4_l_last}};
reg [60:0] wrap_p4_result[0:3]; integer wh_p4_result;
always @(posedge clk)begin wrap_p4_result[0]<=p4_result_word;for(wh_p4_result=1;wh_p4_result<4;wh_p4_result=wh_p4_result+1)wrap_p4_result[wh_p4_result]<=wrap_p4_result[wh_p4_result-1];end
integer err_p4_result[0:16],wer_p4_result[0:16];
wire [60:0] m3_result_word={m3_l_ov,{m3_l_out,m3_l_red,m3_l_redsq,m3_l_raddr,m3_l_last}};
reg [60:0] wrap_m3_result[0:3]; integer wh_m3_result;
always @(posedge clk)begin wrap_m3_result[0]<=m3_result_word;for(wh_m3_result=1;wh_m3_result<4;wh_m3_result=wh_m3_result+1)wrap_m3_result[wh_m3_result]<=wrap_m3_result[wh_m3_result-1];end
integer err_m3_result[0:16],wer_m3_result[0:16];
wire [60:0] r3_result_word={r3_l_ov,{r3_l_out,r3_l_red,r3_l_redsq,r3_l_raddr,r3_l_last}};
reg [60:0] wrap_r3_result[0:3]; integer wh_r3_result;
always @(posedge clk)begin wrap_r3_result[0]<=r3_result_word;for(wh_r3_result=1;wh_r3_result<4;wh_r3_result=wh_r3_result+1)wrap_r3_result[wh_r3_result]<=wrap_r3_result[wh_r3_result-1];end
integer err_r3_result[0:16],wer_r3_result[0:16];
wire [60:0] a7_result_word={a7_l_ov,{a7_l_out,a7_l_red,a7_l_redsq,a7_l_raddr,a7_l_last}};
reg [60:0] wrap_a7_result[0:3]; integer wh_a7_result;
always @(posedge clk)begin wrap_a7_result[0]<=a7_result_word;for(wh_a7_result=1;wh_a7_result<4;wh_a7_result=wh_a7_result+1)wrap_a7_result[wh_a7_result]<=wrap_a7_result[wh_a7_result-1];end
integer err_a7_result[0:16],wer_a7_result[0:16];
wire [1:0] ref_retire_word={ref_retire,1'b0};
reg [1:0] hist_retire[0:15]; integer hi_retire;
always @(posedge clk) begin hist_retire[0]<=ref_retire_word;for(hi_retire=1;hi_retire<16;hi_retire=hi_retire+1)hist_retire[hi_retire]<=hist_retire[hi_retire-1];end
wire [1:0] p4_retire_word={p4_retire,1'b0};
reg [1:0] wrap_p4_retire[0:3]; integer wh_p4_retire;
always @(posedge clk)begin wrap_p4_retire[0]<=p4_retire_word;for(wh_p4_retire=1;wh_p4_retire<4;wh_p4_retire=wh_p4_retire+1)wrap_p4_retire[wh_p4_retire]<=wrap_p4_retire[wh_p4_retire-1];end
integer err_p4_retire[0:16],wer_p4_retire[0:16];
wire [1:0] m3_retire_word={m3_retire,1'b0};
reg [1:0] wrap_m3_retire[0:3]; integer wh_m3_retire;
always @(posedge clk)begin wrap_m3_retire[0]<=m3_retire_word;for(wh_m3_retire=1;wh_m3_retire<4;wh_m3_retire=wh_m3_retire+1)wrap_m3_retire[wh_m3_retire]<=wrap_m3_retire[wh_m3_retire-1];end
integer err_m3_retire[0:16],wer_m3_retire[0:16];
wire [1:0] r3_retire_word={r3_retire,1'b0};
reg [1:0] wrap_r3_retire[0:3]; integer wh_r3_retire;
always @(posedge clk)begin wrap_r3_retire[0]<=r3_retire_word;for(wh_r3_retire=1;wh_r3_retire<4;wh_r3_retire=wh_r3_retire+1)wrap_r3_retire[wh_r3_retire]<=wrap_r3_retire[wh_r3_retire-1];end
integer err_r3_retire[0:16],wer_r3_retire[0:16];
wire [1:0] a7_retire_word={a7_retire,1'b0};
reg [1:0] wrap_a7_retire[0:3]; integer wh_a7_retire;
always @(posedge clk)begin wrap_a7_retire[0]<=a7_retire_word;for(wh_a7_retire=1;wh_a7_retire<4;wh_a7_retire=wh_a7_retire+1)wrap_a7_retire[wh_a7_retire]<=wrap_a7_retire[wh_a7_retire-1];end
integer err_a7_retire[0:16],wer_a7_retire[0:16];
wire [1:0] ref_fault_word={ref_l_fault,1'b0};
reg [1:0] hist_fault[0:15]; integer hi_fault;
always @(posedge clk) begin hist_fault[0]<=ref_fault_word;for(hi_fault=1;hi_fault<16;hi_fault=hi_fault+1)hist_fault[hi_fault]<=hist_fault[hi_fault-1];end
wire [1:0] p4_fault_word={p4_l_fault,1'b0};
reg [1:0] wrap_p4_fault[0:3]; integer wh_p4_fault;
always @(posedge clk)begin wrap_p4_fault[0]<=p4_fault_word;for(wh_p4_fault=1;wh_p4_fault<4;wh_p4_fault=wh_p4_fault+1)wrap_p4_fault[wh_p4_fault]<=wrap_p4_fault[wh_p4_fault-1];end
integer err_p4_fault[0:16],wer_p4_fault[0:16];
wire [1:0] m3_fault_word={m3_l_fault,1'b0};
reg [1:0] wrap_m3_fault[0:3]; integer wh_m3_fault;
always @(posedge clk)begin wrap_m3_fault[0]<=m3_fault_word;for(wh_m3_fault=1;wh_m3_fault<4;wh_m3_fault=wh_m3_fault+1)wrap_m3_fault[wh_m3_fault]<=wrap_m3_fault[wh_m3_fault-1];end
integer err_m3_fault[0:16],wer_m3_fault[0:16];
wire [1:0] r3_fault_word={r3_l_fault,1'b0};
reg [1:0] wrap_r3_fault[0:3]; integer wh_r3_fault;
always @(posedge clk)begin wrap_r3_fault[0]<=r3_fault_word;for(wh_r3_fault=1;wh_r3_fault<4;wh_r3_fault=wh_r3_fault+1)wrap_r3_fault[wh_r3_fault]<=wrap_r3_fault[wh_r3_fault-1];end
integer err_r3_fault[0:16],wer_r3_fault[0:16];
wire [1:0] a7_fault_word={a7_l_fault,1'b0};
reg [1:0] wrap_a7_fault[0:3]; integer wh_a7_fault;
always @(posedge clk)begin wrap_a7_fault[0]<=a7_fault_word;for(wh_a7_fault=1;wh_a7_fault<4;wh_a7_fault=wh_a7_fault+1)wrap_a7_fault[wh_a7_fault]<=wrap_a7_fault[wh_a7_fault-1];end
integer err_a7_fault[0:16],wer_a7_fault[0:16];
integer req_errors=0,requests=0;reg[124:0] reqhist[0:3];integer rh;
wire[124:0] ref_requests={{ref_va_re,ref_va_addr},{ref_vb_re,ref_vb_addr},{ref_vc_re,ref_vc_addr},{ref_wrom_re,ref_wrom_addr},{ref_crom_re,ref_crom_addr}};
wire[124:0] p4_requests={{ext_p4_va_re,ext_p4_va_addr},{ext_p4_vb_re,ext_p4_vb_addr},{ext_p4_vc_re,ext_p4_vc_addr},{ext_p4_wrom_re,ext_p4_wrom_addr},{ext_p4_crom_re,ext_p4_crom_addr}};
always @(posedge clk)begin reqhist[0]<=ref_requests;for(rh=1;rh<4;rh=rh+1)reqhist[rh]<=reqhist[rh-1];end
initial begin for(j=0;j<5;j=j+1)seen[j]=0;for(lag=0;lag<17;lag=lag+1)begin
err_p4_vm[lag]=0;wer_p4_vm[lag]=0;
err_m3_vm[lag]=0;wer_m3_vm[lag]=0;
err_r3_vm[lag]=0;wer_r3_vm[lag]=0;
err_a7_vm[lag]=0;wer_a7_vm[lag]=0;
err_p4_kv[lag]=0;wer_p4_kv[lag]=0;
err_m3_kv[lag]=0;wer_m3_kv[lag]=0;
err_r3_kv[lag]=0;wer_r3_kv[lag]=0;
err_a7_kv[lag]=0;wer_a7_kv[lag]=0;
err_p4_result[lag]=0;wer_p4_result[lag]=0;
err_m3_result[lag]=0;wer_m3_result[lag]=0;
err_r3_result[lag]=0;wer_r3_result[lag]=0;
err_a7_result[lag]=0;wer_a7_result[lag]=0;
err_p4_retire[lag]=0;wer_p4_retire[lag]=0;
err_m3_retire[lag]=0;wer_m3_retire[lag]=0;
err_r3_retire[lag]=0;wer_r3_retire[lag]=0;
err_a7_retire[lag]=0;wer_a7_retire[lag]=0;
err_p4_fault[lag]=0;wer_p4_fault[lag]=0;
err_m3_fault[lag]=0;wer_m3_fault[lag]=0;
err_r3_fault[lag]=0;wer_r3_fault[lag]=0;
err_a7_fault[lag]=0;wer_a7_fault[lag]=0;
end end
always @(negedge clk)begin
cycle=cycle+1;rst_n=(cycle>8);live=(cycle>128&&cycle%256<32);emit0=live;i=cycle%256;i_last_r=(i==31);fin_th=32;
cura0=0;curb0=64;curc0=128;curd0=256;rrow=32;asi=1;bsi=1;csi=1;dsi=1;asrc=(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=1;md=(cycle/512)%2;red=0;dst=(cycle/256)%3;ad=0;ma=0;mb=0;cls=0;accept=0;redsq=0;imm1=32'h3f800000;imm2=0;
if(cycle>256)begin
if(p4_requests!==reqhist[3])req_errors=req_errors+1;
if(ref_vm_we)seen[0]=seen[0]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_vm_word[56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (p4_vm_word[56] && p4_vm_word !== (lag==0?ref_vm_word:hist_vm[lag-1])))err_p4_vm[lag]=err_p4_vm[lag]+1;
if((wrap_p4_vm[3][56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (wrap_p4_vm[3][56] && wrap_p4_vm[3] !== (lag==0?ref_vm_word:hist_vm[lag-1])))wer_p4_vm[lag]=wer_p4_vm[lag]+1;
if((m3_vm_word[56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (m3_vm_word[56] && m3_vm_word !== (lag==0?ref_vm_word:hist_vm[lag-1])))err_m3_vm[lag]=err_m3_vm[lag]+1;
if((wrap_m3_vm[3][56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (wrap_m3_vm[3][56] && wrap_m3_vm[3] !== (lag==0?ref_vm_word:hist_vm[lag-1])))wer_m3_vm[lag]=wer_m3_vm[lag]+1;
if((r3_vm_word[56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (r3_vm_word[56] && r3_vm_word !== (lag==0?ref_vm_word:hist_vm[lag-1])))err_r3_vm[lag]=err_r3_vm[lag]+1;
if((wrap_r3_vm[3][56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (wrap_r3_vm[3][56] && wrap_r3_vm[3] !== (lag==0?ref_vm_word:hist_vm[lag-1])))wer_r3_vm[lag]=wer_r3_vm[lag]+1;
if((a7_vm_word[56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (a7_vm_word[56] && a7_vm_word !== (lag==0?ref_vm_word:hist_vm[lag-1])))err_a7_vm[lag]=err_a7_vm[lag]+1;
if((wrap_a7_vm[3][56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (wrap_a7_vm[3][56] && wrap_a7_vm[3] !== (lag==0?ref_vm_word:hist_vm[lag-1])))wer_a7_vm[lag]=wer_a7_vm[lag]+1;
end
if(ref_kv_we)seen[1]=seen[1]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (p4_kv_word[56] && p4_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_p4_kv[lag]=err_p4_kv[lag]+1;
if((wrap_p4_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_p4_kv[3][56] && wrap_p4_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_p4_kv[lag]=wer_p4_kv[lag]+1;
if((m3_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (m3_kv_word[56] && m3_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_m3_kv[lag]=err_m3_kv[lag]+1;
if((wrap_m3_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_m3_kv[3][56] && wrap_m3_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_m3_kv[lag]=wer_m3_kv[lag]+1;
if((r3_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (r3_kv_word[56] && r3_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_r3_kv[lag]=err_r3_kv[lag]+1;
if((wrap_r3_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_r3_kv[3][56] && wrap_r3_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_r3_kv[lag]=wer_r3_kv[lag]+1;
if((a7_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (a7_kv_word[56] && a7_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_a7_kv[lag]=err_a7_kv[lag]+1;
if((wrap_a7_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_a7_kv[3][56] && wrap_a7_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_a7_kv[lag]=wer_a7_kv[lag]+1;
end
if(ref_l_ov)seen[2]=seen[2]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (p4_result_word[60] && p4_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_p4_result[lag]=err_p4_result[lag]+1;
if((wrap_p4_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_p4_result[3][60] && wrap_p4_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_p4_result[lag]=wer_p4_result[lag]+1;
if((m3_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (m3_result_word[60] && m3_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_m3_result[lag]=err_m3_result[lag]+1;
if((wrap_m3_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_m3_result[3][60] && wrap_m3_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_m3_result[lag]=wer_m3_result[lag]+1;
if((r3_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (r3_result_word[60] && r3_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_r3_result[lag]=err_r3_result[lag]+1;
if((wrap_r3_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_r3_result[3][60] && wrap_r3_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_r3_result[lag]=wer_r3_result[lag]+1;
if((a7_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (a7_result_word[60] && a7_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_a7_result[lag]=err_a7_result[lag]+1;
if((wrap_a7_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_a7_result[3][60] && wrap_a7_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_a7_result[lag]=wer_a7_result[lag]+1;
end
if(ref_retire)seen[3]=seen[3]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (p4_retire_word[1] && p4_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_p4_retire[lag]=err_p4_retire[lag]+1;
if((wrap_p4_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_p4_retire[3][1] && wrap_p4_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_p4_retire[lag]=wer_p4_retire[lag]+1;
if((m3_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (m3_retire_word[1] && m3_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_m3_retire[lag]=err_m3_retire[lag]+1;
if((wrap_m3_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_m3_retire[3][1] && wrap_m3_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_m3_retire[lag]=wer_m3_retire[lag]+1;
if((r3_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (r3_retire_word[1] && r3_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_r3_retire[lag]=err_r3_retire[lag]+1;
if((wrap_r3_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_r3_retire[3][1] && wrap_r3_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_r3_retire[lag]=wer_r3_retire[lag]+1;
if((a7_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (a7_retire_word[1] && a7_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_a7_retire[lag]=err_a7_retire[lag]+1;
if((wrap_a7_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_a7_retire[3][1] && wrap_a7_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_a7_retire[lag]=wer_a7_retire[lag]+1;
end
if(ref_l_fault)seen[4]=seen[4]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (p4_fault_word[1] && p4_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_p4_fault[lag]=err_p4_fault[lag]+1;
if((wrap_p4_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_p4_fault[3][1] && wrap_p4_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_p4_fault[lag]=wer_p4_fault[lag]+1;
if((m3_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (m3_fault_word[1] && m3_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_m3_fault[lag]=err_m3_fault[lag]+1;
if((wrap_m3_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_m3_fault[3][1] && wrap_m3_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_m3_fault[lag]=wer_m3_fault[lag]+1;
if((r3_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (r3_fault_word[1] && r3_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_r3_fault[lag]=err_r3_fault[lag]+1;
if((wrap_r3_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_r3_fault[3][1] && wrap_r3_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_r3_fault[lag]=wer_r3_fault[lag]+1;
if((a7_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (a7_fault_word[1] && a7_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_a7_fault[lag]=err_a7_fault[lag]+1;
if((wrap_a7_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_a7_fault[3][1] && wrap_a7_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_a7_fault[lag]=wer_a7_fault[lag]+1;
end
end
if(cycle>256 && p4_vm_word[56] && p4_vm_word !== hist_vm[3] && err_p4_vm[4]<4)$display("ML12_COUNTEREXAMPLE p4 cycle=%0d ref4=%h got=%h ref_va=%h new_va=%h",cycle,hist_vm[3],p4_vm_word,va_q,p4_va_q);
if(cycle>256 && a7_vm_word[56] && a7_vm_word !== hist_vm[3] && err_a7_vm[4]<4)$display("ML12_COUNTEREXAMPLE a7 cycle=%0d ref4=%h got=%h",cycle,hist_vm[3],a7_vm_word);
if(cycle==2600)begin
$display("ML12_REQUEST_CHECK errors=%0d",req_errors);
$display("ML12_COUNT vm %0d",seen[0]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_vm[lag],wer_p4_vm[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE m3 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_m3_vm[lag],wer_m3_vm[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE r3 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_r3_vm[lag],wer_r3_vm[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE a7 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_a7_vm[lag],wer_a7_vm[lag]);
$display("ML12_COUNT kv %0d",seen[1]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_kv[lag],wer_p4_kv[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE m3 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_m3_kv[lag],wer_m3_kv[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE r3 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_r3_kv[lag],wer_r3_kv[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE a7 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_a7_kv[lag],wer_a7_kv[lag]);
$display("ML12_COUNT result %0d",seen[2]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_result[lag],wer_p4_result[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE m3 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_m3_result[lag],wer_m3_result[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE r3 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_r3_result[lag],wer_r3_result[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE a7 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_a7_result[lag],wer_a7_result[lag]);
$display("ML12_COUNT retire %0d",seen[3]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_retire[lag],wer_p4_retire[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE m3 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_m3_retire[lag],wer_m3_retire[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE r3 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_r3_retire[lag],wer_r3_retire[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE a7 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_a7_retire[lag],wer_a7_retire[lag]);
$display("ML12_COUNT fault %0d",seen[4]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_fault[lag],wer_p4_fault[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE m3 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_m3_fault[lag],wer_m3_fault[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE r3 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_r3_fault[lag],wer_r3_fault[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE a7 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_a7_fault[lag],wer_a7_fault[lag]);
$finish;end
end
endmodule
