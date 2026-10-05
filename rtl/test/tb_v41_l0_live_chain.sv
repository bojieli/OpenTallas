`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Live L0 attention chain through the V4.1 layer die (rtl/chip/ot_chip_v41x_die.sv)
// at FULL_SHAPE with the opt-in WINDOW HBM attention source.  Driven by
// tools/v41_l0_live_chain.py (images) and rtl/test/tb_v41_l0_live_chain_harness.cpp.
//
// The die runs in host mode.  Images (+DIR=...):
//   prog.hex         the production L0 attention words (PC24, 30..34, END)
//   vm_init.hex      q heads at 55744 (sparse, @address records)
//   crom.hex         per-head sink in the constant ROM low word at 12128
//   hbm_window.hex   the packed FP8 window ring of user 0: slot*17 + sector
//   expect_vm.hex    the golden's whole vector memory after the chain
// The window rows reach HBM stack WIN_STACK's K array through the hierarchy
// (DRAM contents), then the host primes their absolute row tags through the
// die's window_prime port; every row the attention engine consumes is read
// by the die's WINDOW source through the real K arbiter and HBM3E timing
// model.  Nothing is replayed between operations: the scores, probabilities
// and PV accumulator move only through the tile's vector memory.
//
// Reports: ISSUE (per program word), UNIT (busy intervals), WIN (source
// counters), STALL (attribution) and the whole-VM verdict.
// ---------------------------------------------------------------------------
module tb_v41_l0_live_chain #(
    parameter integer CREDITS = 8,
    parameter integer STREAM_II1 = 1,
    parameter integer RETAIN = 1,
    parameter integer XHE = 0, XME = 0, XIDX = 0, XSEL = 0, XEG = 0,
    parameter integer VM_AW = 19,
    parameter integer WIN_STACK = 0
) (input wire clk);
    localparam integer K_HAW = 30, NW = 21, AW = 30;
    localparam integer K_MEM = 1 << 19;
    localparam integer WIN_BASE = 1 << 18, WIN_COUNT = 128 * 17;
    localparam integer VM_ELEMS = 1 << VM_AW;
    localparam integer PW = 512 + 3 + 32;

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] pos = 127;
    reg prime_v = 1'b0;
    reg [NW-1:0] prime_row = 0;
    wire prime_ready;
    wire done;
    wire [NW-1:0] next_token;
    wire [31:0] next_val, cycles;
    wire [7:0] fault;
    wire [4:0] unit_busy; wire [2:0] issue_unit;

    ot_chip_v41x_die #(.FULL_SHAPE(1), .RANK(0), .K_MEM(K_MEM), .VM_AW(VM_AW), .WIN_STACK(WIN_STACK),
                       .WINDOW_HBM_ATTENTION(1), .WINDOW_RETAIN_L0(RETAIN),
                       .WINDOW_REFILL_CREDITS(CREDITS), .WINDOW_STREAM_II1(STREAM_II1),
                       .X_HE(XHE), .X_ME(XME), .X_IDX(XIDX), .X_SEL(XSEL), .X_EG(XEG)) dut (
        .clk(clk), .rst_n(rst_n),
        .host_mode(1'b1), .host_start(start), .host_token(21'd0), .host_pos(pos), .host_user(10'd0),
        .host_entry(14'd0), .host_prime_v(1'b0), .host_prime_first(1'b0), .host_prime_cid(12'd0),
        .window_region_valid(1'b1), .window_region_base(K_HAW'(WIN_BASE)), .window_region_count(K_HAW'(WIN_COUNT)),
        .window_prime_v(prime_v), .window_prime_ready(prime_ready), .window_prime_user(10'd0),
        .window_prime_row(prime_row),
        .core_done(done), .core_next_token(next_token), .core_next_val(next_val), .core_cycles(cycles),
        .core_acc_n(),
        .att_packed_desc_v(), .att_packed_desc_accept(), .att_packed_desc_gen(), .att_packed_desc_rows(),
        .att_packed_desc_user(), .att_packed_desc_pos(), .att_packed_desc_tiles(), .att_packed_desc_nout(),
        .att_packed_desc_k(), .att_packed_desc_hg(), .att_packed_desc_mmode(), .att_packed_desc_wbase(),
        .att_packed_desc_ts(), .att_packed_desc_ks(), .att_packed_desc_js(),
        .att_packed_stage_v(1'b0), .att_packed_stage_gen(16'd0), .att_packed_stage_rows(11'd0),
        .att_packed_wrap_drained(1'b1), .att_packed_kv_v(1'b0), .att_packed_kv_ready(),
        .att_packed_kv_gen(16'd0), .att_packed_kv_m(4'd0), .att_packed_kv_w('0), .att_packed_kv_fault(1'b0),
        .att_packed_desc_done(), .att_packed_desc_fault(), .att_packed_desc_fault_code(),
        .cfg_ik_base(AW'(1) << 29), .cfg_me_xs(4'd0), .cfg_q_base('0), .cfg_q_lbase('0),
        .cfg_q_lead(21'd512), .cfg_q_rate(16'd0),
        .qr_compact_re(), .qr_compact_addr(), .qr_compact_valid(1'b0), .qr_compact_fp4(1'b0),
        .qr_compact_fp8('0), .qr_compact_fp4_word('0),
        .rope_table_present(2'b00), .rope_reserved_end({4{K_HAW'(K_MEM)}}),
        .rope_plain_base('0), .rope_yarn_base('0),
        .cfg_users('d1), .cfg_prompt_len('0), .cfg_gen_len('0),
        .pr_re(), .pr_user(), .pr_pos(), .pr_q('0),
        .tok_valid(), .tok_user(), .tok_pos(), .tok_id(), .users_done(),
        .rcfg_we(1'b0), .rcfg_dest(8'd0), .rcfg_mask(3'd0),
        .coll_go(1'b0), .coll_mode(1'b0), .coll_tag('0), .coll_src('0), .coll_n('0), .coll_dst('0),
        .coll_busy(),
        .ucie_tx_valid(), .ucie_tx_ready(1'b1), .ucie_tx_data(), .ucie_tx_last(),
        .ucie_rx_valid(1'b0), .ucie_rx_ready(), .ucie_rx_data(512'd0), .ucie_rx_last(1'b0),
        .ucie_ctx_valid(), .ucie_ctx_ready(1'b1), .ucie_ctx_rec(), .ucie_ccr_in(2'b00),
        .ucie_crx_valid(1'b0), .ucie_crx_rec('0), .ucie_ccr_out(),
        .ucie_rl_tx_valid(), .ucie_rl_tx_rec(), .ucie_rl_rx_valid('0), .ucie_rl_rx_rec('0),
        .bl_tx_valid(), .bl_tx_ready(1'b1), .bl_tx_data(), .bl_tx_last(),
        .bl_rx_valid(1'b0), .bl_rx_ready(), .bl_rx_data(512'd0), .bl_rx_last(1'b0),
        .bl_ctx_valid(), .bl_ctx_ready(2'b11), .bl_ctx_rec(), .bl_ccr_in(4'd0),
        .bl_crx_valid(2'b00), .bl_crx_rec('0), .bl_ccr_out(),
        .fault(fault), .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qs_fetched(), .qs_consumed(), .qs_why(),
        .kb_records(), .kb_writes(), .kb_highwater(), .kb_stalls(),
        .hbm_refreshes(), .hbm_w_reads(), .rtr_drops(),
        .kv_ops(), .kv_words(), .kv_sectors_written(), .kv_refetches(),
        .kv_wq_high(), .kv_hold_cycles(), .kv_hbm_grants(), .kv_fault_code(),
        .rope_region_ok(), .rope_fault(), .rope_hbm_grants(), .rope_hbm_wait_cycles());

    // -- images --------------------------------------------------------------------------------
    reg [31:0]  e_vm [0:VM_ELEMS-1];
    reg [255:0] win [0:WIN_COUNT-1];
    reg [8*512-1:0] dir;
    integer i;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("POS=%d", pos)) pos = 127;
        for (i = 0; i < VM_ELEMS; i = i + 1) begin dut.u_tile.vm[i] = 32'd0; e_vm[i] = 32'd0; end
        $readmemh({dir, "/prog.hex"}, dut.u_tile.prog);
        $readmemh({dir, "/crom.hex"}, dut.u_tile.crom);
        $readmemh({dir, "/vm_init.hex"}, dut.u_tile.vm);
        $readmemh({dir, "/expect_vm.hex"}, e_vm);
        $readmemh({dir, "/hbm_window.hex"}, win);
    end
    reg hbm_loaded = 1'b0;
    always @(posedge clk) if (!hbm_loaded) begin
        for (i = 0; i < WIN_COUNT; i = i + 1) dut.g_hbm[WIN_STACK].u_hbm.u_k.mem[WIN_BASE + i] = win[i];
        hbm_loaded = 1'b1;
    end

    // -- sequencing: reset, prime the 128 absolute row tags, start ------------------------------
    integer cyc = 0, primed = 0, start_cyc = -1;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1'b1;
        if (cyc == 15) prime_row <= pos - NW'(127);
        if (cyc >= 16 && primed < 128) begin
            if (prime_v && prime_ready) begin
                primed <= primed + 1; prime_row <= prime_row + 1'b1; prime_v <= (primed + 1 < 128);
            end else prime_v <= 1'b1;
        end
        start <= 1'b0;
        if (primed == 128 && start_cyc < 0) begin start <= 1'b1; start_cyc <= cyc; end
    end

    // -- observation ----------------------------------------------------------------------------
    // Issue of each program word, unit busy intervals, window source counters and stall attribution.
    `define CORE dut.u_tile.u_core
    `define SRC  dut.g_packed_kv.g_window_hbm_attention.u_source
    integer n_issue = 0;
    reg [4:0] busy_q = 0;
    integer busy_start [0:4];
    integer att_hold = 0, dec_hold = 0, beat_stall_src = 0, beat_stall_eng = 0, beats = 0;
    integer staged_at = -1, first_beat = -1, last_beat = -1, su_busy = 0, me_busy = 0;
    integer hbm_req = 0, hbm_req_stall = 0, hbm_rsp = 0;
    always @(posedge clk) if (start_cyc >= 0) begin
        if (issue_unit != 0) begin
            $display("ISSUE n=%0d cyc=%0d core_cycles=%0d pc=%0d unit=%0d", n_issue, cyc - start_cyc, cycles,
                     `CORE.pc, issue_unit);
            n_issue <= n_issue + 1;
        end
        busy_q <= unit_busy;
        for (i = 0; i < 5; i = i + 1) begin
            if (unit_busy[i] && !busy_q[i]) busy_start[i] = cyc - start_cyc;
            if (!unit_busy[i] && busy_q[i])
                $display("UNIT u=%0d start=%0d end=%0d", i, busy_start[i], cyc - start_cyc);
        end
        if (unit_busy[0]) me_busy <= me_busy + 1;
        if (unit_busy[1]) su_busy <= su_busy + 1;
        // an attention-class op decoded and ready but held for kv_ok (the window service)
        if (`CORE.st == 4'd6 && !`CORE.d_skip && `CORE.d_unit == 3'd1 && `CORE.waited &&
            `CORE.unit_ready && !`CORE.kv_gate) att_hold <= att_hold + 1;
        if (`CORE.st == 4'd5 && !(`CORE.win_idle)) dec_hold <= dec_hold + 1;
        if (dut.win_service_staged && staged_at < 0) staged_at <= cyc - start_cyc;
        if (dut.tile_packed_v && dut.tile_packed_ready) begin
            beats <= beats + 1; last_beat <= cyc - start_cyc;
            if (first_beat < 0) first_beat <= cyc - start_cyc;
        end
        if (dut.tile_packed_v && !dut.tile_packed_ready) beat_stall_eng <= beat_stall_eng + 1;
        if (!dut.tile_packed_v && `CORE.e_go[2] == 1'b0 && `CORE.me_own == 2'd2 && !`CORE.e_idle[2] &&
            dut.tile_packed_ready) beat_stall_src <= beat_stall_src + 1;
        if (`SRC.m_v[WIN_STACK] && `SRC.m_rdy[WIN_STACK]) hbm_req <= hbm_req + 1;
        if (`SRC.m_v[WIN_STACK] && !`SRC.m_rdy[WIN_STACK]) hbm_req_stall <= hbm_req_stall + 1;
        if (`SRC.s_v[WIN_STACK] && `SRC.s_rdy[WIN_STACK]) hbm_rsp <= hbm_rsp + 1;
    end

    // -- verdict --------------------------------------------------------------------------------
    integer bad_vm, drain = 0, first_bad = -1;
    always @(posedge clk) begin
        if (start_cyc >= 0 && cyc > start_cyc + 4 && done && drain == 0) drain <= 1;
        if (drain != 0 && drain < 64) drain <= drain + 1;
        if (drain == 64) begin
            bad_vm = 0;
            for (i = 0; i < VM_ELEMS; i = i + 1) if (dut.u_tile.vm[i] !== e_vm[i]) begin
                if (bad_vm < 12) $display("VMBAD addr=%0d rtl=%h expect=%h", i, dut.u_tile.vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            $display("WIN staged=%0d first_beat=%0d last_beat=%0d beats=%0d sectors_read=%0d rows_fetched=%0d hbm_req=%0d hbm_req_stall=%0d hbm_rsp=%0d",
                     staged_at, first_beat, last_beat, beats, `SRC.sectors_read, `SRC.rows_fetched,
                     hbm_req, hbm_req_stall, hbm_rsp);
            $display("STALL att_kv_hold=%0d dec_win_hold=%0d beat_engine_backpressure=%0d beat_source_empty=%0d me_busy=%0d su_busy=%0d",
                     att_hold, dec_hold, beat_stall_eng, beat_stall_src, me_busy, su_busy);
            $display("L0LIVE pos=%0d core_cycles=%0d wall=%0d fault=%b core_fault=%0d vm_mismatch=%0d issues=%0d",
                     pos, cycles, cyc - start_cyc, fault, fault[0], bad_vm, n_issue);
            if (fault == 8'd0 && bad_vm == 0 && n_issue == 6) $display("PASS"); else $display("FAIL");
            $finish;
        end
        if (cyc > 2000000) begin
            $display("TIMEOUT pc=%0d st=%0d fault=%b primed=%0d", `CORE.pc, `CORE.st, fault, primed);
            $display("FAIL");
            $finish;
        end
    end
endmodule
