`timescale 1ps/1fs
// Actual candidate-state module: async short pulses and releases near an edge.
// This proves RTL reset equivalence; physical recovery/min-pulse checks remain STA.
module tb_s81ph_candidate_reset;
    reg clk=0, rst_n=0, d=0;
    wire q;
    ot_s81ph_candidate_valid dut(.clk(clk),.rst_n(rst_n),.d(d),.q(q));
    always #416.6665 clk=~clk;
    integer n;
    real phase;
    initial begin
        repeat(2) @(negedge clk);
        rst_n=1;d=1;
        @(posedge clk);#0.01;if(q!==1)$fatal(1,"same existing edge not sampled");
        for(n=0;n<6;n=n+1)begin
            @(negedge clk);
            case(n) 0:phase=1;1:phase=25;2:phase=100;3:phase=200;4:phase=400;5:phase=416.5;endcase
            #phase;rst_n=0;#0.01;if(q!==0)$fatal(1,"short async reset missed case%0d",n);
            #0.09;rst_n=1;#0.01;if(q!==0)$fatal(1,"early release changed state before edge case%0d",n);
            @(posedge clk);#0.01;if(q!==1)$fatal(1,"release did not sample same D at edge case%0d",n);
        end
        d=0;@(posedge clk);#0.01;if(q!==0)$fatal(1,"actual D zero not sampled");
        $display("CANDIDATE_RESET PASS6 short-reset/early-release phases; same D/edge, no extra epoch");
        $finish;
    end
endmodule
