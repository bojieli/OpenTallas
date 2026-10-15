`timescale 1ns/1ps
module tb_vms_status4_static;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [75:0] quadrant_status=0;
    wire [18:0] vmstat;
    ot_vms_status4_static dut(.*);
    task automatic step;begin @(posedge clk);#1;end endtask
    initial begin
        step();@(negedge clk);rst_n=1;
        quadrant_status={19'd4,19'd3,19'd2,19'd1};
        step();step();step();
        if(vmstat!==19'd10)$fatal(1,"CP four quadrant sum/latency");
        for(integer q=0;q<4;q++)begin
            @(negedge clk);quadrant_status=0;quadrant_status[q*19+:19]={3'b111,16'h1234};
            step();step();step();
            if(vmstat!=={3'b111,16'h1234})$fatal(1,"CP lost quadrant errors %0d",q);
        end
        @(negedge clk);quadrant_status={4{19'h0ffff}};
        step();step();step();
        if(vmstat!==19'h0ffff)$fatal(1,"CP saturation");
        $display("VMS_STATIC_STATUS4 PASS four quadrants all errors CE saturation three rungs");$finish;
    end
endmodule
