`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// GEMM compute unit: one weight column, NCOL activation columns.
//
// WHY. ot_compute_unit is a GEMV engine. It reads one weight column per cycle,
// broadcasts ONE activation across LANES lanes, and never reads that weight
// again -- a weight reuse factor of exactly 1, two bytes of weight traffic for
// every multiply. Two measurements say that is where the design loses:
//
//   * tools/audit_energy_attribution.py, from routed records: of a compute
//     unit's 0.06508 W, the sixteen lanes account for 0.01625 W (25 %) and
//     operand delivery plus the sequencer for 0.04883 W (75 %). The arithmetic
//     is 3.6x more efficient than the A100 comparator while the whole unit is
//     0.81x, so the deficit is data movement.
//   * tools/audit_kernel_refill_regimes.py: "in a GEMM with batch B, one weight
//     column feeds B activation columns, so the refill cost per column falls by
//     B". That divisor has only ever existed in the analysis. tb_kernel_rom_vs_hbm
//     measures what the hardware actually does with B = 1: at refill period 8,
//     219 of 266 cycles are stalls.
//
// So the fix is not a better multiplier, it is reuse: hold the weight column and
// walk NCOL activation columns against it. That is what a tensor core does, and
// it is the M x N x K tile every GEMM library is written around.
//
// STRUCTURE. NCOL instances of the already-qualified ot_mac_tile share one weight
// bus; tile n carries activation column n. Per cycle the unit reads
//
//     one weight word   16*LANES bits   -- unchanged from ot_compute_unit
//     one activation     16*NCOL bits   -- was 16 bits
//
// and retires LANES*NCOL multiply-accumulates instead of LANES. The weight store,
// the address sequencer and the column counter are unchanged and are now amortised
// over NCOL times the arithmetic; the weight bandwidth per multiply falls by NCOL.
//
// WHAT IT COSTS, and why the activation store is an SRAM here. NCOL columns of
// K_MAX activations is NCOL*K_MAX*16 bits. As the register file ot_compute_unit
// uses that is NCOL*4096 flops at K_MAX=256 -- 32,768 flops at NCOL=8, which the
// routed record prices at about 0.34 um2 per sequential cell, so roughly
// 11,000 um2, more than the sixteen lanes cost. The same capacity in one
// fakeram_256x128 is 1,375.9 um2 by the macro's own LEF -- 23.8 bits per um2
// against the register file's 2.97, eight times the bits for the same area. An
// SRAM read has the same one-cycle latency the weight store already has, so the
// sequencer does not change. That is the whole reason the activation path moves to
// a macro.
//
// OPERAND FAN-OUT IS REGISTERED, per the lesson in ot_mac_tile's header: an
// unbuffered operand driving many loads is a fanout collapse, not a logic-depth
// problem, and the baseline unit closes 0.8 ns with 0.0246 ns of slack -- there is
// no room to add NCOL loads to a weight bit combinationally. Each tile gets its own
// registered replica of the weight word; the activation slice is registered in the
// same stage to keep the pair aligned, and the valid that gates accumulation is
// delayed by the same one cycle.
//
// YOSYS MERGES THOSE REPLICAS, and that is the better outcome. The replicas are
// identical registers with identical inputs, so opt_merge collapses them to one and
// the routed netlist carries a single copy whose output ORFS buffers. Measured, in
// synthesised cell area at 0.85 ns:
//
//     ot_mac_tile LANES=16 alone   3,440.015 um2   1,570 sequential cells
//     ot_probe_gemm_unit_n2        6,974.098       3,160
//     ot_probe_gemm_unit_n4       13,701.145       6,110
//     ot_probe_gemm_unit_n8       27,138.335      12,000
//
// Eight tiles alone are 27,520.12 um2 and 12,560 sequential cells, so the whole
// unit is SMALLER than its tiles: the NCOL*(16*LANES + 16) replica flops never
// appear. In the routed netlists the fixed sequential cost of this unit's operand
// delivery is 555 cells at every NCOL (8,589, 16,623 and 32,691 total at NCOL 2, 4
// and 8, which is 4,017 per tile plus 555). The GEMV unit's 8,410 sequential cells
// include its 4,096-flop activation register file: 49 % of that unit's flip-flops
// are the operand store this one keeps in a macro. Every routed record here reports zero
// max-fanout and zero max-cap violations, so the buffering ORFS substitutes for the
// replicas is doing the job the replicas were written to do.
//
// BIT-EXACTNESS. Each tile is ot_mac_tile with no parameter override, fed the same
// operand pairs the GEMV unit would feed it for that activation column, so column
// n lane l must equal runtime.reference.mac_tile.dot_product(act[n], wgt[l]) --
// the same independent authority, not a comparison against this file's sibling.
// rtl/test/tb_compute_unit_gemm.sv checks all LANES*NCOL of them.
// ---------------------------------------------------------------------------
module ot_compute_unit_gemm #(
    parameter integer LANES = 16,
    parameter integer ACC_W = 40,
    parameter integer K_MAX = 256,          // weight/activation columns the stores hold
    parameter integer NCOL  = 8             // activation columns per weight column
) (
    input  wire                        clk,
    input  wire                        rst_n,

    // ---- control ----
    input  wire                        start,
    input  wire [$clog2(K_MAX+1)-1:0]  cfg_k,        // columns to walk, 1..K_MAX
    input  wire [7:0]                  cfg_scale,    // shared window exponent
    output reg                         busy,
    output reg                         done,

    // ---- weight store write port ----
    input  wire                        wr_en,
    input  wire [$clog2(K_MAX)-1:0]    wr_addr,
    input  wire [16*LANES-1:0]         wr_data,

    // ---- activation store write port: NCOL columns at one K index ----
    input  wire                        act_we,
    input  wire [$clog2(K_MAX)-1:0]    act_waddr,
    input  wire [16*NCOL-1:0]          act_wdata,

    // ---- weight refill backpressure (the ROM-versus-HBM knob) ----
    input  wire                        refill_valid,
    output wire                        refill_ready,
    output wire                        stalled,

    // ---- result read-out: one lane index, all NCOL columns ----
    input  wire [$clog2(LANES)-1:0]    res_sel,
    output wire [ACC_W*NCOL-1:0]       res_data,
    output wire [LANES*NCOL-1:0]       dropped_mask
);
    localparam integer WGT_BITS   = 16 * LANES;
    localparam integer ACT_BITS   = 16 * NCOL;
    localparam integer AW         = $clog2(K_MAX);
    localparam integer KW         = $clog2(K_MAX + 1);
    localparam integer WGT_MACROS = WGT_BITS / 128;

    //: Every width above is derived from LANES, NCOL, ACC_W and K_MAX. The two
    //: shapes the FakeRAM parts cannot express fail to elaborate rather than
    //: silently dropping bits: the weight word must be a whole number of 128-bit
    //: macros, and the activation word must be one of the widths the library
    //: ships (32, 64 or 128 bits).
    localparam integer WGT_OK = (WGT_BITS % 128 == 0) ? 1 : 0;
    localparam integer ACT_OK = (ACT_BITS == 32 || ACT_BITS == 64
                                 || ACT_BITS == 128) ? 1 : 0;
    localparam integer DEPTH_OK = (K_MAX == 256) ? 1 : 0;
    wire [WGT_OK-1:0]   weight_word_is_whole_macros;
    wire [ACT_OK-1:0]   activation_word_is_a_library_width;
    wire [DEPTH_OK-1:0] store_depth_matches_the_macro;

    // ---- weight store: WGT_MACROS x fakeram_256x128 ganged in width ---------
    wire [AW-1:0]        ram_addr;
    wire                 ram_ce, ram_we;
    wire [WGT_BITS-1:0]  wgt_word;

    reg  [AW-1:0] rd_addr;
    assign ram_addr = wr_en ? wr_addr : rd_addr;
    assign ram_ce   = wr_en | busy;
    assign ram_we   = wr_en;

    genvar gm;
    generate
        for (gm = 0; gm < WGT_MACROS; gm = gm + 1) begin : wgt_macro
            wire [127:0] rd;
            fakeram_256x128 u (
                .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
                .wd_in(wr_data[128*gm +: 128]), .rd_out(rd)
            );
            assign wgt_word[128*gm +: 128] = rd;
        end
    endgenerate

    // ---- activation store: one macro, ACT_BITS wide -------------------------
    wire [AW-1:0] act_addr;
    wire          act_ce;
    reg  [AW-1:0] act_raddr;
    wire [ACT_BITS-1:0] act_word;

    assign act_addr = act_we ? act_waddr : act_raddr;
    assign act_ce   = act_we | busy;

    generate
        if (ACT_BITS == 128) begin : act_128
            fakeram_256x128 u (
                .clk(clk), .addr_in(act_addr), .ce_in(act_ce), .we_in(act_we),
                .wd_in(act_wdata), .rd_out(act_word)
            );
        end else if (ACT_BITS == 64) begin : act_64
            fakeram_256x64 u (
                .clk(clk), .addr_in(act_addr), .ce_in(act_ce), .we_in(act_we),
                .wd_in(act_wdata), .rd_out(act_word)
            );
        end else begin : act_32
            fakeram7_256x32 u (
                .clk(clk), .addr_in(act_addr), .ce_in(act_ce), .we_in(act_we),
                .wd_in(act_wdata), .rd_out(act_word)
            );
        end
    endgenerate

    // ---- sequencer ----------------------------------------------------------
    //: Identical to ot_compute_unit's, with ONE more valid delay for the operand
    //: fan-out stage below. Both stores have the same one-cycle read latency, so
    //: the address issue leads the valid pair by two cycles as before, and the
    //: registered fan-out makes it three.
    localparam [1:0] S_IDLE = 2'd0, S_WALK = 2'd1, S_DRAIN = 2'd2;
    reg [1:0]    state;
    reg [KW-1:0] col;
    reg          tile_clear, tile_clear_d, tile_valid, tile_valid_d, tile_valid_d2;
    reg [3:0]    drain;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            tile_valid_d <= 1'b0; tile_valid_d2 <= 1'b0; tile_clear_d <= 1'b0;
        end else begin
            tile_valid_d  <= tile_valid;
            tile_valid_d2 <= tile_valid_d;
            tile_clear_d  <= tile_clear;
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            state <= S_IDLE; col <= {KW{1'b0}};
            rd_addr <= {AW{1'b0}}; act_raddr <= {AW{1'b0}};
            busy <= 1'b0; done <= 1'b0; tile_clear <= 1'b0; tile_valid <= 1'b0;
            drain <= 4'b0;
        end else begin
            done       <= 1'b0;
            tile_clear <= 1'b0;
            case (state)
                S_IDLE:
                    if (start) begin
                        busy <= 1'b1; tile_clear <= 1'b1;
                        col <= {KW{1'b0}};
                        rd_addr <= {AW{1'b0}}; act_raddr <= {AW{1'b0}};
                        tile_valid <= 1'b0;
                        state <= S_WALK;
                    end

                S_WALK: begin
                    tile_valid <= (col < cfg_k) && refill_valid;
                    if (col < cfg_k) begin
                        if (refill_valid) begin
                            rd_addr   <= col[AW-1:0];
                            act_raddr <= col[AW-1:0];
                            col       <= col + {{(KW-1){1'b0}}, 1'b1};
                        end
                    end else begin
                        //: One deeper than ot_compute_unit's 12 for the extra
                        //: fan-out register, so the last column is still
                        //: accumulated and resolved before done.
                        drain <= 4'd13;
                        state <= S_DRAIN;
                    end
                end

                S_DRAIN: begin
                    tile_valid <= 1'b0;
                    if (drain == 4'b0) begin
                        busy <= 1'b0; done <= 1'b1; state <= S_IDLE;
                    end else
                        drain <= drain - 4'd1;
                end

                default: state <= S_IDLE;
            endcase
        end

    // ---- operand fan-out stage: one registered replica per tile -------------
    //: The weight word is shared by every tile, which is the whole point of the
    //: unit, and is therefore the one net that would see NCOL loads. Replicating
    //: it into a per-tile register bounds fanout per driver to a single tile --
    //: the same load ot_compute_unit's weight bit drives -- at a cost of
    //: NCOL*(16*LANES + 16) flops, 2,176 at LANES=16, NCOL=8.
    wire [ACC_W*LANES-1:0] tile_result [0:NCOL-1];
    wire [ACC_W*NCOL-1:0]  res_mux;
    reg  [ACC_W*NCOL-1:0]  res_data_q;

    genvar n;
    generate
        for (n = 0; n < NCOL; n = n + 1) begin : col_tile
            //: (* keep *) is load-bearing, and it is here because the routed
            //: netlist said so rather than on principle.  Without it Yosys merges
            //: these identical registers -- and, through the shared scale, the
            //: b_scale registers INSIDE the tiles as well -- so one flop drives
            //: loads across the whole block.  At NCOL=8 the block is 113,833 um2,
            //: about 337 um on a side, and the 6_finish report named exactly that:
            //:
            //:   u.col_tile[2].u_tile.b_scale[0][6] -> u.col_tile[7].u_tile.lane[14].s2_term[26]
            //:       slack -5.33 ps at a 1.05 ns target
            //:
            //: a register in tile 2 feeding logic in tile 7, which can only happen
            //: because the two tiles' copies were collapsed into one.  Keeping the
            //: replicas costs NCOL*(16*LANES + 24) flops and keeps every operand
            //: driver inside the tile it feeds, which is what the registered
            //: broadcast in ot_mac_tile's header is for.
            (* keep *) reg [WGT_BITS-1:0] wgt_r;
            (* keep *) reg [15:0]         act_r;
            (* keep *) reg [7:0]          scl_r;

            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin
                    wgt_r <= {WGT_BITS{1'b0}}; act_r <= 16'b0; scl_r <= 8'b0;
                end else begin
                    wgt_r <= wgt_word;
                    act_r <= act_word[16*n +: 16];
                    //: registered in the SAME stage as the operand pair, so the
                    //: window exponent reaches each tile's broadcast register on
                    //: the cycle its operands do, whatever the caller does to
                    //: cfg_scale.
                    scl_r <= cfg_scale;
                end

            ot_mac_tile #(.LANES(LANES), .ACC_W(ACC_W)) u_tile (
                .clk(clk), .rst_n(rst_n),
                .clear(tile_clear_d), .valid_in(tile_valid_d2),
                .act(act_r), .wgt(wgt_r), .scale_exp(scl_r),
                .result(tile_result[n]),
                .dropped_mask(dropped_mask[LANES*n +: LANES]),
                .result_valid()
            );

            assign res_mux[ACC_W*n +: ACC_W] =
                tile_result[n][ACC_W*res_sel +: ACC_W];
        end
    endgenerate

    //: THE DRAIN IS REGISTERED, and this too came from the routed report.  The
    //: read-out is a LANES-way mux over NCOL*LANES accumulators from an input port
    //: to an output port, all combinational, and at NCOL=8 it was the worst path in
    //: the design:
    //:
    //:   res_sel[3] (input port) -> res_data[218] (output port)
    //:       slack -5.59 ps at a 1.05 ns target
    //:
    //: It is also the one path where latency is free: the drain runs once per pass,
    //: after done, not once per column, so a cycle of read latency costs nothing
    //: the throughput can feel.  res_data is therefore valid the cycle AFTER
    //: res_sel is presented.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) res_data_q <= {(ACC_W*NCOL){1'b0}};
        else        res_data_q <= res_mux;

    assign res_data = res_data_q;

    assign refill_ready = (state == S_WALK) && (col < cfg_k);
    assign stalled      = refill_ready && !refill_valid;
endmodule
