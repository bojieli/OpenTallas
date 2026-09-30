`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// RESIDUAL ROTATE NETWORK of the distributed vector memory, option H
// (results/uarch/w11_vm_options.json; rtl/hdc/v41x/ot_hdc_v41x_vec.sv VMD_NG).
// A pipelined logarithmic rotator over N lanes of W bits: q[l] = d[(l + k) mod N],
// log2(N) levels of 2:1 multiplexers (level j moves by 2^j when k[j] is set), a
// register after every LPS levels, input and output registered.  Latency =
// 1 + ceil(log2(N) / LPS) cycles (the input register, then one a stage); the
// shift travels beside the data.  Built to MEASURE how many mux levels fit one
// 0.92 ns stage (tools/w11_vm_options.py MUX_LEVELS_PER_STAGE); the wire
// crossing of the SU + VM block is priced separately (uarch_model.wire_cycles).
// ---------------------------------------------------------------------------
module ot_v41_vm_rot #(
    parameter integer N   = 1024,
    parameter integer W   = 32,
    parameter integer LPS = 8,               // mux levels a pipeline stage
    parameter integer LN  = $clog2(N)
) (
    input  wire           clk,
    input  wire [N*W-1:0] d,
    input  wire [LN-1:0]  k,
    output wire [N*W-1:0] q
);
    localparam integer NS = (LN + LPS - 1) / LPS;
    reg  [N*W-1:0] x_r;
    reg  [LN-1:0]  k_r;
    always @(posedge clk) begin x_r <= d; k_r <= k; end
    // level j: y[l] = k[j] ? x[(l + 2^j) mod N] : x[l]
    wire [N*W-1:0] lv [0:LN];
    wire [LN-1:0]  kv [0:LN];
    assign lv[0] = x_r;
    assign kv[0] = k_r;
    genvar j, l;
    generate for (j = 0; j < LN; j = j + 1) begin : g_lvl
        wire [N*W-1:0] y;
        for (l = 0; l < N; l = l + 1) begin : g_lane
            assign y[l*W +: W] = kv[j][j] ? lv[j][((l + (1 << j)) % N)*W +: W] : lv[j][l*W +: W];
        end
        if (((j + 1) % LPS) == 0 || j == LN - 1) begin : g_reg
            reg [N*W-1:0] r;
            reg [LN-1:0]  kr;
            always @(posedge clk) begin r <= y; kr <= kv[j]; end
            assign lv[j+1] = r;
            assign kv[j+1] = kr;
        end else begin : g_wire
            assign lv[j+1] = y;
            assign kv[j+1] = kv[j];
        end
    end endgenerate
    assign q = lv[LN];
endmodule
