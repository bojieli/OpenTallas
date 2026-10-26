`timescale 1ns/1ps
// Exact miter against the source-pinned r6c region. The separate FIFO bench
// provides independent queue reference and mutation gates.
module tb_qfd_vm_region_answers;
    parameter integer ROW_MUT=0, SU_MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,me_in=0;
    reg[7:0]re=0,we=0;
    reg[23:0]ra=0,wl=0;
    reg[127:0]wm=0;reg[4095:0]wd=0;
    reg xv=0,rq=0,pop=0;reg[2:0]rqb=0;
    reg[5:0]sre=0;reg[17:0]sra=0;reg[2:0]sv=0;
    reg[1:0]swe=0;reg[5:0]swl=0;reg[31:0]swm=0;reg[1023:0]swd=0;
    wire[4095:0]xo,old_xo;wire[511:0]ro,old_ro;wire[3071:0]so,old_so;wire ovf,old_ovf;
    ot_qfd_vm_region_answers #(.ROW_MUT(ROW_MUT),.SU_MUT(SU_MUT),.DEPTH(8),.LAW(3),.DEPTHS(8),.LAWS(3),.USE_MACRO(0),.NPP(12)) candidate(.*);
    ot_qfd_vm_grp #(.DEPTH(8),.LAW(3),.DEPTHS(8),.LAWS(3),.USE_MACRO(0),.NPP(12)) golden(
        .clk(clk),.rst_n(rst_n),.me_in(me_in),.re(re),.we(we),.ra(ra),.wl(wl),.wm(wm),.wd(wd),
        .xv(xv),.rq(rq),.pop(pop),.rqb(rqb),.sre(sre),.sra(sra),.sv(sv),.swe(swe),.swl(swl),.swm(swm),.swd(swd),
        .xo(old_xo),.ro(old_ro),.so(old_so),.ovf(old_ovf));
    integer cyc,l,errors=0;
    initial begin
        repeat(5)@(negedge clk);rst_n=1;
        for(cyc=0;cyc<528;cyc=cyc+1)begin
            @(negedge clk);me_in=(cyc%4!=1);
            re=255;we=(cyc%3==0)?255:0;wm={128{1'b1}};
            ra={8{3'(cyc%8)}};wl={8{3'((cyc+3)%8)}};
            for(l=0;l<128;l=l+1)wd[l*32+:32]=(cyc<<8)|l;
            xv=(cyc%48==0);pop=(cyc%48==20);
            rq=(cyc%5==0);rqb=cyc%8;
            sre=63;swe=(cyc%3==0)?3:0;swm={32{1'b1}};
            sra={6{3'(cyc%8)}};swl={2{3'((cyc+3)%8)}};sv=(cyc%5==0)?7:0;
            for(l=0;l<32;l=l+1)swd[l*32+:32]=(cyc<<8)|l;
            @(posedge clk);#1;
            if(xo!==old_xo||ro!==old_ro||so!==old_so||ovf!==old_ovf)begin
                errors=errors+1;if(errors<4)$display("REGION mismatch %0d",cyc);
            end
            if(ovf)$fatal(1,"bench credit underflow/overflow at %0d",cyc);
        end
        if(errors)$fatal(1,"FAIL regionAnswers %0d",errors);
        $display("PASS regionAnswers exact528cycles concurrentx,row,SU,write me1/4stall");$finish;
    end
endmodule
