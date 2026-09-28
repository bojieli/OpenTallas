`timescale 1ns/1ps
module tb_hdc_qwen_hbm_service;
    localparam NPC=128, NC=6, AW=32, CTAGW=17, PTAGW=20;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [NPC*NC-1:0] c_req_v=0, c_req_we=0, c_rsp_rdy='1;
    wire [NPC*NC-1:0] c_req_rdy, c_rsp_v, c_wr_done_v;
    reg [NPC*NC*AW-1:0] c_req_addr=0;
    reg [NPC*NC*CTAGW-1:0] c_req_tag=0;
    reg [NPC*NC*256-1:0] c_req_data=0;
    wire [NPC*NC*CTAGW-1:0] c_rsp_tag, c_wr_done_tag;
    wire [NPC*NC*256-1:0] c_rsp_data;
    wire [NPC-1:0] p_req_v, p_req_we, p_rsp_rdy, pc_fault;
    reg [NPC-1:0] p_req_rdy='1, p_rsp_v=0, p_wr_done_v=0;
    wire [NPC*AW-1:0] p_req_addr;
    wire [NPC*PTAGW-1:0] p_req_tag;
    wire [NPC*256-1:0] p_req_data;
    reg [NPC*PTAGW-1:0] p_rsp_tag=0, p_wr_done_tag=0;
    reg [NPC*256-1:0] p_rsp_data=0;
    ot_hdc_qwen_hbm_service dut (.*);
    integer pc;
    initial begin
        repeat(2) @(negedge clk);
        rst_n=1;
        for (integer k=0;k<4;k=k+1) begin
            case(k) 0:pc=0; 1:pc=31; 2:pc=32; default:pc=127; endcase
            c_req_v[pc*NC + 5]=1;
            c_req_addr[(pc*NC+5)*AW +: AW]=32'(pc);
            c_req_tag[(pc*NC+5)*CTAGW +: CTAGW]=17'(k+1);
        end
        #1;
        for (integer k=0;k<4;k=k+1) begin
            case(k) 0:pc=0; 1:pc=31; 2:pc=32; default:pc=127; endcase
            if (!p_req_v[pc] || !c_req_rdy[pc*NC+5] ||
                p_req_addr[pc*AW +: AW] !== 32'(pc))
                $fatal(1,"stack/PC ownership request %0d",pc);
        end
        @(negedge clk); c_req_v=0;
        for (integer k=0;k<4;k=k+1) begin
            case(k) 0:pc=0; 1:pc=31; 2:pc=32; default:pc=127; endcase
            p_rsp_v[pc]=1;
            p_rsp_tag[pc*PTAGW +: PTAGW]={3'd5,17'(k+1)};
            p_rsp_data[pc*256 +: 256]=256'(k+100);
        end
        #1;
        for (integer k=0;k<4;k=k+1) begin
            case(k) 0:pc=0; 1:pc=31; 2:pc=32; default:pc=127; endcase
            if (!c_rsp_v[pc*NC+5] ||
                c_rsp_tag[(pc*NC+5)*CTAGW +: CTAGW] !== 17'(k+1) ||
                c_rsp_data[(pc*NC+5)*256 +: 256] !== 256'(k+100))
                $fatal(1,"stack/PC response owner %0d",pc);
        end
        @(negedge clk); p_rsp_v=0;
        c_req_v[32*NC]=1;
        c_req_addr[32*NC*AW +: AW]=32'd31;
        @(negedge clk); c_req_v=0;
        #1;
        if (!pc_fault[32] || |(pc_fault & ~(128'b1<<32)))
            $fatal(1,"mismatched PC-sector address was not isolated");
        $display("PASS Qwen four-stack service PCs=0,31,32,127 response_owner=1 region_fault=1");
        $finish;
    end
endmodule
