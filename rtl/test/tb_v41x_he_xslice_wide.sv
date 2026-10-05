`timescale 1ns/1ps
module tb_v41x_he_xslice_wide;
    localparam DEPTH=80,LANES=8,AW=$clog2(DEPTH),LW=$clog2(LANES);
    reg clk=0;
    always #5 clk=~clk;
    reg wr_v=0,pre_v=0,rd_v=0;
    reg [AW-1:0] wr_addr=0,pre_addr=0,rd_addr=0;
    reg [LW-1:0] wr_lane=0;
    reg [15:0] wr_data=0;
    reg [LANES*16-1:0] pre_data=0;
    wire [LANES*16-1:0] rd_data;
    reg [15:0] fixture [0:DEPTH*LANES-1];
    reg [1023:0] data_path;
    integer row,lane,errors=0;
    ot_hdc_v41x_he_xslice_wide #(.DEPTH(DEPTH),.LANES(LANES)) dut(.*);
    initial begin
        if (!$value$plusargs("HE_DATA=%s",data_path)) $fatal(1,"missing +HE_DATA");
        $readmemh(data_path,fixture);
        for(row=0;row<DEPTH;row=row+1) begin
            @(negedge clk);pre_v=1;pre_addr=row;
            for(lane=0;lane<LANES;lane=lane+1)
                pre_data[lane*16 +:16]=fixture[row*LANES+lane];
        end
        @(negedge clk);pre_v=0;rd_v=1;
        for(row=0;row<DEPTH;row=row+1) begin
            @(negedge clk);rd_addr=row;
            @(posedge clk);#1;
            for(lane=0;lane<LANES;lane=lane+1)
                if(rd_data[lane*16 +:16] !== fixture[row*LANES+lane]) errors=errors+1;
        end
        if(errors) $fatal(1,"HE wide errors=%0d",errors);
        $display("HE_XSLICE_WIDE_PASS preload_cycles=%0d reads=%0d errors=0",DEPTH,DEPTH*LANES);
        $finish;
    end
endmodule
