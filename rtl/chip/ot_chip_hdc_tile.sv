`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical tile of the decode-core chips (docs/FULL_CHIP_IMPLEMENTATION.md).
//
// One mesh node of the die: the hardwired decode core (ot_hdc_core: the
// sequencer, the matrix-vector engine ME and the stream unit SU), its KV
// streaming engine (KVS), the package controller and a 5-port fabric router,
// with the core's memories.  It is the composition rtl/test/tb_hdc_array.sv
// and rtl/test/tb_hdc_core_hbm.sv simulate, made synthesizable: every memory
// is a macro instance instead of a behavioural array.
//
// Hierarchy for the physical flow:
//   hard macros   ot_hdc_matvec (ME), ot_hdc_stream (SU), ot_hdc_kv_stream
//                 (KVS), ot_chip_pkg_ctrl, ot_chip_router
//   memories      ot_mem_* placeholders (tools/chip_assembly/macros.py) until
//                 the memory compilers land
//   flat logic    the ot_hdc_core sequencer and this file's glue
//
// Router port 0 is local (the package controller); ports 1..4 are the N, E,
// S and W mesh neighbours.  The weight store is the tile's weight ROM bank on
// the ROM dies and its HBM prefetch buffer on the HBM die (same port).
// ---------------------------------------------------------------------------
module ot_chip_hdc_tile #(
    parameter integer VMA = 14,     // vector-memory element address bits (16,384 FP32)
    parameter integer WSA = 17,     // weight-store word address bits
    parameter integer LINK_STAGES = 3,   // mesh link register stages each way
    parameter integer LINK_DEPTH  = 12   // mesh link receive FIFO (= credits)
) (
    input  wire          clk,
    input  wire          rst_n,
    // mesh ports, [0] N, [1] E, [2] S, [3] W: pipelined, credit flow
    // (rtl/chip/ot_chip_mesh_link.sv); every pin is a flop output or input
    output wire [3:0]    m_out_valid,
    output wire [4*512-1:0] m_out_data,
    output wire [3:0]    m_out_last,
    input  wire [3:0]    m_out_cr,
    input  wire [3:0]    m_in_valid,
    input  wire [4*512-1:0] m_in_data,
    input  wire [3:0]    m_in_last,
    output wire [3:0]    m_in_cr,
    // configuration
    input  wire          rcfg_we,
    input  wire [7:0]    rcfg_dest,
    input  wire [4:0]    rcfg_mask,
    input  wire [7:0]    cfg_users,
    input  wire [15:0]   cfg_prompt_len,
    input  wire [15:0]   cfg_gen_len,
    input  wire [15:0]   cfg_lead,
    // prompt tokens (host interface), synchronous read
    output wire          pr_re,
    output wire [7:0]    pr_user,
    output wire [15:0]   pr_pos,
    input  wire [15:0]   pr_q,
    // HBM request / response (KV cache)
    output wire          hq_v,
    input  wire          hq_rdy,
    output wire          hq_we,
    output wire [23:0]   hq_addr,
    output wire [4:0]    hq_len,
    output wire [13:0]   hq_tag,
    output wire [255:0]  hq_wdata,
    input  wire [3:0]    hr_v,
    output wire [3:0]    hr_rdy,
    input  wire [4*14-1:0] hr_tag,
    input  wire [4*4-1:0]  hr_beat,
    input  wire [4*256-1:0] hr_data,
    // status
    output wire          tok_valid,
    output wire [7:0]    tok_user,
    output wire [15:0]   tok_pos,
    output wire [15:0]   tok_id,
    output wire [7:0]    users_done,
    output wire          core_busy,
    output wire          fault
);
    localparam integer W = 16, G = 4, IL = 8, AW = 24, NW = 16, PAW = 12, INSTR_BITS = 1024;
    localparam integer FLIT = 512;

    // -- decode core ------------------------------------------------------------------
    wire              start, done, core_fault;
    wire [NW-1:0]     token, pos, ntok;
    wire [31:0]       nval, cycles;
    wire              prog_re;  wire [PAW-1:0] prog_addr; wire [INSTR_BITS-1:0] prog_q;
    wire              wrom_re;  wire [AW-1:0]  wrom_addr; wire [G*W*16-1:0] wrom_q;
    wire              crom_re;  wire [AW-1:0]  crom_addr; wire [63:0] crom_q;
    wire              kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr;
    wire [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire [G-1:0]      vx_re; wire [G*AW-1:0] vx_addr; wire [G*32-1:0] vx_q;
    wire              va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
    wire [31:0]       va_q, vb_q, vc_q;
    wire [G-1:0]      vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask;
    wire [G*W*32-1:0] vw_me_data;
    wire              vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
    wire [31:0]       vw_su_data, vw_rd_data;
    wire              me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire              kvd_v;
    wire [AW-1:0]     kvd_wbase, kvd_ts, kvd_ks, kvd_js;
    wire [2:0]        kvd_jsh;
    wire [NW-1:0]     kvd_tiles, kvd_k, kvd_nout, kvd_pos;
    wire              kvd_kindk, kv_ok;

    ot_hdc_core #(.INSTR_BITS(INSTR_BITS), .W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .PAW(PAW),
                  .KV_HBM(1)) u_core (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(ntok), .next_val(nval), .cycles(cycles), .fault(core_fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok));

    // -- KV streaming engine and its window / tail SRAMs --------------------------------
    localparam integer LWIN = 8, TAW = 7;
    wire [G-1:0]      win_we; wire [G*LWIN-1:0] win_waddr; wire [G*W*16-1:0] win_wdata;
    wire              win_re; wire [LWIN-1:0] win_raddr; wire [G*W*16-1:0] win_q;
    wire [1:0]        tl_we, tl_re; wire [2*TAW-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask;
    wire [2*W*16-1:0] tl_wdata, tl_q;
    wire [AW-1:0]     hq_addr_core, kv_base;
    wire              kvs_fault;

    ot_hdc_kv_stream u_kvs (
        .clk(clk), .rst_n(rst_n), .tok_start(start), .tok_pos(pos), .cfg_lead(cfg_lead),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .win_we(win_we), .win_waddr(win_waddr), .win_wdata(win_wdata), .win_re(win_re),
        .win_raddr(win_raddr), .win_q(win_q),
        .tl_we(tl_we), .tl_waddr(tl_waddr), .tl_wmask(tl_wmask), .tl_wdata(tl_wdata), .tl_re(tl_re),
        .tl_raddr(tl_raddr), .tl_q(tl_q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_we(hq_we), .hq_addr(hq_addr_core), .hq_len(hq_len),
        .hq_tag(hq_tag), .hq_wdata(hq_wdata),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(kvs_fault));
    // The KV slice of the running user (the package controller's kv_base).
    assign hq_addr = hq_addr_core + kv_base;

    ot_mem_kvwin u_kvwin (
        .clk(clk), .we(win_we), .waddr(win_waddr), .wdata(win_wdata),
        .re(win_re), .raddr(win_raddr), .q(win_q));
    ot_mem_kvtail u_kvtail (
        .clk(clk), .we(tl_we), .waddr(tl_waddr), .wmask(tl_wmask), .wdata(tl_wdata),
        .re(tl_re), .raddr(tl_raddr), .q(tl_q));

    // -- program ROM, weight store, constant ROM ----------------------------------------
    ot_mem_prog u_prog (.clk(clk), .re(prog_re), .addr(prog_addr), .q(prog_q));
    ot_mem_wstore u_wstore (.clk(clk), .re(wrom_re), .addr(wrom_addr[WSA-1:0]), .q(wrom_q));
    ot_mem_crom u_crom (.clk(clk), .re(crom_re), .addr(crom_addr[11:0]), .q(crom_q));

    // -- package controller -------------------------------------------------------------
    wire              c_we, c_re; wire [7:0] c_waddr, c_raddr;
    wire [FLIT-1:0]   c_wdata, c_rq;
    wire              pc_in_valid, pc_in_ready, pc_in_last, pc_out_valid, pc_out_ready, pc_out_last;
    wire [FLIT-1:0]   pc_in_data, pc_out_data;
    wire              proto_fault;

    ot_chip_pkg_ctrl u_ctrl (
        .clk(clk), .rst_n(rst_n),
        .cfg_users(cfg_users), .cfg_prompt_len(cfg_prompt_len), .cfg_gen_len(cfg_gen_len),
        .in_valid(pc_in_valid), .in_ready(pc_in_ready), .in_data(pc_in_data), .in_last(pc_in_last),
        .out_valid(pc_out_valid), .out_ready(pc_out_ready), .out_data(pc_out_data), .out_last(pc_out_last),
        .core_start(start), .core_token(token), .core_pos(pos), .core_done(done),
        .core_next_token(ntok), .core_next_val(nval), .kv_base(kv_base),
        .vm_we(c_we), .vm_waddr(c_waddr), .vm_wdata(c_wdata), .vm_re(c_re), .vm_raddr(c_raddr), .vm_rq(c_rq),
        .pr_re(pr_re), .pr_user(pr_user), .pr_pos(pr_pos), .pr_q(pr_q),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(tok_user), .tok_pos(tok_pos),
        .tok_id(tok_id), .users_done(users_done), .proto_fault(proto_fault));

    // -- vector memory ------------------------------------------------------------------
    wire [G*VMA-1:0] vx_a;
    wire [G*(VMA-4)-1:0] me_wa;
    genvar q;
    generate
        for (q = 0; q < G; q = q + 1) begin : g_va
            assign vx_a[q*VMA +: VMA] = vx_addr[q*AW +: VMA];
            assign me_wa[q*(VMA-4) +: VMA-4] = vw_me_addr[q*AW +: VMA-4];
        end
    endgenerate
    ot_mem_vmem u_vmem (
        .clk(clk),
        .x_re(vx_re), .x_addr(vx_a), .x_q(vx_q),
        .a_re(va_re), .a_addr(va_addr[VMA-1:0]), .a_q(va_q),
        .b_re(vb_re), .b_addr(vb_addr[VMA-1:0]), .b_q(vb_q),
        .c_re(vc_re), .c_addr(vc_addr[VMA-1:0]), .c_q(vc_q),
        .me_we(vw_me_we), .me_addr(me_wa), .me_mask(vw_me_mask), .me_data(vw_me_data),
        .su_we(vw_su_we), .su_addr(vw_su_addr[VMA-1:0]), .su_data(vw_su_data),
        .rd_we(vw_rd_we), .rd_addr(vw_rd_addr[VMA-1:0]), .rd_data(vw_rd_data),
        .w_we(c_we), .w_addr({{(VMA-12){1'b0}}, c_waddr}), .w_data(c_wdata),
        .r_re(c_re), .r_addr({{(VMA-12){1'b0}}, c_raddr}), .r_q(c_rq));

    // -- fabric router --------------------------------------------------------------------
    wire [4:0]        r_in_valid, r_in_ready, r_in_credit, r_in_last, r_out_valid, r_out_ready, r_out_last;
    wire [5*FLIT-1:0] r_in_data, r_out_data;
    wire [31:0]       drops;
    wire              overflow;
    wire [3:0]        l_in_valid, l_in_last, l_in_ready, l_out_valid, l_out_last, l_out_ready, l_ovf;
    wire [4*FLIT-1:0] l_in_data, l_out_data;
    genvar p;
    generate
        for (p = 0; p < 4; p = p + 1) begin : g_link
            ot_chip_mesh_link_tx #(.W(FLIT), .STAGES(LINK_STAGES), .CREDITS(LINK_DEPTH)) u_tx (
                .clk(clk), .rst_n(rst_n),
                .in_valid(l_out_valid[p]), .in_ready(l_out_ready[p]), .in_data(l_out_data[p*FLIT +: FLIT]),
                .in_last(l_out_last[p]),
                .ch_valid(m_out_valid[p]), .ch_data(m_out_data[p*FLIT +: FLIT]), .ch_last(m_out_last[p]),
                .cr_ret(m_out_cr[p]));
            ot_chip_mesh_link_rx #(.W(FLIT), .IN_STAGES(LINK_STAGES), .RET_STAGES(LINK_STAGES), .DEPTH(LINK_DEPTH)) u_rx (
                .clk(clk), .rst_n(rst_n),
                .ch_valid(m_in_valid[p]), .ch_data(m_in_data[p*FLIT +: FLIT]), .ch_last(m_in_last[p]),
                .out_valid(l_in_valid[p]), .out_ready(l_in_ready[p]), .out_data(l_in_data[p*FLIT +: FLIT]),
                .out_last(l_in_last[p]), .cr_ret(m_in_cr[p]), .overflow(l_ovf[p]));
        end
    endgenerate
    assign r_in_valid  = {l_in_valid, pc_out_valid};
    assign r_in_data   = {l_in_data, pc_out_data};
    assign r_in_last   = {l_in_last, pc_out_last};
    assign pc_out_ready = r_in_ready[0];
    assign l_in_ready  = r_in_ready[4:1];
    assign pc_in_valid = r_out_valid[0];
    assign pc_in_data  = r_out_data[0 +: FLIT];
    assign pc_in_last  = r_out_last[0];
    assign r_out_ready = {l_out_ready, pc_in_ready};
    assign l_out_valid = r_out_valid[4:1];
    assign l_out_data  = r_out_data[FLIT +: 4*FLIT];
    assign l_out_last  = r_out_last[4:1];

    ot_chip_router u_router (
        .clk(clk), .rst_n(rst_n),
        .in_valid(r_in_valid), .in_ready(r_in_ready), .in_credit(r_in_credit), .in_data(r_in_data),
        .in_last(r_in_last), .out_valid(r_out_valid), .out_ready(r_out_ready), .out_data(r_out_data),
        .out_last(r_out_last), .cfg_we(rcfg_we), .cfg_dest(rcfg_dest), .cfg_mask(rcfg_mask),
        .drops(drops), .overflow(overflow));

    // -- status -----------------------------------------------------------------------
    reg fault_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_r <= 1'b0;
        else fault_r <= core_fault | kvs_fault | proto_fault | overflow | (|l_ovf);
    assign fault = fault_r;
endmodule
