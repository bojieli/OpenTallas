`timescale 1ns/1ps
module tb_chip_v41x_hbm_karb_wide;
    localparam integer NPC=32, AW=30, TAGW=16;
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0, k_v=0, k_we=0;
    reg [AW-1:0] k_addr=0;
    reg [3:0] k_len=1;
    reg [TAGW-1:0] k_tag=16'h17;
    wire k_rdy, k_done, k_rsp_v, k_rsp_rdy;
    wire [TAGW-1:0] k_rsp_tag;
    wire [3:0] k_rsp_beat;
    wire [255:0] k_rsp_data;
    wire [NPC-1:0] b_rdy, b_done, b_rsp_v, h_v, h_we, r_rdy;
    wire [NPC*AW-1:0] h_addr;
    wire [NPC*4-1:0] h_len;
    wire [NPC*(TAGW+1)-1:0] h_tag;
    wire [NPC*256-1:0] h_wdata;
    wire [NPC*32-1:0] h_wstrb;
    wire [NPC*TAGW-1:0] b_rsp_tag;
    wire [NPC*4-1:0] b_rsp_beat;
    wire [NPC*256-1:0] b_rsp_data;
    wire [31:0] kg,bg,ct;
    ot_chip_v41x_hbm_karb #(.NPC(NPC), .AW(AW), .TAGW(TAGW)) dut (
        .clk(clk), .rst_n(rst_n),
        .b_v({NPC{1'b0}}), .b_rdy(b_rdy), .b_addr({NPC*AW{1'b0}}),
        .b_len({NPC*4{1'b0}}), .b_tag({NPC*TAGW{1'b0}}),
        .b_we({NPC{1'b0}}), .b_wdata({NPC*256{1'b0}}),
        .b_wstrb({NPC*32{1'b0}}), .b_wr_done(b_done),
        .b_rsp_v(b_rsp_v), .b_rsp_rdy({NPC{1'b1}}), .b_rsp_tag(b_rsp_tag),
        .b_rsp_beat(b_rsp_beat), .b_rsp_data(b_rsp_data),
        .k_v(k_v), .k_rdy(k_rdy), .k_addr(k_addr), .k_len(k_len),
        .k_tag(k_tag), .k_we(k_we), .k_wdata(256'd0), .k_wstrb(32'd0),
        .k_wr_done(k_done), .k_rsp_v(k_rsp_v), .k_rsp_rdy(1'b1),
        .k_rsp_tag(k_rsp_tag), .k_rsp_beat(k_rsp_beat), .k_rsp_data(k_rsp_data),
        .h_v(h_v), .h_rdy({NPC{1'b1}}), .h_addr(h_addr), .h_len(h_len),
        .h_tag(h_tag), .h_we(h_we), .h_wdata(h_wdata), .h_wstrb(h_wstrb),
        .h_wr_done({NPC{1'b0}}), .r_v({NPC{1'b0}}), .r_rdy(r_rdy),
        .r_tag({NPC*(TAGW+1){1'b0}}), .r_beat({NPC*4{1'b0}}),
        .r_data({NPC*256{1'b0}}), .k_grants(kg), .b_grants(bg), .contended(ct));
    integer p, found, bad=0;
    task automatic check_addr(input [AW-1:0] want);
        begin
            @(negedge clk); k_addr=want; k_v=1;
            #0.1; found=0;
            for (p=0; p<NPC; p=p+1)
                if (h_v[p]) begin
                    found=found+1;
                    if (h_addr[p*AW +: AW] !== want || h_tag[p*(TAGW+1)+:TAGW+1] !== {1'b1,k_tag})
                        bad=bad+1;
                end
            if (found != 1 || !k_rdy) bad=bad+1;
            @(negedge clk); k_v=0;
        end
    endtask
    initial begin
        repeat(3) @(negedge clk); rst_n=1;
        check_addr(30'h20000001);
        check_addr(30'h3ffffffe);
        $display("KARB30 cases=2 bad=%0d",bad);
        if (!bad) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
