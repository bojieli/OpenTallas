`timescale 1ns/1ps
module tb_reset_forest;
    reg ck = 0;
    always #5 ck = ~ck;
    reg rst_n = 1;
    wire a, b, deep, shallow;
    ot_s81_reset_leaf #(.DELAY_CYCLES(1)) u_a(ck, rst_n, a);
    ot_s81_reset_leaf #(.DELAY_CYCLES(1)) u_b(ck, a, b);
    ot_s81_reset_leaf #(.DELAY_CYCLES(1)) u_deep(ck, b, deep);
`ifdef MUTANT_EARLY
    ot_s81_reset_leaf #(.DELAY_CYCLES(6)) u_shallow(ck, rst_n, shallow);
`else
    ot_s81_reset_leaf #(.DELAY_CYCLES(7)) u_shallow(ck, rst_n, shallow);
`endif
    integer i;
    task check_release;
        begin
            // The qualified upstream release is presented between active edges.
            @(negedge ck); rst_n = 1;
            for (i = 1; i <= 11; i = i + 1) begin
                @(posedge ck); #0.1;
                if (deep !== (i >= 9) || shallow !== (i >= 9))
                    $fatal(1, "release calendar edge %0d deep=%b shallow=%b", i, deep, shallow);
            end
        end
    endtask
    initial begin
        // Cold assertion off-edge must reset every leaf without a clock edge.
        #1 rst_n = 0; #0.1;
        if ({a,b,deep,shallow} !== 4'b0) $fatal(1, "cold async assertion failed");
        check_release();
        // Warm assertion during operation. It cannot wait for next domain edge.
        #1.3 rst_n = 0; #0.1;
        if ({a,b,deep,shallow} !== 4'b0) $fatal(1, "warm async assertion failed");
        check_release();
        // An interrupted release must restart the full calendar.
        #1 rst_n = 0;
        @(negedge ck); rst_n = 1;
        repeat (4) @(posedge ck);
        #1 rst_n = 0; #0.1;
        if ({a,b,deep,shallow} !== 4'b0) $fatal(1, "interrupted release failed");
        check_release();
        $display("PASS cold/warm/interrupted exact release=9 edges");
        $finish;
    end
endmodule
