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
module dsfd_sp_collective (
    input  wire [0:0]    refclk,
    input  wire [0:0]    por,
    input  wire [591:0]  f_vm,
    input  wire [2:0]    ts,
    input  wire [514:0]  rW0, rW1, rW2, rW3, rE0, rE1, rE2, rE3,
    output wire [0:0]    pll_stream, pll_serial, pll_hbm,
    output wire [0:0]    rst_stream, rst_serial, rst_hbm,
    output wire [2099:0] t_vm,
    output wire [511:0]  tdW0, tdW1, tdW2, tdW3, tdE0, tdE1, tdE2, tdE3,
    output wire [0:0]    tfW0, tfW1, tfW2, tfW3, tfE0, tfE1, tfE2, tfE3
);
`ifndef S81PH_COLL_V1
    // CLAUDE S81-PH coll v2 (redesign pass, coll_m1 7 h in timing-driven placement at ~1M nets): the slab is a
    // composition of tiles: dsfd_coll_ck (PLL, reset sequencer), dsfd_coll_core (engine, VM queues, packer) and 8
    // lane tiles (dsfd_coll_lane_w: W0..W3 = lanes 0..3, dsfd_coll_lane_w mirrored MY: E0..E3 = lanes 4..7), joined by registered
    // 2-slot skid interfaces (physical/s81_ph_views/collective/composition.json).  S81PH_COLL_V1 = the v1 flat slab.
    dsfd_coll_ck u_ck (.refclk(refclk), .por(por), .pll_stream(pll_stream), .pll_serial(pll_serial), .pll_hbm(pll_hbm),
        .rst_stream(rst_stream), .rst_serial(rst_serial), .rst_hbm(rst_hbm));
    wire [7:0] lo_v, lo_r, li_v, li_r;
    wire [8*553-1:0] lo_d, li_d;
    wire [23:0] flt;
`ifdef OT_S81PH_COLL_SPLIT
    // redesign-ds 2026-10-09: the core column as three abutted tiles (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv):
    // bottom dsfd_coll_cb (VM interface, output queue, lanes 0 / 4), middle dsfd_coll_ce (engine, queues, packer,
    // lanes 1, 2, 5, 6), top dsfd_coll_ct (lanes 3 / 7); seams of registered skids / pin registers.
    wire [591:0] s_fvm; wire [5:0] s_fltu, s_fltd;
    wire s_lo0_v, s_lo0_r, s_li0_v, s_li0_r, s_lo4_v, s_lo4_r, s_li4_v, s_li4_r;
    wire s_lo3_v, s_lo3_r, s_li3_v, s_li3_r, s_lo7_v, s_lo7_r, s_li7_v, s_li7_r;
    wire [552:0] s_lo0_d, s_li0_d, s_lo4_d, s_li4_d, s_lo3_d, s_li3_d, s_lo7_d, s_li7_d;
    wire s_bw_v, s_bw_cr, s_bw_flt; wire [2099:1] s_bw_d;
    dsfd_coll_cb u_cb (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .ts(ts), .t_vm(t_vm),
        .wlo_v(lo_v[0]), .wlo_r(lo_r[0]), .wlo_d(lo_d[0*553 +: 553]), .wli_v(li_v[0]), .wli_r(li_r[0]), .wli_d(li_d[0*553 +: 553]), .wflt(flt[0 +: 3]),
        .elo_v(lo_v[4]), .elo_r(lo_r[4]), .elo_d(lo_d[4*553 +: 553]), .eli_v(li_v[4]), .eli_r(li_r[4]), .eli_d(li_d[4*553 +: 553]), .eflt(flt[12 +: 3]),
        .fvm_u(s_fvm), .flt_u(s_fltu),
        .lo0_v(s_lo0_v), .lo0_r(s_lo0_r), .lo0_d(s_lo0_d), .li0_v(s_li0_v), .li0_r(s_li0_r), .li0_d(s_li0_d),
        .lo4_v(s_lo4_v), .lo4_r(s_lo4_r), .lo4_d(s_lo4_d), .li4_v(s_li4_v), .li4_r(s_li4_r), .li4_d(s_li4_d),
        .bw_v(s_bw_v), .bw_d(s_bw_d), .bw_cr(s_bw_cr), .bw_flt(s_bw_flt));
    dsfd_coll_ce u_ce (.ck(pll_stream), .rs(rst_stream),
        .wlo_v(lo_v[2:1]), .wlo_r(lo_r[2:1]), .wlo_d(lo_d[1*553 +: 2*553]), .wli_v(li_v[2:1]), .wli_r(li_r[2:1]), .wli_d(li_d[1*553 +: 2*553]), .wflt(flt[3 +: 6]),
        .elo_v(lo_v[6:5]), .elo_r(lo_r[6:5]), .elo_d(lo_d[5*553 +: 2*553]), .eli_v(li_v[6:5]), .eli_r(li_r[6:5]), .eli_d(li_d[5*553 +: 2*553]), .eflt(flt[15 +: 6]),
        .fvm_u(s_fvm), .flt_u(s_fltu),
        .lo0_v(s_lo0_v), .lo0_r(s_lo0_r), .lo0_d(s_lo0_d), .li0_v(s_li0_v), .li0_r(s_li0_r), .li0_d(s_li0_d),
        .lo4_v(s_lo4_v), .lo4_r(s_lo4_r), .lo4_d(s_lo4_d), .li4_v(s_li4_v), .li4_r(s_li4_r), .li4_d(s_li4_d),
        .bw_v(s_bw_v), .bw_d(s_bw_d), .bw_cr(s_bw_cr), .bw_flt(s_bw_flt),
        .lo3_v(s_lo3_v), .lo3_r(s_lo3_r), .lo3_d(s_lo3_d), .li3_v(s_li3_v), .li3_r(s_li3_r), .li3_d(s_li3_d),
        .lo7_v(s_lo7_v), .lo7_r(s_lo7_r), .lo7_d(s_lo7_d), .li7_v(s_li7_v), .li7_r(s_li7_r), .li7_d(s_li7_d), .flt_d(s_fltd));
    dsfd_coll_ct u_ct (.ck(pll_stream), .rs(rst_stream),
        .wlo_v(lo_v[3]), .wlo_r(lo_r[3]), .wlo_d(lo_d[3*553 +: 553]), .wli_v(li_v[3]), .wli_r(li_r[3]), .wli_d(li_d[3*553 +: 553]), .wflt(flt[9 +: 3]),
        .elo_v(lo_v[7]), .elo_r(lo_r[7]), .elo_d(lo_d[7*553 +: 553]), .eli_v(li_v[7]), .eli_r(li_r[7]), .eli_d(li_d[7*553 +: 553]), .eflt(flt[21 +: 3]),
        .lo3_v(s_lo3_v), .lo3_r(s_lo3_r), .lo3_d(s_lo3_d), .li3_v(s_li3_v), .li3_r(s_li3_r), .li3_d(s_li3_d),
        .lo7_v(s_lo7_v), .lo7_r(s_lo7_r), .lo7_d(s_lo7_d), .li7_v(s_li7_v), .li7_r(s_li7_r), .li7_d(s_li7_d), .flt_d(s_fltd));
`else
    dsfd_coll_core u_core (.ck(pll_stream), .rs(rst_stream), .f_vm(f_vm), .ts(ts), .t_vm(t_vm), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(flt));
`endif
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
`else
    wire ck_s, ck_v, ck_h, lock, pd;
    ot_s81_pll_bb u_pll (.refclk(refclk[0]), .pd(pd), .ck_stream(ck_s), .ck_serial(ck_v), .ck_hbm(ck_h), .lock(lock));
    wire clk = ck_s;
    ot_s81ph_ckbuf u_ob_s (.a(ck_s), .y(pll_stream[0]));
    ot_s81ph_ckbuf u_ob_v (.a(ck_v), .y(pll_serial[0]));
    ot_s81ph_ckbuf u_ob_h (.a(ck_h), .y(pll_hbm[0]));
    wire rs_n, rv_n, rh_n;
    ot_s81ph_coll_rstc u_rstc (.refclk(refclk[0]), .por_n(por[0]), .lock(lock), .pll_pd(pd),
        .rst_stream_n(rs_n), .rst_serial_n(rv_n), .rst_hbm_n(rh_n), .seq_state());
    assign rst_stream[0] = rs_n;
    assign rst_serial[0] = rv_n;
    assign rst_hbm[0] = rh_n;
    // this slab's own stream-domain reset (2-flop synchronised release)
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs_n) if (!rs_n) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    // pin registers
    reg [8*515-1:0] lr;
    reg [591:0] fv_r;
    reg [2:0] ts_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lr <= 0; fv_r <= 0; ts_r <= 0; end
        else begin lr <= {rE3, rE2, rE1, rE0, rW3, rW2, rW1, rW0}; fv_r <= f_vm; ts_r <= ts; end
    wire [8*512-1:0] lt;
    ot_s81ph_coll_core u_core (.clk(clk), .rst_n(rst_n), .lane_rx(lr), .lane_tx(lt), .f_vm(fv_r), .ts(ts_r),
        .t_vm(t_vm), .fault(), .rank(), .eng_en());
    assign {tdE3, tdE2, tdE1, tdE0, tdW3, tdW2, tdW1, tdW0} = lt;
    ot_s81ph_ckbuf u_f0 (.a(clk), .y(tfW0[0]));
    ot_s81ph_ckbuf u_f1 (.a(clk), .y(tfW1[0]));
    ot_s81ph_ckbuf u_f2 (.a(clk), .y(tfW2[0]));
    ot_s81ph_ckbuf u_f3 (.a(clk), .y(tfW3[0]));
    ot_s81ph_ckbuf u_f4 (.a(clk), .y(tfE0[0]));
    ot_s81ph_ckbuf u_f5 (.a(clk), .y(tfE1[0]));
    ot_s81ph_ckbuf u_f6 (.a(clk), .y(tfE2[0]));
    ot_s81ph_ckbuf u_f7 (.a(clk), .y(tfE3[0]));
`endif
endmodule
// ot_s81ph_ckbuf: rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
