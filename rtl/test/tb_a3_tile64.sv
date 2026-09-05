`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Icarus checker for the T64 tile (results/rtl/abi3_tile64.json).
//
// This file and rtl/test/a3_tile64_harness.cpp are two independently written
// checkers over the same RTL and the same generated images.  For every case
// each checker drives the operation descriptor, pulses op_start, starts the
// environment models (SDN and H-tree, in the top), runs the tile to done
// while summing the per-cycle retire count and the cycles of every K-block,
// then compares: every partial the tile wrote (output word and accumulator,
// per lane, per K-block, per element) against the expectation image, the
// unwritten sentinel on every element no lane was to write, the counters,
// the error class / detail / K-block / LQ8 / lane, every LQ8's and lane's
// class and detail, and the top's lockstep monitor (zero).  For a clean
// operation it then reads the captured partials back column by column and
// feeds them through the RE8 endpoint beside the tile in the chained shapes
// of the K-block tree, comparing every root with the reference's.
//
// Case record layout (32-bit words, stride 320):
//    0 rows            1 cols          2 depth          3 kblock
//    4 dtype_a         5 dtype_b       6 group          7 scale_a
//    8 block_a         9 block_rows_a 10 scale_b       11 block_b
//   12 a_base         13 a_stride     14 scale_a_base  15 scale_a_stride
//   16 w_base         17 w_words      18 ws_base       19 ws_stride
//   20 out_base       21 out_stride   22 out_fp32      23 blocks
//   24 flags (bit0 rate, bit1 fault, bit2 refused, bit3 faulting block unchecked,
//             bit4 SDN limit, bit5 SDN ignores credit)
//   25 error_code     26 error_detail 27 error_kblock  28 error_lq8       29 error_lane
//   30 out_count      31 mac_count    32 product_count 33 staging_underruns (0xffffffff: unchecked)
//   34 stream_words_consumed (0xffffffff: unchecked)
//   35 expect partial offset  36 window (rows x cols per lane)  37 expect root offset  38 case id
//   39 act image base  40 act slice full  41 act slice last  42 scale image base  43 scale slice full  44 scale slice last
//   45 cols per lane  46 blocks written fully  47 tree checked  48 SDN words  49 tree vectors
//   64 + j  LQ8 error_code[j]    72 + j  LQ8 error_detail[j]
//   80 + l  written elements in the faulting K-block, lane l
//  144 + l  lane error_code[l]   208 + l  lane error_detail[l]
// Partial expectation: word 35 + (l * blocks + b) * window + e.  Root expectation: word 37 + row * cols + n.
// Result read-back: lane * region_words + out_base + b * out_stride + e.
// ---------------------------------------------------------------------------
module tb_a3_tile64 #(
    parameter integer ADDER_STAGES = 3,
    parameter integer WEIGHT_SOURCE = 0,
    parameter integer STAGING_IN_TILE = 1
);
    localparam integer CASE_STRIDE = 320;
    localparam integer LANES = 64;
    localparam integer LEAVES = 8;
    localparam [31:0]  UNWRITTEN = 32'hdead_beef;
    localparam [31:0]  DONT_CARE = 32'hffff_ffff;
    localparam [31:0]  FLAG_RATE = 32'h1;
    localparam [31:0]  FLAG_FAULT = 32'h2;
    localparam [31:0]  FLAG_REFUSED = 32'h4;
    localparam [31:0]  FLAG_BLOCK_UNCHECKED = 32'h8;
    localparam [31:0]  FLAG_SDN_IGNORE = 32'h20;
    localparam integer MAX_BLOCKS = 256;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    always #5 clk = ~clk;

    reg        op_start = 1'b0;
    reg [15:0] op_rows = 0, op_cols = 0, op_depth = 0, op_kblock = 0;
    reg [7:0]  op_dtype_a = 0, op_dtype_b = 0, op_group = 0;
    reg        op_scale_a = 0, op_scale_b = 0, op_out_fp32 = 0;
    reg [15:0] op_block_a = 0, op_block_rows_a = 0, op_block_b = 0;
    reg [31:0] op_a_base = 0, op_scale_a_base = 0, op_w_base = 0, op_w_words = 0;
    reg [31:0] op_ws_base = 0, op_ws_block_stride = 0, op_out_base = 0, op_out_block_stride = 0;
    reg [15:0] op_a_block_stride = 0, op_scale_a_block_stride = 0;
    reg        env_start = 1'b0, env_sdn_ignore_credit = 1'b0;
    reg [31:0] env_sdn_base = 0, env_sdn_words = 0, env_act_img_base = 0, env_act_region_base = 0;
    reg [31:0] env_scale_img_base = 0, env_scale_region_base = 0;
    reg [15:0] env_act_slice_full = 0, env_act_slice_last = 0, env_act_stride = 0;
    reg [15:0] env_scale_slice_full = 0, env_scale_slice_last = 0, env_scale_stride = 0, env_blocks = 0;
    wire       env_busy;
    wire [31:0] sdn_written;
    wire        dut_busy, dut_done, dut_kblock_active, dut_kblock_done;
    wire [15:0] dut_kblock_index, dut_error_kblock;
    wire [7:0]  dut_error_code, dut_error_detail, dut_error_lq8, dut_error_lane;
    wire [6:0]  dut_retire_count;
    wire [31:0] dut_out_count, dut_saturation_count, dut_mac_count, dut_product_count;
    wire [31:0] dut_staging_underruns, dut_staging_overruns, dut_stream_words_consumed, lockstep_violations;
    reg  [7:0]  lane_rd_sel = 0;
    wire [7:0]  lq8_rd_error_code, lq8_rd_error_detail, lane_rd_error_code, lane_rd_error_detail;
    reg         tree_in_valid = 1'b0, tree_clear = 1'b0;
    reg  [3:0]  tree_in_count = 0;
    reg  [255:0] tree_in_leaf = 0;
    reg  [15:0] tree_in_tag = 0;
    wire        tree_out_valid, tree_busy;
    wire [31:0] tree_out_data;
    wire [15:0] tree_out_tag;
    wire [7:0]  tree_error_code, tree_error_detail;
    reg  [31:0] case_rd_addr = 0, expect_rd_addr = 0, meta_rd_addr = 0, res_rd_addr = 0;
    wire [31:0] case_rd_data, expect_rd_data, meta_rd_data, res_rd_data, acc_rd_data;
    wire [31:0] adder_stages, lanes, region_words, weight_source, staging_in_tile;

    ot_a3_tile64_top #(.ADDER_STAGES(ADDER_STAGES), .WEIGHT_SOURCE(WEIGHT_SOURCE),
                       .STAGING_IN_TILE(STAGING_IN_TILE)) dut (
        .clk(clk), .rst_n(rst_n),
        .op_start(op_start), .op_rows(op_rows), .op_cols(op_cols), .op_depth(op_depth), .op_kblock(op_kblock),
        .op_dtype_a(op_dtype_a), .op_dtype_b(op_dtype_b), .op_group(op_group),
        .op_scale_a(op_scale_a), .op_block_a(op_block_a), .op_block_rows_a(op_block_rows_a),
        .op_scale_b(op_scale_b), .op_block_b(op_block_b),
        .op_a_base(op_a_base), .op_a_block_stride(op_a_block_stride),
        .op_scale_a_base(op_scale_a_base), .op_scale_a_block_stride(op_scale_a_block_stride),
        .op_w_base(op_w_base), .op_w_words(op_w_words),
        .op_ws_base(op_ws_base), .op_ws_block_stride(op_ws_block_stride),
        .op_out_base(op_out_base), .op_out_block_stride(op_out_block_stride), .op_out_fp32(op_out_fp32),
        .env_start(env_start), .env_sdn_base(env_sdn_base), .env_sdn_words(env_sdn_words),
        .env_sdn_ignore_credit(env_sdn_ignore_credit),
        .env_act_img_base(env_act_img_base), .env_act_slice_full(env_act_slice_full),
        .env_act_slice_last(env_act_slice_last), .env_act_stride(env_act_stride),
        .env_act_region_base(env_act_region_base),
        .env_scale_img_base(env_scale_img_base), .env_scale_slice_full(env_scale_slice_full),
        .env_scale_slice_last(env_scale_slice_last), .env_scale_stride(env_scale_stride),
        .env_scale_region_base(env_scale_region_base), .env_blocks(env_blocks),
        .env_busy(env_busy), .sdn_written(sdn_written),
        .dut_busy(dut_busy), .dut_done(dut_done), .dut_kblock_active(dut_kblock_active),
        .dut_kblock_done(dut_kblock_done), .dut_kblock_index(dut_kblock_index),
        .dut_error_code(dut_error_code), .dut_error_detail(dut_error_detail),
        .dut_error_kblock(dut_error_kblock), .dut_error_lq8(dut_error_lq8), .dut_error_lane(dut_error_lane),
        .dut_retire_count(dut_retire_count), .dut_out_count(dut_out_count),
        .dut_saturation_count(dut_saturation_count), .dut_mac_count(dut_mac_count),
        .dut_product_count(dut_product_count), .dut_staging_underruns(dut_staging_underruns),
        .dut_staging_overruns(dut_staging_overruns), .dut_stream_words_consumed(dut_stream_words_consumed),
        .lockstep_violations(lockstep_violations),
        .lane_rd_sel(lane_rd_sel), .lq8_rd_error_code(lq8_rd_error_code), .lq8_rd_error_detail(lq8_rd_error_detail),
        .lane_rd_error_code(lane_rd_error_code), .lane_rd_error_detail(lane_rd_error_detail),
        .tree_in_valid(tree_in_valid), .tree_in_count(tree_in_count), .tree_in_leaf(tree_in_leaf),
        .tree_in_tag(tree_in_tag), .tree_clear(tree_clear),
        .tree_out_valid(tree_out_valid), .tree_out_data(tree_out_data), .tree_out_tag(tree_out_tag),
        .tree_error_code(tree_error_code), .tree_error_detail(tree_error_detail), .tree_busy(tree_busy),
        .case_rd_addr(case_rd_addr), .case_rd_data(case_rd_data),
        .expect_rd_addr(expect_rd_addr), .expect_rd_data(expect_rd_data),
        .meta_rd_addr(meta_rd_addr), .meta_rd_data(meta_rd_data),
        .res_rd_addr(res_rd_addr), .res_rd_data(res_rd_data), .acc_rd_data(acc_rd_data),
        .adder_stages(adder_stages), .lanes(lanes), .region_words(region_words),
        .weight_source(weight_source), .staging_in_tile(staging_in_tile)
    );

    integer failures = 0;
    integer checks = 0;
    integer counted_cases = 0, counted_lane_ops = 0, counted_products = 0, counted_partials = 0;
    integer counted_faults = 0, counted_roots = 0, counted_tree_vectors = 0, counted_kblocks = 0;
    integer meta_cases, meta_lane_ops, meta_products, meta_partials, meta_faults, meta_roots;
    integer meta_stride, meta_tree_vectors, meta_lanes, meta_kblocks;

    integer record [0:CASE_STRIDE-1];
    integer case_index, field, lane, b, e, guard, cycle, n, row, c, k, g, level;
    integer first_retire, last_retire, retired, total_cycles, window, blocks, cpl;
    integer kb_cycles, kb_min, kb_max, kb_sum, kb_count, active_cycles;
    integer written, expect_word, checked_here;
    integer node_count, next_count, vec_count, tree_ok, tag;
    reg [31:0] want, got, got_acc;
    reg [31:0] nodes [0:MAX_BLOCKS-1];
    reg [31:0] next_nodes [0:MAX_BLOCKS-1];

    task fail(input [1023:0] message);
        begin
            failures = failures + 1;
            if (failures < 40) $display("FAIL: case %0d %0s", record[38], message);
        end
    endtask

    task check_equal(input [1023:0] label, input [63:0] got_value, input [63:0] want_value);
        begin
            checks = checks + 1;
            if (got_value !== want_value) begin
                failures = failures + 1;
                if (failures < 40)
                    $display("FAIL: case %0d %0s got %0d want %0d", record[38], label, got_value, want_value);
            end
        end
    endtask

    task read_meta;
        begin
            meta_rd_addr = 0; #1; meta_cases = meta_rd_data;
            meta_rd_addr = 1; #1; meta_lane_ops = meta_rd_data;
            meta_rd_addr = 2; #1; meta_products = meta_rd_data;
            meta_rd_addr = 3; #1; meta_partials = meta_rd_data;
            meta_rd_addr = 4; #1; meta_faults = meta_rd_data;
            meta_rd_addr = 5; #1; meta_roots = meta_rd_data;
            meta_rd_addr = 6; #1; meta_stride = meta_rd_data;
            meta_rd_addr = 7; #1; meta_tree_vectors = meta_rd_data;
            meta_rd_addr = 8; #1; meta_lanes = meta_rd_data;
            meta_rd_addr = 9; #1; meta_kblocks = meta_rd_data;
        end
    endtask

    task load_record(input integer index);
        begin
            for (field = 0; field < CASE_STRIDE; field = field + 1) begin
                case_rd_addr = index * CASE_STRIDE + field;
                #1;
                record[field] = case_rd_data;
            end
        end
    endtask

    task drive_record;
        begin
            op_rows = record[0][15:0]; op_cols = record[1][15:0]; op_depth = record[2][15:0];
            op_kblock = record[3][15:0]; op_dtype_a = record[4][7:0]; op_dtype_b = record[5][7:0];
            op_group = record[6][7:0]; op_scale_a = record[7][0]; op_block_a = record[8][15:0];
            op_block_rows_a = record[9][15:0]; op_scale_b = record[10][0]; op_block_b = record[11][15:0];
            op_a_base = record[12]; op_a_block_stride = record[13][15:0];
            op_scale_a_base = record[14]; op_scale_a_block_stride = record[15][15:0];
            op_w_base = record[16]; op_w_words = record[17]; op_ws_base = record[18];
            op_ws_block_stride = record[19]; op_out_base = record[20]; op_out_block_stride = record[21];
            op_out_fp32 = record[22][0];
            env_sdn_base = record[16]; env_sdn_words = record[48];
            env_sdn_ignore_credit = (record[24] & FLAG_SDN_IGNORE) != 0;
            env_act_img_base = record[39]; env_act_slice_full = record[40][15:0];
            env_act_slice_last = record[41][15:0]; env_act_stride = record[13][15:0];
            env_act_region_base = record[12];
            env_scale_img_base = record[42]; env_scale_slice_full = record[43][15:0];
            env_scale_slice_last = record[44][15:0]; env_scale_stride = record[15][15:0];
            env_scale_region_base = record[14]; env_blocks = record[23][15:0];
        end
    endtask

    // Run one operation to done, sampling at the falling edge (every registered
    // output is stable), summing the retire count and the K-block cycles.
    task launch;
        begin
            @(negedge clk);
            op_start = 1'b1;
            @(negedge clk);
            op_start = 1'b0;
            env_start = 1'b1;
            @(negedge clk);
            env_start = 1'b0;
            cycle = 2;
            retired = 0;
            first_retire = -1;
            last_retire = -1;
            kb_min = -1; kb_max = 0; kb_sum = 0; kb_count = 0; active_cycles = 0;
            guard = 0;
            while (!dut_done && guard < 40000000) begin
                if (dut_retire_count != 7'd0) begin
                    retired = retired + dut_retire_count;
                    if (first_retire < 0) first_retire = cycle;
                    last_retire = cycle;
                end
                if (dut_kblock_active) active_cycles = active_cycles + 1;
                if (dut_kblock_done) begin
                    kb_cycles = active_cycles;
                    active_cycles = 0;
                    kb_count = kb_count + 1;
                    kb_sum = kb_sum + kb_cycles;
                    if (kb_min < 0 || kb_cycles < kb_min) kb_min = kb_cycles;
                    if (kb_cycles > kb_max) kb_max = kb_cycles;
                end
                @(negedge clk);
                cycle = cycle + 1;
                guard = guard + 1;
            end
            total_cycles = cycle;
            if (!dut_done) fail("tile never completed");
            // let the environment models settle
            guard = 0;
            while (env_busy && guard < 100000) begin
                @(negedge clk);
                guard = guard + 1;
            end
        end
    endtask

    // One endpoint vector through the tree beside the tile; waits for its result.
    task tree_vector(input integer count, output reg [31:0] result);
        begin
            @(negedge clk);
            tree_in_valid = 1'b1;
            tree_in_count = count[3:0];
            tree_in_tag = tag[15:0];
            for (k = 0; k < LEAVES; k = k + 1)
                tree_in_leaf[32*k +: 32] = (k < count) ? nodes[g * LEAVES + k] : 32'b0;
            @(negedge clk);
            tree_in_valid = 1'b0;
            guard = 0;
            result = 32'hbad0_bad0;
            while (!tree_out_valid && guard < 40) begin
                @(negedge clk);
                guard = guard + 1;
            end
            if (tree_out_valid) begin
                result = tree_out_data;
                if (tree_out_tag != tag[15:0]) fail("tree output tag mismatch");
            end else begin
                fail("tree endpoint produced no output");
            end
            tag = tag + 1;
            vec_count = vec_count + 1;
        end
    endtask

    initial begin
        repeat (4) @(negedge clk);
        rst_n = 1'b1;
        repeat (2) @(negedge clk);
        read_meta;
        record[38] = -1;
        check_equal("lane count in image", meta_lanes, lanes);
        check_equal("case stride", meta_stride, CASE_STRIDE);

        for (case_index = 0; case_index < meta_cases; case_index = case_index + 1) begin
            load_record(case_index);
            drive_record;
            launch;
            window = record[36];
            blocks = record[23];
            cpl = record[45];
            counted_cases = counted_cases + 1;
            if (record[25] != 0) counted_faults = counted_faults + 1;
            counted_kblocks = counted_kblocks + kb_count;

            check_equal("error_code", {56'b0, dut_error_code}, record[25]);
            check_equal("error_detail", {56'b0, dut_error_detail}, record[26]);
            check_equal("error_kblock", {48'b0, dut_error_kblock}, record[27]);
            check_equal("error_lq8", {56'b0, dut_error_lq8}, record[28]);
            check_equal("error_lane", {56'b0, dut_error_lane}, record[29]);
            check_equal("out_count", {32'b0, dut_out_count}, record[30]);
            check_equal("saturation_count", {32'b0, dut_saturation_count}, 0);
            check_equal("mac_count", {32'b0, dut_mac_count}, record[31]);
            check_equal("product_count", {32'b0, dut_product_count}, record[32]);
            check_equal("retired lane-ops", retired, record[31]);
            if (record[33] != DONT_CARE)
                check_equal("staging_underruns", {32'b0, dut_staging_underruns}, record[33]);
            if (record[26] == 23)
                check_equal("staging_overruns nonzero", (dut_staging_overruns != 0) ? 1 : 0, 1);
            if (record[34] != DONT_CARE)
                check_equal("stream_words_consumed", {32'b0, dut_stream_words_consumed}, record[34]);
            check_equal("K-blocks run", kb_count, (record[24] & FLAG_REFUSED) ? 0 : ((record[25] != 0) ? record[27] + 1 : blocks));
            check_equal("lockstep violations", {32'b0, lockstep_violations}, 0);
            counted_lane_ops = counted_lane_ops + dut_mac_count;
            counted_products = counted_products + dut_product_count;

            if (record[24] & FLAG_RATE) begin
                $display("RATE: case=%0d lane_ops=%0d products=%0d total_cycles=%0d window_cycles=%0d first_retire=%0d last_retire=%0d lanes=%0d kblocks=%0d kblock_cycles_min=%0d kblock_cycles_max=%0d kblock_cycles_sum=%0d",
                         record[38], retired, dut_product_count, total_cycles,
                         (retired > 0) ? (last_retire - first_retire + 1) : 0, first_retire, last_retire, LANES,
                         kb_count, kb_min, kb_max, kb_sum);
            end

            // per-LQ8 and per-lane classes
            for (lane = 0; lane < LANES; lane = lane + 1) begin
                lane_rd_sel = lane[7:0];
                #1;
                check_equal("lane error_code", {56'b0, lane_rd_error_code}, record[144 + lane]);
                check_equal("lane error_detail", {56'b0, lane_rd_error_detail}, record[208 + lane]);
                if (lane % 8 == 0) begin
                    check_equal("lq8 error_code", {56'b0, lq8_rd_error_code}, record[64 + lane / 8]);
                    check_equal("lq8 error_detail", {56'b0, lq8_rd_error_detail}, record[72 + lane / 8]);
                end
            end

            // every partial: written and equal, or unwritten
            checked_here = 0;
            for (lane = 0; lane < LANES; lane = lane + 1) begin
                for (b = 0; b < blocks; b = b + 1) begin
                    if (b < record[46]) written = window;
                    else if ((b == record[46]) && (record[25] != 0) && ((record[24] & FLAG_BLOCK_UNCHECKED) == 0)
                             && ((record[24] & FLAG_REFUSED) == 0)) written = record[80 + lane];
                    else if ((b == record[46]) && (record[24] & FLAG_BLOCK_UNCHECKED)) written = -1;
                    else written = 0;
                    if (written >= 0) begin
                        for (e = 0; e < window; e = e + 1) begin
                            res_rd_addr = lane * region_words + record[20] + b * record[21] + e;
                            expect_rd_addr = record[35] + (lane * blocks + b) * window + e;
                            #1;
                            want = expect_rd_data;
                            got = res_rd_data;
                            got_acc = acc_rd_data;
                            checks = checks + 2;
                            if (e < written) begin
                                checked_here = checked_here + 1;
                                if (got !== want || got_acc !== want) begin
                                    failures = failures + 1;
                                    if (failures < 40)
                                        $display("FAIL: case %0d lane %0d block %0d element %0d got %08x/%08x want %08x",
                                                 record[38], lane, b, e, got, got_acc, want);
                                end
                            end else if (got !== UNWRITTEN || got_acc !== UNWRITTEN) begin
                                failures = failures + 1;
                                if (failures < 40)
                                    $display("FAIL: case %0d lane %0d block %0d element %0d written after the fault: %08x",
                                             record[38], lane, b, e, got);
                            end
                        end
                    end
                end
            end
            counted_partials = counted_partials + checked_here;

            // the tree over the captured partials, column by column
            if (record[47] != 0) begin
                vec_count = 0;
                tag = 1;
                for (row = 0; row < record[0]; row = row + 1) begin
                    for (n = 0; n < record[1]; n = n + 1) begin
                        lane = n % LANES;
                        c = n / LANES;
                        for (b = 0; b < blocks; b = b + 1) begin
                            res_rd_addr = lane * region_words + record[20] + b * record[21] + row * cpl + c;
                            #1;
                            nodes[b] = res_rd_data;
                        end
                        node_count = blocks;
                        while (node_count > 1) begin
                            next_count = 0;
                            for (g = 0; g * LEAVES < node_count; g = g + 1) begin
                                tree_vector((node_count - g * LEAVES < LEAVES) ? (node_count - g * LEAVES) : LEAVES,
                                            next_nodes[g]);
                                next_count = next_count + 1;
                            end
                            for (g = 0; g < next_count; g = g + 1)
                                nodes[g] = next_nodes[g];
                            node_count = next_count;
                        end
                        expect_rd_addr = record[37] + row * record[1] + n;
                        #1;
                        want = expect_rd_data;
                        checks = checks + 1;
                        counted_roots = counted_roots + 1;
                        if (nodes[0] !== want) begin
                            failures = failures + 1;
                            if (failures < 40)
                                $display("FAIL: case %0d row %0d column %0d tree root got %08x want %08x",
                                         record[38], row, n, nodes[0], want);
                        end
                    end
                end
                check_equal("tree vectors", vec_count, record[49]);
                check_equal("tree error_code", {56'b0, tree_error_code}, 0);
                counted_tree_vectors = counted_tree_vectors + vec_count;
            end
        end

        record[38] = -1;
        check_equal("case count", counted_cases, meta_cases);
        check_equal("lane-op count", counted_lane_ops, meta_lane_ops);
        check_equal("product count", counted_products, meta_products);
        check_equal("partial count", counted_partials, meta_partials);
        check_equal("fault case count", counted_faults, meta_faults);
        check_equal("root count", counted_roots, meta_roots);
        check_equal("tree vector count", counted_tree_vectors, meta_tree_vectors);
        check_equal("K-block count", counted_kblocks, meta_kblocks);
        check_equal("final lockstep violations", {32'b0, lockstep_violations}, 0);

        if (failures == 0) begin
            $display("PASS: ABI3 tile64 cases=%0d lane_ops=%0d products=%0d partials=%0d faults=%0d roots=%0d tree_vectors=%0d kblocks=%0d lanes=%0d adder_stages=%0d weight_source=%0d staging_in_tile=%0d",
                     counted_cases, counted_lane_ops, counted_products, counted_partials, counted_faults,
                     counted_roots, counted_tree_vectors, counted_kblocks, LANES, ADDER_STAGES,
                     WEIGHT_SOURCE, STAGING_IN_TILE);
            $display("checks=%0d", checks);
            $finish;
        end else begin
            $display("FAILURES: %0d after checks=%0d", failures, checks);
            $fatal(1);
        end
    end
endmodule
