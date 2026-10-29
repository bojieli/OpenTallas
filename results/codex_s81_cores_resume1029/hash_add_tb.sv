`timescale 1ns/1ps
module hash_add_tb;
    reg clk=1'b0;
    always #5 clk=~clk;
    reg [63:0] a64=64'd0,b64=64'd0;
    reg [27:0] a28=28'd0,b28=28'd0;
    wire eq64,eq28,mut64,mut28;
    hash_add_miter u(.a64(a64),.b64(b64),.a28(a28),.b28(b28),.equal64(eq64),.equal28(eq28),.mut_equal64(mut64),.mut_equal28(mut28));
    integer n;
    integer caught64=0,caught28=0;
    initial begin
        for(n=0;n<20000;n=n+1)begin
            @(negedge clk);
            case(n%8)
                0:begin a64=64'hffff_ffff_ffff_ffff;b64=64'd1;end
                1:begin a64=64'd1<<((n/8)%64);b64=(64'd1<<((n/8)%64))-64'd1;end
                2:begin a64=64'haaaa_aaaa_aaaa_aaaa;b64=64'h5555_5555_5555_5555;end
                default:begin a64={$urandom,$urandom};b64={$urandom,$urandom};end
            endcase
            a28=a64[27:0];b28=b64[27:0];
            @(posedge clk);
            if(!eq64||!eq28)$fatal(1,"LOCKSTEP FAIL edge %0d",n);
            if(!mut64)caught64=caught64+1;
            if(!mut28)caught28=caught28+1;
        end
        if(caught64==0||caught28==0)$fatal(1,"mutant escaped");
        $display("HASH_ADD_LOCKSTEP PASS edges=20000 widths=64,28 mismatches=0 mutants=%0d,%0d added_cycles=0",caught64,caught28);
        $finish;
    end
endmodule
