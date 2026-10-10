`timescale 1ns/1ps
`default_nettype none
// HGI loader die body (hgi-takeover 2026-10-09; die gaps 1 + 4): the half-rate 37-bit loader core
// (ot_hfd_loader_half37: high-address LOAD / STORE engines, ND 1) + the host CP window (ot_hgi_loader_cp: doorbell,
// completion, CFG window, CF-0 read-back, die id, record-ring fetch) in front of its AXI-lite slave + the memory port to
// the four stacks' stream services (ot_hfd_loader_kport: lane 0 = loader core, lane 1 = CP record-ring fetch, read
// only).  Host link (s_*, h_*, h_dma_*, m_*) as the legacy loader wrapper; lq / lr = the per-stack loader_mem lanes.
module ot_hfd_loader_hgi #(
    parameter [35:0] STACK_BYTES = 36'd22500000000
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire s_awvalid, output wire s_awready, input wire [11:0] s_awaddr,
    input  wire s_wvalid, output wire s_wready, input wire [31:0] s_wdata, input wire [3:0] s_wstrb,
    output wire s_bvalid, input wire s_bready, input wire s_arvalid, output wire s_arready, input wire [11:0] s_araddr,
    output wire s_rvalid, input wire s_rready, output wire [31:0] s_rdata,
    output wire h_awvalid, input wire h_awready, output wire [11:0] h_awaddr, output wire h_wvalid, input wire h_wready,
    output wire [31:0] h_wdata, output wire [3:0] h_wstrb, input wire h_bvalid, output wire h_bready, output wire h_arvalid,
    input wire h_arready, output wire [11:0] h_araddr, input wire h_rvalid, output wire h_rready, input wire [31:0] h_rdata,
    input wire h_dma_arvalid, output wire h_dma_arready, input wire [63:0] h_dma_araddr, output wire h_dma_rvalid,
    input wire h_dma_rready, output wire [63:0] h_dma_rdata, output wire [1:0] h_dma_rresp, output wire h_dma_rlast,
    input wire h_dma_awvalid, output wire h_dma_awready, input wire [63:0] h_dma_awaddr, input wire h_dma_wvalid,
    output wire h_dma_wready, input wire [63:0] h_dma_wdata, input wire [7:0] h_dma_wstrb, output wire h_dma_bvalid,
    input wire h_dma_bready, output wire [1:0] h_dma_bresp,
    output wire m_arvalid, input wire m_arready, output wire [63:0] m_araddr, output wire [7:0] m_arlen, output wire [2:0] m_arsize,
    input wire m_rvalid, output wire m_rready, input wire [63:0] m_rdata, input wire [1:0] m_rresp, input wire m_rlast,
    output wire m_awvalid, input wire m_awready, output wire [63:0] m_awaddr, output wire [7:0] m_awlen, output wire [2:0] m_awsize,
    output wire m_wvalid, input wire m_wready, output wire [63:0] m_wdata, output wire [7:0] m_wstrb, output wire m_wlast,
    input wire m_bvalid, output wire m_bready, input wire [1:0] m_bresp,
    output wire [418:0] lcp,
    input  wire [221:0] cpl,
    output wire [4*346-1:0] lq,
    input  wire [4*293-1:0] lr,
    // hgi-takeover (hgi-e2e DIE GAP / F6): the DMA unit (unit 8) beside the loader: record adapter ot_hgi_dma_record +
    // the full-rate mover ot_hgi_dma_mover on kport lane 2 (HBM) and one hfd_hgi_vm packet client
    input  wire [703:0] dma_rec,        // {pos1, n_O, n_A, O, A, header, valid}
    output wire [2:0]   dma_ret,        // {fault, done, ready}
    output wire [337:0] dma_vmq,
    input  wire [273:0] dma_vmr,
    output wire irq,
    output wire fault
);
    wire c_awvalid, c_awready, c_wvalid, c_wready, c_bvalid, c_bready, c_arvalid, c_arready, c_rvalid, c_rready;
    wire [11:0] c_awaddr, c_araddr; wire [31:0] c_wdata, c_rdata; wire [3:0] c_wstrb;
    wire f_v, f_rdy; wire [36:0] f_a; wire lc_fault, ld_fault, kp_fault;
    wire l_req_v, l_req_rdy, l_req_we, l_rsp_v, l_rsp_rdy, l_rsp_we; wire [36:0] l_req_addr; wire [255:0] l_req_wdata, l_rsp_data;
    wire [31:0] l_req_wstrb; wire [15:0] l_req_tag, l_rsp_tag;
    wire [2:0] k_rsp_v, k_rsp_we, k_req_rdy; wire [47:0] k_rsp_tag; wire [767:0] k_rsp_data;
    // ---- DMA unit
    wire d_mv_v, d_mv_rdy, d_mv_done, d_mv_fault, d_fv, d_frdy, d_fdone, d_rdy, d_done, d_fault, dm_fault;
    wire [226:0] d_mv; wire d_kv, d_kwe, d_krr; wire [36:0] d_ka; wire [255:0] d_kd; wire [31:0] d_ks; wire [15:0] d_kt;
    ot_hgi_dma_record #(.LEGACY(0)) u_dma (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(dma_rec[0]), .rec_rdy(d_rdy),
        .rec_hdr(dma_rec[128:1]), .rec_a(dma_rec[384:129]), .rec_o(dma_rec[640:385]), .rec_n_a(dma_rec[661:641]),
        .rec_n_o(dma_rec[682:662]), .rec_pos1(dma_rec[703:683]), .rec_done(d_done), .rec_fault(d_fault), .halted(),
        .lg_mv_v(1'b0), .lg_mv_rdy(), .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(),
        .mv_v(d_mv_v), .mv_rdy(d_mv_rdy), .mv(d_mv), .mv_done(d_mv_done), .mv_fault(d_mv_fault),
        .fence_v(d_fv), .fence_rdy(d_frdy), .fence_done(d_fdone));
    ot_hgi_dma_mover u_mover (.clk(clk), .rst_n(rst_n), .mv_v(d_mv_v), .mv_rdy(d_mv_rdy), .mv(d_mv), .mv_done(d_mv_done),
        .mv_fault(d_mv_fault), .fence_v(d_fv), .fence_rdy(d_frdy), .fence_done(d_fdone),
        .k_req_v(d_kv), .k_req_rdy(k_req_rdy[2]), .k_req_we(d_kwe), .k_req_addr(d_ka), .k_req_wdata(d_kd),
        .k_req_wstrb(d_ks), .k_req_tag(d_kt), .k_rsp_v(k_rsp_v[2]), .k_rsp_rdy(d_krr), .k_rsp_we(k_rsp_we[2]),
        .k_rsp_data(k_rsp_data[767:512]), .k_fault(1'b0), .vmq(dma_vmq), .vmr(dma_vmr));
    assign dma_ret = {d_fault, d_done, d_rdy};
    ot_hgi_loader_cp u_cpw (.clk(clk), .rst_n(rst_n),
        .s_awvalid(s_awvalid), .s_awready(s_awready), .s_awaddr(s_awaddr), .s_wvalid(s_wvalid), .s_wready(s_wready),
        .s_wdata(s_wdata), .s_wstrb(s_wstrb), .s_bvalid(s_bvalid), .s_bready(s_bready), .s_arvalid(s_arvalid),
        .s_arready(s_arready), .s_araddr(s_araddr), .s_rvalid(s_rvalid), .s_rready(s_rready), .s_rdata(s_rdata),
        .c_awvalid(c_awvalid), .c_awready(c_awready), .c_awaddr(c_awaddr), .c_wvalid(c_wvalid), .c_wready(c_wready),
        .c_wdata(c_wdata), .c_wstrb(c_wstrb), .c_bvalid(c_bvalid), .c_bready(c_bready), .c_arvalid(c_arvalid),
        .c_arready(c_arready), .c_araddr(c_araddr), .c_rvalid(c_rvalid), .c_rready(c_rready), .c_rdata(c_rdata),
        .lcp(lcp), .cpl(cpl), .m_req_v(f_v), .m_req_rdy(f_rdy), .m_req_addr(f_a), .m_rsp_v(k_rsp_v[1]),
        .m_rsp_data(k_rsp_data[511:256]), .fault(lc_fault));
    ot_hfd_loader_half37 #(.ENABLE(1), .ND(1), .SHARED(1), .STACK_BYTES({28'd0, STACK_BYTES})) u_ld (
        .clk_host(clk), .rst_host_n(rst_n), .clk_mem(clk), .rst_mem_n(rst_n),
        .s_awvalid(c_awvalid), .s_awready(c_awready), .s_awaddr(c_awaddr), .s_wvalid(c_wvalid), .s_wready(c_wready),
        .s_wdata(c_wdata), .s_wstrb(c_wstrb), .s_bvalid(c_bvalid), .s_bready(c_bready), .s_arvalid(c_arvalid),
        .s_arready(c_arready), .s_araddr(c_araddr), .s_rvalid(c_rvalid), .s_rready(c_rready), .s_rdata(c_rdata),
        .h_awvalid(h_awvalid), .h_awready(h_awready), .h_awaddr(h_awaddr), .h_wvalid(h_wvalid), .h_wready(h_wready),
        .h_wdata(h_wdata), .h_wstrb(h_wstrb), .h_bvalid(h_bvalid), .h_bready(h_bready), .h_arvalid(h_arvalid),
        .h_arready(h_arready), .h_araddr(h_araddr), .h_rvalid(h_rvalid), .h_rready(h_rready), .h_rdata(h_rdata),
        .h_dma_arvalid(h_dma_arvalid), .h_dma_arready(h_dma_arready), .h_dma_araddr(h_dma_araddr),
        .h_dma_rvalid(h_dma_rvalid), .h_dma_rready(h_dma_rready), .h_dma_rdata(h_dma_rdata), .h_dma_rresp(h_dma_rresp),
        .h_dma_rlast(h_dma_rlast), .h_dma_awvalid(h_dma_awvalid), .h_dma_awready(h_dma_awready),
        .h_dma_awaddr(h_dma_awaddr), .h_dma_wvalid(h_dma_wvalid), .h_dma_wready(h_dma_wready), .h_dma_wdata(h_dma_wdata),
        .h_dma_wstrb(h_dma_wstrb), .h_dma_bvalid(h_dma_bvalid), .h_dma_bready(h_dma_bready), .h_dma_bresp(h_dma_bresp),
        .m_arvalid(m_arvalid), .m_arready(m_arready), .m_araddr(m_araddr), .m_arlen(m_arlen), .m_arsize(m_arsize),
        .m_rvalid(m_rvalid), .m_rready(m_rready), .m_rdata(m_rdata), .m_rresp(m_rresp), .m_rlast(m_rlast),
        .m_awvalid(m_awvalid), .m_awready(m_awready), .m_awaddr(m_awaddr), .m_awlen(m_awlen), .m_awsize(m_awsize),
        .m_wvalid(m_wvalid), .m_wready(m_wready), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wlast(m_wlast),
        .m_bvalid(m_bvalid), .m_bready(m_bready), .m_bresp(m_bresp),
        .req_v(l_req_v), .req_rdy(k_req_rdy[0]), .req_we(l_req_we), .req_addr(l_req_addr), .req_wdata(l_req_wdata),
        .req_wstrb(l_req_wstrb), .req_tag(l_req_tag), .rsp_v(k_rsp_v[0]), .rsp_rdy(l_rsp_rdy), .rsp_we(k_rsp_we[0]),
        .rsp_tag(k_rsp_tag[15:0]), .rsp_data(k_rsp_data[255:0]), .irq(irq), .fault(ld_fault));
    ot_hfd_loader_kport #(.ENABLE(1), .ND(3), .STACK_BYTES(STACK_BYTES)) u_kp (.clk(clk), .rst_n(rst_n),
        .req_v({d_kv, f_v, l_req_v}), .req_rdy(k_req_rdy), .req_we({d_kwe, 1'b0, l_req_we}), .req_addr({d_ka, f_a, l_req_addr}),
        .req_wdata({d_kd, 256'd0, l_req_wdata}), .req_wstrb({d_ks, 32'd0, l_req_wstrb}), .req_tag({d_kt, 16'hf000, l_req_tag}),
        .rsp_v(k_rsp_v), .rsp_rdy({d_krr, 1'b1, l_rsp_rdy}), .rsp_we(k_rsp_we), .rsp_tag(k_rsp_tag), .rsp_data(k_rsp_data),
        .lq(lq), .lr(lr), .fault(kp_fault));
    assign f_rdy = k_req_rdy[1];
    assign fault = lc_fault | ld_fault | kp_fault;   // the DMA unit's faults retire through its record (dma_ret)
endmodule
`default_nettype wire
