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
module ot_hdc_vstream_lane_t #(
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
    input  wire              clk,
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
        .clk(clk), .rst_n(rst_n), .emit0(emit0), .live(live), .i(i), .fin_th(fin_th), .i_last_r(i_last_r),
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
        .clk(clk), .rst_n(rst_n), .v(e_v), .x(e_x), .y(e_y), .vo(e_vo), .fault(e_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rcp_t u_rcp (
`else
    ot_hdc_sfu_rcp_t #(.LA(QLA), .LM(QLM)) u_rcp (
`endif
        .clk(clk), .rst_n(rst_n), .v(r_v), .x(r_x), .y(r_y), .vo(r_vo), .fault(r_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rsq_t u_rsq (
`else
    ot_hdc_sfu_rsq_t #(.LA(QLA), .LM(QLM)) u_rsq (
`endif
        .clk(clk), .rst_n(rst_n), .v(q_v), .x(q_x), .y(q_y), .vo(q_vo), .fault(q_f));
endmodule

// ---- the lane head (hard leaf of the lane cluster): the former flat tile body without the SFU pipelines ----
`ifndef OT_SU_LANE_HARD   // lane cluster build: the head is a hard child (LEF / LIB), not RTL
module ot_hdc_vstream_lane_h #(
    // defaults = the HARDENED configuration (Qwen3-8B ROM TP8 SU: a hard child carries no parameter overrides)
    parameter integer WR   = 16,
    parameter integer AW   = 24,
    parameter integer NW   = 18,
    parameter integer KV_FP8 = 1,
    parameter integer ML   = 15,         // the memory latency at the vstream ports (answer at 1 + ML edges)
    parameter integer RD   = 2,          // parent relay stages each way between the vstream ports and this tile
    // el1011-q-sp 2026-10-11: the hardened tile's fp32 latencies (lane QLA / QLM).  Defaults = the hardened
    // configuration (a parent instantiates the hard tile with no overrides): mul 5 (CSA tree | prefix add | round),
    // add 4 (prefix adds split from the alignment).  The tile's results are tagged; only the lane latency grows.
    parameter integer QLA  = 4,
    parameter integer QLM  = 5
) (
    input  wire              clk,
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
    output reg               va_re,
    output reg  [AW-1:0]     va_addr,
    input  wire [31:0]       va_q,
    output reg               vb_re,
    output reg  [AW-1:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output reg               vc_re,
    output reg  [AW-1:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output reg               crom_re,
    output reg  [AW-1:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output reg               vm_we,
    output reg  [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output reg  [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output reg               l_ov,
    output reg  [31:0]       l_out,
    output reg  [1:0]        l_red,
    output reg               l_redsq,
    output reg  [AW-1:0]     l_raddr,
    output reg               l_last,
    output reg               retire,
    output reg               l_fault,
    // the special-function tiles (ot_hdc_sfu_exp_t / _rcp_t / _rsq_t): launch flops out, capture flops in
    output wire              sx_exp_v,
    output wire [31:0]       sx_exp_x,
    input  wire [31:0]       sy_exp_y,
    input  wire              sy_exp_vo,
    input  wire              sy_exp_f,
    output wire              sx_rcp_v,
    output wire [31:0]       sx_rcp_x,
    input  wire [31:0]       sy_rcp_y,
    input  wire              sy_rcp_f,
    output wire              sx_rsq_v,
    output wire [31:0]       sx_rsq_x,
    input  wire [31:0]       sy_rsq_y,
    input  wire              sy_rsq_f
);
    // ---- the tile's reset register (the reset relay of this tile) ----
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;

    // ---- pin flops: valid bits (reset) ----
    reg q_emit0, q_live, q_ilast, q_accept;
    always @(posedge clk or negedge rt)
        if (!rt) begin q_emit0 <= 1'b0; q_live <= 1'b0; q_ilast <= 1'b0; q_accept <= 1'b0; end
        else begin q_emit0 <= emit0; q_live <= live; q_ilast <= i_last_r; q_accept <= accept; end
    // ---- pin flops: data (no reset) ----
    reg [NW-1:0] q_i; reg [NW:0] q_fin_th;
    reg [AW-1:0] q_cura, q_curb, q_curc, q_curd, q_rrow, q_asi, q_bsi, q_csi, q_dsi;
    reg q_asrc, q_bsrc, q_csrc, q_mc, q_md, q_redsq;
    reg [1:0] q_ma, q_mb, q_dst, q_red; reg [2:0] q_ad, q_cls, q_isfu; reg [31:0] q_imm1, q_imm2;
    reg [31:0] q_va, q_vb, q_vc; reg [WR*16-1:0] q_wrom; reg [63:0] q_crom;
    always @(posedge clk) begin
        q_i <= i; q_fin_th <= fin_th;
        q_cura <= cura0; q_curb <= curb0; q_curc <= curc0; q_curd <= curd0; q_rrow <= rrow;
        q_asi <= asi; q_bsi <= bsi; q_csi <= csi; q_dsi <= dsi;
        q_asrc <= asrc; q_bsrc <= bsrc; q_csrc <= csrc; q_mc <= mc; q_md <= md; q_redsq <= redsq;
        q_ma <= ma; q_mb <= mb; q_dst <= dst; q_red <= red; q_ad <= ad; q_cls <= cls; q_isfu <= i_sfu;
        q_imm1 <= imm1; q_imm2 <= imm2;
        q_va <= va_q; q_vb <= vb_q; q_vc <= vc_q; q_wrom <= wrom_q; q_crom <= crom_q;
    end

    // ---- the lane (LANE 0: the address offsets are formed by the parent, LOFF = 1) ----
    wire          n_va_re, n_vb_re, n_vc_re, n_wrom_re, n_crom_re, n_vm_we, n_kv_we;
    wire [AW-1:0] n_va_addr, n_vb_addr, n_vc_addr, n_wrom_addr, n_crom_addr, n_vm_waddr, n_kv_waddr;
    wire [31:0]   n_vm_wdata, n_kv_wdata;
    wire          n_ov, n_redsq, n_last, n_retire, n_fault;
    wire [31:0]   n_out;
    wire [1:0]    n_red;
    wire [AW-1:0] n_raddr;
    ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(0), .KV_FP8(KV_FP8), .ML(ML + 2 + 2 * RD), .QLA(QLA), .QLM(QLM),
                          .SFH(1), .TLS(1)) u_lane (
        .clk(clk), .rst_n(rt), .emit0(q_emit0), .live(q_live), .i(q_i), .fin_th(q_fin_th), .i_last_r(q_ilast),
        .cura0(q_cura), .curb0(q_curb), .curc0(q_curc), .curd0(q_curd), .rrow(q_rrow),
        .asi(q_asi), .bsi(q_bsi), .csi(q_csi), .dsi(q_dsi),
        .asrc(q_asrc), .bsrc(q_bsrc), .csrc(q_csrc), .mc(q_mc), .md(q_md), .redsq(q_redsq),
        .ma(q_ma), .mb(q_mb), .dst(q_dst), .red(q_red), .ad(q_ad), .imm1(q_imm1), .imm2(q_imm2),
        .cls(q_cls), .accept(q_accept), .i_sfu(q_isfu),
        .va_re(n_va_re), .va_addr(n_va_addr), .va_q(q_va),
        .vb_re(n_vb_re), .vb_addr(n_vb_addr), .vb_q(q_vb),
        .vc_re(n_vc_re), .vc_addr(n_vc_addr), .vc_q(q_vc),
        .wrom_re(n_wrom_re), .wrom_addr(n_wrom_addr), .wrom_q(q_wrom),
        .crom_re(n_crom_re), .crom_addr(n_crom_addr), .crom_q(q_crom),
        .vm_we(n_vm_we), .vm_waddr(n_vm_waddr), .vm_wdata(n_vm_wdata),
        .kv_we(n_kv_we), .kv_waddr(n_kv_waddr), .kv_wdata(n_kv_wdata),
        .l_ov(n_ov), .l_out(n_out), .l_red(n_red), .l_redsq(n_redsq),
        .l_raddr(n_raddr), .l_last(n_last), .retire(n_retire), .l_fault(n_fault),
        .sx_exp_v(sx_exp_v), .sx_exp_x(sx_exp_x), .sy_exp_y(sy_exp_y), .sy_exp_vo(sy_exp_vo), .sy_exp_f(sy_exp_f),
        .sx_rcp_v(sx_rcp_v), .sx_rcp_x(sx_rcp_x), .sy_rcp_y(sy_rcp_y), .sy_rcp_f(sy_rcp_f),
        .sx_rsq_v(sx_rsq_v), .sx_rsq_x(sx_rsq_x), .sy_rsq_y(sy_rsq_y), .sy_rsq_f(sy_rsq_f));

    // ---- out flops ----
    always @(posedge clk or negedge rt)
        if (!rt) begin
            va_re <= 1'b0; vb_re <= 1'b0; vc_re <= 1'b0; wrom_re <= 1'b0; crom_re <= 1'b0; vm_we <= 1'b0; kv_we <= 1'b0;
            l_ov <= 1'b0; l_last <= 1'b0; retire <= 1'b0; l_fault <= 1'b0;
        end else begin
            va_re <= n_va_re; vb_re <= n_vb_re; vc_re <= n_vc_re; wrom_re <= n_wrom_re; crom_re <= n_crom_re;
            vm_we <= n_vm_we; kv_we <= n_kv_we; l_ov <= n_ov; l_last <= n_last; retire <= n_retire; l_fault <= n_fault;
        end
    always @(posedge clk) begin
        va_addr <= n_va_addr; vb_addr <= n_vb_addr; vc_addr <= n_vc_addr; wrom_addr <= n_wrom_addr;
        crom_addr <= n_crom_addr; vm_waddr <= n_vm_waddr; vm_wdata <= n_vm_wdata; kv_waddr <= n_kv_waddr;
        kv_wdata <= n_kv_wdata; l_out <= n_out; l_red <= n_red; l_redsq <= n_redsq; l_raddr <= n_raddr;
    end
endmodule
`endif  // OT_SU_LANE_HARD
