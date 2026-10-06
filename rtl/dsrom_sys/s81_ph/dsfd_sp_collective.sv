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
endmodule

// a kept clock buffer (keep_hierarchy: the clock-output / forwarded-clock driver stays a cell)
(* keep_hierarchy *)
module ot_s81ph_ckbuf (input wire a, output wire y);
    assign y = a;
endmodule
