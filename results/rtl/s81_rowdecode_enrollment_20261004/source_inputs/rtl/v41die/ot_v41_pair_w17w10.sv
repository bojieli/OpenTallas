// Experimental companion: FAST/PP/BP default off; no adoption or clock claim.
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
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
module ot_v41_pair_w17w10 #(
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
    // loader: ROM address -> registered word -> element configuration port
    reg         ld_run;
    reg [4:0]   ld_k;
    reg [AW-1:0] ld_a;
    reg [2:0]   ld_np;
    reg         c_v;
    reg [4:0]   c_a;
    reg [47:0]  c_d;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ld_run <= 1'b0; ld_k <= 5'd0; c_v <= 1'b0;
        end else begin
            c_v <= ld_run;
            if (cfg_go) begin
                ld_run <= 1'b1; ld_k <= 5'd0;
                ld_a <= AW'(cfg_ph) * AW'(CW);
                ld_np <= cfg_np;
            end else if (ld_run) begin
                ld_k <= ld_k + 5'd1;
                ld_a <= ld_a + 1'b1;
                if (ld_k == 5'(CW - 1)) ld_run <= 1'b0;
            end
        end
    end
    // An element with no class in the phase gets no `go`: W10's element, started with an empty configuration,
    // walks stale state and corrupts its NEXT op (W17 gate, 2026-09-30; reported to W10).  The flag is the OR
    // of the phase's class-valid bits as they are loaded (no extra ROM bit).
    reg act;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) act <= 1'b0;
        else if (cfg_go) act <= 1'b0;
        else if (c_v && c_a >= 5'(NSEG) && c_a < 5'(2 * NSEG) && c_d[0]) act <= 1'b1;
    end
    wire go_e = go && act;
    always @(posedge clk) begin
        c_a <= ld_k;
        if (ld_run) c_d <= (ld_k == 5'(2 * NSEG)) ? (cmr(ld_a) | {42'd0, ld_np, 3'd0}) : cmr(ld_a);
    end
    wire e_busy;
    assign busy = e_busy;
    assign quiet = !e_busy && !ld_run && !c_v && !cfg_go && !(go && act);
    ot_v41_rom_elem_w10 #(.NSEG(NSEG), .NCH(NCH), .XF(XF), .LV(LV), .BF16(BF16), .NB(2), .MTP(MTP), .EARLY(EARLY),
                      .FAST(FAST), .PP(PP), .BP(BP), .FRONT_PAR(0), .INSTANCE(INSTANCE)) u_e (
        .clk(clk), .rst_n(rst_n), .cfg_v(c_v), .cfg_a(c_a), .cfg_d(c_d),
        .go(go_e), .go_bf(go_bf), .xb_v(xb_v), .xb_b(xb_b), .xb_sv(xb_sv), .xb_u(xb_u), .xb_d(xb_d),
        .xs_v(xs_v), .xs_p(xs_p), .xs_b(xs_b), .xs_sv(xs_sv), .xs_q0(xs_q0), .xs_e0(xs_e0),
        .xs_q1(xs_q1), .xs_e1(xs_e1), .xs_pos(xs_pos), .xb_pos(xb_pos), .ppos(ppos),
        .pv(pv), .pval(pval), .prow(prow), .pseg(pseg), .pnseg(pnseg), .perr(perr),
        .busy(e_busy), .fault(fault));
endmodule
