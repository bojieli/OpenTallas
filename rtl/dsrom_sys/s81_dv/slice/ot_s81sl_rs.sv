`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81-XG3 (LEAD3-S81, 10-19): ot_s81sl_rs -- the slice ring stop data plane as its OWN hardened leaf (sibling of the x
// streamer leaf in the slice parent; the old ot_s81sl_xg tile merged both: 38k flops on one root over 648 um, gate xgr /
// xgr2 FAIL).  Cycle-for-cycle the function of ot_s81sl_rstop #(.RELAY(1)) (same ports, same edges, same faults; checked
// by tools/s81_slice/rs_equiv.sh against ot_s81sl_rstop RELAY=1 under random and protocol stimulus), restructured:
//
//   bit-sliced control  the line word is cut into 46 slices of 24 b.  Each slice owns a kept control copy
//                       (ot_s81sl_rs_cc, keep_hierarchy, no parameters so Yosys cannot rename it): its own pin-flop copies
//                       of the line / V / control-inject headers, xfin NX valids, own-fragment valids and the sid strap,
//                       plus replicas of the fragment-assembly state (on_n / own_v, fr_on / fr_n / asm_v).  Every wide
//                       select (forward / NX / own / V-assembled / control inject, slot writes, own-vs-assembled gather)
//                       drives <= ~24 b of mux from a copy that placement can put beside that slice: in rstop one header
//                       decode drove 1,104-b muxes in both directions plus the 3 x 1,024-b gather word.
//   header bits [20:0]  (hops / src / NX format / gather index) and every scalar valid / fault decision use copy 0 (master)
//                       exactly as ot_s81sl_rstop does.
//   reset               ot_rst_relay, 4 regions (copies + master <= ~160 reset loads a region); release 3 edges after
//                       rst_n (transaction-level, like ot_s81sl_xs).  Payload registers reset-free (RELAY = 1 rule).
//   outputs             every external output leaves through the relay register (RELAY = 1): no single-cycle wire
//                       crosses the tile.
// Mutant defines (S81-XG bench negative controls) keep the rstop names: OT_S81SL_RSTOP_MUT_FRAG / _VASM / _GSWAP / _TIERCOL.
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy *)
module ot_s81sl_rs_cc (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [12:0] iwh_d,     // ri_w[12:0]
    input  wire [12:0] ieh_d,     // ri_e[12:0]
    input  wire [3:0]  ivh_d,     // vi[3:0]
    input  wire        ci0_d,     // ci_b[0]
    input  wire [2:0]  cid_d,     // ci_dir
    input  wire        nev_d,     // nx_eo[172]
    input  wire        nwv_d,     // nx_wo[172]
    input  wire [4:0]  xfv_d,     // xf_v
    input  wire [4:0]  xfs_d,     // xf_s
    input  wire [3:0]  sid_d,
    output wire        fe, output wire fw, output wire ne, output wire nw, output wire oe, output wire ow,
    output wire        ae, output wire aw, output wire ce, output wire cw,
    output wire        tier, output wire map_e, output wire map_w,
    output wire        nxv_e, output wire nxv_out, output wire vci,
    output wire [4:0]  xfv, output wire ofv, output wire ofs,
    output wire        sw0, output wire sw1, output wire sw2, output wire sw3,   // own slot writes / own load
    output wire        vw0, output wire vw1, output wire vw2, output wire vw3,   // V slot writes / assembled load
    output wire        own_v_o, output wire asm_v_o, output wire fr_on_o
);
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    reg [12:0] iwh, ieh; reg [3:0] ivh; reg ci0; reg [2:0] cid; reg nev, nwv; reg [4:0] xfs_q; reg [3:0] sid_c;
    reg [4:0] xfv_q;
    always @(posedge clk) begin
        iwh <= iwh_d; ieh <= ieh_d; ivh <= ivh_d; ci0 <= ci0_d; cid <= cid_d; nev <= nev_d; nwv <= nwv_d;
        xfs_q <= xfs_d; sid_c <= sid_d;
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) xfv_q <= 5'd0; else xfv_q <= xfv_d;
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    wire [2:0] col = sid_c[2:0]; assign tier = sid_c[3];
`else
    wire [2:0] col = sid_c[3:1]; assign tier = sid_c[0];
`endif
    assign map_e = tier ? col == 3'd0 : col == 3'd7;
    assign map_w = tier ? col == 3'd7 : col == 3'd0;
    wire [4:0] h_e = 5'd7 - {2'd0, col}, h_w = {2'd0, col};
    assign xfv = xfv_q;
    assign ofv = |xfv_q;
    assign ofs = |(xfv_q & xfs_q);
    // fragment-assembly state replicas (identical next-state functions to ot_s81sl_rstop)
    reg [1:0] on_n; reg own_v; reg [1:0] fr_n; reg fr_on; reg asm_v;
    wire iv_v = ivh[0]; wire [2:0] iv_k = ivh[3:1];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin on_n <= 2'd0; own_v <= 1'b0; fr_on <= 1'b0; fr_n <= 2'd0; asm_v <= 1'b0; end
        else begin
            own_v <= ofv && !ofs && on_n == 2'd3;
            if (ofv) on_n <= ofs ? 2'd1 : on_n + 2'd1;
            asm_v <= 1'b0;
            if (fr_on) begin
                fr_n <= fr_n + 2'd1;
                if (fr_n == 2'd3) begin fr_on <= 1'b0; asm_v <= 1'b1; end
            end else if (iv_v && (iv_k == K_XQ || iv_k == K_XB)) begin fr_on <= 1'b1; fr_n <= 2'd1; end
        end
    assign own_v_o = own_v; assign asm_v_o = asm_v; assign fr_on_o = fr_on;
    assign sw0 = ofv && (ofs || on_n == 2'd0);
    assign sw1 = ofv && !ofs && on_n == 2'd1;
    assign sw2 = ofv && !ofs && on_n == 2'd2;
    assign sw3 = ofv && !ofs && on_n == 2'd3;
    assign vw0 = !fr_on || fr_n == 2'd0;
    assign vw1 = fr_on && fr_n == 2'd1;
    assign vw2 = fr_on && fr_n == 2'd2;
    assign vw3 = fr_on && fr_n == 2'd3;
    wire iw_v = iwh[0], ie_v = ieh[0];
    wire [2:0] iw_k = iwh[3:1], ie_k = ieh[3:1];
    wire [4:0] iw_h = iwh[8:4], ie_h = ieh[8:4];
    assign fe = iw_v && iw_k != K_NX && iw_h > 5'd1;
    assign fw = ie_v && ie_k != K_NX && ie_h > 5'd1;
    assign ne = tier ? (nwv && !map_w) : (nev && !map_e);
    assign nw = tier ? (nev && !map_e) : (nwv && !map_w);
    assign oe = own_v && h_e != 5'd0; assign ow = own_v && h_w != 5'd0;
    assign ae = asm_v && h_e != 5'd0; assign aw = asm_v && h_w != 5'd0;
    assign ce = ci0 && cid[0]; assign cw = ci0 && cid[1];
    assign nxv_e = map_e && nev;
    assign nxv_out = (map_e && nev) || (map_w && nwv);
    assign vci = ci0 && cid[2];
endmodule

module ot_s81sl_rs #(
    parameter integer W = 1104,
    parameter integer V = 276
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [3:0]      sid,
    input  wire [W-1:0]    ri_w,
    input  wire [W-1:0]    ri_e,
    output wire [W-1:0]    ro_e,
    output wire [W-1:0]    ro_w,
    input  wire [V-1:0]    vi,
    output wire [V-1:0]    vo,
    input  wire [4:0]      xf_v,
    input  wire [4:0]      xf_s,
    input  wire [5*V-1:0]  xf,
    output wire [172:0]    nx_wi,
    output wire [172:0]    nx_ei,
    input  wire [172:0]    nx_eo,
    input  wire [172:0]    nx_wo,
    output reg  [2:0]      g_v,
    output reg  [2:0]      g_fam,
    output reg  [20:0]     g_idx,
    output reg  [3071:0]   g_d,
    output wire            dl_ev, output wire [W-1:0] dl_e,
    output wire            dl_wv, output wire [W-1:0] dl_w,
    output wire            dl_vv, output wire [V-1:0] dl_vb,
    input  wire [2:0]      ci_dir,
    input  wire [W-1:0]    ci_b,
    output reg             fault
);
    localparam integer SW = 24, NS = W / SW;      // 46 control slices
    localparam [2:0] K_XQ = 3'd1, K_XB = 3'd2, K_NX = 3'd3;
    // ---------------------------------------------------------------- reset relay
    wire [3:0] rsv;
    ot_rst_relay #(.REGIONS(4), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rsv));
    wire rs_m = rsv[0];
    // ---------------------------------------------------------------- input pin flops (data)
    reg [W-1:0] iw, ie, ci_q; reg [V-1:0] iv; reg [5*V-1:0] xf_q; reg [172:0] neo_q, nwo_q; reg [3:0] sid_c;
    always @(posedge clk) begin
        iw <= ri_w; ie <= ri_e; iv <= vi; xf_q <= xf; neo_q <= nx_eo; nwo_q <= nx_wo; ci_q <= ci_b; sid_c <= sid;
    end
    // ---------------------------------------------------------------- control copies
    wire [NS-1:0] c_fe, c_fw, c_ne, c_nw, c_oe, c_ow, c_ae, c_aw, c_ce, c_cw, c_tier, c_mape, c_mapw, c_nxve, c_nxvo, c_vci,
                  c_ofv, c_ofs, c_fron, c_sw0, c_sw1, c_sw2, c_sw3, c_vw0, c_vw1, c_vw2, c_vw3, c_ownv, c_asmv;
    wire [4:0] c_xfv [0:NS-1];
    genvar s;
    generate for (s = 0; s < NS; s = s + 1) begin : g_cc
        ot_s81sl_rs_cc u_cc (.clk(clk), .rst_n(rsv[s * 4 / NS]), .iwh_d(ri_w[12:0]), .ieh_d(ri_e[12:0]), .ivh_d(vi[3:0]),
            .ci0_d(ci_b[0]), .cid_d(ci_dir), .nev_d(nx_eo[172]), .nwv_d(nx_wo[172]), .xfv_d(xf_v), .xfs_d(xf_s), .sid_d(sid),
            .fe(c_fe[s]), .fw(c_fw[s]), .ne(c_ne[s]), .nw(c_nw[s]), .oe(c_oe[s]), .ow(c_ow[s]), .ae(c_ae[s]), .aw(c_aw[s]),
            .ce(c_ce[s]), .cw(c_cw[s]), .tier(c_tier[s]), .map_e(c_mape[s]), .map_w(c_mapw[s]), .nxv_e(c_nxve[s]),
            .nxv_out(c_nxvo[s]), .vci(c_vci[s]), .xfv(c_xfv[s]), .ofv(c_ofv[s]), .ofs(c_ofs[s]),
            .sw0(c_sw0[s]), .sw1(c_sw1[s]), .sw2(c_sw2[s]), .sw3(c_sw3[s]), .vw0(c_vw0[s]), .vw1(c_vw1[s]), .vw2(c_vw2[s]),
            .vw3(c_vw3[s]), .own_v_o(c_ownv[s]), .asm_v_o(c_asmv[s]), .fr_on_o(c_fron[s]));
    end endgenerate
    // master (copy 0) scalars
    wire tier = c_tier[0], map_e = c_mape[0], map_w = c_mapw[0];
`ifdef OT_S81SL_RSTOP_MUT_TIERCOL
    wire [2:0] col = sid_c[2:0];
`else
    wire [2:0] col = sid_c[3:1];
`endif
    wire [4:0] h_e = 5'd7 - {2'd0, col}, h_w = {2'd0, col};
    wire own_v = c_ownv[0], asm_v = c_asmv[0], ofv = c_ofv[0];
    wire iw_v = iw[0], ie_v = ie[0];
    wire [2:0] iw_k = iw[3:1], ie_k = ie[3:1];
    wire [4:0] iw_h = iw[8:4], ie_h = ie[8:4];
    wire iv_v = iv[0]; wire [2:0] iv_k = iv[3:1];
    // ---------------------------------------------------------------- own fragments / V fragments: storage per bit
    // of(b) = OR over the 5 leaves of (fragment valid copy & fragment bit b), computed per bit from the slice's copy
    reg [3 * V - 1:0] on_b, fr_b; reg [W-1:0] own, asm_b;
    wire [W-1:0] of_w;        // of(i % V) per line bit, merged with the line bit's slice copy
    wire [V-1:0] of_v;        // of(b) for the V output, merged with bit b's slice copy
    genvar i;
    generate for (i = 0; i < W; i = i + 1) begin : g_of
        localparam integer SI = i / SW, B = i % V;
        wire [4:0] fv = c_xfv[SI];
        assign of_w[i] = (fv[0] & xf_q[B]) | (fv[1] & xf_q[V + B]) | (fv[2] & xf_q[2 * V + B]) | (fv[3] & xf_q[3 * V + B]) |
                         (fv[4] & xf_q[4 * V + B]);
        if (i < V) begin : g_v
            assign of_v[i] = of_w[i];
        end
    end endgenerate
    generate for (i = 0; i < 3 * V; i = i + 1) begin : g_slot
        localparam integer SI = i / SW, SL = i / V;
        wire wo = SL == 0 ? c_sw0[SI] : SL == 1 ? c_sw1[SI] : c_sw2[SI];
        wire wv = SL == 0 ? c_vw0[SI] : SL == 1 ? c_vw1[SI] : c_vw2[SI];
        always @(posedge clk) begin
            if (wo) on_b[i] <= of_w[i];
            if (wv) fr_b[i] <= iv[i % V];
        end
    end endgenerate
    generate for (i = 0; i < W; i = i + 1) begin : g_ld
        localparam integer SI = i / SW, SL = i / V;
`ifdef OT_S81SL_RSTOP_MUT_FRAG
        localparam integer OI = SL == 1 ? i + V : SL == 2 ? i - V : i;     // own slots 1 / 2 swapped
`else
        localparam integer OI = i;
`endif
`ifdef OT_S81SL_RSTOP_MUT_VASM
        localparam integer AI = SL == 1 ? i + V : SL == 2 ? i - V : i;     // V-assembled slots 1 / 2 swapped
`else
        localparam integer AI = i;
`endif
        always @(posedge clk) begin
            if (c_sw3[SI]) own[i] <= SL == 3 ? of_w[i] : on_b[OI];
            if (c_vw3[SI]) asm_b[i] <= SL == 3 ? iv[i - 3 * V] : fr_b[AI];
        end
    end endgenerate
    // ---------------------------------------------------------------- header-format helpers (master, bits [20:0])
    function automatic [W-1:0] hdr(input [W-1:0] b, input [4:0] h, input [3:0] s_);
        begin hdr = b; hdr[8:4] = h; hdr[12:9] = s_; end
    endfunction
    function automatic [W-1:0] nxb(input [172:0] f, input [3:0] s_);
        begin nxb = {W{1'b0}}; nxb[0] = 1'b1; nxb[3:1] = K_NX; nxb[8:4] = {1'b0, f[171:168]}; nxb[12:9] = s_;
              nxb[20:13] = f[167:160]; nxb[21 +: 160] = f[159:0]; end
    endfunction
    wire fe = c_fe[0], fw = c_fw[0], ne = c_ne[0], nw = c_nw[0], oe = c_oe[0], ow = c_ow[0], ae = c_ae[0], aw = c_aw[0];
    wire ce = c_ce[0], cw = c_cw[0];
    wire [172:0] nx_pe = tier ? nwo_q : neo_q, nx_pw = tier ? neo_q : nwo_q;
    wire nxv_out = c_nxvo[0];
    wire [172:0] nxv_f = c_nxve[0] ? neo_q : nwo_q;
    wire [W-1:0] nxv_b = nxb(nxv_f, sid_c);
    wire [W-1:0] he_n = fe ? hdr(iw, iw_h - 5'd1, iw[12:9]) : ne ? nxb(nx_pe, sid_c) : oe ? hdr(own, h_e, sid_c) :
                        ae ? hdr(asm_b, h_e, sid_c) : ce ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_e, sid_c) : ci_q) : {W{1'b0}};
    wire [W-1:0] hw_n = fw ? hdr(ie, ie_h - 5'd1, ie[12:9]) : nw ? nxb(nx_pw, sid_c) : ow ? hdr(own, h_w, sid_c) :
                        aw ? hdr(asm_b, h_w, sid_c) : cw ? ((ci_q[8:4] == 5'd0) ? hdr(ci_q, h_w, sid_c) : ci_q) : {W{1'b0}};
    wire [V-1:0] hv_n = ofv ? of_v : nxv_out ? nxv_b[V-1:0] : c_vci[0] ? ci_q[V-1:0] : {V{1'b0}};
    // ---------------------------------------------------------------- line / V output selection, sliced
    wire [W-1:0] ro_e_n, ro_w_n; wire [V-1:0] vo_n;
    generate for (i = 0; i < W; i = i + 1) begin : g_mux
        localparam integer SI = i / SW;
        if (i < 21) begin : g_h
            assign ro_e_n[i] = he_n[i]; assign ro_w_n[i] = hw_n[i];
        end else begin : g_p
            wire t = c_tier[SI];
            wire nbe = (i < 181) ? (t ? nwo_q[i - 21] : neo_q[i - 21]) : 1'b0;
            wire nbw = (i < 181) ? (t ? neo_q[i - 21] : nwo_q[i - 21]) : 1'b0;
`ifdef OT_S81SL_RS_MUT_SLICE
            // NEGATIVE CONTROL (rs_equiv): slice 7's E-line forward select taken from the W-line decode
            wire fe_s = SI == 7 ? c_fw[SI] : c_fe[SI];
`else
            wire fe_s = c_fe[SI];
`endif
            assign ro_e_n[i] = fe_s ? iw[i] : c_ne[SI] ? nbe : c_oe[SI] ? own[i] : c_ae[SI] ? asm_b[i] :
                               c_ce[SI] ? ci_q[i] : 1'b0;
            assign ro_w_n[i] = c_fw[SI] ? ie[i] : c_nw[SI] ? nbw : c_ow[SI] ? own[i] : c_aw[SI] ? asm_b[i] :
                               c_cw[SI] ? ci_q[i] : 1'b0;
        end
        if (i < V) begin : g_vo
            if (i < 21) begin : g_vh
                assign vo_n[i] = hv_n[i];
            end else begin : g_vp
                wire nbv = (i < 181) ? (c_nxve[SI] ? neo_q[i - 21] : nwo_q[i - 21]) : 1'b0;
                assign vo_n[i] = c_ofv[SI] ? of_v[i] : c_nxvo[SI] ? nbv : c_vci[SI] ? ci_q[i] : 1'b0;
            end
        end
    end endgenerate
    // ---------------------------------------------------------------- faults (master)
    wire [2:0] se = fe + ne + oe + ae + ce, sw_ = fw + nw + ow + aw + cw;
    wire [4:0] xv0 = c_xfv[0];
    wire [2:0] nown = xv0[0] + xv0[1] + xv0[2] + xv0[3] + xv0[4];
    wire [2:0] sv = ofv + nxv_out + c_vci[0];
    always @(posedge clk or negedge rs_m)
        if (!rs_m) fault <= 1'b0;
        else if (se > 3'd1 || sw_ > 3'd1 || nown > 3'd1 || sv > 3'd1 || (own_v && asm_v)) fault <= 1'b1;
    // ---------------------------------------------------------------- output registers (valid bits reset only)
    reg [W-1:0] ro_e_p, ro_w_p, dl_e_p, dl_w_p; reg [V-1:0] vo_p, dl_vb_p; reg dl_ev_p, dl_wv_p, dl_vv_p;
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin ro_e_p[0] <= 1'b0; ro_w_p[0] <= 1'b0; vo_p[0] <= 1'b0; end
        else begin ro_e_p[0] <= ro_e_n[0]; ro_w_p[0] <= ro_w_n[0]; vo_p[0] <= vo_n[0]; end
    always @(posedge clk) begin ro_e_p[W-1:1] <= ro_e_n[W-1:1]; ro_w_p[W-1:1] <= ro_w_n[W-1:1]; vo_p[V-1:1] <= vo_n[V-1:1]; end
    // ---------------------------------------------------------------- deliveries
    reg nxw_v, nxe_v; reg [171:0] nxw_d, nxe_d;
    wire fr_on_m = c_fron[0];
    wire v_nxm = iv_v && iv_k == K_NX && !fr_on_m;
    wire v_cs = iv_v && iv_k != K_XQ && iv_k != K_XB && iv_k != K_NX && !fr_on_m;
    wire xw_nx = tier ? (ie_v && ie_k == K_NX) : (iw_v && iw_k == K_NX);
    wire xe_nx = tier ? (iw_v && iw_k == K_NX) : (ie_v && ie_k == K_NX);
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin g_v <= 3'b000; dl_ev_p <= 1'b0; dl_wv_p <= 1'b0; dl_vv_p <= 1'b0; nxw_v <= 1'b0; nxe_v <= 1'b0; end
        else begin
            g_v <= {ie_v && (ie_k == K_XQ || ie_k == K_XB), iw_v && (iw_k == K_XQ || iw_k == K_XB),
                    (own_v && (own[3:1] == K_XQ || own[3:1] == K_XB)) || asm_v};
            dl_ev_p <= iw_v && iw_k != K_XQ && iw_k != K_XB && iw_k != K_NX;
            dl_wv_p <= ie_v && ie_k != K_XQ && ie_k != K_XB && ie_k != K_NX;
            dl_vv_p <= v_cs;
            nxw_v <= map_w ? v_nxm : xw_nx;
            nxe_v <= map_e ? v_nxm : xe_nx;
        end
    wire [W-1:0] g0m = asm_v ? asm_b : own;
    always @(posedge clk) begin
        g_fam <= {ie_k == K_XB, iw_k == K_XB, g0m[3:1] == K_XB};
        g_idx <= {ie[19:13], iw[19:13], g0m[19:13]};
        dl_e_p <= iw; dl_w_p <= ie; dl_vb_p <= iv;
    end
    // gather payload and NX payload bits: selects from the bit's slice copy
    generate for (i = 0; i < 1024; i = i + 1) begin : g_gd
        localparam integer P = 21 + i, SI = P / SW;
        wire g0b = c_asmv[SI] ? asm_b[P] : own[P];
        always @(posedge clk) begin
`ifdef OT_S81SL_RSTOP_MUT_GSWAP
            g_d[2048 + i] <= iw[P]; g_d[1024 + i] <= ie[P]; g_d[i] <= g0b;
`else
            g_d[2048 + i] <= ie[P]; g_d[1024 + i] <= iw[P]; g_d[i] <= g0b;
`endif
        end
    end endgenerate
    // nx field j: [159:0] <- word bit 21 + j, [167:160] <- bits [20:13], [171:168] <- bits [7:4]
    generate for (i = 0; i < 172; i = i + 1) begin : g_nx
        localparam integer P = i < 160 ? 21 + i : i < 168 ? 13 + (i - 160) : 4 + (i - 168);
        localparam integer SI = P / SW;
        wire t = c_tier[SI];
        wire xwb = t ? ie[P] : iw[P], xeb = t ? iw[P] : ie[P];
        always @(posedge clk) begin
            nxw_d[i] <= c_mapw[SI] ? iv[P] : xwb;
            nxe_d[i] <= c_mape[SI] ? iv[P] : xeb;
        end
    end endgenerate
    wire [172:0] nx_wi_p = {nxw_v, nxw_d}, nx_ei_p = {nxe_v, nxe_d};
    // ---------------------------------------------------------------- output relay (RELAY = 1 of ot_s81sl_rstop)
    reg [W-1:0] ro_e_q, ro_w_q, dl_e_q, dl_w_q; reg [V-1:0] vo_q, dl_vb_q; reg [172:0] nx_wi_q, nx_ei_q;
    reg dl_ev_q, dl_wv_q, dl_vv_q;
    always @(posedge clk or negedge rs_m)
        if (!rs_m) begin
            ro_e_q[0] <= 1'b0; ro_w_q[0] <= 1'b0; vo_q[0] <= 1'b0; dl_ev_q <= 1'b0; dl_wv_q <= 1'b0; dl_vv_q <= 1'b0;
            nx_wi_q[172] <= 1'b0; nx_ei_q[172] <= 1'b0;
        end else begin
            ro_e_q[0] <= ro_e_p[0]; ro_w_q[0] <= ro_w_p[0]; vo_q[0] <= vo_p[0];
            dl_ev_q <= dl_ev_p; dl_wv_q <= dl_wv_p; dl_vv_q <= dl_vv_p;
            nx_wi_q[172] <= nx_wi_p[172]; nx_ei_q[172] <= nx_ei_p[172];
        end
    always @(posedge clk) begin
        ro_e_q[W-1:1] <= ro_e_p[W-1:1]; ro_w_q[W-1:1] <= ro_w_p[W-1:1]; vo_q[V-1:1] <= vo_p[V-1:1];
        dl_e_q <= dl_e_p; dl_w_q <= dl_w_p; dl_vb_q <= dl_vb_p;
        nx_wi_q[171:0] <= nx_wi_p[171:0]; nx_ei_q[171:0] <= nx_ei_p[171:0];
    end
    assign ro_e = ro_e_q; assign ro_w = ro_w_q; assign vo = vo_q;
    assign dl_ev = dl_ev_q; assign dl_e = dl_e_q; assign dl_wv = dl_wv_q; assign dl_w = dl_w_q;
    assign dl_vv = dl_vv_q; assign dl_vb = dl_vb_q; assign nx_wi = nx_wi_q; assign nx_ei = nx_ei_q;
endmodule
