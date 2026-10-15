(* blackbox *) module ot_qfd_su_copy_core #(
 parameter integer READ_EDGES=15,DATA_MUT=0,LATENCY_MUT=0
)(
 input wire ck,rst_n,input wire [55:0] cp,
 input wire [511:0] vq0,vq1,vq2,vq3,input wire su_conflict,
 output wire cp_active,output reg cp_done,fault,
 output reg rd_v,output reg [23:0] rd_src,
 output reg wr_v,output reg [23:0] wr_dst,
 output wire [511:0] wr_data0,wr_data1,wr_data2,wr_data3
);
endmodule
