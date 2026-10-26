`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HEAD LANE (b) STACKED SUB-CHILDREN (STW-S81c-COLLA2-LANE 10-22, steward decision 12:15): the static core adapter of
// ot_s81hd_lane (ot_s81hd_lane.sv documents the protocol) split into STACKED hard sub-children, each with its own local
// CTS root (<= ~1.4k sinks, <= 200 um tall), replacing the single adapter child of p8 (4,523 sinks on one root along the
// 583-um strip: pin-flop spread 163/170 ps TT, 140/162 ps FF).  Same registers and edges per bit as ot_s81hd_lane:
//   TX child  ot_s81hd_lsc_t<N>: N TX slices (ot_s81hd_lane_txs, unchanged) + their tx_d pin flops (txd_p) + its own
//             ot_rst_relay_tree3 (equal depth: release on edge 3, as the original single tree).  tv / cr come from the
//             kept ot_s81hd_kf copies in the control child (one copy per TX child, <= 12 slices each; the original had
//             2 copies of <= 18 slices): kf -> slice tv_q / cr_q is the same register -> register edge as before, now
//             a LANDED seam between two hard children.
//   CTL child ot_s81hd_lsc_r0m / ot_s81hd_lsc_rf: kf copies, RX pin flops (low bits / all bits), RX credit / overflow
//             check, fault flops, reset leaves for the lane (r_lane) and rxen (r_misc).
//   RX child  ot_s81hd_lsc_r1m: RX pin flops of the high bits (data, unreset).
// The adapter slices are replicas in lock step (identical inputs, identical reset release), so lo_v / the TX overflow
// fault come from the TOP TX slice (34, nearest the lane's lo_v pin) instead of slice 0: same value every cycle (the
// equivalence bench checks it against the original lane cycle by cycle).  Only the top TX child has lv / ovf ports.
// Seams: every signal between two sub-children leaves a flop and lands in a flop (kf -> tv_q/cr_q, slice ovf -> flt_q);
// no signal crosses a seam combinationally.
// ---------------------------------------------------------------------------------------------------------------------

// One 16-bit slice of the lane TX buffer with its own replica of the control (kept hierarchy, no parameters).
// Byte-identical body to ot_s81hd_lane.sv / ot_s81hd_lane_ha.sv.
(* keep_hierarchy = "yes" *) module ot_s81hd_lane_txs (
    input  wire        ck,
    input  wire        rn,
    input  wire        tv,          // tx_v pin (this slice's own pin flop)
    input  wire [15:0] td,
    input  wire        cr,          // lo_r credit pulse pin (own pin flop)
    output reg         lv,
    output reg  [15:0] ld,
    output reg         ovf
);
    (* keep = "true" *) reg tv_q, cr_q;
    reg [15:0] td_q;
    reg [15:0] q0, q1, q2;
    reg [2:0] wp, rp;               // one-hot
    reg [1:0] n;                    // occupancy 0..3
    reg [3:0] c;                    // credits in hand 0..8
    wire full = n == 2'd3;
    wire push = tv_q && !full;
    wire send = n != 2'd0 && c != 4'd0;
    always @(posedge ck) begin
        td_q <= td;
        if (push && wp[0]) q0 <= td_q;
        if (push && wp[1]) q1 <= td_q;
        if (push && wp[2]) q2 <= td_q;
        ld <= ({16{rp[0]}} & q0) | ({16{rp[1]}} & q1) | ({16{rp[2]}} & q2);   // loads every cycle (DFREE)
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin tv_q <= 1'b0; cr_q <= 1'b0; wp <= 3'b001; rp <= 3'b001; n <= 2'd0; c <= 4'd8; lv <= 1'b0; ovf <= 1'b0; end
        else begin
            tv_q <= tv; cr_q <= cr;
            if (push) wp <= {wp[1:0], wp[2]};
`ifdef OT_S81HD_LANE_MUT_RP
            if (send && !rp[2]) rp <= {rp[1:0], rp[2]};   // MUTANT: read pointer sticks on slot 2
`else
            if (send) rp <= {rp[1:0], rp[2]};
`endif
            n <= n + {1'b0, push} - {1'b0, send};
            c <= c + {3'd0, cr_q} - {3'd0, send};
            lv <= send;
`ifdef OT_S81HD_LANE_MUT_OVF
            ovf <= 1'b0;                                    // MUTANT: static-schedule overflow never flagged
`else
            ovf <= ovf | (tv_q && full);
`endif
        end
endmodule

// TX child body: NS slices over NB real data bits (NB <= 16*NS; the pad bits of the top slice are constant 0 exactly as
// the original txd_w pad).  Own reset relay tree (NS leaves, one per slice).
`define OT_LSC_TX_BODY(NS_, NB_) \
    localparam integer NS = NS_; \
    localparam integer NB = NB_; \
    wire [NS-1:0] rr; \
    ot_rst_relay_tree3 #(.REGIONS(NS)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); \
    reg [NB-1:0] txd_p; \
    always @(posedge ck) txd_p <= td; \
    wire [NS*16-1:0] txd_w; \
    wire [NS*16-1:0] lod_w; \
    wire [NS-1:0] lov_s, ovf_s; \
    genvar s; \
    generate if (NS*16 > NB) begin : g_pad \
        assign txd_w = {{(NS*16-NB){1'b0}}, txd_p}; \
    end else begin : g_nopad \
        assign txd_w = txd_p; \
    end endgenerate \
    generate for (s = 0; s < NS; s = s + 1) begin : g_txs \
        (* keep_hierarchy = "yes" *) ot_s81hd_lane_txs u_s (.ck(ck), .rn(rr[s]), .tv(tvk), .td(txd_w[16*s +: 16]), \
            .cr(crk), .lv(lov_s[s]), .ld(lod_w[16*s +: 16]), .ovf(ovf_s[s])); \
    end endgenerate \
    assign lod = lod_w[NB-1:0];

// ---- MAIN TX children: 3 x t9 (one master, slices 0..8 / 9..17 / 18..26) + t8 (slices 27..34, top: lv / ovf)
module ot_s81hd_lsc_t9 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [143:0]  td,
    input  wire          tvk,
    input  wire          crk,
    output wire [143:0]  lod
);
    `OT_LSC_TX_BODY(9, 144)
endmodule
module ot_s81hd_lsc_t8 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [120:0]  td,
    input  wire          tvk,
    input  wire          crk,
    output wire [120:0]  lod,
    output wire          lv,
    output wire          ovf
);
    `OT_LSC_TX_BODY(8, 121)
    assign lv = lov_s[NS-1];
    assign ovf = ovf_s[NS-1];
endmodule
// ---- FB TX children: 2 x t12 (one master, slices 0..11 / 12..23) + t11 (slices 24..34, top: lv / ovf)
module ot_s81hd_lsc_t12 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [191:0]  td,
    input  wire          tvk,
    input  wire          crk,
    output wire [191:0]  lod
);
    `OT_LSC_TX_BODY(12, 192)
endmodule
module ot_s81hd_lsc_t11 (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [168:0]  td,
    input  wire          tvk,
    input  wire          crk,
    output wire [168:0]  lod,
    output wire          lv,
    output wire          ovf
);
    `OT_LSC_TX_BODY(11, 169)
    assign lv = lov_s[NS-1];
    assign ovf = ovf_s[NS-1];
endmodule
`undef OT_LSC_TX_BODY

// Control child body: kept kf copies of tx_v / lo_r (one per TX child), RX pin flops for NRX low bits, credit check,
// fault flops, reset leaves {lane, rx, misc} (own tree3: release on edge 3 as the original).
`define OT_LSC_CTL_BODY(NT_, NRX_) \
    localparam integer NT = NT_; \
    localparam integer NRX = NRX_; \
    wire [2:0] rr; \
    ot_rst_relay_tree3 #(.REGIONS(3)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr)); \
    assign r_lane = rr[0]; \
    wire r_rx = rr[1], r_misc = rr[2]; \
    assign r_misc_o = r_misc; \
    genvar k; \
    generate for (k = 0; k < NT; k = k + 1) begin : g_kf \
        ot_s81hd_kf u_tv (.ck(ck), .d(tx_v), .q(tvk[k])); \
        ot_s81hd_kf u_cr (.ck(ck), .d(lo_r), .q(crk[k])); \
    end endgenerate \
    reg rv_q; reg [NRX-1:0] rd_q; reg cr_q; reg [3:0] snd; reg rx_f; \
    always @(posedge ck) rd_q <= li_d; \
    always @(posedge ck or negedge r_rx) \
        if (!r_rx) begin rv_q <= 1'b0; cr_q <= 1'b0; snd <= 4'd8; rx_f <= 1'b0; end \
        else begin \
            rv_q <= li_v; \
            cr_q <= li_v; \
            snd <= snd - {3'd0, li_v} + {3'd0, cr_q}; \
            rx_f <= rx_f | (li_v && snd == 4'd0); \
        end \
    assign li_r = cr_q; \
    assign rx_v = rv_q; \
    assign rx_d = rd_q; \
    reg [3:0] flt_q; \
    always @(posedge ck or negedge r_misc) if (!r_misc) flt_q <= 4'd0; else flt_q <= {rx_f | ovf_t, lf}; \
    assign flt = flt_q;

// MAIN control child: 4 kf copy pairs (t9 x3 + t8), RX bits 0..287.
module ot_s81hd_lsc_r0m (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire          lo_r,
    output wire [3:0]    tvk,
    output wire [3:0]    crk,
    input  wire          li_v,
    output wire          li_r,
    input  wire [287:0]  li_d,
    output wire [287:0]  rx_d,
    output wire          rx_v,
    input  wire [2:0]    lf,
    input  wire          ovf_t,
    output wire [3:0]    flt,
    output wire          r_lane,
    output wire          r_misc_o
);
    `OT_LSC_CTL_BODY(4, 288)
endmodule
// FB control child: 3 kf copy pairs (t12 x2 + t11), all RX bits 0..552.
module ot_s81hd_lsc_rf (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire          lo_r,
    output wire [2:0]    tvk,
    output wire [2:0]    crk,
    input  wire          li_v,
    output wire          li_r,
    input  wire [552:0]  li_d,
    output wire [552:0]  rx_d,
    output wire          rx_v,
    input  wire [2:0]    lf,
    input  wire          ovf_t,
    output wire [3:0]    flt,
    output wire          r_lane,
    output wire          r_misc_o
);
    `OT_LSC_CTL_BODY(3, 553)
endmodule
`undef OT_LSC_CTL_BODY

// MAIN RX child: RX pin flops of bits 288..552 (data, unreset; one edge as the original rd_q).
module ot_s81hd_lsc_r1m (
    input  wire          ck,
    input  wire [264:0]  li_d,
    output reg  [264:0]  rx_d
);
    always @(posedge ck) rx_d <= li_d;
endmodule
