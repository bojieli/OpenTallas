`timescale 1ns/1ps
module tb_hdc_qwen_hbm_sector_bridge;
    localparam integer AW=12, NPC=2, TAGW=8, LBK=3;
    reg clk=0,rst_n=0,log_req_v=0,log_req_we=0;
    always #5 clk=~clk;
    reg [AW-1:0] log_req_addr=0;
    reg [LBK:0] log_req_len=0;
    reg [TAGW-1:0] log_req_tag=0;
    reg [127:0] log_req_data=0;
    wire log_req_ready;
    wire [NPC-1:0] log_rsp_v;
    reg [NPC-1:0] log_rsp_ready=2'b01;
    wire [NPC*TAGW-1:0] log_rsp_tag;
    wire [NPC*LBK-1:0] log_rsp_beat;
    wire [NPC*128-1:0] log_rsp_data;
    wire phys_req_v,phys_req_we,fault;
    wire [AW-1:0] phys_req_sector;
    wire [LBK:0] phys_req_len;
    wire [TAGW-1:0] phys_req_tag;
    wire [255:0] phys_req_data;
    reg [NPC-1:0] phys_rsp_v=0;
    wire [NPC-1:0] phys_rsp_ready;
    reg [NPC*TAGW-1:0] phys_rsp_tag=0;
    reg [NPC*LBK-1:0] phys_rsp_beat=0;
    reg [NPC*256-1:0] phys_rsp_data=0;
    reg [255:0] sectors[0:3];
    integer reads=0,writes=0,beats=0,cyc=0;
    reg [7:0] expected_byte;
    ot_hdc_qwen_hbm_sector_bridge #(.AW(AW),.NPC(NPC),.TAGW(TAGW),.LBK(LBK)) dut (
        .clk(clk),.rst_n(rst_n),.log_req_v(log_req_v),.log_req_ready(log_req_ready),
        .log_req_we(log_req_we),.log_req_addr(log_req_addr),.log_req_len(log_req_len),
        .log_req_tag(log_req_tag),.log_req_data(log_req_data),
        .log_rsp_v(log_rsp_v),.log_rsp_ready(log_rsp_ready),.log_rsp_tag(log_rsp_tag),
        .log_rsp_beat(log_rsp_beat),.log_rsp_data(log_rsp_data),
        .phys_req_v(phys_req_v),.phys_req_ready(1'b1),.phys_req_we(phys_req_we),
        .phys_req_sector(phys_req_sector),.phys_req_len(phys_req_len),
        .phys_req_tag(phys_req_tag),.phys_req_data(phys_req_data),
        .phys_rsp_v(phys_rsp_v),.phys_rsp_ready(phys_rsp_ready),
        .phys_rsp_tag(phys_rsp_tag),.phys_rsp_beat(phys_rsp_beat),
        .phys_rsp_data(phys_rsp_data),.fault(fault));
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (rst_n) begin
            phys_rsp_v <= 0;
            if (phys_req_v && !phys_req_we) begin
                reads <= reads+1;
                phys_rsp_v[0] <= 1;
                phys_rsp_data[0 +: 256] <= sectors[phys_req_sector];
            end
            if (phys_req_v && phys_req_we) begin
                writes <= writes+1;
                sectors[phys_req_sector] <= phys_req_data;
            end
            if (log_rsp_v[0] && log_rsp_ready[0]) begin
                expected_byte = beats==0 ? 8'h22 : beats==1 ? 8'h33 : beats==2 ? 8'h44 :
                                beats==3 ? 8'haa : 8'h44;
                if (log_rsp_data[0 +: 128] !== {16{expected_byte}} ||
                    log_rsp_beat[0 +: LBK] !== (beats<3 ? beats : beats-3) ||
                    log_rsp_tag[0 +: TAGW] !== (beats<3 ? 8'd5 : 8'd6))
                    $fatal(1,"logical response beat %0d",beats);
                beats <= beats+1;
            end
            if (fault) $fatal(1,"sector bridge fault");
            if (cyc>200) $fatal(1,"timeout");
        end
    end
    task automatic request(input bit we,input [AW-1:0] addr,input [LBK:0] len,
                           input [TAGW-1:0] tag,input [127:0] data);
        begin
            @(negedge clk);
            wait(log_req_ready);
            log_req_v=1;log_req_we=we;log_req_addr=addr;log_req_len=len;
            log_req_tag=tag;log_req_data=data;
            @(negedge clk);log_req_v=0;
        end
    endtask
    initial begin
        sectors[0]={{16{8'h22}},{16{8'h11}}};
        sectors[1]={{16{8'h44}},{16{8'h33}}};
        sectors[2]=0;sectors[3]=0;
        repeat(3) @(negedge clk);rst_n=1;
        request(0,1,3,5,0);
        wait(beats==3);
        request(1,2,1,0,{16{8'haa}});
        wait(log_req_ready);
        request(0,2,2,6,0);
        wait(beats==5);
        repeat(2) @(negedge clk);
        if (reads!=4 || writes!=1 || sectors[1][127:0] !== {16{8'haa}} ||
            sectors[1][255:128] !== {16{8'h44}}) $fatal(1,"physical transaction count/data");
        $display("PASS HBM_SECTOR_BRIDGE reads=%0d writes=%0d beats=%0d",reads,writes,beats);
        $finish;
    end
endmodule
