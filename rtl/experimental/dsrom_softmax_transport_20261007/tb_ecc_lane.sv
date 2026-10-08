`timescale 1ns/1ps
module tb_ecc_lane;
    import ot_gpu_w6_secded_pkg::*;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, w_valid=0, r_valid=0;
    reg [63:0] w_data=0;
    reg [71:0] r_code=0;
    wire w_code_valid,r_data_valid,corrected,uncorrectable;
    wire [71:0] w_code;
    wire [63:0] r_data;
    integer checks=0;
    ot_dsrom_softmax_ecc_lane dut(.*);
    task automatic check_read(input [71:0] code, input [63:0] want,
                              input corr, input ue);
        @(negedge clk);r_valid=1;r_code=code;
        @(posedge clk);#1;if(r_data_valid)$fatal(1,"EARLY_VALID_1");
        @(negedge clk);r_valid=0;
        @(posedge clk);#1;if(r_data_valid)$fatal(1,"EARLY_VALID_2");
        @(posedge clk);#1;
        if(!r_data_valid || corrected!==corr || uncorrectable!==ue || (!ue && r_data!==want))
            $fatal(1,"DECODE_MISMATCH check=%0d corr=%b ue=%b data=%h expected=%h",checks,corrected,uncorrectable,r_data,want);
        checks=checks+1;
        @(posedge clk);#1;if(r_data_valid)$fatal(1,"STICKY_VALID");
    endtask
    reg [63:0] word_data;
    reg [71:0] code;
    initial begin
        repeat(2) @(negedge clk);rst_n=1;
        for(integer w=0;w<4;w=w+1) begin
            case(w)
                0:word_data=64'h0;
                1:word_data=64'hffffffffffffffff;
                2:word_data=64'h0123456789abcdef;
                3:word_data=64'hfedcba9876543210;
            endcase
            @(negedge clk);w_valid=1;w_data=word_data;
            @(posedge clk);#1;
            if(!w_code_valid || w_code!==encode64(word_data))$fatal(1,"ENCODE_MISMATCH");
            code=w_code;
            @(negedge clk);w_valid=0;
            check_read(code,word_data,0,0);
            for(integer i=0;i<72;i=i+1)check_read(code^(72'b1<<i),word_data,1,0);
            for(integer i=0;i<72;i=i+1)
                for(integer j=i+1;j<72;j=j+1)
                    check_read(code^(72'b1<<i)^(72'b1<<j),word_data,0,1);
        end
        // Consecutive returns establish II=1 and code/syndrome identity.
        for(integer n=0;n<10;n=n+1) begin
            @(negedge clk);
            r_valid=(n<8);
            r_code=encode64(64'h123456789abcdef0+64'(n))^(72'b1<<(n+2));
            @(posedge clk);#1;
            if(n<2)begin
                if(r_data_valid)$fatal(1,"BURST_EARLY");
            end else begin
                if(!r_data_valid || !corrected || uncorrectable || r_data!==(64'h123456789abcdef0+64'(n-2)))
                    $fatal(1,"BURST_IDENTITY n=%0d",n);
                checks=checks+1;
            end
        end
        // Reset invalidates a return already captured; no stale token escapes.
        @(negedge clk);r_valid=1;r_code=code;
        @(posedge clk);#1;
        @(negedge clk);r_valid=0;rst_n=0;
        @(posedge clk);#1;if(r_data_valid || w_code_valid)$fatal(1,"RESET_VALID");
        @(negedge clk);rst_n=1;
        repeat(4)begin @(posedge clk);#1;if(r_data_valid)$fatal(1,"STALE_POST_RESET");end
        $display("PASS checks=%0d all72 single-bit corrections/all2556 double-bit detections per word; pipeline/reset",checks);
        $finish;
    end
endmodule
