`timescale 1ns/1ps
module tb_hdc_qwen_post_tp_scale_hbm(input wire clk);
    localparam integer PCS=32, TAGW=8, HAW=28, ROWS=4096, BASE=535041;
    localparam [HAW-1:0] HBASE=28'h4000000;
    reg rst_n=0, load=0, crom_re=0;
    reg [23:0] crom_addr=0;
    wire ready, fault;
    wire [63:0] crom_q;
    wire [PCS-1:0] rq_v;
    wire [PCS*HAW-1:0] rq_addr;
    wire [PCS*TAGW-1:0] rq_tag;
    reg [PCS-1:0] rsp_v=0;
    reg [PCS*TAGW-1:0] rsp_tag=0;
    reg [PCS*256-1:0] rsp_data=0;
    reg [63:0] words [0:2*ROWS-1];
    reg [8*512-1:0] img;
    integer reads=0, cycles=0, i=0, p, j, sec, state=0;
    ot_hdc_qwen_post_tp_scale_hbm #(.PCS(PCS),.TAGW(TAGW),
        .ROWS_PER_SCALE(ROWS),.CROM_BASE(BASE)) dut (
        .clk(clk),.rst_n(rst_n),.load(load),.hbm_base_sector(HBASE),
        .ready(ready),.fault(fault),.crom_re(crom_re),.crom_addr(crom_addr),.crom_q(crom_q),
        .rq_v(rq_v),.rq_rdy({PCS{1'b1}}),.rq_addr(rq_addr),.rq_tag(rq_tag),
        .rsp_v(rsp_v),.rsp_tag(rsp_tag),.rsp_data(rsp_data));
    initial begin
        if (!$value$plusargs("IMG=%s",img)) $fatal(1,"missing IMG");
        $readmemh(img,words);
    end
    always @(negedge clk) begin
        cycles=cycles+1;
        if (cycles>10000) $fatal(1,"post-TP scale HBM timeout state=%0d row=%0d",state,i);
        case (state)
            0: if (cycles==3) begin rst_n=1; load=1; state=1; end
            1: begin load=0; state=2; end
            2: if (ready) begin
                if (fault || reads!=2048)
                    $fatal(1,"post-TP HBM preload fault=%0d sectors=%0d",fault,reads);
                crom_re=1; crom_addr=BASE; i=0; state=3;
            end
            3: begin
                if (crom_q !== words[i] || fault)
                    $fatal(1,"post-TP CROM mismatch row=%0d got=%h expected=%h fault=%0d",i,crom_q,words[i],fault);
                if (i==2*ROWS-1) begin crom_addr=BASE-1; state=4; end
                else begin i=i+1; crom_addr=BASE+i; end
            end
            4: begin
                crom_re=0;
                if (!fault) $fatal(1,"unowned CROM address did not latch fault");
                $display("PASS Qwen post-TP scale HBM 8192 words 2048 sectors exact prior to unowned-address fault");
                $finish;
            end
        endcase
    end
    always @(posedge clk) if (rst_n) begin
        rsp_v<=rq_v; rsp_tag<=rq_tag;
        for (p=0;p<PCS;p=p+1) if (rq_v[p]) begin
            sec=rq_addr[p*HAW +: HAW]-HBASE;
            if (sec<0 || sec>=2048) $fatal(1,"HBM sector out of region %0d",sec);
            for (j=0;j<4;j=j+1)
                rsp_data[p*256+j*64 +:64]<=words[4*sec+j];
            reads=reads+1;
        end
    end
endmodule
