`timescale 1ns/1ps
// KV-SRAM-D2D 2026-10-19: FIRST-EPOCH GUARD bench of qkd_d2d_static_sfm (ordinary) / qkd_d2d_static_ovl_sfm (-DOVLM),
// NTX 3, PR 1, TXDP 0x03030416, FEG 1.  Four cold boots (POR + reset each), the image written through the real cfg pins:
//   A  TX entry 7 never written (63 + 2 writes), start 20 edges after the last write: the TX calendar must NOT start, must
//      fault (dut fault pin) and stay halted; the complete RX calendar starts (it is authorised on its own receipt).
//      Then the missing entry is written and a second start is issued: still no start (poisoned, never a queued retry).
//   B  complete image, start on the edge right after a calendar's last write (W+1 at that calendar): rejected, faults;
//      the other calendar (W+2 or later) is authorised.
//   C  complete image, start at W+2: both calendars run, no fault (the earliest authorised start; healthy path).
//   D  cold POR clears the receipt: after POR with no writes a start is rejected.
//   E  warm reset (rst_n only) keeps the unreset image and its receipt: a start after it is authorised.
//   F  the image written from the first edge after rst_n rises (inside the 4-edge local rst_n release window, as the
//      pair bench / DCAL cold INIT does) is accepted by the image and counted by the receipt.  Contract: POR is released
//      >= 6 edges before the first cfg write (the boot's rst_n follows POR); an earlier write is rejected (fail-stop).
// Prints GUARD_PASS or GUARD_FAIL <case>.  MUTFO_V 5 (TX guard disabled) must FAIL case A.
module tb;
`ifndef MUTFO_V
`define MUTFO_V 0
`endif
reg ck = 0; always #5 ck = ~ck;
localparam [31:0] TXDP = 32'h03030416;
reg por_n = 0, rst_n = 0, cfg_tx_we = 0, cfg_rx_we = 0; reg [5:0] cfg_addr = 0; reg [31:0] cfg_data = 0;
reg cal_start = 0, cal_seg = 0;
wire fault, epoch_abort; wire [16:0] z;
`ifdef OVLM
qkd_d2d_static_ovl_sfm #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP), .MUTFO(`MUTFO_V), .SRAMV(1), .FEG(1)) dut (
    .cal_start_rx(cal_start), .cal_seg_rx(cal_seg), .cal_user_tx(2'd0), .cal_user_rx(2'd0), .tx_user(), .rx_user(),
`else
qkd_d2d_static_sfm #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP), .MUTFO(`MUTFO_V), .SRAMV(1), .FEG(1)) dut (
`endif
    .ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
    .cal_start(cal_start), .cal_seg(cal_seg), .host_link_reset_req(1'b0), .host_recovery_clear(1'b0), .host_boot_begin(1'b0),
    .fwd_epoch(), .fwd_link_rst_n(), .att_tx_slot(), .att_tx_kind(), .att_tx_beat(), .att_tx_v(1'b0), .att_tx_payload(548'd0),
    .att_rx_v(), .att_rx_slot(), .att_rx_kind(), .att_rx_beat(), .rx_payload(), .rx_zero17(z), .emb_tx_slot(), .emb_tx_v(1'b0),
    .emb_tx_payload(548'd0), .record_tx_observed_v(1'b0), .record_tx(548'd0), .record_send_kind(), .record_witness_slot(),
    .record_rx_v(), .record_rx(), .kvn_compiled_identity(59'd0), .kvn_compiled_generation(2'd0), .kvn_word_valid(),
    .kvn_word_tag(), .kvn_word_data(), .kvn_word_identity(), .kvn_word_generation(), .kvn_word_slot(), .kvn_word_index(),
    .status_epoch16(16'd0), .serdes_up(1'b1), .kv_drained_local(1'b0), .kv_flush_local(1'b0), .host_drained_local(1'b0),
    .kv_active_local(1'b0), .link_up(), .transport_fault(), .native_links_drained(), .native_link_reset_seen(),
    .native_retrained(), .abort_drained(), .native_kv_drained(), .native_vm_drained(), .native_collective_drained(),
    .native_host_drained(), .native_collective_busy(), .native_kv_flush(), .native_admit_ready(), .crom_fault(),
    .execution_active(), .engine_result_v(), .engine_result_done(), .engine_result_fault(), .engine_result_cause(),
    .engine_result_tag(), .engine_result_gen(), .engine_result_token(), .engine_result_value(), .engine_result_cycles(),
    .fdi_tx_up(1'b1), .fdi_tx_v(), .fdi_tx_flit(), .fdi_rx_v(1'b0), .fdi_rx_flit(583'd0), .phy_rst_n(),
    .epoch_abort(epoch_abort), .recovery_cycles(), .fault(fault));
wire txrun = dut.u_core.u_end.u_txcal.running, rxrun = dut.u_core.u_end.u_rxcal.running;
wire txf = dut.u_core.u_end.u_txcal.fault, rxf = dut.u_core.u_end.u_rxcal.fault;
task tick(input integer n); repeat (n) @(negedge ck); endtask
task boot; begin por_n = 0; rst_n = 0; tick(4); por_n = 1; tick(2); rst_n = 1; tick(8); end endtask
// TX and RX table words: one 200-edge entry each, last bit set on entry 0 (a one-entry segment 0), base 2
task write_image(input integer skip_tx); integer i; begin
    for (i = 0; i < 32; i = i + 1) begin
        cfg_addr = i; cfg_data = {14'd200, (i == 0 || i == 2) ? 1'b1 : 1'b0, 3'd0, 4'd3, 5'd0, 5'd0};
        cfg_tx_we = (i != skip_tx); tick(1); cfg_tx_we = 0;
        cfg_rx_we = 1; tick(1); cfg_rx_we = 0;
    end
    cfg_addr = 6'd32; cfg_data = 32'd2; cfg_tx_we = 1; tick(1); cfg_tx_we = 0; cfg_rx_we = 1; tick(1); cfg_rx_we = 0;
end endtask
task start(input integer gap); begin tick(gap); cal_start = 1; cal_seg = 0; tick(1); cal_start = 0; end endtask
integer ran_tx, ran_rx, j;
task watch(input integer n); begin ran_tx = 0; ran_rx = 0;
    for (j = 0; j < n; j = j + 1) begin tick(1); if (txrun) ran_tx = 1; if (rxrun) ran_rx = 1; end end endtask
task fail(input [8*8-1:0] c); begin $display("GUARD_FAIL %0s tx_ran %0d rx_ran %0d txf %b rxf %b fault %b", c, ran_tx, ran_rx, txf, rxf, fault); $fatal(1); end endtask
initial begin
    // A: TX entry 7 missing; the last cfg write is the RX base; start 20 edges later
    boot; write_image(7); start(20); watch(40);
    if (ran_tx || !txf || !fault || !ran_rx || rxf) fail("A");
    cfg_addr = 7; cfg_data = {14'd200, 1'b0, 3'd0, 4'd3, 5'd0, 5'd0}; cfg_tx_we = 1; tick(1); cfg_tx_we = 0;
    tick(300); start(20); watch(40);
    if (ran_tx || !txf) fail("A2");
    $display("GUARD case A: missing entry -> no TX start, TX fault, RX authorised; no retry after the late write");
    // B: start on the edge right after the RX calendar's last write (RX sees W+1, TX W+2): RX rejected, TX authorised
    boot; write_image(-1); start(0); watch(40);
    if (!ran_tx || ran_rx || txf || !rxf) fail("B");
    // B2: a TX entry rewrite last, start on the next edge (TX sees W+1, RX W+3): TX rejected, RX authorised
    boot; write_image(-1); cfg_addr = 5; cfg_data = {14'd200, 1'b0, 3'd0, 4'd3, 5'd0, 5'd0}; cfg_tx_we = 1; tick(1); cfg_tx_we = 0;
    start(0); watch(40);
    if (ran_tx || !ran_rx || !txf || rxf) fail("B2");
    $display("GUARD case B: a start at W+1 is rejected per calendar (RX in B, TX in B2), W+2 / W+3 authorised");
    // C: start at W+2
    boot; write_image(-1); start(1); watch(40);
    if (!ran_tx || !ran_rx || txf || rxf || fault) fail("C");
    $display("GUARD case C: start at W+2 runs both calendars, no fault");
    // D: reset clears the receipt
    boot; start(5); watch(40);
    if (ran_tx || ran_rx || !txf || !rxf) fail("D");
    $display("GUARD case D: cold POR clears the receipt (start without image rejected)");
    // E: complete image, warm reset (rst_n only; the unreset image is kept, as is its receipt): start at W+2 after reset
    boot; write_image(-1); rst_n = 0; tick(4); rst_n = 1; tick(8); start(1); watch(40);
    if (!ran_tx || !ran_rx || txf || rxf || fault) fail("E");
    // F: image written inside the local rst_n release window (the cold boot's timing) is accepted and counted
    por_n = 0; rst_n = 0; tick(4); por_n = 1; tick(6); rst_n = 1; write_image(-1); start(1); watch(40);
    if (!ran_tx || !ran_rx || txf || rxf || fault) fail("F");
    $display("GUARD case E/F: warm reset keeps image + receipt; writes inside the reset release window are counted");
    $display("GUARD_PASS mutfo=%0d", `MUTFO_V);
    $finish;
end
endmodule
