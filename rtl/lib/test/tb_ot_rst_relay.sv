`timescale 1ns/1ps
// ot_rst_relay unit bench: async assert to every region, release after exactly SYNC_STAGES+TREE_STAGES edges, all regions
// equal, a mid-run glitch re-asserts.  Prints RST_RELAY_PASS or $fatal.
module tb_ot_rst_relay;
    localparam integer R = 6, S = 2, T = 2;
    reg clk = 1'b0, rst_n_in = 1'b0;
    wire [R-1:0] rst_n;
    ot_rst_relay #(.REGIONS(R), .SYNC_STAGES(S), .TREE_STAGES(T)) dut (.clk(clk), .rst_n_in(rst_n_in), .rst_n(rst_n));
    always #5 clk = ~clk;
    integer edges;
    task automatic check_release;
        begin
            edges = 0;
            @(negedge clk) rst_n_in = 1'b1;
            while (rst_n !== {R{1'b1}}) begin
                @(posedge clk); #1 edges = edges + 1;
                if (rst_n !== {R{1'b0}} && rst_n !== {R{1'b1}}) $fatal(1, "regions differ: %b", rst_n);
                if (edges > S + T) $fatal(1, "release later than %0d edges", S + T);
            end
            if (edges != S + T) $fatal(1, "release after %0d edges, expected %0d", edges, S + T);
        end
    endtask
    initial begin
        repeat (3) @(posedge clk);
        #1 if (rst_n !== {R{1'b0}}) $fatal(1, "regions not in reset: %b", rst_n);
        check_release();
        repeat (4) @(posedge clk);
        // async assert: between edges, no clock edge needed
        #2 rst_n_in = 1'b0; #1;
        if (rst_n !== {R{1'b0}}) $fatal(1, "assert not asynchronous: %b", rst_n);
        @(posedge clk); #1;
        check_release();
        // short glitch mid-run re-asserts and re-releases with the full latency
        repeat (2) @(posedge clk);
        #3 rst_n_in = 1'b0; #1 if (rst_n !== {R{1'b0}}) $fatal(1, "glitch not asserted");
        #1 rst_n_in = 1'b1;
        edges = 0;
        while (rst_n !== {R{1'b1}}) begin @(posedge clk); #1 edges = edges + 1; end
        if (edges != S + T) $fatal(1, "glitch release after %0d edges, expected %0d", edges, S + T);
        $display("RST_RELAY_PASS regions=%0d release_cycles=%0d", R, S + T);
        $finish;
    end
endmodule
