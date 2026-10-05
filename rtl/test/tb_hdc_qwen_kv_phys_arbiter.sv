`timescale 1ns/1ps
module tb_hdc_qwen_kv_phys_arbiter;
    localparam AW=12,NPC=2,TAGW=5,LBK=2;
    reg clk=0,rst_n=0;
    always #5 clk=~clk;
    reg a_req_v=0,a_req_we=0,b_r_v=0,b_w_v=0,h_req_ready=0;
    reg [AW-1:0] a_req_sector=0,b_r_sector=0,b_w_sector=0;
    reg [TAGW-1:0] a_req_tag=0;
    reg [255:0] a_req_data=0,b_w_data=0;
    reg [NPC-1:0] h_rsp_v=0,a_rsp_ready=0;
    reg [NPC*TAGW-1:0] h_rsp_tag=0;
    reg [NPC*LBK-1:0] h_rsp_beat=0;
    reg [NPC*256-1:0] h_rsp_data=0;
    wire a_req_ready,b_r_ready,b_w_ready,b_r_resp_v,h_req_v,h_req_we,fault;
    wire [255:0] b_r_resp_data,h_req_data;
    wire [AW-1:0] h_req_sector;
    wire [LBK:0] h_req_len;
    wire [TAGW-1:0] h_req_tag;
    wire [NPC-1:0] a_rsp_v,h_rsp_ready;
    wire [NPC*TAGW-1:0] a_rsp_tag;
    wire [NPC*LBK-1:0] a_rsp_beat;
    wire [NPC*256-1:0] a_rsp_data;
    ot_hdc_qwen_kv_phys_arbiter #(.AW(AW),.NPC(NPC),.TAGW(TAGW),.LBK(LBK)) dut (
        .clk(clk),.rst_n(rst_n),.a_req_v(a_req_v),.a_req_ready(a_req_ready),
        .a_req_we(a_req_we),.a_req_sector(a_req_sector),.a_req_len(3'd1),
        .a_req_tag(a_req_tag),.a_req_data(a_req_data),.a_rsp_v(a_rsp_v),
        .a_rsp_ready(a_rsp_ready),.a_rsp_tag(a_rsp_tag),.a_rsp_beat(a_rsp_beat),
        .a_rsp_data(a_rsp_data),.b_r_v(b_r_v),.b_r_ready(b_r_ready),
        .b_r_sector(b_r_sector),.b_r_resp_v(b_r_resp_v),.b_r_resp_data(b_r_resp_data),
        .b_w_v(b_w_v),.b_w_ready(b_w_ready),.b_w_sector(b_w_sector),.b_w_data(b_w_data),
        .c_r_v(1'b0),.c_r_ready(),.c_r_sector('0),.c_r_resp_v(),.c_r_resp_data(),
        .h_req_v(h_req_v),.h_req_ready(h_req_ready),.h_req_we(h_req_we),
        .h_req_sector(h_req_sector),.h_req_len(h_req_len),.h_req_tag(h_req_tag),
        .h_req_data(h_req_data),.h_rsp_v(h_rsp_v),.h_rsp_ready(h_rsp_ready),
        .h_rsp_tag(h_rsp_tag),.h_rsp_beat(h_rsp_beat),.h_rsp_data(h_rsp_data),.fault(fault));
    initial begin
        repeat(2) @(negedge clk); rst_n=1;
        // Simultaneous V-sector write and streamer read: write accepted first.
        b_w_v=1; b_w_sector=12; b_w_data=256'h55;
        a_req_v=1; a_req_sector=12; a_req_tag=5'd17;
        @(negedge clk);
        if (!h_req_v || !h_req_we || h_req_sector!=12 || a_req_ready || !b_w_ready && h_req_ready)
            $fatal(1,"write was not selected first");
        h_req_ready=1;
        @(posedge clk); #1; b_w_v=0;
        @(negedge clk);
        if (h_req_v) $fatal(1,"write should retire before next request");
        @(negedge clk);
        if (!h_req_v || h_req_we || h_req_sector!=12 || h_req_tag!=17)
            $fatal(1,"streamer read missing after V write");
        @(posedge clk); #1; a_req_v=0;
        @(negedge clk); h_rsp_v=2'b10; h_rsp_tag[5 +: 5]=5'd17;
        h_rsp_data[256 +: 256]=256'habcd;
        #1;
        if (a_rsp_v!=2'b10 || a_rsp_data[256 +: 256]!=256'habcd || h_rsp_ready!=0)
            $fatal(1,"A response/backpressure mismatch state=%0d v=%b data=%h ready=%b",dut.state,a_rsp_v,a_rsp_data[256 +: 256],h_rsp_ready);
        a_rsp_ready=2'b10;
        @(posedge clk); #1; h_rsp_v=0; a_rsp_ready=0;
        // B read-modify-write response goes only to B.
        @(negedge clk); b_r_v=1; b_r_sector=13;
        @(negedge clk);
        if (!h_req_v || h_req_we || h_req_sector!=13) $fatal(1,"B RMW read missing");
        @(posedge clk); #1; b_r_v=0;
        @(negedge clk); h_rsp_v=2'b01; h_rsp_data[0 +: 256]=256'h1234;
        #1;
        if (!b_r_resp_v || b_r_resp_data!=256'h1234 || a_rsp_v || h_rsp_ready!=2'b11)
            $fatal(1,"B response misrouted");
        @(posedge clk); #1; h_rsp_v=0;
        if (fault) $fatal(1,"arbiter fault");
        $display("PASS QWEN_KV_PHYS_ARBITER"); $finish;
    end
endmodule
