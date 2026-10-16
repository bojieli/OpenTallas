`timescale 1ns/1ps
// Q-ELEM-SUC 2026-10-16: PHYSICAL-BUILD-ONLY binding of the qfd_sp_su64_sfu lane children to their closed native views.
// With OT_SU_LANE_HARD, ot_hdc_vstream_lane_clock_entries_candidate instantiates ot_hdc_vstream_lane_h and
// ot_hdc_sfu_{exp,rcp,rsq}_t without parameter overrides; the closed views are qfd_su_lane_h_native_crom5
// (= ot_hdc_vstream_lane_h at its default WR16/AW24/NW18/KVFP8/ML15/RD2/QLA4/QLM5, rtl/physical/ot_qfd_su_lane_h_native_crom5.sv)
// and qfd_su_sfu_{exp,rcp,rsq}_native45 (= ot_hdc_sfu_*_t at LA4/LM5).  These thin wrappers map the module names to the
// view masters (Liberty / LEF cells in the parent route); a flattening synthesis leaves only the view instances.
// Explicit port connections (no .*): the view masters also carry VDD/VSS pg pins (gate yosys 'No matching wire
// for implicit port connection VSS', 2026-10-16); the supply pins stay unconnected in the netlist (PDN connects them).
// Never compile this file with rtl/hdc/ot_hdc_vstream_lane_t.sv or the native view RTL (recursive names): benches use
// the original RTL, which the native views are by construction.
`ifdef OT_SU_LANE_HARD
module ot_hdc_vstream_lane_h (
    input wire clk, rst_n, emit0, live, input wire [17:0] i, input wire [18:0] fin_th, input wire i_last_r,
    input wire [23:0] cura0, curb0, curc0, curd0, rrow, asi, bsi, csi, dsi,
    input wire asrc, bsrc, csrc, mc, md, redsq, input wire [1:0] ma, mb, dst, red, input wire [2:0] ad,
    input wire [31:0] imm1, imm2, input wire [2:0] cls, input wire accept, input wire [2:0] i_sfu,
    output wire va_re, output wire [23:0] va_addr, input wire [31:0] va_q,
    output wire vb_re, output wire [23:0] vb_addr, input wire [31:0] vb_q,
    output wire vc_re, output wire [23:0] vc_addr, input wire [31:0] vc_q,
    output wire wrom_re, output wire [23:0] wrom_addr, input wire [255:0] wrom_q,
    output wire crom_re, output wire [23:0] crom_addr, input wire [63:0] crom_q,
    output wire vm_we, output wire [23:0] vm_waddr, output wire [31:0] vm_wdata,
    output wire kv_we, output wire [23:0] kv_waddr, output wire [31:0] kv_wdata,
    output wire l_ov, output wire [31:0] l_out, output wire [1:0] l_red, output wire l_redsq, output wire [23:0] l_raddr,
    output wire l_last, retire, l_fault,
    output wire sx_exp_v, output wire [31:0] sx_exp_x, input wire [31:0] sy_exp_y, input wire sy_exp_vo, sy_exp_f,
    output wire sx_rcp_v, output wire [31:0] sx_rcp_x, input wire [31:0] sy_rcp_y, input wire sy_rcp_f,
    output wire sx_rsq_v, output wire [31:0] sx_rsq_x, input wire [31:0] sy_rsq_y, input wire sy_rsq_f);
    qfd_su_lane_h_native_crom5 u_n (.clk(clk),.rst_n(rst_n),.emit0(emit0),.live(live),.i(i),.fin_th(fin_th),
        .i_last_r(i_last_r),.cura0(cura0),.curb0(curb0),.curc0(curc0),.curd0(curd0),.rrow(rrow),.asi(asi),.bsi(bsi),
        .csi(csi),.dsi(dsi),.asrc(asrc),.bsrc(bsrc),.csrc(csrc),.mc(mc),.md(md),.redsq(redsq),.ma(ma),.mb(mb),
        .dst(dst),.red(red),.ad(ad),.imm1(imm1),.imm2(imm2),.cls(cls),.accept(accept),.i_sfu(i_sfu),.va_re(va_re),
        .va_addr(va_addr),.va_q(va_q),.vb_re(vb_re),.vb_addr(vb_addr),.vb_q(vb_q),.vc_re(vc_re),.vc_addr(vc_addr),
        .vc_q(vc_q),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.wrom_q(wrom_q),.crom_re(crom_re),.crom_addr(crom_addr),
        .crom_q(crom_q),.vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),.kv_we(kv_we),.kv_waddr(kv_waddr),
        .kv_wdata(kv_wdata),.l_ov(l_ov),.l_out(l_out),.l_red(l_red),.l_redsq(l_redsq),.l_raddr(l_raddr),
        .l_last(l_last),.retire(retire),.l_fault(l_fault),.sx_exp_v(sx_exp_v),.sx_exp_x(sx_exp_x),
        .sy_exp_y(sy_exp_y),.sy_exp_vo(sy_exp_vo),.sy_exp_f(sy_exp_f),.sx_rcp_v(sx_rcp_v),.sx_rcp_x(sx_rcp_x),
        .sy_rcp_y(sy_rcp_y),.sy_rcp_f(sy_rcp_f),.sx_rsq_v(sx_rsq_v),.sx_rsq_x(sx_rsq_x),.sy_rsq_y(sy_rsq_y),
        .sy_rsq_f(sy_rsq_f));
endmodule
module ot_hdc_sfu_exp_t (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo, fault);
    qfd_su_sfu_exp_native45 u_n (.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y),.vo(vo),.fault(fault));
endmodule
module ot_hdc_sfu_rcp_t (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo, fault);
    qfd_su_sfu_rcp_native45 u_n (.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y),.vo(vo),.fault(fault));
endmodule
module ot_hdc_sfu_rsq_t (input wire clk, rst_n, v, input wire [31:0] x, output wire [31:0] y, output wire vo, fault);
    qfd_su_sfu_rsq_native45 u_n (.clk(clk),.rst_n(rst_n),.v(v),.x(x),.y(y),.vo(vo),.fault(fault));
endmodule
`endif
