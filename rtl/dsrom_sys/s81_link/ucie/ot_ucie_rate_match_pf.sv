`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// ot_ucie_rate_match_pf (HBM-OWN/PHY 10-21, HBM host UCIe column ucie6): ot_s81_rate_match_sr with the FIFO state flags
// PRE-COMPUTED one edge ahead (registered), cycle-for-cycle identical function, same ports, no new data edge.
// Why: the ucie5f route (hbm_pdie_ucie_colf-ucie5f-b5f0313fd) failed two short CDC-FIFO cones at TT:
//   u_rm.m_waddr -> fill subtract -> full / near-full compare -> push -> u_rmm/w_ce_in   (-17.99 ps, SRAM setup 41 ps)
//   u_rm.wp_g2  -> gray-to-binary -> == rp -> empty -> rp + 1 -> rp D                    (-14.21 ps)
// Write side: full_r / hi_r = (wp - g2b(rp_g2 one edge earlier)) == 8 / >= 6; D from the next wp (wp or wp+1, both
//   candidates in parallel, selected by push) and the CURRENT rp_g2.  push is a 4-input AND-OR of flops (w_v, idle bits
//   of w_d, full_r, hi_r) -> SRAM w_ce_in.
// Read side: empty_r = (g2b(wp_g2 one edge earlier) == rp); D = empty_r ? (g2b(wp_g2) == rp) : (g2b(wp_g2) == rp + 1);
//   rp's D is a 2:1 mux of rp / rp+1 by a flop.
// CDC: the first synchroniser stages (rp_g1 / wp_g1) still feed ONLY the second stages (no logic on a metastable stage),
//   so each opposite pointer is seen ONE edge later than in ot_s81_rate_match_sr (3-stage visibility, as the closed n32
//   precompute tile).  Both flags stay conservative (fill seen >= true fill on write, <= on read): no overflow, no read of
//   an unwritten row.  PRICE: +1 cycle RX elastic latency at the off-die UCIe boundary (elastic rate matcher, flow
//   control kept at off-die boundaries; not an on-die scheduled edge); IDLE-drop regulation one beat earlier.
// Reset values equal the original flags at reset (full 0, near 0, empty 1).  Separate module (not a parameter of the
// shared S81 file) so the closed S81 SerDes column source stays byte-identical.
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_rate_match_sr (DRIVE-S81-PHY 10-20, S81.STA.OWN.7, SerDes column lp6): the column rate matcher with its
// 8 x 512 elastic storage in a dual-clock SRAM macro (ot_sram_1r1w2c_16x546_m1, a sibling child u_rmm of the column)
// instead of 4,096 flops.  SAFE-DESIGN item 5 (storage > 2 kb -> SRAM) is now met; the lp5 waiver is gone.
// Function = ot_s81_rate_match (rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv, closed tile s81lk_rate_match), cycle for cycle:
//   * write (wclk = recovered pma_rck): push = w_v && !full && !(IDLE && fill >= 6); mem[wp] <= w_d on push (SRAM write
//     port, address = the 4-bit binary write pointer: the FIFO is 8 deep by the fill rule, the 16-row macro is indexed
//     mod 16 on both sides, so reads see exactly the rows the writes filled); sticky overflow fault.
//   * read (rclk = core clk): r_d <= mem[rp] when not empty, else the IDLE beat 512'd2.  The SRAM read port registers
//     mem[rp] on the same edge (r_ce = !empty); the IDLE select is the registered empty, so r_d = sel ? 2 : rd -- the
//     same value on the same edge as the closed tile's r_d register.
//   * 2-stage gray pointer synchronisers (as the closed tile; the n32 third stage is not needed: no broadcast precompute).
// NATIVE32: every driver <= 32 loads.  w_d bit k feeds the SRAM data pin (and bits 33:0 also the 34 spare data columns,
// so no tied macro input); the write mask is 26 KEPT always-1-after-reset flops (<= 21 mask pins each); the IDLE select is
// 16 KEPT copies of the registered empty (32 r_d bits each); the side resets go through 2 kept mid flops.
// The rck -> clk crossing is the 2-stage gray synchronisers only (CDC child: lp.py child_pin_regions; the SRAM is the
// closed-form storage, its two clock pins on the two family roots).
// ---------------------------------------------------------------------------------------------------------------------
(* keep_hierarchy = "yes" *)
module ot_ucie_rms_one #(parameter integer ID = 0) (      // 0 in reset, 1 from the first edge after release
    input  wire clk,
    input  wire rn,
    output reg  q
);
    always @(posedge clk or negedge rn) if (!rn) q <= 1'b0; else q <= 1'b1;
endmodule

(* keep_hierarchy = "yes" *)
module ot_ucie_rms_sel #(parameter integer ID = 0) (      // registered IDLE select copy (1 in reset = IDLE)
    input  wire clk,
    input  wire rn,
    input  wire d,
    output reg  q
);
    always @(posedge clk or negedge rn) if (!rn) q <= 1'b1; else q <= d;
endmodule

module ot_ucie_rate_match_pf (
    input  wire          wclk, wrst_n,
    input  wire          w_v,
    input  wire [511:0]  w_d,
    input  wire          rclk, rrst_n,
    output wire [511:0]  r_d,
    output wire          fault,
    // dual-clock SRAM (sibling child u_rmm, ot_sram_1r1w2c_16x546_m1)
    output wire          m_wce,
    output wire [3:0]    m_waddr,
    output wire [545:0]  m_wd,
    output wire [545:0]  m_wmask,
    output wire          m_rce,
    output wire [3:0]    m_raddr,
    input  wire [545:0]  m_rd
);
    localparam integer NM = 26;     // mask copies: 546 / 26 = 21 pins each
    localparam integer NS = 16;     // select copies: 512 / 16 = 32 bits each
    function automatic [3:0] g2b(input [3:0] g); begin g2b = {g[3], g[3]^g[2], g[3]^g[2]^g[1], g[3]^g[2]^g[1]^g[0]}; end endfunction
    // ---- side reset mids (2 kept flops per side; release one edge after the side reset)
    wire [1:0] wmid, rmid;
    genvar i;
    generate for (i = 0; i < 2; i = i + 1) begin : g_mid
        (* keep_hierarchy = "yes" *) ot_ucie_rms_one #(.ID(i))     u_w (.clk(wclk), .rn(wrst_n), .q(wmid[i]));
        (* keep_hierarchy = "yes" *) ot_ucie_rms_one #(.ID(100+i)) u_r (.clk(rclk), .rn(rrst_n), .q(rmid[i]));
    end endgenerate
    // ---- write side
    reg  [3:0] wp, wp_g, rp_g1, rp_g2;
    reg        flt;
    always @(posedge wclk or negedge wrst_n) if (!wrst_n) begin rp_g1 <= 0; rp_g2 <= 0; end else begin rp_g1 <= rp_g; rp_g2 <= rp_g1; end
    wire idle = w_d[1] && !w_d[0];
    reg  full_r, hi_r;                       // registered full / near-full (see header)
    wire [3:0] rb_n = g2b(rp_g2);            // binary read pointer (2nd synchroniser stage)
    wire [3:0] f_n0 = wp - rb_n;             // next fill without a push
    wire [3:0] f_n1 = wp + 4'd1 - rb_n;      // next fill with a push
    wire full = full_r;
    wire push = w_v && !full_r && !(idle && hi_r);
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin full_r <= 1'b0; hi_r <= 1'b0; end
        else begin
            full_r <= push ? (f_n1 == 4'd8) : (f_n0 == 4'd8);
            hi_r   <= push ? (f_n1 >= 4'd6) : (f_n0 >= 4'd6);
        end
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end
        else begin
            if (push) begin wp <= wp + 1'b1; wp_g <= (wp + 1'b1) ^ ((wp + 1'b1) >> 1); end
            if (w_v && full && !idle) flt <= 1'b1;
        end
    assign m_wce = push;
    assign m_waddr = wp;
    assign m_wd = {w_d[33:0], w_d};
    wire [NM-1:0] mk;
    generate for (i = 0; i < NM; i = i + 1) begin : g_mask
        (* keep_hierarchy = "yes" *) ot_ucie_rms_one #(.ID(200+i)) u_m (.clk(wclk), .rn(wmid[i % 2]), .q(mk[i]));
        localparam integer LO = i * 21;
        localparam integer HI = (i == NM - 1) ? 545 : LO + 20;
        assign m_wmask[HI:LO] = {(HI-LO+1){mk[i]}};
    end endgenerate
    // ---- read side
    reg  [3:0] rp, rp_g, wp_g1, wp_g2;
    always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin wp_g1 <= 0; wp_g2 <= 0; end else begin wp_g1 <= wp_g; wp_g2 <= wp_g1; end
    reg  empty_r;                            // registered empty (see header)
    wire [3:0] wb_n = g2b(wp_g2);            // binary write pointer (2nd synchroniser stage)
    wire empty = empty_r;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) empty_r <= 1'b1;
        else empty_r <= empty_r ? (wb_n == rp) : (wb_n == rp + 4'd1);
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin rp <= 0; rp_g <= 0; end
        else if (!empty) begin rp <= rp + 1'b1; rp_g <= (rp + 1'b1) ^ ((rp + 1'b1) >> 1); end
    assign m_rce = !empty;
    assign m_raddr = rp;
    wire [NS-1:0] sel;
    generate for (i = 0; i < NS; i = i + 1) begin : g_sel
        (* keep_hierarchy = "yes" *) ot_ucie_rms_sel #(.ID(300+i)) u_s (.clk(rclk), .rn(rmid[i % 2]), .d(empty), .q(sel[i]));
        // IDLE beat = 512'd2 (bit 1 set): bit 1 = rd | sel, every other bit = rd & !sel
        if (i == 0) begin : g_b0
            assign r_d[0] = m_rd[0] & !sel[0];
            assign r_d[1] = m_rd[1] | sel[0];
            assign r_d[31:2] = m_rd[31:2] & {30{!sel[0]}};
        end else begin : g_bn
            assign r_d[i*32+31:i*32] = m_rd[i*32+31:i*32] & {32{!sel[i]}};
        end
    end endgenerate
    reg f1, f2; always @(posedge rclk or negedge rrst_n) if (!rrst_n) begin f1 <= 0; f2 <= 0; end else begin f1 <= flt; f2 <= f1; end
    assign fault = f2;
    wire unused_rd = ^m_rd[545:512];
endmodule
`default_nettype wire
