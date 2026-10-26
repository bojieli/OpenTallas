`timescale 1ns/1ps
module ot_hgi_coll_park_q0(input wire clk,rst_n,input wire [3:0] pv,input wire [7:0] pq,ps,input wire [2179:0] pd,output wire hv,output wire [544:0] hd,input wire pop,output wire [3:0] bank_ovf);
ot_hgi_coll_park_queue #(.QID(0)) u_q (.clk(clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv),.hd(hd),.pop(pop),.bank_ovf(bank_ovf));
endmodule
module ot_hgi_coll_park_q1(input wire clk,rst_n,input wire [3:0] pv,input wire [7:0] pq,ps,input wire [2179:0] pd,output wire hv,output wire [544:0] hd,input wire pop,output wire [3:0] bank_ovf);
ot_hgi_coll_park_queue #(.QID(1),.PSTAGE(1)) u_q (.clk(clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv),.hd(hd),.pop(pop),.bank_ovf(bank_ovf));
endmodule
module ot_hgi_coll_park_q2(input wire clk,rst_n,input wire [3:0] pv,input wire [7:0] pq,ps,input wire [2179:0] pd,output wire hv,output wire [544:0] hd,input wire pop,output wire [3:0] bank_ovf);
ot_hgi_coll_park_queue #(.QID(2)) u_q (.clk(clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv),.hd(hd),.pop(pop),.bank_ovf(bank_ovf));
endmodule
module ot_hgi_coll_park_q3(input wire clk,rst_n,input wire [3:0] pv,input wire [7:0] pq,ps,input wire [2179:0] pd,output wire hv,output wire [544:0] hd,input wire pop,output wire [3:0] bank_ovf);
ot_hgi_coll_park_queue #(.QID(3)) u_q (.clk(clk),.rst_n(rst_n),.pv(pv),.pq(pq),.ps(ps),.pd(pd),.hv(hv),.hd(hd),.pop(pop),.bank_ovf(bank_ovf));
endmodule
