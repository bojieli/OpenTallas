`timescale 1ns/1ps
module tb_s8_memalign_sfu;
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
wire  ref_va_re, new_va_re;
wire [23:0] ref_va_addr, new_va_addr;
reg [31:0] va_q=0;
wire  ref_vb_re, new_vb_re;
wire [23:0] ref_vb_addr, new_vb_addr;
reg [31:0] vb_q=0;
wire  ref_vc_re, new_vc_re;
wire [23:0] ref_vc_addr, new_vc_addr;
reg [31:0] vc_q=0;
wire  ref_wrom_re, new_wrom_re;
wire [23:0] ref_wrom_addr, new_wrom_addr;
reg [255:0] wrom_q=0;
wire  ref_crom_re, new_crom_re;
wire [23:0] ref_crom_addr, new_crom_addr;
reg [63:0] crom_q=0;
wire  ref_vm_we, new_vm_we;
wire [23:0] ref_vm_waddr, new_vm_waddr;
wire [31:0] ref_vm_wdata, new_vm_wdata;
wire  ref_kv_we, new_kv_we;
wire [23:0] ref_kv_waddr, new_kv_waddr;
wire [31:0] ref_kv_wdata, new_kv_wdata;
wire  ref_l_ov, new_l_ov;
wire [31:0] ref_l_out, new_l_out;
wire [1:0] ref_l_red, new_l_red;
wire  ref_l_redsq, new_l_redsq;
wire [23:0] ref_l_raddr, new_l_raddr;
wire  ref_l_last, new_l_last;
wire  ref_retire, new_retire;
wire  ref_l_fault, new_l_fault;
wire  ref_sx_exp_v, new_sx_exp_v;
wire [31:0] ref_sx_exp_x, new_sx_exp_x;
wire  ref_sx_rcp_v, new_sx_rcp_v;
wire [31:0] ref_sx_rcp_x, new_sx_rcp_x;
wire  ref_sx_rsq_v, new_sx_rsq_v;
wire [31:0] ref_sx_rsq_x, new_sx_rsq_x;
reg [31:0] vd[0:2], bd[0:2], cd[0:2];
reg [63:0] crd[0:2]; reg [255:0] wrd[0:1];
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(0)) u_ref (.clk(clk),
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
.sy_exp_y(ref_sy_exp_y),
.sy_exp_vo(ref_sy_exp_vo),
.sy_exp_f(ref_sy_exp_f),
.sx_rcp_v(ref_sx_rcp_v),
.sx_rcp_x(ref_sx_rcp_x),
.sy_rcp_y(ref_sy_rcp_y),
.sy_rcp_f(ref_sy_rcp_f),
.sx_rsq_v(ref_sx_rsq_v),
.sx_rsq_x(ref_sx_rsq_x),
.sy_rsq_y(ref_sy_rsq_y),
.sy_rsq_f(ref_sy_rsq_f));
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3)) u_new (.clk(clk),
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
.va_re(new_va_re),
.va_addr(new_va_addr),
.va_q(va_q),
.vb_re(new_vb_re),
.vb_addr(new_vb_addr),
.vb_q(vb_q),
.vc_re(new_vc_re),
.vc_addr(new_vc_addr),
.vc_q(vc_q),
.wrom_re(new_wrom_re),
.wrom_addr(new_wrom_addr),
.wrom_q(wrd[1]),
.crom_re(new_crom_re),
.crom_addr(new_crom_addr),
.crom_q(crd[2]),
.vm_we(new_vm_we),
.vm_waddr(new_vm_waddr),
.vm_wdata(new_vm_wdata),
.kv_we(new_kv_we),
.kv_waddr(new_kv_waddr),
.kv_wdata(new_kv_wdata),
.l_ov(new_l_ov),
.l_out(new_l_out),
.l_red(new_l_red),
.l_redsq(new_l_redsq),
.l_raddr(new_l_raddr),
.l_last(new_l_last),
.retire(new_retire),
.l_fault(new_l_fault),
.sx_exp_v(new_sx_exp_v),
.sx_exp_x(new_sx_exp_x),
.sy_exp_y(new_sy_exp_y),
.sy_exp_vo(new_sy_exp_vo),
.sy_exp_f(new_sy_exp_f),
.sx_rcp_v(new_sx_rcp_v),
.sx_rcp_x(new_sx_rcp_x),
.sy_rcp_y(new_sy_rcp_y),
.sy_rcp_f(new_sy_rcp_f),
.sx_rsq_v(new_sx_rsq_v),
.sx_rsq_x(new_sx_rsq_x),
.sy_rsq_y(new_sy_rsq_y),
.sy_rsq_f(new_sy_rsq_f));
wire [31:0] ref_sy_exp_y; wire ref_sy_exp_vo, ref_sy_exp_f;
ot_hdc_sfu_exp_t u_ref_exp (.clk(clk),.rst_n(rst_n),.v(ref_sx_exp_v),.x(ref_sx_exp_x),.y(ref_sy_exp_y),.vo(ref_sy_exp_vo),.fault(ref_sy_exp_f));
wire [31:0] ref_sy_rcp_y; wire ref_sy_rcp_vo, ref_sy_rcp_f;
ot_hdc_sfu_rcp_t u_ref_rcp (.clk(clk),.rst_n(rst_n),.v(ref_sx_rcp_v),.x(ref_sx_rcp_x),.y(ref_sy_rcp_y),.vo(ref_sy_rcp_vo),.fault(ref_sy_rcp_f));
wire [31:0] ref_sy_rsq_y; wire ref_sy_rsq_vo, ref_sy_rsq_f;
ot_hdc_sfu_rsq_t u_ref_rsq (.clk(clk),.rst_n(rst_n),.v(ref_sx_rsq_v),.x(ref_sx_rsq_x),.y(ref_sy_rsq_y),.vo(ref_sy_rsq_vo),.fault(ref_sy_rsq_f));
wire [31:0] new_sy_exp_y; wire new_sy_exp_vo, new_sy_exp_f;
ot_hdc_sfu_exp_t u_new_exp (.clk(clk),.rst_n(rst_n),.v(new_sx_exp_v),.x(new_sx_exp_x),.y(new_sy_exp_y),.vo(new_sy_exp_vo),.fault(new_sy_exp_f));
wire [31:0] new_sy_rcp_y; wire new_sy_rcp_vo, new_sy_rcp_f;
ot_hdc_sfu_rcp_t u_new_rcp (.clk(clk),.rst_n(rst_n),.v(new_sx_rcp_v),.x(new_sx_rcp_x),.y(new_sy_rcp_y),.vo(new_sy_rcp_vo),.fault(new_sy_rcp_f));
wire [31:0] new_sy_rsq_y; wire new_sy_rsq_vo, new_sy_rsq_f;
ot_hdc_sfu_rsq_t u_new_rsq (.clk(clk),.rst_n(rst_n),.v(new_sx_rsq_v),.x(new_sx_rsq_x),.y(new_sy_rsq_y),.vo(new_sy_rsq_vo),.fault(new_sy_rsq_f));
reg [88:0] op_history[0:2];
wire [88:0] ref_op={ref_l_fault,ref_vm_we,ref_kv_we,ref_l_ov,ref_retire,ref_l_last,ref_vm_waddr,ref_vm_wdata,ref_l_red,ref_l_redsq,ref_l_raddr};
wire [88:0] new_op={new_l_fault,new_vm_we,new_kv_we,new_l_ov,new_retire,new_l_last,new_vm_waddr,new_vm_wdata,new_l_red,new_l_redsq,new_l_raddr};
wire [98:0] ref_sf={ref_sx_exp_v,ref_sx_exp_x,ref_sx_rcp_v,ref_sx_rcp_x,ref_sx_rsq_v,ref_sx_rsq_x};
wire [98:0] new_sf={new_sx_exp_v,new_sx_exp_x,new_sx_rcp_v,new_sx_rcp_x,new_sx_rsq_v,new_sx_rsq_x};
reg [98:0] sf_history[0:2];
integer cycle=0,checked=0,mismatch=0,valid_outputs=0,ph,step,new_class,which;
integer counts[0:4]; integer exp_requests=0,rcp_requests=0,rsq_requests=0;
initial for(integer z=0;z<5;z=z+1)counts[z]=0;
always @(posedge clk) begin
  crd[0]<=crom_q;crd[1]<=crd[0];crd[2]<=crd[1];wrd[0]<=wrom_q;wrd[1]<=wrd[0];
  op_history[0]<=ref_op;op_history[1]<=op_history[0];op_history[2]<=op_history[1];
  sf_history[0]<=ref_sf;sf_history[1]<=sf_history[0];sf_history[2]<=sf_history[1];
end
always @(negedge clk) begin
 cycle=cycle+1;rst_n=(cycle>8);
 ph=(cycle-64)/640;step=(cycle-64)%640;
 case(ph)
 0,5:new_class=0;
 1,9:new_class=1;
 2,8:new_class=2;
 3,7:new_class=3;
 default:new_class=4;
 endcase
 // accept presents the next class while cls still identifies the old class.
 // Update cls only one idle edge later. Guard192 exceeds TAPMAX136; drain416
 // exceeds the full SIGM path before every subsequent class transition.
 accept=(cycle>=64 && step==0);i_sfu=new_class;
 if(cycle>=64 && step>=1)cls=new_class;
 live=(cycle>=64 && ph<10 && step>=192 && step<224);emit0=live;
 i=live?(step-192):0;i_last_r=live && i==31;fin_th=32;
 cura0=0;curb0=0;curc0=0;curd0=256*ph;rrow=32+64*ph;asi=1;bsi=1;csi=1;dsi=1;
 asrc=ph%2;bsrc=(ph/2)%2;csrc=!bsrc;mc=1;md=(ph/3)%2;
 red=0;dst=0;ad=0;ma=0;mb=0;redsq=0;imm1=32'h3f800000;imm2=0;
 va_q=32'h3f000000 | ((cycle*131)&23'h7fffff);vb_q=32'h3f400000 | ((cycle*173)&23'h3fffff);
 vc_q=32'h3f000000 | ((cycle*197)&23'h7fffff);
 crom_q={32'h3f000000 | ((cycle*199)&23'h7fffff),32'h3f000000 | ((cycle*211)&23'h7fffff)};
 wrom_q={16{16'h3f80 | (16'(cycle)&16'h003f)}};
 if(cycle>128)begin
  checked=checked+1;
  if(new_vm_we!==op_history[2][87] || new_kv_we!==op_history[2][86] || new_l_ov!==op_history[2][85] || new_retire!==op_history[2][84])begin
   mismatch=mismatch+1;if(mismatch<8)$display("ALIGN valid mismatch cycle%0d cls%0d ref%h got%h",cycle,cls,op_history[2],new_op);
  end
  if(new_vm_we || new_l_ov)begin
   valid_outputs=valid_outputs+1;counts[cls]=counts[cls]+1;
   if(new_op!==op_history[2] || new_l_fault || op_history[2][88])begin
    mismatch=mismatch+1;if(mismatch<8)$display("ALIGN data/fault mismatch cycle%0d cls%0d ref%h got%h",cycle,cls,op_history[2],new_op);
   end
  end
  if(new_sx_exp_v!==sf_history[2][98] || new_sx_rcp_v!==sf_history[2][65] || new_sx_rsq_v!==sf_history[2][32] ||
      (new_sx_exp_v && new_sx_exp_x!==sf_history[2][97:66]) ||
      (new_sx_rcp_v && new_sx_rcp_x!==sf_history[2][64:33]) ||
      (new_sx_rsq_v && new_sx_rsq_x!==sf_history[2][31:0]))begin
   mismatch=mismatch+1;if(mismatch<8)$display("ALIGN SFU request mismatch cycle%0d cls%0d ref%h got%h",cycle,cls,sf_history[2],new_sf);
  end
  if(new_sx_exp_v)exp_requests=exp_requests+1;
  if(new_sx_rcp_v)rcp_requests=rcp_requests+1;
  if(new_sx_rsq_v)rsq_requests=rsq_requests+1;
 end
 if(cycle==6464)begin
  $display("S8_MEMALIGN_SFU checked=%0d outputs=%0d mismatches=%0d cls_counts=%0d,%0d,%0d,%0d,%0d requests=%0d,%0d,%0d",checked,valid_outputs,mismatch,counts[0],counts[1],counts[2],counts[3],counts[4],exp_requests,rcp_requests,rsq_requests);
  if(mismatch==0 && valid_outputs==320 && counts[0]==64 && counts[1]==64 && counts[2]==64 && counts[3]==64 && counts[4]==64 && exp_requests==128 && rcp_requests==128 && rsq_requests==64)$display("S8_MEMALIGN_SFU PASS");else $display("S8_MEMALIGN_SFU FAIL");
  $finish;
 end
end
endmodule
