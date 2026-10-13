`timescale 1ns/1ps
module tb_qfd_vm_xfifo32_t;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg me_in=0;
    reg[1:0]rtg=0,pgw=0,xg=0;
    reg[1023:0]bx;
    wire[1023:0]xo;
    ot_qfd_vm_xfifo32_t #(.MUT(MUT)) dut(.*);
    reg mr=0;reg[1:0]pp=0,xv=0;
    reg[511:0]queue[0:1][0:6];
    integer wp[0:1],rp[0:1],count[0:1];
    reg[1023:0]expect_q;
    reg[1:0]pop_now;
    integer cyc,b,l,popped=0,errors=0,maximum=0;
    initial begin
        for(b=0;b<2;b=b+1)begin wp[b]=0;rp[b]=0;count[b]=0;end
        repeat(3)@(negedge clk);rtg=3;
        for(cyc=0;cyc<512;cyc=cyc+1)begin
            @(negedge clk);
            me_in=cyc%4!=1;
            // Four pushes followed by four credited pops; never empty/full.
            // The engine is stalled1/4 clocks while SRAM-side pushes use hclk.
            xg=(cyc%32==0||cyc%32==2||cyc%32==4||cyc%32==6)?3:0;
            pgw=(cyc%32==12||cyc%32==16||cyc%32==20||cyc%32==24)?3:0;
            for(l=0;l<32;l=l+1)bx[l*32+:32]=(cyc<<8)|l;
            @(posedge clk);
            pop_now={2{mr}}&pp;
            for(b=0;b<2;b=b+1)begin
                if(pop_now[b])begin
                    if(count[b]<=0)$fatal(1,"bench underflow");
                    expect_q[b*512+:512]=queue[b][rp[b]];
                    rp[b]=(rp[b]+1)%7;count[b]=count[b]-1;
                end
                if(xv[b])begin
                    if(count[b]>=7)$fatal(1,"bench overflow");
                    queue[b][wp[b]]=bx[b*512+:512];
                    wp[b]=(wp[b]+1)%7;count[b]=count[b]+1;
                    if(count[b]>maximum)maximum=count[b];
                end
            end
            if(mr)pp=pgw;
            xv=xg;mr=me_in;
            #1;
            if(|pop_now)begin
                popped=popped+1;
                if(xo!==expect_q)begin
                    errors=errors+1;
                    if(errors<4)$display("FIFO mismatch cycle=%0d",cyc);
                end
            end
        end
        if(errors||popped!=64||count[0]||count[1])
            $fatal(1,"FAIL FIFO errors=%0d pops=%0d pending=%0d/%0d",errors,popped,count[0],count[1]);
        $display("PASS FIFO32x32 NPP7 pops=%0d maximum=%0d engineStall1/4",popped,maximum);$finish;
    end
endmodule
