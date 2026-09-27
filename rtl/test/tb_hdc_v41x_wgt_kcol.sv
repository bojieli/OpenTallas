`timescale 1ns/1ps
// Bench of ot_hdc_v41x_wgt_kcol (cross-tile K-split collector), driven by tests/test_hdc_v41x_wgt.py.
// +in: per row r and part p (index r*P + p) one 33-bit word {fault, fp32 part root}; +exp: per row
// one 49-bit word {fault, bf16, fp32}.  Every port pushes its parts with an independent pseudo-random
// stall (+stall=N: stall with probability N/8), so the ports run skewed against each other.
// Summary: "V41XKCOL rows=.. errors=.. cycles=..".
module tb_hdc_v41x_wgt_kcol #(
    parameter integer S = 1,
    parameter integer NR = 64
) (
    input wire clk
);
    localparam integer P = 1 << S;
    reg rst_n = 1'b0;
    reg [32:0] inm [0:NR*P-1];
    reg [48:0] expm [0:NR-1];
    reg  [P-1:0]      in_v;
    wire [P-1:0]      in_rdy;
    reg  [P*16-1:0]   in_tag;
    reg  [P*32-1:0]   in_y;
    reg  [P-1:0]      in_f;
    wire              o_v;
    wire [15:0]       o_tag;
    wire [31:0]       o_y;
    wire [15:0]       o_bf;
    wire [0:0]        o_f;
    ot_hdc_v41x_wgt_kcol #(.S(S), .M(1), .TGW(16), .DEPTH(8)) dut (
        .clk(clk), .rst_n(rst_n), .in_v(in_v), .in_rdy(in_rdy), .in_tag(in_tag), .in_y(in_y), .in_f(in_f),
        .o_v(o_v), .o_tag(o_tag), .o_y(o_y), .o_bf(o_bf), .o_f(o_f));
    string fi, fe;
    integer stall, cyc, nout, errors, p;
    integer idx [0:P-1];
    reg [31:0] lf [0:P-1];
    initial begin
        if (!$value$plusargs("in=%s", fi)) $fatal(1, "+in");
        if (!$value$plusargs("exp=%s", fe)) $fatal(1, "+exp");
        if (!$value$plusargs("stall=%d", stall)) stall = 0;
        $readmemh(fi, inm);
        $readmemh(fe, expm);
        cyc = 0; nout = 0; errors = 0; in_v = 0;
        for (p = 0; p < P; p = p + 1) begin idx[p] = 0; lf[p] = 32'h9E3779B9 * (p + 1); end
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (rst_n) begin
            for (p = 0; p < P; p = p + 1) begin
                if (in_v[p] && in_rdy[p]) idx[p] = idx[p] + 1;
                lf[p] = {lf[p][30:0], lf[p][31] ^ lf[p][21] ^ lf[p][1] ^ lf[p][0]};
                if (idx[p] < NR && (lf[p] % 8) >= stall) begin
                    in_v[p] <= 1'b1;
                    in_tag[p*16 +: 16] <= idx[p];
                    in_y[p*32 +: 32] <= inm[idx[p]*P + p][31:0];
                    in_f[p] <= inm[idx[p]*P + p][32];
                end else in_v[p] <= 1'b0;
            end
            if (o_v) begin
                if (o_tag != nout || o_f[0] != expm[nout][48] ||
                    (!o_f[0] && (o_y != expm[nout][31:0] || o_bf != expm[nout][47:32]))) begin
                    errors = errors + 1;
                    if (errors < 8) $display("V41XKCOL_ERR row %0d tag %0d y %h/%h f %0d/%0d", nout, o_tag, o_y,
                                             expm[nout][31:0], o_f[0], expm[nout][48]);
                end
                nout = nout + 1;
                if (nout == NR) begin
                    $display("V41XKCOL rows=%0d errors=%0d cycles=%0d", nout, errors, cyc);
                    $finish;
                end
            end
        end
        if (cyc > 100000) begin $display("V41XKCOL TIMEOUT rows=%0d", nout); $finish; end
    end
endmodule
