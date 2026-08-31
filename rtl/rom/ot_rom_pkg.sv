`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM service registry.
//
// Every constant here is transcribed from the frozen ROM region plan produced
// by compiler/backends/rom/common/image.py and published as
// ``notes.rom_plan`` inside an ABI 3.0 ROM deployment.  A value that differs
// from that plan is a contract break, not a tuning knob.
//
//   RomLayoutPolicy.row_bytes        -> ROM_ROW_BYTES
//   RomShard(coordinate, region_offset, bytes, resource_address)
//                                    -> the shard table entry below
//   RepairEntry(coordinate, kind, logical_index, spare_index)
//                                    -> the repair table entry below
//   MEMORY_OBJECT_PAYLOAD.node_id / bank_or_tile / base_address / size_bytes
//                                    -> the object table entry below
//
// The sense granule is not in the plan: the plan's repair unit is the 4,096-B
// row, and the number of bits a sense-amplifier bank resolves per access is a
// macro property no open collateral in this repository establishes.  It is
// therefore a declared parameter of this block (ROM_SENSE_BYTES), not a
// measured quantity, and every energy statement that would depend on it is
// outside this block's claim boundary.
// ---------------------------------------------------------------------------
package ot_rom_pkg;

    // -- geometry -------------------------------------------------------
    // rom_plan.layout.row_bytes for both shipped products (Qwen chip and
    // DeepSeek wafer tile) is 4,096.  The row is the repair unit and the
    // wordline granule.
    localparam integer ROM_ROW_BYTES    = 4096;
    // Declared operand-bus / sense-granule width.  64 B matches the 64-byte
    // transfer granule the rest of this repository's memory front ends use
    // (rtl/ot_ta_dma_hbm_to_sram.sv).  It is a design declaration.
    localparam integer ROM_SENSE_BYTES  = 64;
    localparam integer ROM_SENSE_BITS   = ROM_SENSE_BYTES * 8;
    localparam integer ROM_SUBWORDS_PER_ROW = ROM_ROW_BYTES / ROM_SENSE_BYTES;

    localparam [31:0] ROM_NO_ID = 32'hffff_ffff;

    // The same three numbers in the widths the address arithmetic needs.  They
    // are written out rather than cast so that both simulators elaborate them
    // without a width warning; ot_rom_read_service checks at elaboration that
    // they still equal the integer forms above, because a constant written
    // twice is a constant that can differ once.
    localparam [63:0] ROM_ROW_BYTES_64        = 64'd4096;
    localparam [63:0] ROM_SENSE_BYTES_64      = 64'd64;
    localparam [63:0] ROM_SUBWORDS_PER_ROW_64 = 64'd64;
    localparam [7:0]  ROM_SENSE_BYTES_8       = 8'd64;

    // -- completion status ----------------------------------------------
    localparam [1:0] ROM_STATUS_OK     = 2'd0;  // every requested byte served
    localparam [1:0] ROM_STATUS_MASKED = 2'd1;  // region masked off: no array
                                                // access, no bytes, expected
    localparam [1:0] ROM_STATUS_FAULT  = 2'd2;  // fail closed, no bytes

    // -- fault classes ---------------------------------------------------
    localparam [3:0] ROM_FAULT_NONE            = 4'd0;
    // A ROM-class object that the region plan does not place.  It names no
    // bank, so no wordline can be selected for it.  See the campaign note on
    // generated ROM objects.
    localparam [3:0] ROM_FAULT_UNPLACED_OBJECT = 4'd1;
    localparam [3:0] ROM_FAULT_OUT_OF_RANGE    = 4'd2;
    // The shard table does not tile the region: an address inside the object
    // fell in no shard.  Impossible for a well formed plan; refused rather
    // than silently clamped, because a clamp would read a legal wrong row.
    localparam [3:0] ROM_FAULT_SHARD_GAP       = 4'd3;
    localparam [3:0] ROM_FAULT_QUARANTINED     = 4'd4;
    // A column repair is activated on the resource this read reaches.  This
    // block implements row redundancy only; a column redirect changes which
    // physical bit lines are sensed and this block does not implement it, so
    // it refuses rather than returning the unrepaired column.
    localparam [3:0] ROM_FAULT_COLUMN_REPAIR   = 4'd5;
    localparam [3:0] ROM_FAULT_ZERO_LENGTH     = 4'd6;

    // -- configuration channel selectors ---------------------------------
    localparam [3:0] ROM_CFG_OBJECT     = 4'd0;
    localparam [3:0] ROM_CFG_SHARD      = 4'd1;
    localparam [3:0] ROM_CFG_REPAIR     = 4'd2;
    localparam [3:0] ROM_CFG_REGION_EN  = 4'd3;  // index = region, data[0]=1 masks it
    // Quarantine is a LIST, not a bit per placement resource: index selects a
    // list slot, data[31:0] names the placement resource that slot withdraws
    // and data[32] is the slot's valid bit.  This comment used to read
    // "data[0]=1 quarantines it", which was true when the table was a bitmap
    // indexed by resource; a comment that outlives its field is how a loader
    // ends up writing the wrong word into the right slot.
    localparam [3:0] ROM_CFG_RESOURCE   = 4'd4;
    localparam [3:0] ROM_CFG_OBJECT_N   = 4'd5;  // index = populated object count
    localparam [3:0] ROM_CFG_CLEAR      = 4'd6;  // clear counters and row buffer

    // -- correlation digest ----------------------------------------------
    // A 64-bit Galois LFSR step, used to compare a beat stream that is far too
    // long to publish beat by beat.  It is a correlation aid and nothing else:
    // it is linear, so it is not a cryptographic binding, and the campaign
    // additionally checks the exact beat count, byte count, activation count
    // and the first and last beat of every request.
    localparam [63:0] ROM_DIGEST_POLY = 64'h42f0_e1eb_a9ea_3693;

    function automatic [63:0] rom_digest_step;
        input [63:0] state;
        input [63:0] value;
        begin
            rom_digest_step = {state[62:0], 1'b0}
                            ^ (state[63] ? ROM_DIGEST_POLY : 64'd0)
                            ^ value;
        end
    endfunction

endpackage
