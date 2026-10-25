`timescale 1ns/1ps
module tb_s8_memalign;
`ifdef OT_MIF_HEAD_MUTANT
localparam MIF_HEAD_EXTRA=0;
`else
localparam MIF_HEAD_EXTRA=1;
`endif
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
reg [31:0] sy_exp_y=0;
reg  sy_exp_vo=0;
reg  sy_exp_f=0;
wire  ref_sx_rcp_v, new_sx_rcp_v;
wire [31:0] ref_sx_rcp_x, new_sx_rcp_x;
reg [31:0] sy_rcp_y=0;
reg  sy_rcp_f=0;
wire  ref_sx_rsq_v, new_sx_rsq_v;
wire [31:0] ref_sx_rsq_x, new_sx_rsq_x;
reg [31:0] sy_rsq_y=0;
reg  sy_rsq_f=0;
reg [31:0] vd[0:2], bd[0:2], cd[0:2];
reg [63:0] crd[0:3]; reg [255:0] wrd[0:2];
reg[31:0] va1,vb1,vc1;
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
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(MIF_HEAD_EXTRA)) u_new (.clk(clk),
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
.va_q(va1),
.vb_re(new_vb_re),
.vb_addr(new_vb_addr),
.vb_q(vb1),
.vc_re(new_vc_re),
.vc_addr(new_vc_addr),
.vc_q(vc1),
.wrom_re(new_wrom_re),
.wrom_addr(new_wrom_addr),
.wrom_q(wrd[2]),
.crom_re(new_crom_re),
.crom_addr(new_crom_addr),
.crom_q(crd[3]),
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
.sy_exp_y(sy_exp_y),
.sy_exp_vo(sy_exp_vo),
.sy_exp_f(sy_exp_f),
.sx_rcp_v(new_sx_rcp_v),
.sx_rcp_x(new_sx_rcp_x),
.sy_rcp_y(sy_rcp_y),
.sy_rcp_f(sy_rcp_f),
.sx_rsq_v(new_sx_rsq_v),
.sx_rsq_x(new_sx_rsq_x),
.sy_rsq_y(sy_rsq_y),
.sy_rsq_f(sy_rsq_f));
reg [87:0] op_history[0:3];
wire [87:0] ref_op={ref_vm_we,ref_kv_we,ref_l_ov,ref_retire,ref_l_last,ref_vm_waddr,ref_vm_wdata,ref_l_red,ref_l_redsq,ref_l_raddr};
wire [87:0] new_op={new_vm_we,new_kv_we,new_l_ov,new_retire,new_l_last,new_vm_waddr,new_vm_wdata,new_l_red,new_l_redsq,new_l_raddr};
integer cycle=0,checked=0,mismatch=0,valid_outputs=0;
always @(posedge clk) begin
  crd[0]<=crom_q;crd[1]<=crd[0];crd[2]<=crd[1];crd[3]<=crd[2];wrd[0]<=wrom_q;wrd[1]<=wrd[0];wrd[2]<=wrd[1];va1<=va_q;vb1<=vb_q;vc1<=vc_q;
  op_history[0]<=ref_op;op_history[1]<=op_history[0];op_history[2]<=op_history[1];op_history[3]<=op_history[2];
end
always @(negedge clk) begin
 cycle=cycle+1;
 rst_n=(cycle>8);
 // Long guards between bursts keep class-switch reset epochs outside the arithmetic windows.
 live=(cycle>128 && cycle%256<32);emit0=live;i=cycle%256;i_last_r=(i==31);fin_th=32;
 cura0=0;curb0=0;curc0=0;curd0=0;rrow=32;asi=1;bsi=1;csi=1;dsi=1;
 asrc=(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=1;md=(cycle/512)%2;
 red=0;dst=0;ad=0;ma=0;mb=0;cls=0;accept=0;redsq=0;imm1=32'h3f800000;imm2=0;
 va_q=32'h3f000000 | ((cycle*131)&23'h7fffff);vb_q=32'h3f400000 | ((cycle*173)&23'h3fffff);
 vc_q=32'h3f000000 | ((cycle*197)&23'h7fffff);
 crom_q={32'h3f000000 | ((cycle*199)&23'h7fffff),32'h3f000000 | ((cycle*211)&23'h7fffff)};
 wrom_q={16{16'h3f80 | (16'(cycle)&16'h003f)}};
 if(cycle>128)begin
  checked=checked+1;
  // Valid/retire signals always compare; payload compares only on a real output.
  if(new_vm_we!==op_history[3][87] || new_kv_we!==op_history[3][86] || new_l_ov!==op_history[3][85] || new_retire!==op_history[3][84])begin
   mismatch=mismatch+1;if(mismatch<6)$display("ALIGN valid mismatch cycle%0d ref%h got%h",cycle,op_history[3],new_op);
  end
  if(new_vm_we || new_l_ov)begin
   valid_outputs=valid_outputs+1;
   if(new_op!==op_history[3])begin mismatch=mismatch+1;if(mismatch<6)$display("ALIGN data mismatch cycle%0d ref%h got%h",cycle,op_history[3],new_op);end
  end
 end
 if(cycle==2400)begin
  $display("MIF_HEAD checked=%0d outputs=%0d mismatches=%0d",checked,valid_outputs,mismatch);
  if(mismatch==0 && valid_outputs>100)$display("MIF_HEAD PASS");else $display("MIF_HEAD FAIL");
  $finish;
 end
end
endmodule
