`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 ATT issue decoder (hgi-adapters, 2026-10-09).  The `att` consumer of Codex's G12 record adapter
// (rtl/hbm_accel/generic/g12/record/ot_hgi_att_record_adapter.sv: att_v / att_r, att_hdr, att_desc {O, C, B, A},
// att_done / att_fault; the row list B ring + C rows goes separately to the G12 row sources on rows_cmd).  It turns an
// ATT.QK / ATT.PV record into the attention controller's job word: decode + handshake only.
//   Job (161 b, LSB first): {mode 1 (0 QK, 1 PV), lanes 5 (param[3:0], 0 encodes 16: HGI-1.1), slices 4 (param[7:4]+1),
//     ring 1 (param[8]), hd 10 (QK: A.n; PV: O.n; = 64 x slices), nrows 21 (B.n + C.n: the row list length),
//     b_fmt 3 (B row format: FP32 / BF16 / FP8E4M3 / FP4E2M1), a_base 18, a_stride 32, o_base 18, o_stride 32, pos1 13 (low,
//     for the ring's first slot (POS1 - n) mod m, carried for the controller), c_fmt 3 (C rows: DS compressed rows
//     may differ from the window rows)}
//   QK: A = queries (VM, lanes rows of hd), O = scores (VM, lanes rows of nrows);
//   PV: A = probabilities (VM, lanes rows of nrows: A.n must equal nrows, hgi_sim u_att_pv), O = PV (VM, lanes rows of hd).
// Retire: the controller's done -> att_done (the record adapter joins it with the row list's done); fault -> att_fault.
// Refusals -> att_fault at once (no job): op > 1, A or O not VM, hd != 64 x slices or hd > 512, PV with A.n != nrows,
// B / C fmt not a row format (FP32 / BF16 / FP8E4M3 / FP4E2M1).
// Latency: att accept E0, job_v E1 (one decode edge; the record adapter's station is in front).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_att_issue #(
    parameter integer MUT_LANES = 0       // mutant: lanes 0 decoded as 0 (no HGI-1.1 16)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          att_v,
    output wire          att_r,
    input  wire [127:0]  att_hdr,
    input  wire [1023:0] att_desc,
    input  wire [20:0]   att_pos1,
    output reg           att_done,
    output reg           att_fault,
    output wire          job_v,
    input  wire          job_rdy,
    output reg  [160:0]  job,
    input  wire          job_done,
    input  wire          job_fault
);
    reg iss, busy, in_done, in_fault;
    always @(posedge clk) begin in_done <= job_done; in_fault <= job_fault; end
    assign att_r = !iss && !busy;
    assign job_v = iss;
    wire [255:0] A = att_desc[255:0], B = att_desc[511:256], Cd = att_desc[767:512], O = att_desc[1023:768];
    wire        op   = att_hdr[118];
    wire [5:0]  opc  = att_hdr[123:118];
    wire        cp   = att_hdr[95];                           // opnd bit 2: C present
    wire [3:0]  ln   = att_hdr[67:64];
    wire [4:0]  lanes = (ln == 4'd0 && !MUT_LANES) ? 5'd16 : {1'b0, ln};
    wire [4:0]  slices = {1'b0, att_hdr[71:68]} + 5'd1;
    wire [19:0] hd   = op ? O[67:48] : A[67:48];
    wire [20:0] nrows = {1'b0, B[67:48]} + (cp ? {1'b0, Cd[67:48]} : 21'd0);
    wire        kvf_ok = (B[4:2] <= 3'd3) && (!cp || Cd[4:2] <= 3'd3);       // FP32 / BF16 / FP8E4M3 / FP4E2M1 rows
    wire bad = (opc > 6'd1) || (A[1:0] != 2'd1) || (O[1:0] != 2'd1) || (hd != {9'd0, slices, 6'd0}) || (hd > 20'd512) ||
               (op && {1'b0, A[67:48]} != nrows) || !kvf_ok;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin iss <= 1'b0; busy <= 1'b0; att_done <= 1'b0; att_fault <= 1'b0; job <= 0; end
        else begin
            att_done <= 1'b0; att_fault <= 1'b0;
            if (att_v && att_r) begin
                if (bad) att_fault <= 1'b1;
                else begin
                    iss <= 1'b1; busy <= 1'b1;
                    job <= {cp ? Cd[4:2] : 3'd0, att_pos1[12:0], O[119:88], O[25:8], A[119:88], A[25:8], B[4:2], nrows, hd[9:0], att_hdr[72],
                            slices[3:0], lanes, op};
                end
            end
            if (iss && job_rdy) iss <= 1'b0;
            if (busy && !iss) begin
                if (in_fault) begin att_fault <= 1'b1; busy <= 1'b0; end
                else if (in_done) begin att_done <= 1'b1; busy <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire
