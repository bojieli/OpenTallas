// DIE-KV-26 KV die reset contract bench (DIE-HBM-10 pattern).  Cells = bind26b rtl/bind_cells.sv byte copy
// (bind26b_cells.sv, sha256 in receipt).  Chain = the bound KV root (kv3_hub_C_part.sv:4771-4772, por_gate PASS):
//   pad por_n -> ot_dp_rsync_s2 u_rst_root -> ot_dp_lockq #(STABLE) u_rst_lockq -> DEPTH x ot_dp_rrelay (die + partition
//   wavefront relays) -> sink A: ot_dp_rgate (START-gated consumer tap, run=1 = worst case, mid-run re-arm)
//                     -> sink B: ot_dp_rsync #(S=2) reset-spine landing (async assert, S-clock release)
// Measures, for every arm (power-on, mid-run por_n pulse of any width/phase, lock loss during reset), the number of
// consecutive own-clock rising edges each sink is held in reset WITH the PLL locked (clock valid).  FATAL if < CONTRACT.
// MUT 1: lock qualifier STABLE 4 (short window).  MUT 2: lock qualifier bypassed (window = root synchroniser only).
`timescale 1ps/1ps
module tb_kv_reset_contract;
    parameter integer MUT = 0;
    parameter integer CONTRACT = 16;
    parameter integer DEPTH = 8;
    localparam integer STABLE = (MUT == 1) ? 4 : 16;
    reg clk = 0; always #416 clk = ~clk;          // 832 ps period (1.2 GHz class)
    reg por_n = 0, locked = 0, run = 1;
    wire rst_por_n, rst_lq, rst_root_n;
    ot_dp_rsync_s2 u_rst_root (.clk(clk), .async_rst_n(por_n), .sync_rst_n(rst_por_n));
    ot_dp_lockq #(.STABLE(STABLE)) u_rst_lockq (.clk(clk), .d(rst_por_n), .locked(locked), .q(rst_lq));
    assign rst_root_n = (MUT == 2) ? rst_por_n : rst_lq;
    wire [DEPTH:0] w; assign w[0] = rst_root_n;
    genvar g; generate for (g = 0; g < DEPTH; g = g + 1) begin : rl
        ot_dp_rrelay u (.clk(clk), .d(w[g]), .q(w[g+1]));
    end endgenerate
    wire sink_a, sink_b;
    ot_dp_rgate u_gate (.clk(clk), .d(w[DEPTH]), .run(run), .q(sink_a));
    ot_dp_rsync #(.W(1), .S(2)) u_land (.clk(clk), .a(w[DEPTH]), .q(sink_b));
    integer ca = 0, cb = 0, mina = 1 << 30, minb = 1 << 30, arms = 0, checks = 0, fails = 0;
    reg ina = 0, inb = 0;
    always @(posedge clk) begin
        if (sink_a === 1'b0) begin ina <= 1; if (locked) ca <= ca + 1; end
        else if (sink_a === 1'b1 && ina) begin
            checks = checks + 1; if (ca < mina) mina = ca;
            if (ca < CONTRACT) begin fails = fails + 1; $display("FATAL: sink A (rgate) released after %0d locked edges in reset (contract %0d) t=%0t", ca, CONTRACT, $time); end
            ina <= 0; ca <= 0;
        end
        if (sink_b === 1'b0) begin inb <= 1; if (locked) cb <= cb + 1; end
        else if (sink_b === 1'b1 && inb) begin
            checks = checks + 1; if (cb < minb) minb = cb;
            if (cb < CONTRACT) begin fails = fails + 1; $display("FATAL: sink B (rsync landing) released after %0d locked edges in reset (contract %0d) t=%0t", cb, CONTRACT, $time); end
            inb <= 0; cb <= 0;
        end
    end
    task settle; begin repeat (80) @(posedge clk); end endtask
    task glitch(input integer w_ps, input integer ph_ps); begin
        @(posedge clk); #(ph_ps); por_n = 0; arms = arms + 1; #(w_ps); por_n = 1; settle; end endtask
    integer i, nglitch = 0, nlock = 0;
    initial begin
        // power-on: clock runs unlocked, pad released, lock arrives later
        arms = 1; repeat (10) @(posedge clk); #100 por_n = 1; repeat (12) @(posedge clk); #37 locked = 1; settle;
        // mid-run por_n pulses: widths 0.05..1.94 ns at several phases inside the cycle
        for (i = 0; i < 8; i = i + 1) begin glitch(50 + i * 270, (i * 97) % 800); nglitch = nglitch + 1; end
        // long reset with lock lost during it, lock back after pad release
        @(posedge clk); por_n = 0; arms = arms + 1; repeat (5) @(posedge clk); #11 locked = 0; repeat (6) @(posedge clk);
        por_n = 1; repeat (3) @(posedge clk); #23 locked = 1; settle; nlock = nlock + 1;
        // lock loss after boot (no arm: HOST status) must not re-arm or release anything
        repeat (5) @(posedge clk); #5 locked = 0; repeat (4) @(posedge clk); #5 locked = 1; settle; nlock = nlock + 1;
        if (sink_a !== 1'b1 || sink_b !== 1'b1) begin fails = fails + 1; $display("FATAL: sinks not released at end"); end
        if (checks != 2 * arms) begin fails = fails + 1; $display("FATAL: %0d release checks for %0d arms", checks, arms); end
        if (fails == 0)
            $display("KVRST_PASS checks=%0d arms=%0d min_edges_rgate=%0d min_edges_landing=%0d contract=%0d stable=%0d depth=%0d midrun_glitches=%0d lock_events=%0d",
                     checks, arms, mina, minb, CONTRACT, STABLE, DEPTH, nglitch, nlock);
        else $display("KVRST_FAIL fails=%0d min_edges_rgate=%0d min_edges_landing=%0d", fails, mina, minb);
        $finish;
    end
endmodule
