`timescale 1ns/1ps
module tb_hdc_v41x_idx_shard_quarter_collect;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,cmd_v=0,o_ready=0;
    reg [29:0] cmd_nkeys=0;
    wire busy,fault,o_valid;
    wire [15:0] i_ready;
    reg [15:0] i_valid;
    reg [255:0] i_kv;
    reg [16*16*544-1:0] i_key;
    wire [63:0] o_kv,o_ref;
    wire [3:0] o_last;
    wire [64*544-1:0] o_key;
    ot_hdc_v41x_idx_shard_quarter_collect dut (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(cmd_nkeys),.busy(busy),.fault(fault),
        .i_valid(i_valid),.i_ready(i_ready),.i_kv(i_kv),.i_key(i_key),
        .o_valid(o_valid),.o_ready(o_ready),.o_kv(o_kv),.o_last(o_last),.o_key(o_key),.o_ref(o_ref));
    integer first[0:15],cnt[0:15],src[0:15],total[0:15],delay_ctr[0:15];
    integer n,qs,received,expected_beats,cycles,seed=32'h31415926;
    integer max_gap,last_accept_cycle;
    reg fast;
    integer s,q,j,i,physical,local_key,global_key,qlen,pos;
    reg [543:0] word;
    reg [31:0] scales;
    reg stalled_prev=0;
    reg [63:0] held_out_kv,held_out_ref;
    reg [3:0] held_out_last;
    reg [64*544-1:0] held_out_key;
    function automatic integer rank(input integer x,input integer stack);
        integer t;
        begin t=x%64-16*stack;if(t<0)t=0;if(t>16)t=16;rank=(x/64)*16+t;end
    endfunction
    function automatic [543:0] make_key(input integer g);
        reg [543:0] k;
        integer b;
        begin
            for(b=0;b<16;b=b+1)
                k[b*32 +:32]=(32'(g)*32'h9e3779b9) ^ (32'(b)*32'h7f4a7c15) ^ 32'hbda91f21;
            k[519:512]=8'((g*3)%256);
            k[527:520]=8'((g*7+3)%256);
            k[535:528]=8'((g*11+9)%256);
            k[543:536]=8'((g*19+15)%256);
            make_key=k;
        end
    endfunction
    function automatic ref_key(input [31:0] x);
        ref_key=(x[7:0]>=253 || x[15:8]>=253 || x[23:16]>=253 || x[31:24]>=253);
    endfunction
    always @* begin
        i_valid=0;i_kv=0;i_key=0;
        for(integer a=0;a<16;a=a+1) begin
            i_valid[a]=(src[a]<total[a] && delay_ctr[a]==0);
            physical=(first[a]&~1023)+16*src[a];
            for(integer b=0;b<16;b=b+1) begin
                local_key=physical+b;
                // Model the streamer's leading, skipped physical lanes as
                // asserted kv carrying garbage.  They must be cropped.
                i_kv[a*16+b]=(local_key<first[a]+cnt[a]);
                global_key=(local_key/16)*64+(a/4)*16+(local_key%16);
                i_key[(a*16+b)*544 +:544]=make_key(global_key);
            end
        end
    end
    task automatic start_case(input integer keys);
        integer lo,hi;
        begin
            n=keys;qs=(n/32)*8;received=0;
            expected_beats=(n-3*qs+15)/16;
            for(integer a=0;a<16;a=a+1) begin
                lo=(a%4)*qs;hi=(a%4==3)?n:lo+qs;
                first[a]=rank(lo,a/4);cnt[a]=rank(hi,a/4)-first[a];
                src[a]=0;delay_ctr[a]=fast ? 0 : a%4;
                total[a]=((first[a]+cnt[a]+15)/16)-((first[a]&~1023)/16);
            end
            @(negedge clk);cmd_nkeys=keys;cmd_v=1;
            @(negedge clk);cmd_v=0;
            cycles=0;max_gap=0;last_accept_cycle=-1;
            while(received<expected_beats && cycles<20000) begin
                @(negedge clk);cycles=cycles+1;
            end
            if(received!=expected_beats) $fatal(1,"timeout n=%0d got=%0d/%0d",n,received,expected_beats);
            @(negedge clk);
            if(busy || fault) $fatal(1,"busy/fault after n=%0d busy=%b fault=%b",n,busy,fault);
            $display("PASS n=%0d beats=%0d cycles=%0d",n,received,cycles);
            if(fast && keys==5000) begin
                if(max_gap>2) $fatal(1,"fast output gap=%0d exceeds 2 cycles",max_gap);
                $display("FAST_PASS n=%0d beats=%0d cycles=%0d max_gap=%0d",n,received,cycles,max_gap);
            end
        end
    endtask
    always @(posedge clk) if(rst_n && busy) begin
        if(stalled_prev && (!o_valid || o_kv !== held_out_kv ||
           o_ref !== held_out_ref || o_last !== held_out_last ||
           o_key !== held_out_key)) $fatal(1,"output changed while stalled n=%0d",n);
        stalled_prev=o_valid && !o_ready;
        if(stalled_prev) begin
            held_out_kv=o_kv;held_out_ref=o_ref;held_out_last=o_last;held_out_key=o_key;
        end
        o_ready<=fast ? 1'b1 : (($random(seed)&3)!=0);
        for(integer a=0;a<16;a=a+1) begin
            if(i_valid[a] && i_ready[a]) begin
                src[a]=src[a]+1;
                delay_ctr[a]=fast ? 0 : ($random(seed)&3);
            end else if(delay_ctr[a]>0) delay_ctr[a]=delay_ctr[a]-1;
        end
        if(o_valid && o_ready) begin
            if(last_accept_cycle>=0 && cycles-last_accept_cycle>max_gap)
                max_gap=cycles-last_accept_cycle;
            last_accept_cycle=cycles;
            for(integer a=0;a<4;a=a+1) begin
                qlen=(a==3)?n-3*qs:qs;
                if(o_last[a] !== ((qlen==0)?(received==0):(received==(qlen-1)/16)))
                    $fatal(1,"last n=%0d beat=%0d quarter=%0d",n,received,a);
                for(integer b=0;b<16;b=b+1) begin
                    pos=received*16+b;
                    if(o_kv[a*16+b] !== (pos<qlen))
                        $fatal(1,"kv n=%0d beat=%0d q=%0d lane=%0d",n,received,a,b);
                    if(pos<qlen) begin
                        word=make_key(a*qs+pos);
                        if(o_key[(a*16+b)*544 +:544] !== word)
                            $fatal(1,"key n=%0d beat=%0d q=%0d lane=%0d",n,received,a,b);
                        scales=word[543:512];
                        if(o_ref[a*16+b] !== ref_key(scales))
                            $fatal(1,"ref n=%0d beat=%0d q=%0d lane=%0d",n,received,a,b);
                    end else if(o_key[(a*16+b)*544 +:544] !== 544'd0 || o_ref[a*16+b] !== 0)
                        $fatal(1,"padding n=%0d beat=%0d q=%0d lane=%0d",n,received,a,b);
                end
            end
            received=received+1;
        end
    end
    initial begin
        fast=$test$plusargs("fast");
        repeat(4) @(negedge clk);rst_n=1;
        start_case(1);start_case(7);start_case(8);start_case(16);
        start_case(31);start_case(32);start_case(64);start_case(96);
        start_case(160);start_case(1000);start_case(1032);
        start_case(2048);start_case(2080);start_case(5000);
        $display("PASS quarter collector campaign");$finish;
    end
endmodule
