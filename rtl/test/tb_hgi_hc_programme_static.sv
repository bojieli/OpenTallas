`timescale 1ns/1ps
module tb_hgi_hc_programme_static(input wire clk);
    reg rst_n=0;
    integer cycle=0,errors=0,seen=0;
    reg [255:0] image[0:355];
    wire cfgwe=cycle>=5&&cycle<361;
    wire [9:0] address=10'(cycle-5);
    wire mutate=$test$plusargs("MUTANT");
    wire [255:0] data=image[address]^((mutate&&address==180)?(256'd1<<224):256'd0);
    wire clear,launch,pop,slot,tl,sl,sc,active,done,fault;
    wire [4:0] row;
    wire [31:0] eps;
    wire [43:0] c={eps,sc,sl,tl,row,slot,pop,launch,clear};
    initial $readmemh("programme.mem",image);
    ot_hgi_hc_programme_static dut(.clk(clk),.rst_n(rst_n),.cfg_we(cfgwe),.cfg_addr(address),.cfg_data(data),
        .start_v(cycle==400),.start_base(10'd0),.start_limit(11'd356),.start_loops(16'd1),
        .clear(clear),.row_launch(launch),.row_raw_read(pop),.row_weight_slot(slot),.row_id(row),
        .tail_launch(tl),.sink_launch(sl),.sink_capture(sc),.norm_eps(eps),.active(active),.done(done),.fault(fault));
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==4)rst_n<=1;
        if(cycle>=405&&cycle<761)begin
            seen<=seen+1;
            if(c!==image[cycle-405][43:0])begin errors=errors+1;$display("PROGRAMME_MISMATCH cycle%0d",cycle);end
        end
        if(fault)errors=errors+1;
        if(cycle==765)begin
            $display("HC_PROGRAMME_DONE seen=%0d errors=%0d firstconsumer405",seen,errors);
            if(seen!=356||errors)$fatal(1,"programme mismatch");
            $finish;
        end
    end
endmodule
