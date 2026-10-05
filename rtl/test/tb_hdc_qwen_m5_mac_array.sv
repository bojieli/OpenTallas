`timescale 1ns/1ps
module tb_hdc_qwen_m5_mac_array;
    reg clk=0, rst_n=0, v=0, first=0, last_k=0;
    always #5 clk=~clk;
    wire [319:0] partial_sum;
    wire fault, sum_valid;
    integer cyc=0, match_count=0, valid_count=0, s;
    function automatic [31:0] fp32_small(input integer x);
        case (x)
            1: fp32_small=32'h3f800000; 2: fp32_small=32'h40000000;
            3: fp32_small=32'h40400000; 4: fp32_small=32'h40800000;
            5: fp32_small=32'h40a00000; 6: fp32_small=32'h40c00000;
            8: fp32_small=32'h41000000; 10: fp32_small=32'h41200000;
            default: fp32_small=32'hffffffff;
        endcase
    endfunction
    ot_hdc_qwen_m5_mac_array #(.G(1), .W(2), .IL(8)) dut (
        .clk(clk), .rst_n(rst_n), .v(v), .first(first), .last_k(last_k),
        .weight_fp32({2{32'h3f800000}}),
        .activation_fp32({fp32_small(5),fp32_small(4),fp32_small(3),fp32_small(2),fp32_small(1)}),
        .partial_sum(partial_sum), .sum_valid(sum_valid), .fault(fault)
    );
    reg all_match;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        all_match=1;
        for (s=0;s<5;s=s+1)
            if (partial_sum[s*64 +: 32] !== fp32_small(2*(s+1)) ||
                partial_sum[s*64+32 +: 32] !== fp32_small(2*(s+1))) all_match=0;
        if (sum_valid) valid_count <= valid_count+1;
        if (sum_valid && !all_match) $fatal(1,"m5 final tag misaligned at cycle %0d",cyc);
        if (all_match) begin
            if (match_count == 0) $display("M5_MAC_FIRST_MATCH cycle=%0d",cyc);
            match_count <= match_count+1;
        end
    end
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        repeat (8) begin @(negedge clk); v=1; first=1; end
        repeat (8) begin @(negedge clk); v=1; first=0; last_k=1; end
        @(negedge clk); v=0; first=0; last_k=0;
        repeat (30) @(negedge clk);
        if (fault || match_count != 8 || valid_count != 8)
            $fatal(1,"m5 MAC mismatch fault=%b matches=%0d tags=%0d",fault,match_count,valid_count);
        $display("PASS Qwen m5 MAC-only array: five exact simultaneous sums, %0d matching output cycles",match_count);
        $finish;
    end
endmodule
