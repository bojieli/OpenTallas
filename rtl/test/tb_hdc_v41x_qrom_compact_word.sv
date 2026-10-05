`timescale 1ns/1ps
module tb_hdc_v41x_qrom_compact_word;
    reg fp4=0;
    reg [4351:0] fp8_word=0;
    reg [2303:0] fp4_word=0;
    wire [4351:0] qe_word;
    reg [4351:0] fp8_image [0:3839], fp8_expected [0:3839];
    reg [2303:0] fp4_image [0:6399];
    reg [4351:0] fp4_expected [0:6399];
    string dir;
    integer checks=0;
    ot_hdc_v41x_qrom_compact_word dut (
        .fp4(fp4),.fp8_word(fp8_word),.fp4_word(fp4_word),.qe_word(qe_word));
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"fixture DIR missing");
        $readmemh({dir,"/fp8_physical.hex"},fp8_image);
        $readmemh({dir,"/fp8_logical.hex"},fp8_expected);
        $readmemh({dir,"/fp4_physical.hex"},fp4_image);
        $readmemh({dir,"/fp4_logical.hex"},fp4_expected);
        fp4=0;
        for(integer i=0;i<3840;i++) begin
            fp8_word=fp8_image[i]; #1;
            if(qe_word!==fp8_expected[i]) $fatal(1,"FP8 word mismatch %0d",i);
            checks++;
        end
        fp4=1;
        for(integer i=0;i<6400;i++) begin
            fp4_word=fp4_image[i]; #1;
            if(qe_word!==fp4_expected[i]) $fatal(1,"FP4 word mismatch %0d",i);
            checks++;
        end
        $display("QROM_COMPACT_PASS words=%0d fp8=3840 fp4=6400",checks);
        $finish;
    end
endmodule
