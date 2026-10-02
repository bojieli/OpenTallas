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
module ot_v41_rt_die_I66_observation_only #(
    parameter integer SIM_OBSERVE_I66 = 0, // simulation hooks; off by default

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
// BEGIN I66 SIMULATION OBSERVER
    // synthesis translate_off
    // No engine writes, delayed evals, new hardware ports or transport ACKs.
    // Simulation sequence is correlation only; it is not a DUT generation.
    generate if (SIM_OBSERVE_I66 != 0) begin : g_i66_observer
        longint unsigned obs_edge = 0;
        longint unsigned obs_sequence = 0;
        reg [ROM_R-1:0] pending_we = '0;
        reg [ROM_R*30-1:0] pending_addr = '0;
        reg [ROM_R*32-1:0] pending_data = '0;
        reg [3:0] cdma_we = '0;
        reg [4*15-1:0] cdma_addr = '0;
        reg [4*512-1:0] cdma_data = '0;
        integer port_i, post_i, lane_i;
        initial if (ROM_PHW != 10 || ROM_R != 128 || ROM_BST != 17 || ROM_FBW != 1632)
            $fatal(1, "I66 observer requires enrolled PHW10/R128/BST17/FBW1632");
        always @(posedge clk) begin
            obs_edge = obs_edge + 1;
            pending_we = '0;
            cdma_we = '0;
            if (dut.u_tile.u_core.rst_n) begin
                if (dut.u_tile.u_core.pc == 14'd66)
                    $display("I66_OBS core_pre edge=%0d rank=%0d token=%0d user=%0d pos=%0d pc=%0d st=%0d unit=%0d d_wait=%0h waited=%0d unit_ready=%0d q_gate=%0d kv_gate=%0d m0_gate=%0d win_admit=%0d qe_go=%0d rom_q_go=%0d rom_ready=%0d rom_idle=%0d coll_busy=%0d fs=%0h d_skip=%0d qe_mode=%0d coll_fault=%0d rope_pf_fault=%0d", obs_edge, RANK, token, user, pos,
                        dut.u_tile.u_core.pc, dut.u_tile.u_core.st, dut.u_tile.u_core.d_unit,
                        dut.u_tile.u_core.d_wait, dut.u_tile.u_core.waited, dut.u_tile.u_core.unit_ready,
                        dut.u_tile.u_core.q_gate, dut.u_tile.u_core.kv_gate, dut.u_tile.u_core.m0_gate,
                        dut.u_tile.u_core.win_admit, dut.u_tile.u_core.qe_go, dut.u_tile.u_core.rom_q_go,
                        dut.u_tile.u_core.rom_ready_w, dut.u_tile.u_core.rom_idle_w, dut.coll_busy, dbg_fs,
                        dut.u_tile.u_core.d_skip, dut.u_tile.u_core.qe_mode, dut.u_tile.u_core.coll_fault, dut.u_tile.u_core.rope_pf_fault);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 0 && (dut.u_tile.u_core.rom_q_go || dut.u_tile.u_core.rom_m_go)) begin
                    obs_sequence = obs_sequence + 1;
                    $display("I66_OBS ROM_accept edge=%0d rank=%0d sequence=%0d pc=%0d is_QE=%0d indexed=%0d base=%0d stride=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.pc, dut.u_tile.u_core.rom_q_go,
                        dut.u_tile.u_core.rom_q_go && dut.u_tile.u_core.qe_ind,
                        dut.u_tile.u_core.rom_q_go ? dut.u_tile.u_core.qe_wbase : dut.u_tile.u_core.me_wbase,
                        dut.u_tile.u_core.rom_q_go ? dut.u_tile.u_core.qe_istride : 30'd0);
                end
                if (dut.u_tile.rom_vre)
                    $display("I66_OBS EID_read edge=%0d rank=%0d sequence=%0d address=%0d", obs_edge, RANK, obs_sequence, dut.u_tile.rom_vaddr);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 2)
                    $display("I66_OBS EID_sample edge=%0d rank=%0d sequence=%0d value=%0d", obs_edge, RANK, obs_sequence, dut.u_tile.rom_vq);
                if (dut.u_tile.u_core.g_rom.u_radapt.st == 3)
                    $display("I66_OBS key_lookup edge=%0d rank=%0d sequence=%0d key=%0d hit=%0d phase=%0d word=%0h fault=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.g_rom.u_radapt.key, dut.u_tile.u_core.g_rom.u_radapt.hit,
                        dut.u_tile.u_core.g_rom.u_radapt.hit_p,
                        dut.u_tile.u_core.g_rom.u_radapt.keyrom[dut.u_tile.u_core.g_rom.u_radapt.hit_p],
                        dut.u_tile.u_core.g_rom.u_radapt.fault);
                if (dut.u_tile.u_core.g_rom.u_spine.st == 0 && dut.u_tile.u_core.g_rom.s_go)
                    $display("I66_OBS phase_accept edge=%0d rank=%0d sequence=%0d phase=%0d fault=%0d", obs_edge, RANK, obs_sequence,
                        dut.u_tile.u_core.g_rom.s_ph, dut.u_tile.u_core.g_rom.u_radapt.fault);
                if (dut.u_tile.rom_xre)
                    $display("I66_OBS input_read edge=%0d rank=%0d sequence=%0d address=%0d elems=64", obs_edge, RANK, obs_sequence, dut.u_tile.rom_xaddr);
                if (dut.u_tile.u_core.g_rom.u_spine.f_cfg_go || dut.u_tile.u_core.g_rom.u_spine.f_go ||
                    dut.u_tile.u_core.g_rom.u_spine.f_go_bf || dut.u_tile.u_core.g_rom.u_spine.f_xs_v ||
                    dut.u_tile.u_core.g_rom.u_spine.f_xb_v)
                    $display("I66_OBS broadcast_sample edge=%0d rank=%0d sequence=%0d bus=%0h", obs_edge, RANK, obs_sequence, rom_fb);
                $display("I66_OBS source_state edge=%0d rank=%0d sequence=%0d adapter_st=%0d spine_st=%0d rows_left=%0d ld_run=%0d sm_run=%0d fault=%0d", obs_edge, RANK, obs_sequence,
                    dut.u_tile.u_core.g_rom.u_radapt.st, dut.u_tile.u_core.g_rom.u_spine.st,
                    dut.u_tile.u_core.g_rom.u_spine.rows_left, dut.u_tile.u_core.g_rom.u_spine.ld_run,
                    dut.u_tile.u_core.g_rom.u_spine.sm_run, dut.u_tile.u_core.rom_fault_w);
                pending_we = dut.u_tile.rom_we;
                pending_addr = dut.u_tile.rom_waddr;
                pending_data = dut.u_tile.rom_wdata;
                cdma_we = dut.u_tile.xb_we4;
                cdma_addr = dut.u_tile.xb_waddr4;
                cdma_data = dut.u_tile.xb_wdata4;
                if (|cdma_we || dut.u_cdma.busy)
                    $display("I66_OBS CDMA_pre edge=%0d rank=%0d writes=%0h addresses=%0h busy=%0d mode=%0d topk=%0d tr_done=%0d commit_wait=%0d tk_done=%0d fault=%0d", obs_edge, RANK,
                        cdma_we, cdma_addr, dut.u_cdma.busy, dut.u_cdma.e_mode, dut.u_cdma.tk_r,
                        dut.u_cdma.tr_done, dut.u_cdma.commit_wait, dut.u_cdma.tk_done, dut.u_cdma.fault);
                for (port_i = 0; port_i < ROM_R; port_i = port_i + 1) begin
                    if (rom_fr[port_i*69+68])
                        $display("I66_OBS root_sample edge=%0d rank=%0d sequence=%0d port=%0d record=%0h", obs_edge, RANK, obs_sequence, port_i, rom_fr[port_i*69 +: 69]);
                    if (pending_we[port_i])
                        $display("I66_OBS VM_write_accept edge=%0d rank=%0d sequence=%0d port=%0d address=%0d data=%0h", obs_edge, RANK, obs_sequence, port_i,
                            pending_addr[port_i*30 +: 30], pending_data[port_i*32 +: 32]);
                end
            end
        end
        // Observe after NBA, without #delay or altering the host clock/eval loop.
        // Equality is a checked local snapshot, not an interstage provider ACK.
        always @(negedge clk) begin
            for (post_i = 0; post_i < ROM_R; post_i = post_i + 1)
                if (pending_we[post_i])
                    $display("I66_OBS VM_postNBA edge=%0d rank=%0d sequence=%0d port=%0d address=%0d expected=%0h actual=%0h", obs_edge, RANK, obs_sequence, post_i,
                        pending_addr[post_i*30 +: 30], pending_data[post_i*32 +: 32],
                        dut.u_tile.vm[pending_addr[post_i*30 +: 19]]);
            for (post_i = 0; post_i < 4; post_i = post_i + 1)
                if (cdma_we[post_i])
                    for (lane_i = 0; lane_i < 16; lane_i = lane_i + 1)
                        $display("I66_OBS CDMA_VM_postNBA edge=%0d rank=%0d port=%0d lane=%0d expected=%0h actual=%0h busy=%0d fault=%0d", obs_edge, RANK, post_i, lane_i,
                            cdma_data[post_i*512+lane_i*32 +: 32],
                            dut.u_tile.vm[{cdma_addr[post_i*15 +: 15], 4'(lane_i)}], dut.u_cdma.busy, dut.u_cdma.fault);
        end
    end endgenerate
    // synthesis translate_on
// END I66 SIMULATION OBSERVER
endmodule
