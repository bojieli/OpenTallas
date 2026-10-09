`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_sp_su64_sfu_bv (qwen-vm-me 2026-10-08): the re-cut stream-unit master of qwen-rtl-finish
// (ot_qfd_sp_su64_sfu_ab) with its vector-memory ports in the form the BANKED vector memory serves
// (ot_qfd_sp_vector_memory_bv):
//   reads    per operand (va / vb / vc) a descriptor {re0, re1, a0, a1}: lane 0's and lane 1's strobe and address (the
//            lane registers themselves, no logic before the pins; every lane l reads a0 + l * (a1 - a0) by construction
//            of ot_hdc_vstream_lane).  The memory answers all SW lanes 1 + VL edges after the strobe (VL = 7, dedicated
//            replica banks per operand); the lanes run at ML = max(IS + OS + CRX, VL) (ot_hdc_vstream_lane ML) and the
//            answer is delayed ML - VL here, the far constant ROM's ML - (IS + OS + CRX).  The embedding decode (the
//            row buffer, ot_qfd_su_embed_pf) answers its lanes one edge after the strobe; they are delayed ML and
//            selected per lane by the strobe mask (the lanes whose va strobe did not go to the memory).  A lane that
//            did not read keeps its previous answer (the base's registered, held-when-not-read port), 3 x SW x 32 flops.
//   writes   {mask = the lane write strobes, a0, a1 = lane 0 / lane 1 write addresses, data}; the reducer's scalar write.
// Everything else (control stations, constant ROM, embedding row buffer, KV write) is ot_qfd_sp_su64_sfu_ab's.  The SU
// element latency grows from IS + OS + CRX to ML (cost: ML - (IS + OS + CRX) edges per element; 3 at IS = OS = 1, CRX = 2).
// MUT = 1: flips constant-ROM bit 0 of lane 0 at the input station (as ot_qfd_sp_su64_sfu_ab).
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_sp_su64_sfu_bv #(
    parameter integer SW = 64,
    parameter integer LV = 7,
    parameter integer W = 16,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer KV_FP8 = 1,
    parameter integer IS = 1,
    parameter integer OS = 1,
    parameter integer CRX = 2,              // constant-ROM edges outside this master beyond the base's one
    parameter integer HID = 4096,
    parameter integer CRD = 4,
    parameter integer VL = 7,               // the banked vector memory's extra read latency (answer at 1 + VL)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    // control (stationed)
    input  wire              go,
    output wire              ready,
    output wire              idle,
    output wire              obs_active,
    output wire [7:0]        obs_inflight,
    input  wire [NW-1:0]     i_nout, i_nin,
    input  wire              i_asrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi,
    input  wire              i_bsrc,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_csrc,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire [1:0]        i_ma, i_mb,
    input  wire [2:0]        i_ad, i_sfu,
    input  wire              i_mc, i_md,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire [1:0]        i_red,
    input  wire              i_redsq,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2,
    input  wire              a_src,          // the embedding selector (po_su_asrc_raw)
    input  wire [NW-1:0]     tok,            // the token (static from the token start)
    output wire [15:0]       progress,
    output wire [15:0]       progress_rows,
    output wire              fault,
    // banked vector memory (abutted, no stations): operand o = 0 a, 1 b, 2 c
    output wire [2:0]        s_re0,
    output wire [2:0]        s_re1,
    output wire [3*AW-1:0]   s_a0,
    output wire [3*AW-1:0]   s_a1,
    input  wire [3*SW*32-1:0] s_q,
    output wire [SW-1:0]     sw_mask,
    output wire [AW-1:0]     sw_a0,
    output wire [AW-1:0]     sw_a1,
    output wire [SW*32-1:0]  sw_data,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    // KV write (posted, stationed) and its copy for the controller's flush
    output wire [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    // constant ROM across the channel (stationed; answers 1 + CRX edges after the far strobe)
    output wire [SW-1:0]     crom_re,
    output wire [SW*AW-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    // embedding ROM (stationed both ways)
    output wire              ea_v,
    output wire              ea_kind,
    output wire [AW-1:0]     ea_addr,
    input  wire              ea_cr,
    input  wire              eq_v,
    input  wire [511:0]      eq_data,
    output wire              wrom_fault
);
    localparam integer MC = OS + IS + CRX;
    localparam integer ML = (VL > MC) ? VL : MC;
    localparam integer FI = 2*NW + 1 + 3*AW + 1 + 3*AW + 1 + 3*AW + 2 + 2 + 3 + 3 + 1 + 1 + 2 + 3*AW + 2 + 1 + 2*AW + 64;
    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    // ---- input stations ----
    wire [FI-1:0] f_d = {i_nout, i_nin, i_asrc, i_abase, i_aso, i_asi, i_bsrc, i_bbase, i_bso, i_bsi, i_csrc, i_cbase,
                         i_cso, i_csi, i_ma, i_mb, i_ad, i_sfu, i_mc, i_md, i_dst, i_dbase, i_dso, i_dsi, i_red,
                         i_redsq, i_rbase, i_rso, i_imm1, i_imm2};
    wire [FI-1:0] f_q, f_go;
    wire go_q, asrc_q, cr_q, eqv_q, go_s;
    wire [NW-1:0] tok_q;
    wire [511:0] eqd_q;
    wire [SW*64-1:0] crq_q, crq_q0;
    wire [SW*64-1:0] crom_m = (MUT != 0) ? (crom_q ^ {{(SW*64-1){1'b0}}, 1'b1}) : crom_q;
    ot_hdc_delay #(.W(FI + NW + SW*64 + 512), .D(IS)) u_if (.clk(clk), .rst_n(rst_n),
        .d({f_d, tok, crom_m, eq_data}), .q({f_q, tok_q, crq_q0, eqd_q}));
    ot_hdc_delay #(.W(SW*64), .D(ML - MC)) u_crl (.clk(clk), .rst_n(rst_n), .d(crq_q0), .q(crq_q));
    ot_hdc_delay #(.W(4), .D(IS), .RESET(1)) u_ig (.clk(clk), .rst_n(rst_n), .d({go, a_src, ea_cr, eq_v}),
        .q({go_q, asrc_q, cr_q, eqv_q}));
    // ---- embedding row buffer + decode; the go is held while a row is fetched ----
    wire [SW-1:0] s_va_re, e_va_re;
    wire [SW*AW-1:0] s_va_addr, e_va_addr;
    wire [SW*32-1:0] e_va_q;
    wire e_pend, e_fault, e_v, e_kind;
    wire [AW-1:0] e_addr;
    ot_qfd_su_embed_pf #(.SW(SW), .AW(AW), .NW(NW), .HID(HID), .CRD(CRD), .FI(FI)) u_emb (
        .clk(clk), .rst_n(rs), .go_in(go_q), .a_src(asrc_q), .tok(tok_q), .f_in(f_q), .go_out(go_s), .f_out(f_go),
        .pend(e_pend), .su_va_re(s_va_re), .su_va_addr(s_va_addr), .su_va_q(e_va_q), .va_re(e_va_re),
        .va_addr(e_va_addr), .va_q({(SW*32){1'b0}}), .ea_v(e_v), .ea_kind(e_kind), .ea_addr(e_addr), .ea_cr(cr_q),
        .eq_v(eqv_q), .eq_data(eqd_q), .fault(e_fault));
    // ---- descriptors to the banked memory (lane 0 / lane 1 registers) ----
    wire [SW-1:0] vb_re, vc_re;
    wire [SW*AW-1:0] vb_addr, vc_addr;
    assign s_re0 = {vc_re[0], vb_re[0], e_va_re[0]};
    assign s_re1 = {vc_re[1], vb_re[1], e_va_re[1]};
    assign s_a0 = {vc_addr[0 +: AW], vb_addr[0 +: AW], e_va_addr[0 +: AW]};
    assign s_a1 = {vc_addr[AW +: AW], vb_addr[AW +: AW], e_va_addr[AW +: AW]};
    // ---- answers: the memory's at 1 + VL, the embedding decode's at 1: both to 1 + ML ----
    reg  [SW-1:0] emb_sel;                             // lanes whose va strobe went to the embedding decode
    always @(posedge clk) emb_sel <= s_va_re & ~e_va_re;
    wire [SW-1:0] emb_sel_m;
    wire [SW*32-1:0] emb_m, vaq_v, vbq_m, vcq_m;
    ot_hdc_delay #(.W(SW + SW*32), .D(ML)) u_eml (.clk(clk), .rst_n(rst_n), .d({emb_sel, e_va_q}), .q({emb_sel_m, emb_m}));
    wire [3*SW*32-1:0] vq_new;
    ot_hdc_delay #(.W(3*SW*32), .D(ML - VL)) u_vml (.clk(clk), .rst_n(rst_n), .d(s_q), .q(vq_new));
    // the base port contract: a lane's registered answer HOLDS when the lane did not read (the memory answers every
    // lane of a descriptor; the lanes that did not strobe keep their previous value, so the lane datapath sees the
    // base's sequence of values, ML edges later)
    reg  [3*SW-1:0] vm_m1;
    always @(posedge clk) vm_m1 <= {vc_re, vb_re, e_va_re};
    wire [3*SW-1:0] vm_mk;
    ot_hdc_delay #(.W(3*SW), .D(ML), .RESET(1)) u_vmk (.clk(clk), .rst_n(rst_n), .d(vm_m1), .q(vm_mk));
    reg  [3*SW*32-1:0] vq_hold;
    wire [3*SW*32-1:0] vq_eff;
    genvar gl;
    generate for (gl = 0; gl < 3*SW; gl = gl + 1) begin : g_hold
        assign vq_eff[gl*32 +: 32] = vm_mk[gl] ? vq_new[gl*32 +: 32] : vq_hold[gl*32 +: 32];
    end endgenerate
    always @(posedge clk) vq_hold <= vq_eff;
    assign {vcq_m, vbq_m, vaq_v} = vq_eff;
    wire [SW*32-1:0] vaq_m;
    generate for (gl = 0; gl < SW; gl = gl + 1) begin : g_amux
        assign vaq_m[gl*32 +: 32] = emb_sel_m[gl] ? emb_m[gl*32 +: 32] : vaq_v[gl*32 +: 32];
    end endgenerate
    wire [NW-1:0] q_nout, q_nin;
    wire q_asrc, q_bsrc, q_csrc, q_mc, q_md, q_redsq;
    wire [AW-1:0] q_abase, q_aso, q_asi, q_bbase, q_bso, q_bsi, q_cbase, q_cso, q_csi, q_dbase, q_dso, q_dsi, q_rbase, q_rso;
    wire [1:0] q_ma, q_mb, q_dst, q_red;
    wire [2:0] q_ad, q_sfu;
    wire [31:0] q_imm1, q_imm2;
    assign {q_nout, q_nin, q_asrc, q_abase, q_aso, q_asi, q_bsrc, q_bbase, q_bso, q_bsi, q_csrc, q_cbase,
            q_cso, q_csi, q_ma, q_mb, q_ad, q_sfu, q_mc, q_md, q_dst, q_dbase, q_dso, q_dsi, q_red,
            q_redsq, q_rbase, q_rso, q_imm1, q_imm2} = f_go;
    wire s_ready, s_idle, s_fault, s_wrom_re, s_active;
    wire [7:0] s_inflight;
    wire [SW-1:0] s_crom_re, s_kv_we;
    wire [SW*AW-1:0] s_crom_addr, s_kv_waddr;
    wire [SW*32-1:0] s_kv_wdata;
    wire [AW-1:0] s_wrom_addr;
    wire [SW*AW-1:0] vm_waddr;
    assign sw_a0 = vm_waddr[0 +: AW];
    assign sw_a1 = vm_waddr[AW +: AW];
    wire [15:0] s_progress, s_rows;
    ot_hdc_vstream #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8), .ML(ML)) u_su (
        .clk(clk), .rst_n(rs), .go(go_s), .ready(s_ready), .idle(s_idle),
        .i_nout(q_nout), .i_nin(q_nin),
        .i_asrc(q_asrc), .i_abase(q_abase), .i_aso(q_aso), .i_asi(q_asi),
        .i_bsrc(q_bsrc), .i_bbase(q_bbase), .i_bso(q_bso), .i_bsi(q_bsi),
        .i_csrc(q_csrc), .i_cbase(q_cbase), .i_cso(q_cso), .i_csi(q_csi),
        .i_ma(q_ma), .i_mb(q_mb), .i_ad(q_ad), .i_sfu(q_sfu), .i_mc(q_mc), .i_md(q_md),
        .i_dst(q_dst), .i_dbase(q_dbase), .i_dso(q_dso), .i_dsi(q_dsi),
        .i_red(q_red), .i_redsq(q_redsq), .i_rbase(q_rbase), .i_rso(q_rso), .i_imm1(q_imm1), .i_imm2(q_imm2),
        .va_re(s_va_re), .va_addr(s_va_addr), .va_q(vaq_m),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vbq_m),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vcq_m),
        .wrom_re(s_wrom_re), .wrom_addr(s_wrom_addr), .wrom_q({(W*16){1'b0}}),
        .crom_re(s_crom_re), .crom_addr(s_crom_addr), .crom_q(crq_q),
        .vm_we(sw_mask), .vm_waddr(vm_waddr), .vm_wdata(sw_data),
        .kv_we(s_kv_we), .kv_waddr(s_kv_waddr), .kv_wdata(s_kv_wdata),
        .red_we(red_we), .red_addr(red_addr), .red_data(red_data),
        .progress(s_progress), .progress_rows(s_rows), .fault(s_fault),
        .obs_active(s_active), .obs_inflight(s_inflight));
    // ---- output stations ----
    localparam integer FS = 1 + 1 + 1 + 8 + 1 + 1 + 1 + 1 + SW + SW + 32;
    localparam integer FD = SW*AW + SW*AW + SW*32 + AW;
    ot_hdc_delay #(.W(FS), .D(OS), .RESET(1)) u_os (.clk(clk), .rst_n(rst_n),
        .d({s_ready && !e_pend, s_idle && !e_pend, s_active || e_pend, s_inflight, s_fault || e_fault, s_wrom_re,
            e_v, e_kind, s_crom_re, s_kv_we, s_progress, s_rows}),
        .q({ready, idle, obs_active, obs_inflight, fault, wrom_fault, ea_v, ea_kind, crom_re, kv_we, progress,
            progress_rows}));
    ot_hdc_delay #(.W(FD), .D(OS)) u_od (.clk(clk), .rst_n(rst_n),
        .d({s_crom_addr, s_kv_waddr, s_kv_wdata, e_addr}), .q({crom_addr, kv_waddr, kv_wdata, ea_addr}));
endmodule
