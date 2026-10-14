module dsfd_die_rstsync (ck,
    rn,
    rst);
 input ck;
 output rn;
 input rst;

 wire _0_;
 wire _1_;
 wire \q[0] ;
 wire net3;
 wire net;
 wire net1;
 wire net2;
 wire ot_outhold_p00000;
 wire ot_outhold_n00000_0;
 wire ot_outhold_n00000_1;
 wire rn4;
 wire clknet_0_ck;
 wire clknet_1_0__leaf_ck;
 wire clknet_1_1__leaf_ck;
 wire net5;
 wire net6;
 wire net7;
 wire net8;
 wire net9;
 wire net10;
 wire net11;

 INVx3_ASAP7_75t_R _3_ (.A(net9),
    .Y(\q[0] ));
 INVx3_ASAP7_75t_R _4_ (.A(_0_),
    .Y(rn));
 BUFx8_ASAP7_75t_R clkbuf_0_ck (.A(ck),
    .Y(clknet_0_ck));
 BUFx8_ASAP7_75t_R clkbuf_1_0__f_ck (.A(clknet_0_ck),
    .Y(clknet_1_0__leaf_ck));
 BUFx8_ASAP7_75t_R clkbuf_1_1__f_ck (.A(clknet_0_ck),
    .Y(clknet_1_1__leaf_ck));
 BUFx2_ASAP7_75t_R hold10 (.A(net11),
    .Y(net9));
 BUFx2_ASAP7_75t_R hold11 (.A(\q[0] ),
    .Y(net10));
 BUFx2_ASAP7_75t_R hold12 (.A(_1_),
    .Y(net11));
 BUFx2_ASAP7_75t_R hold6 (.A(net7),
    .Y(net5));
 BUFx2_ASAP7_75t_R hold7 (.A(net3),
    .Y(net6));
 BUFx2_ASAP7_75t_R hold8 (.A(rst),
    .Y(net7));
 BUFx2_ASAP7_75t_R hold9 (.A(net5),
    .Y(net8));
 BUFx2_ASAP7_75t_R input4 (.A(net8),
    .Y(net3));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00000_0 (.A(rn),
    .Y(ot_outhold_n00000_0));
 BUFx4f_ASAP7_75t_R ot_ohdrv_00000_2 (.A(ot_outhold_n00000_1),
    .Y(ot_outhold_p00000));
 HB4xp67_ASAP7_75t_R ot_outhold_00000_1 (.A(ot_outhold_n00000_0),
    .Y(ot_outhold_n00000_1));
 BUFx2_ASAP7_75t_R output5 (.A(ot_outhold_p00000),
    .Y(rn4));
 DFFASRHQNx1_ASAP7_75t_R \q[0]$_DFF_PN0_  (.CLK(clknet_1_0__leaf_ck),
    .D(net),
    .QN(_1_),
    .RESETN(net6),
    .SETN(net1));
 TIEHIx1_ASAP7_75t_R \q[0]$_DFF_PN0__1  (.H(net));
 TIEHIx1_ASAP7_75t_R \q[0]$_DFF_PN0__2  (.H(net1));
 DFFASRHQNx1_ASAP7_75t_R \q[1]$_DFF_PN0_  (.CLK(clknet_1_1__leaf_ck),
    .D(net10),
    .QN(_0_),
    .RESETN(net6),
    .SETN(net2));
 TIEHIx1_ASAP7_75t_R \q[1]$_DFF_PN0__3  (.H(net2));
 assign rn = rn4;
endmodule
