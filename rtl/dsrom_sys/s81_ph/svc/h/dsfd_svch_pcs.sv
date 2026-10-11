`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// CLAUDE s81die-1011/ctrl svch: dsfd_svch_pcs -- the hardened PER-PC SERVICE SLICE of a scan-service quadrant
// (8 per dsfd_svc_quad, slice i directly above u_pc[8 QID + i], 265.584 um pitch: S face abutted to the PC tile's
// N face, N face to the quadrant's lane ends).  One ot_s81_svch_pcsvc with NP 1 (the PC's 3-way pipelined arbiter:
// requester queues -> registered candidates -> registered rq, DQ credits, landing reservation) between:
//   A lane  (index reader)   request receiver FIFO (credits out), responses valid-only out (landing credits in)
//   B lane  (window stream)  same
//   G lane  (quadrant G hub) request receiver FIFO (credits out), responses on a credit lane to the hub, write
//                            completions as a pulse vector to the hub
// Every incoming signal (lanes, credits, the PC face's responses / rk / wd) is captured by a pin flop; every output
// leaves a flop.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svch_pcs #(
    parameter integer QID = 0,
    parameter integer PCL = 0,               // local PC index 0..7
    parameter integer NG = 13,
    parameter integer DA = 14,               // A request receiver depth (2 NRI + 8)
    parameter integer DB = 14,               // B request receiver depth (2 NRH + 8)
    parameter integer DG = 8,                // G receiver / sender depth to the hub (adjacent)
    parameter integer DRA = 64,
    parameter integer DRB = 64,
    parameter integer HDLY = 0               // > 0: HDLY inverter pairs (keep_hierarchy, logically identity) in front of
                                             // the input pin flops and the G-response output register (hold-only miss
                                             // of svch_pcs-e1d02f5ae-tc: FF -2.88 ps at pdat / bqd / gqd / u_gtx.o_d)
) (
    input  wire [0:0]    ck,
    input  wire [0:0]    rst,
    // PC tile N face
    output wire [340:0]  qrq,
    input  wire [0:0]    qrk, qwd, qrv,
    input  wire [255:0]  qr_data,
    input  wire [16:0]   qr_tag,
    input  wire [3:0]    qr_beat,
    // A lane
    input  wire [0:0]    aq_v, input wire [49:0] aq_d, output wire [0:0] aq_c,
    output wire [0:0]    ar_v, output wire [275:0] ar_d, input wire [0:0] ar_c,
    // B lane
    input  wire [0:0]    bq_v, input wire [45:0] bq_d, output wire [0:0] bq_c,
    output wire [0:0]    br_v, output wire [271:0] br_d, input wire [0:0] br_c,
    // G (hub)
    input  wire [0:0]    gq_v, input wire [343:0] gq_d, output wire [0:0] gq_c,
    output wire [0:0]    gr_v, output wire [275:0] gr_d, input wire [0:0] gr_c,
    output wire [NG-1:0] gwd,
    output wire [0:0]    fo
);
    wire clk = ck[0];
    reg [1:0] rs;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    wire [5:0] vin_d;
    reg aqv, bqv, gqv, arc, brc, grc; reg [49:0] aqd; reg [45:0] bqd; reg [343:0] gqd;
    always @(posedge clk or negedge rn)
        if (!rn) begin aqv <= 0; bqv <= 0; gqv <= 0; arc <= 0; brc <= 0; grc <= 0; end
        else begin aqv <= vin_d[5]; bqv <= vin_d[4]; gqv <= vin_d[3]; arc <= ar_c[0]; brc <= br_c[0]; grc <= gr_c[0]; end
    wire [49:0] aq_dd; wire [45:0] bq_dd; wire [343:0] gq_dd; wire [255:0] qr_data_d; wire [16:0] qr_tag_d; wire [3:0] qr_beat_d;
    ot_s81_svch_hdly #(.W(50 + 46 + 344 + 256 + 17 + 4 + 6), .N(HDLY)) u_hdi (
        .a({aq_d, bq_d, gq_d, qr_data, qr_tag, qr_beat, aq_v[0], bq_v[0], gq_v[0], qrk[0], qwd[0], qrv[0]}),
        .y({aq_dd, bq_dd, gq_dd, qr_data_d, qr_tag_d, qr_beat_d, vin_d}));
    always @(posedge clk) begin aqd <= aq_dd; bqd <= bq_dd; gqd <= gq_dd; end
    // PC-face pin flops (the ctrl response / credit / write-done side; +1 cycle, credit round trip +1)
    reg pk, pw, pv; reg [255:0] pdat; reg [16:0] ptag; reg [3:0] pbeat;
    always @(posedge clk or negedge rn) if (!rn) begin pk <= 0; pw <= 0; pv <= 0; end else begin pk <= vin_d[2]; pw <= vin_d[1]; pv <= vin_d[0]; end
    always @(posedge clk) begin pdat <= qr_data_d; ptag <= qr_tag_d; pbeat <= qr_beat_d; end
    wire a_v, a_r, b_v, b_r, g_v, g_r, ova, ovb, ovg; wire [49:0] a_d; wire [45:0] b_d; wire [343:0] g_d;
    ot_s81_svch_crx #(.W(50), .DEPTH(DA)) u_arx (.clk(clk), .rst_n(rn), .i_v(aqv), .i_d(aqd), .o_v(a_v), .o_r(a_r), .o_d(a_d),
        .c_out(aq_c[0]), .ovf(ova));
    ot_s81_svch_crx #(.W(46), .DEPTH(DB)) u_brx (.clk(clk), .rst_n(rn), .i_v(bqv), .i_d(bqd), .o_v(b_v), .o_r(b_r), .o_d(b_d),
        .c_out(bq_c[0]), .ovf(ovb));
    ot_s81_svch_crx #(.W(344), .DEPTH(DG)) u_grx (.clk(clk), .rst_n(rn), .i_v(gqv), .i_d(gqd), .o_v(g_v), .o_r(g_r), .o_d(g_d),
        .c_out(gq_c[0]), .ovf(ovg));
    wire go_v, go_r; wire [275:0] go_d; wire pf; wire [7:0] pfc;
    ot_s81_svch_pcsvc #(.QID(QID), .NP(1), .PC0(PCL), .NG(NG), .DRA(DRA), .DRB(DRB)) u_pcs (
        .clk(clk), .rst_n(rn),
        .a_v(a_v), .a_r(a_r), .a_d(a_d), .ar_v(ar_v), .ar_d(ar_d), .ar_c(arc),
        .b_v(b_v), .b_r(b_r), .b_d(b_d), .br_v(br_v), .br_d(br_d), .br_c(brc),
        .g_v(g_v), .g_r(g_r), .g_d(g_d), .go_v(go_v), .go_r(go_r), .go_d(go_d), .gwd(gwd),
        .rq(qrq), .rk(pk), .rv(pv), .r_tag(ptag), .r_beat(pbeat), .r_data(pdat), .wd(pw),
        .fault(pf), .fault_code(pfc));
    wire [275:0] go_dd;
    ot_s81_svch_hdly #(.W(276), .N(HDLY)) u_hdo (.a(go_d), .y(go_dd));
    ot_s81_svch_ctx #(.W(276), .DEPTH(DG)) u_gtx (.clk(clk), .rst_n(rn), .i_v(go_v), .i_r(go_r), .i_d(go_dd),
        .o_v(gr_v[0]), .o_d(gr_d), .c_in(grc));
    reg flt;
    always @(posedge clk or negedge rn) if (!rn) flt <= 1'b0; else if (pf | ova | ovb | ovg) flt <= 1'b1;
    assign fo[0] = flt;
endmodule

// ---------------------------------------------------------------------------------------------------------------
// ot_s81_svch_ghub: the quadrant's G hub (in dsfd_svc_quad, at the middle of its PC row).  G requests from the
// home's lane (one receiver FIFO upstream) are steered by their local PC field to that slice's credit lane (a
// request whose quadrant field is not QID is a sticky fault and is dropped); the 8 slices' G responses land in
// per-slice receiver FIFOs and leave one a cycle through a REGISTERED 8-way round robin onto the hub's egress;
// the slices' write-completion pulses are summed per port (one pulse a cycle per port, counters).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_svch_ghub #(
    parameter integer QID = 0,
    parameter integer NG = 13,
    parameter integer DG = 8
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              i_v,
    output wire              i_r,
    input  wire [343:0]      i_d,
    output wire [7:0]        sq_v,
    output wire [8*344-1:0]  sq_d,
    input  wire [7:0]        sq_c,
    input  wire [7:0]        sr_v,
    input  wire [8*276-1:0]  sr_d,
    output wire [7:0]        sr_c,
    input  wire [8*NG-1:0]   swd,
    output reg               o_v,
    input  wire              o_r,
    output reg  [275:0]      o_d,
    output reg  [NG-1:0]     gwd,
    output reg               fault
);
    wire [2:0] tp = i_d[341:339];
    wire mine = i_d[343:342] == 2'(QID);
    wire [7:0] tx_r;
    assign i_r = !mine || tx_r[tp];
    genvar gp;
    wire [7:0] rx_v, ovf; reg [7:0] rx_r; wire [275:0] rx_d [0:7];
    reg [7:0] sqc, srv; reg [8*276-1:0] srd; reg [8*NG-1:0] swdq;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin sqc <= 0; srv <= 0; swdq <= 0; end else begin sqc <= sq_c; srv <= sr_v; swdq <= swd; end
    always @(posedge clk) srd <= sr_d;
    generate for (gp = 0; gp < 8; gp = gp + 1) begin : g_s
        ot_s81_svch_ctx #(.W(344), .DEPTH(DG)) u_tx (.clk(clk), .rst_n(rst_n), .i_v(i_v && mine && tp == 3'(gp)),
            .i_r(tx_r[gp]), .i_d(i_d), .o_v(sq_v[gp]), .o_d(sq_d[gp*344 +: 344]), .c_in(sqc[gp]));
        ot_s81_svch_crx #(.W(276), .DEPTH(DG)) u_rx (.clk(clk), .rst_n(rst_n), .i_v(srv[gp]), .i_d(srd[gp*276 +: 276]),
            .o_v(rx_v[gp]), .o_r(rx_r[gp]), .o_d(rx_d[gp]), .c_out(sr_c[gp]), .ovf(ovf[gp]));
    end endgenerate
    reg [2:0] rr; reg f; reg [2:0] pk; integer s, k, p;
    always @(*) begin
        rx_r = 0; f = 1'b0; pk = 0;
        if (!o_v || o_r)
            for (s = 0; s < 8; s = s + 1)
                if (!f && rx_v[3'(32'(rr) + s)]) begin f = 1'b1; pk = 3'(32'(rr) + s); end
        if (f) rx_r[pk] = 1'b1;
    end
    always @(posedge clk) if (f) o_d <= rx_d[pk];
    reg [5:0] wdc [0:NG-1]; reg [3:0] wadd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin o_v <= 1'b0; rr <= 0; gwd <= 0; fault <= 1'b0; for (k = 0; k < NG; k = k + 1) wdc[k] <= 0; end
        else begin
            if (o_v && o_r) o_v <= 1'b0;
            if (f) begin o_v <= 1'b1; rr <= pk + 1'b1; end
            if (i_v && !mine) fault <= 1'b1;
            if (|ovf) fault <= 1'b1;
            for (k = 0; k < NG; k = k + 1) begin
                wadd = 0;
                for (p = 0; p < 8; p = p + 1) wadd = wadd + 4'(swdq[p*NG + k]);
                gwd[k] <= (wdc[k] != 0) || (wadd != 0);
                wdc[k] <= wdc[k] + 6'(wadd) - 6'((wdc[k] != 0) || (wadd != 0));
            end
        end
endmodule
