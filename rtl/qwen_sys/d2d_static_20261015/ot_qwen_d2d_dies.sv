`timescale 1ns/1ps
// =====================================================================================================================
// Q-LINK 2026-10-15: die-name RTL of the static D2D link ends (owner no-stub rule: every die instance binds to real RTL
// under its die name). Both ends: PHY FDI 583 = slot-link frame (548 payload + 19 + CRC16), ot_qkvd_ucie_x64_phy.
//
// Port map (calendar port numbers; the compiler table tools/qwen_split/d2d_link_calendar.py uses the same numbers)
//   compute TX: 0 native59 typed548 CMD/Q (qfd_native59_compute_service, codec 1 edge)
//               1 program record kind 14 witness (qfd_program_record_port, codec 2 edges)
//               2 compute STATUS/RESULT kind 15 (ot_qwen_d2d_status_tx in this wrapper, 1 edge)
//               3 KVN kind 5 (qfd_kvn_static_transport slot -> x3 1 edge -> ot_qwen_d2d_kvn_tx 1 edge = 2 edges)
//   compute RX: 0 native59 RESULT/STATUS (kinds 3/4), 1 program record (kinds 12 context / 13 BEGIN+AUTH),
//               2 embedding row (kinds 6/7, 64 words per token, token run)
//   KV TX:      0 attention record RESULT/STATUS (qkd_native_attention_record KV_SIDE 1, 1 edge)
//               1 HOST record port kinds 12/13 (qkd_host_record_port, 2 edges)
//               2 embedding row kinds 6/7 (KV die embedding provider, 1 edge; token run)
//   KV RX:      0 attention CMD/Q, 1 HOST record kind 14 witness, 2 compute STATUS kind 15, 3 KVN kind 5
// =====================================================================================================================

// KVN record, kind 5: [547:543] epoch[12:8], [542:539] 5, [538:533] stage6, [532:522] tag11, [521:520] gen2,
// [519:512] epoch[7:0], [511:0] data. Token/position/segment of TAG59 are not carried: the KV side binds them to the
// compiled context (kind 12) and checks every carried field against it.
module ot_qwen_d2d_kvn_tx (
    input  wire         ck, rst_n,
    input  wire [523:0] x3,               // {v, tag11, data512} from qfd_kvn_static_transport
    input  wire [58:0]  x3_identity,      // TAG59 {epoch16, stage6, token18, position13, segment6}
    input  wire [1:0]   x3_generation,
    output reg          tx_valid,
    output reg  [547:0] tx_payload,
    output reg          fault
);
    wire [15:0] ep = x3_identity[58:43];
    wire [5:0]  sg = x3_identity[42:37];
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin tx_valid <= 0; tx_payload <= 0; fault <= 0; end
        else begin
            tx_valid <= x3[523];
            if (x3[523]) begin
                tx_payload <= {ep[12:8], 4'd5, sg, x3[522:512], x3_generation, ep[7:0], x3[511:0]};
                if (x3[522:520] != 3'd2 || ep[15:13] != 3'd0) fault <= 1'b1;   // KVN class only; epoch < 8192
            end
        end
endmodule

module ot_qwen_d2d_kvn_rx (
    input  wire         ck, rst_n,
    input  wire         rx_event, rx_slot,
    input  wire [4:0]   rx_beat,
    input  wire [547:0] rx_payload,
    input  wire [58:0]  compiled_identity,
    input  wire [1:0]   compiled_generation,
    output reg          word_valid,
    output reg  [10:0]  word_tag,
    output reg  [511:0] word_data,
    output reg  [58:0]  word_identity,
    output reg  [1:0]   word_generation,
    output reg          word_slot,         // compiled expectation, aligned with word_valid
    output reg  [1:0]   word_index,
    output reg          fault
);
    wire [15:0] cep = compiled_identity[58:43];
    wire bad = rx_payload[542:539] != 4'd5 || {rx_payload[547:543], rx_payload[519:512]} != cep[12:0] ||
               rx_payload[538:533] != compiled_identity[42:37] || rx_payload[521:520] != compiled_generation ||
               rx_payload[532:530] != 3'd2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            word_valid <= 0; word_tag <= 0; word_data <= 0; word_identity <= 0; word_generation <= 0;
            word_slot <= 0; word_index <= 0; fault <= 0;
        end else begin
            word_valid <= rx_event && !(bad || fault);
            word_slot <= rx_slot; word_index <= rx_beat[1:0];
            if (rx_event != rx_slot || (rx_event && bad)) fault <= 1'b1;
            if (rx_event) begin
                word_tag <= rx_payload[532:522]; word_data <= rx_payload[511:0];
                word_identity <= compiled_identity; word_generation <= rx_payload[521:520];
            end
        end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// COMPUTE die end (die name qfd_d2d_static; replaces qfd_d2d_rom = credit romlink + LLR, historical)
// ---------------------------------------------------------------------------------------------------------------------
module qfd_d2d_static_core #(parameter integer MUT = 0, parameter [31:0] TXDP = {8'd2, 8'd1, 8'd2, 8'd1}) (
    input  wire         ck,                              // core D2D clock (PLL core trunk, 1.2 GHz; one CTS root incl. the slot-store SRAMs)
    input  wire         por_n, rst_n,
    input  wire         cfg_tx_we, cfg_rx_we, input wire [5:0] cfg_addr, input wire [31:0] cfg_data,
    input  wire         cal_start,                       // compiled run start (compute ROM sequencer)
    input  wire         cal_seg,                         // 0 layer run, 1 token run (terminal RESULT / embedding row)
    input  wire         fwd_epoch,                       // forwarded epoch strobe bump (KV die)
    input  wire         fwd_link_rst_n,                  // forwarded link reset bump (KV die)
    // native59 typed548
    output wire         native_tx_slot, output wire [3:0] native_tx_slot_kind, output wire [4:0] native_tx_slot_beat,
    input  wire         native_tx_v, input wire [547:0] native_tx_payload,
    output wire [547:0] rx_payload,                      // checked RX word, shared by every RX port (valid per port)
    output wire         native_rx_v,
    output wire         native_rx_slot, output wire [3:0] native_rx_slot_kind, output wire [4:0] native_rx_slot_beat,
    // program record port
    output wire         prog_witness_slot, output wire prog_auth_slot, output wire prog_context_slot,
    input  wire         prog_tx_observed_v, input wire [547:0] prog_tx_record,
    output wire         prog_rx_v,
    // embedding row (RX port 2; kinds 6/7 = row words 0..31/32..63 from the KV die embedding provider)
    output wire         emb_rx_v, output wire emb_rx_slot,
    // KVN
    output wire         kv_x3_slot,
    input  wire [523:0] x3, input wire [58:0] x3_identity, input wire [1:0] x3_generation,
    // STATUS/RESULT producers (owners: Q-DVM vm_drained, Q-COLL collective_drained/busy, Q-COMPUTE crom_fault,
    // Q-FUNC execution_active/admit_ready/terminal result)
    input  wire [15:0]  status_epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire         result_v, result_done, result_fault, input wire [3:0] result_cause, input wire [58:0] result_tag,
    input  wire [1:0]   result_gen, input wire [17:0] result_token, input wire [31:0] result_value, result_cycles,
    // PHY FDI (ot_qkvd_ucie_x64_phy, 583)
    input  wire         fdi_tx_up, output wire fdi_tx_v, output wire [582:0] fdi_tx_flit,
    input  wire         fdi_rx_v, input wire [582:0] fdi_rx_flit,
    output wire         phy_rst_n,
    output wire         epoch_abort, output wire [7:0] transport_fault, output wire fault
);
    localparam integer FW = 548;
    wire [3:0] txs, rxe, rxs; wire [3:0] tk, rk; wire [4:0] tb, rb; wire [FW-1:0] rxp;
    wire [3:0] tv; wire [4*FW-1:0] tp;
    wire eb, ab, endf, own_rst_n, rec; wire [7:0] ep, fc;
    wire st_f, kvn_f;
    ot_qwen_d2d_recovery #(.MASTER(0)) u_rec (.ck(ck), .por_n(por_n), .rst_n(rst_n), .abort(ab | endf),
        .fault_cause(fc), .end_fault(endf), .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_rx_v(fdi_rx_v),
        .reset_req(1'b0), .recovery_clear(1'b0), .boot_begin(1'b0), .fwd_epoch_i(fwd_epoch), .fwd_epoch_o(),
        .fwd_link_rst_n(), .phy_rst_n(own_rst_n), .epoch_begin(eb), .epoch(ep), .link_up(), .links_drained(),
        .link_reset_seen(), .retrained(), .transport_fault(transport_fault), .recovering(rec), .recovery_cycles());
    assign phy_rst_n = own_rst_n & fwd_link_rst_n;
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD(TXDP), .MUT(MUT)) u_end (
        .ck({5{ck}}), .rst_n(rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .epoch_begin(eb), .epoch(ep), .cal_start(cal_start), .cal_seg(cal_seg),
        .tx_slot(txs), .tx_kind(tk), .tx_beat(tb), .tx_valid(tv), .tx_payload(tp),
        .rx_event(rxe), .rx_slot(rxs), .rx_kind(rk), .rx_beat(rb), .rx_payload(rxp),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .epoch_abort(ab), .fault_cause(fc), .end_fault(endf), .cal_running());
    assign epoch_abort = ab;
    // port 0 native59
    assign native_tx_slot = txs[0]; assign native_tx_slot_kind = tk; assign native_tx_slot_beat = tb;
    assign tv[0] = native_tx_v; assign tp[0 +: FW] = native_tx_payload;
    assign rx_payload = rxp;
    assign native_rx_v = rxe[0];
    assign native_rx_slot = rxs[0]; assign native_rx_slot_kind = rk; assign native_rx_slot_beat = rb;
    // port 1 program record
    assign prog_witness_slot = txs[1];
    assign tv[1] = prog_tx_observed_v; assign tp[FW +: FW] = prog_tx_record;
    assign prog_rx_v = rxe[1];
    // port 2 embedding row (consumer: compute SU embedding face, owner q_native_embedding / Q-COMPUTE)
    assign emb_rx_v = rxe[2]; assign emb_rx_slot = rxs[2];
    assign prog_auth_slot = rxs[1] && rk == 4'd13;
    assign prog_context_slot = rxs[1] && rk == 4'd12;
    // port 2 status/result
    ot_qwen_d2d_status_tx u_st (.ck(ck), .rst_n(rst_n & ~eb), .epoch16(status_epoch16),
        .vm_drained(vm_drained), .collective_drained(collective_drained), .collective_busy(collective_busy),
        .crom_fault(crom_fault), .execution_active(execution_active), .admit_ready(admit_ready),
        .result_v(result_v), .result_done(result_done), .result_fault(result_fault), .result_cause(result_cause),
        .result_tag(result_tag), .result_gen(result_gen), .result_token(result_token), .result_value(result_value),
        .result_cycles(result_cycles), .tx_slot(txs[2]), .tx_kind(tk), .tx_valid(tv[2]), .tx_payload(tp[2*FW +: FW]),
        .fault(st_f));
    // port 3 KVN
    assign kv_x3_slot = txs[3];
    ot_qwen_d2d_kvn_tx u_kvn (.ck(ck), .rst_n(rst_n & ~eb), .x3(x3), .x3_identity(x3_identity),
        .x3_generation(x3_generation), .tx_valid(tv[3]), .tx_payload(tp[3*FW +: FW]), .fault(kvn_f));
    assign fault = endf | st_f | kvn_f;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// KV/system die end (die name qkd_d2d_static; replaces qkd_d2d = ot_qkvd_kv_end + LLR, historical) + HOST services
// ---------------------------------------------------------------------------------------------------------------------
module qkd_d2d_static_core #(parameter integer MUT = 0, parameter integer NL = 2, parameter [31:0] TXDP = {8'd1, 8'd1, 8'd2, 8'd1}) (
    input  wire         ck,                              // core D2D clock (PLL core trunk, 1.2 GHz; one CTS root incl. the slot-store SRAMs)
    input  wire         por_n, rst_n,
    input  wire         cfg_tx_we, cfg_rx_we, input wire [5:0] cfg_addr, input wire [31:0] cfg_data,
    input  wire         cal_start,                       // compiled run start (KV sequencer)
    input  wire         cal_seg,                         // 0 layer run, 1 token run (terminal RESULT / embedding row)
    // HOST (qkd_host_root_pt) control of the exceptional mode
    input  wire         host_link_reset_req, host_recovery_clear, host_boot_begin,
    output wire         fwd_epoch, fwd_link_rst_n,       // bumps to the compute die
    // attention record (KV_SIDE 1)
    output wire         att_tx_slot, output wire [3:0] att_tx_kind, output wire [4:0] att_tx_beat,
    input  wire         att_tx_v, input wire [547:0] att_tx_payload,
    output wire         att_rx_v, output wire att_rx_slot, output wire [3:0] att_rx_kind, output wire [4:0] att_rx_beat,
    output wire [547:0] rx_payload,
    // embedding row (TX port 2; producer: KV die embedding provider, row staged before its compiled token run)
    output wire         emb_tx_slot,
    input  wire         emb_tx_v, input wire [547:0] emb_tx_payload,
    // HOST record port (to qkd_host_root_pt record_* ports)
    input  wire         record_tx_observed_v, input wire [547:0] record_tx,
    output wire [1:0]   record_send_kind, output wire record_witness_slot, record_rx_v, output wire [547:0] record_rx,
    // KVN to qkd_kv_static_writer_native
    input  wire [58:0]  kvn_compiled_identity, input wire [1:0] kvn_compiled_generation,
    output wire         kvn_word_valid, output wire [10:0] kvn_word_tag, output wire [511:0] kvn_word_data,
    output wire [58:0]  kvn_word_identity, output wire [1:0] kvn_word_generation,
    output wire         kvn_word_slot, output wire [1:0] kvn_word_index,
    // HOST root inputs produced here (see qkd_host_link_services)
    input  wire [15:0]  status_epoch16,
    input  wire         serdes_up, kv_drained_local, kv_flush_local, host_drained_local, kv_active_local,
    output wire [NL-1:0] link_up, output wire [7:0] transport_fault,
    output wire         native_links_drained, native_link_reset_seen, native_retrained,
    output wire [3:0]   abort_drained,
    output wire         native_kv_drained, native_vm_drained, native_collective_drained, native_host_drained,
    output wire         native_collective_busy, native_kv_flush, native_admit_ready, crom_fault, execution_active,
    output wire         engine_result_v, engine_result_done, engine_result_fault, output wire [3:0] engine_result_cause,
    output wire [58:0]  engine_result_tag, output wire [1:0] engine_result_gen, output wire [17:0] engine_result_token,
    output wire [31:0]  engine_result_value, engine_result_cycles,
    // PHY FDI (ot_qkvd_ucie_x64_phy, 583)
    input  wire         fdi_tx_up, output wire fdi_tx_v, output wire [582:0] fdi_tx_flit,
    input  wire         fdi_rx_v, input wire [582:0] fdi_rx_flit,
    output wire         phy_rst_n,
    output wire         epoch_abort, output wire [31:0] recovery_cycles, output wire fault
);
    localparam integer FW = 548;
    wire [3:0] txs, rxe, rxs; wire [3:0] tk, rk; wire [4:0] tb, rb; wire [FW-1:0] rxp;
    wire [3:0] tv; wire [4*FW-1:0] tp;
    wire eb, ab, endf, lu, dr, seen, rt, rec; wire [7:0] ep, fc, tf;
    wire s_vm, s_co, s_cb, s_cf, s_ea, s_ar, s_fr, s_f, kvn_f;
    ot_qwen_d2d_recovery #(.MASTER(1)) u_rec (.ck(ck), .por_n(por_n), .rst_n(rst_n), .abort(ab | endf),
        .fault_cause(fc), .end_fault(endf), .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_rx_v(fdi_rx_v),
        .reset_req(host_link_reset_req), .recovery_clear(host_recovery_clear), .boot_begin(host_boot_begin),
        .fwd_epoch_i(1'b0), .fwd_epoch_o(fwd_epoch), .fwd_link_rst_n(fwd_link_rst_n), .phy_rst_n(phy_rst_n),
        .epoch_begin(eb), .epoch(ep), .link_up(lu), .links_drained(dr), .link_reset_seen(seen), .retrained(rt),
        .transport_fault(tf), .recovering(rec), .recovery_cycles(recovery_cycles));
    ot_qwen_d2d_static_end #(.NT(4), .NR(4), .TXD(TXDP), .MUT(MUT)) u_end (
        .ck({5{ck}}), .rst_n(rst_n), .cfg_tx_we(cfg_tx_we), .cfg_rx_we(cfg_rx_we), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .epoch_begin(eb), .epoch(ep), .cal_start(cal_start), .cal_seg(cal_seg),
        .tx_slot(txs), .tx_kind(tk), .tx_beat(tb), .tx_valid(tv), .tx_payload(tp),
        .rx_event(rxe), .rx_slot(rxs), .rx_kind(rk), .rx_beat(rb), .rx_payload(rxp),
        .p_tx_up(fdi_tx_up), .p_tx_v(fdi_tx_v), .p_tx_flit(fdi_tx_flit), .p_rx_v(fdi_rx_v), .p_rx_flit(fdi_rx_flit),
        .epoch_abort(ab), .fault_cause(fc), .end_fault(endf), .cal_running());
    assign epoch_abort = ab;
    assign rx_payload = rxp;
    assign att_tx_slot = txs[0]; assign att_tx_kind = tk; assign att_tx_beat = tb;
    assign tv[0] = att_tx_v; assign tp[0 +: FW] = att_tx_payload;
    assign att_rx_v = rxe[0]; assign att_rx_slot = rxs[0]; assign att_rx_kind = rk; assign att_rx_beat = rb;
    assign tv[1] = record_tx_observed_v; assign tp[FW +: FW] = record_tx;
    // port 2 embedding row (codec latency 1: the provider's registered word one edge after emb_tx_slot)
    assign emb_tx_slot = txs[2];
    assign tv[2] = emb_tx_v; assign tp[2*FW +: FW] = emb_tx_payload;
    // port 3 carries no KV-die TX traffic in the compiled program: no producer, the end faults any stray valid
    assign tv[3] = 1'b0; assign tp[4*FW-1:3*FW] = {FW{1'b0}};
    ot_qwen_d2d_status_rx u_st (.ck(ck), .rst_n(rst_n), .epoch16(status_epoch16), .rx_event(rxe[2]), .rx_slot(rxs[2]),
        .rx_payload(rxp), .vm_drained(s_vm), .collective_drained(s_co), .collective_busy(s_cb), .crom_fault(s_cf),
        .execution_active(s_ea), .admit_ready(s_ar), .status_fresh(s_fr), .result_v(engine_result_v),
        .result_done(engine_result_done), .result_fault(engine_result_fault), .result_cause(engine_result_cause),
        .result_tag(engine_result_tag), .result_gen(engine_result_gen), .result_token(engine_result_token),
        .result_value(engine_result_value), .result_cycles(engine_result_cycles), .epoch_begin(eb), .fault(s_f));
    ot_qwen_d2d_kvn_rx u_kvn (.ck(ck), .rst_n(rst_n & ~eb), .rx_event(rxe[3]), .rx_slot(rxs[3]), .rx_beat(rb),
        .rx_payload(rxp), .compiled_identity(kvn_compiled_identity), .compiled_generation(kvn_compiled_generation),
        .word_valid(kvn_word_valid), .word_tag(kvn_word_tag), .word_data(kvn_word_data),
        .word_identity(kvn_word_identity), .word_generation(kvn_word_generation), .word_slot(kvn_word_slot),
        .word_index(kvn_word_index), .fault(kvn_f));
    qkd_host_link_services #(.NL(NL)) u_hls (.ck(ck), .rst_n(rst_n),
        .d2d_link_up(lu), .serdes_up(serdes_up), .d2d_transport_fault(tf), .d2d_links_drained(dr),
        .d2d_link_reset_seen(seen), .d2d_retrained(rt),
        .rec_tx_slot(txs[1]), .rec_tx_kind(tk), .rec_tx_beat(tb), .rec_rx_event(rxe[1]), .rec_rx_slot(rxs[1]),
        .rx_payload(rxp), .c_vm_drained(s_vm), .c_collective_drained(s_co), .c_collective_busy(s_cb),
        .c_crom_fault(s_cf), .c_execution_active(s_ea), .c_admit_ready(s_ar), .c_status_fresh(s_fr),
        .kv_drained_local(kv_drained_local), .kv_flush_local(kv_flush_local), .host_drained_local(host_drained_local),
        .kv_active_local(kv_active_local),
        .link_up(link_up), .transport_fault(transport_fault), .native_links_drained(native_links_drained),
        .native_link_reset_seen(native_link_reset_seen), .native_retrained(native_retrained),
        .abort_drained(abort_drained), .native_kv_drained(native_kv_drained), .native_vm_drained(native_vm_drained),
        .native_collective_drained(native_collective_drained), .native_host_drained(native_host_drained),
        .native_collective_busy(native_collective_busy), .native_kv_flush(native_kv_flush),
        .native_admit_ready(native_admit_ready), .crom_fault(crom_fault), .execution_active(execution_active),
        .record_send_kind(record_send_kind), .record_witness_slot(record_witness_slot), .record_rx_v(record_rx_v),
        .record_rx(record_rx));
    assign fault = endf | s_f | kvn_f;
endmodule

// ==== PINREG WRAPPERS (generated by tools/qwen_split/d2d_pinreg_gen.py; do not edit) ====

// Pin-registered die masters: every functional port has one flop at its pin (PR = 1, production).  The core

// producer capture latency is +2 per EXTERNAL port (slot out + payload in); the compute STATUS codec
// (port 2) is inside the core and keeps 1; see the generator docstring for the cost.

module qfd_d2d_static #(parameter integer MUT = 0, parameter integer PR = 1) (
    input  wire ck,
    input  wire por_n,
    input  wire rst_n,
    input  wire cfg_tx_we,
    input  wire cfg_rx_we,
    input  wire [5:0] cfg_addr,
    input  wire [31:0] cfg_data,
    input  wire cal_start,
    input  wire cal_seg,
    input  wire fwd_epoch,
    input  wire fwd_link_rst_n,
    output wire native_tx_slot,
    output wire [3:0] native_tx_slot_kind,
    output wire [4:0] native_tx_slot_beat,
    input  wire native_tx_v,
    input  wire [547:0] native_tx_payload,
    output wire [547:0] rx_payload,
    output wire native_rx_v,
    output wire native_rx_slot,
    output wire [3:0] native_rx_slot_kind,
    output wire [4:0] native_rx_slot_beat,
    output wire prog_witness_slot,
    output wire prog_auth_slot,
    output wire prog_context_slot,
    input  wire prog_tx_observed_v,
    input  wire [547:0] prog_tx_record,
    output wire prog_rx_v,
    output wire emb_rx_v,
    output wire emb_rx_slot,
    output wire kv_x3_slot,
    input  wire [523:0] x3,
    input  wire [58:0] x3_identity,
    input  wire [1:0] x3_generation,
    input  wire [15:0] status_epoch16,
    input  wire vm_drained,
    input  wire collective_drained,
    input  wire collective_busy,
    input  wire crom_fault,
    input  wire execution_active,
    input  wire admit_ready,
    input  wire result_v,
    input  wire result_done,
    input  wire result_fault,
    input  wire [3:0] result_cause,
    input  wire [58:0] result_tag,
    input  wire [1:0] result_gen,
    input  wire [17:0] result_token,
    input  wire [31:0] result_value,
    input  wire [31:0] result_cycles,
    input  wire fdi_tx_up,
    output wire fdi_tx_v,
    output wire [582:0] fdi_tx_flit,
    input  wire fdi_rx_v,
    input  wire [582:0] fdi_rx_flit,
    output wire phy_rst_n,
    output wire epoch_abort,
    output wire [7:0] transport_fault,
    output wire fault
);
    wire c_cfg_tx_we;
    reg q_cfg_tx_we;
    always @(posedge ck) q_cfg_tx_we <= cfg_tx_we;
    assign c_cfg_tx_we = PR ? q_cfg_tx_we : cfg_tx_we;
    wire c_cfg_rx_we;
    reg q_cfg_rx_we;
    always @(posedge ck) q_cfg_rx_we <= cfg_rx_we;
    assign c_cfg_rx_we = PR ? q_cfg_rx_we : cfg_rx_we;
    wire [5:0] c_cfg_addr;
    reg [5:0] q_cfg_addr;
    always @(posedge ck) q_cfg_addr <= cfg_addr;
    assign c_cfg_addr = PR ? q_cfg_addr : cfg_addr;
    wire [31:0] c_cfg_data;
    reg [31:0] q_cfg_data;
    always @(posedge ck) q_cfg_data <= cfg_data;
    assign c_cfg_data = PR ? q_cfg_data : cfg_data;
    wire c_cal_start;
    reg q_cal_start;
    always @(posedge ck) q_cal_start <= cal_start;
    assign c_cal_start = PR ? q_cal_start : cal_start;
    wire c_cal_seg;
    reg q_cal_seg;
    always @(posedge ck) q_cal_seg <= cal_seg;
    assign c_cal_seg = PR ? q_cal_seg : cal_seg;
    wire c_fwd_epoch;
    reg q_fwd_epoch;
    always @(posedge ck) q_fwd_epoch <= fwd_epoch;
    assign c_fwd_epoch = PR ? q_fwd_epoch : fwd_epoch;
    wire c_fwd_link_rst_n;
    reg q_fwd_link_rst_n;
    always @(posedge ck) q_fwd_link_rst_n <= fwd_link_rst_n;
    assign c_fwd_link_rst_n = PR ? q_fwd_link_rst_n : fwd_link_rst_n;
    wire c_native_tx_slot;
    reg q_native_tx_slot;
    always @(posedge ck) q_native_tx_slot <= c_native_tx_slot;
    assign native_tx_slot = PR ? q_native_tx_slot : c_native_tx_slot;
    wire [3:0] c_native_tx_slot_kind;
    reg [3:0] q_native_tx_slot_kind;
    always @(posedge ck) q_native_tx_slot_kind <= c_native_tx_slot_kind;
    assign native_tx_slot_kind = PR ? q_native_tx_slot_kind : c_native_tx_slot_kind;
    wire [4:0] c_native_tx_slot_beat;
    reg [4:0] q_native_tx_slot_beat;
    always @(posedge ck) q_native_tx_slot_beat <= c_native_tx_slot_beat;
    assign native_tx_slot_beat = PR ? q_native_tx_slot_beat : c_native_tx_slot_beat;
    wire c_native_tx_v;
    reg q_native_tx_v;
    always @(posedge ck) q_native_tx_v <= native_tx_v;
    assign c_native_tx_v = PR ? q_native_tx_v : native_tx_v;
    wire [547:0] c_native_tx_payload;
    reg [547:0] q_native_tx_payload;
    always @(posedge ck) q_native_tx_payload <= native_tx_payload;
    assign c_native_tx_payload = PR ? q_native_tx_payload : native_tx_payload;
    wire [547:0] c_rx_payload;
    reg [547:0] q_rx_payload;
    always @(posedge ck) q_rx_payload <= c_rx_payload;
    assign rx_payload = PR ? q_rx_payload : c_rx_payload;
    wire c_native_rx_v;
    reg q_native_rx_v;
    always @(posedge ck) q_native_rx_v <= c_native_rx_v;
    assign native_rx_v = PR ? q_native_rx_v : c_native_rx_v;
    wire c_native_rx_slot;
    reg q_native_rx_slot;
    always @(posedge ck) q_native_rx_slot <= c_native_rx_slot;
    assign native_rx_slot = PR ? q_native_rx_slot : c_native_rx_slot;
    wire [3:0] c_native_rx_slot_kind;
    reg [3:0] q_native_rx_slot_kind;
    always @(posedge ck) q_native_rx_slot_kind <= c_native_rx_slot_kind;
    assign native_rx_slot_kind = PR ? q_native_rx_slot_kind : c_native_rx_slot_kind;
    wire [4:0] c_native_rx_slot_beat;
    reg [4:0] q_native_rx_slot_beat;
    always @(posedge ck) q_native_rx_slot_beat <= c_native_rx_slot_beat;
    assign native_rx_slot_beat = PR ? q_native_rx_slot_beat : c_native_rx_slot_beat;
    wire c_prog_witness_slot;
    reg q_prog_witness_slot;
    always @(posedge ck) q_prog_witness_slot <= c_prog_witness_slot;
    assign prog_witness_slot = PR ? q_prog_witness_slot : c_prog_witness_slot;
    wire c_prog_auth_slot;
    reg q_prog_auth_slot;
    always @(posedge ck) q_prog_auth_slot <= c_prog_auth_slot;
    assign prog_auth_slot = PR ? q_prog_auth_slot : c_prog_auth_slot;
    wire c_prog_context_slot;
    reg q_prog_context_slot;
    always @(posedge ck) q_prog_context_slot <= c_prog_context_slot;
    assign prog_context_slot = PR ? q_prog_context_slot : c_prog_context_slot;
    wire c_prog_tx_observed_v;
    reg q_prog_tx_observed_v;
    always @(posedge ck) q_prog_tx_observed_v <= prog_tx_observed_v;
    assign c_prog_tx_observed_v = PR ? q_prog_tx_observed_v : prog_tx_observed_v;
    wire [547:0] c_prog_tx_record;
    reg [547:0] q_prog_tx_record;
    always @(posedge ck) q_prog_tx_record <= prog_tx_record;
    assign c_prog_tx_record = PR ? q_prog_tx_record : prog_tx_record;
    wire c_prog_rx_v;
    reg q_prog_rx_v;
    always @(posedge ck) q_prog_rx_v <= c_prog_rx_v;
    assign prog_rx_v = PR ? q_prog_rx_v : c_prog_rx_v;
    wire c_emb_rx_v;
    reg q_emb_rx_v;
    always @(posedge ck) q_emb_rx_v <= c_emb_rx_v;
    assign emb_rx_v = PR ? q_emb_rx_v : c_emb_rx_v;
    wire c_emb_rx_slot;
    reg q_emb_rx_slot;
    always @(posedge ck) q_emb_rx_slot <= c_emb_rx_slot;
    assign emb_rx_slot = PR ? q_emb_rx_slot : c_emb_rx_slot;
    wire c_kv_x3_slot;
    reg q_kv_x3_slot;
    always @(posedge ck) q_kv_x3_slot <= c_kv_x3_slot;
    assign kv_x3_slot = PR ? q_kv_x3_slot : c_kv_x3_slot;
    wire [523:0] c_x3;
    reg [523:0] q_x3;
    always @(posedge ck) q_x3 <= x3;
    assign c_x3 = PR ? q_x3 : x3;
    wire [58:0] c_x3_identity;
    reg [58:0] q_x3_identity;
    always @(posedge ck) q_x3_identity <= x3_identity;
    assign c_x3_identity = PR ? q_x3_identity : x3_identity;
    wire [1:0] c_x3_generation;
    reg [1:0] q_x3_generation;
    always @(posedge ck) q_x3_generation <= x3_generation;
    assign c_x3_generation = PR ? q_x3_generation : x3_generation;
    wire [15:0] c_status_epoch16;
    reg [15:0] q_status_epoch16;
    always @(posedge ck) q_status_epoch16 <= status_epoch16;
    assign c_status_epoch16 = PR ? q_status_epoch16 : status_epoch16;
    wire c_vm_drained;
    reg q_vm_drained;
    always @(posedge ck) q_vm_drained <= vm_drained;
    assign c_vm_drained = PR ? q_vm_drained : vm_drained;
    wire c_collective_drained;
    reg q_collective_drained;
    always @(posedge ck) q_collective_drained <= collective_drained;
    assign c_collective_drained = PR ? q_collective_drained : collective_drained;
    wire c_collective_busy;
    reg q_collective_busy;
    always @(posedge ck) q_collective_busy <= collective_busy;
    assign c_collective_busy = PR ? q_collective_busy : collective_busy;
    wire c_crom_fault;
    reg q_crom_fault;
    always @(posedge ck) q_crom_fault <= crom_fault;
    assign c_crom_fault = PR ? q_crom_fault : crom_fault;
    wire c_execution_active;
    reg q_execution_active;
    always @(posedge ck) q_execution_active <= execution_active;
    assign c_execution_active = PR ? q_execution_active : execution_active;
    wire c_admit_ready;
    reg q_admit_ready;
    always @(posedge ck) q_admit_ready <= admit_ready;
    assign c_admit_ready = PR ? q_admit_ready : admit_ready;
    wire c_result_v;
    reg q_result_v;
    always @(posedge ck) q_result_v <= result_v;
    assign c_result_v = PR ? q_result_v : result_v;
    wire c_result_done;
    reg q_result_done;
    always @(posedge ck) q_result_done <= result_done;
    assign c_result_done = PR ? q_result_done : result_done;
    wire c_result_fault;
    reg q_result_fault;
    always @(posedge ck) q_result_fault <= result_fault;
    assign c_result_fault = PR ? q_result_fault : result_fault;
    wire [3:0] c_result_cause;
    reg [3:0] q_result_cause;
    always @(posedge ck) q_result_cause <= result_cause;
    assign c_result_cause = PR ? q_result_cause : result_cause;
    wire [58:0] c_result_tag;
    reg [58:0] q_result_tag;
    always @(posedge ck) q_result_tag <= result_tag;
    assign c_result_tag = PR ? q_result_tag : result_tag;
    wire [1:0] c_result_gen;
    reg [1:0] q_result_gen;
    always @(posedge ck) q_result_gen <= result_gen;
    assign c_result_gen = PR ? q_result_gen : result_gen;
    wire [17:0] c_result_token;
    reg [17:0] q_result_token;
    always @(posedge ck) q_result_token <= result_token;
    assign c_result_token = PR ? q_result_token : result_token;
    wire [31:0] c_result_value;
    reg [31:0] q_result_value;
    always @(posedge ck) q_result_value <= result_value;
    assign c_result_value = PR ? q_result_value : result_value;
    wire [31:0] c_result_cycles;
    reg [31:0] q_result_cycles;
    always @(posedge ck) q_result_cycles <= result_cycles;
    assign c_result_cycles = PR ? q_result_cycles : result_cycles;
    wire c_fdi_tx_up;
    reg q_fdi_tx_up;
    always @(posedge ck) q_fdi_tx_up <= fdi_tx_up;
    assign c_fdi_tx_up = PR ? q_fdi_tx_up : fdi_tx_up;
    wire c_fdi_tx_v;
    reg q_fdi_tx_v;
    always @(posedge ck) q_fdi_tx_v <= c_fdi_tx_v;
    assign fdi_tx_v = PR ? q_fdi_tx_v : c_fdi_tx_v;
    wire [582:0] c_fdi_tx_flit;
    reg [582:0] q_fdi_tx_flit;
    always @(posedge ck) q_fdi_tx_flit <= c_fdi_tx_flit;
    assign fdi_tx_flit = PR ? q_fdi_tx_flit : c_fdi_tx_flit;
    wire c_fdi_rx_v;
    reg q_fdi_rx_v;
    always @(posedge ck) q_fdi_rx_v <= fdi_rx_v;
    assign c_fdi_rx_v = PR ? q_fdi_rx_v : fdi_rx_v;
    wire [582:0] c_fdi_rx_flit;
    reg [582:0] q_fdi_rx_flit;
    always @(posedge ck) q_fdi_rx_flit <= fdi_rx_flit;
    assign c_fdi_rx_flit = PR ? q_fdi_rx_flit : fdi_rx_flit;
    wire c_phy_rst_n;
    reg q_phy_rst_n;
    always @(posedge ck) q_phy_rst_n <= c_phy_rst_n;
    assign phy_rst_n = PR ? q_phy_rst_n : c_phy_rst_n;
    wire c_epoch_abort;
    reg q_epoch_abort;
    always @(posedge ck) q_epoch_abort <= c_epoch_abort;
    assign epoch_abort = PR ? q_epoch_abort : c_epoch_abort;
    wire [7:0] c_transport_fault;
    reg [7:0] q_transport_fault;
    always @(posedge ck) q_transport_fault <= c_transport_fault;
    assign transport_fault = PR ? q_transport_fault : c_transport_fault;
    wire c_fault;
    reg q_fault;
    always @(posedge ck) q_fault <= c_fault;
    assign fault = PR ? q_fault : c_fault;
    qfd_d2d_static_core #(.MUT(MUT), .TXDP(PR ? {8'd4, 8'd1, 8'd3, 8'd3} : {8'd2, 8'd1, 8'd2, 8'd1})) u_core (.ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(c_cfg_tx_we), .cfg_rx_we(c_cfg_rx_we), .cfg_addr(c_cfg_addr), .cfg_data(c_cfg_data), .cal_start(c_cal_start), .cal_seg(c_cal_seg), .fwd_epoch(c_fwd_epoch), .fwd_link_rst_n(c_fwd_link_rst_n), .native_tx_slot(c_native_tx_slot), .native_tx_slot_kind(c_native_tx_slot_kind), .native_tx_slot_beat(c_native_tx_slot_beat), .native_tx_v(c_native_tx_v), .native_tx_payload(c_native_tx_payload), .rx_payload(c_rx_payload), .native_rx_v(c_native_rx_v), .native_rx_slot(c_native_rx_slot), .native_rx_slot_kind(c_native_rx_slot_kind), .native_rx_slot_beat(c_native_rx_slot_beat), .prog_witness_slot(c_prog_witness_slot), .prog_auth_slot(c_prog_auth_slot), .prog_context_slot(c_prog_context_slot), .prog_tx_observed_v(c_prog_tx_observed_v), .prog_tx_record(c_prog_tx_record), .prog_rx_v(c_prog_rx_v), .emb_rx_v(c_emb_rx_v), .emb_rx_slot(c_emb_rx_slot), .kv_x3_slot(c_kv_x3_slot), .x3(c_x3), .x3_identity(c_x3_identity), .x3_generation(c_x3_generation), .status_epoch16(c_status_epoch16), .vm_drained(c_vm_drained), .collective_drained(c_collective_drained), .collective_busy(c_collective_busy), .crom_fault(c_crom_fault), .execution_active(c_execution_active), .admit_ready(c_admit_ready), .result_v(c_result_v), .result_done(c_result_done), .result_fault(c_result_fault), .result_cause(c_result_cause), .result_tag(c_result_tag), .result_gen(c_result_gen), .result_token(c_result_token), .result_value(c_result_value), .result_cycles(c_result_cycles), .fdi_tx_up(c_fdi_tx_up), .fdi_tx_v(c_fdi_tx_v), .fdi_tx_flit(c_fdi_tx_flit), .fdi_rx_v(c_fdi_rx_v), .fdi_rx_flit(c_fdi_rx_flit), .phy_rst_n(c_phy_rst_n), .epoch_abort(c_epoch_abort), .transport_fault(c_transport_fault), .fault(c_fault));
endmodule

module qkd_d2d_static #(parameter integer MUT = 0, parameter integer NL = 2, parameter integer PR = 1) (
    input  wire ck,
    input  wire por_n,
    input  wire rst_n,
    input  wire cfg_tx_we,
    input  wire cfg_rx_we,
    input  wire [5:0] cfg_addr,
    input  wire [31:0] cfg_data,
    input  wire cal_start,
    input  wire cal_seg,
    input  wire host_link_reset_req,
    input  wire host_recovery_clear,
    input  wire host_boot_begin,
    output wire fwd_epoch,
    output wire fwd_link_rst_n,
    output wire att_tx_slot,
    output wire [3:0] att_tx_kind,
    output wire [4:0] att_tx_beat,
    input  wire att_tx_v,
    input  wire [547:0] att_tx_payload,
    output wire att_rx_v,
    output wire att_rx_slot,
    output wire [3:0] att_rx_kind,
    output wire [4:0] att_rx_beat,
    output wire [547:0] rx_payload,
    output wire emb_tx_slot,
    input  wire emb_tx_v,
    input  wire [547:0] emb_tx_payload,
    input  wire record_tx_observed_v,
    input  wire [547:0] record_tx,
    output wire [1:0] record_send_kind,
    output wire record_witness_slot,
    output wire record_rx_v,
    output wire [547:0] record_rx,
    input  wire [58:0] kvn_compiled_identity,
    input  wire [1:0] kvn_compiled_generation,
    output wire kvn_word_valid,
    output wire [10:0] kvn_word_tag,
    output wire [511:0] kvn_word_data,
    output wire [58:0] kvn_word_identity,
    output wire [1:0] kvn_word_generation,
    output wire kvn_word_slot,
    output wire [1:0] kvn_word_index,
    input  wire [15:0] status_epoch16,
    input  wire serdes_up,
    input  wire kv_drained_local,
    input  wire kv_flush_local,
    input  wire host_drained_local,
    input  wire kv_active_local,
    output wire [NL-1:0] link_up,
    output wire [7:0] transport_fault,
    output wire native_links_drained,
    output wire native_link_reset_seen,
    output wire native_retrained,
    output wire [3:0] abort_drained,
    output wire native_kv_drained,
    output wire native_vm_drained,
    output wire native_collective_drained,
    output wire native_host_drained,
    output wire native_collective_busy,
    output wire native_kv_flush,
    output wire native_admit_ready,
    output wire crom_fault,
    output wire execution_active,
    output wire engine_result_v,
    output wire engine_result_done,
    output wire engine_result_fault,
    output wire [3:0] engine_result_cause,
    output wire [58:0] engine_result_tag,
    output wire [1:0] engine_result_gen,
    output wire [17:0] engine_result_token,
    output wire [31:0] engine_result_value,
    output wire [31:0] engine_result_cycles,
    input  wire fdi_tx_up,
    output wire fdi_tx_v,
    output wire [582:0] fdi_tx_flit,
    input  wire fdi_rx_v,
    input  wire [582:0] fdi_rx_flit,
    output wire phy_rst_n,
    output wire epoch_abort,
    output wire [31:0] recovery_cycles,
    output wire fault
);
    wire c_cfg_tx_we;
    reg q_cfg_tx_we;
    always @(posedge ck) q_cfg_tx_we <= cfg_tx_we;
    assign c_cfg_tx_we = PR ? q_cfg_tx_we : cfg_tx_we;
    wire c_cfg_rx_we;
    reg q_cfg_rx_we;
    always @(posedge ck) q_cfg_rx_we <= cfg_rx_we;
    assign c_cfg_rx_we = PR ? q_cfg_rx_we : cfg_rx_we;
    wire [5:0] c_cfg_addr;
    reg [5:0] q_cfg_addr;
    always @(posedge ck) q_cfg_addr <= cfg_addr;
    assign c_cfg_addr = PR ? q_cfg_addr : cfg_addr;
    wire [31:0] c_cfg_data;
    reg [31:0] q_cfg_data;
    always @(posedge ck) q_cfg_data <= cfg_data;
    assign c_cfg_data = PR ? q_cfg_data : cfg_data;
    wire c_cal_start;
    reg q_cal_start;
    always @(posedge ck) q_cal_start <= cal_start;
    assign c_cal_start = PR ? q_cal_start : cal_start;
    wire c_cal_seg;
    reg q_cal_seg;
    always @(posedge ck) q_cal_seg <= cal_seg;
    assign c_cal_seg = PR ? q_cal_seg : cal_seg;
    wire c_host_link_reset_req;
    reg q_host_link_reset_req;
    always @(posedge ck) q_host_link_reset_req <= host_link_reset_req;
    assign c_host_link_reset_req = PR ? q_host_link_reset_req : host_link_reset_req;
    wire c_host_recovery_clear;
    reg q_host_recovery_clear;
    always @(posedge ck) q_host_recovery_clear <= host_recovery_clear;
    assign c_host_recovery_clear = PR ? q_host_recovery_clear : host_recovery_clear;
    wire c_host_boot_begin;
    reg q_host_boot_begin;
    always @(posedge ck) q_host_boot_begin <= host_boot_begin;
    assign c_host_boot_begin = PR ? q_host_boot_begin : host_boot_begin;
    wire c_fwd_epoch;
    reg q_fwd_epoch;
    always @(posedge ck) q_fwd_epoch <= c_fwd_epoch;
    assign fwd_epoch = PR ? q_fwd_epoch : c_fwd_epoch;
    wire c_fwd_link_rst_n;
    reg q_fwd_link_rst_n;
    always @(posedge ck) q_fwd_link_rst_n <= c_fwd_link_rst_n;
    assign fwd_link_rst_n = PR ? q_fwd_link_rst_n : c_fwd_link_rst_n;
    wire c_att_tx_slot;
    reg q_att_tx_slot;
    always @(posedge ck) q_att_tx_slot <= c_att_tx_slot;
    assign att_tx_slot = PR ? q_att_tx_slot : c_att_tx_slot;
    wire [3:0] c_att_tx_kind;
    reg [3:0] q_att_tx_kind;
    always @(posedge ck) q_att_tx_kind <= c_att_tx_kind;
    assign att_tx_kind = PR ? q_att_tx_kind : c_att_tx_kind;
    wire [4:0] c_att_tx_beat;
    reg [4:0] q_att_tx_beat;
    always @(posedge ck) q_att_tx_beat <= c_att_tx_beat;
    assign att_tx_beat = PR ? q_att_tx_beat : c_att_tx_beat;
    wire c_att_tx_v;
    reg q_att_tx_v;
    always @(posedge ck) q_att_tx_v <= att_tx_v;
    assign c_att_tx_v = PR ? q_att_tx_v : att_tx_v;
    wire [547:0] c_att_tx_payload;
    reg [547:0] q_att_tx_payload;
    always @(posedge ck) q_att_tx_payload <= att_tx_payload;
    assign c_att_tx_payload = PR ? q_att_tx_payload : att_tx_payload;
    wire c_att_rx_v;
    reg q_att_rx_v;
    always @(posedge ck) q_att_rx_v <= c_att_rx_v;
    assign att_rx_v = PR ? q_att_rx_v : c_att_rx_v;
    wire c_att_rx_slot;
    reg q_att_rx_slot;
    always @(posedge ck) q_att_rx_slot <= c_att_rx_slot;
    assign att_rx_slot = PR ? q_att_rx_slot : c_att_rx_slot;
    wire [3:0] c_att_rx_kind;
    reg [3:0] q_att_rx_kind;
    always @(posedge ck) q_att_rx_kind <= c_att_rx_kind;
    assign att_rx_kind = PR ? q_att_rx_kind : c_att_rx_kind;
    wire [4:0] c_att_rx_beat;
    reg [4:0] q_att_rx_beat;
    always @(posedge ck) q_att_rx_beat <= c_att_rx_beat;
    assign att_rx_beat = PR ? q_att_rx_beat : c_att_rx_beat;
    wire [547:0] c_rx_payload;
    reg [547:0] q_rx_payload;
    always @(posedge ck) q_rx_payload <= c_rx_payload;
    assign rx_payload = PR ? q_rx_payload : c_rx_payload;
    wire c_emb_tx_slot;
    reg q_emb_tx_slot;
    always @(posedge ck) q_emb_tx_slot <= c_emb_tx_slot;
    assign emb_tx_slot = PR ? q_emb_tx_slot : c_emb_tx_slot;
    wire c_emb_tx_v;
    reg q_emb_tx_v;
    always @(posedge ck) q_emb_tx_v <= emb_tx_v;
    assign c_emb_tx_v = PR ? q_emb_tx_v : emb_tx_v;
    wire [547:0] c_emb_tx_payload;
    reg [547:0] q_emb_tx_payload;
    always @(posedge ck) q_emb_tx_payload <= emb_tx_payload;
    assign c_emb_tx_payload = PR ? q_emb_tx_payload : emb_tx_payload;
    wire c_record_tx_observed_v;
    reg q_record_tx_observed_v;
    always @(posedge ck) q_record_tx_observed_v <= record_tx_observed_v;
    assign c_record_tx_observed_v = PR ? q_record_tx_observed_v : record_tx_observed_v;
    wire [547:0] c_record_tx;
    reg [547:0] q_record_tx;
    always @(posedge ck) q_record_tx <= record_tx;
    assign c_record_tx = PR ? q_record_tx : record_tx;
    wire [1:0] c_record_send_kind;
    reg [1:0] q_record_send_kind;
    always @(posedge ck) q_record_send_kind <= c_record_send_kind;
    assign record_send_kind = PR ? q_record_send_kind : c_record_send_kind;
    wire c_record_witness_slot;
    reg q_record_witness_slot;
    always @(posedge ck) q_record_witness_slot <= c_record_witness_slot;
    assign record_witness_slot = PR ? q_record_witness_slot : c_record_witness_slot;
    wire c_record_rx_v;
    reg q_record_rx_v;
    always @(posedge ck) q_record_rx_v <= c_record_rx_v;
    assign record_rx_v = PR ? q_record_rx_v : c_record_rx_v;
    wire [547:0] c_record_rx;
    reg [547:0] q_record_rx;
    always @(posedge ck) q_record_rx <= c_record_rx;
    assign record_rx = PR ? q_record_rx : c_record_rx;
    wire [58:0] c_kvn_compiled_identity;
    reg [58:0] q_kvn_compiled_identity;
    always @(posedge ck) q_kvn_compiled_identity <= kvn_compiled_identity;
    assign c_kvn_compiled_identity = PR ? q_kvn_compiled_identity : kvn_compiled_identity;
    wire [1:0] c_kvn_compiled_generation;
    reg [1:0] q_kvn_compiled_generation;
    always @(posedge ck) q_kvn_compiled_generation <= kvn_compiled_generation;
    assign c_kvn_compiled_generation = PR ? q_kvn_compiled_generation : kvn_compiled_generation;
    wire c_kvn_word_valid;
    reg q_kvn_word_valid;
    always @(posedge ck) q_kvn_word_valid <= c_kvn_word_valid;
    assign kvn_word_valid = PR ? q_kvn_word_valid : c_kvn_word_valid;
    wire [10:0] c_kvn_word_tag;
    reg [10:0] q_kvn_word_tag;
    always @(posedge ck) q_kvn_word_tag <= c_kvn_word_tag;
    assign kvn_word_tag = PR ? q_kvn_word_tag : c_kvn_word_tag;
    wire [511:0] c_kvn_word_data;
    reg [511:0] q_kvn_word_data;
    always @(posedge ck) q_kvn_word_data <= c_kvn_word_data;
    assign kvn_word_data = PR ? q_kvn_word_data : c_kvn_word_data;
    wire [58:0] c_kvn_word_identity;
    reg [58:0] q_kvn_word_identity;
    always @(posedge ck) q_kvn_word_identity <= c_kvn_word_identity;
    assign kvn_word_identity = PR ? q_kvn_word_identity : c_kvn_word_identity;
    wire [1:0] c_kvn_word_generation;
    reg [1:0] q_kvn_word_generation;
    always @(posedge ck) q_kvn_word_generation <= c_kvn_word_generation;
    assign kvn_word_generation = PR ? q_kvn_word_generation : c_kvn_word_generation;
    wire c_kvn_word_slot;
    reg q_kvn_word_slot;
    always @(posedge ck) q_kvn_word_slot <= c_kvn_word_slot;
    assign kvn_word_slot = PR ? q_kvn_word_slot : c_kvn_word_slot;
    wire [1:0] c_kvn_word_index;
    reg [1:0] q_kvn_word_index;
    always @(posedge ck) q_kvn_word_index <= c_kvn_word_index;
    assign kvn_word_index = PR ? q_kvn_word_index : c_kvn_word_index;
    wire [15:0] c_status_epoch16;
    reg [15:0] q_status_epoch16;
    always @(posedge ck) q_status_epoch16 <= status_epoch16;
    assign c_status_epoch16 = PR ? q_status_epoch16 : status_epoch16;
    wire c_serdes_up;
    reg q_serdes_up;
    always @(posedge ck) q_serdes_up <= serdes_up;
    assign c_serdes_up = PR ? q_serdes_up : serdes_up;
    wire c_kv_drained_local;
    reg q_kv_drained_local;
    always @(posedge ck) q_kv_drained_local <= kv_drained_local;
    assign c_kv_drained_local = PR ? q_kv_drained_local : kv_drained_local;
    wire c_kv_flush_local;
    reg q_kv_flush_local;
    always @(posedge ck) q_kv_flush_local <= kv_flush_local;
    assign c_kv_flush_local = PR ? q_kv_flush_local : kv_flush_local;
    wire c_host_drained_local;
    reg q_host_drained_local;
    always @(posedge ck) q_host_drained_local <= host_drained_local;
    assign c_host_drained_local = PR ? q_host_drained_local : host_drained_local;
    wire c_kv_active_local;
    reg q_kv_active_local;
    always @(posedge ck) q_kv_active_local <= kv_active_local;
    assign c_kv_active_local = PR ? q_kv_active_local : kv_active_local;
    wire [NL-1:0] c_link_up;
    reg [NL-1:0] q_link_up;
    always @(posedge ck) q_link_up <= c_link_up;
    assign link_up = PR ? q_link_up : c_link_up;
    wire [7:0] c_transport_fault;
    reg [7:0] q_transport_fault;
    always @(posedge ck) q_transport_fault <= c_transport_fault;
    assign transport_fault = PR ? q_transport_fault : c_transport_fault;
    wire c_native_links_drained;
    reg q_native_links_drained;
    always @(posedge ck) q_native_links_drained <= c_native_links_drained;
    assign native_links_drained = PR ? q_native_links_drained : c_native_links_drained;
    wire c_native_link_reset_seen;
    reg q_native_link_reset_seen;
    always @(posedge ck) q_native_link_reset_seen <= c_native_link_reset_seen;
    assign native_link_reset_seen = PR ? q_native_link_reset_seen : c_native_link_reset_seen;
    wire c_native_retrained;
    reg q_native_retrained;
    always @(posedge ck) q_native_retrained <= c_native_retrained;
    assign native_retrained = PR ? q_native_retrained : c_native_retrained;
    wire [3:0] c_abort_drained;
    reg [3:0] q_abort_drained;
    always @(posedge ck) q_abort_drained <= c_abort_drained;
    assign abort_drained = PR ? q_abort_drained : c_abort_drained;
    wire c_native_kv_drained;
    reg q_native_kv_drained;
    always @(posedge ck) q_native_kv_drained <= c_native_kv_drained;
    assign native_kv_drained = PR ? q_native_kv_drained : c_native_kv_drained;
    wire c_native_vm_drained;
    reg q_native_vm_drained;
    always @(posedge ck) q_native_vm_drained <= c_native_vm_drained;
    assign native_vm_drained = PR ? q_native_vm_drained : c_native_vm_drained;
    wire c_native_collective_drained;
    reg q_native_collective_drained;
    always @(posedge ck) q_native_collective_drained <= c_native_collective_drained;
    assign native_collective_drained = PR ? q_native_collective_drained : c_native_collective_drained;
    wire c_native_host_drained;
    reg q_native_host_drained;
    always @(posedge ck) q_native_host_drained <= c_native_host_drained;
    assign native_host_drained = PR ? q_native_host_drained : c_native_host_drained;
    wire c_native_collective_busy;
    reg q_native_collective_busy;
    always @(posedge ck) q_native_collective_busy <= c_native_collective_busy;
    assign native_collective_busy = PR ? q_native_collective_busy : c_native_collective_busy;
    wire c_native_kv_flush;
    reg q_native_kv_flush;
    always @(posedge ck) q_native_kv_flush <= c_native_kv_flush;
    assign native_kv_flush = PR ? q_native_kv_flush : c_native_kv_flush;
    wire c_native_admit_ready;
    reg q_native_admit_ready;
    always @(posedge ck) q_native_admit_ready <= c_native_admit_ready;
    assign native_admit_ready = PR ? q_native_admit_ready : c_native_admit_ready;
    wire c_crom_fault;
    reg q_crom_fault;
    always @(posedge ck) q_crom_fault <= c_crom_fault;
    assign crom_fault = PR ? q_crom_fault : c_crom_fault;
    wire c_execution_active;
    reg q_execution_active;
    always @(posedge ck) q_execution_active <= c_execution_active;
    assign execution_active = PR ? q_execution_active : c_execution_active;
    wire c_engine_result_v;
    reg q_engine_result_v;
    always @(posedge ck) q_engine_result_v <= c_engine_result_v;
    assign engine_result_v = PR ? q_engine_result_v : c_engine_result_v;
    wire c_engine_result_done;
    reg q_engine_result_done;
    always @(posedge ck) q_engine_result_done <= c_engine_result_done;
    assign engine_result_done = PR ? q_engine_result_done : c_engine_result_done;
    wire c_engine_result_fault;
    reg q_engine_result_fault;
    always @(posedge ck) q_engine_result_fault <= c_engine_result_fault;
    assign engine_result_fault = PR ? q_engine_result_fault : c_engine_result_fault;
    wire [3:0] c_engine_result_cause;
    reg [3:0] q_engine_result_cause;
    always @(posedge ck) q_engine_result_cause <= c_engine_result_cause;
    assign engine_result_cause = PR ? q_engine_result_cause : c_engine_result_cause;
    wire [58:0] c_engine_result_tag;
    reg [58:0] q_engine_result_tag;
    always @(posedge ck) q_engine_result_tag <= c_engine_result_tag;
    assign engine_result_tag = PR ? q_engine_result_tag : c_engine_result_tag;
    wire [1:0] c_engine_result_gen;
    reg [1:0] q_engine_result_gen;
    always @(posedge ck) q_engine_result_gen <= c_engine_result_gen;
    assign engine_result_gen = PR ? q_engine_result_gen : c_engine_result_gen;
    wire [17:0] c_engine_result_token;
    reg [17:0] q_engine_result_token;
    always @(posedge ck) q_engine_result_token <= c_engine_result_token;
    assign engine_result_token = PR ? q_engine_result_token : c_engine_result_token;
    wire [31:0] c_engine_result_value;
    reg [31:0] q_engine_result_value;
    always @(posedge ck) q_engine_result_value <= c_engine_result_value;
    assign engine_result_value = PR ? q_engine_result_value : c_engine_result_value;
    wire [31:0] c_engine_result_cycles;
    reg [31:0] q_engine_result_cycles;
    always @(posedge ck) q_engine_result_cycles <= c_engine_result_cycles;
    assign engine_result_cycles = PR ? q_engine_result_cycles : c_engine_result_cycles;
    wire c_fdi_tx_up;
    reg q_fdi_tx_up;
    always @(posedge ck) q_fdi_tx_up <= fdi_tx_up;
    assign c_fdi_tx_up = PR ? q_fdi_tx_up : fdi_tx_up;
    wire c_fdi_tx_v;
    reg q_fdi_tx_v;
    always @(posedge ck) q_fdi_tx_v <= c_fdi_tx_v;
    assign fdi_tx_v = PR ? q_fdi_tx_v : c_fdi_tx_v;
    wire [582:0] c_fdi_tx_flit;
    reg [582:0] q_fdi_tx_flit;
    always @(posedge ck) q_fdi_tx_flit <= c_fdi_tx_flit;
    assign fdi_tx_flit = PR ? q_fdi_tx_flit : c_fdi_tx_flit;
    wire c_fdi_rx_v;
    reg q_fdi_rx_v;
    always @(posedge ck) q_fdi_rx_v <= fdi_rx_v;
    assign c_fdi_rx_v = PR ? q_fdi_rx_v : fdi_rx_v;
    wire [582:0] c_fdi_rx_flit;
    reg [582:0] q_fdi_rx_flit;
    always @(posedge ck) q_fdi_rx_flit <= fdi_rx_flit;
    assign c_fdi_rx_flit = PR ? q_fdi_rx_flit : fdi_rx_flit;
    wire c_phy_rst_n;
    reg q_phy_rst_n;
    always @(posedge ck) q_phy_rst_n <= c_phy_rst_n;
    assign phy_rst_n = PR ? q_phy_rst_n : c_phy_rst_n;
    wire c_epoch_abort;
    reg q_epoch_abort;
    always @(posedge ck) q_epoch_abort <= c_epoch_abort;
    assign epoch_abort = PR ? q_epoch_abort : c_epoch_abort;
    wire [31:0] c_recovery_cycles;
    reg [31:0] q_recovery_cycles;
    always @(posedge ck) q_recovery_cycles <= c_recovery_cycles;
    assign recovery_cycles = PR ? q_recovery_cycles : c_recovery_cycles;
    wire c_fault;
    reg q_fault;
    always @(posedge ck) q_fault <= c_fault;
    assign fault = PR ? q_fault : c_fault;
    qkd_d2d_static_core #(.MUT(MUT), .NL(NL), .TXDP(PR ? {8'd3, 8'd3, 8'd4, 8'd3} : {8'd1, 8'd1, 8'd2, 8'd1})) u_core (.ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(c_cfg_tx_we), .cfg_rx_we(c_cfg_rx_we), .cfg_addr(c_cfg_addr), .cfg_data(c_cfg_data), .cal_start(c_cal_start), .cal_seg(c_cal_seg), .host_link_reset_req(c_host_link_reset_req), .host_recovery_clear(c_host_recovery_clear), .host_boot_begin(c_host_boot_begin), .fwd_epoch(c_fwd_epoch), .fwd_link_rst_n(c_fwd_link_rst_n), .att_tx_slot(c_att_tx_slot), .att_tx_kind(c_att_tx_kind), .att_tx_beat(c_att_tx_beat), .att_tx_v(c_att_tx_v), .att_tx_payload(c_att_tx_payload), .att_rx_v(c_att_rx_v), .att_rx_slot(c_att_rx_slot), .att_rx_kind(c_att_rx_kind), .att_rx_beat(c_att_rx_beat), .rx_payload(c_rx_payload), .emb_tx_slot(c_emb_tx_slot), .emb_tx_v(c_emb_tx_v), .emb_tx_payload(c_emb_tx_payload), .record_tx_observed_v(c_record_tx_observed_v), .record_tx(c_record_tx), .record_send_kind(c_record_send_kind), .record_witness_slot(c_record_witness_slot), .record_rx_v(c_record_rx_v), .record_rx(c_record_rx), .kvn_compiled_identity(c_kvn_compiled_identity), .kvn_compiled_generation(c_kvn_compiled_generation), .kvn_word_valid(c_kvn_word_valid), .kvn_word_tag(c_kvn_word_tag), .kvn_word_data(c_kvn_word_data), .kvn_word_identity(c_kvn_word_identity), .kvn_word_generation(c_kvn_word_generation), .kvn_word_slot(c_kvn_word_slot), .kvn_word_index(c_kvn_word_index), .status_epoch16(c_status_epoch16), .serdes_up(c_serdes_up), .kv_drained_local(c_kv_drained_local), .kv_flush_local(c_kv_flush_local), .host_drained_local(c_host_drained_local), .kv_active_local(c_kv_active_local), .link_up(c_link_up), .transport_fault(c_transport_fault), .native_links_drained(c_native_links_drained), .native_link_reset_seen(c_native_link_reset_seen), .native_retrained(c_native_retrained), .abort_drained(c_abort_drained), .native_kv_drained(c_native_kv_drained), .native_vm_drained(c_native_vm_drained), .native_collective_drained(c_native_collective_drained), .native_host_drained(c_native_host_drained), .native_collective_busy(c_native_collective_busy), .native_kv_flush(c_native_kv_flush), .native_admit_ready(c_native_admit_ready), .crom_fault(c_crom_fault), .execution_active(c_execution_active), .engine_result_v(c_engine_result_v), .engine_result_done(c_engine_result_done), .engine_result_fault(c_engine_result_fault), .engine_result_cause(c_engine_result_cause), .engine_result_tag(c_engine_result_tag), .engine_result_gen(c_engine_result_gen), .engine_result_token(c_engine_result_token), .engine_result_value(c_engine_result_value), .engine_result_cycles(c_engine_result_cycles), .fdi_tx_up(c_fdi_tx_up), .fdi_tx_v(c_fdi_tx_v), .fdi_tx_flit(c_fdi_tx_flit), .fdi_rx_v(c_fdi_rx_v), .fdi_rx_flit(c_fdi_rx_flit), .phy_rst_n(c_phy_rst_n), .epoch_abort(c_epoch_abort), .recovery_cycles(c_recovery_cycles), .fault(c_fault));
endmodule
