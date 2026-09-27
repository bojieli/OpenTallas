`timescale 1ns/1ps
// Token-level simulation top of the HBM comparator: the hardwired decode core
// with its WEIGHTS and its KV cache in HBM -- ot_hdc_core (KV_HBM = 1,
// W_HBM = 1) + ot_hdc_wstream + ot_hdc_kv_stream sharing one timing-faithful
// HBM model (ot_hdc_hbm_model) through ot_hdc_hbm_arb; behavioural window and
// tail SRAMs.  There is no weight ROM: the weights are loaded into the HBM
// model from tools/hdc_program.py --wchunk (hbm_w.hex, the stream in
// consumption order plus the embedding table).  The ROM image is loaded only
// to CHECK every word the streamer delivers.
//
// Default: one decode step at +POS on the golden-prefilled KV cache, then a
// bit-exact check of every logit, the whole vector memory and the whole KV
// cache (HBM plus tail) against the ISA-level model.
// +MULTI: start from an EMPTY cache, run every prompt token, then generate
// +NGEN tokens and compare them with the oracle's (+CHECKLAST: check the final
// step in full instead).  The weight stream runs on across tokens.
// +LEAD=n: the KV streamer's lead; +WLEAD=n, +WRATE=r: the weight streamer's
// lead (cycles) and guaranteed rate (words per cycle x 256);
// +NTOT, +EMBH, +EMBR: the weight image (hbm.args).
module tb_hdc_core_whbm #(
    parameter integer G = 4,
    parameter integer LOG_HD = 4,
    parameter integer LOG_TW = 2,
    parameter integer LLG = 3,
    parameter integer V0_WORD = 512,
    parameter integer LWIN = 8,
    parameter integer NPC = 4,
    parameter integer BK = 16,
    parameter integer LWINW = 11,
    parameter integer RQW = 4,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, IL = 8;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KV_WORDS = 1024;
    localparam integer VM_ELEMS = 4096, VOCAB = 4096, PROG_WORDS = 4096;
    localparam integer WIN = 1 << LWIN, TAW = LLG + LOG_HD, TDEPTH = 1 << TAW;
    localparam integer LG = $clog2(G), TAGK = 1 + LWIN + LG + 3, LBK = $clog2(BK);
    localparam integer WB = G * W * 16, WS = WB / 256, TAGWW = LWINW + 1;
    localparam integer TAGH = 1 + ((TAGK > TAGWW) ? TAGK : TAGWW);
    localparam integer WBASE = KV_WORDS;           // HBM sector of the weight region
    localparam integer HMEM = 131072;              // HBM model sectors (4 MiB)
    localparam integer WWIN = 1 << LWINW;

    reg [WB-1:0]    wref [0:WROM_WORDS-1];        // CHECK ONLY: the ROM image
    reg [63:0]      crom [0:CROM_WORDS-1];
    reg [W*32-1:0]  kv   [0:KV_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]      vm   [0:VM_ELEMS-1];
    reg [31:0]      e_vm [0:VM_ELEMS-1];
    reg [31:0]      e_kv [0:KV_WORDS*W-1];
    reg [31:0]      e_lg [0:VOCAB-1];
    reg [31:0]      lg   [0:VOCAB-1];
    reg [W*16-1:0]  win  [0:G-1][0:WIN-1];
    reg [W*16-1:0]  tl   [0:1][0:TDEPTH-1];
    localparam integer WBF = 2, WNB = WBF * WS;
    reg [255:0]     wwin [0:WNB-1][0:WWIN/WBF-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    reg [NW-1:0] lead, wlead;
    reg [15:0]   wrate;
    reg [31:0]   ntot, embh, embr;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] cycles;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re, wrom_su; wire [AW-1:0] wrom_addr; wire [WB-1:0] wrom_q;
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
    wire wd_v, w_ok, emb_ok;
    wire [AW-1:0] wd_wbase;
    wire [NW-1:0] wd_tiles, wd_k;

    ot_hdc_core_whbm #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .KV_HBM(1), .W_HBM(1)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .cycles(cycles), .fault(fault),
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
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok),
        .wrom_su(wrom_su), .wd_v(wd_v), .wd_wbase(wd_wbase), .wd_tiles(wd_tiles), .wd_k(wd_k),
        .w_ok(w_ok), .emb_ok(emb_ok));

    // ---- KV streaming engine, window and tail SRAMs ----------------------------------------
    wire [G-1:0] win_we; wire [G*LWIN-1:0] win_waddr; wire [G*W*16-1:0] win_wdata;
    wire win_re; wire [LWIN-1:0] win_raddr; reg [G*W*16-1:0] win_q;
    wire [1:0] tl_we, tl_re; wire [2*TAW-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask;
    wire [2*W*16-1:0] tl_wdata; reg [2*W*16-1:0] tl_q;
    wire kq_v, kq_rdy, kq_we; wire [AW-1:0] kq_addr; wire [LBK:0] kq_len; wire [TAGK-1:0] kq_tag;
    wire [W*16-1:0] kq_wdata;
    wire [NPC-1:0] kr_v, kr_rdy; wire [NPC*TAGK-1:0] kr_tag;
    wire kvs_fault;
    // ---- HBM model and the shared port ---------------------------------------------------------
    wire hq_v, hq_rdy, hq_we; wire [AW-1:0] hq_addr; wire [LBK:0] hq_len; wire [TAGH-1:0] hq_tag;
    wire [255:0] hq_wdata;
    wire [NPC-1:0] hr_v, hr_rdy; wire [NPC*TAGH-1:0] hr_tag; wire [NPC*LBK-1:0] hr_beat;
    wire [NPC*256-1:0] hr_data;
    wire [NPC-1:0] pc_room;
    ot_hdc_kv_stream #(.W(W), .G(G), .IL(IL), .AW(AW), .NW(NW), .LWIN(LWIN), .NPC(NPC), .BK(BK),
                       .LOG_HD(LOG_HD), .LOG_TW(LOG_TW), .LLG(LLG), .V0_WORD(V0_WORD)) u_kvs (
        .clk(clk), .rst_n(rst_n), .tok_start(start), .tok_pos(pos), .cfg_lead(lead),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(kvd_ts), .kvd_ks(kvd_ks), .kvd_js(kvd_js),
        .kvd_jsh(kvd_jsh), .kvd_tiles(kvd_tiles), .kvd_k(kvd_k), .kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .win_we(win_we), .win_waddr(win_waddr), .win_wdata(win_wdata), .win_re(win_re), .win_raddr(win_raddr),
        .win_q(win_q),
        .tl_we(tl_we), .tl_waddr(tl_waddr), .tl_wmask(tl_wmask), .tl_wdata(tl_wdata), .tl_re(tl_re),
        .tl_raddr(tl_raddr), .tl_q(tl_q),
        .hq_v(kq_v), .hq_rdy(kq_rdy), .hq_we(kq_we), .hq_addr(kq_addr), .hq_len(kq_len), .hq_tag(kq_tag),
        .hq_wdata(kq_wdata),
        .hr_v(kr_v), .hr_rdy(kr_rdy), .hr_tag(kr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(kvs_fault));

    // ---- weight streaming engine and its window --------------------------------------------------
    wire [WNB-1:0] ww_we; wire [WNB*LWINW-1:0] ww_waddr; wire [WBF*WB-1:0] ww_wdata;
    wire [WNB-1:0] ww_re; wire [LWINW-1:0] ww_raddr; reg [WBF*WB-1:0] ww_q;
    wire wq_v, wq_rdy; wire [AW-1:0] wq_addr; wire [LBK:0] wq_len; wire [TAGWW-1:0] wq_tag;
    wire [NPC-1:0] wr_v, wr_rdy; wire [NPC*TAGWW-1:0] wr_tag;
    wire ws_fault; wire [3:0] ws_why; wire [31:0] ws_fetched, ws_consumed;
    ot_hdc_wstream #(.WB(WB), .SB(256), .AW(AW), .HAW(AW), .NW(NW), .IL(IL), .LWIN(LWINW), .NPC(NPC),
                     .RQW(RQW), .LENW(LBK+1), .BEATW(LBK), .EMBW(128 / (G*W))) u_ws (
        .clk(clk), .rst_n(rst_n),
        .cfg_base(WBASE[AW-1:0]), .cfg_ntot(ntot), .cfg_emb_base(WBASE + embh * WS), .cfg_emb_rom(embr[AW-1:0]),
        .cfg_lead(wlead), .cfg_rate(wrate),
        .tok_start(start), .token(token),
        .wd_v(wd_v), .wd_wbase(wd_wbase), .wd_tiles(wd_tiles), .wd_k(wd_k), .w_ok(w_ok), .emb_ok(emb_ok),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_su(wrom_su), .wrom_q(wrom_q),
        .win_we(ww_we), .win_waddr(ww_waddr), .win_wdata(ww_wdata), .win_re(ww_re), .win_raddr(ww_raddr),
        .win_q(ww_q),
        .hq_v(wq_v), .hq_rdy(wq_rdy), .hq_addr(wq_addr), .hq_len(wq_len), .hq_tag(wq_tag), .hq_room(pc_room),
        .hr_v(wr_v), .hr_rdy(wr_rdy), .hr_tag(wr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(ws_fault), .fault_why(ws_why), .st_fetched(ws_fetched), .st_consumed(ws_consumed));

    ot_hdc_hbm_arb #(.NPC(NPC), .AW(AW), .DW(256), .LENW(LBK+1), .BEATW(LBK), .TAGA(TAGK), .TAGB(TAGWW),
                     .TAGW(TAGH)) u_arb (
        .a_v(kq_v), .a_rdy(kq_rdy), .a_we(kq_we), .a_addr(kq_addr), .a_len(kq_len), .a_tag(kq_tag),
        .a_wdata(kq_wdata), .a_hr_v(kr_v), .a_hr_rdy(kr_rdy),
        .b_v(wq_v), .b_rdy(wq_rdy), .b_addr(wq_addr), .b_len(wq_len), .b_tag(wq_tag),
        .b_hr_v(wr_v), .b_hr_rdy(wr_rdy),
        .a_hr_tag(kr_tag), .b_hr_tag(wr_tag),
        .req_v(hq_v), .req_rdy(hq_rdy), .req_we(hq_we), .req_addr(hq_addr), .req_len(hq_len), .req_tag(hq_tag),
        .req_wdata(hq_wdata), .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag));

    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(256), .MEM_WORDS(HMEM), .TAGW(TAGH), .LENW(LBK+1),
                       .BEATW(LBK), .CLK_PS(CLK_PS), .PC_RDY(1), .PC_ROOM(2 * WS)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .pc_room(pc_room), .req_we(hq_we), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(hq_wdata),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));

    // synchronous-read memories
    integer l, q, b;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (crom_re) crom_q <= crom[crom_addr[11:0]];
        for (q = 0; q < G; q = q + 1) begin
            if (win_re) win_q[q*W*16 +: W*16] <= win[q][win_raddr];
            if (win_we[q]) win[q][win_waddr[q*LWIN +: LWIN]] <= win_wdata[q*W*16 +: W*16];
        end
        for (q = 0; q < WNB; q = q + 1) begin
            if (ww_re[q]) ww_q[q*256 +: 256] <= wwin[q][ww_raddr / WBF];
            if (ww_we[q]) wwin[q][ww_waddr[q*LWINW +: LWINW] / WBF] <= ww_wdata[q*256 +: 256];
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
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l]) lg[{me_oaddr[q*AW +: 8], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
    end

    function automatic [W*16-1:0] pack16(input [W*32-1:0] w32);
        integer i;
        for (i = 0; i < W; i = i + 1) pack16[i*16 +: 16] = w32[i*32 + 16 +: 16];
    endfunction
    function automatic [W*16-1:0] logical_kv(input integer a, input integer to);
        integer T;
        begin
            T = (a >> LOG_HD) & ((1 << LOG_TW) - 1);
            if (a < V0_WORD && (T == to || T + 1 == to))
                logical_kv = tl[T & 1][((a >> (LOG_HD + LOG_TW)) << LOG_HD) | (a & ((1 << LOG_HD) - 1))];
            else
                logical_kv = u_hbm.mem[a][W*16-1:0];
        end
    endfunction

    reg [8*512-1:0] dir;
    integer cyc = 0, i, bad_lg, bad_vm, bad_kv, T;
    reg trace = 1'b0, multi = 1'b0, checklast = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0;
    integer me_busy = 0, su_busy = 0, both_idle = 0;
    integer kv_stall = 0, kv_ops = 0, kvq_bad = 0, kvq_zero = 0;
    integer w_stall = 0, emb_stall = 0, w_ops = 0, wq_bad = 0, w_words = 0;
    //: cycles the sequencer waits only for the weight window (or only for the embedding row)
    wire seq_base_ok = (dut.d_drain ? dut.drained : (!dut.d_chase || dut.chased)) && dut.unit_ready && dut.kv_gate;
    always @(posedge clk) if (dut.st != 0) begin
        if (dut.u_me.active) me_busy <= me_busy + 1;
        if (dut.u_su.active) su_busy <= su_busy + 1;
        if (!dut.u_me.active && !dut.u_su.active) both_idle <= both_idle + 1;
        if (dut.st == 6 && dut.d_unit == 1 && seq_base_ok && !dut.w_gate) w_stall <= w_stall + 1;
        if (dut.st == 6 && dut.d_unit == 2 && seq_base_ok && !dut.w_gate) emb_stall <= emb_stall + 1;
        if (dut.st == 6 && dut.d_unit == 1 && (dut.d_barrier ? dut.drained : (!dut.d_chase || dut.chased)) &&
            dut.unit_ready && !dut.kv_gate) kv_stall <= kv_stall + 1;
    end
    // delivered KV words against the cache, delivered weight words against the ROM image
    reg chk_v; reg [G*AW-1:0] chk_addr; reg [W*16-1:0] lw; reg [W*32-1:0] lw32;
    reg wchk_v; reg [AW-1:0] wchk_addr;
    always @(posedge clk) begin
        chk_v <= kv_re; chk_addr <= kv_raddr;
        wchk_v <= wrom_re; wchk_addr <= wrom_addr;
        if (chk_v)
            for (q = 0; q < G; q = q + 1) begin
                lw = logical_kv(chk_addr[q*AW +: AW] % KV_WORDS, pos >> 4);
                for (l = 0; l < W; l = l + 1) lw32[l*32 +: 32] = {lw[l*16 +: 16], 16'h0};
                if (kv_q[q*W*32 +: W*32] != lw32) begin
                    if (kv_q[q*W*32 +: W*32] == 0) kvq_zero = kvq_zero + 1;
                    else kvq_bad = kvq_bad + 1;
                end
            end
        if (wchk_v) begin
            w_words <= w_words + 1;
            if (wrom_q !== wref[wchk_addr[16:0]]) begin
                if (wq_bad < 3) $display("WBAD cyc=%0d addr=%0d", cycles, wchk_addr);
                wq_bad = wq_bad + 1;
            end
        end
        if (kvd_v) kv_ops <= kv_ops + 1;
        if (wd_v) w_ops <= w_ops + 1;
        if (trace && dut.me_go && !dut.me_wsrc)
            $display("WGO cyc=%0d pc=%0d tiles=%0d k=%0d words=%0d cp=%0d cons=%0d fp=%0d", cycles, dut.pc,
                     dut.me_tiles, dut.me_k, dut.me_tiles * dut.me_k * IL, u_ws.cp, u_ws.cons, u_ws.fp);
    end

    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        if (!$value$plusargs("LEAD=%d", lead)) lead = 512;
        if (!$value$plusargs("WLEAD=%d", wlead)) wlead = 512;
        if (!$value$plusargs("WRATE=%d", wrate)) wrate = 0;
        if (!$value$plusargs("NTOT=%d", ntot)) ntot = 0;
        if (!$value$plusargs("EMBH=%d", embh)) embh = 0;
        if (!$value$plusargs("EMBR=%d", embr)) embr = 0;
        $readmemh({dir, "/wrom.hex"}, wref);
        $readmemh({dir, "/crom.hex"}, crom);
        if ($test$plusargs("MULTI")) multi = 1'b1;
        if ($test$plusargs("CHECKLAST")) checklast = 1'b1;
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = 0;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 0;
        if (multi) begin
            $readmemh({dir, "/prompt.hex"}, prompt);
            $readmemh({dir, "/generated.hex"}, gold_gen);
            for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
        end else
            $readmemh({dir, "/kv.hex"}, kv);
        // HBM: the KV image at sector 0, the weights (stream + embedding table) at WBASE
        for (i = 0; i < HMEM; i = i + 1) u_hbm.mem[i] = 256'd0;
        for (i = 0; i < KV_WORDS; i = i + 1) u_hbm.mem[i] = {{(256-W*16){1'b0}}, pack16(kv[i])};
        $readmemh({dir, "/hbm_w.hex"}, u_hbm.mem, WBASE);
        for (b = 0; b < 2; b = b + 1)
            for (i = 0; i < TDEPTH; i = i + 1) tl[b][i] = 0;
        T = multi ? 0 : (pos >> 4);
        for (i = T - 1; i <= T; i = i + 1)
            if (i >= 0)
                for (b = 0; b < TDEPTH; b = b + 1)
                    tl[i & 1][b] = pack16(kv[((b >> LOG_HD) << (LOG_HD + LOG_TW)) | (i << LOG_HD) | (b & ((1 << LOG_HD) - 1))]);
        $readmemh({dir, "/prog.hex"}, prog);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    task automatic hbm_stats;
        integer p, sum_rd, sum_wr, sum_act, sum_hit, sum_conf, sum_ref;
        begin
            sum_rd = 0; sum_wr = 0; sum_act = 0; sum_hit = 0; sum_conf = 0; sum_ref = 0;
            for (p = 0; p < NPC; p = p + 1) begin
                sum_rd = sum_rd + u_hbm.st_rd[p]; sum_wr = sum_wr + u_hbm.st_wr[p];
                sum_act = sum_act + u_hbm.st_act[p]; sum_hit = sum_hit + u_hbm.st_hit[p];
                sum_conf = sum_conf + u_hbm.st_conf[p]; sum_ref = sum_ref + u_hbm.st_ref[p];
            end
            $display("WSTREAM w_stall_cycles=%0d emb_stall_cycles=%0d w_ops=%0d w_words=%0d wq_bad=%0d ws_fault=%0d ws_why=%0d fetched=%0d consumed=%0d kv_stall_cycles=%0d kv_ops=%0d kvs_fault=%0d kvq_bad=%0d hbm_reads=%0d hbm_writes=%0d acts=%0d row_hits=%0d row_conflicts=%0d refreshes=%0d rd_lat_avg_ps=%0d rd_lat_max_ps=%0d req_backpressure_cycles=%0d total_cycles=%0d",
                     w_stall, emb_stall, w_ops, w_words, wq_bad, ws_fault, ws_why, ws_fetched, ws_consumed,
                     kv_stall, kv_ops, kvs_fault, kvq_bad, sum_rd, sum_wr, sum_act, sum_hit, sum_conf, sum_ref,
                     (sum_rd > 0) ? u_hbm.st_rd_lat_sum / sum_rd : 0, u_hbm.st_rd_lat_max, u_hbm.st_bp_cycles,
                     multi ? total_cycles : cycles);
        end
    endtask

    task automatic check_and_finish(input [NW-1:0] exp_tok);
        reg [W*16-1:0] w16;
        begin
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                bad_lg = bad_lg + 1;
            end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm[i]) begin
                if (bad_vm < 5) $display("vm %0d rtl %h expect %h", i, vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS; i = i + 1) begin
                w16 = logical_kv(i, pos >> 4);
                for (l = 0; l < W; l = l + 1)
                    if ({w16[l*16 +: 16], 16'h0} !== e_kv[i*W + l]) begin
                        if (bad_kv < 5) $display("kv %0d rtl %h expect %h", i*W + l, {w16[l*16 +: 16], 16'h0}, e_kv[i*W + l]);
                        bad_kv = bad_kv + 1;
                    end
            end
            $display("HDC token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv);
            $display("UTIL me_issue_cycles=%0d su_issue_cycles=%0d both_idle_cycles=%0d", me_busy, su_busy, both_idle);
            hbm_stats();
            if (next_token == exp_tok && !fault && !kvs_fault && !ws_fault && kvq_bad == 0 && wq_bad == 0 &&
                bad_lg == 0 && bad_vm == 0 && bad_kv == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
    endtask

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        start <= (cyc == 10);
        if (cyc == 9 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && cyc > 12 && done && !start) begin
            total_cycles = total_cycles + cycles;
            if (step >= n_prompt - 1 && !checklast) begin
                $display("STEP pos=%0d in=%0d out=%0d gold=%0d cycles=%0d fault=%0d", pos, token, next_token,
                         gold_gen[step - (n_prompt - 1)], cycles, fault);
                if (next_token != gold_gen[step - (n_prompt - 1)] || fault || kvs_fault || ws_fault) gen_bad = gen_bad + 1;
            end
            if (step + 1 == n_prompt + n_gen - 1) begin
                if (checklast) check_and_finish(expect_tok);
                else begin
                    $display("HDC_MULTI steps=%0d generated=%0d mismatches=%0d total_cycles=%0d", step + 1,
                             n_gen, gen_bad, total_cycles);
                    hbm_stats();
                    if (gen_bad == 0 && !kvs_fault && !ws_fault && kvq_bad == 0 && wq_bad == 0) $display("PASS");
                    else $display("FAIL");
                    $finish;
                end
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
        end
        if (!multi && cyc > 12 && done) check_and_finish(expect_tok);
        //: a streamer fault ends the run: its state no longer follows the engine
        if (kvs_fault || ws_fault) begin
            $display("STREAM_FAULT cyc=%0d pc=%0d kv=%0d w=%0d why=%0d", cycles, dut.pc, kvs_fault, ws_fault, ws_why);
            check_and_finish(expect_tok);
        end
        if (trace && (dut.me_go || dut.su_go))
            $display("ISSUE cyc=%0d pc=%0d unit=%0d barrier=%0d", cycles, dut.pc, dut.d_unit, dut.d_barrier);
        if (cyc > 40000000) begin
            $display("TIMEOUT pc=%0d st=%0d me_idle=%0d su_idle=%0d kv_ok=%0d w_ok=%0d emb_ok=%0d", dut.pc, dut.st,
                     dut.me_idle, dut.su_idle, kv_ok, w_ok, emb_ok);
            hbm_stats();
            $finish;
        end
    end
endmodule
