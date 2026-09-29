module ot_gpu_barrier_node (clk,
    rel_in,
    rst_n,
    up,
    arr,
    rel);
 input clk;
 input rel_in;
 input rst_n;
 output up;
 input [7:0] arr;
 output [7:0] rel;

 wire _00_;
 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire net2;
 wire net3;
 wire net4;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net12;
 wire net10;
 wire net11;
 wire net13;
 wire net;
 wire net1;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;

 INVx1_ASAP7_75t_R _08_ (.A(_01_),
    .Y(net13));
 OR4x1_ASAP7_75t_R _09_ (.A(net4),
    .B(net3),
    .C(net2),
    .D(net9),
    .Y(_03_));
 OR5x1_ASAP7_75t_R _10_ (.A(net8),
    .B(net7),
    .C(net6),
    .D(net5),
    .E(_03_),
    .Y(_04_));
 AND4x2_ASAP7_75t_R _11_ (.A(net4),
    .B(net3),
    .C(net2),
    .D(net9),
    .Y(_05_));
 AND5x1_ASAP7_75t_R _12_ (.A(net8),
    .B(net7),
    .C(net6),
    .D(net5),
    .E(_05_),
    .Y(_06_));
 AO21x2_ASAP7_75t_R _13_ (.A1(net13),
    .A2(_04_),
    .B(_06_),
    .Y(_02_));
 INVx1_ASAP7_75t_R _14_ (.A(_00_),
    .Y(net12));
 BUFx2_ASAP7_75t_R clkbuf_0_clk (.A(clk),
    .Y(clknet_0_clk));
 BUFx2_ASAP7_75t_R clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .Y(clknet_1_0__leaf_clk));
 BUFx2_ASAP7_75t_R clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .Y(clknet_1_1__leaf_clk));
 BUFx2_ASAP7_75t_R input10 (.A(arr[7]),
    .Y(net9));
 BUFx2_ASAP7_75t_R input11 (.A(rel_in),
    .Y(net10));
 BUFx2_ASAP7_75t_R input12 (.A(rst_n),
    .Y(net11));
 BUFx2_ASAP7_75t_R input3 (.A(arr[0]),
    .Y(net2));
 BUFx2_ASAP7_75t_R input4 (.A(arr[1]),
    .Y(net3));
 BUFx2_ASAP7_75t_R input5 (.A(arr[2]),
    .Y(net4));
 BUFx2_ASAP7_75t_R input6 (.A(arr[3]),
    .Y(net5));
 BUFx2_ASAP7_75t_R input7 (.A(arr[4]),
    .Y(net6));
 BUFx2_ASAP7_75t_R input8 (.A(arr[5]),
    .Y(net7));
 BUFx2_ASAP7_75t_R input9 (.A(arr[6]),
    .Y(net8));
 BUFx2_ASAP7_75t_R output13 (.A(net12),
    .Y(rel[0]));
 BUFx2_ASAP7_75t_R output14 (.A(net12),
    .Y(rel[1]));
 BUFx2_ASAP7_75t_R output15 (.A(net12),
    .Y(rel[2]));
 BUFx2_ASAP7_75t_R output16 (.A(net12),
    .Y(rel[3]));
 BUFx2_ASAP7_75t_R output17 (.A(net12),
    .Y(rel[4]));
 BUFx2_ASAP7_75t_R output18 (.A(net12),
    .Y(rel[5]));
 BUFx2_ASAP7_75t_R output19 (.A(net12),
    .Y(rel[6]));
 BUFx2_ASAP7_75t_R output20 (.A(net12),
    .Y(rel[7]));
 BUFx2_ASAP7_75t_R output21 (.A(net13),
    .Y(up));
 DFFASRHQNx1_ASAP7_75t_R \rel[0]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_clk),
    .D(net10),
    .QN(_00_),
    .RESETN(net11),
    .SETN(net));
 TIEHIx1_ASAP7_75t_R \rel[0]$_DFF_PN0__1  (.H(net));
 DFFASRHQNx1_ASAP7_75t_R \up$_DFFE_PN0P_  (.CLK(clknet_1_0__leaf_clk),
    .D(_02_),
    .QN(_01_),
    .RESETN(net11),
    .SETN(net1));
 TIEHIx1_ASAP7_75t_R \up$_DFFE_PN0P__2  (.H(net1));
endmodule
