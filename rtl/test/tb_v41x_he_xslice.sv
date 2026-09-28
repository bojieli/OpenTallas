`timescale 1ns/1ps
module tb_v41x_he_xslice;
    localparam DEPTH=80, LANES=8, AW=$clog2(DEPTH), LW=$clog2(LANES);
    reg clk=0;
    always #5 clk=~clk;
    reg wr_v=0,rd_v=0;
    reg [AW-1:0] wr_addr=0,rd_addr=0;
    reg [LW-1:0] wr_lane=0;
    reg [15:0] wr_data=0;
    wire [LANES*16-1:0] rd_data;
    integer row,lane,t,errors=0;
    reg [15:0] expected_data;
    reg [15:0] real_data [0:DEPTH*LANES-1];
    reg [1023:0] real_path;
    reg use_real=0;
    ot_hdc_v41x_he_xslice #(.DEPTH(DEPTH),.LANES(LANES)) dut(.*);
    function automatic [15:0] datum(input integer r,input integer l);
        datum=use_real ? real_data[r*LANES+l] : ((r*131+l*503) & 16'hffff);
    endfunction
    initial begin
        if ($value$plusargs("HE_DATA=%s",real_path)) begin
            $readmemh(real_path,real_data);
            use_real=1;
        end
        for (row=0;row<DEPTH;row=row+1)
            for (lane=0;lane<LANES;lane=lane+1) begin
                @(negedge clk);
                wr_v=1;wr_addr=row;wr_lane=lane;wr_data=datum(row,lane);
            end
        @(negedge clk);wr_v=0;
        for(t=0;t<1000;t=t+1) begin
            @(negedge clk);rd_v=1;rd_addr=(t*37)%DEPTH;
            @(posedge clk);#1;
            for(lane=0;lane<LANES;lane=lane+1) begin
                expected_data=datum(rd_addr,lane);
                if(rd_data[lane*16 +:16] !== expected_data) begin
                    if(errors<8) $display("ERR t=%0d lane=%0d got=%h expected=%h",t,lane,
                                           rd_data[lane*16 +:16],expected_data);
                    errors=errors+1;
                end
            end
        end
        if(errors) $fatal(1,"HE xslice errors=%0d",errors);
        $display("HE_XSLICE_PASS depth=%0d lanes=%0d reads=%0d",DEPTH,LANES,1000*LANES);
        $finish;
    end
endmodule
