`timescale 1ns/1ps
module tb_hdc_qwen_pc_lane_map;
    localparam P=128, AW=32, TAGW=17, MTAGW=24;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [P-1:0] s_req_v=0, s_req_we=0, s_rsp_rdy='1;
    wire [P-1:0] s_req_rdy, p_req_v, p_req_we, p_rsp_rdy, s_rsp_v, s_wr_done_v;
    reg [P*AW-1:0] s_req_addr=0;
    reg [P*TAGW-1:0] s_req_tag=0;
    reg [P*256-1:0] s_req_data=0;
    wire [P*AW-1:0] p_req_addr;
    wire [P*MTAGW-1:0] p_req_tag;
    wire [P*256-1:0] p_req_data, s_rsp_data;
    reg [P-1:0] p_req_rdy='1, p_rsp_v=0, p_wr_done_v=0;
    reg [P*MTAGW-1:0] p_rsp_tag=0, p_wr_done_tag=0;
    reg [P*256-1:0] p_rsp_data=0;
    wire [P*TAGW-1:0] s_rsp_tag, s_wr_done_tag;
    wire fault;
    ot_hdc_qwen_pc_lane_map #(.TAGW(TAGW),.MTAGW(MTAGW)) dut (.*);
    initial begin
        repeat(2) @(negedge clk); rst_n=1;
        // Real compact gate/up scale base 456 rotates source lane 0 to PC72.
        s_req_v[0]=1; s_req_addr[0 +: AW]=32'd456;
        s_req_tag[0 +: TAGW]=17'h10123;
        s_req_v[63]=1; s_req_addr[63*AW +: AW]=32'd519;
        s_req_tag[63*TAGW +: TAGW]=17'h10077;
        #1;
        if (!p_req_v[72] || !p_req_v[7] || !s_req_rdy[0] || !s_req_rdy[63] ||
            p_req_tag[72*MTAGW +: MTAGW] !== {7'd0,17'h10123} ||
            p_req_tag[7*MTAGW +: MTAGW] !== {7'd63,17'h10077})
            $fatal(1,"independent scale-base PC rotation failed");
        @(negedge clk); s_req_v=0;
        p_rsp_v[72]=1; p_rsp_tag[72*MTAGW +: MTAGW]={7'd0,17'h10123};
        p_rsp_data[72*256 +: 256]=256'h1234;
        p_rsp_v[7]=1; p_rsp_tag[7*MTAGW +: MTAGW]={7'd63,17'h10077};
        p_rsp_data[7*256 +: 256]=256'h5678;
        #1;
        if (!s_rsp_v[0] || !s_rsp_v[63] || !p_rsp_rdy[72] || !p_rsp_rdy[7] ||
            s_rsp_tag[0 +: TAGW] !== 17'h10123 ||
            s_rsp_tag[63*TAGW +: TAGW] !== 17'h10077 ||
            s_rsp_data[0 +: 256] !== 256'h1234 ||
            s_rsp_data[63*256 +: 256] !== 256'h5678)
            $fatal(1,"out-of-order response did not return to issuing lanes");
        p_wr_done_v[72]=1; p_wr_done_tag[72*MTAGW +: MTAGW]={7'd0,17'h11111};
        #1;
        if (!s_wr_done_v[0] || s_wr_done_tag[0 +: TAGW] !== 17'h11111)
            $fatal(1,"write completion lane mapping failed");
        if (fault) $fatal(1,"unexpected lane-map fault");
        $display("PASS Qwen PC lane map scale_base=456 source_lanes=0,63 PCs=72,7");
        $finish;
    end
endmodule
