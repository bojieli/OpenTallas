`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_sys_die: one die of the Qwen3 ROM system top (TP-N tensor group).
// NEW composition; every block on the die's token path is RTL:
//
//   ot_hdc_core (KV_HBM = 1)       the decode core; its KV-sourced matrix ops
//                                  issue only on the KV service's kv_ok
//   ot_qwen_tp_seq_sys             the per-die sequencer (segments, collectives,
//                                  argmax gather), full-position collective tags
//   ot_rom_oneshot_die             the one-shot collective engine (rank-order
//                                  FP32 all-reduce, all-gather)
//   ot_qwen_d2d_link x (N-1)       link layers to the other dies (seq / CRC /
//                                  ACK-NAK replay / training)
//   ot_qwen_sys_kv_svc             KV in attached HBM: per-token fills, write-
//                                  back with tagged write-done, kv_ok, drained
//   ot_qwen_sys_rom x 4            program, descriptor, weight (and embedding)
//                                  and constant ROMs with address bounds
//   vector memory                  the die's VM SRAM (element and word ports)
//
// Memories are macro models (synchronous read, latency 1); ROM images are the
// tools/hdc_program.py --tp images of this die.  PHY flit ports go to the
// package's die-to-die channels; the HBM port to the die's HBM controller.
// ---------------------------------------------------------------------------
module ot_qwen_sys_die #(
    parameter integer N          = 4,
    parameter integer RANK       = 0,
    parameter integer G          = 4,
    parameter integer NW         = 16,
    parameter integer TAG_FULL   = 1,
    parameter integer TAGW       = 40,
    parameter integer CDEPTH     = 16,
    parameter integer WROM_WORDS = 16384,
    parameter integer KVWORDS    = 512,
    parameter integer LWB        = 6,
    parameter integer NPC        = 4,
    parameter integer HTAGW      = 7,
    parameter integer LINK_TMO   = 96,
    parameter integer SEQ_WDOG   = 1 << 20,
    parameter [23:0]  BOOT_SECTOR = 24'hFFFFFF,
    parameter integer SCRUB_SECTORS = 0,
    // ME_CDC = 1: the matrix engine, its weight-ROM port, the KV read port and the VM x read port run on fclk
    // (1.2 GHz streaming domain); sequencer, stream unit, reducers, VM writes, KV service, collective engine and
    // links on clk (0.9 GHz).  The core is ot_hdc_core_2clk (tools/qwen_rom_sys_core2clk_emit.py).
    parameter integer ME_CDC = 0,
    parameter integer KV_PREFETCH = 0,
    parameter integer LFW        = 32 + 1 + 1 + 8 + 1 + 8 + 1 + 1 + 3 + (512 + 2 + TAGW)
) (
    input  wire               clk,
    input  wire               fclk,
    input  wire               link_rst_n,
    input  wire               hbm_rst_n,
    input  wire               rst_n,          // core, sequencer, collective engine
    // package controller
    input  wire               start,
    input  wire [NW-1:0]      token,
    input  wire [NW-1:0]      pos,
    input  wire [22:0]        kv_base,        // HBM word offset of the user's KV
    output wire               done,
    output wire [NW-1:0]      next_token,
    output wire [31:0]        next_val,
    output wire               drained,
    // PHY: one flit a cycle to / from every other die (index = far rank)
    output wire [N*LFW-1:0]   ph_tx,
    input  wire [N-1:0]       ph_rx_v,
    input  wire [N*LFW-1:0]   ph_rx,
    output wire [N-1:0]       link_up,
    // HBM controller port
    output wire               h_req_v,
    input  wire               h_req_rdy,
    output wire               h_req_we,
    output wire [23:0]        h_req_addr,
    output wire [4:0]         h_req_len,
    output wire [HTAGW-1:0]   h_req_tag,
    output wire [255:0]       h_req_wdata,
    input  wire [NPC-1:0]     h_rsp_v,
    output wire [NPC-1:0]     h_rsp_rdy,
    input  wire [NPC*HTAGW-1:0] h_rsp_tag,
    input  wire [NPC*4-1:0]   h_rsp_beat,
    input  wire [NPC*256-1:0] h_rsp_data,
    input  wire [NPC-1:0]     h_rsp_wr,
    input  wire               boot_go,
    output wire               boot_done,
    output wire               boot_ok,
    // faults: [0] core or ROM bound, [1] sequencer, [2] collective, [3] KV service, [4] link
    output wire [4:0]         fault_vec,
    output wire [8*32-1:0]    stats            // {kv fill words, kv wb sectors, kv_ok wait, crc errors,
                                               //  replays, seq drops, collective cycles, busy cycles}
);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, PAW = 12, DAW = 6, FLIT = 512;
    localparam integer RB = (N > 1) ? $clog2(N) : 1;
    localparam integer PW = FLIT + 2 + TAGW;
    localparam integer VM_ELEMS = 4096, CROM_WORDS = 4096, PROG_WORDS = 4096;

    // ---------------------------------------------------------------- core <-> memories
    wire prog_re; wire [PAW-1:0] prog_addr; wire [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; wire [G*W*16-1:0] wrom_q;
    wire crom_re; wire [AW-1:0] crom_addr; wire [63:0] crom_q;
    wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; wire [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    reg [31:0] va_q, vb_q, vc_q;
    wire vw_su_we, vw_rd_we; wire [AW-1:0] vw_su_addr, vw_rd_addr;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
    wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [31:0] vw_su_data, vw_rd_data;
    wire vw_mx_we; wire [AW-1:0] vw_mx_addr;
    wire [W-1:0] vw_mx_mask; wire [W*32-1:0] vw_mx_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [31:0] cycles;
    wire core_start, core_done, core_fault;
    wire [NW-1:0] core_tok, core_pos, core_ntok; wire [31:0] core_nval;
    wire [PAW-1:0] prog_base;
    wire desc_re; wire [DAW-1:0] desc_addr; wire [63:0] desc_q;
    wire s_vre, s_vwe; wire [7:0] s_vraddr, s_vwaddr; wire [FLIT-1:0] s_vwdata; reg [FLIT-1:0] s_vrq;
    wire kvd_v, kvd_kindk; wire [AW-1:0] kvd_wbase;
    wire kv_ok;

    wire f_wrom_re; wire [AW-1:0] f_wrom_addr; wire [G*W*16-1:0] f_wrom_q;
    ot_hdc_core_2clk #(.ME_CDC(ME_CDC), .W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .KV_HBM(1)) core (
        .clk(clk), .fclk(fclk), .f_wrom_re(f_wrom_re), .f_wrom_addr(f_wrom_addr), .f_wrom_q(f_wrom_q), .rst_n(rst_n), .start(core_start), .token(core_tok), .pos(core_pos),
        .done(core_done), .next_token(core_ntok), .next_val(core_nval),
        .cycles(cycles), .fault(core_fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .kv_write_drained(drained), .kv_write_flush(),   // read only with KV_VEC_WRITE_BRIDGE = 1
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_mx_we(vw_mx_we), .vw_mx_addr(vw_mx_addr), .vw_mx_mask(vw_mx_mask), .vw_mx_data(vw_mx_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kvd_ts(), .kvd_ks(), .kvd_js(), .kvd_wcs(), .kvd_split(),
        .kvd_jsh(), .kvd_tiles(), .kvd_k(), .kvd_nout(), .kvd_kindk(kvd_kindk), .kvd_pos(), .kv_ok(kv_ok));

    // ---------------------------------------------------------------- ROMs
    wire [3:0] oob;
    ot_qwen_sys_rom #(.DW(INSTR_BITS), .DEPTH(PROG_WORDS), .AW(AW), .NAME("prog_d"), .DIE(RANK)) u_prog (
        .clk(clk), .rst_n(rst_n), .re(prog_re), .addr({{(AW-PAW){1'b0}}, prog_base} + {{(AW-PAW){1'b0}}, prog_addr}),
        .q(prog_q), .oob(oob[0]));
    ot_qwen_sys_rom #(.DW(64), .DEPTH(64), .AW(AW), .NAME("desc_d"), .DIE(RANK)) u_desc (
        .clk(clk), .rst_n(rst_n), .re(desc_re), .addr({{(AW-DAW){1'b0}}, desc_addr}), .q(desc_q), .oob(oob[1]));
    ot_qwen_sys_rom #(.DW(G*W*16), .DEPTH(WROM_WORDS), .AW(AW), .NAME("wrom_d"), .DIE(RANK)) u_wrom (
        .clk(clk), .rst_n(rst_n), .re(wrom_re), .addr(wrom_addr), .q(wrom_q), .oob(oob[2]));
    // the engine's weight port on fclk (ME_CDC): a second read port of the same ROM image
    wire fck = (ME_CDC != 0) ? fclk : clk;
    wire oob_f;
    ot_qwen_sys_rom #(.DW(G*W*16), .DEPTH(WROM_WORDS), .AW(AW), .NAME("wrom_d"), .DIE(RANK)) u_wrom_f (
        .clk(fck), .rst_n(rst_n), .re(f_wrom_re), .addr(f_wrom_addr), .q(f_wrom_q), .oob(oob_f));
    ot_qwen_sys_rom #(.DW(64), .DEPTH(CROM_WORDS), .AW(AW), .NAME("crom_d"), .DIE(RANK)) u_crom (
        .clk(clk), .rst_n(rst_n), .re(crom_re), .addr(crom_addr), .q(crom_q), .oob(oob[3]));

    // ---------------------------------------------------------------- vector memory
    reg [31:0] vm [0:VM_ELEMS-1];
    integer q, l, k;
    initial for (k = 0; k < VM_ELEMS; k = k + 1) vm[k] = 32'd0;
    // the engine's x read port runs on the engine clock (fclk with ME_CDC): 1R1W, fast read, slow write
    always @(posedge fck)
        for (q = 0; q < G; q = q + 1)
            if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
    always @(posedge clk) begin
        if (va_re) va_q <= vm[va_addr[11:0]];
        if (vb_re) vb_q <= vm[vb_addr[11:0]];
        if (vc_re) vc_q <= vm[vc_addr[11:0]];
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        if (vw_mx_we)
            for (l = 0; l < W; l = l + 1)
                if (vw_mx_mask[l]) vm[{vw_mx_addr[7:0], 4'b0} + l] <= vw_mx_data[32*l +: 32];
        if (vw_su_we) vm[vw_su_addr[11:0]] <= vw_su_data;
        if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
        if (s_vre) for (l = 0; l < W; l = l + 1) s_vrq[32*l +: 32] <= vm[{s_vraddr, 4'b0} + l];
        if (s_vwe) for (l = 0; l < W; l = l + 1) vm[{s_vwaddr, 4'b0} + l] <= s_vwdata[32*l +: 32];
    end

    // ---------------------------------------------------------------- sequencer
    wire cv, crd, cl, cm, rv, rl, re_;
    wire [FLIT-1:0] cd, rd;
    wire [TAGW-1:0] ct;
    wire [RB-1:0] rr;
    wire s_fault, coll_busy;
    wire [2:0] s_fcode;
    ot_qwen_tp_seq_sys #(.TAG_FULL(TAG_FULL), .STRAY_FAULT(1), .WDOG(SEQ_WDOG),
                         .N(N), .NW(NW), .PAW(PAW), .VWA(8), .DAW(DAW), .FW(FLIT), .TAGW(TAGW)) seq (
        .clk(clk), .rst_n(rst_n),
        .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .next_val(next_val),
        .fault(s_fault), .coll_busy(coll_busy),
        .core_start(core_start), .core_token(core_tok), .core_pos(core_pos), .core_done(core_done),
        .core_next_token(core_ntok), .core_next_val(core_nval), .core_fault(core_fault),
        .prog_base(prog_base), .desc_re(desc_re), .desc_addr(desc_addr), .desc_q(desc_q),
        .vm_re(s_vre), .vm_raddr(s_vraddr), .vm_rq(s_vrq),
        .vm_we(s_vwe), .vm_waddr(s_vwaddr), .vm_wdata(s_vwdata),
        .c_valid(cv), .c_ready(crd), .c_data(cd), .c_last(cl), .c_mode(cm), .c_tag(ct),
        .r_valid(rv), .r_data(rd), .r_last(rl), .r_rank(rr), .r_err(re_), .fault_code(s_fcode));

    // ---------------------------------------------------------------- collective engine + links
    wire          e_txv;
    wire [PW-1:0] e_txr;
    wire [N-1:0]  e_txrdy, e_crin, e_rxv, e_crout;
    wire [N*PW-1:0] e_rxr;
    wire          e_fault;
    wire [2:0]    e_fcode;
    ot_rom_oneshot_die #(.N(N), .RANK(RANK), .LANES(FLIT / 32), .TAGW(TAGW), .DEPTH(CDEPTH)) u_coll (
        .clk(clk), .rst_n(rst_n),
        .in_valid(cv), .in_ready(crd), .in_data(cd), .in_last(cl), .in_mode(cm), .in_tag(ct),
        .tx_valid(e_txv), .tx_rec(e_txr), .tx_ready(e_txrdy), .cr_in(e_crin),
        .rx_valid(e_rxv), .rx_rec(e_rxr), .cr_out(e_crout),
        .out_valid(rv), .out_data(rd), .out_last(rl), .out_rank(rr), .out_err(re_),
        .fault(e_fault), .fault_code(e_fcode));

    wire [N-1:0]  l_fault;
    wire [N*32-1:0] l_crc, l_rep, l_drop;
    genvar r;
    generate for (r = 0; r < N; r = r + 1) begin : g_peer
        if (r == RANK) begin : g_self
            assign e_txrdy[r] = 1'b1; assign e_crin[r] = 1'b0; assign e_rxv[r] = 1'b0;
            assign e_rxr[r*PW +: PW] = {PW{1'b0}};
            assign ph_tx[r*LFW +: LFW] = {LFW{1'b0}};
            assign link_up[r] = 1'b1; assign l_fault[r] = 1'b0;
            assign l_crc[32*r +: 32] = 0; assign l_rep[32*r +: 32] = 0; assign l_drop[32*r +: 32] = 0;
        end else begin : g_link
            ot_qwen_d2d_link #(.PW(PW), .TMO(LINK_TMO)) u_link (
                .clk(clk), .rst_n(link_rst_n),
                .up_valid(e_txv), .up_ready(e_txrdy[r]), .up_rec(e_txr), .up_cr(e_crout[r]),
                .dn_valid(e_rxv[r]), .dn_rec(e_rxr[r*PW +: PW]), .dn_cr(e_crin[r]),
                .tx_flit(ph_tx[r*LFW +: LFW]), .rx_valid(ph_rx_v[r]), .rx_flit(ph_rx[r*LFW +: LFW]),
                .link_up(link_up[r]), .link_fault(l_fault[r]),
                .n_crc_err(l_crc[32*r +: 32]), .n_replay(l_rep[32*r +: 32]), .n_seq_drop(l_drop[32*r +: 32]),
                .n_sent());
        end
    end endgenerate

    // ---------------------------------------------------------------- KV service
    wire kv_fault;
    wire [5:0] kv_fcode;
    wire [31:0] kv_fill, kv_wb, kv_wait;
    ot_qwen_sys_kv_svc #(.W(W), .G(G), .AW(AW), .KVWORDS(KVWORDS), .LWB(LWB), .HAW(24), .SECW(256),
                         .NPC(NPC), .LOT(HTAGW - 1), .LENW(5), .BEATW(4), .BOOT_SECTOR(BOOT_SECTOR), .SCRUB_SECTORS(SCRUB_SECTORS),
                         .RCLK_SEP(ME_CDC), .PREFETCH(KV_PREFETCH)) u_kv (
        .clk(clk), .rclk(fclk), .rst_n(hbm_rst_n), .tok_start(start), .kv_base(kv_base),
        .kvd_v(kvd_v), .kvd_wbase(kvd_wbase), .kv_ok(kv_ok),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .drained(drained),
        .h_req_v(h_req_v), .h_req_rdy(h_req_rdy), .h_req_we(h_req_we), .h_req_addr(h_req_addr),
        .h_req_len(h_req_len), .h_req_tag(h_req_tag), .h_req_wdata(h_req_wdata),
        .h_rsp_v(h_rsp_v), .h_rsp_rdy(h_rsp_rdy), .h_rsp_tag(h_rsp_tag), .h_rsp_beat(h_rsp_beat),
        .h_rsp_data(h_rsp_data), .h_rsp_wr(h_rsp_wr),
        .boot_go(boot_go), .boot_done(boot_done), .boot_ok(boot_ok),
        .fault(kv_fault), .fault_code(kv_fcode),
        .n_fill_words(kv_fill), .n_wb_sectors(kv_wb), .n_kvok_wait(kv_wait));

    assign fault_vec = {|l_fault, kv_fault, e_fault, s_fault, core_fault | (|oob) | oob_f};

    // ---------------------------------------------------------------- statistics
    reg [31:0] st_coll, st_busy;
    reg started;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin st_coll <= 0; st_busy <= 0; started <= 1'b0; end
        else begin
            if (start) started <= 1'b1;
            if (coll_busy) st_coll <= st_coll + 1;
            if (started && !done) st_busy <= st_busy + 1;
        end
    end
    reg [31:0] s_crc, s_rep, s_drop;
    integer j;
    always @(*) begin
        s_crc = 0; s_rep = 0; s_drop = 0;
        for (j = 0; j < N; j = j + 1) begin
            s_crc = s_crc + l_crc[32*j +: 32]; s_rep = s_rep + l_rep[32*j +: 32]; s_drop = s_drop + l_drop[32*j +: 32];
        end
    end
    assign stats = {kv_fill, kv_wb, kv_wait, s_crc, s_rep, s_drop, st_coll, st_busy};
endmodule
