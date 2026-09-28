`timescale 1ns/1ps
module tb_hdc_qwen_embed_row_hbm;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, load=0, code_re=0, scale_re=0;
    reg [15:0] token=3, scale_addr=3;
    reg [23:0] code_addr=6;
    wire ready, fault;
    wire [511:0] code_q;
    wire [15:0] scale_q;
    wire [1:0] rq_v;
    wire [55:0] rq_addr;
    wire [15:0] rq_tag;
    reg [1:0] rsp_v=0;
    reg [15:0] rsp_tag=0;
    reg [511:0] rsp_data=0;
    reg [255:0] hmem [0:200];
    integer i,j,cycles=0,reads=0;
    ot_hdc_qwen_embed_row_hbm #(.ROW_WORDS(2),.PCS(2),.TAGW(8)) dut (
        .clk(clk),.rst_n(rst_n),.load(load),.token(token),
        .code_base_sector(28'd0),.scale_base_sector(28'd100),.ready(ready),.fault(fault),
        .code_re(code_re),.code_addr(code_addr),.code_q(code_q),
        .scale_re(scale_re),.scale_addr(scale_addr),.scale_q(scale_q),
        .rq_v(rq_v),.rq_rdy(2'b11),.rq_addr(rq_addr),.rq_tag(rq_tag),
        .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
    initial begin
        for (i=0;i<201;i=i+1)
            for (j=0;j<32;j=j+1) hmem[i][8*j +: 8]=(i*13+j)&255;
        repeat(3) @(negedge clk); rst_n=1;
        @(negedge clk); load=1;
        @(negedge clk); load=0;
        while (!ready && cycles<100) begin @(negedge clk); cycles=cycles+1; end
        if (!ready || fault) $fatal(1,"embedding HBM preload failed");
        code_re=1; code_addr=6; scale_re=1;
        @(negedge clk); code_re=0; scale_re=0;
        if (code_q !== {hmem[13],hmem[12]}) $fatal(1,"embedding word 6 mismatch");
        if (scale_q !== hmem[100][3*16 +: 16]) $fatal(1,"embedding scale 3 mismatch");
        code_re=1; code_addr=7;
        @(negedge clk); code_re=0;
        if (code_q !== {hmem[15],hmem[14]}) $fatal(1,"embedding word 7 mismatch");
        if (reads!=5) $fatal(1,"wrong HBM sector count %0d",reads);
        $display("PASS Qwen embedding HBM row: token 3, 5 sectors, exact 2 code words and scale");
        $finish;
    end
    always @(posedge clk) if (rst_n) begin
        rsp_v<=rq_v; rsp_tag<=rq_tag;
        for (integer p=0;p<2;p=p+1) if (rq_v[p]) begin
            rsp_data[p*256 +: 256]<=hmem[rq_addr[p*28 +: 28]];
            reads=reads+1;
        end
    end
endmodule
