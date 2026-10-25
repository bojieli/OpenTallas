`timescale 1ns/1ps
// tb_dsfd_node_static: production master bench of a generated return node dsfd_node_<a><b>[f] (die ports, leaf / node
// packing, registered fault chain) against tools/s81/static_return_calendar.py.  Every edge: o == expected (66-b
// {e, data, tag, v}); end: fo == FAULT; for an 'f' master a final fi pulse must reach fo exactly two edges later
// (S81-KITS-RTLB 10-24: fi lands in its own pin register fil, then fr <= flt | fil: +1 cycle on the fault chain;
// fo must still be 0 after the first edge, so the old unregistered fi -> fr form is rejected).
// Compile with -DDUT=<master> -DHAS_FI=<0|1>; +DIR +T +FAULT.
module tb_dsfd_node_static;
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    reg [65:0] a = 0, b = 0; reg fi = 0;
    wire [65:0] o; wire fo;
`ifdef LA
    wire [62:0] ap = a[62:0];
`else
    wire [65:0] ap = a;
`endif
`ifdef LB
    wire [62:0] bp = b[62:0];
`else
    wire [65:0] bp = b;
`endif
`ifdef HAS_FI
    `DUT dut (.a(ap), .b(bp), .clk(clk), .fi(fi), .fo(fo), .o(o), .rst_n(rst_n));
`else
    `DUT dut (.a(ap), .b(bp), .clk(clk), .fo(fo), .o(o), .rst_n(rst_n));
`endif
    integer fs, fe, T, n, bad, words, xf, r, ev, ee; reg [1023:0] dir; reg [67:0] sa, sb; reg [31:0] et, ed;
    initial begin
        if (!$value$plusargs("DIR=%s", dir) || !$value$plusargs("T=%d", T) || !$value$plusargs("FAULT=%d", xf)) $fatal(1, "args");
        fs = $fopen({dir, "/stim_packed.hex"}, "r"); fe = $fopen({dir, "/expect.hex"}, "r");
        bad = 0; words = 0;
        repeat (3) @(posedge clk); #0.1 rst_n = 1;
        for (n = 0; n < T; n = n + 1) begin
            r = $fscanf(fs, "%h %h\n", sa, sb); r = $fscanf(fe, "%d %h %h %d\n", ev, et, ed, ee);
            a = sa[65:0]; b = sb[65:0];
            @(posedge clk);
            if (ev != 2 && (o[0] !== ev[0] || (ev == 1 && o !== {ee[0], ed, et, 1'b1}))) begin
                bad = bad + 1; if (bad < 6) $display("NODE_STATIC mismatch edge %0d got %h want v%0d t%h d%h e%0d", n, o, ev, et, ed, ee);
            end
            if (ev == 1) words = words + 1;
            #0.1;
        end
        @(posedge clk); #0.1;
        if (fo !== xf[0]) begin bad = bad + 1; $display("NODE_STATIC fo %b want %0d", fo, xf); end
`ifdef HAS_FI
        if (xf == 0) begin
            fi = 1; @(posedge clk); #0.1 fi = 0;
            if (fo !== 1'b0) begin bad = bad + 1; $display("NODE_STATIC fi reached fo after 1 edge (fi pin register missing)"); end
            @(posedge clk); #0.1;
            if (fo !== 1'b1) begin bad = bad + 1; $display("NODE_STATIC fi did not reach fo after 2 edges"); end
        end
`endif
        if (bad) begin $display("NODE_STATIC FAIL %0d", bad); $fatal(1); end
        $display("NODE_STATIC PASS %0d edges %0d words exact, fo %0d", T, words, xf);
        $finish;
    end
endmodule
