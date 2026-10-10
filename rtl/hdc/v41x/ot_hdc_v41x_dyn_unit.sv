// ot_hdc_v41x_dyn_unit: the v41x core sequencer's DYN table (capture at S_DYN + the decode read selectors), moved
// out of ot_hdc_core_v41x VERBATIM (mtp-lead 2026-10-09) so the ring-8 DYN25/26 repair (ROLLBACK_RING_DYN, V36) has a
// routable physical vehicle.  Behaviour and cycles are unchanged: the capture is the same always block on the same
// enable; each read port is the same combinational array read dyn[slot * NDYN + idx] the core's `DY macro made.
// Read ports (core order): 0 ME_D_NOUT 1 ME_D_TILES 2 ME_D_K 3 ME_D_WBASE 4 SU_D_NOUT 5 SU_D_NIN 6 XU_D_N 7 XU_D_K
// 8 ME_D_XBASE 9 ME_D_OBASE 10 A_D 11 B_D 12 C_D 13 D_D 14 O_D 15 QE_D_OBASE 16 rope prefetch position (idx 4).
module ot_hdc_v41x_dyn_unit #(
    parameter integer FULL_SHAPE = 0,
    parameter integer W    = 16,
    parameter integer G    = 4,
    parameter integer AW   = FULL_SHAPE ? 30 : 24,
    parameter integer NW   = FULL_SHAPE ? 21 : 16,
    parameter integer DIM  = FULL_SHAPE ? 5120 : 160,
    parameter integer TOPK = FULL_SHAPE ? 512 : 16,
    parameter integer HDIM = FULL_SHAPE ? 512 : 32,
    parameter integer ROPE_PAIR = FULL_SHAPE ? 32 : 2,
    parameter integer FULL_WINDOW = 128,
    parameter integer FULL_SCAN_CAP = 16384,
    parameter integer FULL_TP = 4,
    parameter integer NSLOT = 1,
    parameter integer ROLLBACK_RING_DYN = 1,
    parameter integer NRD = 17,
    parameter integer RIW = 8
) (
    input  wire              clk,
    input  wire              cap,          // st == S_DYN
    input  wire [2:0]        ds,           // DYN bank being computed
    input  wire [NW-1:0]     b_tok,
    input  wire [NW-1:0]     b_pos,
    input  wire [NRD*3-1:0]  rd_slot,
    input  wire [NRD*RIW-1:0] rd_idx,
    output wire [NRD*AW-1:0] rd_val
);
    `include "ot_hdc_isa_v41_profiles.svh"
    localparam integer LG = $clog2(W * G);
    localparam integer NDYN = FULL_SHAPE ? 64 : 32;
    reg [AW-1:0] dyn [0:NSLOT*NDYN-1];
    genvar gr;
    generate for (gr = 0; gr < NRD; gr = gr + 1) begin : g_rd
        assign rd_val[gr * AW +: AW] = dyn[rd_slot[gr * 3 +: 3] * NDYN + rd_idx[gr * RIW +: RIW]];
    end endgenerate

    wire [NW-1:0] p1 = b_pos + 1'b1;
    wire [NW-1:0] n2 = p1 >> 1;
    wire [NW-1:0] ns1 = (p1 < TOPK) ? p1 : TOPK;
    wire [NW-1:0] ns2 = (n2 < TOPK) ? n2 : TOPK;
    function automatic [AW-1:0] rnds(input [NW-1:0] x);
        rnds = (x == 0) ? 0 : ((x - 1) >> LG) + 1;
    endfunction
    function automatic [AW-1:0] rnd16(input [NW-1:0] x);      // 16-row tiles: head-group KV ops
        rnd16 = (x == 0) ? 0 : ((x - 1) >> $clog2(W)) + 1;
    endfunction
    integer di;
    wire [$clog2(NSLOT*NDYN)-1:0] db = ds * NDYN;
    always @(posedge clk) if (cap) begin
        for (di = 0; di < NDYN; di = di + 1) dyn[db + di] <= 0;
        dyn[db + 1] <= b_tok * DIM;
        dyn[db + 2] <= b_pos * ROPE_PAIR;
        dyn[db + 3] <= (b_pos == 0) ? 0 : (b_pos - 1) * ROPE_PAIR;
        dyn[db + 4] <= b_pos;
        dyn[db + 5] <= p1;
        dyn[db + 6] <= n2;
        dyn[db + 7] <= (n2 == 0) ? 0 : n2 - 1;
        dyn[db + 8] <= ns1;
        dyn[db + 9] <= ns2;
        dyn[db + 10] <= p1 + ns1;
        dyn[db + 11] <= p1 + ns2;
        dyn[db + 12] <= rnds(p1);
        dyn[db + 13] <= rnds(n2);
        dyn[db + 14] <= rnds(p1 + ns1);
        dyn[db + 15] <= rnds(p1 + ns2);
        dyn[db + 16] <= b_pos * HDIM;
        dyn[db + 17] <= p1 * HDIM;
        dyn[db + 18] <= b_pos[0] ? 4 : 0;
        dyn[db + 19] <= b_pos[0] ? 64 : 0;
        dyn[db + 20] <= (n2 == 0) ? 0 : (n2 - 1) * HDIM;
        dyn[db + 21] <= rnd16(p1);
        dyn[db + 22] <= rnd16(n2);
        dyn[db + 23] <= rnd16(p1 + ns1);
        dyn[db + 24] <= rnd16(p1 + ns2);
        if (NSLOT > 1 || ROLLBACK_RING_DYN != 0) begin
            // Ring storage is independent of the number of token slots. A
            // one-position wavefront still needs the current record and pair.
            dyn[db + 25] <= {b_pos[2:0], 2'b00};
            dyn[db + 26] <= {b_pos[2:1], 7'd0};
        end
        if (NSLOT > 1) begin
            dyn[db + 27] <= b_tok * 32;
        end
        if (FULL_SHAPE) begin
            dyn[db + FDYN_WIN] <= (p1 < FULL_WINDOW) ? p1 : FULL_WINDOW;
            dyn[db + FDYN_NC1] <= p1;
            dyn[db + FDYN_NC2] <= n2;
            dyn[db + FDYN_NS1] <= ns1;
            dyn[db + FDYN_NS2] <= ns2;
            dyn[db + FDYN_T0] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW);
            dyn[db + FDYN_T1] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns1;
            dyn[db + FDYN_T2] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns2;
            dyn[db + FDYN_SC1] <= (p1 + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_SC2] <= (n2 + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_SCR] <= (((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP;
            dyn[db + FDYN_NSL1] <= (((p1 + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((p1 + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_NSL2] <= (((n2 + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((n2 + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_NSLR] <= (((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) < TOPK) ?
                                     ((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) : TOPK;
            dyn[db + FDYN_CEIL_SC1_16] <= (((p1 + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_SC1_8] <= (((p1 + FULL_TP - 1) / FULL_TP) + 7) >> 3;
            dyn[db + FDYN_CEIL_SC2_16] <= (((n2 + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_SCR_16] <= (((((p1 < FULL_SCAN_CAP) ? p1 : FULL_SCAN_CAP) + FULL_TP - 1) / FULL_TP) + 15) >> 4;
            dyn[db + FDYN_CEIL_T0_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + 31) >> 5;
            dyn[db + FDYN_CEIL_T1_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns1 + 31) >> 5;
            dyn[db + FDYN_CEIL_T2_32] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) + ns2 + 31) >> 5;
            dyn[db + FDYN_WINM1] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) - 1;
            dyn[db + FDYN_WIN_ROW] <= ((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) * HDIM;
            dyn[db + FDYN_WINM1_ROW] <= (((p1 < FULL_WINDOW) ? p1 : FULL_WINDOW) - 1) * HDIM;
        end
    end
endmodule
