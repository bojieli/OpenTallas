`timescale 1ns/1ps
// Current R3 CBUF candidate: actual released CROM + three real return stages.
// Per-group sequence control is independent of SU request addresses. Eight
// CROM, eight CBUF and eight return roots remain distinct compensated pins.
// Exact same-phase component contract: far pins->return11, f_lat_total12,
// local request->answer5. Physical homes, route phases and native timeline OPEN.
module qfd_native_crom8_r3_tp8 #(parameter integer CROM_MUT=0,RETURN_MUT=0)(
 input wire [7:0] crom_ck,cbuf_ck,return_ck,input wire rst_n,
 input wire [24:0] cbc0,cbc1,cbc2,cbc3,cbc4,cbc5,cbc6,cbc7,
 input wire [205:0] ca0,ca1,ca2,ca3,ca4,ca5,ca6,ca7,
 output wire [511:0] cq0,cq1,cq2,cq3,cq4,cq5,cq6,cq7,
 output wire [9:0] cbr0,cbr1,cbr2,cbr3,cbr4,cbr5,cbr6,cbr7,
 output wire [7:0] constants_resident,group_fault,
 output wire [47:0] constants_resident_stage,
 output wire [143:0] constants_resident_tpos,
 output wire [15:0] crom_fault_code,output wire fault);
 wire [1647:0] ca={ca7,ca6,ca5,ca4,ca3,ca2,ca1,ca0};
 wire [199:0] cbc={cbc7,cbc6,cbc5,cbc4,cbc3,cbc2,cbc1,cbc0};
 wire [4095:0] cq;wire [79:0] cbr;
 assign {cq7,cq6,cq5,cq4,cq3,cq2,cq1,cq0}=cq;
 assign {cbr7,cbr6,cbr5,cbr4,cbr3,cbr2,cbr1,cbr0}=cbr;
 genvar g;
 generate for(g=0;g<8;g=g+1)begin:g_group
 wire [205:0] req=ca[206*g+:206];wire [24:0] control=cbc[25*g+:25];
 wire [7:0] far_re;wire [191:0] far_addr;wire [5:0] far_stage;
 wire [511:0] rom_q,far_q;wire rom_fault,far_fault;wire [1:0] unused_rom_code;
 qfd_su_cbuf_native_l0_p13_l12_r3 u_cbuf(
 .clk(cbuf_ck[g]),.rst_n(rst_n),.grp(3'(g)),
 .crom_re(req[7:0]),.crom_addr(req[199:8]),.crom_stage(req[205:200]),.crom_q(cq[512*g+:512]),
 .stage(control[5:0]),.tok_start(control[6]),.tpos(control[24:7]),
 .st_rdy(constants_resident[g]),.st_rdy_stage(constants_resident_stage[6*g+:6]),
 .st_rdy_tpos(constants_resident_tpos[18*g+:18]),
 .f_re(far_re),.f_addr(far_addr),.f_stage(far_stage),.f_q(far_q),.f_fault(far_fault),
 .f_lat_total(5'd12),.fault(group_fault[g]),.fault_code(crom_fault_code[2*g+:2]));
 ot_qfd_crom_gr #(.TP(8),.IMG_LB(8*g),.MUT(CROM_MUT)) u_rom(
 .clk(crom_ck[g]),.rst_n(rst_n),.crom_re(far_re),.crom_addr(far_addr),.crom_stage(far_stage),
 .crom_lb(6'(8*g)),.crom_q(rom_q),.fault(rom_fault),.fault_code(unused_rom_code));
 // Three real pin-register stages with one explicitly exposed leaf root.
 qfd_crom_return3 #(.MUT(RETURN_MUT)) u_return(
 .ck(return_ck[g]),.rst_n(rst_n),.a({rom_fault,rom_q}),.b({far_fault,far_q}));
 assign cbr[10*g+:10]={crom_fault_code[2*g+:2],group_fault[g],
 constants_resident_stage[6*g+:6],constants_resident[g]};
 end endgenerate
 assign fault=|group_fault;
endmodule

// Fixed physical leaf candidate: every data input captures in p0 and every
// output launches from p2. MUT bypasses the final stage only in the bench.
// One kept reset pin sink; asynchronous assert, one-edge local release.
module qfd_crom_return3 #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[512:0]a,output wire[512:0]b);
 (* keep *) reg reset_q;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)reset_q<=0;else reset_q<=1;
 (* keep *) reg[512:0]p0,p1,p2;
 always @(posedge ck or negedge reset_q)
 if(!reset_q)begin p0<=0;p1<=0;p2<=0;end
 else begin p0<=a;p1<=p0;p2<=p1;end
 assign b=(MUT!=0)?p1:p2;
endmodule
