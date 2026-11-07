module qfd_dv_lane_h_ma7_probe #(parameter integer CONTROL_SAFE=1, MEMORY_ALIGNMENT=0, MEMORY_READ_EXTRA=0, KV_WR_PIPE=0) (
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
    // Test fixture: MA7 guard only removed; generate logic unmodified.
`endif
    ml12_qfd_dv_safe1_head #(.FLOP(1), .ML(5+MEMORY_ALIGNMENT+MEMORY_READ_EXTRA), .KV_WR_PIPE(KV_WR_PIPE)) u_h (
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
