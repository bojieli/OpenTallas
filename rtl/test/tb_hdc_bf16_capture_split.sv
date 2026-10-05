`timescale 1ns/1ps
module tb_hdc_bf16_capture_split;
    reg [31:0] vm_word=0, kr_word=0;
    reg select_kr=0;
    wire [15:0] high_increment;
    wire round_up;
    ot_hdc_bf16_capture_split dut(.*);
    reg [31:0] picked;
    reg [15:0] expected_hi;
    reg expected_up;
    integer hi, j, sel, checked=0;
    reg [15:0] low;
    task check;
        begin
            #1;
            picked=select_kr ? kr_word : vm_word;
            expected_hi=picked[31:16]+16'd1;
            expected_up=picked[15] & ((|picked[14:0]) | picked[16]);
            if (high_increment !== expected_hi || round_up !== expected_up)
                $fatal(1,"BF16_CAPTURE_FAIL vm=%h kr=%h sel=%b hi=%h/%h up=%b/%b",
                    vm_word,kr_word,select_kr,high_increment,expected_hi,round_up,expected_up);
            checked=checked+1;
        end
    endtask
    initial begin
        // Full unsigned upper-half space: overflow, signed zero, NaN/Inf are
        // source bit patterns, not a substituted arithmetic policy.
        for (hi=0; hi<65536; hi=hi+1)
            for (j=0;j<5;j=j+1) begin
                case(j)
                    0:low=16'h0000; 1:low=16'h8000;
                    2:low=16'h8001; 3:low=16'h7fff; default:low=16'hffff;
                endcase
                vm_word={hi[15:0],low}; kr_word=~vm_word;
                for (sel=0;sel<2;sel=sel+1) begin select_kr=sel; check; end
            end
        $display("BF16_CAPTURE_PASS checked=%0d",checked);
        $finish;
    end
endmodule
