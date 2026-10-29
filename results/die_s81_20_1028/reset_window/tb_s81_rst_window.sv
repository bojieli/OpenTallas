// tb_s81_rst_window: reset window (clocked edges with the core rst_n pin low) delivered by the S81 die reset generator
// as generated on origin/main: die rst_n pad -> ONE root ot_dp_rsync_s2 (u_rst_root, reset.sync_stages 2) -> wavefront
// ot_dp_rrelay chain (u_rst_in, u_rrl_*, rst_o, ...; no reset of their own) -> hard-core rst_n pin.  S81 plan reset
// has no pad/lock (no ot_dp_lockq) and no START gate.  Cells: s81_reset_cells.v (verbatim from gen_rtl.CELLS).
// Measures, for power-on and for mid-run die rst_n pulses of many widths/phases, the number of posedges at which the
// core pin is sampled low; FATAL if any window < CONTRACT.
// MUT 1: one-flop root synchroniser (S=1).  PROP: bench-only PROPOSAL hold stage after the root (not in any RTL).
`timescale 1ns/1ps
module ot_dp_rsync_s1_mut (input wire clk, input wire async_rst_n, output wire sync_rst_n);
    reg p;
    always @(posedge clk or negedge async_rst_n) if (!async_rst_n) p <= 1'b0; else p <= 1'b1;
    assign sync_rst_n = p;
endmodule
// PROPOSAL only (estimate of the fix): synchronous hold counter after the root synchroniser; q stays low until d has
// been high for HOLD consecutive edges; any low d (power-on or a mid-run pulse) restarts the window.
module ot_dp_rhold_prop #(parameter integer HOLD = 16) (input wire clk, input wire d, output reg q);
    localparam integer CW = $clog2(HOLD + 1);
    reg [CW-1:0] c;
    always @(posedge clk)
        if (!d) begin c <= 0; q <= 1'b0; end
        else if (c != HOLD) begin c <= c + 1'b1; q <= 1'b0; end
        else q <= 1'b1;
endmodule
module tb_s81_rst_window;
    parameter integer CONTRACT = 2;
    parameter integer E = 6;            // relay stages root -> core pin (any E: a synchronous copy keeps the window)
    parameter integer MUT = 0;
    parameter integer PROP = 0;         // >0: PROPOSAL hold stage with HOLD = PROP
    reg clk = 0, rst_n = 0;
    always #0.4165 clk = ~clk;          // 1.2 GHz
    wire root;
    generate if (MUT == 1) begin : g_m1
        ot_dp_rsync_s1_mut u_rst_root (.clk(clk), .async_rst_n(rst_n), .sync_rst_n(root));
    end else begin : g_s2
        ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(rst_n), .sync_rst_n(root));
    end endgenerate
    wire rel;
    generate if (PROP > 0) begin : g_p
        ot_dp_rhold_prop #(.HOLD(PROP)) u_hold (.clk(clk), .d(root), .q(rel));
    end else begin : g_np
        assign rel = root;
    end endgenerate
    wire [E:0] ch;
    assign ch[0] = rel;
    genvar g;
    generate for (g = 0; g < E; g = g + 1) begin : g_r
        ot_dp_rrelay u_rrl (.clk(clk), .d(ch[g]), .q(ch[g + 1]));
    end endgenerate
    wire pin = ch[E];                   // the hard core's rst_n_pin (ot_v41_bf_col / ot_v41_rom_elem_q_qxpq_w10_gb)
    integer run = 0, minw = 1 << 30, maxw = 0, nwin = 0, fails = 0, checks = 0;
    reg in_win = 0;
    // count posedges at which the core samples its pin low (X at power-up counts as NOT asserted: conservative)
    always @(posedge clk) begin
        if (pin === 1'b0) begin run = run + 1; in_win = 1; end
        else if (in_win && pin === 1'b1) begin
            checks = checks + 1; nwin = nwin + 1;
            if (run < minw) minw = run;
            if (run > maxw) maxw = run;
            if (run < CONTRACT) begin
                $display("FATAL: window %0d edges < contract %0d (event %0d, t=%0t)", run, CONTRACT, nwin, $time);
                fails = fails + 1;
            end
            run = 0; in_win = 0;
        end
    end
    real w [0:9];
    integer i, j;
    initial begin
        w[0] = 0.05; w[1] = 0.1; w[2] = 0.2; w[3] = 0.3; w[4] = 0.4; w[5] = 0.6; w[6] = 0.8; w[7] = 1.0; w[8] = 1.4; w[9] = 1.9;
        rst_n = 0;                      // power-on: pad low, clock running, 1 clk
        #(0.833); rst_n = 1;
        #(60);
        for (i = 0; i < 10; i = i + 1)  // mid-run pulses: 10 widths x 8 phases
            for (j = 0; j < 8; j = j + 1) begin
                #(0.1041 * j + 0.013); rst_n = 0; #(w[i]); rst_n = 1; #(60);
            end
        #(20);
        if (in_win) begin $display("FATAL: core pin still low at end"); fails = fails + 1; end
        if (fails == 0)
            $display("S81RST_PASS windows=%0d min_edges=%0d max_edges=%0d contract=%0d E=%0d mut=%0d prop_hold=%0d",
                     nwin, minw, maxw, CONTRACT, E, MUT, PROP);
        else
            $display("S81RST_FAIL fails=%0d windows=%0d min_edges=%0d contract=%0d mut=%0d prop_hold=%0d",
                     fails, nwin, minw, CONTRACT, MUT, PROP);
        $finish;
    end
endmodule
