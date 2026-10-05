`timescale 1ns/1ps
// Sequential-read bandwidth probe of the HBM model (ot_hdc_hbm_model): a
// requester issues back-to-back reads of +LEN consecutive sectors from sector 0
// up (the weight streamer's pattern) and takes every response at once; after
// +N sectors it reports sectors per core cycle, and per pseudo-channel.
module tb_hdc_hbm_probe #(
    parameter integer NPC = 4,
    parameter integer CLK_PS = 1000,
    parameter integer QD = 64,
    parameter integer RQD = 32
) (input wire clk);
    localparam integer AW = 24, LENW = 5, BEATW = 4, TAGW = 4;
    reg rst_n = 1'b0;
    reg req_v = 1'b0;
    wire req_rdy;
    reg [AW-1:0] addr = 0;
    reg [LENW-1:0] len;
    wire [NPC-1:0] rsp_v;
    wire [NPC*TAGW-1:0] rsp_tag; wire [NPC*BEATW-1:0] rsp_beat; wire [NPC*256-1:0] rsp_data;
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(256), .MEM_WORDS(4096), .TAGW(TAGW), .LENW(LENW),
                       .BEATW(BEATW), .CLK_PS(CLK_PS), .QD(QD), .RQD(RQD)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(req_v), .req_rdy(req_rdy), .req_we(1'b0), .req_addr(addr),
        .req_len(len), .req_tag({TAGW{1'b0}}), .req_wdata(256'd0),
        .rsp_v(rsp_v), .rsp_rdy({NPC{1'b1}}), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));
    integer cyc = 0, n = 0, got = 0, t0 = 0, p, nreq;
    initial begin
        if (!$value$plusargs("N=%d", nreq)) nreq = 200000;
        if (!$value$plusargs("LEN=%d", len)) len = 16;
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        if (rst_n) begin
            if (req_v && req_rdy) begin addr <= addr + len; n = n + len; end
            req_v <= (n + len <= nreq);
            for (p = 0; p < NPC; p = p + 1) if (rsp_v[p]) got = got + 1;
            if (got == 1 && t0 == 0) t0 = cyc;
            if (got >= nreq) begin
                $display("HBMPROBE npc=%0d len=%0d sectors=%0d cycles=%0d first=%0d refreshes=%0d", NPC, len, got,
                         cyc - 6, t0 - 6, u_hbm.st_ref[0]);
                $finish;
            end
        end
    end
endmodule
