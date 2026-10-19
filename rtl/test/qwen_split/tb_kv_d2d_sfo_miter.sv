`timescale 1ns/1ps
// KV-D2D 2026-10-19 (claude/kv-d2d-1019): LOCKSTEP MITER of the SAFE FAN-OUT KV link end against the as-built end.
//   ref : qkd_d2d_static    #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(0x03030416))          (-DOVLM: qkd_d2d_static_ovl)
//   dut : qkd_d2d_static_sf #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(0x03030416), .MUTFO)  (-DOVLM: qkd_d2d_static_ovl_sf)
// Every output bit is compared on every clock from cycle 8 on (RANDINIT: payload words only with their valid, and only
// through the legal lifecycle, because unreset payload / SRAM state legitimately differs between two random instances).
// Stimulus (both ends see the same inputs):
//   0..15      POR + reset
//   100..165   the EXACT production cold sequence (ot_qwen_d2d_cal_seq INIT): TX entry i at 100+2i, RX entry i at
//              101+2i (64 table words), then the TX segment-1 base (addr 32) at 164 and the RX base at 165 -- 66 writes;
//              program P1 = 32-beat port-0 bursts (the codec2 lifecycle program), segment-1 base 2
//   210        HOST boot (epoch strobe); 260 token start (segment 1); att producer answers its slots 20 edges later;
//              461..492 the 32 TX frames come back on the RX pins (RX calendar expects them); 600 an unexpected frame
//              aborts the epoch; 600..999 drain, HOST link reset, PHY down / retrain, recovery clear, second epoch
//   1000..2999 random inputs every edge (random image writes, bases, starts, halts, PHY, host) incl. reset at 1200
//   3000..3019 POR + reset; 3100..3165 a second exact 66-write cold sequence with the multi-entry program P2
//              (segments 0 = entries 0..9, 1 = base 12: entries 12..20, 21..31; bursts, TX port 0 answered by its producer at
//              the compiled capture edge, RX expectations answered in order with the transmitted frames);
//              3210 boot, 3260 / 3460 / 3660 starts (seg 0, seg 1, seg 1 after a base rewrite to 21 at 3640/3641)
//   3900..5999 random inputs again (reset at 4500)
// Coverage asserted: >= 2 epochs, drain / link reset / retrain / recovery, 32 golden RX frames, >= 32 TX frames,
// pointer advance across a segment (ptr >= 9 and a segment-1 run past entry 12) in BOTH ends' calendars.
// OT_FO_CHECK (run script): every copy register in the dut compares itself with its master on every edge and prints
// FO_COPY_MISMATCH (the run script fails on it).  With +verilator+rand+reset+2 this is the first-edge convergence proof.
module tb;
`ifndef MUTFO_V
`define MUTFO_V 0
`endif
reg ck = 0; always #5 ck = ~ck;
localparam [31:0] TXDP = 32'h03030416;
reg [582:0] frames [0:31];
integer epochs = 0, drained_seen = 0, reset_seen = 0, trained_seen = 0, recovery_seen = 0, early_seen = 0, stored = 0;
integer received = 0, cyc = 0, checks = 0, tx = 0, aborted = 0, p2_ev = 0, ptr_hi = 0, seg1_run = 0, mism = 0;
integer p2_tx = 0, p2_rx = 0, p2_rd = 0, p2_abort = 0; reg [582:0] p2f [0:255]; reg [1:0] emb_d = 0;
reg [19:0] slot_delay = 0;
reg por_n = 0, rst_n = 0, cfg_tx_we = 0, cfg_rx_we = 0; reg [5:0] cfg_addr = 0; reg [31:0] cfg_data = 0;
reg cal_start = 0, cal_seg = 0, cal_start_rx = 0, cal_seg_rx = 0; reg [1:0] cal_user_tx = 0, cal_user_rx = 0;
reg host_link_reset_req = 0, host_recovery_clear = 0, host_boot_begin = 0;
reg att_tx_v = 0; reg [547:0] att_tx_payload = 0; reg emb_tx_v = 0; reg [547:0] emb_tx_payload = 0;
reg record_tx_observed_v = 0; reg [547:0] record_tx = 0;
reg [58:0] kvn_compiled_identity = 0; reg [1:0] kvn_compiled_generation = 0; reg [15:0] status_epoch16 = 0;
reg serdes_up = 0, kv_drained_local = 0, kv_flush_local = 0, host_drained_local = 0, kv_active_local = 0;
reg fdi_tx_up = 0, fdi_rx_v = 0; reg [582:0] fdi_rx_flit = 0;
`define OUTS(P) \
wire P``fwd_epoch, P``fwd_link_rst_n, P``att_tx_slot, P``att_rx_v, P``att_rx_slot, P``emb_tx_slot, P``record_witness_slot; \
wire P``record_rx_v, P``kvn_word_valid, P``kvn_word_slot, P``native_links_drained, P``native_link_reset_seen; \
wire P``native_retrained, P``native_kv_drained, P``native_vm_drained, P``native_collective_drained, P``native_host_drained; \
wire P``native_collective_busy, P``native_kv_flush, P``native_admit_ready, P``crom_fault, P``execution_active; \
wire P``engine_result_v, P``engine_result_done, P``engine_result_fault, P``fdi_tx_v, P``phy_rst_n, P``epoch_abort, P``fault; \
wire [3:0] P``att_tx_kind, P``att_rx_kind, P``abort_drained, P``engine_result_cause; wire [4:0] P``att_tx_beat, P``att_rx_beat; \
wire [547:0] P``rx_payload, P``record_rx; wire [1:0] P``record_send_kind, P``kvn_word_index, P``kvn_word_generation; \
wire [10:0] P``kvn_word_tag; wire [511:0] P``kvn_word_data; wire [58:0] P``kvn_word_identity, P``engine_result_tag; \
wire [1:0] P``link_up, P``engine_result_gen, P``tx_user, P``rx_user; wire [7:0] P``transport_fault; wire [17:0] P``engine_result_token; \
wire [31:0] P``engine_result_value, P``engine_result_cycles, P``recovery_cycles; wire [582:0] P``fdi_tx_flit;
`OUTS(r_)
`OUTS(d_)
`define CONN(P) \
.ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data), \
.cal_start(cal_start), .cal_seg(cal_seg), .host_link_reset_req(host_link_reset_req), .host_recovery_clear(host_recovery_clear), \
.host_boot_begin(host_boot_begin), .fwd_epoch(P``fwd_epoch), .fwd_link_rst_n(P``fwd_link_rst_n), .att_tx_slot(P``att_tx_slot), \
.att_tx_kind(P``att_tx_kind), .att_tx_beat(P``att_tx_beat), .att_tx_v(att_tx_v), .att_tx_payload(att_tx_payload), \
.att_rx_v(P``att_rx_v), .att_rx_slot(P``att_rx_slot), .att_rx_kind(P``att_rx_kind), .att_rx_beat(P``att_rx_beat), \
.rx_payload(P``rx_payload), .emb_tx_slot(P``emb_tx_slot), .emb_tx_v(emb_tx_v), .emb_tx_payload(emb_tx_payload), \
.record_tx_observed_v(record_tx_observed_v), .record_tx(record_tx), .record_send_kind(P``record_send_kind), \
.record_witness_slot(P``record_witness_slot), .record_rx_v(P``record_rx_v), .record_rx(P``record_rx), \
.kvn_compiled_identity(kvn_compiled_identity), .kvn_compiled_generation(kvn_compiled_generation), \
.kvn_word_valid(P``kvn_word_valid), .kvn_word_tag(P``kvn_word_tag), .kvn_word_data(P``kvn_word_data), \
.kvn_word_identity(P``kvn_word_identity), .kvn_word_generation(P``kvn_word_generation), .kvn_word_slot(P``kvn_word_slot), \
.kvn_word_index(P``kvn_word_index), .status_epoch16(status_epoch16), .serdes_up(serdes_up), .kv_drained_local(kv_drained_local), \
.kv_flush_local(kv_flush_local), .host_drained_local(host_drained_local), .kv_active_local(kv_active_local), \
.link_up(P``link_up), .transport_fault(P``transport_fault), .native_links_drained(P``native_links_drained), \
.native_link_reset_seen(P``native_link_reset_seen), .native_retrained(P``native_retrained), .abort_drained(P``abort_drained), \
.native_kv_drained(P``native_kv_drained), .native_vm_drained(P``native_vm_drained), \
.native_collective_drained(P``native_collective_drained), .native_host_drained(P``native_host_drained), \
.native_collective_busy(P``native_collective_busy), .native_kv_flush(P``native_kv_flush), \
.native_admit_ready(P``native_admit_ready), .crom_fault(P``crom_fault), .execution_active(P``execution_active), \
.engine_result_v(P``engine_result_v), .engine_result_done(P``engine_result_done), .engine_result_fault(P``engine_result_fault), \
.engine_result_cause(P``engine_result_cause), .engine_result_tag(P``engine_result_tag), .engine_result_gen(P``engine_result_gen), \
.engine_result_token(P``engine_result_token), .engine_result_value(P``engine_result_value), \
.engine_result_cycles(P``engine_result_cycles), .fdi_tx_up(fdi_tx_up), .fdi_tx_v(P``fdi_tx_v), .fdi_tx_flit(P``fdi_tx_flit), \
.fdi_rx_v(fdi_rx_v), .fdi_rx_flit(fdi_rx_flit), .phy_rst_n(P``phy_rst_n), .epoch_abort(P``epoch_abort), \
.recovery_cycles(P``recovery_cycles), .fault(P``fault)
`ifdef OVLM
qkd_d2d_static_ovl #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP)) ref_dut (`CONN(r_), .cal_start_rx(cal_start_rx),
    .cal_seg_rx(cal_seg_rx), .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx), .tx_user(r_tx_user), .rx_user(r_rx_user));
qkd_d2d_static_ovl_sf #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP), .MUTFO(`MUTFO_V)) dut (`CONN(d_), .cal_start_rx(cal_start_rx),
    .cal_seg_rx(cal_seg_rx), .cal_user_tx(cal_user_tx), .cal_user_rx(cal_user_rx), .tx_user(d_tx_user), .rx_user(d_rx_user));
`else
assign r_tx_user = 2'd0; assign r_rx_user = 2'd0; assign d_tx_user = 2'd0; assign d_rx_user = 2'd0;
qkd_d2d_static #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP)) ref_dut (`CONN(r_));
qkd_d2d_static_sf #(.SAFE_RC(1), .NTX(3), .PR(1), .TXDP(TXDP), .MUTFO(`MUTFO_V)) dut (`CONN(d_));
`endif
`define CTRL(P) {P``fwd_epoch, P``fwd_link_rst_n, P``att_tx_slot, P``att_tx_kind, P``att_tx_beat, P``att_rx_v, P``att_rx_slot, \
P``att_rx_kind, P``att_rx_beat, P``emb_tx_slot, P``record_send_kind, P``record_witness_slot, P``record_rx_v, P``kvn_word_valid, \
P``kvn_word_slot, P``kvn_word_index, P``link_up, P``transport_fault, P``native_links_drained, P``native_link_reset_seen, \
P``native_retrained, P``abort_drained, P``native_kv_drained, P``native_vm_drained, P``native_collective_drained, \
P``native_host_drained, P``native_collective_busy, P``native_kv_flush, P``native_admit_ready, P``crom_fault, P``execution_active, \
P``engine_result_v, P``engine_result_done, P``engine_result_fault, P``engine_result_cause, P``engine_result_tag, \
P``engine_result_gen, P``engine_result_token, P``engine_result_value, P``engine_result_cycles, P``fdi_tx_v, P``phy_rst_n, \
P``epoch_abort, P``recovery_cycles, P``fault, P``tx_user, P``rx_user}
`define FULL(P) {`CTRL(P), P``rx_payload, P``record_rx, P``kvn_word_tag, P``kvn_word_data, P``kvn_word_identity, \
P``kvn_word_generation, P``fdi_tx_flit}
`ifdef RANDINIT
localparam integer CHECK_END = 1000;
wire same = (`CTRL(d_) === `CTRL(r_)) && (!r_fdi_tx_v || d_fdi_tx_flit === r_fdi_tx_flit) &&
            (!r_att_rx_v || d_rx_payload === r_rx_payload) && (!r_record_rx_v || d_record_rx === r_record_rx) &&
            (!r_kvn_word_valid || {d_kvn_word_tag, d_kvn_word_data, d_kvn_word_identity, d_kvn_word_generation} ===
                                  {r_kvn_word_tag, r_kvn_word_data, r_kvn_word_identity, r_kvn_word_generation});
`else
localparam integer CHECK_END = 1 << 30;
wire same = (`FULL(d_) === `FULL(r_));
`endif
// program P2 (multi-entry): entry fields {dt14, last1, port3, kind4, beat5, rep5}
function [31:0] p2tx(input integer i);
    p2tx = {14'(2 + i % 5), (i == 9 || i == 20 || i == 31) ? 1'b1 : 1'b0, 3'd0, 4'(i % 16), 5'(i % 8), 5'(i % 4)};
endfunction
function [31:0] p2rx(input integer i);
    p2rx = {(i == 0 || i == 12 || i == 21) ? 14'd60 : 14'(6 + i % 4), (i == 9 || i == 20 || i == 31) ? 1'b1 : 1'b0,
            3'((i + 1) % 4), 4'((i * 3) % 16), 5'(i % 5), 5'(i % 3)};
endfunction
task check; begin
    if (cyc >= 8 && cyc < CHECK_END) begin
        if (!same) begin
            mism = mism + 1;
            if (mism <= 5) $display("MISMATCH cycle %0d", cyc);
            if (mism == 5) begin $display("SFO_MITER_FAIL mismatches"); $fatal(1); end
        end
        checks = checks + 1;
    end
    if (cyc < 1000) begin
        if (r_fwd_epoch) epochs = epochs + 1;
        if (cyc > 600 && r_native_links_drained) drained_seen = 1;
        if (cyc > 600 && r_native_link_reset_seen) reset_seen = 1;
        if (cyc > 600 && r_native_retrained) trained_seen = 1;
        if (cyc > 600 && r_recovery_cycles != 0) recovery_seen = 1;
        if (cyc > 600 && r_transport_fault[3]) early_seen = 1;
        if (r_fdi_tx_v) begin tx = tx + 1; if (stored < 32) begin frames[stored] = r_fdi_tx_flit; stored = stored + 1; end end
        if (r_att_rx_v) begin
            received = received + 1;
            if (r_rx_payload !== {4'd0, {17{32'h12345678}}}) begin $display("SFO_MITER_FAIL RX_GOLDEN_DATA cycle %0d", cyc); $fatal(1); end
        end
    end
    if (cyc >= 3200 && cyc < 3900) begin
        if (r_att_tx_slot || r_emb_tx_slot || r_att_rx_slot) p2_ev = p2_ev + 1;
        if (r_fdi_tx_v) begin p2_tx = p2_tx + 1; if (p2_tx <= 256) p2f[p2_tx - 1] = r_fdi_tx_flit; end
        if ((r_epoch_abort || ref_dut.u_core.u_end.end_fault) && cyc > 3215) p2_abort = 1;
        if (ref_dut.u_core.u_end.u_txcal.ptr >= 9) ptr_hi = 1;
        if (ref_dut.u_core.u_end.u_txcal.ptr >= 14 && ref_dut.u_core.u_end.u_txcal.ptr <= 21) seg1_run = 1;
    end
    if (r_epoch_abort) aborted = aborted + 1;
end endtask
integer i;
initial begin
    for (cyc = 0; cyc < 6000; cyc = cyc + 1) begin
        @(negedge ck);
        cfg_tx_we = $random; cfg_rx_we = $random; cfg_addr = $random; cfg_data = $random;
        cal_start = $random; cal_seg = $random; cal_start_rx = $random; cal_seg_rx = $random;
        cal_user_tx = $random; cal_user_rx = $random;
        host_link_reset_req = $random; host_recovery_clear = $random; host_boot_begin = $random;
        att_tx_v = $random; emb_tx_v = $random; record_tx_observed_v = $random;
        for (i = 0; i < 18; i = i + 1) begin
            att_tx_payload[32*i +: 32] = $random; emb_tx_payload[32*i +: 32] = $random; record_tx[32*i +: 32] = $random;
        end
        for (i = 0; i < 19; i = i + 1) fdi_rx_flit[32*i +: 32] = $random;
        kvn_compiled_identity = {$random, $random}; kvn_compiled_generation = $random; status_epoch16 = $random;
        serdes_up = $random; kv_drained_local = $random; kv_flush_local = $random; host_drained_local = $random;
        kv_active_local = $random; fdi_tx_up = $random; fdi_rx_v = $random;
        por_n = (cyc >= 16 && !(cyc >= 3000 && cyc < 3020));
        rst_n = (cyc >= 16 && !(cyc >= 1200 && cyc < 1220) && !(cyc >= 3000 && cyc < 3020) && !(cyc >= 4500 && cyc < 4520));
        // ---- legal lifecycle windows: no stray control ----
        if (cyc < 1000 || (cyc >= 3000 && cyc < 3900)) begin
            cfg_tx_we = 0; cfg_rx_we = 0; cal_start = 0; cal_start_rx = 0; host_boot_begin = 0; host_link_reset_req = 0;
            host_recovery_clear = 0; att_tx_v = 0; emb_tx_v = 0; record_tx_observed_v = 0; fdi_rx_v = 0; fdi_tx_up = 1;
            cal_user_tx = 0; cal_user_rx = 0;
        end
        // ---- cold sequence 1 (program P1): 64 table words + TX / RX segment-1 bases ----
        if (cyc >= 100 && cyc < 164) begin
            cfg_tx_we = (cyc % 2 == 0); cfg_rx_we = (cyc % 2 == 1); cfg_addr = (cyc - 100) / 2;
            cfg_data = {(cyc % 2 == 0) ? 14'd40 : 14'd200, 1'b1, 3'd0, 4'd3, 5'd0, 5'd31};
        end
        if (cyc == 164 || cyc == 165) begin cfg_tx_we = (cyc == 164); cfg_rx_we = (cyc == 165); cfg_addr = 6'd32; cfg_data = 32'd2; end
        if (cyc >= 200 && cyc < 1000) begin
            cal_start = (cyc == 260); cal_seg = 1; cal_start_rx = (cyc == 260); cal_seg_rx = 1;
            host_boot_begin = (cyc == 210);
            att_tx_v = slot_delay[19]; slot_delay = {slot_delay[18:0], r_att_tx_slot}; att_tx_payload = {17{32'h12345678}};
        end
        if (cyc >= 461 && cyc < 493) begin fdi_rx_v = 1; fdi_rx_flit = frames[cyc - 461]; end
        if (cyc == 600) begin fdi_rx_v = 1; fdi_rx_flit = frames[0]; end
        if (cyc >= 600 && cyc < 1000) begin
            host_link_reset_req = (cyc >= 650 && cyc < 800); host_recovery_clear = (cyc == 750); fdi_tx_up = !(cyc >= 660 && cyc < 700);
        end
        // ---- cold sequence 2 (program P2) ----
        if (cyc >= 3100 && cyc < 3164) begin
            cfg_tx_we = (cyc % 2 == 0); cfg_rx_we = (cyc % 2 == 1); cfg_addr = (cyc - 3100) / 2;
            cfg_data = (cyc % 2 == 0) ? p2tx((cyc - 3100) / 2) : p2rx((cyc - 3100) / 2);
        end
        if (cyc == 3164 || cyc == 3165) begin cfg_tx_we = (cyc == 3164); cfg_rx_we = (cyc == 3165); cfg_addr = 6'd32; cfg_data = 32'd12; end
        if (cyc == 3640 || cyc == 3641) begin cfg_tx_we = (cyc == 3640); cfg_rx_we = (cyc == 3641); cfg_addr = 6'd32; cfg_data = 32'd21; end
        if (cyc >= 3200 && cyc < 3900) begin
            host_boot_begin = (cyc == 3210);
            cal_start = (cyc == 3260 || cyc == 3460 || cyc == 3660); cal_seg = (cyc != 3260);
            cal_start_rx = cal_start; cal_seg_rx = cal_seg; cal_user_tx = cyc[1:0]; cal_user_rx = cyc[2:1];
            // producers answer at the compiled capture edge (port 0: TXD 22 - 2 pin edges; port 2: TXD 3 - 2)
            att_tx_v = slot_delay[19]; slot_delay = {slot_delay[18:0], r_att_tx_slot};
            emb_tx_v = emb_d[0]; emb_d = {1'b0, r_emb_tx_slot};
            // the RX calendar's expectation fires at the next edge: present the next transmitted frame on the pins now
            if (ref_dut.u_core.u_end.u_rxcal.running && ref_dut.u_core.u_end.u_rxcal.cnt == 14'd1 &&
                !ref_dut.u_core.u_end.halt && p2_rd < p2_tx) begin
                fdi_rx_v = 1; fdi_rx_flit = p2f[p2_rd]; p2_rd = p2_rd + 1; p2_rx = p2_rx + 1;
            end
        end
        @(posedge ck); #1; check();
    end
    if (epochs < 2 || !drained_seen || !reset_seen || !trained_seen || !recovery_seen || !early_seen) begin
        $display("SFO_MITER_FAIL RECOVERY_COVERAGE epochs%0d drain%0d reset%0d train%0d rec%0d early%0d", epochs, drained_seen,
                 reset_seen, trained_seen, recovery_seen, early_seen);
        $fatal(1);
    end
    if (received != 32) begin $display("SFO_MITER_FAIL RX activity %0d expected 32", received); $fatal(1); end
    if (tx < 32) begin $display("SFO_MITER_FAIL TX activity %0d", tx); $fatal(1); end
    if (p2_ev < 40 || !ptr_hi || !seg1_run || p2_tx < 40 || p2_rx < 40 || p2_abort) begin
        $display("SFO_MITER_FAIL P2 coverage events %0d ptr_hi %0d seg1_run %0d tx %0d rx %0d abort %0d", p2_ev, ptr_hi,
                 seg1_run, p2_tx, p2_rx, p2_abort); $fatal(1);
    end
    if (mism != 0) begin $display("SFO_MITER_FAIL mismatches %0d", mism); $fatal(1); end
    $display("SFO_MITER_PASS checks=%0d tx=%0d rx=%0d epochs=%0d aborted=%0d p2_events=%0d p2_tx=%0d p2_rx=%0d", checks, tx,
             received, epochs, aborted, p2_ev, p2_tx, p2_rx);
    $finish;
end
endmodule
