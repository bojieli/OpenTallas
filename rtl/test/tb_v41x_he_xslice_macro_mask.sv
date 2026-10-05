`timescale 1ns/1ps
module tb_v41x_he_xslice_macro_mask;
    reg clk=0;
    always #5 clk=~clk;
    reg wr_v=0, pre_v=0, rd_v=0;
    reg [6:0] wr_addr=0, pre_addr=0, rd_addr=0;
    reg [2:0] wr_lane=0;
    reg [15:0] wr_data=0;
    reg [127:0] pre_data=0;
    wire [127:0] rd_data;
    ot_hdc_v41x_he_xslice_macro dut(.*);
    integer i;
    initial begin
        for(i=0;i<8;i=i+1) pre_data[i*16 +:16]=16'h1000+i;
        @(negedge clk); pre_v=1;
        @(negedge clk); pre_v=0; wr_v=1; wr_lane=3; wr_data=16'hbeef;
        @(negedge clk); wr_v=0; rd_v=1;
        @(posedge clk); #1;
        for(i=0;i<8;i=i+1)
            if(rd_data[i*16 +:16] !== (i==3 ? 16'hbeef : 16'h1000+i))
                $fatal(1,"masked write lane %0d got %h",i,rd_data[i*16 +:16]);
        // Same-address read/write returns the old word on this SRAM abstract.
        @(negedge clk); wr_v=1; wr_lane=5; wr_data=16'hface;
        @(posedge clk); #1;
        if(rd_data[5*16 +:16] !== 16'h1005) $fatal(1,"read-before-write failed");
        @(negedge clk); wr_v=0;
        @(posedge clk); #1;
        if(rd_data[5*16 +:16] !== 16'hface) $fatal(1,"masked update failed");
        $display("HE_XSLICE_MACRO_MASK_PASS lanes=8 read_before_write=1");
        $finish;
    end
endmodule
