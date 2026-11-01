`timescale 1ns/1ps
`default_nettype none
// Register-file delay line, cycle-exact equivalent of ot_hdc_delay #(W,D,RESET=0) for D >= 3:
// q is d delayed by exactly D edges. Structure: pin input register -> circular buffer of N = D-2 rows
// (one row written per edge at wptr, oldest row read through an N:1 mux) -> pin output register.
// Why (H-IDX 2026-10-15, hidx_meta W25/D123): the shift-register form is 3,075 back-to-back flop->flop hops
// with zero logic; at FF hold + 30 ps margin every one is a hold endpoint and the hold ECO could not pad 3,100
// endpoints in the tile (2,211 cells added, still -2.14 ps). Here only 25 data flops toggle per edge, the
// row-write path crosses the write-enable mux and the read path crosses the N:1 mux tree, so no zero-logic
// flop->flop hop remains. Data carries no reset (as RESET=0). wptr carries no reset either: any start value
// converges (>= N-1 wraps to 0) within 2^k - N + 1 edges of power-up, before the line has filled; a reset
// pulse therefore never disturbs data (same as the shift form).
module ot_hdc_delay_rf #(
    parameter integer W = 32,
    parameter integer D = 3,
    // OH=1 (opt-in, HBM-CORES-KITS-37 10-31; idx_query_static TT setup -30.8 ps on mem[r] D from the binary wptr
    // decode + fanout trees): a registered one-hot row select we_q[N-1:0] (we_q[r] <= wptr_next == r, so
    // we_q == onehot(wptr) on every edge after the first) gates the row writes (mem[r] <= din when we_q[r]) and the
    // read (dout <= OR_r we_q[r] & mem[r], an AND-OR mux). One set of N registers, no reset, no replicas; wptr and
    // its wrap stay as in OH=0. Same values on every edge after the first (wptr itself converges as in OH=0);
    // OH=0 (default) = the historical binary-pointer form, unchanged.
    parameter integer OH = 0
) (
    input  wire         clk,
    input  wire         rst_n,      // unused: kept for port identity with ot_hdc_delay
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer N = D - 2;
    localparam integer K = (N <= 2) ? 1 : $clog2(N);
    localparam [K-1:0] LAST = N - 1;
    reg [W-1:0] din, dout;
    reg [W-1:0] mem [0:N-1];
    reg [K-1:0] wptr;
`ifndef SYNTHESIS
    initial wptr = {K{1'b0}};
`endif
    generate if (OH == 0) begin : g_bin
    always @(posedge clk) begin
        din <= d;
        mem[wptr] <= din;
        dout <= mem[wptr];
        wptr <= (wptr >= LAST) ? {K{1'b0}} : wptr + 1'b1;
    end
    end else begin : g_oh
        wire [K-1:0] wptr_next = (wptr >= LAST) ? {K{1'b0}} : wptr + 1'b1;
        reg  [N-1:0] we_q;
`ifndef SYNTHESIS
        initial we_q = 1;   // onehot(0), the same start as wptr
`endif
        reg  [W-1:0] rd_oh;
        integer r;
        always @* begin
            rd_oh = {W{1'b0}};
            for (r = 0; r < N; r = r + 1) rd_oh = rd_oh | ({W{we_q[r]}} & mem[r]);
        end
        integer s;
        always @(posedge clk) begin
            din <= d;
            for (s = 0; s < N; s = s + 1) if (we_q[s]) mem[s] <= din;
            dout <= rd_oh;
            for (s = 0; s < N; s = s + 1) we_q[s] <= (wptr_next == s);
            wptr <= wptr_next;
        end
    end endgenerate
    assign q = dout;
    wire unused_rst = rst_n;
endmodule
`default_nettype wire
