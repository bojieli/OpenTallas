`timescale 1ns/1ps
module tb_w11_field_prefix_sequential_gate (
 input wire clk, rst_n, fv, mv, tv, fp4,
 input wire [31:0] a, b,
 input wire [255:0] xq,wq,
 input wire signed [9:0] xe,we,
 input wire [16:0] tag,
 output wire [31:0] ref_add_y,sim_add_y,ref_mul_y,sim_mul_y,ref_term_y,sim_term_y,
 output wire [1:0] ref_add_err,sim_add_err,
 output wire ref_add_v,sim_add_v,ref_mul_fault,sim_mul_fault,ref_term_v,sim_term_v,ref_term_f,sim_term_f,
 output wire [16:0] ref_term_tag,sim_term_tag
);
 field_ref_ot_v41_fadd #(.CUT(9'd379)) a_ref (.clk(clk),.rst_n(rst_n),.valid_in(fv),.a(a),.b(b),.y(ref_add_y),.err(ref_add_err),.valid_out(ref_add_v));
 field_ref_ot_v41_bmul2 m_ref (.clk(clk),.rst_n(rst_n),.v(mv),.a(a),.b(b),.y(ref_mul_y),.fault(ref_mul_fault));
 field_ref_ot_v41_bterm2_w10 #(.TW(17)) t_ref (.clk(clk),.rst_n(rst_n),.v(tv),.fp4(fp4),.xq(xq),.wq(wq),.xe(xe),.we(we),.tag(tag),.ov(ref_term_v),.y(ref_term_y),.f(ref_term_f),.otag(ref_term_tag));
 field_sim_ot_v41_fadd #(.CUT(9'd379)) a_sim (.clk(clk),.rst_n(rst_n),.valid_in(fv),.a(a),.b(b),.y(sim_add_y),.err(sim_add_err),.valid_out(sim_add_v));
 field_sim_ot_v41_bmul2 m_sim (.clk(clk),.rst_n(rst_n),.v(mv),.a(a),.b(b),.y(sim_mul_y),.fault(sim_mul_fault));
 field_sim_ot_v41_bterm2_w10 #(.TW(17)) t_sim (.clk(clk),.rst_n(rst_n),.v(tv),.fp4(fp4),.xq(xq),.wq(wq),.xe(xe),.we(we),.tag(tag),.ov(sim_term_v),.y(sim_term_y),.f(sim_term_f),.otag(sim_term_tag));
endmodule
