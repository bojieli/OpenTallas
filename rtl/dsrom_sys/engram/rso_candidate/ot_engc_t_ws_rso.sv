// SOURCE-ONLY RSO CANDIDATE: new master/port; existing closed views do not bind this variant.
`timescale 1ns/1ps
// ot_engc_t_ws (el1011-ds-misc/engram, 2026-10-11): WEST SEAM tile of the all-tile dsfd_engram_c (under the sink, W die
// edge).  Terminates the two buses that cross in the west of the outline, each with registered faces:
//   sink write port (N face) -> W0 pin flops -> SECDED encode + compact address -> W1 out flops (S face):
//       bank 1 {w_oh, w_a, b1_d 256} to the band tile, transit {bank2 64, bank0 256} for the column tiles
//       (W0 / W1 = the old prefetch W1 split at the encoder: write commit +1 edge; werr = an address fault, sticky later)
//   HBM backend pair (W face pins) <-> the lookup's S face: 2 stages each way (= the old hqd/hrd relays).
module ot_engc_t_ws_rso (
    input  wire         ck,
    input  wire         rst,
    input  wire         wr_v,
    input  wire [10:0]  wr_addr,      // {slot 3, column 5, beat 3}; column < 24
    input  wire [511:0] wr_data,
    output reg          werr,         // write address fault (pulse), relayed to T_IO via T_WIN
    output reg  [5:0]   w_oh,
    output reg  [7:0]   w_a,
    output reg  [255:0] b1_d,
    output reg  [319:0] x_d,          // {bank 2 64 b, bank 0 256 b}
    // HBM pair
    input  wire         lk_hqv,
    input  wire [30:0]  lk_hqa,
    input  wire [2:0]   lk_hqt,
    output wire [34:0]  t_hq,         // {hq_tag 3, hq_atom 31, hq_v}
    input  wire [264:0] f_hr,         // {hr_d 256, hr_idx 4, hr_tag 3, hr_v, hq_cred}
    output wire [264:0] lk_hr         // same packing, two stages later
,
    output wire rso
);
    reg [1:0] rs_q;
    always @(posedge ck or negedge rst) if (!rst) rs_q <= 2'b00; else rs_q <= {rs_q[0], 1'b1};
    wire rn = rs_q[1];
    assign rso = rn;
    // ---------------- write: W0 pin flops
    reg wv0; reg [10:0] wa0; reg [511:0] wd0;
    always @(posedge ck or negedge rn) if (!rn) wv0 <= 1'b0; else wv0 <= wr_v;
    always @(posedge ck) begin wa0 <= wr_addr; wd0 <= wr_data; end
    wire ok = wa0[7:3] < 24;
    wire [10:0] cmp = ({8'd0, wa0[10:8]} << 7) + ({8'd0, wa0[10:8]} << 6) + {3'd0, wa0[7:0]};
    wire [575:0] enc;
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_enc
        ot_s81_secded_enc72 u_enc (.d(wd0[64*l+:64]), .c(enc[72*l+:72]));
    end endgenerate
    // W1 out flops
    always @(posedge ck or negedge rn)
        if (!rn) begin w_oh <= 6'd0; werr <= 1'b0; end
        else begin w_oh <= {6{wv0 && ok}} & (6'd1 << cmp[10:8]); werr <= wv0 && !ok; end
    always @(posedge ck) begin w_a <= cmp[7:0]; b1_d <= enc[511:256]; x_d <= {enc[575:512], enc[255:0]}; end
    // ---------------- HBM pair relays (data unreset; valid / credit reset)
    reg [33:0] hqd_1, hqd_2; reg hqv_1, hqv_2; reg [262:0] hrd_1, hrd_2; reg [1:0] hrv_1, hrv_2;
    always @(posedge ck) begin hqd_1 <= {lk_hqt, lk_hqa}; hqd_2 <= hqd_1; hrd_1 <= f_hr[264:2]; hrd_2 <= hrd_1; end
    always @(posedge ck or negedge rn)
        if (!rn) begin hqv_1 <= 1'b0; hqv_2 <= 1'b0; hrv_1 <= 2'b00; hrv_2 <= 2'b00; end
        else begin hqv_1 <= lk_hqv; hqv_2 <= hqv_1; hrv_1 <= f_hr[1:0]; hrv_2 <= hrv_1; end
    assign t_hq = {hqd_2, hqv_2};
    assign lk_hr = {hrd_2, hrv_2};
endmodule
