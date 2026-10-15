`timescale 1ns/1ps
module tb_s81_su_cn_ik #(parameter integer D=128,MUT_NO_ROPE=0);
    localparam integer NE=D/8,NQ=D/32;
    reg clk=0;always #0.5 clk=~clk;
    reg rst=0,go=0,gv=0,xv=0;
    reg [D*32-1:0] x,gain;
    reg [1023:0] cc,ss;
    wire [D*16-1:0] y;
    wire [NQ-1:0] yv;wire [NQ*144-1:0] raw;
    wire fault;
    ot_s81_su_cn_ik #(.D(D),.E4M3(D==512),.MUT_NO_ROPE(MUT_NO_ROPE)) dut(
        .ck_norm({NE{clk}}),.rs_norm({NE{rst}}),.ck_half({2{clk}}),.rs_half({2{rst}}),
        .ck_reduce(clk),.rs_reduce(rst),.ck_align({NE{clk}}),.rs_align({NE{rst}}),
        .ck_quant({NQ{clk}}),.rs_quant({NQ{rst}}),.go(go),.gain_v(gv),.x_v(xv),
        .gain(gain),.x(x),.eps(32'h358637bd),.cos_t(cc),.sin_t(ss),.y(y),.y_v(yv),.raw(raw),.fault(fault));
    reg [31:0] xm[0:D-1],wm[0:D-1],cm[0:31],sm[0:31];
    reg [15:0] expected[0:D-1];reg [143:0] expected_raw[0:NQ-1];
    integer i,q,j,bad=0,seen=0,cyc=0;
    always @(negedge clk) if(rst)begin
        cyc=cyc+1;
        for(q=0;q<NQ;q=q+1)if(yv[q])begin
            seen=seen+32;
            if(raw[144*q+:144] !== expected_raw[q])begin
                $display("CNIK raw mismatch D=%0d block=%0d got=%h want=%h",D,q,raw[144*q+:144],expected_raw[q]);bad=bad+1;
            end
            for(j=0;j<32;j=j+1)if(y[512*q+16*j+:16]!==expected[32*q+j])begin
                if(bad<10)$display("CNIK mismatch D=%0d lane=%0d got=%h want=%h",D,32*q+j,y[512*q+16*j+:16],expected[32*q+j]);
                bad=bad+1;
            end
        end
    end
    initial begin
        $readmemh("x.mem",xm);$readmemh("gain.mem",wm);$readmemh("cos.mem",cm);$readmemh("sin.mem",sm);$readmemh("expected.mem",expected);$readmemh("raw.mem",expected_raw);
        for(i=0;i<D;i=i+1)begin x[32*i+:32]=xm[i];gain[32*i+:32]=wm[i];end
        for(i=0;i<32;i=i+1)begin cc[32*i+:32]=cm[i];ss[32*i+:32]=sm[i];end
        repeat(8)@(negedge clk);rst=1;
        repeat(8)@(negedge clk);gv=1;@(negedge clk);gv=0;
        repeat(8)@(negedge clk);go=1;@(negedge clk);go=0;xv=1;@(negedge clk);xv=0;
        repeat(350)@(negedge clk);
        $display("CNIK D=%0d words=%0d bad=%0d fault=%0d cycle=%0d",D,seen,bad,fault,cyc);
        if(bad || seen!=D || fault)$fatal(1,"CNIK FAIL");
        $display("CNIK PASS");$finish;
    end
endmodule
