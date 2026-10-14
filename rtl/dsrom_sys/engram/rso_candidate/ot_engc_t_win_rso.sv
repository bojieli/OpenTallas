// SOURCE-ONLY RSO CANDIDATE: new master/port; existing closed views do not bind this variant.
`timescale 1ns/1ps
// ot_engc_t_win (el1011-ds-misc/engram, 2026-10-11): WINDOW / ALL-GATHER tile of the all-tile dsfd_engram_c (above the
// lookup, under f_win / t_ag).  Holds the old composition's window side, every flop of it now inside a tile:
//   f_win pin flops, the 2-entry window hold queue + the descriptor queue (window released only under a queued eng
//   descriptor, in order; wrong descriptor / overflow = sticky fault jf), window to the lookup REGISTERED (+1 cycle),
//   lookup window credits, t_collective (window credit return), rank releases (rel) to the lookup;
//   all-gather out: lookup N face -> 2 stages -> t_ag; f_agc -> o_cred (1 stage);
//   seams: cfg (2nd stage) to the lookup; reset synchronisers of the lookup / sink (registered outputs); the sink's
//   rdy / perr (2 relay stages toward T_IO) and the VM release (2 relay stages toward the sink's W face);
//   descriptor jn (2nd stage) from T_IO, windows released wn (1st stage) and jf (1st stage) to T_IO; werr relay.
module ot_engc_t_win_rso (
    input  wire          ck,
    input  wire          rst,
    input  wire [72:0]   f_win,           // {win_v, win_ids 4 x 17, rel 4}
    output reg           t_collective,
    // lookup window side
    output reg           lk_wv,
    output reg  [67:0]   lk_wid,
    input  wire          lk_wcred,
    output reg  [3:0]    lk_rel,
    // lookup all-gather side
    input  wire          lk_ov, lk_stv, lk_stb, lk_fault,
    input  wire [4:0]    lk_oc,
    input  wire [2:0]    lk_ob, lk_os, lk_sts,
    input  wire [263:0]  lk_od,
    output wire [281:0]  t_ag,
    input  wire          f_agc,
    output reg           lk_ocred,
    // cfg straps (1st stage in T_IO)
    input  wire [2:0]    cfg_i,
    output reg  [2:0]    cfg_o,
    // leaf resets
    output wire          rn_lk,
    output wire          rn_sk,
    // sink seams
    input  wire [7:0]    s_rdy, s_perr,
    output reg  [7:0]    rdy_o, perr_o,
    input  wire [3:0]    vrel_i,          // {rel_slot 3, rel_v}
    output reg  [3:0]    vrel_o,
    // T_IO seams
    input  wire [17:0]   jn_i,            // {j_new, reserved != 0, n 16} (1st stage in T_IO)
    output reg  [15:0]   wn_o,
    output reg           jf_o,
    input  wire          werr_i,
    output reg           werr_o
,
    output wire rso
);
    localparam integer IDW = 17;
    reg [1:0] rs_q, rsl_q, rss_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q  <= 2'b00; else rs_q  <= {rs_q[0], 1'b1};
    always @(posedge ck or negedge rst) if (!rst) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    always @(posedge ck or negedge rst) if (!rst) rss_q <= 2'b00; else rss_q <= {rss_q[0], 1'b1};
    wire rn = rs_q[1];
    assign rso = rn;
    assign rn_lk = rsl_q[1]; assign rn_sk = rss_q[1];

    // ---------------- window hold queue
    reg wv_q; reg [4*IDW-1:0] wid_q; reg wcred_q; reg [17:0] jn_q;
    always @(posedge ck or negedge rn) if (!rn) begin wv_q <= 1'b0; lk_rel <= 4'd0; wcred_q <= 1'b0; jn_q <= 18'd0; end
                                       else begin wv_q <= f_win[72]; lk_rel <= f_win[3:0]; wcred_q <= lk_wcred; jn_q <= jn_i; end
    always @(posedge ck) wid_q <= f_win[71:4];
    reg [4*IDW-1:0] hq_w [0:1]; reg hh, ht; reg [1:0] hn;
    reg [16:0] ia [0:7]; reg [2:0] iw, ir; reg [3:0] in_;
    reg [15:0] wn; reg [1:0] lc; reg jf;
    wire rel_w = (hn != 2'd0) && (in_ != 4'd0) && (lc != 2'd0);
    always @(posedge ck or negedge rn)
        if (!rn) begin
            hh <= 1'b0; ht <= 1'b0; hn <= 2'd0; iw <= 0; ir <= 0; in_ <= 0; wn <= 0; lc <= 2'd2; jf <= 1'b0;
            t_collective <= 1'b0; lk_wv <= 1'b0;
        end else begin
            if (wv_q) begin hq_w[ht] <= wid_q; ht <= ~ht; if (hn == 2'd2 && !rel_w) jf <= 1'b1; end
            if (rel_w) hh <= ~hh;
            hn <= hn + wv_q - rel_w;
            t_collective <= rel_w;
            lk_wv <= rel_w;
            if (jn_q[17]) begin ia[iw] <= jn_q[16:0]; iw <= iw + 1'b1; end
            if (rel_w && in_ != 4'd0) begin
                if (ia[ir][16] || ia[ir][15:0] != wn) jf <= 1'b1;
                ir <= ir + 1'b1;
            end
            in_ <= in_ + jn_q[17] - (rel_w && in_ != 4'd0);
            if (rel_w) wn <= wn + 1'b1;
            lc <= lc - rel_w + wcred_q;
        end
    always @(posedge ck) lk_wid <= hq_w[hh];
    always @(posedge ck or negedge rn) if (!rn) begin wn_o <= 16'd0; jf_o <= 1'b0; werr_o <= 1'b0; end
                                       else begin wn_o <= wn; jf_o <= jf; werr_o <= werr_i; end

    // ---------------- all-gather relays (data unreset)
    reg [3:0] ags_1, ags_2; reg [274:0] agd_1, agd_2; reg [2:0] agv_1, agv_2;
    always @(posedge ck) begin ags_1 <= {lk_stb, lk_sts}; ags_2 <= ags_1; agd_1 <= {lk_od, lk_os, lk_ob, lk_oc}; agd_2 <= agd_1; end
    always @(posedge ck or negedge rn_lk)
        if (!rn_lk) begin agv_1 <= 3'd0; agv_2 <= 3'd0; lk_ocred <= 1'b0; end
        else begin agv_1 <= {lk_fault, lk_stv, lk_ov}; agv_2 <= agv_1; lk_ocred <= f_agc; end
    assign t_ag = {agv_2[2], ags_2[3], ags_2[2:0], agv_2[1], agd_2, agv_2[0]};
    always @(posedge ck) cfg_o <= cfg_i;

    // ---------------- sink seams (rdy / perr toward T_IO, release toward the sink)
    reg [7:0] rdy_1, perr_1; reg [3:0] vrel_1;
    always @(posedge ck or negedge rn)
        if (!rn) begin rdy_1 <= 8'd0; perr_1 <= 8'd0; rdy_o <= 8'd0; perr_o <= 8'd0; end
        else begin rdy_1 <= s_rdy; perr_1 <= s_perr; rdy_o <= rdy_1; perr_o <= perr_1; end
    always @(posedge ck or negedge rn_sk)
        if (!rn_sk) begin vrel_1 <= 4'd0; vrel_o <= 4'd0; end
        else begin vrel_1 <= vrel_i; vrel_o <= vrel_1; end
endmodule
