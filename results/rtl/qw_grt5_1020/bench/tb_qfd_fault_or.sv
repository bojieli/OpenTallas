// tb_qfd_fault_or: sticky / latency / reset / every-bit check for qfd_fault_or (N = 16 and N = 1).
`timescale 1ns/1ps
module tb;
    reg ck = 0, rs = 0;
    always #0.5 ck = ~ck;
    reg  [15:0] f16 = 0; reg [0:0] f1 = 0;
    wire o16, o1;
    qfd_fault_or #(.N(16)) u16 (.ck(ck), .rs(rs), .f(f16), .o(o16));
    qfd_fault_or #(.N(1))  u1  (.ck(ck), .rs(rs), .f(f1),  .o(o1));
    integer errors = 0, b, k, seen16, seen1, t16, t1, cyc;
    // reference: o rises exactly 3 edges after the first sampled 1 after release, then holds until reset
    task automatic run_case(input integer bit_i, input integer pulse_at);
        begin
            rs = 0; f16 = 0; f1 = 0; repeat (3) @(negedge ck); rs = 1;
            repeat (4) @(negedge ck);               // 2-stage reset landing settles
            seen16 = -1; seen1 = -1;
            for (cyc = 0; cyc < 40; cyc = cyc + 1) begin
                f16 = (cyc == pulse_at) ? (16'h1 << bit_i) : 16'h0;
                f1  = (cyc == pulse_at && bit_i == 0);
                @(posedge ck); #0.1;
                if (o16 && seen16 < 0) seen16 = cyc;
                if (o1 && seen1 < 0) seen1 = cyc;
                if (seen16 >= 0 && !o16) begin errors = errors + 1; $display("FAIL sticky lost N16 bit %0d cyc %0d", bit_i, cyc); end
                if (cyc >= pulse_at + 3 && !o16) begin errors = errors + 1; $display("FAIL N16 bit %0d not visible at +3 (cyc %0d)", bit_i, cyc); end
                @(negedge ck);
            end
            if (seen16 != pulse_at + 2) begin errors = errors + 1; $display("FAIL N16 bit %0d latency seen %0d pulse %0d", bit_i, seen16, pulse_at); end
            if (bit_i == 0 && seen1 != pulse_at + 2) begin errors = errors + 1; $display("FAIL N1 latency seen %0d", seen1); end
            rs = 0; #0.2; if (o16 || o1) begin errors = errors + 1; $display("FAIL async reset did not clear"); end
        end
    endtask
    initial begin
        for (b = 0; b < 16; b = b + 1) run_case(b, 5 + b);
        // no fault -> never set
        rs = 0; f16 = 0; repeat (3) @(negedge ck); rs = 1;
        for (k = 0; k < 50; k = k + 1) begin @(negedge ck); if (o16 || o1) begin errors = errors + 1; $display("FAIL spurious"); end end
        if (errors == 0) $display("TB_QFD_FAULT_OR PASS cases=17");
        else $display("TB_QFD_FAULT_OR FAIL errors=%0d", errors);
        $finish;
    end
endmodule
