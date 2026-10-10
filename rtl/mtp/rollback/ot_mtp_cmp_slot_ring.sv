`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Compressor open-group record ring with exact MTP rollback (DS-V4.1 ratio-2 KV sources L2 / L8 / L14;
// stream mtp-rollback 2026-10-08).
//
// The ratio-r compressor (golden Model.compressor) appends every position's (kv, score) slot to the
// source's OPEN GROUP and, at the position completing the group ((p+1) mod r == 0), pools the r slots
// into one compressed row and empties the group.  The open group is ROLLBACK STATE, not a dead row:
// when a verify pass commits n = q+2+a positions with n mod r != 0, the committed open group is
// positions n - (n mod r) .. n-1, but a rejected position n may already have completed (and emptied)
// that group and rejected n+1 may have opened a new one.  The golden's truncate() rebuilds the group
// from `slotrec`, the record of every position's slot.
//
// This unit is that record, in hardware: slot of position p at p mod SR with its position tag.  The
// group-completing write streams the group's r slots (oldest first, the completing slot bypassed)
// straight from the ring, so the pooled row only ever sees committed-or-current-pass slots of the
// right positions.  Rollback is the commit pointer alone (n_set): positions >= n are dead and the
// committed open group stays in the ring untouched as long as SR >= (r - 1) + PMAX.
//
//   g_v/g_idx/g_data  registered, 1 cycle after the completing write: group index p >> RLOG and the
//                     r slots, slot of position p-r+1+i in g_data[i*DW +: DW]
//   op_*              the committed open group (positions n - n mod r .. n-1), one slot a cycle;
//                     op_empty when n mod r == 0 (the state read the ingest/checkpoint path needs)
//
// MUT_OPEN_REG = 1 (bench mutant only): the AR-style single open-group register that is emptied on
// completion and never restored -- the "dead-row invariant covers it" assumption T2 flagged.
// Cycles: write 1, group out +1, commit 1, rollback 0.  Storage SR x DW per source per user
// (V4.1: SR 8 x (512 kv + 512 score) FP32 = 32 KiB).
// ---------------------------------------------------------------------------
module ot_mtp_cmp_slot_ring #(
    parameter integer RLOG  = 1,
    parameter integer SR    = 8,
    parameter integer PMAX  = 8,
    parameter integer DW    = 32,
    parameter integer PW    = 32,
    parameter integer MUT_OPEN_REG = 0
) (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    n_set,
    input  wire [PW-1:0]           n_val,
    input  wire                    wr_v,
    input  wire [PW-1:0]           wr_pos,
    input  wire [DW-1:0]           wr_data,
    output reg                     g_v,
    output reg  [PW-1:0]           g_idx,
    output reg  [(DW<<RLOG)-1:0]   g_data,
    input  wire                    op_req,
    output wire                    op_ready,
    output reg                     op_v,
    output reg  [DW-1:0]           op_data,
    output reg  [PW-1:0]           op_pos,
    output reg                     op_last,
    output reg                     op_empty,
    output reg                     err
);
    localparam integer RR = 1 << RLOG;
    localparam integer SB = $clog2(SR);
    initial if (RLOG < 1 || (1 << SB) != SR || SR < RR - 1 + PMAX)
        $fatal(1, "ot_mtp_cmp_slot_ring: ratio >= 2 and SR a power of two >= r - 1 + PMAX");

    reg [DW-1:0] mem [0:SR-1];
    reg [PW-1:0] tag [0:SR-1];
    reg          tv  [0:SR-1];
    reg [DW-1:0] oreg [0:RR-1];          // MUT_OPEN_REG only
    reg [RLOG:0] ocnt;
    reg [PW-1:0] n;
    reg          busy;
    reg [PW-1:0] p_cur, p_end;
    integer i;
    assign op_ready = !busy;

    function automatic [SB-1:0] slot(input [PW-1:0] p);
        slot = p[SB-1:0];
    endfunction

    wire complete = ((wr_pos + 1) & (RR - 1)) == 0;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            n <= 0; err <= 1'b0; g_v <= 1'b0; g_idx <= 0; g_data <= 0; busy <= 1'b0; ocnt <= 0;
            op_v <= 1'b0; op_last <= 1'b0; op_empty <= 1'b0; op_data <= 0; op_pos <= 0;
            for (i = 0; i < SR; i = i + 1) tv[i] <= 1'b0;
        end else begin
            g_v <= 1'b0; op_v <= 1'b0; op_last <= 1'b0; op_empty <= 1'b0;
            if (n_set) n <= n_val;
            if (wr_v) begin
                if (MUT_OPEN_REG) begin
                    if (complete) begin
                        g_v <= 1'b1; g_idx <= wr_pos >> RLOG;
                        for (i = 0; i < RR - 1; i = i + 1) g_data[i*DW +: DW] <= oreg[i];
                        g_data[(RR-1)*DW +: DW] <= wr_data;
                        ocnt <= 0;
                    end else begin
                        oreg[ocnt] <= wr_data; ocnt <= ocnt + 1'b1;
                    end
                end else begin
                    mem[slot(wr_pos)] <= wr_data; tag[slot(wr_pos)] <= wr_pos; tv[slot(wr_pos)] <= 1'b1;
                    if ($signed(wr_pos - n) >= PMAX || $signed(wr_pos - n) < -(SR - PMAX)) err <= 1'b1;
                    if (complete) begin
                        g_v <= 1'b1; g_idx <= wr_pos >> RLOG;
                        for (i = 0; i < RR - 1; i = i + 1) begin
                            g_data[i*DW +: DW] <= mem[slot(wr_pos - (RR - 1) + i)];
                            if (!tv[slot(wr_pos - (RR - 1) + i)] || tag[slot(wr_pos - (RR - 1) + i)] != wr_pos - (RR - 1) + i)
                                err <= 1'b1;
                        end
                        g_data[(RR-1)*DW +: DW] <= wr_data;
                    end
                end
            end
            // committed open-group read
            if (!busy && op_req) begin
                if (MUT_OPEN_REG ? (ocnt == 0) : ((n & (RR - 1)) == 0)) begin
                    op_v <= 1'b1; op_last <= 1'b1; op_empty <= 1'b1;
                end else begin
                    busy <= 1'b1;
                    p_cur <= MUT_OPEN_REG ? 0 : n - (n & (RR - 1));
                    p_end <= MUT_OPEN_REG ? ocnt - 1 : n - 1;
                end
            end else if (busy) begin
                op_v <= 1'b1; op_pos <= p_cur;
                if (MUT_OPEN_REG) op_data <= oreg[p_cur[RLOG-1:0]];
                else begin
                    op_data <= mem[slot(p_cur)];
                    if (!tv[slot(p_cur)] || tag[slot(p_cur)] != p_cur) err <= 1'b1;
                end
                if (p_cur == p_end) begin busy <= 1'b0; op_last <= 1'b1; end
                else p_cur <= p_cur + 1;
            end
        end
    end
endmodule
