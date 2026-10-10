`timescale 1ns/1ps
// redesign-qwen 2026-10-09: 8 constant-ROM group tiles (ot_qfd_crom SW 8, LB 8g) against the 64-lane ot_qfd_crom on the same
// random-content mask images (+OT_ROM_DIR) and the same contract reads (lane l reads rb + 64 r + l of one region, random
// lane subsets, random stage 0..36): every answer word and the fault must match every edge.  GMUT 1: every tile's lane base
// 0 (alignment check wrong for groups 1-7) -> the fault differs -> FAIL.
module tb_qfd_crom_g #(parameter integer N = 6000, parameter integer GMUT = 0);
    localparam integer SW = 64, AW = 24;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    reg [SW-1:0] re = 0; reg [SW*AW-1:0] addr = 0; reg [5:0] st = 0;
    wire [SW*64-1:0] q_ref, q_g; wire f_ref; wire [1:0] fc_ref; wire [7:0] f_g; wire [15:0] fc_g;
    ot_qfd_crom ref_ (.clk(clk), .rst_n(rst_n), .crom_re(re), .crom_addr(addr), .crom_stage(st), .crom_q(q_ref),
        .fault(f_ref), .fault_code(fc_ref));
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_t
        ot_qfd_crom #(.SW(8), .LB((GMUT != 0) ? 0 : 8 * g)) u (.clk(clk), .rst_n(rst_n), .crom_re(re[8*g +: 8]),
            .crom_addr(addr[8*g*AW +: 8*AW]), .crom_stage(st), .crom_q(q_g[8*g*64 +: 8*64]), .fault(f_g[g]),
            .fault_code(fc_g[2*g +: 2]));
    end endgenerate
    integer n, l, bad = 0, checks = 0, k, r;
    reg [31:0] rs = 32'h2468ace1;
    reg [AW-1:0] rb;
    task automatic rnd; begin rs = rs ^ (rs << 13); rs = rs ^ (rs >> 17); rs = rs ^ (rs << 5); end endtask
    always @(posedge clk) if (rst_n) begin
        checks = checks + 1;
        if (q_g !== q_ref || (|f_g) !== f_ref) begin
            if (bad < 5) $display("MISMATCH at check %0d fault ref %b tiles %b", checks, f_ref, f_g);
            bad = bad + 1;
        end
    end
    initial begin
        repeat (4) @(posedge clk); rst_n <= 1;
        for (n = 0; n < N; n = n + 1) begin
            rnd; st <= rs % 36;
            rnd; k = rs % 5;
            rnd;
            case (k)
                0: begin rb = 4096;   r = rs % 20; end
                1: begin rb = 533761; r = rs % 64; end
                2: begin rb = 537857; r = rs % 64; end
                3: begin rb = 9473;   r = rs % 8192; end
                default: begin rb = 0; r = rs % 64; end
            endcase
            rnd;
            for (l = 0; l < SW; l = l + 1) begin
                re[l] <= (rs >> (l % 32)) & 1;
                addr[l*AW +: AW] <= rb + 64 * r + l;
            end
            @(posedge clk);
        end
        re <= 0; repeat (10) @(posedge clk);
        if (bad == 0) $display("PASS crom_g checks=%0d fault=%0d", checks, f_ref);
        else $display("FAIL crom_g bad=%0d checks=%0d", bad, checks);
        $finish;
    end
endmodule
