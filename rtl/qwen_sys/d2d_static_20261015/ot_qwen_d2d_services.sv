`timescale 1ns/1ps
// =====================================================================================================================
// Q-LINK 2026-10-15: exceptional-mode recovery of the static D2D link, the forwarded epoch strobe, the compute-die
// STATUS/RESULT record (kind 15) and the KV/system-die HOST link-service collector (real producers of the HOST root
// inputs listed in results/arch/qwen_split_1014/kvsys_v1_4_candidate/host_bind_census.json that belong to the link).
// =====================================================================================================================

// ---------------------------------------------------------------------------------------------------------------------
// Recovery (KV/system die end = MASTER, compute die end = FOLLOWER). Explicit exceptional mode, never a normal path.
//   MASTER: abort -> DRAIN consecutive quiet PHY cycles (links_drained) -> HOST reset_req -> link reset of BOTH PHYs
//           (own PHY + forwarded link reset bump to the compute die) for RSTC cycles; link_reset_seen once own tx_up is
//           observed low -> release -> retrained once tx_up returns -> HOST recovery_clear -> forwarded epoch strobe:
//           local epoch_begin BUMP edges after launch, the compute die receives it after the same BUMP edges.
//   FOLLOWER: abort -> halt (end does it) -> epoch_begin = the forwarded strobe (fixed-latency capture flops).
// Epoch numbers: each end counts its own epoch_begin pulses from POR (por_n only), so both carry the same epoch.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_recovery #(
    parameter integer MASTER = 1, DRAIN = 32, RSTC = 16, BUMP = 3
) (
    input  wire       ck,
    input  wire       por_n,          // power-on only: epoch counter
    input  wire       rst_n,
    input  wire       abort,          // end epoch_abort | end_fault
    input  wire [7:0] fault_cause,
    input  wire       end_fault,
    input  wire       p_tx_up,
    input  wire       p_tx_v, p_rx_v,
    input  wire       reset_req,      // MASTER: HOST lifecycle link_reset_request (level, sampled in DRAINED)
    input  wire       recovery_clear, // MASTER: HOST recovery_complete after retrained (pulse)
    input  wire       boot_begin,     // MASTER: HOST boot_go (level; its rising edge starts the first epoch); FOLLOWER: unused
    input  wire       fwd_epoch_i,    // FOLLOWER: forwarded epoch strobe from the bump
    output wire       fwd_epoch_o,    // MASTER: forwarded epoch strobe to the bump (registered)
    output wire       fwd_link_rst_n, // MASTER: forwarded link reset to the compute die PHY (registered)
    output wire       phy_rst_n,      // own PHY reset
    output reg        epoch_begin,
    output reg  [7:0] epoch,
    output wire       link_up,
    output wire       links_drained,
    output wire       link_reset_seen,
    output wire       retrained,
    output reg  [7:0] transport_fault,// typed, sticky until the next epoch_begin
    output wire       recovering,
    output reg  [31:0] recovery_cycles // measured length of the last exceptional episode (abort -> epoch_begin)
);
    localparam [2:0] S_RUN = 0, S_DRAIN = 1, S_DRAINED = 2, S_RST = 3, S_TRAIN = 4, S_READY = 5;
    reg [2:0] st; reg [15:0] n; reg seen, lrst, fep, bq;
    reg [BUMP-1:0] eq;            // MASTER local copy of the forwarded strobe delay
    reg [BUMP-1:0] fq;            // FOLLOWER capture flops
    reg counting;
    assign fwd_epoch_o = fep;
    assign fwd_link_rst_n = ~lrst;
    assign phy_rst_n = rst_n & ~lrst;
    assign links_drained = (st == S_DRAINED) || (st == S_RST) || (st == S_TRAIN) || (st == S_READY);
    assign link_reset_seen = seen;
    assign retrained = (st == S_READY);
    assign recovering = (st != S_RUN);
    assign link_up = p_tx_up && (st == S_RUN) && !abort;
    wire begin_now = MASTER ? eq[BUMP-1] : fq[BUMP-1];
    always @(posedge ck or negedge por_n)
        if (!por_n) begin epoch <= 8'd0; end
        else if (epoch_begin) epoch <= epoch + 8'd1;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_RUN; n <= 0; seen <= 0; lrst <= 0; fep <= 0; eq <= 0; fq <= 0; epoch_begin <= 0; bq <= 0;
            transport_fault <= 0; counting <= 0; recovery_cycles <= 0;
        end else begin
            fep <= 1'b0; epoch_begin <= begin_now; bq <= boot_begin;
            eq <= {eq, fep}; fq <= {fq, fwd_epoch_i};
            if (counting) recovery_cycles <= recovery_cycles + 1;
            if (begin_now) begin st <= S_RUN; seen <= 0; counting <= 0; transport_fault <= 0; end
            case (st)
            S_RUN: begin
                if (MASTER && boot_begin && !bq) fep <= 1'b1;
                if (abort && !epoch_begin) begin
                    st <= MASTER ? S_DRAIN : S_READY; n <= 0; counting <= 1; recovery_cycles <= 0;
                    transport_fault <= fault_cause | {end_fault, 7'd0};
                end
            end
            S_DRAIN: if (p_tx_v || p_rx_v) n <= 0; else if (n == DRAIN - 1) st <= S_DRAINED; else n <= n + 1;
            S_DRAINED: if (reset_req) begin st <= S_RST; n <= 0; lrst <= 1; end
            S_RST: begin
                if (!p_tx_up) seen <= 1;
                if (n == RSTC - 1) begin lrst <= 0; st <= S_TRAIN; end else n <= n + 1;
            end
            S_TRAIN: if (seen && p_tx_up) st <= S_READY;
            S_READY: if (MASTER && recovery_clear) fep <= 1'b1;
            default: st <= S_RUN;
            endcase
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// Compute die -> KV/system die STATUS/RESULT record, typed548 kind 15 (layer sentinel 63, beat 0):
//   DATA[0] vm_drained [1] collective_drained [2] collective_busy [3] crom_fault [4] execution_active [5] admit_ready
//   [6] result_v [7] result_done [8] result_fault [12:9] cause [71:13] tag59 [73:72] gen2 [91:74] token18
//   [123:92] value32 [155:124] cycles32, rest 0.
// TX: one register (codec latency 1). A terminal result is held from its pulse until the next compiled kind-15 slot;
// a second result before that slot is a schedule fault (the compiler spaces them). Levels are sampled at the slot.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qwen_d2d_status_tx (
    input  wire         ck, rst_n,
    input  wire [15:0]  epoch16,
    input  wire         vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    input  wire         result_v, result_done, result_fault,
    input  wire [3:0]   result_cause,
    input  wire [58:0]  result_tag,
    input  wire [1:0]   result_gen,
    input  wire [17:0]  result_token,
    input  wire [31:0]  result_value, result_cycles,
    input  wire         tx_slot,
    input  wire [3:0]   tx_kind,
    output reg          tx_valid,
    output reg  [547:0] tx_payload,
    output reg          fault
);
    reg pend; reg [148:0] r;
    wire [148:0] rin = {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done};
    wire [148:0] rsel = result_v ? rin : r;
    wire         psel = pend | result_v;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin pend <= 0; r <= 0; tx_valid <= 0; tx_payload <= 0; fault <= 0; end
        else begin
            tx_valid <= tx_slot;
            if (result_v && pend && !tx_slot) fault <= 1'b1;
            if (tx_slot && tx_kind != 4'd15) fault <= 1'b1;
            if (tx_slot) begin
                tx_payload <= {5'd0, 4'd15, 6'd63, epoch16, 5'd0,
                               356'd0, rsel[148:1], rsel[0], psel,
                               admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained};
                pend <= 1'b0;
            end else if (result_v) begin pend <= 1'b1; r <= rin; end
        end
    end
endmodule

module ot_qwen_d2d_status_rx (
    input  wire         ck, rst_n,
    input  wire [15:0]  epoch16,
    input  wire         rx_event, rx_slot,
    input  wire [547:0] rx_payload,
    output reg          vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready,
    output reg          status_fresh,   // at least one good record in this epoch
    output reg          result_v, result_done, result_fault,
    output reg  [3:0]   result_cause,
    output reg  [58:0]  result_tag,
    output reg  [1:0]   result_gen,
    output reg  [17:0]  result_token,
    output reg  [31:0]  result_value, result_cycles,
    input  wire         epoch_begin,
    output reg          fault
);
    wire [511:0] d = rx_payload[511:0];
    wire bad_hdr = rx_payload[547:543] != 0 || rx_payload[542:539] != 4'd15 || rx_payload[538:533] != 6'd63 ||
                   rx_payload[532:517] != epoch16 || rx_payload[516:512] != 0 || d[511:156] != 0;
    always @(posedge ck or negedge rst_n) begin
        if (!rst_n) begin
            {vm_drained, collective_drained, collective_busy, crom_fault, execution_active, admit_ready} <= 6'd0;
            status_fresh <= 0; result_v <= 0; result_done <= 0; result_fault <= 0; result_cause <= 0; result_tag <= 0;
            result_gen <= 0; result_token <= 0; result_value <= 0; result_cycles <= 0; fault <= 0;
        end else begin
            result_v <= 1'b0;
            if (epoch_begin) status_fresh <= 1'b0;
            if (rx_event != rx_slot || (rx_event && bad_hdr)) fault <= 1'b1;
            else if (rx_event && !fault) begin
                {admit_ready, execution_active, crom_fault, collective_busy, collective_drained, vm_drained} <= d[5:0];
                status_fresh <= 1'b1;
                result_v <= d[6];
                {result_cycles, result_value, result_token, result_gen, result_tag, result_cause, result_fault, result_done}
                    <= d[155:7];
            end
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// KV/system die HOST link services: drives the HOST root (qkd_host_root_pt) inputs owned by the link.
//   link_up[NL-1:0]       bit 0 = D2D UCIe (this end), bit 1 = board SerDes PHY up; NL = real link ends of the die
//   transport_fault[7:0]  typed D2D causes {ownership/end, collision, unread, tx_not_up, unexpected, missing, slot, crc}
//   native_links_drained / native_link_reset_seen / native_retrained   recovery witnesses
//   abort_drained[3:0]    {HOST, collective, VM, KV}: HOST/KV local owners, VM/collective from the kind-15 record
//   native_* / crom_fault / execution_active / engine_result_*         from the kind-15 record (compute die producers)
//   record_send_kind / record_witness_slot / record_rx_v / record_rx  from the HOST record port's calendar slots
// ---------------------------------------------------------------------------------------------------------------------
module qkd_host_link_services #(parameter integer NL = 2) (
    input  wire          ck, rst_n,
    // D2D end + recovery
    input  wire          d2d_link_up, serdes_up,
    input  wire [7:0]    d2d_transport_fault,
    input  wire          d2d_links_drained, d2d_link_reset_seen, d2d_retrained,
    // HOST-record port slots from the KV end (TX port 1 / RX port 1)
    input  wire          rec_tx_slot, input wire [3:0] rec_tx_kind, input wire [4:0] rec_tx_beat,
    input  wire          rec_rx_event, rec_rx_slot, input wire [547:0] rx_payload,
    // kind-15 decoded compute status
    input  wire          c_vm_drained, c_collective_drained, c_collective_busy, c_crom_fault, c_execution_active,
    input  wire          c_admit_ready, c_status_fresh,
    // KV-die local producers (owners: Q-KVSYS-ELEM leaves, HOST)
    input  wire          kv_drained_local, kv_flush_local, host_drained_local, kv_active_local,
    output wire [NL-1:0] link_up,
    output wire [7:0]    transport_fault,
    output wire          native_links_drained, native_link_reset_seen, native_retrained,
    output wire [3:0]    abort_drained,
    output wire          native_kv_drained, native_vm_drained, native_collective_drained, native_host_drained,
    output wire          native_collective_busy, native_kv_flush, native_admit_ready, crom_fault, execution_active,
    output wire [1:0]    record_send_kind,
    output wire          record_witness_slot, record_rx_v,
    output wire [547:0]  record_rx
);
    wire [1:0] lu = {serdes_up, d2d_link_up};
    assign link_up = lu[NL-1:0];
    assign transport_fault = d2d_transport_fault;
    assign native_links_drained = d2d_links_drained;
    assign native_link_reset_seen = d2d_link_reset_seen;
    assign native_retrained = d2d_retrained;
    // stale compute status (no record yet in this epoch) never reports drained / ready
    assign native_vm_drained = c_vm_drained & c_status_fresh;
    assign native_collective_drained = c_collective_drained & c_status_fresh;
    assign native_collective_busy = c_collective_busy | ~c_status_fresh;
    assign native_admit_ready = c_admit_ready & c_status_fresh;
    assign crom_fault = c_crom_fault;
    assign execution_active = c_execution_active | kv_active_local;
    assign native_kv_drained = kv_drained_local;
    assign native_kv_flush = kv_flush_local;
    assign native_host_drained = host_drained_local;
    assign abort_drained = {host_drained_local, native_collective_drained, native_vm_drained, kv_drained_local};
    // HOST record port: send_kind 1 BEGIN (kind13 beat1), 2 AUTH (kind13 beat2), 3 context (kind12)
    assign record_send_kind = !rec_tx_slot ? 2'd0 : rec_tx_kind == 4'd12 ? 2'd3 :
                              rec_tx_kind == 4'd13 && rec_tx_beat == 5'd1 ? 2'd1 :
                              rec_tx_kind == 4'd13 && rec_tx_beat == 5'd2 ? 2'd2 : 2'd0;
    assign record_witness_slot = rec_rx_slot;
    assign record_rx_v = rec_rx_event;
    assign record_rx = rx_payload;
endmodule
