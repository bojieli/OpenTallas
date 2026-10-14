`timescale 1ns/1ps
// Bench: ot_qwen_rst_root driving a tree of ot_qwen_rst_rep shaped like the die tree (a deep trunk of NL repeaters, a
// shallow branch off the first repeater's q1 padded to the same depth with PAD-8 cells + plain repeaters, as
// _reset_tree pads a slack edge).  Tree flops power up X.  Checks, for power-on and for a ONE-cycle req_n pulse:
//   1 no leaf is X or released while root_n is asserted + DEPTH; 2 both leaves release in the SAME cycle, exactly
//   DEPTH cycles after root_n; 3 all leaves were asserted together with the root for >= MARGIN cycles; 4 start_ok
//   rises only after every leaf has been released for >= MARGIN cycles, and is low whenever a leaf is in reset.
// +define MUT_ROOT=1|2 (root mutants), MUT_REP=1 (repeater mutant: q1 early -> unequal release) must FAIL.
`ifndef MUT_ROOT
`define MUT_ROOT 0
`endif
`ifndef MUT_REP
`define MUT_REP 0
`endif
module tb_ot_qwen_rst_tree;
    localparam integer NL = 23;                      // trunk repeaters: depth = 2 * NL cycles
    localparam integer DEPTH = 2 * NL;
    localparam integer MARGIN = 8;
    // shallow branch: rep0.q1 -> 4 x PAD8 (40) + 2 x plain (4) = 44 = DEPTH - 2 cycles after rep0
    reg clk = 0, por_n = 0, req_n = 1;
    wire root_n, start_ok;
    always #0.4165 clk = ~clk;
    ot_qwen_rst_root #(.DEPTH(DEPTH), .MARGIN(MARGIN), .MUT(`MUT_ROOT)) u_root (.clk(clk), .por_n(por_n), .req_n(req_n),
                                                                             .root_n(root_n), .start_ok(start_ok));
    wire [NL:0] t;
    wire [NL-1:0] t1;
    assign t[0] = root_n;
    genvar g;
    generate
        for (g = 0; g < NL; g = g + 1) begin : trunk
            ot_qwen_rst_rep #(.PAD(0), .MUT(g == 0 ? `MUT_REP : 0)) u (.clk(clk), .d(t[g]), .q0(t[g + 1]), .q1(t1[g]));
        end
    endgenerate
    wire [6:0] b;
    assign b[0] = t1[0];
    generate
        for (g = 0; g < 6; g = g + 1) begin : br
            ot_qwen_rst_rep #(.PAD(g < 4 ? 8 : 0)) u (.clk(clk), .d(b[g]), .q0(b[g + 1]), .q1());
        end
    endgenerate
    wire leaf_a = t[NL], leaf_b = b[6];
    integer errs = 0, cyc = 0, t_root = -1, t_a = -1, t_b = -1, t_ok = -1, both_low = 0, phase = 0;
    reg root_q = 0;
    task fail(input [255:0] s); begin errs = errs + 1; if (errs < 10) $display("ERR @%0d: %0s", cyc, s); end endtask
    always @(posedge clk) begin
        cyc <= cyc + 1;
        root_q <= root_n;
        if (phase != 0) begin
            if (root_n === 1'b1 && root_q === 1'b0) t_root <= cyc;
            if (root_n === 1'b0) begin t_root <= -1; t_a <= -1; t_b <= -1; t_ok <= -1; end
            if (t_root >= 0) begin
                if (leaf_a === 1'bx || leaf_b === 1'bx) fail("leaf X after root release");
                if (leaf_a === 1'b1 && t_a < 0) t_a <= cyc;
                if (leaf_b === 1'b1 && t_b < 0) t_b <= cyc;
                if (start_ok === 1'b1 && t_ok < 0) t_ok <= cyc;
                if (start_ok === 1'b1 && (leaf_a !== 1'b1 || leaf_b !== 1'b1)) fail("start_ok with a leaf in reset");
            end
            if (root_n === 1'b0 && leaf_a === 1'b0 && leaf_b === 1'b0) both_low <= both_low + 1;
            if (start_ok === 1'b1 && root_n !== 1'b1) fail("start_ok with the root asserted");
        end
    end
    task check(input [255:0] s);
        begin
            if (t_root < 0 || t_a < 0 || t_b < 0 || t_ok < 0) fail("no release / no start_ok");
            if (t_a != t_b) fail("leaves release in different cycles");
            if (t_a - t_root != DEPTH) fail("leaf release is not DEPTH cycles after the root");
            if (both_low < MARGIN) fail("leaves and root not asserted together for MARGIN cycles");
            if (t_ok - t_a < MARGIN) fail("start_ok earlier than MARGIN cycles after the leaves");
            $display("%0s: root %0d leaf_a %0d leaf_b %0d start_ok %0d all-asserted %0d cycles", s, t_root, t_a, t_b, t_ok, both_low);
        end
    endtask
    initial begin
        repeat (3) @(posedge clk);
        phase = 1; por_n = 1;
        repeat (4 * DEPTH + 60) @(posedge clk);
        check("power-on");
        both_low = 0;
        @(negedge clk) req_n = 0;
        @(negedge clk) req_n = 1;                    // a one-cycle request
        repeat (4 * DEPTH + 60) @(posedge clk);
        check("one-cycle pulse");
        if (errs == 0) $display("PASS tb_ot_qwen_rst_tree DEPTH=%0d MARGIN=%0d", DEPTH, MARGIN);
        else $display("FAIL tb_ot_qwen_rst_tree errs=%0d", errs);
        $finish;
    end
endmodule
