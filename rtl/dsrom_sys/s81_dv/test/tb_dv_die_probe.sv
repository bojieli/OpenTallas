`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// TOKEN-PASS-S81 (2026-10-18): tb_dv_die_probe -- FULL-RTL elaboration + idle-run cost probe of the CURRENT S81 die
// (p4l bind9 dv_die: 40 masters, 7,489 instances, strict DIE_PORT_BIND PASS; die top + RTL closure from
// tools/die_port_bind.py --elab-out).  NOT a layer run: there is no DV-die layer program (no compiler emits the seq_host
// calendar / CTL templates / frame cfg7 programs / svc + gunit jobs for a layer yet), so this bench only measures what a
// per-layer die vehicle will cost: Verilator build wall / memory and simulated die cycles per wall second after reset.
// All 25 region clocks are driven by one bench clock (functional sim: landings are fixed-latency, skew is a timing
// question); PMA rx lanes idle (off-die boundary, modelled).  Checks: land_fault stays 0 through NCYC idle cycles.
// ---------------------------------------------------------------------------------------------------------------------
module tb_dv_die_probe;
    parameter integer NRST = 64;
    integer NCYC = 2000;   // +NCYC=<n>
    reg ck = 1'b0; always #0.4165 ck = ~ck;
    reg rst_n = 1'b0;
    wire [512:0] lk_WS0_pma_tx;
    wire [0:0] lk_WS0_pma_tck;
    wire [512:0] lk_WS0_pma_rx = 0;
    wire [0:0] lk_WS0_pma_rck = 0;
    wire [543:0] lk_WS1_pma_tx;
    wire [0:0] lk_WS1_pma_tck;
    wire [543:0] lk_WS1_pma_rx = 0;
    wire [0:0] lk_WS1_pma_rck = 0;
    wire [543:0] lk_WN0_pma_tx;
    wire [0:0] lk_WN0_pma_tck;
    wire [543:0] lk_WN0_pma_rx = 0;
    wire [0:0] lk_WN0_pma_rck = 0;
    wire [543:0] lk_WN1_pma_tx;
    wire [0:0] lk_WN1_pma_tck;
    wire [543:0] lk_WN1_pma_rx = 0;
    wire [0:0] lk_WN1_pma_rck = 0;
    wire [512:0] lk_ES0_pma_tx;
    wire [0:0] lk_ES0_pma_tck;
    wire [512:0] lk_ES0_pma_rx = 0;
    wire [0:0] lk_ES0_pma_rck = 0;
    wire [543:0] lk_ES1_pma_tx;
    wire [0:0] lk_ES1_pma_tck;
    wire [543:0] lk_ES1_pma_rx = 0;
    wire [0:0] lk_ES1_pma_rck = 0;
    wire [543:0] lk_EN0_pma_tx;
    wire [0:0] lk_EN0_pma_tck;
    wire [543:0] lk_EN0_pma_rx = 0;
    wire [0:0] lk_EN0_pma_rck = 0;
    wire [543:0] lk_EN1_pma_tx;
    wire [0:0] lk_EN1_pma_tck;
    wire [543:0] lk_EN1_pma_rx = 0;
    wire [0:0] lk_EN1_pma_rck = 0;
    wire [223:0] land_fault;
    dv_die u_die (.ck_cl0N(ck), .ck_cl0S(ck), .ck_cl1N(ck), .ck_cl1S(ck), .ck_cl2N(ck), .ck_cl2S(ck), .ck_cl3N(ck), .ck_cl3S(ck), .ck_cl4N(ck), .ck_cl4S(ck), .ck_cl5N(ck), .ck_cl5S(ck), .ck_cl6N(ck), .ck_cl6S(ck), .ck_cl7N(ck), .ck_cl7S(ck), .ck_edge0(ck), .ck_edge8(ck), .ck_south2(ck), .ck_south3(ck), .ck_south4(ck), .ck_south5(ck), .ck_void1(ck), .ck_void3(ck), .ck_void4(ck), .rst_n(rst_n), .lk_WS0_pma_tx(lk_WS0_pma_tx), .lk_WS0_pma_tck(lk_WS0_pma_tck), .lk_WS0_pma_rx(lk_WS0_pma_rx), .lk_WS0_pma_rck(lk_WS0_pma_rck), .lk_WS1_pma_tx(lk_WS1_pma_tx), .lk_WS1_pma_tck(lk_WS1_pma_tck), .lk_WS1_pma_rx(lk_WS1_pma_rx), .lk_WS1_pma_rck(lk_WS1_pma_rck), .lk_WN0_pma_tx(lk_WN0_pma_tx), .lk_WN0_pma_tck(lk_WN0_pma_tck), .lk_WN0_pma_rx(lk_WN0_pma_rx), .lk_WN0_pma_rck(lk_WN0_pma_rck), .lk_WN1_pma_tx(lk_WN1_pma_tx), .lk_WN1_pma_tck(lk_WN1_pma_tck), .lk_WN1_pma_rx(lk_WN1_pma_rx), .lk_WN1_pma_rck(lk_WN1_pma_rck), .lk_ES0_pma_tx(lk_ES0_pma_tx), .lk_ES0_pma_tck(lk_ES0_pma_tck), .lk_ES0_pma_rx(lk_ES0_pma_rx), .lk_ES0_pma_rck(lk_ES0_pma_rck), .lk_ES1_pma_tx(lk_ES1_pma_tx), .lk_ES1_pma_tck(lk_ES1_pma_tck), .lk_ES1_pma_rx(lk_ES1_pma_rx), .lk_ES1_pma_rck(lk_ES1_pma_rck), .lk_EN0_pma_tx(lk_EN0_pma_tx), .lk_EN0_pma_tck(lk_EN0_pma_tck), .lk_EN0_pma_rx(lk_EN0_pma_rx), .lk_EN0_pma_rck(lk_EN0_pma_rck), .lk_EN1_pma_tx(lk_EN1_pma_tx), .lk_EN1_pma_tck(lk_EN1_pma_tck), .lk_EN1_pma_rx(lk_EN1_pma_rx), .lk_EN1_pma_rck(lk_EN1_pma_rck), .land_fault(land_fault));
    integer cyc = 0, txa = 0, flt = 0;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (rst_n && (|land_fault)) flt <= flt + 1;
        if (rst_n && ((|lk_WS0_pma_tx) || (|lk_WS1_pma_tx) || (|lk_WN0_pma_tx) || (|lk_WN1_pma_tx) || (|lk_ES0_pma_tx) || (|lk_ES1_pma_tx) || (|lk_EN0_pma_tx) || (|lk_EN1_pma_tx))) txa <= txa + 1;
    end
    initial begin
        if (!$value$plusargs("NCYC=%d", NCYC)) NCYC = 2000;
        repeat (NRST) @(posedge ck);
        $system("date +DV_DIE_PROBE_T0=%s.%N");
        rst_n = 1'b1;
        repeat (NCYC) @(posedge ck);
        $system("date +DV_DIE_PROBE_T1=%s.%N");
        $display("DV_DIE_PROBE cycles=%0d land_fault_cycles=%0d tx_active_cycles=%0d land_fault=%h", NCYC, flt, txa, land_fault);
        if (flt == 0) $display("TB_DV_DIE_PROBE PASS"); else $display("TB_DV_DIE_PROBE FAIL");
        $finish;
    end
endmodule
