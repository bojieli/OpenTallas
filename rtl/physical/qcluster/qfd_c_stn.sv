`timescale 1ns/1ps
// Q-CLUSTER3 (2026-10-17, coordinator decision HANDOFF 0de+5): the qfd_c_b16_dv fabric stations as small replicated HARD
// tiles.  Each master has its own clock pin and local tree; every data input pin drives a flop D (flop-first) and every
// data output pin is a flop Q (flop-last), so the cluster clock reaches only the child clock pins (station tiles + A0
// leaves + the 1-bit reset stages) instead of ~78k loose fabric flops.  Logic is exactly the soft stations they replace:
//   qfd_c_stn516 / qfd_c_stn514 = qfd_q3h_stn #(.W(516 / 514), .N(1))  (one registered stage, q = d one edge later);
//   qfd_c_xstn                  = qfd_xcst_n without its die strap tie outputs (the cluster left them open).
// No reset on data (static schedule), no ready / credit / backpressure.

module qfd_c_stn516 (
    input  wire         ck,
    input  wire [515:0] d,
    output wire [515:0] q
);
    (* keep *) reg [515:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = q_r;
endmodule

module qfd_c_stn514 (
    input  wire         ck,
    input  wire [513:0] d,
    output wire [513:0] q
);
    (* keep *) reg [513:0] q_r;
    always @(posedge ck) q_r <= d;
    assign q = q_r;
endmodule

// column station: corridor word b_d (S) -> a_d (N) one edge later, tap_d to the A0 tile (E face; MY for a W-side tile)
module qfd_c_xstn (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst_rep #(.AW(24), .NW(18), .XOFF(3)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d),
        .b_d(a_d), .tap_d(tap_d));
endmodule

// the same column station with its tap on the W face (a tile W of the lane: columns 1 and 3).  A separate master, not
// qfd_c_xstn placed MY: a mirrored 34.56-um tile puts its S / N M3 / M5 pins off the track lattice (no width is
// mirror-legal for both the 0.036 M3 and the 0.048 M5 pitch), as qfd_xcst_n_my did.
module qfd_c_xstnw (
    input  wire         ck,
    input  wire         rst_n,
    input  wire [2:0]   sidx,
    input  wire [515:0] b_d,
    output wire [515:0] a_d,
    output wire [507:0] tap_d
);
    ot_qfd_xcst_rep #(.AW(24), .NW(18), .XOFF(3)) u_st (.ck(ck), .rst_n(rst_n), .sidx(sidx), .a_d(b_d),
        .b_d(a_d), .tap_d(tap_d));
endmodule

// QC-CBGLUE-1116 (2026-11-16): ot_qfd_xcst with its x-hold control duplicated per 16-bit hold segment.  Measured on
// cbx_q10__cl94a12200 (post-CTS TT): u_st.sx[2] -> u_st.tap_d[408] hold -1093 ps, one unbuffered 78 fF net (1402 ps
// slew) from the single 3-bit sx / tag compare / run-count control to the far end of the 64-bit cap / hold bank.
// Each segment k (cap / hold bits [16k +: 16]) has its own sx, tag, go, cnt and run registers, captured from the same
// a_d / sidx bits on the same edge as the original single copies (b_q tag / go are a_d one edge later), so every copy
// equals the original register in every cycle: same function, same latency, 0 added cycles, +4x16 flops.
// b_q (corridor word) and t_q (tap {ib, go}) are unchanged.  No tap ready (a_r) / b_r: the column stations never
// connected them (a_r() open, b_r 1'b1).
module ot_qfd_xcst_rep #(
    parameter integer AW   = 24,
    parameter integer NW   = 18,
    parameter integer IL   = 8,
    parameter integer XOFF = 3,
    parameter integer NSEG = 4
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [2:0]    sidx,
    input  wire [1+(3*NW+13*AW+13)+128+8-1:0] a_d,
    output wire [1+(3*NW+13*AW+13)+128+8-1:0] b_d,
    output wire [1+(3*NW+13*AW+13)+128-1:0] tap_d
);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    localparam integer CW  = 1 + IBW + 128 + 8;
    localparam integer SEG = 64 / NSEG;
    (* keep *) reg [CW-1:0] b_q;
    always @(posedge ck) b_q <= a_d;
    assign b_d = b_q;
    (* keep *) reg [IBW:0] t_q;
    always @(posedge ck) t_q <= a_d[IBW:0];
    wire [127:0] xl = b_q[1 + IBW +: 128];
    wire [63:0]  hold;
    genvar k, i;
    generate for (k = 0; k < NSEG; k = k + 1) begin : g_seg
        (* keep *) reg [2:0] sx;
        (* keep *) reg [7:0] tag;
        (* keep *) reg       go;
        always @(posedge ck) begin
            sx  <= sidx;
            tag <= a_d[1 + IBW + 128 +: 8];
            go  <= a_d[0];
        end
        (* keep *) reg [3:0] cnt;
        (* keep *) reg       run;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) begin cnt <= 4'd0; run <= 1'b0; end
            else if (go) begin cnt <= XOFF - 2; run <= 1'b1; end
            else if (run) cnt <= (cnt == 0) ? IL - 1 : cnt - 1'b1;
        wire tag_a = tag[3] && tag[2:0] == sx;
        wire tag_b = tag[7] && tag[6:4] == sx;
        reg [SEG-1:0] cap;
        (* keep *) reg [SEG-1:0] hold_q;
        always @(posedge ck) begin
            if (tag_a) cap <= xl[SEG*k +: SEG];
            else if (tag_b) cap <= xl[64 + SEG*k +: SEG];
        end
        always @(posedge ck) if (run && cnt == 0)
            hold_q <= tag_a ? xl[SEG*k +: SEG] : tag_b ? xl[64 + SEG*k +: SEG] : cap;
        assign hold[SEG*k +: SEG] = hold_q;
    end endgenerate
    wire [127:0] xo;
    generate for (i = 0; i < 4; i = i + 1) begin : g_x
        assign xo[32*i +: 32] = {hold[16*i +: 16], 16'h0000};
    end endgenerate
    assign tap_d = {xo, t_q};
endmodule
