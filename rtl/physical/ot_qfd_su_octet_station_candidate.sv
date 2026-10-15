// Exact existing IS1/OS1 and broadcast-stage registers; distinct opt-in cut.
`timescale 1ns/1ps
module ot_qfd_su_octet_station_candidate #(parameter integer DATA_MUT=0,RESET_MUT=0)(
 input wire clk,rst_n,b_rst_n,
 input wire [511:0] crom_d,input wire [639:0] os_d,input wire [15:0] os_v,
 input wire [499:0] b_d,input wire [2:0] b_v,
 output reg [511:0] crom_q,output reg [639:0] os_q,output reg [15:0] os_vq,
 output reg [499:0] b_q,output reg [2:0] b_vq
);
 reg rg;
 always @(posedge clk or negedge b_rst_n)if(!b_rst_n)rg<=0;else rg<=1;
 always @(posedge clk or negedge rst_n)if(!rst_n)os_vq<=0;else os_vq<=os_v;
 generate if(RESET_MUT==0)begin:g_native_reset
 always @(posedge clk or negedge rg)if(!rg)b_vq<=0;else b_vq<=b_v;
 end else begin:g_mut_reset
 always @(posedge clk or negedge b_rst_n)if(!b_rst_n)b_vq<=0;else b_vq<=b_v;
 end endgenerate
 always @(posedge clk)begin
 crom_q<=crom_d ^ DATA_MUT;
 os_q<=os_d;
 b_q<=b_d;
 end
endmodule

// The original reducer input stage, including exact inactive SUM/MAX fill.
module ot_qfd_su_reducer_station_candidate #(parameter integer DATA_MUT=0)(
 input wire clk,rst_n,input wire [63:0] l_ov,input wire [127:0] l_red,
 input wire [63:0] l_redsq,l_last,input wire [1535:0] l_raddr,
 input wire [2047:0] l_out,
 output reg rd_v,rd_mx,rd_sq,rd_last,output reg [23:0] rd_addr,output reg [2047:0] rd_x
);
 integer li;
 always @(posedge clk or negedge rst_n)
 if(!rst_n)rd_v<=0;else rd_v<=l_ov[0]&&l_red[1:0]!=2'd0;
 always @(posedge clk)begin
 rd_mx<=(l_red[1:0]==2'd2);rd_sq<=l_redsq[0];rd_last<=l_last[0];rd_addr<=l_raddr[0+:24];
 for(li=0;li<64;li=li+1)
 rd_x[32*li+:32]<=(l_ov[li]?l_out[32*li+:32]:(l_red[1:0]==2'd2)?l_out[31:0]:32'd0) ^ ((li==0)?DATA_MUT:0);
 end
endmodule
