`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Physical tile of the DeepSeek-V4.1 universal die
// (docs/FULL_CHIP_IMPLEMENTATION.md): one mesh node holding the V4.1 decode
// core (ot_hdc_core_v41: the sequencer, the matrix engine ME -- the same
// ot_hdc_matvec macro as the HDC tile -- the four-operand stream unit SU, the
// quantised block-dot engine QE, the select / Sinkhorn / Engram unit XU and
// the hyper-connection projection HE), the package controller, a 5-port
// router with pipelined credit links on its four mesh ports, and the core's
// memories as macros:
//
//   weight ROMs    wrom (BF16 matrices), ewrom (embedding rows), qrom (FP8/FP4
//                  block weights, the bulk), hrom (FP32 HC projections),
//                  erom (Engram table rows) -- via-programmed, personalised
//                  per die by the via mask; the layout is the same on every die
//   program ROM, constant ROMs (4 stream ports + 1 auxiliary)
//   KV SRAM        the core's KV port (the V4.1 core has no streaming
//                  interface yet; the die-level HBM path is future RTL)
//   vector memory  the core's 19 read / 7 write ports
//
// The collective engines (MoE dispatch / combine / expert port, argmax,
// multicast) are fabric endpoints of the die (rtl/chip/ot_chip_v41_die2x2.sv),
// not of this tile.
// ---------------------------------------------------------------------------
module ot_chip_v41_tile #(
    parameter integer VMA = 14,          // vector-memory element address bits
    parameter integer WSA = 17,          // weight-ROM word address bits
    parameter integer LINK_STAGES = 3,
    parameter integer LINK_DEPTH  = 12
) (
    input  wire          clk,
    input  wire          rst_n,
    output wire [3:0]    m_out_valid,
    output wire [4*512-1:0] m_out_data,
    output wire [3:0]    m_out_last,
    input  wire [3:0]    m_out_cr,
    input  wire [3:0]    m_in_valid,
    input  wire [4*512-1:0] m_in_data,
    input  wire [3:0]    m_in_last,
    output wire [3:0]    m_in_cr,
    input  wire          rcfg_we,
    input  wire [7:0]    rcfg_dest,
    input  wire [4:0]    rcfg_mask,
    input  wire [7:0]    cfg_users,
    input  wire [15:0]   cfg_prompt_len,
    input  wire [15:0]   cfg_gen_len,
    output wire          pr_re,
    output wire [7:0]    pr_user,
    output wire [15:0]   pr_pos,
    input  wire [15:0]   pr_q,
    output wire          tok_valid,
    output wire [7:0]    tok_user,
    output wire [15:0]   tok_pos,
    output wire [15:0]   tok_id,
    output wire [7:0]    users_done,
    output wire          core_busy,
    output wire          fault
);
    localparam integer W = 16, G = 4, AW = 24, NW = 16, PAW = 14, INSTR_BITS = 1536;
    localparam integer BL = 16, QLB = 272, HNL = 3, FLIT = 512;

    wire              start, done, core_fault;
    wire [NW-1:0]     token, pos, ntok;
    wire [31:0]       nval, cycles;
    wire              prog_re;  wire [PAW-1:0] prog_addr; wire [INSTR_BITS-1:0] prog_q;
    wire              wrom_re, ewrom_re, hrom_re, qrom_re, erom_re, xcrom_re;
    wire [AW-1:0]     wrom_addr, ewrom_addr, hrom_addr, qrom_addr, erom_addr, xcrom_addr;
    wire [G*W*16-1:0] wrom_q, ewrom_q;
    wire [HNL*32-1:0] hrom_q;
    wire [BL*QLB-1:0] qrom_q;
    wire [263:0]      erom_q;
    wire [3:0]        crom_re; wire [4*AW-1:0] crom_addr; wire [4*64-1:0] crom_q;
    wire [63:0]       xcrom_q;
    wire              kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr;
    wire [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire [G-1:0]      vx_re; wire [G*AW-1:0] vx_addr; wire [G*32-1:0] vx_q;
    wire [3:0]        vs_re; wire [4*AW-1:0] vs_addr; wire [4*32-1:0] vs_q;
    wire              vi_re, vq_re, vr_re, vh_re, wqr_re, wxr_re;
    wire [AW-1:0]     vi_addr, vq_addr, vr_addr, vh_addr, wqr_addr, wxr_addr;
    wire [31:0]       vi_q, vq_q, vr_q, vh_q;
    wire [1023:0]     wqr_q, wxr_q;
    wire [G-1:0]      vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask;
    wire [G*W*32-1:0] vw_me_data;
    wire              vw_su_we, vw_rd_we, vw_xe_we;
    wire [AW-1:0]     vw_su_addr, vw_rd_addr, vw_xe_addr;
    wire [31:0]       vw_su_data, vw_rd_data, vw_xe_data;
    wire              ww_q_we, ww_h_we, ww_x_we;
    wire [AW-1:0]     ww_q_addr, ww_h_addr, ww_x_addr;
    wire [31:0]       ww_q_mask, ww_h_mask, ww_x_mask;
    wire [1023:0]     ww_q_data, ww_h_data, ww_x_data;
    wire              me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [4:0]        unit_busy; wire [2:0] issue_unit;

    ot_hdc_core_v41 u_core (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(ntok), .next_val(nval), .cycles(cycles), .fault(core_fault),
        .prime_v(1'b0), .prime_first(1'b0), .prime_cid(12'd0),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
        .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q),
        .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
        .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q),
        .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q),
        .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
        .vh_re(vh_re), .vh_addr(vh_addr), .vh_q(vh_q),
        .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit));

    // -- ROMs ----------------------------------------------------------------------------
    ot_m41_prog  u_prog  (.clk(clk), .re(prog_re), .addr(prog_addr[11:0]), .q(prog_q));
    ot_m41_wrom  u_wrom  (.clk(clk), .re(wrom_re), .addr(wrom_addr[WSA-1:0]), .q(wrom_q));
    ot_m41_ewrom u_ewrom (.clk(clk), .re(ewrom_re), .addr(ewrom_addr[WSA-1:0]), .q(ewrom_q));
    ot_m41_hrom  u_hrom  (.clk(clk), .re(hrom_re), .addr(hrom_addr[15:0]), .q(hrom_q));
    ot_m41_qrom  u_qrom  (.clk(clk), .re(qrom_re), .addr(qrom_addr[WSA-1:0]), .q(qrom_q));
    ot_m41_erom  u_erom  (.clk(clk), .re(erom_re), .addr(erom_addr[WSA-1:0]), .q(erom_q));
    wire [4*12-1:0] crom_a;
    genvar c;
    generate for (c = 0; c < 4; c = c + 1) begin : g_ca
        assign crom_a[c*12 +: 12] = crom_addr[c*AW +: 12];
    end endgenerate
    ot_m41_crom  u_crom  (.clk(clk), .re(crom_re), .addr(crom_a), .q(crom_q),
                          .xre(xcrom_re), .xaddr(xcrom_addr[11:0]), .xq(xcrom_q));

    // -- KV SRAM ------------------------------------------------------------------------
    wire [G*12-1:0] kv_ra;
    generate for (c = 0; c < G; c = c + 1) begin : g_kva
        assign kv_ra[c*12 +: 12] = kv_raddr[c*AW +: 12];
    end endgenerate
    ot_m41_kv u_kv (.clk(clk), .re(kv_re), .raddr(kv_ra), .q(kv_q),
                    .we(kv_we), .waddr(kv_waddr[15:0]), .wdata(kv_wdata));

    // -- package controller -------------------------------------------------------------
    wire              c_we, c_re; wire [7:0] c_waddr, c_raddr;
    wire [FLIT-1:0]   c_wdata, c_rq;
    wire              pc_in_valid, pc_in_ready, pc_in_last, pc_out_valid, pc_out_ready, pc_out_last;
    wire [FLIT-1:0]   pc_in_data, pc_out_data;
    wire [AW-1:0]     kv_base;
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
    function automatic [VMA-1:0] ea(input [AW-1:0] a); ea = a[VMA-1:0]; endfunction
    wire [G*VMA-1:0] vx_a; wire [4*VMA-1:0] vs_a; wire [G*(VMA-4)-1:0] me_wa;
    generate for (c = 0; c < 4; c = c + 1) begin : g_vma
        assign vx_a[c*VMA +: VMA] = vx_addr[c*AW +: VMA];
        assign vs_a[c*VMA +: VMA] = vs_addr[c*AW +: VMA];
        assign me_wa[c*(VMA-4) +: VMA-4] = vw_me_addr[c*AW +: VMA-4];
    end endgenerate
    ot_m41_vmem u_vmem (
        .clk(clk),
        .x_re(vx_re), .x_addr(vx_a), .x_q(vx_q),
        .s_re(vs_re), .s_addr(vs_a), .s_q(vs_q),
        .i_re(vi_re), .i_addr(ea(vi_addr)), .i_q(vi_q),
        .q_re(vq_re), .q_addr(ea(vq_addr)), .q_q(vq_q),
        .r_re(vr_re), .r_addr(ea(vr_addr)), .r_q(vr_q),
        .h_re(vh_re), .h_addr(ea(vh_addr)), .h_q(vh_q),
        .wq_re(wqr_re), .wq_addr(ea(wqr_addr)), .wq_q(wqr_q),
        .wx_re(wxr_re), .wx_addr(ea(wxr_addr)), .wx_q(wxr_q),
        .me_we(vw_me_we), .me_addr(me_wa), .me_mask(vw_me_mask), .me_data(vw_me_data),
        .su_we(vw_su_we), .su_addr(ea(vw_su_addr)), .su_data(vw_su_data),
        .rd_we(vw_rd_we), .rd_addr(ea(vw_rd_addr)), .rd_data(vw_rd_data),
        .xe_we(vw_xe_we), .xe_addr(ea(vw_xe_addr)), .xe_data(vw_xe_data),
        .qw_we(ww_q_we), .qw_addr(ea(ww_q_addr)), .qw_mask(ww_q_mask), .qw_data(ww_q_data),
        .hw_we(ww_h_we), .hw_addr(ea(ww_h_addr)), .hw_mask(ww_h_mask), .hw_data(ww_h_data),
        .xw_we(ww_x_we), .xw_addr(ea(ww_x_addr)), .xw_mask(ww_x_mask), .xw_data(ww_x_data),
        .w_we(c_we), .w_addr({{(VMA-12){1'b0}}, c_waddr}), .w_data(c_wdata),
        .r_re2(c_re), .r_addr2({{(VMA-12){1'b0}}, c_raddr}), .r_q2(c_rq));

    // -- router and mesh links (as in ot_chip_hdc_tile) ----------------------------------
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
            ot_chip_mesh_link_rx #(.W(FLIT), .IN_STAGES(LINK_STAGES), .RET_STAGES(LINK_STAGES),
                                   .DEPTH(LINK_DEPTH)) u_rx (
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

    reg fault_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault_r <= 1'b0;
        else fault_r <= core_fault | proto_fault | overflow | (|l_ovf);
    assign fault = fault_r;
endmodule
