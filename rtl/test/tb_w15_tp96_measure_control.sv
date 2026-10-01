`timescale 1ns/1ps
// Small instrumentation control, not a collective campaign or alternative engine.
module tb_w15_tp96_measure_control #(
    parameter integer WIDTH = 64
);
    reg clk=0, enabled=0;
    // Match the collective bench's 1ps precision and nominal serial period.
    always #(1.111111/2) clk=~clk;
    wire [WIDTH-1:0] cycles;
    reg [15:0] protocol_now=0;
    longint unsigned issue=0, done=0;
    longint unsigned tick_ps=0, previous_tick_ps=0;
    integer overflow_test=0;
    w15_tp96_measure_counter #(.WIDTH(WIDTH)) dut(.clk(clk),.enabled(enabled),.cycles(cycles));
    initial begin
        if (!$value$plusargs("OVERFLOW=%d",overflow_test)) overflow_test=0;
        repeat(4) @(negedge clk);
        if (cycles != 0) $fatal(1,"disabled measurement counter advanced");
        enabled=1;
    end
    always @(posedge clk) if (enabled) begin
        tick_ps=$realtime*1000.0;
        if (cycles>0 && tick_ps-previous_tick_ps!=1112) $fatal(1,"effective clock period mismatch");
        previous_tick_ps=tick_ps;
        if (protocol_now !== cycles[15:0]) $fatal(1,"measurement changed protocol low bits");
        protocol_now<=protocol_now+1'b1;
        if (cycles==65530) issue=cycles;
        if (cycles==528992) done=cycles;
        if (!overflow_test && cycles==600000) begin
            if (done-issue != 463462) $fatal(1,"elapsed measurement wrapped");
            $display("MEASURE_CONTROL_PASS issue=%0d done=%0d elapsed=%0d final=%0d protocol=%0d wraps=%0d period_ps=1112",issue,done,done-issue,cycles,protocol_now,cycles/65536);
            $finish;
        end
    end
    initial begin #10000000; $fatal(1,"measurement control timeout"); end
endmodule
