`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for ROUTE.CANDIDATE_MASK
// (rtl/abi3/ot_a3_route_candidate_mask.sv;
//  results/rtl/a3_v41_candidate_mask_campaign.json).
//
// Both checkers -- rtl/test/tb_a3_candidate_mask.sv on Icarus Verilog and
// rtl/test/a3_candidate_mask_harness.cpp on Verilator -- instantiate this
// module and read the same generated images, so the two simulators run
// identical RTL through independently written checkers.  The stimulus is INSIDE
// the top and is a deterministic function of the case table, so the two
// simulators must report the same CYCLES as well as the same values -- which is
// what makes the measured initiation interval a cross-checked number.
//
// FIVE ELABORATIONS, not one.  Each case names the geometry it runs on:
//
//   0  BLOCK 8,  MAX_WIDTH 1,048,576, MAX_IDS 2,048, pinned   -- V4.1
//   1  BLOCK 1,  MAX_WIDTH 4,096,     MAX_IDS 4,096, pinned   -- degenerate
//   2  BLOCK 3,  MAX_WIDTH 4,095,     MAX_IDS 1,365, pinned   -- not 2^k
//   3  BLOCK 16, MAX_WIDTH 8,192,     MAX_IDS 512,   pinned   -- wider block
//   4  BLOCK 8,  MAX_WIDTH 4,096,     MAX_IDS 2,048, UNPINNED -- what the
//                                                                pinned-last-
//                                                                block rule is
//                                                                worth
//
// The geometry table is a parameter of this top, not a constant of the block,
// and every instance drives its elaborated values back out on obs_param_*, so a
// checker compares against what was ELABORATED rather than against a number it
// was told.
//
// Images (tools/build_a3_v41_candidate_mask_vectors.py):
//   cm_case.hex    one 16-word record per case
//   cm_ids.hex     the chosen-block id operand memory
//   cm_expect.hex  the expected mask words, from
//                  runtime/reference/candidate_pool.py::select_candidate_mask
//   cm_meta.hex    case count and campaign totals
// ---------------------------------------------------------------------------
module ot_a3_candidate_mask_top #(
    parameter integer WORD_BITS = 32,
    parameter integer GEOMS = 5,
    parameter integer G0_BLOCK = 8,
    parameter integer G0_WIDTH = 1048576,
    parameter integer G0_IDS   = 2048,
    parameter integer G0_PIN   = 1,
    parameter integer G1_BLOCK = 1,
    parameter integer G1_WIDTH = 4096,
    parameter integer G1_IDS   = 4096,
    parameter integer G1_PIN   = 1,
    parameter integer G2_BLOCK = 3,
    parameter integer G2_WIDTH = 4095,
    parameter integer G2_IDS   = 1365,
    parameter integer G2_PIN   = 1,
    parameter integer G3_BLOCK = 16,
    parameter integer G3_WIDTH = 8192,
    parameter integer G3_IDS   = 512,
    parameter integer G3_PIN   = 1,
    parameter integer G4_BLOCK = 8,
    parameter integer G4_WIDTH = 4096,
    parameter integer G4_IDS   = 2048,
    parameter integer G4_PIN   = 0,
    parameter integer CASE_WORDS   = 1024,
    parameter integer IDS_WORDS    = 16384,
    parameter integer EXPECT_WORDS = 65536,
    parameter integer META_WORDS   = 8,
    parameter integer CAP_WORDS    = 32768,
    parameter integer CASE_STRIDE  = 16,
    parameter integer TIMEOUT      = 4000000
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        run,
    input  wire [31:0] run_case,
    output reg         busy,
    output reg         done,

    // the block's own reports, from the geometry this case named
    output wire [7:0]  obs_error_code,
    output wire [7:0]  obs_error_detail,
    output wire [31:0] obs_error_slot,
    output wire [31:0] obs_error_value,
    output wire [31:0] obs_out_count,
    output wire [31:0] obs_population,
    output wire [31:0] obs_blocks,
    output wire [31:0] obs_ids_consumed,
    output wire [31:0] obs_emit_gap_max,
    output wire [31:0] obs_param_block,
    output wire [31:0] obs_param_max_width,
    output wire [31:0] obs_param_max_ids,
    output wire [31:0] obs_param_word_bits,
    output wire [31:0] obs_param_pin_last,
    output wire        obs_block_busy,

    // what the top measured for itself
    output reg  [31:0] obs_pulses,          // out_we assertions observed
    output reg  [31:0] obs_span,            // cycles from the first to the last
    output reg  [31:0] obs_addr_errors,     // out_addr not out_base + pulse
    output reg  [31:0] obs_cycles,          // start to done
    output reg  [31:0] obs_done_pulses,
    output reg  [31:0] obs_timeout,
    output reg  [31:0] obs_write_overflow,  // writes outside the capture window
    output reg  [31:0] obs_id_reads,        // operand-port reads the block issued

    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] ids_rd_addr,
    output wire [31:0] ids_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] cap_rd_addr,
    output wire [31:0] cap_rd_data,
    output wire [31:0] geoms_param,
    output wire [31:0] case_stride_param
);
    reg [31:0] case_mem   [0:CASE_WORDS-1];
    reg [31:0] ids_mem    [0:IDS_WORDS-1];
    reg [31:0] expect_mem [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem   [0:META_WORDS-1];
    reg [31:0] cap_mem    [0:CAP_WORDS-1];

    integer init_i;
    initial begin
        $readmemh("cm_case.hex", case_mem);
        $readmemh("cm_ids.hex", ids_mem);
        $readmemh("cm_expect.hex", expect_mem);
        $readmemh("cm_meta.hex", meta_mem);
        for (init_i = 0; init_i < CAP_WORDS; init_i = init_i + 1)
            cap_mem[init_i] = 32'hdeadbeef;
    end

    assign case_rd_data   = (case_rd_addr   < CASE_WORDS)   ? case_mem[case_rd_addr]     : 32'b0;
    assign ids_rd_data    = (ids_rd_addr    < IDS_WORDS)    ? ids_mem[ids_rd_addr]       : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr   < META_WORDS)   ? meta_mem[meta_rd_addr]     : 32'b0;
    assign cap_rd_data    = (cap_rd_addr    < CAP_WORDS)    ? cap_mem[cap_rd_addr]       : 32'hdeadbeef;
    assign geoms_param      = GEOMS;
    assign case_stride_param = CASE_STRIDE;

    // -- the case, read out of the image ------------------------------------
    reg [31:0] base;
    wire [31:0] f_geom     = case_mem[base + 0];
    wire [7:0]  f_subop    = case_mem[base + 1][7:0];
    wire [31:0] f_width    = case_mem[base + 2];
    wire [31:0] f_id_count = case_mem[base + 3];
    wire [31:0] f_block    = case_mem[base + 4];
    wire [31:0] f_max_pop  = case_mem[base + 5];
    wire [31:0] f_ids_base = case_mem[base + 6];
    wire [31:0] f_out_base = case_mem[base + 7];

    reg        start;
    reg [31:0] sel;
    reg [31:0] out_base_r;

    wire                 d_id_rd_en   [0:GEOMS-1];
    wire [31:0]          d_id_rd_addr [0:GEOMS-1];
    wire                 d_out_we     [0:GEOMS-1];
    wire [31:0]          d_out_addr   [0:GEOMS-1];
    wire [WORD_BITS-1:0] d_out_data   [0:GEOMS-1];
    wire                 d_busy       [0:GEOMS-1];
    wire                 d_done       [0:GEOMS-1];
    wire [7:0]           d_err_code   [0:GEOMS-1];
    wire [7:0]           d_err_detail [0:GEOMS-1];
    wire [31:0]          d_err_slot   [0:GEOMS-1];
    wire [31:0]          d_err_value  [0:GEOMS-1];
    wire [31:0]          d_out_count  [0:GEOMS-1];
    wire [31:0]          d_population [0:GEOMS-1];
    wire [31:0]          d_blocks     [0:GEOMS-1];
    wire [31:0]          d_ids_used   [0:GEOMS-1];
    wire [31:0]          d_gap_max    [0:GEOMS-1];
    wire [31:0]          d_p_block    [0:GEOMS-1];
    wire [31:0]          d_p_width    [0:GEOMS-1];
    wire [31:0]          d_p_ids      [0:GEOMS-1];
    wire [31:0]          d_p_word     [0:GEOMS-1];
    wire [31:0]          d_p_pin      [0:GEOMS-1];

    // one synchronous operand read, shared: only the named geometry runs
    reg [31:0] ids_q;
    wire [31:0] sel_id_addr = d_id_rd_addr[sel[2:0]];
    always @(posedge clk) begin
        ids_q <= (sel_id_addr < IDS_WORDS) ? ids_mem[sel_id_addr] : 32'hffffffff;
    end

    genvar gi;
    generate
        for (gi = 0; gi < GEOMS; gi = gi + 1) begin : g_dut
            localparam integer P_BLOCK =
                (gi == 0) ? G0_BLOCK : (gi == 1) ? G1_BLOCK :
                (gi == 2) ? G2_BLOCK : (gi == 3) ? G3_BLOCK : G4_BLOCK;
            localparam integer P_WIDTH =
                (gi == 0) ? G0_WIDTH : (gi == 1) ? G1_WIDTH :
                (gi == 2) ? G2_WIDTH : (gi == 3) ? G3_WIDTH : G4_WIDTH;
            localparam integer P_IDS =
                (gi == 0) ? G0_IDS : (gi == 1) ? G1_IDS :
                (gi == 2) ? G2_IDS : (gi == 3) ? G3_IDS : G4_IDS;
            localparam integer P_PIN =
                (gi == 0) ? G0_PIN : (gi == 1) ? G1_PIN :
                (gi == 2) ? G2_PIN : (gi == 3) ? G3_PIN : G4_PIN;
            ot_a3_route_candidate_mask #(
                .BLOCK(P_BLOCK),
                .MAX_WIDTH(P_WIDTH),
                .MAX_IDS(P_IDS),
                .WORD_BITS(WORD_BITS),
                .PIN_LAST_BLOCK(P_PIN)
            ) u_cm (
                .clk(clk),
                .rst_n(rst_n),
                .start(start && (sel == gi)),
                .cfg_subop(f_subop),
                .cfg_width(f_width),
                .cfg_id_count(f_id_count),
                .cfg_block(f_block),
                .cfg_max_pop(f_max_pop),
                .cfg_ids_base(f_ids_base),
                .cfg_out_base(f_out_base),
                .id_rd_en(d_id_rd_en[gi]),
                .id_rd_addr(d_id_rd_addr[gi]),
                .id_rd_data(ids_q),
                .out_we(d_out_we[gi]),
                .out_addr(d_out_addr[gi]),
                .out_data(d_out_data[gi]),
                .busy(d_busy[gi]),
                .done(d_done[gi]),
                .error_code(d_err_code[gi]),
                .error_detail(d_err_detail[gi]),
                .error_slot(d_err_slot[gi]),
                .error_value(d_err_value[gi]),
                .obs_out_count(d_out_count[gi]),
                .obs_population(d_population[gi]),
                .obs_blocks(d_blocks[gi]),
                .obs_ids_consumed(d_ids_used[gi]),
                .obs_emit_gap_max(d_gap_max[gi]),
                .obs_param_block(d_p_block[gi]),
                .obs_param_max_width(d_p_width[gi]),
                .obs_param_max_ids(d_p_ids[gi]),
                .obs_param_word_bits(d_p_word[gi]),
                .obs_param_pin_last(d_p_pin[gi])
            );
        end
    endgenerate

    wire [2:0] s = sel[2:0];
    assign obs_error_code   = d_err_code[s];
    assign obs_error_detail = d_err_detail[s];
    assign obs_error_slot   = d_err_slot[s];
    assign obs_error_value  = d_err_value[s];
    assign obs_out_count    = d_out_count[s];
    assign obs_population   = d_population[s];
    assign obs_blocks       = d_blocks[s];
    assign obs_ids_consumed = d_ids_used[s];
    assign obs_emit_gap_max = d_gap_max[s];
    assign obs_param_block     = d_p_block[s];
    assign obs_param_max_width = d_p_width[s];
    assign obs_param_max_ids   = d_p_ids[s];
    assign obs_param_word_bits = d_p_word[s];
    assign obs_param_pin_last  = d_p_pin[s];
    assign obs_block_busy   = d_busy[s];

    wire        sel_id_en    = d_id_rd_en[s];
    wire        sel_out_we   = d_out_we[s];
    wire [31:0] sel_out_addr = d_out_addr[s];
    wire [WORD_BITS-1:0] sel_out_data = d_out_data[s];
    wire        sel_done     = d_done[s];

    localparam [2:0] T_IDLE   = 3'd0;
    localparam [2:0] T_LAUNCH = 3'd1;
    localparam [2:0] T_WAIT   = 3'd2;
    localparam [2:0] T_FINISH = 3'd3;
    reg [2:0] tstate;
    reg [31:0] guard;
    reg [31:0] first_cycle;
    reg        first_seen;

    always @(posedge clk) begin
        if (!rst_n) begin
            tstate <= T_IDLE;
            busy <= 1'b0;
            done <= 1'b0;
            start <= 1'b0;
            sel <= 32'd0;
            base <= 32'd0;
            out_base_r <= 32'd0;
            obs_pulses <= 32'd0;
            obs_span <= 32'd0;
            obs_addr_errors <= 32'd0;
            obs_cycles <= 32'd0;
            obs_done_pulses <= 32'd0;
            obs_timeout <= 32'd0;
            obs_write_overflow <= 32'd0;
            obs_id_reads <= 32'd0;
            guard <= 32'd0;
            first_seen <= 1'b0;
            first_cycle <= 32'd0;
        end else begin
            done <= 1'b0;
            start <= 1'b0;
            case (tstate)
                T_IDLE: begin
                    if (run) begin
                        busy <= 1'b1;
                        base <= run_case * CASE_STRIDE;
                        obs_pulses <= 32'd0;
                        obs_span <= 32'd0;
                        obs_addr_errors <= 32'd0;
                        obs_cycles <= 32'd0;
                        obs_done_pulses <= 32'd0;
                        obs_timeout <= 32'd0;
                        obs_write_overflow <= 32'd0;
                        obs_id_reads <= 32'd0;
                        guard <= 32'd0;
                        first_seen <= 1'b0;
                        first_cycle <= 32'd0;
                        tstate <= T_LAUNCH;
                    end
                end
                T_LAUNCH: begin
                    // the case fields are combinational on base, which is now
                    // stable: latch the geometry and pulse start
                    sel <= (f_geom < GEOMS) ? f_geom : 32'd0;
                    out_base_r <= f_out_base;
                    start <= 1'b1;
                    tstate <= T_WAIT;
                end
                T_WAIT: begin
                    guard <= guard + 32'd1;
                    obs_cycles <= obs_cycles + 32'd1;
                    if (sel_id_en) obs_id_reads <= obs_id_reads + 32'd1;
                    if (sel_out_we) begin
                        if (sel_out_addr < CAP_WORDS)
                            cap_mem[sel_out_addr] <= sel_out_data;
                        else
                            obs_write_overflow <= obs_write_overflow + 32'd1;
                        if (sel_out_addr != out_base_r + obs_pulses)
                            obs_addr_errors <= obs_addr_errors + 32'd1;
                        obs_pulses <= obs_pulses + 32'd1;
                        if (!first_seen) begin
                            first_seen <= 1'b1;
                            first_cycle <= obs_cycles;
                        end else begin
                            obs_span <= obs_cycles - first_cycle;
                        end
                    end
                    if (sel_done) begin
                        obs_done_pulses <= obs_done_pulses + 32'd1;
                        tstate <= T_FINISH;
                    end
                    if (guard + 32'd1 >= TIMEOUT) begin
                        obs_timeout <= 32'd1;
                        tstate <= T_FINISH;
                    end
                end
                T_FINISH: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    tstate <= T_IDLE;
                end
                default: tstate <= T_IDLE;
            endcase
        end
    end
endmodule
