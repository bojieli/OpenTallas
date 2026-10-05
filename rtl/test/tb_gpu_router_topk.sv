`timescale 1ns/1ps
// Exactness bench of rtl/gpu/ot_gpu_router_topk.sv: NV router vectors of N FP32 values from VEC (hex, one value
// a line), streamed back to back at P values a beat; prints every selection (ascending ids) and the latency
// from a vector's last beat to its selection.  tools/rtl_w19_expert_fetch.py compares them with the golden.
module tb_gpu_router_topk;
    parameter integer N = 384, P = 16, K = 6, NV = 1;
    parameter VEC = "rt.hex";
    localparam integer IW = 9;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [31:0] mem [0:N*NV-1];
    reg in_valid = 0, in_last = 0;
    reg [P*32-1:0] in_vals;
    wire out_valid;
    wire [K*IW-1:0] out_ids;
    ot_gpu_router_topk #(.N(N), .P(P), .K(K), .IW(IW)) dut (.clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_vals(in_vals), .in_last(in_last), .out_valid(out_valid), .out_ids(out_ids));
    integer v, b, j, got = 0, cyc = 0, t_last [0:NV-1];
    always @(posedge clk) cyc <= cyc + 1;
    always @(posedge clk) if (out_valid) begin
        $write("TOPK %0d lat=%0d", got, cyc - t_last[got]);
        for (j = 0; j < K; j = j + 1) $write(" %0d", out_ids[j*IW +: IW]);
        $write("\n");
        got = got + 1;
    end
    initial begin
        $readmemh(VEC, mem);
        repeat (3) @(posedge clk);
        rst_n = 1;
        for (v = 0; v < NV; v = v + 1)
            for (b = 0; b < N / P; b = b + 1) begin
                @(negedge clk);
                in_valid = 1; in_last = (b == N / P - 1);
                for (j = 0; j < P; j = j + 1) in_vals[32*j +: 32] = mem[v * N + b * P + j];
                if (in_last) t_last[v] = cyc;
            end
        @(negedge clk); in_valid = 0; in_last = 0;
        wait (got == NV);
        repeat (2) @(posedge clk);
        $display("TOPKDONE vectors=%0d", got);
        $finish;
    end
    initial begin #10000000; $display("TOPK TIMEOUT"); $finish; end
endmodule
