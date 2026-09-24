`timescale 1ns/1ps
// Drives ot_hdc_blockdot with golden linear_q rows, IL rows in flight on the
// lane's circulating accumulator, with random bubbles and random idle slots,
// and checks every row's FP32 sum and BF16 result bit for bit, in order.
//   bd_blk.mem  per block {meta[31:0] = {11'b0, fp4, xe[9:0], we[9:0]}, xq[255:0], wq[255:0]}
//   bd_job.mem  per row   {start[31:0], nblk[15:0], flags[15:0]}  (flags[0]: fault expected)
//   bd_exp.mem  per row   {acc[31:0], y[15:0]}
// A slot is the cycle count mod IL (the ring's period), so the element this
// bench presents in a cycle joins the sum of the row it assigned to that slot.
// +NBLK / +NJOB counts; +SEED; +BUBBLE in 1/16ths (0: every cycle issues, II = 1).
module tb_hdc_v41_blockdot #(
    parameter integer MAXB = 1 << 19,
    parameter integer MAXJ = 1 << 18,
    parameter integer IL = 8
) (input wire clk);
    reg [543:0] blk [0:MAXB-1];
    reg [63:0]  job [0:MAXJ-1];
    reg [47:0]  exq [0:MAXJ-1];
    integer nblk = 0, njob = 0, bubble = 4;
    reg [31:0] seed = 32'h13579bdf;
    initial begin
        if (!$value$plusargs("NBLK=%d", nblk)) nblk = 0;
        if (!$value$plusargs("NJOB=%d", njob)) njob = 0;
        if (!$value$plusargs("SEED=%d", seed)) seed = 32'h13579bdf;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 4;
        if (nblk > 0) $readmemh("bd_blk.mem", blk, 0, nblk - 1);
        if (njob > 0) begin
            $readmemh("bd_job.mem", job, 0, njob - 1);
            $readmemh("bd_exp.mem", exq, 0, njob - 1);
        end
    end
    function automatic [31:0] xs(input [31:0] s);
        reg [31:0] t;
        begin t = s ^ (s << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction

    reg rst_n = 1'b0;
    reg              v = 1'b0, first = 1'b0, last = 1'b0, fp4 = 1'b0;
    reg [255:0]      xq = 0, wq = 0;
    reg signed [9:0] xe = 0, we = 0;
    wire [$clog2(IL)-1:0] phase;
    wire        ov, fault;
    wire [15:0] y;
    wire [31:0] acc;
    ot_hdc_blockdot #(.IL(IL)) dut (.clk(clk), .rst_n(rst_n), .v(v), .first(first), .last(last), .fp4(fp4),
                                    .xq(xq), .xe(xe), .wq(wq), .we(we), .phase(phase), .ov(ov), .y(y),
                                    .acc(acc), .fault(fault));

    // per-slot schedule
    integer act [0:IL-1];
    integer nb  [0:IL-1];
    integer eb  [0:IL-1];
    integer jb  [0:IL-1];
    // rows in the order their last block went in
    integer fifo [0:MAXJ-1];
    integer fw = 0, fr = 0;
    integer cyc = 0, slot = 0, nextj = 0, errors = 0, faults_ok = 0, bubbles = 0, idle = 0, k, busy;
    integer blocks_in = 0, phase_bad = 0;
    reg [543:0] b;
    reg [47:0]  e;
    initial for (k = 0; k < IL; k = k + 1) act[k] = 0;
    always @(posedge clk) begin
        cyc = cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        slot = cyc % IL;
        v <= 1'b0; first <= 1'b0; last <= 1'b0;
        xq <= {8{seed}}; wq <= {8{~seed}};                    // bubbles carry junk
        if (cyc > 6) begin
            seed = xs(seed);
            if (!act[slot] && nextj < njob && (bubble == 0 || seed[4])) begin  // slots also start rows late
                act[slot] = 1; jb[slot] = nextj; nb[slot] = job[nextj][63:32];
                eb[slot] = job[nextj][63:32] + job[nextj][31:16]; nextj = nextj + 1;
            end
            if (act[slot] && seed[3:0] >= bubble) begin
                b = blk[nb[slot]];
                v <= 1'b1;
                first <= (nb[slot] == job[jb[slot]][63:32]);
                last <= (nb[slot] + 1 == eb[slot]);
                fp4 <= b[532]; xe <= b[531:522]; we <= b[521:512];
                xq <= b[511:256]; wq <= b[255:0];
                blocks_in = blocks_in + 1;
                nb[slot] = nb[slot] + 1;
                if (nb[slot] == eb[slot]) begin
                    act[slot] = 0; fifo[fw] = jb[slot]; fw = fw + 1;
                end
            end else if (act[slot]) bubbles = bubbles + 1;
        end
        if (rst_n && ov) begin
            e = exq[fifo[fr]];
            if (job[fifo[fr]][0]) begin
                if (fault !== 1'b1) begin
                    if (errors < 10) $display("BD MISSING FAULT row=%0d", fifo[fr]);
                    errors = errors + 1;
                end else faults_ok = faults_ok + 1;
            end else if (fault !== 1'b0 || acc !== e[47:16] || y !== e[15:0]) begin
                if (errors < 10) $display("BD MISMATCH row=%0d fault=%b acc=%h/%h y=%h/%h", fifo[fr], fault,
                                          acc, e[47:16], y, e[15:0]);
                errors = errors + 1;
            end
            fr = fr + 1;
        end
        busy = 0;
        for (k = 0; k < IL; k = k + 1) busy = busy | act[k];
        if (nextj == njob && !busy && fr == fw) idle = idle + 1;
        if (idle == 40 || cyc > 100 + 40 * (nblk + njob)) begin
            $display("V41BD rows=%0d checked=%0d errors=%0d faults_expected_and_raised=%0d blocks=%0d bubbles=%0d cycles=%0d",
                     njob, fr, errors, faults_ok, blocks_in, bubbles, cyc);
            if (errors == 0 && fr == njob && blocks_in == nblk) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule

`ifndef VERILATOR
module tb_hdc_v41_blockdot_icarus;
    reg clk = 1'b0;
    always #0.5 clk = ~clk;
    tb_hdc_v41_blockdot #(.MAXB(1 << 14), .MAXJ(1 << 12)) u (.clk(clk));
endmodule
`endif
