`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// HEAD LANE (b) (STW-S81c-COLLA2-VP 10-22, steward decision): ot_s81hd_lane with its STATIC ADAPTER HARDENED as its own
// child ot_s81hd_lane_adp (own CTS).  Same module name, ports, registers and edges as ot_s81hd_lane.sv (whose header
// documents the protocol); only the hierarchy changes:
//   u_ln  = dsfd_coll_lane_w_safe8_ntf (closed view, unchanged)
//   u_adp = ot_s81hd_lane_adp: reset relay tree, tx pin stage + kept copies, 35 TX slices, RX pin flops / credit / fault,
//           fault flops.  Every adapter<->lane signal is register -> register (slice lv/ld, cr_q, relay leaf r_lane out;
//           lane lo_r / li_v / li_d / flt in from the lane's pin registers): a landed seam between two hard children,
//           balanced by the parent spine on both children's routed boundary insertion.
//   rxen  = the one parent flop (the lane rx word's valid bit sits on the lane's W face, ~0.75 mm from the adapter).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81hd_lane (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          chb,
    input  wire [513:0]  rx,
    output wire [511:0]  tx,
    input  wire          tx_v,
    input  wire [552:0]  tx_d,
    output wire          rx_v,
    output wire [552:0]  rx_d,
    output wire [3:0]    flt
);
    wire r_lane, r_misc;
    // ---- lane rx word and receive enable (parent flop beside the lane's W face)
    reg rxen;
    always @(posedge ck or negedge r_misc) if (!r_misc) rxen <= 1'b0; else rxen <= 1'b1;
    wire [514:0] lrx = {rx[512], rx[513], rx[511:0], rxen};
    wire lo_v, lo_r, li_v, li_r; wire [552:0] lo_d, li_d; wire [2:0] lf;
    dsfd_coll_lane_w_safe8_ntf u_ln (.ck(ck), .rs(r_lane), .chb(chb), .rx(lrx), .tx(tx), .lo_v(lo_v), .lo_r(lo_r),
        .lo_d(lo_d), .li_v(li_v), .li_r(li_r), .li_d(li_d), .flt(lf));
    ot_s81hd_lane_adp u_adp (.ck(ck), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .rx_v(rx_v), .rx_d(rx_d), .flt(flt),
        .lo_v(lo_v), .lo_d(lo_d), .lo_r(lo_r), .li_v(li_v), .li_d(li_d), .li_r(li_r), .lf(lf), .r_lane(r_lane), .r_misc_o(r_misc));
endmodule
module ot_s81hd_lane_adp (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          tx_v,
    input  wire [552:0]  tx_d,
    output wire          rx_v,
    output wire [552:0]  rx_d,
    output wire [3:0]    flt,
    output wire          lo_v,
    output wire [552:0]  lo_d,
    input  wire          lo_r,
    input  wire          li_v,
    input  wire [552:0]  li_d,
    output wire          li_r,
    input  wire [2:0]    lf,
    output wire          r_lane,
    output wire          r_misc_o
);
    localparam integer NS = 35;                 // 35 x 16 = 560 >= 553
    localparam integer NR = NS + 3;             // reset leaves: slices, lane, rx, misc
    wire [NR-1:0] rr;
    ot_rst_relay_tree3 #(.REGIONS(NR)) u_rr (.clk(ck), .rst_n_in(rst_n), .rst_n(rr));
    assign r_lane = rr[NS]; wire r_rx = rr[NS + 1], r_misc = rr[NS + 2];
    assign r_misc_o = r_misc;
    // ---- TX: bit-sliced 3-flit buffer, credit sender
    // pin stage: tx_d lands here, tx_v / lo_r land in 2 kept copies each (<= 18 slices per copy)
    reg [552:0] txd_p;
    always @(posedge ck) txd_p <= tx_d;
    wire [1:0] tv_c, cr_c;
    ot_s81hd_kf u_tv0 (.ck(ck), .d(tx_v), .q(tv_c[0])); ot_s81hd_kf u_tv1 (.ck(ck), .d(tx_v), .q(tv_c[1]));
    ot_s81hd_kf u_cr0 (.ck(ck), .d(lo_r), .q(cr_c[0])); ot_s81hd_kf u_cr1 (.ck(ck), .d(lo_r), .q(cr_c[1]));
    wire [NS*16-1:0] txd_w = {{(NS*16-553){1'b0}}, txd_p};
    wire [NS*16-1:0] lod_w;
    wire [NS-1:0] lov_s, ovf_s;
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_txs
        (* keep_hierarchy = "yes" *) ot_s81hd_lane_txs u_s (.ck(ck), .rn(rr[s]), .tv(tv_c[s % 2]), .td(txd_w[16*s +: 16]),
            .cr(cr_c[s % 2]), .lv(lov_s[s]), .ld(lod_w[16*s +: 16]), .ovf(ovf_s[s]));
    end endgenerate
    assign lo_v = lov_s[0];
    assign lo_d = lod_w[552:0];
`ifndef SYNTHESIS
`ifdef OT_S81HD_LANE_CHK
    always @(posedge ck) if (rr[0] && (lov_s != {NS{1'b0}}) && (lov_s != {NS{1'b1}})) $fatal(1, "ot_s81hd_lane: TX slices out of lock step");
`endif
`endif
    // ---- RX: always-accept pin flops, credit pulse per beat, would-overflow check against the sender's credits
    reg rv_q; reg [552:0] rd_q; reg cr_q; reg [3:0] snd; reg rx_f;
    always @(posedge ck) rd_q <= li_d;
    always @(posedge ck or negedge r_rx)
        if (!r_rx) begin rv_q <= 1'b0; cr_q <= 1'b0; snd <= 4'd8; rx_f <= 1'b0; end
        else begin
            rv_q <= li_v;
            cr_q <= li_v;                                    // the beat is taken now: credit back next edge
            snd <= snd - {3'd0, li_v} + {3'd0, cr_q};
            rx_f <= rx_f | (li_v && snd == 4'd0);
        end
    assign li_r = cr_q;
    assign rx_v = rv_q;
    assign rx_d = rd_q;
    // ---- faults
    reg [3:0] flt_q;
    always @(posedge ck or negedge r_misc) if (!r_misc) flt_q <= 4'd0; else flt_q <= {rx_f | ovf_s[0], lf};
    assign flt = flt_q;
endmodule
// One 16-bit slice of the lane TX buffer with its own replica of the control (kept hierarchy, no parameters).
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
