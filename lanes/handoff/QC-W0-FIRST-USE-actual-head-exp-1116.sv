`timescale 1ns/1ps
module tb;
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
wire  va_re;
wire [23:0] va_addr;
reg [31:0] va_q=0;
wire  vb_re;
wire [23:0] vb_addr;
reg [31:0] vb_q=0;
wire  vc_re;
wire [23:0] vc_addr;
reg [31:0] vc_q=0;
wire  wrom_re;
wire [23:0] wrom_addr;
reg [255:0] wrom_q=0;
wire  crom_re;
wire [23:0] crom_addr;
reg [63:0] crom_q=0;
wire  vm_we;
wire [23:0] vm_waddr;
wire [31:0] vm_wdata;
wire  kv_we;
wire [23:0] kv_waddr;
wire [31:0] kv_wdata;
wire  l_ov;
wire [31:0] l_out;
wire [1:0] l_red;
wire  l_redsq;
wire [23:0] l_raddr;
wire  l_last;
wire  retire;
wire  l_fault;
wire  sx_exp_v;
wire [31:0] sx_exp_x;
reg [31:0] sy_exp_y=0;
reg  sy_exp_vo=0;
reg  sy_exp_f=0;
wire  sx_rcp_v;
wire [31:0] sx_rcp_x;
reg [31:0] sy_rcp_y=0;
reg  sy_rcp_f=0;
wire  sx_rsq_v;
wire [31:0] sx_rsq_x;
reg [31:0] sy_rsq_y=0;
reg  sy_rsq_f=0;
wire [31:0] exp_y; wire exp_vo,exp_fault;
ot_hdc_sfu_exp_t dut_exp(.clk(clk),.rst_n(rst_n),.v(sx_exp_v),.x(sx_exp_x),.y(exp_y),.vo(exp_vo),.fault(exp_fault));
qfd_dv_lane_h_su_mem9 #(.MEMORY_ALIGNMENT(3),.MEMORY_READ_EXTRA(44),.KV_WR_PIPE(1),.SEGMENTED_MEMORY_DELAY(1)) dut_head(.clk(clk),.rst_n(rst_n),.emit0(emit0),.live(live),.i(i),.fin_th(fin_th),.i_last_r(i_last_r),.cura0(cura0),.curb0(curb0),.curc0(curc0),.curd0(curd0),.rrow(rrow),.asi(asi),.bsi(bsi),.csi(csi),.dsi(dsi),.asrc(asrc),.bsrc(bsrc),.csrc(csrc),.mc(mc),.md(md),.redsq(redsq),.ma(ma),.mb(mb),.dst(dst),.red(red),.ad(ad),.imm1(imm1),.imm2(imm2),.cls(cls),.accept(accept),.i_sfu(i_sfu),.va_re(va_re),.va_addr(va_addr),.va_q(va_q),.vb_re(vb_re),.vb_addr(vb_addr),.vb_q(vb_q),.vc_re(vc_re),.vc_addr(vc_addr),.vc_q(vc_q),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.wrom_q(wrom_q),.crom_re(crom_re),.crom_addr(crom_addr),.crom_q(crom_q),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.l_ov(l_ov),.l_out(l_out),.l_red(l_red),.l_redsq(l_redsq),.l_raddr(l_raddr),.l_last(l_last),.retire(retire),.l_fault(l_fault),.sx_exp_v(sx_exp_v),.sx_exp_x(sx_exp_x),.sy_exp_y(exp_y),.sy_exp_vo(exp_vo),.sy_exp_f(exp_fault),.sx_rcp_v(sx_rcp_v),.sx_rcp_x(sx_rcp_x),.sy_rcp_y(sy_rcp_y),.sy_rcp_f(sy_rcp_f),.sx_rsq_v(sx_rsq_v),.sx_rsq_x(sx_rsq_x),.sy_rsq_y(sy_rsq_y),.sy_rsq_f(sy_rsq_f));
integer cycle=0,epoch=0,reset_edges=0,accepted=0,sent=0,consumed=0,outputs=0,retired=0;
integer first_pin_accept=-1,first_captured_accept=-1;
integer first_accept=-1,first_exp=-1,first_consumer=-1,first_output=-1;
reg observing=0;
always @(posedge clk) begin
 cycle=cycle+1;
 if (!rst_n) reset_edges=reset_edges+1;
 if(observing) begin
  if(accept && first_pin_accept<0)first_pin_accept=cycle;
  if(dut_head.u_h.q_accept && first_captured_accept<0)first_captured_accept=cycle;
  if (dut_head.u_h.u_lane.e_v) begin accepted=accepted+1; if(first_accept<0)first_accept=cycle; end
  if (sx_exp_v) begin sent=sent+1;if(first_exp<0)first_exp=cycle; end
  if (dut_exp.u_exp.vd[dut_exp.u_exp.T_R1]) begin
    consumed=consumed+1;if(first_consumer<0)first_consumer=cycle;
    if(dut_exp.u_exp.lo_d[30] !== 1'b0) $fatal(1,"UNSAFE consumer bit30 cycle=%0d",cycle);
  end
  if(exp_vo)begin outputs=outputs+1;if(first_output<0)first_output=cycle;
    if(exp_y !== 32'h3f800000 || exp_fault !== 0) $fatal(1,"WRONG valid exp y=%h fault=%b",exp_y,exp_fault);
  end
  if(retire)retired=retired+1;
 end
end
task run_epoch(input integer which);
 integer k;
 begin
  epoch=which;observing=0;rst_n=0;emit0=0;live=0;accept=0;reset_edges=0;
  // Deliberately poison the exact failing state before cold/warm held reset.
  dut_exp.u_exp.a_lo[30]=1'b1;dut_exp.u_exp.d_lo.g_line.line[126]=1'b1;
  repeat(64)@(negedge clk);
  if(dut_exp.u_exp.lo_d[30] !== 0)$fatal(1,"heldreset didnotflush");
  $display("RESET epoch=%0d heldedges=%0d a_lo30=%b d_lo126=%b rt=%b",which,reset_edges,dut_exp.u_exp.a_lo[30],dut_exp.u_exp.d_lo.g_line.line[126],dut_exp.rt);
  accepted=0;sent=0;consumed=0;outputs=0;retired=0;first_pin_accept=-1;first_captured_accept=-1;first_accept=-1;first_exp=-1;first_consumer=-1;first_output=-1;
  rst_n=1;observing=1;live=1;accept=1;emit0=1;
  // Earliest externally supplied stream begins immediately on reset release.
  repeat(12)@(negedge clk);emit0=0;accept=0;
  repeat(250)@(negedge clk);
  if(accepted==0 || sent==0 || consumed!=sent || outputs!=sent)$fatal(1,"NO/TRUNCATED stream a=%0d s=%0d c=%0d o=%0d",accepted,sent,consumed,outputs);
  $display("ACCEPT_AUTHORITY epoch=%0d pin_accept=%0d captured_accept=%0d real_head_issue=%0d actual_exp_consumer=%0d",which,first_pin_accept,first_captured_accept,first_accept,first_consumer);
  $display("FIRST_USE epoch=%0d first_head_emit=%0d first_exp_send=%0d first_exp_consumer=%0d first_valid_output=%0d accepted=%0d sent=%0d consumer=%0d outputs=%0d retired=%0d",which,first_accept,first_exp,first_consumer,first_output,accepted,sent,consumed,outputs,retired);
 end
endtask
initial begin
 cls=1;i_sfu=1;ma=0;mb=0;ad=0;va_q=0;vb_q=0;vc_q=0;fin_th=1;i_last_r=1;
 run_epoch(0);run_epoch(1);$display("FIRST_USE_PASS cold+warm actualheadMEM44+actualEXP noaddedboot");$finish;
end
endmodule
