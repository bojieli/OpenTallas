`timescale 1ns/1ps
module tb_vms_status_static;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg [143:0] bank_status=0;
    reg [2:0] hub_status=0;
    reg ring_fault=0;
    wire [18:0] vmstat;
    ot_vms_status_static dut(.*);
    task automatic step;begin @(posedge clk);#1;end endtask
    initial begin
        step();@(negedge clk);rst_n=1;
        for(integer b=0;b<8;b++)bank_status[b*18+:18]=18'(b+1);
        step();step();step();
        if(vmstat!==19'd36)$fatal(1,"CE sum or three-edge latency");
        @(negedge clk);bank_status[7*18+:18]={2'b10,16'hffff};
        bank_status[6*18+16]=1;hub_status=2;
        step();step();step();
        if(vmstat!=={3'b111,16'hffff})$fatal(1,"CE saturation or distant-bank faults lost");
        @(negedge clk);bank_status=0;hub_status=0;ring_fault=1;
        step();step();step();
        if(vmstat!=={3'b100,16'd0})$fatal(1,"ring schedule fault lost");
        $display("VMS_STATIC_STATUS PASS sum saturation fault aggregation three edges");$finish;
    end
endmodule
