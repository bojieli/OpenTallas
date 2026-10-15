`timescale 1ns/1ps
module tb_svc_probability_pack;
    parameter integer MUT=0;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,go=0,iv=0;
    reg [9:0] rows=0,row=0;
    reg [511:0] data=0;
    wire ov,dn,flt; wire [8:0] word; wire [511:0] od;
    integer errors=0, checked=0, ends=0, r,h,n;
    reg [255:0] lo,cv; reg [511:0] want;
    reg [31:0] x;
    ot_s81_svc_probability_pack #(.MUT(MUT)) u(clk,rst_n,go,rows,iv,row,data,ov,word,od,dn,flt);
    task automatic tick;
        begin @(posedge clk); #1; end
    endtask
    initial begin
        tick(); @(negedge clk); rst_n=1;
        // Full production maximum and non-multiple-of-two case T=133.
        for(n=0;n<2;n=n+1) begin
            @(negedge clk); go=1;rows=(n==0)?640:133; tick();
            @(negedge clk); go=0;
            for(r=0;r<rows;r=r+1) begin
                iv=1;row=r;data=0;cv=0;
                for(h=0;h<16;h=h+1) begin
                    // Halfway ties with even/odd retained LSB, less/greater
                    // than half, +0, tiny/subnormal probabilities.
                    case(h%6)
                    0:x=32'h3f008000; 1:x=32'h3f018000;
                    2:x=32'h3f007fff+r; 3:x=32'h3f008001+r;
                    4:x=32'h00000000; default:x=32'h00018000;
                    endcase
                    if (h%6 < 4) x=x ^ ((r%2)<<16);
                    data[h*32+:32]=x;
                    cv[h*16+:16]=(x+32'h00007fff+((x>>16)&1))>>16;
                end
                if(r%2==1) want={cv,lo};else begin lo=cv;want={256'd0,cv};end
                tick();
                if(ov != ((r%2==1)||(r+1==rows))) errors=errors+1;
                if(ov) begin checked=checked+1;if(word!==r/2||od!==want) errors=errors+1;end
                if(dn!=(r+1==rows)) errors=errors+1;
                if(dn) ends=ends+1;
                @(negedge clk);
                // Fixed compile-time gap every seventh input. Not ready driven.
                if(r%7==0) begin iv=0;tick();if(ov||dn)errors=errors+1;@(negedge clk);end
            end
            iv=0;tick();if(flt) errors=errors+1;
        end
        @(negedge clk);go=1;rows=3;tick();
        @(negedge clk);go=0;iv=1;row=1;data=0;tick();
        if(!flt)errors=errors+1;
        @(negedge clk);iv=0;rst_n=0;tick();if(ov||dn||flt)errors=errors+1;
        @(negedge clk);rst_n=1;tick();if(ov||dn||flt)errors=errors+1;
        $display("PROBPACK checked=%0d ends=%0d errors=%0d verdict=%s",checked,ends,errors,(errors==0&&checked==387&&ends==2)?"PASS":"FAIL");
        if(errors!=0) $fatal(1,"probability pack mismatch");
        $finish;
    end
endmodule
