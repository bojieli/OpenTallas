`timescale 1ns/1ps
module tb_hdc_qwen_kv_pc_adapter;
    localparam PCS=128, HAW=32, TAGW=25, MTAGW=32;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, page_valid=0, bridge_req_v=0, bridge_req_we=0;
    reg [HAW-1:0] kv_base_sector=139054720;
    reg [23:0] bridge_req_sector=0;
    reg [TAGW-1:0] bridge_req_tag=25'h12345;
    reg [255:0] bridge_req_data=256'h5678;
    wire bridge_req_rdy, fault;
    wire [PCS-1:0] bridge_rsp_v, pc_req_v, pc_req_we, pc_rsp_rdy;
    reg [PCS-1:0] bridge_rsp_rdy='1, pc_req_rdy='1, pc_rsp_v=0;
    wire [PCS*TAGW-1:0] bridge_rsp_tag;
    wire [PCS*256-1:0] bridge_rsp_data, pc_req_data;
    wire [PCS*HAW-1:0] pc_req_addr;
    wire [PCS*MTAGW-1:0] pc_req_tag;
    reg [PCS*MTAGW-1:0] pc_rsp_tag=0;
    reg [PCS*256-1:0] pc_rsp_data=0;
    ot_hdc_qwen_kv_pc_adapter dut (.*);
    initial begin
        repeat(2) @(negedge clk); rst_n=1; page_valid=1; bridge_req_v=1;
        bridge_req_sector=0;
        #1;
        if (!pc_req_v[0] || pc_req_addr[0 +: HAW] !== kv_base_sector)
            $fatal(1,"first packed KV sector failed physical PC0 mapping");
        bridge_req_sector=1;
        #1;
        if (!pc_req_v[1] || !bridge_req_rdy ||
            pc_req_addr[1*HAW +: HAW] !== kv_base_sector+1 ||
            pc_req_tag[1*MTAGW +: MTAGW] !== {7'd0,bridge_req_tag})
            $fatal(1,"KV logical sector1 failed physical PC1 mapping");
        pc_rsp_v[1]=1; pc_rsp_tag[1*MTAGW +: MTAGW]={7'd0,bridge_req_tag};
        pc_rsp_data[1*256 +: 256]=256'h9876;
        #1;
        if (!bridge_rsp_v[1] || bridge_rsp_tag[1*TAGW +: TAGW] !== bridge_req_tag ||
            bridge_rsp_data[1*256 +: 256] !== 256'h9876 || !pc_rsp_rdy[1])
            $fatal(1,"KV response tag/data route failed");
        pc_rsp_v=0;
        bridge_req_sector=262143;
        #1;
        if (!pc_req_v[127] || pc_req_addr[127*HAW +: HAW] !== kv_base_sector+262143)
            $fatal(1,"last packed KV sector mapped outside layer page");
        bridge_req_sector=262144;
        @(negedge clk);
        #1;
        if (!fault || bridge_req_rdy || |pc_req_v)
            $fatal(1,"out-of-page KV request did not fault closed");
        $display("PASS Qwen packed-KV bridge PC map 32B sectors page=262144 tag=25");
        $finish;
    end
endmodule
