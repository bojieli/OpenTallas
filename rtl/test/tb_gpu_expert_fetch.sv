`timescale 1ns/1ps
// Routed-expert fetch bench (W19 B2): router values -> rtl/gpu/ot_gpu_router_topk.sv -> expert ids ->
// rtl/gpu/ot_gpu_expert_fetch.sv -> the timing-faithful HBM model rtl/hdc/kv/ot_hdc_hbm_model.sv (one stack:
// NPC pseudo-channels, 1.0 TB/s) -> the SMEM staging of the NSM SMs homed on that stack -> each SM's tensor core
// taking one line a cycle.  Core clock CLK_PS.  MODE 0: the ids come from the router selector fed with RVEC;
// MODE 1: NIDS ids from IDS (the MTP union) one a cycle.  The request starts at cycle START (after the model's
// first refresh interval, so the staggered all-bank refreshes are live).  BG_PPM > 0 adds a competing background
// stream of 1-KB sequential reads, issued whenever the fetch path leaves the request port free, from cycle 0.
// Every released line is checked against the backing-store pattern of the address the layout puts in that SM
// at that position of its stream.  Prints one FETCH line of cycle stamps (tools/rtl_w19_expert_fetch.py).
module tb_gpu_expert_fetch;
    parameter integer NSM = 8, NPC = 32, MODE = 0, NIDS = 6, START = 6000, BG_PPM = 0;
    parameter integer CLK_PS = 833, REQ_PS = 10000, RSP_PS = 10000, QD = 64, RQD = 32, REFI_PS = 3900000;
    parameter CFG = "cfg.hex", IDS = "ids.hex", RVEC = "rv.hex";
    localparam integer AW = 24, LENW = 6, TAGW = 16, BEATW = 5, MEMW = 1 << 20, IW = 9, P = 16, N = 384;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    // configuration: base, exp_lines, NSM offsets, NSM lines, NSM w1/w3 lines (of the first expert)
    reg [31:0] cfg [0:3 + 3 * NSM];
    reg [31:0] idmem [0:63];
    reg [31:0] rv [0:N-1];
    reg [NSM*16-1:0] cfg_off, cfg_lines;
    integer j, k, i;
    // ---- router selector ----
    reg r_valid = 0, r_last = 0;
    reg [P*32-1:0] r_vals;
    wire t_valid;
    wire [6*IW-1:0] t_ids;
    ot_gpu_router_topk #(.N(N), .P(P), .K(6), .IW(IW)) u_topk (.clk(clk), .rst_n(rst_n), .in_valid(r_valid),
        .in_vals(r_vals), .in_last(r_last), .out_valid(t_valid), .out_ids(t_ids));
    // ---- id stream into the fetch path ----
    reg [IW-1:0] ids [0:63];
    integer nids = 0, id_p = 0;
    reg e_valid = 0;
    wire e_ready;
    wire [IW-1:0] e_id = ids[id_p];
    // ---- fetch path and HBM ----
    wire f_req_v, m_rdy;
    wire [AW-1:0] f_addr; wire [LENW-1:0] f_len; wire [TAGW-1:0] f_tag;
    wire [NPC-1:0] rsp_v, f_rsp_rdy; wire [NPC*TAGW-1:0] rsp_tag; wire [NPC*BEATW-1:0] rsp_beat;
    wire [NPC*256-1:0] rsp_data; wire [NPC-1:0] pc_room;
    wire [NSM-1:0] s_valid; wire [NSM*1024-1:0] s_data; wire f_idle;
    ot_gpu_expert_fetch #(.NSM(NSM), .NPC(NPC), .AW(AW), .LENW(LENW), .TAGW(TAGW), .BEATW(BEATW), .IW(IW)) dut (
        .clk(clk), .rst_n(rst_n), .cfg_base(cfg[0][AW-3:0]), .cfg_exp_lines(cfg[1][15:0]), .cfg_off(cfg_off),
        .cfg_lines(cfg_lines), .e_valid(e_valid), .e_ready(e_ready), .e_id(e_id),
        .req_v(f_req_v), .req_rdy(m_rdy & f_req_v), .req_addr(f_addr), .req_len(f_len), .req_tag(f_tag),
        .rsp_v(rsp_v), .rsp_rdy(f_rsp_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data),
        .s_valid(s_valid), .s_ready({NSM{1'b1}}), .s_data(s_data), .idle(f_idle));
    // background stream: 1-KB sequential reads when the port is free
    reg bg_v; integer bg_credit = 0; reg [AW-1:0] bg_addr = 24'd700000;
    wire m_req_v = f_req_v | bg_v;
    wire [AW-1:0] m_addr = f_req_v ? f_addr : bg_addr;
    wire [LENW-1:0] m_len = f_req_v ? f_len : 6'd32;
    wire [TAGW-1:0] m_tag = f_req_v ? f_tag : 16'h8000;
    reg [NPC-1:0] bg_rdy;
    always @(*) for (k = 0; k < NPC; k = k + 1) bg_rdy[k] = rsp_v[k] && rsp_tag[k*TAGW + TAGW - 1];
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .MEM_WORDS(MEMW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
        .CLK_PS(CLK_PS), .REQ_PS(REQ_PS), .RSP_PS(RSP_PS), .PC_RDY(1), .QD(QD), .RQD(RQD),
        .REFI_PS(REFI_PS)) hbm (
        .clk(clk), .rst_n(rst_n), .req_v(m_req_v), .req_rdy(m_rdy), .pc_room(pc_room), .req_we(1'b0),
        .req_addr(m_addr), .req_len(m_len), .req_tag(m_tag), .req_wdata(256'd0),
        .rsp_v(rsp_v), .rsp_rdy(f_rsp_rdy | bg_rdy), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));
    function automatic [255:0] pat(input [31:0] s);
        pat = {8{s ^ 32'hA500_0000}};
    endfunction
    // ---- measurement ----
    integer cyc = 0, t0 = -1, t_topk = -1, t_desc = -1, t_req = -1, t_sect = -1, t_line = -1, t_idsdone = -1;
    integer cnt [0:NSM-1], t_w13 [0:NSM-1], t_exp1 [0:NSM-1], t_done [0:NSM-1];
    integer bad = 0, lines_total = 0, bg_issued = 0, e_l, e_e, fl;
    reg [31:0] line;
    always @(posedge clk) cyc <= cyc + 1;
    always @(*) bg_v = (BG_PPM > 0) && rst_n && !f_req_v && bg_credit >= 1000000;
    always @(posedge clk) if (rst_n) begin
        if (BG_PPM > 0) begin
            bg_credit = bg_credit + BG_PPM;
            if (bg_credit > 2000000) bg_credit = 2000000;
            if (bg_v && m_rdy) begin
                bg_credit = bg_credit - 1000000; bg_addr <= (bg_addr + 32 >= 24'd1040000) ? 24'd700000 : bg_addr + 32;
                bg_issued = bg_issued + 1;
            end
        end
        if (e_valid && e_ready && t_desc < 0) t_desc = cyc;
        if (f_req_v && m_rdy && t_req < 0) t_req = cyc;
        if ((|(rsp_v & f_rsp_rdy)) && t_sect < 0) t_sect = cyc;
        for (j = 0; j < NSM; j = j + 1) if (s_valid[j]) begin
            if (t_line < 0) t_line = cyc;
            // expected line: position cnt[j] of SM j's stream
            e_e = cnt[j] / cfg[2 + NSM + j]; e_l = cnt[j] % cfg[2 + NSM + j];
            line = cfg[0] + ids[e_e] * cfg[1] + cfg[2 + j] + e_l;
            for (k = 0; k < 4; k = k + 1)
                if (s_data[j*1024 + k*256 +: 256] !== pat(line * 4 + k)) bad = bad + 1;
            cnt[j] = cnt[j] + 1;
            lines_total = lines_total + 1;
            if (cnt[j] == cfg[2 + 2 * NSM + j]) t_w13[j] = cyc;
            if (cnt[j] == cfg[2 + NSM + j]) t_exp1[j] = cyc;
            if (cnt[j] == cfg[2 + NSM + j] * nids) t_done[j] = cyc;
        end
    end
    // id stream: one id a cycle once available
    always @(posedge clk) if (rst_n) begin
        if (t_valid && MODE == 0) begin
            t_topk = cyc;
            for (k = 0; k < 6; k = k + 1) ids[k] = t_ids[k*IW +: IW];
            nids = 6;
        end
        if (e_valid && e_ready) begin
            if (id_p == nids - 1) begin e_valid <= 1'b0; t_idsdone = cyc; end
            id_p <= id_p + 1;
        end else if (!e_valid && nids > 0 && id_p == 0 && t_idsdone < 0) e_valid <= 1'b1;
    end
    integer mx_w13, mx_e1, mx_done, mn_w13;
    initial begin
        $readmemh(CFG, cfg);
        $readmemh(IDS, idmem);
        $readmemh(RVEC, rv);
        for (j = 0; j < NSM; j = j + 1) begin
            cfg_off[j*16 +: 16] = cfg[2 + j]; cfg_lines[j*16 +: 16] = cfg[2 + NSM + j];
            cnt[j] = 0; t_w13[j] = -1; t_exp1[j] = -1; t_done[j] = -1;
        end
        for (i = 0; i < MEMW; i = i + 1) hbm.mem[i] = pat(i);
        repeat (3) @(posedge clk);
        rst_n = 1;
        while (cyc < START) @(posedge clk);
        t0 = cyc;
        if (MODE == 0) begin
            for (k = 0; k < N / P; k = k + 1) begin
                @(negedge clk);
                r_valid = 1; r_last = (k == N / P - 1);
                for (j = 0; j < P; j = j + 1) r_vals[32*j +: 32] = rv[k * P + j];
            end
            @(negedge clk); r_valid = 0; r_last = 0;
        end else begin
            @(negedge clk);
            for (k = 0; k < NIDS; k = k + 1) ids[k] = idmem[k][IW-1:0];
            nids = NIDS;
        end
        wait (nids > 0);
        fl = 1;
        while (fl) begin
            @(posedge clk);
            fl = 0;
            for (j = 0; j < NSM; j = j + 1) if (t_done[j] < 0 && cfg[2 + NSM + j] != 0) fl = 1;
        end
        mx_w13 = 0; mx_e1 = 0; mx_done = 0; mn_w13 = 1 << 30;
        for (j = 0; j < NSM; j = j + 1) if (cfg[2 + NSM + j] != 0) begin
            if (t_w13[j] > mx_w13) mx_w13 = t_w13[j];
            if (t_w13[j] < mn_w13) mn_w13 = t_w13[j];
            if (t_exp1[j] > mx_e1) mx_e1 = t_exp1[j];
            if (t_done[j] > mx_done) mx_done = t_done[j];
        end
        $write("FETCH t0=%0d topk=%0d desc=%0d req=%0d sect=%0d line=%0d w13_first_min=%0d w13_first_all=%0d exp1_all=%0d done=%0d lines=%0d bad=%0d nids=%0d bg_issued=%0d rd_lat_max_ps=%0d refreshes=%0d ids",
               t0, t_topk, t_desc, t_req, t_sect, t_line, mn_w13, mx_w13, mx_e1, mx_done, lines_total, bad, nids,
               bg_issued, hbm.st_rd_lat_max, hbm.st_ref[0]);
        for (k = 0; k < nids; k = k + 1) $write(" %0d", ids[k]);
        $write("\n");
        $finish;
    end
    initial begin #3000000; $display("FETCH TIMEOUT"); $finish; end
endmodule
