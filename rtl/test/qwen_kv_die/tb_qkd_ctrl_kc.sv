`timescale 1ns/1ps
// el1013-qwen-kvstrips 2026-10-13: exact bench of qkd_ctrl_kc (the kc stream-command crossing of a controller strip)
// with three ot_qkvd_kcmd_tap stations behind it (the chain the 32 qkd_ctrl_pc leaves form by abutment).
//   * 4,000 random command words from the core clock at random gaps: every word leaves on ko once, in order, exact,
//     and reaches the end of the tap chain exact; every DESC / GO gives each tap its controller command
//     {n 1,024, row ROW0 + layer} / GO;
//   * no fault while the issuer keeps its rate; fi (hclk) reaches kf; a 14-word burst overflows the FIFO -> kf.
// MUT 1 (the leaf's mutant): layer bit flipped -> FAIL.
module tb_qkd_ctrl_kc;
    parameter integer MUT = 0, N = 4000;
    reg ck = 0, hclk = 0;
    always #0.416667 ck = ~ck;
    initial begin #0.2; forever #0.512 hclk = ~hclk; end
    reg rsi = 0, hrst = 0, fi = 0;
    reg  [32:0] kc = 0;
    wire [32:0] ko;
    wire        kf;
    qkd_ctrl_kc #(.MUT(MUT)) dut (.ck(ck), .rsi(rsi), .pll_hbm(hclk), .hrst(hrst), .kc(kc), .ko(ko), .fi(fi), .kf(kf));
    wire [32:0] t [0:3];
    wire [2:0]  c_v; wire [31:0] c_d [0:2];
    assign t[0] = ko;
    for (genvar i = 0; i < 3; i++) begin : tap
        ot_qkvd_kcmd_tap #(.ROW0(64)) u (.clk(hclk), .rst_n(dut.hr_q), .i_v(t[i][0]), .i_d(t[i][32:1]),
            .o_v(t[i+1][0]), .o_d(t[i+1][32:1]), .c_v(c_v[i]), .c_d(c_d[i]));
    end
    reg [31:0] sent [$], sent_e [$], sent_c [0:2][$];
    longint n_ko = 0, n_end = 0, n_cmd = 0, n_err = 0;
    bit chk = 1;
    task automatic bad(input string what);
        if (n_err < 10) $display("MISMATCH %s", what);
        n_err++;
    endtask
    always @(posedge hclk) if (chk) begin
        if (ko[0]) begin
            n_ko++;
            if (sent.size() == 0) bad("ko word with nothing sent");
            else begin automatic reg [31:0] w = sent.pop_front(); if (ko[32:1] !== w) bad($sformatf("ko word %h, sent %h", ko[32:1], w)); end
        end
        if (t[3][0]) begin
            n_end++;
            if (sent_e.size() == 0) bad("chain-end word with nothing sent");
            else begin automatic reg [31:0] w = sent_e.pop_front(); if (t[3][32:1] !== w) bad("chain-end word"); end
        end
        for (int i = 0; i < 3; i++) if (c_v[i]) begin
            automatic reg [31:0] w;
            n_cmd++;
            if (sent_c[i].size() == 0) bad("tap command with nothing sent");
            else begin
                w = sent_c[i].pop_front();
                if (w[31:30] == 2'd0 && c_d[i] !== {2'd0, 11'd1024, 19'(64 + w[19:14])}) bad("tap DESC command");
                if (w[31:30] == 2'd1 && c_d[i] !== {2'd1, 30'd0}) bad("tap GO command");
            end
        end
    end
    reg [31:0] rnd = 32'h2468ace1;
    integer k;
    initial begin
        repeat (6) @(negedge ck);
        rsi = 1; @(negedge hclk); hrst = 1;
        repeat (40) @(negedge ck);
        for (k = 0; k < N; k++) begin
            automatic reg [31:0] w;
            rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
            w = {1'b0, rnd[0], 10'd0, rnd[9:4], rnd[23:10]};          // op 0 DESC / 1 GO, layer, T
            @(negedge ck); kc = {w, 1'b1}; sent.push_back(w); sent_e.push_back(w);
            for (int i = 0; i < 3; i++) sent_c[i].push_back(w);
            @(negedge ck); kc = 33'd0;
            repeat (1 + rnd[27:25]) @(negedge ck);
        end
        repeat (60) @(negedge ck);
        if (kf !== 1'b0) bad("kf set with no fault");
        if (n_ko != N || n_end != N || n_cmd != 3 * N) bad("coverage floor");
        fi = 1; repeat (8) @(negedge ck);
        if (kf !== 1'b1) bad("fi did not reach kf");
        fi = 0; rsi = 0; hrst = 0; repeat (6) @(negedge ck); rsi = 1; @(negedge hclk); hrst = 1; repeat (40) @(negedge ck);
        if (kf !== 1'b0) bad("kf not cleared by reset");
        chk = 0; sent.delete(); sent_e.delete(); for (int i = 0; i < 3; i++) sent_c[i].delete();
        for (k = 0; k < 14; k++) begin @(negedge ck); kc = {32'd0 | (32'd3 << 30), 1'b1}; end   // op 3: no tap command
        @(negedge ck); kc = 33'd0; repeat (10) @(negedge ck);
        if (kf !== 1'b1) bad("FIFO overflow did not reach kf");
        if (n_err == 0) $display("PASS qkd_ctrl_kc: %0d command words crossed exact and in order, %0d tap commands exact, fault chain and overflow reach kf", N, n_cmd);
        else $display("FAIL qkd_ctrl_kc mut=%0d: %0d mismatches", MUT, n_err);
        $finish;
    end
    initial begin #20000000; $display("FAIL qkd_ctrl_kc mut=%0d: watchdog", MUT); $finish; end
endmodule
