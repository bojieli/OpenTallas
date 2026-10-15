`timescale 1ns/1ps
module tb_qfd_slab_word_half;
    parameter integer MUTANT=0;
    reg ck=0,rst_n=0;
    always #1 ck=~ck;
    reg [4111:0] bw=0;
    wire [2049:0] cw;
    qfd_slab_word_half #(.MUTANT(MUTANT)) dut (.ck(ck),.rst_n(rst_n),
        .ck_bw0(ck),.ck_bw1(ck),.ck_bw2(ck),.ck_bw3(ck),
        .ck_bw4(ck),.ck_bw5(ck),.ck_bw6(ck),.ck_bw7(ck),
        .ck_pair0(ck),.ck_pair1(ck),.ck_pair2(ck),.ck_pair3(ck),.bw(bw),.cw(cw));
    function automatic [31:0] root_value(input integer i);
        case(i)
          0:root_value=32'h3f800000; 1:root_value=32'h40000000;
          2:root_value=32'h40400000; 3:root_value=32'h40800000;
          4:root_value=32'h40a00000; 5:root_value=32'h40c00000;
          6:root_value=32'h40e00000; default:root_value=32'h41000000;
        endcase
    endfunction
    function automatic [31:0] sum_value(input integer i);
        case(i)
          0:sum_value=32'h40400000; 1:sum_value=32'h40e00000;
          2:sum_value=32'h41300000; default:sum_value=32'h41700000;
        endcase
    endfunction
    reg [2047:0] expected[0:1023];
    integer written=0,readout=0,bad=0,i,l,n,shift;
    initial begin
        repeat(12) @(negedge ck);
        rst_n=1;
        for(n=0;n<500;n=n+1) begin
            @(negedge ck);
            bw=0;
            if(n<480 && n%11!=0 && n%11!=3) begin
                shift=(n/7)%4;
                for(i=0;i<8;i=i+1) begin
                    bw[514*i+512]=1;
                    for(l=0;l<16;l=l+1)
                        bw[514*i+32*l +:32]=root_value(i)+32'h00800000*shift;
                end
                for(i=0;i<4;i=i+1)
                    for(l=0;l<16;l=l+1)
                        expected[written][512*i+32*l +:32]=sum_value(i)+32'h00800000*shift;
                written=written+1;
            end
            @(posedge ck); #0.1;
            if(cw[2048]) begin
                if(readout>=written || cw[2047:0]!==expected[readout]) bad=bad+1;
                readout=readout+1;
            end
            if(cw[2049]) bad=bad+1;
        end
        if(readout!=written || bad) $fatal(1,"SLAB_WORD_FAIL inputs=%0d outputs=%0d bad=%0d",written,readout,bad);
        $display("SLAB_WORD_PASS 8roots 4positions 16lanes fullrate words=%0d",readout);
        $finish;
    end
endmodule
