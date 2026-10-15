`timescale 1ns/1ps
module tb_s81_su_iq #(parameter integer MUT=0);
    reg clk=0;always #0.5 clk=~clk;
    reg rst=0,start=0,qv=0;reg [4:0] head=0;
    reg [2047:0] q=0;reg [15:0] w=0;reg [1023:0] cc,ss;
    reg [511:0] hdr;
    wire fv,dn,fault;wire [511:0] fd;
    ot_s81_su_iq #(.MUT(MUT)) dut(.ck_rope({4{clk}}),.rs_rope({4{rst}}),
        .ck_quant({4{clk}}),.rs_quant({4{rst}}),.ck_delay(clk),.rs_delay(rst),
        .ck_weight(clk),.rs_weight(rst),.ck_wdelay(clk),.rs_wdelay(rst),.ck_frame(clk),.rs_frame(rst),
        .start(start),.header(hdr),.q_v(qv),.q_head(head),.q_bf16(q),.weight_proj_bf16(w),
        .cos_t(cc),.sin_t(ss),.f_v(fv),.f_d(fd),.done(dn),.fault(fault));
    reg [2047:0] qm[0:31];reg [15:0] wm[0:31];
    reg [1023:0] cm[0:1];reg [511:0] expected[0:64];
    integer h,seen=0,bad=0,cycle=0,first=-1,last=-1;
    always @(negedge clk)if(rst)begin
        cycle=cycle+1;
        if(fv)begin
            if(first<0)first=cycle;last=cycle;
            if(seen>64||fd!==expected[seen])begin
                if(bad<8)$display("IQ mismatch word=%0d got=%h want=%h",seen,fd,expected[seen]);bad=bad+1;
            end
            seen=seen+1;
        end
    end
    initial begin
        $readmemh("queries.mem",qm);$readmemh("weights.mem",wm);$readmemh("cs.mem",cm);$readmemh("expected.mem",expected);
        cc=cm[0];ss=cm[1];hdr=expected[0];
        repeat(8)@(negedge clk);rst=1;repeat(8)@(negedge clk);
        for(h=0;h<32;h=h+1)begin
            start=(h==0);qv=!(MUT==3&&h==7);head=h;q=qm[h];w=wm[h];
            @(negedge clk);start=0;qv=0;@(negedge clk);
        end
        repeat(80)@(negedge clk);
        $display("IQ words=%0d bad=%0d fault=%0d first=%0d last=%0d elapsed=%0d",seen,bad,fault,first,last,last-first);
        if(seen!=65||bad||fault||last-first!=97)$fatal(1,"IQ FAIL");
        $display("IQ PASS");$finish;
    end
    initial begin #10000;$fatal(1,"IQ TIMEOUT");end
endmodule
