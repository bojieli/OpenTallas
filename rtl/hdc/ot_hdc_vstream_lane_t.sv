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
    parameter integer QLM  = 5,
    // r6 2026-10-14 (compute-die lead decision 07:27, option 1): OREG = 1 registers every lane-cluster OUTPUT in this
    // parent (one fanout-1 kept flop per output pin, valid bits reset by the parent's own reset register), so the
    // cluster's output launch no longer depends on where the closed head's N / S pins sit.  All 24 outputs: the 14
    // write / result outputs leave 1 edge later; the 5 read requests also leave 1 edge later and the stream unit
    // (ot_hdc_vstream LOREG = 1) brings their answers back over ONE FEWER relay stage, so the head's read-to-data
    // alignment (ML + 2 + 2*RD, fixed in the closed head) is unchanged.  0 = the original wires-only cluster.
    parameter integer OREG = 0,
    // r7 2026-10-14 (native pin audit of the CLOSED OREG cluster qfd_su_lane_t_or-or1-2ae5f6ce3: capture FAIL, 665 input
    // pins S + R 278..332 ps > 190 at the cluster R 715.8 -- the inputs went straight to the closed head's pins, whose
    // own flops sit ~92 ps earlier than the cluster's boundary reference, plus the in-cluster wire): IREG = 1 registers
    // every lane-cluster INPUT in this parent too (one fanout-1 kept flop per input pin; the four valid bits reset by the
    // parent reset register), and the children's rst_n is the parent reset register (rst_n is a pin flop's async input
    // only).  The cluster is then pin-registered on both faces.  Cost: the issue fields arrive 1 edge later (results
    // +1 edge per op); the memory answers also arrive 1 edge later, and the stream unit (ot_hdc_vstream LIREG = 1)
    // sends the five read requests over ONE FEWER relay stage, so the head's read-to-data alignment is unchanged.
    parameter integer IREG = 0,
    // Q-ELEM-SUH 2026-10-16 (variant h, native fallback for qfd_su_lane_h_native_crom5): HPR = the head's pin-register
    // stage (ot_hdc_vstream_lane_h HPR).  Every head input and output is 1 edge later (results +2 edges per op, the SFU
    // classes +1 more per traversal); the head absorbs the read round trip in its own ML, so no other knob moves.
    parameter integer HPR = 0
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
    // wires only at OREG = 0: no flop, no gate at this level.  Every child registers every pin (and its own reset).
    wire              h_va_re, h_vb_re, h_vc_re, h_wrom_re, h_crom_re, h_vm_we, h_kv_we, h_l_ov, h_l_redsq, h_l_last,
                      h_retire, h_l_fault;
    wire [AW-1:0]     h_va_addr, h_vb_addr, h_vc_addr, h_wrom_addr, h_crom_addr, h_vm_waddr, h_kv_waddr, h_l_raddr;
    wire [31:0]       h_vm_wdata, h_kv_wdata, h_l_out;
    wire [1:0]        h_l_red;
    localparam integer OVB = 12;                                   // valid bits (reset)
    localparam integer ODB = 8*AW + 3*32 + 2;                      // data bits (no reset)
    wire [OVB-1:0] hv = {h_va_re, h_vb_re, h_vc_re, h_wrom_re, h_crom_re, h_vm_we, h_kv_we, h_l_ov, h_l_redsq, h_l_last,
                         h_retire, h_l_fault};
    wire [ODB-1:0] hd = {h_va_addr, h_vb_addr, h_vc_addr, h_wrom_addr, h_crom_addr, h_vm_waddr, h_kv_waddr, h_l_raddr,
                         h_vm_wdata, h_kv_wdata, h_l_out, h_l_red};
    wire [OVB-1:0] ov;
    wire [ODB-1:0] od;
    wire rs;                                                       // the parent's reset register (async assert, registered deassert)
    generate if (OREG != 0 || IREG != 0) begin : g_rs
        reg rsr;
        always @(posedge clk or negedge rst_n) if (!rst_n) rsr <= 1'b0; else rsr <= 1'b1;
        assign rs = rsr;
    end else begin : g_rs_none
        assign rs = rst_n;
    end endgenerate
    wire rst_c = (IREG != 0) ? rs : rst_n;                         // the children's reset
    // ---- IREG: input pin flops (valid bits reset by rs, data none) ----
    localparam integer IVB = 4;
    localparam integer IDB = NW + (NW + 1) + 9*AW + 6 + 8 + 3 + 64 + 3 + 3 + 3*32 + WR*16 + 64;
    wire [IVB-1:0] pv = {emit0, live, i_last_r, accept};
    wire [IDB-1:0] pd = {i, fin_th, cura0, curb0, curc0, curd0, rrow, asi, bsi, csi, dsi, asrc, bsrc, csrc, mc, md, redsq,
                         ma, mb, dst, red, ad, imm1, imm2, cls, i_sfu, va_q, vb_q, vc_q, wrom_q, crom_q};
    wire [IVB-1:0] iv;
    wire [IDB-1:0] id;
    generate if (IREG != 0) begin : g_ireg
        (* keep *) reg [IVB-1:0] ivr;
        (* keep *) reg [IDB-1:0] idr;
        always @(posedge clk or negedge rs) if (!rs) ivr <= {IVB{1'b0}}; else ivr <= pv;
        always @(posedge clk) idr <= pd;
        assign iv = ivr;
        assign id = idr;
    end else begin : g_iwire
        assign iv = pv;
        assign id = pd;
    end endgenerate
    wire          c_emit0, c_live, c_ilast, c_accept;
    wire [NW-1:0] c_i; wire [NW:0] c_fin_th;
    wire [AW-1:0] c_cura, c_curb, c_curc, c_curd, c_rrow, c_asi, c_bsi, c_csi, c_dsi;
    wire c_asrc, c_bsrc, c_csrc, c_mc, c_md, c_redsq;
    wire [1:0] c_ma, c_mb, c_dst, c_red; wire [2:0] c_ad, c_cls, c_isfu; wire [31:0] c_imm1, c_imm2;
    wire [31:0] c_va, c_vb, c_vc; wire [WR*16-1:0] c_wrom; wire [63:0] c_crom;
    wire [31:0] c_va_r;
`ifdef OT_IREG_MUT
    assign c_va = va_q;      // bench mutant: the va answer bypasses its pin flop (one edge early: must FAIL)
`else
    assign c_va = c_va_r;
`endif
    assign {c_emit0, c_live, c_ilast, c_accept} = iv;
    assign {c_i, c_fin_th, c_cura, c_curb, c_curc, c_curd, c_rrow, c_asi, c_bsi, c_csi, c_dsi, c_asrc, c_bsrc, c_csrc, c_mc,
            c_md, c_redsq, c_ma, c_mb, c_dst, c_red, c_ad, c_imm1, c_imm2, c_cls, c_isfu, c_va_r, c_vb, c_vc, c_wrom,
            c_crom} = id;
    generate if (OREG != 0) begin : g_oreg
        (* keep *) reg [OVB-1:0] ovr;
        (* keep *) reg [ODB-1:0] odr;
        always @(posedge clk or negedge rs) if (!rs) ovr <= {OVB{1'b0}}; else ovr <= hv;
        always @(posedge clk) odr <= hd;
        assign ov = ovr;
        assign od = odr;
    end else begin : g_wire
        assign ov = hv;
        assign od = hd;
    end endgenerate
    assign {va_re, vb_re, vc_re, wrom_re, crom_re, vm_we, kv_we, l_ov, l_redsq, l_last, retire, l_fault} = ov;
    assign {va_addr, vb_addr, vc_addr, wrom_addr, crom_addr, vm_waddr, kv_waddr, l_raddr, vm_wdata, kv_wdata, l_out,
            l_red} = od;
    wire        e_v, e_vo, e_f, r_v, r_vo, r_f, q_v, q_vo, q_f;
    wire [31:0] e_x, e_y, r_x, r_y, q_x, q_y;
`ifdef OT_SU_LANE_HARD
    // hard children: no parameter overrides (the LEF / LIB cells); their defaults must be this cluster's config
    generate if (WR != 16 || AW != 24 || NW != 18 || KV_FP8 != 1 || ML != 15 || RD != 2 || QLA != 4 || QLM != 5) begin : g_cfg_err
        OT_SU_LANE_HARD_VIEW_IS_WR16_AW24_NW18_KVFP8_ML15_RD2_QLA4_QLM5 u_cfg_err ();   // undefined: elaboration stops
    end endgenerate
    generate if (HPR != 0) begin : g_hpr_err
        OT_SU_LANE_HARD_VIEW_HAS_NO_HPR_USE_qfd_su_lane_h_native_crom5r u_hpr_err ();   // undefined: elaboration stops
    end endgenerate
    ot_hdc_vstream_lane_h u_head (
`else
    ot_hdc_vstream_lane_h #(.WR(WR), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML(ML), .RD(RD), .QLA(QLA), .QLM(QLM), .HPR(HPR)) u_head (
`endif
        .clk(clk), .rst_n(rst_c), .emit0(c_emit0), .live(c_live), .i(c_i), .fin_th(c_fin_th), .i_last_r(c_ilast),
        .cura0(c_cura), .curb0(c_curb), .curc0(c_curc), .curd0(c_curd), .rrow(c_rrow), .asi(c_asi), .bsi(c_bsi),
        .csi(c_csi), .dsi(c_dsi), .asrc(c_asrc), .bsrc(c_bsrc), .csrc(c_csrc), .mc(c_mc), .md(c_md), .redsq(c_redsq),
        .ma(c_ma), .mb(c_mb), .dst(c_dst), .red(c_red), .ad(c_ad), .imm1(c_imm1), .imm2(c_imm2), .cls(c_cls),
        .accept(c_accept), .i_sfu(c_isfu),
        .va_re(h_va_re), .va_addr(h_va_addr), .va_q(c_va), .vb_re(h_vb_re), .vb_addr(h_vb_addr), .vb_q(c_vb), .vc_re(h_vc_re),
        .vc_addr(h_vc_addr), .vc_q(c_vc), .wrom_re(h_wrom_re), .wrom_addr(h_wrom_addr), .wrom_q(c_wrom), .crom_re(h_crom_re),
        .crom_addr(h_crom_addr), .crom_q(c_crom), .vm_we(h_vm_we), .vm_waddr(h_vm_waddr), .vm_wdata(h_vm_wdata),
        .kv_we(h_kv_we), .kv_waddr(h_kv_waddr), .kv_wdata(h_kv_wdata), .l_ov(h_l_ov), .l_out(h_l_out), .l_red(h_l_red),
        .l_redsq(h_l_redsq), .l_raddr(h_l_raddr), .l_last(h_l_last), .retire(h_retire), .l_fault(h_l_fault),
        .sx_exp_v(e_v), .sx_exp_x(e_x), .sy_exp_y(e_y), .sy_exp_vo(e_vo), .sy_exp_f(e_f), .sx_rcp_v(r_v),
        .sx_rcp_x(r_x), .sy_rcp_y(r_y), .sy_rcp_f(r_f), .sx_rsq_v(q_v), .sx_rsq_x(q_x), .sy_rsq_y(q_y),
        .sy_rsq_f(q_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_exp_t u_exp (
`else
    ot_hdc_sfu_exp_t #(.LA(QLA), .LM(QLM)) u_exp (
`endif
        .clk(clk), .rst_n(rst_c), .v(e_v), .x(e_x), .y(e_y), .vo(e_vo), .fault(e_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rcp_t u_rcp (
`else
    ot_hdc_sfu_rcp_t #(.LA(QLA), .LM(QLM)) u_rcp (
`endif
        .clk(clk), .rst_n(rst_c), .v(r_v), .x(r_x), .y(r_y), .vo(r_vo), .fault(r_f));
`ifdef OT_SU_LANE_HARD
    ot_hdc_sfu_rsq_t u_rsq (
`else
    ot_hdc_sfu_rsq_t #(.LA(QLA), .LM(QLM)) u_rsq (
`endif
        .clk(clk), .rst_n(rst_c), .v(q_v), .x(q_x), .y(q_y), .vo(q_vo), .fault(q_f));
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
    parameter integer QLM  = 5,
    // Q-ELEM-SUH 2026-10-16 (variant h, owner/coordinator-approved native fallback, +2 edges ledger): HPR = 1 puts one
    // more register stage behind every pin flop: every parent-facing input (pin flop -> p_* -> lane), every
    // parent-facing output (lane -> m_* -> out flop -> pin) and every SFU result input (sy_* pin -> HPR flop -> the
    // lane's capture flop).  So each pin flop drives / is driven by one flop only and can sit at its pin.  The read
    // round trip grows by 2 (lane ML + 2*HPR); each SFU traversal by 1 (lane SFXX = HPR).  The SFU launch side keeps
    // its single port flop: SFXX = 2 would make the sigmoid depth 130 > 129, the 128-word TLS ring's limit.
    // 0 = the original head, unchanged.
    parameter integer HPR  = 0
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

    // ---- HPR: the stage behind the pin flops (valid bits reset by rt, data none); wires at HPR = 0 ----
    localparam integer HVB = 4;
    localparam integer HDB = NW + (NW + 1) + 9*AW + 6 + 8 + 3 + 64 + 3 + 3 + 3*32 + WR*16 + 64;
    wire [HVB-1:0] hqv = {q_emit0, q_live, q_ilast, q_accept};
    wire [HDB-1:0] hqd = {q_i, q_fin_th, q_cura, q_curb, q_curc, q_curd, q_rrow, q_asi, q_bsi, q_csi, q_dsi, q_asrc,
                          q_bsrc, q_csrc, q_mc, q_md, q_redsq, q_ma, q_mb, q_dst, q_red, q_ad, q_imm1, q_imm2, q_cls,
                          q_isfu, q_va, q_vb, q_vc, q_wrom, q_crom};
    localparam integer SYV = 5;                                    // sy_exp_vo and the three faults (reset)
    localparam integer SYD = 3*32;
    wire [SYV-1:0] syv_i = {sy_exp_vo, sy_exp_f, sy_rcp_f, sy_rsq_f, 1'b0};
    wire [SYD-1:0] syd_i = {sy_exp_y, sy_rcp_y, sy_rsq_y};
    wire [HVB-1:0] hpv;
    wire [HDB-1:0] hpd;
    wire [SYV-1:0] syv;
    wire [SYD-1:0] syd;
    generate if (HPR != 0) begin : g_hpr_in
        (* keep *) reg [HVB-1:0] hpvr;
        (* keep *) reg [HDB-1:0] hpdr;
        (* keep *) reg [SYV-1:0] syvr;
        (* keep *) reg [SYD-1:0] sydr;
        always @(posedge clk or negedge rt) if (!rt) begin hpvr <= {HVB{1'b0}}; syvr <= {SYV{1'b0}}; end
                                            else begin hpvr <= hqv; syvr <= syv_i; end
        always @(posedge clk) begin hpdr <= hqd; sydr <= syd_i; end
        assign hpv = hpvr; assign hpd = hpdr; assign syv = syvr; assign syd = sydr;
    end else begin : g_hpr_in_wire
        assign hpv = hqv; assign hpd = hqd; assign syv = syv_i; assign syd = syd_i;
    end endgenerate
    wire          p_emit0, p_live, p_ilast, p_accept;
    wire [NW-1:0] p_i; wire [NW:0] p_fin_th;
    wire [AW-1:0] p_cura, p_curb, p_curc, p_curd, p_rrow, p_asi, p_bsi, p_csi, p_dsi;
    wire p_asrc, p_bsrc, p_csrc, p_mc, p_md, p_redsq;
    wire [1:0] p_ma, p_mb, p_dst, p_red; wire [2:0] p_ad, p_cls, p_isfu; wire [31:0] p_imm1, p_imm2;
    wire [31:0] p_va, p_vb, p_vc; wire [WR*16-1:0] p_wrom; wire [63:0] p_crom;
    assign {p_emit0, p_live, p_ilast, p_accept} = hpv;
    assign {p_i, p_fin_th, p_cura, p_curb, p_curc, p_curd, p_rrow, p_asi, p_bsi, p_csi, p_dsi, p_asrc, p_bsrc, p_csrc,
            p_mc, p_md, p_redsq, p_ma, p_mb, p_dst, p_red, p_ad, p_imm1, p_imm2, p_cls, p_isfu, p_va, p_vb, p_vc,
            p_wrom, p_crom} = hpd;
    wire        p_sy_exp_vo, p_sy_exp_f, p_sy_rcp_f, p_sy_rsq_f, p_sy_unused;
    wire [31:0] p_sy_exp_y, p_sy_rcp_y, p_sy_rsq_y;
    assign {p_sy_exp_vo, p_sy_exp_f, p_sy_rcp_f, p_sy_rsq_f, p_sy_unused} = syv;
    assign {p_sy_exp_y, p_sy_rcp_y, p_sy_rsq_y} = syd;
`ifdef OT_HPR_MUT
    localparam integer HML = 0;    // bench mutant: the lane's read alignment ignores the HPR stages (must FAIL)
`else
    localparam integer HML = 2 * HPR;
`endif
`ifdef OT_SFXX_MUT
    localparam integer HSF = 0;    // bench mutant: the SFU class depths ignore the HPR result stage (must FAIL)
`else
    localparam integer HSF = HPR;
`endif

    // ---- the lane (LANE 0: the address offsets are formed by the parent, LOFF = 1) ----
    wire          n_va_re, n_vb_re, n_vc_re, n_wrom_re, n_crom_re, n_vm_we, n_kv_we;
    wire [AW-1:0] n_va_addr, n_vb_addr, n_vc_addr, n_wrom_addr, n_crom_addr, n_vm_waddr, n_kv_waddr;
    wire [31:0]   n_vm_wdata, n_kv_wdata;
    wire          n_ov, n_redsq, n_last, n_retire, n_fault;
    wire [31:0]   n_out;
    wire [1:0]    n_red;
    wire [AW-1:0] n_raddr;
    ot_hdc_vstream_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(0), .KV_FP8(KV_FP8), .ML(ML + 2 + 2 * RD + HML), .QLA(QLA),
                          .QLM(QLM), .SFH(1), .TLS(1), .SFXX(HSF)) u_lane (
        .clk(clk), .rst_n(rt), .emit0(p_emit0), .live(p_live), .i(p_i), .fin_th(p_fin_th), .i_last_r(p_ilast),
        .cura0(p_cura), .curb0(p_curb), .curc0(p_curc), .curd0(p_curd), .rrow(p_rrow),
        .asi(p_asi), .bsi(p_bsi), .csi(p_csi), .dsi(p_dsi),
        .asrc(p_asrc), .bsrc(p_bsrc), .csrc(p_csrc), .mc(p_mc), .md(p_md), .redsq(p_redsq),
        .ma(p_ma), .mb(p_mb), .dst(p_dst), .red(p_red), .ad(p_ad), .imm1(p_imm1), .imm2(p_imm2),
        .cls(p_cls), .accept(p_accept), .i_sfu(p_isfu),
        .va_re(n_va_re), .va_addr(n_va_addr), .va_q(p_va),
        .vb_re(n_vb_re), .vb_addr(n_vb_addr), .vb_q(p_vb),
        .vc_re(n_vc_re), .vc_addr(n_vc_addr), .vc_q(p_vc),
        .wrom_re(n_wrom_re), .wrom_addr(n_wrom_addr), .wrom_q(p_wrom),
        .crom_re(n_crom_re), .crom_addr(n_crom_addr), .crom_q(p_crom),
        .vm_we(n_vm_we), .vm_waddr(n_vm_waddr), .vm_wdata(n_vm_wdata),
        .kv_we(n_kv_we), .kv_waddr(n_kv_waddr), .kv_wdata(n_kv_wdata),
        .l_ov(n_ov), .l_out(n_out), .l_red(n_red), .l_redsq(n_redsq),
        .l_raddr(n_raddr), .l_last(n_last), .retire(n_retire), .l_fault(n_fault),
        .sx_exp_v(sx_exp_v), .sx_exp_x(sx_exp_x), .sy_exp_y(p_sy_exp_y), .sy_exp_vo(p_sy_exp_vo), .sy_exp_f(p_sy_exp_f),
        .sx_rcp_v(sx_rcp_v), .sx_rcp_x(sx_rcp_x), .sy_rcp_y(p_sy_rcp_y), .sy_rcp_f(p_sy_rcp_f),
        .sx_rsq_v(sx_rsq_v), .sx_rsq_x(sx_rsq_x), .sy_rsq_y(p_sy_rsq_y), .sy_rsq_f(p_sy_rsq_f));

    // ---- HPR: the stage in front of the out flops (valid bits reset by rt, data none); wires at HPR = 0 ----
    localparam integer MVB = 11;
    localparam integer MDB = 8*AW + 3*32 + 2 + 1;
    wire [MVB-1:0] mvi = {n_va_re, n_vb_re, n_vc_re, n_wrom_re, n_crom_re, n_vm_we, n_kv_we, n_ov, n_last, n_retire,
                          n_fault};
    wire [MDB-1:0] mdi = {n_va_addr, n_vb_addr, n_vc_addr, n_wrom_addr, n_crom_addr, n_vm_waddr, n_kv_waddr, n_raddr,
                          n_vm_wdata, n_kv_wdata, n_out, n_red, n_redsq};
    wire [MVB-1:0] mv;
    wire [MDB-1:0] md_;
    generate if (HPR != 0) begin : g_hpr_out
        (* keep *) reg [MVB-1:0] mvr;
        (* keep *) reg [MDB-1:0] mdr;
        always @(posedge clk or negedge rt) if (!rt) mvr <= {MVB{1'b0}}; else mvr <= mvi;
        always @(posedge clk) mdr <= mdi;
        assign mv = mvr; assign md_ = mdr;
    end else begin : g_hpr_out_wire
        assign mv = mvi; assign md_ = mdi;
    end endgenerate
    wire          m_va_re, m_vb_re, m_vc_re, m_wrom_re, m_crom_re, m_vm_we, m_kv_we, m_ov, m_last, m_retire, m_fault;
    wire [AW-1:0] m_va_addr, m_vb_addr, m_vc_addr, m_wrom_addr, m_crom_addr, m_vm_waddr, m_kv_waddr, m_raddr;
    wire [31:0]   m_vm_wdata, m_kv_wdata, m_out;
    wire [1:0]    m_red;
    wire          m_redsq;
    assign {m_va_re, m_vb_re, m_vc_re, m_wrom_re, m_crom_re, m_vm_we, m_kv_we, m_ov, m_last, m_retire, m_fault} = mv;
    assign {m_va_addr, m_vb_addr, m_vc_addr, m_wrom_addr, m_crom_addr, m_vm_waddr, m_kv_waddr, m_raddr, m_vm_wdata,
            m_kv_wdata, m_out, m_red, m_redsq} = md_;

    // ---- out flops ----
    always @(posedge clk or negedge rt)
        if (!rt) begin
            va_re <= 1'b0; vb_re <= 1'b0; vc_re <= 1'b0; wrom_re <= 1'b0; crom_re <= 1'b0; vm_we <= 1'b0; kv_we <= 1'b0;
            l_ov <= 1'b0; l_last <= 1'b0; retire <= 1'b0; l_fault <= 1'b0;
        end else begin
            va_re <= m_va_re; vb_re <= m_vb_re; vc_re <= m_vc_re; wrom_re <= m_wrom_re; crom_re <= m_crom_re;
            vm_we <= m_vm_we; kv_we <= m_kv_we; l_ov <= m_ov; l_last <= m_last; retire <= m_retire; l_fault <= m_fault;
        end
    always @(posedge clk) begin
        va_addr <= m_va_addr; vb_addr <= m_vb_addr; vc_addr <= m_vc_addr; wrom_addr <= m_wrom_addr;
        crom_addr <= m_crom_addr; vm_waddr <= m_vm_waddr; vm_wdata <= m_vm_wdata; kv_waddr <= m_kv_waddr;
        kv_wdata <= m_kv_wdata; l_out <= m_out; l_red <= m_red; l_redsq <= m_redsq; l_raddr <= m_raddr;
    end
endmodule
`endif  // OT_SU_LANE_HARD
