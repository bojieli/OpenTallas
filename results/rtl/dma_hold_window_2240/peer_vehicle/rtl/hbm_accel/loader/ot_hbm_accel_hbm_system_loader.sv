`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hbm_accel_hbm_system: HBM-accelerator successor of
// rtl/gpu_sys/ot_gpu_hbm_system.sv (byte-identical, still the ablation top)
// for HA3.  HA3 = 0 (default): the same composition (ot_hbm_accel_simt_sm at
// HA3 = 0 behaves as ot_gpu_simt_sm; ot_gpu_coll_mux + ot_gpu_coll_system).
// HA3 = 1: SMs with COLLX / COLLSS, and per die ot_hbm_accel_coll_port (the
// cut-through, multicast, fused-epilogue SM -> collective endpoint) in front
// of the unchanged ot_gpu_coll_fabric (NVLS switch).  Otherwise as the
// original (see its header).
// ---------------------------------------------------------------------------
module ot_hbm_accel_hbm_system_loader #(parameter integer LOADER=0,
    parameter integer ENABLE    = 0,
    parameter integer HA3       = 0,     // 1: HA3 collective port (cut-through, multicast, fused epilogue)
    parameter integer FLAT      = 5,
    parameter integer EPI       = 1,     // HA3 port: 0 = cut-through only (fused requests fault)
    parameter integer ND        = 2,
    parameter integer NSM       = 2,
    parameter integer NL        = 128,
    parameter integer IMW       = 13,
    parameter integer CB        = 8,
    parameter integer NS        = 2,
    parameter integer NPC       = 2,
    parameter integer MEM_WORDS = 65536,
    parameter integer SW_PIPE   = 8,
    parameter integer USE_W2    = 0,     // 1: Nash's W2 exact tag/generation completion in every HBM partition
    parameter integer HAS_DIV   = 0,     // SM div.rn/sqrt.rn lanes (DeepSeek-V4.1)
    parameter integer HAS_BD    = 0      // SM block-scaled tensor core (DeepSeek-V4.1)
) (
    input  wire        por_n,              // power-on reset (asynchronous); ot_gpu_reset_ctrl releases each domain
    input  wire        clk_host,
    input  wire        clk_sm,
    input  wire        clk_mem,
    input  wire        clk_link,
    // host BAR (AXI4-Lite slave)
    input  wire        s_awvalid,
    output wire        s_awready,
    input  wire [11:0] s_awaddr,
    input  wire        s_wvalid,
    output wire        s_wready,
    input  wire [31:0] s_wdata,
    input  wire [3:0]  s_wstrb,
    output wire        s_bvalid,
    input  wire        s_bready,
    input  wire        s_arvalid,
    output wire        s_arready,
    input  wire [11:0] s_araddr,
    output wire        s_rvalid,
    input  wire        s_rready,
    output wire [31:0] s_rdata,
    // DMA to host memory (AXI4 master, single beats)
    output wire        m_arvalid,
    input  wire        m_arready,
    output wire [63:0] m_araddr,
    input  wire        m_rvalid,
    input  wire [63:0] m_rdata,
    input  wire [1:0]  m_rresp,
    input  wire        m_rlast,
    output wire        m_awvalid,
    input  wire        m_awready,
    output wire [63:0] m_awaddr,
    output wire        m_wvalid,
    input  wire        m_wready,
    output wire [63:0] m_wdata,
    output wire [7:0]  m_wstrb,
    input  wire        m_bvalid,
    input  wire [1:0]  m_bresp,
    output wire        irq,
    // driver loader
    input  wire        ld_v,
    output wire        ld_rdy,
    input  wire        ld_target,
    input  wire [3:0]  ld_die,
    input  wire [3:0]  ld_sm,
    input  wire [23:0] ld_addr,
    input  wire [63:0] ld_data,
    output wire        sys_fault,
    output wire [31:0] st_steps,
    output wire[7:0] m_arlen,m_awlen,
    output wire[2:0] m_arsize,m_awsize,
    output wire m_rready,m_wlast,m_bready
);
initial if(LOADER!=0&&LOADER!=1)$fatal(1,"LOADER must be 0 or 1");
generate if (ENABLE == 0) begin : g_off
    assign s_awready = 1'b0; assign s_wready = 1'b0; assign s_bvalid = 1'b0; assign s_arready = 1'b0;
    assign s_rvalid = 1'b0; assign s_rdata = 32'd0; assign m_arvalid = 1'b0; assign m_araddr = 64'd0;
    assign m_awvalid = 1'b0; assign m_awaddr = 64'd0; assign m_wvalid = 1'b0; assign m_wdata = 64'd0;
    assign m_wstrb = 8'd0; assign irq = 1'b0; assign ld_rdy = 1'b0; assign sys_fault = 1'b0; assign st_steps = 32'd0;
    assign m_arlen=0;assign m_awlen=0;assign m_arsize=0;assign m_awsize=0;assign m_rready=0;assign m_wlast=0;assign m_bready=0;
end else begin : g_on
    localparam integer NCL = 2 * NSM;          // memory clients per die: LSU and bulk copy of every SM
    wire rst_host_n, rst_sm_n, rst_mem_n, rst_link_n;
    ot_gpu_reset_ctrl #(.ENABLE(1)) u_rst (.por_n(por_n), .clk_mem(clk_mem), .clk_link(clk_link), .clk_sm(clk_sm),
        .clk_host(clk_host), .rst_mem_n(rst_mem_n), .rst_link_n(rst_link_n), .rst_sm_n(rst_sm_n), .rst_host_n(rst_host_n));
    // ------------------------------------------------------------------ host interface
    wire        eng_start, eng_done, eng_fault, eng_clr_req, eng_clr_ack;
    wire [15:0] eng_token, eng_pos, eng_next_token;
    wire [3:0]  eng_slot;
    wire [23:0] kv_base;
    wire [31:0] eng_cycles;
    wire        pb_we, pb_re;
    wire [11:0] pb_waddr, pb_raddr;
    wire [15:0] pb_wdata;
    reg  [15:0] pb_q;
    reg  [15:0] pbuf [0:4095];
    always @(posedge clk_host) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
    end
    wire[7:0] h_m_arlen,h_m_awlen;wire[2:0] h_m_arsize,h_m_awsize;
    wire [1:0] s_bresp, s_rresp;
    wire h_m_rready,h_m_wlast,h_m_bready;
    wire arr_rst_n; wire [7:0] cfg_users; wire [15:0] cfg_prompt_len, cfg_gen_len;
    wire h_s_awvalid,h_s_awready,h_s_wvalid,h_s_wready,h_s_bvalid,h_s_bready,h_s_arvalid,h_s_arready,h_s_rvalid,h_s_rready;
    wire[11:0] h_s_awaddr,h_s_araddr;wire[31:0] h_s_wdata,h_s_rdata;wire[3:0] h_s_wstrb;
    wire h_m_arvalid,h_m_arready,h_m_rvalid,h_m_rlast,h_m_awvalid,h_m_awready,h_m_wvalid,h_m_wready,h_m_bvalid,h_irq;
    wire[63:0] h_m_araddr,h_m_rdata,h_m_awaddr,h_m_wdata;wire[7:0] h_m_wstrb;wire[1:0] h_m_rresp,h_m_bresp;
    wire loader_irq,loader_fault;
    wire[ND-1:0] lrq_v,lrq_rdy,lrq_we,lrs_v,lrs_rdy,lrs_we;
    wire[ND*32-1:0] lrq_addr,lrq_strb;wire[ND*256-1:0] lrq_data,lrs_data;wire[ND*16-1:0] lrq_tag,lrs_tag;
    ot_host_if #(.NSLOT(16), .MODE(0), .ENG_CTX(16), .NW(16), .PLB(8), .CTX_MAX(64), .AW(24), .KVW(1024)) u_host (
        .clk(clk_host), .rst_n(rst_host_n),
        .s_awvalid(h_s_awvalid), .s_awready(h_s_awready), .s_awaddr(h_s_awaddr), .s_wvalid(h_s_wvalid), .s_wready(h_s_wready),
        .s_wdata(h_s_wdata), .s_wstrb(h_s_wstrb), .s_bvalid(h_s_bvalid), .s_bready(h_s_bready), .s_bresp(s_bresp),
        .s_arvalid(h_s_arvalid), .s_arready(h_s_arready), .s_araddr(h_s_araddr), .s_rvalid(h_s_rvalid), .s_rready(h_s_rready),
        .s_rdata(h_s_rdata), .s_rresp(s_rresp),
        .m_arvalid(h_m_arvalid), .m_arready(h_m_arready), .m_araddr(h_m_araddr), .m_arlen(h_m_arlen), .m_arsize(h_m_arsize),
        .m_rvalid(h_m_rvalid), .m_rready(h_m_rready), .m_rdata(h_m_rdata), .m_rresp(h_m_rresp), .m_rlast(h_m_rlast),
        .m_awvalid(h_m_awvalid), .m_awready(h_m_awready), .m_awaddr(h_m_awaddr), .m_awlen(h_m_awlen), .m_awsize(h_m_awsize),
        .m_wvalid(h_m_wvalid), .m_wready(h_m_wready), .m_wdata(h_m_wdata), .m_wstrb(h_m_wstrb), .m_wlast(h_m_wlast),
        .m_bvalid(h_m_bvalid), .m_bready(h_m_bready), .m_bresp(h_m_bresp), .irq(h_irq),
        .pb_we(pb_we), .pb_waddr(pb_waddr), .pb_wdata(pb_wdata), .pb_re(pb_re), .pb_raddr(pb_raddr), .pb_q(pb_q),
        .eng_start(eng_start), .eng_token(eng_token), .eng_pos(eng_pos), .eng_slot(eng_slot), .kv_base(kv_base),
        .eng_done(eng_done), .eng_next_token(eng_next_token), .eng_cycles(eng_cycles), .eng_fault(eng_fault),
        .eng_clr_req(eng_clr_req), .eng_clr_ack(eng_clr_ack),
        .arr_rst_n(arr_rst_n), .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos(16'd0), .tok_valid(1'b0), .tok_user(8'd0), .tok_pos(16'd0),
        .tok_id(16'd0), .users_done(8'd0), .arr_fault(1'b0));
    assign irq=h_irq|loader_irq;
    ot_hbm_accel_loader_host #(.ENABLE(LOADER),.ND(ND)) u_loader_host(
        .clk_host(clk_host),
        .rst_host_n(rst_host_n),
        .clk_mem(clk_mem),
        .rst_mem_n(rst_mem_n),
        .s_awvalid(s_awvalid),
        .h_awvalid(h_s_awvalid),
        .s_awready(s_awready),
        .h_awready(h_s_awready),
        .s_awaddr(s_awaddr),
        .h_awaddr(h_s_awaddr),
        .s_wvalid(s_wvalid),
        .h_wvalid(h_s_wvalid),
        .s_wready(s_wready),
        .h_wready(h_s_wready),
        .s_wdata(s_wdata),
        .h_wdata(h_s_wdata),
        .s_wstrb(s_wstrb),
        .h_wstrb(h_s_wstrb),
        .s_bvalid(s_bvalid),
        .h_bvalid(h_s_bvalid),
        .s_bready(s_bready),
        .h_bready(h_s_bready),
        .s_arvalid(s_arvalid),
        .h_arvalid(h_s_arvalid),
        .s_arready(s_arready),
        .h_arready(h_s_arready),
        .s_araddr(s_araddr),
        .h_araddr(h_s_araddr),
        .s_rvalid(s_rvalid),
        .h_rvalid(h_s_rvalid),
        .s_rready(s_rready),
        .h_rready(h_s_rready),
        .s_rdata(s_rdata),
        .h_rdata(h_s_rdata),
        .h_dma_arvalid(h_m_arvalid),
        .h_dma_arready(h_m_arready),
        .h_dma_araddr(h_m_araddr),
        .h_dma_rvalid(h_m_rvalid),
        .h_dma_rready(h_m_rready),
        .h_dma_rdata(h_m_rdata),
        .h_dma_rresp(h_m_rresp),
        .h_dma_rlast(h_m_rlast),
        .h_dma_awvalid(h_m_awvalid),
        .h_dma_awready(h_m_awready),
        .h_dma_awaddr(h_m_awaddr),
        .h_dma_wvalid(h_m_wvalid),
        .h_dma_wready(h_m_wready),
        .h_dma_wdata(h_m_wdata),
        .h_dma_wstrb(h_m_wstrb),
        .h_dma_bvalid(h_m_bvalid),
        .h_dma_bready(h_m_bready),
        .h_dma_bresp(h_m_bresp),
        .m_arvalid(m_arvalid),
        .m_arready(m_arready),
        .m_araddr(m_araddr),
        .m_arlen(m_arlen),
        .m_arsize(m_arsize),
        .m_rvalid(m_rvalid),
        .m_rready(m_rready),
        .m_rdata(m_rdata),
        .m_rresp(m_rresp),
        .m_rlast(m_rlast),
        .m_awvalid(m_awvalid),
        .m_awready(m_awready),
        .m_awaddr(m_awaddr),
        .m_awlen(m_awlen),
        .m_awsize(m_awsize),
        .m_wvalid(m_wvalid),
        .m_wready(m_wready),
        .m_wdata(m_wdata),
        .m_wstrb(m_wstrb),
        .m_wlast(m_wlast),
        .m_bvalid(m_bvalid),
        .m_bready(m_bready),
        .m_bresp(m_bresp),
        .req_v(lrq_v),
        .req_rdy(lrq_rdy),
        .req_we(lrq_we),
        .req_addr(lrq_addr),
        .req_wdata(lrq_data),
        .req_wstrb(lrq_strb),
        .req_tag(lrq_tag),
        .rsp_v(lrs_v),
        .rsp_rdy(lrs_rdy),
        .rsp_we(lrs_we),
        .rsp_tag(lrs_tag),
        .rsp_data(lrs_data),
        .irq(loader_irq),
        .fault(loader_fault));
    reg [31:0] steps_q;
    always @(posedge clk_host or negedge rst_host_n)
        if (!rst_host_n) steps_q <= 0; else if (eng_done) steps_q <= steps_q + 1;
    assign st_steps = steps_q;

    wire [ND-1:0]      db_v, db_rdy, cpl_v, cpl_rdy;
    wire [ND*32-1:0]   db_tokpos;
    wire [ND*52-1:0]   cpl_data;
    wire [ND-1:0]      cmd_we;
    wire [CB-1:0]      cmd_addr;
    wire [63:0]        cmd_wdata, im_data;
    wire [ND*NSM-1:0]  im_we;
    wire [IMW-1:0]     im_addr;
    wire               bridge_fault;
    ot_gpu_host_bridge #(.ENABLE(1), .ND(ND), .NSM(NSM), .CB(CB), .IMW(IMW)) u_bridge (
        .clk_host(clk_host), .rst_host_n(rst_host_n), .clk_sm(clk_sm), .rst_sm_n(rst_sm_n),
        .eng_start(eng_start), .eng_token(eng_token), .eng_pos(eng_pos), .eng_done(eng_done),
        .eng_next_token(eng_next_token), .eng_cycles(eng_cycles), .eng_fault(eng_fault),
        .eng_clr_req(eng_clr_req), .eng_clr_ack(eng_clr_ack),
        .ld_v(ld_v), .ld_rdy(ld_rdy), .ld_target(ld_target), .ld_die(ld_die), .ld_sm(ld_sm), .ld_addr(ld_addr),
        .ld_data(ld_data), .db_v(db_v), .db_rdy(db_rdy), .db_tokpos(db_tokpos), .cpl_v(cpl_v), .cpl_rdy(cpl_rdy),
        .cpl_data(cpl_data), .cmd_we(cmd_we), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata), .im_we(im_we),
        .im_addr(im_addr), .im_data(im_data), .cdc_fault(bridge_fault));

    // ------------------------------------------------------------------ collective fabric
    wire [ND-1:0]         ep_req_v, ep_req_rdy, ep_mode, ep_rsp_v, ep_rsp_rdy;
    wire [ND*8-1:0]       ep_count;
    wire [ND*NL*32-1:0]   ep_data, ep_rsp_data;
    wire                  coll_fault;
    localparam integer PW = 32 * 16 + 2 + 32;
    wire [ND-1:0]         up_v, dn_v, port_f;
    wire [ND*PW-1:0]      up_rec, dn_rec;
    if (HA3 == 0) begin : g_coll0
        ot_gpu_coll_system #(.ENABLE(1), .R(ND), .NL(NL), .SW_PIPE(SW_PIPE)) u_coll (
            .clk_sm(clk_sm), .rst_sm_n(rst_sm_n), .clk_link(clk_link), .rst_link_n(rst_link_n),
            .req_v(ep_req_v), .req_rdy(ep_req_rdy), .mode(ep_mode), .count(ep_count), .data(ep_data),
            .rsp_v(ep_rsp_v), .rsp_rdy(ep_rsp_rdy), .rsp_data(ep_rsp_data), .fault(coll_fault));
        assign up_v = {ND{1'b0}}; assign up_rec = {ND*PW{1'b0}};
    end else begin : g_coll1
        wire fab_f;
        ot_gpu_coll_fabric #(.ENABLE(1), .R(ND), .NL(NL), .SW_PIPE(SW_PIPE)) u_fab (
            .clk_link(clk_link), .rst_link_n(rst_link_n), .up_v(up_v), .up_rec(up_rec), .dn_v(dn_v), .dn_rec(dn_rec),
            .fault(fab_f));
        assign coll_fault = fab_f | (|port_f);
        assign ep_req_rdy = {ND{1'b0}}; assign ep_rsp_v = {ND{1'b0}}; assign ep_rsp_data = {ND*NL*32{1'b0}};
    end

    // ------------------------------------------------------------------ dies
    wire [ND-1:0] die_fault;
    genvar d, s;
    for (d = 0; d < ND; d = d + 1) begin : g_die
        wire [NSM-1:0] launch_v, sm_done, sm_fault, res_v, bar_arr, bar_rel, busy;
        wire [31:0] launch_pc;
        wire [15:0] launch_token, launch_pos;
        wire [NSM*32-1:0] res_data;
        wire [15:0] cpl_token; wire [3:0] cpl_status; wire [31:0] cpl_cycles, st_kernels, st_busy;
        ot_gpu_cmdproc #(.ENABLE(1), .NSM(NSM), .NCMD(1 << CB)) u_cp (
            .clk(clk_sm), .rst_n(rst_sm_n), .cmd_we(cmd_we[d]), .cmd_addr(cmd_addr), .cmd_wdata(cmd_wdata),
            .db_v(db_v[d]), .db_rdy(db_rdy[d]), .db_token(db_tokpos[d*32 +: 16]), .db_pos(db_tokpos[d*32+16 +: 16]),
            .launch_v(launch_v), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
            .sm_done(sm_done), .sm_fault(sm_fault), .res_v(res_v), .res_data(res_data),
            .cpl_v(cpl_v[d]), .cpl_rdy(cpl_rdy[d]), .cpl_token(cpl_token), .cpl_status(cpl_status),
            .cpl_cycles(cpl_cycles), .st_kernels(st_kernels), .st_busy(st_busy));
        assign cpl_data[d*52 +: 52] = {cpl_cycles, cpl_status, cpl_token};
        // grid barrier: one node, the SMs of the die as children (root: release = own arrival sense)
        wire bar_up;
        ot_gpu_barrier_node #(.K(NSM)) u_bar (.clk(clk_sm), .rst_n(rst_sm_n), .arr(bar_arr), .up(bar_up),
                                              .rel_in(bar_up), .rel(bar_rel));
        // memory clients (clk_sm side) and their crossings
        wire [NCL-1:0]       c_req_v, c_req_rdy, c_req_we, c_rsp_v, c_rsp_rdy, c_rsp_we;
        wire [NCL*32-1:0]    c_req_addr, c_req_wstrb;
        wire [NCL*256-1:0]   c_req_wdata, c_rsp_data;
        wire [NCL*16-1:0]    c_req_tag, c_rsp_tag;
        wire [NCL+LOADER-1:0] x_req_v,x_req_rdy,x_req_we,x_rsp_v,x_rsp_rdy,x_rsp_we;
        wire[NCL-1:0] cdc_f;
        wire [(NCL+LOADER)*32-1:0] x_req_addr, x_req_wstrb;
        wire [(NCL+LOADER)*256-1:0] x_req_wdata, x_rsp_data;
        wire [(NCL+LOADER)*16-1:0] x_req_tag, x_rsp_tag;
        // collective ports of the SMs
        wire [NSM-1:0] cs_req_v, cs_req_rdy, cs_mode, cs_rsp_v, cs_rsp_rdy;
        wire [NSM*8-1:0] cs_count;
        wire [NSM*NL*32-1:0] cs_data;
        wire [NL*32-1:0] cs_rsp_data;
        wire [NSM-1:0] cs_x, cs_fuse;
        wire [NSM*8-1:0] cs_off, cs_nown;
        wire [NSM*NL*32-1:0] cs_resid;
        wire [31:0] cs_rsp_ss;
        wire cs_rsp_err;
        for (s = 0; s < NSM; s = s + 1) begin : g_sm
            wire [31:0] st_instr, st_cycles, st_stall_mem, st_tc_rows;
            wire [31:0] rd;
            assign res_data[s*32 +: 32] = rd;
            ot_hbm_accel_simt_sm #(.ENABLE(1), .HA3(HA3), .FLAT(FLAT), .NL(NL), .IMW(IMW), .HAS_DIV(HAS_DIV), .HAS_BD(HAS_BD)) u_sm (
                .clk(clk_sm), .rst_n(rst_sm_n), .sm_id(s[7:0]), .die_id(d[7:0]),
                .im_we(im_we[d*NSM + s]), .im_addr(im_addr), .im_data(im_data),
                .launch_v(launch_v[s]), .launch_pc(launch_pc), .launch_token(launch_token), .launch_pos(launch_pos),
                .sm_done(sm_done[s]), .sm_fault(sm_fault[s]), .res_v(res_v[s]), .res_data(rd), .busy(busy[s]),
                .bar_arrive(bar_arr[s]), .bar_release(bar_rel[s]),
                .lreq_v(c_req_v[2*s]), .lreq_rdy(c_req_rdy[2*s]), .lreq_we(c_req_we[2*s]),
                .lreq_addr(c_req_addr[2*s*32 +: 32]), .lreq_wdata(c_req_wdata[2*s*256 +: 256]),
                .lreq_wstrb(c_req_wstrb[2*s*32 +: 32]), .lreq_tag(c_req_tag[2*s*16 +: 16]),
                .lrsp_v(c_rsp_v[2*s]), .lrsp_rdy(c_rsp_rdy[2*s]), .lrsp_tag(c_rsp_tag[2*s*16 +: 16]),
                .lrsp_we(c_rsp_we[2*s]), .lrsp_data(c_rsp_data[2*s*256 +: 256]),
                .treq_v(c_req_v[2*s+1]), .treq_rdy(c_req_rdy[2*s+1]), .treq_addr(c_req_addr[(2*s+1)*32 +: 32]),
                .treq_tag(c_req_tag[(2*s+1)*16 +: 16]), .trsp_v(c_rsp_v[2*s+1]), .trsp_rdy(c_rsp_rdy[2*s+1]),
                .trsp_tag(c_rsp_tag[(2*s+1)*16 +: 16]), .trsp_data(c_rsp_data[(2*s+1)*256 +: 256]),
                .coll_req_v(cs_req_v[s]), .coll_req_rdy(cs_req_rdy[s]), .coll_mode(cs_mode[s]),
                .coll_count(cs_count[s*8 +: 8]), .coll_data(cs_data[s*NL*32 +: NL*32]), .coll_rsp_v(cs_rsp_v[s]),
                .coll_rsp_rdy(cs_rsp_rdy[s]), .coll_rsp_data(cs_rsp_data),
                .coll_x(cs_x[s]), .coll_off(cs_off[s*8 +: 8]), .coll_nown(cs_nown[s*8 +: 8]), .coll_fuse(cs_fuse[s]),
                .coll_resid(cs_resid[s*NL*32 +: NL*32]), .coll_rsp_ss(cs_rsp_ss), .coll_rsp_err(cs_rsp_err),
                .st_instr(st_instr), .st_cycles(st_cycles), .st_stall_mem(st_stall_mem), .st_tc_rows(st_tc_rows));
            // the bulk-copy port only reads
            assign c_req_we[2*s+1] = 1'b0;
            assign c_req_wdata[(2*s+1)*256 +: 256] = 256'd0;
            assign c_req_wstrb[(2*s+1)*32 +: 32] = 32'd0;
        end
        genvar c;
        for (c = 0; c < NCL; c = c + 1) begin : g_cdc
            ot_gpu_mreq_cdc #(.ENABLE(1), .AW(3)) u_x (
                .clk_s(clk_sm), .rst_s_n(rst_sm_n), .clk_m(clk_mem), .rst_m_n(rst_mem_n),
                .s_req_v(c_req_v[c]), .s_req_rdy(c_req_rdy[c]), .s_req_we(c_req_we[c]), .s_req_addr(c_req_addr[c*32 +: 32]),
                .s_req_wdata(c_req_wdata[c*256 +: 256]), .s_req_wstrb(c_req_wstrb[c*32 +: 32]), .s_req_tag(c_req_tag[c*16 +: 16]),
                .s_rsp_v(c_rsp_v[c]), .s_rsp_rdy(c_rsp_rdy[c]), .s_rsp_tag(c_rsp_tag[c*16 +: 16]), .s_rsp_we(c_rsp_we[c]),
                .s_rsp_data(c_rsp_data[c*256 +: 256]),
                .m_req_v(x_req_v[c]), .m_req_rdy(x_req_rdy[c]), .m_req_we(x_req_we[c]), .m_req_addr(x_req_addr[c*32 +: 32]),
                .m_req_wdata(x_req_wdata[c*256 +: 256]), .m_req_wstrb(x_req_wstrb[c*32 +: 32]), .m_req_tag(x_req_tag[c*16 +: 16]),
                .m_rsp_v(x_rsp_v[c]), .m_rsp_rdy(x_rsp_rdy[c]), .m_rsp_tag(x_rsp_tag[c*16 +: 16]), .m_rsp_we(x_rsp_we[c]),
                .m_rsp_data(x_rsp_data[c*256 +: 256]), .fault(cdc_f[c]));
        end
        if(LOADER)begin:g_loader_client
            assign x_req_v[NCL]=lrq_v[d];assign lrq_rdy[d]=x_req_rdy[NCL];assign x_req_we[NCL]=lrq_we[d];
            assign x_req_addr[NCL*32+:32]=lrq_addr[d*32+:32];assign x_req_wdata[NCL*256+:256]=lrq_data[d*256+:256];
            assign x_req_wstrb[NCL*32+:32]=lrq_strb[d*32+:32];assign x_req_tag[NCL*16+:16]=lrq_tag[d*16+:16];
            assign lrs_v[d]=x_rsp_v[NCL];assign x_rsp_rdy[NCL]=lrs_rdy[d];assign lrs_we[d]=x_rsp_we[NCL];
            assign lrs_tag[d*16+:16]=x_rsp_tag[NCL*16+:16];assign lrs_data[d*256+:256]=x_rsp_data[NCL*256+:256];
        end else begin:g_no_loader_client
            assign lrq_rdy[d]=0;assign lrs_v[d]=0;assign lrs_we[d]=0;assign lrs_tag[d*16+:16]=0;assign lrs_data[d*256+:256]=0;
        end
        wire mem_fault;
        ot_gpu_memsys_adapter #(.ENABLE(1), .NC(NCL+LOADER), .NS(NS), .NPC(NPC), .MEM_WORDS(MEM_WORDS), .DIE(d), .USE_W2(USE_W2)) u_mem (
            .clk(clk_mem), .rst_n(rst_mem_n),
            .c_req_v(x_req_v), .c_req_rdy(x_req_rdy), .c_req_we(x_req_we), .c_req_addr(x_req_addr),
            .c_req_wdata(x_req_wdata), .c_req_wstrb(x_req_wstrb), .c_req_tag(x_req_tag),
            .c_rsp_v(x_rsp_v), .c_rsp_rdy(x_rsp_rdy), .c_rsp_tag(x_rsp_tag), .c_rsp_we(x_rsp_we), .c_rsp_data(x_rsp_data),
            .fault(mem_fault));
        if (HA3 == 0) begin : g_mux
            ot_gpu_coll_mux #(.ENABLE(1), .NSM(NSM), .NL(NL)) u_cmux (
                .clk(clk_sm), .rst_n(rst_sm_n), .s_req_v(cs_req_v), .s_req_rdy(cs_req_rdy), .s_mode(cs_mode),
                .s_count(cs_count), .s_data(cs_data), .s_rsp_v(cs_rsp_v), .s_rsp_rdy(cs_rsp_rdy), .s_rsp_data(cs_rsp_data),
                .m_req_v(ep_req_v[d]), .m_req_rdy(ep_req_rdy[d]), .m_mode(ep_mode[d]), .m_count(ep_count[d*8 +: 8]),
                .m_data(ep_data[d*NL*32 +: NL*32]), .m_rsp_v(ep_rsp_v[d]), .m_rsp_rdy(ep_rsp_rdy[d]),
                .m_rsp_data(ep_rsp_data[d*NL*32 +: NL*32]));
            assign cs_rsp_ss = 32'd0; assign cs_rsp_err = 1'b0; assign port_f[d] = 1'b0;
        end else begin : g_port
            wire [31:0] st_coll;
            ot_hbm_accel_coll_port #(.ENABLE(1), .NSM(NSM), .NL(NL), .R(ND), .RANK(d), .FLAT(FLAT), .EPI(EPI)) u_port (
                .clk_sm(clk_sm), .rst_sm_n(rst_sm_n), .s_req_v(cs_req_v), .s_req_rdy(cs_req_rdy), .s_mode(cs_mode),
                .s_count(cs_count), .s_data(cs_data), .s_x(cs_x), .s_off(cs_off), .s_nown(cs_nown), .s_fuse(cs_fuse),
                .s_resid(cs_resid), .s_rsp_v(cs_rsp_v), .s_rsp_rdy(cs_rsp_rdy), .s_rsp_data(cs_rsp_data),
                .s_rsp_ss(cs_rsp_ss), .s_rsp_err(cs_rsp_err), .fault(port_f[d]), .st_coll(st_coll),
                .clk_link(clk_link), .rst_link_n(rst_link_n), .lk_tx_v(up_v[d]), .lk_tx_rec(up_rec[d*PW +: PW]),
                .lk_rx_v(dn_v[d]), .lk_rx_rec(dn_rec[d*PW +: PW]));
            assign ep_req_v[d] = 1'b0; assign ep_rsp_rdy[d] = 1'b0; assign ep_mode[d] = 1'b0; assign ep_count[d*8 +: 8] = 8'd0;
            assign ep_data[d*NL*32 +: NL*32] = {NL*32{1'b0}};
        end
        assign die_fault[d] = (|sm_fault) | (|cdc_f) | mem_fault;
    end
    assign sys_fault = (|die_fault) | bridge_fault | coll_fault | eng_fault | loader_fault;
end endgenerate
endmodule
