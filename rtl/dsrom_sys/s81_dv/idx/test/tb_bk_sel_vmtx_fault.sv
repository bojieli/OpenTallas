`timescale 1ns/1ps
// S81/PORTFIX-FLT (2026-10-25, S81 DECISION 4): fault bench of the die master dsdv_bk_sel_vmtx's ONE 1-bit sticky fault.
// Idle die (no beats) -> fault 0; one collision (child lanes A and B valid in the same cycle = the vmux compile-error
// fault, formerly the separate vm_fault port) -> fault rises within 4 edges and stays 1 (sticky) for 200 edges; the
// reset (control state) clears it; idle again -> 0.  Verdict "PASS bk_sel_fault" / "FAIL bk_sel_fault".
// Negative controls (run_bk_sel_fault.sh, sed copies of the RTL): vm_fault dropped from the OR; port = bk_sel fault only.
module tb_bk_sel_vmtx_fault;
    localparam integer V = 276;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0; reg [V-1:0] ca = 0, cb = 0;
    wire [V-1:0] vo_n, vo_s, tl_o; wire fault;
    dsdv_bk_sel_vmtx #(.TX_SRAM(0)) u_dut (.clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10), .ik(3'd1), .ek(3'd2),
        .uid(8'h5C), .eg_n(1'b0), .vi_s({V{1'b0}}), .vo_n(vo_n), .vi_n({V{1'b0}}), .vo_s(vo_s), .vi_idx({V{1'b0}}),
        .ca(ca), .cb(cb), .fault(fault), .tl_o(tl_o));
    integer bad = 0, k, rise = -1;
    initial begin
        repeat (5) @(posedge clk); rst_n = 1;
        repeat (300) begin @(posedge clk); if (fault) bad = bad + 1; end
        if (bad) $display("ERR idle fault");
        @(negedge clk); ca[0] = 1; cb[0] = 1; ca[20:1] = 20'h12345; cb[20:1] = 20'h54321;
        @(negedge clk); ca = 0; cb = 0;
        for (k = 0; k < 6; k = k + 1) begin @(posedge clk); #0.01; if (fault && rise < 0) rise = k; end
        if (rise < 0) begin bad = bad + 1; $display("ERR collision fault never rose"); end
        else $display("OK  collision -> fault after %0d edges", rise + 1);
        for (k = 0; k < 200; k = k + 1) begin @(posedge clk); #0.01; if (!fault) begin bad = bad + 1; if (k < 3) $display("ERR fault fell (not sticky) at +%0d", k); end end
        @(negedge clk); rst_n = 0; repeat (3) @(posedge clk); #0.01;
        if (fault) begin bad = bad + 1; $display("ERR reset did not clear fault"); end
        @(negedge clk); rst_n = 1;
        for (k = 0; k < 300; k = k + 1) begin @(posedge clk); if (fault) begin bad = bad + 1; if (k < 3) $display("ERR fault after reset"); end end
        if (bad == 0) $display("PASS bk_sel_fault: idle 0, collision -> sticky fault, reset clears");
        else $display("FAIL bk_sel_fault: %0d errors", bad);
        $finish;
    end
endmodule
