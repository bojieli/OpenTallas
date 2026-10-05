`timescale 1ns/1ps
// Token-level simulation top of the hardwired decode core: behavioural
// memories loaded from tools/hdc_program.py images.  Driven by Verilator
// (rtl/test/hdc_core_harness.cpp) or any simulator that toggles `clk`.
//
// Default: one decode step at +POS for +TOKEN on the golden-prefilled KV cache,
// then a bit-exact check of every logit, the whole vector memory and the whole
// KV cache against the ISA-level model.
// +MULTI: start from an EMPTY KV cache, run every prompt token through the core
// (the core writes its own KV rows), then generate +NGEN tokens feeding each
// output back, and compare the generated ids with the torch oracle's.
//
// +define+OT_HDC_MEMSYS: the memories are the ASAP7 compiled macros behind
// rtl/hdc/ot_hdc_memsys.sv (ROM content from +OT_ROM_DIR via maps, SECDED on the
// ROM read path, replicated 1R1W KV SRAM).  The golden KV cache is preloaded,
// and read back after the token, through the memory subsystem's test port, so
// the core starts later in simulation time; the core's own cycle count is what
// is reported and compared.
module tb_hdc_core #(
    parameter integer G = 4,                 // matrix-engine lane groups (tools/hdc_isa.py GROUPS)
    parameter integer SU_VEC = 1,            // the vector stream unit (0: the scalar one, SW = 1)
    parameter integer SW = 8,                // stream-unit lanes (tools/hdc_isa.py SU_WIDTH)
    parameter integer KV_BRIDGE = 0          // mirror vector writes through packed sector/tail bridge
) (input wire clk);
    localparam integer INSTR_BITS = 1024;
    localparam integer W = 16, AW = 24, NW = 16, PAW = 12;
    localparam integer WROM_WORDS = 131072, CROM_WORDS = 4096, KV_WORDS = 1024;
    localparam integer VM_ELEMS = 4096, VOCAB = 4096, PROG_WORDS = 4096;

`ifndef OT_HDC_MEMSYS
    reg [G*W*16-1:0] wrom [0:WROM_WORDS-1];
    reg [63:0]      crom [0:CROM_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]      vm   [0:VM_ELEMS-1];
    localparam integer START = 300; // 256 logical K words booted through the hardware bank port
`else
    localparam integer START = 10 + KV_WORDS + 4;   // after the KV preload through the test port
`endif
    reg [W*32-1:0]  kv   [0:KV_WORDS-1];
    reg [31:0]      e_vm [0:VM_ELEMS-1];
    reg [31:0]      e_kv [0:KV_WORDS*W-1];
    reg [31:0]      e_lg [0:VOCAB-1];
    reg [31:0]      lg   [0:VOCAB-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] cycles;

`ifndef OT_HDC_MEMSYS
    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire [SW-1:0] crom_re; wire [SW*AW-1:0] crom_addr; reg [SW*64-1:0] crom_q;
    wire kv_re; wire [SW-1:0] kv_we; wire [G*AW-1:0] kv_raddr; wire [SW*AW-1:0] kv_waddr;
    wire [G*W*32-1:0] kv_q; reg [G*W*32-1:0] kv_q_beh;
    wire [SW*32-1:0] kv_wdata;
    wire kv_write_flush;
    wire [SW-1:0] va_re, vb_re, vc_re; wire [SW*AW-1:0] va_addr, vb_addr, vc_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    reg [SW*32-1:0] va_q, vb_q, vc_q;
`else
    wire prog_re; wire [PAW-1:0] prog_addr; wire [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; wire [G*W*16-1:0] wrom_q;
    wire crom_re; wire [AW-1:0] crom_addr; wire [63:0] crom_q;
    wire kv_re, kv_we; wire [G*AW-1:0] kv_raddr; wire [AW-1:0] kv_waddr; wire [G*W*32-1:0] kv_q; wire [31:0] kv_wdata;
    wire va_re, vb_re, vc_re; wire [AW-1:0] va_addr, vb_addr, vc_addr;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; wire [G*32-1:0] vx_q;
    wire [31:0] va_q, vb_q, vc_q;
    reg tst_kv_en = 1'b1, tst_kv_we = 1'b0, tst_kv_re = 1'b0;
    reg [9:0] tst_kv_waddr = 0, tst_kv_raddr = 0;
    reg [W*32-1:0] tst_kv_wdata = 0;
    wire [W*32-1:0] tst_kv_q;
    reg [11:0] tst_vm_addr = 0;
    wire [31:0] tst_vm_q;
    wire [31:0] ecc_corrected, ecc_uncorrectable;
    localparam integer N_KV = G * 2, N_ROM = 4 + 1 + 6 * G;
    reg bist_en = 1'b0, bist_start = 1'b0, bist_started = 1'b0;
    wire bist_busy, bist_done, bist_pass, rep_scan_out;
    wire [2*N_KV-1:0] bist_sram_status;
    wire [2*N_ROM-1:0] bist_rom_status;
    reg [31:0] exp_sig_mem [0:N_ROM-1];
    wire [32*N_ROM-1:0] bist_exp_sig;
    genvar gs;
    generate for (gs = 0; gs < N_ROM; gs = gs + 1) begin : g_sig
        assign bist_exp_sig[32*gs +: 32] = exp_sig_mem[gs];
    end endgenerate
`endif
    wire [SW-1:0] vw_su_we; wire vw_rd_we; wire [SW*AW-1:0] vw_su_addr; wire [AW-1:0] vw_rd_addr;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr;
    wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data; wire [SW*32-1:0] vw_su_data; wire [31:0] vw_rd_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire vw_mx_we; wire [AW-1:0] vw_mx_addr; wire [W-1:0] vw_mx_mask; wire [W*32-1:0] vw_mx_data;
    wire bridge_drained, bridge_fault;
    wire system_drained, system_kv_ok, system_fault;
    wire [G*W*32-1:0] system_kv_q;
    wire kvd_v,kvd_kindk;
    wire [AW-1:0] kvd_wbase,kvd_ts,kvd_ks,kvd_js,kvd_wcs;
    wire [3:0] kvd_split;
    wire [2:0] kvd_jsh;
    wire [NW-1:0] kvd_tiles,kvd_k,kvd_nout,kvd_pos;
    assign kv_q=system_kv_q;

    ot_hdc_core #(.W(W), .G(G), .AW(AW), .NW(NW), .PAW(PAW), .SU_VEC(SU_VEC), .SW(SW),
                  .KV_HBM(1),.KV_FP8(1),.KV_VEC_WRITE_BRIDGE(1)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos),
        .done(done), .next_token(next_token), .cycles(cycles), .fault(fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .kv_write_drained(system_drained),
        .kv_write_flush(kv_write_flush),
        .kvd_v(kvd_v),.kvd_wbase(kvd_wbase),.kvd_ts(kvd_ts),.kvd_ks(kvd_ks),.kvd_js(kvd_js),
        .kvd_wcs(kvd_wcs),.kvd_split(kvd_split),
        .kvd_jsh(kvd_jsh),.kvd_tiles(kvd_tiles),.kvd_k(kvd_k),.kvd_nout(kvd_nout),
        .kvd_kindk(kvd_kindk),.kvd_pos(kvd_pos),.kv_ok(system_kv_ok),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q),
        .va_re(va_re), .va_addr(va_addr), .va_q(va_q),
        .vb_re(vb_re), .vb_addr(vb_addr), .vb_q(vb_q),
        .vc_re(vc_re), .vc_addr(vc_addr), .vc_q(vc_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .vw_mx_we(vw_mx_we), .vw_mx_addr(vw_mx_addr), .vw_mx_mask(vw_mx_mask), .vw_mx_data(vw_mx_data));

`ifndef OT_HDC_MEMSYS
    localparam integer SYS_LWIN=8,SYS_NPC=4,SYS_BK=16;
    localparam integer SYS_TAGW=1+SYS_LWIN+$clog2(G)+3,SYS_LBK=$clog2(SYS_BK);
    reg [127:0] kv_fp8 [0:KV_WORDS-1];
    reg [255:0] system_hbm [0:KV_WORDS/2-1];
    reg [W*16-1:0] system_win [0:G-1][0:(1<<SYS_LWIN)-1];
    reg [127:0] system_bank [0:2*SW-1][0:15];
    reg [G*W*16-1:0] system_win_q=0;
    reg [2*SW*128-1:0] system_bank_q=0;
    wire [G-1:0] system_win_we;
    wire [G*SYS_LWIN-1:0] system_win_waddr;
    wire [G*W*16-1:0] system_win_wdata;
    wire system_win_re;
    wire [SYS_LWIN-1:0] system_win_raddr;
    wire [2*SW-1:0] system_bank_we,system_bank_re;
    wire [2*SW*AW-1:0] system_bank_wrow,system_bank_rrow;
    wire [2*SW*16-1:0] system_bank_wmask;
    wire [2*SW*128-1:0] system_bank_wdata;
    wire system_hq_v,system_hq_we;
    wire [AW-1:0] system_hq_sector;
    wire [SYS_LBK:0] system_hq_len;
    wire [SYS_TAGW-1:0] system_hq_tag;
    wire [255:0] system_hq_data;
    reg [SYS_NPC-1:0] system_hr_v=0;
    wire [SYS_NPC-1:0] system_hr_ready;
    reg [SYS_NPC*SYS_TAGW-1:0] system_hr_tag=0;
    reg [SYS_NPC*SYS_LBK-1:0] system_hr_beat=0;
    reg [SYS_NPC*256-1:0] system_hr_data=0;
    integer system_hbm_reads=0,system_hbm_writes=0,system_wait_cycles=0;
    reg system_waiting=0;
    wire system_boot_v=(lc>=6 && lc<262 && rst_n);
    wire [7:0] system_boot_idx=lc-6;
    wire [1:0] system_boot_tile=system_boot_idx[7] ? pos[5:4] : (pos[5:4]-2'd1);
    wire [AW-1:0] system_boot_word={1'b0,system_boot_idx[6:4],system_boot_tile,system_boot_idx[3:0]};
    function automatic [7:0] packed_fp8(input [15:0] b);
        reg [7:0] e;
        begin
            e=b[14:7];
            if (e==0) packed_fp8={b[15],7'b0};
            else if (e==118) packed_fp8={b[15],7'd1};
            else if (e==119) packed_fp8={b[15],5'b0,1'b1,b[6]};
            else if (e==120) packed_fp8={b[15],4'b0,1'b1,b[6:5]};
            else packed_fp8={b[15],(e[3:0]-4'd8),b[6:4]};
        end
    endfunction
    ot_hdc_qwen_kv_system #(.W(W),.G(G),.SW(SW),.AW(AW),.NW(NW),
                             .LWIN(SYS_LWIN),.NPC(SYS_NPC),.BK(SYS_BK),
                             .LOG_HD(4),.LOG_TW(2),.LLG(3),.V0_WORD(512)) u_system (
        .clk(clk),.rst_n(rst_n),.tok_start(start),.tok_pos(pos),.cfg_lead(16'd512),
        .kvd_v(kvd_v),.kvd_wbase(kvd_wbase),.kvd_ts(kvd_ts),.kvd_ks(kvd_ks),.kvd_js(kvd_js),
        .kvd_wcs(kvd_wcs),.kvd_split(kvd_split),
        .kvd_jsh(kvd_jsh),.kvd_tiles(kvd_tiles),.kvd_k(kvd_k),.kvd_nout(kvd_nout),
        .kvd_pos(kvd_pos),.kvd_kindk(kvd_kindk),.kv_ok(system_kv_ok),
        .kv_re(kv_re),.kv_raddr(kv_raddr),.kv_q(system_kv_q),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_flush(kv_write_flush),.kv_write_drained(system_drained),
        .boot_v(system_boot_v),.boot_word(system_boot_word),.boot_data(kv_fp8[system_boot_word]),
        .boot_start(1'b0),.boot_busy(),.boot_done(),
        .win_we(system_win_we),.win_waddr(system_win_waddr),.win_wdata(system_win_wdata),
        .win_re(system_win_re),.win_raddr(system_win_raddr),.win_q(system_win_q),
        .bank_we(system_bank_we),.bank_re(system_bank_re),
        .bank_wrow(system_bank_wrow),.bank_rrow(system_bank_rrow),
        .bank_wmask(system_bank_wmask),.bank_wdata(system_bank_wdata),.bank_q(system_bank_q),
        .h_req_v(system_hq_v),.h_req_ready(1'b1),.h_req_we(system_hq_we),
        .h_req_sector(system_hq_sector),.h_req_len(system_hq_len),
        .h_req_tag(system_hq_tag),.h_req_data(system_hq_data),
        .h_rsp_v(system_hr_v),.h_rsp_ready(system_hr_ready),
        .h_rsp_tag(system_hr_tag),.h_rsp_beat(system_hr_beat),.h_rsp_data(system_hr_data),
        .fault(system_fault));
    always @(posedge clk) begin
        system_hr_v<=0;
        if (kvd_v) system_waiting<=1;
        else if (system_kv_ok) system_waiting<=0;
        if (system_waiting && !system_kv_ok) system_wait_cycles<=system_wait_cycles+1;
        if (system_hq_v) begin
            if (system_hq_we) begin
                system_hbm[system_hq_sector] <= system_hq_data;
                system_hbm_writes<=system_hbm_writes+1;
            end
            else begin
                system_hbm_reads<=system_hbm_reads+1;
                system_hr_v[0]<=1;
                system_hr_tag[0 +: SYS_TAGW]<=system_hq_tag;
                system_hr_beat[0 +: SYS_LBK]<=0;
                system_hr_data[0 +: 256]<=system_hbm[system_hq_sector];
            end
        end
        for (integer bg=0;bg<G;bg=bg+1) begin
            if (system_win_re) system_win_q[bg*W*16 +: W*16]<=system_win[bg][system_win_raddr];
            if (system_win_we[bg]) system_win[bg][system_win_waddr[bg*SYS_LWIN +: SYS_LWIN]]
                <=system_win_wdata[bg*W*16 +: W*16];
        end
        for (integer bb=0;bb<2*SW;bb=bb+1) begin
            if (system_bank_re[bb]) system_bank_q[bb*128 +: 128]
                <=system_bank[bb][system_bank_rrow[bb*AW +: AW]];
            if (system_bank_we[bb])
                for (integer by=0;by<16;by=by+1)
                    if (system_bank_wmask[bb*16+by])
                        system_bank[bb][system_bank_wrow[bb*AW +: AW]][by*8 +: 8]
                        =system_bank_wdata[bb*128+by*8 +: 8];
        end
    end
    // Functional physical-write mirror for the vector token gate. The core's
    // normal KV array supplies reads; the bridge independently captures every
    // emitted write through FIFO, E4M3 encoding, tail banks and 32-byte RMW.
    // The terminal check verifies that no core byte was lost under sector stalls.
    localparam integer BV0 = KV_WORDS*W/2;
    localparam integer BLOG_HD = 4, BLOG_TW = 2, BLG_SW = $clog2(SW);
    reg [255:0] bridge_sector [0:KV_WORDS/2-1];
    reg [127:0] bridge_bank [0:2*SW-1][0:255];
    reg [7:0] bridge_expect [0:KV_WORDS*W-1];
    reg bridge_written [0:KV_WORDS*W-1];
    wire [SW*8-1:0] bridge_q;
    wire [2*SW-1:0] bridge_tl_we;
    wire [2*SW*AW-1:0] bridge_tl_row;
    wire [2*SW*16-1:0] bridge_tl_mask;
    wire [2*SW*128-1:0] bridge_tl_data;
    wire bridge_mem_r_v, bridge_mem_w_v;
    wire [AW-1:0] bridge_mem_r_sector, bridge_mem_w_sector;
    wire [255:0] bridge_mem_w_data;
    reg bridge_mem_r_resp_v;
    reg [255:0] bridge_mem_r_resp_data;
    integer bridge_i, bridge_j, bridge_b, bridge_r, bridge_a, bridge_bad;
    initial begin
        for (bridge_i=0;bridge_i<KV_WORDS/2;bridge_i=bridge_i+1) bridge_sector[bridge_i]=0;
        for (bridge_i=0;bridge_i<2*SW;bridge_i=bridge_i+1)
            for (bridge_j=0;bridge_j<256;bridge_j=bridge_j+1) bridge_bank[bridge_i][bridge_j]=0;
        for (bridge_i=0;bridge_i<KV_WORDS*W;bridge_i=bridge_i+1) begin
            bridge_written[bridge_i]=0; bridge_expect[bridge_i]=0;
        end
    end
    generate if (KV_BRIDGE) begin : g_bridge
        for (genvar v=0;v<SW;v=v+1) begin : g_q
            ot_hdc_ingest_fp8q u_q (.f(kv_wdata[v*32 +: 32]), .q(bridge_q[v*8 +: 8]));
        end
        ot_hdc_qwen_kv_vector_bridge #(.SW(SW), .AW(AW), .LOG_HD(BLOG_HD),
                                        .LOG_TW(BLOG_TW), .V0_ELEMENT(BV0),
                                        .FIFO_BEATS(128)) u_bridge (
            .clk(clk), .rst_n(rst_n), .core_we(kv_we), .core_addr(kv_waddr), .core_data(kv_wdata),
            .drained(bridge_drained), .tl_we(bridge_tl_we), .tl_row(bridge_tl_row),
            .tl_mask(bridge_tl_mask), .tl_data(bridge_tl_data),
            .fl_v(1'b0), .fl_ready(), .fl_word_addr('0), .fl_word_data('0),
            .flush(kv_write_flush),
            .mem_r_v(bridge_mem_r_v), .mem_r_ready(1'b1),
            .mem_r_sector(bridge_mem_r_sector), .mem_r_resp_v(bridge_mem_r_resp_v),
            .mem_r_resp_data(bridge_mem_r_resp_data),
            .mem_w_v(bridge_mem_w_v), .mem_w_ready(1'b1),
            .mem_w_sector(bridge_mem_w_sector), .mem_w_data(bridge_mem_w_data),
            .fault(bridge_fault));
        always @(posedge clk) begin
            bridge_mem_r_resp_v <= rst_n && bridge_mem_r_v;
            if (bridge_mem_r_v) bridge_mem_r_resp_data <= bridge_sector[bridge_mem_r_sector];
            if (bridge_mem_w_v) bridge_sector[bridge_mem_w_sector] <= bridge_mem_w_data;
            // Shadow banks are write-only until the terminal check. Apply
            // masked bytes in bank/byte order; no same-cycle read observes them.
            for (integer z=0;z<2*SW;z=z+1) if (bridge_tl_we[z])
                for (integer k=0;k<16;k=k+1) if (bridge_tl_mask[z*16+k])
                    bridge_bank[z][bridge_tl_row[z*AW +: AW]][k*8 +: 8] =
                        bridge_tl_data[z*128+k*8 +: 8];
            for (integer z=0;z<SW;z=z+1) if (kv_we[z]) begin
                bridge_a = kv_waddr[z*AW +: AW];
                bridge_written[bridge_a] = 1'b1;
                bridge_expect[bridge_a] = bridge_q[z*8 +: 8];
            end
        end
    end else begin : g_no_bridge
        assign bridge_drained=1'b1;
        assign bridge_fault=1'b0;
        assign bridge_q='0;
        assign bridge_tl_we='0;
        assign bridge_tl_row='0;
        assign bridge_tl_mask='0;
        assign bridge_tl_data='0;
        assign bridge_mem_r_v=1'b0;
        assign bridge_mem_w_v=1'b0;
        assign bridge_mem_r_sector='0;
        assign bridge_mem_w_sector='0;
        assign bridge_mem_w_data='0;
    end endgenerate
`else
    assign bridge_drained=1'b1;
    assign bridge_fault=1'b0;
`endif

    integer l, q;
`ifdef OT_HDC_MEMSYS
    ot_hdc_memsys #(.W(W), .G(G), .AW(AW), .PAW(PAW)) u_mem (
        .clk(clk),
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
        .vw_mx_we(vw_mx_we), .vw_mx_addr(vw_mx_addr), .vw_mx_mask(vw_mx_mask), .vw_mx_data(vw_mx_data),
        .tst_kv_en(tst_kv_en), .tst_kv_we(tst_kv_we), .tst_kv_waddr(tst_kv_waddr), .tst_kv_wdata(tst_kv_wdata),
        .tst_kv_re(tst_kv_re), .tst_kv_raddr(tst_kv_raddr), .tst_kv_q(tst_kv_q),
        .tst_vm_addr(tst_vm_addr), .tst_vm_q(tst_vm_q),
        .ecc_corrected(ecc_corrected), .ecc_uncorrectable(ecc_uncorrectable),
        .rst_n(rst_n), .bist_start(bist_start), .bist_busy(bist_busy), .bist_done(bist_done), .bist_pass(bist_pass),
        .bist_sram_status(bist_sram_status), .bist_rom_status(bist_rom_status), .bist_exp_sig(bist_exp_sig),
        .rep_scan_en(1'b0), .rep_scan_in(1'b0), .rep_scan_out(rep_scan_out));
    always @(posedge clk) begin
`else
    // synchronous-read memories
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[16:0]];
        for (q = 0; q < SW; q = q + 1)
            if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 12]];
        for (q = 0; q < G; q = q + 1)
            if (kv_re) kv_q_beh[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 10]];
        for (q = 0; q < G; q = q + 1)
            if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 12]];
        for (q = 0; q < SW; q = q + 1) begin
            if (va_re[q]) va_q[32*q +: 32] <= vm[va_addr[q*AW +: 12]];
            if (vb_re[q]) vb_q[32*q +: 32] <= vm[vb_addr[q*AW +: 12]];
            if (vc_re[q]) vc_q[32*q +: 32] <= vm[vc_addr[q*AW +: 12]];
            if (kv_we[q]) kv[kv_waddr[q*AW + 4 +: 10]][32*kv_waddr[q*AW +: 4] +: 32] <= kv_wdata[32*q +: 32];
        end
        // All synchronous VM reads above sample the old array. Apply ME
        // writes here in port order; the later SU/reducer/max writes retain
        // their priority on collisions. Blocking stores also avoid Verilator's
        // delayed-array-write elaboration limit at large G.
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 8], 4'b0} + l] = vw_me_data[32*(q*W + l) +: 32];
        for (q = 0; q < SW; q = q + 1)
            if (vw_su_we[q]) vm[vw_su_addr[q*AW +: 12]] <= vw_su_data[32*q +: 32];
        if (vw_rd_we) vm[vw_rd_addr[11:0]] <= vw_rd_data;
        if (vw_mx_we)
            for (l = 0; l < W; l = l + 1)
                if (vw_mx_mask[l]) vm[{vw_mx_addr[7:0], 4'b0} + l] <= vw_mx_data[32*l +: 32];
`endif
        // the result words of the one unwritten matrix-vector op are the logits
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l]) lg[{me_oaddr[q*AW +: 8], 4'b0} + l] = me_odata[32*(q*W + l) +: 32];
    end

    reg finishing = 1'b0;
    integer dump_i = 0;
`ifdef OT_HDC_MEMSYS
    `define VM_AT(i) u_mem.vm[i]
`else
    `define VM_AT(i) vm[i]
`endif
    reg [8*512-1:0] dir;
    reg [8*1024-1:0] dir_rom;
`ifdef OT_HDC_MEMSYS
`ifdef OT_MEM_FAULTS
    integer fkv_k, fkv_r, fkv_c, fwr_k, fwr_r, fwr_c;
    reg fkv = 1'b0, fwr = 1'b0;
    always @(posedge clk) if (cyc == 1) begin
        if (fkv) begin
            u_mem.g_kvrep[0].g_kvcol[0].u_sram.f_kind[0] = fkv_k[3:0];
            u_mem.g_kvrep[0].g_kvcol[0].u_sram.f_r[0] = fkv_r;
            u_mem.g_kvrep[0].g_kvcol[0].u_sram.f_c[0] = fkv_c;
            $display("FAULT kv kind=%0d row=%0d col=%0d", fkv_k, fkv_r, fkv_c);
        end
        if (fwr) begin
            u_mem.g_wrow[0].g_wcol[0].u_rom.f_kind[0] = fwr_k[3:0];
            u_mem.g_wrow[0].g_wcol[0].u_rom.f_r[0] = fwr_r;
            u_mem.g_wrow[0].g_wcol[0].u_rom.f_c[0] = fwr_c;
            $display("FAULT wrom kind=%0d row=%0d col=%0d", fwr_k, fwr_r, fwr_c);
        end
    end
`endif
`endif
    integer cyc = 0, lc = 0, i, bad_lg, bad_vm, bad_kv;
    reg go = 1'b1;
    reg trace = 1'b0, multi = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0;
    // utilisation counters (per step)
    integer me_busy = 0, su_busy = 0, both_idle = 0, lane_slots = 0;
    always @(posedge clk) if (dut.st != 0) begin
        if (dut.u_me.active) me_busy <= me_busy + 1;
        if (dut.su_active) su_busy <= su_busy + 1;
        if (!dut.u_me.active && !dut.su_active) both_idle <= both_idle + 1;
    end
    reg [31:0] kv_e;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
`ifndef OT_HDC_MEMSYS
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/crom.hex"}, crom);
`endif
        if ($test$plusargs("MULTI")) multi = 1'b1;
`ifdef OT_HDC_MEMSYS
        for (i = 0; i < N_ROM; i = i + 1) exp_sig_mem[i] = 32'd0;
        if ($test$plusargs("BIST")) begin
            bist_en = 1'b1;
            go = 1'b0;
            if ($value$plusargs("OT_ROM_DIR=%s", dir_rom)) $readmemh({dir_rom, "/signatures.hex"}, exp_sig_mem);
        end
`ifdef OT_MEM_FAULTS
        // one stuck cell in KV replica 0 / column tile 0 and one via defect in weight ROM
        // tile r0 c0; applied on the first clock (the macro models clear their slots in
        // their own initial blocks)
        fkv = $value$plusargs("FAULT_KV_KIND=%d", fkv_k) && $value$plusargs("FAULT_KV_ROW=%d", fkv_r)
              && $value$plusargs("FAULT_KV_COL=%d", fkv_c);
        fwr = $value$plusargs("FAULT_WROM_KIND=%d", fwr_k) && $value$plusargs("FAULT_WROM_ROW=%d", fwr_r)
              && $value$plusargs("FAULT_WROM_COL=%d", fwr_c);
`endif
`endif
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = 0;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 0;
        if (multi) begin
            $readmemh({dir, "/prompt.hex"}, prompt);
            $readmemh({dir, "/generated.hex"}, gold_gen);
            for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
        end else
            $readmemh({dir, "/kv.hex"}, kv);
        for (i=0;i<KV_WORDS;i=i+1) begin
            for (integer e=0;e<W;e=e+1)
                kv_fp8[i][e*8 +: 8]=packed_fp8(kv[i][e*32+16 +: 16]);
            system_hbm[i/2][(i%2)*128 +: 128]=kv_fp8[i];
        end
        for (i=0;i<2*SW;i=i+1)
            for (integer br=0;br<16;br=br+1) system_bank[i][br]=0;
        for (i=0;i<G;i=i+1)
            for (integer wr=0;wr<(1<<SYS_LWIN);wr=wr+1) system_win[i][wr]=0;
`ifndef OT_HDC_MEMSYS
        $readmemh({dir, "/prog.hex"}, prog);
`endif
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/expect_kv.hex"}, e_kv);
        $readmemh({dir, "/expect_logits.hex"}, e_lg);
`ifndef OT_HDC_MEMSYS
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
`endif
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (lc < 5 || go) lc <= lc + 1;
        if (lc == 5) rst_n <= 1'b1;
        start <= (lc == START) && (lc < 5 || go);
        if (lc == START - 1 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && lc > START + 2 && done && !start) begin
            total_cycles = total_cycles + cycles;
            if (step >= n_prompt - 1) begin
                $display("STEP pos=%0d in=%0d out=%0d gold=%0d cycles=%0d fault=%0d", pos, token, next_token,
                         gold_gen[step - (n_prompt - 1)], cycles, fault);
                if (next_token != gold_gen[step - (n_prompt - 1)] || fault) gen_bad = gen_bad + 1;
            end
            if (step + 1 == n_prompt + n_gen - 1) begin
                $display("HDC_MULTI steps=%0d generated=%0d mismatches=%0d total_cycles=%0d", step + 1,
                         n_gen, gen_bad, total_cycles);
                if (gen_bad == 0) $display("PASS"); else $display("FAIL");
                $finish;
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
        end
        if (!multi && lc > START + 2 && done && !finishing) begin
`ifdef OT_HDC_MEMSYS
            finishing <= 1'b1;
            dump_i <= 0;
        end
        // KV preload before the token and read-back after it, through the test port
        tst_kv_we <= 1'b0;
        tst_kv_re <= 1'b0;
        if (lc >= 6 && lc < 6 + KV_WORDS) begin
            tst_kv_en <= 1'b1;
            if (!multi) begin
                tst_kv_we <= 1'b1;
                tst_kv_waddr <= lc - 6;
                tst_kv_wdata <= kv[lc - 6];
            end
        end else if (lc == 6 + KV_WORDS) tst_kv_en <= 1'b0;
        // memory self-test (+BIST): runs after reset, before the KV preload and the token
        bist_start <= bist_en && lc == 5 && !bist_started;
        if (bist_start) bist_started <= 1'b1;
        if (bist_started && bist_done && !go) begin
            go <= 1'b1;
            $display("BIST pass=%0d sram_status=%b rom_status=%b bist_cycles=%0d", bist_pass, bist_sram_status,
                     bist_rom_status, cyc - 6);
        end
        // read issued at step i is sampled by the macro one edge later and seen here two later
        if (finishing && dump_i <= KV_WORDS + 1) begin
            tst_kv_en <= 1'b1;
            tst_kv_re <= (dump_i < KV_WORDS);
            tst_kv_raddr <= dump_i;
            if (dump_i >= 2) kv[dump_i - 2] <= tst_kv_q;
            dump_i <= dump_i + 1;
        end
        if (finishing && dump_i == KV_WORDS + 2) begin
`endif
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                bad_lg = bad_lg + 1;
            end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (`VM_AT(i) !== e_vm[i]) begin
                if (bad_vm < 5) $display("vm %0d rtl %h expect %h", i, `VM_AT(i), e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 5) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
            $display("HDC token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, expect_tok, cycles, fault, bad_lg, bad_vm, bad_kv);
            $display("AMAX idx=%0d val=%h", dut.u_me.am_idx, dut.u_me.am_val);
            $display("UTIL me_issue_cycles=%0d su_issue_cycles=%0d both_idle_cycles=%0d", me_busy, su_busy, both_idle);
            $display("KV_SYSTEM fault=%0d drained=%0d hbm_reads=%0d hbm_writes=%0d wait_cycles=%0d",
                     system_fault,system_drained,system_hbm_reads,system_hbm_writes,system_wait_cycles);
`ifdef OT_HDC_MEMSYS
            $display("ROM_ECC corrected=%0d uncorrectable=%0d", ecc_corrected, ecc_uncorrectable);
`endif
`ifndef OT_HDC_MEMSYS
            bridge_bad=0;
            if (KV_BRIDGE) begin
                for (i=0;i<KV_WORDS*W;i=i+1) if (bridge_written[i]) begin
                    if (i < BV0) begin
                        bridge_b = (((i >> 4) >> BLOG_HD) & 1)*SW + ((i >> 4) & (SW-1));
                        bridge_r = (((i >> 4) >> (BLOG_HD+BLOG_TW)) << (BLOG_HD-BLG_SW)) |
                                   (((i >> 4) & ((1 << BLOG_HD)-1)) >> BLG_SW);
                        if (bridge_bank[bridge_b][bridge_r][(i & 15)*8 +: 8] !== bridge_expect[i])
                            bridge_bad=bridge_bad+1;
                    end else if (bridge_sector[i >> 5][(i & 31)*8 +: 8] !== bridge_expect[i])
                        bridge_bad=bridge_bad+1;
                end
                $display("KV_BRIDGE written_byte_mismatches=%0d fault=%0d drained=%0d",
                         bridge_bad, bridge_fault, bridge_drained);
            end
`endif
            if (next_token == expect_tok && !fault && !system_fault && system_drained &&
                bad_lg == 0 && bad_vm == 0 && bad_kv == 0 &&
                (!KV_BRIDGE || (!bridge_fault && bridge_drained && bridge_bad == 0)))
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (trace && (dut.me_go || dut.su_go))
            $display("ISSUE cyc=%0d pc=%0d unit=%0d barrier=%0d", cycles, dut.pc, dut.d_unit, dut.d_barrier);
        if (cyc > 5000000) begin
            $display("TIMEOUT pc=%0d st=%0d me_idle=%0d su_idle=%0d su_ready=%0d inflight=%0d", dut.pc, dut.st,
                     dut.me_idle, dut.su_idle, dut.su_ready, dut.su_inflight);
            $finish;
        end
    end
endmodule
