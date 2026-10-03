`timescale 1ns/1ps
// Opt-in generated return successor. SOURCE partials must obey lv/lready.
// Nonstallable ROM producers require the separately priced 8-row/pair buffer.
module ot_v41_return_credit_generated(
 input wire clk,rst_n, input wire [9:0] lv,le,
 input wire [319:0] lt,ld,
 output wire [9:0] lready,
 output wire [1:0] rv,re, output wire [31:0] rrow,rbf16,
 output wire [5:0] rpos, output wire [63:0] rfp32,
 output wire fault,quiet);
 wire [17:0] v,e,c,q; wire [31:0] tag[0:17],data[0:17];
 wire [9:0] faults;

assign v[0]=lv[0]; assign e[0]=le[0]; assign tag[0]=lt[0+:32]; assign data[0]=ld[0+:32]; assign q[0]=!lv[0];
assign v[1]=lv[1]; assign e[1]=le[1]; assign tag[1]=lt[32+:32]; assign data[1]=ld[32+:32]; assign q[1]=!lv[1];
assign v[2]=lv[2]; assign e[2]=le[2]; assign tag[2]=lt[64+:32]; assign data[2]=ld[64+:32]; assign q[2]=!lv[2];
assign v[3]=lv[3]; assign e[3]=le[3]; assign tag[3]=lt[96+:32]; assign data[3]=ld[96+:32]; assign q[3]=!lv[3];
assign v[4]=lv[4]; assign e[4]=le[4]; assign tag[4]=lt[128+:32]; assign data[4]=ld[128+:32]; assign q[4]=!lv[4];
assign v[5]=lv[5]; assign e[5]=le[5]; assign tag[5]=lt[160+:32]; assign data[5]=ld[160+:32]; assign q[5]=!lv[5];
assign v[6]=lv[6]; assign e[6]=le[6]; assign tag[6]=lt[192+:32]; assign data[6]=ld[192+:32]; assign q[6]=!lv[6];
assign v[7]=lv[7]; assign e[7]=le[7]; assign tag[7]=lt[224+:32]; assign data[7]=ld[224+:32]; assign q[7]=!lv[7];
assign v[8]=lv[8]; assign e[8]=le[8]; assign tag[8]=lt[256+:32]; assign data[8]=ld[256+:32]; assign q[8]=!lv[8];
assign v[9]=lv[9]; assign e[9]=le[9]; assign tag[9]=lt[288+:32]; assign data[9]=ld[288+:32]; assign q[9]=!lv[9];
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n0(
 .clk(clk),.rst_n(rst_n),.a_v(v[0]),.a_t(tag[0]),.a_d(data[0]),.a_e(e[0]),
 .b_v(v[1]),.b_t(tag[1]),.b_d(data[1]),.b_e(e[1]),
 .a_ready(lready[0]),.b_ready(lready[1]),
 .a_credit(c[0]),.b_credit(c[1]),.o_credit(c[10]),
 .o_v(v[10]),.o_t(tag[10]),.o_d(data[10]),.o_e(e[10]),.fault(faults[0]),.quiet(q[10]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n1(
 .clk(clk),.rst_n(rst_n),.a_v(v[2]),.a_t(tag[2]),.a_d(data[2]),.a_e(e[2]),
 .b_v(v[3]),.b_t(tag[3]),.b_d(data[3]),.b_e(e[3]),
 .a_ready(lready[2]),.b_ready(lready[3]),
 .a_credit(c[2]),.b_credit(c[3]),.o_credit(c[11]),
 .o_v(v[11]),.o_t(tag[11]),.o_d(data[11]),.o_e(e[11]),.fault(faults[1]),.quiet(q[11]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(128),.RST(1)) n2(
 .clk(clk),.rst_n(rst_n),.a_v(v[10]),.a_t(tag[10]),.a_d(data[10]),.a_e(e[10]),
 .b_v(v[11]),.b_t(tag[11]),.b_d(data[11]),.b_e(e[11]),
 .a_ready(),.b_ready(),
 .a_credit(c[10]),.b_credit(c[11]),.o_credit(c[12]),
 .o_v(v[12]),.o_t(tag[12]),.o_d(data[12]),.o_e(e[12]),.fault(faults[2]),.quiet(q[12]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n3(
 .clk(clk),.rst_n(rst_n),.a_v(v[5]),.a_t(tag[5]),.a_d(data[5]),.a_e(e[5]),
 .b_v(v[6]),.b_t(tag[6]),.b_d(data[6]),.b_e(e[6]),
 .a_ready(lready[5]),.b_ready(lready[6]),
 .a_credit(c[5]),.b_credit(c[6]),.o_credit(c[13]),
 .o_v(v[13]),.o_t(tag[13]),.o_d(data[13]),.o_e(e[13]),.fault(faults[3]),.quiet(q[13]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n4(
 .clk(clk),.rst_n(rst_n),.a_v(v[4]),.a_t(tag[4]),.a_d(data[4]),.a_e(e[4]),
 .b_v(v[13]),.b_t(tag[13]),.b_d(data[13]),.b_e(e[13]),
 .a_ready(lready[4]),.b_ready(),
 .a_credit(c[4]),.b_credit(c[13]),.o_credit(c[14]),
 .o_v(v[14]),.o_t(tag[14]),.o_d(data[14]),.o_e(e[14]),.fault(faults[4]),.quiet(q[14]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n5(
 .clk(clk),.rst_n(rst_n),.a_v(v[8]),.a_t(tag[8]),.a_d(data[8]),.a_e(e[8]),
 .b_v(v[9]),.b_t(tag[9]),.b_d(data[9]),.b_e(e[9]),
 .a_ready(lready[8]),.b_ready(lready[9]),
 .a_credit(c[8]),.b_credit(c[9]),.o_credit(c[15]),
 .o_v(v[15]),.o_t(tag[15]),.o_d(data[15]),.o_e(e[15]),.fault(faults[5]),.quiet(q[15]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(4),.RST(1)) n6(
 .clk(clk),.rst_n(rst_n),.a_v(v[7]),.a_t(tag[7]),.a_d(data[7]),.a_e(e[7]),
 .b_v(v[15]),.b_t(tag[15]),.b_d(data[15]),.b_e(e[15]),
 .a_ready(lready[7]),.b_ready(),
 .a_credit(c[7]),.b_credit(c[15]),.o_credit(c[16]),
 .o_v(v[16]),.o_t(tag[16]),.o_d(data[16]),.o_e(e[16]),.fault(faults[6]),.quiet(q[16]),
 .peak_a(),.peak_b(),.credit_stalls());
ot_v41_retn_credit #(.RD(4),.OUTD(128),.RST(1)) n7(
 .clk(clk),.rst_n(rst_n),.a_v(v[14]),.a_t(tag[14]),.a_d(data[14]),.a_e(e[14]),
 .b_v(v[16]),.b_t(tag[16]),.b_d(data[16]),.b_e(e[16]),
 .a_ready(),.b_ready(),
 .a_credit(c[14]),.b_credit(c[16]),.o_credit(c[17]),
 .o_v(v[17]),.o_t(tag[17]),.o_d(data[17]),.o_e(e[17]),.fault(faults[7]),.quiet(q[17]),
 .peak_a(),.peak_b(),.credit_stalls());
wire rq0;
 ot_v41_ret_credit_root #(.ROOTD(128)) root0(.clk(clk),.rst_n(rst_n),
 .i_v(v[12]),.i_t(tag[12]),.i_d(data[12]),.i_e(e[12]),.i_ready(),.i_credit(c[12]),
 .r_v(rv[0]),.r_e(re[0]),.r_row(rrow[0+:16]),.r_pos(rpos[0+:3]),
 .r_fp32(rfp32[0+:32]),.r_bf16(rbf16[0+:16]),.fault(faults[8]),
 .quiet(rq0),.peak_q(),.peak_held(),.blocked_cycles());
wire rq1;
 ot_v41_ret_credit_root #(.ROOTD(128)) root1(.clk(clk),.rst_n(rst_n),
 .i_v(v[17]),.i_t(tag[17]),.i_d(data[17]),.i_e(e[17]),.i_ready(),.i_credit(c[17]),
 .r_v(rv[1]),.r_e(re[1]),.r_row(rrow[16+:16]),.r_pos(rpos[3+:3]),
 .r_fp32(rfp32[32+:32]),.r_bf16(rbf16[16+:16]),.fault(faults[9]),
 .quiet(rq1),.peak_q(),.peak_held(),.blocked_cycles());
assign fault=|faults; assign quiet=(&q) && rq0 && rq1;
endmodule
