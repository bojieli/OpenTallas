`timescale 1ns/1ps
module tb_loader_reset_leaf;
    reg clk=0, parent_reset_n=0;
    wire reset_n;
    always #0.833333333 clk=~clk;
`ifdef MUT_RESET
    assign reset_n=1'b1;
`else
    ot_hfd_loader_reset_leaf dut(.*);
`endif
    initial begin
        #0.2; if(reset_n!==0) $fatal(1,"raw assertion missing");
        #0.1 parent_reset_n=1;
        #0.1; if(reset_n!==0) $fatal(1,"release bypassed local edge");
        @(posedge clk); #0.001; if(reset_n!==1) $fatal(1,"one edge release missing");
        #0.2 parent_reset_n=0;
        #0.001; if(reset_n!==0) $fatal(1,"active reset failed to assert");
        #0.17 parent_reset_n=1;
        #0.01; if(reset_n!==0) $fatal(1,"restart bypassed local edge");
        @(posedge clk); #0.001; if(reset_n!==1) $fatal(1,"restart release missing");
        $display("LOADER_RESET_LEAF PASS one-cycle release, asynchronous active reset"); $finish;
    end
endmodule
