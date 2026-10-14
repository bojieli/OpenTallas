`timescale 1ns/1ps
module tb_qwen_xepoch_cache;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    integer cyc=0;
    always @(posedge clk) cyc<=cyc+1;
    genvar t;
    generate for(t=0;t<768;t=t+1) begin:g
        // Four phase responses per k, 23 edges of band selection+transport.
        localparam integer PH=(32'(t)%32'd128)/32;
        wire lv=cyc>=23 && ((cyc-23)%8)==PH && (cyc-23)/8<32;
        wire [15:0] le=(cyc-23)/8;
        wire rv=cyc>=27 && cyc<27+256;
        wire [15:0] re=(cyc-27)/8;
        function automatic [127:0] px(input integer k);
            px={32'hdeadbeef ^ (32'(t)%32'd128),32'h13572468 ^ k,32'ha55aa55a ^ (k*32'd8191),32'h12345678 ^ ((32'(t)%32'd128)+k)};
        endfunction
        wire qv,f;wire [127:0] q;
        ot_qwen_xepoch_cache #(.MUT_STALE_BANK(MUT)) dut(clk,rst_n,1'b0,lv,le,px(le),rv,re,qv,q,f);
        reg expected_v;reg [127:0] expected;
        always @(posedge clk) begin
            expected_v=rv;expected=px(re);
            #1;
            if(rst_n && expected_v && (!qv || q!==expected || f)) $fatal(1,"epoch replay mismatch tile=%0d cycle=%0d k=%0d",t,cyc,re);
        end
    end endgenerate
    initial begin
        repeat(2) @(negedge clk);rst_n=1;
        repeat(285) @(negedge clk);
        $display("PASS pingpong tiles=768 k=32 j=8 read_edges=196608 roots=32 phases=4 band_latency=23 first_issue=27 issue_bubbles=0");$finish;
    end
endmodule
