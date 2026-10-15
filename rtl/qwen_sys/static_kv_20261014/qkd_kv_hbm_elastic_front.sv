`timescale 1ns/1ps
// HANDOFF 0az HBM-backed KV boundary: elastic block-ready front buffer.
//
// The HBM stack/PHY return time is NOT compile-time fixed. Corrected KV read
// sectors (controller co[0] = actual ECC landing valid, in reservation order:
// the controller tag queue and landing ECC are in-order) land here WHENEVER
// they arrive, at the next entry of an NBLK x BLK staging ring. A block is
// READY once all BLK of its sectors have landed. This is the only place the
// variable HBM latency is absorbed.
//
// Inside the die everything is compiler fixed-slot from "buffer block ready":
// the compiler prefetches each block (issues its RD reservations) ahead and
// places a release slot blk_go (pll_hbm domain) no earlier than the block's
// nominal corrected landing + the PHY latency window. At blk_go the front
// checks ONE ready for that block and re-emits its BLK sectors on fixed edges
// (first put 2 edges after blk_go, then one every STRIDE edges) as a
// controller-format co word + compiled_hbm_put strobe, which drive the fixed
// dual-clock return ring (qkd_static_kv_return_slots) unchanged.
//
// Flow control kept at the boundary (owner 0az), one event per block:
//  - blk_freed: one pulse per block after its last sector is re-emitted; the
//    RD reservation issuer may prefetch block b+NBLK only after block b's
//    pulse (block-granular request credit toward the HBM stack, not per lane).
//  - hold: blk_go is pending but its block has not fully landed (PHY late
//    beyond the compiled window). Release waits for ready (data is never
//    dropped), stall_edges counts it, and hold is the explicit exceptional
//    signal to the sequencer (the internal programme pauses at block
//    granularity, like CRC retry). A valid production programme shows zero.
//  - fault_overflow: a sector landed while the ring was full (issuer broke the
//    block credit). fault_go: more blk_go pending than blocks exist.
// Storage: NBLK*BLK entries x 297 b {epoch16, co[281:1]}. co[293:282]
// (write completion/hand fields, not part of the read return) pass through.
module qkd_kv_hbm_elastic_front #(
    parameter integer NBLK = 2,
    parameter integer BLK = 8,
    parameter integer STRIDE = 1,
    parameter integer MUT = 0   // 1: read address +1, 2: ready one sector early, 3: release ignores ready
)(
    input wire pll_hbm, hrst,
    input wire [293:0] co_in,
    input wire [15:0] epoch_in,
    input wire blk_go,
    output wire [293:0] co_out,
    output wire [15:0] epoch_out,
    output wire compiled_hbm_put,
    output reg blk_freed,
    output reg hold,
    output reg [15:0] stall_edges,
    output wire [$clog2(NBLK*BLK):0] occupancy,
    output reg fault_overflow, fault_go
);
    localparam integer DEPTH = NBLK * BLK;
    localparam integer AW = $clog2(DEPTH);
    localparam integer BW = $clog2(BLK);
    localparam integer SW = (STRIDE > 1) ? $clog2(STRIDE) : 1;
    localparam integer PW = $clog2(NBLK + 1) + 1;
    initial if (NBLK < 2 || (NBLK & (NBLK-1)) != 0 || BLK < 2 || (BLK & (BLK-1)) != 0 || STRIDE < 1)
        $error("elastic front: NBLK>=2 and BLK>=2 powers of two, STRIDE>=1");

    (* keep *) reg hr;
    always @(posedge pll_hbm) hr <= hrst;

    // ---- landing side: actual arrival, in order --------------------------------------------------------------
    (* keep *) reg land_v;
    (* keep *) reg [296:0] land_d;
    always @(posedge pll_hbm or negedge hr)
        if (!hr) land_v <= 1'b0; else land_v <= co_in[0];
    always @(posedge pll_hbm) land_d <= {epoch_in, co_in[281:1]};
    reg [296:0] mem [0:DEPTH-1];
    reg [AW:0] wp, rp, bs;          // write, emit read, next block start (entries, wrap bit)
    wire [AW:0] filled = wp - bs;   // landed entries of the next block to release and beyond
    wire ready = (MUT == 3) ? 1'b1 : (MUT == 2) ? (filled >= (AW+1)'(BLK-1)) : (filled >= (AW+1)'(BLK));
    assign occupancy = wp - rp;
    always @(posedge pll_hbm) if (land_v) mem[wp[AW-1:0]] <= land_d;

    // ---- release side: compiled blk_go, one ready check per block --------------------------------------------
    reg [PW-1:0] pending;
    reg emitting;
    reg [BW-1:0] cnt;
    reg [SW-1:0] sc;
    wire start = pending != 0 && !emitting && ready;
    wire last = emitting && sc == SW'(STRIDE-1) && cnt == BW'(BLK-1);
    wire take = emitting && sc == SW'(STRIDE-1);
    reg put_q;
    reg [296:0] out_q;
    wire [AW-1:0] ra = (MUT == 1) ? rp[AW-1:0] + 1'b1 : rp[AW-1:0];
    always @(posedge pll_hbm or negedge hr)
        if (!hr) begin
            wp <= 0; rp <= 0; bs <= 0; pending <= 0; emitting <= 0; cnt <= 0; sc <= 0;
            put_q <= 0; blk_freed <= 0; hold <= 0; stall_edges <= 0; fault_overflow <= 0; fault_go <= 0;
        end else begin
            put_q <= 0; blk_freed <= 0;
            if (land_v) begin
                wp <= wp + 1'b1;
                if (wp - rp == (AW+1)'(DEPTH)) fault_overflow <= 1'b1;
            end
            pending <= pending + PW'(blk_go) - PW'(start);
            if (blk_go && pending == PW'(NBLK)) fault_go <= 1'b1;
            hold <= pending != 0 && !emitting && !ready;
            if (pending != 0 && !emitting && !ready && stall_edges != 16'hffff) stall_edges <= stall_edges + 1'b1;
            if (start) begin emitting <= 1'b1; cnt <= 0; sc <= SW'(STRIDE-1); bs <= bs + (AW+1)'(BLK); end
            if (emitting) begin
                sc <= (sc == SW'(STRIDE-1)) ? SW'(0) : sc + 1'b1;
                if (take) begin
                    put_q <= 1'b1; rp <= rp + 1'b1; cnt <= cnt + 1'b1;
                    if (last) begin emitting <= 1'b0; blk_freed <= 1'b1; end
                end
            end
        end
    always @(posedge pll_hbm) if (take) out_q <= mem[ra];

    // ---- controller-format output (drives qkd_static_kv_return_slots) ----------------------------------------
    // Pass-through fields are re-timed by the same two edges as the release word.
    reg [11:0] pass_q, pass_q2;
    always @(posedge pll_hbm) begin pass_q <= co_in[293:282]; pass_q2 <= pass_q; end
    assign co_out = {pass_q2, out_q[280:0], put_q};
    assign epoch_out = out_q[296:281];
    assign compiled_hbm_put = put_q;
endmodule
