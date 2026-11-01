`timescale 1ns/1ps
module tb_kvpipe;
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
reg [63:0] crd[0:2]; reg [255:0] wrd[0:1];
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .KV_WR_PIPE(0)) u_ref (.clk(clk),
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
.wrom_q(wrd[1]),
.crom_re(ref_crom_re),
.crom_addr(ref_crom_addr),
.crom_q(crd[2]),
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
qfd_dv_lane_h_safe2 #(.MEMORY_ALIGNMENT(3), .KV_WR_PIPE(1)) u_new (.clk(clk),
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
wire [4095:0] ref_all = {ref_crom_addr,ref_crom_re,ref_kv_waddr,ref_kv_wdata,ref_kv_we,ref_l_fault,ref_l_last,ref_l_out,ref_l_ov,ref_l_raddr,ref_l_red,ref_l_redsq,ref_retire,ref_sx_exp_v,ref_sx_exp_x,ref_sx_rcp_v,ref_sx_rcp_x,ref_sx_rsq_v,ref_sx_rsq_x,ref_va_addr,ref_va_re,ref_vb_addr,ref_vb_re,ref_vc_addr,ref_vc_re,ref_vm_waddr,ref_vm_wdata,ref_vm_we,ref_wrom_addr,ref_wrom_re};
wire [4095:0] new_all = {new_crom_addr,new_crom_re,new_kv_waddr,new_kv_wdata,new_kv_we,new_l_fault,new_l_last,new_l_out,new_l_ov,new_l_raddr,new_l_red,new_l_redsq,new_retire,new_sx_exp_v,new_sx_exp_x,new_sx_rcp_v,new_sx_rcp_x,new_sx_rsq_v,new_sx_rsq_x,new_va_addr,new_va_re,new_vb_addr,new_vb_re,new_vc_addr,new_vc_re,new_vm_waddr,new_vm_wdata,new_vm_we,new_wrom_addr,new_wrom_re};
integer cycle=0,checked=0,mismatch=0,kvw=0,kvz=0,kvsub=0,kvsat=0,kvnorm=0;
reg [31:0] rnd;
always @(posedge clk) begin crd[0]<=crom_q;crd[1]<=crd[0];crd[2]<=crd[1];wrd[0]<=wrom_q;wrd[1]<=wrd[0]; end
function automatic [31:0] rf(input [31:0] r, input [31:0] c);  // random fp32 around the fp8 subnormal..saturation range
  rf = {r[31], 8'(8'd100 + (r[29:24] % 6'd50)), r[22:0] ^ c[22:0]};
endfunction
always @(negedge clk) begin
 cycle=cycle+1;
 rst_n=(cycle>8);
 live=(cycle>128 && cycle%256<32);emit0=live;i=cycle%256;i_last_r=(i==31);fin_th=32;
 cura0=0;curb0=0;curc0=0;curd0=0;rrow=32;asi=1;bsi=1;csi=1;dsi=1;
 asrc=(cycle/768)%2;bsrc=(cycle/256)%2;csrc=!bsrc;mc=1;md=(cycle/512)%2;
 red=0;dst=(cycle/256)%3==2 ? 2'd1 : 2'd2;ad=0;ma=0;mb=0;cls=0;accept=0;redsq=0;imm1=32'h3f800000;imm2=0;
 rnd=$random; va_q=rf(rnd, cycle*131); rnd=$random; vb_q=rf(rnd, cycle*173); rnd=$random; vc_q=rf(rnd, cycle*197);
 crom_q={$random,$random};
 wrom_q={16{16'h3f80 | (16'(cycle)&16'h003f)}};
 if(cycle>8)begin
  checked=checked+1;
  if(new_all!==ref_all)begin mismatch=mismatch+1;if(mismatch<6)$display("KVPIPE mismatch cycle%0d kv ref %b %h %h new %b %h %h",cycle,ref_kv_we,ref_kv_waddr,ref_kv_wdata,new_kv_we,new_kv_waddr,new_kv_wdata);end
  if(ref_kv_we)begin kvw=kvw+1;
   if(ref_kv_wdata[30:0]==0) kvz=kvz+1; else if(ref_kv_wdata[30:23]==8'd135 && ref_kv_wdata[22:20]==3'b110) kvsat=kvsat+1;
   else if(ref_kv_wdata[30:23]<=8'd121) kvsub=kvsub+1; else kvnorm=kvnorm+1; end
 end
 if(cycle==40000)begin
  $display("KVPIPE checked=%0d kv_writes=%0d (zero %0d sub/min %0d sat %0d normal %0d) mismatches=%0d outputs_compared=%0d bits",checked,kvw,kvz,kvsub,kvsat,kvnorm,mismatch,$bits(ref_all));
  if(mismatch==0 && kvw>1000)$display("KVPIPE PASS");else $display("KVPIPE FAIL");
  $finish;
 end
end
endmodule
