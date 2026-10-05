`timescale 1ns/1ps
// Shared reliability/availability/service (RAS) controller.  Correctable
// events are counted, uncorrectable events poison the transaction, and fatal or
// watchdog events request SAFE.  The first-error record is sticky and retained
// until an explicit clear.
module ot_ras_controller #(
    parameter integer TELEMETRY_DEPTH = 16,
    parameter integer WATCHDOG_W = 24
) (
    input  wire                         clk,
    input  wire                         rst_n,
    input  wire                         event_valid,
    input  wire [11:0]                  event_code,
    input  wire [1:0]                   event_severity, // 0 info,1 corr,2 uncorr,3 fatal
    input  wire [9:0]                   event_source,
    input  wire [7:0]                   event_epoch,
    input  wire [15:0]                  event_transaction,
    input  wire [15:0]                  event_syndrome,
    input  wire                         event_clear_first,
    input  wire                         telemetry_ready,
    output wire                         telemetry_valid,
    output wire [127:0]                 telemetry_record,
    input  wire                         telemetry_pop,
    input  wire                         transaction_active,
    input  wire                         transaction_poison_in,
    output reg                          transaction_poison,
    output reg                          safe_request,
    output reg                          admission_block,
    output reg [31:0]                   correctable_count,
    output reg [31:0]                   uncorrectable_count,
    output reg [31:0]                   fatal_count,
    output reg                          first_error_valid,
    output reg [1:0]                    first_error_severity,
    output reg [9:0]                    first_error_source,
    output reg [7:0]                    first_error_epoch,
    output reg [15:0]                   first_error_transaction,
    output reg [15:0]                   first_error_syndrome,
    input  wire                         watchdog_enable,
    input  wire                         watchdog_kick,
    input  wire [WATCHDOG_W-1:0]        watchdog_limit,
    output reg                          watchdog_timeout
);
    localparam integer PTR_W = (TELEMETRY_DEPTH <= 2) ? 1 : $clog2(TELEMETRY_DEPTH);
    localparam integer CNT_W = $clog2(TELEMETRY_DEPTH+1);
    localparam integer PTR_LAST_INT = TELEMETRY_DEPTH-1;
    localparam [PTR_W-1:0] PTR_LAST = PTR_LAST_INT[PTR_W-1:0];
    localparam [CNT_W-1:0] DEPTH_COUNT = TELEMETRY_DEPTH[CNT_W-1:0];
    localparam [CNT_W-1:0] ADMISSION_THRESHOLD = PTR_LAST_INT[CNT_W-1:0];
    reg [127:0] telemetry_mem [0:TELEMETRY_DEPTH-1];
    reg [PTR_W-1:0] wr_ptr;
    reg [PTR_W-1:0] rd_ptr;
    reg [CNT_W-1:0] telem_count;
    reg [47:0] timestamp;
    reg [WATCHDOG_W-1:0] watchdog_count;
    reg [127:0] event_record;
    reg [111:0] event_body;
    reg [15:0] event_crc;
    wire telem_push = event_valid && (telem_count < DEPTH_COUNT);
    wire telem_pop_fire = telemetry_valid && (telemetry_ready || telemetry_pop);
    wire fatal_event_now = event_valid && (event_severity == 2'd3);
    wire watchdog_expire_now = watchdog_enable && !watchdog_kick &&
                               (watchdog_limit != 0) &&
                               (watchdog_count >= watchdog_limit);
    wire telemetry_blocks_next =
        (telem_push && !telem_pop_fire) ?
            ((telem_count + 1'b1) >= ADMISSION_THRESHOLD) :
        (!telem_push && telem_pop_fire) ?
            ((telem_count - 1'b1) >= ADMISSION_THRESHOLD) :
            (telem_count >= ADMISSION_THRESHOLD);

    function automatic [15:0] crc16_112;
        input [111:0] d;
        integer by;
        integer bi;
        reg [15:0] c;
        reg fb;
        begin
            c = 16'hffff;
            for (by = 0; by < 14; by = by + 1)
                for (bi = 7; bi >= 0; bi = bi - 1) begin
                    fb = c[15] ^ d[by*8+bi];
                    c = {c[14:0],1'b0};
                    if (fb) c = c ^ 16'h1021;
                end
            crc16_112 = c;
        end
    endfunction

    always @* begin
        event_body = 112'b0;
        event_body[11:0] = event_code;
        event_body[13:12] = event_severity;
        event_body[23:14] = event_source;
        event_body[31:24] = event_epoch;
        event_body[47:32] = event_transaction;
        event_body[95:48] = timestamp;
        event_body[111:96] = event_syndrome;
        event_crc = crc16_112(event_body);
        event_record = {event_crc,event_body};
    end

    assign telemetry_valid = (telem_count != 0);
    assign telemetry_record = telemetry_mem[rd_ptr];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            telem_count <= 0;
            timestamp <= 0;
            transaction_poison <= 1'b0;
            safe_request <= 1'b0;
            admission_block <= 1'b0;
            correctable_count <= 0;
            uncorrectable_count <= 0;
            fatal_count <= 0;
            first_error_valid <= 1'b0;
            first_error_severity <= 0;
            first_error_source <= 0;
            first_error_epoch <= 0;
            first_error_transaction <= 0;
            first_error_syndrome <= 0;
            watchdog_count <= 0;
            watchdog_timeout <= 1'b0;
        end else begin
            timestamp <= timestamp + 1'b1;
            // Poison is monotonic only for the lifetime of the active
            // architectural transaction.  An idle boundary starts the next
            // transaction clean; sticky error history remains in telemetry.
            if (!transaction_active)
                transaction_poison <= 1'b0;
            if (event_clear_first)
                first_error_valid <= 1'b0;
            if (event_valid) begin
                if (event_severity == 2'd1) begin
                    if (~&correctable_count)
                        correctable_count <= correctable_count + 1'b1;
                end else if (event_severity == 2'd2) begin
                    if (~&uncorrectable_count)
                        uncorrectable_count <= uncorrectable_count + 1'b1;
                end else if (event_severity == 2'd3) begin
                    if (~&fatal_count)
                        fatal_count <= fatal_count + 1'b1;
                end
                if (!first_error_valid && !event_clear_first) begin
                    first_error_valid <= 1'b1;
                    first_error_severity <= event_severity;
                    first_error_source <= event_source;
                    first_error_epoch <= event_epoch;
                    first_error_transaction <= event_transaction;
                    first_error_syndrome <= event_syndrome;
                end
                if ((event_severity >= 2'd2) && transaction_active)
                    transaction_poison <= 1'b1;
                if (event_severity == 2'd3)
                    safe_request <= 1'b1;
            end
            if (transaction_poison_in && transaction_active)
                transaction_poison <= 1'b1;
            if (telem_push) begin
                telemetry_mem[wr_ptr] <= event_record;
                if (wr_ptr == PTR_LAST) wr_ptr <= 0;
                else wr_ptr <= wr_ptr + 1'b1;
            end
            if (telem_pop_fire) begin
                if (rd_ptr == PTR_LAST) rd_ptr <= 0;
                else rd_ptr <= rd_ptr + 1'b1;
            end
            case ({telem_push,telem_pop_fire})
                2'b10: telem_count <= telem_count + 1'b1;
                2'b01: telem_count <= telem_count - 1'b1;
                default: telem_count <= telem_count;
            endcase
            // Once the lossless telemetry queue is full, stop new admission;
            // existing work may drain and free the reserved entries.
            admission_block <= telemetry_blocks_next || safe_request ||
                               fatal_event_now || watchdog_expire_now;
            if (!watchdog_enable || watchdog_kick) begin
                watchdog_count <= 0;
                watchdog_timeout <= 1'b0;
            end else if (watchdog_limit != 0) begin
                if (watchdog_count >= watchdog_limit) begin
                    watchdog_timeout <= 1'b1;
                    safe_request <= 1'b1;
                end else begin
                    watchdog_count <= watchdog_count + 1'b1;
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        if (TELEMETRY_DEPTH < 2 || (TELEMETRY_DEPTH & (TELEMETRY_DEPTH-1)) != 0)
            $error("ot_ras_controller TELEMETRY_DEPTH must be power of two >= 2");
    end
`endif
endmodule
