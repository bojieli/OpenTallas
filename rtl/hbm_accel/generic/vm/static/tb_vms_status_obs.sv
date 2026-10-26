`timescale 1ns/1ps
`default_nettype none
// HBM-BIND P-VMST-OBS (2026-10-26): B2 die-top composition vm_status4 (ot_vms_status4_static NQ=2) -> obs_C
// (ot_hbm_obs_leaf LID 0) exactly as tools/hbm_b2/make_wiring.py emits it: obs = {vmstat[18:0], other[NOTHER-1:0]}.
// Each trial holds random quadrant words {proto, mask, ue, ce[15:0]} (and random other bits), lets the pipeline settle,
// reads obs_C page 0 (live) words 3 and 4 through the chain and checks bits [NOTHER+18:NOTHER] =
// {OR of the quadrant flags, saturating sum of the quadrant ce counts}, the other bits unchanged.  Then a page-1
// (sticky) read of word 4 after a one-cycle ue pulse in quadrant NE must return the ue bit.
module tb_vms_status_obs;
    localparam integer NOTHER = 125, N = NOTHER + 19;
    reg clk = 0, rst_n = 0;
    always #1 clk = ~clk;
    reg [37:0] qs;                 // {NE[18:0], NW[18:0]} (LSB-first source list: NW first)
    reg [NOTHER-1:0] other;
    wire [18:0] vmstat;
    ot_vms_status4_static #(.NQ(2)) vm_status4 (.clk(clk), .rst_n(rst_n), .quadrant_status(qs), .vmstat(vmstat));
    reg q_v = 0; reg [7:0] q_idx = 0;
    wire r_v; wire [7:0] r_idx; wire [31:0] r_d;
`ifdef OT_OBS_MUT
    ot_hbm_obs_leaf #(.N(N), .LID(0), .MUT(2)) obs_C (
`else
    ot_hbm_obs_leaf #(.N(N), .LID(0)) obs_C (
`endif
        .clk(clk), .rst_n(rst_n), .obs({vmstat, other}), .q_v(q_v), .q_idx(q_idx), .q_d(32'd0),
        .r_v(r_v), .r_idx(r_idx), .r_d(r_d));
    integer checks = 0, errors = 0, t, s;
    reg [31:0] w3, w4;
    reg [63:0] rd;
    reg [18:0] exp_v;
    reg [16:0] sum;
    task automatic rd_word(input [7:0] idx, output [31:0] d);
        begin
            @(negedge clk); q_v = 1; q_idx = idx; @(negedge clk); q_v = 0;
            while (!r_v) @(negedge clk);
            d = r_d;
        end
    endtask
    initial begin
        qs = 0; other = 0;
        repeat (6) @(negedge clk); rst_n = 1; repeat (8) @(negedge clk);
        for (t = 0; t < 400; t = t + 1) begin
            qs = {$random, $random};
            if (t % 4 == 0) qs[18:16] = 0;                       // flag-free trials
            if (t % 4 == 1) begin qs[15:0] = 16'hf000 + t; qs[34:19] = 16'h2000; end   // saturating trials
            if (t % 4 == 2) begin qs[37:35] = 0; qs[18:16] = 0; qs[16 + (t / 4) % 3] = 1'b1; end
            other = {$random, $random, $random, $random};
            repeat (8) @(negedge clk);
            sum = {1'b0, qs[15:0]} + {1'b0, qs[34:19]};
            exp_v = {qs[18:16] | qs[37:35], sum[16] ? 16'hffff : sum[15:0]};
            rd_word(8'h03, w3); rd_word(8'h04, w4);
            rd = {w4, w3};                                       // bits [159:96] of the live vector
            checks = checks + 1;
            if (rd[N - 96 - 1 -: 19] !== exp_v || rd[NOTHER - 96 - 1:0] !== other[NOTHER - 1:96] || rd[63:N - 96] !== 0) begin
                errors = errors + 1;
                if (errors < 5) $display("MISMATCH t=%0d vmstat_obs=%h exp=%h", t, rd[N - 96 - 1 -: 19], exp_v);
            end
        end
        // sticky page: one-cycle ue pulse on NE is held until the page-1 read
        qs = 0; repeat (8) @(negedge clk); rd_word(8'h14, w4);   // clear sticky word 4
        qs[35] = 1'b1; @(negedge clk); qs[35] = 1'b0; repeat (10) @(negedge clk);
        rd_word(8'h04, w4); checks = checks + 1; if (w4[N - 128 - 1 - 2] !== 1'b0) errors = errors + 1;   // live: gone
        rd_word(8'h14, w4); checks = checks + 1; if (w4[N - 128 - 1 - 2] !== 1'b1) errors = errors + 1;   // sticky: held
        $display("VMS_STATUS_OBS %s checks=%0d errors=%0d", errors == 0 ? "PASS" : "FAIL", checks, errors);
        $finish;
    end
endmodule
`default_nettype wire
