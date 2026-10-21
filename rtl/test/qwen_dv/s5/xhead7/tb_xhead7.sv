`timescale 1ns/1ps
module tb_xhead7;
reg ck=0; always #5 ck=~ck;
integer cycle,failures=0,compares=0,mutate,sparse;
reg [0:0] rst_n;
reg [5:0] cid;
reg [0:0] fault_i;
reg [1186:0] a_f;
reg [379:0] a_ib;
wire [515:0] n_d_ref, n_d_dut, n_d_mut;
wire [515:0] s_d_ref, s_d_dut, s_d_mut;
wire [0:0] w0_v_ref, w0_v_dut, w0_v_mut;
wire [0:0] w0_ep_ref, w0_ep_dut, w0_ep_mut;
wire [0:0] c0_v_ref, c0_v_dut, c0_v_mut;
wire [0:0] c0_ep_ref, c0_ep_dut, c0_ep_mut;
wire [0:0] w1_v_ref, w1_v_dut, w1_v_mut;
wire [0:0] w1_ep_ref, w1_ep_dut, w1_ep_mut;
wire [0:0] c1_v_ref, c1_v_dut, c1_v_mut;
wire [0:0] c1_ep_ref, c1_ep_dut, c1_ep_mut;
wire [5:0] w0_off_ref, w0_off_dut, w0_off_mut;
wire [5:0] w1_off_ref, w1_off_dut, w1_off_mut;
wire [63:0] w0_m_ref, w0_m_dut, w0_m_mut;
wire [63:0] w1_m_ref, w1_m_dut, w1_m_mut;
wire [1023:0] w0_d_ref, w0_d_dut, w0_d_mut;
wire [1023:0] w1_d_ref, w1_d_dut, w1_d_mut;
wire [71:0] w0_ctl_ref, w0_ctl_dut, w0_ctl_mut;
wire [71:0] w1_ctl_ref, w1_ctl_dut, w1_ctl_mut;
wire [3:0] r0_v_ref, r0_v_dut, r0_v_mut;
wire [3:0] r0_t_ref, r0_t_dut, r0_t_mut;
wire [3:0] r0_ep_ref, r0_ep_dut, r0_ep_mut;
wire [3:0] r1_v_ref, r1_v_dut, r1_v_mut;
wire [3:0] r1_t_ref, r1_t_dut, r1_t_mut;
wire [3:0] r1_ep_ref, r1_ep_dut, r1_ep_mut;
wire [111:0] r0_p_ref, r0_p_dut, r0_p_mut;
wire [111:0] r1_p_ref, r1_p_dut, r1_p_mut;
reg [255:0] q0;
reg [255:0] q1;
reg [3:0] q0_v;
reg [3:0] q1_v;
reg [3:0] q0_bad;
reg [3:0] q1_bad;
wire [0:0] l_rst_n_ref, l_rst_n_dut, l_rst_n_mut;
wire [0:0] fault_ref, fault_dut, fault_mut;
reg [1186:0] a_f_d1; reg [379:0] a_ib_d1; reg rst_ref;
always @(posedge ck) begin a_f_d1 <= a_f; a_ib_d1 <= a_ib; rst_ref <= rst_n; end
qfd_dv_s5_xhead u_ref(.ck(ck),.rst_n(rst_ref),.cid(cid),.fault_i(fault_i),.a_f(a_f_d1),.a_ib(a_ib_d1),.n_d(n_d_ref),.s_d(s_d_ref),.w0_v(w0_v_ref),.w0_ep(w0_ep_ref),.c0_v(c0_v_ref),.c0_ep(c0_ep_ref),.w1_v(w1_v_ref),.w1_ep(w1_ep_ref),.c1_v(c1_v_ref),.c1_ep(c1_ep_ref),.w0_off(w0_off_ref),.w1_off(w1_off_ref),.w0_m(w0_m_ref),.w1_m(w1_m_ref),.w0_d(w0_d_ref),.w1_d(w1_d_ref),.w0_ctl(w0_ctl_ref),.w1_ctl(w1_ctl_ref),.r0_v(r0_v_ref),.r0_t(r0_t_ref),.r0_ep(r0_ep_ref),.r1_v(r1_v_ref),.r1_t(r1_t_ref),.r1_ep(r1_ep_ref),.r0_p(r0_p_ref),.r1_p(r1_p_ref),.q0(q0),.q1(q1),.q0_v(q0_v),.q1_v(q1_v),.q0_bad(q0_bad),.q1_bad(q1_bad),.l_rst_n(l_rst_n_ref),.fault(fault_ref));
qfd_dv_s5_xhead2 u_dut(.ck(ck),.rst_n(rst_n),.cid(cid),.fault_i(fault_i),.a_f(a_f),.a_ib(a_ib),.n_d(n_d_dut),.s_d(s_d_dut),.w0_v(w0_v_dut),.w0_ep(w0_ep_dut),.c0_v(c0_v_dut),.c0_ep(c0_ep_dut),.w1_v(w1_v_dut),.w1_ep(w1_ep_dut),.c1_v(c1_v_dut),.c1_ep(c1_ep_dut),.w0_off(w0_off_dut),.w1_off(w1_off_dut),.w0_m(w0_m_dut),.w1_m(w1_m_dut),.w0_d(w0_d_dut),.w1_d(w1_d_dut),.w0_ctl(w0_ctl_dut),.w1_ctl(w1_ctl_dut),.r0_v(r0_v_dut),.r0_t(r0_t_dut),.r0_ep(r0_ep_dut),.r1_v(r1_v_dut),.r1_t(r1_t_dut),.r1_ep(r1_ep_dut),.r0_p(r0_p_dut),.r1_p(r1_p_dut),.q0(q0),.q1(q1),.q0_v(q0_v),.q1_v(q1_v),.q0_bad(q0_bad),.q1_bad(q1_bad),.l_rst_n(l_rst_n_dut),.fault(fault_dut));
qfd_dv_s5_xhead_bounded_mut u_mut(.ck(ck),.rst_n(rst_n),.cid(cid),.fault_i(fault_i),.a_f(a_f),.a_ib(a_ib),.n_d(n_d_mut),.s_d(s_d_mut),.w0_v(w0_v_mut),.w0_ep(w0_ep_mut),.c0_v(c0_v_mut),.c0_ep(c0_ep_mut),.w1_v(w1_v_mut),.w1_ep(w1_ep_mut),.c1_v(c1_v_mut),.c1_ep(c1_ep_mut),.w0_off(w0_off_mut),.w1_off(w1_off_mut),.w0_m(w0_m_mut),.w1_m(w1_m_mut),.w0_d(w0_d_mut),.w1_d(w1_d_mut),.w0_ctl(w0_ctl_mut),.w1_ctl(w1_ctl_mut),.r0_v(r0_v_mut),.r0_t(r0_t_mut),.r0_ep(r0_ep_mut),.r1_v(r1_v_mut),.r1_t(r1_t_mut),.r1_ep(r1_ep_mut),.r0_p(r0_p_mut),.r1_p(r1_p_mut),.q0(q0),.q1(q1),.q0_v(q0_v),.q1_v(q1_v),.q0_bad(q0_bad),.q1_bad(q1_bad),.l_rst_n(l_rst_n_mut),.fault(fault_mut));
initial begin
mutate=$test$plusargs("mutate");
rst_n=0; cid=6'd0;
for(cycle=0;cycle<10000;cycle=cycle+1) begin
@(negedge ck);
if(cycle%1000==0) cid=$urandom;
sparse=((cycle/500)%2==1);
fault_i[0 +: 1]=$urandom;
a_f[0 +: 32]=$urandom;
a_f[32 +: 32]=$urandom;
a_f[64 +: 32]=$urandom;
a_f[96 +: 32]=$urandom;
a_f[128 +: 32]=$urandom;
a_f[160 +: 32]=$urandom;
a_f[192 +: 32]=$urandom;
a_f[224 +: 32]=$urandom;
a_f[256 +: 32]=$urandom;
a_f[288 +: 32]=$urandom;
a_f[320 +: 32]=$urandom;
a_f[352 +: 32]=$urandom;
a_f[384 +: 32]=$urandom;
a_f[416 +: 32]=$urandom;
a_f[448 +: 32]=$urandom;
a_f[480 +: 32]=$urandom;
a_f[512 +: 32]=$urandom;
a_f[544 +: 32]=$urandom;
a_f[576 +: 32]=$urandom;
a_f[608 +: 32]=$urandom;
a_f[640 +: 32]=$urandom;
a_f[672 +: 32]=$urandom;
a_f[704 +: 32]=$urandom;
a_f[736 +: 32]=$urandom;
a_f[768 +: 32]=$urandom;
a_f[800 +: 32]=$urandom;
a_f[832 +: 32]=$urandom;
a_f[864 +: 32]=$urandom;
a_f[896 +: 32]=$urandom;
a_f[928 +: 32]=$urandom;
a_f[960 +: 32]=$urandom;
a_f[992 +: 32]=$urandom;
a_f[1024 +: 32]=$urandom;
a_f[1056 +: 32]=$urandom;
a_f[1088 +: 32]=$urandom;
a_f[1120 +: 32]=$urandom;
a_f[1152 +: 32]=$urandom;
a_f[1184 +: 3]=$urandom;
a_ib[0 +: 32]=$urandom;
a_ib[32 +: 32]=$urandom;
a_ib[64 +: 32]=$urandom;
a_ib[96 +: 32]=$urandom;
a_ib[128 +: 32]=$urandom;
a_ib[160 +: 32]=$urandom;
a_ib[192 +: 32]=$urandom;
a_ib[224 +: 32]=$urandom;
a_ib[256 +: 32]=$urandom;
a_ib[288 +: 32]=$urandom;
a_ib[320 +: 32]=$urandom;
a_ib[352 +: 28]=$urandom;
q0[0 +: 32]=$urandom;
q0[32 +: 32]=$urandom;
q0[64 +: 32]=$urandom;
q0[96 +: 32]=$urandom;
q0[128 +: 32]=$urandom;
q0[160 +: 32]=$urandom;
q0[192 +: 32]=$urandom;
q0[224 +: 32]=$urandom;
q1[0 +: 32]=$urandom;
q1[32 +: 32]=$urandom;
q1[64 +: 32]=$urandom;
q1[96 +: 32]=$urandom;
q1[128 +: 32]=$urandom;
q1[160 +: 32]=$urandom;
q1[192 +: 32]=$urandom;
q1[224 +: 32]=$urandom;
q0_v[0 +: 4]=$urandom;
q1_v[0 +: 4]=$urandom;
q0_bad[0 +: 4]=$urandom;
q1_bad[0 +: 4]=$urandom;
if(sparse) begin a_ib[0]=($urandom%8)==0; a_f[0]=($urandom%8)==0; a_f[73]=($urandom%8)==0; fault_i=0; end
if(cycle<12 || (cycle>=3100&&cycle<3112) || (cycle>=6700&&cycle<6712)) a_ib[0]=0;
rst_n=(cycle>=8)&&!(cycle>=3100&&cycle<3108)&&!(cycle>=6700&&cycle<6708);
@(posedge ck); #1;
if(cycle>16) begin
compares=compares+1; if(n_d_ref !== (mutate ? n_d_mut : n_d_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH n_d cycle=%0d",cycle); end
compares=compares+1; if(s_d_ref !== (mutate ? s_d_mut : s_d_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH s_d cycle=%0d",cycle); end
compares=compares+1; if(w0_v_ref !== (mutate ? w0_v_mut : w0_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_v cycle=%0d",cycle); end
compares=compares+1; if(w0_ep_ref !== (mutate ? w0_ep_mut : w0_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_ep cycle=%0d",cycle); end
compares=compares+1; if(c0_v_ref !== (mutate ? c0_v_mut : c0_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH c0_v cycle=%0d",cycle); end
compares=compares+1; if(c0_ep_ref !== (mutate ? c0_ep_mut : c0_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH c0_ep cycle=%0d",cycle); end
compares=compares+1; if(w1_v_ref !== (mutate ? w1_v_mut : w1_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_v cycle=%0d",cycle); end
compares=compares+1; if(w1_ep_ref !== (mutate ? w1_ep_mut : w1_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_ep cycle=%0d",cycle); end
compares=compares+1; if(c1_v_ref !== (mutate ? c1_v_mut : c1_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH c1_v cycle=%0d",cycle); end
compares=compares+1; if(c1_ep_ref !== (mutate ? c1_ep_mut : c1_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH c1_ep cycle=%0d",cycle); end
compares=compares+1; if(w0_off_ref !== (mutate ? w0_off_mut : w0_off_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_off cycle=%0d",cycle); end
compares=compares+1; if(w1_off_ref !== (mutate ? w1_off_mut : w1_off_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_off cycle=%0d",cycle); end
compares=compares+1; if(w0_m_ref !== (mutate ? w0_m_mut : w0_m_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_m cycle=%0d",cycle); end
compares=compares+1; if(w1_m_ref !== (mutate ? w1_m_mut : w1_m_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_m cycle=%0d",cycle); end
compares=compares+1; if(w0_d_ref !== (mutate ? w0_d_mut : w0_d_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_d cycle=%0d",cycle); end
compares=compares+1; if(w1_d_ref !== (mutate ? w1_d_mut : w1_d_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_d cycle=%0d",cycle); end
compares=compares+1; if(w0_ctl_ref !== (mutate ? w0_ctl_mut : w0_ctl_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w0_ctl cycle=%0d",cycle); end
compares=compares+1; if(w1_ctl_ref !== (mutate ? w1_ctl_mut : w1_ctl_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH w1_ctl cycle=%0d",cycle); end
compares=compares+1; if(r0_v_ref !== (mutate ? r0_v_mut : r0_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r0_v cycle=%0d",cycle); end
compares=compares+1; if(r0_t_ref !== (mutate ? r0_t_mut : r0_t_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r0_t cycle=%0d",cycle); end
compares=compares+1; if(r0_ep_ref !== (mutate ? r0_ep_mut : r0_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r0_ep cycle=%0d",cycle); end
compares=compares+1; if(r1_v_ref !== (mutate ? r1_v_mut : r1_v_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r1_v cycle=%0d",cycle); end
compares=compares+1; if(r1_t_ref !== (mutate ? r1_t_mut : r1_t_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r1_t cycle=%0d",cycle); end
compares=compares+1; if(r1_ep_ref !== (mutate ? r1_ep_mut : r1_ep_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r1_ep cycle=%0d",cycle); end
compares=compares+1; if(r0_p_ref !== (mutate ? r0_p_mut : r0_p_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r0_p cycle=%0d",cycle); end
compares=compares+1; if(r1_p_ref !== (mutate ? r1_p_mut : r1_p_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH r1_p cycle=%0d",cycle); end
compares=compares+1; if(l_rst_n_ref !== (mutate ? l_rst_n_mut : l_rst_n_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH l_rst_n cycle=%0d",cycle); end
compares=compares+1; if(fault_ref !== (mutate ? fault_mut : fault_dut)) begin failures=failures+1; if(failures<6) $display("XH7_MISMATCH fault cycle=%0d",cycle); end
end
end
if(failures) $display("XH7_EQ FAIL mismatches=%0d compares=%0d",failures,compares);
else $display("XH7_EQ PASS compares=%0d cycles=%0d",compares,cycle);
$finish;
end
endmodule
