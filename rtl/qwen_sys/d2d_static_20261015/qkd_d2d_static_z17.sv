`timescale 1ns/1ps
module qkd_d2d_static_z17 #(parameter integer Z17 = 0, parameter integer MUT = 0, parameter integer NL = 2, parameter integer NTX = 4, parameter integer PR = 1, parameter [31:0] TXDP = 32'd0) (
    output wire [16:0] rx_zero17,
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
    // TXDP = the compiler's per-TX-port producer capture latency (port p = byte p, 1..255 edges), set by the die GEN
    // from d2d_cal_image.svh (D2D_TXDP_C / D2D_TXDP_K, tools/qwen_split/d2d_cal_seq_image.py) or txdp.svh
    // (tools/qwen_split/d2d_link_calendar.py).  No production default exists: PR = 1 with an uncompiled (zero) port
    // byte does not elaborate (QXF-LINK 2026-10-18, TOKEN-XDIE-QWEN F4; the r4..r9 masters hard-wired the
    // component-bench codec latencies).
    generate if (PR != 0 && (TXDP[7:0] == 8'd0 || TXDP[15:8] == 8'd0 || TXDP[23:16] == 8'd0 || TXDP[31:24] == 8'd0)) begin : g_txdp_uncompiled
        D2D_TXDP_NOT_COMPILED__set_TXDP_from_the_compiler u_txdp_uncompiled ();
    end endgenerate
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
    // PRIVATE Z17: same producer capture as q_rx_payload; deliberately no reset/enable.
    generate if (Z17 && PR) begin : g_z17
        reg [16:0] q_zero17;
        integer z;
        always @(posedge ck) begin
            q_zero17[0] <= |c_rx_payload[31:19];
            q_zero17[1] <= |c_rx_payload[31:5];
            for (z=1; z<=15; z=z+1)
                q_zero17[z+1] <= |c_rx_payload[32*z +: 32];
        end
        assign rx_zero17 = q_zero17;
    end else begin : g_no_z17
        assign rx_zero17 = 17'b0;
    end endgenerate

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
    qkd_d2d_static_core #(.MUT(MUT), .NL(NL), .NTX(NTX), .TXDP(PR ? TXDP : {8'd1, 8'd1, 8'd2, 8'd1})) u_core (.ck(ck), .por_n(por_n), .rst_n(rst_n), .cfg_tx_we(c_cfg_tx_we), .cfg_rx_we(c_cfg_rx_we), .cfg_addr(c_cfg_addr), .cfg_data(c_cfg_data), .cal_start(c_cal_start), .cal_seg(c_cal_seg), .host_link_reset_req(c_host_link_reset_req), .host_recovery_clear(c_host_recovery_clear), .host_boot_begin(c_host_boot_begin), .fwd_epoch(c_fwd_epoch), .fwd_link_rst_n(c_fwd_link_rst_n), .att_tx_slot(c_att_tx_slot), .att_tx_kind(c_att_tx_kind), .att_tx_beat(c_att_tx_beat), .att_tx_v(c_att_tx_v), .att_tx_payload(c_att_tx_payload), .att_rx_v(c_att_rx_v), .att_rx_slot(c_att_rx_slot), .att_rx_kind(c_att_rx_kind), .att_rx_beat(c_att_rx_beat), .rx_payload(c_rx_payload), .emb_tx_slot(c_emb_tx_slot), .emb_tx_v(c_emb_tx_v), .emb_tx_payload(c_emb_tx_payload), .record_tx_observed_v(c_record_tx_observed_v), .record_tx(c_record_tx), .record_send_kind(c_record_send_kind), .record_witness_slot(c_record_witness_slot), .record_rx_v(c_record_rx_v), .record_rx(c_record_rx), .kvn_compiled_identity(c_kvn_compiled_identity), .kvn_compiled_generation(c_kvn_compiled_generation), .kvn_word_valid(c_kvn_word_valid), .kvn_word_tag(c_kvn_word_tag), .kvn_word_data(c_kvn_word_data), .kvn_word_identity(c_kvn_word_identity), .kvn_word_generation(c_kvn_word_generation), .kvn_word_slot(c_kvn_word_slot), .kvn_word_index(c_kvn_word_index), .status_epoch16(c_status_epoch16), .serdes_up(c_serdes_up), .kv_drained_local(c_kv_drained_local), .kv_flush_local(c_kv_flush_local), .host_drained_local(c_host_drained_local), .kv_active_local(c_kv_active_local), .link_up(c_link_up), .transport_fault(c_transport_fault), .native_links_drained(c_native_links_drained), .native_link_reset_seen(c_native_link_reset_seen), .native_retrained(c_native_retrained), .abort_drained(c_abort_drained), .native_kv_drained(c_native_kv_drained), .native_vm_drained(c_native_vm_drained), .native_collective_drained(c_native_collective_drained), .native_host_drained(c_native_host_drained), .native_collective_busy(c_native_collective_busy), .native_kv_flush(c_native_kv_flush), .native_admit_ready(c_native_admit_ready), .crom_fault(c_crom_fault), .execution_active(c_execution_active), .engine_result_v(c_engine_result_v), .engine_result_done(c_engine_result_done), .engine_result_fault(c_engine_result_fault), .engine_result_cause(c_engine_result_cause), .engine_result_tag(c_engine_result_tag), .engine_result_gen(c_engine_result_gen), .engine_result_token(c_engine_result_token), .engine_result_value(c_engine_result_value), .engine_result_cycles(c_engine_result_cycles), .fdi_tx_up(c_fdi_tx_up), .fdi_tx_v(c_fdi_tx_v), .fdi_tx_flit(c_fdi_tx_flit), .fdi_rx_v(c_fdi_rx_v), .fdi_rx_flit(c_fdi_rx_flit), .phy_rst_n(c_phy_rst_n), .epoch_abort(c_epoch_abort), .recovery_cycles(c_recovery_cycles), .fault(c_fault));
endmodule
