`timescale 1ns/1ps
`default_nettype none
// Lockstep bench (HBM-NATIVE 10-17): ot_hbm_host_phy_adapt (two-flop pin stages) vs the CLOSED dcfed59ab RTL
// (ot_hbm_host_phy_adapt_ref) on the same random stimulus (ep_tx, phy_rx incl. reserved lanes, phy_st, session_pad,
// random resets). On EVERY edge: phy_tx, ep_rx, session == the reference value ONE edge earlier (+1 TX/RX/session);
// pad_fault, phy_fault == the reference on the same edge. Mutant OT_HOST_PHY_STAGE_MUT (TX stage bypassed) must FAIL.
module tb_host_phy_pin_stage;
`ifndef SEED
`define SEED 7
`endif
    reg clk = 0, rst_n = 0; always #1 clk = ~clk;
    reg [486:0] ep_tx = 0; reg [511:0] phy_rx = 0; reg [1:0] st = 0; reg [23:0] sp = 0;
    wire [511:0] tx0, tx1; wire [486:0] rx0, rx1; wire [23:0] s0, s1; wire pf0, pf1, ff0, ff1;
    ot_hbm_host_phy_adapt_ref ref_(.clk(clk), .rst_n(rst_n), .ep_tx(ep_tx), .phy_tx(tx0), .phy_rx(phy_rx), .phy_st(st),
        .ep_rx(rx0), .session_pad(sp), .session(s0), .pad_fault(pf0), .phy_fault(ff0));
    ot_hbm_host_phy_adapt dut(.clk(clk), .rst_n(rst_n), .ep_tx(ep_tx), .phy_tx(tx1), .phy_rx(phy_rx), .phy_st(st),
        .ep_rx(rx1), .session_pad(sp), .session(s1), .pad_fault(pf1), .phy_fault(ff1));
    integer seed = `SEED, cyc = 0, k, mism = 0, dmism = 0, faults = 0, resets = 0;
    reg [511:0] tx0_d; reg [486:0] rx0_d; reg [23:0] s0_d;
    always @(posedge clk) begin tx0_d <= tx0; rx0_d <= rx0; s0_d <= s0; end
    always @(negedge clk) begin
        cyc = cyc + 1;
        if (cyc > 3) begin
            if ({tx1, rx1, s1} !== {tx0_d, rx0_d, s0_d}) begin dmism = dmism + 1; if (dmism <= 3) $display("DATA MISMATCH cyc %0d", cyc); end
            if ({pf1, ff1} !== {pf0, ff0}) begin mism = mism + 1; if (mism <= 3) $display("FAULT MISMATCH cyc %0d", cyc); end
            if (pf0 || ff0) faults = faults + 1;
        end
        rst_n = !(cyc < 3 || ($random(seed) % 3000) == 0); if (!rst_n && cyc >= 3) resets = resets + 1;
        for (k = 0; k < 16; k = k + 1) begin ep_tx[32*k +: 32] = $random(seed); phy_rx[32*k +: 32] = $random(seed); end
        if (($random(seed) % 50) != 0) phy_rx[511:487] = 0;
        st = (($random(seed) % 200) == 0) ? 2'($random(seed)) : st;
        if (($random(seed) % 500) == 0) sp = $random(seed);
        if (cyc == 60000) begin
            $display("HOST_PHY_PIN_STAGE seed %0d cycles %0d data_mismatches %0d fault_mismatches %0d fault_edges %0d resets %0d",
                `SEED, cyc, dmism, mism, faults, resets);
            if (dmism == 0 && mism == 0 && faults > 100 && resets > 5) $display("HOST_PHY_PIN_STAGE PASS"); else $display("HOST_PHY_PIN_STAGE FAIL");
            $finish;
        end
    end
endmodule
`default_nettype wire
