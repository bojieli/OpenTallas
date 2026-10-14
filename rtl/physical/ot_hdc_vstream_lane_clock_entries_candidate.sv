// Separate wires-only four-child clock-entry candidate; no physical qualification.
// el1011-q-sp 2026-10-11 (owner textbook audit: hardened sub-tiles): ot_hdc_vstream_lane as a HARDENED TILE.
// The 64 su64 lanes were one flat block (~780k flops, one clock tree over 1.5 x 2 mm, one reset net, lane I/O wired
// combinationally across the tile).  This wrapper is the lane tile: every input registered at the tile pins (pin
// flops), every output registered (out flops), its own reset register (async assert, registered deassert) -- so the
// tile is routed once (identical for all 64 lanes, LOFF=1) with its own local clock tree, and the parent sees only
// flop-to-pin / pin-to-flop seams.  The parent (ot_hdc_vstream LT=1) adds RD relay stages each way.
// Latency: the memory answers reach the inner lane 2 + 2*RD edges later than at the vstream ports, so the inner lane
// runs with ML + 2 + 2*RD (its own read-to-data alignment); every lane output leaves 1 + RD edges later.  The stream's
// only feedback from the lanes is retire (inflight / progress counters), which stays ordered with the lane writes.
// Only the valid bits (emit0 / live / accept / i_last_r in; *_re / *_we / l_ov / l_last / retire / l_fault out) carry a
// reset; data flops have none.
//
// el1013-qwen-stalls 2026-10-13 (ML15 lane: 51,612 sinks on one clock root, refused): the lane tile is now a WIRES-ONLY
// CLUSTER of four hardened leaves, each with its own clock root (<= 15k sinks) and reset register:
//   ot_hdc_vstream_lane_h   the lane head: the tile's pin flops (in and out, as before), the address cycle, the ML
//                           tag line, the multipliers / adder and the write; its B / C / tail tapped line lives in ONE
//                           1R1W SRAM macro (lane TLS = 1: 16k flops -> ot_sram_1r1w_128x256_m1_r2c2, cycle-exact)
//   ot_hdc_sfu_exp_t / _rcp_t / _rsq_t   the special-function pipelines (rtl/hdc/ot_hdc_vstream_sfu_t.sv)
// Head <-> SFU seams are flop -> pin -> wire -> pin -> flop both ways (lane SFH = 1): an SFU traversal is 4 edges
// longer, so the SFU classes retire later (exp / recip / rsqrt + 4, sigmoid + 8 edges); the non-SFU class and every
// value are unchanged (results are tagged).  Ports, parameters and the memory-latency contract are unchanged.
module ot_hdc_vstream_lane_clock_entries_candidate #(
    parameter integer WR   = 64,
    parameter integer AW   = 24,
    parameter integer NW   = 16,
    parameter integer KV_FP8 = 1,
    parameter integer ML   = 0,          // the memory latency at the vstream ports (answer at 1 + ML edges)
    parameter integer RD   = 1,          // parent relay stages each way between the vstream ports and this tile
    // el1011-q-sp 2026-10-11: the hardened tile's fp32 latencies (lane QLA / QLM).  Defaults = the hardened
    // configuration (a parent instantiates the hard tile with no overrides): mul 5 (CSA tree | prefix add | round),
    // add 4 (prefix adds split from the alignment).  The tile's results are tagged; only the lane latency grows.
    parameter integer QLA  = 4,
    parameter integer QLM  = 5
) (
    input wire ck_head,ck_exp,ck_rcp,ck_rsq,
    input  wire              rst_n,
    input  wire              emit0,
    input  wire              live,
    input  wire [NW-1:0]     i,
    input  wire [NW:0]       fin_th,
    input  wire              i_last_r,
    input  wire [AW-1:0]     cura0, curb0, curc0, curd0, rrow,
    input  wire [AW-1:0]     asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    output wire              va_re,
    output wire [AW-1:0]     va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [AW-1:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [AW-1:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output wire              crom_re,
    output wire [AW-1:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [AW-1:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [AW-1:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [AW-1:0]     l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault
);
    // wires only: no flop, no gate at this level.  Every child registers every pin (and its own reset).
    wire        e_v, e_vo, e_f, r_v, r_vo, r_f, q_v, q_vo, q_f;
    wire [31:0] e_x, e_y, r_x, r_y, q_x, q_y;
`ifdef OT_SU_LANE_HARD
    // hard children: no parameter overrides (the LEF / LIB cells); their defaults must be this cluster's config
    generate if (WR != 16 || AW != 24 || NW != 18 || KV_FP8 != 1 || ML != 15 || RD != 2 || QLA != 4 || QLM != 5) begin : g_cfg_err
        OT_SU_LANE_HARD_VIEW_IS_WR16_AW24_NW18_KVFP8_ML15_RD2_QLA4_QLM5 u_cfg_err ();   // undefined: elaboration stops
    end endgenerate
    ot_hdc_vstream_lane_h u_head (
`else
    ot_hdc_vstream_lane_h #(.WR(WR), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML(ML), .RD(RD), .QLA(QLA), .QLM(QLM)) u_head (
`endif
        .clk(ck_head), .rst_n(rst_n), .emit0(emit0), .live(live), .i(i), .fin_th(fin_th), .i_last_r(i_last_r),
        .cura0(cura0), .curb0(curb0), .curc0(curc0), .curd0(curd0), .rrow(rrow), .asi(asi), .bsi(bsi), .csi(csi),
        .dsi(dsi), .asrc(asrc), .bsrc(bsrc), .csrc(csrc), .mc(mc), .md(md), .redsq(redsq), .ma(ma), .mb(mb),
        .dst(dst), .red(red), .ad(ad), .imm1(imm1), .imm2(imm2), .cls(cls), .accept(accept), .i_sfu(i_sfu),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q), .vc_re(vc_re),
        .vc_addr(vc_addr), .vc_q(vc_q), .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q), .crom_re(crom_re),
        .crom_addr(crom_addr), .crom_q(crom_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .l_ov(l_ov), .l_out(l_out), .l_red(l_red),
        .l_redsq(l_redsq), .l_raddr(l_raddr), .l_last(l_last), .retire(retire), .l_fault(l_fault),
        .sx_exp_v(e_v), .sx_exp_x(e_x), .sy_exp_y(e_y), .sy_exp_vo(e_vo), .sy_exp_f(e_f), .sx_rcp_v(r_v),
        .sx_rcp_x(r_x), .sy_rcp_y(r_y), .sy_rcp_f(r_f), .sx_rsq_v(q_v), .sx_rsq_x(q_x), .sy_rsq_y(q_y),
        .sy_rsq_f(q_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_exp_t u_exp (
`else
    ot_hdc_sfu_exp_t #(.LA(QLA), .LM(QLM)) u_exp (
`endif
        .clk(ck_exp), .rst_n(rst_n), .v(e_v), .x(e_x), .y(e_y), .vo(e_vo), .fault(e_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rcp_t u_rcp (
`else
    ot_hdc_sfu_rcp_t #(.LA(QLA), .LM(QLM)) u_rcp (
`endif
        .clk(ck_rcp), .rst_n(rst_n), .v(r_v), .x(r_x), .y(r_y), .vo(r_vo), .fault(r_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rsq_t u_rsq (
`else
    ot_hdc_sfu_rsq_t #(.LA(QLA), .LM(QLM)) u_rsq (
`endif
        .clk(ck_rsq), .rst_n(rst_n), .v(q_v), .x(q_x), .y(q_y), .vo(q_vo), .fault(q_f));
endmodule