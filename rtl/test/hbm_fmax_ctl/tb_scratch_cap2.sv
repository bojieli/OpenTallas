`timescale 1ns/1ps
// Transaction lockstep: ot_gpu_scratch_service CAP2 = 0 (as built) vs CAP2 = 1, each driven with the same
// NTX random reads / writes (clustered addresses so reads hit written lines, random done_ready back-pressure,
// random idle gaps).  Every completed transaction's rdata must be equal; each read must take exactly one cycle more.
module tb_scratch_cap2;
    parameter integer NTX = 4000, SEED = 1;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg  [0:0]   wr [0:NTX-1];
    reg  [9:0]   ad [0:NTX-1];
    reg  [511:0] wd [0:NTX-1];
    reg  [3:0]   hold [0:NTX-1];
    reg  [511:0] r0 [0:NTX-1], r1 [0:NTX-1];
    integer l0 [0:NTX-1], l1 [0:NTX-1];
    integer seed, t, bad = 0, reads = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
`define PORT(I, C) \
    reg v``I = 0, w``I = 0, dr``I = 0; reg [9:0] a``I = 0; reg [511:0] d``I = 0; wire rdy``I, dn``I; wire [511:0] q``I; \
    integer n``I = 0, c``I = 0, ts``I = 0, hc``I = 0; \
    ot_gpu_scratch_service #(.CAP2(C)) u``I (.clk(clk), .rst_n(rst_n), .valid(v``I), .write(w``I), .ready(rdy``I), \
        .addr(a``I), .wdata(d``I), .done(dn``I), .done_ready(dr``I), .rdata(q``I)); \
    always @(posedge clk) if (rst_n) begin \
        if (v``I && rdy``I) begin ts``I = cyc; v``I <= 0; end \
        if (dn``I && dr``I) begin r``I[c``I] = q``I; c``I = c``I + 1; dr``I <= 0; end \
    end \
    always @(negedge clk) if (rst_n) begin \
        if (dn``I && !dr``I) begin if (hc``I == 0) begin dr``I <= 1; l``I[c``I] = cyc - ts``I; end else hc``I = hc``I - 1; end \
        if (!v``I && !dn``I && n``I < NTX && c``I == n``I) begin \
            v``I <= 1; w``I <= wr[n``I]; a``I <= ad[n``I]; d``I <= wd[n``I]; hc``I = hold[n``I]; n``I = n``I + 1; end \
    end
    `PORT(0, 0)
    `PORT(1, 1)
    initial begin
        seed = SEED;
        for (t = 0; t < NTX; t = t + 1) begin
            wr[t] = $random(seed); ad[t] = $unsigned($random(seed)) % 64 + ((t % 7 == 0) ? $unsigned($random(seed)) % 1024 : 0);
            wd[t] = {16{$random(seed)}}; hold[t] = ($random(seed) & 3) == 0 ? $unsigned($random(seed)) % 4 : 0;
        end
        repeat (3) @(posedge clk); rst_n = 1;
        wait (c0 == NTX && c1 == NTX);
        for (t = 0; t < NTX; t = t + 1) begin
            if (r0[t] !== r1[t]) begin bad = bad + 1; if (bad < 5) $display("MISMATCH data tx %0d", t); end
            if (l1[t] - l0[t] != (wr[t] ? 0 : 1)) begin bad = bad + 1; if (bad < 5) $display("MISMATCH latency tx %0d %0d %0d", t, l0[t], l1[t]); end
            if (!wr[t]) reads = reads + 1;
        end
        $display("LOCKSTEP scratch tx=%0d reads=%0d mismatches=%0d (read latency +1, write +0)", NTX, reads, bad);
        $finish;
    end
endmodule
