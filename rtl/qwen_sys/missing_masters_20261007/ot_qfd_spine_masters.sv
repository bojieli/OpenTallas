`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Qwen3-8B ROM die spine masters that the r21 die generator only reserved (qwen-missing 2026-10-07).
// Physical masters: each is the RTL that implements the function in the token bench today, wrapped with
// registered pin stations on every port (owner rule: register every block boundary, ~700 ps stages).
//
//   ot_qfd_sp_su64_sfu            die master qfd_sp_su64_sfu: the vector stream unit ot_hdc_vstream
//                                 (SW = 64 lanes, LV = 7, KV FP8) -- the u_su of ot_qwen_rom_core, whose lanes hold
//                                 the SFU (ot_hdc_vstream_lane i_sfu) -- with IS input and OS output stations.
//   ot_qfd_sp_constants_sequencer die master qfd_sp_constants_sequencer: the core controller ot_qwen_rom_core_ctrl
//                                 (fetch / decode / DYN / issue / argmax fold / engine clock gate / INT8 embedding
//                                 decode; tools/qwen_missing/emit_partition.py), the TP sequencer ot_qwen_tp_seq_w12,
//                                 the program ROM (64 x 1,024 b) and the segment-descriptor ROM (8 x 64 b), with IS /
//                                 OS stations.  The constant ROM (543,233 x 64 b, 64 lane read ports in the RTL) is
//                                 NOT in this master: its 64-port read is an RTL idealisation that needs a banking
//                                 contract (like the vector memory's), see results/rtl/qwen_missing_masters_20261007.
//
// Station semantics: every input is delayed IS cycles and every output OS cycles (ot_hdc_delay; data lines carry no
// reset, valid / strobe / go lines are reset lines), and reset is released IS cycles late (ot_qfd_rst_stn), so the
// master is cycle-for-cycle the bare RTL slice shifted by IS + OS (tb_qfd_spine_masters checks this, with a mutant).
// The shift is a closure cost on the loops that cross the boundary (issue ready/go, memory read data, progress /
// idle): priced in results/rtl/qwen_missing_masters_20261007 and the Qwen closure-cost ledger.  IS = OS = 0 is the
// bare slice (the partition bench tools/qwen_missing/partition_token.py runs the die on the same three slices).
// ---------------------------------------------------------------------------

// reset copy: asserts with rst_n (asynchronously), releases D edges later
module ot_qfd_rst_stn #(parameter integer D = 1) (
    input  wire clk,
    input  wire rst_n,
    output wire rst_q
);
    generate if (D == 0) begin : g_w
        assign rst_q = rst_n;
    end else begin : g_r
        reg [D-1:0] r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r <= {D{1'b0}};
            else r <= {r, 1'b1};
        assign rst_q = r[D-1];
    end endgenerate
endmodule


module ot_qfd_sp_su64_sfu #(
    parameter integer SW = 64,
    parameter integer LV = 7,
    parameter integer W = 16,
    parameter integer AW = 24,
    parameter integer NW = 18,
    parameter integer KV_FP8 = 1,
    parameter integer IS = 1,
    parameter integer OS = 1,
    parameter integer MUT = 0          // bench mutant: drop lane 0's va_q bit 0 at the input station
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
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
    output wire [SW-1:0]     va_re,
    output wire [SW*AW-1:0]  va_addr,
    input  wire [SW*32-1:0]  va_q,
    output wire [SW-1:0]     vb_re,
    output wire [SW*AW-1:0]  vb_addr,
    input  wire [SW*32-1:0]  vb_q,
    output wire [SW-1:0]     vc_re,
    output wire [SW*AW-1:0]  vc_addr,
    input  wire [SW*32-1:0]  vc_q,
    output wire [SW-1:0]     crom_re,
    output wire [SW*AW-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    output wire [SW-1:0]     vm_we,
    output wire [SW*AW-1:0]  vm_waddr,
    output wire [SW*32-1:0]  vm_wdata,
    output wire [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    output wire [15:0]       progress,
    output wire [15:0]       progress_rows,
    output wire              fault,
    output wire              wrom_fault       // the stream unit's weight-ROM port is unused on the ROM die (INT8 embedding)
);
    localparam integer FI = 2*NW + 1 + 3*AW + 1 + 3*AW + 1 + 3*AW + 2 + 2 + 3 + 3 + 1 + 1 + 2 + 3*AW + 2 + 1 + 2*AW + 64;
    wire rs;
    ot_qfd_rst_stn #(.D(IS)) u_rs (.clk(clk), .rst_n(rst_n), .rst_q(rs));
    // ---- input stations ----
    wire [FI-1:0] f_d = {i_nout, i_nin, i_asrc, i_abase, i_aso, i_asi, i_bsrc, i_bbase, i_bso, i_bsi, i_csrc, i_cbase,
                         i_cso, i_csi, i_ma, i_mb, i_ad, i_sfu, i_mc, i_md, i_dst, i_dbase, i_dso, i_dsi, i_red,
                         i_redsq, i_rbase, i_rso, i_imm1, i_imm2};
    wire [FI-1:0] f_q;
    wire          go_q;
    wire [SW*32-1:0] vaq_q, vbq_q, vcq_q;
    wire [SW*64-1:0] crq_q;
    wire [SW*32-1:0] va_m = (MUT != 0) ? (va_q ^ {{(SW*32-1){1'b0}}, 1'b1}) : va_q;
    ot_hdc_delay #(.W(FI), .D(IS)) u_if (.clk(clk), .rst_n(rst_n), .d(f_d), .q(f_q));
    ot_hdc_delay #(.W(1), .D(IS), .RESET(1)) u_ig (.clk(clk), .rst_n(rst_n), .d(go), .q(go_q));
    ot_hdc_delay #(.W(3*SW*32 + SW*64), .D(IS)) u_iq (.clk(clk), .rst_n(rst_n), .d({va_m, vb_q, vc_q, crom_q}),
        .q({vaq_q, vbq_q, vcq_q, crq_q}));
    wire [NW-1:0] q_nout, q_nin;
    wire q_asrc, q_bsrc, q_csrc, q_mc, q_md, q_redsq;
    wire [AW-1:0] q_abase, q_aso, q_asi, q_bbase, q_bso, q_bsi, q_cbase, q_cso, q_csi, q_dbase, q_dso, q_dsi, q_rbase, q_rso;
    wire [1:0] q_ma, q_mb, q_dst, q_red;
    wire [2:0] q_ad, q_sfu;
    wire [31:0] q_imm1, q_imm2;
    assign {q_nout, q_nin, q_asrc, q_abase, q_aso, q_asi, q_bsrc, q_bbase, q_bso, q_bsi, q_csrc, q_cbase,
            q_cso, q_csi, q_ma, q_mb, q_ad, q_sfu, q_mc, q_md, q_dst, q_dbase, q_dso, q_dsi, q_red,
            q_redsq, q_rbase, q_rso, q_imm1, q_imm2} = f_q;
    // ---- the stream unit ----
    wire s_ready, s_idle, s_red_we, s_fault, s_wrom_re;
    wire [SW-1:0] s_va_re, s_vb_re, s_vc_re, s_crom_re, s_vm_we, s_kv_we;
    wire [SW*AW-1:0] s_va_addr, s_vb_addr, s_vc_addr, s_crom_addr, s_vm_waddr, s_kv_waddr;
    wire [SW*32-1:0] s_vm_wdata, s_kv_wdata;
    wire [AW-1:0] s_red_addr, s_wrom_addr;
    wire [31:0] s_red_data;
    wire [15:0] s_progress, s_rows;
    ot_hdc_vstream #(.SW(SW), .LV(LV), .WR(W), .AW(AW), .NW(NW), .KV_FP8(KV_FP8)) u_su (
        .clk(clk), .rst_n(rs), .go(go_q), .ready(s_ready), .idle(s_idle),
        .i_nout(q_nout), .i_nin(q_nin),
        .i_asrc(q_asrc), .i_abase(q_abase), .i_aso(q_aso), .i_asi(q_asi),
        .i_bsrc(q_bsrc), .i_bbase(q_bbase), .i_bso(q_bso), .i_bsi(q_bsi),
        .i_csrc(q_csrc), .i_cbase(q_cbase), .i_cso(q_cso), .i_csi(q_csi),
        .i_ma(q_ma), .i_mb(q_mb), .i_ad(q_ad), .i_sfu(q_sfu), .i_mc(q_mc), .i_md(q_md),
        .i_dst(q_dst), .i_dbase(q_dbase), .i_dso(q_dso), .i_dsi(q_dsi),
        .i_red(q_red), .i_redsq(q_redsq), .i_rbase(q_rbase), .i_rso(q_rso), .i_imm1(q_imm1), .i_imm2(q_imm2),
        .va_re(s_va_re), .va_addr(s_va_addr), .va_q(vaq_q),
        .vb_re(s_vb_re), .vb_addr(s_vb_addr), .vb_q(vbq_q),
        .vc_re(s_vc_re), .vc_addr(s_vc_addr), .vc_q(vcq_q),
        .wrom_re(s_wrom_re), .wrom_addr(s_wrom_addr), .wrom_q({(W*16){1'b0}}),
        .crom_re(s_crom_re), .crom_addr(s_crom_addr), .crom_q(crq_q),
        .vm_we(s_vm_we), .vm_waddr(s_vm_waddr), .vm_wdata(s_vm_wdata),
        .kv_we(s_kv_we), .kv_waddr(s_kv_waddr), .kv_wdata(s_kv_wdata),
        .red_we(s_red_we), .red_addr(s_red_addr), .red_data(s_red_data),
        .progress(s_progress), .progress_rows(s_rows), .fault(s_fault));
    // ---- output stations: strobes / status on reset lines, addresses and data plain ----
    localparam integer FS = 2 + 4*SW + SW + SW + 1 + 1 + 1 + 32;
    localparam integer FD = 4*SW*AW + SW*AW + SW*32 + SW*AW + SW*32 + AW + 32;
    ot_hdc_delay #(.W(FS), .D(OS), .RESET(1)) u_os (.clk(clk), .rst_n(rst_n),
        .d({s_ready, s_idle, s_va_re, s_vb_re, s_vc_re, s_crom_re, s_vm_we, s_kv_we, s_red_we, s_fault, s_wrom_re,
            s_progress, s_rows}),
        .q({ready, idle, va_re, vb_re, vc_re, crom_re, vm_we, kv_we, red_we, fault, wrom_fault, progress,
            progress_rows}));
    ot_hdc_delay #(.W(FD), .D(OS)) u_od (.clk(clk), .rst_n(rst_n),
        .d({s_va_addr, s_vb_addr, s_vc_addr, s_crom_addr, s_vm_waddr, s_vm_wdata, s_kv_waddr, s_kv_wdata, s_red_addr,
            s_red_data}),
        .q({va_addr, vb_addr, vc_addr, crom_addr, vm_waddr, vm_wdata, kv_waddr, kv_wdata, red_addr,
            red_data}));
endmodule
