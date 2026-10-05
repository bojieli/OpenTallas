`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Cross-tile K-split collector of the V4.1x weight engines (block `wgt`).
//
// A row too long for one tile's share of the die's time (wo_b on the quantised
// engine: 5,120 rows x 256 blocks per die) is cut into P = 2^S ALIGNED parts:
// part p holds chunks [p * NP/P, (p+1) * NP/P) of the row's padded chunk tree
// (NP = the power of two >= the row's chunk count).  Each part runs on its own
// tile as an ordinary row, and the tile's FP32 result (o_y) is that part's
// subtree root -- the tile pads its part's tree to its own power of two, and
// the further padding up to NP/P is adds of +0, the identity.  This module adds
// the P roots by the top S levels of the SAME padded pairwise tree, in fixed
// order ((r0 + r1) + (r2 + r3) ...), so the result is tools/hdc_golden_v41.csum
// of the whole row bit for bit.  A part with no chunks (the row is shorter than
// the aligned split) is presented as +0, which is the tree's own padding.
//
// PROTOCOL.  Port p takes the part-p results of a stream of rows in row order
// (valid, row tag, M FP32 values, M faults); ports may run skewed by up to
// DEPTH results against each other (the tiles finish at different times).
// Each port has a DEPTH-entry FIFO; a row issues into the tree when every port
// holds its head.  in_rdy[p] is low when port p's FIFO is full.  A head-tag
// mismatch across ports raises the result's fault (fail closed).
// LATENCY 1 (FIFO register) + 3*S (tree) + 1 (output register) = 3S + 2 cycles
// from the last part's arrival; one row per cycle.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_kcol #(
    parameter integer S = 1,              // log2 parts
    parameter integer M = 1,              // positions
    parameter integer TGW = 16,           // row tag
    parameter integer DEPTH = 8
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [(1<<S)-1:0]        in_v,
    output wire [(1<<S)-1:0]        in_rdy,
    input  wire [(1<<S)*TGW-1:0]    in_tag,
    input  wire [(1<<S)*M*32-1:0]   in_y,
    input  wire [(1<<S)*M-1:0]      in_f,
    output reg                      o_v,
    output reg  [TGW-1:0]           o_tag,
    output reg  [M*32-1:0]          o_y,
    output reg  [M*16-1:0]          o_bf,
    output reg  [M-1:0]             o_f
);
    localparam integer P = 1 << S;
    localparam integer EW = TGW + M*32 + M;
    localparam integer AW = (DEPTH <= 2) ? 1 : $clog2(DEPTH);

    wire [P-1:0]      hv;
    wire [P*EW-1:0]   hd;
    wire              go = &hv;
    genvar p, l, n;
    generate
        for (p = 0; p < P; p = p + 1) begin : g_fifo
            reg [EW-1:0] mem [0:DEPTH-1];
            reg [AW:0]   cnt;
            reg [AW-1:0] wp, rp;
            wire push = in_v[p] && in_rdy[p];
            assign in_rdy[p] = (cnt != DEPTH);
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n) begin cnt <= 0; wp <= 0; rp <= 0; end
                else begin
                    if (push) wp <= (wp == DEPTH - 1) ? {AW{1'b0}} : wp + 1'b1;
                    if (go) rp <= (rp == DEPTH - 1) ? {AW{1'b0}} : rp + 1'b1;
                    cnt <= cnt + push - go;
                end
            end
            always @(posedge clk) if (push) mem[wp] <= {in_tag[p*TGW +: TGW], in_y[p*M*32 +: M*32], in_f[p*M +: M]};
            assign hv[p] = (cnt != 0);
            assign hd[p*EW +: EW] = mem[rp];
        end
    endgenerate

    // stage F: the heads, registered; the tag check
    reg              f_v;
    reg [P*M*32-1:0] f_y;
    reg [P*M-1:0]    f_f;
    reg [TGW-1:0]    f_tag;
    reg              f_bad;
    integer i;
    reg bad;
    always @(*) begin
        bad = 1'b0;
        for (i = 1; i < P; i = i + 1) bad = bad | (hd[i*EW + M*32 + M +: TGW] != hd[M*32 + M +: TGW]);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) f_v <= 1'b0;
        else f_v <= go;
    end
    always @(posedge clk) begin
        f_tag <= hd[M*32 + M +: TGW];
        f_bad <= bad;
        for (i = 0; i < P; i = i + 1) begin
            f_y[i*M*32 +: M*32] <= hd[i*EW + M +: M*32];
            f_f[i*M +: M] <= hd[i*EW +: M] | {M{bad}};
        end
    end

    // the top S levels of the row's padded pairwise tree, fixed order
    wire [(S+1)*P*M*32-1:0] TV;
    wire [(S+1)*P*M-1:0]    TF;
    wire [(S+1)*TGW-1:0]    TT;
    wire [S:0]              TVV;
    assign TV[P*M*32-1:0] = f_y; assign TF[P*M-1:0] = f_f; assign TT[TGW-1:0] = f_tag; assign TVV[0] = f_v;
    generate
        for (l = 1; l <= S; l = l + 1) begin : g_lvl
            localparam integer NN = P >> l;
            wire [NN-1:0]      av;
            wire [NN*TGW-1:0]  at;
            wire [NN*M*32-1:0] ay;
            wire [NN*M-1:0]    af;
            for (n = 0; n < NN; n = n + 1) begin : g_n
                ot_hdc_v41x_wgt_add #(.M(M), .TW(TGW)) u_a (
                    .clk(clk), .rst_n(rst_n), .v(TVV[l-1]),
                    .a(TV[(l-1)*P*M*32 + (2*n)*M*32 +: M*32]), .af(TF[(l-1)*P*M + (2*n)*M +: M]),
                    .b(TV[(l-1)*P*M*32 + (2*n+1)*M*32 +: M*32]), .bf(TF[(l-1)*P*M + (2*n+1)*M +: M]),
                    .t(TT[(l-1)*TGW +: TGW]), .ov(av[n]), .y(ay[n*M*32 +: M*32]), .yf(af[n*M +: M]),
                    .ot(at[n*TGW +: TGW]));
            end
            assign TVV[l] = av[0];
            assign TT[l*TGW +: TGW] = at[TGW-1:0];
            assign TV[l*P*M*32 +: P*M*32] = {{((P-NN)*M*32){1'b0}}, ay};
            assign TF[l*P*M +: P*M] = {{((P-NN)*M){1'b0}}, af};
        end
    endgenerate

    reg [32:0] rb;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) o_v <= 1'b0;
        else o_v <= TVV[S];
    end
    always @(posedge clk) begin
        o_tag <= TT[S*TGW +: TGW];
        o_y <= TV[S*P*M*32 +: M*32];
        o_f <= TF[S*P*M +: M];
        for (i = 0; i < M; i = i + 1) begin
            rb = {1'b0, TV[S*P*M*32 + 32*i +: 32]} + 33'h7FFF + {32'd0, TV[S*P*M*32 + 32*i + 16]};
            o_bf[16*i +: 16] <= rb[31:16];
        end
    end
endmodule
