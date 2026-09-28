`timescale 1ns/1ps
module tb_hdc_qwen_int8_pc_window;
    localparam G=4, W=16, AW=24, HAW=28, PC=2, TAGW=16;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, load=0, code_re=0, scale_re=0;
    reg [AW-1:0] op_base=5, code_addr=0;
    reg [15:0] op_words=2, op_nout=32;
    reg [G*AW-1:0] scale_addr=0;
    reg [G-1:0] scale_gre={G{1'b1}};
    wire [G*W*8-1:0] code_q;
    wire [G*W*16-1:0] scale_q;
    wire ready, fault;
    wire [PC-1:0] rq_v;
    reg [PC-1:0] rq_rdy=2'b11, rsp_v=0;
    wire [PC*HAW-1:0] rq_addr;
    wire [PC*TAGW-1:0] rq_tag;
    reg [PC*TAGW-1:0] rsp_tag=0;
    reg [PC*256-1:0] rsp_data=0;
    reg [255:0] hmem [0:1100];
    integer i,j,cyc=0, reqs=0;
    ot_hdc_qwen_int8_pc_window #(.G(G),.W(W),.AW(AW),.HAW(HAW),.PCS(PC),
                                   .WIN_WORDS(2),.SCALE_WORDS(2),.TAGW(TAGW)) dut (
        .clk(clk),.rst_n(rst_n),.load(load),.op_base(op_base),.op_words(op_words),.op_nout(op_nout),
        .code_base_sector(28'd100),.scale_base_sector(28'd1000),.ready(ready),.fault(fault),
        .code_re(code_re),.code_addr(code_addr),.code_q(code_q),
        .scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr),.scale_q(scale_q),
        .rq_v(rq_v),.rq_rdy(rq_rdy),.rq_addr(rq_addr),.rq_tag(rq_tag),
        .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
    initial begin
        for (i=0;i<1101;i=i+1)
            for (j=0;j<32;j=j+1) hmem[i][8*j +: 8] = (i*17+j) & 255;
        repeat(3) @(negedge clk); rst_n=1;
        @(negedge clk); load=1;
        @(negedge clk); load=0;
        while (!ready && cyc<100) begin
            @(negedge clk); cyc=cyc+1;
            rq_rdy=cyc[0] ? 2'b01 : 2'b11;
        end
        if (!ready || fault) $fatal(1,"prefetch failed ready=%b fault=%b",ready,fault);
        code_re=1; code_addr=5;
        scale_re=1;
        scale_addr[0 +: AW]=5; scale_addr[AW +: AW]=6;
        scale_addr[2*AW +: AW]=7; scale_addr[3*AW +: AW]=5;
        @(negedge clk); code_re=0; scale_re=0;
        if (code_q !== {hmem[111],hmem[110]}) $fatal(1,"code word 5 mismatch");
        if (scale_q !== {hmem[1005],256'd0,hmem[1006],hmem[1005]})
            $fatal(1,"scale word mismatch");
        code_re=1; code_addr=6;
        @(negedge clk); code_re=0;
        if (code_q !== {hmem[113],hmem[112]}) $fatal(1,"code word 6 mismatch");
        @(negedge clk); load=1; op_words=3;
        @(negedge clk); load=0;
        if (!fault) $fatal(1,"overlong op did not fault");
        $display("PASS Qwen INT8 PC-local HBM window: %0d sectors, %0d cycles, exact codes/scales",reqs,cyc);
        $finish;
    end
    always @(posedge clk) begin
        if (rst_n) begin
            rsp_v <= rq_v & rq_rdy;
            rsp_tag <= rq_tag;
            for (integer p=0;p<PC;p=p+1)
                if (rq_v[p] && rq_rdy[p]) begin
                    if (rq_addr[p*HAW +: HAW]>1100) $fatal(1,"HBM sector address out of range");
                    rsp_data[p*256 +: 256] <= hmem[rq_addr[p*HAW +: HAW]];
                    reqs = reqs+1;
                end
        end
    end
endmodule
