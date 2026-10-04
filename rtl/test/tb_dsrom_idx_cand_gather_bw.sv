`timescale 1ns/1ps
// DS ROM re-index candidate-key read on one HBM3E stack (HBM path audit 2026-10-04).
// +list=<hex file: per line {addr[23:0], len[3:0], off[15:0]}> +n_req +n_sect +t0 (start cycle).
// HBM: ot_hdc_v41x_idx_hbm, 32 PCs, MEM_MODE 1 (data = pat(sector)), W11 gate values, 1.2 GHz clock.
// Every landed sector is compared with pat(address); prints one BW line and a verdict.
module tb_dsrom_idx_cand_gather_bw;
    parameter integer CLK_PS = 833;
    localparam integer NPC = 32, AW = 24, TAGW = 16, LENW = 5, BEATW = 4, NMAX = 1024, SMAX = 4096;
    reg clk = 0, rst_n = 0;
    always #(CLK_PS / 2000.0) clk = ~clk;
    longint cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer T0 = 5000, NREQ = 0, NSECT = 0; reg [1023:0] fn;
    reg [43:0] lst [0:NMAX-1];
    function automatic [255:0] pat(input [AW-1:0] s);
        for (integer w = 0; w < 8; w = w + 1) pat[32*w +: 32] = (s * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995;
    endfunction
    wire [NPC-1:0] h_req_v, h_req_rdy, h_req_we, h_wr_done, h_rsp_v, h_rsp_rdy;
    wire [NPC*AW-1:0] h_req_addr; wire [NPC*LENW-1:0] h_req_len; wire [NPC*TAGW-1:0] h_req_tag, h_rsp_tag;
    wire [NPC*256-1:0] h_req_wdata, h_rsp_data; wire [NPC*32-1:0] h_req_wstrb; wire [NPC*BEATW-1:0] h_rsp_beat;
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .QD(64), .RQD(32), .RW(16),
        .MAXSKIP(16), .REFPB(3), .CLK_PS(CLK_PS), .MEM_MODE(1)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr),
        .req_len(h_req_len), .req_tag(h_req_tag), .req_we(h_req_we), .req_wdata(h_req_wdata),
        .req_wstrb(h_req_wstrb), .wr_done(h_wr_done), .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy),
        .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data));
    reg ld_v = 0, start = 0; reg [9:0] ld_idx = 0; reg [AW-1:0] ld_addr = 0; reg [2:0] ld_len = 0; reg [11:0] ld_off = 0;
    reg [11:0] rd_sect = 0; wire [255:0] rd_data; wire busy, done, fault;
    ot_dsrom_hbm_list_gather_la #(.ENABLE(1), .NPC(NPC), .AW(AW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
        .NMAX(NMAX), .SMAX(SMAX)) u_dut (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_idx(ld_idx), .ld_addr(ld_addr), .ld_len(ld_len), .ld_off(ld_off),
        .start(start), .n_req(11'(NREQ)), .n_sect(13'(NSECT)), .busy(busy), .done(done), .fault(fault),
        .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr), .req_len(h_req_len), .req_tag(h_req_tag),
        .req_we(h_req_we), .req_wdata(h_req_wdata), .req_wstrb(h_req_wstrb), .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy),
        .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data), .rd_sect(rd_sect), .rd_data(rd_data));
    longint t_start, t_first = -1, t_done; integer beats = 0, bad = 0;
    always @(posedge clk) if (rst_n && t_first < 0 && |h_rsp_v && busy) t_first = cyc;
    always @(posedge clk) for (integer p = 0; p < NPC; p = p + 1) if (h_rsp_v[p]) beats = beats + 1;
    initial begin
        if (!$value$plusargs("list=%s", fn)) $fatal(1, "+list required");
        void'($value$plusargs("n_req=%d", NREQ)); void'($value$plusargs("n_sect=%d", NSECT));
        void'($value$plusargs("t0=%d", T0));
        $readmemh(fn, lst);
        repeat (10) @(posedge clk); rst_n = 1;
        for (integer i = 0; i < NREQ; i = i + 1) begin
            @(negedge clk); ld_v = 1; ld_idx = 10'(i); ld_addr = lst[i][43:20]; ld_len = lst[i][18:16]; ld_off = lst[i][11:0];
        end
        @(negedge clk); ld_v = 0;
        while (cyc < T0) @(posedge clk);
        @(negedge clk); start = 1; t_start = cyc + 1;
        @(negedge clk); start = 0;
        @(posedge clk); while (!done && !fault && cyc < T0 + 400000) @(posedge clk);
        t_done = cyc;
        for (integer i = 0; i < NREQ; i = i + 1)
            for (integer b = 0; b < int'(lst[i][18:16]); b = b + 1) begin
                @(negedge clk); rd_sect = 12'(int'(lst[i][11:0]) + b); #0.001;
                if (rd_data !== pat(AW'(lst[i][43:20] + b))) begin
                    bad = bad + 1; if (bad < 4) $display("SECTOR MISMATCH req=%0d beat=%0d", i, b);
                end
            end
        begin
            real ns, tbps;
            ns = real'(t_done - t_start) * CLK_PS / 1000.0;
            tbps = real'(NSECT) * 32.0 / ns / 1000.0;
            $display("BW clk_ps=%0d t0=%0d n_req=%0d cycles=%0d first_rsp_cycles=%0d sectors=%0d beats=%0d bytes=%0d ns=%0.1f tbps=%0.4f frac=%0.4f rd_lat_mean_ns=%0.1f rd_lat_max_ns=%0.1f bad=%0d fault=%0d",
                CLK_PS, T0, NREQ, t_done - t_start, t_first - t_start, NSECT, beats, NSECT * 32, ns, tbps,
                tbps / (32.0 * 32.0 / 1.024 / 1000.0),
                (beats > 0) ? real'(u_hbm.st_rd_lat_sum) / beats / 1000.0 : 0.0, real'(u_hbm.st_rd_lat_max) / 1000.0,
                bad, fault);
            $display("VERDICT %s", (bad == 0 && !fault && done && beats == NSECT) ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
