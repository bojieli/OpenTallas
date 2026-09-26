`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Host-interface simulation top, HBM comparator: ot_host_if (MODE 0,
// ENG_CTX 1) driving the decode core with its KV cache in HBM -- ot_hdc_core
// (KV_HBM = 1), the KV streaming engine ot_hdc_kv_stream, its window and tail
// SRAMs, and the timing-faithful HBM model ot_hdc_hbm_model (the structure of
// tb_hdc_core_hbm.sv).  Weights stay in the behavioural ROM image here.
//
// The tail SRAM holds the open position tile of the running user, so the core
// serves one user at a time: before a different user's first step the host
// interface raises eng_clr_req, and this top resets the core and the streamer
// and clears the tail SRAM before acknowledging.  The HBM rows a new user
// reads are the ones it has written itself (positions below its own).
// ---------------------------------------------------------------------------
module tb_host_hbm #(
    parameter integer G = 4,
    parameter integer NSLOT = 16,
    parameter integer LOG_HD = 4,
    parameter integer LOG_TW = 2,
    parameter integer LLG = 3,
    parameter integer V0_WORD = 512,
    parameter integer LWIN = 8,
    parameter integer NPC = 4,
    parameter integer BK = 16,
    parameter integer CLK_PS = 1000
) (
`include "tb_host_ports.svh"
);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, IL = 8, PLB = 8;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KV_WORDS = 1024;
    localparam integer VM_ELEMS = 4096, PROG_WORDS = 4096;
    localparam integer WIN = 1 << LWIN, TAW = LLG + LOG_HD, TDEPTH = 1 << TAW;
    localparam integer LG = $clog2(G), TAGW = 1 + LWIN + LG + 3, LBK = $clog2(BK);
    localparam integer SB = $clog2(NSLOT);

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]      crom [0:CROM_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]      vm   [0:VM_ELEMS-1];
    reg [W*16-1:0]  win  [0:G-1][0:WIN-1];
    reg [W*16-1:0]  tl   [0:1][0:TDEPTH-1];
    reg [NW-1:0]    pbuf [0:NSLOT*(1<<PLB)-1];

    wire pb_we, pb_re; wire [SB+PLB-1:0] pb_waddr, pb_raddr; wire [NW-1:0] pb_wdata; reg [NW-1:0] pb_q;
    wire start, done, fault;
    wire [NW-1:0] token, pos, next_token;
    wire [31:0] next_val, cycles;
    wire clr_req; reg clr_ack = 1'b0; reg core_rst_n = 1'b1;
    wire c_rst_n = rst_n && core_rst_n;
    reg [NW-1:0] lead;

    ot_host_if #(.NSLOT(NSLOT), .MODE(0), .ENG_CTX(1), .NW(NW), .PLB(PLB), .CTX_MAX(64), .AW(AW),
                 .KVW(KV_WORDS)) u_host (
`include "tb_host_conn.svh"
        .eng_start(start), .eng_token(token), .eng_pos(pos), .eng_slot(), .kv_base(),
        .eng_done(done), .eng_next_token(next_token), .eng_cycles(cycles), .eng_fault(fault),
        .eng_clr_req(clr_req), .eng_clr_ack(clr_ack),
        .arr_rst_n(), .cfg_users(), .cfg_prompt_len(), .cfg_gen_len(),
        .pr_re(1'b0), .pr_user(8'd0), .pr_pos({NW{1'b0}}),
        .tok_valid(1'b0), .tok_user(8'd0), .tok_pos({NW{1'b0}}), .tok_id({NW{1'b0}}), .users_done(8'd0),
        .arr_fault(1'b0));
    assign eng_busy = u_host.inflight;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire crom_re; wire [AW-1:0] crom_addr; reg [63:0] crom_q;
    wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; wire [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    reg [31:0] va_q, vb_q, vc_q;
    wire vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
    wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [31:0] vw_su_data, vw_rd_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire kvd_v, kvd_kindk, kv_ok;
    wire [AW-1:0] kvd_wbase, kvd_ts, kvd_ks, kvd_js;
    wire [2:0] kvd_jsh;
    wire [NW-1:0] kvd_tiles, kvd_k, kvd_nout, kvd_pos;

    ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .KV_HBM(1)) core (
        .clk(clk), .rst_n(c_rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok));

    wire [G-1:0] win_we; wire [G*LWIN-1:0] win_waddr; wire [G*W*16-1:0] win_wdata;
    wire win_re; wire [LWIN-1:0] win_raddr; reg [G*W*16-1:0] win_q;
    wire [1:0] tl_we, tl_re; wire [2*TAW-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask;
    wire [2*W*16-1:0] tl_wdata; reg [2*W*16-1:0] tl_q;
    wire hq_v, hq_rdy, hq_we; wire [AW-1:0] hq_addr; wire [LBK:0] hq_len; wire [TAGW-1:0] hq_tag;
    wire [W*16-1:0] hq_wdata;
    wire [NPC-1:0] hr_v, hr_rdy; wire [NPC*TAGW-1:0] hr_tag; wire [NPC*LBK-1:0] hr_beat;
    wire [NPC*W*16-1:0] hr_data;
    wire kvs_fault;
    ot_hdc_kv_stream #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .LWIN(LWIN), .NPC(NPC), .BK(BK),
                       .LOG_HD(LOG_HD), .LOG_TW(LOG_TW), .LLG(LLG), .V0_WORD(V0_WORD)) u_kvs (
        .clk(clk), .rst_n(c_rst_n), .tok_start(start), .tok_pos(pos), .cfg_lead(lead),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .win_we(win_we), .win_waddr(win_waddr), .win_wdata(win_wdata), .win_re(win_re), .win_raddr(win_raddr),
        .win_q(win_q),
        .tl_we(tl_we), .tl_waddr(tl_waddr), .tl_wmask(tl_wmask), .tl_wdata(tl_wdata), .tl_re(tl_re),
        .tl_raddr(tl_raddr), .tl_q(tl_q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_we(hq_we), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hq_wdata(hq_wdata),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(kvs_fault));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(W*16), .MEM_WORDS(KV_WORDS), .TAGW(TAGW), .LENW(LBK+1),
                       .BEATW(LBK), .CLK_PS(CLK_PS)) u_hbm (
        .clk(clk), .rst_n(c_rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .req_we(hq_we), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(hq_wdata),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));

    integer l, q, b, i;
    always @(posedge clk) begin
        if (pb_we) pbuf[pb_waddr] <= pb_wdata;
        if (pb_re) pb_q <= pbuf[pb_raddr];
        clr_ack <= 1'b0;
        if (clr_req && !clr_ack && core_rst_n) begin
            core_rst_n <= 1'b0;
            for (b = 0; b < 2; b = b + 1)
                for (i = 0; i < TDEPTH; i = i + 1) tl[b][i] = 0;
        end else if (!core_rst_n) begin
            core_rst_n <= 1'b1; clr_ack <= 1'b1;
        end
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
        if (crom_re) crom_q <= crom[crom_addr[11:0]];
        for (q = 0; q < G; q = q + 1) begin
            if (win_re) win_q[q*W*16 +: W*16] <= win[q][win_raddr];
            if (win_we[q]) win[q][win_waddr[q*LWIN +: LWIN]] <= win_wdata[q*W*16 +: W*16];
        end
        for (b = 0; b < 2; b = b + 1) begin
            if (tl_re[b]) tl_q[b*W*16 +: W*16] <= tl[b][tl_raddr[b*TAW +: TAW]];
            if (tl_we[b])
                for (l = 0; l < W; l = l + 1)
                    if (tl_wmask[b*W + l]) tl[b][tl_waddr[b*TAW +: TAW]][l*16 +: 16] <= tl_wdata[(b*W + l)*16 +: 16];
        end
        for (q = 0; q < G; q = q + 1)
            if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
        if (va_re) va_q <= vm[va_addr[11:0]];
        if (vb_re) vb_q <= vm[vb_addr[11:0]];
        if (vc_re) vc_q <= vm[vc_addr[11:0]];
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        if (vw_su_we) vm[vw_su_addr[11:0]] <= vw_su_data;
        if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
    end

    reg [8*512-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("LEAD=%d", lead)) lead = 512;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < KV_WORDS; i = i + 1) u_hbm.mem[i] = 0;
        for (b = 0; b < 2; b = b + 1)
            for (i = 0; i < TDEPTH; i = i + 1) tl[b][i] = 0;
    end
endmodule
