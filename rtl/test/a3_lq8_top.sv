`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Verification top for the LQ8 lane block (the D1 extension to eight lanes
// and the block rate; results/rtl/abi3_lq8.json).
//
// Both checkers -- rtl/test/tb_a3_lq8.sv on Icarus and
// rtl/test/a3_lq8_harness.cpp on Verilator -- instantiate this module and
// read the same generated images, so the two simulators run identical RTL
// through independently written checkers.  It holds:
//
//   u_dut   rtl/abi3/ot_a3_lq8.sv with LANES lanes on the shared activation
//           port, the weight stream port and the weight scale table port;
//   u_ref   one rtl/abi3/ot_a3_lane_pipelined.sv, the qualified single lane,
//           which the checkers run once per block lane on that lane's own
//           column-major weight image and lane-local scale image -- the
//           same weight elements the stream carries, in the layout the
//           single lane was qualified on (gate D1).
//
// Result memories are split into one region per lane: block lane i writes
// region i, and the reference run for lane i writes region i of its own
// memory under ref_lane, so the checkers compare the two region by region.
//
// Images (tools/build_abi3_lq8_vectors.py):
//   lq8_m0.hex     activation words, one 64-bit word per k-group (shared)
//   lq8_m2.hex     activation E8M0 codes, one per 32-bit word (shared)
//   lq8_w.hex      the weight stream, one 128-bit word per block lane-op
//   lq8_ws.hex     the weight scale table, one 64-bit word per lane-local
//                  E8M0 index (byte i for lane i)
//   lq8_m1.hex     per-lane column-major weight words for the reference runs
//   lq8_m3.hex     per-lane lane-local E8M0 codes for the reference runs
//   lq8_expect.hex two words per lane per output element [word, accumulator]
//   lq8_case.hex   one record per case (layout in the checkers)
//   lq8_meta.hex   case count and the campaign totals
//
// Lockstep is an invariant of the block, not a policed condition; this top
// checks it on every clock: whenever a lane requests an activation word, its
// addresses must equal the ones the block forwarded, and its four request
// enables must agree.  lockstep_violations counts the cycles on which that
// failed and must read zero after every case.
// ---------------------------------------------------------------------------
module ot_a3_lq8_top #(
    parameter integer LANES         = 8,
    parameter integer ADDER_STAGES  = 3,
    parameter integer ACC_SLOTS     = 8,
    parameter integer OPERAND_WORDS = 262144,
    parameter integer STREAM_WORDS  = 524288,
    parameter integer SCALE_WORDS   = 65536,
    parameter integer REGION_WORDS  = 16384,
    parameter integer CASE_WORDS    = 16384,
    parameter integer EXPECT_WORDS  = 262144,
    parameter integer META_WORDS    = 12
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start_dut,
    input  wire        start_ref,
    // shared configuration
    input  wire [15:0] cfg_rows,
    input  wire [15:0] cfg_cols,           // block columns (u_dut)
    input  wire [15:0] cfg_depth,
    input  wire [7:0]  cfg_dtype_a,
    input  wire [7:0]  cfg_dtype_b,
    input  wire [7:0]  cfg_group,
    input  wire [31:0] cfg_a_base,
    input  wire        cfg_scale_a,
    input  wire [15:0] cfg_block_a,
    input  wire [15:0] cfg_block_rows_a,
    input  wire [31:0] cfg_scale_a_base,
    input  wire        cfg_scale_b,
    input  wire [15:0] cfg_block_b,
    input  wire [31:0] cfg_out_base,
    input  wire        cfg_out_fp32,
    // block only
    input  wire [31:0] cfg_w_base,
    input  wire [31:0] cfg_ws_base,
    // reference lane only
    input  wire [15:0] ref_cfg_cols,       // columns per lane
    input  wire [31:0] ref_cfg_b_base,
    input  wire [31:0] ref_cfg_scale_b_base,
    input  wire [3:0]  ref_lane,           // result region the reference writes

    // block status
    output wire        dut_busy,
    output wire        dut_done,
    output wire [7:0]  dut_error_code,
    output wire [7:0]  dut_error_detail,
    output wire [7:0]  dut_error_lane,
    output wire [31:0] dut_out_count,
    output wire [31:0] dut_saturation_count,
    output wire [31:0] dut_mac_count,
    output wire [31:0] dut_product_count,
    output wire [3:0]  dut_retire_count,
    output reg  [31:0] lockstep_violations,

    // per-lane status, selected
    input  wire [3:0]  lane_rd_sel,
    output reg  [31:0] lane_rd_error_code,
    output reg  [31:0] lane_rd_error_detail,
    output reg  [31:0] lane_rd_out_count,
    output reg  [31:0] lane_rd_saturation_count,
    output reg  [31:0] lane_rd_mac_count,
    output reg  [31:0] lane_rd_product_count,

    // reference lane status
    output wire        ref_busy,
    output wire        ref_done,
    output wire [7:0]  ref_error_code,
    output wire [7:0]  ref_error_detail,
    output wire [31:0] ref_out_count,
    output wire [31:0] ref_saturation_count,
    output wire [31:0] ref_mac_count,
    output wire [31:0] ref_product_count,

    // read-back for the checkers
    input  wire [31:0] case_rd_addr,
    output wire [31:0] case_rd_data,
    input  wire [31:0] expect_rd_addr,
    output wire [31:0] expect_rd_data,
    input  wire [31:0] meta_rd_addr,
    output wire [31:0] meta_rd_data,
    input  wire [31:0] res_rd_addr,        // region * REGION_WORDS + address
    output wire [31:0] dut_res_rd_data,
    output wire [31:0] dut_acc_rd_data,
    output wire [31:0] ref_res_rd_data,
    output wire [31:0] ref_acc_rd_data,
    output wire [31:0] adder_stages,
    output wire [31:0] lanes,
    output wire [31:0] region_words
);
    localparam [31:0]  UNWRITTEN    = 32'hdead_beef;
    localparam integer RESULT_WORDS = LANES * REGION_WORDS;

    reg [63:0]         m0_mem  [0:OPERAND_WORDS-1];
    reg [31:0]         m2_mem  [0:SCALE_WORDS-1];
    reg [16*LANES-1:0] w_mem   [0:STREAM_WORDS-1];
    reg [8*LANES-1:0]  ws_mem  [0:SCALE_WORDS-1];
    reg [63:0]         m1_mem  [0:STREAM_WORDS-1];
    reg [31:0]         m3_mem  [0:SCALE_WORDS-1];
    reg [31:0] dut_res_mem [0:RESULT_WORDS-1];
    reg [31:0] dut_acc_mem [0:RESULT_WORDS-1];
    reg [31:0] ref_res_mem [0:RESULT_WORDS-1];
    reg [31:0] ref_acc_mem [0:RESULT_WORDS-1];
    reg [31:0] case_mem   [0:CASE_WORDS-1];
    reg [31:0] expect_mem [0:EXPECT_WORDS-1];
    reg [31:0] meta_mem   [0:META_WORDS-1];

    assign adder_stages = ADDER_STAGES;
    assign lanes = LANES;
    assign region_words = REGION_WORDS;

    integer clear_index;
    initial begin
        $readmemh("lq8_m0.hex", m0_mem);
        $readmemh("lq8_m2.hex", m2_mem);
        $readmemh("lq8_w.hex", w_mem);
        $readmemh("lq8_ws.hex", ws_mem);
        $readmemh("lq8_m1.hex", m1_mem);
        $readmemh("lq8_m3.hex", m3_mem);
        $readmemh("lq8_case.hex", case_mem);
        $readmemh("lq8_expect.hex", expect_mem);
        $readmemh("lq8_meta.hex", meta_mem);
        for (clear_index = 0; clear_index < RESULT_WORDS; clear_index = clear_index + 1) begin
            dut_res_mem[clear_index] = UNWRITTEN;
            dut_acc_mem[clear_index] = UNWRITTEN;
            ref_res_mem[clear_index] = UNWRITTEN;
            ref_acc_mem[clear_index] = UNWRITTEN;
        end
    end

    // -- block ports ----------------------------------------------------------------
    wire        d_a_en, d_s_en, d_w_en, d_ws_en;
    wire [31:0] d_a_addr, d_s_addr, d_w_addr, d_ws_addr;
    reg  [63:0] d_a_data;
    reg  [31:0] d_s_data;
    reg  [16*LANES-1:0] d_w_data;
    reg  [8*LANES-1:0]  d_ws_data;
    wire [LANES-1:0]    d_out_we;
    wire [32*LANES-1:0] d_out_addr, d_out_data, d_out_acc;
    wire [LANES-1:0]    lane_busy, lane_done, op_retire;
    wire [8*LANES-1:0]  lane_error_code, lane_error_detail;

    // -- reference lane ports ---------------------------------------------------------
    wire        r_a_en, r_b_en, r_s_en, r_t_en;
    wire [31:0] r_a_addr, r_b_addr, r_s_addr, r_t_addr;
    reg  [63:0] r_a_data, r_b_data;
    reg  [31:0] r_s_data, r_t_data;
    wire        r_out_we;
    wire [31:0] r_out_addr, r_out_data, r_out_acc;

    // -- one cycle of read latency on every port -----------------------------------------
    always @(posedge clk) begin
        if (d_a_en  && (d_a_addr  < OPERAND_WORDS)) d_a_data  <= m0_mem[d_a_addr];
        if (d_s_en  && (d_s_addr  < SCALE_WORDS))   d_s_data  <= m2_mem[d_s_addr];
        if (d_w_en  && (d_w_addr  < STREAM_WORDS))  d_w_data  <= w_mem[d_w_addr];
        if (d_ws_en && (d_ws_addr < SCALE_WORDS))   d_ws_data <= ws_mem[d_ws_addr];
        if (r_a_en && (r_a_addr < OPERAND_WORDS)) r_a_data <= m0_mem[r_a_addr];
        if (r_b_en && (r_b_addr < STREAM_WORDS))  r_b_data <= m1_mem[r_b_addr];
        if (r_s_en && (r_s_addr < SCALE_WORDS))   r_s_data <= m2_mem[r_s_addr];
        if (r_t_en && (r_t_addr < SCALE_WORDS))   r_t_data <= m3_mem[r_t_addr];
    end

    // -- result memories, one region per lane -------------------------------------------
    integer wi;
    always @(posedge clk) begin
        for (wi = 0; wi < LANES; wi = wi + 1) begin
            if (d_out_we[wi] && (d_out_addr[32*wi +: 32] < REGION_WORDS)) begin
                dut_res_mem[wi * REGION_WORDS + d_out_addr[32*wi +: 32]] <= d_out_data[32*wi +: 32];
                dut_acc_mem[wi * REGION_WORDS + d_out_addr[32*wi +: 32]] <= d_out_acc[32*wi +: 32];
            end
        end
        if (r_out_we && (r_out_addr < REGION_WORDS) && (ref_lane < LANES)) begin
            ref_res_mem[ref_lane * REGION_WORDS + r_out_addr] <= r_out_data;
            ref_acc_mem[ref_lane * REGION_WORDS + r_out_addr] <= r_out_acc;
        end
    end

    assign case_rd_data   = (case_rd_addr < CASE_WORDS) ? case_mem[case_rd_addr] : 32'b0;
    assign expect_rd_data = (expect_rd_addr < EXPECT_WORDS) ? expect_mem[expect_rd_addr] : 32'b0;
    assign meta_rd_data   = (meta_rd_addr < META_WORDS) ? meta_mem[meta_rd_addr] : 32'b0;
    assign dut_res_rd_data = (res_rd_addr < RESULT_WORDS) ? dut_res_mem[res_rd_addr] : 32'b0;
    assign dut_acc_rd_data = (res_rd_addr < RESULT_WORDS) ? dut_acc_mem[res_rd_addr] : 32'b0;
    assign ref_res_rd_data = (res_rd_addr < RESULT_WORDS) ? ref_res_mem[res_rd_addr] : 32'b0;
    assign ref_acc_rd_data = (res_rd_addr < RESULT_WORDS) ? ref_acc_mem[res_rd_addr] : 32'b0;

    // -- the block ----------------------------------------------------------------------
    ot_a3_lq8 #(
        .LANES(LANES),
        .ADDER_STAGES(ADDER_STAGES),
        .ACC_SLOTS(ACC_SLOTS)
    ) u_dut (
        .clk(clk), .rst_n(rst_n),
        .start(start_dut),
        .cfg_rows(cfg_rows), .cfg_cols(cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
        .cfg_a_base(cfg_a_base), .cfg_scale_a(cfg_scale_a),
        .cfg_block_a(cfg_block_a), .cfg_block_rows_a(cfg_block_rows_a),
        .cfg_scale_a_base(cfg_scale_a_base),
        .cfg_w_base(cfg_w_base), .cfg_scale_b(cfg_scale_b), .cfg_block_b(cfg_block_b),
        .cfg_ws_base(cfg_ws_base), .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
        .a_rd_en(d_a_en), .a_rd_addr(d_a_addr), .a_rd_data(d_a_data),
        .s_rd_en(d_s_en), .s_rd_addr(d_s_addr), .s_rd_data(d_s_data),
        .w_rd_en(d_w_en), .w_rd_addr(d_w_addr), .w_rd_data(d_w_data),
        .ws_rd_en(d_ws_en), .ws_rd_addr(d_ws_addr), .ws_rd_data(d_ws_data),
        .out_we(d_out_we), .out_addr(d_out_addr), .out_data(d_out_data), .out_acc(d_out_acc),
        .busy(dut_busy), .done(dut_done),
        .error_code(dut_error_code), .error_detail(dut_error_detail), .error_lane(dut_error_lane),
        .lane_error_code(lane_error_code), .lane_error_detail(lane_error_detail),
        .lane_busy(lane_busy), .lane_done(lane_done), .op_retire(op_retire),
        .retire_count(dut_retire_count),
        .out_count(dut_out_count), .saturation_count(dut_saturation_count),
        .mac_count(dut_mac_count), .product_count(dut_product_count)
    );

    // -- the qualified single lane, run once per block lane by the checkers -------------
    ot_a3_lane_pipelined #(
        .ADDER_STAGES(ADDER_STAGES),
        .ACC_SLOTS(ACC_SLOTS)
    ) u_ref (
        .clk(clk), .rst_n(rst_n),
        .start(start_ref),
        .cfg_rows(cfg_rows), .cfg_cols(ref_cfg_cols), .cfg_depth(cfg_depth),
        .cfg_dtype_a(cfg_dtype_a), .cfg_dtype_b(cfg_dtype_b), .cfg_group(cfg_group),
        .cfg_a_base(cfg_a_base), .cfg_b_base(ref_cfg_b_base),
        .cfg_scale_a(cfg_scale_a), .cfg_scale_b(cfg_scale_b),
        .cfg_block_a(cfg_block_a), .cfg_block_b(cfg_block_b),
        .cfg_block_rows_a(cfg_block_rows_a), .cfg_block_rows_b(16'd0),
        .cfg_scale_a_base(cfg_scale_a_base), .cfg_scale_b_base(ref_cfg_scale_b_base),
        .cfg_out_base(cfg_out_base), .cfg_out_fp32(cfg_out_fp32),
        .a_rd_en(r_a_en), .a_rd_addr(r_a_addr), .a_rd_data(r_a_data),
        .b_rd_en(r_b_en), .b_rd_addr(r_b_addr), .b_rd_data(r_b_data),
        .s_rd_en(r_s_en), .s_rd_addr(r_s_addr), .s_rd_data(r_s_data),
        .t_rd_en(r_t_en), .t_rd_addr(r_t_addr), .t_rd_data(r_t_data),
        .out_we(r_out_we), .out_addr(r_out_addr), .out_data(r_out_data), .out_acc(r_out_acc),
        .busy(ref_busy), .done(ref_done),
        .error_code(ref_error_code), .error_detail(ref_error_detail),
        .out_count(ref_out_count), .saturation_count(ref_saturation_count),
        .mac_count(ref_mac_count), .product_count(ref_product_count),
        .op_retire()
    );

    // -- per-lane status, through the hierarchy (test-only visibility) -----------------
    wire [LANES-1:0]    mon_a_en, mon_b_en, mon_s_en, mon_t_en;
    wire [32*LANES-1:0] mon_a_addr, mon_s_addr, mon_t_addr;
    wire [32*LANES-1:0] mon_out_count, mon_sat_count, mon_mac_count, mon_product_count;
    genvar gi;
    generate
        for (gi = 0; gi < LANES; gi = gi + 1) begin : gen_mon
            assign mon_a_en[gi] = u_dut.gen_lane[gi].u_lane.a_rd_en;
            assign mon_b_en[gi] = u_dut.gen_lane[gi].u_lane.b_rd_en;
            assign mon_s_en[gi] = u_dut.gen_lane[gi].u_lane.s_rd_en;
            assign mon_t_en[gi] = u_dut.gen_lane[gi].u_lane.t_rd_en;
            assign mon_a_addr[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.a_rd_addr;
            assign mon_s_addr[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.s_rd_addr;
            assign mon_t_addr[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.t_rd_addr;
            assign mon_out_count[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.out_count;
            assign mon_sat_count[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.saturation_count;
            assign mon_mac_count[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.mac_count;
            assign mon_product_count[32*gi +: 32] = u_dut.gen_lane[gi].u_lane.product_count;
        end
    endgenerate

    always @* begin
        lane_rd_error_code = 32'b0;
        lane_rd_error_detail = 32'b0;
        lane_rd_out_count = 32'b0;
        lane_rd_saturation_count = 32'b0;
        lane_rd_mac_count = 32'b0;
        lane_rd_product_count = 32'b0;
        if (lane_rd_sel < LANES) begin
            lane_rd_error_code = {24'b0, lane_error_code[8*lane_rd_sel +: 8]};
            lane_rd_error_detail = {24'b0, lane_error_detail[8*lane_rd_sel +: 8]};
            lane_rd_out_count = mon_out_count[32*lane_rd_sel +: 32];
            lane_rd_saturation_count = mon_sat_count[32*lane_rd_sel +: 32];
            lane_rd_mac_count = mon_mac_count[32*lane_rd_sel +: 32];
            lane_rd_product_count = mon_product_count[32*lane_rd_sel +: 32];
        end
    end

    // -- lockstep monitor ------------------------------------------------------------------
    reg violation_now;
    integer mi;
    always @* begin
        violation_now = 1'b0;
        for (mi = 0; mi < LANES; mi = mi + 1) begin
            if (mon_a_en[mi]) begin
                if (!d_a_en) violation_now = 1'b1;
                if (mon_a_addr[32*mi +: 32] != d_a_addr) violation_now = 1'b1;
                if (mon_s_addr[32*mi +: 32] != d_s_addr) violation_now = 1'b1;
                if (mon_t_addr[32*mi +: 32] != u_dut.sel_t_addr) violation_now = 1'b1;
            end
            if ((mon_b_en[mi] != mon_a_en[mi]) || (mon_s_en[mi] != mon_a_en[mi]) ||
                (mon_t_en[mi] != mon_a_en[mi]))
                violation_now = 1'b1;
        end
        // A request from any lane must be forwarded; none may be invented.
        if (d_a_en != (|mon_a_en)) violation_now = 1'b1;
        if (d_w_en != (|mon_b_en)) violation_now = 1'b1;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            lockstep_violations <= 32'b0;
        else if (violation_now)
            lockstep_violations <= lockstep_violations + 32'd1;
    end
endmodule
