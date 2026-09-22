`timescale 1ns/1ps
module tb_a3_fp32_div_pipe_protocol;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,in_valid=0,out_ready=0;
    reg [31:0] numerator_code=0,denominator_code=0;
    wire in_ready,out_valid;
    wire [31:0] result_code;
    wire [1:0] result_error;
    ot_a3_fp32_div_rne_pipe dut(.*);
    integer phase_index,stalled_cycles;
    task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
    task launch(input [31:0] n,input [31:0] d);
        begin
            numerator_code=n;denominator_code=d;in_valid=1;
            #1;if(!in_ready)$fatal(1,"request refused while idle");
            tick();in_valid=0;
            // Inputs are no longer owned after acceptance.
            numerator_code=32'h7fc00000;denominator_code=0;
        end
    endtask
    task expect_result(input [31:0] value,input [1:0] error);
        begin
            wait(out_valid);@(negedge clk);
            if(result_code!==value || result_error!==error)$fatal(1,"wrong division result");
            // Hold another command valid against the blocked output. Neither
            // payload nor ownership may change until that output is consumed.
            in_valid=1;numerator_code=32'h40800000;denominator_code=32'h40000000;
            for(stalled_cycles=0;stalled_cycles<7;stalled_cycles=stalled_cycles+1)begin
                if(in_ready || !out_valid || result_code!==value || result_error!==error)
                    $fatal(1,"stalled result changed or command accepted");
                tick();
            end
            in_valid=0;out_ready=1;tick();out_ready=0;
            if(out_valid || !in_ready)$fatal(1,"output did not release");
        end
    endtask
    initial begin
        tick();rst_n=1;
        launch(32'h3f800000,32'h40400000);expect_result(32'h3eaaaaab,0); // 1/3 RNE
        // Reset at each of STEP_MUL, STEP_CMP, ROUND_MUL, ROUND_CMP.
        for(phase_index=0;phase_index<4;phase_index=phase_index+1)begin
            launch(32'h3f800000,32'h40400000);
            wait(dut.busy && dut.phase==2'(phase_index));@(negedge clk);
            rst_n=0;#1;if(out_valid)$fatal(1,"reset failed to revoke result");
            tick();rst_n=1;
            repeat(4)tick();
            if(out_valid || !in_ready)$fatal(1,"cancelled work escaped reset");
            launch(32'h40800000,32'h40000000);expect_result(32'h40000000,0);
        end
        launch(32'h3f800000,0);expect_result(0,1);
        launch(0,32'h3f800000);expect_result(0,0);
        // Consume held result and accept its successor on the same edge.
        launch(32'h3f800000,32'h40000000);
        wait(out_valid);@(negedge clk);
        if(result_code!==32'h3f000000)$fatal(1,"half result");
        numerator_code=32'h41100000;denominator_code=32'h40400000;in_valid=1;out_ready=1;
        #1;if(!in_ready)$fatal(1,"replacement request blocked");
        tick();in_valid=0;out_ready=0;
        expect_result(32'h40400000,0);
        $display("PASS divider protocol reset_phases=4 stalled_results=8 replacement=1");$finish;
    end
    initial begin #1000000;$fatal(1,"protocol timeout");end
endmodule
