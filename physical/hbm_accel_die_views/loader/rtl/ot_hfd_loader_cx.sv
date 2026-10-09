`timescale 1ns/1ps
// Default-off external-core-clock successor. Model tools/hbm_loader_cx_model.py.
// Finite CDC channels preserved from L-DIV; actual PLL producer is an integration obligation.
module ot_hfd_cxchan #(parameter integer W = 1, parameter integer AW = 3) (
    input  wire         sclk, srst_n, s_v, input wire [W-1:0] s_d, output wire s_rdy,
    input  wire         dclk, drst_n, output wire d_v, output wire [W-1:0] d_d, input wire d_rdy
);
    wire full, empty, ovf; wire [AW:0] freed, cnt;
    assign s_rdy = !full;
    assign d_v = !empty;
    ot_link_afifo #(.W(W), .AW(AW)) u_f (.wclk(sclk), .wrst_n(srst_n), .wr(s_v && !full), .wdata(s_d), .wfull(full),
        .wfreed(freed), .ovf(ovf), .rclk(dclk), .rrst_n(drst_n), .rd(d_v && d_rdy), .rempty(empty), .rdata(d_d), .rcount(cnt));
endmodule

module ot_hfd_loader_cx #(parameter integer ENABLE=0, ND=2, SHARED=0, AW=3)(
 input wire clk_core, input wire clk_host, input wire rst_host_n, input wire clk_mem, input wire rst_mem_n,
 input wire s_awvalid, output wire s_awready, input wire [11:0] s_awaddr,
 input wire s_wvalid, output wire s_wready, input wire [31:0] s_wdata, input wire [3:0] s_wstrb,
 output wire s_bvalid, input wire s_bready, input wire s_arvalid, output wire s_arready, input wire [11:0] s_araddr,
 output wire s_rvalid, input wire s_rready, output wire [31:0] s_rdata,
 output wire h_awvalid, input wire h_awready, output wire [11:0] h_awaddr,
 output wire h_wvalid, input wire h_wready, output wire [31:0] h_wdata, output wire [3:0] h_wstrb,
 input wire h_bvalid, output wire h_bready, output wire h_arvalid, input wire h_arready, output wire [11:0] h_araddr,
 input wire h_rvalid, output wire h_rready, input wire [31:0] h_rdata,
 input wire h_dma_arvalid, output wire h_dma_arready, input wire [63:0] h_dma_araddr,
 output wire h_dma_rvalid, input wire h_dma_rready, output wire [63:0] h_dma_rdata, output wire [1:0] h_dma_rresp, output wire h_dma_rlast,
 input wire h_dma_awvalid, output wire h_dma_awready, input wire [63:0] h_dma_awaddr,
 input wire h_dma_wvalid, output wire h_dma_wready, input wire [63:0] h_dma_wdata, input wire [7:0] h_dma_wstrb,
 output wire h_dma_bvalid, input wire h_dma_bready, output wire [1:0] h_dma_bresp,
 output wire m_arvalid, input wire m_arready, output wire [63:0] m_araddr, output wire [7:0] m_arlen, output wire [2:0] m_arsize,
 input wire m_rvalid, output wire m_rready, input wire [63:0] m_rdata, input wire [1:0] m_rresp, input wire m_rlast,
 output wire m_awvalid, input wire m_awready, output wire [63:0] m_awaddr, output wire [7:0] m_awlen, output wire [2:0] m_awsize,
 output wire m_wvalid, input wire m_wready, output wire [63:0] m_wdata, output wire [7:0] m_wstrb, output wire m_wlast,
 input wire m_bvalid, output wire m_bready, input wire [1:0] m_bresp,
 output wire [ND-1:0] req_v, input wire [ND-1:0] req_rdy, output wire [ND-1:0] req_we,
 output wire [ND*32-1:0] req_addr, output wire [ND*256-1:0] req_wdata, output wire [ND*32-1:0] req_wstrb, output wire [ND*16-1:0] req_tag,
 input wire [ND-1:0] rsp_v, output wire [ND-1:0] rsp_rdy, input wire [ND-1:0] rsp_we,
 input wire [ND*16-1:0] rsp_tag, input wire [ND*256-1:0] rsp_data,
 output wire irq, output wire fault);
    // ---- divided core clock (no gating) and the core reset
    wire ckd = clk_core; // actual independent clock pin; no generated/gated clock
    wire rn_d;
    ot_reset_sync u_rsd (.clk(ckd), .async_rst_n(rst_host_n & rst_mem_n), .sync_rst_n(rn_d));
    // ---- core-side nets
    wire c_s_awvalid, c_s_awready, c_s_wvalid, c_s_wready, c_s_bvalid, c_s_bready, c_s_arvalid, c_s_arready, c_s_rvalid, c_s_rready;
    wire [11:0] c_s_awaddr, c_s_araddr; wire [31:0] c_s_wdata, c_s_rdata; wire [3:0] c_s_wstrb;
    wire c_h_awvalid, c_h_awready, c_h_wvalid, c_h_wready, c_h_bvalid, c_h_bready, c_h_arvalid, c_h_arready, c_h_rvalid, c_h_rready;
    wire [11:0] c_h_awaddr, c_h_araddr; wire [31:0] c_h_wdata, c_h_rdata; wire [3:0] c_h_wstrb;
    wire c_d_arvalid, c_d_arready, c_d_rvalid, c_d_rready, c_d_rlast, c_d_awvalid, c_d_awready, c_d_wvalid, c_d_wready, c_d_bvalid, c_d_bready;
    wire [63:0] c_d_araddr, c_d_rdata, c_d_awaddr, c_d_wdata; wire [1:0] c_d_rresp, c_d_bresp; wire [7:0] c_d_wstrb;
    wire c_m_arvalid, c_m_arready, c_m_rvalid, c_m_rready, c_m_rlast, c_m_awvalid, c_m_awready, c_m_wvalid, c_m_wready, c_m_wlast, c_m_bvalid, c_m_bready;
    wire [63:0] c_m_araddr, c_m_rdata, c_m_awaddr, c_m_wdata; wire [7:0] c_m_arlen, c_m_awlen, c_m_wstrb; wire [2:0] c_m_arsize, c_m_awsize;
    wire [1:0] c_m_rresp, c_m_bresp;
    wire [ND-1:0] c_req_v, c_req_rdy, c_req_we, c_rsp_v, c_rsp_rdy, c_rsp_we;
    wire [ND*32-1:0] c_req_addr, c_req_wstrb; wire [ND*256-1:0] c_req_wdata, c_rsp_data; wire [ND*16-1:0] c_req_tag, c_rsp_tag;
    wire c_irq, c_fault;
    ot_hfd_loader_host_m #(.ENABLE(ENABLE), .ND(ND)) u_core (
     .clk_host(ckd), .rst_host_n(rn_d), .clk_mem(ckd), .rst_mem_n(rn_d),
     .s_awvalid(c_s_awvalid), .s_awready(c_s_awready), .s_awaddr(c_s_awaddr), .s_wvalid(c_s_wvalid), .s_wready(c_s_wready),
     .s_wdata(c_s_wdata), .s_wstrb(c_s_wstrb), .s_bvalid(c_s_bvalid), .s_bready(c_s_bready), .s_arvalid(c_s_arvalid),
     .s_arready(c_s_arready), .s_araddr(c_s_araddr), .s_rvalid(c_s_rvalid), .s_rready(c_s_rready), .s_rdata(c_s_rdata),
     .h_awvalid(c_h_awvalid), .h_awready(c_h_awready), .h_awaddr(c_h_awaddr), .h_wvalid(c_h_wvalid), .h_wready(c_h_wready),
     .h_wdata(c_h_wdata), .h_wstrb(c_h_wstrb), .h_bvalid(c_h_bvalid), .h_bready(c_h_bready), .h_arvalid(c_h_arvalid),
     .h_arready(c_h_arready), .h_araddr(c_h_araddr), .h_rvalid(c_h_rvalid), .h_rready(c_h_rready), .h_rdata(c_h_rdata),
     .h_dma_arvalid(c_d_arvalid), .h_dma_arready(c_d_arready), .h_dma_araddr(c_d_araddr), .h_dma_rvalid(c_d_rvalid),
     .h_dma_rready(c_d_rready), .h_dma_rdata(c_d_rdata), .h_dma_rresp(c_d_rresp), .h_dma_rlast(c_d_rlast),
     .h_dma_awvalid(c_d_awvalid), .h_dma_awready(c_d_awready), .h_dma_awaddr(c_d_awaddr), .h_dma_wvalid(c_d_wvalid),
     .h_dma_wready(c_d_wready), .h_dma_wdata(c_d_wdata), .h_dma_wstrb(c_d_wstrb), .h_dma_bvalid(c_d_bvalid),
     .h_dma_bready(c_d_bready), .h_dma_bresp(c_d_bresp),
     .m_arvalid(c_m_arvalid), .m_arready(c_m_arready), .m_araddr(c_m_araddr), .m_arlen(c_m_arlen), .m_arsize(c_m_arsize),
     .m_rvalid(c_m_rvalid), .m_rready(c_m_rready), .m_rdata(c_m_rdata), .m_rresp(c_m_rresp), .m_rlast(c_m_rlast),
     .m_awvalid(c_m_awvalid), .m_awready(c_m_awready), .m_awaddr(c_m_awaddr), .m_awlen(c_m_awlen), .m_awsize(c_m_awsize),
     .m_wvalid(c_m_wvalid), .m_wready(c_m_wready), .m_wdata(c_m_wdata), .m_wstrb(c_m_wstrb), .m_wlast(c_m_wlast),
     .m_bvalid(c_m_bvalid), .m_bready(c_m_bready), .m_bresp(c_m_bresp),
     .req_v(c_req_v), .req_rdy(c_req_rdy), .req_we(c_req_we), .req_addr(c_req_addr), .req_wdata(c_req_wdata),
     .req_wstrb(c_req_wstrb), .req_tag(c_req_tag), .rsp_v(c_rsp_v), .rsp_rdy(c_rsp_rdy), .rsp_we(c_rsp_we),
     .rsp_tag(c_rsp_tag), .rsp_data(c_rsp_data), .irq(c_irq), .fault(c_fault));
    // ---- host face (clk_host) <-> core (ckd)
    wire hr = rst_host_n, mr = rst_mem_n;
    wire [0:0] nb_s, nb_h;
    ot_hfd_cxchan #(12, AW) x_saw (clk_host, hr, s_awvalid, s_awaddr, s_awready, ckd, rn_d, c_s_awvalid, c_s_awaddr, c_s_awready);
    ot_hfd_cxchan #(36, AW) x_sw  (clk_host, hr, s_wvalid, {s_wstrb, s_wdata}, s_wready, ckd, rn_d, c_s_wvalid, {c_s_wstrb, c_s_wdata}, c_s_wready);
    ot_hfd_cxchan #(1, AW)  x_sb  (ckd, rn_d, c_s_bvalid, 1'b0, c_s_bready, clk_host, hr, s_bvalid, nb_s, s_bready);
    ot_hfd_cxchan #(12, AW) x_sar (clk_host, hr, s_arvalid, s_araddr, s_arready, ckd, rn_d, c_s_arvalid, c_s_araddr, c_s_arready);
    ot_hfd_cxchan #(32, AW) x_sr  (ckd, rn_d, c_s_rvalid, c_s_rdata, c_s_rready, clk_host, hr, s_rvalid, s_rdata, s_rready);
    ot_hfd_cxchan #(12, AW) x_haw (ckd, rn_d, c_h_awvalid, c_h_awaddr, c_h_awready, clk_host, hr, h_awvalid, h_awaddr, h_awready);
    ot_hfd_cxchan #(36, AW) x_hw  (ckd, rn_d, c_h_wvalid, {c_h_wstrb, c_h_wdata}, c_h_wready, clk_host, hr, h_wvalid, {h_wstrb, h_wdata}, h_wready);
    ot_hfd_cxchan #(1, AW)  x_hb  (clk_host, hr, h_bvalid, 1'b0, h_bready, ckd, rn_d, c_h_bvalid, nb_h, c_h_bready);
    ot_hfd_cxchan #(12, AW) x_har (ckd, rn_d, c_h_arvalid, c_h_araddr, c_h_arready, clk_host, hr, h_arvalid, h_araddr, h_arready);
    ot_hfd_cxchan #(32, AW) x_hr  (clk_host, hr, h_rvalid, h_rdata, h_rready, ckd, rn_d, c_h_rvalid, c_h_rdata, c_h_rready);
    ot_hfd_cxchan #(64, AW) x_dar (clk_host, hr, h_dma_arvalid, h_dma_araddr, h_dma_arready, ckd, rn_d, c_d_arvalid, c_d_araddr, c_d_arready);
    ot_hfd_cxchan #(67, AW) x_dr  (ckd, rn_d, c_d_rvalid, {c_d_rlast, c_d_rresp, c_d_rdata}, c_d_rready, clk_host, hr, h_dma_rvalid,
                                  {h_dma_rlast, h_dma_rresp, h_dma_rdata}, h_dma_rready);
    ot_hfd_cxchan #(64, AW) x_daw (clk_host, hr, h_dma_awvalid, h_dma_awaddr, h_dma_awready, ckd, rn_d, c_d_awvalid, c_d_awaddr, c_d_awready);
    ot_hfd_cxchan #(72, AW) x_dw  (clk_host, hr, h_dma_wvalid, {h_dma_wstrb, h_dma_wdata}, h_dma_wready, ckd, rn_d, c_d_wvalid,
                                  {c_d_wstrb, c_d_wdata}, c_d_wready);
    ot_hfd_cxchan #(2, AW)  x_db  (ckd, rn_d, c_d_bvalid, c_d_bresp, c_d_bready, clk_host, hr, h_dma_bvalid, h_dma_bresp, h_dma_bready);
    // ---- host DMA memory AXI m_* (clk_host, as in the unchanged host) and the per-die MREQ port req / rsp (clk_mem)
    ot_hfd_cxchan #(75, AW) x_mar (ckd, rn_d, c_m_arvalid, {c_m_arsize, c_m_arlen, c_m_araddr}, c_m_arready, clk_host, hr, m_arvalid,
                                  {m_arsize, m_arlen, m_araddr}, m_arready);
    ot_hfd_cxchan #(67, AW) x_mr  (clk_host, hr, m_rvalid, {m_rlast, m_rresp, m_rdata}, m_rready, ckd, rn_d, c_m_rvalid,
                                  {c_m_rlast, c_m_rresp, c_m_rdata}, c_m_rready);
    ot_hfd_cxchan #(75, AW) x_maw (ckd, rn_d, c_m_awvalid, {c_m_awsize, c_m_awlen, c_m_awaddr}, c_m_awready, clk_host, hr, m_awvalid,
                                  {m_awsize, m_awlen, m_awaddr}, m_awready);
    ot_hfd_cxchan #(73, AW) x_mw  (ckd, rn_d, c_m_wvalid, {c_m_wlast, c_m_wstrb, c_m_wdata}, c_m_wready, clk_host, hr, m_wvalid,
                                  {m_wlast, m_wstrb, m_wdata}, m_wready);
    ot_hfd_cxchan #(2, AW)  x_mb  (clk_host, hr, m_bvalid, m_bresp, m_bready, ckd, rn_d, c_m_bvalid, c_m_bresp, c_m_bready);
    genvar k;
    generate for (k = 0; k < ND; k = k + 1) begin : g_d
        ot_hfd_cxchan #(337, AW) x_req (ckd, rn_d, c_req_v[k],
            {c_req_we[k], c_req_addr[k*32 +: 32], c_req_wdata[k*256 +: 256], c_req_wstrb[k*32 +: 32], c_req_tag[k*16 +: 16]},
            c_req_rdy[k], clk_mem, mr, req_v[k],
            {req_we[k], req_addr[k*32 +: 32], req_wdata[k*256 +: 256], req_wstrb[k*32 +: 32], req_tag[k*16 +: 16]}, req_rdy[k]);
        ot_hfd_cxchan #(273, AW) x_rsp (clk_mem, mr, rsp_v[k], {rsp_we[k], rsp_tag[k*16 +: 16], rsp_data[k*256 +: 256]},
            rsp_rdy[k], ckd, rn_d, c_rsp_v[k], {c_rsp_we[k], c_rsp_tag[k*16 +: 16], c_rsp_data[k*256 +: 256]}, c_rsp_rdy[k]);
    end endgenerate
    // ---- levels
    (* async_reg = "true" *) reg [1:0] irq_s, flt_s;
    always @(posedge clk_host or negedge rst_host_n)
        if (!rst_host_n) begin irq_s <= 0; flt_s <= 0; end
        else begin irq_s <= {irq_s[0], c_irq}; flt_s <= {flt_s[0], c_fault}; end
    assign irq = irq_s[1];
    assign fault = flt_s[1];
endmodule
