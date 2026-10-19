// QW-CLUSTER3/HEAD 10-19: copy of qfd_dv_su_lane_native_b64_fixture.sv binding the structurally safe head qfd_dv_lane_h_safe1 (rtl/qwen_dv/qfd_dv_head_safe1.sv).
module qfd_dv_su_lane_landed (
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
    qfd_dv_lane_h_safe1 #(.CONTROL_SAFE(
`ifdef OT_HEAD_CONTROL_SAFE
    1
`else
    0
`endif
    )) u_head (
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
