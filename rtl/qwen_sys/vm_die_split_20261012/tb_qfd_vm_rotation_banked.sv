`timescale 1ns/1ps
module tb_qfd_vm_rotation_banked;
    parameter integer MUT=0;
    // Full 64-bank shape, 512-bit banks, nonuniform stage depths. These are test
    // depths, not claimed routed depths. Clock stalls exercise engine-edge tags.
    localparam integer W=512, LAT=2+3+4+2+3+4+6;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,me_ce=0,me_in_e=1,in_valid=0;
    reg[5:0]in_rot=0;
    reg[64*W-1:0]in_data;
    wire out_valid;wire[5:0]out_rot;wire[64*W-1:0]out_data;
    ot_qfd_vm_rotation_banked_vehicle #(.D0(2),.D1(3),.D2(4),.D3(2),.D4(3),.D5(4),.MUT(MUT)) dut(.*);
    reg[64*W-1:0]gold[0:LAT-1];reg[5:0]tags[0:LAT-1];reg[LAT-1:0]valid=0;
    reg[64*W-1:0]now;
    integer cyc,b,e,k,checked=0,errors=0,stalls=0;
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        for(cyc=0;cyc<450;cyc=cyc+1)begin
            @(negedge clk);
            me_ce=(cyc%4!=1);me_in_e=((cyc+1)%4!=1);in_valid=(cyc<360)&&(cyc%7!=2);in_rot=cyc%64;
            for(b=0;b<64;b=b+1)for(e=0;e<16;e=e+1)
                in_data[b*W+e*32+:32]=(cyc<<16)|(b<<4)|e;
            for(b=0;b<64;b=b+1)now[b*W+:W]=in_data[((b+in_rot)%64)*W+:W];
            @(posedge clk);
            if(me_ce)begin
                for(k=LAT-1;k>0;k=k-1)begin gold[k]=gold[k-1];tags[k]=tags[k-1];valid[k]=valid[k-1];end
                gold[0]=now;tags[0]=in_rot;valid[0]=in_valid;
            end else stalls=stalls+1;
            #1;
            if(out_valid!==valid[LAT-1])begin errors=errors+1;$display("VALID mismatch cycle %0d",cyc);end
            if(out_valid)begin
                checked=checked+1;
                if(out_rot!==tags[LAT-1]||out_data!==gold[LAT-1])begin
                    errors=errors+1;
                    if(errors<4)$display("DATA mismatch cycle %0d tag %0d expected %0d",cyc,out_rot,tags[LAT-1]);
                end
            end
        end
        if(errors||checked<200||stalls<100)$fatal(1,"FAIL rotation errors=%0d checked=%0d stalls=%0d",errors,checked,stalls);
        $display("PASS full64x512 rotation checked=%0d stalls=%0d LAT=%0d",checked,stalls,LAT);$finish;
    end
endmodule
