`timescale 1ns/1ps
// RTLGAP2-HEADTB (10-21) CUT-B replay shim: drop-in for ot_s81hd_bundle (same parameters and ports) used ONLY in the
// die-level head cut TB (tb_s81hd_diecut).  Every other die element stays the bound RTL: the ot_s81hd_tile wrapper
// (pin registers, x pass-through, chain-best merge, keys, fire), spo / spr, all relays / landings / ICGs, ctl glue,
// dsfd_mtp_seq, lep_regional, lanes and SerDes columns.
// The bundle's computation (ROM reads + 5 elements + argmax) was run in full RTL by CUT-A (tb_s81hd_tilecut, one run per
// tile, logits bit-exact) with the golden bus-B stream; this shim
//   INPUT face  checks, bit for bit, what the die delivers to the bundle: one go per position, row0 = a recorded tile
//               strap, and x slice m (xa = xa.hex[m % 256], xb = xb.hex[m % 64]) at go + 5 + m for m < NSLICE, i.e. the
//               exact stream CUT-A's bundle consumed;
//   OUTPUT face replays CUT-A's recorded result for that row0: res_v at go + LAT (a level until the next go), res_row,
//               res_bits, fault.
// A face mismatch prints "FACE_FAIL <row0> ..." and raises fault (sticky), which the tile ORs into the chain flt.
// Plusargs: +HC_REC=<hex file: one line per tile {row0[16:0], lat[15:0], row[16:0], bits[31:0], flt} = 83 b>
//           +DIR=<dir with xa.hex / xb.hex>.  Prints "FACE_OK <row0> lat <lat> slices <n>" per position.
module ot_s81hd_bundle #(
    parameter integer BST = 2,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer SPLIT9 = 0,
    parameter integer NC = 1,
    parameter integer SK = 7,
    parameter INSTANCE = "h",
    parameter integer IOREG = 0,
    parameter integer SAFE = 1,
    parameter integer A_INPUT_STAGES = 0,
    parameter integer NSLICE = 8248,
    parameter integer NREC = 253
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         go,
    input  wire [16:0]  row0,
    input  wire [255:0] xa,
    input  wire [255:0] xb,
    output reg          res_v,
    output reg  [16:0]  res_row,
    output reg  [31:0]  res_bits,
    output wire         fault,
    output wire [3:0]   head_v,
    output wire [127:0] head_d,
    output wire [67:0]  head_row
);
    assign head_v = 4'd0; assign head_d = 128'd0; assign head_row = 68'd0;
    reg [82:0]  rec [0:NREC-1];
    reg [255:0] ma [0:255];
    reg [255:0] mb [0:63];
    reg [8*1024-1:0] recf, dir;
    initial begin
        if (!$value$plusargs("HC_REC=%s", recf)) $fatal(1, "+HC_REC");
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "+DIR");
        $readmemh(recf, rec);
        $readmemh({dir, "/xa.hex"}, ma);
        $readmemh({dir, "/xb.hex"}, mb);
    end
    integer c = -1, k, hit, nbad = 0, nok = 0;
    reg [15:0] lat;
    reg [16:0] rrow;
    reg [31:0] rbits;
    reg        rflt, flt_q = 1'b0;
    assign fault = flt_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin res_v <= 1'b0; c = -1; end
        else if (go) begin
            hit = -1;
            for (k = 0; k < NREC; k = k + 1) if (rec[k][82:66] == row0) hit = k;
            if (hit < 0) begin $display("FACE_FAIL %0d no CUT-A record for row0", row0); flt_q <= 1'b1; lat = 16'hFFFF; end
            else begin lat = rec[hit][65:50]; rrow = rec[hit][49:33]; rbits = rec[hit][32:1]; rflt = rec[hit][0]; end
            c = 0; nbad = 0; nok = 0; res_v <= 1'b0;
        end else if (c >= 0) begin
            c = c + 1;
            if (c >= 5 && c < 5 + NSLICE) begin
                if (xa !== ma[(c - 5) % 256] || xb !== mb[(c - 5) % 64]) begin
                    if (nbad < 4) $display("FACE_FAIL %0d x slice %0d xa %0s xb %0s", row0, c - 5,
                                           xa !== ma[(c - 5) % 256] ? "BAD" : "ok", xb !== mb[(c - 5) % 64] ? "BAD" : "ok");
                    nbad = nbad + 1; flt_q <= 1'b1;
                end else nok = nok + 1;
            end
            if (c == lat - 3) begin res_row <= rrow; res_bits <= rbits; end
            if (c == lat) begin
                res_v <= 1'b1; if (rflt) flt_q <= 1'b1;
                if (nbad == 0 && nok == (lat - 5 < NSLICE ? lat - 5 : NSLICE))
                    $display("FACE_OK %0d lat %0d slices %0d (checked before res_v)", row0, lat, nok);
            end
            if (c == 5 + NSLICE) begin
                if (nbad == 0 && nok == NSLICE) $display("FACE_XOK %0d slices %0d", row0, nok);
                else $display("FACE_FAIL %0d slices ok %0d bad %0d", row0, nok, nbad);
            end
        end
endmodule
