// Minimal repro of the DS V4.1 HBM system multi-thread divergence (ot_gpu_simt_sm.sv bd_xd, fixed 2026-10-04).
// A register written with a BLOCKING assignment in one clocked process (xd) and sampled by another clocked process
// on a later edge is an IEEE same-edge race.  Verilator 5.050 single-threaded orders the reader after the writer
// (deterministic, but the reader sees the value written on the SAME edge); with --threads the two processes run
// unordered and the result changes from run to run.  Sharing loop temporaries (jj/lj) between a combinational and a
// clocked block is NOT the cause (variant B below keeps nondeterminism; variant A alone removes it).
//   V=verilator; $V --binary --timing -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH --top-module top --threads 8 \
//     rtl/test/gpu_sys/repro_verilator_threads_blkseq.sv && for r in 1 2 3; do obj_dir/Vtop; done
// Measured (Verilator 5.050): single-thread HASH 02b57dc0 every run; --threads 8: 06b98c9c, b056f1f2, 1887534d.
// With `xd <= ...` (the fix, variant A): HASH e4534140 for 1 and 8 threads, every run.
// Minimal repro: a module-scope loop temporary (jj/lj) written by BOTH a combinational always @* block and a
// clocked block, plus a blocking-assigned data register (xd) sampled by a sibling's clocked block on the next edge.
module leaf #(parameter integer SEED = 1) (input wire clk, input wire [31:0] in, output reg [31:0] acc);
    integer jj; reg [7:0] lj;
    reg [255:0] comb_y; reg [255:0] buf_q;
    always @* begin
        comb_y = 256'd0;
        for (jj = 0; jj < 32; jj = jj + 1) begin lj = jj[7:0] + in[7:0]; comb_y[jj*8 +: 8] = lj ^ buf_q[jj*8 +: 8]; end
    end
    reg [255:0] xd; reg xw; reg [255:0] xmem;
    always @(posedge clk) begin
        for (jj = 0; jj < 32; jj = jj + 1) begin lj = in[15:8] + jj[7:0] * SEED; buf_q[jj*8 +: 8] <= lj ^ comb_y[jj*8 +: 8]; end
        xw <= in[0];
        if (in[0]) xd = {8{in}} ^ comb_y;          // blocking write of a register sampled below on the next edge
    end
    always @(posedge clk) if (xw) xmem <= xd;
    always @(posedge clk) acc <= acc * 33 ^ xmem[31:0] ^ xmem[255:224] ^ buf_q[63:32];
    initial acc = 0;
endmodule
module top;
    reg clk = 0; always #1 clk = ~clk;
    reg [31:0] lfsr = 32'h1;
    always @(posedge clk) lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
    localparam N = 64;
    wire [31:0] acc [0:N-1];
    genvar g;
    for (g = 0; g < N; g++) begin : g_l
        leaf #(.SEED(g + 1)) u (.clk(clk), .in(lfsr ^ g), .acc(acc[g]));
    end
    integer c = 0; reg [31:0] h;
    always @(posedge clk) begin
        c <= c + 1;
        if (c == 20000) begin h = 0; for (int i = 0; i < N; i++) h = h * 31 ^ acc[i]; $display("HASH %08h", h); $finish; end
    end
endmodule
