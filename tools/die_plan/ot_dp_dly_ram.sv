`timescale 1ns/1ps
// ot_dp_dly_ram -- FIX-KV-PV-MESOFIFO 11-23 (ledger rc128, VIS-KV pad FIFO ruling): a landing-pad delay line held in an SRAM
// ring instead of D x W reset-less flops.
//
// Contract: the same as ot_dp_dly #(.W(W), .D(D)) -- q at a clock edge is d sampled D edges earlier, every cycle, no
// valid, no reset, no back-pressure.  Like the flop line it holds arbitrary values for the first D cycles after power-up.
// So the bind latency (LATCHECK) and the lane schedule are unchanged: only the storage of the pad moves.
//
// Why: the KV pv types carried 1.25 M pad flops (kv3_pv_v6n i_astk_W owner response 768 b x 46..67 cycles = 43 k flops,
// 60 % of the kit flops with the lockup latches of kit_dly_lockup), packed into one ~100 um channel with the clock trunk
// and the stacked taps (rc128 GRT-0228, VIS-KV pad_delay_column on 19 KV types).  An SRAM ring stores the same bits in
// 95 x 41 um per 256 bits x 128 cycles and puts nothing on the clock tree but its input / pointer / output registers.
// (ot_meso_fifo, named in the ruling, is a 4-slot mesochronous clock-crossing ring: it cannot hold a 59-cycle delay.)
//
// Pipeline (one write and one read per cycle, never the same slot in one cycle):
//   edge s      d_r   <= d                         input register (the macro write data is registered at the macro)
//   edge s+1    mem[wp] <= d_r,  wp <= wp + 1       write slot a = wp
//   edge s+1+G  rd_out <= mem[rp]                  rp = a here: rp <= wp - (G - 1) every cycle
//   edge s+2+G  q_r   <= rd_out                    q_r = the line's last register
//   shift line: d sampled at edge s is q after edge s + D - 1   =>   G = D - 3,  1 <= G <= DEPTH - 1   =>   4 <= D <= DEPTH + 2
// The slot read at s+1+G is rewritten at s+1+DEPTH > s+1+G, and the slot written in that cycle is a+G != a.
// wp / rp are reset-less like the flops they replace: rp - wp is a constant of the update rule, so any power-up value works.
// DLYRAM-RESET 11-24: PROVEN, not only argued: from ANY state (wp, rp, every SRAM word, d_r, rd_out, q_r free) q equals the
// D-stage flop line from the D-th edge on, D = 4..130 (yosys SAT; an off-by-one lag, an independent rp counter and a D-1
// window all FAIL).  Power-up behaviour is therefore exactly that of ot_dp_dly: D cycles of garbage, which the die reset
// hold must flush (neither line has a reset).  4-STATE SIMULATION ONLY: an X wp never resolves (X + 1 = X), so a 4-state
// sim shows X forever; define OT_DLY_RAM_PTR_INIT to start wp at 0 in simulation (synthesis never sees it: SYNTHESIS
// guard).  Bench rtl/test/dp_dly_ram/run_reset.sh.
//
// Macro: ot_sram_1r1w_128x256_m1_r2c2 (ASAP7 1R1W 128 x 256, read registered, read-before-write; already a KV kit macro,
// kv3_pc_v3).  NB = ceil(W / 256) macros, instance g_b[k].u_m; repair inputs tied off (no redundancy in a delay line).
module ot_dp_dly_ram #(
    parameter integer W = 1,
    parameter integer D = 4
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer WM = 256;
    localparam integer DEPTH = 128;
    localparam integer AW = 7;
    localparam integer NB = (W + WM - 1) / WM;
    localparam integer G = D - 3;
    /* verilator lint_off WIDTHTRUNC */
    localparam [AW-1:0] RP_LAG = G - 1;
    /* verilator lint_on WIDTHTRUNC */

    generate if (D < 4 || D > DEPTH + 2 || W < 1) begin : g_bad
        // elaboration error on purpose: an out-of-range delay must never synthesise
        ot_dp_dly_ram_D_out_of_range_4_to_130 u_bad ();
    end endgenerate

    reg [W-1:0] d_r;
    reg [AW-1:0] wp;
    reg [AW-1:0] rp;
    reg [W-1:0] q_r;
`ifndef SYNTHESIS
`ifdef OT_DLY_RAM_PTR_INIT
    initial wp = {AW{1'b0}};
`endif
`endif
    always @(posedge clk) begin
        d_r <= d;
        wp <= wp + 1'b1;
        rp <= wp - RP_LAG;
    end

    wire [NB*WM-1:0] wd = {{(NB*WM-W){1'b0}}, d_r};
    /* verilator lint_off UNUSEDSIGNAL */
    wire [NB*WM-1:0] rd;
    /* verilator lint_on UNUSEDSIGNAL */
    genvar b;
    generate for (b = 0; b < NB; b = b + 1) begin : g_b
        ot_sram_1r1w_128x256_m1_r2c2 u_m (
            .clk(clk),
            .r_ce_in(1'b1), .r_addr_in(rp), .rd_out(rd[b*WM +: WM]),
            .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(wd[b*WM +: WM]), .w_mask_in({WM{1'b1}}),
            .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    end endgenerate

    always @(posedge clk) q_r <= rd[W-1:0];
    assign q = q_r;
endmodule
