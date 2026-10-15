`timescale 1ns/1ps
// q15 port-tiles hierarchy equivalence: old inline qfd_slab_word_half / qfd_slab_result_half (renamed *_old) vs the
// new leaf hierarchy (qfd_slab_pair_add / qfd_slab_port_leaf), same random stimulus, every output compared on every
// edge.  MUT=1 drives the new word half with MUTANT=1 (pair order) -> must FAIL; MUT=2 corrupts one new port's
// pt_id strap -> must FAIL.  Clocks: all entries are one scheduled family (same edge here).
module tb_halves_equiv;
    parameter integer MUT = 0;
    parameter integer CYC = 3000;
    reg ck=0; always #1 ck=~ck;
    reg rst_n=0;
    reg [8*514-1:0] bw; reg [340:0] tc; reg [2047:0] ty;
    wire [2049:0] cw_o, cw_n; wire [2212:0] rq_o, rq_n; wire [51:0] am_o, am_n;
    qfd_slab_word_half_old #(.MUTANT(0)) wo (.ck(ck),.ck_bw0(ck),.ck_bw1(ck),.ck_bw2(ck),.ck_bw3(ck),.ck_bw4(ck),.ck_bw5(ck),.ck_bw6(ck),.ck_bw7(ck),
        .ck_pair0(ck),.ck_pair1(ck),.ck_pair2(ck),.ck_pair3(ck),.rst_n(rst_n),.bw(bw),.cw(cw_o));
    qfd_slab_word_half #(.MUTANT(MUT==1)) wn (.ck(ck),.ck_bw0(ck),.ck_bw1(ck),.ck_bw2(ck),.ck_bw3(ck),.ck_bw4(ck),.ck_bw5(ck),.ck_bw6(ck),.ck_bw7(ck),
        .ck_pair0(ck),.ck_pair1(ck),.ck_pair2(ck),.ck_pair3(ck),.rst_n(rst_n),.bw(bw),.cw(cw_n));
    qfd_slab_result_half_old #(.BAND(1),.HALF(1)) ro (.ck(ck),.rst_n(rst_n),.ck_col({16{ck}}),.ck_mul({16{ck}}),.ck_group({4{ck}}),.tc(tc),.ty(ty),.rq(rq_o),.am(am_o));
    qfd_slab_result_half #(.BAND(1),.HALF(MUT==2 ? 0 : 1)) rn (.ck(ck),.rst_n(rst_n),.ck_col({16{ck}}),.ck_mul({16{ck}}),.ck_group({4{ck}}),.tc(tc),.ty(ty),.rq(rq_n),.am(am_n));
    function [31:0] rf(input integer s); begin rf = {$random(s)} ; end endfunction
    integer cyc=0, err=0, seed=7, i, act=0, ract=0, rfl=0;
    reg [31:0] r;
    task drive_inputs; begin
        for(i=0;i<8;i=i+1) begin : bwl
            integer j;
            for(j=0;j<16;j=j+1) begin r=$random(seed); bw[514*i+32*j +: 32] = {r[31],4'b1000 ^ r[30:27],r[26:0]}; end
            bw[514*i+512] = (cyc%5)!=3; bw[514*i+513] = (cyc==1700) && (i==2);
        end
        for(i=0;i<11;i=i+1) begin r=$random(seed); tc[32*i +: 32]=r; end
        r=$random(seed); tc[340:320]=r[20:0];
        for(i=0;i<64;i=i+1) begin r=$random(seed); ty[32*i +: 32]={r[31],4'b1000 ^ r[30:27],r[26:0]}; end
    end endtask
    always @(negedge ck) begin
        cyc=cyc+1; if(cyc==8) rst_n=1; if(cyc==1200) rst_n=0; if(cyc==1206) rst_n=1;
        drive_inputs;
        if (cyc>2) begin
            if (cw_o!==cw_n) begin err=err+1; if(err<4) $display("MISMATCH cw cyc %0d",cyc); end
            if (rq_o!==rq_n) begin err=err+1; if(err<4) $display("MISMATCH rq cyc %0d",cyc); end
            if (am_o!==am_n) begin err=err+1; if(err<4) $display("MISMATCH am cyc %0d",cyc); end
            if (cw_o[2048]) act=act+1;
            if ((|rq_o[2211:2208]) | am_o[50] | (|rq_o[2047:0])) ract=ract+1;
            if (am_o[51]) rfl=rfl+1;
        end
        if (cyc==CYC) begin
            $display("EQUIV MUT=%0d cycles=%0d word_active=%0d result_active=%0d result_fault=%0d mismatches=%0d %s",MUT,cyc,act,ract,rfl,err,(err==0)?"PASS":"FAIL");
            $finish;
        end
    end
endmodule
