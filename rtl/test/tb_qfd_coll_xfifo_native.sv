`timescale 1ns/1ps
// Every received native record is checked against an independent engine/posted-consumer word model.
// Continuous gather traffic makes reservation failure observable: faster engine, slower posted consumer.
module tb_qfd_coll_xfifo_native;
    parameter integer M = 3000, META = 0;
    reg ck=0, ckd=0, rst_n=0, go=0;
    always #0.416667 ck=~ck;
    always #0.555556 ckd=~ckd;
    reg sv=0; reg [545:0] sd=0;
    wire sc, ev; wire [545:0] ed;
    reg ec=0, rv=0; reg [516:0] rd=0;
    wire ov, fc, fd; wire [516:0] od;
    qfd_coll_xfifo_native dut(.ck(ck),.ckd(ckd),.rst_n(rst_n),
        .i_seq_coll_v(sv),.i_seq_coll(sd),.i_seq_coll_cr(sc),
        .o_seq_coll_v(ev),.o_seq_coll(ed),.o_seq_coll_cr(ec),
        .i_coll_seq_v(rv),.i_coll_seq(rd),.o_coll_seq_v(ov),.o_coll_seq(od),.fault_ck(fc),.fault_ckd(fd));
    function integer gather(input integer m); gather=(m%3)!=0; endfunction
    function [511:0] data(input integer m,input integer rank);
        integer k; reg [31:0] x;
        begin x=32'h9e3779b9^(m*32'h45d9f3b)^(rank*32'h27d4eb2d);
            for(k=0;k<16;k=k+1) begin x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);data[k*32+:32]=x;end end
    endfunction
    function [31:0] tag(input integer m);
        reg [31:0] x;
        begin x=32'h9e3779b9^(m*32'h45d9f3b);x=x^(x<<13);x=x^(x>>17);tag=META?x^(x<<5):32'(m);end
    endfunction
    function integer lastflag(input integer m);lastflag=META?(m%5==0):1;endfunction
    function [516:0] result(input integer m,input integer r);
        result={1'(META&&(m%7==0)),3'(r),1'(lastflag(m)&&(r==(gather(m)?7:0))),data(m,r)};
    endfunction
    integer ns=0, credits=32, nr=0, cm=0, cr=0, bad=0, eng_bad=0, cycles=0;
    integer ew=0, er=0, rank=0, per=0, enm=0;
    reg [545:0] queue[0:M+32];
    reg [511:0] seen0=0, seen1=0;
    always @(posedge ckd) if(go) begin
        cycles=cycles+1;
        credits=credits-(sv?1:0)+(sc?1:0);
        if(sv) ns=ns+1;
        if(ov) begin
            if(cm>=M || od!==result(cm,cr)) bad=bad+1;
            nr=nr+1;seen1=seen1|od[511:0];seen0=seen0|~od[511:0];
            if(cr==(gather(cm)?7:0)) begin cm=cm+1;cr=0;end else cr=cr+1;
        end
    end
    always @(negedge ckd) if(go) begin
        sv=(ns<M)&&(credits>0);
        sd={tag(ns),1'(gather(ns)),1'(lastflag(ns)),data(ns,0)};
    end
    always @(posedge ck) if(go) begin
        ec<=ev;
        if(ev) begin
            if(ed!=={tag(ew),1'(gather(ew)),1'(lastflag(ew)),data(ew,0)}) eng_bad=eng_bad+1;
            queue[ew]=ed;ew=ew+1;
        end
        if(rv) begin
            if(rank==per-1) begin rank=0;er=er+1;end else rank=rank+1;
        end
    end
    always @(negedge ck) if(go) begin
        rv=er<ew;
        if(rv) begin enm=er;per=queue[er][513]?8:1;rd=result(enm,rank);end
    end
    initial begin
        repeat(20)@(negedge ckd);rst_n=1;
        repeat(40)@(negedge ckd);go=1;
        fork
            begin wait(cm==M||bad!=0||eng_bad!=0||fc||fd);repeat(300)@(negedge ckd);end
            begin repeat(M*80+20000)@(negedge ckd);end
        join_any
        disable fork;
        if(ns==M&&cm==M&&bad==0&&eng_bad==0&&!fc&&!fd&&(&seen0)&&(&seen1))
            $display("PASS native_coll_port messages=%0d words=%0d cycles=%0d rank3 exact posted everybeat; data everybit0and1",cm,nr,cycles);
        else $display("FAIL native_coll_port sent=%0d complete=%0d words=%0d mismatch=%0d engine_mismatch=%0d fault_ck=%0d fault_ckd=%0d",ns,cm,nr,bad,eng_bad,fc,fd);
        $finish;
    end
endmodule
