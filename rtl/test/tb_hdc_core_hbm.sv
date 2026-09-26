`timescale 1ns/1ps
// Token-level simulation top of the hardwired decode core with its KV cache in
// HBM: ot_hdc_core (KV_HBM = 1) + ot_hdc_kv_stream + the timing-faithful HBM
// model (ot_hdc_hbm_model), behavioural window and tail SRAMs.  Same images
// and checks as tb_hdc_core.sv (tools/hdc_program.py):
//
// Default: one decode step at +POS on the golden-prefilled KV cache (loaded
// into HBM; the open position tile and the one before it into the tail SRAM),
// then a bit-exact check of every logit, the whole vector memory and the whole
// KV cache (HBM plus tail) against the ISA-level model.
// +MULTI: start from an EMPTY cache, run every prompt token, then generate
// +NGEN tokens and compare them with the oracle's; +CHECKLAST instead checks the
// final step like the default mode (a long prompt from an empty cache: the
// core writes, flushes and re-reads every K and V row through HBM).
// +LEAD=n: the streamer's fetch lead (cycles).
//
// +define+OT_HDC_KV_MACROS: the window and tail SRAMs are the ASAP7 compiled
// macros behind rtl/hdc/kv/ot_hdc_kv_bufs.sv (MBIST collars, one shared
// controller, spare-row/column repair).  The core, the streamer and the HBM
// model are held in reset while the optional memory self-test (+BIST) runs and
// the golden tail tiles are written through the buffers' test port, so every
// cycle count is measured from the same reset release as without macros.  The
// tail array below is then a write-side shadow used only by the checks; every
// word the core reads comes out of the macros.
module tb_hdc_core_hbm #(
    parameter integer G = 4,
    parameter integer LOG_HD = 4,
    parameter integer LOG_TW = 2,
    parameter integer LLG = 3,
    parameter integer V0_WORD = 512,
    parameter integer LWIN = 8,
    parameter integer NPC = 4,
    parameter integer BK = 16,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12, IL = 8;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KV_WORDS = 1024;
    localparam integer VM_ELEMS = 4096, VOCAB = 4096, PROG_WORDS = 4096;
    localparam integer WIN = 1 << LWIN, TAW = LLG + LOG_HD, TDEPTH = 1 << TAW;
    localparam integer LG = $clog2(G), TAGW = 1 + LWIN + LG + 3, LBK = $clog2(BK);

    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]      crom [0:CROM_WORDS-1];
    reg [W*32-1:0]  kv   [0:KV_WORDS-1];          // image only (loaded into HBM / tail)
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]      vm   [0:VM_ELEMS-1];
    reg [31:0]      e_vm [0:VM_ELEMS-1];
    reg [31:0]      e_kv [0:KV_WORDS*W-1];
    reg [31:0]      e_lg [0:VOCAB-1];
    reg [31:0]      lg   [0:VOCAB-1];
    reg [W*16-1:0]  win  [0:G-1][0:WIN-1];
    reg [W*16-1:0]  tl   [0:1][0:TDEPTH-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    reg [NW-1:0] lead;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] cycles;

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

    ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .KV_HBM(1)) dut (
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
        .kvd_kindk(kvd_kindk), .kvd_pos(kvd_pos), .kv_ok(kv_ok));

    // KV streaming engine, window and tail SRAMs, HBM
    wire [G-1:0] win_we; wire [G*LWIN-1:0] win_waddr; wire [G*W*16-1:0] win_wdata;
`ifndef OT_HDC_KV_MACROS
    wire win_re; wire [LWIN-1:0] win_raddr; reg [G*W*16-1:0] win_q;
    wire [1:0] tl_we, tl_re; wire [2*TAW-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask;
    wire [2*W*16-1:0] tl_wdata; reg [2*W*16-1:0] tl_q;
`else
    wire win_re; wire [LWIN-1:0] win_raddr; wire [G*W*16-1:0] win_q;
    wire [1:0] tl_we, tl_re; wire [2*TAW-1:0] tl_waddr, tl_raddr; wire [2*W-1:0] tl_wmask;
    wire [2*W*16-1:0] tl_wdata; wire [2*W*16-1:0] tl_q;
    localparam integer N_M = G + 2;
    reg bist_rst_n = 1'b0, bist_en = 1'b0, bist_start = 1'b0, bist_started = 1'b0;
    wire bist_busy, bist_done, bist_pass, rep_scan_out;
    wire [2*N_M-1:0] bist_sram_status;
    reg tst_tl_en = 1'b0;
    reg [1:0] tst_tl_we = 2'b00;
    reg [TAW-1:0] tst_tl_addr = 0;
    reg [2*W*16-1:0] tst_tl_wdata = 0;
    integer pre_i = 0;
    reg pre_busy = 1'b0;
    ot_hdc_kv_bufs #(.G(G), .W(W), .LWIN(LWIN), .TAW(TAW)) u_bufs (
        .clk(clk), .rst_n(bist_rst_n),
        .win_we(win_we), .win_waddr(win_waddr), .win_wdata(win_wdata), .win_re(win_re),
        .win_raddr(win_raddr), .win_q(win_q),
        .tl_we(tl_we), .tl_waddr(tl_waddr), .tl_wmask(tl_wmask), .tl_wdata(tl_wdata), .tl_re(tl_re),
        .tl_raddr(tl_raddr), .tl_q(tl_q),
        .tst_tl_en(tst_tl_en), .tst_tl_we(tst_tl_we), .tst_tl_addr(tst_tl_addr), .tst_tl_wdata(tst_tl_wdata),
        .bist_start(bist_start), .bist_busy(bist_busy), .bist_done(bist_done), .bist_pass(bist_pass),
        .bist_sram_status(bist_sram_status), .rep_scan_en(1'b0), .rep_scan_in(1'b0),
        .rep_scan_out(rep_scan_out));
`endif
    wire hq_v, hq_rdy, hq_we; wire [AW-1:0] hq_addr; wire [LBK:0] hq_len; wire [TAGW-1:0] hq_tag;
    wire [W*16-1:0] hq_wdata;
    wire [NPC-1:0] hr_v, hr_rdy; wire [NPC*TAGW-1:0] hr_tag; wire [NPC*LBK-1:0] hr_beat;
    wire [NPC*W*16-1:0] hr_data;
    wire kvs_fault;
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
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_we(hq_we), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hq_wdata(hq_wdata),
        .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(kvs_fault));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .DW(W*16), .MEM_WORDS(KV_WORDS), .TAGW(TAGW), .LENW(LBK+1),
                       .BEATW(LBK), .CLK_PS(CLK_PS)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy), .req_we(hq_we), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(hq_wdata),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag), .rsp_beat(hr_beat), .rsp_data(hr_data));

    // synchronous-read memories
    integer l, q, b;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
        if (crom_re) crom_q <= crom[crom_addr[11:0]];
`ifndef OT_HDC_KV_MACROS
        for (q = 0; q < G; q = q + 1) begin
            if (win_re) win_q[q*W*16 +: W*16] <= win[q][win_raddr];
            if (win_we[q]) win[q][win_waddr[q*LWIN +: LWIN]] <= win_wdata[q*W*16 +: W*16];
        end
`endif
        for (b = 0; b < 2; b = b + 1) begin
`ifndef OT_HDC_KV_MACROS
            if (tl_re[b]) tl_q[b*W*16 +: W*16] <= tl[b][tl_raddr[b*TAW +: TAW]];
`endif
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

    // The KV cache as the core sees it: HBM, except the open position tile and
    // the one before it, which live in the tail SRAM.
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
                logical_kv = u_hbm.mem[a];
        end
    endfunction

    reg [8*512-1:0] dir;
    integer cyc = 0, lc = 0, i, bad_lg, bad_vm, bad_kv, lgi, T;
    reg go = 1'b1;
    reg trace = 1'b0, multi = 1'b0, checklast = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0;
    integer me_busy = 0, su_busy = 0, both_idle = 0;
    // KV streaming statistics
    integer kv_stall = 0, kv_ops = 0, kvq_bad = 0, kvq_zero = 0, kvd_cyc = 0;
    reg [63:0] kv_stall_total = 0;
    wire seq_other_ok = (dut.d_barrier ? dut.drained : (!dut.d_chase || dut.chased)) && dut.unit_ready;
    always @(posedge clk) if (dut.st != 0) begin
        if (dut.u_me.active) me_busy <= me_busy + 1;
        if (dut.u_su.active) su_busy <= su_busy + 1;
        if (!dut.u_me.active && !dut.u_su.active) both_idle <= both_idle + 1;
        //: cycles the sequencer waits only for the KV window
        if (dut.st == 6 && dut.d_unit == 1 && seq_other_ok && !dut.kv_gate) kv_stall <= kv_stall + 1;
    end
    // delivered KV words against the cache (nonzero deliveries must match)
    reg chk_v; reg [G*AW-1:0] chk_addr; reg [W*16-1:0] lw; reg [W*32-1:0] lw32;
    always @(posedge clk) begin
        chk_v <= kv_re; chk_addr <= kv_raddr;
        if (chk_v)
            for (q = 0; q < G; q = q + 1) begin
                lw = logical_kv(chk_addr[q*AW +: AW] % KV_WORDS, pos >> 4);
                for (l = 0; l < W; l = l + 1) lw32[l*32 +: 32] = {lw[l*16 +: 16], 16'h0};
                if (kv_q[q*W*32 +: W*32] != lw32) begin
                    if (kv_q[q*W*32 +: W*32] == 0) kvq_zero = kvq_zero + 1;
                    else kvq_bad = kvq_bad + 1;
                end
            end
        if (kvd_v) begin kvd_cyc <= cycles; kv_ops <= kv_ops + 1; end
        if (trace && dut.me_go && dut.me_wsrc)
            $display("KVGO cyc=%0d pc=%0d announced=%0d wait=%0d tiles=%0d k=%0d jsh=%0d", cycles, dut.pc, kvd_cyc,
                     cycles - kvd_cyc, dut.me_tiles, dut.me_k, dut.me_jsh);
    end

`ifdef OT_HDC_KV_MACROS
`ifdef OT_MEM_FAULTS
    // +FAULT_WIN_KIND/ROW/COL: one fault in window bank 0's macro (physical cell
    // coordinates, kinds as in tools/mem_compiler/behav.py), applied on the first clock
    integer fk_k, fk_r, fk_c;
    reg fk = 1'b0;
    initial fk = $value$plusargs("FAULT_WIN_KIND=%d", fk_k) && $value$plusargs("FAULT_WIN_ROW=%d", fk_r)
                 && $value$plusargs("FAULT_WIN_COL=%d", fk_c);
    always @(posedge clk) if (cyc == 1 && fk) begin
        u_bufs.g_win[0].u_sram.f_kind[0] = fk_k[3:0];
        u_bufs.g_win[0].u_sram.f_r[0] = fk_r;
        u_bufs.g_win[0].u_sram.f_c[0] = fk_c;
        $display("FAULT win0 kind=%0d row=%0d col=%0d", fk_k, fk_r, fk_c);
    end
`endif
`endif
    reg [W*32-1:0] kvw;
    integer to0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        if (!$value$plusargs("LEAD=%d", lead)) lead = 512;
`ifdef OT_HDC_KV_MACROS
        go = 1'b0;
        if ($test$plusargs("BIST")) bist_en = 1'b1;
`endif
        $readmemh({dir, "/wrom.hex"}, wrom);
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
        // HBM holds the whole image; the tail the open tile and the one before it
        for (i = 0; i < KV_WORDS; i = i + 1) u_hbm.mem[i] = pack16(kv[i]);
        for (b = 0; b < 2; b = b + 1)
            for (i = 0; i < TDEPTH; i = i + 1) tl[b][i] = 0;
        to0 = multi ? 0 : (pos >> 4);
        for (T = to0 - 1; T <= to0; T = T + 1)
            if (T >= 0)
                for (i = 0; i < TDEPTH; i = i + 1)
                    tl[T & 1][i] = pack16(kv[((i >> LOG_HD) << (LOG_HD + LOG_TW)) | (T << LOG_HD) | (i & ((1 << LOG_HD) - 1))]);
        $readmemh({dir, "/prog.hex"}, prog);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    task automatic check_and_finish(input [NW-1:0] exp_tok);
        reg [W*16-1:0] w16;
        integer p, sum_rd, sum_wr, sum_act, sum_hit, sum_conf, sum_ref;
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
            sum_rd = 0; sum_wr = 0; sum_act = 0; sum_hit = 0; sum_conf = 0; sum_ref = 0;
            for (p = 0; p < NPC; p = p + 1) begin
                sum_rd = sum_rd + u_hbm.st_rd[p]; sum_wr = sum_wr + u_hbm.st_wr[p];
                sum_act = sum_act + u_hbm.st_act[p]; sum_hit = sum_hit + u_hbm.st_hit[p];
                sum_conf = sum_conf + u_hbm.st_conf[p]; sum_ref = sum_ref + u_hbm.st_ref[p];
            end
            $display("HDC token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, exp_tok, cycles, fault, bad_lg, bad_vm, bad_kv);
            $display("UTIL me_issue_cycles=%0d su_issue_cycles=%0d both_idle_cycles=%0d", me_busy, su_busy, both_idle);
            $display("KVSTREAM kv_stall_cycles=%0d kv_ops=%0d stream_fault=%0d kvq_bad=%0d kvq_zero=%0d hbm_reads=%0d hbm_writes=%0d acts=%0d row_hits=%0d row_conflicts=%0d refreshes=%0d rd_lat_avg_ps=%0d rd_lat_max_ps=%0d req_backpressure_cycles=%0d total_cycles=%0d",
                     kv_stall, kv_ops, kvs_fault, kvq_bad, kvq_zero, sum_rd, sum_wr, sum_act, sum_hit, sum_conf, sum_ref,
                     (sum_rd > 0) ? u_hbm.st_rd_lat_sum / sum_rd : 0, u_hbm.st_rd_lat_max, u_hbm.st_bp_cycles,
                     multi ? total_cycles : cycles);
            if (next_token == exp_tok && !fault && !kvs_fault && kvq_bad == 0 && bad_lg == 0 && bad_vm == 0 && bad_kv == 0)
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
    endtask

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (lc < 5 || go) lc <= lc + 1;
        if (lc == 5 && go) rst_n <= 1'b1;
        start <= (lc == 10);
        if (lc == 9 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && lc > 12 && done && !start) begin
            total_cycles = total_cycles + cycles;
            if (step >= n_prompt - 1 && !checklast) begin
                $display("STEP pos=%0d in=%0d out=%0d gold=%0d cycles=%0d fault=%0d", pos, token, next_token,
                         gold_gen[step - (n_prompt - 1)], cycles, fault);
                if (next_token != gold_gen[step - (n_prompt - 1)] || fault || kvs_fault) gen_bad = gen_bad + 1;
            end
            if (step + 1 == n_prompt + n_gen - 1) begin
                if (checklast) check_and_finish(expect_tok);
                else begin
                $display("HDC_MULTI steps=%0d generated=%0d mismatches=%0d total_cycles=%0d", step + 1,
                         n_gen, gen_bad, total_cycles);
                $display("KVSTREAM kv_stall_cycles=%0d kv_ops=%0d stream_fault=%0d kvq_bad=%0d kvq_zero=%0d total_cycles=%0d",
                         kv_stall, kv_ops, kvs_fault, kvq_bad, kvq_zero, total_cycles);
                if (gen_bad == 0 && !kvs_fault && kvq_bad == 0) $display("PASS"); else $display("FAIL");
                $finish;
                end
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
        end
        if (!multi && lc > 12 && done) check_and_finish(expect_tok);
`ifdef OT_HDC_KV_MACROS
        // buffers out of reset, optional self-test, then the tail preload, then the core
        if (cyc == 2) bist_rst_n <= 1'b1;
        bist_start <= bist_en && cyc == 4 && !bist_started;
        if (bist_start) bist_started <= 1'b1;
        tst_tl_we <= 2'b00;
        if (!go && !pre_busy && cyc >= 4 && (!bist_en || (bist_started && bist_done))) begin
            if (bist_en)
                $display("BIST pass=%0d sram_status=%b bist_cycles=%0d", bist_pass, bist_sram_status, cyc - 5);
            pre_busy <= 1'b1; pre_i <= 0; tst_tl_en <= 1'b1;
        end
        if (pre_busy) begin
            if (pre_i < TDEPTH) begin
                tst_tl_we <= 2'b11; tst_tl_addr <= pre_i;
                tst_tl_wdata <= {tl[1][pre_i], tl[0][pre_i]};
                pre_i <= pre_i + 1;
            end else begin
                pre_busy <= 1'b0; tst_tl_en <= 1'b0; go <= 1'b1;
            end
        end
`endif
        //: an underflow (or any streamer fault) ends the run: its state no longer follows the engine
        if (kvs_fault) begin
            $display("STREAM_FAULT cyc=%0d pc=%0d", cycles, dut.pc);
            check_and_finish(expect_tok);
        end
        if (trace && (dut.me_go || dut.su_go))
            $display("ISSUE cyc=%0d pc=%0d unit=%0d barrier=%0d", cycles, dut.pc, dut.d_unit, dut.d_barrier);
        if (cyc > 20000000) begin
            $display("TIMEOUT pc=%0d st=%0d me_idle=%0d su_idle=%0d kv_ok=%0d kvs_fault=%0d", dut.pc, dut.st,
                     dut.me_idle, dut.su_idle, kv_ok, kvs_fault);
            $finish;
        end
    end
endmodule
