`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Compute unit: SRAM-backed operand delivery plus a 16-lane MAC tile.
//
// The MAC tile on its own is not a design. Its 2.912 TFLOP/s per mm² is an upper
// bound precisely because it has no operand storage -- a number that only counts
// multipliers flatters itself by every byte of memory it does not have. This unit
// adds the operand delivery a real compute unit needs, so the density figure
// becomes a design figure.
//
// Structure, following the standard weight-stationary GEMM compute unit:
//
//   weight SRAM   two fakeram_256x128 ganged to 256 words x 256 bits, which
//                 holds one 16-lane x 16-bit weight column per word and so K=256
//                 columns of a weight tile. Single-port synchronous, one cycle of
//                 read latency, per the FakeRAM liberty this flow ships.
//   activation    a small register file, read one word per cycle and broadcast
//                 to every lane -- the reuse that makes an array worth building.
//   MAC tile      ot_mac_tile, already qualified bit-exact against
//                 runtime.reference.mac_tile.
//   drain         accumulators are read out over the result bus after the tile
//                 signals valid.
//
// The sequencer walks K columns: issue a weight address, wait the SRAM's read
// latency, present the column with its activation, repeat. That is the memory
// access pattern the performance model must charge for, and it is visible here
// rather than assumed: one SRAM read per column, one activation read per column,
// no operand re-fetch.
//
// NOT a full SM. There is no scheduler, no multi-warp issue, no DMA engine and no
// interconnect. It is the compute unit those would feed, and it is the level at
// which an area/throughput figure stops being a multiplier count.
// ---------------------------------------------------------------------------
module ot_compute_unit #(
    parameter integer LANES = 16,
    parameter integer ACC_W = 40,
    parameter integer K_MAX = 256          // weight columns the SRAM holds
) (
    input  wire                   clk,
    input  wire                   rst_n,

    // ---- control ----
    input  wire                   start,       // begin a K-column pass
    input  wire [8:0]             cfg_k,       // columns to walk, 1..K_MAX
    input  wire [7:0]             cfg_scale,   // shared window exponent
    output reg                    busy,
    output reg                    done,

    // ---- weight SRAM write port (host/DMA fill) ----
    input  wire                   wr_en,
    input  wire [7:0]             wr_addr,
    input  wire [16*LANES-1:0]    wr_data,

    // ---- activation register file write port ----
    input  wire                   act_we,
    input  wire [8:0]             act_waddr,
    input  wire [15:0]            act_wdata,

    // ---- result read-out ----
    input  wire [4:0]             res_sel,
    output wire [ACC_W-1:0]       res_data,
    output wire [LANES-1:0]       dropped_mask
);
    localparam integer WGT_BITS = 16 * LANES;          // 256 for LANES=16

    // ---- weight SRAM: two fakeram_256x128 ganged in width -----------------
    wire [7:0]   ram_addr;
    wire         ram_ce, ram_we;
    wire [127:0] rd_lo, rd_hi;
    wire [WGT_BITS-1:0] wgt_word = {rd_hi, rd_lo};

    reg  [7:0]   rd_addr;
    assign ram_addr = wr_en ? wr_addr : rd_addr;
    assign ram_ce   = wr_en | busy;
    assign ram_we   = wr_en;

    fakeram_256x128 u_wgt_lo (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(wr_data[127:0]),   .rd_out(rd_lo)
    );
    fakeram_256x128 u_wgt_hi (
        .clk(clk), .addr_in(ram_addr), .ce_in(ram_ce), .we_in(ram_we),
        .wd_in(wr_data[WGT_BITS-1:128]), .rd_out(rd_hi)
    );

    // ---- activation register file -----------------------------------------
    // Small and read once per column, so registers are the right structure here:
    // an SRAM's read latency would have to be hidden for no density gain.
    reg [15:0] act_rf [0:K_MAX-1];
    reg [8:0]  act_raddr;
    reg [15:0] act_q;

    always @(posedge clk)
        if (act_we) act_rf[act_waddr] <= act_wdata;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) act_q <= 16'b0;
        else        act_q <= act_rf[act_raddr];

    // ---- sequencer --------------------------------------------------------
    // One column per cycle once the SRAM pipeline is primed. The tile consumes
    // (activation, weight column) pairs; both arrive one cycle after their
    // address, so the valid that gates accumulation follows by the same amount.
    localparam [1:0] S_IDLE = 2'd0, S_WALK = 2'd1, S_DRAIN = 2'd2;
    reg [1:0] state;
    reg [8:0] col;
    reg       tile_clear, tile_valid, tile_valid_d;
    reg [3:0] drain;

    //: TWO cycles, not one.  The address is presented to the SRAM during the
    //: cycle after it is registered, rd_out updates at the END of that cycle, so
    //: the operand pair is only valid on the SECOND cycle after the issue.
    //: Asserting valid one cycle early made the tile latch the PREVIOUS column's
    //: operands against this column's valid, and every lane came out wrong.
    always @(posedge clk or negedge rst_n)
        if (!rst_n) tile_valid_d <= 1'b0;
        else        tile_valid_d <= tile_valid;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            state <= S_IDLE; col <= 9'b0; rd_addr <= 8'b0; act_raddr <= 9'b0;
            busy <= 1'b0; done <= 1'b0; tile_clear <= 1'b0; tile_valid <= 1'b0;
            drain <= 4'b0;
        end else begin
            done       <= 1'b0;
            tile_clear <= 1'b0;
            case (state)
                S_IDLE:
                    if (start) begin
                        busy <= 1'b1; tile_clear <= 1'b1;
                        col <= 9'b0; rd_addr <= 8'b0; act_raddr <= 9'b0;
                        tile_valid <= 1'b0;
                        state <= S_WALK;
                    end

                S_WALK: begin
                    //: valid must follow the ADDRESS ISSUE by exactly one cycle,
                    //: because that is the SRAM's read latency and the register
                    //: file's.  Deriving it from `col != 0` instead dropped the
                    //: LAST column: the final pair becomes valid on the same
                    //: cycle col reaches cfg_k, which is where the old code
                    //: deasserted valid.  31 of 32 columns accumulated and every
                    //: lane came out wrong -- caught by tb_compute_unit.
                    tile_valid <= (col < cfg_k);
                    if (col < cfg_k) begin
                        rd_addr   <= col[7:0];
                        act_raddr <= col;
                        col       <= col + 9'd1;
                    end else begin
                        drain <= 4'd12;       // tile pipeline depth plus margin
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

    // ---- the qualified MAC tile -------------------------------------------
    wire [ACC_W*LANES-1:0] tile_result;

    ot_mac_tile #(.LANES(LANES), .ACC_W(ACC_W)) u_tile (
        .clk(clk), .rst_n(rst_n),
        .clear(tile_clear), .valid_in(tile_valid_d),
        .act(act_q), .wgt(wgt_word), .scale_exp(cfg_scale),
        .result(tile_result), .dropped_mask(dropped_mask),
        .result_valid()
    );

    assign res_data = tile_result[ACC_W*res_sel +: ACC_W];
endmodule
