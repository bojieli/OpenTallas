`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-AHUB3 2026-10-19 (LEAD2-KV, tree K.STA.AHUB): qkd_ahub_static_dw_g2 = the SAFE attention hub qkd_ahub_static_dw_safe
// re-written as a WIRES-ONLY flat parent, so tools/landed_parent/lp.py can generate its LANDED-REGION form
// qkd_ahub_static_dw_g2_lp (spec tools/landed_parent/specs/qkd_ahub_static_dw_g2.json).
//
// Why: both single-root SAFE kits failed the clock rule (qkd_ahub_sfa pin-flop spread 86.5 TT / 97.3 FF, sfb 116.3 /
// 123.2): one insertion-aware spine across 734 x 540 um pads every hub flop to the hard children's insertion (ot_nhb_zh
// 246.5 ps, ot_qkh_recip_leaf 238.7 ps).  The landed form gives each Z tree its own region root ck_z<a> (the tree + its
// landing halves) and the core / io / reciprocal leaf the core root ck_c; every core <-> Z tree bus crosses through an
// lp.py landing (ot_pl_land_chunk ring on the source root, read on the destination root: LANDING-CONTRACT L1-L7, D 4,
// E = K 2, +3 edges, fixed latency, no ready / credit / backpressure).  This REPLACES the private grouped ZH transport
// (KV-AHUB2 7222d4264, results/arch/kv_ahub2_1019): that component was common-clock only (one `phase` for write and
// read); the lp.py landing IS the two-clock split (write ring + write pointer on the tx root, free-running read pointer
// + flop-last read on the rx root, epochs from equal-depth regional reset runs), chunked at 8 b with kept per-chunk
// selectors and a per-chunk reset forest (fanout <= 32 without a grouped admission tree).
//
// Function = qkd_ahub_static_dw_safe at the same parameters (same children, same nets, same relays), with three changes
// that are pure re-packaging (edge-exact):
//   * no internal reset synchroniser: every child reset pin is the rst_n port (lp.py inserts the regional reset runs;
//     the flat bench drives a synchronous reset);
//   * the ap pin flops (ap_q) and the Z-tree error flops (zh_err_q) are ot_qkd_drly N=1 children (were always blocks);
//   * the am_astk reorder / si_* field split / generate loops are written out as assigns.
// Z_LAND (0 in the flat parent): the edges the landed form adds to the core -> Z tree -> core round trip (2 landings x 3);
// only the core's calendar check RECIP_ISSUE > Z_START + 77 + Z_RT uses it (Z_RT = ZW_RLY + ZR_RLY + Z_LAND), so the flat
// reference with ZW_RLY = ZR_RLY = 3 and the landed form with Z_LAND = 6 check the same law.  The compiler moves HUB_RECIP
// (and HUB_PUB with it, the RECIP / PUB law unchanged) by +6 edges; see results/arch/kv_ahub3_1019/README.md.
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_static_dw_g2 #(
    parameter [63:0] AP_OFS = 64'hffd9ffdaffd8ffd8,
    parameter integer FR_OFS = -7,
    parameter integer Z_IN_STRIDE = 4,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer Z_LAND = 0,
    parameter integer RX_RLY = 1,
    parameter integer RY_RLY = 2,
    parameter integer RS_RLY = 1,
    parameter integer WF_RLY = 1,
    parameter integer HMUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,
    input  wire [15:0]   hs_cal_r,
    input  wire [42:0]   ap0,
    input  wire [42:0]   ap1,
    input  wire [42:0]   ap2,
    input  wire [42:0]   ap3,
    output wire [35:0]   am0,
    output wire [35:0]   am1,
    output wire [35:0]   am2,
    output wire [35:0]   am3,
    output wire          fr_valid,
    output wire [15:0]   fr_epoch,
    output wire [127:0]  fr_rz,
    output wire          hf
);
    wire start;  wire [15:0] epoch;  wire [5:0] layer;  wire [13:0] T;  wire [191:0] hub_cal;
    wire [63:0] si_epoch;  wire [23:0] si_layer;
    wire [143:0] am;  wire rz_valid, rz_publish, hub_fault;  wire [1:0] rz_head;  wire [31:0] rz_data;
    wire [15:0] rz_epoch;  wire [127:0] rz_vector;
    // ap pin flops (flop-first pins; + 1 edge on the hub input ages, priced in AP_OFS as in qkd_ahub_static_dw_safe)
    wire [171:0] ap;
    ot_qkd_drly #(.W(172), .N(1)) u_apq (.clk(ck), .d({ap3, ap2, ap1, ap0}), .q(ap));
    wire [3:0] si_valid, si_g, si_any;  wire [7:0] si_type, si_hh;  wire [15:0] si_k;  wire [127:0] si_data;
    assign si_valid = {ap[129], ap[86], ap[43], ap[0]};
    assign si_type  = {ap[131:130], ap[88:87], ap[45:44], ap[2:1]};
    assign si_g     = {ap[132], ap[89], ap[46], ap[3]};
    assign si_hh    = {ap[134:133], ap[91:90], ap[48:47], ap[5:4]};
    assign si_k     = {ap[138:135], ap[95:92], ap[52:49], ap[9:6]};
    assign si_any   = {ap[139], ap[96], ap[53], ap[10]};
    assign si_data  = {ap[171:140], ap[128:97], ap[85:54], ap[42:11]};
    // hub am copy s = {valid 35, g 34, hh 33:32, data 31:0} -> ASTK am order {data, hh, g, valid} (LSB first)
    assign am0 = {am[31:0],    am[33:32],   am[34],  am[35]};
    assign am1 = {am[67:36],   am[69:68],   am[70],  am[71]};
    assign am2 = {am[103:72],  am[105:104], am[106], am[107]};
    assign am3 = {am[139:108], am[141:140], am[142], am[143]};
    // W-face export relay (KV-AHUB7 WF_RLY; u_io emits WF_RLY edges earlier, fr lands on pvfin's R slot unchanged)
    wire fr_valid_i;  wire [15:0] fr_epoch_i;  wire [127:0] fr_rz_i;
    ot_qkd_drly #(.W(145), .N((HMUT == 6) ? 0 : WF_RLY)) u_rw (.clk(ck), .d({fr_rz_i, fr_epoch_i, fr_valid_i}),
        .q({fr_rz, fr_epoch, fr_valid}));
    qkd_ahub_static_io_safe #(.AP_OFS(AP_OFS), .FR_OFS(FR_OFS), .WF_RLY(WF_RLY), .MUT(HMUT)) u_io (
        .ck(ck), .rst_n(rst_n), .hs_start(hs_start), .hs_ep(hs_ep), .hs_layer(hs_layer), .hs_ctx(hs_ctx),
        .hs_cal_lo(hs_cal_lo), .hs_cal_r(hs_cal_r), .start(start), .epoch(epoch), .layer(layer), .T(T),
        .hub_cal(hub_cal), .si_epoch(si_epoch), .si_layer(si_layer), .rz_publish(rz_publish), .rz_epoch(rz_epoch),
        .rz_vector(rz_vector), .hub_fault(hub_fault), .fr_valid(fr_valid_i), .fr_epoch(fr_epoch_i), .fr_rz(fr_rz_i),
        .fault(hf));
    // ---- static hub core (look-ahead decodes) ----
    wire [3:0] zh_start, zh_g;  wire [511:0] zh_we, zh_sid;  wire [15:0] zh_iv;
    wire [23:0] zh_p;  wire [15:0] zh_err_q;
    wire rc_v, rc_vo, rc_fault;  wire [31:0] rc_x, rc_y;
    wire [15:0] recip_return = hub_cal[175:160] + 16'(67 + RS_RLY + RX_RLY + RY_RLY);
    wire [207:0] core_cal = {hub_cal[191:176], recip_return, hub_cal[175:0]};
    qkd_ahub_static_core_la_safe #(.Z_IN_STRIDE(Z_IN_STRIDE), .Z_LEVEL_GAP(10), .RS_RLY(RS_RLY),
                                   .Z_RT(ZW_RLY + ZR_RLY + Z_LAND), .MUT(HMUT)) u_core (
        .cal(core_cal),
        .clk(ck), .rst_n(rst_n), .start(start), .active_layer_parity(layer[0]), .request_epoch(epoch),
        .active_layer(layer), .T(T),
        .si_valid(si_valid), .si_type(si_type), .si_g(si_g), .si_hh(si_hh), .si_k(si_k), .si_any(si_any),
        .si_epoch(si_epoch), .si_layer(si_layer), .si_data(si_data),
        .am(am), .zh_start(zh_start), .zh_we(zh_we), .zh_sid(zh_sid), .zh_iv(zh_iv), .zh_g(zh_g), .zh_p(zh_p),
        .zh_root({zo3[63:0], zo2[63:0], zo1[63:0], zo0[63:0]}), .zh_err(zh_err_q), .rc_v(rc_v), .rc_x(rc_x), .rc_y(rc_y), .rc_vo(rc_vo), .rc_fault(rc_fault),
        .rz_valid(rz_valid), .rz_head(rz_head), .rz_data(rz_data), .rz_epoch(rz_epoch), .rz_publish(rz_publish),
        .rz4(rz_vector), .fault(hub_fault));
    // Z-tree error flops (KV-AHUBDW2: + 1 edge on that fault input only), core side
    ot_qkd_drly #(.W(16), .N(1)) u_eq (.clk(ck), .d({zo3[67:64], zo2[67:64], zo1[67:64], zo0[67:64]}), .q(zh_err_q));
    // ---- four Z trees: command relay (core side) -> tree -> return relay (tree side) ----
    wire [267:0] zi0, zi1, zi2, zi3;
    wire [67:0]  zt0, zt1, zt2, zt3, zo0, zo1, zo2, zo3;
    ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri0 (.clk(ck),
        .d({zh_start[0], zh_we[127:0],   zh_sid[127:0],   zh_iv[3:0],   zh_g[0], zh_p[5:0]}),   .q(zi0));
    ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri1 (.clk(ck),
        .d({zh_start[1], zh_we[255:128], zh_sid[255:128], zh_iv[7:4],   zh_g[1], zh_p[11:6]}),  .q(zi1));
    ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri2 (.clk(ck),
        .d({zh_start[2], zh_we[383:256], zh_sid[383:256], zh_iv[11:8],  zh_g[2], zh_p[17:12]}), .q(zi2));
    ot_qkd_drly #(.W(268), .N(ZW_RLY)) u_ri3 (.clk(ck),
        .d({zh_start[3], zh_we[511:384], zh_sid[511:384], zh_iv[15:12], zh_g[3], zh_p[23:18]}), .q(zi3));
    ot_nhb_zh u_zh0 (.clk(ck), .rst_n(rst_n), .start(zi0[267]), .zs_we(zi0[266:139]), .sid(zi0[138:11]),
                     .ziv(zi0[10:7]), .zg(zi0[6]), .zp(zi0[5:0]), .root(zt0[63:0]), .zerr(zt0[67:64]));
    ot_nhb_zh u_zh1 (.clk(ck), .rst_n(rst_n), .start(zi1[267]), .zs_we(zi1[266:139]), .sid(zi1[138:11]),
                     .ziv(zi1[10:7]), .zg(zi1[6]), .zp(zi1[5:0]), .root(zt1[63:0]), .zerr(zt1[67:64]));
    ot_nhb_zh u_zh2 (.clk(ck), .rst_n(rst_n), .start(zi2[267]), .zs_we(zi2[266:139]), .sid(zi2[138:11]),
                     .ziv(zi2[10:7]), .zg(zi2[6]), .zp(zi2[5:0]), .root(zt2[63:0]), .zerr(zt2[67:64]));
    ot_nhb_zh u_zh3 (.clk(ck), .rst_n(rst_n), .start(zi3[267]), .zs_we(zi3[266:139]), .sid(zi3[138:11]),
                     .ziv(zi3[10:7]), .zg(zi3[6]), .zp(zi3[5:0]), .root(zt3[63:0]), .zerr(zt3[67:64]));
    ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro0 (.clk(ck), .d(zt0), .q(zo0));
    ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro1 (.clk(ck), .d(zt1), .q(zo1));
    ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro2 (.clk(ck), .d(zt2), .q(zo2));
    ot_qkd_drly #(.W(68), .N(ZR_RLY)) u_ro3 (.clk(ck), .d(zt3), .q(zo3));
    // (the core reads the four roots and u_eq the four error nibbles straight off zo0..3: one landed net per tree)
    // ---- reciprocal leaf (core region): tree select -> RX relay -> leaf -> RY relay ----
    wire [32:0] rx;  wire [33:0] ry, ryt;
    ot_qkd_drly #(.W(33), .N(RX_RLY)) u_rx (.clk(ck), .d({rc_v, rc_x}), .q(rx));
    ot_qkh_recip_leaf u_recip (.clk(ck), .rst_n(rst_n), .v(rx[32]), .x(rx[31:0]), .y(ryt[31:0]), .vo(ryt[32]),
                               .fault(ryt[33]));
    ot_qkd_drly #(.W(34), .N(RY_RLY)) u_ry (.clk(ck), .d(ryt), .q(ry));
    assign rc_y = ry[31:0];  assign rc_vo = ry[32];  assign rc_fault = ry[33];
endmodule
