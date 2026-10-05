`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// THE OBJECT PLACEMENT TABLE.  One object -> one base, held in memory and
// INDEXED, read through a registered port.
//
// WHAT THIS REPLACES.  The engine issue bridge used to carry the whole table
// as 64 top-level configuration ports (``cfg_place_object_0..31`` /
// ``cfg_place_base_0..31``) and resolve an object with a function that
// compared it against all 32 entries COMBINATIONALLY.  That is two walls at
// once, and both were measured before this module was written:
//
//   CAPACITY.  Qwen3-reduced references exactly 32 distinct placed objects,
//   which is why it works.  DeepSeek-V4.1-Flash ROM references 675 and
//   DeepSeek-V4-Flash ROM 264.  Walking the V4.1 wafer program in order, the
//   32 slots are exhausted at PC 55 of 4,343 -- 1.3% -- on a VECTOR.RMS_NORM
//   that needs objects 22 and 1237 with 32 already bound.
//
//   TIMING.  A 32-way combinational compare sits in front of every operand
//   address.  At 675 entries it would be a 675-way one.  This repository has
//   been bitten three times by that shape.
//
// WHY A HASH AND NOT A DIRECT MAP.  An object id is sparse and large: the
// V4.1 wafer deployment's 675 objects carry ids 1..9,442, so a table indexed
// directly by object id needs 9,443 entries to hold 675 of them -- 7.1%
// occupancy -- and its size tracks the id space rather than the model.  A
// compact open-addressed table indexed by a hash of the id holds the same 675
// in 2,048 entries at 33.0% load, 4.6x smaller, and its size tracks the
// object count.  The cost of compaction is that a lookup may probe: measured
// over the real id sets, with the xor-fold hash below,
//
//   deepseek-v41-flash-rom-wafer-2  675 objects / 2,048 entries  worst 6, mean 1.05
//   deepseek-v41-flash-rom-array-64 678 objects / 2,048 entries  worst 4, mean 1.05
//   deepseek-v4-flash-rom           264 objects / 2,048 entries  worst 1, mean 1.00
//   qwen3-reduced-rom                32 objects /    64 entries  worst 5, mean 1.28
//
// and the RTL reproduces those exactly: 675 of the wafer deployment's own ids
// loaded into a 2,048-entry instance read back in 13 cycles worst and 3.11
// mean, which at three cycles for a probe-0 hit and two per further probe is
// worst 6 and mean 1.055 probes.  So a lookup is one memory probe in the
// overwhelming majority of cases and the tail is small.
//
// WHY ENTRIES DEFAULTS TO 64 AND NOT 32.  The legacy port surface binds at
// most 32 objects, and 32 of them in 32 entries is a 100%-loaded open-
// addressed table: measured over Qwen3-reduced's own ids, the worst probe is
// 21 and the mean 3.62.  At 64 entries the same 32 ids probe 5 in the worst
// case and 1.28 on average.  The default therefore admits exactly the set the
// 32 ports could express, and no other elaboration has to say anything.
//
// WHAT IT COSTS, post-route through the pinned ASAP7 flow at a 1.2 ns target,
// against ot_a3_place_scan_ref -- the combinational scan this replaces,
// extracted verbatim from the bridge at the commit before this change, with
// the same registered query and answer, the same flow and the same target:
//
//                       cells   cell area   post-route Fmax   WNS    headroom
//   32-way scan        23,675   3,133 um2    1,125.19 MHz   0.311 ns   0.259
//   this table (64)    17,428   2,656 um2    1,123.31 MHz   0.310 ns   0.258
//
// both DRC-clean and antenna-clean with no slew, fan-out or capacitance
// violations; routed wirelength 175,725 um against 343,658.  The registered
// lookup costs 0.17% of frequency and 26% fewer cells.  Note that PRE-LAYOUT
// STA says something very different -- 506.54 MHz against 1,058.00 -- because
// the entry array's write control is one x1 gate with 513 loads carrying 58%
// of an unbuffered path, which is exactly what repair_design exists to fix and
// exactly why a fan-out-limited block must be measured after routing.
//
// AT 2,048 ENTRIES THE ARRAY MUST BE A MACRO.  Synthesised as inferred flops
// the same subsystem is 510,588 cells and 75,525 um2, of which 38,287 um2 is
// 131,365 flops; 2,048 x 64 bits is 16 KiB, which is eight fakeram_256x64
// parts at 687.971 um2 each -- 5,504 um2, 13.7x less -- and the port contract
// below is written to be exactly theirs so the swap is a netlist change and
// not a logic change.
//
// THE PROBE BOUND IS THE WHOLE TABLE, so a binding is never refused while a
// free slot exists and a present key is never missed: linear probing from the
// hash visits every entry, and the walk stops early at the first empty one,
// which is sound because nothing is ever deleted.  An insertion that finds no
// free slot sets ``overflowed``; an insertion that finds its own key already
// present sets ``bound_twice``.  Both are sticky, and the bridge turns either
// into the DESCRIPTOR trap it already returned for a table that named an
// object twice -- the refusal moved from an O(N^2) combinational comparison
// (1,024 comparators at 32 entries, 4 million at 2,048) to the one insertion
// path every binding must pass through.
//
// THE MEMORY is a single-port synchronous RAM written or read on one address
// per cycle, which is exactly the operation the ASAP7 FakeRAM parts in
// rtl/abi3/ot_a3_asap7_fakeram_blackbox.sv state in their liberty:
//
//     always @(posedge clk) if (ce) begin
//         if (we) mem[addr] <= wd;   // rd holds
//         else    rd        <= mem[addr];
//     end
//
// so a 64-bit-wide instance of this table can be swapped for
// ``fakeram_256x64`` parts without changing a line of the logic below.
//
// THERE IS ONE WAY IN.  Both the legacy 32-port surface and the host load
// path reach the entries through ``ld_*`` -- the same hash, the same probe,
// the same uniqueness detection.  Nothing bypasses it, so two surfaces cannot
// disagree about where an object lives.
// ---------------------------------------------------------------------------
module ot_a3_place_table #(
    // Entries the table holds.  MUST be a power of two: the hash folds to
    // ``log2(ENTRIES)`` bits and the probe wraps modulo the table.
    parameter integer ENTRIES = 64
) (
    input  wire          clk,
    input  wire          rst_n,

    // -- flush: empty every entry and clear the sticky refusals ----------
    // Asserted for one cycle.  While the flush runs nothing is accepted and
    // no lookup completes.
    input  wire          flush,
    output wire          flushing,

    // -- load port: ONE object -> base binding, hashed and probed in -----
    // Accepted on the cycle ``ld_en && ld_ready``.  ``ld_object == NO_ID`` is
    // the empty binding and is accepted and discarded, so a caller walking a
    // sparse surface needs no filter of its own.
    input  wire          ld_en,
    input  wire [31:0]   ld_object,
    input  wire [31:0]   ld_base,
    output wire          ld_ready,

    // -- sticky refusals -------------------------------------------------
    output reg           bound_twice,
    output reg           overflowed,
    output wire [31:0]   bound_count,

    // -- registered lookup port ------------------------------------------
    // ``lk_req`` is a one-cycle request; ``lk_done`` is a one-cycle reply,
    // never in the same cycle.  A request offered while the table is busy is
    // held and served, so the caller never has to know what else is going on.
    input  wire          lk_req,
    input  wire [31:0]   lk_object,
    output reg           lk_done,
    output reg           lk_found,
    output reg  [31:0]   lk_base
);
    localparam [31:0] NO_ID = 32'hffff_ffff;

    // Address width is derived from the entry count, never fixed: a register
    // wide enough for 64 entries silently truncates a 2,048-entry table's
    // probe and resolves the wrong object.
    localparam integer AW = (ENTRIES <= 2) ? 1 : $clog2(ENTRIES);

    // THE HASH IS TWO LEVELS OF XOR, and that is a measured choice.  The
    // obvious one -- Knuth's multiplicative hash, ``(id * 2654435761) >> (32 -
    // AW)`` -- mixes slightly better (worst probe 4 rather than 6 over the
    // V4.1 wafer deployment's 675 ids at 2,048 entries) and puts a 32-bit
    // constant multiplier between the key register and the memory address.
    // Measured through the pinned ASAP7 flow, that multiplier cost this block
    // more than half its frequency: 499.32 MHz pre-layout with the multiply
    // against 1,058.00 MHz for the combinational scan it replaces.  Folding
    // the id onto itself instead costs two XOR levels, and the probe lengths
    // it produces over the real id sets are:
    //
    //   deepseek-v41-flash-rom-wafer-2  675 / 2,048  worst 6, mean 1.05
    //   deepseek-v41-flash-rom-array-64 678 / 2,048  worst 4, mean 1.05
    //   deepseek-v4-flash-rom           264 / 2,048  worst 1, mean 1.00
    //   qwen3-reduced-rom                32 /    64  worst 5, mean 1.28
    //
    // The shifts are 10 and 20 because an object id is a small dense integer
    // in these deployments (1..9,442 for the wafer one, 1..217 for Qwen3), so
    // the bits that vary sit low and folding the whole 32-bit word down onto
    // the index width is what spreads them.  A pure ``id mod ENTRIES`` was
    // measured too and is worse on the same sets (worst 12 rather than 6).
    // Constants sized from the table, not from a convenient literal.
    localparam [AW-1:0] ONE_A     = {{(AW-1){1'b0}}, 1'b1};
    localparam [AW:0]   ONE_S     = {{AW{1'b0}}, 1'b1};
    /* verilator lint_off WIDTHTRUNC */
    localparam [AW:0]   LAST_ADDR = ENTRIES - 1;
    /* verilator lint_on WIDTHTRUNC */
    localparam integer   COUNT_PAD = 32 - (AW + 1);
    function automatic [AW-1:0] hash_of;
        input [31:0] object_id;
        /* verilator lint_off UNUSEDSIGNAL */
        reg [31:0] mixed;   // only the low AW bits of the fold index the table
        /* verilator lint_on UNUSEDSIGNAL */
        begin
            mixed = object_id ^ (object_id >> 10) ^ (object_id >> 20);
            hash_of = mixed[AW-1:0];
        end
    endfunction

    // -- the memory ------------------------------------------------------
    // {object[63:32], base[31:0]}.  One port: one address per cycle, either
    // written or read, with the read landing in ``entry_q`` the cycle after.
    reg [63:0] entry [0:ENTRIES-1];
    reg [63:0] entry_q;

    // The port controls are COMBINATIONAL, so a read issued in T_ISSUE lands
    // in ``entry_q`` for T_ISSUE's successor to compare.  Registering them
    // instead costs a whole extra state per probe and, written that way once,
    // made T_CMP compare the PREVIOUS probe's entry.
    reg          mem_en;
    reg          mem_we;
    reg [AW-1:0] mem_addr;
    reg [63:0]   mem_wdata;

    always @(posedge clk) begin
        if (mem_en) begin
            if (mem_we) entry[mem_addr] <= mem_wdata;
            else        entry_q         <= entry[mem_addr];
        end
    end

    localparam [2:0] T_FLUSH = 3'd0;
    localparam [2:0] T_IDLE  = 3'd1;
    localparam [2:0] T_ISSUE = 3'd2;
    localparam [2:0] T_CMP   = 3'd3;

    reg [2:0]    tstate;
    reg [AW-1:0] addr;
    reg [AW-1:0] probe;
    reg [AW:0]   sweep;        // one bit wider than an address: it counts TO ENTRIES
    reg [31:0]   key;
    reg [31:0]   val;
    reg          op_insert;
    reg [AW:0]   filled;       // 0..ENTRIES, so AW+1 bits and not AW
    reg          lk_pending;
    reg [31:0]   lk_key;

    assign flushing   = (tstate == T_FLUSH);
    assign ld_ready   = (tstate == T_IDLE);
    assign bound_count = {{COUNT_PAD{1'b0}}, filled};

    wire [31:0] entry_object = entry_q[63:32];
    wire [31:0] entry_base   = entry_q[31:0];
    wire        entry_hit    = (entry_object == key);
    wire        entry_empty  = (entry_object == NO_ID);
    wire        probe_last   = (probe == {AW{1'b1}});

    // One address per cycle, either written or read -- never both.
    always @* begin
        mem_en    = 1'b0;
        mem_we    = 1'b0;
        mem_addr  = addr;
        mem_wdata = {key, val};
        case (tstate)
            T_FLUSH: begin
                mem_en    = 1'b1;
                mem_we    = 1'b1;
                mem_addr  = sweep[AW-1:0];
                mem_wdata = {NO_ID, 32'd0};
            end
            T_ISSUE: begin
                mem_en = 1'b1;
                mem_we = 1'b0;
            end
            T_CMP: begin
                // the one write a probe walk performs: the binding lands in
                // the first empty entry the walk reaches
                if (op_insert && !entry_hit && entry_empty) begin
                    mem_en = 1'b1;
                    mem_we = 1'b1;
                end
            end
            default: ;
        endcase
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tstate <= T_FLUSH;
            addr <= {AW{1'b0}};
            probe <= {AW{1'b0}};
            sweep <= {(AW+1){1'b0}};
            key <= NO_ID;
            val <= 32'd0;
            op_insert <= 1'b0;
            filled <= {(AW+1){1'b0}};
            bound_twice <= 1'b0;
            overflowed <= 1'b0;
            lk_pending <= 1'b0;
            lk_key <= NO_ID;
            lk_done <= 1'b0;
            lk_found <= 1'b0;
            lk_base <= 32'd0;
        end else begin
            lk_done <= 1'b0;

            // A lookup offered at any time is remembered.  It is not answered
            // out of order: one probe walk runs at a time.
            if (lk_req) begin
                lk_pending <= 1'b1;
                lk_key <= lk_object;
            end

            if (flush && (tstate != T_FLUSH)) begin
                tstate <= T_FLUSH;
                sweep <= {(AW+1){1'b0}};
                filled <= {(AW+1){1'b0}};
                bound_twice <= 1'b0;
                overflowed <= 1'b0;
            end else begin
                case (tstate)
                    T_FLUSH: begin
                        sweep <= sweep + ONE_S;
                        if (sweep == LAST_ADDR)
                            tstate <= T_IDLE;
                    end

                    T_IDLE: begin
                        // A load wins over a pending lookup.  They never
                        // overlap in a real run -- bindings are loaded before
                        // the transaction starts -- and giving the load
                        // priority means a seed always completes.
                        if (ld_en) begin
                            if (ld_object == NO_ID) begin
                                // the empty binding: accepted, nothing stored
                            end else begin
                                op_insert <= 1'b1;
                                key <= ld_object;
                                val <= ld_base;
                                addr <= hash_of(ld_object);
                                probe <= {AW{1'b0}};
                                tstate <= T_ISSUE;
                            end
                        end else if (lk_pending) begin
                            lk_pending <= 1'b0;
                            if (lk_key == NO_ID) begin
                                // NO_ID names no object and must never match
                                // the empty-entry marker.
                                lk_done <= 1'b1;
                                lk_found <= 1'b0;
                                lk_base <= 32'd0;
                            end else begin
                                op_insert <= 1'b0;
                                key <= lk_key;
                                addr <= hash_of(lk_key);
                                probe <= {AW{1'b0}};
                                tstate <= T_ISSUE;
                            end
                        end
                    end

                    T_ISSUE: tstate <= T_CMP;

                    T_CMP: begin
                        if (op_insert) begin
                            if (entry_hit) begin
                                // This object already has a base.  Two
                                // entries cannot disagree about where one
                                // object lives, so the table is refused.
                                bound_twice <= 1'b1;
                                tstate <= T_IDLE;
                            end else if (entry_empty) begin
                                filled <= filled + ONE_S;
                                tstate <= T_IDLE;
                            end else if (probe_last) begin
                                overflowed <= 1'b1;
                                tstate <= T_IDLE;
                            end else begin
                                addr <= addr + ONE_A;
                                probe <= probe + ONE_A;
                                tstate <= T_ISSUE;
                            end
                        end else begin
                            if (entry_hit) begin
                                lk_done <= 1'b1;
                                lk_found <= 1'b1;
                                lk_base <= entry_base;
                                tstate <= T_IDLE;
                            end else if (entry_empty || probe_last) begin
                                // An empty entry ends the walk: nothing is
                                // ever deleted, so a key past one was never
                                // inserted.  An object the table does not name
                                // is NOT a guess -- the caller traps.
                                lk_done <= 1'b1;
                                lk_found <= 1'b0;
                                lk_base <= 32'd0;
                                tstate <= T_IDLE;
                            end else begin
                                addr <= addr + ONE_A;
                                probe <= probe + ONE_A;
                                tstate <= T_ISSUE;
                            end
                        end
                    end

                    default: tstate <= T_IDLE;
                endcase
            end
        end
    end

`ifndef YOSYS
    initial begin
        if ((ENTRIES < 2) || ((ENTRIES & (ENTRIES - 1)) != 0))
            $fatal(1, "ot_a3_place_table: ENTRIES=%0d is not a power of two >= 2",
                   ENTRIES);
    end
`endif
endmodule
