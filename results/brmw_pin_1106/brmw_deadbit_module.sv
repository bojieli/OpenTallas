module ot_hgi_sm_xload_cl2_bdring #(
    parameter integer PMAX = 8,
    parameter integer NR   = 64
) (
    input  wire               clk,
    input  wire [15:0]        r_wsel,
    input  wire               zlo, zhi,
    input  wire [255:0]       qq_lo, qq_hi,
    input  wire signed [9:0]  qe_lo, qe_hi,
    input  wire [2*((PMAX*3152+2047)/2048)-1:0] bsel,  // one-hot {parity, beat} (registered in ctl)
    input  wire [PMAX*8-1:0]  lane_en_i,
    output wire [2047:0]      bq_d
);
    // cl2e: the beat register holds the INVERTED beat so the ASAP7 QN-only flop (DFFHQN) drives bq_d with no output
    // inverter. cl2d placed 25 of the 2048 output-polarity INVs ~300 um from their pin flops (native launch 489.6 ps
    // on bq_d[420]); with the inversion folded into the D-side AND-OR (AOI) the pin is driven by the flop itself.
    // Same edge, same values at the pin.
    reg [2047:0] bq_n;
    assign bq_d = ~bq_n;
    localparam integer XC = 3152;
    localparam integer NBQ = (PMAX * XC + 2047) / 2048;
    localparam integer RB = 2048 / NR;
    reg [PMAX*8-1:0] lane_en;              // local copy (command constant; refreshed every edge)
    always @(posedge clk) lane_en <= lane_en_i;
    reg [265:0] wr_lo, wr_hi;              // quantiser words registered at the pins (cl's wd edge)
    // cl2d: ring controls registered at the pins on the SAME edge as wr_lo/wr_hi (ctl sends them one edge early);
    // one enable copy per parity (532 loads each), no pin-to-storage gating left.
    reg [15:0] wsel_q [0:1];
    reg        zlo_q, zhi_q;
    always @(posedge clk) begin
        wr_lo <= {qe_lo, qq_lo}; wr_hi <= {qe_hi, qq_hi};
        wsel_q[0] <= r_wsel; wsel_q[1] <= r_wsel; zlo_q <= zlo; zhi_q <= zhi;
    end
    wire [265:0] wd_lo = zlo_q ? wr_lo : 266'd0, wd_hi = zhi_q ? wr_hi : 266'd0;
    wire [265:0] ring [0:1][0:15];
    genvar gpa, gsl;
    generate for (gpa = 0; gpa < 2; gpa = gpa + 1) begin : g_rp
        for (gsl = 0; gsl < 16; gsl = gsl + 1) begin : g_rs
            reg [265:0] w;
            always @(posedge clk) if (wsel_q[gpa][gsl]) w <= (gpa == 0) ? wd_lo : wd_hi;
            assign ring[gpa][gsl] = w;
        end
    end endgenerate
    wire [2047:0] beat_w [0:1][0:NBQ-1];
    genvar gbb2, gpp, gjj;
    generate for (gpa = 0; gpa < 2; gpa = gpa + 1) begin : g_ap
        for (gbb2 = 0; gbb2 < NBQ; gbb2 = gbb2 + 1) begin : g_ab
            wire [2047:0] parts [0:PMAX*8];
            assign parts[0] = 2048'd0;
            for (gpp = 0; gpp < PMAX; gpp = gpp + 1) begin : g_lp
                for (gjj = 0; gjj < 8; gjj = gjj + 1) begin : g_lj
                    localparam integer LI = gpp * 8 + gjj;
                    localparam integer ST = gpp * XC + 266 * gjj - 2048 * gbb2;
                    wire [265:0] lw = ring[gpa][(gpp % 2) * 8 + gjj] & {266{lane_en[LI]}};
                    if (ST >= 2048 || ST + 266 <= 0) begin : g_out
                        assign parts[LI + 1] = parts[LI];
                    end else if (ST >= 0) begin : g_in
                        wire [2048+266-1:0] sh = {2048'd0, lw} << ST;
                        assign parts[LI + 1] = parts[LI] | sh[2047:0];
                    end else begin : g_lo
                        wire [265:0] sh = lw >> (-ST);
                        assign parts[LI + 1] = parts[LI] | {1782'd0, sh};
                    end
                end
            end
            assign beat_w[gpa][gbb2] = parts[PMAX*8];
        end
    end endgenerate
    // NR replicas of the one-hot select (pin registers), each an AND-OR over 2 x NBQ beat words for RB output bits
    reg [2*NBQ-1:0] bs [0:NR-1];
    always @(posedge clk) for (integer k = 0; k < NR; k = k + 1) bs[k] <= bsel;
    always @(posedge clk) for (integer k = 0; k < NR; k = k + 1) begin : sel
        reg [RB-1:0] acc; acc = {RB{1'b0}};
        for (integer x = 0; x < NBQ; x = x + 1)
            acc = acc | ({RB{bs[k][x]}} & beat_w[0][x][k*RB +: RB]) | ({RB{bs[k][NBQ + x]}} & beat_w[1][x][k*RB +: RB]);
        bq_n[k*RB +: RB] <= ~acc;
    end
endmodule