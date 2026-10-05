`timescale 1ns/1ps
module tb_hdc_matvec_nonpow2_argmax;
    reg clk=0, rst_n=0;
    always #5 clk=~clk;
    wire [17:0] am_idx;
    wire [31:0] am_val;
    wire am_any;
    // The scoring pipeline is driven at its registered result boundary to
    // isolate the non-power-of-two compare tree. G3/W2 has six live leaves
    // and two invalid padded leaves at the eight-leaf tree boundary.
    ot_hdc_matvec #(.W(2),.G(3),.IL(8),.AW(24),.NW(18)) dut (
        .clk(clk),.rst_n(rst_n),.go(1'b0),.am_idx(am_idx),
        .am_val(am_val),.am_any(am_any));
    initial begin
        repeat (3) @(negedge clk); rst_n=1;
        force dut.r_v=1'b1;
        force dut.r_last=1'b1;
        force dut.r_amax=1'b1;
        force dut.r_rmax=1'b0;
        force dut.r_opend=1'b1;
        force dut.r_nb=19'd0;
        force dut.r_mask=6'b111111;
        // Winner is the last real leaf: group 2 lane 1, row 2*2*8+1.
        force dut.res={32'h40c00000,32'h3f800000,32'h40000000,
                       32'h3f800000,32'h40400000,32'h3f800000};
        repeat (10) @(negedge clk);
        if (!am_any || am_idx!==18'd33 || am_val!==32'h40c00000)
            $fatal(1,"non-power-of-two argmax lost leaf: any=%b idx=%0d val=%h",am_any,am_idx,am_val);
        $display("PASS non-power-of-two matvec argmax: G3/W2, padded leaves invalid, winner row 33");
        $finish;
    end
    initial begin #2000; $fatal(1,"argmax timeout"); end
endmodule
