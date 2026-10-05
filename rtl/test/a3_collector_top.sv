`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for PC64, the partial collector
// (rtl/abi3/ot_a3_partial_collector.sv; results/rtl/abi3_partial_collector.json).
//
// Both checkers -- rtl/test/tb_a3_collector.sv on Icarus and
// rtl/test/a3_collector_harness.cpp on Verilator -- instantiate this module
// and read the same generated images, so the two simulators run identical RTL
// through independently written checkers.  The stimulus is INSIDE the top and
// is a deterministic function of the case table, so the two simulators must
// report the same cycles as well as the same values.
//
// It holds:
//   u_coll   the collector under test;
//   u_tree   one rtl/abi3/ot_a3_tree_endpoint_fp32.sv on the collector's leaf
//            port -- the real consumer of the port this block exists to drive,
//            not a model of it;
//   a partial-port driver that presents the tile's partial port the way
//   ot_a3_tile64 presents it: lane-local addresses op_out_base + b x elems + e,
//   the K-block index on part_kblock, and (mode 0) all 64 lanes on one cycle,
//   which is what the tile's cross-LQ8 lockstep makes happen;
//   capture memories for every emitted leaf vector and every root.
//
// Images (tools/build_abi3_collector_vectors.py):
//   pc_part.hex    the binary32 partials, (block, element, lane) major
//   pc_case.hex    one record per case
//   pc_expect.hex  per case, the tree root and tag of every emitted vector
//   pc_meta.hex    case count and campaign totals
// ---------------------------------------------------------------------------
module ot_a3_collector_top #(
    parameter integer TILE_LANES  = 64,
    parameter integer LEAVES      = 8,
    parameter integer SLOT_ELEMS  = 2,
    parameter integer ADDER_STAGES = 3,
    parameter integer PART_WORDS  = 32768,
    parameter integer CASE_WORDS  = 2048,
    parameter integer EXPECT_WORDS = 8192,
    parameter integer META_WORDS  = 8,
    parameter integer VEC_WORDS   = 2048,
    parameter integer ROOT_WORDS  = 512,
    parameter integer CASE_STRIDE = 24
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        run,
    input  wire [31:0] run_case,
    output reg         busy,
    output reg         done,

    output reg  [31:0] obs_timeout,
    output reg  [31:0] obs_done_pulses,
    output reg  [31:0] obs_vectors,
    output reg  [31:0] obs_roots,
    output wire [7:0]  obs_error_code,
    output wire [7:0]  obs_error_detail,
    output wire [15:0] obs_error_lane,
    output wire [31:0] obs_error_slot,
    output wire [31:0] obs_captured,
    output wire [31:0] obs_vectors_count,
    output wire        obs_busy,
    output wire [7:0]  obs_tree_error_code,
    output reg  [31:0] obs_tag_order_errors,

    input  wire [31:0] part_rd_addr,
    output wire [31:0] part_rd_data,
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] vec_rd_addr,
    output wire [31:0] vec_rd_data,
    input  wire [31:0] root_rd_addr,
    output wire [31:0] root_rd_data,
    output wire [31:0] slot_elems_param,
    output wire [31:0] leaves_param,
    output wire [31:0] adder_stages_param
);
    localparam integer VEC_STRIDE = LEAVES + 2;      // leaves, tag, count
    localparam integer LANE_AW    = $clog2(TILE_LANES);

    reg [31:0] part_mem   [0:PART_WORDS-1];
    reg [31:0] case_mem   [0:CASE_WORDS-1];
    reg [31:0] expect_mem [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem   [0:META_WORDS-1];
    reg [31:0] vec_mem    [0:VEC_WORDS-1];
    reg [31:0] root_mem   [0:ROOT_WORDS-1];

    integer init_i;
    initial begin
        $readmemh("pc_part.hex", part_mem);
        $readmemh("pc_case.hex", case_mem);
        $readmemh("pc_expect.hex", expect_mem);
        $readmemh("pc_meta.hex", meta_mem);
        for (init_i = 0; init_i < VEC_WORDS; init_i = init_i + 1) vec_mem[init_i] = 32'hdeadbeef;
        for (init_i = 0; init_i < ROOT_WORDS; init_i = init_i + 1) root_mem[init_i] = 32'hdeadbeef;
    end

    assign part_rd_data   = (part_rd_addr   < PART_WORDS)   ? part_mem[part_rd_addr]     : 32'b0;
    assign case_rd_data   = (case_rd_addr   < CASE_WORDS)   ? case_mem[case_rd_addr]     : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr   < META_WORDS)   ? meta_mem[meta_rd_addr]     : 32'b0;
    assign vec_rd_data    = (vec_rd_addr    < VEC_WORDS)    ? vec_mem[vec_rd_addr]       : 32'b0;
    assign root_rd_data   = (root_rd_addr   < ROOT_WORDS)   ? root_mem[root_rd_addr]     : 32'b0;
    assign slot_elems_param   = SLOT_ELEMS;
    assign leaves_param       = LEAVES;
    assign adder_stages_param = ADDER_STAGES;

    // -- the case, read combinationally out of the image -------------------------------------
    reg [31:0] base;
    wire [31:0] f_blocks   = case_mem[base + 0];
    wire [31:0] f_elems    = case_mem[base + 1];
    wire [31:0] f_out_base = case_mem[base + 2];
    wire [31:0] f_part_base = case_mem[base + 3];
    wire [31:0] f_mode     = case_mem[base + 4];
    wire [31:0] f_inject   = case_mem[base + 5];
    wire [31:0] f_cfg_blocks = case_mem[base + 6];
    wire [31:0] f_cfg_elems  = case_mem[base + 7];

    // Injections.  1 an address outside the K-block window; 2 a K-block index at
    // or above B; 3 the same leaf written twice; 4 a leaf never written, so the
    // slot becomes ready incomplete; 5..7 inadmissible configuration.
    localparam integer INJ_NONE       = 0;
    localparam integer INJ_ADDR       = 1;
    localparam integer INJ_KBLOCK     = 2;
    localparam integer INJ_DUPLICATE  = 3;
    localparam integer INJ_INCOMPLETE = 4;

    // -- collector ports ------------------------------------------------------------------------
    reg                       cfg_start;
    reg  [15:0]               cfg_blocks;
    reg  [15:0]               cfg_elems;
    reg  [31:0]               cfg_out_base;
    reg                       clear;
    reg  [TILE_LANES-1:0]     part_we;
    reg  [32*TILE_LANES-1:0]  part_addr;
    reg  [32*TILE_LANES-1:0]  part_data;
    reg  [15:0]               part_kblock;

    wire                  coll_out_valid;
    wire [3:0]            coll_out_count;
    wire [32*LEAVES-1:0]  coll_out_leaf;
    wire [15:0]           coll_out_tag;
    wire                  coll_out_last;
    wire                  coll_done;

    ot_a3_partial_collector #(
        .TILE_LANES(TILE_LANES), .LEAVES(LEAVES), .SLOT_ELEMS(SLOT_ELEMS), .TAG_W(16)
    ) u_coll (
        .clk(clk), .rst_n(rst_n),
        .cfg_start(cfg_start), .cfg_blocks(cfg_blocks), .cfg_elems(cfg_elems),
        .cfg_out_base(cfg_out_base), .clear(clear),
        .part_we(part_we), .part_addr(part_addr), .part_data(part_data),
        .part_kblock(part_kblock),
        .out_valid(coll_out_valid), .out_leaf_count(coll_out_count),
        .out_leaf(coll_out_leaf), .out_tag(coll_out_tag), .out_last(coll_out_last),
        .busy(obs_busy), .done(coll_done),
        .error_code(obs_error_code), .error_detail(obs_error_detail),
        .error_lane(obs_error_lane), .error_slot(obs_error_slot),
        .captured_count(obs_captured), .vectors_count(obs_vectors_count)
    );

    // -- the real consumer of the leaf port -----------------------------------------------------
    /* verilator lint_off UNUSEDSIGNAL */
    wire        tree_out_last;
    wire [7:0]  tree_error_detail;
    wire [1:0]  tree_error_level;
    wire [15:0] tree_error_tag;
    wire        tree_busy;
    wire [31:0] tree_adds, tree_combines;
    /* verilator lint_on UNUSEDSIGNAL */
    wire        tree_out_valid;
    wire [31:0] tree_out_data;
    wire [15:0] tree_out_tag;

    ot_a3_tree_endpoint_fp32 #(.LEAVES(LEAVES), .ADDER_STAGES(ADDER_STAGES), .TAG_W(16)) u_tree (
        .clk(clk), .rst_n(rst_n),
        .in_valid(coll_out_valid), .in_leaf_count(coll_out_count), .in_leaf(coll_out_leaf),
        .in_tag(coll_out_tag), .in_last(coll_out_last), .clear(clear),
        .out_valid(tree_out_valid), .out_data(tree_out_data), .out_tag(tree_out_tag),
        .out_last(tree_out_last),
        .error_code(obs_tree_error_code), .error_detail(tree_error_detail),
        .error_level(tree_error_level), .error_tag(tree_error_tag), .busy(tree_busy),
        .adds_count(tree_adds), .combines_count(tree_combines)
    );

    // -- capture ----------------------------------------------------------------------------------
    reg [15:0] next_tag;
    integer cv;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            obs_vectors <= 32'b0;
            obs_roots <= 32'b0;
            obs_tag_order_errors <= 32'b0;
            next_tag <= 16'b0;
        end else begin
            if (cfg_start) begin
                obs_vectors <= 32'b0;
                obs_roots <= 32'b0;
                obs_tag_order_errors <= 32'b0;
                next_tag <= 16'b0;
            end else begin
                if (coll_out_valid) begin
                    if (coll_out_tag != next_tag)
                        obs_tag_order_errors <= obs_tag_order_errors + 32'd1;
                    next_tag <= coll_out_tag + 16'd1;
                    for (cv = 0; cv < LEAVES; cv = cv + 1)
                        vec_mem[obs_vectors * VEC_STRIDE + cv] <= coll_out_leaf[32*cv +: 32];
                    vec_mem[obs_vectors * VEC_STRIDE + LEAVES]     <= {16'b0, coll_out_tag};
                    vec_mem[obs_vectors * VEC_STRIDE + LEAVES + 1] <= {28'b0, coll_out_count};
                    obs_vectors <= obs_vectors + 32'd1;
                end
                if (tree_out_valid) begin
                    root_mem[obs_roots * 2]     <= tree_out_data;
                    root_mem[obs_roots * 2 + 1] <= {16'b0, tree_out_tag};
                    obs_roots <= obs_roots + 32'd1;
                end
            end
        end
    end

    // -- the partial-port driver -------------------------------------------------------------------
    localparam [2:0] D_IDLE = 3'd0, D_START = 3'd1, D_DRIVE = 3'd2, D_GAP = 3'd3,
                     D_SETTLE = 3'd4, D_FINISH = 3'd5;
    reg [2:0]  dstate;
    reg [15:0] d_b, d_e;
    reg [LANE_AW-1:0] d_lane;
    reg [15:0] blocks_r, elems_r;
    reg [31:0] out_base_r, part_base_r, mode_r, inject_r;
    reg [31:0] settle;
    reg        refused;

    wire [31:0] step_index = ({16'b0, d_b} * {16'b0, elems_r}) + {16'b0, d_e};
    wire [31:0] part_word_base = part_base_r + step_index * TILE_LANES;
    wire        first_step = (d_b == 16'b0) && (d_e == 16'b0);
    wire [31:0] drive_addr_normal = out_base_r + step_index;
    wire [31:0] drive_addr = (first_step && (inject_r == INJ_ADDR))
                             ? (out_base_r + {16'b0, elems_r} + step_index)
                             : drive_addr_normal;
    wire [15:0] drive_kblock = (first_step && (inject_r == INJ_KBLOCK)) ? blocks_r : d_b;
    // INJ_INCOMPLETE: lane 0's element 0 of K-block 0 is never written.
    wire        skip_lane0 = (inject_r == INJ_INCOMPLETE) && first_step;
    // INJ_DUPLICATE: K-block 0 element 0 is presented twice (the gap state repeats it).
    reg         duplicate_pending;

    integer dj;
    always @* begin
        part_we   = {TILE_LANES{1'b0}};
        part_addr = {32*TILE_LANES{1'b0}};
        part_data = {32*TILE_LANES{1'b0}};
        part_kblock = d_b;
        if (dstate == D_DRIVE) begin
            part_kblock = drive_kblock;
            for (dj = 0; dj < TILE_LANES; dj = dj + 1) begin
                part_addr[32*dj +: 32] = drive_addr;
                part_data[32*dj +: 32] = part_mem[(part_word_base + dj) % PART_WORDS];
                if (mode_r == 32'd0)
                    part_we[dj] = !(skip_lane0 && (dj == 0));
                else
                    part_we[dj] = (dj[LANE_AW-1:0] == d_lane) && !(skip_lane0 && (dj == 0));
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dstate <= D_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            cfg_start <= 1'b0;
            clear <= 1'b0;
            cfg_blocks <= 16'b0;
            cfg_elems <= 16'b0;
            cfg_out_base <= 32'b0;
            base <= 32'b0;
            d_b <= 16'b0; d_e <= 16'b0; d_lane <= {LANE_AW{1'b0}};
            blocks_r <= 16'b0; elems_r <= 16'b0;
            out_base_r <= 32'b0; part_base_r <= 32'b0; mode_r <= 32'b0; inject_r <= 32'b0;
            settle <= 32'b0;
            obs_timeout <= 32'b0;
            obs_done_pulses <= 32'b0;
            refused <= 1'b0;
            duplicate_pending <= 1'b0;
        end else begin
            done <= 1'b0;
            cfg_start <= 1'b0;
            clear <= 1'b0;
            if (coll_done) obs_done_pulses <= obs_done_pulses + 32'd1;

            case (dstate)
                D_IDLE: begin
                    if (run) begin
                        base <= run_case * CASE_STRIDE;
                        busy <= 1'b1;
                        // the previous case's fault is cleared HERE, one cycle
                        // before cfg_start, so that a case's error_* survive
                        // until the checker has read them
                        clear <= 1'b1;
                        obs_timeout <= 32'b0;
                        obs_done_pulses <= 32'b0;
                        dstate <= D_START;
                    end
                end
                D_START: begin
                    blocks_r <= f_blocks[15:0];
                    elems_r <= f_elems[15:0];
                    out_base_r <= f_out_base;
                    part_base_r <= f_part_base;
                    mode_r <= f_mode;
                    inject_r <= f_inject;
                    cfg_blocks <= f_cfg_blocks[15:0];
                    cfg_elems <= f_cfg_elems[15:0];
                    cfg_out_base <= f_out_base;
                    cfg_start <= 1'b1;
                    refused <= (f_cfg_blocks == 32'd0) || (f_cfg_blocks > LEAVES) ||
                               (f_cfg_elems == 32'd0) || (f_cfg_elems > SLOT_ELEMS);
                    d_b <= 16'b0; d_e <= 16'b0; d_lane <= {LANE_AW{1'b0}};
                    duplicate_pending <= (f_inject == INJ_DUPLICATE);
                    settle <= 32'b0;
                    dstate <= D_SETTLE;
                end
                D_SETTLE: begin
                    // one cycle for cfg_start to be sampled; a refused configuration
                    // never drives the port at all
                    dstate <= refused ? D_FINISH : D_DRIVE;
                end
                D_DRIVE: begin
                    if (mode_r == 32'd0) begin
                        if (duplicate_pending && first_step) begin
                            duplicate_pending <= 1'b0;   // present the same step again
                        end else if (d_e + 16'd1 >= elems_r) begin
                            d_e <= 16'b0;
                            if (d_b + 16'd1 >= blocks_r) begin
                                dstate <= D_GAP;
                                settle <= 32'b0;
                            end else begin
                                d_b <= d_b + 16'd1;
                            end
                        end else begin
                            d_e <= d_e + 16'd1;
                        end
                    end else begin
                        if (d_lane + {{(LANE_AW-1){1'b0}}, 1'b1} == {LANE_AW{1'b0}}) begin
                            d_lane <= {LANE_AW{1'b0}};
                            if (duplicate_pending && first_step) begin
                                duplicate_pending <= 1'b0;
                            end else if (d_e + 16'd1 >= elems_r) begin
                                d_e <= 16'b0;
                                if (d_b + 16'd1 >= blocks_r) begin
                                    dstate <= D_GAP;
                                    settle <= 32'b0;
                                end else begin
                                    d_b <= d_b + 16'd1;
                                end
                            end else begin
                                d_e <= d_e + 16'd1;
                            end
                        end else begin
                            d_lane <= d_lane + {{(LANE_AW-1){1'b0}}, 1'b1};
                        end
                    end
                    if (obs_error_code != 8'b0) begin
                        dstate <= D_GAP;
                        settle <= 32'b0;
                    end
                end
                D_GAP: begin
                    // drain: the collector emits, the endpoint retires
                    settle <= settle + 32'd1;
                    if ((!obs_busy && !tree_busy) || (settle > 32'd4000)) begin
                        if (settle > 32'd4000) obs_timeout <= 32'd1;
                        settle <= 32'b0;
                        dstate <= D_FINISH;
                    end
                end
                D_FINISH: begin
                    settle <= settle + 32'd1;
                    if (settle > 32'd8) begin
                        busy <= 1'b0;
                        done <= 1'b1;
                        dstate <= D_IDLE;
                    end
                end
                default: dstate <= D_IDLE;
            endcase
        end
    end
endmodule
