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

    //: One pass over the block: the mask, the count, whether any live lane
    //: follows a pad lane, and whether any live lane is out of range.
    reg [SLOTS-1:0] mask_scan;
    reg [31:0] count_scan;
    reg        interleaved_scan;
    reg        out_of_range_scan;
    reg        seen_pad;
    reg [31:0] slot_code;
    always @* begin
        mask_scan = {SLOTS{1'b0}};
        count_scan = 32'd0;
        interleaved_scan = 1'b0;
        out_of_range_scan = 1'b0;
        seen_pad = 1'b0;
        for (i = 0; i < SLOTS; i = i + 1) begin
            //: Named, because indexing a part-select is the construct Verilator
            //: accepts and the pinned Icarus 11 rejects.
            slot_code = indices[i*32 +: 32];
            if (slot_code == PAD_INDEX) begin
                seen_pad = 1'b1;
            end else begin
                mask_scan[i] = 1'b1;
                count_scan = count_scan + 32'd1;
                //: A live lane after a pad lane breaks A6's trailing-run rule.
                if (seen_pad) interleaved_scan = 1'b1;
                //: Unsigned, so this is the >= kv_rows bound directly.
                if (slot_code >= cfg_kv_rows) out_of_range_scan = 1'b1;
            end
        end
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
