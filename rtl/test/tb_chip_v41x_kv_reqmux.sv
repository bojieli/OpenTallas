`timescale 1ns/1ps
module tb_chip_v41x_kv_reqmux;
    localparam integer HAW = 30, TAGW = 16;
    reg [3:0] w_v=0, c_v=0, m_rdy=4'hf, m_wr_done=0, s_v=0;
    reg [4*HAW-1:0] w_addr=0, c_addr=0;
    reg [15:0] w_len=0, c_len=0, w_tag=0, c_tag=0, s_beat=0;
    reg [4*TAGW-1:0] wt=0, ct=0, s_tag=0;
    reg [3:0] w_we=0, c_we=0;
    reg [1023:0] w_wdata=0, c_wdata=0, s_data=0;
    reg [127:0] w_wstrb=0, c_wstrb=0;
    wire [3:0] w_rdy, c_rdy, w_done, c_done, w_sv, c_sv, m_v, m_we, s_rdy;
    wire [4*HAW-1:0] m_addr;
    wire [15:0] m_len, w_sbeat, c_sbeat;
    wire [4*TAGW-1:0] m_tag, w_stag, c_stag;
    wire [1023:0] m_wdata, w_sdata, c_sdata;
    wire [127:0] m_wstrb;
    ot_chip_v41x_kv_reqmux dut (
        .w_v(w_v), .w_rdy(w_rdy), .w_addr(w_addr), .w_len(w_len), .w_tag(wt),
        .w_we(w_we), .w_wdata(w_wdata), .w_wstrb(w_wstrb), .w_wr_done(w_done),
        .w_sv(w_sv), .w_srdy(4'hf), .w_stag(w_stag), .w_sbeat(w_sbeat), .w_sdata(w_sdata),
        .c_v(c_v), .c_rdy(c_rdy), .c_addr(c_addr), .c_len(c_len), .c_tag(ct),
        .c_we(c_we), .c_wdata(c_wdata), .c_wstrb(c_wstrb), .c_wr_done(c_done),
        .c_sv(c_sv), .c_srdy(4'hf), .c_stag(c_stag), .c_sbeat(c_sbeat), .c_sdata(c_sdata),
        .m_v(m_v), .m_rdy(m_rdy), .m_addr(m_addr), .m_len(m_len), .m_tag(m_tag),
        .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb), .m_wr_done(m_wr_done),
        .s_v(s_v), .s_rdy(s_rdy), .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));
    integer bad=0;
    initial begin
        w_v[2]=1; c_v[2]=1; w_addr[2*HAW +: HAW]=30'd100;
        c_addr[2*HAW +: HAW]=30'd200;
        wt[2*TAGW +: TAGW]=16'd7; ct[2*TAGW +: TAGW]=16'd5;
        w_len[2*4 +: 4]=1; c_len[2*4 +: 4]=1;
        w_we[2]=1; w_wdata[2*256 +: 256]=256'h1234;
        #1;
        if (!m_v[2] || m_addr[2*HAW +: HAW]!=100 || !m_we[2] ||
            !w_rdy[2] || c_rdy[2] || m_tag[2*TAGW +: TAGW]!=7) bad++;
        w_v[2]=0; c_we[2]=1; #1;
        if (m_addr[2*HAW +: HAW]!=200 || m_we[2] || !c_rdy[2] ||
            m_tag[2*TAGW +: TAGW]!=16'h8005) bad++;
        s_v[2]=1; s_tag[2*TAGW +: TAGW]=16'h8005; s_data[2*256 +: 256]=256'h55;
        #1;
        if (!c_sv[2] || w_sv[2] || c_stag[2*TAGW +: TAGW]!=5 ||
            c_sdata[2*256 +: 256]!=256'h55) bad++;
        s_tag[2*TAGW +: TAGW]=16'd7; m_wr_done[2]=1; #1;
        if (!w_sv[2] || c_sv[2] || w_stag[2*TAGW +: TAGW]!=7 ||
            !w_done[2] || c_done[2]) bad++;
        w_v[2]=1; c_v[3]=1; c_addr[3*HAW +: HAW]=30'd300; #1;
        if (!m_v[2] || !m_v[3] || m_addr[2*HAW +: HAW]!=100 ||
            m_addr[3*HAW +: HAW]!=300 || !w_rdy[2] || !c_rdy[3]) bad++;
        $display("KV_REQMUX bad=%0d", bad);
        if (!bad) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
