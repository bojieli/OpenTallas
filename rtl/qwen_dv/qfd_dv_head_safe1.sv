`timescale 1ns/1ps
// QW-CLUSTER3/HEAD 2026-10-19: qfd_dv_lane_h_safe1 -- structurally safe successor of the opt-in ML5 native head
// (rtl/qwen_dv/qfd_dv_head_native_b64.sv @5cd31ebb8, CONTROL_SAFE=1 path, which stays byte-identical).
// Values and every output port's cycle are those of the CONTROL_SAFE=1 head; the changes are structural only:
//   R  reset: rst_n lands in TWO registered stages at the face (qfd_dv_s1_rst_land: async assert, sync release),
//      then a balanced relay tree (3 branch relays -> 11 leaf relays, every leaf at depth 4, kept hierarchy);
//      every leaf drives <= 32 asynchronous-reset sinks (the old single tile reset register rt drove 1,603).
//      FPU payload reset off (DRST 0: only valid bits reset; results are valid-tagged).  Release is +3 edges after
//      rst_n deasserts (boot only; no steady-state cycle).
//   F  fanout: the broad roots get KEPT same-edge copies (qfd_dv_s1_cp1 / cp4 / cp5: unparameterised modules
//      with keep_hierarchy, so opt_merge cannot fold them): the TLS ring_on decode (130 loads) and the class
//      one-hot are registered at the face from the cls pin (same edge as q_cls), 5 + 1 copies; the S1 tag
//      lane (128 / 64 loads) x4, bsrc (65) x3; the dmc mc flag (33) is written twice into a spare SRAM column.
//   H  holding chains: imm1/ma/mb/ad/imm2 + the 62-bit tail no longer ride s1_tag -> s2 -> s3 flop lines after the
//      SRAM capture: they ride a separate same-clock native ring of age ML+2 (q = the S2 value) and land in ONE
//      flop (s3) before the next ring; daddr leaves the dmd ring for its own ring of age LM+1 (q = the lane write
//      address register), so SRAM capture -> face out flop is the only remaining hop.
// Every added FF is a same-edge copy or a reset relay; added steady-state cycles: 0.
// Mutant OT_HS1_RON_MUT (bench must FAIL): ring_on copy 1 (the C operand bits of the tap) captures 0.
module qfd_dv_lane_h_safe1 #(parameter integer CONTROL_SAFE=1) (
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
    qfd_dv_safe1_head u_h (
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

// safe2 = safe1 with every fixed-age ring (all < 2 kb) in flops: qfd_dv_s1_flop_ring (16-bit slices, own pointer,
// N = D - 1 slots, write and read the same slot each edge = age D), no 32x64 macros; TLS 128x64 natives kept.
module qfd_dv_lane_h_safe2 #(parameter integer CONTROL_SAFE=1, MEMORY_ALIGNMENT=0, MEMORY_READ_EXTRA=0) (
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
    // All-memory MIF staging adds one reply edge without changing relative operand alignment.
`ifndef SYNTHESIS
    initial if (MEMORY_READ_EXTRA != 0 && MEMORY_READ_EXTRA != 1) $fatal(1,"memory read extra must be0 or1");
`endif
    // S8 memory contract: CROM answers3 edges after VM and1 after BTAB. Match data and
    // metadata to the slowest reply; physical CROM relay stages remain intact. Opt-in until exact gate.
    wire [31:0] aligned_va, aligned_vb, aligned_vc; wire [255:0] aligned_wr;
    generate if (MEMORY_ALIGNMENT == 3) begin : g_memory_alignment
        reg [95:0] vm_pipe[0:2]; reg [255:0] wr_pipe;
        always @(posedge clk) begin
            vm_pipe[0] <= {va_q,vb_q,vc_q}; vm_pipe[1] <= vm_pipe[0]; vm_pipe[2] <= vm_pipe[1];
            wr_pipe <= wrom_q;
        end
`ifdef OT_S8_CROM_ALIGN_MUTANT
        assign {aligned_va,aligned_vb,aligned_vc} = vm_pipe[1];
`else
        assign {aligned_va,aligned_vb,aligned_vc} = vm_pipe[2];
`endif
        assign aligned_wr = wr_pipe;
    end else begin : g_memory_unmodified
        assign {aligned_va,aligned_vb,aligned_vc,aligned_wr} = {va_q,vb_q,vc_q,wrom_q};
    end endgenerate
`ifndef SYNTHESIS
    initial if (MEMORY_ALIGNMENT != 0 && MEMORY_ALIGNMENT != 3) $fatal(1,"S8 memory alignment must be0 or3");
`endif
    qfd_dv_safe1_head #(.FLOP(1), .ML(5+MEMORY_ALIGNMENT+MEMORY_READ_EXTRA)) u_h (
        .clk(clk), .rst_n(rst_n), .emit0(emit0), .live(live), .i(i), .fin_th(fin_th), .i_last_r(i_last_r),
        .cura0(cura0), .curb0(curb0), .curc0(curc0), .curd0(curd0), .rrow(rrow), .asi(asi), .bsi(bsi), .csi(csi),
        .dsi(dsi), .asrc(asrc), .bsrc(bsrc), .csrc(csrc), .mc(mc), .md(md), .redsq(redsq), .ma(ma), .mb(mb),
        .dst(dst), .red(red), .ad(ad), .imm1(imm1), .imm2(imm2), .cls(cls), .accept(accept), .i_sfu(i_sfu),
        .va_re(va_re), .va_addr(va_addr), .va_q(aligned_va), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(aligned_vb), .vc_re(vc_re),
        .vc_addr(vc_addr), .vc_q(aligned_vc), .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(aligned_wr), .crom_re(crom_re),
        .crom_addr(crom_addr), .crom_q(crom_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .l_ov(l_ov), .l_out(l_out), .l_red(l_red),
        .l_redsq(l_redsq), .l_raddr(l_raddr), .l_last(l_last), .retire(retire), .l_fault(l_fault),
        .sx_exp_v(sx_exp_v), .sx_exp_x(sx_exp_x), .sy_exp_y(sy_exp_y), .sy_exp_vo(sy_exp_vo), .sy_exp_f(sy_exp_f),
        .sx_rcp_v(sx_rcp_v), .sx_rcp_x(sx_rcp_x), .sy_rcp_y(sy_rcp_y), .sy_rcp_f(sy_rcp_f),
        .sx_rsq_v(sx_rsq_v), .sx_rsq_x(sx_rsq_x), .sy_rsq_y(sy_rsq_y), .sy_rsq_f(sy_rsq_f));
endmodule

// ---- reset: face landing (two registered stages) + balanced relay tree, kept hierarchy ----------------------
(* keep_hierarchy *)
module qfd_dv_s1_rst_land (input wire clk, input wire arst_n, output wire q);
    (* async_reg = "true" *) reg [1:0] s;
    always @(posedge clk or negedge arst_n) if (!arst_n) s <= 2'b00; else s <= {s[0], 1'b1};
    assign q = s[1];
endmodule
(* keep_hierarchy *)
module qfd_dv_s1_rst_relay (input wire clk, input wire arst_n, output reg q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 1'b0; else q <= 1'b1;
endmodule
// ---- kept same-edge copies (unparameterised: keep_hierarchy survives synthesis, opt_merge cannot fold them) ----
(* keep_hierarchy *)
module qfd_dv_s1_cp1 (input wire clk, input wire d, output reg q);
    always @(posedge clk) q <= d;
endmodule
(* keep_hierarchy *)
module qfd_dv_s1_cp4 (input wire clk, input wire [3:0] d, output reg [3:0] q);
    always @(posedge clk) q <= d;
endmodule
(* keep_hierarchy *)
module qfd_dv_s1_cp5 (input wire clk, input wire [4:0] d, output reg [4:0] q);
    always @(posedge clk) q <= d;
endmodule

module qfd_dv_safe1_head #(
    parameter integer WR = 16, AW = 24, NW = 18, KV_FP8 = 1, ML = 5, RD = 2, QLA = 4, QLM = 5, FLOP = 0
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
    // ---- reset: face landing (2 stages) -> 3 branch relays -> 11 leaf relays (all leaves at depth 4) ----
    localparam integer NL = 11;
    wire r_land;
    wire [3:0] r_br;      // r_br[3]: the flop rings' own leaf relays (FLOP 1)
    wire [NL-1:0] rl;
    qfd_dv_s1_rst_land u_rland (.clk(clk), .arst_n(rst_n), .q(r_land));
    genvar gb;
    for (gb = 0; gb < 4; gb = gb + 1) begin : g_rbr
        qfd_dv_s1_rst_relay u_r (.clk(clk), .arst_n(r_land), .q(r_br[gb]));
    end
    for (gb = 0; gb < NL; gb = gb + 1) begin : g_rlf
        qfd_dv_s1_rst_relay u_r (.clk(clk), .arst_n(r_br[gb / 4]), .q(rl[gb]));
    end
    wire rt = rl[0];      // leaf 0: the face valid pin / out flops (15 sinks)

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
    // ---- class decode registered at the face, same edge as q_cls (kept copies) ----
    wire ron_d = (cls == 3'd1) || (cls == 3'd2) || (cls == 3'd3) || (cls == 3'd4);
    wire [4:0] q_ron;
    for (gb = 0; gb < 5; gb = gb + 1) begin : g_ron
`ifdef OT_HS1_RON_MUT
        qfd_dv_s1_cp1 u_c (.clk(clk), .d((gb == 1) ? 1'b0 : ron_d), .q(q_ron[gb]));
`else
        qfd_dv_s1_cp1 u_c (.clk(clk), .d(ron_d), .q(q_ron[gb]));
`endif
    end
    wire [4:0] q_coh;     // one-hot {SIGM, RSQRT, RECIP, EXP, other}
    qfd_dv_s1_cp5 u_coh (.clk(clk), .d({cls == 3'd4, cls == 3'd3, cls == 3'd2, cls == 3'd1,
                                         !((cls == 3'd1) || (cls == 3'd2) || (cls == 3'd3) || (cls == 3'd4))}), .q(q_coh));

    wire          n_va_re, n_vb_re, n_vc_re, n_wrom_re, n_crom_re, n_vm_we, n_kv_we;
    wire [AW-1:0] n_va_addr, n_vb_addr, n_vc_addr, n_wrom_addr, n_crom_addr, n_vm_waddr, n_kv_waddr;
    wire [31:0]   n_vm_wdata, n_kv_wdata;
    wire          n_ov, n_redsq, n_last, n_retire, n_fault;
    wire [31:0]   n_out;
    wire [1:0]    n_red;
    wire [AW-1:0] n_raddr;
    qfd_dv_safe1_lane #(.WR(WR), .AW(AW), .NW(NW), .LANE(0), .KV_FP8(KV_FP8), .ML(ML + 2 + 2 * RD), .QLA(QLA), .QLM(QLM),
                        .NL(NL), .FLOP(FLOP)) u_lane (
        .clk(clk), .rl(rl), .rbr(r_br[3]), .ron(q_ron), .coh(q_coh),
        .emit0(q_emit0), .live(q_live), .i(q_i), .fin_th(q_fin_th), .i_last_r(q_ilast),
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

// FPU wrappers: the same units as ot_hdc_qmul / ot_hdc_qadd at L > 3 (bit for bit), payload reset off (DRST 0).
module qfd_dv_s1_qmul #(parameter integer L = 5) (
    input wire clk, rst_n, v, input wire [31:0] a, b, output wire [31:0] y, output wire fault);
    wire [1:0] err; wire vo;
    ot_hdc_fp32_mul_lat #(.LAT(L), .DRST(0)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                              .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule
module qfd_dv_s1_qadd #(parameter integer L = 4) (
    input wire clk, rst_n, v, input wire [31:0] a, b, output wire [31:0] y, output wire fault);
    wire [1:0] err; wire vo;
    ot_hdc_fp32_add_lat #(.LAT(L), .DRST(0)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                              .valid_out(vo));
    assign fault = vo && (err != 2'd0);
endmodule

module qfd_dv_safe1_lane #(
    parameter integer WR = 16, AW = 24, NW = 18, LANE = 0, KV_FP8 = 1, ML = 11, QLA = 4, QLM = 5, NL = 11, FLOP = 0
) (
    input  wire              clk,
    input  wire [NL-1:0]     rl,          // reset leaves (each <= 32 sinks)
    input  wire              rbr,         // reset branch for the flop rings' own leaves (FLOP 1)
    input  wire [4:0]        ron,         // ring_on, registered at the face (kept copies)
    input  wire [4:0]        coh,         // class one-hot, registered at the face
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
    output wire [AW-1:0]     vm_waddr,
    output reg  [31:0]       vm_wdata,
    output reg               kv_we,
    output wire [AW-1:0]     kv_waddr,
    output reg  [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [AW-1:0]     l_raddr,
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
    // reset leaves (rl[0] is the head face leaf)
    wire r_ctl = rl[1], r_grd = rl[2], r_ml = rl[3], r_d38 = rl[4], r_tls = rl[5], r_dmx = rl[6],
         r_fab = rl[7], r_fcd = rl[8], r_fad = rl[9], r_sfx = rl[10];

    wire emit = emit0 && live;
    wire [AW-1:0] cura = cura0 + LANE * asi;
    wire [AW-1:0] curb = curb0 + LANE * bsi;
    wire [AW-1:0] curc = curc0 + LANE * csi;
    wire [AW-1:0] curd = curd0 + LANE * dsi;
    localparam integer LW = $clog2(WR);
    localparam [1:0] MA_BYP = 0, MA_AB = 1, MA_AA = 2, MA_AIMM = 3;
    localparam [1:0] MB_OFF = 0, MB_POS = 1, MB_NEG = 2;
    localparam [2:0] AD_BYP = 0, AD_Q = 1, AD_C = 2, AD_NEGB = 3, AD_IMM = 4;
    localparam [2:0] SFU_NONE = 0, SFU_EXP = 1, SFU_RECIP = 2, SFU_RSQRT = 3, SFU_SIGM = 4;
    localparam integer LA = QLA, LM = QLM;
    localparam integer SFX = 4;
    localparam integer D_EXP = 7 * LM + 8 * LA + 4 + SFX, D_RECIP = 1 + 3 * (2 * LM + LA) + SFX,
                       D_RSQRT = 1 + 3 * (3 * LM + LA) + SFX;
    localparam integer D_SIGM = D_EXP + LA + D_RECIP;
    localparam integer TAP0 = LM + 1 + LA;
    localparam integer TAPMAX = TAP0 + D_SIGM;

    function automatic [31:0] fp8r(input [31:0] v);
        reg [7:0] ex; reg [22:0] mt; reg [24:0] sig; reg [4:0] sh; reg [24:0] n, rem, half;
        reg [3:0] m4; reg up; integer e; reg [31:0] y;
        begin
            ex = v[30:23]; mt = v[22:0]; e = ex - 127;
            if (ex == 0) y = 32'd0;
            else if (e >= -6) begin
                up = v[19] && ((|v[18:0]) || v[20]);
                m4 = {1'b1, v[22:20]} + up;
                if (m4 == 0) begin e = e + 1; m4 = 4'd8; end
                if (e > 8 || (e == 8 && m4 > 4'd14)) y = {v[31], 8'd135, 3'b110, 20'd0};
                else y = {v[31], e[7:0] + 8'd127, m4[2:0], 20'd0};
            end else begin
                sig = {2'b01, mt};
                if (14 - e >= 26) y = 32'd0;
                else begin
                    sh = 14 - e;
                    n = sig >> sh; rem = sig & ((25'd1 << sh) - 1); half = 25'd1 << (sh - 1);
                    if (rem > half || (rem == half && n[0])) n = n + 1;
                    if (n == 0) y = 32'd0;
                    else if (n[3]) y = {v[31], 8'd121, 23'd0};
                    else if (n[2]) y = {v[31], 8'd120, n[1:0], 21'd0};
                    else if (n[1]) y = {v[31], 8'd119, n[0], 22'd0};
                    else y = {v[31], 8'd118, 23'd0};
                end
            end
            fp8r = y;
        end
    endfunction

    localparam integer BOOTW = $clog2(TAPMAX + 2);
    wire [BOOTW-1:0] valid_boot_age, valid_class_age;
    wire valid_class_clear = accept && i_sfu != cls;
    qfd_dv_s1_valid_guards #(.LIMIT(TAPMAX)) u_valid_guards (
        .clk(clk), .rst_n(r_grd), .clear(valid_class_clear), .boot(valid_boot_age), .epoch(valid_class_age));

    // -- address cycle (c') --------------------------------------------------------
    reg          e_v;
    reg          e_asrc, e_bsrc, e_csrc, e_mc, e_md, e_redsq;
    reg [1:0]    e_ma, e_mb, e_dst, e_red;
    reg [2:0]    e_ad;
    reg [31:0]   e_imm1, e_imm2;
    reg [LW-1:0] e_lane;
    reg          e_ifirst, e_first8, e_final, e_last;
    reg [2:0]    e_p;
    reg [AW-1:0] e_daddr, e_raddr;
    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) begin
            e_v <= 1'b0; va_re <= 1'b0; vb_re <= 1'b0; vc_re <= 1'b0; wrom_re <= 1'b0; crom_re <= 1'b0;
        end else begin
            e_v <= emit;
            va_re <= emit && !asrc; wrom_re <= emit && asrc;
            vb_re <= emit && !bsrc; vc_re <= emit && !csrc;
            crom_re <= emit && (bsrc || csrc);
        end
    end
    always @(posedge clk) begin
        va_addr <= cura; wrom_addr <= cura >> LW; e_lane <= cura[LW-1:0];
        vb_addr <= curb; vc_addr <= curc; crom_addr <= bsrc ? curb : curc;
        e_asrc <= asrc; e_bsrc <= bsrc; e_csrc <= csrc; e_mc <= mc; e_md <= md; e_redsq <= redsq;
        e_ma <= ma; e_mb <= mb; e_ad <= ad; e_dst <= dst; e_red <= red;
        e_imm1 <= imm1; e_imm2 <= imm2;
        e_ifirst <= (i == 0); e_first8 <= (i < 8);
        e_final <= ($signed({1'b0, i}) >= $signed(fin_th)); e_last <= i_last_r;
        e_p <= i[2:0]; e_daddr <= curd; e_raddr <= rrow;
    end

    // -- S1 (memories answer) -> S2 (capture) -> S3 (operand select) ------------------
    // S1 fields (age ML): valid + the operand-source selects; the S2/S3 fields ride their own ring (age ML+2).
    localparam integer TT = 1 + 1 + 2 + AW + 2 + 1 + AW + 1+1+1+1 + 3;
    localparam integer HW = 1 + 3 + LW;                         // v, asrc, bsrc, csrc, lane
    localparam integer SW = 32 + 2 + 2 + 3 + 32 + TT;           // imm1, ma, mb, ad, imm2, tail
    wire [TT-1:0] e_tail = {e_mc, e_md, e_dst, e_daddr, e_red, e_redsq, e_raddr, e_ifirst, e_first8, e_final, e_last, e_p};
    wire packed_ml_v, m_asrc, m_bsrc, m_csrc;
    wire [LW-1:0] m_lane;
    qfd_dv_s1_delay #(.W(HW), .D(ML), .FLOP(FLOP)) u_ml_head (.clk(clk), .rbr(rbr), .rst_n(r_ml),
        .d({e_v, e_asrc, e_bsrc, e_csrc, e_lane}), .q({packed_ml_v, m_asrc, m_bsrc, m_csrc, m_lane}));
    wire [31:0] r2_imm1, r2_imm2;
    wire [1:0]  r2_ma, r2_mb;
    wire [2:0]  r2_ad;
    wire [TT-1:0] r2_tail;
    qfd_dv_s1_delay #(.W(SW), .D(ML + 2), .FLOP(FLOP)) u_ml_s2 (.clk(clk), .rbr(rbr), .rst_n(r_ml),
        .d({e_imm1, e_ma, e_mb, e_ad, e_imm2, e_tail}), .q({r2_imm1, r2_ma, r2_mb, r2_ad, r2_imm2, r2_tail}));
    wire e_v_m = packed_ml_v && valid_boot_age >= ML;
    reg s1_v, s2_v, s3_v;
    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) begin s1_v <= 0; s2_v <= 0; s3_v <= 0; end
        else begin s1_v <= e_v_m; s2_v <= s1_v; s3_v <= s2_v; end
    end
    // S1 select captures: kept copies (lane x4: one per 4-bit group of the 16-bit weight lane; bsrc x3)
    wire [4*LW-1:0] t_lane_c;
    wire t_asrc, t_csrc;
    wire [2:0] t_bsrc_c;
    genvar gk, gl;
    for (gk = 0; gk < 4; gk = gk + 1) begin : g_lane_cp
        qfd_dv_s1_cp4 u_c (.clk(clk), .d(m_lane), .q(t_lane_c[LW*gk +: LW]));
    end
    for (gk = 0; gk < 3; gk = gk + 1) begin : g_bsrc_cp
        qfd_dv_s1_cp1 u_c (.clk(clk), .d(m_bsrc), .q(t_bsrc_c[gk]));
    end
    qfd_dv_s1_cp1 u_asrc_c (.clk(clk), .d(m_asrc), .q(t_asrc));
    qfd_dv_s1_cp1 u_csrc_c (.clk(clk), .d(m_csrc), .q(t_csrc));
    reg [31:0] s2_a, s2_blo, s2_bhi, s2_c;
    // weight-lane select as a one-hot AND-OR per 4-bit group g, each group decoded from its own lane copy
    wire [15:0] w_sel;
    for (gk = 0; gk < 4; gk = gk + 1) begin : g_wsel
        wire [4*WR-1:0] terms;
        for (gl = 0; gl < WR; gl = gl + 1) begin : g_t
            assign terms[4*gl +: 4] = {4{t_lane_c[LW*gk +: LW] == gl}} & wrom_q[16*gl + 4*gk +: 4];
        end
        wire [4*(WR+1)-1:0] acc;
        assign acc[3:0] = 4'd0;
        for (gl = 0; gl < WR; gl = gl + 1) begin : g_or
            assign acc[4*(gl+1) +: 4] = acc[4*gl +: 4] | terms[4*gl +: 4];
        end
        assign w_sel[4*gk +: 4] = acc[4*WR +: 4];
    end
    always @(posedge clk) begin
        s2_a <= t_asrc ? {w_sel, 16'h0000} : va_q;
        s2_blo <= t_bsrc_c[0] ? crom_q[31:0] : vb_q;
        s2_bhi <= t_bsrc_c[1] ? crom_q[63:32] : 32'd0;
        s2_c <= (t_csrc && !t_bsrc_c[2]) ? crom_q[31:0] : vc_q;
    end
    reg [31:0] ma_x, ma_y, mb_x, mb_y, s3_a, s3_blo, s3_c, s3_imm2;
    reg [1:0]  s3_ma, s3_mb;
    reg [2:0]  s3_ad;
    reg [TT-1:0] s3_tail;
    always @(posedge clk) begin
        ma_x <= s2_a;
        ma_y <= (r2_ma == MA_AB) ? s2_blo : (r2_ma == MA_AA) ? s2_a : r2_imm1;
        mb_x <= s2_c;
        mb_y <= (r2_mb == MB_NEG) ? {~s2_bhi[31], s2_bhi[30:0]} : s2_bhi;
        s3_a <= s2_a; s3_blo <= s2_blo; s3_c <= s2_c; s3_imm2 <= r2_imm2;
        s3_ma <= r2_ma; s3_mb <= r2_mb; s3_ad <= r2_ad; s3_tail <= r2_tail;
    end

    // -- S3 -> S3+LM: the two multipliers ------------------------------------------
    wire [31:0] p_mul, q_mul;
    wire fa, fb_;
    qfd_dv_s1_qmul #(.L(LM)) u_ma (clk, r_fab, s3_v && s3_ma != MA_BYP, ma_x, ma_y, p_mul, fa);
    qfd_dv_s1_qmul #(.L(LM)) u_mb (clk, r_fab, s3_v && s3_mb != MB_OFF, mb_x, mb_y, q_mul, fb_);
    wire [31:0] a8, blo8, c8, imm2_8;
    wire [1:0]  ma8;
    wire [2:0]  ad8;
    wire packed_v3;
    qfd_dv_s1_delay #(.W(32*4 + 2 + 3 + 1), .D(LM), .FLOP(FLOP)) u_d38 (.clk(clk), .rbr(rbr), .rst_n(r_d38),
        .d({s3_v, s3_a, s3_blo, s3_c, s3_imm2, s3_ma, s3_ad}), .q({packed_v3, a8, blo8, c8, imm2_8, ma8, ad8}));
    reg final_v;
    always @(posedge clk or negedge r_ctl) if (!r_ctl) final_v <= 0; else final_v <= packed_v3 && valid_boot_age >= LM;
    wire [LM+1:0] v3 = {final_v, {LM{1'b0}}, s3_v};

    // -- S3+LM -> operand select -> adder (LA) -> R ----------------------------------
    reg [31:0] ad_x, ad_y;
    reg [2:0]  ad9;
    always @(posedge clk) begin
        ad_x <= (ma8 == MA_BYP) ? a8 : p_mul;
        case (ad8)
            AD_Q:    ad_y <= q_mul;
            AD_C:    ad_y <= c8;
            AD_NEGB: ad_y <= {~blo8[31], blo8[30:0]};
            default: ad_y <= imm2_8;
        endcase
        ad9 <= ad8;
    end
    wire [31:0] r_add, px14;
    wire fad;
    qfd_dv_s1_qadd #(.L(LA)) u_ad (clk, r_fad, v3[LM+1] && ad9 != AD_BYP, ad_x, ad_y, r_add, fad);
    wire packed_v9;
    wire [2:0] ad14;
    qfd_dv_s1_delay #(.W(36), .D(LA), .FLOP(FLOP)) u_d914 (.clk(clk), .rbr(rbr), .rst_n(r_d38), .d({v3[LM+1], ad_x, ad9}),
        .q({packed_v9, px14, ad14}));
    wire [LA:0] v9 = {(packed_v9 && valid_boot_age >= LA), {LA{1'b0}}};
    wire [31:0] r14 = (ad14 == AD_BYP) ? px14 : r_add;
    wire        v14 = v9[LA];

    // -- R: special functions (SFH = 1: hardened tiles over the sx_* / sy_* ports) ------
    wire [31:0] y_exp, y_rcp, y_rsq;
    wire vo_exp, f_exp, f_rcp, f_rsq;
    wire        exp_v = v14 && (cls == SFU_EXP || cls == SFU_SIGM);
    wire        rsq_v = v14 && cls == SFU_RSQRT;
    wire [31:0] e1;
    wire f_e1;
    qfd_dv_s1_qadd #(.L(LA)) u_e1 (clk, r_fad, vo_exp && cls == SFU_SIGM, y_exp, 32'h3F800000, e1, f_e1);
    wire delayed_v;
    qfd_dv_s1_small_valid_ring #(.D(LA)) u_ve1 (.clk(clk), .rst_n(r_grd), .d(vo_exp && cls == SFU_SIGM), .q(delayed_v));
    wire [LA:0] ve1 = {(delayed_v && valid_boot_age >= LA), {LA{1'b0}}};
    wire        rcp_v = (cls == SFU_SIGM) ? ve1[LA] : (v14 && cls == SFU_RECIP);
    wire [31:0] rcp_x = (cls == SFU_SIGM) ? e1 : r14;
    reg        lv_exp, lv_rcp, lv_rsq;
    reg [31:0] lx_exp, lx_rcp, lx_rsq;
    always @(posedge clk or negedge r_sfx)
        if (!r_sfx) begin lv_exp <= 1'b0; lv_rcp <= 1'b0; lv_rsq <= 1'b0; end
        else begin lv_exp <= exp_v; lv_rcp <= rcp_v; lv_rsq <= rsq_v; end
    always @(posedge clk) begin lx_exp <= r14; lx_rcp <= rcp_x; lx_rsq <= r14; end
    assign sx_exp_v = lv_exp; assign sx_exp_x = lx_exp;
    assign sx_rcp_v = lv_rcp; assign sx_rcp_x = lx_rcp;
    assign sx_rsq_v = lv_rsq; assign sx_rsq_x = lx_rsq;
    reg        cv_exp, cf_exp, cf_rcp, cf_rsq;
    reg [31:0] cy_exp, cy_rcp, cy_rsq;
    always @(posedge clk or negedge r_sfx)
        if (!r_sfx) begin cv_exp <= 1'b0; cf_exp <= 1'b0; cf_rcp <= 1'b0; cf_rsq <= 1'b0; end
        else begin cv_exp <= sy_exp_vo; cf_exp <= sy_exp_f; cf_rcp <= sy_rcp_f; cf_rsq <= sy_rsq_f; end
    always @(posedge clk) begin cy_exp <= sy_exp_y; cy_rcp <= sy_rcp_y; cy_rsq <= sy_rsq_y; end
    assign y_exp = cy_exp; assign vo_exp = cv_exp; assign f_exp = cf_exp;
    assign y_rcp = cy_rcp; assign f_rcp = cf_rcp;
    assign y_rsq = cy_rsq; assign f_rsq = cf_rsq;

    // -- B, C and the tail: TAP0 ring (non-SFU tap) + the TLS 128-word native ring (SFU class taps) ----
    localparam integer LT = 32 + 32 + TT;
    wire packed_tap0_v, packed_tls_v;
    wire [LT-1:0] t0;
    qfd_dv_s1_delay #(.W(LT + 1), .D(TAP0), .FLOP(FLOP)) u_tap0_ring (.clk(clk), .rbr(rbr), .rst_n(r_tls),
        .d({(s3_v && !valid_class_clear), s3_blo, s3_c, s3_tail}), .q({packed_tap0_v, t0}));
    reg [7:0] dsel;
    always @(*) begin
        case (cls)
            SFU_EXP:   dsel = D_EXP;
            SFU_RECIP: dsel = D_RECIP;
            SFU_RSQRT: dsel = D_RSQRT;
            default:   dsel = D_SIGM;
        endcase
    end
    reg  [6:0]  wp, rp;
    always @(posedge clk or negedge r_tls)
        if (!r_tls) begin wp <= 7'd0; rp <= 7'd0; end
`ifdef OT_TLS_MUT
        else begin wp <= wp + 7'd1; rp <= wp + 7'd2 - dsel[6:0]; end
`else
        else begin wp <= wp + 7'd1; rp <= wp + 7'd3 - dsel[6:0]; end
`endif
    reg  [LT-1:0] cq;
    wire [127:0] tls_in = {{(127-LT){1'b0}}, packed_tap0_v, t0};
    wire [127:0] tls_q;
    always @(posedge clk) cq <= tls_q[LT-1:0];
    reg cq_valid; always @(posedge clk) cq_valid <= tls_q[LT];
    assign packed_tls_v = cq_valid;
    genvar bank, bit_i;
    for (bank = 0; bank < 2; bank = bank + 1) begin : g_native_bank
        wire [63:0] mask;
        for (bit_i = 0; bit_i < 64; bit_i = bit_i + 1) begin : g_mask
            assign mask[bit_i] = (bank * 64 + bit_i < LT + 1);
        end
        ot_sram_1r1w2c_128x64_m1 u_tlm (.wclk(clk), .rclk(clk),
            .r_ce_in(ron[4]), .r_addr_in(rp),
`ifdef OT_HEAD_B64_BANK_MUT
            .rd_out(tls_q[64*(1-bank) +: 64]),
`else
            .rd_out(tls_q[64*bank +: 64]),
`endif
            .w_ce_in(ron[4]), .w_addr_in(wp), .wd_in(tls_in[64*bank +: 64]), .w_mask_in(mask));
    end
    // the 126-bit tap select, one kept ring_on copy per <= 32-bit group
    wire [LT-1:0] tap;
    assign tap[LT-1 -: 32]  = ron[0] ? cq[LT-1 -: 32]  : t0[LT-1 -: 32];        // B
    assign tap[LT-33 -: 32] = ron[1] ? cq[LT-33 -: 32] : t0[LT-33 -: 32];       // C
    assign tap[TT-1 -: 31]  = ron[2] ? cq[TT-1 -: 31]  : t0[TT-1 -: 31];        // tail high
    assign tap[TT-32:0]     = ron[3] ? cq[TT-32:0]     : t0[TT-32:0];           // tail low
`ifndef SYNTHESIS
    initial if (LT > 127 || D_SIGM > 129 || D_RECIP < 3 || D_RSQRT < 3 || D_EXP < 3 || TT < 33)
        $fatal(1, "qfd_dv_safe1_lane TLS: line %0d b, class depths %0d/%0d/%0d/%0d outside the ring", LT, D_EXP,
               D_RECIP, D_RSQRT, D_SIGM);
`endif
    // the SFU result select by the registered class one-hot {SIGM, RSQRT, RECIP, EXP, other}
    wire [31:0] s_val = ({32{coh[1]}} & y_exp) | ({32{coh[2] | coh[4]}} & y_rcp) | ({32{coh[3]}} & y_rsq) |
                        ({32{coh[0]}} & r14);
    wire safe_tapv = (valid_class_age >= (cls == SFU_EXP ? TAP0 + D_EXP : cls == SFU_RECIP ? TAP0 + D_RECIP :
                                          cls == SFU_RSQRT ? TAP0 + D_RSQRT : cls == SFU_SIGM ? TAP0 + D_SIGM : TAP0)) &&
                     ((cls >= SFU_EXP && cls <= SFU_SIGM) ? packed_tls_v : packed_tap0_v);

    // -- MC select (+1) -> multiplier (+LM) -> MD select (+1) -> multiplier (+LM) -> write --
    reg [31:0] mc_x, mc_y, mc_b;
    reg        mc_v;
    reg [TT-1:0] mc_tail;
    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) mc_v <= 1'b0;
        else mc_v <= safe_tapv;
    end
    always @(posedge clk) begin
        mc_x <= s_val; mc_b <= tap[LT-1 -: 32]; mc_y <= tap[LT-33 -: 32]; mc_tail <= tap[TT-1:0];
    end
    wire [31:0] mc_out, byp5, b5;
    wire fmc;
    qfd_dv_s1_qmul #(.L(LM)) u_mc (clk, r_fcd, mc_v && mc_tail[TT-1], mc_x, mc_y, mc_out, fmc);
    wire [TT-1:0] c_tail;
    wire packed_vmc, c_mc_dup;
    // spare column 127 carries a second copy of the mc flag (the md_x select's high half)
    qfd_dv_s1_delay #(.W(64 + TT + 2), .D(LM), .FLOP(FLOP)) u_dmc (.clk(clk), .rbr(rbr), .rst_n(r_dmx),
        .d({mc_tail[TT-1], mc_v, mc_x, mc_b, mc_tail}), .q({c_mc_dup, packed_vmc, byp5, b5, c_tail}));
    wire [LM:0] vmc = {(packed_vmc && valid_boot_age >= LM), {LM{1'b0}}};
    reg [31:0] md_x, md_y;
    reg        md_v;
    reg [TT-1:0] md_tail;
    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) md_v <= 1'b0;
        else md_v <= vmc[LM];
    end
    always @(posedge clk) begin
        md_x[15:0]  <= c_tail[TT-1] ? mc_out[15:0]  : byp5[15:0];
        md_x[31:16] <= c_mc_dup     ? mc_out[31:16] : byp5[31:16];
        md_y <= b5; md_tail <= c_tail;
    end
    wire [31:0] md_out, dbyp5;
    wire fmd;
    qfd_dv_s1_qmul #(.L(LM)) u_md (clk, r_fcd, md_v && md_tail[TT-2], md_x, md_y, md_out, fmd);
    // dmd ring: everything but the write address (TT - AW tail bits); daddr rides its own ring of age LM + 1,
    // whose capture flop IS the lane's write-address register (vm_waddr / kv_waddr)
    localparam integer TN = TT - AW;
    wire [TN-1:0] md_tail_n = {md_tail[TT-1 -: 4], md_tail[TT-5-AW:0]};      // {mc, md, dst} + {red ... p}
    wire [TN-1:0] o_tail_n;
    wire packed_vmd;
    qfd_dv_s1_delay #(.W(32 + TN + 1), .D(LM), .FLOP(FLOP)) u_dmd (.clk(clk), .rbr(rbr), .rst_n(r_dmx), .d({md_v, md_x, md_tail_n}),
        .q({packed_vmd, dbyp5, o_tail_n}));
    wire [AW-1:0] w_daddr;
    qfd_dv_s1_delay #(.W(AW), .D(LM + 1), .FLOP(FLOP)) u_dadr (.clk(clk), .rbr(rbr), .rst_n(r_dmx), .d(md_tail[TT-5 -: AW]), .q(w_daddr));
    wire [LM:0] vmd = {(packed_vmd && valid_boot_age >= LM), {LM{1'b0}}};
    wire          o_mc, o_md;
    wire [1:0]    o_dst, o_red;
    wire          o_redsq;
    wire [AW-1:0] o_raddr;
    wire          o_ifirst, o_first8, o_final, o_last;
    wire [2:0]    o_p;
    assign {o_mc, o_md, o_dst, o_red, o_redsq, o_raddr, o_ifirst, o_first8, o_final, o_last, o_p} = o_tail_n;
    wire [31:0] out = o_md ? md_out : dbyp5;
    wire        ov = vmd[LM];
    assign retire = ov;

    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) begin vm_we <= 1'b0; kv_we <= 1'b0; end
        else begin
            vm_we <= ov && o_dst == 2'd1;
            kv_we <= ov && o_dst == 2'd2;
        end
    end
    assign vm_waddr = w_daddr;
    assign kv_waddr = w_daddr;
    always @(posedge clk) begin
        vm_wdata <= out;
        kv_wdata <= KV_FP8 ? fp8r(out) : (out + 32'h7FFF + {31'd0, out[16]}) & 32'hFFFF0000;
    end

    assign l_ov = ov;
    assign l_out = out;
    assign l_red = o_red;
    assign l_redsq = o_redsq;
    assign l_raddr = o_raddr;
    assign l_last = o_last;
    reg lf;
    always @(posedge clk or negedge r_ctl) begin
        if (!r_ctl) lf <= 1'b0;
        else lf <= fa | fb_ | fad | f_exp | f_e1 | f_rcp | f_rsq | fmc | fmd;
    end
    assign l_fault = lf;
endmodule

// Fixed-age same-clock native SRAM ring (as qfd_dv_head_sram_delay @5cd31ebb8).
module qfd_dv_s1_sram_delay #(parameter integer W = 32, D = 3) (
    input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    localparam integer NB = (W + 63) / 64;
    wire [NB*64-1:0] di = {{(NB*64-W){1'b0}}, d};
    wire [NB*64-1:0] qo;
    genvar b;
    for (b = 0; b < NB; b = b + 1) begin : g_bank
        (* keep_hierarchy = "yes" *) qfd_dv_s1_sram_delay_bank #(.D(D), .BANK_ID(b), .USED_BITS((W-64*b < 64) ? W-64*b : 64)) u_bank (
            .clk(clk), .rst_n(rst_n), .d(di[b*64 +: 64]), .q(qo[b*64 +: 64]));
    end
    assign q = qo[W-1:0];
`ifndef SYNTHESIS
    initial if (D < 3 || D > 32 || W < 1) $fatal(1, "S1_SRAM_DELAY unsupported shape");
`endif
endmodule
module qfd_dv_s1_sram_delay_bank #(parameter integer D = 3, BANK_ID = 0, USED_BITS = 64) (
    input wire clk, rst_n, input wire [63:0] d, output wire [63:0] q
);
    (* keep *) reg [4:0] wp;
`ifdef OT_HEAD_RING_AGE_MUT
    wire [4:0] rp = wp - 5'(D-3);
`else
    wire [4:0] rp = wp - 5'(D-2);
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wp <= 0; else wp <= wp + 1'b1;
    wire [63:0] rq;
    ot_sram_1r1w_32x64_m1 u_mem (.clk(clk),
        .r_ce_in(1'b1), .r_addr_in(rp), .rd_out(rq),
        .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(d), .w_mask_in(64'hffffffffffffffff >> (64-USED_BITS)));
    reg [USED_BITS-1:0] used_q;
    assign q = {{(64-USED_BITS){1'b0}}, used_q};
    always @(posedge clk) used_q <= rq[USED_BITS-1:0];
endmodule

module qfd_dv_s1_small_valid_ring #(parameter integer D = 4) (input wire clk, rst_n, d, output wire q);
    generate if (D < 3) begin : g_short
        reg [D-1:0] p; always @(posedge clk) p <= (p << 1) | d; assign q = p[D-1];
    end else begin : g_ring
        localparam integer N = D - 1, PW = $clog2(N);
        reg [N-1:0] bank; reg [PW-1:0] wp; reg result;
        always @(posedge clk or negedge rst_n) if (!rst_n) wp <= 0; else wp <= (wp == N-1) ? 0 : wp + 1'b1;
        always @(posedge clk) begin bank[wp] <= d; result <= bank[wp]; end
        assign q = result;
    end endgenerate
endmodule

module qfd_dv_s1_valid_guards #(parameter integer LIMIT = 136, W = $clog2(LIMIT+2)) (
    input wire clk, rst_n, clear, output reg [W-1:0] boot, epoch);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin boot <= 0; epoch <= 0; end
        else begin
            if (boot < LIMIT) boot <= boot + 1'b1;
`ifdef OT_HEAD_VALID_CLEAR_MUT
            if (1'b0) epoch <= 0;
`else
            if (clear) epoch <= 0;
`endif
            else if (epoch < LIMIT) epoch <= epoch + 1'b1;
        end
    end
endmodule

// fixed-age delay: native SRAM ring (FLOP 0) or flop ring (FLOP 1), same age D
module qfd_dv_s1_delay #(parameter integer W = 32, D = 3, FLOP = 0) (
    input wire clk, rbr, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (FLOP != 0) begin : g_f
        qfd_dv_s1_flop_ring #(.W(W), .D(D)) u (.clk(clk), .rbr(rbr), .d(d), .q(q));
    end else begin : g_s
        qfd_dv_s1_sram_delay #(.W(W), .D(D)) u (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
    end endgenerate
endmodule
// MIF1 explicitly sizes the existing133-bit S2 ring at17edges (2128slot bits, +133).
// Other shapes retain the2048-bit engineering bound; price qwen_sram_if_mif_model.
// flop ring: 16-bit slices (each pointer drives N slot compares; each slot select drives <= 32 loads), own leaf
// relays fed by the reset branch rbr (leaves at depth 4 like every other leaf, <= 32 pointer sinks each)
module qfd_dv_s1_flop_ring #(parameter integer W = 32, D = 3) (
    input wire clk, rbr, input wire [W-1:0] d, output wire [W-1:0] q
);
    localparam integer N = D - 1, PB = (N < 2) ? 1 : $clog2(N);
    localparam integer NS = (W + 15) / 16, SPL = 32 / PB, NLF = (NS + SPL - 1) / SPL;
    wire [NLF-1:0] lf;
    genvar k;
    for (k = 0; k < NLF; k = k + 1) begin : g_lf
        qfd_dv_s1_rst_relay u_r (.clk(clk), .arst_n(rbr), .q(lf[k]));
    end
    for (k = 0; k < NS; k = k + 1) begin : g_sl
        localparam integer SW = (W - 16 * k < 16) ? W - 16 * k : 16;
        qfd_dv_s1_ring_slice #(.W(SW), .N(N)) u_s (.clk(clk), .rst_n(lf[k / SPL]), .d(d[16*k +: SW]), .q(q[16*k +: SW]));
    end
`ifndef SYNTHESIS
    initial if (D < 3 || D > 33 || (W * (D - 1) > 2048 && !(W == 133 && D == 17))) $fatal(1, "S1_FLOP_RING unsupported shape W %0d D %0d", W, D);
`endif
endmodule
(* keep_hierarchy *)
module qfd_dv_s1_ring_slice #(parameter integer W = 16, N = 4) (
    input wire clk, rst_n, input wire [W-1:0] d, output reg [W-1:0] q
);
    localparam integer PB = (N < 2) ? 1 : $clog2(N);
    reg [PB-1:0] p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) p <= 0; else p <= (p == N - 1) ? {PB{1'b0}} : p + 1'b1;
    reg [W*N-1:0] slot;
    wire [W*(N+1)-1:0] rd;
    assign rd[W-1:0] = {W{1'b0}};
    genvar j;
    for (j = 0; j < N; j = j + 1) begin : g_slot
        wire sel = (p == j);
        always @(posedge clk) if (sel) slot[W*j +: W] <= d;
        assign rd[W*(j+1) +: W] = rd[W*j +: W] | ({W{sel}} & slot[W*j +: W]);
    end
`ifdef OT_HS1_RING_AGE_MUT
    always @(posedge clk) q <= rd[W*N +: W] ^ {{(W-1){1'b0}}, (p == 0)};
`else
    always @(posedge clk) q <= rd[W*N +: W];
`endif
endmodule
