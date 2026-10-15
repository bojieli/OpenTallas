`timescale 1ns/1ps
// dsfd_coll_ck -- clock TILE of the S81 collective slab (CLAUDE S81-PH coll v2): the die PLL (ot_s81_pll_bb hard
// macro), the reset sequencer ot_s81ph_coll_rstc (refclk domain) and the kept clock-output buffers, as in the v1
// slab.  pll_stream is the stream clock of every collective tile (die clock tree root).
module dsfd_coll_ck (
    input  wire [0:0] refclk,
    input  wire [0:0] por,
    output wire [0:0] pll_stream, pll_serial, pll_hbm,
    output wire [0:0] rst_stream, rst_serial, rst_hbm
);
    wire ck_s, ck_v, ck_h, lock, pd;
    ot_s81_pll_bb u_pll (.refclk(refclk[0]), .pd(pd), .ck_stream(ck_s), .ck_serial(ck_v), .ck_hbm(ck_h), .lock(lock));
    ot_s81ph_ckbuf u_ob_s (.a(ck_s), .y(pll_stream[0]));
    ot_s81ph_ckbuf u_ob_v (.a(ck_v), .y(pll_serial[0]));
    ot_s81ph_ckbuf u_ob_h (.a(ck_h), .y(pll_hbm[0]));
    wire rs_n, rv_n, rh_n;
    ot_s81ph_coll_rstc u_rstc (.refclk(refclk[0]), .por_n(por[0]), .lock(lock), .pll_pd(pd),
        .rst_stream_n(rs_n), .rst_serial_n(rv_n), .rst_hbm_n(rh_n), .seq_state());
    assign rst_stream[0] = rs_n;
    assign rst_serial[0] = rv_n;
    assign rst_hbm[0] = rh_n;
endmodule
