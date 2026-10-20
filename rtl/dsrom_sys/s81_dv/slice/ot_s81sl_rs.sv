`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-XG4 (LEAD4-S81, 10-20): ot_s81sl_rs -- the slice ring stop data plane as its own hardened leaf (sibling of the x
// streamer leaf in the slice parent).  Successor of the S81-XG3 leaf (claude/s81-xgr-1019 eae783e87), rebuilt from the
// CURRENT main ot_s81sl_rstop (S81-SMWIRE CI_XB own delivery + 4-fragment V train included), because:
//   - the XG3 leaf lacked CI_XB (current main rstop behaviour), and
//   - its mapped native census FAILED the <=32-load rule: 466 drivers > 32, max 202 (codex 3f8b2506d: per-copy sid_c 202,
//     4 reset regions 164, 24-bit slice selects 48-50, every header port 47 = 46 copies + data flop).
//
// Function: cycle-for-cycle current-main ot_s81sl_rstop with every output leaving through ONE relay register
// (RELAY = 1: line E / W, V, control-plane deliveries, xfin NX ports, AND the gather port g_*), so no single-cycle wire
// crosses the tile (pins on all four faces of a ~860 x 520 um pin-bound leaf).  fault is not relayed (as RELAY = 1).
// Checked by tools/s81_slice/rs_equiv.sh against main ot_s81sl_rstop + a one-edge testbench relay on those outputs.
// Schedule: +1 edge per stop on the line / V / NX / control deliveries and +1 edge on the gather port into the x
// streamer -> handed to the die calendar (MU.S81.CAL) and priced there; the ring protocol itself is unchanged.
//
// Native-load structure (every driver <= 32 load pins by construction):
//   - copies   31 capture copies (ot_s81sl_rs_cp): each header / valid / strap port bit feeds 31 copy flops + at most one
//              data flop = 32.  A copy feeds 3 select leaves (and copy 0 also the master).
//   - leaves   92 select leaves (ot_s81sl_rs_lf), one per 12 line bits: its own replicas of the fragment-assembly / V
//              train state, its own registered strap decode, and priority-qualified ONE-HOT selects that each drive
//              <= 12 bit muxes.  Leaf j also computes 3 bits of the merged own fragment (276 bits computed once).
//   - master   ot_s81sl_rs_m: scalar valids, fault, NX valids, gather family / index select (own state replica).
//   - reset    ot_s81sl_rs_rst: port -> 2 sync flops -> 6 -> 48 region flops (release 4 edges after rst_n, assert 2
//              edges after, clock running); every region <= 23 reset loads; payload registers are reset-free.
//   - sid      strap (die.v literal 2c + r): copy capture (edge 1) -> leaf r_sid (edge 2) -> leaf strap decode (edge 3).
//              It is settled before the first non-reset edge: the regions release 4 edges after rst_n rises and sid is
//              a constant strap from power-up; every valid / state register is held in reset until then.
// Mutants (negative controls; names shared with ot_s81sl_rstop): OT_S81SL_RSTOP_MUT_FRAG / _VASM / _GSWAP / _TIERCOL /
// _CIXB, and OT_S81SL_RS_MUT_SLICE (leaf 7's E-line forward select taken from the W decode).
// ---------------------------------------------------------------------------------------------------------------------

// reset tree: rst_n port drives 2 flops only; 6 + 48 kept relay flops (no async clear: assert is clocked)
(* keep_hierarchy *)
module ot_s81sl_rs_rst (
    input  wire        clk,
    input  wire        rst_n_in,
    output wire [47:0] rst_n
);
    (* keep = "true", dont_touch = "true" *) reg s0, s1;
    always @(posedge clk or negedge rst_n_in)
        if (!rst_n_in) begin s0 <= 1'b0; s1 <= 1'b0; end
        else begin s0 <= 1'b1; s1 <= s0; end
    (* keep = "true", dont_touch = "true" *) reg [5:0]  l1;
    (* keep = "true", dont_touch = "true" *) reg [47:0] l2;
    integer k;
    always @(posedge clk) begin
        l1 <= {6{s1}};
        for (k = 0; k < 48; k = k + 1) l2[k] <= l1[k / 8];
    end
    assign rst_n = l2;
endmodule

// capture copy: header / valid / strap bits of every port a select depends on
(* keep_hierarchy *)
module ot_s81sl_rs_cp (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [8:0]  iwh_d,     // ri_w[8:0]  {hops, kind, v}
    input  wire [8:0]  ieh_d,     // ri_e[8:0]
    input  wire [3:0]  ivh_d,     // vi[3:0]
    input  wire [8:0]  cih_d,     // ci_b[8:0]
    input  wire [2:0]  cid_d,     // ci_dir
    input  wire        nev_d,     // nx_eo[172]
    input  wire        nwv_d,     // nx_wo[172]
    input  wire [4:0]  xfv_d,     // xf_v
    input  wire [4:0]  xfs_d,     // xf_s
    input  wire [3:0]  sid_d,     // sid strap
    output reg  [8:0]  iwh, output reg [8:0] ieh, output reg [3:0] ivh, output reg [8:0] cih, output reg [2:0] cid,
    output reg         nev, output reg nwv, output reg [4:0] xfv, output reg [4:0] xfs, output reg [3:0] sid
);
    always @(posedge clk) begin
        iwh <= iwh_d; ieh <= ieh_d; ivh <= ivh_d; cih <= cih_d; cid <= cid_d; nev <= nev_d; nwv <= nwv_d;
        xfs <= xfs_d; sid <= sid_d;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) xfv <= 5'd0; else xfv <= xfv_d;
endmodule

// select leaf: 12 line bits.  State replicas use the next-state functions of ot_s81sl_rstop verbatim.
(* keep_hierarchy *)
module ot_s81sl_rs_lf (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [8:0]  iwh, input wire [8:0] ieh, input wire [3:0] ivh, input wire [8:0] cih, input wire [2:0] cid,
    input  wire        nev, input wire nwv, input wire [4:0] xfv, input wire [4:0] xfs, input wire [3:0] sid,
    input  wire [14:0] xf3,       // {xf_q[4V+b], xf_q[3V+b], xf_q[2V+b], xf_q[V+b], xf_q[b]} for b = 3j + 0..2
    output wire [2:0]  of3,       // merged own fragment bits 3j + 0..2
    // E line one-hot (priority fe > ne > oe > ae > ce)
    output wire        e_f, output wire e_nw, output wire e_ne, output wire e_o, output wire e_a, output wire e_c,
    // W line one-hot (fw > nw > ow > aw > cw)
    output wire        w_f, output wire w_ne, output wire w_nw, output wire w_o, output wire w_a, output wire w_c,
    output wire        c_h0,      // control inject hops == 0 (line default hops / src inserted)
    // V out one-hot (own fragment > V-mapped NX > control V beat > ci XB V train slot 0 / 1 / 2)
    output wire        v_o, output wire v_ne, output wire v_nw, output wire v_c, output wire v_t0, output wire v_t1,
    output wire        v_t2,
    output wire        sw0, output wire sw1, output wire sw2, output wire sw3,   // own slot writes / own load
    output wire        vw0, output wire vw1, output wire vw2, output wire vw3,   // V slot writes / assembled load
    output wire        vtl,                                                      // ci XB V train load
    output wire        g_a, output wire g_c, output wire g_o,                    // gather own word: asm / ci / own
    output reg         x_wv, output reg x_wie, output reg x_wiw,                 // xfin wi payload: V / ie / iw
    output reg         x_ev, output reg x_eiw, output reg x_eie,                 // xfin ei payload: V / iw / ie
    output reg  [3:0]  r_sid, output reg [4:0] r_he, output reg [4:0] r_hw
);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    // ------------------------------------------------ strap decode (registered: sid is a constant strap)
    reg r_tier, r_mape, r_mapw, r_hez, r_hwz;
    always @(posedge clk) r_sid <= sid;
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    wire [2:0] col = r_sid[2:0]; wire tier = r_sid[3];
`else
    wire [2:0] col = r_sid[3:1]; wire tier = r_sid[0];
`endif
    wire map_e = tier ? col == 3'd0 : col == 3'd7;
    wire map_w = tier ? col == 3'd7 : col == 3'd0;
    always @(posedge clk) begin
        r_tier <= tier; r_mape <= map_e; r_mapw <= map_w;
        r_he <= 5'd7 - {2'd0, col}; r_hw <= {2'd0, col};
        r_hez <= col != 3'd7; r_hwz <= col != 3'd0;
        x_wv <= map_w; x_wie <= !map_w && tier; x_wiw <= !map_w && !tier;
        x_ev <= map_e; x_eiw <= !map_e && tier; x_eie <= !map_e && !tier;
    end
    // ------------------------------------------------ own fragments
    wire ofv = |xfv;
    wire ofs = |(xfv & xfs);
    genvar b;
    generate for (b = 0; b < 3; b = b + 1) begin : g_of
        assign of3[b] = (xfv[0] & xf3[b * 5 + 0]) | (xfv[1] & xf3[b * 5 + 1]) | (xfv[2] & xf3[b * 5 + 2]) |
                        (xfv[3] & xf3[b * 5 + 3]) | (xfv[4] & xf3[b * 5 + 4]);
    end endgenerate
    // ------------------------------------------------ state replicas (ot_s81sl_rstop next-state functions)
    reg [1:0] on_n; reg own_v; reg [1:0] fr_n; reg fr_on; reg asm_v; reg [1:0] vt_n;
    wire iv_v = ivh[0]; wire [2:0] iv_k = ivh[3:1];
    wire ci_xb = cih[0] && cih[3:1] == K_XB;
`ifdef OT_S81SL_RSTOP_MUT_CIXB
    wire cxo = 1'b0;
`else
    wire cxo = ci_xb && (cid[0] || cid[1]);
`endif
    assign vtl = ci_xb && cid[2];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin on_n <= 2'd0; own_v <= 1'b0; fr_on <= 1'b0; fr_n <= 2'd0; asm_v <= 1'b0; vt_n <= 2'd0; end
        else begin
            own_v <= ofv && !ofs && on_n == 2'd3;
            if (ofv) on_n <= ofs ? 2'd1 : on_n + 2'd1;
            asm_v <= 1'b0;
            if (fr_on) begin
                fr_n <= fr_n + 2'd1;
                if (fr_n == 2'd3) begin fr_on <= 1'b0; asm_v <= 1'b1; end
            end else if (iv_v && (iv_k == K_XQ || iv_k == K_XB)) begin fr_on <= 1'b1; fr_n <= 2'd1; end
            vt_n <= vtl ? 2'd3 : (vt_n != 2'd0) ? vt_n - 2'd1 : 2'd0;
        end
    assign sw0 = ofv && (ofs || on_n == 2'd0);
    assign sw1 = ofv && !ofs && on_n == 2'd1;
    assign sw2 = ofv && !ofs && on_n == 2'd2;
    assign sw3 = ofv && !ofs && on_n == 2'd3;
    assign vw0 = !fr_on || fr_n == 2'd0;
    assign vw1 = fr_on && fr_n == 2'd1;
    assign vw2 = fr_on && fr_n == 2'd2;
    assign vw3 = fr_on && fr_n == 2'd3;
    // ------------------------------------------------ line selects
    wire iw_v = iwh[0], ie_v = ieh[0];
    wire [2:0] iw_k = iwh[3:1], ie_k = ieh[3:1];
    wire [4:0] iw_h = iwh[8:4], ie_h = ieh[8:4];
    wire fe = iw_v && iw_k != K_NX && iw_h > 5'd1;
    wire fw = ie_v && ie_k != K_NX && ie_h > 5'd1;
    // E port NX: tier N carries xfin wo, tier S eo;  W port the other
    wire ne_w = r_tier && nwv && !r_mapw, ne_e = !r_tier && nev && !r_mape;
    wire nw_e = r_tier && nev && !r_mape, nw_w = !r_tier && nwv && !r_mapw;
    wire ne = ne_w || ne_e, nw = nw_e || nw_w;
    wire oe = own_v && r_hez, ow = own_v && r_hwz;
    wire ae = asm_v && r_hez, aw = asm_v && r_hwz;
    wire ce = cih[0] && cid[0], cw = cih[0] && cid[1];
    assign e_f = fe;
    assign e_nw = !fe && ne_w;
    assign e_ne = !fe && ne_e;
    assign e_o = !fe && !ne && oe;
    assign e_a = !fe && !ne && !oe && ae;
    assign e_c = !fe && !ne && !oe && !ae && ce;
    assign w_f = fw;
    assign w_ne = !fw && nw_e;
    assign w_nw = !fw && nw_w;
    assign w_o = !fw && !nw && ow;
    assign w_a = !fw && !nw && !ow && aw;
    assign w_c = !fw && !nw && !ow && !aw && cw;
    assign c_h0 = cih[8:4] == 5'd0;
    // ------------------------------------------------ V out selects
    wire nxv_e = r_mape && nev;
    wire nxv_out = nxv_e || (r_mapw && nwv);
    wire vci = cih[0] && cid[2];
    assign v_o = ofv;
    assign v_ne = !ofv && nxv_e;
    assign v_nw = !ofv && nxv_out && !nxv_e;
    assign v_c = !ofv && !nxv_out && vci;
    assign v_t0 = !ofv && !nxv_out && !vci && vt_n == 2'd3;
    assign v_t1 = !ofv && !nxv_out && !vci && vt_n == 2'd2;
    assign v_t2 = !ofv && !nxv_out && !vci && vt_n == 2'd1;
    // ------------------------------------------------ gather own word: asm_v ? asm_b : cxo ? ci : own
    assign g_a = asm_v;
    assign g_c = !asm_v && cxo;
    assign g_o = !asm_v && !cxo;
endmodule

// master: scalar valids, fault, NX valids, gather family / index own-word select
(* keep_hierarchy *)
module ot_s81sl_rs_m (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [8:0]  iwh, input wire [8:0] ieh, input wire [3:0] ivh, input wire [8:0] cih, input wire [2:0] cid,
    input  wire        nev, input wire nwv, input wire [4:0] xfv, input wire [4:0] xfs, input wire [3:0] sid,
    input  wire [2:0]  own_k,     // own[3:1]
    output wire        flt_set,
    output wire [2:0]  g_v_n,
    output wire        g_fe, output wire g_fw,   // g_fam[2] / g_fam[1]
    output wire        m_a, output wire m_c, output wire m_o,
    output wire        dlev_n, output wire dlwv_n, output wire dlvv_n,
    output wire        nxwv_n, output wire nxev_n
);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    reg [3:0] r_sid; reg r_tier, r_mape, r_mapw, r_hez, r_hwz;
    always @(posedge clk) r_sid <= sid;
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    wire [2:0] col = r_sid[2:0]; wire tier = r_sid[3];
`else
    wire [2:0] col = r_sid[3:1]; wire tier = r_sid[0];
`endif
    always @(posedge clk) begin
        r_tier <= tier;
        r_mape <= tier ? col == 3'd0 : col == 3'd7;
        r_mapw <= tier ? col == 3'd7 : col == 3'd0;
        r_hez <= col != 3'd7; r_hwz <= col != 3'd0;
    end
    wire ofv = |xfv;
    wire ofs = |(xfv & xfs);
    wire [2:0] nown = xfv[0] + xfv[1] + xfv[2] + xfv[3] + xfv[4];
    reg [1:0] on_n; reg own_v; reg [1:0] fr_n; reg fr_on; reg asm_v; reg [1:0] vt_n;
    wire iv_v = ivh[0]; wire [2:0] iv_k = ivh[3:1];
    wire ci_xb = cih[0] && cih[3:1] == K_XB;
`ifdef OT_S81SL_RSTOP_MUT_CIXB
    wire cxo = 1'b0;
`else
    wire cxo = ci_xb && (cid[0] || cid[1]);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin on_n <= 2'd0; own_v <= 1'b0; fr_on <= 1'b0; fr_n <= 2'd0; asm_v <= 1'b0; vt_n <= 2'd0; end
        else begin
            own_v <= ofv && !ofs && on_n == 2'd3;
            if (ofv) on_n <= ofs ? 2'd1 : on_n + 2'd1;
            asm_v <= 1'b0;
            if (fr_on) begin
                fr_n <= fr_n + 2'd1;
                if (fr_n == 2'd3) begin fr_on <= 1'b0; asm_v <= 1'b1; end
            end else if (iv_v && (iv_k == K_XQ || iv_k == K_XB)) begin fr_on <= 1'b1; fr_n <= 2'd1; end
            vt_n <= (ci_xb && cid[2]) ? 2'd3 : (vt_n != 2'd0) ? vt_n - 2'd1 : 2'd0;
        end
    wire iw_v = iwh[0], ie_v = ieh[0];
    wire [2:0] iw_k = iwh[3:1], ie_k = ieh[3:1];
    wire [4:0] iw_h = iwh[8:4], ie_h = ieh[8:4];
    wire fe = iw_v && iw_k != K_NX && iw_h > 5'd1;
    wire fw = ie_v && ie_k != K_NX && ie_h > 5'd1;
    wire ne = r_tier ? (nwv && !r_mapw) : (nev && !r_mape);
    wire nw = r_tier ? (nev && !r_mape) : (nwv && !r_mapw);
    wire oe = own_v && r_hez, ow = own_v && r_hwz;
    wire ae = asm_v && r_hez, aw = asm_v && r_hwz;
    wire ce = cih[0] && cid[0], cw = cih[0] && cid[1];
    wire [2:0] se = fe + ne + oe + ae + ce, sw_ = fw + nw + ow + aw + cw;
    wire nxv_out = (r_mape && nev) || (r_mapw && nwv);
    wire vt_on = vt_n != 2'd0;
    wire [2:0] sv = ofv + nxv_out + (cih[0] && cid[2]) + vt_on;
    assign flt_set = se > 3'd1 || sw_ > 3'd1 || nown > 3'd1 || sv > 3'd1 || (own_v && asm_v) || (cxo && (own_v || asm_v));
    assign g_v_n = {ie_v && (ie_k == K_XQ || ie_k == K_XB), iw_v && (iw_k == K_XQ || iw_k == K_XB),
                    (own_v && (own_k == K_XQ || own_k == K_XB)) || asm_v || cxo};
    assign g_fe = ie_k == K_XB;
    assign g_fw = iw_k == K_XB;
    assign m_a = asm_v; assign m_c = !asm_v && cxo; assign m_o = !asm_v && !cxo;
    assign dlev_n = iw_v && iw_k != K_XQ && iw_k != K_XB && iw_k != K_NX;
    assign dlwv_n = ie_v && ie_k != K_XQ && ie_k != K_XB && ie_k != K_NX;
    assign dlvv_n = iv_v && iv_k != K_XQ && iv_k != K_XB && iv_k != K_NX && !fr_on;
    wire v_nx = iv_v && iv_k == K_NX && !fr_on;
    wire xw_nx = r_tier ? (ie_v && ie_k == K_NX) : (iw_v && iw_k == K_NX);
    wire xe_nx = r_tier ? (iw_v && iw_k == K_NX) : (ie_v && ie_k == K_NX);
    assign nxwv_n = r_mapw ? v_nx : xw_nx;
    assign nxev_n = r_mape ? v_nx : xe_nx;
endmodule

module ot_s81sl_rs (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,          // 2 * col + tier (strap)
    input  wire [1103:0]   ri_w,
    input  wire [1103:0]   ri_e,
    output wire [1103:0]   ro_e,
    output wire [1103:0]   ro_w,
    input  wire [275:0]    vi,
    output wire [275:0]    vo,
    input  wire [4:0]      xf_v,
    input  wire [4:0]      xf_s,
    input  wire [1379:0]   xf,
    output wire [172:0]    nx_wi,
    output wire [172:0]    nx_ei,
    input  wire [172:0]    nx_eo,
    input  wire [172:0]    nx_wo,
    output wire [2:0]      g_v,
    output wire [2:0]      g_fam,
    output wire [20:0]     g_idx,
    output wire [3071:0]   g_d,
    output wire            dl_ev, output wire [1103:0] dl_e,
    output wire            dl_wv, output wire [1103:0] dl_w,
    output wire            dl_vv, output wire [275:0] dl_vb,
    input  wire [2:0]      ci_dir,
    input  wire [1103:0]   ci_b,
    output reg             fault
);
    localparam integer W = 1104, V = 276, LB = 12, NL = 92, NC = 31;
    // ---------------------------------------------------------------- reset regions
    wire [47:0] rr;
    ot_s81sl_rs_rst u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rs_v = rr[47], rs_m = rr[46];
    // ---------------------------------------------------------------- data pin flops (reset-free)
    reg [W-1:0] iw, ie, ci_q; reg [V-1:0] iv; reg [5*V-1:0] xf_q; reg [171:0] neo_q, nwo_q;
    always @(posedge clk) begin
        iw <= ri_w; ie <= ri_e; iv <= vi; xf_q <= xf; neo_q <= nx_eo[171:0]; nwo_q <= nx_wo[171:0]; ci_q <= ci_b;
    end
    // ---------------------------------------------------------------- capture copies
    wire [8:0] c_iwh [0:NC-1]; wire [8:0] c_ieh [0:NC-1]; wire [3:0] c_ivh [0:NC-1]; wire [8:0] c_cih [0:NC-1];
    wire [2:0] c_cid [0:NC-1]; wire [NC-1:0] c_nev, c_nwv; wire [4:0] c_xfv [0:NC-1]; wire [4:0] c_xfs [0:NC-1];
    wire [3:0] c_sid [0:NC-1];
    genvar c, j, i;
    generate for (c = 0; c < NC; c = c + 1) begin : g_cp
        ot_s81sl_rs_cp u_cp (.clk(clk), .rst_n(rr[c]), .iwh_d(ri_w[8:0]), .ieh_d(ri_e[8:0]), .ivh_d(vi[3:0]),
            .cih_d(ci_b[8:0]), .cid_d(ci_dir), .nev_d(nx_eo[172]), .nwv_d(nx_wo[172]), .xfv_d(xf_v), .xfs_d(xf_s),
            .sid_d(sid), .iwh(c_iwh[c]), .ieh(c_ieh[c]), .ivh(c_ivh[c]), .cih(c_cih[c]), .cid(c_cid[c]), .nev(c_nev[c]),
            .nwv(c_nwv[c]), .xfv(c_xfv[c]), .xfs(c_xfs[c]), .sid(c_sid[c]));
    end endgenerate
    // ---------------------------------------------------------------- select leaves
    wire [NL-1:0] l_ef, l_enw, l_ene, l_eo, l_ea, l_ec, l_wf, l_wne, l_wnw, l_wo, l_wa, l_wc, l_ch0,
                  l_vo, l_vne, l_vnw, l_vc, l_vt0, l_vt1, l_vt2, l_sw0, l_sw1, l_sw2, l_sw3, l_vw0, l_vw1, l_vw2, l_vw3,
                  l_vtl, l_ga, l_gc, l_go, l_xwv, l_xwie, l_xwiw, l_xev, l_xeiw, l_xeie;
    wire [3:0] l_sid [0:NL-1]; wire [4:0] l_he [0:NL-1]; wire [4:0] l_hw [0:NL-1];
    wire [V-1:0] of;
    generate for (j = 0; j < NL; j = j + 1) begin : g_lf
        localparam integer CP = j / 3;
        wire [14:0] xf3;
        for (i = 0; i < 3; i = i + 1) begin : g_x
            assign xf3[i * 5 +: 5] = {xf_q[4 * V + 3 * j + i], xf_q[3 * V + 3 * j + i], xf_q[2 * V + 3 * j + i],
                                      xf_q[V + 3 * j + i], xf_q[3 * j + i]};
        end
        ot_s81sl_rs_lf u_lf (.clk(clk), .rst_n(rr[j / 2]), .iwh(c_iwh[CP]), .ieh(c_ieh[CP]), .ivh(c_ivh[CP]),
            .cih(c_cih[CP]), .cid(c_cid[CP]), .nev(c_nev[CP]), .nwv(c_nwv[CP]), .xfv(c_xfv[CP]), .xfs(c_xfs[CP]),
            .sid(c_sid[CP]), .xf3(xf3), .of3(of[3 * j +: 3]),
            .e_f(l_ef[j]), .e_nw(l_enw[j]), .e_ne(l_ene[j]), .e_o(l_eo[j]), .e_a(l_ea[j]), .e_c(l_ec[j]),
            .w_f(l_wf[j]), .w_ne(l_wne[j]), .w_nw(l_wnw[j]), .w_o(l_wo[j]), .w_a(l_wa[j]), .w_c(l_wc[j]),
            .c_h0(l_ch0[j]), .v_o(l_vo[j]), .v_ne(l_vne[j]), .v_nw(l_vnw[j]), .v_c(l_vc[j]), .v_t0(l_vt0[j]),
            .v_t1(l_vt1[j]), .v_t2(l_vt2[j]), .sw0(l_sw0[j]), .sw1(l_sw1[j]), .sw2(l_sw2[j]), .sw3(l_sw3[j]),
            .vw0(l_vw0[j]), .vw1(l_vw1[j]), .vw2(l_vw2[j]), .vw3(l_vw3[j]), .vtl(l_vtl[j]),
            .g_a(l_ga[j]), .g_c(l_gc[j]), .g_o(l_go[j]),
            .x_wv(l_xwv[j]), .x_wie(l_xwie[j]), .x_wiw(l_xwiw[j]), .x_ev(l_xev[j]), .x_eiw(l_xeiw[j]), .x_eie(l_xeie[j]),
            .r_sid(l_sid[j]), .r_he(l_he[j]), .r_hw(l_hw[j]));
    end endgenerate
    // ---------------------------------------------------------------- slot storage (constant-index decoded writes)
    reg [3 * V - 1:0] on_b, fr_b, vt_b; reg [W-1:0] own, asm_b;
    generate for (i = 0; i < 3 * V; i = i + 1) begin : g_slot
        localparam integer L = i / LB, SL = i / V, LT = (V + i) / LB;
        wire wo = SL == 0 ? l_sw0[L] : SL == 1 ? l_sw1[L] : l_sw2[L];
        wire wv = SL == 0 ? l_vw0[L] : SL == 1 ? l_vw1[L] : l_vw2[L];
        always @(posedge clk) begin
            if (wo) on_b[i] <= of[i % V];
            if (wv) fr_b[i] <= iv[i % V];
            if (l_vtl[LT]) vt_b[i] <= ci_q[V + i];
        end
    end endgenerate
    generate for (i = 0; i < W; i = i + 1) begin : g_ld
        localparam integer L = i / LB, SL = i / V;
`ifdef OT_S81SL_RSTOP_MUT_FRAG
        localparam integer OI = SL == 1 ? i + V : SL == 2 ? i - V : i;
`else
        localparam integer OI = i;
`endif
`ifdef OT_S81SL_RSTOP_MUT_VASM
        localparam integer AI = SL == 1 ? i + V : SL == 2 ? i - V : i;
`else
        localparam integer AI = i;
`endif
        always @(posedge clk) begin
            if (l_sw3[L]) own[i] <= SL == 3 ? of[i - 3 * V] : on_b[OI];
            if (l_vw3[L]) asm_b[i] <= SL == 3 ? iv[i - 3 * V] : fr_b[AI];
        end
    end endgenerate
    // ---------------------------------------------------------------- master
    wire flt_set, g_fe, g_fw, m_a, m_c, m_o, dlev_n, dlwv_n, dlvv_n, nxwv_n, nxev_n; wire [2:0] g_v_n;
    ot_s81sl_rs_m u_m (.clk(clk), .rst_n(rs_m), .iwh(c_iwh[0]), .ieh(c_ieh[0]), .ivh(c_ivh[0]), .cih(c_cih[0]),
        .cid(c_cid[0]), .nev(c_nev[0]), .nwv(c_nwv[0]), .xfv(c_xfv[0]), .xfs(c_xfs[0]), .sid(c_sid[0]), .own_k(own[3:1]),
        .flt_set(flt_set), .g_v_n(g_v_n), .g_fe(g_fe), .g_fw(g_fw), .m_a(m_a), .m_c(m_c), .m_o(m_o),
        .dlev_n(dlev_n), .dlwv_n(dlwv_n), .dlvv_n(dlvv_n), .nxwv_n(nxwv_n), .nxev_n(nxev_n));
    always @(posedge clk or negedge rs_m)
        if (!rs_m) fault <= 1'b0;
        else if (flt_set) fault <= 1'b1;
    // ---------------------------------------------------------------- line / V output words (one-hot AND-OR)
    wire [4:0] iw_hd = iw[8:4] - 5'd1, ie_hd = ie[8:4] - 5'd1;
    wire [W-1:0] ro_e_n, ro_w_n; wire [V-1:0] vo_n;
    generate for (i = 0; i < W; i = i + 1) begin : g_mux
        localparam integer L = i / LB;
        // field values per bit: forward (hops - 1), own / assembled / ci with this stop's hops + src, NX format
        wire [3:0] s4 = l_sid[L]; wire [4:0] he = l_he[L], hw = l_hw[L];
        wire fwd_e = (i >= 4 && i <= 8) ? iw_hd[(i >= 4 && i <= 8) ? i - 4 : 0] : iw[i];
        wire fwd_w = (i >= 4 && i <= 8) ? ie_hd[(i >= 4 && i <= 8) ? i - 4 : 0] : ie[i];
        wire hs_e = (i >= 4 && i <= 8) ? he[(i >= 4 && i <= 8) ? i - 4 : 0] : s4[(i >= 9 && i <= 12) ? i - 9 : 0];
        wire hs_w = (i >= 4 && i <= 8) ? hw[(i >= 4 && i <= 8) ? i - 4 : 0] : s4[(i >= 9 && i <= 12) ? i - 9 : 0];
        localparam integer HF = (i >= 4 && i <= 12) ? 1 : 0;           // hdr() field bit
        wire own_e = HF ? hs_e : own[i], own_w = HF ? hs_w : own[i];
        wire asm_e = HF ? hs_e : asm_b[i], asm_w = HF ? hs_w : asm_b[i];
        wire ci_e = (HF && l_ch0[L]) ? hs_e : ci_q[i], ci_w = (HF && l_ch0[L]) ? hs_w : ci_q[i];
        // nxb(f, sid) bit i for f = neo / nwo (xfin side word {v, h 4, b 8, d 160})
        wire nx_n, nx_s;   // from nwo_q / neo_q
        if (i == 0 || i == 1 || i == 2) begin : g_n1
            assign nx_n = 1'b1; assign nx_s = 1'b1;
        end else if (i == 3 || i == 8) begin : g_n0
            assign nx_n = 1'b0; assign nx_s = 1'b0;
        end else if (i >= 4 && i <= 7) begin : g_nh
            assign nx_n = nwo_q[168 + i - 4]; assign nx_s = neo_q[168 + i - 4];
        end else if (i >= 9 && i <= 12) begin : g_ns
            assign nx_n = s4[i - 9]; assign nx_s = s4[i - 9];
        end else if (i >= 13 && i <= 20) begin : g_nb
            assign nx_n = nwo_q[160 + i - 13]; assign nx_s = neo_q[160 + i - 13];
        end else if (i >= 21 && i <= 180) begin : g_nd
            assign nx_n = nwo_q[i - 21]; assign nx_s = neo_q[i - 21];
        end else begin : g_nz
            assign nx_n = 1'b0; assign nx_s = 1'b0;
        end
`ifdef OT_S81SL_RS_MUT_SLICE
        wire ef = L == 7 ? l_wf[L] : l_ef[L];
`else
        wire ef = l_ef[L];
`endif
        assign ro_e_n[i] = (ef & fwd_e) | (l_enw[L] & nx_n) | (l_ene[L] & nx_s) | (l_eo[L] & own_e) | (l_ea[L] & asm_e) |
                           (l_ec[L] & ci_e);
        assign ro_w_n[i] = (l_wf[L] & fwd_w) | (l_wne[L] & nx_s) | (l_wnw[L] & nx_n) | (l_wo[L] & own_w) |
                           (l_wa[L] & asm_w) | (l_wc[L] & ci_w);
        if (i < V) begin : g_vo
            assign vo_n[i] = (l_vo[L] & of[i]) | (l_vne[L] & nx_s) | (l_vnw[L] & nx_n) | (l_vc[L] & ci_q[i]) |
                             (l_vt0[L] & vt_b[i]) | (l_vt1[L] & vt_b[V + i]) | (l_vt2[L] & vt_b[2 * V + i]);
        end
    end endgenerate
    // ---------------------------------------------------------------- gather word (own side: asm / ci / own)
    wire [3071:0] g_d_n;
    generate for (i = 0; i < 1024; i = i + 1) begin : g_gd
        localparam integer P = 21 + i, L = P / LB;
`ifdef OT_S81SL_RSTOP_MUT_GSWAP
        assign g_d_n[2048 + i] = iw[P]; assign g_d_n[1024 + i] = ie[P];
`else
        assign g_d_n[2048 + i] = ie[P]; assign g_d_n[1024 + i] = iw[P];
`endif
        assign g_d_n[i] = (l_ga[L] & asm_b[P]) | (l_gc[L] & ci_q[P]) | (l_go[L] & own[P]);
    end endgenerate
    wire [9:0] g0h;   // g0 bits [3:1] and [19:13] (master select)
    generate for (i = 0; i < 10; i = i + 1) begin : g_g0
        localparam integer P = i < 3 ? 1 + i : 13 + (i - 3);
        assign g0h[i] = (m_a & asm_b[P]) | (m_c & ci_q[P]) | (m_o & own[P]);
    end endgenerate
    // ---------------------------------------------------------------- xfin NX payloads
    wire [171:0] nxw_dn, nxe_dn;
    generate for (i = 0; i < 172; i = i + 1) begin : g_nx
        localparam integer P = i < 160 ? 21 + i : i < 168 ? 13 + (i - 160) : 4 + (i - 168);
        localparam integer L = P / LB;
        assign nxw_dn[i] = (l_xwv[L] & iv[P]) | (l_xwie[L] & ie[P]) | (l_xwiw[L] & iw[P]);
        assign nxe_dn[i] = (l_xev[L] & iv[P]) | (l_xeiw[L] & iw[P]) | (l_xeie[L] & ie[P]);
    end endgenerate
    // ---------------------------------------------------------------- stage p (= ot_s81sl_rstop output registers)
    reg [W-1:0] ro_e_p, ro_w_p, dl_e_p, dl_w_p; reg [V-1:0] vo_p, dl_vb_p; reg [171:0] nxw_d, nxe_d;
    reg [2:0] g_v_p, g_fam_p; reg [20:0] g_idx_p; reg [3071:0] g_d_p; reg dl_ev_p, dl_wv_p, dl_vv_p, nxw_v, nxe_v;
    always @(posedge clk or negedge rs_v)
        if (!rs_v) begin
            ro_e_p[0] <= 1'b0; ro_w_p[0] <= 1'b0; vo_p[0] <= 1'b0; g_v_p <= 3'b000;
            dl_ev_p <= 1'b0; dl_wv_p <= 1'b0; dl_vv_p <= 1'b0; nxw_v <= 1'b0; nxe_v <= 1'b0;
        end else begin
            ro_e_p[0] <= ro_e_n[0]; ro_w_p[0] <= ro_w_n[0]; vo_p[0] <= vo_n[0]; g_v_p <= g_v_n;
            dl_ev_p <= dlev_n; dl_wv_p <= dlwv_n; dl_vv_p <= dlvv_n; nxw_v <= nxwv_n; nxe_v <= nxev_n;
        end
    always @(posedge clk) begin
        ro_e_p[W-1:1] <= ro_e_n[W-1:1]; ro_w_p[W-1:1] <= ro_w_n[W-1:1]; vo_p[V-1:1] <= vo_n[V-1:1];
        dl_e_p <= iw; dl_w_p <= ie; dl_vb_p <= iv;
        nxw_d <= nxw_dn; nxe_d <= nxe_dn;
        g_fam_p <= {g_fe, g_fw, g0h[2:0] == 3'd2};
        g_idx_p <= {ie[19:13], iw[19:13], g0h[9:3]};
        g_d_p <= g_d_n;
    end
    // ---------------------------------------------------------------- stage q (output relay at the pins)
    reg [W-1:0] ro_e_q, ro_w_q, dl_e_q, dl_w_q; reg [V-1:0] vo_q, dl_vb_q; reg [172:0] nx_wi_q, nx_ei_q;
    reg [2:0] g_v_q, g_fam_q; reg [20:0] g_idx_q; reg [3071:0] g_d_q; reg dl_ev_q, dl_wv_q, dl_vv_q;
    always @(posedge clk or negedge rs_v)
        if (!rs_v) begin
            ro_e_q[0] <= 1'b0; ro_w_q[0] <= 1'b0; vo_q[0] <= 1'b0; dl_ev_q <= 1'b0; dl_wv_q <= 1'b0; dl_vv_q <= 1'b0;
            nx_wi_q[172] <= 1'b0; nx_ei_q[172] <= 1'b0; g_v_q <= 3'b000;
        end else begin
            ro_e_q[0] <= ro_e_p[0]; ro_w_q[0] <= ro_w_p[0]; vo_q[0] <= vo_p[0];
            dl_ev_q <= dl_ev_p; dl_wv_q <= dl_wv_p; dl_vv_q <= dl_vv_p;
            nx_wi_q[172] <= nxw_v; nx_ei_q[172] <= nxe_v; g_v_q <= g_v_p;
        end
    always @(posedge clk) begin
        ro_e_q[W-1:1] <= ro_e_p[W-1:1]; ro_w_q[W-1:1] <= ro_w_p[W-1:1]; vo_q[V-1:1] <= vo_p[V-1:1];
        dl_e_q <= dl_e_p; dl_w_q <= dl_w_p; dl_vb_q <= dl_vb_p;
        nx_wi_q[171:0] <= nxw_d; nx_ei_q[171:0] <= nxe_d;
        g_fam_q <= g_fam_p; g_idx_q <= g_idx_p; g_d_q <= g_d_p;
    end
    assign ro_e = ro_e_q; assign ro_w = ro_w_q; assign vo = vo_q;
    assign dl_ev = dl_ev_q; assign dl_e = dl_e_q; assign dl_wv = dl_wv_q; assign dl_w = dl_w_q;
    assign dl_vv = dl_vv_q; assign dl_vb = dl_vb_q; assign nx_wi = nx_wi_q; assign nx_ei = nx_ei_q;
    assign g_v = g_v_q; assign g_fam = g_fam_q; assign g_idx = g_idx_q; assign g_d = g_d_q;
endmodule
