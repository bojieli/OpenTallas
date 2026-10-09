`timescale 1ns/1ps
// dsfd_sp_collective (CLAUDE S81-PH, 2026-10-06): the S81 die collective slab, named and ported as the
// tools/dsrom_s81_fulldie.py r9 master WITH the contract's generator changes (f_vm 592 in, ts 3 in, t_vm 2100 out;
// results/rtl/s81_ph_20261006/collective/contract.json; ports physical/s81_ph_views/ports_ph/<die>/dsfd_sp_collective).
//   clocks: die PLL (ot_s81_pll_bb, hard IP) from refclk; pll_stream also clocks this slab; pll_serial / pll_hbm
//           pass through kept buffers.  Resets: ot_s81ph_coll_rstc (por -> lock -> stream, serial, hbm release).
//   links:  8 lanes (W0..W3 = lanes 0..3, E0..E3 = lanes 4..7): rX = the hub meso end block's {fault, live,
//           data 512, valid}; tdX = the 512-b beat, tfX its forwarded clock (= the slab clock, kept buffer; the
//           first station captures on its falling edge as for every r9 start block).
//   every die input is captured in a flop at the pin, every die output is launched from a flop (clock / reset
//   outputs: kept cells / reset flops).
module dsfd_sp_collective_ctrl #(parameter integer CTRL_ENABLE=0, CTRL_LANE=3) (
    input  wire [0:0]    refclk,
    input  wire [0:0]    por,
    input  wire [591:0]  f_vm,
    input  wire [2:0]    ts,
    input  wire [514:0]  rW0, rW1, rW2, rW3, rE0, rE1, rE2, rE3,
    output wire [0:0]    pll_stream, pll_serial, pll_hbm,
    output wire [0:0]    rst_stream, rst_serial, rst_hbm,
    input wire c_tx_v,output wire c_tx_r,input wire[511:0] c_tx_d,input wire c_tx_l,
    output wire c_rx_v,input wire c_rx_r,output wire[511:0] c_rx_d,output wire c_rx_l,output wire c_fault,
    output wire [2099:0] t_vm,
    output wire [511:0]  tdW0, tdW1, tdW2, tdW3, tdE0, tdE1, tdE2, tdE3,
    output wire [0:0]    tfW0, tfW1, tfW2, tfW3, tfE0, tfE1, tfE2, tfE3
);
`ifdef S81PH_COLL_V1
    initial $fatal(1,"control composition requires v2 core/lane tiles");
`else
    // CLAUDE S81-PH coll v2 (redesign pass, coll_m1 7 h in timing-driven placement at ~1M nets): the slab is a
    // composition of tiles: dsfd_coll_ck (PLL, reset sequencer), dsfd_coll_core (engine, VM queues, packer) and 8
    // lane tiles (dsfd_coll_lane_w: W0..W3 = lanes 0..3, dsfd_coll_lane_w mirrored MY: E0..E3 = lanes 4..7), joined by registered
    // 2-slot skid interfaces (physical/s81_ph_views/collective/composition.json).  S81PH_COLL_V1 = the v1 flat slab.
    dsfd_coll_ck u_ck (.refclk(refclk), .por(por), .pll_stream(pll_stream), .pll_serial(pll_serial), .pll_hbm(pll_hbm),
        .rst_stream(rst_stream), .rst_serial(rst_serial), .rst_hbm(rst_hbm));
    wire [7:0] lo_v, lo_r, li_v, li_r;
    wire [8*553-1:0] lo_d, li_d;
    wire [23:0] flt;
    wire [7:0] core_lo_v,core_lo_r,core_li_v,core_li_r;
    wire [8*553-1:0] core_lo_d,core_li_d;
    genvar a;
    generate for(a=0;a<8;a=a+1)begin:g_adapter
        if(a==CTRL_LANE)begin:g_ctrl
            ot_s81_ctrl_lane_adapter #(.ENABLE(CTRL_ENABLE)) u_adapter(
                .clk(pll_stream),.rst_n(rst_stream),.core_lo_v(core_lo_v[a]),.core_lo_r(core_lo_r[a]),.core_lo_d(core_lo_d[553*a+:553]),
                .core_li_v(core_li_v[a]),.core_li_r(core_li_r[a]),.core_li_d(core_li_d[553*a+:553]),
                .lane_lo_v(lo_v[a]),.lane_lo_r(lo_r[a]),.lane_lo_d(lo_d[553*a+:553]),
                .lane_li_v(li_v[a]),.lane_li_r(li_r[a]),.lane_li_d(li_d[553*a+:553]),
                .c_tx_v(c_tx_v),.c_tx_r(c_tx_r),.c_tx_d(c_tx_d),.c_tx_l(c_tx_l),
                .c_rx_v(c_rx_v),.c_rx_r(c_rx_r),.c_rx_d(c_rx_d),.c_rx_l(c_rx_l),.fault(c_fault));
        end else begin:g_normal
            assign lo_v[a]=core_lo_v[a];assign core_lo_r[a]=lo_r[a];assign lo_d[553*a+:553]=core_lo_d[553*a+:553];
            assign core_li_v[a]=li_v[a];assign li_r[a]=core_li_r[a];assign core_li_d[553*a+:553]=li_d[553*a+:553];
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if(CTRL_LANE<3||CTRL_LANE>7)$fatal(1,"control lane must be reserved pass-through3..7");
`endif
    dsfd_coll_core u_core (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .ts(ts), .t_vm(t_vm), .lo_v(core_lo_v), .lo_r(core_lo_r),
        .lo_d(core_lo_d), .li_v(core_li_v), .li_r(core_li_r), .li_d(core_li_d), .flt(flt));
    wire [514:0] rxl [0:7];
    wire [511:0] txl [0:7];
    wire [7:0] tfl;
    assign rxl[0] = rW0; assign rxl[1] = rW1; assign rxl[2] = rW2; assign rxl[3] = rW3;
    assign rxl[4] = rE0; assign rxl[5] = rE1; assign rxl[6] = rE2; assign rxl[7] = rE3;
    assign {tdE3, tdE2, tdE1, tdE0, tdW3, tdW2, tdW1, tdW0} = {txl[7], txl[6], txl[5], txl[4], txl[3], txl[2], txl[1], txl[0]};
    assign {tfE3[0], tfE2[0], tfE1[0], tfE0[0], tfW3[0], tfW2[0], tfW1[0], tfW0[0]} = tfl;
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_lane
        wire chb = !(g == 0 || g == 4);                 // lanes 0 (W0) and 4 (E0): UCIe ACK timeout
        if (g < 4) begin : g_w
            dsfd_coll_lane_w u_l (.ck(pll_stream), .rs(rst_stream), .chb(chb), .rx(rxl[g]), .tx(txl[g]), .tf(tfl[g]),
                .lo_v(lo_v[g]), .lo_r(lo_r[g]), .lo_d(lo_d[g*553 +: 553]), .li_v(li_v[g]), .li_r(li_r[g]),
                .li_d(li_d[g*553 +: 553]), .flt(flt[3*g +: 3]));
        end else begin : g_e
            dsfd_coll_lane_w u_l (.ck(pll_stream), .rs(rst_stream), .chb(chb), .rx(rxl[g]), .tx(txl[g]), .tf(tfl[g]),
                .lo_v(lo_v[g]), .lo_r(lo_r[g]), .lo_d(lo_d[g*553 +: 553]), .li_v(li_v[g]), .li_r(li_r[g]),
                .li_d(li_d[g*553 +: 553]), .flt(flt[3*g +: 3]));
        end
    end endgenerate
`endif
endmodule
