`timescale 1ns/1ps
// TOKEN-PASS-HBMDS (10-18): d4g die layer vehicle, stage 0 = the WHOLE generated die top (hbm_v16_die, GEN2 smoke
// netlist, tools/hbm_die_v16/contract_die_v.py) elaborated and clocked under Verilator with only off-chip models:
//   - HBM PHY ot_hbm3e_phy_rc_e8p5: (* blackbox *) macro abstract (stage 0: no DRAM model behind it, outputs undriven);
//   - PLL ot_hbm_pll_bb: behavioural PLL model (rtl/hbm_accel/control/tb_hfd_ckgen.sv), refclk 100 MHz;
//   - SerDes / UCIe PMA: the far end of every die link is quiet (rx 0, rck free-running at the link clock).
// Stage 0 answers: does the die RTL of record elaborate + build as ONE design, what does a build cost (wall, RSS),
// and does it come out of reset without an X / fault (static-assert modules elaborate).  Layer stages (programme
// images from the compiler's static schedule, results/rtl/hbm_ds_layer_tput_1018/priced_layers.json) plug in at the
// host PMA (host_N) once the die's programme loaders exist (pre.json gaps G-SU-PROG-HOST, G-SFU-LOADER-*,
// G-HOST-LOADER-CAL/SVG, G-CIL-IDXCP/AMCP).  Plusargs: +CYCLES=<stream edges after reset> (default 4000).
module tb_hbm_d4g_die_vehicle;
    reg refclk = 1'b0, por_n = 1'b0;
    always #5 refclk = ~refclk;
    reg lrck = 1'b0;
    always #0.416667 lrck = ~lrck;
    wire [543:0] s0_tx, s1_tx, s3_tx, n0_tx, n2_tx;
    wire s0_tck, s1_tck, s3_tck, n0_tck, n2_tck, h_tck;
    wire [512:0] h_tx;
    hbm_v16_die dut (
        .hb_ckgen__refclk(refclk), .hb_ckgen__por_n(por_n),
        .lk_S0__pma_tx(s0_tx), .lk_S0__pma_tck(s0_tck), .lk_S0__pma_rx(544'd0), .lk_S0__pma_rck(lrck),
        .lk_S1__pma_tx(s1_tx), .lk_S1__pma_tck(s1_tck), .lk_S1__pma_rx(544'd0), .lk_S1__pma_rck(lrck),
        .lk_S3__pma_tx(s3_tx), .lk_S3__pma_tck(s3_tck), .lk_S3__pma_rx(544'd0), .lk_S3__pma_rck(lrck),
        .lk_N0__pma_tx(n0_tx), .lk_N0__pma_tck(n0_tck), .lk_N0__pma_rx(544'd0), .lk_N0__pma_rck(lrck),
        .lk_N2__pma_tx(n2_tx), .lk_N2__pma_tck(n2_tck), .lk_N2__pma_rx(544'd0), .lk_N2__pma_rck(lrck),
        .host_N__pma_tx(h_tx), .host_N__pma_tck(h_tck), .host_N__pma_rx(513'd0), .host_N__pma_rck(lrck),
        .host_cp_rxs__session(8'd0));
    wire sclk = dut.hb_ckgen__pll_stream;
    wire srst = dut.hb_ckgen__por_stream;
    integer edges = 0, cycles = 4000, t_rel = -1;
    integer tx_toggles = 0;
    reg [543:0] s0_prev = 0;
    real t0;
    initial begin
        if (!$value$plusargs("CYCLES=%d", cycles)) cycles = 4000;
        t0 = $realtime;
        #100 por_n = 1'b1;
    end
    always @(posedge sclk) begin
        if (srst) begin
            if (t_rel < 0) begin t_rel = edges; $display("VEHICLE_RESET_RELEASE stream_edge=%0d t=%0t", edges, $time); end
            if (s0_tx !== s0_prev) tx_toggles = tx_toggles + 1;
            s0_prev <= s0_tx;
        end
        edges = edges + 1;
        if (t_rel >= 0 && edges - t_rel >= cycles) begin
            if (^h_tx === 1'bx || ^s0_tx === 1'bx) begin
                $display("VEHICLE_FAIL X on a die output after %0d edges", cycles);
                $fatal(1, "X");
            end
            $display("VEHICLE_STAGE0_PASS die=hbm_v16_die edges_after_reset=%0d link_s0_tx_changes=%0d", cycles, tx_toggles);
            $finish;
        end
    end
    initial begin
        #2000000;
        $display("VEHICLE_FAIL no stream reset release / timeout");
        $fatal(1, "timeout");
    end
endmodule
