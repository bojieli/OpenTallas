`timescale 1ns/1ps
module tb_s81_su_calendar_store;
    parameter integer MUT=0;
    reg clk=0,rst=0,arm=0,we=0,commit=0;
    always #5 clk=~clk;
    reg[5:0]addr=0;reg[3:0]lane=0;reg[63:0]data=0;
    wire[1023:0]cw;wire valid,sfault,run,flt,st,done;wire[31:0]cycle;
    wire[15:0]rq;wire[223:0]ra;wire[3:0]kind,code;wire[1:0]gs;wire f4;wire[7:0]jid,tag;wire mv;wire[13:0]mr;
    ot_s81_su_calendar_store #(.DEPTH(64)) mem(.clk(clk),.rst_n(rst),.arm(arm),
        .running(run),.cycle(cycle),.boot_we(we),.boot_commit(commit),
        .boot_addr(addr),.boot_lane(lane),.boot_data(data),.calendar_word(cw),
        .program_valid(valid),.fault(sfault));
    ot_s81_su_calendar_ctl ctl(.clk(clk),.rst_n(rst),.arm(arm),
        .calendar_valid(valid),.calendar_cycle(cycle),.calendar_word(cw),.cycle(cycle),
        .rq_v(rq),.rq_row(ra),.rs_v(16'd0),.wq_v(16'd0),.wq_row(224'd0),.wq_mask(256'd0),
        .dn_st(st),.dn_kind(kind),.dn_gsel(gs),.dn_fp4(f4),.dn_jid(jid),
        .moe_v(mv),.moe_row(mr),.done(done),.done_tag(tag),.up_fu(1'b0),.up_fo(1'b0),.up_alive(1'b1),
        .up_den(1'b1),.up_rdy(1'b0),.up_rjid(8'd0),.fault(flt),.fault_code(code),.running(run));
    function automatic [1023:0] word(input integer n);
        reg[1023:0]v;
        begin
            v=0;v[0]=1;v[29:16]=n+64;
            if(n==0)begin v[752]=1;v[756:753]=9;v[767:760]=7;end
            if(n==13)begin v[789]=1;v[803:790]=9000;end
            if(n==63)begin v[768]=1;v[776:769]=42;v[788]=1;end
            word=v;
        end
    endfunction
    integer i,j,seen=0,nd=0;reg[1023:0]v;
    always@(negedge clk)if(rq)begin
        if(ra[13:0]!=64+seen)$fatal(1,"calendar read address/order mismatch at %0d",seen);
        if(st!=(seen==0))$fatal(1,"announce moved");
        if(mv!=(seen==13) || (mv && mr!=9000))$fatal(1,"MOE compiled pulse moved");
        if(done!=(seen==63))$fatal(1,"completion moved");
        seen=seen+1;
        if(done)nd=nd+1;
    end
    initial begin
        repeat(3)@(negedge clk);rst=1;
        for(i=0;i<64;i=i+1)begin
            v=word(i);if(MUT!=0 && i==20)v[1023]=1;
            for(j=0;j<16;j=j+1)begin
                @(negedge clk);we=1;addr=i;lane=j;data=v[64*j+:64];
            end
        end
        @(negedge clk);we=0;commit=1;
        @(negedge clk);commit=0;arm=1;
        @(negedge clk);arm=0;
        repeat(68)@(negedge clk);
        $display("MAPPED_CALENDAR seen=%0d done=%0d fault=%0d storefault=%0d cycle=%0d",seen,nd,flt,sfault,cycle);
        if(seen!=64 || nd!=1 || flt || sfault || run || cycle!=64)$fatal(1,"MAPPED_CALENDAR FAIL");
        $display("MAPPED_CALENDAR PASS");$finish;
    end
endmodule
