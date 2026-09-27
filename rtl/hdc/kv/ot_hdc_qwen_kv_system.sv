`timescale 1ns/1ps
// Qwen vector KV boundary: fixed-latency matrix reads come from the streamer's
// prefetched BF16 window or the 2*SW FP8 K-tail banks. Vector writes are
// buffered, quantized and sent to the same tail banks or to physical 32-byte
// V sectors. The streamer flushes closed K tiles through the shared HBM port.
// A controller boots resident K tiles through boot_* before the first token,
// and holds a dependent KV op until kv_ok and kv_write_drained are both high.
module ot_hdc_qwen_kv_system #(
    parameter integer W=16, G=4, SW=8, IL=8, AW=24, NW=16,
    parameter integer LWIN=8, NPC=4, BK=16,
    parameter integer LOG_HD=7, LOG_TW=2, LLG=3, V0_WORD=4096
) (
    input wire clk,rst_n,
    input wire tok_start, input wire [NW-1:0] tok_pos,cfg_lead,
    input wire kvd_v, input wire [AW-1:0] kvd_wbase,kvd_ts,kvd_ks,kvd_js,
    input wire [AW-1:0] kvd_wcs, input wire [3:0] kvd_split,
    input wire [2:0] kvd_jsh,
    input wire [NW-1:0] kvd_tiles,kvd_k,kvd_nout,kvd_pos,
    input wire kvd_kindk, output wire kv_ok,
    input wire kv_re, input wire [G*AW-1:0] kv_raddr,
    output wire [G*W*32-1:0] kv_q,
    input wire [SW-1:0] kv_we,
    input wire [SW*AW-1:0] kv_waddr,
    input wire [SW*32-1:0] kv_wdata,
    input wire kv_write_flush, output wire kv_write_drained,
    // Physical pre-token K-tail boot, one logical FP8 word per cycle.
    input wire boot_v, input wire [AW-1:0] boot_word,
    input wire [127:0] boot_data,
    // G-bank BF16 prefetch window SRAM.
    output wire [G-1:0] win_we,
    output wire [G*LWIN-1:0] win_waddr,
    output wire [G*W*16-1:0] win_wdata,
    output wire win_re, output wire [LWIN-1:0] win_raddr,
    input wire [G*W*16-1:0] win_q,
    // 2*SW 1R1W FP8 tail banks; physical memory/macro owner supplies q.
    output wire [2*SW-1:0] bank_we,bank_re,
    output wire [2*SW*AW-1:0] bank_wrow,bank_rrow,
    output wire [2*SW*16-1:0] bank_wmask,
    output wire [2*SW*128-1:0] bank_wdata,
    input wire [2*SW*128-1:0] bank_q,
    // Shared 32-byte HBM port.
    output wire h_req_v, input wire h_req_ready, output wire h_req_we,
    output wire [AW-1:0] h_req_sector,
    output wire [$clog2(BK):0] h_req_len,
    output wire [1+LWIN+$clog2(G)+3-1:0] h_req_tag,
    output wire [255:0] h_req_data,
    input wire [NPC-1:0] h_rsp_v,
    output wire [NPC-1:0] h_rsp_ready,
    input wire [NPC*(1+LWIN+$clog2(G)+3)-1:0] h_rsp_tag,
    input wire [NPC*$clog2(BK)-1:0] h_rsp_beat,
    input wire [NPC*256-1:0] h_rsp_data,
    output wire fault
);
    localparam integer LBK=$clog2(BK), TAGW=1+LWIN+$clog2(G)+3;
    localparam integer TAW=LLG+LOG_HD, LSW=$clog2(SW);
    wire kvs_ok,kvs_fault,tail_fault,sector_fault,arb_fault,write_fault;
    reg desc_pending,desc_overrun;
    reg [AW-1:0] desc_wbase,desc_ts,desc_ks,desc_js,desc_wcs;
    reg [3:0] desc_split;
    reg [2:0] desc_jsh;
    reg [NW-1:0] desc_tiles,desc_k,desc_nout,desc_pos;
    reg desc_kindk;
    wire stream_kvd_v = desc_pending && kv_write_drained;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin desc_pending<=0; desc_overrun<=0; end
        else begin
            if (stream_kvd_v) desc_pending<=0;
            if (kvd_v) begin
                if (desc_pending && !stream_kvd_v) desc_overrun<=1;
                desc_pending<=1;
                desc_wbase<=kvd_wbase; desc_ts<=kvd_ts; desc_ks<=kvd_ks; desc_js<=kvd_js;
                desc_wcs<=kvd_wcs; desc_split<=kvd_split;
                desc_jsh<=kvd_jsh; desc_tiles<=kvd_tiles; desc_k<=kvd_k;
                desc_nout<=kvd_nout; desc_pos<=kvd_pos; desc_kindk<=kvd_kindk;
            end
        end
    end
    wire [1:0] tl_re,ignored_tl_we;
    wire [2*TAW-1:0] tl_raddr,ignored_tl_waddr;
    wire [2*W-1:0] ignored_tl_wmask;
    wire [2*W*16-1:0] tl_q,ignored_tl_wdata;
    wire [G-1:0] tl_group_re;
    wire [G*AW-1:0] tl_group_raddr;
    wire [G*W*16-1:0] tl_group_q;
    wire [2*SW-1:0] vec_tl_we,group_bank_re,flush_bank_re;
    wire [2*SW*AW-1:0] vec_tl_row,group_bank_row,flush_bank_row;
    wire group_fault,flush_fault;
    wire tail_collision=|(group_bank_re & flush_bank_re);
    wire [2*SW*16-1:0] vec_tl_mask;
    wire [2*SW*128-1:0] vec_tl_data;
    wire lq_v,lq_ready,lq_we;
    wire [AW-1:0] lq_addr;
    wire [LBK:0] lq_len;
    wire [TAGW-1:0] lq_tag;
    wire [127:0] lq_data;
    wire [NPC-1:0] lr_v,lr_ready;
    wire [NPC*TAGW-1:0] lr_tag;
    wire [NPC*LBK-1:0] lr_beat;
    wire [NPC*128-1:0] lr_data;
    wire aq_v,aq_ready,aq_we;
    wire [AW-1:0] aq_sector;
    wire [LBK:0] aq_len;
    wire [TAGW-1:0] aq_tag;
    wire [255:0] aq_data;
    wire [NPC-1:0] ar_v,ar_ready;
    wire [NPC*TAGW-1:0] ar_tag;
    wire [NPC*LBK-1:0] ar_beat;
    wire [NPC*256-1:0] ar_data;
    wire vr_v,vr_ready,vr_resp_v,vw_v,vw_ready;
    wire [AW-1:0] vr_sector,vw_sector;
    wire [255:0] vr_resp_data,vw_data;
    wire [AW-1:0] boot_row =
        ((boot_word >> (LOG_HD+LOG_TW)) << (LOG_HD-LSW)) |
        ((boot_word & ((1<<LOG_HD)-1)) >> LSW);
    wire [$clog2(2*SW)-1:0] boot_bank =
        (boot_word[LOG_HD] ? SW : 0) + boot_word[LSW-1:0];
    initial begin
        if (W!=16 || SW>(1<<LOG_HD)) $error("Unsupported Qwen KV tail geometry");
    end
    assign kv_ok=kvs_ok && kv_write_drained && !boot_v && !desc_pending && !kvd_v;
    assign fault=kvs_fault || tail_fault || sector_fault || arb_fault || write_fault || desc_overrun;
    assign tail_fault=group_fault || flush_fault || tail_collision;
    ot_hdc_kv_stream #(.W(W),.G(G),.IL(IL),.AW(AW),.NW(NW),.LWIN(LWIN),.NPC(NPC),.BK(BK),.SPLIT_AWARE(1),
                       .LOG_HD(LOG_HD),.LOG_TW(LOG_TW),.LLG(LLG),.V0_WORD(V0_WORD),.HBM_FP8(1)) u_stream (
        .clk(clk),.rst_n(rst_n),.tok_start(tok_start),.tok_pos(tok_pos),.cfg_lead(cfg_lead),
        .kvd_v(stream_kvd_v),.kvd_wbase(desc_wbase),.kvd_ts(desc_ts),.kvd_ks(desc_ks),.kvd_js(desc_js),
        .kvd_wcs(desc_wcs),.kvd_split(desc_split),
        .kvd_jsh(desc_jsh),.kvd_tiles(desc_tiles),.kvd_k(desc_k),.kvd_nout(desc_nout),
        .kvd_kindk(desc_kindk),.kvd_pos(desc_pos),.kv_ok(kvs_ok),
        .kv_re(kv_re),.kv_raddr(kv_raddr),.kv_q(kv_q),
        .kv_we(1'b0),.kv_waddr('0),.kv_wdata('0),
        .win_we(win_we),.win_waddr(win_waddr),.win_wdata(win_wdata),
        .win_re(win_re),.win_raddr(win_raddr),.win_q(win_q),
        .tl_we(ignored_tl_we),.tl_waddr(ignored_tl_waddr),
        .tl_wmask(ignored_tl_wmask),.tl_wdata(ignored_tl_wdata),
        .tl_re(tl_re),.tl_raddr(tl_raddr),.tl_q(tl_q),
        .tl_group_re(tl_group_re),.tl_group_raddr(tl_group_raddr),.tl_group_q(tl_group_q),
        .boot_v(1'b0),.boot_addr('0),.boot_data('0),
        .hq_v(lq_v),.hq_rdy(lq_ready),.hq_we(lq_we),.hq_addr(lq_addr),
        .hq_len(lq_len),.hq_tag(lq_tag),.hq_wdata(lq_data),
        .hr_v(lr_v),.hr_rdy(lr_ready),.hr_tag(lr_tag),.hr_beat(lr_beat),.hr_data(lr_data),
        .fault(kvs_fault));
    ot_hdc_qwen_kv_tail_group_port #(.G(G),.SW(SW),.AW(AW),.LOG_HD(LOG_HD),.LOG_TW(LOG_TW),.W(W)) u_tail (
        .clk(clk),.rst_n(rst_n),.rd_v(tl_group_re),.rd_word(tl_group_raddr),.rd_data(tl_group_q),
        .bank_re(group_bank_re),.bank_row(group_bank_row),.bank_q(bank_q),.addr_error(group_fault));
    ot_hdc_qwen_kv_tail_bank_port #(.SW(SW),.AW(AW),.LOG_HD(LOG_HD),.LOG_TW(LOG_TW),.LLG(LLG),.W(W)) u_flush_tail (
        .clk(clk),.rst_n(rst_n),.tl_re(tl_re),.tl_raddr(tl_raddr),.tl_q(tl_q),
        .bank_re(flush_bank_re),.bank_row(flush_bank_row),.bank_q(bank_q),.addr_error(flush_fault));
    assign bank_re=group_bank_re | flush_bank_re;
    genvar rb;
    generate for (rb=0;rb<2*SW;rb=rb+1) begin : g_read_bank
        assign bank_rrow[rb*AW +: AW]=group_bank_re[rb] ?
            group_bank_row[rb*AW +: AW] : flush_bank_row[rb*AW +: AW];
    end endgenerate
    genvar b;
    generate for (b=0;b<2*SW;b=b+1) begin : g_bank
        assign bank_we[b]=boot_v ? (boot_bank==b) : vec_tl_we[b];
        assign bank_wrow[b*AW +: AW]=boot_v ? boot_row : vec_tl_row[b*AW +: AW];
        assign bank_wmask[b*16 +: 16]=boot_v ? 16'hffff : vec_tl_mask[b*16 +: 16];
        assign bank_wdata[b*128 +: 128]=boot_v ? boot_data : vec_tl_data[b*128 +: 128];
    end endgenerate
    ot_hdc_qwen_kv_vector_bridge #(.SW(SW),.AW(AW),.LOG_HD(LOG_HD),.LOG_TW(LOG_TW),
                                    .V0_ELEMENT(V0_WORD*W)) u_write (
        .clk(clk),.rst_n(rst_n),.core_we(kv_we),.core_addr(kv_waddr),.core_data(kv_wdata),
        .drained(kv_write_drained),.tl_we(vec_tl_we),.tl_row(vec_tl_row),
        .tl_mask(vec_tl_mask),.tl_data(vec_tl_data),
        .fl_v(1'b0),.fl_ready(),.fl_word_addr('0),.fl_word_data('0),
        .flush(kv_write_flush),.mem_r_v(vr_v),.mem_r_ready(vr_ready),
        .mem_r_sector(vr_sector),.mem_r_resp_v(vr_resp_v),.mem_r_resp_data(vr_resp_data),
        .mem_w_v(vw_v),.mem_w_ready(vw_ready),.mem_w_sector(vw_sector),
        .mem_w_data(vw_data),.fault(write_fault));
    ot_hdc_qwen_hbm_sector_bridge #(.AW(AW),.NPC(NPC),.TAGW(TAGW),.LBK(LBK)) u_sector (
        .clk(clk),.rst_n(rst_n),.log_req_v(lq_v),.log_req_ready(lq_ready),
        .log_req_we(lq_we),.log_req_addr(lq_addr),.log_req_len(lq_len),
        .log_req_tag(lq_tag),.log_req_data(lq_data),
        .log_rsp_v(lr_v),.log_rsp_ready(lr_ready),.log_rsp_tag(lr_tag),
        .log_rsp_beat(lr_beat),.log_rsp_data(lr_data),
        .phys_req_v(aq_v),.phys_req_ready(aq_ready),.phys_req_we(aq_we),
        .phys_req_sector(aq_sector),.phys_req_len(aq_len),.phys_req_tag(aq_tag),
        .phys_req_data(aq_data),.phys_rsp_v(ar_v),.phys_rsp_ready(ar_ready),
        .phys_rsp_tag(ar_tag),.phys_rsp_beat(ar_beat),.phys_rsp_data(ar_data),.fault(sector_fault));
    ot_hdc_qwen_kv_phys_arbiter #(.AW(AW),.NPC(NPC),.TAGW(TAGW),.LBK(LBK)) u_arb (
        .clk(clk),.rst_n(rst_n),.a_req_v(aq_v),.a_req_ready(aq_ready),
        .a_req_we(aq_we),.a_req_sector(aq_sector),.a_req_len(aq_len),
        .a_req_tag(aq_tag),.a_req_data(aq_data),.a_rsp_v(ar_v),
        .a_rsp_ready(ar_ready),.a_rsp_tag(ar_tag),.a_rsp_beat(ar_beat),.a_rsp_data(ar_data),
        .b_r_v(vr_v),.b_r_ready(vr_ready),.b_r_sector(vr_sector),
        .b_r_resp_v(vr_resp_v),.b_r_resp_data(vr_resp_data),
        .b_w_v(vw_v),.b_w_ready(vw_ready),.b_w_sector(vw_sector),.b_w_data(vw_data),
        .h_req_v(h_req_v),.h_req_ready(h_req_ready),.h_req_we(h_req_we),
        .h_req_sector(h_req_sector),.h_req_len(h_req_len),.h_req_tag(h_req_tag),
        .h_req_data(h_req_data),.h_rsp_v(h_rsp_v),.h_rsp_ready(h_rsp_ready),
        .h_rsp_tag(h_rsp_tag),.h_rsp_beat(h_rsp_beat),.h_rsp_data(h_rsp_data),.fault(arb_fault));
endmodule
