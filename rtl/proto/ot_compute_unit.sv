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
//   weight SRAM   WGT_BANKS x (two fakeram_256x128 ganged to 256 words x 256
//                 bits), which holds one 16-lane x 16-bit weight column per word
//                 and so K=256 columns of a weight tile per bank. Single-port
//                 synchronous, one cycle of read latency, per the FakeRAM liberty
//                 this flow ships.
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
//
// OPERAND DELIVERY: WHY THERE ARE TWO FLOW-CONTROL MODES HERE
// ===========================================================
// results/derived/sustained_array_iso_area_audit.json puts the array at 2.059x
// the A100's standard-cell-logic density at REFILL SKEW 0 -- every unit fed every
// cycle -- and at 1.124x / 1.006x at SKEW 2, one unit in sixteen at a 50 % refill
// duty. Its verdict names operand delivery as the binding constraint, and the
// same block is 59.6 % of this unit's occupied area and 75 % of its power.
//
// The cause is visible in the OLD flow control, kept here as
// REFILL_DECOUPLED=0 because it is the measurement baseline:
//
//     tile_valid <= (col < cfg_k) && refill_valid;     // per COLUMN CONSUMED
//
// A column could only be consumed on a cycle when refill_valid happened to be
// high, so the refill port was in LOCKSTEP with the MAC tile. Three consequences,
// all measured and none of them a property of the memory:
//
//   1. NO REUSE ACROSS PASSES. A descriptor's passes re-walk the same resident
//      weight columns -- rd_addr restarts at 0 on every start and the tile is
//      never re-written -- yet each pass re-ran the handshake, paying the fetch
//      three times at three passes per descriptor for weights already in the
//      SRAM. A weight-stationary datapath with weight-STREAMING flow control.
//   2. NO OVERLAP. A refill offered while the unit was draining or idle was
//      dropped, because refill_ready was `(state == S_WALK) && (col < cfg_k)`.
//      Nothing could be fetched ahead of the pass that needed it.
//   3. NO RESIDENCY STATE AT ALL, so the unit could not tell an operand it
//      already held from one it did not.
//
// REFILL_DECOUPLED=1 replaces the lockstep with a FILL FRONTIER: refill delivers
// a column into `bank_fill` at index `refill_col`, `fill_cnt` records how many
// columns of the tile have arrived, and the walk stalls only on a column that has
// NOT arrived (`col >= res_rd`). Delivery may run ahead of the walk, continue
// through S_DRAIN and S_IDLE, and is charged ONCE per tile rather than once per
// column consumed. `wgt_reload` -- asserted by the distributor on the FIRST pass
// of a descriptor only -- is what marks a tile as new and therefore payable.
//
// WGT_BANKS IS THE DOUBLE BUFFER, AND IT IS NOT FREE
// --------------------------------------------------
// The FakeRAM parts have ONE port: a write and a read cannot share a cycle. The
// walk therefore runs only on a bank that holds a COMPLETE tile and the fill only
// ever writes a bank that does not, so the two can never want the same port --
// and what WGT_BANKS decides is whether they can proceed at the same time at all.
//
//   WGT_BANKS=1   fetch and compute SERIALISE. The tile is retired at the
//                 descriptor boundary, refetched into the one bank there is while
//                 the walk stalls, and only then walked. One weight SRAM, and the
//                 fetch is exposed in full.
//   WGT_BANKS=2   pass N reads bank_act while the NEXT descriptor's tile lands in
//                 bank_fill; the banks exchange roles at the descriptor boundary.
//                 Delivery costs the walk nothing as long as a tile fetch fits
//                 inside a descriptor's compute time. The price is one extra macro
//                 pair -- 100 % more weight SRAM -- plus the 256-bit read mux.
//
// Letting the walk CHASE the fill frontier inside its own bank was built and
// rejected on measurement, not taste: the walk's read took the port on every
// advance, halving the fill rate on top of the refill duty, and at one pass per
// descriptor that cost 1,015 cycles per descriptor against the lockstep
// baseline's 565. The chase is gone; a stall until the whole tile lands is
// cheaper and it is also what makes the port arbitration disappear.
// ---------------------------------------------------------------------------
module ot_compute_unit #(
    parameter integer LANES = 16,
    parameter integer ACC_W = 40,
    parameter integer K_MAX = 256,         // weight columns one bank holds
    //: 1 reproduces the lockstep handshake the 46/78/142/266 stall table was
    //: measured on, bit for bit.  1 is the fill frontier described in the header.
    parameter integer REFILL_DECOUPLED = 0,
    //: weight banks.  1 is a single buffer: the fill and the walk share one macro
    //: port.  2 is the double buffer, at one extra macro pair.
    parameter integer WGT_BANKS = 1
) (
    input  wire                   clk,
    input  wire                   rst_n,

    // ---- control ----
    input  wire                   start,       // begin a K-column pass
    input  wire [8:0]             cfg_k,       // columns to walk, 1..K_MAX
    input  wire [7:0]             cfg_scale,   // shared window exponent
    //: THE FIRST PASS OF A DESCRIPTOR brings a new weight tile; the later passes
    //: of the same descriptor re-walk the tile already resident.  The distributor
    //: knows which is which -- ot_dispatch_tree derives it from the last-pass flag
    //: already in its payload -- so residency is DERIVED from the descriptor
    //: stream rather than assumed by the unit.  Tie it high to charge a fresh
    //: fetch for every pass, which is what REFILL_DECOUPLED=0 always did.
    input  wire                   wgt_reload,
    output reg                    busy,
    output reg                    done,

    // ---- weight SRAM write port (host/DMA fill) ----
    //: bank 0 only: this is the host's image loader, not the operand-delivery
    //: path.  Under REFILL_DECOUPLED=1 with WGT_BANKS=2 the walk reads a bank the
    //: host never wrote, so a residency or bank-select fault shows up as a WRONG
    //: ACCUMULATOR rather than as a cycle count nobody can check.
    input  wire                   wr_en,
    input  wire [7:0]             wr_addr,
    input  wire [16*LANES-1:0]    wr_data,

    // ---- activation register file write port ----
    input  wire                   act_we,
    input  wire [8:0]             act_waddr,
    input  wire [15:0]            act_wdata,

    //: WEIGHT REFILL -- the one place the two designs differ.
    //:
    //: The compute datapath is IDENTICAL on both sides of this project's
    //: comparison: same MAC tile, same accumulate, same P&R flow.  What differs
    //: is where a weight column comes from when it is not already in the local
    //: buffer:
    //:
    //:   ROM design   an on-die mask ROM read.  No off-chip traffic, so the
    //:                refill is limited by on-die bandwidth only.
    //:   HBM design   an off-chip read.  Limited by HBM bandwidth per byte, so a
    //:                miss stalls the array.
    //:
    //: Modelling that as BACKPRESSURE on one port keeps both sides at equal
    //: fidelity: the same gates, the same timing closure, and the cycle count is
    //: the comparison rather than an assumption fed into a spreadsheet.  A design
    //: that got its weights for free in the RTL and paid for them only in an
    //: analytical model would not be comparable to one that did the opposite.
    //:
    //: Under REFILL_DECOUPLED=1 the port also CARRIES the column: refill_col says
    //: which column of the tile the unit wants next and refill_data is written
    //: into the fill bank on the accepted cycle.  That is what makes the fill
    //: frontier checkable against the reference instead of being a counter.
    input  wire                   refill_valid,   // a weight column is available
    input  wire [16*LANES-1:0]    refill_data,    // ... this one
    output wire [8:0]             refill_col,     // ... and this is the one wanted
    output wire                   refill_ready,   // the unit wants one now
    output wire                   stalled,        // waiting on refill this cycle

    // ---- result read-out ----
    input  wire [4:0]             res_sel,
    output wire [ACC_W-1:0]       res_data,
    output wire [LANES-1:0]       dropped_mask
);
    localparam integer WGT_BITS = 16 * LANES;          // 256 for LANES=16
    localparam integer BANK_W   = (WGT_BANKS > 1) ? $clog2(WGT_BANKS) : 1;
    localparam integer DECOUP   = (REFILL_DECOUPLED != 0) ? 1 : 0;
    localparam [BANK_W-1:0] BANK_ZERO = {BANK_W{1'b0}};
    //: the bank stride.  ZERO when there is only one bank, which is what makes
    //: every "move to the next bank" below a no-op in the single-buffer build
    //: instead of a special case.
    localparam [BANK_W-1:0] BANK_ONE  = (WGT_BANKS > 1) ? 1 : 0;

    // ---- operand-delivery state -------------------------------------------
    //: bank_act  the bank the walk reads.       bank_fill  the bank being filled.
    //: They are EQUAL while the walk chases its own fill (a single buffer always,
    //: a double buffer only until the first tile completes) and DIFFERENT while
    //: the next tile is being prefetched behind the current one.
    reg  [BANK_W-1:0] bank_act, bank_fill;
    reg  [8:0]        fill_cnt;    // columns of the fill bank's tile delivered
    reg  [8:0]        act_cnt;     // columns resident in bank_act
    reg               swap_pend;   // active tile retired, waiting on the fill
    reg               rd_issue;    // a walk read drives the macro port this cycle

    wire [31:0] ba_int = {{(32-BANK_W){1'b0}}, bank_act};
    wire [31:0] bf_int = {{(32-BANK_W){1'b0}}, bank_fill};

    //: A WHOLE TILE, NEVER HALF OF ONE.  The walk runs only on a bank that is
    //: fully resident, and the fill only ever writes a bank that is not.  So a
    //: read and a write can never want the same single-ported macro in the same
    //: cycle -- the arbitration a FakeRAM part would otherwise force is removed by
    //: construction rather than resolved by a priority rule.
    //:
    //: Letting the walk CHASE the frontier inside its own bank was measured and
    //: rejected: the walk's read took the port on every advance, which halved the
    //: fill rate on top of whatever the refill duty already was, and at one pass
    //: per descriptor it cost 1,015 cycles per descriptor against the lockstep
    //: baseline's 565 (16 units, skew 2, tb_dispatch_tree_throughput).
    wire [8:0]  res_rd     = act_cnt;
    wire        fill_full  = (fill_cnt >= cfg_k);

    // ---- sequencer --------------------------------------------------------
    // One column per cycle once the SRAM pipeline is primed. The tile consumes
    // (activation, weight column) pairs; both arrive one cycle after their
    // address, so the valid that gates accumulation follows by the same amount.
    localparam [1:0] S_IDLE = 2'd0, S_WALK = 2'd1, S_DRAIN = 2'd2;
    reg [1:0] state;
    reg [8:0] col;
    reg [7:0] rd_addr;
    reg       tile_clear, tile_valid, tile_valid_d;
    reg [3:0] drain;

    //: a column is BACKED when it has arrived.  Under the old flow control that
    //: question could not be asked, so `refill_valid` on the consuming cycle
    //: stood in for it.
    wire        col_backed = (DECOUP != 0) ? (col < res_rd) : refill_valid;
    wire        walking    = (state == S_WALK) && (col < cfg_k);
    wire        walk_adv   = walking && col_backed;
    wire        promote    = (DECOUP != 0) && (state == S_IDLE) && start && wgt_reload;

    wire        fill_want  = (DECOUP != 0) && !fill_full && !wr_en && !promote;
    assign refill_ready    = (DECOUP != 0) ? fill_want : walking;
    wire        fill_go    = refill_ready && refill_valid && (DECOUP != 0);
    //: the fill completes the tile on this cycle.  If the walk is waiting for it,
    //: that is the cycle the banks exchange roles.
    wire        fill_done  = fill_go && ((fill_cnt + 9'd1) >= cfg_k);
    wire        swap_now   = fill_done && swap_pend;

    assign stalled    = (DECOUP != 0) ? (walking && !col_backed)
                                      : (refill_ready && !refill_valid);
    assign refill_col = fill_cnt;

    wire [BANK_W-1:0] bank_next = bank_fill + BANK_ONE;

    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            //: the fill starts in the bank the host image does NOT occupy, so a
            //: decoupled run proves delivery rather than inheriting a preload.
            bank_act  <= BANK_ZERO;
            bank_fill <= BANK_ONE;
            fill_cnt  <= 9'b0;
            act_cnt   <= 9'b0;
            swap_pend <= 1'b0;
        end else begin
            if (promote) begin
                //: A NEW TILE IS DUE.  The one in the active bank is retired on
                //: this cycle whatever happens, because the descriptor that owned
                //: it has been superseded -- so act_cnt is what charges the fetch.
                if ((WGT_BANKS > 1) && fill_full) begin
                    //: prefetched and complete: the banks exchange roles and the
                    //: fill starts the NEXT tile in the bank just vacated.  This
                    //: is the only path on which delivery costs the walk nothing,
                    //: and it is the reason for the second macro pair.
                    bank_act  <= bank_fill;
                    act_cnt   <= fill_cnt;
                    bank_fill <= bank_next;
                    fill_cnt  <= 9'b0;
                    swap_pend <= 1'b0;
                end else begin
                    //: not there yet.  The walk waits -- res_rd is 0, so every
                    //: column stalls -- while the fill finishes the tile.  With
                    //: one bank this is the ONLY path, which is exactly what a
                    //: single buffer means: fetch and compute serialise.
                    act_cnt   <= 9'b0;
                    swap_pend <= 1'b1;
                    if (WGT_BANKS == 1) fill_cnt <= 9'b0;
                end
            end else if (swap_now) begin
                //: the tile the walk is stalled on has just landed.
                bank_act  <= bank_fill;
                act_cnt   <= cfg_k;
                swap_pend <= 1'b0;
                if (WGT_BANKS > 1) begin
                    bank_fill <= bank_next;
                    fill_cnt  <= 9'b0;
                end else
                    fill_cnt <= fill_cnt + 9'd1;
            end else if (fill_go)
                fill_cnt <= fill_cnt + 9'd1;
        end

    always @(posedge clk or negedge rst_n)
        if (!rst_n) rd_issue <= 1'b0;
        else        rd_issue <= walk_adv;

    // ---- weight SRAM: WGT_BANKS x two fakeram_256x128 ganged in width -------
    wire [WGT_BANKS*128-1:0] rd_lo_bus, rd_hi_bus;

    genvar b;
    generate
        for (b = 0; b < WGT_BANKS; b = b + 1) begin : wbank
            wire is_act    = (ba_int == b);
            wire is_fill   = (bf_int == b);
            wire wr_here   = wr_en && (b == 0);
            wire fill_here = fill_go && is_fill;
            wire rd_here   = rd_issue && is_act && !wr_here && !fill_here;
            wire [7:0] addr_here = wr_here   ? wr_addr
                                 : fill_here ? fill_cnt[7:0]
                                             : rd_addr;
            wire [WGT_BITS-1:0] wd_here = wr_here ? wr_data : refill_data;
            //: THE BANK'S MACRO COMPOSITION FOLLOWS ITS DEPTH, and the depth is
            //: K_MAX -- the columns one bank holds -- so no second parameter
            //: decides it.  Both compositions present the same 256-bit row to
            //: the read mux below, so nothing downstream of here changes.
            //:
            //: 256 is the original: two ``fakeram_256x128`` ganged in width, 2 x
            //: 1404.5 = 2,809 um2 per bank.  A double buffer at that depth
            //: therefore costs 100 % MORE WEIGHT SRAM, which is why it loses to
            //: the single buffer whenever operand supply is good enough that the
            //: second bank is never waited on -- measured as 1.41x the A100's
            //: logic density against the single buffer's 1.95x at refill skew 0.
            //:
            //: 128 is the answer to that: four ``fakeram7_128x64``, 4 x 361.2 =
            //: 1,444.8 um2, so TWO half-depth banks are 2,890 um2 against the one
            //: full-depth bank's 2,809 -- 2.9 % more SRAM for a true ping-pong,
            //: where the full-depth pair pays 100 %.  The tile is half as wide, so
            //: a K=256 kernel becomes two tiles rather than one and the refill is
            //: charged twice; whether that trade wins is a measurement, not an
            //: argument, and it is the one the campaign at this geometry makes.
            if (K_MAX == 256) begin : depth256
                fakeram_256x128 u_lo (
                    .clk(clk), .addr_in(addr_here),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[127:0]), .rd_out(rd_lo_bus[b*128 +: 128])
                );
                fakeram_256x128 u_hi (
                    .clk(clk), .addr_in(addr_here),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[WGT_BITS-1:128]), .rd_out(rd_hi_bus[b*128 +: 128])
                );
            end else if (K_MAX == 128) begin : depth128
                //: 7-bit ports, so the address is truncated rather than widened:
                //: ``cfg_k`` is bounded by K_MAX above, so a column index that
                //: needed bit 7 could not have been issued.
                fakeram7_128x64 u_lo0 (
                    .clk(clk), .addr_in(addr_here[6:0]),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[63:0]), .rd_out(rd_lo_bus[b*128 +: 64])
                );
                fakeram7_128x64 u_lo1 (
                    .clk(clk), .addr_in(addr_here[6:0]),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[127:64]), .rd_out(rd_lo_bus[b*128 + 64 +: 64])
                );
                fakeram7_128x64 u_hi0 (
                    .clk(clk), .addr_in(addr_here[6:0]),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[191:128]), .rd_out(rd_hi_bus[b*128 +: 64])
                );
                fakeram7_128x64 u_hi1 (
                    .clk(clk), .addr_in(addr_here[6:0]),
                    .ce_in(wr_here | fill_here | rd_here),
                    .we_in(wr_here | fill_here),
                    .wd_in(wd_here[WGT_BITS-1:192]),
                    .rd_out(rd_hi_bus[b*128 + 64 +: 64])
                );
            end else begin : depth_unsupported
                //: A depth with no macro composition is refused at elaboration
                //: rather than silently built from the wrong parts.
                $error("ot_compute_unit: K_MAX=%0d has no weight-SRAM macro composition; 128 and 256 are built", K_MAX);
            end
        end
    endgenerate

    //: the read mux.  256 bits wide and one level deep at WGT_BANKS=2, and it
    //: sits between the macro's rd_out and the tile's operand register, which is
    //: the path with 24.6 ps of slack in the one-bank record -- so it is the term
    //: to look for if the post-route frequency moves.
    reg [WGT_BITS-1:0] wgt_word;
    integer bi;
    always @* begin
        wgt_word = {WGT_BITS{1'b0}};
        for (bi = 0; bi < WGT_BANKS; bi = bi + 1)
            if (bi == ba_int)
                wgt_word = {rd_hi_bus[bi*128 +: 128], rd_lo_bus[bi*128 +: 128]};
    end

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
                    //: An unbacked column stalls the walk.  The array holds its
                    //: accumulators and burns a cycle, which is exactly what a
                    //: bandwidth-starved compute unit does.
                    //: valid must follow the ADDRESS ISSUE by exactly one cycle,
                    //: because that is the SRAM's read latency and the register
                    //: file's.  Deriving it from `col != 0` instead dropped the
                    //: LAST column: the final pair becomes valid on the same
                    //: cycle col reaches cfg_k, which is where the old code
                    //: deasserted valid.  31 of 32 columns accumulated and every
                    //: lane came out wrong -- caught by tb_compute_unit.
                    tile_valid <= walk_adv;
                    if (col < cfg_k) begin
                        if (col_backed) begin
                            rd_addr   <= col[7:0];
                            act_raddr <= col;
                            col       <= col + 9'd1;
                        end
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
