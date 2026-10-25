`timescale 1ns/1ps
module tb_dsdv_idx_vmux6;
    reg ck=0,rst=0; always #0.5 ck=~ck;
    reg [6*276-1:0] a=0;
    wire [275:0] o,m1,m2; wire f,f1,f2;
    reg [275:0] prev=0,next_word;
    reg prev_collision=0,want_fault=0;
    integer c,j,b,nvalid,bad=0,mut1=0,mut2=0;
`define CON .ck(ck),.rst(rst),.i_r(a[0+:276]),.i_s(a[276+:276]),.i_a(a[552+:276]),.i_b(a[828+:276]),.i_n(a[1104+:276]),.i_l(a[1380+:276])
    dsdv_idx_vmux6 u(`CON,.o(o),.fault(f));
    dsdv_idx_vmux6 #(.MUT(1)) u1(`CON,.o(m1),.fault(f1));
    dsdv_idx_vmux6 #(.MUT(2)) u2(`CON,.o(m2),.fault(f2));
    initial begin
        repeat(8) @(negedge ck); rst=1; repeat(12) @(negedge ck);
        for(c=0;c<2048;c=c+1) begin
            @(negedge ck);
            for(b=0;b<6*276;b=b+1) a[b]=$random;
            for(j=0;j<6;j=j+1) a[276*j]=(c%7==j)||((c%31==30)&&(j==4||j==5));
            next_word=0; nvalid=0;
            for(j=0;j<6;j=j+1) if(a[276*j]) begin next_word=next_word|a[276*j+:276]; nvalid=nvalid+1; end
            @(posedge ck); #0.01;
            want_fault=want_fault|prev_collision;
            if(o!==prev||f!==want_fault) bad=bad+1;
            if(m1!==prev||f1!==want_fault) mut1=mut1+1;
            if(m2!==prev||f2!==want_fault) mut2=mut2+1;
            prev=next_word; prev_collision=nvalid>1;
        end
        if(bad==0&&mut1>0&&mut2>0) $display("VMUX6_MITER PASS cases=%0d errors=%0d wrong_input=%0d lost_loop_valid=%0d",c,bad,mut1,mut2);
        else $fatal(1,"VMUX6_MITER FAIL errors=%0d wrong_input=%0d lost_loop_valid=%0d",bad,mut1,mut2);
        $finish;
    end
endmodule
