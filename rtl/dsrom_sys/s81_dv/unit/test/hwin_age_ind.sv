`timescale 1ns/1ps
// FABLE-FIX-S81-SEQHOST (2026-11-19): induction harness of dsdv_mu_hwin_age (yosys sat -tempinduct, run_mu_hwin_eq.sh).
// Definition (the former source, per entry): the entry is written at tm = ts; a = (tm - ts) mod 2^32;
//   mf[e] = (ts + D[e] == tm) = (a == D[e]);  lf[e] = (ts + D[e] - tm > 32'h7fffffff) = bit 31 of (D[e] - a);
//   df = (ts + RL - 1 == tm) = (a == RL - 1).
// D / RL are constants here (they only change while no entry is valid; the same-edge write is the *_n bypass of the
// module, exercised by the lockstep bench).  ok = "since the first write the cell's flags, age and helper flags equal
// the definition"; the helper terms make the property inductive.  ok must hold on every edge.
module hwin_age_ind #(parameter integer NEV = 2) (
    input  wire ck,
    input  wire wr,
    input  wire [NEV*21-1:0] d_in,          // D / RL: free until the first write, constant from it on
    input  wire [23:0] rl_in,
    output wire ok
);
    reg [NEV*21-1:0] Dr; reg [23:0] RLr; reg [31:0] a; reg seen;
    wire [NEV*21-1:0] D = seen ? Dr : d_in; wire [23:0] RL = seen ? RLr : rl_in;
    wire [31:0] rlm1 = {8'd0, RL} - 32'd1;
    always @(posedge ck) begin Dr <= D; RLr <= RL; a <= wr ? 32'd1 : a + 32'd1; seen <= seen | wr; end
    wire [NEV-1:0] e1, e0, mf, lf, smf, slf; wire df;
    genvar g;
    generate for (g = 0; g < NEV; g = g + 1) begin : g_e
        wire [31:0] d = {11'd0, D[21*g +: 21]};
        wire [31:0] diff = d - a;
        assign e1[g] = d == 32'd1; assign e0[g] = d == 32'd0;
        assign smf[g] = a == d; assign slf[g] = diff[31];
    end endgenerate
    dsdv_mu_hwin_age #(.NEV(NEV)) dut (.ck(ck), .wr(wr), .eD(D), .e1n(e1), .e0n(e0), .crlm1(rlm1), .c2n(RL == 24'd2),
        .mf(mf), .lf(lf), .df(df));
    wire [NEV-1:0] slm; 
    generate for (g = 0; g < NEV; g = g + 1) begin : g_l assign slm[g] = a[20:0] == D[21*g +: 21]; end endgenerate
    // cell internals: tied to dut.b / dut.lm / dut.hz / dut.hc by "connect -set" after flatten (run_mu_hwin_eq.sh)
    (* keep *) wire [31:0] p_b; (* keep *) wire [NEV-1:0] p_lm; (* keep *) wire p_hz, p_hc;
    wire inv = p_b == a + 32'd1 && p_lm == slm && p_hz == (a[31:21] == 11'd0) && p_hc == (a[31:21] == 11'h400);
    assign ok = !seen || (mf == smf && lf == slf && df == (a == rlm1) && inv);
endmodule
