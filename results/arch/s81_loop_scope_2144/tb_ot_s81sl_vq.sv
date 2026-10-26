`timescale 1ns/1ps
module tb_ot_s81sl_vq;
wire MUT=$test$plusargs("mutant");
reg clk=0; always #1 clk=~clk;
reg  rst_n=0;
reg  y_v=0;
reg [2:0] y_i=0;
reg [127:0] y=0;
reg  u_v=0;
reg [2:0] u_i=0;
reg [255:0] u=0;
reg [3:0] sid=0;
reg [2:0] k=0;
reg  m_v=0;
reg  m_q=0;
reg  m_b=0;
reg [7:0] m_i=0;
reg  um_v=0;
reg  um_q=0;
reg  um_b=0;
reg [7:0] um_i=0;
wire  g_xf_v,n_xf_v;
wire  g_xf_s,n_xf_s;
wire [275:0] g_xf,n_xf;
wire  g_fault,n_fault;
ot_s81sl_vq_gold #(.AQ_XMEM(2)) gold(.clk(clk),.rst_n(rst_n),.y_v(y_v),.y_i(y_i),.y(y),.u_v(u_v),.u_i(u_i),.u(u),.sid(sid),.k(k),.m_v(m_v),.m_q(m_q),.m_b(m_b),.m_i(m_i),.um_v(um_v),.um_q(um_q),.um_b(um_b),.um_i(um_i),.xf_v(g_xf_v),.xf_s(g_xf_s),.xf(g_xf),.fault(g_fault));
ot_s81sl_vq #(.AQ_XMEM(2)) dut(.clk(clk),.rst_n(rst_n),.y_v(y_v),.y_i(y_i),.y(y),.u_v(u_v),.u_i(MUT ? u_i^3'd1 : u_i),.u(u),.sid(sid),.k(k),.m_v(m_v),.m_q(m_q),.m_b(m_b),.m_i(m_i),.um_v(um_v),.um_q(um_q),.um_b(um_b),.um_i(um_i),.xf_v(n_xf_v),.xf_s(n_xf_s),.xf(n_xf),.fault(n_fault));
integer cyc=0, checks=0, active=0;
initial begin
repeat(5) @(negedge clk); rst_n=1;
for(cyc=0;cyc<10000;cyc=cyc+1) begin
@(negedge clk);
y_v=$urandom;
y_i[0 +: 3]=$urandom;
y[0 +: 32]=$urandom;
y[32 +: 32]=$urandom;
y[64 +: 32]=$urandom;
y[96 +: 32]=$urandom;
u_v=$urandom;
u_i[0 +: 3]=$urandom;
u[0 +: 32]=$urandom;
u[32 +: 32]=$urandom;
u[64 +: 32]=$urandom;
u[96 +: 32]=$urandom;
u[128 +: 32]=$urandom;
u[160 +: 32]=$urandom;
u[192 +: 32]=$urandom;
u[224 +: 32]=$urandom;
sid[0 +: 4]=$urandom;
k[0 +: 3]=$urandom;
m_v=$urandom;
m_q=$urandom;
m_b=$urandom;
m_i[0 +: 8]=$urandom;
um_v=$urandom;
um_q=$urandom;
um_b=$urandom;
um_i[0 +: 8]=$urandom;
m_v=(cyc%200==0); m_q=1; m_b=1; m_i=cyc/200; um_v=0; y_v=0;
u_v=(cyc%200>=8 && cyc%200<16); u_i=(cyc%200)-8;
@(posedge clk); #0.1;
if(cyc>10) begin
if((g_xf_v !== n_xf_v) || (g_xf_s !== n_xf_s) || (g_xf !== n_xf) || (g_fault !== n_fault)) begin $display("FAIL ot_s81sl_vq cycle=%0d",cyc); $finish; end
checks=checks+1;
end
end
$display("PASS ot_s81sl_vq checks=%0d",checks); $finish; end
endmodule
