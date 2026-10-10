`timescale 1ns/1ps
// hbm-forks 2026-10-09: CF-ARG for ot_dshbm_argmax_m at IW 18 (HGI-1: IW 17 -> 18 universal, no mode field).
//   CF-1  lockstep: IW 18 vs the closed IW 17 element on DS rows (<= 129,280 elements; random values incl. NaN, -0, +0,
//         ties; bias on / off), every output every cycle (out_idx zero-extended), FAST 0 and FAST 1.
//   Qwen  rows of 151,936 (the full vocabulary on one die) and the TP4 shard 37,984 against a behavioural numpy.argmax
//         (lowest index of the max, -0 == +0, first NaN wins): the max planted at 151,935, at 131,072 (bit 17), a tie
//         at 131,071 / 151,935 (lowest wins), a NaN at 140,000 after a larger finite value.
// Prints HGI_ARGMAX PASS / FAIL.
module tb_hgi_argmax;
    parameter integer FAST = 0;
    localparam integer LP = 8;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    reg in_v = 0, in_last = 0, in_bias_en = 0; reg [LP-1:0] in_mask = 0; reg [LP*32-1:0] in_vals = 0, in_bias = 0;
    wire ov17, ov18, on17, on18, f17, f18; wire [16:0] oi17; wire [17:0] oi18;
    ot_dshbm_argmax_m #(.LP(LP), .IW(17), .FAST(FAST)) ref_ (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_last(in_last),
        .in_bias_en(in_bias_en), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias), .out_v(ov17), .out_idx(oi17),
        .out_nan(on17), .fault(f17));
    ot_dshbm_argmax_m #(.LP(LP), .IW(18), .FAST(FAST)) dut (.clk(clk), .rst_n(rst_n), .in_v(in_v), .in_last(in_last),
        .in_bias_en(in_bias_en), .in_mask(in_mask), .in_vals(in_vals), .in_bias(in_bias), .out_v(ov18), .out_idx(oi18),
        .out_nan(on18), .fault(f18));
    reg ls = 1; integer mism = 0, fails = 0, rows = 0;
    always @(posedge clk) if (rst_n && ls && ({ov18, on18, f18} !== {ov17, on17, f17} || (ov18 && oi18 !== {1'b0, oi17}))) begin
        mism = mism + 1; if (mism < 4) $display("LOCKSTEP_MISMATCH idx %0d/%0d", oi18, oi17);
    end
    // the expected answer of a row (no bias): numpy.argmax on FP32
    function automatic [32:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) okey = {1'b1, 32'hFFFF_FFFF};
            else begin c = (x == 32'h8000_0000) ? 32'd0 : x; okey = {1'b0, c[31] ? ~c : (c | 32'h8000_0000)}; end
        end
    endfunction
    reg [31:0] row [0:151935];
    integer exp_idx; reg [32:0] bk;
    task send_row(input integer n, input integer bias);
        integer b, j, i;
        begin
            exp_idx = 0; bk = okey(row[0]);
            for (i = 1; i < n; i = i + 1) if (okey(row[i]) > bk) begin bk = okey(row[i]); exp_idx = i; end
            for (b = 0; b * LP < n; b = b + 1) begin
                @(negedge clk);
                in_v = 1; in_last = (b + 1) * LP >= n; in_bias_en = bias;
                for (j = 0; j < LP; j = j + 1) begin
                    in_mask[j] = (b * LP + j) < n;
                    in_vals[32*j +: 32] = ((b * LP + j) < n) ? row[b * LP + j] : $urandom;
                    in_bias[32*j +: 32] = bias ? {1'b0, 8'(100 + $urandom % 20), 23'($urandom)} : $urandom;
                end
            end
            @(negedge clk); in_v = 0; in_last = 0;
        end
    endtask
    task check_q(input integer want);
        integer t;
        begin
            t = 0; while (!ov18 && t < 200) begin @(posedge clk); t = t + 1; end
            #0.1;
            if (!ov18 || oi18 !== want[17:0]) begin $display("FAIL qwen row: idx %0d want %0d", oi18, want); fails = fails + 1; end
            rows = rows + 1;
            @(posedge clk);
        end
    endtask
    function automatic [31:0] rnd();
        integer r;
        begin
            r = $urandom % 100;
            rnd = (r == 0) ? 32'h7FC0_0001 : (r == 1) ? 32'h8000_0000 : (r == 2) ? 32'd0 :
                  {1'($urandom % 2), 8'(120 + $urandom % 16), 23'($urandom)};
        end
    endfunction
    integer i, n, k;
    initial begin
        repeat (3) @(posedge clk); rst_n = 1;
        // ---- CF-1 lockstep on DS rows
        for (k = 0; k < 40; k = k + 1) begin
            n = (k % 10 == 0) ? 129280 : 1 + $urandom % 3000;
            for (i = 0; i < n; i = i + 1) row[i] = (k % 3 == 0) ? 32'h3F80_0000 : rnd();   // k % 3 == 0: all ties
            send_row(n, k % 4 == 1);
            repeat ($urandom % 3) @(negedge clk);
        end
        repeat (40) @(posedge clk);
        if (mism != 0) begin $display("FAIL CF-1 lockstep mismatches %0d", mism); fails = fails + 1; end
        ls = 0;
        // ---- Qwen rows (IW 18 only)
        n = 151936;
        for (i = 0; i < n; i = i + 1) row[i] = {1'b0, 8'd120, 23'($urandom)};
        row[151935] = 32'h4300_0000; send_row(n, 0); check_q(151935);
        row[131072] = 32'h4400_0000; send_row(n, 0); check_q(131072);
        row[131071] = 32'h4500_0000; row[151935] = 32'h4500_0000; send_row(n, 0); check_q(131071);
        row[140000] = 32'h7FC0_0000; row[150000] = 32'h7FC0_1234; send_row(n, 0); check_q(140000);
        n = 37984;
        for (i = 0; i < n; i = i + 1) row[i] = rnd();
        row[37983] = 32'h7F7F_FFFF; send_row(n, 0); check_q(exp_idx);
        for (i = 0; i < n; i = i + 1) row[i] = (i % 1000 == 999 || (i > 0 && i % 1000 == 0)) ? 32'h4000_0000 : 32'h3F80_0000;
        send_row(n, 0); check_q(999);
        if (fails == 0) $display("HGI_ARGMAX PASS fast=%0d cf1_rows=40 qwen_rows=%0d", FAST, rows);
        else $display("HGI_ARGMAX FAIL %0d", fails);
        $finish;
    end
endmodule
