`timescale 1ns/1ps
module tb_hdc_qwen_pc_service;
    localparam NC=3, AW=28, CTAGW=6, PTAGW=8;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [NC-1:0] c_req_v=0, c_req_we=0, c_rsp_rdy=3'b111;
    wire [NC-1:0] c_req_rdy, c_rsp_v, c_wr_done_v;
    reg [NC*AW-1:0] c_req_addr=0;
    reg [NC*CTAGW-1:0] c_req_tag=0;
    reg [NC*256-1:0] c_req_data=0;
    wire [NC*CTAGW-1:0] c_rsp_tag, c_wr_done_tag;
    wire [NC*256-1:0] c_rsp_data;
    wire p_req_v, p_req_we, p_rsp_rdy, fault;
    reg p_req_rdy=1, p_rsp_v=0, p_wr_done_v=0;
    wire [AW-1:0] p_req_addr;
    wire [PTAGW-1:0] p_req_tag;
    wire [255:0] p_req_data;
    reg [PTAGW-1:0] p_rsp_tag=0, p_wr_done_tag=0;
    reg [255:0] p_rsp_data=256'h1234;
    ot_hdc_qwen_pc_service #(.NC(NC),.AW(AW),.CTAGW(CTAGW),
        .MAX_OUT(2)) dut (.*);
    integer i;
    initial begin
        c_req_addr[0 +: AW]=28'h100; c_req_addr[AW +: AW]=28'h200;
        c_req_addr[2*AW +: AW]=28'h300;
        c_req_tag[0 +: CTAGW]=6'd10;
        c_req_tag[CTAGW +: CTAGW]=6'd20;
        c_req_tag[2*CTAGW +: CTAGW]=6'd30;
        c_req_we[2]=1;
        repeat(2) @(negedge clk);
        rst_n=1; c_req_v=3'b111;
        for (i=0;i<6;i=i+1) begin
            #1;
            if (!p_req_v || p_req_tag[PTAGW-1:CTAGW] !== (i%3) ||
                c_req_rdy !== (3'b001 << (i%3)))
                $fatal(1,"round-robin grant %0d tag=%h ready=%b",i,p_req_tag,c_req_rdy);
            @(negedge clk);
        end
        #1;
        if (p_req_v || fault) $fatal(1,"finite credits did not stop all clients");
        p_rsp_v=1; p_rsp_tag={2'd1,6'd20}; c_rsp_rdy[1]=0;
        #1;
        if (p_rsp_rdy || !c_rsp_v[1] || c_rsp_tag[CTAGW +: CTAGW] !== 6'd20)
            $fatal(1,"response ownership/backpressure failed");
        @(negedge clk);
        #1;
        if (p_req_v) $fatal(1,"backpressured response released credit");
        c_rsp_rdy[1]=1;
        @(negedge clk);
        p_rsp_v=0;
        #1;
        if (!p_req_v || p_req_tag[PTAGW-1:CTAGW] !== 1)
            $fatal(1,"released credit did not return to owner");
        // A completed KV write releases exactly its source credit.
        c_req_v=0; p_wr_done_v=1; p_wr_done_tag={2'd2,6'd30};
        #1;
        if (!c_wr_done_v[2] || c_wr_done_tag[2*CTAGW +: CTAGW] !== 6'd30)
            $fatal(1,"write-completion ownership failed");
        @(negedge clk);
        p_wr_done_v=0; c_req_v=3'b100;
        #1;
        if (!p_req_v || p_req_tag[PTAGW-1:CTAGW] !== 2)
            $fatal(1,"write completion did not release KV client");
        if (fault) $fatal(1,"unexpected service fault");
        $display("PASS Qwen PC service fair=6 finite=2 backpressure=1 write_done=1");
        $finish;
    end
endmodule
