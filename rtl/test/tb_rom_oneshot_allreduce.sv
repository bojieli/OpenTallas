`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Unit bench of rtl/rom/ot_rom_oneshot_allreduce.sv (Verilator).
//
// +VEC/part.hex holds NMSG messages of WORDS words per die (message m, die d,
// word w at (m*N + d)*WORDS + w), +VEC/mode.hex each message's mode (0
// all-reduce, 1 all-gather) and +VEC/sum.hex the rank-order sum of every
// all-reduce word (tools/hdc_golden.fold).  Every die sends its messages in
// order, with random gaps (+GAP percent), tagged with the message number.
// Every die checks every output word: an all-reduce word against sum.hex, an
// all-gather word (index-major, rank order) against the sender's word, and
// its rank.  +INJECT=m: die 2 corrupts word 0 lane 3 of message m (+IVAL, a
// NaN by default) -- the bench then expects every die to fault instead.
// +SKEW=c: die d starts c*d cycles late (arrival order differs per die).
// Prints cycles from the first send to the last result and the words per
// cycle sustained.
// ---------------------------------------------------------------------------
module tb_rom_oneshot_allreduce #(
    parameter integer N = 4,
    parameter integer LANES = 16,
    parameter integer DEPTH = 16,
    parameter integer LAT = 12,
    parameter integer BPC = 3600
) (input wire clk);
    localparam integer FW = 32 * LANES, TAGW = 32, RB = $clog2(N), MAXW = 1 << 16;
    reg [FW-1:0] part [0:MAXW-1];
    reg [FW-1:0] sum  [0:MAXW-1];
    reg          mode [0:4095];
    integer NMSG, WORDS, GAP, SEED, INJECT, SKEW;
    reg [31:0] IVAL;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    wire [N-1:0] iv, ir, il, im, ov, ol, oe, flt;
    wire [N*FW-1:0] id, od;
    wire [N*TAGW-1:0] it;
    wire [N*RB-1:0] orank;
    wire [N*3-1:0] fc;
    wire [31:0] stalls;
    ot_rom_oneshot_allreduce #(.N(N), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .LAT(LAT), .BPC_NUM(BPC)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(iv), .in_ready(ir), .in_data(id), .in_last(il), .in_mode(im),
        .in_tag(it), .out_valid(ov), .out_data(od), .out_last(ol), .out_rank(orank), .out_err(oe),
        .fault(flt), .fault_code(fc), .link_stalls(stalls));

    function [31:0] xs(input [31:0] v0);
        reg [31:0] v;
        begin v = v0 ^ (v0 << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction
    integer bad = 0, words_out = 0, first = -1, lastc = 0, errs = 0;
    integer done_n = 0;
    genvar g;
    generate
        for (g = 0; g < N; g = g + 1) begin : g_die
            // sender
            integer m = 0, w = 0;
            reg go = 1'b0;
            reg [31:0] rnd = 32'h9e3779b9 * (g + 1);
            always @(posedge clk) begin
                if (cyc == 1) rnd <= 32'h9e3779b9 * (g + 1) ^ SEED;
                else rnd <= xs(rnd);
                go <= rst_n && (cyc >= 20 + SKEW * g) && ((rnd % 100) >= GAP);
                if (iv[g] && ir[g]) begin
                    if (first < 0) first = cyc;
                    if (w == WORDS - 1) begin w = 0; m = m + 1; end else w = w + 1;
                end
            end
            reg [FW-1:0] word;
            always @(*) begin
                word = part[(m*N + g)*WORDS + w];
                if (INJECT == m && g == 2 && w == 0) word[3*32 +: 32] = IVAL;
            end
            assign iv[g] = go && m < NMSG;
            assign id[g*FW +: FW] = word;
            assign il[g] = (w == WORDS - 1);
            assign im[g] = mode[m];
            assign it[g*TAGW +: TAGW] = m;
            // checker
            integer rm = 0, rk = 0;      // message, output word within it
            reg [FW-1:0] exp;
            integer per;
            always @(posedge clk) if (ov[g]) begin
                per = mode[rm] ? N * WORDS : WORDS;
                if (oe[g]) errs = errs + 1;
                if (mode[rm]) begin
                    exp = part[(rm*N + rk % N)*WORDS + rk / N];
                    if (orank[g*RB +: RB] != rk % N) begin
                        bad = bad + 1;
                        if (bad < 5) $display("RANK die=%0d msg=%0d word=%0d rank=%0d", g, rm, rk, orank[g*RB +: RB]);
                    end
                end else begin
                    exp = sum[rm*WORDS + rk];
                end
                if (od[g*FW +: FW] !== exp && INJECT < 0) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH die=%0d msg=%0d word=%0d mode=%0d", g, rm, rk, mode[rm]);
                end
                if (ol[g] != (rk == per - 1)) begin
                    bad = bad + 1;
                    if (bad < 5) $display("LAST die=%0d msg=%0d word=%0d last=%0d", g, rm, rk, ol[g]);
                end
                words_out = words_out + 1; lastc = cyc;
                if (rk == per - 1) begin
                    rk = 0; rm = rm + 1;
                    if (rm == NMSG) done_n = done_n + 1;
                end else rk = rk + 1;
            end
        end
    endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NMSG=%d", NMSG)) NMSG = 16;
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 8;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("INJECT=%d", INJECT)) INJECT = -1;
        if (!$value$plusargs("IVAL=%h", IVAL)) IVAL = 32'h7fc00000;
        if (!$value$plusargs("SKEW=%d", SKEW)) SKEW = 0;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sum);
        $readmemh({dir, "/mode.hex"}, mode);
    end

    always @(posedge clk) begin
        if (done_n == N || (INJECT >= 0 && cyc > 2000 + NMSG * WORDS * 8)) begin
            $display("ONESHOT n=%0d depth=%0d lat=%0d msgs=%0d words=%0d gap=%0d skew=%0d inject=%0d mismatches=%0d out_err=%0d fault=%b code=%b words_out=%0d first=%0d last=%0d link_stalls=%0d",
                     N, DEPTH, LAT, NMSG, WORDS, GAP, SKEW, INJECT, bad, errs, flt, fc, words_out, first, lastc, stalls);
            if (INJECT < 0) begin
                if (bad == 0 && flt == 0 && errs == 0 && done_n == N) $display("PASS"); else $display("FAIL");
            end else begin
                if (flt == {N{1'b1}} && errs >= N) $display("PASS"); else $display("FAIL");
            end
            $finish;
        end
        if (cyc > 5000000) begin $display("TIMEOUT"); $finish; end
    end
endmodule
