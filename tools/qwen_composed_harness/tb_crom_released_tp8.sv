`timescale 1ns/1ps
// Q-FUNC: native TP8 constant ROM with the RELEASED whole-token stage images (crom_native_masks.py).
// The same eight ot_qfd_crom_gr TP=8 group tiles (48 real ot_rom_4096x266_m8 models, lane-base straps, RLY relays)
// that ot_qwen_native_memory_cluster instantiates. One 64-lane read issued EVERY edge (stage changes per read);
// each answer must appear at exactly strobe+8 and the station must hold the previous answer at strobe+7.
// Expected words are loaded only for comparison; nothing from them reaches the DUT.
module tb_crom_released_tp8;
parameter integer MUT = 0;
parameter integer NMAX = 20000;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg [63:0] re = 0; reg [1535:0] addr = 0; reg [5:0] stage = 0;
wire [4095:0] q; wire [7:0] fault; wire [15:0] code;
genvar g;
generate for (g = 0; g < 8; g = g + 1) begin : groups
    ot_qfd_crom_gr #(.TP(8), .IMG_LB(8*g), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .crom_re(re[8*g +: 8]),
        .crom_addr(addr[192*g +: 192]), .crom_stage(stage), .crom_lb(6'(8*g)), .crom_q(q[512*g +: 512]),
        .fault(fault[g]), .fault_code(code[2*g +: 2]));
end endgenerate
reg [63:0] hdr [0:NMAX-1];
reg [63:0] exp_w [0:NMAX*64-1];
reg [1023:0] tdir;
integer n, i, l, errors = 0, checked = 0, k;
initial begin
    if (!$value$plusargs("TESTS=%s", tdir)) begin $display("FAIL no +TESTS"); $finish; end
    if (!$value$plusargs("N=%d", n)) begin $display("FAIL no +N"); $finish; end
    if (n > NMAX) begin $display("FAIL N > NMAX"); $finish; end
    $readmemh({tdir, "/tests_hdr.hex"}, hdr);
    $readmemh({tdir, "/tests_exp.hex"}, exp_w);
    repeat (4) @(negedge clk); rst_n = 1; repeat (12) @(negedge clk);
    // cycle k: check test k-8 (exact strobe+8 edge; back-to-back reads make an early/late answer mismatch), then drive test k
    for (k = 0; k < n + 8; k = k + 1) begin
        if (k >= 8) begin
            i = k - 8;
            for (l = 0; l < 64; l = l + 1) if (q[64*l +: 64] !== exp_w[64*i + l]) begin
                errors = errors + 1;
                if (errors < 10) $display("MISMATCH test=%0d stage=%0d base=%0d lane=%0d got=%h exp=%h", i, hdr[i][37:32],
                                          hdr[i][23:0], l, q[64*l +: 64], exp_w[64*i + l]);
            end
            checked = checked + 1;
        end
        if (k < n) begin
            stage = hdr[k][37:32]; re = {64{1'b1}};
            for (l = 0; l < 64; l = l + 1) addr[24*l +: 24] = hdr[k][31] ? hdr[k][23:0] : 24'(hdr[k][23:0] + l);
        end else re = 0;
        @(negedge clk);
    end
    if (|fault) begin errors = errors + 1; $display("FAULT codes=%h", code); end
    if (checked != n) begin errors = errors + 1; $display("FAIL checked %0d of %0d", checked, n); end
    if (errors) $display("FAIL crom_released_tp8 errors=%0d tests=%0d", errors, n);
    else $display("PASS crom_released_tp8 tests=%0d lanes=64 macros=48 latency=8 back-to-back", n);
    $finish;
end
endmodule
