`timescale 1ns/1ps
// qfd_dv_s5_xhead2: QW-SLICE7-LEAVES successor master of qfd_dv_s5_xhead (claude/qw-slice6-heads-1019 f4746778a).  Same ports
// and values; the body is the bounded constructor netlist qfd_dv_s5_xhead_bounded (tools/qwen_dv/bound_math_netlist.py
// --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb --fuse-ao) of qfd_dv_s5_xhead_rt
// (the retag moved in front of the n_q / s_q output registers: every output pin leaves a flop, 0 edges).  Recipe:
// rtl/test/qwen_dv/s5/xhead7/{prepare,native,bench}.sh, evidence results/arch/qw_slice7_1020/xhead.
module qfd_dv_s5_xhead2 (
    input  wire           ck,
    input  wire           rst_n,
    input  wire [5:0]     cid,
    input  wire           fault_i,
    input  wire [1186:0]  a_f,
    input  wire [379:0]   a_ib,
    output wire [515:0]   n_d,
    output wire [515:0]   s_d,
    output wire           w0_v, w0_ep, c0_v, c0_ep, w1_v, w1_ep, c1_v, c1_ep,
    output wire [5:0]     w0_off, w1_off,
    output wire [63:0]    w0_m, w1_m,
    output wire [1023:0]  w0_d, w1_d,
    output wire [71:0]    w0_ctl, w1_ctl,
    output wire [3:0]     r0_v, r0_t, r0_ep, r1_v, r1_t, r1_ep,
    output wire [111:0]   r0_p, r1_p,
    input  wire [255:0]   q0, q1,
    input  wire [3:0]     q0_v, q1_v,
    input  wire [3:0]     q0_bad, q1_bad,
    output wire           l_rst_n,
    output wire           fault
);
    qfd_dv_s5_xhead_bounded u_xh (.ck(ck),.rst_n(rst_n),.cid(cid),.fault_i(fault_i),.a_f(a_f),.a_ib(a_ib),.n_d(n_d),.s_d(s_d),.w0_v(w0_v),.w0_ep(w0_ep),.c0_v(c0_v),.c0_ep(c0_ep),.w1_v(w1_v),.w1_ep(w1_ep),.c1_v(c1_v),.c1_ep(c1_ep),.w0_off(w0_off),.w1_off(w1_off),.w0_m(w0_m),.w1_m(w1_m),.w0_d(w0_d),.w1_d(w1_d),.w0_ctl(w0_ctl),.w1_ctl(w1_ctl),.r0_v(r0_v),.r0_t(r0_t),.r0_ep(r0_ep),.r1_v(r1_v),.r1_t(r1_t),.r1_ep(r1_ep),.r0_p(r0_p),.r1_p(r1_p),.q0(q0),.q1(q1),.q0_v(q0_v),.q1_v(q1_v),.q0_bad(q0_bad),.q1_bad(q1_bad),.l_rst_n(l_rst_n),.fault(fault));
endmodule
