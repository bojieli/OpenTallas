`timescale 1ns/1ps
// The Qwen SU lane as a hardened macro: ot_hdc_vstream_lane_f12 at the vehicle shape (LA 5, LM 6, WR 16, AW 24,
// NW 18, LANE 0, KV_FP8 1), parameter-free so its routed abstract (LEF + corner ETMs) can stand in for all 64
// lanes of ot_hdc_vstream_rt_f12_h (the emitted lanes are parameter-identical; the parent adds l x stride).
module ot_hdc_vstream_lane_f12_m (
    input  wire              clk,
    input  wire              rst_n,
    // controller state (lane 0's view) and this lane's element
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
    // memories
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
    input  wire [256-1:0]  wrom_q,
    output wire              crom_re,
    output wire [23:0]     crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [23:0]     vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [23:0]     kv_waddr,
    output wire [31:0]       kv_wdata,
    // to the vector reducer
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [23:0]     l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault

);
    ot_hdc_vstream_lane_f12 #(.LA(5), .LM(6), .WR(16), .AW(24), .NW(18), .LANE(0), .KV_FP8(1)) u (.clk(clk), .rst_n(rst_n), .emit0(emit0), .live(live), .i(i), .fin_th(fin_th), .i_last_r(i_last_r), .cura0(cura0), .curb0(curb0), .curc0(curc0), .curd0(curd0), .rrow(rrow), .asi(asi), .bsi(bsi), .csi(csi), .dsi(dsi), .asrc(asrc), .bsrc(bsrc), .csrc(csrc), .mc(mc), .md(md), .redsq(redsq), .ma(ma), .mb(mb), .dst(dst), .red(red), .ad(ad), .imm1(imm1), .imm2(imm2), .cls(cls), .accept(accept), .i_sfu(i_sfu), .va_re(va_re), .va_addr(va_addr), .va_q(va_q), .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q), .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q), .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q), .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .l_ov(l_ov), .l_out(l_out), .l_red(l_red), .l_redsq(l_redsq), .l_raddr(l_raddr), .l_last(l_last), .retire(retire), .l_fault(l_fault));
endmodule
