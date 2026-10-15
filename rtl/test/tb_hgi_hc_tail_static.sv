`timescale 1ns/1ps
module tb_hgi_hc_tail_static(input wire clk,sink_clk);
    localparam CASES=16,PERIOD=700;
    reg rst_n=0;
    integer cycle=0,k=0,age=0,errors=0,seen=0;
    reg [31:0] mixmem[0:CASES*24-1],basemem[0:CASES*24-1],scalemem[0:CASES*3-1],exp[0:CASES*24-1];
    wire [767:0] mixes,bases;
    wire [95:0] scales;
    wire [1:0] fault,valid,erdy;
    wire [767:0] result[0:1];
    wire launch=rst_n&&age==10;
    // Global sink clock rising edges are cycle%7==0. Reserve launch at
    // localage217 when global cycle=k*700+217, then capture41sinkedges+2.
    wire sklaunch=rst_n&&age==217;
    wire skcapture=rst_n&&age==506;
    wire mutate=$test$plusargs("MUTANT");
    initial begin
        $readmemh("tail_mix.mem",mixmem);$readmemh("tail_base.mem",basemem);
        $readmemh("tail_scale.mem",scalemem);$readmemh("tail_exp.mem",exp);
    end
    for(genvar j=0;j<24;j=j+1)begin
        assign mixes[j*32+:32]=mixmem[k*24+j];
        assign bases[j*32+:32]=basemem[k*24+j];
    end
    for(genvar j=0;j<3;j=j+1)assign scales[j*32+:32]=scalemem[k*3+j];
    for(genvar m=0;m<2;m=m+1)begin:engines
        ot_hgi_hc_tail_static #(.MUT_PRE(m)) dut(.clk(clk),.sink_clk(sink_clk),.rst_n(rst_n),
            .launch(launch),.mixes(mixes),.bases(bases),.scales(scales),
            .sink_launch(sklaunch),.sink_capture(skcapture),.e_ready(erdy[m]),
            .result_v(valid[m]),.result(result[m]),.fault(fault[m]));
    end
    always @(posedge clk)begin
        cycle<=cycle+1;
        if(cycle==6)rst_n<=1;
        if(rst_n)begin
            age<=age+1;
            if(fault[mutate])$fatal(1,"tail calendar fault case%0d age%0d",k,age);
            if(valid[mutate])begin
                if(age!=507)$fatal(1,"tail output moved cycle%0d",age);
                seen<=seen+1;
                for(integer j=0;j<24;j=j+1)if(result[mutate][j*32+:32]!==exp[k*24+j])begin
                    errors=errors+1;
                    $display("TAIL_MISMATCH case%0d word%0d got=%08x exp=%08x",k,j,result[mutate][j*32+:32],exp[k*24+j]);
                end
            end
            if(age==PERIOD-1)begin
                if(seen!=k+1)$fatal(1,"tail result missing");
                if(k==CASES-1)begin
                    $display("HC_TAIL_DONE cases=%0d errors=%0d resultcycle507",seen,errors);
                    if(errors)$fatal(1,"tail exact mismatch");
                    $finish;
                end
                k<=k+1;age<=0;
            end
        end
        if(cycle>12000)$fatal(1,"tail bench watchdog");
    end
endmodule
