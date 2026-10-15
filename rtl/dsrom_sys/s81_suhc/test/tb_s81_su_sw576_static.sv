`timescale 1ns/1ps
module tb_s81_su_sw576_static #(parameter integer MUT=0,MISSING=0);
    reg clk=0,rst=0,we=0,re=0;
    always #5 clk=~clk;
    reg [5:0] wa=0,ra=0;reg [6143:0]boot;
    reg [6143:0]stim[0:7];reg[511:0]expected[0:27];
    wire[6143:0]data;wire[11:0]wv;wire[167:0]adr;wire[191:0]mask;wire[6143:0]wd;
    reg[1:0]kind=0,pass=0,kq=0,pq=0;reg u=0,uq=0;
    wire fault;reg[11:0]presence=0;
    genvar b;
    generate for(b=0;b<12;b=b+1)begin:g_operand
        ot_sram_bank #(.DEPTH(64)) mem(.clk(clk),.we(we),.wa(wa),.wd(boot[512*b+:512]),.wm({512{1'b1}}),.re(re),.ra(ra),.q(data[512*b+:512]));
    end endgenerate
    always@(posedge clk)begin
        kq<=kind;pq<=pass;uq<=u;
        presence<=re ? ((MISSING!=0 && ra==5)?12'hffe:12'hfff):0;
    end
    ot_s81_su_sw576_static #(.MUT(MUT)) dut(.ck({152{clk}}),.rst_n(rst),
        .issue_kind(kq),.issue_pass(pq),.issue_u(uq),.present(presence),.data(data),
        .wv(wv),.wa(adr),.wm(mask),.wd(wd),.fault(fault));
    reg out_re=0;reg[5:0]out_addr=0;wire[14335:0]readback;
    generate for(b=0;b<28;b=b+1)begin:g_result
        reg [511:0]d,m;reg en;integer s,j;
        always@*begin
            d=0;m=0;en=0;
            for(s=0;s<12;s=s+1)if(wv[s] && adr[14*s+:14]==8000+b)begin
                en=1;
                for(j=0;j<16;j=j+1)if(mask[16*s+j])begin
                    d[32*j+:32]=d[32*j+:32]|wd[512*s+32*j+:32];m[32*j+:32]=32'hffffffff;
                end
            end
        end
        ot_sram_bank #(.DEPTH(64)) mem(.clk(clk),.we(en),.wa(6'd0),.wd(d),.wm(m),
            .re(out_re),.ra(6'd0),.q(readback[512*b+:512]));
    end endgenerate
    integer i,s,j,errors=0,nwrite=0,cyc=0,first=-1,last=-1;
    reg[15:0]seen[0:27];
    always@(posedge clk)begin
        cyc=cyc+1;
        for(s=0;s<12;s=s+1)if(wv[s])begin
            if(first<0)first=cyc;last=cyc;nwrite=nwrite+1;
            if(adr[14*s+:14]<8000 || adr[14*s+:14]>8027)errors=errors+1;
            else begin
                i=adr[14*s+:14]-8000;
                for(j=0;j<16;j=j+1)if(mask[16*s+j])begin
                    if(seen[i][j])errors=errors+1;
                    seen[i][j]=1;
                    if(wd[512*s+32*j+:32]!==expected[i][32*j+:32])errors=errors+1;
                end
            end
        end
    end
    integer n,r;
    initial begin
        for(n=0;n<28;n=n+1)seen[n]=0;
        $readmemh("sw_operands.mem",stim);$readmemh("sw_expected.mem",expected);
        repeat(4)@(negedge clk);rst=1;
        for(n=0;n<8;n=n+1)begin @(negedge clk);we=1;wa=n;boot=stim[n];end
        @(negedge clk);we=0;repeat(8)@(negedge clk);
        for(n=0;n<8;n=n+1)begin
            @(negedge clk);re=1;ra=n;
            kind=n==0?1:n==1?2:3;pass=n<2?0:(n-2)%3;u=n>=5;
        end
        @(negedge clk);re=0;kind=0;
        repeat(240)@(negedge clk);
        out_re=1;repeat(2)@(negedge clk);
        for(n=0;n<28;n=n+1)begin
            if(seen[n] !== ((n==9)?16'h01ff:16'hffff))errors=errors+1;
            for(r=0;r<16;r=r+1)if(seen[n][r] && readback[512*n+32*r+:32]!==expected[n][32*r+:32])errors=errors+1;
        end
        $display("STATIC_SW576 writes=%0d errors=%0d fault=%0d first=%0d last=%0d",nwrite,errors,fault,first,last);
        if(nwrite!=36 || errors || fault)$fatal(1,"STATIC_SW576 FAIL");
        $display("STATIC_SW576 PASS");$finish;
    end
endmodule
