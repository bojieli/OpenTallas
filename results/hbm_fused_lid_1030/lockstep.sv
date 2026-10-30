`timescale 1ns/1ps
module tb;reg clk=0;always #5 clk=~clk;reg rst_n=1;integer id_arg=0,cycle=0,checks=0,mutant_hits=0,rqs=0,ups=0,jobs=0;
reg [4:0] lid=0;
wire rq_v,c_rq_v,m_rq_v;
wire [15:0] rq_s,c_rq_s,m_rq_s;
reg rr_v=0;
reg [255:0] rr_d=0;
wire wq_v,c_wq_v,m_wq_v;
wire [15:0] wq_s,c_wq_s,m_wq_s;
wire [255:0] wq_d,c_wq_d,m_wq_d;
reg dn_v=0;
reg [2:0] dn_op=0;
reg [7:0] dn_x=0;
reg [127:0] dn_d=0;
reg r_v=0;
reg [31:0] r_d=0;
wire up_v,c_up_v,m_up_v;
wire up_t,c_up_t,m_up_t;
wire [9:0] up_x,c_up_x,m_up_x;
wire [255:0] up_d,c_up_d,m_up_d;
wire fin,c_fin,m_fin;
wire flt,c_flt,m_flt;
ot_hnx_fused_lane__native_reference #(.D(5120),.KX(4),.RR(10)) refdut(.clk(clk),.rst_n(rst_n),.lid(lid),.rq_v(rq_v),.rq_s(rq_s),.rr_v(rr_v),.rr_d(rr_d),.wq_v(wq_v),.wq_s(wq_s),.wq_d(wq_d),.dn_v(dn_v),.dn_op(dn_op),.dn_x(dn_x),.dn_d(dn_d),.r_v(r_v),.r_d(r_d),.up_v(up_v),.up_t(up_t),.up_x(up_x),.up_d(up_d),.fin(fin),.flt(flt));
hnx_fused_lane__static_lid dut(.clk(clk),.rst_n(rst_n),.strap_lid(lid),.rq_v(c_rq_v),.rq_s(c_rq_s),.rr_v(rr_v),.rr_d(rr_d),.wq_v(c_wq_v),.wq_s(c_wq_s),.wq_d(c_wq_d),.dn_v(dn_v),.dn_op(dn_op),.dn_x(dn_x),.dn_d(dn_d),.r_v(r_v),.r_d(r_d),.up_v(c_up_v),.up_t(c_up_t),.up_x(c_up_x),.up_d(c_up_d),.fin(c_fin),.flt(c_flt));
hnx_fused_lane__static_lid mutant(.clk(clk),.rst_n(rst_n),.strap_lid(lid ^ 5'd1),.rq_v(m_rq_v),.rq_s(m_rq_s),.rr_v(rr_v),.rr_d(rr_d),.wq_v(m_wq_v),.wq_s(m_wq_s),.wq_d(m_wq_d),.dn_v(dn_v),.dn_op(dn_op),.dn_x(dn_x),.dn_d(dn_d),.r_v(r_v),.r_d(r_d),.up_v(m_up_v),.up_t(m_up_t),.up_x(m_up_x),.up_d(m_up_d),.fin(m_fin),.flt(m_flt));
wire[559:0] old_o={rq_v,rq_s,wq_v,wq_s,wq_d,up_v,up_t,up_x,up_d,fin,flt};wire[559:0] new_o={c_rq_v,c_rq_s,c_wq_v,c_wq_s,c_wq_d,c_up_v,c_up_t,c_up_x,c_up_d,c_fin,c_flt};wire[559:0] bad_o={m_rq_v,m_rq_s,m_wq_v,m_wq_s,m_wq_d,m_up_v,m_up_t,m_up_x,m_up_d,m_fin,m_flt};
initial begin if(!$value$plusargs("ID=%d",id_arg))id_arg=0; if(id_arg<0||id_arg>31)$fatal(1,"ID range"); lid=id_arg; #1;rst_n=0;#0.1;if(old_o!==new_o)$fatal(1,"true POR boundary mismatch ID%0d",id_arg);end
always @(negedge clk)begin cycle=cycle+1;dn_v=0;dn_op=cycle%8;dn_x=0;dn_d=128'hfedcba98765432100123456789abcdef;rr_v=(rst_n && refdut.vexp[10]===1'b1);rr_d={8{32'h3f800000}};r_v=0;r_d=32'h3f800000;
if(cycle<66 || (cycle>=120 && cycle<186))begin rst_n=0;dn_v=1;dn_op=cycle%8;end else rst_n=1;
if(cycle==80 || cycle==200)begin dn_v=1;dn_op=0;dn_d=0;dn_d[9:5]=lid;end
if(cycle==84 || cycle==204)begin dn_v=1;dn_op=2;dn_d=0;dn_d[4:0]=lid;end
if(cycle==90 || cycle==210)begin dn_v=1;dn_op=2;dn_d=0;dn_d[4:0]=lid^5'd1;end
if(rr_v && cycle>190)begin rr_d[9]=1'bx;rr_d[73]=1'bz;end
end
always @(posedge clk or negedge rst_n) begin #0.1;checks=checks+1;if(old_o!==new_o)$fatal(1,"full boundary mismatch ID%0d cycle%0d reset%b old%h new%h",id_arg,cycle,rst_n,old_o,new_o);if(old_o!==bad_o)mutant_hits=mutant_hits+1;
if(refdut.c_job===1'b1 || refdut.c_scr===1'b1)begin if(refdut.lid_q!==dut.u_native.lid_q)$fatal(1,"ID consumed before capture settled ID%0d cycle%0d",id_arg,cycle);end
if(refdut.c_job===1'b1)jobs=jobs+1;if(rq_v===1'b1)rqs=rqs+1;if(up_v===1'b1)ups=ups+1;
if(cycle>74 && rst_n && flt!==1'b0)$fatal(1,"reference fault ID%0d cycle%0d fault%b",id_arg,cycle,flt);
if(cycle==230)begin if(!mutant_hits || rqs!=2 || ups!=2 || jobs!=2)$fatal(1,"coverage ID%0d mutant%0d rq%0d up%0d job%0d",id_arg,mutant_hits,rqs,ups,jobs);$display("PASS ID%0d full560output 4state cold66/warm66/truePOR/firstedges checks%0d rq%0d up%0d job%0d wrongID%0d",id_arg,checks,rqs,ups,jobs,mutant_hits);$finish;end end
initial begin #2400;$fatal(1,"timeout");end
endmodule
