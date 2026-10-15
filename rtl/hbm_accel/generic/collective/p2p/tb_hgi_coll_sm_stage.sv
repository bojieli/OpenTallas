`timescale 1ns/1ps
module tb_hgi_coll_sm_stage;
    parameter integer MUT_BANK=0,MUT_COLUMN=0;
    reg clk=0,rst_n=0;always #5 clk=~clk;
    reg [7:0] fb=0,fbank=0,pv=0,pblock=0,rv=0;
    reg [47:0] beat=0;
    reg [95:0] row=0;
    reg [2047:0] data[0:3];
    reg pre=0,pbank=0,rel=0,relbank=0;
    reg [1:0] head=0;
    reg [3:0] dimvec=0;
    reg lpi=0,lpbank=0;
    reg [3:0] group=0,lpvec=0;
    reg [1:0] lphead=0;
    integer lp_epoch=0;
    wire [3:0] lpv,selector_fault;
    wire [255:0] lpd[0:3];
    wire [3:0] group_o[0:3];
    wire [7:0] ready[0:3],done[0:3],fault[0:3];
    wire [15:0] banks[0:3];
    for(genvar q=0;q<4;q=q+1)begin:g_q
        ot_hgi_coll_sm_stage_q #(.MUT_BANK(MUT_BANK),.MUT_COLUMN(MUT_COLUMN)) dut(
            .clk_select(clk),.clk_control({8{clk}}),.clk_mem({16{clk}}),.rst_n(rst_n),
            .fill_begin(fb),.fill_bank(fbank),.pub_slot(pv),.pub_block(pblock),.pub_beat(beat),
            .rv(rv),.rrow(row),.rdata(data[q]),.prefetch_begin(pre),.prefetch_bank(pbank),
            .prefetch_head(head),.prefetch_dimvec(dimvec),.release_v(rel),.release_bank(relbank),
            .lp_issue(lpi),.lp_group(group),.lp_bank(lpbank),.lp_head(lphead),.lp_dimvec(lpvec),
            .lp_v(lpv[q]),.lp_data(lpd[q]),.lp_group_o(group_o[q]),.vector_ready(ready[q]),
            .prefetch_done(done[q]),.leaf_fault(fault[q]),.bank_ready(banks[q]),.selector_fault(selector_fault[q]));
    end
    // Test oracle uses only the actual producer pins and registered LP outputs.
    // Every word has a unique finite FP32 payload; no DUT SRAM/internal array is read.
    function automatic [31:0] value(input integer epoch,q,sm,slot,h,dim);
        return 32'h3f000000+32'((epoch<<19)+(q<<17)+(sm<<13)+(slot<<12)+(h<<8)+dim);
    endfunction
    integer scenario=0,checks=0;
    bit previous_issue=0;
    integer previous_group=0,previous_head=0,previous_vec=0,previous_epoch=0;
    always @(posedge clk)begin:monitor
        bit ci;integer cg,ch,cv,ce;
        ci=lpi;cg=integer'(group);ch=integer'(lphead);cv=integer'(lpvec);ce=lp_epoch;
        #1;
        if(rst_n&&scenario==0)begin
            for(integer q=0;q<4;q=q+1)begin
                if((|fault[q])||selector_fault[q])$fatal(1,"SM_STAGE unexpected fault q%0d leaf%h selector%0d",q,fault[q],selector_fault[q]);
                if(lpv[q]!==previous_issue)$fatal(1,"SM_STAGE LP latency q%0d got%0d expected%0d",q,lpv[q],previous_issue);
                if(previous_issue)begin
                    if(group_o[q]!==4'(previous_group))$fatal(1,"SM_STAGE group mismatch");
                    for(integer l=0;l<8;l=l+1)begin
                        if(lpd[q][l*32+:32]!==value(previous_epoch,q,previous_group/2,previous_group%2,previous_head,previous_vec*8+l))
                            $fatal(1,"SM_STAGE data mismatch q%0d group%0d h%0d vec%0d lane%0d got%h expected%h",q,previous_group,previous_head,previous_vec,l,lpd[q][l*32+:32],value(previous_epoch,q,previous_group/2,previous_group%2,previous_head,previous_vec*8+l));
                        checks=checks+1;
                    end
                end
            end
        end
        previous_issue=ci;previous_group=cg;previous_head=ch;previous_vec=cv;previous_epoch=ce;
    end
    task automatic fill(input integer epoch,input bit bank);
        @(negedge clk);fb=8'hff;fbank={8{bank}};
        @(negedge clk);fb=0;
        for(integer i=0;i<128;i=i+1)begin
            if(i!=0)@(negedge clk);
            pv=8'hff;rv=(scenario==2&&i==4)?0:8'hff;
            pblock={8{1'(i/64)}};
            for(integer sm=0;sm<8;sm=sm+1)begin
                beat[sm*6+:6]=6'(i%64);
                row[sm*12+:12]=12'(i%64+((scenario==1&&i==3)?64:0));
                for(integer q=0;q<4;q=q+1)for(integer c=0;c<8;c=c+1)
                    data[q][sm*256+c*32+:32]=value(epoch,q,sm,i/64,c/2,i%64+64*(c%2));
            end
        end
        @(negedge clk);pv=0;rv=0;
        repeat(3)@(negedge clk);
        for(integer q=0;q<4;q=q+1)for(integer sm=0;sm<8;sm=sm+1)
            if(banks[q][sm*2+integer'(bank)]!==1)$fatal(1,"SM_STAGE bank did not commit q%0d sm%0d bank%0d",q,sm,bank);
    endtask
    task automatic prefetch(input bit bank,input integer h,v);
        @(negedge clk);pre=1;pbank=bank;head=2'(h);dimvec=4'(v);
        @(posedge clk);#2;
        @(negedge clk);pre=0;
        for(integer t=1;t<=11;t=t+1)begin
            @(posedge clk);#2;
            for(integer q=0;q<4;q=q+1)begin
                if(t<11 && (|done[q]))$fatal(1,"SM_STAGE early prefetch t%0d",t);
                if(t==11 && (ready[q]!==8'hff || done[q]!==8'hff))$fatal(1,"SM_STAGE prefetch timing t%0d ready%h done%h",t,ready[q],done[q]);
            end
        end
    endtask
    task automatic groups(input integer epoch,input bit bank,input integer h,v);
        for(integer t=0;t<52;t=t+1)begin
            @(negedge clk);lpi=(t<8||t>=44);group=4'(t<8?t:t-36);
            lpbank=bank;lphead=2'(h);lpvec=4'(v);lp_epoch=epoch;
            @(posedge clk);#2;
        end
        @(negedge clk);lpi=0;
        repeat(2)begin @(posedge clk);#2;end
    endtask
    task automatic drain(input integer epoch,input bit bank);
        for(integer h=0;h<4;h=h+1)for(integer v=0;v<16;v=v+1)begin
            prefetch(bank,h,v);groups(epoch,bank,h,v);
        end
    endtask
    task automatic release_bank(input bit bank);
        @(negedge clk);rel=1;relbank=bank;
        @(negedge clk);rel=0;
        repeat(2)@(negedge clk);
    endtask
    task automatic require_fault;
        bit seen;
        seen=|selector_fault;
        for(integer q=0;q<4;q=q+1)seen=seen||(|fault[q]);
        if(!seen)$fatal(1,"SM_STAGE fault escaped scenario%0d",scenario);
        $display("SM_STAGE FAULT PASS scenario=%0d actual_macros=64 no_stall=1",scenario);$finish;
    endtask
    initial begin
        for(integer q=0;q<4;q=q+1)data[q]=0;
        if($value$plusargs("fault=%d",scenario))begin end
        repeat(5)@(negedge clk);rst_n=1;
        if(scenario==3)begin prefetch(0,0,0);require_fault();end
        if(scenario==6)begin
            @(negedge clk);lpi=1;
            @(negedge clk);lpi=0;
            @(posedge clk);#2;
            if(lpv!==4'hf)$fatal(1,"SM_STAGE invalid LP stalled instead of faulting");
            require_fault();
        end
        fill(0,0);
        if(scenario==1||scenario==2)require_fault();
        if(scenario==4)begin prefetch(0,0,0);fill(1,0);require_fault();end
        if(scenario==5)begin
            prefetch(0,0,0);
            @(negedge clk);lpi=1;lphead=1;
            @(negedge clk);lpi=0;
            @(posedge clk);#2;
            if(lpv!==4'hf)$fatal(1,"SM_STAGE identity-invalid LP stalled");
            require_fault();
        end
        // Fill the next real bank while all32SM drain the current bank.
        fork fill(1,1); join_none
        drain(0,0);release_bank(0);
        fork fill(2,0); join_none
        drain(1,1);release_bank(1);
        drain(2,0);release_bank(0);
        if(checks!=98304)$fatal(1,"SM_STAGE coverage missing %0d",checks);
        $display("SM_STAGE PASS quadrants=4 SMs=32 actual_macros=64 epochs=3 FP32_checked=%0d pub_beats=12288 writes512=6144 reads512=49152 prefetch_ready=11 LP_latency=1 ring_wave=44 allocation=UNALLOCATED",checks);
        $finish;
    end
endmodule
