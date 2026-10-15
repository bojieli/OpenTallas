`timescale 1ns/1ps
module tb_svc_probability_frame;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;reg[514:0]q=0;
    wire[514:0]qo;wire fault;
    ot_s81_svc_probability_frame #(.MUT(MUT))u(clk,rst_n,q,qo,fault);
    integer n,r,h,T,checks=0,errors=0;
    reg[511:0]hdr,want,rd;reg[255:0]lo,cv;reg[31:0]x;
    task tick;begin @(posedge clk);#1;end endtask
    initial begin
        tick();@(negedge clk);rst_n=1;
        for(n=0;n<2;n=n+1)begin
            T=(n==0)?640:133;
            hdr=0;hdr[511:508]=14;hdr[507]=1;hdr[502:495]=8'h91;hdr[491:480]=T;
            q={2'b01,hdr,1'b1};want=hdr;want[511:508]=5;want[491:480]=(T+1)/2;
            tick();if(qo!=={2'b01,want,1'b1})errors=errors+1;checks=checks+1;
            @(negedge clk);
            for(r=0;r<T;r=r+1)begin
                rd=0;cv=0;
                for(h=0;h<16;h=h+1)begin
                    x=32'h3e008000^((r%2)<<16)^(h<<17);
                    rd[h*32+:32]=x;
                    cv[h*16+:16]=(x+32'h7fff+((x>>16)&1))>>16;
                end
                q={2'b01,rd,1'b1};
                if(r%2==1)want={cv,lo};else begin lo=cv;want={256'b0,cv};end
                tick();
                if(r%2==1||r+1==T)begin if(qo!=={2'b01,want,1'b1})errors=errors+1;checks=checks+1;end
                else if(qo[0])errors=errors+1;
                @(negedge clk);
            end
            // Immediate next non-PV header proves no hidden tail handshake.
            hdr=512'h1234;hdr[511:508]=12;hdr[491:480]=0;q={2'b01,hdr,1'b1};
            tick();if(qo!==q)errors=errors+1;checks=checks+1;
            @(negedge clk);q=0;tick();if(qo[0]||fault)errors=errors+1;@(negedge clk);
        end
        $display("PROBFRAME checked=%0d errors=%0d verdict=%s",checks,errors,errors==0?"PASS":"FAIL");
        if(errors)$fatal(1,"frame pack mismatch");$finish;
    end
endmodule
