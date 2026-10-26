`timescale 1ns/1ps
module tb_hgi_coll_sm_stage_profiles;
    parameter integer MUT_BANK=0,MUT_COLUMN=0,MUT_EPOCH=0,MUT_READ_DROP=0,RAW_ONLY=0;
    reg clk=0,rst_n=0;always #5 clk=~clk;
    reg fb=0,fbank=0,pv=0,pblock=0,rv=0;
    reg [7:0] fepoch=0;
    reg [5:0] beat=0;
    reg [11:0] row=0;
    reg [255:0] data[0:31];
    reg pre=0,pbank=0,rb=0,rbank=0,rel=0,relbank=0;
    reg [7:0] pepoch=0,repoch=0;
    reg [1:0] head=0;reg [3:0] dimvec=0;
    wire [511:0] out[0:31];
    wire [31:0] vv,done,fault,rawv,rawdone,rawbank;
    wire [1:0] banks[0:31],vhead[0:31];
    wire [3:0] vvec[0:31];wire [31:0] vbank;
    wire [7:0] vepoch[0:31],rawepoch[0:31];
    wire [5:0] rawseq[0:31];
    for(genvar s=0;s<32;s=s+1)begin:g_sm
        ot_hgi_coll_sm_stage_profiles #(.MUT_BANK(MUT_BANK),.MUT_COLUMN(MUT_COLUMN),.MUT_EPOCH(MUT_EPOCH),.MUT_READ_DROP(MUT_READ_DROP)) dut(
            .clk_control(clk),.clk_mem({2{clk}}),.rst_n(rst_n),
            .fill_begin(fb),.fill_bank(fbank),.fill_epoch(fepoch),.pub_slot(pv),.pub_block(pblock),.pub_beat(beat),
            .rv(rv),.rrow(row),.rdata(data[s]),.prefetch_begin(pre),.prefetch_bank(pbank),.prefetch_epoch(pepoch),
            .prefetch_head(head),.prefetch_dimvec(dimvec),.raw_begin(rb),.raw_bank(rbank),.raw_epoch(repoch),
            .release_v(rel),.release_bank(relbank),.vectors(out[s]),.vector_valid(vv[s]),.prefetch_done(done[s]),
            .vector_bank(vbank[s]),.vector_head(vhead[s]),.vector_dimvec(vvec[s]),.vector_epoch(vepoch[s]),
            .bank_full(banks[s]),.fault(fault[s]),.raw_v(rawv[s]),.raw_done(rawdone[s]),
            .raw_seq(rawseq[s]),.raw_bank_o(rawbank[s]),.raw_epoch_o(rawepoch[s]));
    end
    function automatic [31:0] value(input integer epoch,q,sm,slot,h,dim);
        return 32'h3f000000+32'((epoch<<19)+(q<<17)+(sm<<13)+(slot<<12)+(h<<8)+dim);
    endfunction
    bit ev[0:9999],eb[0:9999];integer ee[0:9999],es[0:9999];
    integer cycle=0,scenario=0,raw_checks=0,vector_checks=0,raw_rows=0,required_raw_rows=64;
    always @(posedge clk)begin:monitor
        #1;
        if(rst_n)begin
            if(scenario==0)begin
                if(|fault)$fatal(1,"RAW_STAGE unexpected fault cycle%0d mask%h",cycle,fault);
                if(rawv!={32{ev[cycle]}})$fatal(1,"RAW_STAGE latency mismatch cycle%0d got%h expected%0d",cycle,rawv,ev[cycle]);
                if(rawdone!={32{ev[cycle]&&es[cycle]==63}})$fatal(1,"RAW_STAGE done mismatch cycle%0d",cycle);
                if(ev[cycle])begin
                    for(integer s=0;s<32;s=s+1)begin
                        if(rawseq[s]!==6'(es[cycle]) || rawbank[s]!==eb[cycle])$fatal(1,"RAW_STAGE descriptor mismatch cycle%0d sm%0d",cycle,s);
                        if(rawepoch[s]!==8'(ee[cycle]))$fatal(1,"RAW_STAGE epoch mismatch cycle%0d sm%0d got%0d expected%0d",cycle,s,rawepoch[s],ee[cycle]);
                        for(integer w=0;w<16;w=w+1)begin
                            if(out[s][w*32+:32]!==value(ee[cycle],s/8,s%8,es[cycle]%2,(w%8)/2,2*(es[cycle]/2)+w/8+64*(w%2)))
                                $fatal(1,"RAW_STAGE data mismatch cycle%0d sm%0d seq%0d word%0d got%h expected%h",cycle,s,es[cycle],w,out[s][w*32+:32],value(ee[cycle],s/8,s%8,es[cycle]%2,(w%8)/2,2*(es[cycle]/2)+w/8+64*(w%2)));
                            raw_checks=raw_checks+1;
                        end
                    end
                end
            end
            if(rawv==32'hffffffff)raw_rows=raw_rows+1;
        end
        cycle=cycle+1;
    end
    task automatic fill(input integer epoch,input bit bank);
        @(negedge clk);fb=1;fbank=bank;fepoch=8'(epoch);
        @(negedge clk);fb=0;
        for(integer i=0;i<128;i=i+1)begin
            if(i!=0)@(negedge clk);
            pv=1;rv=1;pblock=1'(i/64);beat=6'(i%64);row=12'(i%64);
            for(integer s=0;s<32;s=s+1)for(integer c=0;c<8;c=c+1)
                data[s][c*32+:32]=value(epoch,s/8,s%8,i/64,c/2,i%64+64*(c%2));
        end
        @(negedge clk);pv=0;rv=0;
        repeat(3)@(negedge clk);
        for(integer s=0;s<32;s=s+1)if(!banks[s][bank])$fatal(1,"RAW_STAGE missing committed bank");
    endtask
    task automatic vector_profile;
        for(integer h=0;h<4;h=h+1)for(integer v=0;v<16;v=v+1)begin
            @(negedge clk);pre=1;pbank=0;pepoch=1;head=2'(h);dimvec=4'(v);
            @(posedge clk);#2;
            @(negedge clk);pre=0;
            for(integer t=1;t<=11;t=t+1)begin
                @(posedge clk);#2;
                if(t<11 && (|done))$fatal(1,"RAW_STAGE vector early done");
                if(t==11)begin
                    if(vv!==32'hffffffff || done!==32'hffffffff)$fatal(1,"RAW_STAGE vector latency changed");
                    for(integer s=0;s<32;s=s+1)begin
                        if(vbank[s]!=0 || vhead[s]!=2'(h)||vvec[s]!=4'(v)||vepoch[s]!=1)$fatal(1,"RAW_STAGE vector metadata");
                        for(integer b=0;b<2;b=b+1)for(integer l=0;l<8;l=l+1)begin
                            if(out[s][b*256+l*32+:32]!==value(1,s/8,s%8,b,h,v*8+l))$fatal(1,"RAW_STAGE vector ABI data mismatch");
                            vector_checks=vector_checks+1;
                        end
                    end
                end
            end
        end
    endtask
    task automatic start_raw(input bit bank,input integer epoch);
        integer base;
        @(negedge clk);rb=1;rbank=bank;repoch=8'(epoch);
        @(posedge clk);#0.1;base=cycle;
        for(integer i=0;i<64;i=i+1)begin
            if(ev[base+4+i])$fatal(1,"RAW_STAGE compiler output collision");
            ev[base+4+i]=1;eb[base+4+i]=bank;ee[base+4+i]=epoch;es[base+4+i]=i;
        end
        @(negedge clk);rb=0;
    endtask
    task automatic release_bank(input bit bank);
        @(negedge clk);rel=1;relbank=bank;
        @(negedge clk);rel=0;
    endtask
    task automatic require_fault;
        if(!(|fault))$fatal(1,"RAW_STAGE invalid read escaped scenario%0d",scenario);
        if(raw_rows<required_raw_rows)$fatal(1,"RAW_STAGE invalid read stalled rows%0d",raw_rows);
        $display("RAW_STAGE FAULT PASS scenario=%0d fixed_raw_rows=%0d",scenario,raw_rows);$finish;
    endtask
    initial begin
        for(integer i=0;i<10000;i=i+1)begin ev[i]=0;eb[i]=0;ee[i]=0;es[i]=0;end
        for(integer s=0;s<32;s=s+1)data[s]=0;
        if($value$plusargs("fault=%d",scenario))begin end
        repeat(5)@(negedge clk);rst_n=1;
        if(scenario==1)begin start_raw(0,0);repeat(70)@(negedge clk);require_fault();end
        fill(1,0);
        if(scenario==2)begin start_raw(0,2);repeat(70)@(negedge clk);require_fault();end
        if(scenario==3)begin start_raw(1,1);repeat(70)@(negedge clk);require_fault();end
        if(scenario==4)begin start_raw(0,1);fill(2,0);repeat(70)@(negedge clk);require_fault();end
        if(scenario==5)begin
            required_raw_rows=128;
            start_raw(0,1);repeat(70)@(negedge clk);release_bank(0);fill(2,0);
            start_raw(0,1);repeat(70)@(negedge clk);require_fault();
        end
        fill(2,1);
        if(RAW_ONLY==0)vector_profile();
        start_raw(0,1);
        repeat(62)@(negedge clk);
        start_raw(1,2);
        // This release is processed on the exact last bank0 return edge.
        release_bank(0);
        fork fill(3,0);join_none
        repeat(140)@(negedge clk);
        start_raw(0,3);
        repeat(70)@(negedge clk);
        release_bank(0);release_bank(1);repeat(3)@(negedge clk);
        if(raw_checks!=98304 || (RAW_ONLY==0&&vector_checks!=32768))$fatal(1,"RAW_STAGE coverage raw%0d vector%0d",raw_checks,vector_checks);
        $display("RAW_STAGE PASS SMs=32 native_macros=64 raw_epochs=3 raw_FP32=%0d vector_FP32=%0d raw_rows_per_SM=192 first_latency=4 stream_rows=64 next_start_spacing=64 continuous_first_two_rows=128 row_order=slot0_slot1_interleave allocation=DEDICATED_PHYSICAL_PENDING",raw_checks,vector_checks);
        $finish;
    end
endmodule
