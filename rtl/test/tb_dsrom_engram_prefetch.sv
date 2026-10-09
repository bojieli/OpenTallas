`timescale 1ns/1ps
module tb_dsrom_engram_prefetch #(
    parameter [71:0] INJECT=72'd0
);
    reg ck=0;always #5 ck=~ck;
    reg rst_n=0,wv=0,rv=0;
    reg [10:0] wa=0,ra=0;
    reg [511:0] data=0;
    wire pending,ov,ce,ue,fault;
    wire [511:0] out;
    integer n,read_count=0;
    function [10:0] sparse(input integer j);
        sparse=((j/192)<<8)|(j%192);
    endfunction
    function [511:0] value(input integer j);
        integer lane;
        begin
            for(lane=0;lane<8;lane=lane+1)
                value[64*lane+:64]=(64'hcafe123400001111*j)^(64'h9876543200004567*lane);
        end
    endfunction
    ot_dsrom_engram_prefetch #(.READ_INJECT(INJECT)) dut(
        .ck(ck),.rst_n(rst_n),.wr_v(wv),.wr_addr(wa),.wr_data(data),.wr_pending(pending),
        .rd_v(rv),.rd_addr(ra),.out_v(ov),.out_data(out),.out_ce(ce),.out_ue(ue),.fault(fault));
    always @(negedge ck) if(rst_n&&ov) begin
        if(INJECT==0 || INJECT==1) begin
            if(out!==value(read_count)) $fatal(1,"prefetch payload mismatch row%0d",read_count);
            if(ce!==(INJECT==1)||ue) $fatal(1,"prefetch correction flags wrong");
        end else if(!ue) $fatal(1,"prefetch double error not rejected");
        read_count=read_count+1;
    end
    initial begin
        repeat(3) @(posedge ck);#1;rst_n=1;
        for(n=0;n<1536;n=n+1) begin
            @(posedge ck);#1;wv=1;wa=sparse(n);data=value(n);
        end
        @(posedge ck);#1;wv=0;
        repeat(3) @(posedge ck);
        if(pending) $fatal(1,"prefetch write pipeline not drained");
        for(n=0;n<1536;n=n+1) begin
            @(posedge ck);#1;rv=1;ra=sparse(n);
        end
        @(posedge ck);#1;rv=0;
        repeat(4) @(posedge ck);
        if(read_count!=1536) $fatal(1,"prefetch read accounting");
        if(fault!==(INJECT==3)) $fatal(1,"sticky ECC fault wrong");
        // Column24 is outside each slot's finite192-beat window.
        @(posedge ck);#1;wv=1;wa=11'd192;
        @(posedge ck);#1;wv=0;
        repeat(3) @(posedge ck);
        if(!fault) $fatal(1,"address bound not rejected");
        $display("ENGRAM_PREFETCH PASS words=1536 slots=8 banks=18 inject=%0d bounds=1",INJECT);$finish;
    end
endmodule
