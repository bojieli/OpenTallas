`timescale 1ns/1ps
module tb_ml8_req4;
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
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(0)) u_p4 (.clk(clk),
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
wire z0_va_re;
wire [23:0] z0_va_addr;
wire z0_vb_re;
wire [23:0] z0_vb_addr;
wire z0_vc_re;
wire [23:0] z0_vc_addr;
wire z0_wrom_re;
wire [23:0] z0_wrom_addr;
wire z0_crom_re;
wire [23:0] z0_crom_addr;
wire z0_vm_we;
wire [23:0] z0_vm_waddr;
wire [31:0] z0_vm_wdata;
wire z0_kv_we;
wire [23:0] z0_kv_waddr;
wire [31:0] z0_kv_wdata;
wire z0_l_ov;
wire [31:0] z0_l_out;
wire [1:0] z0_l_red;
wire z0_l_redsq;
wire [23:0] z0_l_raddr;
wire z0_l_last;
wire z0_retire;
wire z0_l_fault;
wire z0_sx_exp_v;
wire [31:0] z0_sx_exp_x;
wire z0_sx_rcp_v;
wire [31:0] z0_sx_rcp_x;
wire z0_sx_rsq_v;
wire [31:0] z0_sx_rsq_x;
wire [31:0] z0_va_q;
wire [31:0] z0_vb_q;
wire [31:0] z0_vc_q;
wire [255:0] z0_wrom_q;
wire [63:0] z0_crom_q;
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(0)) u_z0 (.clk(clk),
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
.va_re(z0_va_re),
.va_addr(z0_va_addr),
.va_q(z0_va_q),
.vb_re(z0_vb_re),
.vb_addr(z0_vb_addr),
.vb_q(z0_vb_q),
.vc_re(z0_vc_re),
.vc_addr(z0_vc_addr),
.vc_q(z0_vc_q),
.wrom_re(z0_wrom_re),
.wrom_addr(z0_wrom_addr),
.wrom_q(z0_wrom_q),
.crom_re(z0_crom_re),
.crom_addr(z0_crom_addr),
.crom_q(z0_crom_q),
.vm_we(z0_vm_we),
.vm_waddr(z0_vm_waddr),
.vm_wdata(z0_vm_wdata),
.kv_we(z0_kv_we),
.kv_waddr(z0_kv_waddr),
.kv_wdata(z0_kv_wdata),
.l_ov(z0_l_ov),
.l_out(z0_l_out),
.l_red(z0_l_red),
.l_redsq(z0_l_redsq),
.l_raddr(z0_l_raddr),
.l_last(z0_l_last),
.retire(z0_retire),
.l_fault(z0_l_fault),
.sx_exp_v(z0_sx_exp_v),
.sx_exp_x(z0_sx_exp_x),
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(z0_sx_rcp_v),
.sx_rcp_x(z0_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(z0_sx_rsq_v),
.sx_rsq_x(z0_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));

wire ext_z0_va_re=z0_va_re; wire [23:0] ext_z0_va_addr=z0_va_addr;
reg [31:0] z0_va_mem[0:0]; integer z0_va_mi;
always @(posedge clk) begin if(ext_z0_va_re)z0_va_mem[0]<=fp(ext_z0_va_addr,0); for(z0_va_mi=1;z0_va_mi<1;z0_va_mi=z0_va_mi+1)z0_va_mem[z0_va_mi]<=z0_va_mem[z0_va_mi-1];end
assign z0_va_q=z0_va_mem[0];
wire ext_z0_vb_re=z0_vb_re; wire [23:0] ext_z0_vb_addr=z0_vb_addr;
reg [31:0] z0_vb_mem[0:0]; integer z0_vb_mi;
always @(posedge clk) begin if(ext_z0_vb_re)z0_vb_mem[0]<=fp(ext_z0_vb_addr,1); for(z0_vb_mi=1;z0_vb_mi<1;z0_vb_mi=z0_vb_mi+1)z0_vb_mem[z0_vb_mi]<=z0_vb_mem[z0_vb_mi-1];end
assign z0_vb_q=z0_vb_mem[0];
wire ext_z0_vc_re=z0_vc_re; wire [23:0] ext_z0_vc_addr=z0_vc_addr;
reg [31:0] z0_vc_mem[0:0]; integer z0_vc_mi;
always @(posedge clk) begin if(ext_z0_vc_re)z0_vc_mem[0]<=fp(ext_z0_vc_addr,2); for(z0_vc_mi=1;z0_vc_mi<1;z0_vc_mi=z0_vc_mi+1)z0_vc_mem[z0_vc_mi]<=z0_vc_mem[z0_vc_mi-1];end
assign z0_vc_q=z0_vc_mem[0];
wire ext_z0_wrom_re=z0_wrom_re; wire [23:0] ext_z0_wrom_addr=z0_wrom_addr;
reg [255:0] z0_wrom_mem[0:2]; integer z0_wrom_mi;
always @(posedge clk) begin if(ext_z0_wrom_re)z0_wrom_mem[0]<=fw(ext_z0_wrom_addr); for(z0_wrom_mi=1;z0_wrom_mi<3;z0_wrom_mi=z0_wrom_mi+1)z0_wrom_mem[z0_wrom_mi]<=z0_wrom_mem[z0_wrom_mi-1];end
assign z0_wrom_q=z0_wrom_mem[2];
wire ext_z0_crom_re=z0_crom_re; wire [23:0] ext_z0_crom_addr=z0_crom_addr;
reg [63:0] z0_crom_mem[0:3]; integer z0_crom_mi;
always @(posedge clk) begin if(ext_z0_crom_re)z0_crom_mem[0]<={fp(ext_z0_crom_addr,5),fp(ext_z0_crom_addr,6)}; for(z0_crom_mi=1;z0_crom_mi<4;z0_crom_mi=z0_crom_mi+1)z0_crom_mem[z0_crom_mi]<=z0_crom_mem[z0_crom_mi-1];end
assign z0_crom_q=z0_crom_mem[3];
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
wire [56:0] z0_vm_word={z0_vm_we,{z0_vm_waddr,z0_vm_wdata}};
reg [56:0] wrap_z0_vm[0:3]; integer wh_z0_vm;
always @(posedge clk)begin wrap_z0_vm[0]<=z0_vm_word;for(wh_z0_vm=1;wh_z0_vm<4;wh_z0_vm=wh_z0_vm+1)wrap_z0_vm[wh_z0_vm]<=wrap_z0_vm[wh_z0_vm-1];end
integer err_z0_vm[0:16],wer_z0_vm[0:16];
wire [56:0] ref_kv_word={ref_kv_we,{ref_kv_waddr,ref_kv_wdata}};
reg [56:0] hist_kv[0:15]; integer hi_kv;
always @(posedge clk) begin hist_kv[0]<=ref_kv_word;for(hi_kv=1;hi_kv<16;hi_kv=hi_kv+1)hist_kv[hi_kv]<=hist_kv[hi_kv-1];end
wire [56:0] p4_kv_word={p4_kv_we,{p4_kv_waddr,p4_kv_wdata}};
reg [56:0] wrap_p4_kv[0:3]; integer wh_p4_kv;
always @(posedge clk)begin wrap_p4_kv[0]<=p4_kv_word;for(wh_p4_kv=1;wh_p4_kv<4;wh_p4_kv=wh_p4_kv+1)wrap_p4_kv[wh_p4_kv]<=wrap_p4_kv[wh_p4_kv-1];end
integer err_p4_kv[0:16],wer_p4_kv[0:16];
wire [56:0] z0_kv_word={z0_kv_we,{z0_kv_waddr,z0_kv_wdata}};
reg [56:0] wrap_z0_kv[0:3]; integer wh_z0_kv;
always @(posedge clk)begin wrap_z0_kv[0]<=z0_kv_word;for(wh_z0_kv=1;wh_z0_kv<4;wh_z0_kv=wh_z0_kv+1)wrap_z0_kv[wh_z0_kv]<=wrap_z0_kv[wh_z0_kv-1];end
integer err_z0_kv[0:16],wer_z0_kv[0:16];
wire [60:0] ref_result_word={ref_l_ov,{ref_l_out,ref_l_red,ref_l_redsq,ref_l_raddr,ref_l_last}};
reg [60:0] hist_result[0:15]; integer hi_result;
always @(posedge clk) begin hist_result[0]<=ref_result_word;for(hi_result=1;hi_result<16;hi_result=hi_result+1)hist_result[hi_result]<=hist_result[hi_result-1];end
wire [60:0] p4_result_word={p4_l_ov,{p4_l_out,p4_l_red,p4_l_redsq,p4_l_raddr,p4_l_last}};
reg [60:0] wrap_p4_result[0:3]; integer wh_p4_result;
always @(posedge clk)begin wrap_p4_result[0]<=p4_result_word;for(wh_p4_result=1;wh_p4_result<4;wh_p4_result=wh_p4_result+1)wrap_p4_result[wh_p4_result]<=wrap_p4_result[wh_p4_result-1];end
integer err_p4_result[0:16],wer_p4_result[0:16];
wire [60:0] z0_result_word={z0_l_ov,{z0_l_out,z0_l_red,z0_l_redsq,z0_l_raddr,z0_l_last}};
reg [60:0] wrap_z0_result[0:3]; integer wh_z0_result;
always @(posedge clk)begin wrap_z0_result[0]<=z0_result_word;for(wh_z0_result=1;wh_z0_result<4;wh_z0_result=wh_z0_result+1)wrap_z0_result[wh_z0_result]<=wrap_z0_result[wh_z0_result-1];end
integer err_z0_result[0:16],wer_z0_result[0:16];
wire [1:0] ref_retire_word={ref_retire,1'b0};
reg [1:0] hist_retire[0:15]; integer hi_retire;
always @(posedge clk) begin hist_retire[0]<=ref_retire_word;for(hi_retire=1;hi_retire<16;hi_retire=hi_retire+1)hist_retire[hi_retire]<=hist_retire[hi_retire-1];end
wire [1:0] p4_retire_word={p4_retire,1'b0};
reg [1:0] wrap_p4_retire[0:3]; integer wh_p4_retire;
always @(posedge clk)begin wrap_p4_retire[0]<=p4_retire_word;for(wh_p4_retire=1;wh_p4_retire<4;wh_p4_retire=wh_p4_retire+1)wrap_p4_retire[wh_p4_retire]<=wrap_p4_retire[wh_p4_retire-1];end
integer err_p4_retire[0:16],wer_p4_retire[0:16];
wire [1:0] z0_retire_word={z0_retire,1'b0};
reg [1:0] wrap_z0_retire[0:3]; integer wh_z0_retire;
always @(posedge clk)begin wrap_z0_retire[0]<=z0_retire_word;for(wh_z0_retire=1;wh_z0_retire<4;wh_z0_retire=wh_z0_retire+1)wrap_z0_retire[wh_z0_retire]<=wrap_z0_retire[wh_z0_retire-1];end
integer err_z0_retire[0:16],wer_z0_retire[0:16];
wire [1:0] ref_fault_word={ref_l_fault,1'b0};
reg [1:0] hist_fault[0:15]; integer hi_fault;
always @(posedge clk) begin hist_fault[0]<=ref_fault_word;for(hi_fault=1;hi_fault<16;hi_fault=hi_fault+1)hist_fault[hi_fault]<=hist_fault[hi_fault-1];end
wire [1:0] p4_fault_word={p4_l_fault,1'b0};
reg [1:0] wrap_p4_fault[0:3]; integer wh_p4_fault;
always @(posedge clk)begin wrap_p4_fault[0]<=p4_fault_word;for(wh_p4_fault=1;wh_p4_fault<4;wh_p4_fault=wh_p4_fault+1)wrap_p4_fault[wh_p4_fault]<=wrap_p4_fault[wh_p4_fault-1];end
integer err_p4_fault[0:16],wer_p4_fault[0:16];
wire [1:0] z0_fault_word={z0_l_fault,1'b0};
reg [1:0] wrap_z0_fault[0:3]; integer wh_z0_fault;
always @(posedge clk)begin wrap_z0_fault[0]<=z0_fault_word;for(wh_z0_fault=1;wh_z0_fault<4;wh_z0_fault=wh_z0_fault+1)wrap_z0_fault[wh_z0_fault]<=wrap_z0_fault[wh_z0_fault-1];end
integer err_z0_fault[0:16],wer_z0_fault[0:16];
integer req_errors=0,requests=0;reg[124:0] reqhist[0:3];integer rh;
wire[124:0] ref_requests={{ref_va_re,ref_va_addr},{ref_vb_re,ref_vb_addr},{ref_vc_re,ref_vc_addr},{ref_wrom_re,ref_wrom_addr},{ref_crom_re,ref_crom_addr}};
wire[124:0] p4_requests={{ext_p4_va_re,ext_p4_va_addr},{ext_p4_vb_re,ext_p4_vb_addr},{ext_p4_vc_re,ext_p4_vc_addr},{ext_p4_wrom_re,ext_p4_wrom_addr},{ext_p4_crom_re,ext_p4_crom_addr}};
always @(posedge clk)begin reqhist[0]<=ref_requests;for(rh=1;rh<4;rh=rh+1)reqhist[rh]<=reqhist[rh-1];end
initial begin for(j=0;j<5;j=j+1)seen[j]=0;for(lag=0;lag<17;lag=lag+1)begin
err_p4_vm[lag]=0;wer_p4_vm[lag]=0;
err_z0_vm[lag]=0;wer_z0_vm[lag]=0;
err_p4_kv[lag]=0;wer_p4_kv[lag]=0;
err_z0_kv[lag]=0;wer_z0_kv[lag]=0;
err_p4_result[lag]=0;wer_p4_result[lag]=0;
err_z0_result[lag]=0;wer_z0_result[lag]=0;
err_p4_retire[lag]=0;wer_p4_retire[lag]=0;
err_z0_retire[lag]=0;wer_z0_retire[lag]=0;
err_p4_fault[lag]=0;wer_p4_fault[lag]=0;
err_z0_fault[lag]=0;wer_z0_fault[lag]=0;
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
if((z0_vm_word[56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (z0_vm_word[56] && z0_vm_word !== (lag==0?ref_vm_word:hist_vm[lag-1])))err_z0_vm[lag]=err_z0_vm[lag]+1;
if((wrap_z0_vm[3][56] !== ((lag==0?ref_vm_word:hist_vm[lag-1])>>56)) || (wrap_z0_vm[3][56] && wrap_z0_vm[3] !== (lag==0?ref_vm_word:hist_vm[lag-1])))wer_z0_vm[lag]=wer_z0_vm[lag]+1;
end
if(ref_kv_we)seen[1]=seen[1]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (p4_kv_word[56] && p4_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_p4_kv[lag]=err_p4_kv[lag]+1;
if((wrap_p4_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_p4_kv[3][56] && wrap_p4_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_p4_kv[lag]=wer_p4_kv[lag]+1;
if((z0_kv_word[56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (z0_kv_word[56] && z0_kv_word !== (lag==0?ref_kv_word:hist_kv[lag-1])))err_z0_kv[lag]=err_z0_kv[lag]+1;
if((wrap_z0_kv[3][56] !== ((lag==0?ref_kv_word:hist_kv[lag-1])>>56)) || (wrap_z0_kv[3][56] && wrap_z0_kv[3] !== (lag==0?ref_kv_word:hist_kv[lag-1])))wer_z0_kv[lag]=wer_z0_kv[lag]+1;
end
if(ref_l_ov)seen[2]=seen[2]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (p4_result_word[60] && p4_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_p4_result[lag]=err_p4_result[lag]+1;
if((wrap_p4_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_p4_result[3][60] && wrap_p4_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_p4_result[lag]=wer_p4_result[lag]+1;
if((z0_result_word[60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (z0_result_word[60] && z0_result_word !== (lag==0?ref_result_word:hist_result[lag-1])))err_z0_result[lag]=err_z0_result[lag]+1;
if((wrap_z0_result[3][60] !== ((lag==0?ref_result_word:hist_result[lag-1])>>60)) || (wrap_z0_result[3][60] && wrap_z0_result[3] !== (lag==0?ref_result_word:hist_result[lag-1])))wer_z0_result[lag]=wer_z0_result[lag]+1;
end
if(ref_retire)seen[3]=seen[3]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (p4_retire_word[1] && p4_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_p4_retire[lag]=err_p4_retire[lag]+1;
if((wrap_p4_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_p4_retire[3][1] && wrap_p4_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_p4_retire[lag]=wer_p4_retire[lag]+1;
if((z0_retire_word[1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (z0_retire_word[1] && z0_retire_word !== (lag==0?ref_retire_word:hist_retire[lag-1])))err_z0_retire[lag]=err_z0_retire[lag]+1;
if((wrap_z0_retire[3][1] !== ((lag==0?ref_retire_word:hist_retire[lag-1])>>1)) || (wrap_z0_retire[3][1] && wrap_z0_retire[3] !== (lag==0?ref_retire_word:hist_retire[lag-1])))wer_z0_retire[lag]=wer_z0_retire[lag]+1;
end
if(ref_l_fault)seen[4]=seen[4]+1;
for(lag=0;lag<17;lag=lag+1)begin
if((p4_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (p4_fault_word[1] && p4_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_p4_fault[lag]=err_p4_fault[lag]+1;
if((wrap_p4_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_p4_fault[3][1] && wrap_p4_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_p4_fault[lag]=wer_p4_fault[lag]+1;
if((z0_fault_word[1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (z0_fault_word[1] && z0_fault_word !== (lag==0?ref_fault_word:hist_fault[lag-1])))err_z0_fault[lag]=err_z0_fault[lag]+1;
if((wrap_z0_fault[3][1] !== ((lag==0?ref_fault_word:hist_fault[lag-1])>>1)) || (wrap_z0_fault[3][1] && wrap_z0_fault[3] !== (lag==0?ref_fault_word:hist_fault[lag-1])))wer_z0_fault[lag]=wer_z0_fault[lag]+1;
end
end
if(cycle>256 && p4_vm_word[56] && ref_vm_word[56] && p4_vm_word !== ref_vm_word && err_p4_vm[0]<4)$display("UNCHANGED_ML8_REQ4_COUNTEREXAMPLE cycle=%0d ref=%h got=%h ref_va=%h later_va=%h",cycle,ref_vm_word,p4_vm_word,va_q,p4_va_q);
if(cycle==2600)begin
$display("ML12_REQUEST_CHECK errors=%0d",req_errors);
$display("ML12_COUNT vm %0d",seen[0]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_vm[lag],wer_p4_vm[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE z0 vm lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_z0_vm[lag],wer_z0_vm[lag]);
$display("ML12_COUNT kv %0d",seen[1]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_kv[lag],wer_p4_kv[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE z0 kv lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_z0_kv[lag],wer_z0_kv[lag]);
$display("ML12_COUNT result %0d",seen[2]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_result[lag],wer_p4_result[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE z0 result lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_z0_result[lag],wer_z0_result[lag]);
$display("ML12_COUNT retire %0d",seen[3]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_retire[lag],wer_p4_retire[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE z0 retire lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_z0_retire[lag],wer_z0_retire[lag]);
$display("ML12_COUNT fault %0d",seen[4]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE p4 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_p4_fault[lag],wer_p4_fault[lag]);
for(lag=0;lag<17;lag=lag+1)$display("PHASE z0 fault lag=%0d raw_err=%0d wrapped_err=%0d",lag,err_z0_fault[lag],wer_z0_fault[lag]);
$finish;end
end
endmodule
