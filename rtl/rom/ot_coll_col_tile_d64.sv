`timescale 1ns/1ps
// qwen-coll-io 2026-10-14: ot_coll_col_tile_d64 -- ot_coll_col_tile with a 64-word FIFO per source (two 32 x 128 macros a
// source, 8 a leaf; slot index 6 bits on c_wp / c_l1).  Why: at the TP8 board crossing (one-way LAT 339 cycles) the
// engine stops broadcasting once its LOCAL source FIFO holds DEPTH words (can_tx[RANK]); with DEPTH 32 a 128-word owner
// half needs four crossings (AR256 1,683 cycles with link-level credits) -- DEPTH 64 + 128-word result reservations
// measure AR256 953 / 2x256 1,657 (WT0 sweep, el1014-qwen-coll-io.log).  Everything else is ot_coll_col_tile verbatim.
// qwen-tp8/coll4 2026-10-12: ot_coll_col_tile -- one 128-bit column of the MARGIN-9 collective engine datapath
// (rtl/rom/ot_rom_oneshot_die_m.sv CT 1), hardened ONCE and replicated x5 (four 128-bit data columns of the 512-bit
// word + one column holding the 34 {tag, mode, last} bits of the 546-bit record; its 94 upper bits are tied 0).
//
// Why: the MARGIN-8 engine kept ~11k datapath flops (input buffer, receive pin registers, FIFO heads, s0 operands,
// gather register) in the cluster glue; the cluster clock spine over them built 1.75 ns (io_rt) / 3.3 ns (rt2) TT
// insertion and both routes failed FF hold flat (-505 / -781 ps).  The column tile takes the datapath into a leaf
// with its own clock tree (~3.5k flops); the cluster keeps only the control state machine (~0.4k flops), the output
// registers and the per-column fold slices.
//
// Timing: the tile is a ONE-CYCLE-DELAYED REPLICA of the engine's column datapath.  Every control input is taken
// into a pin flop (registered seam), so the tile performs at edge t+1 exactly the write the engine performed at
// edge t; every data input therefore passes through two flops (pin flop + alignment flop) so it meets its delayed
// control.  The tile outputs (s0 operands, gather word, tx word) are the engine's values one cycle later; the
// cluster delays the matching control (red_in, go_v/go_last/go_rank, tx_valid, the last-flag line) by one edge.
//
// No parameters (hardened children carry none): N 4 sources, DEPTH 32 FIFO (one ot_sram_1r1w_32x128_m1 per source),
// IB 4 input-buffer words, look-ahead registered IB head (IBH), PR 2 level-2 per-source pop/refill registers.
// Control inputs (cluster engine signals at engine timing):
//   c_ibw / c_iw   : IB write (iv_q && !ib_full) and its slot iw[1:0]
//   c_fire / c_ir  : the transmit decision and the IB read pointer ir[1:0] (IBH look-ahead head)
//   c_push / c_wp  : per-source FIFO write and slot (source = rank: the local word lpq; else the rx word)
//   c_l1           : per-source level-1 decision state {hv[3:0], gb, pop, s0m, hm, !iz, mnz, rp[5:0]} (dup16 image)
//   c_gidx         : gather source index gc_idx
//   rank_oh        : static one-hot strap of the die's own source
module ot_coll_col_tile_d64 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [3:0]    rank_oh,
    input  wire [127:0]  in_d,
    input  wire [511:0]  rx_d,
    input  wire          c_ibw,
    input  wire [1:0]    c_iw,
    input  wire          c_fire,
    input  wire [1:0]    c_ir,
    input  wire [3:0]    c_push,
    input  wire [23:0]   c_wp,
    input  wire [63:0]   c_l1,
    input  wire [1:0]    c_gidx,
    output wire [511:0]  s0,
    output reg  [127:0]  go,
    output reg  [127:0]  tx
);
    genvar g;
    integer r;
    // ---- reset synchroniser (control pin flops and level-2 registers only) --------------------------------------
    (* async_reg = "true" *) reg [1:0] rs;
    always @(posedge clk or negedge rst_n) if (!rst_n) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rst_t = rs[1];
    // ---- control pin flops ----------------------------------------------------------------------------------------
    reg        ibw, fire;
    reg [1:0]  iw, ir, gidx;
    reg [3:0]  push, rk;
    reg [23:0] wp;
    reg [63:0] l1;
    always @(posedge clk or negedge rst_t)
        if (!rst_t) begin ibw <= 1'b0; fire <= 1'b0; iw <= 2'd0; ir <= 2'd0; gidx <= 2'd0; push <= 4'd0;
                          rk <= 4'd0; wp <= 24'd0; l1 <= 64'd0; end
        else begin ibw <= c_ibw; fire <= c_fire; iw <= c_iw; ir <= c_ir; gidx <= c_gidx; push <= c_push;
                   rk <= rank_oh; wp <= c_wp; l1 <= c_l1; end
    // ---- data pin flops + alignment flops ---------------------------------------------------------------------------
    reg [127:0] in_p, irec;
    reg [511:0] rx_p, rxr;
    always @(posedge clk) begin in_p <= in_d; irec <= in_p; rx_p <= rx_d; rxr <= rx_p; end
    // ---- input buffer (IB 4) with the registered look-ahead head ----------------------------------------------------
    reg [127:0] ib [0:3];
    reg [127:0] hq, lpq;
    always @(posedge clk) if (ibw) ib[iw] <= irec;
    wire [1:0] ir_nx = fire ? ir + 2'd1 : ir;
    always @(posedge clk)
`ifdef OT_ONESHOT_M_IBH_MUTANT
        if (1'b0) hq <= irec;
`else
        if (ibw && (iw == ir_nx)) hq <= irec;
`endif
        else hq <= ib[ir_nx];
    always @(posedge clk) begin lpq <= hq; tx <= hq; end
    // ---- per-source FIFO macro, level-2 decision registers, head and s0 operand registers ---------------------------
    wire [127:0] s0w [0:3];
    generate for (g = 0; g < 4; g = g + 1) begin : g_r
        wire [15:0] l1q = l1[g*16 +: 16];
        wire [3:0]  hvc = l1q[15:12];
        wire gbc = l1q[11], s0vc = l1q[10], s0mc = l1q[9], hmc = l1q[8], izc = !l1q[7], mnzc = l1q[6];
        wire [5:0]  rpc = l1q[5:0];
        wire popk = (&hvc) && !gbc && ((!(s0vc && s0mc) && !hmc) || (hmc && izc && !s0vc));
        wire refk = mnzc && (!hvc[g] || popk);
        reg  [7:0]  l2q;
        always @(posedge clk or negedge rst_t) if (!rst_t) l2q <= 8'd0; else l2q <= {popk, refk, l1q[5:0]};
        wire popq = l2q[7], refq = l2q[6];
`ifdef OT_ONESHOT_M_MEMM_MUTANT
        wire [5:0] mra = rpc + 1'b1;
`else
        wire [5:0] mra = rpc;
`endif
        wire [127:0] wd = rk[g] ? lpq : rxr[g*128 +: 128];
        // DEPTH 64: two 32 x 128 macros a source, slot bit 5 selects the macro; the read select is registered with
        // the (registered) macro read so the head capture takes the macro that was read
        wire [127:0] mrow0, mrow1;
        reg          rsel;
        always @(posedge clk) if (refk) rsel <= mra[5];
        ot_sram_1r1w_32x128_m1 u_m0 (.clk(clk), .r_ce_in(refk && !mra[5]), .r_addr_in(mra[4:0]), .rd_out(mrow0),
            .w_ce_in(push[g] && !wp[g*6+5]), .w_addr_in(wp[g*6 +: 5]), .wd_in(wd), .w_mask_in({128{1'b1}}));
        ot_sram_1r1w_32x128_m1 u_m1 (.clk(clk), .r_ce_in(refk && mra[5]), .r_addr_in(mra[4:0]), .rd_out(mrow1),
            .w_ce_in(push[g] && wp[g*6+5]), .w_addr_in(wp[g*6 +: 5]), .wd_in(wd), .w_mask_in({128{1'b1}}));
        wire [127:0] mrow = rsel ? mrow1 : mrow0;
        reg [127:0] hdk, s0k;
        always @(posedge clk) begin
            if (refq) hdk <= mrow;
            if (popq) s0k <= hdk;
        end
        assign s0[g*128 +: 128] = s0k;
        assign s0w[g] = s0k;
    end endgenerate
    always @(posedge clk) go <= s0w[gidx];
endmodule
