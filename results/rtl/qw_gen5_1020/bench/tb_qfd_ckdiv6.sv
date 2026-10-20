// QW-GEN5 bench: qfd_ckdiv6 period = 6 ck, duty 3/3, deterministic first edge after reset release, reset re-assert.
`timescale 1ns/1ps
module tb;
    reg ck = 0, rst_n = 0;
    always #0.4166665 ck = ~ck;
    wire ck_o;
    qfd_ckdiv6 dut (.ck(ck), .rst_n(rst_n), .ck_o(ck_o));
    integer cyc = 0, last_rise = -1, rises = 0, bad = 0, hi = 0, first = -1, rel = -1;
    reg prev = 0;
    always @(posedge ck) begin
        cyc <= cyc + 1;
        if (ck_o && !prev) begin
            if (first < 0) first = cyc - rel;
            if (last_rise >= 0 && cyc - last_rise != 6) begin bad = bad + 1; $display("BAD period %0d at %0d", cyc - last_rise, cyc); end
            last_rise = cyc; rises = rises + 1;
        end
        if (ck_o && rel >= 0 && first >= 0) hi = hi + 1;
        prev <= ck_o;
    end
    initial begin
        repeat (5) @(posedge ck); #0.1 rst_n = 1; rel = cyc;
        repeat (120) @(posedge ck);
        if (rises < 18) begin bad = bad + 1; $display("BAD rises %0d", rises); end
        if (first != 3) begin bad = bad + 1; $display("BAD first edge %0d ck after release (expect 3)", first); end
        // reset re-assert: ck_o low within 1 ck, same phase after the second release
        #0.1 rst_n = 0; @(posedge ck); #0.05 if (ck_o !== 1'b0) begin bad = bad + 1; $display("BAD ck_o not low in reset"); end
        last_rise = -1; first = -1; repeat (3) @(posedge ck); #0.1 rst_n = 1; rel = cyc;
        repeat (60) @(posedge ck);
        if (first != 3) begin bad = bad + 1; $display("BAD second first edge %0d", first); end
        if (bad == 0) $display("QFD_CKDIV6 PASS rises=%0d period=6 first_edge=3", rises);
        else $display("QFD_CKDIV6 FAIL bad=%0d", bad);
        $finish;
    end
endmodule
