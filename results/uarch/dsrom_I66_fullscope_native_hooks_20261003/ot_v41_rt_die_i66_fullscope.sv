`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// SIMULATION ONLY (W17 runtime composition of the adopted V4.1 layer die, tools/v41_die_rt.py):
// one layer die of a TP-4 group -- ot_chip_v41x_die FULL_SHAPE = 1 with X_ROM = 1 (every weight op on the ROM
// field through the spine) and the attention engine cut (V41_ATT_CUT) -- whose ROM field (ot_v41_pair,
// ot_v41_retn, ot_v41_ret_root) and attention engine (ot_hdc_v41x_attn) are separately compiled models
// composed by the host (rtl/test/v41_runtime/v41_die_rt.cpp), and whose collective links to the other three
// dies are the host's deterministic-release delay lines (W15: records are released at a fixed latency).
//
// Images (+DIR=<dir>, every file optional; a file that is absent leaves the memory zero):
//   prog.hex crom.hex hbank.hex hrom.hex erom.hex   the tile's ROMs (as tb_chip_v41x_die_smoke)
//   vm_init.hex                                     the tile's vector memory at step start
//   hbm<s>.hex (s = 0..3)                           stack s's K-port sectors (256 bits a line), from sector 0
//   hbmsparse<s>.hex                                "<sector hex> <256-bit hex>" lines (sparse regions: the
//                                                   RoPE table rows of the step's position)
// The ROM-field images are the host's (per-element words and configuration served through DPI).
// ---------------------------------------------------------------------------
module ot_v41_rt_die_i66_fullscope #(
    parameter integer I66_OBSERVE = 0,
    parameter integer RANK = 0,
    parameter integer K_MEM = 1 << 24,
    parameter integer ROM_R = 128,
    parameter integer ROM_PHW = 6,
    parameter integer ROM_SAW = 16,
    parameter integer ROM_BST = 17,
    parameter integer SUN = 256,            // >= 256 at full shape: the SU's span depth L = log2(ceil(n/SUN)) <= LV (7) for
                                            // the hc_post sum of squares over 20,480 (tools/v41_su_legality.py)
    parameter integer SUM = 64,
    parameter integer CL_LANES = 16,
    parameter integer CL_DEPTH = 256,
    parameter integer CL_RELAY = 0,
    parameter integer ROM_FBW = 1 + ROM_PHW + 3 + 1 + 1 + 1 + 8 + 3 + 2 + 256 + 10 + 256 + 10 + 3 + 3 + 1 + 3 + 4 + 32 + 1024,
    parameter integer ROM_FRW = ROM_R * 69,
    parameter integer ATW = 1 + 16 + 1 + 512*16 + 1 + 4 + 4*16*265 + 1 + 1 + 32*16 + 1,
    parameter integer AFW = 4 + 16 + 4 + 4*16*32 + 4*16 + 2 + 8 + 4*16*16*32 + 4*16*16,
    parameter integer CL_PW = 32 * CL_LANES + 3 + 32
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              start,
    input  wire [20:0]       token,
    input  wire [20:0]       pos,
    input  wire [9:0]        user,
    // configuration (the manifest's values; held for the step)
    input  wire [29:0]       cfg_ik_base,
    input  wire              window_region_valid,
    input  wire [29:0]       window_region_base,
    input  wire [29:0]       window_region_count,
    input  wire              window_prime_v,
    output wire              window_prime_ready,
    input  wire [9:0]        window_prime_user,
    input  wire [20:0]       window_prime_row,
    input  wire [1:0]        rope_table_present,
    input  wire [4*30-1:0]   rope_reserved_end,
    input  wire [4*30-1:0]   rope_plain_base,
    input  wire [4*30-1:0]   rope_yarn_base,
    output wire              done,
    output wire [31:0]       cycles,
    output wire [7:0]        fault,
    output wire [4:0]        unit_busy,
    output wire [2:0]        issue_unit,
    output wire [13:0]       dbg_pc,           // the core's program counter (observability only)
    output wire [63:0]       dbg_state,        // {core st, d_unit, idles, coll_busy, waited, cdma busy/mode, e/o valid-ready}
    output wire [31:0]       dbg_words,        // {cdma words_out[15:0], words_in[15:0]}
    output reg  [23:0]       dbg_fs,           // sticky fault sources, one bit each (index map below)
    // ROM field
    output wire [ROM_FBW-1:0] rom_fb,
    input  wire [ROM_FRW-1:0] rom_fr,
    input  wire              rom_ffault,
    // attention engine
    output wire [ATW-1:0]    att_to,
    input  wire [AFW-1:0]    att_from,
    // collective records (TP-4): UCIe to the package peer, T1 board links to the partner package's two dies
    output wire              ucie_ctx_valid,
    input  wire              ucie_ctx_ready,
    output wire [CL_PW-1:0]  ucie_ctx_rec,
    input  wire [1:0]        ucie_ccr_in,
    input  wire              ucie_crx_valid,
    input  wire [CL_PW-1:0]  ucie_crx_rec,
    output wire [1:0]        ucie_ccr_out,
    output wire [1:0]        bl_ctx_valid,
    input  wire [1:0]        bl_ctx_ready,
    output wire [CL_PW-1:0]  bl_ctx_rec,
    input  wire [3:0]        bl_ccr_in,
    input  wire [1:0]        bl_crx_valid,
    input  wire [2*CL_PW-1:0] bl_crx_rec,
    output wire [3:0]        bl_ccr_out
);
    ot_chip_v41x_die #(.FULL_SHAPE(1), .RANK(RANK), .X_ROM(1), .ROM_R(ROM_R), .ROM_PHW(ROM_PHW), .ROM_SAW(ROM_SAW),
                       .ROM_BST(ROM_BST), .X_ATT(1), .X_ME(0), .X_IDX(0), .X_SEL(0), .X_EG(0), .W_HBM(0),
                       .WINDOW_HBM_ATTENTION(1), .K_MEM(K_MEM), .SUN(SUN), .SUM(SUM),
                       .CL_LANES(CL_LANES), .CL_DEPTH(CL_DEPTH), .CL_RELAY(CL_RELAY)) dut (
        .clk(clk), .rst_n(rst_n), .rom_fb(rom_fb), .rom_fr(rom_fr), .rom_ffault(rom_ffault),
        .att_to(att_to), .att_from(att_from),
        .host_mode(1'b1), .host_start(start), .host_token(token), .host_pos(pos), .host_user(user),
        .host_entry(14'd0), .host_prime_v(1'b0), .host_prime_first(1'b0), .host_prime_cid(12'd0),
        .window_region_valid(window_region_valid), .window_region_base(window_region_base),
        .window_region_count(window_region_count), .window_prime_v(window_prime_v),
        .window_prime_ready(window_prime_ready), .window_prime_user(window_prime_user),
        .window_prime_row(window_prime_row),
        .core_done(done), .core_next_token(), .core_next_val(), .core_cycles(cycles), .core_acc_n(),
        .att_packed_desc_v(), .att_packed_desc_accept(), .att_packed_desc_gen(), .att_packed_desc_rows(),
        .att_packed_desc_user(), .att_packed_desc_pos(), .att_packed_desc_tiles(), .att_packed_desc_nout(),
        .att_packed_desc_k(), .att_packed_desc_hg(), .att_packed_desc_mmode(), .att_packed_desc_wbase(),
        .att_packed_desc_ts(), .att_packed_desc_ks(), .att_packed_desc_js(),
        .att_packed_stage_v(1'b0), .att_packed_stage_gen(16'd0), .att_packed_stage_rows(11'd0),
        .att_packed_wrap_drained(1'b0), .att_packed_kv_v(1'b0), .att_packed_kv_ready(), .att_packed_kv_gen(16'd0),
        .att_packed_kv_m(4'd0), .att_packed_kv_w('0), .att_packed_kv_fault(1'b0),
        .att_packed_desc_done(), .att_packed_desc_fault(), .att_packed_desc_fault_code(),
        .cfg_ik_base(cfg_ik_base), .cfg_me_xs(4'd0), .cfg_q_base(30'd0), .cfg_q_lbase('0), .cfg_q_lead(21'd0),
        .cfg_q_rate(16'd0),
        .qr_compact_re(), .qr_compact_addr(), .qr_compact_valid(1'b0), .qr_compact_fp4(1'b0),
        .qr_compact_fp8('0), .qr_compact_fp4_word('0),
        .rope_table_present(rope_table_present), .rope_reserved_end(rope_reserved_end),
        .rope_plain_base(rope_plain_base), .rope_yarn_base(rope_yarn_base),
        .cfg_users('d1), .cfg_prompt_len(21'd0), .cfg_gen_len(21'd0),
        .pr_re(), .pr_user(), .pr_pos(), .pr_q(21'd0),
        .tok_valid(), .tok_user(), .tok_pos(), .tok_id(), .users_done(),
        .rcfg_we(1'b0), .rcfg_dest(8'd0), .rcfg_mask(3'd0),
        .coll_go(1'b0), .coll_mode(1'b0), .coll_tag('0), .coll_src('0), .coll_n('0), .coll_dst('0), .coll_busy(),
        .ucie_tx_valid(), .ucie_tx_ready(1'b1), .ucie_tx_data(), .ucie_tx_last(),
        .ucie_rx_valid(1'b0), .ucie_rx_ready(), .ucie_rx_data(512'd0), .ucie_rx_last(1'b0),
        .ucie_ctx_valid(ucie_ctx_valid), .ucie_ctx_ready(ucie_ctx_ready), .ucie_ctx_rec(ucie_ctx_rec),
        .ucie_ccr_in(ucie_ccr_in), .ucie_crx_valid(ucie_crx_valid), .ucie_crx_rec(ucie_crx_rec),
        .ucie_ccr_out(ucie_ccr_out),
        .ucie_rl_tx_valid(), .ucie_rl_tx_rec(), .ucie_rl_rx_valid(4'd0), .ucie_rl_rx_rec('0),
        .bl_tx_valid(), .bl_tx_ready(1'b1), .bl_tx_data(), .bl_tx_last(),
        .bl_rx_valid(1'b0), .bl_rx_ready(), .bl_rx_data(512'd0), .bl_rx_last(1'b0),
        .bl_ctx_valid(bl_ctx_valid), .bl_ctx_ready(bl_ctx_ready), .bl_ctx_rec(bl_ctx_rec), .bl_ccr_in(bl_ccr_in),
        .bl_crx_valid(bl_crx_valid), .bl_crx_rec(bl_crx_rec), .bl_ccr_out(bl_ccr_out),
        .fault(fault), .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qs_fetched(), .qs_consumed(), .qs_why(), .kb_records(), .kb_writes(), .kb_highwater(), .kb_stalls(),
        .hbm_refreshes(), .hbm_w_reads(), .rtr_drops(), .kv_ops(), .kv_words(), .kv_sectors_written(),
        .kv_refetches(), .kv_wq_high(), .kv_hold_cycles(), .kv_hbm_grants(), .kv_fault_code(),
        .rope_region_ok(), .rope_fault(), .rope_hbm_grants(), .rope_hbm_wait_cycles());

    assign dbg_pc = dut.u_tile.u_core.pc;
    wire [31:0] dbg_faults = {11'd0, dut.u_tile.qrom_rom_fault, dut.u_tile.rope_read_fault, dut.u_tile.idx_user_fault, dut.u_tile.kb_ring_fault,
        dut.u_tile.u_core.coll_fault, dut.u_tile.u_core.rope_pf_fault, dut.u_tile.u_core.win_fault,
        dut.u_tile.u_core.win_capture_fault, dut.u_tile.u_core.rom_fault_w, dut.u_tile.u_core.he_fault,
        dut.u_tile.u_core.xu_fault, dut.u_tile.u_core.qe_fault, dut.u_tile.u_core.su_fault, dut.u_tile.u_core.me_fault,
        dut.u_tile.u_core.e_fault, dut.u_tile.u_core.fuse_orphan, 1'b0};
    // sticky copy of the fault sources (a source may pulse: the core latches the OR)
    reg [31:0] dbg_fsticky;
    always @(posedge clk or negedge rst_n) if (!rst_n) dbg_fsticky <= 32'd0; else dbg_fsticky <= dbg_fsticky | dbg_faults
        | {31'd0, dut.u_tile.u_core.FULL_SHAPE != 0 && dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
           (dut.u_tile.u_core.d_ctl == 3'd5 || dut.u_tile.u_core.d_ctl == 3'd6) && !dut.u_tile.u_core.rope_ctl_ok};
    assign dbg_state = {dbg_fsticky, 4'(dut.u_tile.u_core.st), dut.u_tile.u_core.d_unit, dut.u_tile.u_core.idles,
                        dut.coll_busy, dut.u_tile.u_core.waited, dut.u_cdma.busy, dut.u_cdma.e_mode, dut.u_cdma.fault,
                        dut.e_valid, dut.e_ready, dut.o_valid, dut.o_ready, 7'd0};
    // dbg_fs: 0 me 1 su 2 qe 3 xu 4 he 5 rom 6 coll 7 rope_pf 8 win 9 win_cap 10 qrom 11 rope_read 12 idx_user
    //         13 kb_ring 14..17 e_fault[0..3] 18 fuse_orphan 19 rope ctl 20 key_user(die) 21 core.fault 22 t_fault
    wire [23:0] fs_now;
    assign fs_now[0] = dut.u_tile.u_core.me_fault;
    assign fs_now[1] = dut.u_tile.u_core.su_fault;
    assign fs_now[2] = dut.u_tile.u_core.qe_fault;
    assign fs_now[3] = dut.u_tile.u_core.xu_fault;
    assign fs_now[4] = dut.u_tile.u_core.he_fault;
    assign fs_now[5] = dut.u_tile.u_core.rom_fault_w;
    assign fs_now[6] = dut.u_tile.u_core.coll_fault;
    assign fs_now[7] = dut.u_tile.u_core.rope_pf_fault;
    assign fs_now[8] = dut.u_tile.u_core.win_fault;
    assign fs_now[9] = dut.u_tile.u_core.win_capture_fault;
    assign fs_now[10] = dut.u_tile.qrom_rom_fault;
    assign fs_now[11] = dut.u_tile.rope_read_fault;
    assign fs_now[12] = dut.u_tile.idx_user_fault;
    assign fs_now[13] = dut.u_tile.kb_ring_fault;
    assign fs_now[17:14] = dut.u_tile.u_core.e_fault;
    assign fs_now[18] = dut.u_tile.u_core.fuse_orphan;
    assign fs_now[19] = dut.u_tile.u_core.st == 4'd6 && dut.u_tile.u_core.d_unit == 3'd0 &&
                        (dut.u_tile.u_core.d_ctl == 3'd5 || dut.u_tile.u_core.d_ctl == 3'd6) && !dut.u_tile.u_core.rope_ctl_ok;
    assign fs_now[20] = dut.key_user_fault;
    assign fs_now[21] = dut.u_tile.u_core.fault;
    assign fs_now[22] = dut.t_fault;
    assign fs_now[23] = 1'b0;
    always @(posedge clk or negedge rst_n) if (!rst_n) dbg_fs <= 24'd0; else dbg_fs <= dbg_fs | fs_now;
    assign dbg_words = {dut.u_cdma.words_out[15:0], dut.u_cdma.words_in[15:0]};
    // ---- images ---------------------------------------------------------------------------------------
    string dir;
    integer fd, i;
    reg [255:0] sw;
    reg [31:0] sa;
    function automatic bit exists(input string f);
        integer h;
        begin
            h = $fopen(f, "r");
            exists = h != 0;
            if (h != 0) $fclose(h);
        end
    endfunction
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (exists({dir, "/prog.hex"})) $readmemh({dir, "/prog.hex"}, dut.u_tile.prog);
        if (exists({dir, "/crom.hex"})) $readmemh({dir, "/crom.hex"}, dut.u_tile.crom);
        if (exists({dir, "/hbank.hex"})) $readmemh({dir, "/hbank.hex"}, dut.u_tile.hbank);
        if (exists({dir, "/hrom.hex"})) $readmemh({dir, "/hrom.hex"}, dut.u_tile.hrom);
        if (exists({dir, "/erom.hex"})) $readmemh({dir, "/erom.hex"}, dut.u_tile.erom);
        if (exists({dir, "/vm_init.hex"})) $readmemh({dir, "/vm_init.hex"}, dut.u_tile.vm);
        if (exists({dir, "/hbm0.hex"})) $readmemh({dir, "/hbm0.hex"}, dut.g_hbm[0].u_hbm.u_k.mem);
        if (exists({dir, "/hbm1.hex"})) $readmemh({dir, "/hbm1.hex"}, dut.g_hbm[1].u_hbm.u_k.mem);
        if (exists({dir, "/hbm2.hex"})) $readmemh({dir, "/hbm2.hex"}, dut.g_hbm[2].u_hbm.u_k.mem);
        if (exists({dir, "/hbm3.hex"})) $readmemh({dir, "/hbm3.hex"}, dut.g_hbm[3].u_hbm.u_k.mem);
        fd = $fopen({dir, "/hbmsparse0.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[0].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse1.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[1].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse2.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[2].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/hbmsparse3.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[3].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        // indexed layers: the compressed rows this die owns, '<sector> <word>' on stack k (ckv_s<k>.hex)
        fd = $fopen({dir, "/ckv_s0.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[0].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s1.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[1].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s2.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[2].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
        fd = $fopen({dir, "/ckv_s3.hex"}, "r");
        if (fd != 0) begin while ($fscanf(fd, "%h %h\n", sa, sw) == 2) dut.g_hbm[3].u_hbm.u_k.mem[sa] = sw; $fclose(fd); end
    end
    // final vector memory dump on request (the host calls it through DPI export)
    export "DPI-C" function v41rt_vm_word;
    import "DPI-C" context function void v41rt_die_register(input int rank);
    initial v41rt_die_register(RANK);
    function int v41rt_vm_word(input int a);
        v41rt_vm_word = dut.u_tile.vm[a];
    endfunction
// I66_PASSIVE_OBSERVER_BEGIN
// Simulation observation only. No drives, forces or provider completion flags.
    generate if (I66_OBSERVE != 0) begin : g_i66_passive
        longint unsigned i66_edge = 0;
        // Count every clock including reset; never reuse an edge across reset epochs.
        always @(posedge clk) i66_edge <= i66_edge + 1;
        initial if (ROM_PHW != 10 || ROM_R != 128 || ROM_FBW != 1632 || SUN != 256)
            $fatal(1, "I66 observer requires exact full PHW10/SUN256 binding");
        always @(posedge clk) begin
        if (1) $display("I66FULLHOOK pre %0d %0d edge rst_n=%h pc=%h st=%h unit=%h wait_mask=%h skip=%h waited=%h unit_ready=%h q_gate=%h kv_gate=%h m0_gate=%h idles=%h gos=%h coll_busy=%h faults=%h user10=%h writer_mask=%h", i66_edge, RANK, rst_n, dut.u_tile.u_core.pc, dut.u_tile.u_core.st, dut.u_tile.u_core.d_unit, dut.u_tile.u_core.d_wait, dut.u_tile.u_core.d_skip, dut.u_tile.u_core.waited, dut.u_tile.u_core.unit_ready, dut.u_tile.u_core.q_gate, dut.u_tile.u_core.kv_gate, dut.u_tile.u_core.m0_gate, dut.u_tile.u_core.idles, dut.u_tile.u_core.gos, dut.coll_busy, dbg_fs, user, {(|dut.u_tile.ww_h_we),(|dut.u_tile.rom_we),(|dut.u_tile.vw_me_we),(|dut.u_tile.vw_su_we),(|dut.u_tile.vw_rd_we),(|dut.u_tile.xs_vm_we),(|dut.u_tile.xs_res_we),(|dut.u_tile.vw_xe_we),(|dut.u_tile.ww_q_we),(|dut.u_tile.ww_x_we),(|dut.u_tile.xa_we),(|dut.u_tile.xb_we4)});
        if (dut.u_tile.u_core.st == 6) $display("I66FULLHOOK pre %0d %0d issue_sample pc=%h unit=%h qe_mode=%h word=%h", i66_edge, RANK, dut.u_tile.u_core.pc, dut.u_tile.u_core.d_unit, dut.u_tile.u_core.qe_mode, dut.u_tile.u_core.ir);
        if (rst_n && dut.u_tile.u_core.rom_q_go && dut.u_tile.u_core.g_rom.u_radapt.st == 0) $display("I66FULLHOOK pre %0d %0d rom_accept pc=%h key=%h stride=%h indexed=%h ibase=%h obase=%h", i66_edge, RANK, dut.u_tile.u_core.pc, dut.u_tile.u_core.qe_wbase, dut.u_tile.u_core.qe_istride, dut.u_tile.u_core.qe_ind, dut.u_tile.u_core.qe_ibase, dut.u_tile.u_core.qe_obase);
        if (1) $display("I66FULLHOOK pre %0d %0d adapter st=%h s_go=%h s_idle=%h s_ready=%h key=%h hit=%h phase=%h vi_re=%h vi_addr=%h vi_q=%h fault=%h", i66_edge, RANK, dut.u_tile.u_core.g_rom.u_radapt.st, dut.u_tile.u_core.g_rom.s_go, dut.u_tile.u_core.g_rom.s_idle, dut.u_tile.u_core.g_rom.s_ready, dut.u_tile.u_core.g_rom.u_radapt.key, dut.u_tile.u_core.g_rom.u_radapt.hit, dut.u_tile.u_core.g_rom.s_ph, dut.u_tile.u_core.g_rom.u_radapt.vi_re, dut.u_tile.u_core.g_rom.u_radapt.vi_addr, dut.u_tile.u_core.g_rom.u_radapt.vi_q, dut.u_tile.u_core.g_rom.u_radapt.fault);
        if (rst_n && dut.u_tile.u_core.su_go && !dut.u_tile.u_core.g_su_x.u_su.pend) $display("I66FULLHOOK pre %0d %0d SU_front pc=%h seq=%h abase=%h cbase=%h", i66_edge, RANK, dut.u_tile.u_core.pc, dut.u_tile.u_core.g_su_x.u_su.seq, dut.u_tile.u_core.a_base, dut.u_tile.u_core.c_base);
        if (rst_n && dut.u_tile.u_core.g_su_x.u_su.v_acc) $display("I66FULLHOOK pre %0d %0d vector_accept seq=%h copy=%h abase=%h cbase=%h", i66_edge, RANK, dut.u_tile.u_core.g_su_x.u_su.seq, dut.u_tile.u_core.g_su_x.u_su.cp, dut.u_tile.u_core.g_su_x.u_su.abase, dut.u_tile.u_core.g_su_x.u_su.cbase);
        if (rst_n && dut.u_tile.u_core.g_su_x.u_su.u_vec.vx) $display("I66FULLHOOK pre %0d %0d Xtag cw=%h cw_width=%h", i66_edge, RANK, dut.u_tile.u_core.g_su_x.u_su.u_vec.cwx, $bits(dut.u_tile.u_core.g_su_x.u_su.u_vec.cwx));
        if (rst_n && (|dut.u_tile.ww_h_we)) $display("I66FULLHOOK pre %0d %0d writer_ww_h ww_h_we=%h ww_h_addr=%h ww_h_mask=%h ww_h_data=%h", i66_edge, RANK, dut.u_tile.ww_h_we, dut.u_tile.ww_h_addr, dut.u_tile.ww_h_mask, dut.u_tile.ww_h_data);
        if (rst_n && (|dut.u_tile.rom_we)) $display("I66FULLHOOK pre %0d %0d writer_rom rom_we=%h rom_waddr=%h rom_wdata=%h", i66_edge, RANK, dut.u_tile.rom_we, dut.u_tile.rom_waddr, dut.u_tile.rom_wdata);
        if (rst_n && (|dut.u_tile.vw_me_we)) $display("I66FULLHOOK pre %0d %0d writer_vw_me vw_me_we=%h vw_me_addr=%h vw_me_mask=%h vw_me_data=%h", i66_edge, RANK, dut.u_tile.vw_me_we, dut.u_tile.vw_me_addr, dut.u_tile.vw_me_mask, dut.u_tile.vw_me_data);
        if (rst_n && (|dut.u_tile.vw_su_we)) $display("I66FULLHOOK pre %0d %0d writer_vw_su vw_su_we=%h vw_su_addr=%h vw_su_data=%h", i66_edge, RANK, dut.u_tile.vw_su_we, dut.u_tile.vw_su_addr, dut.u_tile.vw_su_data);
        if (rst_n && (|dut.u_tile.vw_rd_we)) $display("I66FULLHOOK pre %0d %0d writer_vw_rd vw_rd_we=%h vw_rd_addr=%h vw_rd_data=%h", i66_edge, RANK, dut.u_tile.vw_rd_we, dut.u_tile.vw_rd_addr, dut.u_tile.vw_rd_data);
        if (rst_n && (|dut.u_tile.xs_vm_we)) $display("I66FULLHOOK pre %0d %0d writer_xs_vm xs_vm_we=%h xs_vm_waddr=%h xs_vm_wdata=%h", i66_edge, RANK, dut.u_tile.xs_vm_we, dut.u_tile.xs_vm_waddr, dut.u_tile.xs_vm_wdata);
        if (rst_n && (|dut.u_tile.xs_res_we)) $display("I66FULLHOOK pre %0d %0d writer_xs_res xs_res_we=%h xs_res_addr=%h xs_res_data=%h", i66_edge, RANK, dut.u_tile.xs_res_we, dut.u_tile.xs_res_addr, dut.u_tile.xs_res_data);
        if (rst_n && (|dut.u_tile.vw_xe_we)) $display("I66FULLHOOK pre %0d %0d writer_vw_xe vw_xe_we=%h vw_xe_addr=%h vw_xe_data=%h", i66_edge, RANK, dut.u_tile.vw_xe_we, dut.u_tile.vw_xe_addr, dut.u_tile.vw_xe_data);
        if (rst_n && (|dut.u_tile.ww_q_we)) $display("I66FULLHOOK pre %0d %0d writer_ww_q ww_q_we=%h ww_q_addr=%h ww_q_mask=%h ww_q_data=%h", i66_edge, RANK, dut.u_tile.ww_q_we, dut.u_tile.ww_q_addr, dut.u_tile.ww_q_mask, dut.u_tile.ww_q_data);
        if (rst_n && (|dut.u_tile.ww_x_we)) $display("I66FULLHOOK pre %0d %0d writer_ww_x ww_x_we=%h ww_x_addr=%h ww_x_mask=%h ww_x_data=%h", i66_edge, RANK, dut.u_tile.ww_x_we, dut.u_tile.ww_x_addr, dut.u_tile.ww_x_mask, dut.u_tile.ww_x_data);
        if (rst_n && (|dut.u_tile.xa_we)) $display("I66FULLHOOK pre %0d %0d writer_xa xa_we=%h xa_waddr=%h xa_wdata=%h", i66_edge, RANK, dut.u_tile.xa_we, dut.u_tile.xa_waddr, dut.u_tile.xa_wdata);
        if (rst_n && (|dut.u_tile.xb_we4)) $display("I66FULLHOOK pre %0d %0d writer_xb xb_we4=%h xb_waddr4=%h xb_wdata4=%h", i66_edge, RANK, dut.u_tile.xb_we4, dut.u_tile.xb_waddr4, dut.u_tile.xb_wdata4);
        end
        for (genvar r = 0; r < ROM_R; r = r + 1) begin : g_pub
            reg [29:0] saved_addr;
            longint unsigned saved_edge;
            always @(posedge clk) if (rst_n && dut.u_tile.rom_we[r]) begin
                saved_addr = dut.u_tile.rom_waddr[r*30 +: 30];
                saved_edge = i66_edge;
                // $strobe executes after NBA. Full address is logged to reject VM19 alias.
                $strobe("I66FULLHOOK post %0d %0d VM root=%h address=%h value=%h",
                        saved_edge, RANK, r, saved_addr, dut.u_tile.vm[saved_addr[18:0]]);
            end
        end
        for (genvar p = 0; p < 4*SUN; p = p + 1) begin : g_read
            always @(posedge clk) if (rst_n && dut.u_tile.xs_rd_re[p] && dut.u_tile.xs_rd_src[p*2 +: 2] == 0)
                $display("I66FULLHOOK pre %0d %0d read port=%h src=%h address=%h value=%h",
                    i66_edge, RANK, p, dut.u_tile.xs_rd_src[p*2 +: 2],
                    dut.u_tile.xs_rd_addr[p*30 +: 30],
                    dut.u_tile.vm[dut.u_tile.xs_rd_addr[p*30 +: 19]]);
        end
        // All PCs and pipeline tails remain observable; never stop at PC105.
        longint unsigned saved_retire_edge;
        reg [7:0] saved_retire_seq;
        always @(posedge clk) begin
        if (1) $display("I66FULLHOOK pre %0d %0d clock rst_n=%h sim_time_ns=%h", i66_edge, RANK, rst_n, $time);
        if (rst_n && dut.u_tile.u_core.su_go && !dut.u_tile.u_core.g_su_x.u_su.pend) $display("I66FULLHOOK pre %0d %0d SU_shape pc=%h seq=%h nin=%h nout=%h m=%h asrc=%h csrc=%h abase=%h cbase=%h aso=%h asi=%h cso=%h csi=%h cpair=%h", i66_edge, RANK, dut.u_tile.u_core.pc, dut.u_tile.u_core.g_su_x.u_su.seq, dut.u_tile.u_core.su_nin, dut.u_tile.u_core.su_nout, dut.u_tile.u_core.mx_m, dut.u_tile.u_core.a_src, dut.u_tile.u_core.c_src, dut.u_tile.u_core.a_base, dut.u_tile.u_core.c_base, dut.u_tile.u_core.a_so, dut.u_tile.u_core.a_si, dut.u_tile.u_core.c_so, dut.u_tile.u_core.c_si, dut.u_tile.u_core.c_pair);
        if (rst_n && dut.u_tile.u_core.g_su_x.u_su.v_acc) $display("I66FULLHOOK pre %0d %0d vector_shape seq=%h copy=%h nin=%h nout=%h m=%h asrc=%h csrc=%h abase=%h cbase=%h xo=%h", i66_edge, RANK, dut.u_tile.u_core.g_su_x.u_su.seq, dut.u_tile.u_core.g_su_x.u_su.cp, dut.u_tile.u_core.g_su_x.u_su.nin, dut.u_tile.u_core.g_su_x.u_su.nout, dut.u_tile.u_core.g_su_x.u_su.m_r, dut.u_tile.u_core.g_su_x.u_su.asrc, dut.u_tile.u_core.g_su_x.u_su.csrc, dut.u_tile.u_core.g_su_x.u_su.abase, dut.u_tile.u_core.g_su_x.u_su.cbase, dut.u_tile.u_core.g_su_x.u_su.xo);
        if (rst_n && dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p) $display("I66FULLHOOK pre %0d %0d vector_retire seq=%h last=%h fault=%h", i66_edge, RANK, dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_seq, dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_last, dut.u_tile.u_core.su_fault);
            if (rst_n && dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p &&
                       dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_last) begin
                saved_retire_edge = i66_edge;
                saved_retire_seq = dut.u_tile.u_core.g_su_x.u_su.u_vec.ret_p_seq;
                $strobe("I66FULLHOOK post %0d %0d vector_done seq=%h cr_dseq=%h",
                    saved_retire_edge, RANK, saved_retire_seq, dut.u_tile.u_core.g_su_x.u_su.u_vec.cr_dseq);
            end
        end
        for (genvar s = 0; s < ROM_R; s = s + 1) begin : g_roots
            always @(posedge clk) if (rst_n && dut.u_tile.u_core.g_rom.r_v[s])
                $display("I66FULLHOOK pre %0d %0d root_sample root=%h row=%h pos=%h fp32=%h bf16=%h error=%h",
                    i66_edge, RANK, s, dut.u_tile.u_core.g_rom.r_row[s*16 +: 16],
                    dut.u_tile.u_core.g_rom.r_pos[s*3 +: 3], dut.u_tile.u_core.g_rom.r_fp32[s*32 +: 32],
                    dut.u_tile.u_core.g_rom.r_bf16[s*16 +: 16], dut.u_tile.u_core.g_rom.r_e[s]);
        end
    end endgenerate
// I66_PASSIVE_OBSERVER_END
endmodule
