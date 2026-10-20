`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-AHUB4 2026-10-19 (LEAD2-KV, tree K.STA.AHUB): qkd_ahub_static_dw_g3 = qkd_ahub_static_dw_g2 with the FACE IO split out
// of the core region, so tools/landed_parent/lp.py can give the W-face and E-face pin registers their OWN region roots
// (spec tools/landed_parent/specs/qkd_ahub_static_dw_g3.json -> qkd_ahub_static_dw_g3_lp).
//
// Why (gate l1 of qkd_ahub_g2l, KV-AHUB3 95bed49c0): one core root ck_c owned the core logic, the reciprocal leaf AND the
// pin flops of BOTH side faces (x 0 and x 734): 11,690 flops over the whole 730 x 536 outline, soft pin-flop spread
// 686.8..1029.7 ps TT vs u_recip 655.6..674.3 (374.1 TT / 331.4 FF, limit 80).  Structural fix (landed-regions standard):
//   * W face (ap0 / ap1 pin flops u_apw, am0 / am1 face drivers u_amw, fr export relay u_rw) = region w, root ck_w;
//   * E face (ap2 / ap3 pin flops u_ape, am2 / am3 face drivers u_ame) = region e, root ck_e;
//   * core region c keeps io (hs pins, hf), the core, the relays and the reciprocal leaf; z0..z3 one Z tree each.
//   Every w / e <-> c bus crosses through an lp.py landing (D 4, E = K 2, +3 edges, fixed latency, no ready / credit).
//
// Function = qkd_ahub_static_dw_g2 at the same parameters when AP_RLY = AP_LAND = AM_RLY = FR_RLY = FR_LAND = 0 (the
// default: edge-exact with g2).  The new latency parameters are the face-landing analogues of Z_LAND:
//   AP_RLY  registered stages after the ap pin flops (flat reference of the landed form: 3)
//   AP_LAND edges the landed form adds between the ap pin flops and the core (landed: 3); the hub's input ages use
//           AP_OFS + AP_RLY + AP_LAND per stack (AP_OFS keeps its die meaning: no die re-binding of AP_OFS)
//   AM_RLY  registered stages between the core am registers and the am pins (flat reference: 3; landed: 0, the landing
//           read flop IS the face register) -> am reaches the ASTK pins AM_RLY (or 3 landed) edges later than g2
//   FR_RLY / FR_LAND  the same for the fr export (u_io emits WF_RLY + FR_RLY + FR_LAND edges early, so fr still lands on
//           pvfin's R slot: FR_OFS unchanged, 0 edges)
// ---------------------------------------------------------------------------------------------------------------------
module qkd_ahub_static_dw_g3 #(
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
    parameter integer AP_RLY = 0,
    parameter integer AP_LAND = 0,
    parameter integer AM_RLY = 0,
    parameter integer FR_RLY = 0,
    parameter integer FR_LAND = 0,
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
    wire rz_valid, rz_publish, hub_fault;  wire [1:0] rz_head;  wire [31:0] rz_data;
    wire [15:0] rz_epoch;  wire [127:0] rz_vector;
    // ap pin flops per FACE (flop-first pins; + 1 edge on the hub input ages, priced in AP_OFS as in qkd_ahub_static_dw_safe),
    // then AP_RLY reference stages (the landed form: the w / e -> c landing, AP_LAND edges)
    wire [85:0] apw, ape;
    ot_qkd_drly #(.W(86), .N(1 + AP_RLY)) u_apw (.clk(ck), .d({ap1, ap0}), .q(apw));
    ot_qkd_drly #(.W(86), .N(1 + AP_RLY)) u_ape (.clk(ck), .d({ap3, ap2}), .q(ape));
    // hub am copy s = {valid 35, g 34, hh 33:32, data 31:0} -> ASTK am order {data, hh, g, valid} (LSB first); core am
    // copies 0 / 1 go to the W face (u_amw), 2 / 3 to the E face (u_ame)
    wire [71:0] amw_c, ame_c, amw, ame;
    ot_qkd_drly #(.W(72), .N(AM_RLY)) u_amw (.clk(ck), .d(amw_c), .q(amw));
    ot_qkd_drly #(.W(72), .N(AM_RLY)) u_ame (.clk(ck), .d(ame_c), .q(ame));
    assign am0 = {amw[31:0],  amw[33:32], amw[34], amw[35]};
    assign am1 = {amw[67:36], amw[69:68], amw[70], amw[71]};
    assign am2 = {ame[31:0],  ame[33:32], ame[34], ame[35]};
    assign am3 = {ame[67:36], ame[69:68], ame[70], ame[71]};
    // W-face export relay (KV-AHUB7 WF_RLY; u_io emits WF_RLY edges earlier, fr lands on pvfin's R slot unchanged)
    wire fr_valid_i;  wire [15:0] fr_epoch_i;  wire [127:0] fr_rz_i;
    ot_qkd_drly #(.W(145), .N((HMUT == 6) ? 0 : WF_RLY + FR_RLY)) u_rw (.clk(ck), .d({fr_rz_i, fr_epoch_i, fr_valid_i}),
        .q({fr_rz, fr_epoch, fr_valid}));
    qkd_ahub_static_io_safe #(.AP_OFS({16'(AP_OFS[63:48] + AP_RLY + AP_LAND), 16'(AP_OFS[47:32] + AP_RLY + AP_LAND),
                                       16'(AP_OFS[31:16] + AP_RLY + AP_LAND), 16'(AP_OFS[15:0] + AP_RLY + AP_LAND)}),
                              .FR_OFS(FR_OFS), .WF_RLY(WF_RLY + FR_RLY + FR_LAND), .MUT(HMUT)) u_io (
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
        .si_valid({ape[43], ape[0], apw[43], apw[0]}), .si_type({ape[45:44], ape[2:1], apw[45:44], apw[2:1]}),
        .si_g({ape[46], ape[3], apw[46], apw[3]}), .si_hh({ape[48:47], ape[5:4], apw[48:47], apw[5:4]}),
        .si_k({ape[52:49], ape[9:6], apw[52:49], apw[9:6]}), .si_any({ape[53], ape[10], apw[53], apw[10]}),
        .si_epoch(si_epoch), .si_layer(si_layer), .si_data({ape[85:54], ape[42:11], apw[85:54], apw[42:11]}),
        .am({ame_c, amw_c}), .zh_start(zh_start), .zh_we(zh_we), .zh_sid(zh_sid), .zh_iv(zh_iv), .zh_g(zh_g), .zh_p(zh_p),
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
