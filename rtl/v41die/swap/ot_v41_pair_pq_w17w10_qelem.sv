// Experimental companion: PQ default off; no adoption or clock claim beyond its own screen.
// FILE SWAP of rtl/v41die/ot_v41_pair_pq_w17w10.sv (CLAUDE DS-INTEGRATION, 2026-10-05): the same module, with the
// DS q-element option of ot_v41_pair_w17w10 (QELEM / QXV) added, so the v9 field spine vehicle
// (ot_v41_fieldtop_pqc_w17w10) can run with the q-element on its FP8/FP4 pairs.  A source list names this file OR
// the original, never both; the original (pinned by the field_spine records) is unchanged.
//   QELEM defaults to `OT_PAIR_PQ_QELEM (0 when undefined: then this file elaborates exactly the original's logic).
//   QELEM != 0 with BF16 = 0 and PQ = 0: ot_v41_rom_elem_q_qx_w10 at the routed parameters ot_v41_pair_w17w10 uses
//     (QPIPE boundary registers, QZ / QY, QX = QXV); the PQ loader runs in its PQ = 0 mode, which never reads the
//     element's shadow / bank status (ld_ok = 1), so those inputs are tied to 1.  A BF16 go never starts it.
//   QELEM != 0 with PQ != 0: NOT BUILDABLE -- the q-element has no PQ shadow configuration, no op tag on its rows and
//     no segment-tree op parity (ot_v41_rom_elem_pq_w10's mechanism); elaboration stops with $fatal.
`ifndef OT_PAIR_PQ_QELEM
`define OT_PAIR_PQ_QELEM 0
`endif
`ifndef OT_PAIR_PQ_QXV
`define OT_PAIR_PQ_QXV 9
`endif
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_pair_pq_w17w10: SUCCESSOR of ot_v41_pair_w17w10 (DS-ROM recovery lever "field", 2026-10-04) on the PQ
// element ot_v41_rom_elem_pq_w10, its loader in ot_v41_pair_pq_ld.  PQ = 1: the next op's configuration is loaded
// into the element's shadow while the current op runs (held while the shadow is full or the tag bank drains); a
// `go` that finds its load not finished is a FAULT -- never a silent skip.  go_tag (the op's 2-bit tag) is passed
// to the element.  PQ = 0: identical to ot_v41_pair_w17w10.
//
// ot_v41_pair_w17w10: one ROM-field element of an experimental V4.1 FAST/PP runtime baseline (W17 die integration).
//
//   W10's ot_v41_rom_elem_w10 experimental baseline (NB = 2: a W1 macro pair sharing one front end, MTP,
//   fill cuts) + its per-element CONFIGURATION ROM and loader (root decision 2026-09-30 (b)).
//
// Configuration ROM.  Every phase the die runs has, for every element, the element's 3*NSEG+1 = 25
// configuration words (W10 ot_v41_rom_elem header: cfg_a 0..NSEG-1 segments, NSEG..2NSEG-1 classes,
// 2NSEG sub-blocks/positions, 2NSEG+1.. the second macro's rows), at entry ph*CW + a.  The spine
// broadcasts {cfg_go, cfg_ph}; every element then writes its CW words into its element on consecutive
// cycles (one ROM read a cycle, one register stage), in parallel across the field: a phase's
// configuration costs CW + 2 cycles regardless of the element count, and no configuration wire leaves
// the element.  The ROM is a mask ROM like the weights (tools/v41_die_images.py writes it).
//
// cfg_ph also carries the phase's positions - 1 (MTP) in the spine's broadcast; the ROM's word 2NSEG
// holds the sub-block count and the loader ORs the positions field in, so one ROM entry serves 1..6
// positions.
//
// Simulation: the ROM contents come from +OT_ROM_DIR=<dir>/<INSTANCE>.cfg.hex (flat builds) or, with V41_RT,
// are served by the runtime host through DPI (rtl/test/v41_runtime).
// ---------------------------------------------------------------------------
module ot_v41_pair_pq_w17w10 #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,
    parameter integer MTP = 1,
    parameter integer EARLY = 1,
    parameter integer FAST = 0,
    parameter integer PP = 0,
    parameter integer BP = 0,
    parameter integer PHW = 6,          // phase id bits: 2^PHW phases per die
    parameter integer PQ = 0,
    parameter integer QELEM = `OT_PAIR_PQ_QELEM,
    parameter integer QXV = `OT_PAIR_PQ_QXV,
    parameter INSTANCE = ""
) (
    input  wire         clk,
    input  wire         rst_n,
    // spine broadcast (after the broadcast wire stages)
    input  wire         cfg_go,
    input  wire [PHW-1:0] cfg_ph,
    input  wire [2:0]   cfg_np,         // positions - 1
    input  wire         go,
    input  wire         go_bf,
    input  wire [1:0]   go_tag,
    input  wire         xs_v,
    input  wire [7:0]   xs_p,
    input  wire [2:0]   xs_b,
    input  wire [1:0]   xs_sv,
    input  wire [255:0] xs_q0,
    input  wire [9:0]   xs_e0,
    input  wire [255:0] xs_q1,
    input  wire [9:0]   xs_e1,
    input  wire [2:0]   xs_pos,
    input  wire [2:0]   xb_pos,
    input  wire         xb_v,
    input  wire [2:0]   xb_b,
    input  wire [3:0]   xb_sv,
    input  wire [31:0]  xb_u,
    input  wire [1023:0] xb_d,
    // the two macros' partials (return-tree leaves 2g, 2g + 1)
    output wire [1:0]   pv,
    output wire [63:0]  pval,
    output wire [31:0]  prow,
    output wire [9:0]   pseg,
    output wire [9:0]   pnseg,
    output wire [1:0]   perr,
    output wire [5:0]   ppos,
    output wire         busy,
    output wire         fault,
    // quiet: no op in flight, no partial pending, no configuration load (the element's clock is gated): clocking
    // a quiet pair changes nothing until cfg_go or go (simulation host uses it to skip evaluations)
    output wire         quiet
);
    localparam integer CW = 3 * NSEG + 1;
    localparam integer DEPTH = CW << PHW;
    localparam integer AW = $clog2(DEPTH);
    // the configuration mask ROM (48-bit words)
`ifdef V41_RT
    // runtime composition: the host serves the words (keyed by the calling scope, registered at time 0)
    import "DPI-C" context function void v41rt_cfg_register();
    import "DPI-C" context function longint v41rt_cfg_read(input int addr);
    initial v41rt_cfg_register();
    function automatic [47:0] cmr(input [AW-1:0] a);
        cmr = 48'(v41rt_cfg_read(32'(a)));
    endfunction
`else
    reg [47:0] cm [0:DEPTH-1];
    reg [8*1024-1:0] rom_dir;
    integer ii;
    initial begin
        for (ii = 0; ii < DEPTH; ii = ii + 1) cm[ii] = 48'd0;
        if ($value$plusargs("OT_ROM_DIR=%s", rom_dir) && INSTANCE != "")
            $readmemh({rom_dir, "/", INSTANCE, ".cfg.hex"}, cm);
    end
    function automatic [47:0] cmr(input [AW-1:0] a);
        cmr = cm[a];
    endfunction
`endif
    // loader + PQ pending load + act (ot_v41_pair_pq_ld): ROM address -> registered word -> element configuration
    wire        c_v, go_e, pq_fault, ld_busy;
    wire [4:0]  c_a;
    wire [47:0] c_d;
    wire [AW-1:0] cm_a;
    wire        e_walking, e_bank_free, e_sh_free, e_fault;
    ot_v41_pair_pq_ld #(.NSEG(NSEG), .PHW(PHW), .PQ(PQ)) u_ld (.clk(clk), .rst_n(rst_n), .cfg_go(cfg_go),
        .cfg_ph(cfg_ph), .cfg_np(cfg_np), .go(go), .e_sh_free(e_sh_free), .e_bank_free(e_bank_free), .cm_a(cm_a),
        .cm_q(cmr(cm_a)), .c_v(c_v), .c_a(c_a), .c_d(c_d), .go_e(go_e), .ld_busy(ld_busy), .fault(pq_fault));
    wire e_busy;
    assign busy = e_busy;
    assign quiet = !e_busy && !ld_busy && !cfg_go && !(go && go_e);
    if (QELEM != 0 && BF16 == 0) begin : g_q
        if (PQ != 0) begin : g_bad
            $fatal(1, "ot_v41_pair_pq_w17w10 (swap): QELEM with PQ = 1 is not buildable (no PQ q-element)");
        end
        assign e_walking = 1'b0;
        assign e_bank_free = 1'b1;
        assign e_sh_free = 1'b1;
        ot_v41_rom_elem_q_qx_w10 #(.NB(2), .MTP(MTP), .EARLY(EARLY), .FAST(1), .PP(1), .FRONT_PAR(0), .QTIMING_FIX(1),
                                   .QPIPE(1), .QP_XS(1), .QP_CAP(0), .QP_P1(1), .QP_CSAM(10), .QZ(1), .QZ_NS(8),
                                   .QZ_NE(4), .QY(1), .QX(QXV), .INSTANCE(INSTANCE)) u_e (
            .clk(clk), .rst_n(rst_n), .cfg_v(c_v), .cfg_a(c_a), .cfg_d(c_d), .go(go_e && !go_bf),
            .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0),
            .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .pv(pv), .pval(pval), .prow(prow), .pseg(pseg),
            .pnseg(pnseg), .perr(perr), .ppos(ppos), .busy(e_busy), .fault(e_fault));
    end else begin : g_w
        ot_v41_rom_elem_pq_w10 #(.PQ(PQ), .NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NB(2), .MTP(MTP), .EARLY(EARLY),
                          .FAST(FAST), .PP(PP), .BP(BP), .FRONT_PAR(0), .INSTANCE(INSTANCE)) u_e (
            .clk(clk), .rst_n(rst_n), .cfg_v(c_v), .cfg_a(c_a), .cfg_d(c_d),
            .go(go_e), .go_bf(go_bf), .go_tag(go_tag), .walking(e_walking), .bank_free(e_bank_free), .sh_free(e_sh_free), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u), .xb_d(xb_d),
            .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0),
            .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .ppos(ppos),
            .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr),
            .busy(e_busy), .fault(e_fault));
    end
    assign fault = e_fault | pq_fault;
endmodule
