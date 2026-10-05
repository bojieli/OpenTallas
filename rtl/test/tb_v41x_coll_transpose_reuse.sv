`timescale 1ns/1ps
// Two consecutive blocking descriptors catch stale local-selector state.
module tb_v41x_coll_transpose_reuse;
    localparam integer WA=12, FW=512;
    reg clk=0, rst_n=0, start=0, running=0;
    always #5 clk=~clk;
    reg [WA-1:0] dst=0, n=0;
    integer op=0, sent=0, writes=0, lasts=0, stalls=0, cyc=0;
    wire in_ready, out_valid, out_last, done, fault;
    wire [3:0] out_we;
    wire [4*WA-1:0] out_addr;
    wire [4*FW-1:0] out_data;
    reg [4*FW-1:0] in_data;
    reg [4095:0] seen=0;
    wire in_valid=running && sent<integer'(n);
    wire in_last=sent==integer'(n)-1;

    function automatic [FW-1:0] payload(input integer opid,rank,idx);
        reg [FW-1:0] p;
        begin
            for(integer j=0;j<FW/32;j=j+1)
                p[32*j+:32]=(32'(opid)<<28)|(32'(rank)<<24)|(32'(idx)<<8)|32'(j);
            return p;
        end
    endfunction
    always @(*) for(integer r=0;r<4;r=r+1) in_data[r*FW+:FW]=payload(op,r,sent);
    ot_chip_v41x_coll_transpose #(.WA(WA),.FW(FW),.OUT_PIPE(1)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.dst(dst),.n(n),
        .in_ready(in_ready),.in_valid(in_valid),.in_data(in_data),.in_last(in_last),
        .out_ready(1'b1),.out_valid(out_valid),.out_we(out_we),
        .out_addr(out_addr),.out_data(out_data),.out_last(out_last),
        .done(done),.fault(fault));

    always @(posedge clk) if(rst_n) begin : check
        integer a,rank,idx,wc;
        wc=0;cyc<=cyc+1;
        if(in_valid&&in_ready) sent<=sent+1;
        if(in_valid&&!in_ready) stalls<=stalls+1;
        if(out_last) lasts<=lasts+1;
        for(integer k=0;k<4;k=k+1) if(out_we[k]) begin
            a=integer'(out_addr[k*WA+:WA]);
            rank=(a-integer'(dst))/integer'(n);
            idx=(a-integer'(dst))%integer'(n);
            if(a<integer'(dst)||a>=integer'(dst)+4*integer'(n)||rank<0||rank>3||idx<0||idx>=integer'(n))
                $fatal(1,"reuse address out of range op=%0d addr=%0d",op,a);
            if(seen[a]||out_data[k*FW+:FW]!==payload(op,rank,idx))
                $fatal(1,"reuse data/duplicate op=%0d rank=%0d idx=%0d",op,rank,idx);
            seen[a]<=1;wc=wc+1;
        end
        writes<=writes+wc;
    end

    task automatic run_op(input integer opid,words,base,total);
        begin
            @(negedge clk);op=opid;dst=WA'(base);n=WA'(words);sent=0;start=1;running=0;
            @(negedge clk);start=0;running=1;
            wait(done||fault);
            @(negedge clk);running=0;
            if(fault||sent!=words||writes!=total||lasts!=opid+1)
                $fatal(1,"reuse completion op=%0d fault=%0d sent=%0d writes=%0d lasts=%0d",
                       opid,fault,sent,writes,lasts);
        end
    endtask
    initial begin
        repeat(5)@(negedge clk);rst_n=1;
        run_op(0,5,101,20);
        run_op(1,266,205,1084);
        if(stalls==0)$fatal(1,"reuse stress did not backpressure input");
        $display("TRANSPOSE_REUSE_PASS ops=2 writes=%0d lasts=%0d stalls=%0d cycles=%0d",writes,lasts,stalls,cyc);
        $finish;
    end
    initial begin #1000000;$fatal(1,"transpose reuse timeout");end
endmodule
