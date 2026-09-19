`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ATTENTION.SPARSE's selected-row decode: one query row's index block.
//
// The engine reads a [span, slots] U32 index array where 0xffffffff is padding,
// and both the QK and the AV walk need the same three things out of it: which
// lanes are live, how many, and each live lane's KV row -- IN THE ORDER THE
// PRODUCER WROTE THEM.
//
// THE ORDER IS PART OF THE CONTRACT AND SORTING IT IS A DEFECT.  The reference's
// own decode says so at length: ROUTE.WINDOW_INDEX emits chronological physical
// ring slots, which wrap numerically once the decode cursor passes slot 127, and
// "the engine therefore must not silently sort here" because that order reaches
// the block-64 online softmax and the BF16 AV accumulation. Rejecting the wrap
// is what once made every uncompressed sparse layer trap at decode position 128
// with every selected row valid. This block preserves the order and refuses
// nothing on account of it.
//
// PADDING IS A TRAILING RUN, WHICH IS A SEPARATE RULE FROM COUNTING IT.  ABI 3.0
// amendment A6 fixes padding as one trailing run, so the reference requires
// ``all(valid[:count])`` -- a live lane AFTER a pad lane is a refusal, not a
// lane to be compacted. Counting the live lanes and checking they are the first
// ``count`` of them are two different checks and this does both: a block holding
// [row, pad, row] has count 2 and is REFUSED, where a block that merely counted
// would accept it and silently drop a row.
//
// THREE REFUSALS, each the reference's own:
//   * a live index at or beyond the resolved KV row count -- trap class 3, and
//     bounded against the PHYSICAL operand, never against the much larger
//     absolute position space that sparse aux_id_2 carries;
//   * padding interleaved with live lanes;
//   * an all-padding row -- "an empty softmax has no defined value", trap
//     class 6. Note this is per QUERY ROW and not per source block: a later
//     block of a row may legally be all padding, which is why
//     ot_a3_attention_softmax_block admits that case and this does not.
// ---------------------------------------------------------------------------
module ot_a3_attention_kv_index #(
    parameter integer SLOTS = 64
) (
    input  wire        clk,
    input  wire        rst_n,

    input  wire        start,
    //: Rows the resolved KV operand actually has. The bound is this, not the
    //: absolute position count.
    input  wire [31:0] cfg_kv_rows,
    input  wire [SLOTS*32-1:0] indices,

    output reg         busy,
    output reg         done,
    output reg  [SLOTS-1:0] lane_valid,
    output reg  [31:0] live_count,
    output reg  [7:0]  error_code
);
    localparam [7:0] ERR_NONE = ot_a3_engine_pkg::ERR_NONE;
    localparam [7:0] ERR_INDEX_RANGE = ot_a3_engine_pkg::ERR_INDEX_RANGE;
    localparam [7:0] ERR_SHAPE = ot_a3_engine_pkg::ERR_SHAPE;

    localparam [31:0] PAD_INDEX = 32'hffff_ffff;

    integer i;
    integer node;

    //: ONE PASS OVER THE BLOCK, BUT NOT ONE CHAIN.  The four things this block
    //: publishes -- the mask, the count, whether a live lane follows a pad lane,
    //: and whether a live lane is out of range -- are all REDUCTIONS, and a
    //: sequential accumulate over SLOTS turns two of them into serial carries.
    //: Written that way, the routed block reported 148.1 MHz at a 4 ns target
    //: with 157 ``HAxp5`` half-adders on one path from ``indices`` to
    //: ``lane_valid``: 64 chained 32-bit increments, which is what
    //: ``count = count + 1`` inside the loop means after synthesis.
    //:
    //: Each is restated as a per-lane term under a balanced reduction, which is
    //: the same function at logarithmic depth:
    //:
    //:   * the mask is already per-lane and was never the problem;
    //:   * the count is a POPCOUNT of the mask, summed up a binary tree, so its
    //:     depth is ``$clog2(SLOTS)`` narrow adds instead of SLOTS wide ones;
    //:   * "a live lane after a pad lane" is LOCAL.  A6 fixes padding as one
    //:     TRAILING run, and a mask is one trailing run exactly when no live
    //:     lane follows a dead one -- so ``mask[i] & ~mask[i-1]`` over i >= 1 is
    //:     the whole test and the serial ``seen_pad`` carry is not needed.
    //:     (Both directions: a live lane with ANY earlier pad lane has a nearest
    //:     one, and the lane just after that pad satisfies the local test.)
    //:   * the range refusal is a per-lane compare under an OR.
    reg [SLOTS-1:0] mask_scan;
    reg [SLOTS-1:0] mask_prev;
    reg [SLOTS-1:0] range_bit;
    reg [31:0] count_scan;
    reg        interleaved_scan;
    reg        out_of_range_scan;
    reg [31:0] slot_code;

    //: The popcount tree, as a heap over the next power of two at or above
    //: SLOTS: leaves at ``[LEAVES .. 2*LEAVES-1]``, each internal node the sum
    //: of its two children, the total at node 1.  CW is the width that holds
    //: SLOTS, so the adds are 1 to CW bits wide rather than 32.
    localparam integer LEAVES = 1 << $clog2(SLOTS);
    localparam integer CW = $clog2(SLOTS + 1);
    reg [CW-1:0] adder_node [0:2*LEAVES-1];

    always @* begin
        mask_scan = {SLOTS{1'b0}};
        range_bit = {SLOTS{1'b0}};
        for (i = 0; i < SLOTS; i = i + 1) begin
            //: Named, because indexing a part-select is the construct Verilator
            //: accepts and the pinned Icarus 11 rejects.
            slot_code = indices[i*32 +: 32];
            if (slot_code != PAD_INDEX) begin
                mask_scan[i] = 1'b1;
                //: Unsigned, so this is the >= kv_rows bound directly.
                range_bit[i] = (slot_code >= cfg_kv_rows);
            end
        end
        out_of_range_scan = |range_bit;

        //: A live lane after a pad lane breaks A6's trailing-run rule.  Bit i of
        //: ``mask_prev`` is lane i-1, and bit 0 is 1 -- there is no pad lane
        //: before lane 0 -- which the truncating assignment of an SLOTS+1 bit
        //: concatenation to an SLOTS bit reg produces directly, and which is
        //: also correct at SLOTS == 1.
        mask_prev = {mask_scan, 1'b1};
        interleaved_scan = |(mask_scan & ~mask_prev);

        for (i = 0; i < LEAVES; i = i + 1)
            adder_node[LEAVES + i] =
                (i < SLOTS) ? {{(CW-1){1'b0}}, mask_scan[i]} : {CW{1'b0}};
        for (node = LEAVES - 1; node >= 1; node = node - 1)
            adder_node[node] = adder_node[2*node] + adder_node[2*node + 1];
        count_scan = adder_node[1];
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy <= 1'b0; done <= 1'b0;
            lane_valid <= {SLOTS{1'b0}};
            live_count <= 32'd0;
            error_code <= ERR_NONE;
        end else begin
            done <= 1'b0;
            if (start) begin
                busy <= 1'b0;
                done <= 1'b1;
                //: The mask and count are published only when the block is
                //: admitted, so a refused block cannot be mistaken for an
                //: empty one by a caller that reads them without the code.
                if (out_of_range_scan) begin
                    error_code <= ERR_INDEX_RANGE;
                    lane_valid <= {SLOTS{1'b0}};
                    live_count <= 32'd0;
                end else if (interleaved_scan) begin
                    error_code <= ERR_SHAPE;
                    lane_valid <= {SLOTS{1'b0}};
                    live_count <= 32'd0;
                end else if (count_scan == 32'd0) begin
                    error_code <= ERR_SHAPE;
                    lane_valid <= {SLOTS{1'b0}};
                    live_count <= 32'd0;
                end else begin
                    error_code <= ERR_NONE;
                    lane_valid <= mask_scan;
                    live_count <= count_scan;
                end
            end
        end
    end
endmodule
