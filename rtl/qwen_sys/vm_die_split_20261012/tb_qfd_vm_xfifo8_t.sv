`timescale 1ns/1ps
module tb_qfd_vm_xfifo8_t;
    parameter integer MUT=0;
    parameter integer NPP=12;
    reg clk=0;always #5 clk=~clk;
    reg me_in=0;
    reg[0:0]rtg=0,pgw=0,xg=0;
    reg[255:0]bx;
    wire[255:0]xo;
    ot_qfd_vm_xfifo8_t #(.MUT(MUT),.NPP(NPP)) dut(.*);
    reg mr=0;reg[0:0]pp=0,xv=0;
    reg[255:0]queue[0:0][0:NPP-1];
    integer wp[0:0],rp[0:0],count[0:0];
    reg[255:0]expect_q;
    reg[0:0]pop_now;
    integer cyc,b,l,popped=0,errors=0,maximum=0,steady_pops=0,steady_budget=0;
    initial begin
        for(b=0;b<1;b=b+1)begin wp[b]=0;rp[b]=0;count[b]=0;end
        repeat(3)@(negedge clk);rtg=1;
        for(cyc=0;cyc<512;cyc=cyc+1)begin
            @(negedge clk);
            me_in=cyc%4!=1;
            // Prefill four credits, then sustain one1024-bitbeat perenabled
            // engineedge. Clock-sidepush andenginepop stayfinite andmatched.
            if(cyc<8)begin xg=(cyc<4)?1:0;pgw=0;end
            else if(cyc<400)begin xg=me_in?1:0;pgw=1;end
            else begin xg=0;pgw=(cyc%4==0 && count[0]>0)?1:0;end
            for(l=0;l<8;l=l+1)bx[l*32+:32]=(cyc<<8)|l;
            @(posedge clk);
            pop_now={1{mr}}&pp;
            if(cyc>=16 && cyc<392)begin
                if(mr)steady_budget=steady_budget+1;
                if(pop_now==1)steady_pops=steady_pops+1;
            end
            for(b=0;b<1;b=b+1)begin
                if(pop_now[b])begin
                    if(count[b]<=0)$fatal(1,"bench underflow");
                    expect_q[b*256+:256]=queue[b][rp[b]];
                    rp[b]=(rp[b]+1)%NPP;count[b]=count[b]-1;
                end
                if(xv[b])begin
                    if(count[b]>=NPP)$fatal(1,"bench overflow");
                    queue[b][wp[b]]=bx[b*256+:256];
                    wp[b]=(wp[b]+1)%NPP;count[b]=count[b]+1;
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
        if(errors||popped!=298||steady_pops!=282||steady_pops!=steady_budget||count[0])
            $fatal(1,"FAIL FIFO errors=%0d pops=%0d pending=%0d",errors,popped,count[0]);
        $display("PASS FIFO8x32 NPP%0d pops=%0d maximum=%0d steady=%0d/%0d engineStall1/4",NPP,popped,maximum,steady_pops,steady_budget);$finish;
    end
endmodule
