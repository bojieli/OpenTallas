`timescale 1ns/1ps
// Full rank1280-element canonical MOE_SUM component. Seven actual operand
// stores, five actual alignment SRAMs, six native FP32-add leaves and actual
// result SRAM. The boundary stimuli/expected answers come from external files.
module tb_s81_su_moe_sum_static;
    parameter integer MUT=0,MISSING=0;
    reg clk=0,rst_n=0,we=0,ren=0;
    always #5 clk=~clk;
    reg[6:0]wa=0,ra=0;reg[3583:0]boot;
    wire[3583:0]operands;
    wire[6:0]present;
    reg rv=0;reg[13:0]rid=0;
    reg[3583:0]stim[0:79];reg[511:0]expected[0:79];
    wire ov,fault;wire[511:0]od;wire[13:0]orow;
    genvar e;
    generate for(e=0;e<7;e=e+1)begin:g_e
        wire enable=ren && !(MISSING!=0 && e==3 && ra==17);
        reg vv;
        always@(posedge clk or negedge rst_n)if(!rst_n)vv<=0;else vv<=enable;
        assign present[e]=vv;
        ot_sram_bank #(.DEPTH(128),.AW(7)) bank(.clk(clk),.we(we),.wa(wa),
            .wd(boot[512*e+:512]),.wm({512{1'b1}}),.re(enable),.ra(ra),.q(operands[512*e+:512]));
    end endgenerate
    ot_s81_su_moe_sum_static #(.MUT(MUT)) dut(.ck({6{clk}}),.rst_n(rst_n),
        .i_v(rv),.i_e(operands),.i_present(present),.i_row(rid),
        .o_v(ov),.o_d(od),.o_row(orow),.fault(fault));
    reg out_re=0;reg[6:0]out_addr=0;wire[511:0]out_data;
    ot_sram_bank #(.DEPTH(128),.AW(7)) result_store(.clk(clk),.we(ov),.wa(7'(orow-8000)),
        .wd(od),.wm({512{1'b1}}),.re(out_re),.ra(out_addr),.q(out_data));
    integer i,nout=0,errors=0,cyc=0,first=-1,last=-1;
    always@(posedge clk)begin
        if(!rst_n)begin rv<=0;rid<=0;cyc<=0;end
        else begin
            cyc<=cyc+1;rv<=ren;rid<=8000+ra;
            if(ov)begin
                if(first<0)first=cyc;last=cyc;
                if(orow!=8000+nout || od!==expected[nout])errors=errors+1;
                nout=nout+1;
            end
        end
    end
    initial begin
        $readmemh("operands.mem",stim);$readmemh("expected.mem",expected);
        repeat(4)@(negedge clk);rst_n=1;
        for(i=0;i<80;i=i+1)begin @(negedge clk);we=1;wa=i;boot=stim[i];end
        @(negedge clk);we=0;
        repeat(8)@(negedge clk);
        // Exactly80consecutive read reservations. No ready/fault/completion input.
        for(i=0;i<80;i=i+1)begin @(negedge clk);ren=1;ra=i;end
        @(negedge clk);ren=0;
        repeat(48)@(negedge clk);
        for(i=0;i<80;i=i+1)begin
            @(negedge clk);out_re=1;out_addr=i;
            @(negedge clk);
            if(out_data!==expected[i])errors=errors+1;
        end
        out_re=0;
        $display("STATIC_MOE rows=%0d errors=%0d fault=%0d first=%0d last=%0d span=%0d",nout,errors,fault,first,last,last-first+1);
        if(nout!=80 || errors || fault || last-first!=79)$fatal(1,"STATIC_MOE FAIL");
        $display("STATIC_MOE PASS");$finish;
    end
endmodule
