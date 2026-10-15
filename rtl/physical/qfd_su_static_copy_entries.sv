`timescale 1ns/1ps
// Compiler-reserved, bit-transparent replay at the actual SU/VM face.
// cp command: start[0], scalar src[24:1], scalar dst[48:25], beats[55:49].
// One contiguous 64-lane A descriptor per edge; no ready, credit or arbitration.
// Native memory samples the registered request and answers after READ_EDGES
// pipeline edges. A separate output register copies every raw bit unchanged.
// cp_done means last output at this face, NOT SRAM commit or XS delivery.
module qfd_su_static_copy_entries #(
 parameter integer READ_EDGES=15, DATA_MUT=0, LATENCY_MUT=0
)(
 input wire ck_copy,rst_n,
 input wire [55:0] cp,
 input wire [2366:0] su_va,
 input wire [6143:0] vq,
 output wire [2366:0] va,
 output wire [2136:0] xsw,
 output wire cp_active,
 output wire cp_done,fault
);
 wire rd_v,wr_v;wire [23:0]rd_src,wr_dst;wire [2047:0]wr_data;
 wire occupied=cp_active;
 wire su_conflict=(|{su_va[149:148],su_va[99:98],su_va[49:48]})||(|su_va[2309:2246])||su_va[2366];
 ot_qfd_su_copy_core #(.READ_EDGES(READ_EDGES),.DATA_MUT(DATA_MUT),.LATENCY_MUT(LATENCY_MUT)) u_core (
 .ck(ck_copy),.rst_n(rst_n),.cp(cp),.vq0(vq[511:0]),.vq1(vq[1023:512]),.vq2(vq[1535:1024]),.vq3(vq[2047:1536]),.su_conflict(su_conflict),
 .cp_active(cp_active),.cp_done(cp_done),.fault(fault),
 .rd_v(rd_v),.rd_src(rd_src),.wr_v(wr_v),.wr_dst(wr_dst),.wr_data0(wr_data[511:0]),.wr_data1(wr_data[1023:512]),.wr_data2(wr_data[1535:1024]),.wr_data3(wr_data[2047:1536]));
 wire [2366:0] copy_va;
 qfd_su_vm_pack u_pack(
 .s_re0({2'd0,rd_v}),.s_re1({2'd0,rd_v}),
 .s_a0({48'd0,rd_src}),.s_a1({48'd0,rd_src+24'd1}),
 .sw_mask({64{wr_v}}),.sw_a0(wr_dst),.sw_a1(wr_dst+24'd1),.sw_data(wr_data),
 .red_we(1'b0),.red_addr(24'd0),.red_data(32'd0),.va(copy_va));
 // Selection follows a compiled reservation, never observed readiness.
 assign va=occupied?copy_va:su_va;
 assign xsw=occupied?{wr_data,{64{wr_v}},wr_dst,wr_v}:
 {su_va[2197:150],su_va[2309:2246],su_va[2221:2198],(|su_va[2309:2246])};
 initial if(READ_EDGES<2 || LATENCY_MUT<0 || LATENCY_MUT>1)$fatal(1,"invalid static copy latency");
endmodule
