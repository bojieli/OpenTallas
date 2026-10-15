`timescale 1ns/1ps
module tb_s81_su_cp;
    parameter integer MUT=0;
    reg clk=0;always #0.416667 clk=~clk;
    reg rst_n=0,start=0,slot_i=0,pool_i=0,i_v=0;
    reg [31:0] group_i=0;
    reg [255:0] i_d=0;
    wire ov,done,fault,active;wire [127:0] od;wire [15:0] sch;
    ot_s81_su_cp #(.MUT(MUT)) dut(clk,rst_n,start,slot_i,pool_i,group_i,i_v,i_d,ov,od,done,fault,active,sch);
    reg [255:0] inp[0:255];reg[127:0] exp[0:127];
    integer errors=0,nout=0,j,t,slot,first=-1,last=-1;
    string dir;
    initial begin
        if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
        $readmemh({dir,"/in.mem"},inp);$readmemh({dir,"/expected.mem"},exp);
        repeat(8)@(negedge clk);rst_n=1;repeat(4)@(negedge clk);
        for(slot=0;slot<2;slot=slot+1)begin
            start=1;slot_i=slot;pool_i=slot;group_i=32'h10002;
            @(negedge clk);start=0;
            for(t=1;t<=280;t=t+1)begin
                i_v=(t>=10 && t<138);
                if(i_v)i_d=inp[128*slot+t-10];
                @(negedge clk);
                if(ov)begin
                    if(slot!=1 || nout>=128)errors=errors+1;
                    else if(od!==exp[nout])begin
                        errors=errors+1;
                        if(errors<8)$display("BAD beat%0d got%h expected%h",nout,od,exp[nout]);
                    end
                    if(first<0)first=t;last=t;nout=nout+1;
                end
                if(done)begin
                    $display("CP_DONE slot%0d cycles%0d scheduled%0d fault%0d outputs%0d",slot,t,sch,fault,nout);
                    if(t!=(slot?271:138))errors=errors+1;
                    break;
                end
            end
            i_v=0;
            if(!done || fault)errors=errors+1;
            @(negedge clk);
        end
        if(nout!=128)errors=errors+1;
        $display("CP_RESULT errors%0d words%0d first%0d last%0d",errors,nout*4,first,last);
        if(errors)$fatal(1,"CP FAIL");
        $display("CP PASS");$finish;
    end
endmodule
