`timescale 1ns/1ps
// =====================================================================================================================
// S-QSLICE 10-18: the Q-DV slice SU lane tile, hardened once and placed 8 times per slice (x 12 slices).
//
// qfd_dv_su_lane is ot_hdc_vstream_lane_t (rtl/hdc, the CLOSED qfd_su_lane_t_io structure: four hard leaves on one
// clock, pin-registered on both faces, IREG 1 / OREG 1, own reset register) at the SLICE configuration WR 16 / AW 24 /
// NW 18 / KV_FP8 1 / ML 1 / RD 2 / QLA 4 / QLM 5, with no parameters, so a parent binds it (and its children) as
// LEF / LIB cells.  The body below is lane_t's, copied with its parameters fixed and the head replaced:
//   qfd_dv_lane_h        the lane head ot_hdc_vstream_lane_h at ML 1 / RD 2 (the closed qfd_su_lane_h view is ML 15:
//                        its tag line / alignment are 14 edges deeper, so it is NOT this lane).  Pin flops in and out,
//                        own reset register, TLS 1 tapped line in one ot_sram_1r1w_128x256_m1_r2c2.
//   ot_hdc_sfu_exp_t / _rcp_t / _rsq_t   the CLOSED SFU leaves (defaults LA 4 / LM 5 = this configuration).
// The parent qfd_dv_su8_entries instantiates it with LT = 1, LOFF = 1, LTD = 1 (slice parameter SU_LT): RD = 2
// relay stages each way, the memory answers and the five read requests over RD - 1 (the ot_hdc_vstream LOREG / LIREG
// arrangement), so the head's read-to-data alignment ML + 2 + 2 RD (inner ML 7) holds.
// Latency vs the flat lanes (LT 0): the read round trip grows by 2 + 2 RD = 6 edges, issue fields reach the head
// 1 + RD + 1 later and results leave 1 + 1 + RD later; SFU classes + 4 (exp / recip / rsqrt) / + 8 (sigmoid) edges.
// Values and order unchanged (results are tagged); the compiler prices the edges (cycles_dv.py).
// =====================================================================================================================
`ifndef OT_DV_SU_LANE_HARD   // lane cluster build: the head is a hard child (LEF / LIB), not RTL
module qfd_dv_lane_h (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              emit0,
    input  wire              live,
    input  wire [17:0]       i,
    input  wire [18:0]       fin_th,
    input  wire              i_last_r,
    input  wire [23:0]       cura0, curb0, curc0, curd0, rrow,
    input  wire [23:0]       asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    output wire              va_re,
    output wire [23:0]       va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [23:0]       vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [23:0]       vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [23:0]       wrom_addr,
    input  wire [255:0]      wrom_q,
    output wire              crom_re,
    output wire [23:0]       crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [23:0]       vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [23:0]       kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [23:0]       l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault,
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
    ot_hdc_vstream_lane_h #(.WR(16), .AW(24), .NW(18), .KV_FP8(1), .ML(1), .RD(2), .QLA(4), .QLM(5)) u_h (
        .clk(clk), .rst_n(rst_n), .emit0(emit0), .live(live), .i(i), .fin_th(fin_th), .i_last_r(i_last_r),
        .cura0(cura0), .curb0(curb0), .curc0(curc0), .curd0(curd0), .rrow(rrow), .asi(asi), .bsi(bsi), .csi(csi),
        .dsi(dsi), .asrc(asrc), .bsrc(bsrc), .csrc(csrc), .mc(mc), .md(md), .redsq(redsq), .ma(ma), .mb(mb),
        .dst(dst), .red(red), .ad(ad), .imm1(imm1), .imm2(imm2), .cls(cls), .accept(accept), .i_sfu(i_sfu),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q), .vc_re(vc_re),
        .vc_addr(vc_addr), .vc_q(vc_q), .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q), .crom_re(crom_re),
        .crom_addr(crom_addr), .crom_q(crom_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .l_ov(l_ov), .l_out(l_out), .l_red(l_red),
        .l_redsq(l_redsq), .l_raddr(l_raddr), .l_last(l_last), .retire(retire), .l_fault(l_fault),
        .sx_exp_v(sx_exp_v), .sx_exp_x(sx_exp_x), .sy_exp_y(sy_exp_y), .sy_exp_vo(sy_exp_vo), .sy_exp_f(sy_exp_f),
        .sx_rcp_v(sx_rcp_v), .sx_rcp_x(sx_rcp_x), .sy_rcp_y(sy_rcp_y), .sy_rcp_f(sy_rcp_f),
        .sx_rsq_v(sx_rsq_v), .sx_rsq_x(sx_rsq_x), .sy_rsq_y(sy_rsq_y), .sy_rsq_f(sy_rsq_f));
endmodule
`endif

module qfd_dv_su_lane (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              emit0,
    input  wire              live,
    input  wire [17:0]     i,
    input  wire [18:0]       fin_th,
    input  wire              i_last_r,
    input  wire [23:0]     cura0, curb0, curc0, curd0, rrow,
    input  wire [23:0]     asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    output wire              va_re,
    output wire [23:0]     va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [23:0]     vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [23:0]     vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [23:0]     wrom_addr,
    input  wire [255:0]  wrom_q,
    output wire              crom_re,
    output wire [23:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [23:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [23:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [23:0]     l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault
);
    // the slice lane configuration (fixed: a hard child carries no parameter overrides)
    localparam integer WR = 16, AW = 24, NW = 18, KV_FP8 = 1, ML = 1, RD = 2, QLA = 4, QLM = 5, OREG = 1, IREG = 1;

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
    qfd_dv_lane_h u_head (
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
    ot_hdc_sfu_exp_t u_exp (
        .clk(clk), .rst_n(rst_c), .v(e_v), .x(e_x), .y(e_y), .vo(e_vo), .fault(e_f));
    ot_hdc_sfu_rcp_t u_rcp (
        .clk(clk), .rst_n(rst_c), .v(r_v), .x(r_x), .y(r_y), .vo(r_vo), .fault(r_f));
    ot_hdc_sfu_rsq_t u_rsq (
        .clk(clk), .rst_n(rst_c), .v(q_v), .x(q_x), .y(q_y), .vo(q_vo), .fault(q_f));
endmodule
