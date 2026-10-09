// hfd_loader: thin registered die wrapper (tools/hbm_die_wrap.py, CLAUDE HBM-ABSTRACTS spine).
// L-DIV (stream ingest 2026-10-08, reviewer-approved): identical die wrapper with the core adapter ot_hfd_loader_div (unchanged
// ot_hfd_loader_host_m on ck / 2 from a divider flop, async-FIFO channel crossings, no clock gating, no multicycle);
// SDC loader/sdc/hfd_loader_div.sdc (generated clock ckd, asynchronous to core_clk).
// Die ports exactly as the r16g generator master (tools/hbm_die_views.py ports); default-off: nothing
// instantiates it except the die view route.  ot_hfd_loader_host_m (ENABLE 1, ND 2): ot_hbm_accel_loader_host with every CRC-32 fold pipelined (make_loader_m.py; the unchanged host: tapeout_hbm_loader_20261004 clock_r2_final not_met, host SS -3,672 ps at 1.0 ns; ld3 -4,229 ps at the store CRC); exact vs the unchanged host (tb_loader_m_equiv.sv). Host AXI-lite slave s_*, host master h_* and DMA h_dma_* on the host link (rx 243 of 256 b used, rest of the DMA inputs on the cfg chain; tx 176 of 256 b); request slot 0 -> cmdproc program-store word t_cmdproc[72:0]; clk_host and clk_mem both on the die clock; memory AXI m_* and rsp_* have no die net (cfg chain / folded). HALF RATE (views agent 2026-10-06, 30c5fa080 SS -863): ot_hfd_loader_half SHARED 1 = the core on ck/2 with handshake gating.
module hfd_loader_cx_local_reset (
    input wire [0:0] cx,
    input wire [0:0] ck,
    inout wire [513:0] h,
    input wire [0:0] rst,
    output wire [340:0] t_cmdproc
);
    wire clk = ck[0];
    reg [1:0] rst_s; always @(posedge clk) rst_s <= {rst_s[0], rst[0]};
    wire rst_n = ~rst_s[1];
    reg [513:0] i0_h; always @(posedge clk) i0_h <= h;
    reg [513:0] i_h; always @(posedge clk) i_h <= i0_h;
    wire [0:0] w_ld_clk_host;
    wire [0:0] w_ld_rst_host_n;
    wire [0:0] w_ld_clk_mem;
    wire [0:0] w_ld_rst_mem_n;
    wire [0:0] w_ld_s_awvalid;
    wire [0:0] w_ld_s_awready;
    wire [11:0] w_ld_s_awaddr;
    wire [0:0] w_ld_s_wvalid;
    wire [0:0] w_ld_s_wready;
    wire [31:0] w_ld_s_wdata;
    wire [3:0] w_ld_s_wstrb;
    wire [0:0] w_ld_s_bvalid;
    wire [0:0] w_ld_s_bready;
    wire [0:0] w_ld_s_arvalid;
    wire [0:0] w_ld_s_arready;
    wire [11:0] w_ld_s_araddr;
    wire [0:0] w_ld_s_rvalid;
    wire [0:0] w_ld_s_rready;
    wire [31:0] w_ld_s_rdata;
    wire [0:0] w_ld_h_awvalid;
    wire [0:0] w_ld_h_awready;
    wire [11:0] w_ld_h_awaddr;
    wire [0:0] w_ld_h_wvalid;
    wire [0:0] w_ld_h_wready;
    wire [31:0] w_ld_h_wdata;
    wire [3:0] w_ld_h_wstrb;
    wire [0:0] w_ld_h_bvalid;
    wire [0:0] w_ld_h_bready;
    wire [0:0] w_ld_h_arvalid;
    wire [0:0] w_ld_h_arready;
    wire [11:0] w_ld_h_araddr;
    wire [0:0] w_ld_h_rvalid;
    wire [0:0] w_ld_h_rready;
    wire [31:0] w_ld_h_rdata;
    wire [0:0] w_ld_h_dma_arvalid;
    wire [0:0] w_ld_h_dma_arready;
    wire [63:0] w_ld_h_dma_araddr;
    wire [0:0] w_ld_h_dma_rvalid;
    wire [0:0] w_ld_h_dma_rready;
    wire [63:0] w_ld_h_dma_rdata;
    wire [1:0] w_ld_h_dma_rresp;
    wire [0:0] w_ld_h_dma_rlast;
    wire [0:0] w_ld_h_dma_awvalid;
    wire [0:0] w_ld_h_dma_awready;
    wire [63:0] w_ld_h_dma_awaddr;
    wire [0:0] w_ld_h_dma_wvalid;
    wire [0:0] w_ld_h_dma_wready;
    wire [63:0] w_ld_h_dma_wdata;
    wire [7:0] w_ld_h_dma_wstrb;
    wire [0:0] w_ld_h_dma_bvalid;
    wire [0:0] w_ld_h_dma_bready;
    wire [1:0] w_ld_h_dma_bresp;
    wire [0:0] w_ld_m_arvalid;
    wire [0:0] w_ld_m_arready;
    wire [63:0] w_ld_m_araddr;
    wire [7:0] w_ld_m_arlen;
    wire [2:0] w_ld_m_arsize;
    wire [0:0] w_ld_m_rvalid;
    wire [0:0] w_ld_m_rready;
    wire [63:0] w_ld_m_rdata;
    wire [1:0] w_ld_m_rresp;
    wire [0:0] w_ld_m_rlast;
    wire [0:0] w_ld_m_awvalid;
    wire [0:0] w_ld_m_awready;
    wire [63:0] w_ld_m_awaddr;
    wire [7:0] w_ld_m_awlen;
    wire [2:0] w_ld_m_awsize;
    wire [0:0] w_ld_m_wvalid;
    wire [0:0] w_ld_m_wready;
    wire [63:0] w_ld_m_wdata;
    wire [7:0] w_ld_m_wstrb;
    wire [0:0] w_ld_m_wlast;
    wire [0:0] w_ld_m_bvalid;
    wire [0:0] w_ld_m_bready;
    wire [1:0] w_ld_m_bresp;
    wire [1:0] w_ld_req_v;
    wire [1:0] w_ld_req_rdy;
    wire [1:0] w_ld_req_we;
    wire [63:0] w_ld_req_addr;
    wire [511:0] w_ld_req_wdata;
    wire [63:0] w_ld_req_wstrb;
    wire [31:0] w_ld_req_tag;
    wire [1:0] w_ld_rsp_v;
    wire [1:0] w_ld_rsp_rdy;
    wire [1:0] w_ld_rsp_we;
    wire [31:0] w_ld_rsp_tag;
    wire [511:0] w_ld_rsp_data;
    wire [0:0] w_ld_irq;
    wire [0:0] w_ld_fault;
    // configuration chain: 688 RTL input bits the die interface does not carry, shifted from die input h[499]
    reg [687:0] cfg; always @(posedge clk) cfg <= {cfg[686:0], i_h[499]};
    assign w_ld_clk_host = {1{clk}};
    assign w_ld_rst_host_n = {1{rst_n}};
    assign w_ld_clk_mem = {1{clk}};
    assign w_ld_rst_mem_n = {1{rst_n}};
    assign w_ld_s_awvalid = {i_h[256:256]};
    assign w_ld_s_awaddr = {i_h[268:257]};
    assign w_ld_s_wvalid = {i_h[269:269]};
    assign w_ld_s_wdata = {i_h[301:270]};
    assign w_ld_s_wstrb = {i_h[305:302]};
    assign w_ld_s_bready = {i_h[306:306]};
    assign w_ld_s_arvalid = {i_h[307:307]};
    assign w_ld_s_araddr = {i_h[319:308]};
    assign w_ld_s_rready = {i_h[320:320]};
    assign w_ld_h_awready = {i_h[321:321]};
    assign w_ld_h_wready = {i_h[322:322]};
    assign w_ld_h_bvalid = {i_h[323:323]};
    assign w_ld_h_arready = {i_h[324:324]};
    assign w_ld_h_rvalid = {i_h[325:325]};
    assign w_ld_h_rdata = {i_h[357:326]};
    assign w_ld_h_dma_arvalid = {i_h[358:358]};
    assign w_ld_h_dma_araddr = {i_h[422:359]};
    assign w_ld_h_dma_rready = {i_h[423:423]};
    assign w_ld_h_dma_awvalid = {i_h[424:424]};
    assign w_ld_h_dma_awaddr = {i_h[488:425]};
    assign w_ld_h_dma_wvalid = {i_h[489:489]};
    assign w_ld_h_dma_wdata = cfg[63:0];
    assign w_ld_h_dma_wstrb = {i_h[497:490]};
    assign w_ld_h_dma_bready = {i_h[498:498]};
    assign w_ld_m_arready = cfg[64:64];
    assign w_ld_m_rvalid = cfg[65:65];
    assign w_ld_m_rdata = cfg[129:66];
    assign w_ld_m_rresp = cfg[131:130];
    assign w_ld_m_rlast = cfg[132:132];
    assign w_ld_m_awready = cfg[133:133];
    assign w_ld_m_wready = cfg[134:134];
    assign w_ld_m_bvalid = cfg[135:135];
    assign w_ld_m_bresp = cfg[137:136];
    assign w_ld_req_rdy = cfg[139:138];
    assign w_ld_rsp_v = cfg[141:140];
    assign w_ld_rsp_we = cfg[143:142];
    assign w_ld_rsp_tag = cfg[175:144];
    assign w_ld_rsp_data = cfg[687:176];
    ot_hfd_loader_cx_local_reset #(.ENABLE(1), .ND(2), .SHARED(1)) u_ld (.clk_core(cx[0]), .clk_host(w_ld_clk_host), .rst_host_n(w_ld_rst_host_n), .clk_mem(w_ld_clk_mem), .rst_mem_n(w_ld_rst_mem_n), .s_awvalid(w_ld_s_awvalid), .s_awready(w_ld_s_awready), .s_awaddr(w_ld_s_awaddr), .s_wvalid(w_ld_s_wvalid), .s_wready(w_ld_s_wready), .s_wdata(w_ld_s_wdata), .s_wstrb(w_ld_s_wstrb), .s_bvalid(w_ld_s_bvalid), .s_bready(w_ld_s_bready), .s_arvalid(w_ld_s_arvalid), .s_arready(w_ld_s_arready), .s_araddr(w_ld_s_araddr), .s_rvalid(w_ld_s_rvalid), .s_rready(w_ld_s_rready), .s_rdata(w_ld_s_rdata), .h_awvalid(w_ld_h_awvalid), .h_awready(w_ld_h_awready), .h_awaddr(w_ld_h_awaddr), .h_wvalid(w_ld_h_wvalid), .h_wready(w_ld_h_wready), .h_wdata(w_ld_h_wdata), .h_wstrb(w_ld_h_wstrb), .h_bvalid(w_ld_h_bvalid), .h_bready(w_ld_h_bready), .h_arvalid(w_ld_h_arvalid), .h_arready(w_ld_h_arready), .h_araddr(w_ld_h_araddr), .h_rvalid(w_ld_h_rvalid), .h_rready(w_ld_h_rready), .h_rdata(w_ld_h_rdata), .h_dma_arvalid(w_ld_h_dma_arvalid), .h_dma_arready(w_ld_h_dma_arready), .h_dma_araddr(w_ld_h_dma_araddr), .h_dma_rvalid(w_ld_h_dma_rvalid), .h_dma_rready(w_ld_h_dma_rready), .h_dma_rdata(w_ld_h_dma_rdata), .h_dma_rresp(w_ld_h_dma_rresp), .h_dma_rlast(w_ld_h_dma_rlast), .h_dma_awvalid(w_ld_h_dma_awvalid), .h_dma_awready(w_ld_h_dma_awready), .h_dma_awaddr(w_ld_h_dma_awaddr), .h_dma_wvalid(w_ld_h_dma_wvalid), .h_dma_wready(w_ld_h_dma_wready), .h_dma_wdata(w_ld_h_dma_wdata), .h_dma_wstrb(w_ld_h_dma_wstrb), .h_dma_bvalid(w_ld_h_dma_bvalid), .h_dma_bready(w_ld_h_dma_bready), .h_dma_bresp(w_ld_h_dma_bresp), .m_arvalid(w_ld_m_arvalid), .m_arready(w_ld_m_arready), .m_araddr(w_ld_m_araddr), .m_arlen(w_ld_m_arlen), .m_arsize(w_ld_m_arsize), .m_rvalid(w_ld_m_rvalid), .m_rready(w_ld_m_rready), .m_rdata(w_ld_m_rdata), .m_rresp(w_ld_m_rresp), .m_rlast(w_ld_m_rlast), .m_awvalid(w_ld_m_awvalid), .m_awready(w_ld_m_awready), .m_awaddr(w_ld_m_awaddr), .m_awlen(w_ld_m_awlen), .m_awsize(w_ld_m_awsize), .m_wvalid(w_ld_m_wvalid), .m_wready(w_ld_m_wready), .m_wdata(w_ld_m_wdata), .m_wstrb(w_ld_m_wstrb), .m_wlast(w_ld_m_wlast), .m_bvalid(w_ld_m_bvalid), .m_bready(w_ld_m_bready), .m_bresp(w_ld_m_bresp), .req_v(w_ld_req_v), .req_rdy(w_ld_req_rdy), .req_we(w_ld_req_we), .req_addr(w_ld_req_addr), .req_wdata(w_ld_req_wdata), .req_wstrb(w_ld_req_wstrb), .req_tag(w_ld_req_tag), .rsp_v(w_ld_rsp_v), .rsp_rdy(w_ld_rsp_rdy), .rsp_we(w_ld_rsp_we), .rsp_tag(w_ld_rsp_tag), .rsp_data(w_ld_rsp_data), .irq(w_ld_irq), .fault(w_ld_fault));
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_arvalid
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_arvalid[k]), .q());
    end
    for (genvar k = 0; k < 64; k = k + 1) begin : g_sink_w_ld_m_araddr
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_araddr[k]), .q());
    end
    for (genvar k = 0; k < 8; k = k + 1) begin : g_sink_w_ld_m_arlen
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_arlen[k]), .q());
    end
    for (genvar k = 0; k < 3; k = k + 1) begin : g_sink_w_ld_m_arsize
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_arsize[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_rready
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_rready[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_awvalid
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_awvalid[k]), .q());
    end
    for (genvar k = 0; k < 64; k = k + 1) begin : g_sink_w_ld_m_awaddr
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_awaddr[k]), .q());
    end
    for (genvar k = 0; k < 8; k = k + 1) begin : g_sink_w_ld_m_awlen
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_awlen[k]), .q());
    end
    for (genvar k = 0; k < 3; k = k + 1) begin : g_sink_w_ld_m_awsize
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_awsize[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_wvalid
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_wvalid[k]), .q());
    end
    for (genvar k = 0; k < 64; k = k + 1) begin : g_sink_w_ld_m_wdata
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_wdata[k]), .q());
    end
    for (genvar k = 0; k < 8; k = k + 1) begin : g_sink_w_ld_m_wstrb
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_wstrb[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_wlast
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_wlast[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_m_bready
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_m_bready[k]), .q());
    end
    for (genvar k = 0; k < 2; k = k + 1) begin : g_sink_w_ld_req_we
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_req_we[k]), .q());
    end
    for (genvar k = 0; k < 64; k = k + 1) begin : g_sink_w_ld_req_wstrb
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_req_wstrb[k]), .q());
    end
    for (genvar k = 0; k < 32; k = k + 1) begin : g_sink_w_ld_req_tag
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_req_tag[k]), .q());
    end
    for (genvar k = 0; k < 2; k = k + 1) begin : g_sink_w_ld_rsp_rdy
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_rsp_rdy[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_irq
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_irq[k]), .q());
    end
    for (genvar k = 0; k < 1; k = k + 1) begin : g_sink_w_ld_fault
        (* keep *) ot_hfd_sink1 u (.clk(clk), .d(w_ld_fault[k]), .q());
    end
    wire fclk_0; ot_fwd_clk_inv u_fclk_0 (.a(clk), .y(fclk_0));
    wire [513:0] od_h = {338'd0, w_ld_h_dma_bresp[1:0], w_ld_h_dma_bvalid[0:0], w_ld_h_dma_wready[0:0], w_ld_h_dma_awready[0:0], w_ld_h_dma_rlast[0:0], w_ld_h_dma_rresp[1:0], w_ld_h_dma_rdata[63:0], w_ld_h_dma_rvalid[0:0], w_ld_h_dma_arready[0:0], w_ld_h_rready[0:0], w_ld_h_araddr[11:0], w_ld_h_arvalid[0:0], w_ld_h_bready[0:0], w_ld_h_wstrb[3:0], w_ld_h_wdata[31:0], w_ld_h_wvalid[0:0], w_ld_h_awaddr[11:0], w_ld_h_awvalid[0:0], w_ld_s_rdata[31:0], w_ld_s_rvalid[0:0], w_ld_s_arready[0:0], w_ld_s_bvalid[0:0], w_ld_s_wready[0:0], w_ld_s_awready[0:0]};
    wire [513:0] o_h;
    for (genvar k = 0; k < 514; k = k + 1) begin : g_o_h
        ot_hfd_oreg2 u (.clk(clk), .d(od_h[k]), .q(o_h[k]));
    end
    assign h[255:0] = o_h[255:0];
    assign h[512] = fclk_0;
    wire [340:0] od_t_cmdproc = {268'd0, w_ld_req_wdata[63:0], w_ld_req_addr[7:0], w_ld_req_v[0]};
    wire [340:0] o_t_cmdproc;
    for (genvar k = 0; k < 341; k = k + 1) begin : g_o_t_cmdproc
        ot_hfd_oreg2 u (.clk(clk), .d(od_t_cmdproc[k]), .q(o_t_cmdproc[k]));
    end
    assign t_cmdproc[340:0] = o_t_cmdproc[340:0];
endmodule
