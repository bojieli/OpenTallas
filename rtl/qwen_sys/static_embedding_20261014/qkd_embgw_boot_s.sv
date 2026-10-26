`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, RTL-BUILD-KV/BOOT 2026-10-18 (results/arch/qwen_kv_boot_path_1018/note.md): the embedding gateway for
// the STATIC KV die, successor of qkd_embgw_boot.  The legacy gateway sent BOOT_WR / BOOT_END over four credit links
// (emf_<q> / emr_<q>) to the per-stack embedding strips (ot_qfd_emb_strip in qkd_land) and took {count, checksum}
// STATUS back; the static die removed the strips, so those links have no far end.  This cell does the strips' boot
// job itself, at the gateway:
//   hb {v, end, E 25, data 256} (host boot words, BD-word skid, hb_cr = one credit a word taken: the HOST boot
//   boundary, owner rule 10-14: credits stay at the boot / off-die boundaries)
//   BOOT_WR  -> map E (ot_qfd_emb_pkg.emb_loc, the strip's map, unchanged) -> ONE registered boot word a send edge
//               bw = {data 256, address 29 = {bank, col, row}, pc 5, stack 2, v} to the writer-side chain root
//               (qkd_kv_es_fan_root2_b), which carries it on the existing static PC chain to the home PC's station
//               (qkd_kv_pc_chain_station_b) -> that PC's HOST slice land_es (the slice's landing source, unchanged
//               qkd_host_pc_slice_die) -> the slice's boot-qualified static arbiter -> es merge _b -> the controller.
//               count + checksum (sum of crc_sector(E, data) mod 2^32, the strip's definition, cumulative from
//               reset as the strips' were) are taken on the words as sent.
//   BOOT_END -> expected {count [31:0], checksum [63:32]} (the HOST dispatcher sends it only after every boot write's
//               REAL controller completion has retired on its commit-order ledger); emb_ready drops, and HOLD edges
//               later rises iff the sums match (else fault code bit 5).  HOLD keeps the not-ready phase the HOST
//               boot barrier (qkd_host_emb_boot_barrier, require_fresh) must observe; the legacy STATUS round trip
//               gave the same window.
//   Re-load: a BOOT_WR at the skid head while emb_ready is high first drops emb_ready and holds the stream HOLD edges
//               (REOPEN), so every PC's es merge _b has handed its controller face back to the HOST slice before the
//               first new word can reach it (the est trunk is shorter than HOLD edges).  The HOST stops the static
//               programme before a re-load (boot is the exceptional phase).
//   est = {cause 11, fault, emb_ready}: cause [7:0] fault code ([0] BOOT_WR sector out of range, [5] sum mismatch),
//   [8] 0 (no strip link), [9] boot skid overrun, [10] 0 (no strip link credits).
// Pacing: one send every GAP edges (GAP >= 1).  A PC receives one word per 128 consecutive sectors of an ascending
// image; the slice's 4-word landing queue and the controller's static queue absorb the HBM side (credits inside the
// slice); an over-full slice queue is a fault there, never a stall here (boot contract, note.md).
// MUT (bench only): 1 = BOOT_WR mapped to pc ^ 1; 2 = BOOT_END checks the count only; 3 = no REOPEN (emb_ready stays
// high while a re-load is written).
// ---------------------------------------------------------------------------------------------------------------------
module qkd_embgw_boot_s #(
    parameter integer BD   = 4,
    parameter integer GAP  = 1,
    parameter integer HOLD = 64,
    parameter integer ROW0 = 24427,
    parameter integer MUT  = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [282:0]  hb,
    output reg           hb_cr,
    output wire [12:0]   est,
    output reg  [292:0]  bw
);
    import ot_qfd_emb_pkg::*;
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    localparam integer GW = (GAP <= 1) ? 1 : $clog2(GAP + 1);
    localparam integer HW = $clog2(HOLD + 2);
    // ---- reset: asynchronous assert, synchronous release (as qkd_embgw_boot) ----
    reg rs0, rs;
    always @(posedge ck or negedge rst_n) if (!rst_n) begin rs0 <= 1'b0; rs <= 1'b0; end else begin rs0 <= 1'b1; rs <= rs0; end
    // ---- hb pin capture ----
    reg          hbv_p, hbe_p;
    reg [24:0]   hbs_p;
    reg [255:0]  hbd_p;
    always @(posedge ck or negedge rs) if (!rs) hbv_p <= 1'b0; else hbv_p <= hb[0];
    always @(posedge ck) begin hbe_p <= hb[1]; hbs_p <= hb[26:2]; hbd_p <= hb[282:27]; end
    // ---- boot skid ----
    reg  [281:0] bq [0:BD-1];
    reg  [BA:0]  bwp, brp;
    wire         bne    = (bwp != brp);
    wire         bfull  = (bwp[BA-1:0] == brp[BA-1:0]) && (bwp[BA] != brp[BA]);
    wire [281:0] bh     = bq[brp[BA-1:0]];
    wire         bh_end = bh[281];
    wire [24:0]  bh_e   = bh[280:256];
    wire [255:0] bh_d   = bh[255:0];
    always @(posedge ck) if (hbv_p && !bfull) bq[bwp[BA-1:0]] <= {hbe_p, hbs_p, hbd_p};
    // ---- pacing / REOPEN ----
    reg  [GW-1:0] gc;
    reg  [HW-1:0] wc, hold;
    reg           emb_ready, pend, f_bq, ck_v;
    wire          reopen = bne && !bh_end && emb_ready && MUT != 3;
    wire          go     = bne && (gc == 0) && (wc == 0) && !reopen;
    wire [25:0]   loc    = emb_loc(bh_e);             // {valid, stack, pc, bank, col, row_off}
    wire [4:0]    mpc    = (MUT == 1) ? (loc[22:18] ^ 5'd1) : loc[22:18];
    wire [18:0]   mrow   = 19'(ROW0) + 19'(loc[7:0]);
    // ---- checksum stage (registered: the sums are compared HOLD edges after BOOT_END) ----
    reg  [31:0]   ck_c, a_cnt, a_csum, x_cnt, x_csum;
    reg  [7:0]    fc;
    always @(posedge ck) ck_c <= crc_sector(bh_e, bh_d);
    always @(posedge ck) if (go && !bh_end) bw[292:1] <= {bh_d, loc[17:13], loc[12:8], mrow, mpc, loc[24:23]};
    always @(posedge ck or negedge rs)
        if (!rs) begin
            bwp <= 0; brp <= 0; gc <= 0; wc <= 0; hb_cr <= 1'b0; bw[0] <= 1'b0; ck_v <= 1'b0; f_bq <= 1'b0;
            a_cnt <= 0; a_csum <= 0; x_cnt <= 0; x_csum <= 0; pend <= 1'b0; emb_ready <= 1'b0; hold <= 0; fc <= 8'd0;
        end else begin
            hb_cr <= go;
            bw[0] <= go && !bh_end && loc[25];
            ck_v  <= go && !bh_end && loc[25];
            if (hbv_p) begin if (bfull) f_bq <= 1'b1; else bwp <= bwp + 1'b1; end
            if (go) begin brp <= brp + 1'b1; gc <= GW'(GAP - 1); end
            else if (gc != 0) gc <= gc - 1'b1;
            if (reopen) begin emb_ready <= 1'b0; wc <= HW'(HOLD); end
            else if (wc != 0) wc <= wc - 1'b1;
            if (go && !bh_end && !loc[25]) fc[0] <= 1'b1;   // out-of-range sector: never written
            if (ck_v) begin a_cnt <= a_cnt + 1'b1; a_csum <= a_csum + ck_c; end
            if (go && bh_end) begin
                x_cnt <= bh_d[31:0]; x_csum <= bh_d[63:32];
                emb_ready <= 1'b0; pend <= 1'b1; hold <= HW'(HOLD);
            end else if (pend) begin
                if (hold != 0) hold <= hold - 1'b1;
                else begin
                    pend <= 1'b0;
                    if (a_cnt == x_cnt && (MUT == 2 || a_csum == x_csum)) emb_ready <= 1'b1;
                    else fc[5] <= 1'b1;
                end
            end
        end
    // ---- status (flops at the pins) ----
    reg  [12:0] st_q;
    wire        any_f = (|fc) | f_bq;
    always @(posedge ck or negedge rs)
        if (!rs) st_q <= 13'd0;
        else st_q <= {1'b0, f_bq, 1'b0, fc, any_f, emb_ready && !any_f};
    assign est = st_q;
endmodule
