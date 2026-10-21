`timescale 1ns/1ps
module tb(input wire ck,rst_n,pw_v,start,candidate_v,input wire[9:0]pw_addr,input wire[63:0]pw_data,input wire[11:0]candidate_pc,input wire[1:0]candidate_unit,
output wire mismatch,issue_new,end_new,active_new,ready_new,fault_new);
wire[111:0] a,b;
wire gi,ge,gcp,ga,gd,gr,gf,ni,ne,ncp,na,nd,nr,nf;wire[55:0]gc,nc;wire[11:0]gp,np;wire[1:0]gu,nu;wire[31:0]gt,nt;
gold_ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(1),.OWN(1),.SREG(1),.SLATE(1)) gold(.clk(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.start(start),.stage(6'd0),.candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(1'b1),.end_ok(1'b1),.cp_available(1'b1),.issue_v(gi),.end_v(ge),.cp_cmd(gc),.cp_v(gcp),.issue_pc(gp),.issue_unit(gu),.active(ga),.done(gd),.cycle(gt),.image_ready(gr),.fault(gf));
ot_qwen_fixed_issue_pw #(.DENSE_IMAGE(1),.OWN(1),.SREG(1),.SLATE(1),.SEG(0)) gate(.clk(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),.start(start),.stage(6'd0),.start_base(12'habc),.candidate_v(candidate_v),.candidate_pc(candidate_pc),.candidate_unit(candidate_unit),.available(1'b1),.end_ok(1'b1),.cp_available(1'b1),.issue_v(ni),.end_v(ne),.cp_cmd(nc),.cp_v(ncp),.issue_pc(np),.issue_unit(nu),.active(na),.done(nd),.cycle(nt),.image_ready(nr),.fault(nf));
assign a={gi,ge,gc,gcp,gp,gu,ga,gd,gt,gr,gf};assign b={ni,ne,nc,ncp,np,nu,na,nd,nt,nr,nf};
assign mismatch=a!==b;assign issue_new=ni;assign end_new=ne;assign active_new=na;assign ready_new=nr;assign fault_new=nf;
endmodule
