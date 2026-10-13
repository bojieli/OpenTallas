`timescale 1ns/1ps
// redesign-qwen 2026-10-09: 8 constant-ROM group tiles (ot_qfd_crom SW 8, LB 8g) against the 64-lane ot_qfd_crom on the same
// random-content mask images (+OT_ROM_DIR) and the same contract reads (lane l reads rb + 64 r + l of one region, random
// lane subsets, random stage 0..36): every answer word and the fault must match every edge.  GMUT 1: every tile's lane base
// 0 (alignment check wrong for groups 1-7) -> the fault differs -> FAIL.
// RLY 1 (q13 2026-10-13): the tiles are the slot-shaped M5 master ot_qfd_crom_gr (lane-base STRAP pin + relay stages,
// strobe -> q 8 edges): the reference answer is delayed 3 edges, the fault is compared undelayed (its timing is unchanged).
// GMUT 1 there: every strap 0; GMUT 2: MUT 1 in tile 0 (one answer bit flipped).
module tb_qfd_crom_g #(parameter integer N = 6000, parameter integer GMUT = 0, parameter integer RLY = 0);
    localparam integer SW = 64, AW = 24;
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    reg [SW-1:0] re = 0; reg [SW*AW-1:0] addr = 0; reg [5:0] st = 0;
    wire [SW*64-1:0] q_ref0, q_ref, q_g; wire f_ref; wire [1:0] fc_ref; wire [7:0] f_g; wire [15:0] fc_g;
    ot_qfd_crom ref_ (.clk(clk), .rst_n(rst_n), .crom_re(re), .crom_addr(addr), .crom_stage(st), .crom_q(q_ref0),
        .fault(f_ref), .fault_code(fc_ref));
    genvar g;
    generate for (g = 0; g < 8; g = g + 1) begin : g_t
      if (RLY != 0) begin : g_r
        ot_qfd_crom_gr #(.IMG_LB(8 * g), .MUT((GMUT == 2 && g == 0) ? 1 : 0)) u (.clk(clk), .rst_n(rst_n), .crom_re(re[8*g +: 8]),
            .crom_addr(addr[8*g*AW +: 8*AW]), .crom_stage(st), .crom_lb((GMUT == 1) ? 6'd0 : 6'd8 * g[2:0]), .crom_q(q_g[8*g*64 +: 8*64]), .fault(f_g[g]),
            .fault_code(fc_g[2*g +: 2]));
      end else begin : g_p
        ot_qfd_crom #(.SW(8), .LB((GMUT != 0) ? 0 : 8 * g)) u (.clk(clk), .rst_n(rst_n), .crom_re(re[8*g +: 8]),
            .crom_addr(addr[8*g*AW +: 8*AW]), .crom_stage(st), .crom_q(q_g[8*g*64 +: 8*64]), .fault(f_g[g]),
            .fault_code(fc_g[2*g +: 2]));
      end
    end endgenerate
    reg [SW*64-1:0] qd0, qd1, qd2;
    always @(posedge clk) begin qd0 <= q_ref0; qd1 <= qd0; qd2 <= qd1; end
    assign q_ref = (RLY != 0) ? qd2 : q_ref0;
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
        if (RLY != 0) repeat (4) @(posedge clk);   // ot_rst_relay: the tile releases 3 edges after the port
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
