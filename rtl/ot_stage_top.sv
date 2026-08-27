`timescale 1ns/1ps
// Public-reference stage top.  AON and core command/response/telemetry paths
// cross explicit asynchronous FIFOs; all model-specific arithmetic and external
// ROM/HBM/PHY resources terminate at the service ports below.
module ot_stage_top #(
    parameter integer SESSION_ENTRIES = 16,
    parameter integer CREDIT_SINKS = 4,
    parameter integer CREDIT_DEPTH = 8,
    parameter integer CMD_FIFO_DEPTH = 8,
    parameter integer RSP_FIFO_DEPTH = 8,
    parameter integer TELEM_FIFO_DEPTH = 16,
    parameter integer SCHEDULE_SLOTS = 256,
    parameter integer SCHEDULE_PORTS = 8,
    parameter integer SCHEDULE_SLOT_W = (SCHEDULE_SLOTS <= 2) ? 1 : $clog2(SCHEDULE_SLOTS),
    parameter integer SCHEDULE_PORT_ID_W = (SCHEDULE_PORTS <= 2) ? 1 : $clog2(SCHEDULE_PORTS),
    parameter integer SCHEDULE_ENTRY_W = SCHEDULE_PORT_ID_W + 2,
    parameter integer STAGE_ID = 0,
    parameter integer OWNED_FIRST_LAYER = 0,
    parameter integer OWNED_LAST_LAYER = 127,
    parameter [255:0] IMAGE_IDENTITY = 256'b0
) (
    input  wire                         aon_clk,
    input  wire                         core_clk,
    input  wire                         aon_rst_n,
    input  wire                         core_rst_n,
    input  wire                         host_cmd_valid,
    output wire                         host_cmd_ready,
    input  wire [255:0]                 host_cmd_record,
    output wire                         host_rsp_valid,
    input  wire                         host_rsp_ready,
    output wire [127:0]                 host_rsp_record,
    output wire                         telemetry_valid,
    input  wire                         telemetry_ready,
    output wire [127:0]                 telemetry_record,
    input  wire                         csr_req_valid,
    output wire                         csr_req_ready,
    input  wire [127:0]                 csr_req_record,
    output wire                         csr_rsp_valid,
    input  wire                         csr_rsp_ready,
    output wire [127:0]                 csr_rsp_record,
    // Core-domain qualified availability state, static while service is enabled.
    input  wire [255:0]                 image_slot_valid,
    // Core-domain abstract qualified service boundary (tile/HBM/link model).
    output wire                         service_start_valid,
    input  wire                         service_start_ready,
    output wire [15:0]                  service_transaction_id,
    output wire [23:0]                  service_session_id,
    output wire [6:0]                   service_first_layer,
    output wire [6:0]                   service_last_layer,
    output wire [15:0]                  service_batch_minus_one,
    output wire [3:0]                   service_draft_tokens,
    output wire                         service_poison,
    input  wire                         service_done_valid,
    input  wire [7:0]                   service_done_status,
    input  wire [7:0]                   service_done_error_source,
    input  wire [3:0]                   service_done_syndrome,
    // AON power/clock/BIST/thermal observations.
    input  wire                         power_good,
    input  wire                         clock_stable,
    input  wire                         hbm_ready,
    input  wire                         link_ready,
    input  wire                         bist_done,
    input  wire                         bist_pass,
    input  wire                         thermal_warning,
    input  wire                         thermal_fatal,
    input  wire                         fatal_error,
    input  wire                         requalify,
    input  wire                         test_enable,
    // Core-domain abort request.
    input  wire                         abort_valid,
    input  wire [15:0]                  abort_transaction_id,
    output wire [3:0]                   power_state,
    output wire                         safe_state,
    output wire                         stage_idle,
    output wire                         admission_block,
    // Optional schedule shadow interface (normally driven by boot firmware).
    input  wire                         schedule_wr_valid,
    input  wire [7:0]                   schedule_wr_slot,
    input  wire [15:0]                  schedule_wr_data,
    output wire                         schedule_wr_ready,
    output wire                         schedule_wr_ack,
    output wire                         schedule_wr_error,
    input  wire                         schedule_commit_req,
    output wire                         schedule_commit_ready,
    input  wire                         schedule_manifest_crc_ok,
    output wire                         schedule_commit_ack,
    output wire                         schedule_commit_error,
    output wire                         schedule_valid
);
    // AON -> core command FIFO.
    wire cmd_fifo_wr_ready, cmd_fifo_rd_valid, cmd_fifo_rd_ready;
    wire [255:0] cmd_fifo_rd_data;
    wire cmd_fifo_overflow, cmd_fifo_underflow;
    wire ras_telem_valid;
    wire [127:0] ras_telem_record;
    wire [63:0] ras_first_error;
    wire [31:0] ras_fatal_count;
    wire ras_admission_block;
    wire power_safe_request;
    wire power_isolation;
    wire power_throttle;
    wire power_quiesce_ack;
    wire power_stop_ack;
    wire [7:0] power_reset_cause;
    wire core_reset_n_qualified;
    wire core_domain_rst_n;
    wire stage_idle_aon;
    ot_reset_sync core_reset_conditioner (
        .clk(core_clk),
        .async_rst_n(core_rst_n && core_reset_n_qualified),
        .sync_rst_n(core_domain_rst_n));
    ot_async_fifo #(.WIDTH(256),.DEPTH(CMD_FIFO_DEPTH)) cmd_cdc (
        .wr_clk(aon_clk), .wr_rst_n(aon_rst_n), .wr_valid(host_cmd_valid),
        .wr_ready(cmd_fifo_wr_ready), .wr_data(host_cmd_record),
        .wr_overflow(cmd_fifo_overflow), .rd_clk(core_clk), .rd_rst_n(core_domain_rst_n),
        .rd_valid(cmd_fifo_rd_valid), .rd_ready(cmd_fifo_rd_ready),
        .rd_data(cmd_fifo_rd_data), .rd_underflow(cmd_fifo_underflow));
    assign host_cmd_ready = cmd_fifo_wr_ready;

    // Core -> AON response FIFO.
    wire rsp_fifo_wr_valid, rsp_fifo_wr_ready;
    wire [127:0] rsp_fifo_wr_data;
    wire rsp_fifo_rd_valid, rsp_fifo_rd_ready;
    wire [127:0] rsp_fifo_rd_data;
    ot_async_fifo #(.WIDTH(128),.DEPTH(RSP_FIFO_DEPTH)) rsp_cdc (
        .wr_clk(core_clk), .wr_rst_n(core_domain_rst_n), .wr_valid(rsp_fifo_wr_valid),
        .wr_ready(rsp_fifo_wr_ready), .wr_data(rsp_fifo_wr_data), .wr_overflow(),
        .rd_clk(aon_clk), .rd_rst_n(aon_rst_n), .rd_valid(rsp_fifo_rd_valid),
        .rd_ready(rsp_fifo_rd_ready), .rd_data(rsp_fifo_rd_data), .rd_underflow());
    assign host_rsp_valid = rsp_fifo_rd_valid;
    assign host_rsp_record = rsp_fifo_rd_data;
    assign rsp_fifo_rd_ready = host_rsp_ready;

    // Core -> AON lossless telemetry FIFO.
    wire telem_fifo_wr_ready, telem_fifo_rd_valid, telem_fifo_rd_ready;
    wire [127:0] telem_fifo_rd_data;
    wire telem_fifo_underflow;
    ot_async_fifo #(.WIDTH(128),.DEPTH(TELEM_FIFO_DEPTH)) telemetry_cdc (
        .wr_clk(core_clk), .wr_rst_n(core_domain_rst_n), .wr_valid(ras_telem_valid),
        .wr_ready(telem_fifo_wr_ready), .wr_data(ras_telem_record), .wr_overflow(),
        .rd_clk(aon_clk), .rd_rst_n(aon_rst_n), .rd_valid(telem_fifo_rd_valid),
        .rd_ready(telem_fifo_rd_ready), .rd_data(telem_fifo_rd_data),
        .rd_underflow(telem_fifo_underflow));
    assign telemetry_valid = telem_fifo_rd_valid;
    assign telemetry_record = telem_fifo_rd_data;
    assign telem_fifo_rd_ready = telemetry_ready;

    // AON CSR and power/reset ownership.
    wire [63:0] csr_control, csr_error_mask;
    wire [63:0] csr_error_clear;
    wire csr_sched_valid, csr_repair_valid;
    wire [15:0] csr_sched_addr, csr_repair_addr;
    wire [63:0] csr_sched_data, csr_repair_data;
    wire [7:0] csr_sched_strobe, csr_repair_strobe;
    wire csr_req_ready_int, csr_rsp_valid_int;
    wire [127:0] csr_rsp_record_int;
    wire [63:0] heartbeat;
    reg [63:0] aon_heartbeat;
    assign heartbeat = aon_heartbeat;
    always @(posedge aon_clk or negedge aon_rst_n)
        if (!aon_rst_n) aon_heartbeat <= 0;
        else aon_heartbeat <= aon_heartbeat + 1'b1;
    ot_csr_block csr (
        .clk(aon_clk), .rst_n(aon_rst_n), .req_valid(csr_req_valid), .req_ready(csr_req_ready_int),
        .req_record(csr_req_record), .rsp_valid(csr_rsp_valid_int), .rsp_ready(csr_rsp_ready),
        .rsp_record(csr_rsp_record_int), .capabilities(64'h0001_0004_0000_0010),
        .status_in({58'b0,stage_idle_aon,safe_state,power_state}), .heartbeat(heartbeat),
        .power_thermal_state({60'b0,thermal_fatal,thermal_warning,2'b0}),
        .image_identity(IMAGE_IDENTITY), .first_error(ras_first_error),
        .error_status_in({32'b0,ras_fatal_count}), .ras_dft_status(64'b0),
        .control(csr_control), .error_mask(csr_error_mask), .error_status_clear(csr_error_clear),
        .schedule_window_valid(csr_sched_valid), .schedule_window_address(csr_sched_addr),
        .schedule_window_data(csr_sched_data), .schedule_window_strobe(csr_sched_strobe),
        .repair_window_valid(csr_repair_valid), .repair_window_address(csr_repair_addr),
        .repair_window_data(csr_repair_data), .repair_window_strobe(csr_repair_strobe),
        .bad_request_count());
    assign csr_req_ready = csr_req_ready_int;
    assign csr_rsp_valid = csr_rsp_valid_int;
    assign csr_rsp_record = csr_rsp_record_int;

    wire core_ready = 1'b1;
    wire service_enable_aon;
    wire ras_safe_request_core;
    wire ras_safe_request_aon;
    wire ras_watchdog_timeout;
    ot_sync_bits #(.WIDTH(1)) ras_safe_sync (
        .clk(aon_clk), .rst_n(aon_rst_n), .async_in(ras_safe_request_core),
        .sync_out(ras_safe_request_aon));
    ot_power_reset_controller power (
        .aon_clk(aon_clk), .aon_rst_n(aon_rst_n), .power_good(power_good),
        .clock_stable(clock_stable), .core_ready(core_ready), .hbm_ready(hbm_ready),
        .link_ready(link_ready), .bist_done(bist_done), .bist_pass(bist_pass),
        .service_request(csr_control[0]), .quiesce_request(csr_control[1]),
        .core_quiescent(stage_idle_aon), .thermal_warning(thermal_warning),
        .thermal_fatal(thermal_fatal), .fatal_error(fatal_error || ras_safe_request_aon),
        .requalify(requalify),
        .test_enable(test_enable), .state(power_state), .core_reset_n(core_reset_n_qualified),
        .service_enable(service_enable_aon), .isolation_enable(power_isolation), .throttle_enable(power_throttle),
        .safe(power_safe_request), .quiesce_ack(power_quiesce_ack), .stop_ack(power_stop_ack), .reset_cause(power_reset_cause));
    wire service_enable_core;
    ot_sync_bits #(.WIDTH(1)) service_sync (
        .clk(core_clk), .rst_n(core_domain_rst_n), .async_in(service_enable_aon),
        .sync_out(service_enable_core));
    wire power_safe_core;
    ot_sync_bits #(.WIDTH(1)) power_safe_sync (
        .clk(core_clk), .rst_n(core_domain_rst_n), .async_in(power_safe_request),
        .sync_out(power_safe_core));
    ot_sync_level #(.WIDTH(1),.QUAL_CYCLES(3),.RESET_VALUE(1'b1)) idle_sync (
        .clk(aon_clk), .rst_n(aon_rst_n), .async_in(stage_idle),
        .sync_out(stage_idle_aon));
    assign safe_state = (power_state == 4'd4);

    // Epoch/schedule owner.
    wire [7:0] active_epoch;
    wire active_slot_valid;
    wire [SCHEDULE_PORT_ID_W-1:0] active_source_port;
    wire active_expect_valid, active_idle;
    wire schedule_shadow_ready_core;
    wire schedule_commit_ack_core, schedule_commit_error_core;
    wire schedule_valid_core;
    wire schedule_mail_src_ready, schedule_mail_src_done;
    wire [1:0] schedule_mail_src_response;
    wire schedule_mail_dst_valid, schedule_mail_dst_ready;
    wire [25:0] schedule_mail_dst_data;
    reg schedule_commit_dispatched;
    wire schedule_mail_kind = schedule_mail_dst_data[25];
    wire schedule_mail_crc_ok = schedule_mail_dst_data[24];
    wire [7:0] schedule_mail_slot = schedule_mail_dst_data[23:16];
    wire [15:0] schedule_mail_data = schedule_mail_dst_data[15:0];
    wire schedule_write_illegal = (schedule_mail_slot >= SCHEDULE_SLOTS) ||
                                  (!schedule_mail_data[SCHEDULE_ENTRY_W-1] &&
                                   (schedule_mail_data[SCHEDULE_PORT_ID_W-1:0] >= SCHEDULE_PORTS));
    wire [1:0] schedule_mail_dst_response = {
        schedule_mail_kind,
        schedule_mail_kind ? (schedule_commit_error_core && !schedule_commit_ack_core) :
                             schedule_write_illegal
    };
    assign schedule_commit_ready = schedule_mail_src_ready;
    assign schedule_wr_ready = schedule_mail_src_ready && !schedule_commit_req;
    assign schedule_wr_ack = schedule_mail_src_done &&
                             !schedule_mail_src_response[1] &&
                             !schedule_mail_src_response[0];
    assign schedule_wr_error = schedule_mail_src_done &&
                               !schedule_mail_src_response[1] &&
                               schedule_mail_src_response[0];
    assign schedule_commit_ack = schedule_mail_src_done &&
                                 schedule_mail_src_response[1] &&
                                 !schedule_mail_src_response[0];
    assign schedule_commit_error = schedule_mail_src_done &&
                                   schedule_mail_src_response[1] &&
                                   schedule_mail_src_response[0];
    ot_cdc_mailbox #(.WIDTH(26),.RESPONSE_W(2)) schedule_cdc (
        .src_clk(aon_clk), .src_rst_n(aon_rst_n),
        .src_valid(schedule_commit_req || schedule_wr_valid),
        .src_ready(schedule_mail_src_ready),
        .src_data({schedule_commit_req,schedule_manifest_crc_ok,
                   schedule_wr_slot,schedule_wr_data}),
        .src_done(schedule_mail_src_done),
        .src_response(schedule_mail_src_response),
        .dst_clk(core_clk), .dst_rst_n(core_domain_rst_n),
        .dst_valid(schedule_mail_dst_valid),
        .dst_ready(schedule_mail_dst_ready),
        .dst_data(schedule_mail_dst_data),
        .dst_response(schedule_mail_dst_response));
    wire schedule_commit_pulse = schedule_mail_dst_valid && schedule_mail_kind &&
                                 !schedule_commit_dispatched;
    always @(posedge core_clk or negedge core_domain_rst_n) begin
        if (!core_domain_rst_n)
            schedule_commit_dispatched <= 1'b0;
        else if (!schedule_mail_dst_valid || !schedule_mail_kind)
            schedule_commit_dispatched <= 1'b0;
        else if (!schedule_commit_dispatched)
            schedule_commit_dispatched <= 1'b1;
    end
    assign schedule_mail_dst_ready = schedule_mail_kind ?
                                     (schedule_commit_dispatched &&
                                      (schedule_commit_ack_core || schedule_commit_error_core)) :
                                     schedule_shadow_ready_core;
    ot_schedule_controller #(.PORTS(SCHEDULE_PORTS),.SLOTS(SCHEDULE_SLOTS),
                              .PORT_ID_W(SCHEDULE_PORT_ID_W),
                              .SLOT_W(SCHEDULE_SLOT_W),.ENTRY_W(SCHEDULE_ENTRY_W)) schedule (
        .clk(core_clk), .rst_n(core_domain_rst_n),
        .shadow_wr_valid(schedule_mail_dst_valid && !schedule_mail_kind),
        .shadow_wr_ready(schedule_shadow_ready_core),
        .shadow_wr_slot(schedule_mail_slot[SCHEDULE_SLOT_W-1:0]),
        .shadow_wr_data(schedule_mail_data[SCHEDULE_ENTRY_W-1:0]),
        .commit_req(schedule_commit_pulse),
        .quiescent(stage_idle), .epoch_boundary(1'b1),
        .manifest_crc_ok(schedule_mail_crc_ok), .commit_ack(schedule_commit_ack_core),
        .commit_error(schedule_commit_error_core), .schedule_valid(schedule_valid_core),
        .epoch_id(active_epoch),
        .active_slot({SCHEDULE_SLOT_W{1'b0}}), .active_slot_valid(active_slot_valid),
        .active_source_port(active_source_port), .active_expect_valid(active_expect_valid),
        .active_idle(active_idle), .active_schedule_crc(), .commit_pending());
    ot_sync_level #(.WIDTH(1),.QUAL_CYCLES(3)) schedule_valid_sync (
        .clk(aon_clk), .rst_n(aon_rst_n), .async_in(schedule_valid_core),
        .sync_out(schedule_valid));

    // Command frontend and stage controller.
    wire dispatch_valid, dispatch_ready;
    wire [7:0] dispatch_opcode, dispatch_flags, dispatch_epoch, dispatch_schedule;
    wire [23:0] dispatch_session;
    wire [19:0] dispatch_position, dispatch_context;
    wire [15:0] dispatch_batch, dispatch_txn;
    wire [6:0] dispatch_first, dispatch_last;
    wire [3:0] dispatch_draft;
    wire [7:0] dispatch_image;
    wire [47:0] dispatch_address;
    wire [31:0] dispatch_cookie;
    wire completion_valid;
    wire [7:0] completion_status, completion_source;
    wire [3:0] completion_syndrome;
    ot_cmd_frontend frontend (
        .clk(core_clk), .rst_n(core_domain_rst_n), .cmd_valid(cmd_fifo_rd_valid),
        .cmd_ready(cmd_fifo_rd_ready), .cmd_record(cmd_fifo_rd_data),
        .dispatch_valid(dispatch_valid), .dispatch_ready(dispatch_ready),
        .dispatch_opcode(dispatch_opcode), .dispatch_flags(dispatch_flags),
        .dispatch_epoch(dispatch_epoch), .dispatch_schedule(dispatch_schedule),
        .dispatch_session(dispatch_session), .dispatch_position(dispatch_position),
        .dispatch_context_minus_one(dispatch_context), .dispatch_batch_minus_one(dispatch_batch),
        .dispatch_first_layer(dispatch_first), .dispatch_last_layer(dispatch_last),
        .dispatch_draft_tokens(dispatch_draft), .dispatch_image_slot(dispatch_image),
        .dispatch_activation_address(dispatch_address), .dispatch_cookie(dispatch_cookie),
        .dispatch_transaction_id(dispatch_txn), .completion_valid(completion_valid),
        .completion_status(completion_status), .completion_error_source(completion_source),
        .completion_syndrome(completion_syndrome), .active_epoch(active_epoch),
        .image_slot_valid(image_slot_valid), .service_enable(service_enable_core),
        .quiesce(!service_enable_core), .rsp_valid(rsp_fifo_wr_valid),
        .rsp_ready(rsp_fifo_wr_ready), .rsp_record(rsp_fifo_wr_data),
        .bad_crc_count(), .bad_field_count(), .accepted_count(), .transaction_counter());

    wire session_req_valid, session_req_ready;
    wire [2:0] session_req_op;
    wire [23:0] session_req_session;
    wire [7:0] session_req_image;
    wire [19:0] session_req_context, session_req_position;
    wire [7:0] session_req_epoch;
    wire [15:0] session_req_transaction;
    wire session_req_force, session_rsp_valid, session_rsp_hit, session_rsp_poison;
    wire [7:0] session_rsp_status;
    wire [19:0] session_rsp_expected;
    ot_session_table #(.ENTRIES(SESSION_ENTRIES)) sessions (
        .clk(core_clk), .rst_n(core_domain_rst_n), .req_valid(session_req_valid),
        .req_ready(session_req_ready), .req_op(session_req_op), .req_session_id(session_req_session),
        .req_image_slot(session_req_image), .req_context_minus_one(session_req_context),
        .req_position(session_req_position), .req_epoch_id(session_req_epoch),
        .req_transaction_id(session_req_transaction), .req_force(session_req_force),
        .rsp_valid(session_rsp_valid), .rsp_status(session_rsp_status), .rsp_hit(session_rsp_hit),
        .rsp_generation(), .rsp_expected_position(session_rsp_expected), .rsp_poison(session_rsp_poison),
        .busy_bitmap(), .integrity_error());

    wire credit_reserve_valid, credit_reserve_ready, credit_release_valid;
    wire [CREDIT_SINKS-1:0] credit_reserve_mask, credit_release_mask;
    ot_credit_manager #(.SINKS(CREDIT_SINKS),.DEPTH(CREDIT_DEPTH)) credits (
        .clk(core_clk), .rst_n(core_domain_rst_n), .reserve_valid(credit_reserve_valid),
        .reserve_ready(credit_reserve_ready), .reserve_mask(credit_reserve_mask),
        .release_valid(credit_release_valid), .release_mask(credit_release_mask),
        .free_count(), .overflow_error(), .underflow_error(), .conservation_error());

    ot_ras_controller ras (
        .clk(core_clk), .rst_n(core_domain_rst_n),
        .event_valid(service_done_valid && (service_done_status != 0 || service_done_error_source != 0)),
        .event_code(12'h201),
        .event_severity((service_done_status != 0) ? 2'd2 : 2'd1),
        .event_source({2'b0,service_done_error_source}), .event_epoch(active_epoch),
        .event_transaction(service_transaction_id), .event_syndrome({12'b0,service_done_syndrome}),
        .event_clear_first(1'b0), .telemetry_ready(telem_fifo_wr_ready),
        .telemetry_valid(ras_telem_valid), .telemetry_record(ras_telem_record),
        .telemetry_pop(1'b0), .transaction_active(!stage_idle),
        .transaction_poison_in(service_poison), .transaction_poison(),
        .safe_request(ras_safe_request_core),
        .admission_block(ras_admission_block), .correctable_count(), .uncorrectable_count(),
        .fatal_count(ras_fatal_count), .first_error_valid(), .first_error_severity(),
        .first_error_source(), .first_error_epoch(), .first_error_transaction(),
        .first_error_syndrome(), .watchdog_enable(!stage_idle), .watchdog_kick(service_done_valid),
        .watchdog_limit(24'd100000), .watchdog_timeout(ras_watchdog_timeout));
    assign ras_first_error = {16'b0,ras_fatal_count,16'b0};
    assign admission_block = ras_admission_block || power_safe_core || !service_enable_core;

    ot_stage_controller #(.SINKS(CREDIT_SINKS),.STAGE_ID(STAGE_ID),
                           .OWNED_FIRST_LAYER(OWNED_FIRST_LAYER),.OWNED_LAST_LAYER(OWNED_LAST_LAYER)) controller (
        .clk(core_clk), .rst_n(core_domain_rst_n), .cmd_valid(dispatch_valid), .cmd_ready(dispatch_ready),
        .cmd_opcode(dispatch_opcode), .cmd_flags(dispatch_flags), .cmd_epoch(dispatch_epoch),
        .cmd_schedule(dispatch_schedule), .cmd_session(dispatch_session), .cmd_position(dispatch_position),
        .cmd_context_minus_one(dispatch_context), .cmd_batch_minus_one(dispatch_batch),
        .cmd_first_layer(dispatch_first), .cmd_last_layer(dispatch_last), .cmd_draft_tokens(dispatch_draft),
        .cmd_image_slot(dispatch_image), .cmd_activation_address(dispatch_address),
        .cmd_cookie(dispatch_cookie), .cmd_transaction_id(dispatch_txn), .quiesce(!service_enable_core),
        .admission_block(admission_block), .abort_valid(abort_valid),
        .abort_transaction_id(abort_transaction_id), .session_req_valid(session_req_valid),
        .session_req_ready(session_req_ready), .session_req_op(session_req_op),
        .session_req_session(session_req_session), .session_req_image_slot(session_req_image),
        .session_req_context_minus_one(session_req_context), .session_req_position(session_req_position),
        .session_req_epoch(session_req_epoch), .session_req_transaction(session_req_transaction),
        .session_req_force(session_req_force), .session_rsp_valid(session_rsp_valid),
        .session_rsp_status(session_rsp_status), .session_rsp_hit(session_rsp_hit),
        .session_rsp_expected_position(session_rsp_expected), .credit_reserve_valid(credit_reserve_valid),
        .credit_reserve_ready(credit_reserve_ready), .credit_reserve_mask(credit_reserve_mask),
        .credit_release_valid(credit_release_valid), .credit_release_mask(credit_release_mask),
        .service_start_valid(service_start_valid), .service_start_ready(service_start_ready),
        .service_transaction_id(service_transaction_id), .service_session_id(service_session_id),
        .service_first_layer(service_first_layer), .service_last_layer(service_last_layer),
        .service_batch_minus_one(service_batch_minus_one), .service_draft_tokens(service_draft_tokens),
        .service_poison(service_poison), .service_done_valid(service_done_valid),
        .service_done_status(service_done_status), .service_done_error_source(service_done_error_source),
        .service_done_syndrome(service_done_syndrome), .watchdog_timeout(ras_watchdog_timeout),
        .completion_valid(completion_valid), .completion_status(completion_status),
        .completion_error_source(completion_source), .completion_syndrome(completion_syndrome),
        .completion_transaction_id(), .completion_session_id(), .completion_position(),
        .completion_cookie(), .stage_idle(stage_idle), .stage_poison());
endmodule
