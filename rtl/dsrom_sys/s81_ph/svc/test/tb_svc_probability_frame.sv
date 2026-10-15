`timescale 1ns/1ps
module tb_svc_probability_frame;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;reg[514:0]q=0;
    wire[514:0]qo;wire fault;
    ot_s81_svc_probability_frame #(.MUT(MUT))u(clk,rst_n,q,qo,fault);
    integer n,r,h,T,checks=0,errors=0;
    reg[511:0]hdr,want,rd;reg[255:0]lo,cv;reg[31:0]x;
    reg ev=0;reg[514:0]expected=0;
    reg[2:0]ve=0;reg[514:0]de[0:2];
    always @(posedge clk) begin
        if(!rst_n)ve<=0;
        else begin ve<={ve[1:0],ev};de[0]<=expected;de[1]<=de[0];de[2]<=de[1];end
        #1;
        if(rst_n)begin
            if(qo[0]!==ve[2])errors=errors+1;
            if(ve[2])begin checks=checks+1;if(qo!==de[2])errors=errors+1;end
        end
    end
    task tick;begin @(posedge clk);#2;end endtask
    initial begin
        tick();@(negedge clk);rst_n=1;
        for(n=0;n<2;n=n+1)begin
            T=(n==0)?640:133;
            hdr=0;hdr[511:508]=14;hdr[507]=1;hdr[502:495]=8'h91;hdr[491:480]=T;
            q={2'b01,hdr,1'b1};want=hdr;want[511:508]=5;want[491:480]=(T+1)/2;
            ev=1;expected={2'b01,want,1'b1};tick();@(negedge clk);
            for(r=0;r<T;r=r+1)begin
                rd=0;cv=0;
                for(h=0;h<16;h=h+1)begin
                    x=32'h3e008000^((r%2)<<16)^(h<<17);
                    rd[h*32+:32]=x;
                    cv[h*16+:16]=(x+32'h7fff+((x>>16)&1))>>16;
                end
                q={2'b01,rd,1'b1};
                if(r%2==1)want={cv,lo};else begin lo=cv;want={256'b0,cv};end
                ev=(r%2==1||r+1==T);expected={2'b01,want,1'b1};tick();@(negedge clk);
            end
            // Immediate next header at full input rate, exact three-edge flight.
            hdr=512'h1234;hdr[511:508]=12;hdr[491:480]=0;q={2'b01,hdr,1'b1};
            ev=1;expected=q;tick();@(negedge clk);q=0;ev=0;
            repeat(4)tick();if(fault)errors=errors+1;@(negedge clk);
        end
        $display("PROBFRAME checked=%0d latency_edges=3 errors=%0d verdict=%s",checks,errors,errors==0&&checks==391?"PASS":"FAIL");
        if(errors||checks!=391)$fatal(1,"frame pack mismatch");$finish;
    end
endmodule
