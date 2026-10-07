`timescale 1ns/1ps
// CLAUDE S81-PH: dual-clock Gray-pointer FIFO for the S81 HBM controller boundary (dsfd_ctrl), after rtl/lib/ot_async_fifo.sv.
// Differences: (1) wr_ready is a REGISTER that reserves AF free entries (AF = 2: a producer whose response is captured
// by a pin register one cycle before it reaches w_v never overruns); (2) the write side exports one credit pulse per
// entry the reader has freed (registered, at most one a cycle, never lost: counted against the synchronised read
// pointer); (3) both sides reset from one die reset, each through its own synchroniser (wrst_n / rrst_n are the
// synchronised resets); pointers clear together, so no rendezvous is needed.  Data is not reset; the read word is
// mem[rbin] (written >= 2 synchroniser cycles before its pointer is visible: constrain mem -> read-domain paths with
// set_max_delay -datapath_only, as the Qwen stream4 CDC closure did).
module ot_s81ph_afifo #(
    parameter integer W = 32,
    parameter integer DEPTH = 8,
    parameter integer AF = 2
) (
    input  wire         wclk,
    input  wire         wrst_n,
    input  wire         w_v,
    input  wire [W-1:0] w_d,
    output reg          w_rdy,      // registered: >= AF entries free (counting the entries already written)
    output reg          w_credit,   // registered pulse: one entry freed by the reader
    output reg          w_ovf,      // sticky: a write into a full FIFO (dropped)
    input  wire         rclk,
    input  wire         rrst_n,
    output wire         r_v,
    input  wire         r_pop,
    output wire [W-1:0] r_d
);
    localparam integer AW = $clog2(DEPTH);
    localparam integer PW = AW + 1;
    function automatic [PW-1:0] g2b(input [PW-1:0] g);
        integer i;
        begin
            g2b[PW-1] = g[PW-1];
            for (i = PW - 2; i >= 0; i = i - 1) g2b[i] = g2b[i+1] ^ g[i];
        end
    endfunction
    // storage: one register row per entry, written through a REGISTERED one-hot enable (computed a cycle ahead from
    // flops only), one enable flop per 64-bit slice (synthesis may merge identical copies; the placer's repair_design
    // buffers what remains, with no logic in front of the tree).  A row is written every cycle the FIFO is not full, with or
    // without w_v: a write without w_v lands in the free slot wbin, which the next real write overwrites before the
    // write pointer publishes it, so the reader never sees it (same values, same cycles as a w_v-gated write).
    localparam integer NCP = (W + 63) / 64;
    wire [DEPTH*W-1:0] mrd;
    reg [PW-1:0] wbin, wgray, rbin, rgray, cbin;
    (* async_reg = "true" *) reg [PW-1:0] rg_w1, rg_w2;
    (* async_reg = "true" *) reg [PW-1:0] wg_r1, wg_r2;
    wire [PW-1:0] rbin_w = g2b(rg_w2);
    wire [PW-1:0] used = wbin - rbin_w;
    wire          full = used[AW];
    wire          wfire = w_v && !full;
    wire [PW-1:0] wbin_n = wbin + {{(PW-1){1'b0}}, wfire};
    wire [PW-1:0] used_n = wbin_n - rbin_w;
    wire [PW-1:0] used_nn = wbin_n - g2b(rg_w1);        // next cycle's `used` (rg_w2 <= rg_w1)
    wire          full_n = used_nn[AW];
    genvar ge, gc;
    generate for (ge = 0; ge < DEPTH; ge = ge + 1) begin : g_e
        for (gc = 0; gc < NCP; gc = gc + 1) begin : g_c
            localparam integer LO = gc * 64;
            localparam integer WD = (gc == NCP - 1) ? W - LO : 64;
            reg [WD-1:0] q;
            (* keep *) reg wen_q;
            always @(posedge wclk or negedge wrst_n)
                if (!wrst_n) wen_q <= (ge == 0);
                else wen_q <= (wbin_n[AW-1:0] == ge) && !full_n;
            always @(posedge wclk) if (wen_q) q <= w_d[LO +: WD];
            assign mrd[ge*W + LO +: WD] = q;
        end
    end endgenerate
    always @(posedge wclk or negedge wrst_n)
        if (!wrst_n) begin
            wbin <= 0; wgray <= 0; rg_w1 <= 0; rg_w2 <= 0; cbin <= 0;
            w_rdy <= 1'b0; w_credit <= 1'b0; w_ovf <= 1'b0;
        end else begin
            wbin <= wbin_n;
            wgray <= (wbin_n >> 1) ^ wbin_n;
            rg_w1 <= rgray; rg_w2 <= rg_w1;
            w_rdy <= (DEPTH - 32'(used_n)) >= AF;
`ifdef S81PH_MUT_CREDIT
            w_credit <= wfire;                                                   // mutant: credit on write, not on free
`else
            w_credit <= cbin != rbin_w;
            if (cbin != rbin_w) cbin <= cbin + 1'b1;
`endif
            if (w_v && full) w_ovf <= 1'b1;
        end
    reg empty;
    wire rfire = r_pop && !empty;
    wire [PW-1:0] rbin_n = rbin + {{(PW-1){1'b0}}, rfire};
    wire [PW-1:0] rgray_n = (rbin_n >> 1) ^ rbin_n;
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) begin
            rbin <= 0; rgray <= 0; wg_r1 <= 0; wg_r2 <= 0; empty <= 1'b1;
        end else begin
            rbin <= rbin_n; rgray <= rgray_n;
            wg_r1 <= wgray; wg_r2 <= wg_r1;
            empty <= rgray_n == wg_r2;
        end
    assign r_v = !empty;
    assign r_d = mrd[rbin[AW-1:0]*W +: W];
endmodule

// pulse crossing: one destination pulse (registered) per source pulse, by a Gray event counter (never lost while the
// destination keeps within 2^(CW-1) events of the source)
module ot_s81ph_pulse_x #(parameter integer CW = 4) (
    input  wire sclk, input wire srst_n, input wire s_p,
    input  wire dclk, input wire drst_n, output reg d_p
);
    reg [CW-1:0] sbin, sgray, dbin;
    (* async_reg = "true" *) reg [CW-1:0] g1, g2;
    wire [CW-1:0] sbin_n = sbin + {{(CW-1){1'b0}}, s_p};
    always @(posedge sclk or negedge srst_n)
        if (!srst_n) begin sbin <= 0; sgray <= 0; end
        else begin sbin <= sbin_n; sgray <= (sbin_n >> 1) ^ sbin_n; end
    reg [CW-1:0] gb;
    integer i;
    always @(*) begin
        gb[CW-1] = g2[CW-1];
        for (i = CW - 2; i >= 0; i = i - 1) gb[i] = gb[i+1] ^ g2[i];
    end
    always @(posedge dclk or negedge drst_n)
        if (!drst_n) begin g1 <= 0; g2 <= 0; dbin <= 0; d_p <= 1'b0; end
        else begin
            g1 <= sgray; g2 <= g1;
            d_p <= dbin != gb;
            if (dbin != gb) dbin <= dbin + 1'b1;
        end
endmodule

// level synchroniser (2 flops)
module ot_s81ph_sync #(parameter integer W = 1) (
    input wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q);
    (* async_reg = "true" *) reg [W-1:0] s1, s2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s1 <= 0; s2 <= 0; end else begin s1 <= d; s2 <= s1; end
    assign q = s2;
endmodule
