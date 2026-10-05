`timescale 1ps/1fs
// ---------------------------------------------------------------------------
// Qwen3-8B HBM accelerator, DSpark verify: MULTI-POSITION WEIGHT REUSE window release (default-off).
//
// The p-position verify program (tools/qwen_rom_verify_program_w12.py) issues every dense matvec p times back
// to back; the spine reads the op's HBM code words in increasing stream order in every pass.  A window slot
// may be returned to the stream only after its LAST use, so the consumed count C advances only on reads of
// the p-th pass.  The pass is tracked, not stored per slot:
//   * a read at or beyond HI (the furthest word read so far, + 1) is pass 1 of a new op;
//   * a read below the previous read's index starts the next pass of the same op;
//   * a read is a last use when its pass == nuse (nuse = p; nuse = 1 reproduces the HA8 release).
// C (less LAGW words in flight to the tiles) returns Gray-coded to the HBM controller domain as
// ot_hbmacc_qwen_wstream expects.  rel_fault (sticky) flags a read below C (a released word), or a new op
// started before the previous op's p-th pass (the program contract broken).
//
// Screens: per-slot 3-bit counters with a 1,024-entry read-modify-write: 650 MHz SS r2r; a 32-bit pass
// counter with the C update in the same stage: 803 MHz.  This version: IW-bit (16) indices, the pass loop
// alone in stage 2, the C / Gray update in stage 3 and a registered C for the fault compare, so C trails
// the zero-latency simulation model by 4 core cycles (well under one stream word, ~30 cycles; inside LAGW).
// ENABLE = 0 ties every output to zero.
// ---------------------------------------------------------------------------
module ot_hbmacc_win_usecount #(
    parameter integer ENABLE = 0,
    parameter integer LAGW   = 40,
    parameter integer CW     = 32,
    parameter integer IW     = 16       // stream-index bits tracked (a token streams < 2^IW words a die)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rd_v,           // an HBM code-word read by the spine (engine edge)
    input  wire [CW-1:0] rd_idx,         // its stream index
    input  wire [3:0]    nuse,           // passes per op (verify positions p)
    output reg  [CW-1:0] c_gray,         // consumed words, Gray (to the HBM domain)
    output reg           rel_fault
);
    generate if (ENABLE == 0) begin : g_off
        always @(posedge clk) begin c_gray <= 0; rel_fault <= 1'b0; end
    end else begin : g_on
        // stage 1: register the read (the index narrowed to IW bits: a token's stream is < 2^IW words)
        reg          r1_v;
        reg [IW-1:0] r1_idx;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r1_v <= 1'b0; r1_idx <= 0; end
            else begin r1_v <= rd_v; r1_idx <= rd_idx[IW-1:0]; end
        // stage 2: pass tracking (the only loop: two IW-bit compares and a 4-bit counter)
        reg  [IW-1:0] hi, last_idx, r2_idx1;
        reg  [3:0]    pass;
        reg           r2_last, r2_v, r2_newop_bad;
        wire          fresh = (r1_idx >= hi);                 // beyond every word read so far: a new op
        wire          back  = (r1_idx < last_idx);            // restart of the op: next pass
        wire [3:0]    pass_n = fresh ? 4'd1 : back ? pass + 4'd1 : pass;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                hi <= 0; last_idx <= 0; pass <= 4'd1; r2_last <= 1'b0; r2_v <= 1'b0; r2_idx1 <= 0; r2_newop_bad <= 1'b0;
            end else begin
                r2_v <= r1_v;
                r2_last <= r1_v && (pass_n >= nuse);
                r2_newop_bad <= r1_v && fresh && pass > 4'd1 && pass < nuse;
                r2_idx1 <= r1_idx + 1'b1;
                if (r1_v) begin
                    pass <= pass_n;
                    last_idx <= r1_idx;
                    if (fresh) hi <= r1_idx + 1'b1;
                end
            end
        // stage 3: release count (the last pass reads increasing indices, so the last use sets C), Gray, fault
        reg  [IW-1:0] cmax, c_rel;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cmax <= 0; c_rel <= 0; c_gray <= 0; rel_fault <= 1'b0; end
            else begin
                if (r2_last) cmax <= r2_idx1;
                c_rel  <= (cmax > IW'(LAGW)) ? cmax - IW'(LAGW) : 0;
                c_gray <= CW'(c_rel) ^ (CW'(c_rel) >> 1);
                if ((r1_v && r1_idx < c_rel) || r2_newop_bad || (r2_last && r2_idx1 <= cmax)) rel_fault <= 1'b1;
            end
    end endgenerate
endmodule
