`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the ROM read service.
//
// It is one of two independently written checkers over the same generated
// images.  It shares no checking code with rtl/test/rom_service_harness.cpp;
// the two agree only on the images, which come from real ABI 3.0 ROM
// deployments and from the ROM read stream runtime.sim.device.Device actually
// issued for those deployments.
//
// Per request it requires exact agreement on: completion status, fault class,
// beat count, byte count, row-activation count, the first and last beat record
// (resource, resource address, region byte, physical row, sense granule, byte
// count and the activation bit), the beat-stream digest and the operand-data
// digest.  Across the run it requires the service's own counters to reconcile
// with the sum of the per-request results, the array's independently kept
// activation count to equal the service's, and the window model never to miss.
// ---------------------------------------------------------------------------
module tb_rom_service;
    localparam integer OBJECTS        = 512;
    localparam integer SHARDS         = 16384;
    localparam integer REGIONS        = 512;
    localparam integer RESOURCES      = 16384;
    localparam integer REPAIR_ENTRIES = 64;
    localparam integer REQUESTS       = 32768;
    localparam integer WINDOW_ENTRIES = 16384;
    localparam integer MASKS          = 256;
    localparam integer EXPECT_STRIDE  = 32;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        cfg_start = 1'b0;
    wire       cfg_done;
    reg        case_start = 1'b0;
    reg [31:0] case_index = 32'd0;
    reg        out_ready_in = 1'b1;
    reg        sense_ready_in = 1'b1;
    wire       case_busy;
    wire       case_done;

    wire [1:0]   cmp_status;
    wire [3:0]   cmp_fault;
    wire [63:0]  cmp_beats;
    wire [63:0]  cmp_bytes;
    wire [63:0]  cmp_activations;
    wire [63:0]  cmp_beat_digest;
    wire [63:0]  cmp_data_digest;
    wire [255:0] cmp_first_beat;
    wire [255:0] cmp_last_beat;
    wire [15:0]  cmp_tag;
    wire [63:0]  count_requests;
    wire [63:0]  count_beats;
    wire [63:0]  count_bytes;
    wire [63:0]  count_activations;
    wire [63:0]  count_masked;
    wire [63:0]  count_faults;
    wire [3:0]   first_fault_class;
    wire [31:0]  first_fault_object;
    wire [63:0]  array_act_count;
    wire [63:0]  array_sense_count;
    wire [63:0]  bus_bytes;
    wire [63:0]  bus_beats;
    wire [63:0]  bus_last_beats;
    wire         window_miss;
    wire [31:0]  meta_object_count;
    wire [31:0]  meta_shard_count;
    wire [31:0]  meta_repair_count;
    wire [31:0]  meta_mask_count;
    wire [31:0]  meta_request_count;
    wire [31:0]  meta_window_count;
    wire [31:0]  meta_marker_lo;
    wire [31:0]  meta_marker_hi;
    wire [31:0]  cap_objects, cap_shards, cap_regions, cap_resources;
    wire [31:0]  cap_repair_entries, cap_requests, cap_window_entries, cap_masks;
    wire [31:0]  req_objects, req_shards, req_regions, req_resources;
    wire [31:0]  req_repair_entries, req_requests, req_window_entries, req_masks;

    rom_service_top #(
        .OBJECTS(OBJECTS), .SHARDS(SHARDS), .REGIONS(REGIONS),
        .RESOURCES(RESOURCES), .REPAIR_ENTRIES(REPAIR_ENTRIES),
        .REQUESTS(REQUESTS), .WINDOW_ENTRIES(WINDOW_ENTRIES), .MASKS(MASKS)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .cfg_start(cfg_start), .cfg_done(cfg_done),
        .case_start(case_start), .case_index(case_index),
        .out_ready_in(out_ready_in), .sense_ready_in(sense_ready_in),
        .case_busy(case_busy), .case_done(case_done),
        .cmp_status(cmp_status), .cmp_fault(cmp_fault),
        .cmp_beats(cmp_beats), .cmp_bytes(cmp_bytes),
        .cmp_activations(cmp_activations),
        .cmp_beat_digest(cmp_beat_digest), .cmp_data_digest(cmp_data_digest),
        .cmp_first_beat(cmp_first_beat), .cmp_last_beat(cmp_last_beat),
        .cmp_tag(cmp_tag),
        .count_requests(count_requests), .count_beats(count_beats),
        .count_bytes(count_bytes), .count_activations(count_activations),
        .count_masked(count_masked), .count_faults(count_faults),
        .first_fault_class(first_fault_class),
        .first_fault_object(first_fault_object),
        .array_act_count(array_act_count),
        .array_sense_count(array_sense_count),
        .bus_bytes(bus_bytes),
        .bus_beats(bus_beats),
        .bus_last_beats(bus_last_beats),
        .window_miss(window_miss),
        .meta_object_count(meta_object_count),
        .meta_shard_count(meta_shard_count),
        .meta_repair_count(meta_repair_count),
        .meta_mask_count(meta_mask_count),
        .meta_request_count(meta_request_count),
        .meta_window_count(meta_window_count),
        .meta_marker_lo(meta_marker_lo), .meta_marker_hi(meta_marker_hi),
        .cap_objects(cap_objects), .cap_shards(cap_shards),
        .cap_regions(cap_regions), .cap_resources(cap_resources),
        .cap_repair_entries(cap_repair_entries), .cap_requests(cap_requests),
        .cap_window_entries(cap_window_entries), .cap_masks(cap_masks),
        .req_objects(req_objects), .req_shards(req_shards),
        .req_regions(req_regions), .req_resources(req_resources),
        .req_repair_entries(req_repair_entries), .req_requests(req_requests),
        .req_window_entries(req_window_entries), .req_masks(req_masks)
    );

    reg [31:0] expect_mem [0:REQUESTS*EXPECT_STRIDE-1];
    reg [31:0] meta2 [0:31];
    integer zi;
    initial begin
        for (zi = 0; zi < REQUESTS*EXPECT_STRIDE; zi = zi + 1)
            expect_mem[zi] = 32'd0;
        $readmemh("rom_meta.hex", meta2);
        if (meta2[4] > 0)
            $readmemh("rom_expect.hex", expect_mem, 0, meta2[4]*EXPECT_STRIDE - 1);
    end

    integer checks;
    integer i;
    integer stall_tick;
    reg [63:0] sum_beats, sum_bytes, sum_acts, sum_masked, sum_faults;
    reg [63:0] e64;
    reg [255:0] e256;
    reg [63:0] exp_beats;

    task fail(input [1023:0] label, input integer index,
              input [63:0] got, input [63:0] want);
        begin
            $display("FAIL: request %0d %0s: %0d expected %0d",
                     index, label, got, want);
            $finish;
        end
    endtask

    task capacity_ok(input [1023:0] label, input [31:0] need,
                     input [31:0] have);
        begin
            checks = checks + 1;
            if (need > have) begin
                $display("FAIL: vector set needs %0d %0s but the top holds %0d",
                         need, label, have);
                $finish;
            end
        end
    endtask

    task expect_eq(input [1023:0] label, input integer index,
                   input [63:0] got, input [63:0] want);
        begin
            checks = checks + 1;
            if (got !== want) fail(label, index, got, want);
        end
    endtask

    task expect_eq256(input [1023:0] label, input integer index,
                      input [255:0] got, input [255:0] want);
        begin
            checks = checks + 1;
            if (got !== want) begin
                $display("FAIL: request %0d %0s: %h expected %h",
                         index, label, got, want);
                $finish;
            end
        end
    endtask

    function [63:0] word64(input integer base);
        begin
            word64 = {expect_mem[base+1], expect_mem[base+0]};
        end
    endfunction

    function [255:0] word256(input integer base);
        begin
            word256 = {expect_mem[base+7], expect_mem[base+6],
                       expect_mem[base+5], expect_mem[base+4],
                       expect_mem[base+3], expect_mem[base+2],
                       expect_mem[base+1], expect_mem[base+0]};
        end
    endfunction

    initial begin
        checks = 0;
        sum_beats = 64'd0; sum_bytes = 64'd0; sum_acts = 64'd0;
        sum_masked = 64'd0; sum_faults = 64'd0;
        stall_tick = 0;
        repeat (6) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        cfg_start = 1'b1;
        wait (cfg_done);
        @(posedge clk);
        cfg_start = 1'b0;
        repeat (2) @(posedge clk);

        if (meta_request_count == 0) begin
            $display("FAIL: the vector set carries no requests");
            $finish;
        end
        // Refuse a vector set that outgrew a table depth rather than let it
        // alias onto a legal wrong entry.
        capacity_ok("objects", req_objects, cap_objects);
        capacity_ok("shards", req_shards, cap_shards);
        capacity_ok("regions", req_regions, cap_regions);
        capacity_ok("resources", req_resources, cap_resources);
        capacity_ok("repair_entries", req_repair_entries, cap_repair_entries);
        capacity_ok("requests", req_requests, cap_requests);
        capacity_ok("window_entries", req_window_entries, cap_window_entries);
        capacity_ok("masks", req_masks, cap_masks);

        for (i = 0; i < meta_request_count; i = i + 1) begin
            exp_beats = word64(i*EXPECT_STRIDE + 2);
            // Back-pressure the operand bus and the sense port on the short
            // requests.  The very long ones are replayed at full rate: the
            // stall pattern is proved on the short cases and repeating it over
            // twenty million beats buys no coverage and costs an hour.
            if (exp_beats <= 64'd65536) begin
                out_ready_in   = ((i % 3) != 0);
                sense_ready_in = ((i % 5) != 1);
            end else begin
                out_ready_in   = 1'b1;
                sense_ready_in = 1'b1;
            end
            case_index = i;
            case_start = 1'b1;
            @(posedge clk);
            while (!case_busy) @(posedge clk);
            case_start = 1'b0;
            while (!case_done) begin
                @(posedge clk);
                stall_tick = stall_tick + 1;
                if (exp_beats <= 64'd65536) begin
                    out_ready_in   = ((stall_tick % 3) != 0);
                    sense_ready_in = ((stall_tick % 4) != 1);
                end
            end
            out_ready_in   = 1'b1;
            sense_ready_in = 1'b1;

            expect_eq("status", i, {62'd0, cmp_status},
                      {32'd0, expect_mem[i*EXPECT_STRIDE + 0]});
            expect_eq("fault", i, {60'd0, cmp_fault},
                      {32'd0, expect_mem[i*EXPECT_STRIDE + 1]});
            expect_eq("beats", i, cmp_beats, word64(i*EXPECT_STRIDE + 2));
            expect_eq("bytes", i, cmp_bytes, word64(i*EXPECT_STRIDE + 4));
            expect_eq("activations", i, cmp_activations,
                      word64(i*EXPECT_STRIDE + 6));
            expect_eq("beat_digest", i, cmp_beat_digest,
                      word64(i*EXPECT_STRIDE + 8));
            expect_eq("data_digest", i, cmp_data_digest,
                      word64(i*EXPECT_STRIDE + 10));
            expect_eq256("first_beat", i, cmp_first_beat,
                         word256(i*EXPECT_STRIDE + 12));
            expect_eq256("last_beat", i, cmp_last_beat,
                         word256(i*EXPECT_STRIDE + 20));
            expect_eq("tag", i, {48'd0, cmp_tag},
                      {32'd0, expect_mem[i*EXPECT_STRIDE + 28]});

            sum_beats = sum_beats + cmp_beats;
            sum_bytes = sum_bytes + cmp_bytes;
            sum_acts  = sum_acts + cmp_activations;
            if (cmp_status == 2'd1) sum_masked = sum_masked + 64'd1;
            if (cmp_status == 2'd2) sum_faults = sum_faults + 64'd1;
        end

        expect_eq("count_requests", -1, count_requests,
                  {32'd0, meta_request_count});
        expect_eq("count_beats", -1, count_beats, sum_beats);
        expect_eq("count_bytes", -1, count_bytes, sum_bytes);
        expect_eq("count_activations", -1, count_activations, sum_acts);
        expect_eq("count_masked", -1, count_masked, sum_masked);
        expect_eq("count_faults", -1, count_faults, sum_faults);
        // The array keeps its own activation count from the sense port alone.
        expect_eq("array_activations", -1, array_act_count, sum_acts);
        expect_eq("array_senses", -1, array_sense_count, sum_beats);
        expect_eq("window_miss", -1, {63'd0, window_miss}, 64'd0);
        // What actually crossed the operand bus, counted by the bench.
        expect_eq("bus_bytes", -1, bus_bytes, sum_bytes);
        expect_eq("bus_beats", -1, bus_beats, sum_beats);
        expect_eq("bus_last_beats", -1, bus_last_beats,
                  {32'd0, meta_request_count} - sum_masked - sum_faults);
        expect_eq("total_beats", -1, sum_beats, {meta2[9], meta2[8]});
        expect_eq("total_bytes", -1, sum_bytes, {meta2[11], meta2[10]});
        expect_eq("total_activations", -1, sum_acts, {meta2[13], meta2[12]});
        expect_eq("total_masked", -1, sum_masked, {meta2[15], meta2[14]});
        expect_eq("total_faults", -1, sum_faults, {meta2[17], meta2[16]});

        $display("ROM-SERVICE-OK requests=%0d beats=%0d bytes=%0d activations=%0d masked=%0d faults=%0d marker=%08x%08x",
                 meta_request_count, sum_beats, sum_bytes, sum_acts,
                 sum_masked, sum_faults, meta_marker_hi, meta_marker_lo);
        $display("checks=%0d", checks);
        $finish;
    end
endmodule
