`timescale 1ps/1fs
// ---------------------------------------------------------------------------
// Qwen3-8B HBM accelerator, DSpark verify: MULTI-POSITION WEIGHT REUSE window release (default-off).
//
// The p-position verify program issues every dense matvec p times back to back, so each HBM code word is
// read p times from the prefetch window.  A window slot may be returned to the stream only after its LAST
// use.  This block counts reads per slot (3-bit counter, slot = stream index mod NSLOT) and advances the
// consumed count C on the nuse-th read of a word; C (less LAGW words in flight to the tiles) is returned
// Gray-coded to the HBM controller domain exactly as ot_hbmacc_qwen_wstream expects.  A read of a word
// already released raises rel_fault (sticky).  nuse = 1 reproduces the HA8 release (C = furthest read + 1).
//
// Timing: the read port is registered (rd stage), the slot read-modify-write and the C update are one
// stage each, so C trails the simulation model (rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12_vp.sv,
// zero-latency) by 2 core cycles -- far below one stream word (~30 cycles) and inside the LAGW lag.
// ENABLE = 0 ties every output to zero.
// ---------------------------------------------------------------------------
module ot_hbmacc_win_usecount #(
    parameter integer ENABLE = 0,
    parameter integer NSLOT  = 1024,     // window slots (>= WINW), a power of two
    parameter integer LAGW   = 40,
    parameter integer CW     = 32
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rd_v,           // an HBM code-word read by the spine (engine edge)
    input  wire [CW-1:0] rd_idx,         // its stream index
    input  wire [3:0]    nuse,           // reads per word before release (verify positions p)
    output reg  [CW-1:0] c_gray,         // consumed words, Gray (to the HBM domain)
    output reg           rel_fault
);
    localparam integer SB = $clog2(NSLOT);
    generate if (ENABLE == 0) begin : g_off
        always @(posedge clk) begin c_gray <= 0; rel_fault <= 1'b0; end
    end else begin : g_on
        // stage 1: register the read
        reg          r1_v;
        reg [CW-1:0] r1_idx;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin r1_v <= 1'b0; r1_idx <= 0; end
            else begin r1_v <= rd_v; r1_idx <= rd_idx; end
        // stage 2: slot read-modify-write, last-use decision
        reg [2:0]    uses [0:NSLOT-1];
        reg          r2_last;
        reg [CW-1:0] r2_idx;
        wire [2:0]   u_now = uses[r1_idx[SB-1:0]];
        wire         last  = (4'(u_now) + 4'd1 >= nuse);
        integer k;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin
                for (k = 0; k < NSLOT; k = k + 1) uses[k] <= 3'd0;
                r2_last <= 1'b0; r2_idx <= 0;
            end else begin
                if (r1_v) uses[r1_idx[SB-1:0]] <= last ? 3'd0 : u_now + 3'd1;
                r2_last <= r1_v && last;
                r2_idx  <= r1_idx;
            end
        // stage 3: furthest last-used word, released count, Gray, fault
        reg  [CW-1:0] cmax;
        wire [CW-1:0] c_bin = (cmax > CW'(LAGW)) ? cmax - CW'(LAGW) : 0;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin cmax <= 0; c_gray <= 0; rel_fault <= 1'b0; end
            else begin
                if (r2_last && r2_idx + 1 > cmax) cmax <= r2_idx + 1;
                c_gray <= c_bin ^ (c_bin >> 1);
                if (r1_v && r1_idx < c_bin) rel_fault <= 1'b1;
            end
    end endgenerate
endmodule
