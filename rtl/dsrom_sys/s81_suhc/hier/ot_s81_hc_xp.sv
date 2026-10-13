`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81 HC POST express (stream s81hc-express-1013, 2026-10-13; coordinator decision 03:40 PT in el1011-s81die.log).
//
// The serial column chain delivers a POST beat to the farthest half-octet 105 cycles after the sequencer and brings its
// completion back in 121-122 (measured, results/rtl/s81hc_throughput_20261013): 286-287 cycles against the immutable
// price of 112.9.  The express moves the job ACCEPT / DISPATCH / COMPLETION point to the corridor midpoint and reaches
// the 24 regions (8 a column, 2-3 half-octets each, none crossing the corridor) point to point:
//
//   ot_s81_hc_xmid   midpoint station: the engine adapter (cck / sk CDC, die command / done pins), the dispatcher (POST
//                    here, every other kind forwarded to ot_s81_hc_cseq and its done brought back), the POST go word,
//                    the per-region ACK ledger and the in-order global beat pointer (y credit return, done).
//   ot_s81_hc_xyacc  slab-face y accept: valid / ready on a credit of YQ beats, returned per globally complete beat.
//   ot_s81_hc_xrs    region station at the region head: ONE registered stage on the whole forward bundle (reset, fv,
//                    fd and the NORM chunk carry cy together), the region's y slice FIFO, the coefficient-epoch gate
//                    and the beat injector.  Injected beats use the tiles' existing pins, so the tiles (ot_s81_hc_cth
//                    hard leaves) are unchanged; the region's tiles get them through the existing y-shift hops.
//   ot_s81_hc_xtap   per half-octet: registered AND of its 8 hc_post lane-pair write-back strobes (+ fault OR).
//   ot_s81_hc_xrc    region collector at the region's midpoint-facing end: per-tile beat counters, one ACK a beat.
//   ot_s81_hc_xlink  a point-to-point run of registered relay stages, each <= G_REACH (500 um) of v13 wire.
//   ot_s81_hc_xcol   one column: chain + corridor stations + regions + links (composition, never hardened as one).
//
// What is preserved: (1) coefficient epochs -- HLOAD / COEF / GAIN beats carry a generation and a last flag in the
// POST-only PB bits (ot_s81_hc_cseq XP=1); a region injects a POST only after the LAST beat of the generation the
// midpoint dispatched it under has passed its station (+ SETTLE), and the injected beat then follows that beat through
// the same tile chain, so every tile sees the two in issue order, as on the serial chain.  (2) every beat and ACK --
// 20 beats x 24 regions, each ACK checked for job tag and in-order beat number; the done needs all of them.  (3) the
// NORM golden order -- the station delays cy with fv, every column gets the same number of stations (lockstep at the
// combine tile), and NORM / HSTORE / HLOAD / COEF / GAIN still run on the serial chain.
// XMUT (bench negative controls, 0 in silicon): 1 the epoch gate is ignored; 2 one region drops one ACK; 3 the stations
// do not delay cy (NORM chunk carry out of order).  MUT 1 / 2 / 4 / 5 as ot_s81_hc_cseq (no write-back, wrong slot,
// early retirement, wrong tag).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xlink #(
    parameter integer W = 1, N = 1
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         v_i,
    input  wire [W-1:0] d_i,
    output wire         v_o,
    output wire [W-1:0] d_o
);
    ot_hdc_delay #(.W(1), .D(N), .RESET(1)) u_v (.clk(clk), .rst_n(rst_n), .d(v_i), .q(v_o));
    ot_hdc_delay #(.W(W), .D(N)) u_d (.clk(clk), .rst_n(rst_n), .d(d_i), .q(d_o));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xtap: half-octet completion tap (centre band, beside ot_s81_hc_ctra which already collects these flops).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xtap (
    input  wire       clk,
    input  wire       srs,
    input  wire [7:0] hov,          // ot_s81_hc_ctpl hov_d: the lane pair's output beat (write-back strobe + 1)
    input  wire [7:0] hnz,
    input  wire [7:0] pflt,
    output reg        tb,           // one completed beat of the half-octet
    output reg        tf
);
    reg [1:0] rsr;
    always @(posedge clk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin tb <= 1'b0; tf <= 1'b0; end
        else begin tb <= &hov; tf <= ((|hov) && !(&hov)) | (|hnz) | (|pflt); end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xrs: region station.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xrs #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, RSZ = 3, YD = 64, SETTLE = 8, XMUT = 0
) (
    input  wire                 clk,
    input  wire                 srs,
    input  wire                 rst_i,
    input  wire [FVW-1:0]       fv_i,
    input  wire [FDW-1:0]       fd_i,
    input  wire [127:0]         cy_i,
    output reg                  rst_o,
    output reg  [FVW-1:0]       fv_o,
    output reg  [FDW-1:0]       fd_o,
    output wire [127:0]         cy_o,
    input  wire                 go_v,
    input  wire [GD-1:0]        go_d,       // {gen[7:0], wb, hs, cs, tag[7:0]}
    input  wire                 y_v,
    input  wire [YRW-1:0]       y_d,
    output reg                  flt
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32, GT = GS / 2;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_PB = 5 + S_RD * 16, O_D = O_PB + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FVW = S_RD + 5;
    localparam integer YRW = RSZ * GT * 32, GD = 19, NR = D / NG;
    reg [1:0] rsr;
    always @(posedge clk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    // pin flops of the express inputs
    reg            gv, yv;
    reg [GD-1:0]   gd;
    reg [YRW-1:0]  yd;
    always @(posedge clk or negedge rs_n) if (!rs_n) begin gv <= 1'b0; yv <= 1'b0; end else begin gv <= go_v; yv <= y_v; end
    always @(posedge clk) begin gd <= go_d; yd <= y_d; end
    wire [YRW-1:0] yh;
    wire           yhv, yovf;
    reg            inj;
    ot_fifo_sram_fwft #(.W(YRW), .DEPTH(YD), .MACRO(0), .ESL(0)) u_yf (.clk(clk), .rst_n(rs_n), .push(yv), .wdata(yd),
        .pop(inj), .hv(yhv), .head(yh), .ovf(yovf));
    // the job and the coefficient-epoch gate
    reg        jv, jwb, jhs, jcs;
    reg [7:0]  jgen, sg;
    reg        sl;
    reg [7:0]  bi, st;
    wire up_rd   = |fv_i[S_RD-1:0];
    wire up_busy = |(fv_i & ~({{(FVW-1){1'b0}}, 1'b1} << S_RD));        // any upstream beat but a foreign POST
    wire gate    = (XMUT == 1) || (sg == jgen && sl && st == 0 && !up_rd);
    always @(*) inj = jv && gate && yhv && !up_busy;
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin
            jv <= 1'b0; jwb <= 1'b0; jhs <= 1'b0; jcs <= 1'b0; jgen <= 0; sg <= 0; sl <= 1'b1; bi <= 0; st <= 0;
            flt <= 1'b0; fv_o <= 0;
        end else begin
            if (up_rd) begin
                sg <= fd_i[O_PB + 4 +: 8]; sl <= fd_i[O_PB + 12];
                st <= SETTLE;
            end else if (st != 0) st <= st - 8'd1;
            if (inj) begin bi <= bi + 8'd1; if (bi == NR - 1) jv <= 1'b0; end
            if (gv) begin
                if (jv) flt <= 1'b1;
                jv <= 1'b1; bi <= 0; {jgen, jwb, jhs, jcs} <= gd[GD-1:8];
            end
            if (yovf) flt <= 1'b1;
            // a POST beat from the region upstream ends here (its tiles pass it on); this region's own are injected
            fv_o <= inj ? ({{(FVW-1){1'b0}}, 1'b1} << S_RD) : (fv_i & ~({{(FVW-1){1'b0}}, 1'b1} << S_RD));
        end
    always @(posedge clk) begin
        rst_o <= rst_i;
        fd_o <= fd_i;
        if (inj) begin
            fd_o <= {FDW{1'b0}};
            fd_o[O_PB] <= (bi == 0); fd_o[O_PB + 1] <= jwb; fd_o[O_PB + 2] <= jhs; fd_o[O_PB + 3] <= jcs;
            fd_o[O_PB + 4 +: 16] <= {8'd0, bi};
            fd_o[O_D +: YRW] <= yh;
        end
    end
    generate if (XMUT == 3) begin : g_cy_mut
        assign cy_o = cy_i;
    end else begin : g_cy
        reg [127:0] cq;
        always @(posedge clk) cq <= cy_i;
        assign cy_o = cq;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xrc: region collector.  ACK word {beat[7:0], tag[7:0]}.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xrc #(
    parameter integer NG = 256, D = 5120, RSZ = 3, DROP = 0, DROP_BEAT = 7
) (
    input  wire            clk,
    input  wire            srs,
    input  wire [RSZ-1:0]  tb,
    input  wire [RSZ-1:0]  tf,
    input  wire            sflt,
    input  wire            go_v,
    input  wire [7:0]      go_tag,
    output reg             ak_v,
    output reg             ak_f,
    output reg  [15:0]     ak_d
);
    localparam integer NR = D / NG;
    reg [1:0] rsr;
    always @(posedge clk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg [RSZ-1:0] tbq, tfq;
    reg           sfq, gv;
    reg [7:0]     gt;
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin tbq <= 0; tfq <= 0; sfq <= 1'b0; gv <= 1'b0; end
        else begin tbq <= tb; tfq <= tf; sfq <= sflt; gv <= go_v; end
    always @(posedge clk) gt <= go_tag;
    reg [7:0] cnt [0:RSZ-1];
    reg [7:0] acked, tag;
    reg       act, ef;
    reg       all;
    integer i;
    always @(*) begin
        all = 1'b1;
        for (i = 0; i < RSZ; i = i + 1) if (!(cnt[i] > acked)) all = 1'b0;
    end
    always @(posedge clk or negedge rs_n)
        if (!rs_n) begin
            for (i = 0; i < RSZ; i = i + 1) cnt[i] <= 0;
            acked <= 0; tag <= 0; act <= 1'b0; ef <= 1'b0; ak_v <= 1'b0; ak_f <= 1'b0; ak_d <= 0;
        end else begin
            ak_v <= 1'b0;
            ak_f <= ef | (|tfq) | sfq;
            if (|tfq || sfq) ef <= 1'b1;
            for (i = 0; i < RSZ; i = i + 1)
                if (tbq[i]) begin
                    if (!act || cnt[i] == NR) ef <= 1'b1; else cnt[i] <= cnt[i] + 8'd1;
                end
            if (act && all && acked < NR) begin
                ak_v <= !(DROP != 0 && acked == DROP_BEAT);
                ak_d <= {acked, tag};
                acked <= acked + 8'd1;
            end
            if (gv) begin
                for (i = 0; i < RSZ; i = i + 1) cnt[i] <= 0;
                acked <= 0; tag <= gt; act <= 1'b1;
                if (act && acked != NR) ef <= 1'b1;
            end
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xyacc: slab-face y accept (beside the centre pin tile; the y pin flops sit over each column's third).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xyacc #(
    parameter integer NG = 256, YQ = 40, HOLD = 63
) (
    input  wire              sk,
    input  wire              srs,
    input  wire              y_v,
    output reg               y_rdy,
    input  wire [NG*32-1:0]  y_d,
    input  wire              cr_v,           // one beat complete in every region (from the midpoint)
    input  wire              flt_i,          // the midpoint's fault / online (relayed; joined here on the way to the pins)
    input  wire              on_i,
    output reg               o_v,
    output reg  [NG*32-1:0]  o_d,
    output reg               flt_o,
    output reg               on_o
);
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg       crq, hd, uf;
    reg [7:0] os, hc;
    wire      acc = y_v && y_rdy;
    wire [8:0] nx = {1'b0, os} + {8'd0, acc} - {8'd0, crq};
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin crq <= 1'b0; hd <= 1'b0; uf <= 1'b0; os <= 0; hc <= 0; y_rdy <= 1'b0; o_v <= 1'b0; flt_o <= 1'b0; on_o <= 1'b0; end
        else begin
            crq <= cr_v;
            // every express station is out of its reset relay before the first beat leaves (reset-tree skew <= HOLD)
            if (hc == HOLD) hd <= 1'b1; else hc <= hc + 8'd1;
            if (crq && os == 0 && !acc) uf <= 1'b1;
            os <= nx[7:0];
            y_rdy <= hd && (nx < YQ);
            o_v <= acc;
            flt_o <= flt_i | uf; on_o <= on_i;
        end
    always @(posedge sk) o_d <= y_d;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xmid: midpoint station.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xmid #(
    parameter integer NG = 256, D = 5120, NA = 24, MUT = 0, AMUT = 0
) (
    input  wire              cck, crs, sk, srs,
    input  wire              c_cmd_v,
    input  wire [83:0]       c_cmd_d,
    output wire              c_done_v,
    output wire [7:0]        c_done_tag,
    input  wire              inp,
    // every kind but POST: to / from ot_s81_hc_cseq (relayed)
    output reg               up_v,
    output reg  [83:0]       up_d,
    input  wire              dn_v,
    input  wire [7:0]        dn_t,
    output reg               st_flt,
    output reg               st_on,
    // POST express
    output reg               go_v,
    output reg  [GD-1:0]     go_d,
    input  wire [NA-1:0]     ak_v,
    input  wire [NA-1:0]     ak_f,
    input  wire [NA-1:0]     ak_p,           // strap: the region exists
    input  wire [NA*16-1:0]  ak_d,
    output reg               cr_v
);
    localparam integer GD = 19, NR = D / NG, NRE = NR - ((MUT == 4) ? 1 : 0);
    localparam [2:0] K_HLOAD = 0, K_COEF = 2, K_POST = 3, K_GAIN = 5;
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg [1:0] crsr;
    always @(posedge cck) crsr <= {crsr[0], crs};
    wire crs_n = crsr[1];
    // ---------------------------------------------------------------- adapter (die pins in flops)
    wire e_v, e_r, a_flt, online;
    wire [83:0] e_d;
    reg         d_v;
    reg  [7:0]  d_t;
    reg  inp_q;
    always @(posedge sk or negedge rs_n) if (!rs_n) inp_q <= 1'b0; else inp_q <= inp;
    reg        cv_q;
    reg [83:0] cd_q;
    always @(posedge cck or negedge crs_n) if (!crs_n) cv_q <= 1'b0; else cv_q <= c_cmd_v;
    always @(posedge cck) cd_q <= c_cmd_d;
    wire       cdv;
    wire [7:0] cdt;
    ot_s81_engine_adapter #(.QD(8), .MUT(AMUT)) u_ad (
        .c_clk(cck), .c_rst_n(crs_n), .c_cmd_v(cv_q), .c_cmd_d(cd_q), .c_done_v(cdv), .c_done_tag(cdt),
        .fault(a_flt), .online(online),
        .e_clk(sk), .e_rst_n(srs), .e_cmd_v(e_v), .e_cmd_d(e_d), .e_cmd_ready(e_r), .e_inputs_present(inp_q),
        .e_done_v(d_v), .e_done_tag(d_t));
    reg       dv_q;
    reg [7:0] dt_q;
    always @(posedge cck or negedge crs_n) if (!crs_n) dv_q <= 1'b0; else dv_q <= cdv;
    always @(posedge cck) dt_q <= cdt;
    assign c_done_v = dv_q;
    assign c_done_tag = dt_q;
    reg [1:0] af_s, on_s;
    // ---------------------------------------------------------------- seam captures
    reg [NA-1:0]    akv, akf;
    reg [NA*16-1:0] akd;
    reg             dnv;
    reg [7:0]       dnt;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin akv <= 0; akf <= 0; dnv <= 1'b0; af_s <= 0; on_s <= 0; end
        else begin akv <= ak_v & ak_p; akf <= ak_f & ak_p; dnv <= dn_v; af_s <= {af_s[0], a_flt}; on_s <= {on_s[0], online}; end
    always @(posedge sk) begin akd <= ak_d; dnt <= dn_t; end
    // ---------------------------------------------------------------- dispatcher + ACK ledger
    reg        busy, post, fault, jslot;
    reg [7:0]  jtag, gen, gp;
    reg [7:0]  cnt [0:NA-1];
    assign e_r = !busy && !fault;
    wire take = e_v && e_r;
    wire [23:0] c_arg = e_d[30:7];
    wire [2:0]  ck = c_arg[22:20];
    reg         all;
    integer r;
    always @(*) begin
        all = 1'b1;
        for (r = 0; r < NA; r = r + 1) if (ak_p[r] && !(cnt[r] > gp)) all = 1'b0;
    end
    wire hsx = (MUT == 2) ? ~e_d[83] : e_d[83];
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin
            busy <= 1'b0; post <= 1'b0; fault <= 1'b0; jslot <= 1'b0; jtag <= 0; gen <= 0; gp <= 0;
            for (r = 0; r < NA; r = r + 1) cnt[r] <= 0;
            up_v <= 1'b0; go_v <= 1'b0; cr_v <= 1'b0; d_v <= 1'b0; d_t <= 0; st_flt <= 1'b0; st_on <= 1'b0;
        end else begin
            up_v <= 1'b0; go_v <= 1'b0; cr_v <= 1'b0; d_v <= 1'b0;
            st_flt <= fault | af_s[1]; st_on <= on_s[1];
            for (r = 0; r < NA; r = r + 1) begin
                if (akf[r]) fault <= 1'b1;
                if (akv[r]) begin
                    if (!(busy && post) || akd[16 * r +: 8] != jtag || akd[16 * r + 8 +: 8] != cnt[r]) fault <= 1'b1;
                    else cnt[r] <= cnt[r] + 8'd1;
                end
            end
            if (busy && post && all && gp < NRE) begin
                gp <= gp + 8'd1; cr_v <= 1'b1;
                if (gp + 1 == NRE) begin busy <= 1'b0; d_v <= 1'b1; d_t <= (MUT == 5) ? (jtag ^ 8'h01) : jtag; end
            end
            if (dnv) begin
                if (!(busy && !post)) fault <= 1'b1;
                else begin busy <= 1'b0; d_v <= 1'b1; d_t <= dnt; end
            end
            if (take) begin
                busy <= 1'b1; jslot <= e_d[83]; jtag <= {e_d[83], e_d[6:0]};
                if (ck == K_POST) begin
                    post <= 1'b1; gp <= 0;
                    for (r = 0; r < NA; r = r + 1) cnt[r] <= 0;
                    go_v <= 1'b1;
                    if (c_arg[23]) fault <= 1'b1;
                end else begin
                    post <= 1'b0; up_v <= 1'b1;
                    if (ck == K_HLOAD || ck == K_COEF || ck == K_GAIN) gen <= gen + 8'd1;
                end
            end
        end
    always @(posedge sk) if (take) begin
        up_d <= e_d;
        go_d <= {gen, (MUT != 1), hsx, e_d[83], e_d[83], e_d[6:0]};
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_xcol: one column of the express slab (chain C): head rows, the die's CORR_ST corridor stations, tail rows,
// a region station before each region's first half-octet, the taps / collectors, and every express link of the column
// with its stage count derived from the v13 geometry (0.01 um units; station = the N edge of its first slot, collector
// = the region's midpoint-facing edge, tap = slot centre, midpoint = corridor centre of the centre column, y pins and
// the sequencer G_ROOT_H above the first head slot).  A stage is <= G_REACH of Manhattan wire by construction.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_xcol #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2, S_RT = 4, WIN = 2, WOUT = 2, ML = 5, AL = 4, RLY = 2,
    parameter integer CNL_PIN = 0, CHAIN_STEP = AL, LANE_SPECIALIZE = 0,
    parameter integer C = 0, HEAD_ROWS = 10, CORR_ST = 7, NRMAX = 8, YD = 64, XMUT = 0,
    parameter integer G_SLOT_H = 74088, G_COL_P = 61992, G_CORR = 151200, G_ROOT_H = 84000, G_REACH = 50000,
    parameter integer FVW = S_RD + 5, RVW = S_RT + 4,
    parameter integer FDW = (72+16*S_RD)+((S_RD*512>((NG/GS+NCOL-1)/NCOL)*GS*32)?S_RD*512:((NG/GS+NCOL-1)/NCOL)*GS*32),
    parameter integer RDW = S_RT+24*S_RT+8+512*S_RT,
    parameter integer YS = (C == 1 ? (NG/GS - 2*((NG/GS+NCOL-1)/NCOL)) : ((NG/GS+NCOL-1)/NCOL)) * GS * 32
) (
    input  wire               sk,
    input  wire               srs,
    input  wire               rst_in,
    input  wire [FVW-1:0]     fv_in,
    input  wire [FDW-1:0]     fd_in,
    output wire [RVW-1:0]     rv_out,
    output wire [RDW-1:0]     rd_out,
    input  wire               go_v,           // at the midpoint station
    input  wire [18:0]        go_d,
    input  wire               y_v,            // at the slab face
    input  wire [YS-1:0]      y_d,
    output wire [NRMAX-1:0]   ak_v,           // at the midpoint station
    output wire [NRMAX-1:0]   ak_f,
    output wire [NRMAX-1:0]   ak_p,
    output wire [NRMAX*16-1:0] ak_d
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, L1 = (NS - 2 * NP > 0) ? NS - 2 * NP : 0, GT = GS / 2;
    localparam integer LC = ((C == 1) ? L1 : NP) * 2, BC = ((C == 0) ? 0 : (C == 1) ? NP : NP + L1) * 2;
    localparam integer NH = (LC < HEAD_ROWS) ? LC : HEAD_ROWS, NTL = LC - NH;
    localparam integer NRH = (NH + 2) / 3, NRT = (NTL + 2) / 3, NREG = NRH + NRT, PADF = NRMAX - NREG;
    localparam integer BW = 1 + FVW + FDW + 128;
    function automatic integer rsz(input integer r);
        integer t;
        begin
            if (r < NRH) rsz = NH / NRH + ((r < NH % NRH) ? 1 : 0);
            else begin t = r - NRH; rsz = NTL / NRT + ((t < NTL % NRT) ? 1 : 0); end
        end
    endfunction
    function automatic integer rfi(input integer r);
        integer t, q;
        begin t = 0; for (q = 0; q < r; q = q + 1) t = t + rsz(q); rfi = t; end
    endfunction
    function automatic integer yrow(input integer i);
        yrow = (i < NH) ? i * G_SLOT_H : NH * G_SLOT_H + G_CORR + (i - NH) * G_SLOT_H;
    endfunction
    function automatic integer ycol(input integer r);
        ycol = (r < NRH) ? yrow(rfi(r) + rsz(r) - 1) + G_SLOT_H : yrow(rfi(r));
    endfunction
    function automatic integer absd(input integer a, input integer b);
        absd = (a > b) ? a - b : b - a;
    endfunction
    function automatic integer stg(input integer d);
        stg = (d <= G_REACH) ? 1 : (d + G_REACH - 1) / G_REACH;
    endfunction
    localparam integer YMID = HEAD_ROWS * G_SLOT_H + G_CORR / 2;
    localparam integer DXC = (C == NCOL / 2) ? 0 : G_COL_P * absd(C, NCOL / 2);
`ifndef SYNTHESIS
    initial if (PADF < 0 || NH < 1) $fatal(1, "ot_s81_hc_xcol: NRMAX %0d < the column's %0d regions", NRMAX, NREG);
`endif
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    wire [FVW-1:0] fvo [0:LC-1];
    wire [FDW-1:0] fdo [0:LC-1];
    wire [RVW-1:0] rvo [0:LC-1];
    wire [RDW-1:0] rdo [0:LC-1];
    wire           rso [0:LC-1];
    wire [127:0]   cyo [0:LC-1];
    wire [RVW-1:0] rvn [0:LC-1];              // return into tile p
    wire [RDW-1:0] rdn [0:LC-1];
    // a column with fewer regions than the widest gets plain stages at its head: every column the same count (lockstep)
    wire [BW-1:0] hb;
    ot_hdc_delay #(.W(BW), .D(PADF), .RESET(0)) u_pad (.clk(sk), .rst_n(rs_n), .d({rst_in, fv_in, fd_in, 128'd0}), .q(hb));
    // the die's corridor stations between head and tail (common clock; the reset is an in-band forward bit)
    wire [BW-1:0]      cfo;
    wire [RVW+RDW-1:0] cro;
    genvar r, k, p;
    generate
    if (NTL > 0) begin : g_corr
        ot_hdc_delay #(.W(BW), .D(CORR_ST), .RESET(0)) u_cf (.clk(sk), .rst_n(rs_n),
            .d({rso[NH-1], fvo[NH-1], fdo[NH-1], cyo[NH-1]}), .q(cfo));
        ot_hdc_delay #(.W(RVW+RDW), .D(CORR_ST), .RESET(0)) u_cr (.clk(sk), .rst_n(rs_n), .d({rvo[NH < LC ? NH : 0], rdo[NH < LC ? NH : 0]}), .q(cro));
    end else begin : g_ncorr
        assign cfo = {BW{1'b0}}; assign cro = {(RVW+RDW){1'b0}};
    end
    for (p = 0; p < LC; p = p + 1) begin : g_ret
        if (p == LC - 1) begin : g_end
            assign rvn[p] = {RVW{1'b0}}; assign rdn[p] = {RDW{1'b0}};
        end else if (p + 1 == NH) begin : g_cor
            assign {rvn[p], rdn[p]} = cro;
        end else begin : g_nxt
            assign rvn[p] = rvo[p + 1]; assign rdn[p] = rdo[p + 1];
        end
    end
    for (r = 0; r < NRMAX; r = r + 1) begin : g_r
        if (r < NREG) begin : g_live
            localparam integer F = rfi(r), Z = rsz(r), YRW = Z * GT * 32;
            localparam integer YST = yrow(F), YCO = ycol(r);
            localparam integer N_GOS = stg(absd(YST, YMID) + DXC), N_GOC = stg(absd(YCO, YMID) + DXC);
            localparam integer N_Y = stg(YST + G_ROOT_H + DXC), N_SF = stg(absd(YST, YCO));
            wire [BW-1:0] sb;
            if (F == 0) begin : g_h
                assign sb = hb;
            end else if (F == NH) begin : g_c
                assign sb = cfo;
            end else begin : g_p
                assign sb = {rso[F > 0 ? F - 1 : 0], fvo[F > 0 ? F - 1 : 0], fdo[F > 0 ? F - 1 : 0], cyo[F > 0 ? F - 1 : 0]};
            end
            wire             gs_v, gc_v, ys_v, t_rst, s_flt, sf_q;
            wire [18:0]      gs_d, gc_d;
            wire [YRW-1:0]   ys_d;
            wire [FVW-1:0]   t_fv;
            wire [FDW-1:0]   t_fd;
            wire [127:0]     t_cy;
            wire [Z-1:0]     tbq, tfq;
            wire             a_v, a_f;
            wire [15:0]      a_d;
            ot_s81_hc_xlink #(.W(19), .N(N_GOS)) u_lgs (.clk(sk), .rst_n(rs_n), .v_i(go_v), .d_i(go_d), .v_o(gs_v), .d_o(gs_d));
            ot_s81_hc_xlink #(.W(19), .N(N_GOC)) u_lgc (.clk(sk), .rst_n(rs_n), .v_i(go_v), .d_i(go_d), .v_o(gc_v), .d_o(gc_d));
            ot_s81_hc_xlink #(.W(YRW), .N(N_Y)) u_ly (.clk(sk), .rst_n(rs_n), .v_i(y_v), .d_i(y_d[F * GT * 32 +: YRW]),
                .v_o(ys_v), .d_o(ys_d));
            ot_s81_hc_xrs #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .RSZ(Z), .YD(YD), .XMUT(XMUT)) u_s (
                .clk(sk), .srs(srs), .rst_i(sb[BW-1]), .fv_i(sb[128 + FDW +: FVW]), .fd_i(sb[128 +: FDW]), .cy_i(sb[127:0]),
                .rst_o(t_rst), .fv_o(t_fv), .fd_o(t_fd), .cy_o(t_cy), .go_v(gs_v), .go_d(gs_d), .y_v(ys_v), .y_d(ys_d),
                .flt(s_flt));
            ot_hdc_delay #(.W(1), .D(N_SF), .RESET(1)) u_lsf (.clk(sk), .rst_n(rs_n), .d(s_flt), .q(sf_q));
            for (k = 0; k < Z; k = k + 1) begin : g_t
                localparam integer P = F + k;
                localparam [7:0] TID = BC + P;
                localparam integer N_TAP = stg(absd(yrow(P) + G_SLOT_H / 2, YCO));
                wire [7:0] x_hov, x_hnz, x_pflt;
                wire       tb, tf;
                ot_s81_hc_cth #(.NG(NG), .D(D), .NCOL(NCOL), .GS(GS), .S_RD(S_RD), .S_RT(S_RT), .WIN(WIN), .WOUT(WOUT),
                                .ML(ML), .AL(AL), .RLY(RLY), .CNL_PIN(CNL_PIN), .CHAIN_STEP(CHAIN_STEP),
                                .LANE_SPECIALIZE(LANE_SPECIALIZE)) u_t (
                    .clk(sk), .rst_in(k == 0 ? t_rst : rso[P > 0 ? P - 1 : 0]), .rst_out(rso[P]), .tid(TID),
                    .last(P == LC - 1),
                    .fv_in(k == 0 ? t_fv : fvo[P > 0 ? P - 1 : 0]), .fd_in(k == 0 ? t_fd : fdo[P > 0 ? P - 1 : 0]),
                    .fv_out(fvo[P]), .fd_out(fdo[P]), .rv_in(rvn[P]), .rd_in(rdn[P]), .rv_out(rvo[P]), .rd_out(rdo[P]),
                    .cy_out(cyo[P]), .cy_in(k == 0 ? t_cy : cyo[P > 0 ? P - 1 : 0]),
                    .x_hov(x_hov), .x_hnz(x_hnz), .x_pflt(x_pflt));
                ot_s81_hc_xtap u_x (.clk(sk), .srs(srs), .hov(x_hov), .hnz(x_hnz), .pflt(x_pflt), .tb(tb), .tf(tf));
                ot_hdc_delay #(.W(2), .D(N_TAP), .RESET(1)) u_lt (.clk(sk), .rst_n(rs_n), .d({tf, tb}), .q({tfq[k], tbq[k]}));
`ifndef SYNTHESIS
                initial if ($test$plusargs("HC_XGEOM")) $display("HCX tap c=%0d r=%0d p=%0d stages=%0d", C, r, P, N_TAP);
`endif
            end
            ot_s81_hc_xrc #(.NG(NG), .D(D), .RSZ(Z), .DROP(XMUT == 2 && C == NCOL / 2 && r == NREG - 1)) u_c (
                .clk(sk), .srs(srs), .tb(tbq), .tf(tfq), .sflt(sf_q), .go_v(gc_v), .go_tag(gc_d[7:0]),
                .ak_v(a_v), .ak_f(a_f), .ak_d(a_d));
            ot_hdc_delay #(.W(2), .D(N_GOC), .RESET(1)) u_lav (.clk(sk), .rst_n(rs_n), .d({a_f, a_v}), .q({ak_f[r], ak_v[r]}));
            ot_hdc_delay #(.W(16), .D(N_GOC)) u_lad (.clk(sk), .rst_n(rs_n), .d(a_d), .q(ak_d[16 * r +: 16]));
            assign ak_p[r] = 1'b1;
`ifndef SYNTHESIS
            initial if ($test$plusargs("HC_XGEOM"))
                $display("HCX region c=%0d r=%0d first=%0d size=%0d go_station=%0d go_collector=%0d ack=%0d y=%0d sflt=%0d",
                         C, r, F, Z, N_GOS, N_GOC, N_GOC, N_Y, N_SF);
`endif
        end else begin : g_none
            assign ak_v[r] = 1'b0; assign ak_f[r] = 1'b0; assign ak_p[r] = 1'b0; assign ak_d[16 * r +: 16] = 16'd0;
        end
    end
    endgenerate
    assign rv_out = rvo[0];
    assign rd_out = rdo[0];
endmodule
