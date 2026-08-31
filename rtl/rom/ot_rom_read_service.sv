`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ROM read service: deployment-named ROM object -> bank/row/sense -> operand
// bus.
//
// WHAT THIS BLOCK IS
// ------------------
// It is the addressing, ordering, masking and repair-translation front end of
// an immutable weight store.  It answers exactly one question, and it answers
// it the way the compiled deployment says to:
//
//     given (object_id, byte_offset, byte_length), which placement resource,
//     which row inside it, which sense granule of that row, in what order,
//     and is this read allowed to happen at all?
//
// Every table it consults is the compiled ROM region plan
// (compiler/backends/rom/common/image.py, published as ``notes.rom_plan`` in
// an ABI 3.0 ROM deployment), written in through the configuration channel:
//
//   object table   one entry per ROM MEMORY_OBJECT: the region it belongs to,
//                  its byte offset inside that region, its size, and the range
//                  of shard-table entries that region occupies.
//   shard table    one entry per RomShard: the placement resource (node,
//                  reticle, tile, bank), the region byte offset the shard
//                  starts at, its length, and its address inside the resource.
//                  A region larger than one resource has many shards; walking
//                  them is what makes a wafer tile addressable.
//   repair table   one entry per activated spare.  Row redundancy is applied
//                  here, so a logical row address stays stable across repair.
//   region mask    one bit per region.  A masked region performs NO array
//                  access at all: no wordline, no sense, no bytes, and the
//                  completion says MASKED rather than returning zeros a
//                  consumer could mistake for weights.
//   quarantine     a short list of withdrawn placement resources, compared
//                  against the shard's resource.  A quarantined resource fails
//                  the read closed; it does not silently serve.
//
// WHAT THIS BLOCK IS NOT
// ----------------------
// There is no ROM array in this file.  The array sits behind the sense
// interface (sense_req_* / sense_rsp_*) and is supplied by whatever this block
// is integrated with -- in the correlation campaign a behavioural window of
// authenticated checkpoint bytes, in a product a foundry macro.  Nothing here
// establishes ROM cell area, read energy, sense margin, wordline delay or
// yield.  This is a control and addressing claim.
//
// There is no write path, and no port on this module could become one: the
// array interface carries a request and a response and nothing else.
//
// ORDERING
// --------
// One request at a time, beats in ascending byte order, one outstanding sense
// access.  A row is activated when the (resource, physical row) pair differs
// from the one held in the row buffer; the row buffer persists across
// requests, so two reads landing in the same row activate once.  Activations
// versus sense accesses is the only quantity here an energy model could use,
// and it is reported as a count, not as an energy.
//
// FAIL CLOSED MEANS BEFORE, NOT DURING
// ------------------------------------
// The extent is walked twice: once to prove every placement resource it
// reaches is in service, and only then to read.  A read that crosses from a
// healthy resource into a quarantined one must put no byte on the operand bus
// at all -- a consumer cannot tell a partial weight from a whole one -- and it
// must not disturb the row buffer either, or the next read's activation count
// would move.  Both properties are checked from outside the block: the array's
// own sense count must equal the sum of the per-request beat counts, so a
// masked or refused request that touched the array would fail.
// ---------------------------------------------------------------------------
// Package items are referenced fully qualified rather than imported:
// the pinned open synthesis front end does not accept a package import,
// and a block that cannot be synthesised is not an implementation.
module ot_rom_read_service #(
    parameter integer OBJECTS         = 512,
    parameter integer SHARDS          = 16384,
    parameter integer REGIONS         = 256,
    parameter integer REPAIR_ENTRIES  = 64,
    parameter integer QUARANTINE_ENTRIES = 32,
    parameter integer TAG_W           = 16,
    parameter integer OBJ_IDX_W       = (OBJECTS        <= 2) ? 1 : $clog2(OBJECTS),
    parameter integer SHD_IDX_W       = (SHARDS         <= 2) ? 1 : $clog2(SHARDS),
    parameter integer REG_IDX_W       = (REGIONS        <= 2) ? 1 : $clog2(REGIONS),
    parameter integer REP_IDX_W       = (REPAIR_ENTRIES <= 2) ? 1 : $clog2(REPAIR_ENTRIES),
    parameter integer QUA_IDX_W       = (QUARANTINE_ENTRIES <= 2) ? 1
                                        : $clog2(QUARANTINE_ENTRIES)
) (
    input  wire                      clk,
    input  wire                      rst_n,

    // -- configuration channel (the compiled plan, written in) ----------
    input  wire                      cfg_valid,
    input  wire [3:0]                cfg_sel,
    input  wire [31:0]               cfg_index,
    input  wire [319:0]              cfg_data,
    output wire                      cfg_ready,
    // Sticky until reset.  A configuration write that named a slot outside the
    // table it selects, or a selector this block does not implement, is
    // DROPPED and recorded here.  It is not folded onto a legal slot: a
    // quarantine entry silently folded onto slot 0 forgets a withdrawn
    // placement resource, and the read that follows serves it.  That is
    // fail-open, and it is the failure signature this whole campaign exists to
    // catch, so the block refuses instead of the loader being trusted to count.
    output reg                       cfg_error,

    // -- request --------------------------------------------------------
    input  wire                      req_valid,
    output wire                      req_ready,
    input  wire [31:0]               req_object_id,
    input  wire [63:0]               req_byte_offset,
    input  wire [31:0]               req_byte_length,
    input  wire [TAG_W-1:0]          req_tag,

    // -- sense interface to the ROM array (read only, by construction) ---
    output reg                       sense_req_valid,
    input  wire                      sense_req_ready,
    output reg  [31:0]               sense_resource,
    output reg  [31:0]               sense_row,
    output reg  [7:0]                sense_subword,
    output reg                       sense_activate,
    input  wire                      sense_rsp_valid,
    input  wire [ot_rom_pkg::ROM_SENSE_BITS-1:0] sense_rsp_data,

    // -- operand bus ----------------------------------------------------
    output reg                       out_valid,
    input  wire                      out_ready,
    output reg  [ot_rom_pkg::ROM_SENSE_BITS-1:0] out_data,
    output reg  [15:0]               out_bytes,
    output reg  [TAG_W-1:0]          out_tag,
    output reg                       out_last,

    // -- completion -----------------------------------------------------
    output reg                       cmp_valid,
    output reg  [TAG_W-1:0]          cmp_tag,
    output reg  [1:0]                cmp_status,
    output reg  [3:0]                cmp_fault,
    output reg  [63:0]               cmp_beats,
    output reg  [63:0]               cmp_bytes,
    output reg  [63:0]               cmp_activations,
    output reg  [63:0]               cmp_beat_digest,
    output reg  [63:0]               cmp_data_digest,
    output reg  [255:0]              cmp_first_beat,
    output reg  [255:0]              cmp_last_beat,

    // -- architectural counters -----------------------------------------
    output reg  [63:0]               count_requests,
    output reg  [63:0]               count_beats,
    output reg  [63:0]               count_bytes,
    output reg  [63:0]               count_activations,
    output reg  [63:0]               count_masked,
    output reg  [63:0]               count_faults,
    output reg  [3:0]                first_fault_class,
    output reg  [31:0]               first_fault_object
);
    // -----------------------------------------------------------------
    // Tables.  Written only through cfg_*; nothing in the request path
    // writes them, and there is no other writer in this file.
    //
    // object entry   [ 31:  0] object_id      [ 63: 32] region_id
    //                [ 95: 64] shard_first    [127: 96] shard_count
    //                [191:128] region_offset  [255:192] size_bytes
    // shard entry    [ 31:  0] region_id      [ 47: 32] node_id
    //                [ 63: 48] reticle        [ 79: 64] tile
    //                [ 95: 80] bank           [127: 96] resource_index
    //                [191:128] region_offset  [255:192] bytes
    //                [319:256] resource_address
    // repair entry   [ 31:  0] resource_index [ 63: 32] logical_index
    //                [ 95: 64] spare_index, with the kind (0 row, 1 column)
    //                and valid bits held in their own packed vectors
    // -----------------------------------------------------------------
    // The two health masks and the activated-spare valid/kind bits are packed
    // vectors rather than arrays of one-bit elements, so reset clears them in
    // one assignment.  An unpacked array cleared in a reset for-loop is not
    // synthesisable in the older public front end this repository also lints
    // with, and a block that only elaborates under the newer one is not a
    // portable implementation.
    reg [255:0] object_table [0:OBJECTS-1];
    reg [319:0] shard_table  [0:SHARDS-1];
    reg [95:0]  repair_table [0:REPAIR_ENTRIES-1];
    reg [REPAIR_ENTRIES-1:0] repair_valid;
    reg [REPAIR_ENTRIES-1:0] repair_column;
    reg [REGIONS-1:0]        region_masked;
    // Quarantine is a short LIST, not a bit per placement resource.  A wafer
    // plan has 9,300 of them and a flip-flop each would be nine thousand flops
    // in a read path to record a handful of withdrawn tiles; a fuse-programmed
    // comparator list is what a macro periphery uses and what a repair map
    // actually contains.  A list that overflows is refused by the loader rather
    // than truncated, which is why the bench publishes the depth it needs.
    reg [31:0]  quarantine_table [0:QUARANTINE_ENTRIES-1];
    reg [QUARANTINE_ENTRIES-1:0] quarantine_valid;
    reg [31:0]  object_count;

    assign cfg_ready = 1'b1;

    // The table depths at the width cfg_index is compared at.  Written once
    // each, because a bound written twice is a bound that can differ once.
    localparam [31:0] N_OBJECTS    = OBJECTS;
    localparam [31:0] N_SHARDS     = SHARDS;
    localparam [31:0] N_REGIONS    = REGIONS;
    localparam [31:0] N_REPAIR     = REPAIR_ENTRIES;
    localparam [31:0] N_QUARANTINE = QUARANTINE_ENTRIES;

    // Every table write below indexes with cfg_index truncated to the table's
    // address width.  Truncation is silent: an out-of-range slot lands on a
    // legal wrong entry and nothing says so.  This decides, at full width,
    // whether the slot exists at all.
    // An object entry also CARRIES two indices this block truncates: the
    // region_id it selects the mask bit with, and the shard range its search
    // walks.  Those are payload, not slot, and an out-of-range one is the same
    // silent fold by a different door -- a masked region read as an unmasked
    // one, or a shard search that walks entries belonging to another region.
    wire [32:0] obj_shard_end = {1'b0, cfg_data[95:64]} + {1'b0, cfg_data[127:96]};
    wire        obj_payload_bad = (cfg_data[63:32] >= N_REGIONS)
                                  || (obj_shard_end > {1'b0, N_SHARDS});

    reg cfg_slot_bad;
    always @* begin
        case (cfg_sel)
            ot_rom_pkg::ROM_CFG_OBJECT:    cfg_slot_bad = (cfg_index >= N_OBJECTS)
                                                          || obj_payload_bad;
            ot_rom_pkg::ROM_CFG_SHARD:     cfg_slot_bad = (cfg_index >= N_SHARDS);
            ot_rom_pkg::ROM_CFG_REPAIR:    cfg_slot_bad = (cfg_index >= N_REPAIR);
            ot_rom_pkg::ROM_CFG_REGION_EN: cfg_slot_bad = (cfg_index >= N_REGIONS);
            ot_rom_pkg::ROM_CFG_RESOURCE:  cfg_slot_bad = (cfg_index >= N_QUARANTINE);
            // The populated object count is the binary search's upper bound.
            // A count past the table depth walks entries that were never
            // written, so it is a bound, not a slot: equal is legal.
            ot_rom_pkg::ROM_CFG_OBJECT_N:  cfg_slot_bad = (cfg_index > N_OBJECTS);
            ot_rom_pkg::ROM_CFG_CLEAR:     cfg_slot_bad = 1'b0;
            default:                       cfg_slot_bad = 1'b1;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            object_count    <= 32'd0;
            repair_valid    <= '0;
            repair_column   <= '0;
            region_masked   <= '0;
            quarantine_valid <= '0;
            cfg_error       <= 1'b0;
        end else if (cfg_valid && cfg_slot_bad) begin
            cfg_error <= 1'b1;
        end else if (cfg_valid) begin
            case (cfg_sel)
                ot_rom_pkg::ROM_CFG_OBJECT:
                    object_table[cfg_index[OBJ_IDX_W-1:0]] <= cfg_data[255:0];
                ot_rom_pkg::ROM_CFG_SHARD:
                    shard_table[cfg_index[SHD_IDX_W-1:0]] <= cfg_data;
                ot_rom_pkg::ROM_CFG_REPAIR: begin
                    repair_table[cfg_index[REP_IDX_W-1:0]]  <= cfg_data[95:0];
                    repair_column[cfg_index[REP_IDX_W-1:0]] <= cfg_data[96];
                    repair_valid[cfg_index[REP_IDX_W-1:0]]  <= cfg_data[97];
                end
                ot_rom_pkg::ROM_CFG_REGION_EN:
                    region_masked[cfg_index[REG_IDX_W-1:0]] <= cfg_data[0];
                ot_rom_pkg::ROM_CFG_RESOURCE: begin
                    // cfg_index selects a list slot; the payload names the
                    // placement resource that slot withdraws.
                    quarantine_table[cfg_index[QUA_IDX_W-1:0]] <= cfg_data[31:0];
                    quarantine_valid[cfg_index[QUA_IDX_W-1:0]] <= cfg_data[32];
                end
                ot_rom_pkg::ROM_CFG_OBJECT_N:
                    object_count <= cfg_index;
                default: ;
            endcase
        end
    end

    // -- table read ports (register-file style, index registered) --------
    reg [OBJ_IDX_W-1:0] obj_index;
    reg [SHD_IDX_W-1:0] shd_index;
    reg [REG_IDX_W-1:0] reg_index;

    // Registered word selects, which is what a table this deep is in a real
    // design and what both simulators elaborate cheaply.  The read costs one
    // cycle, so every table lookup below spends a state waiting for it rather
    // than assuming a combinational table.
    reg [255:0] obj_rd;
    reg [319:0] shd_rd;
    reg         mask_rd;
    always @(posedge clk) begin
        obj_rd  <= object_table[obj_index];
        shd_rd  <= shard_table[shd_index];
        mask_rd <= region_masked[reg_index];
    end

    // The quarantine list is a comparator sweep, not a table read: it answers
    // in the same cycle the shard's resource is known.
    reg     quarantined;
    integer qi;
    always @* begin
        quarantined = 1'b0;
        for (qi = 0; qi < QUARANTINE_ENTRIES; qi = qi + 1)
            if (quarantine_valid[qi] && (quarantine_table[qi] == s_resource))
                quarantined = 1'b1;
    end

    // -----------------------------------------------------------------
    // Request state
    // -----------------------------------------------------------------
    localparam [3:0] S_IDLE       = 4'd0;
    localparam [3:0] S_OBJ_STEP   = 4'd1;
    localparam [3:0] S_OBJ_RD     = 4'd2;
    localparam [3:0] S_OBJ_CMP    = 4'd3;
    localparam [3:0] S_OBJ_CHECK  = 4'd4;
    localparam [3:0] S_MASK_WAIT  = 4'd5;
    localparam [3:0] S_SHD_STEP   = 4'd6;
    localparam [3:0] S_SHD_RD     = 4'd7;
    localparam [3:0] S_SHD_CMP    = 4'd8;
    localparam [3:0] S_RES_RD     = 4'd9;
    localparam [3:0] S_RES_WAIT   = 4'd10;
    localparam [3:0] S_BEAT_ISSUE = 4'd11;
    localparam [3:0] S_BEAT_WAIT  = 4'd12;
    localparam [3:0] S_BEAT_PUSH  = 4'd13;
    localparam [3:0] S_DONE       = 4'd14;

    reg [3:0]  state;
    reg [31:0] r_object_id;
    reg [63:0] r_offset;
    reg [63:0] r_length;
    reg [TAG_W-1:0] r_tag;

    reg [63:0] r_size;
    reg [63:0] r_obj_region_offset;
    reg [31:0] r_shard_first;
    reg [31:0] r_shard_count;

    // The end of the requested extent, at 65 bits.
    //
    // req_byte_offset is a 64-bit field the REQUESTER supplies.  The range
    // check used to be (r_offset + r_length) > r_size at 64 bits, and a 64-bit
    // sum wraps: an offset within 4 GiB of 2**64 makes the sum small, the
    // in-range test passes, and region_byte then wraps too and lands in the
    // middle of the object.  The read is served, the completion says OK, and
    // the bytes are weights the request did not ask for.  Legal values, no
    // trap, nothing refused, wrong answer.
    //
    // The Python reference this campaign compares against computes the same
    // sum in arbitrary precision and never wrapped, so the two sides were
    // never equivalent -- they simply never disagreed, because the widest
    // offset any published vector set carries is 21 GiB.  This makes the RTL
    // side exact rather than making the reference wrap.  No vector set reaches
    // the wrap, so nothing here exercises this guard, and §9 of
    // docs/ROM_SERVICE_RTL.md says so rather than letting it read as tested.
    wire [64:0] r_extent_end = {1'b0, r_offset} + {1'b0, r_length};

    reg [31:0] lo;
    reg [31:0] hi;
    reg [31:0] mid;
    // The binary-search midpoint, computed ONCE.  It used to be written twice
    // -- once at full width into `mid`, once truncated into the table index --
    // and the two disagreed as soon as lo + hi reached the table depth, which
    // a sixteen-object chip plan never does and a three-hundred-and-twelve
    // object wafer plan does. The search then compared one entry and moved its
    // bounds as though it had compared another.
    wire [31:0] mid_next = (lo + hi) >> 1;

    reg [31:0] s_resource;
    reg [63:0] s_region_offset;
    reg [63:0] s_bytes;
    reg [63:0] s_resource_address;
    reg        s_valid;

    reg [63:0] cur;
    reg [63:0] region_byte;
    // The extent is walked twice: once to prove every placement resource it
    // reaches is in service, and only then to read.  A refused read must not
    // put a single byte of weight on the operand bus -- a consumer cannot tell
    // a partial weight from a whole one -- so the health of the last resource a
    // read reaches has to be known before the first beat leaves the first one.
    reg        validating;
    reg [63:0] r_start_byte;
    reg [63:0] r_end_byte;
    reg [63:0] beat_index;
    reg [63:0] acc_beats;
    reg [63:0] acc_bytes;
    reg [63:0] acc_acts;
    reg [63:0] acc_beat_digest;
    reg [63:0] acc_data_digest;
    reg [255:0] first_beat;
    reg [255:0] last_beat;
    reg        have_first;

    reg        rowbuf_valid;
    reg [31:0] rowbuf_resource;
    reg [31:0] rowbuf_row;

    reg [63:0] b_resource_address;
    reg [63:0] b_region_byte;
    reg [31:0] b_resource;
    reg [31:0] b_physical_row;
    reg [7:0]  b_subword;
    reg [15:0] b_bytes;
    reg [7:0]  b_byte_in_word;
    reg        b_activate;

    reg [1:0]  r_status;
    reg [3:0]  r_fault;

    assign req_ready = (state == S_IDLE);

    // -----------------------------------------------------------------
    // Geometry of the beat that would start at region_byte.  Split against
    // three limits at once: what is left of the request, what is left of the
    // sense granule, and what is left of the shard.  A shard end is a
    // placement-resource boundary, so a beat may never cross one.
    // -----------------------------------------------------------------
    localparam [63:0] ROW_BYTES_64    = ot_rom_pkg::ROM_ROW_BYTES_64;
    localparam [63:0] SENSE_BYTES_64  = ot_rom_pkg::ROM_SENSE_BYTES_64;
    localparam [63:0] SUBWORDS_64     = ot_rom_pkg::ROM_SUBWORDS_PER_ROW_64;
    localparam [7:0]  SENSE_BYTES_8   = ot_rom_pkg::ROM_SENSE_BYTES_8;

    // The package writes each of these three numbers twice, once as an integer
    // and once at the width the address arithmetic needs.  A constant written
    // twice is a constant that can differ once, so both halves are compared
    // here -- at equal widths, so no lint pragma is needed and no tool is asked
    // to ignore anything.
    initial begin
        if (ROW_BYTES_64[31:0] != ot_rom_pkg::ROM_ROW_BYTES
            || ROW_BYTES_64[63:32] != 32'd0)
            $error("ot_rom_pkg row-byte constants disagree");
        if (SENSE_BYTES_64[31:0] != ot_rom_pkg::ROM_SENSE_BYTES
            || SENSE_BYTES_64[63:32] != 32'd0)
            $error("ot_rom_pkg sense-byte constants disagree");
        if (SUBWORDS_64[31:0] != ot_rom_pkg::ROM_SUBWORDS_PER_ROW
            || SUBWORDS_64[63:32] != 32'd0)
            $error("ot_rom_pkg subword constants disagree");
        if ({24'd0, SENSE_BYTES_8} != ot_rom_pkg::ROM_SENSE_BYTES)
            $error("ot_rom_pkg sense-byte byte constant disagrees");
        if (ot_rom_pkg::ROM_SENSE_BYTES * ot_rom_pkg::ROM_SUBWORDS_PER_ROW
            != ot_rom_pkg::ROM_ROW_BYTES)
            $error("the sense granule does not tile the ROM row");
    end

    wire [63:0] g_offset_in_shard  = region_byte - s_region_offset;
    wire [63:0] g_resource_address = s_resource_address + g_offset_in_shard;
    wire [63:0] g_left_request     = r_length - cur;
    wire [63:0] g_left_word        = SENSE_BYTES_64
                                   - (g_resource_address % SENSE_BYTES_64);
    wire [63:0] g_left_shard       = s_bytes - g_offset_in_shard;

    reg  [63:0] g_take;
    always @* begin
        g_take = g_left_request;
        if (g_left_word  < g_take) g_take = g_left_word;
        if (g_left_shard < g_take) g_take = g_left_shard;
    end

    // A placement resource may be larger than 4 GiB (the Qwen chip plan uses
    // 8 GiB banks), so the resource address is 64 bits wide and only the row
    // index that comes out of it is 32.
    wire [63:0] g_row64       = g_resource_address / ROW_BYTES_64;
    wire [63:0] g_subword64   = (g_resource_address / SENSE_BYTES_64)
                              % SUBWORDS_64;
    wire [31:0] c_logical_row = g_row64[31:0];

    // -- activated-spare lookup, on the candidate beat -------------------
    reg        rep_row_hit;
    reg [31:0] rep_row_spare;
    reg        rep_col_hit;
    integer    ri;
    always @* begin
        rep_row_hit   = 1'b0;
        rep_row_spare = 32'd0;
        rep_col_hit   = 1'b0;
        for (ri = 0; ri < REPAIR_ENTRIES; ri = ri + 1) begin
            if (repair_valid[ri] && (repair_table[ri][31:0] == s_resource)) begin
                if (repair_column[ri]) begin
                    rep_col_hit = 1'b1;
                end else if (repair_table[ri][63:32] == c_logical_row) begin
                    rep_row_hit   = 1'b1;
                    rep_row_spare = repair_table[ri][95:64];
                end
            end
        end
    end

    wire [31:0] c_physical_row = rep_row_hit ? rep_row_spare : c_logical_row;
    wire [7:0]  c_subword      = g_subword64[7:0];
    // ONE open row for the whole array, not one per bank.  With a single
    // outstanding sense access and reads that walk ascending addresses that is
    // exact; for an access pattern that alternates between placement resources
    // it re-activates where a per-bank row buffer would not, so the activation
    // count this block reports is an upper bound for such patterns rather than
    // a measurement of them.  It is a declared design choice, and since
    // activations are the one quantity here an energy model could use, saying
    // which way it errs matters more than the number.
    wire        c_activate     = !rowbuf_valid
                               || (rowbuf_resource != s_resource)
                               || (rowbuf_row      != c_physical_row);

    // -- the column mux --------------------------------------------------
    // The sensed granule holds ROM_SENSE_BYTES bytes.  A beat that starts part
    // way into the granule presents its payload from the low lane, and the
    // lanes above the payload are zeroed rather than left holding the
    // neighbouring ROM bytes, which a consumer would otherwise read as weights
    // it did not ask for.
    reg [ot_rom_pkg::ROM_SENSE_BITS-1:0] aligned;
    reg [ot_rom_pkg::ROM_SENSE_BITS-1:0] lane_mask;
    integer mi;
    always @* begin
        lane_mask = {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};
        for (mi = 0; mi < ot_rom_pkg::ROM_SENSE_BYTES; mi = mi + 1)
            if (mi < {16'd0, b_bytes})
                lane_mask[mi*8 +: 8] = 8'hff;
        aligned = (sense_rsp_data >> ({3'd0, b_byte_in_word} * 8)) & lane_mask;
    end

    // -- the published beat record ---------------------------------------
    wire [255:0] beat_record = {b_resource_address,
                                b_region_byte,
                                b_resource,
                                b_physical_row,
                                b_subword,
                                b_bytes,
                                b_activate,
                                7'd0,
                                beat_index[31:0]};

    // Digest next-values, computed combinationally so the sequential block
    // stays free of blocking assignments.
    reg [63:0] next_beat_digest;
    always @* begin
        next_beat_digest = ot_rom_pkg::rom_digest_step(acc_beat_digest, beat_record[ 63:  0]);
        next_beat_digest = ot_rom_pkg::rom_digest_step(next_beat_digest, beat_record[127: 64]);
        next_beat_digest = ot_rom_pkg::rom_digest_step(next_beat_digest, beat_record[191:128]);
        next_beat_digest = ot_rom_pkg::rom_digest_step(next_beat_digest, beat_record[255:192]);
    end

    reg [63:0] next_data_digest;
    // Fields the tables carry that this block does not fully consult: the
    // shard's node/reticle/tile/bank coordinate (it addresses by the flat
    // resource index the plan assigns), the high halves of the row and granule
    // indices, which a legal address cannot reach, and the object entry's
    // 32-bit region_id, of which only the low REG_IDX_W bits are read -- how
    // many that is depends on the REGIONS parameter, so the whole field is
    // named here rather than a slice that would be right for one elaboration
    // and wrong for another.  An object entry whose region_id does not fit
    // REGIONS is refused at configuration by cfg_error, so what reaches this
    // select is never a truncation.
    // Named so the reader knows they were considered rather than overlooked.
    wire _unused_ok = &{1'b0,
                        obj_rd[63:32],
                        shd_rd[95:0],
                        g_row64[63:32],
                        g_subword64[63:8],
                        1'b0};

    integer di;
    always @* begin
        next_data_digest = acc_data_digest;
        for (di = 0; di < ot_rom_pkg::ROM_SENSE_BITS/64; di = di + 1)
            next_data_digest = ot_rom_pkg::rom_digest_step(next_data_digest,
                                               out_data[di*64 +: 64]);
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state              <= S_IDLE;
            sense_req_valid    <= 1'b0;
            sense_resource     <= 32'd0;
            sense_row          <= 32'd0;
            sense_subword      <= 8'd0;
            sense_activate     <= 1'b0;
            out_valid          <= 1'b0;
            out_data           <= {ot_rom_pkg::ROM_SENSE_BITS{1'b0}};
            out_bytes          <= 16'd0;
            out_tag            <= {TAG_W{1'b0}};
            out_last           <= 1'b0;
            cmp_valid          <= 1'b0;
            cmp_tag            <= {TAG_W{1'b0}};
            cmp_status         <= ot_rom_pkg::ROM_STATUS_OK;
            cmp_fault          <= ot_rom_pkg::ROM_FAULT_NONE;
            cmp_beats          <= 64'd0;
            cmp_bytes          <= 64'd0;
            cmp_activations    <= 64'd0;
            cmp_beat_digest    <= 64'd0;
            cmp_data_digest    <= 64'd0;
            cmp_first_beat     <= 256'd0;
            cmp_last_beat      <= 256'd0;
            rowbuf_valid       <= 1'b0;
            rowbuf_resource    <= 32'd0;
            rowbuf_row         <= 32'd0;
            count_requests     <= 64'd0;
            count_beats        <= 64'd0;
            count_bytes        <= 64'd0;
            count_activations  <= 64'd0;
            count_masked       <= 64'd0;
            count_faults       <= 64'd0;
            first_fault_class  <= ot_rom_pkg::ROM_FAULT_NONE;
            first_fault_object <= ot_rom_pkg::ROM_NO_ID;
            obj_index          <= {OBJ_IDX_W{1'b0}};
            shd_index          <= {SHD_IDX_W{1'b0}};
            reg_index          <= {REG_IDX_W{1'b0}};
            r_object_id        <= ot_rom_pkg::ROM_NO_ID;
            r_offset           <= 64'd0;
            r_length           <= 64'd0;
            r_tag              <= {TAG_W{1'b0}};
            r_size             <= 64'd0;
            r_obj_region_offset<= 64'd0;
            r_shard_first      <= 32'd0;
            r_shard_count      <= 32'd0;
            lo                 <= 32'd0;
            hi                 <= 32'd0;
            mid                <= 32'd0;
            s_resource         <= 32'd0;
            s_region_offset    <= 64'd0;
            s_bytes            <= 64'd0;
            s_resource_address <= 64'd0;
            s_valid            <= 1'b0;
            cur                <= 64'd0;
            region_byte        <= 64'd0;
            validating         <= 1'b0;
            r_start_byte       <= 64'd0;
            r_end_byte         <= 64'd0;
            beat_index         <= 64'd0;
            acc_beats          <= 64'd0;
            acc_bytes          <= 64'd0;
            acc_acts           <= 64'd0;
            acc_beat_digest    <= 64'd0;
            acc_data_digest    <= 64'd0;
            first_beat         <= 256'd0;
            last_beat          <= 256'd0;
            have_first         <= 1'b0;
            b_resource_address <= 64'd0;
            b_region_byte      <= 64'd0;
            b_resource         <= 32'd0;
            b_physical_row     <= 32'd0;
            b_subword          <= 8'd0;
            b_bytes            <= 16'd0;
            b_byte_in_word     <= 8'd0;
            b_activate         <= 1'b0;
            r_status           <= ot_rom_pkg::ROM_STATUS_OK;
            r_fault            <= ot_rom_pkg::ROM_FAULT_NONE;
        end else begin
            cmp_valid <= 1'b0;
            if (cfg_valid && (cfg_sel == ot_rom_pkg::ROM_CFG_CLEAR)) begin
                count_requests     <= 64'd0;
                count_beats        <= 64'd0;
                count_bytes        <= 64'd0;
                count_activations  <= 64'd0;
                count_masked       <= 64'd0;
                count_faults       <= 64'd0;
                first_fault_class  <= ot_rom_pkg::ROM_FAULT_NONE;
                first_fault_object <= ot_rom_pkg::ROM_NO_ID;
                rowbuf_valid       <= 1'b0;
            end
            case (state)
            S_IDLE: begin
                if (req_valid) begin
                    r_object_id     <= req_object_id;
                    r_offset        <= req_byte_offset;
                    r_length        <= {32'd0, req_byte_length};
                    r_tag           <= req_tag;
                    lo              <= 32'd0;
                    hi              <= object_count;
                    r_status        <= ot_rom_pkg::ROM_STATUS_OK;
                    r_fault         <= ot_rom_pkg::ROM_FAULT_NONE;
                    cur             <= 64'd0;
                    beat_index      <= 64'd0;
                    acc_beats       <= 64'd0;
                    acc_bytes       <= 64'd0;
                    acc_acts        <= 64'd0;
                    acc_beat_digest <= 64'd0;
                    acc_data_digest <= 64'd0;
                    first_beat      <= 256'd0;
                    last_beat       <= 256'd0;
                    have_first      <= 1'b0;
                    s_valid         <= 1'b0;
                    validating      <= 1'b0;
                    count_requests  <= count_requests + 64'd1;
                    state           <= S_OBJ_STEP;
                end
            end
            // -- object lookup: binary search on object_id --------------
            S_OBJ_STEP: begin
                if (lo >= hi) begin
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_UNPLACED_OBJECT;
                    state    <= S_DONE;
                end else begin
                    mid       <= mid_next;
                    obj_index <= mid_next[OBJ_IDX_W-1:0];
                    state     <= S_OBJ_RD;
                end
            end
            S_OBJ_RD: state <= S_OBJ_CMP;
            S_OBJ_CMP: begin
                if (obj_rd[31:0] == r_object_id) begin
                    r_shard_first       <= obj_rd[95:64];
                    r_shard_count       <= obj_rd[127:96];
                    r_obj_region_offset <= obj_rd[191:128];
                    r_size              <= obj_rd[255:192];
                    reg_index           <= obj_rd[32 +: REG_IDX_W];
                    state               <= S_OBJ_CHECK;
                end else if (obj_rd[31:0] < r_object_id) begin
                    lo    <= mid + 32'd1;
                    state <= S_OBJ_STEP;
                end else begin
                    hi    <= mid;
                    state <= S_OBJ_STEP;
                end
            end
            S_OBJ_CHECK: begin
                if (r_length == 64'd0) begin
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_ZERO_LENGTH;
                    state    <= S_DONE;
                end else if (r_extent_end > {1'b0, r_size}) begin
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_OUT_OF_RANGE;
                    state    <= S_DONE;
                end else begin
                    region_byte  <= r_obj_region_offset + r_offset;
                    r_start_byte <= r_obj_region_offset + r_offset;
                    r_end_byte   <= r_obj_region_offset + r_offset + r_length;
                    state        <= S_MASK_WAIT;
                end
            end
            S_MASK_WAIT: begin
                if (mask_rd) begin
                    // A masked region is not an error.  Nothing is activated,
                    // nothing is sensed, no byte reaches the operand bus.
                    r_status <= ot_rom_pkg::ROM_STATUS_MASKED;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_NONE;
                    state    <= S_DONE;
                end else begin
                    lo         <= r_shard_first;
                    hi         <= r_shard_first + r_shard_count;
                    s_valid    <= 1'b0;
                    validating <= 1'b1;
                    state      <= S_SHD_STEP;
                end
            end
            // -- shard lookup: greatest region_offset <= region_byte -----
            S_SHD_STEP: begin
                if (lo >= hi) begin
                    if (!s_valid ||
                        (region_byte >= (s_region_offset + s_bytes))) begin
                        r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                        r_fault  <= ot_rom_pkg::ROM_FAULT_SHARD_GAP;
                        state    <= S_DONE;
                    end else begin
                        state     <= S_RES_RD;
                    end
                end else begin
                    mid       <= mid_next;
                    shd_index <= mid_next[SHD_IDX_W-1:0];
                    state     <= S_SHD_RD;
                end
            end
            S_SHD_RD: state <= S_SHD_CMP;
            S_SHD_CMP: begin
                if (shd_rd[191:128] <= region_byte) begin
                    s_resource         <= shd_rd[127:96];
                    s_region_offset    <= shd_rd[191:128];
                    s_bytes            <= shd_rd[255:192];
                    s_resource_address <= shd_rd[319:256];
                    s_valid            <= 1'b1;
                    lo                 <= mid + 32'd1;
                end else begin
                    hi                 <= mid;
                end
                state <= S_SHD_STEP;
            end
            S_RES_RD: state <= S_RES_WAIT;
            S_RES_WAIT: begin
                if (quarantined) begin
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_QUARANTINED;
                    state    <= S_DONE;
                end else if (validating && rep_col_hit) begin
                    // Column redundancy is activated on a resource this read
                    // reaches and this block does not implement a column
                    // redirect.  Refuse before anything is sensed.
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_COLUMN_REPAIR;
                    state    <= S_DONE;
                end else if (validating) begin
                    lo      <= r_shard_first;
                    hi      <= r_shard_first + r_shard_count;
                    s_valid <= 1'b0;
                    if ((s_region_offset + s_bytes) >= r_end_byte) begin
                        // every resource the extent reaches is in service
                        validating  <= 1'b0;
                        region_byte <= r_start_byte;
                    end else begin
                        region_byte <= s_region_offset + s_bytes;
                    end
                    state <= S_SHD_STEP;
                end else begin
                    state <= S_BEAT_ISSUE;
                end
            end
            // -- beat -----------------------------------------------------
            S_BEAT_ISSUE: begin
                if (rep_col_hit) begin
                    // Unreachable: the validation pass proved no resource this
                    // extent reaches carries an activated column repair.  Kept
                    // as a guard, because reaching it would mean the two passes
                    // disagree, and refusing is the safe way to be wrong.
                    r_status <= ot_rom_pkg::ROM_STATUS_FAULT;
                    r_fault  <= ot_rom_pkg::ROM_FAULT_COLUMN_REPAIR;
                    state    <= S_DONE;
                end else begin
                    b_region_byte      <= region_byte;
                    b_resource_address <= g_resource_address;
                    b_resource         <= s_resource;
                    b_bytes            <= g_take[15:0];
                    b_byte_in_word     <= g_resource_address[7:0]
                                          % SENSE_BYTES_8;
                    b_subword          <= c_subword;
                    b_physical_row     <= c_physical_row;
                    b_activate         <= c_activate;
                    sense_req_valid    <= 1'b1;
                    sense_resource     <= s_resource;
                    sense_row          <= c_physical_row;
                    sense_subword      <= c_subword;
                    sense_activate     <= c_activate;
                    state              <= S_BEAT_WAIT;
                end
            end
            S_BEAT_WAIT: begin
                if (sense_req_valid && sense_req_ready)
                    sense_req_valid <= 1'b0;
                if (sense_rsp_valid) begin
                    out_valid       <= 1'b1;
                    out_data        <= aligned;
                    out_bytes       <= b_bytes;
                    out_tag         <= r_tag;
                    out_last        <= ((cur + {48'd0, b_bytes}) >= r_length);
                    rowbuf_valid    <= 1'b1;
                    rowbuf_resource <= b_resource;
                    rowbuf_row      <= b_physical_row;
                    state           <= S_BEAT_PUSH;
                end
            end
            S_BEAT_PUSH: begin
                if (out_valid && out_ready) begin
                    out_valid <= 1'b0;
                    acc_beat_digest <= next_beat_digest;
                    acc_data_digest <= next_data_digest;
                    if (!have_first) begin
                        first_beat <= beat_record;
                        have_first <= 1'b1;
                    end
                    last_beat   <= beat_record;
                    acc_beats   <= acc_beats + 64'd1;
                    acc_bytes   <= acc_bytes + {48'd0, b_bytes};
                    if (b_activate) acc_acts <= acc_acts + 64'd1;
                    beat_index  <= beat_index + 64'd1;
                    cur         <= cur + {48'd0, b_bytes};
                    region_byte <= region_byte + {48'd0, b_bytes};
                    if ((cur + {48'd0, b_bytes}) >= r_length) begin
                        state <= S_DONE;
                    end else if (((region_byte + {48'd0, b_bytes})
                                  - s_region_offset) >= s_bytes) begin
                        // the next byte lives on the next placement resource
                        lo      <= r_shard_first;
                        hi      <= r_shard_first + r_shard_count;
                        s_valid <= 1'b0;
                        state   <= S_SHD_STEP;
                    end else begin
                        state <= S_BEAT_ISSUE;
                    end
                end
            end
            S_DONE: begin
                cmp_valid       <= 1'b1;
                cmp_tag         <= r_tag;
                cmp_status      <= r_status;
                cmp_fault       <= r_fault;
                cmp_beats       <= acc_beats;
                cmp_bytes       <= acc_bytes;
                cmp_activations <= acc_acts;
                cmp_beat_digest <= acc_beat_digest;
                cmp_data_digest <= acc_data_digest;
                cmp_first_beat  <= first_beat;
                cmp_last_beat   <= last_beat;
                count_beats       <= count_beats + acc_beats;
                count_bytes       <= count_bytes + acc_bytes;
                count_activations <= count_activations + acc_acts;
                if (r_status == ot_rom_pkg::ROM_STATUS_MASKED)
                    count_masked <= count_masked + 64'd1;
                if (r_status == ot_rom_pkg::ROM_STATUS_FAULT) begin
                    count_faults <= count_faults + 64'd1;
                    if (first_fault_class == ot_rom_pkg::ROM_FAULT_NONE) begin
                        first_fault_class  <= r_fault;
                        first_fault_object <= r_object_id;
                    end
                end
                state <= S_IDLE;
            end
            default: state <= S_IDLE;
            endcase
        end
    end
endmodule
