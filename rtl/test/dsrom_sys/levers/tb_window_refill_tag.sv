`timescale 1ns/1ps
// Lever item 2 bench: WINDOW_REFILL_CREDITS=8 refill tags across epoch 512 through the real owner mux.
//
// Five arms receive the SAME stimulus every cycle (prime row r, then prefetch row r, N_REFILL times, r = i % 128),
// each arm = prefetch -> ot_chip_v41x_kv_rope_reqmux (the outer KV/RoPE owner mux that admits a WINDOW request
// only with owner bits 15:14 == 00, inner kv_reqmux included) -> its own identical bounded out-of-order memory:
//   A  original ot_chip_v41x_window_kv_prefetch, REFILL_CREDITS 8           (the hazard)
//   B  successor ot_dsrom_window_kv_prefetch_lv, REFILL_CREDITS 8, EPOCH_SAFE 1   (the fix)
//   C  successor, REFILL_CREDITS 8, EPOCH_SAFE 0 (default)                 (must equal A every cycle, hazard included)
//   E  original, REFILL_CREDITS 1 (die default)
//   F  successor, all parameters default                                  (must equal E every cycle)
// Checks: every staged row of B (and of A, E before their end) equals the memory image bit for bit; B equals A on
// every observed port every cycle until A's 512th refill; A stalls there with the mux's sticky fault (owner tag
// 0x4000); B completes all refills with no fault and its epoch wraps 511 -> 0; C == A and F == E on every cycle.
// The driver is paced by arm B (A is past its last refill once it hangs; its inputs keep the shared values).
module tb_window_refill_tag #(parameter integer N_REFILL = 600);
    localparam integer HAW = 30, TAGW = 16, BASE = 64, COUNT = 128*17, NA = 5;
    reg clk = 0; always #2 clk = ~clk;
    reg rst_n = 0;
    reg prime_v = 0, prefetch_v = 0;
    reg [20:0] prime_row = 0, prefetch_row = 0;
    integer cycle = 0;
    reg stale_mode = 0, stale_injected = 0;
    integer refill_i = 0;
    initial stale_mode = $test$plusargs("STALE_AT_WRAP");
    // per-arm wires
    wire [NA-1:0] prime_ready, prefetch_ready, kv_ok, pf_fault, mux_fault, packed_valid;
    wire [4223:0] packed_row [0:NA-1];
    wire [31:0] rows_fetched [0:NA-1];
    wire [3:0] m_v [0:NA-1];
    wire [4*HAW-1:0] m_addr [0:NA-1];
    wire [4*TAGW-1:0] m_tag [0:NA-1];
    wire [4*TAGW-1:0] w_tag [0:NA-1];
    wire [3:0] w_v [0:NA-1];

    function automatic [255:0] sector_data(input integer addr);
        reg [255:0] d;
        begin
            d = 0;
            for (integer n = 0; n < 32; n = n + 1) d[8*n +: 8] = 8'(1 + ((addr*7 + n) % 100));
            sector_data = d;
        end
    endfunction

    genvar a;
    generate for (a = 0; a < NA; a = a + 1) begin : g_arm
        // arm parameters
        localparam integer CRED = (a == 3 || a == 4) ? 1 : 8;
        wire [3:0] pm_v, pm_rdy, pm_we, pm_wr_done, ps_v, ps_rdy;
        wire [4*HAW-1:0] pm_addr; wire [15:0] pm_len; wire [4*TAGW-1:0] pm_tag, ps_tag;
        wire [1023:0] pm_wdata, ps_data; wire [127:0] pm_wstrb; wire [15:0] ps_beat;
        // mux master side
        wire [3:0] mm_v, mm_rdy, mm_we, mm_wr_done, ms_v, ms_rdy;
        wire [4*HAW-1:0] mm_addr; wire [15:0] mm_len; wire [4*TAGW-1:0] mm_tag;
        wire [1023:0] mm_wdata; wire [127:0] mm_wstrb;
        reg [4*TAGW-1:0] ms_tag = 0; reg [1023:0] ms_data = 0; reg [3:0] ms_vr = 0;
        assign ms_v = ms_vr;
        wire [31:0] st_rows, st_blk, st_srd, st_swr; wire [4:0] fcode; wire [31:0] q_unused;
        wire brv; wire [3:0] brm, brvm; wire [9:0] bru; wire [20:0] brf; wire [4*4224-1:0] brr; wire brfault, brr_ready;
        wire [255:0] pcodes; wire [7:0] pscale;
        if (a == 0 || a == 3) begin : g_orig
            ot_chip_v41x_window_kv_prefetch #(.WIN_STACK(0), .REFILL_CREDITS(CRED)) u_pf (
                .clk(clk), .rst_n(rst_n), .region_base_sector(30'(BASE)), .region_sector_count(30'(COUNT)),
                .prime_v(prime_v), .prime_ready(prime_ready[a]), .prime_user(10'd0), .prime_row(prime_row),
                .blk_v(1'b0), .blk_ready(), .blk_user(10'd0), .blk_row(21'd0), .blk_idx(4'd0), .blk_codes(256'd0),
                .blk_scale(8'd0), .prefetch_v(prefetch_v), .prefetch_ready(prefetch_ready[a]),
                .prefetch_user(10'd0), .prefetch_row(prefetch_row), .kv_ok(kv_ok[a]),
                .re(1'b0), .ruser(10'd0), .rrow(21'd0), .relem(9'd0), .q(q_unused),
                .packed_re(1'b0), .packed_ruser(10'd0), .packed_rrow(prefetch_row), .packed_ridx(4'd0),
                .packed_valid(packed_valid[a]), .packed_row(packed_row[a]), .packed_codes(pcodes), .packed_scale(pscale),
                .bank_req_v(1'b0), .bank_req_ready(brr_ready), .bank_req_user(10'd0), .bank_req_first(21'd0),
                .bank_req_mask(4'd0), .bank_rsp_v(brv), .bank_rsp_user(bru), .bank_rsp_first(brf), .bank_rsp_mask(brm),
                .bank_rsp_valid_mask(brvm), .bank_rsp_rows(brr), .bank_rsp_fault(brfault),
                .fault(pf_fault[a]), .fault_code(fcode), .st_rows_fetched(st_rows), .st_blocks_written(st_blk),
                .st_sectors_read(st_srd), .st_sectors_written(st_swr),
                .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len), .m_tag(pm_tag), .m_we(pm_we),
                .m_wdata(pm_wdata), .m_wstrb(pm_wstrb), .m_wr_done(pm_wr_done), .s_v(ps_v), .s_rdy(ps_rdy),
                .s_tag(ps_tag), .s_beat(ps_beat), .s_data(ps_data));
        end else begin : g_succ
            ot_dsrom_window_kv_prefetch_lv #(.WIN_STACK(0), .REFILL_CREDITS(CRED), .EPOCH_SAFE(a == 1)) u_pf (
                .clk(clk), .rst_n(rst_n), .region_base_sector(30'(BASE)), .region_sector_count(30'(COUNT)),
                .prime_v(prime_v), .prime_ready(prime_ready[a]), .prime_user(10'd0), .prime_row(prime_row),
                .blk_v(1'b0), .blk_ready(), .blk_user(10'd0), .blk_row(21'd0), .blk_idx(4'd0), .blk_codes(256'd0),
                .blk_scale(8'd0), .prefetch_v(prefetch_v), .prefetch_ready(prefetch_ready[a]),
                .prefetch_user(10'd0), .prefetch_row(prefetch_row), .kv_ok(kv_ok[a]),
                .re(1'b0), .ruser(10'd0), .rrow(21'd0), .relem(9'd0), .q(q_unused),
                .packed_re(1'b0), .packed_ruser(10'd0), .packed_rrow(prefetch_row), .packed_ridx(4'd0),
                .packed_valid(packed_valid[a]), .packed_row(packed_row[a]), .packed_codes(pcodes), .packed_scale(pscale),
                .bank_req_v(1'b0), .bank_req_ready(brr_ready), .bank_req_user(10'd0), .bank_req_first(21'd0),
                .bank_req_mask(4'd0), .bank_rsp_v(brv), .bank_rsp_user(bru), .bank_rsp_first(brf), .bank_rsp_mask(brm),
                .bank_rsp_valid_mask(brvm), .bank_rsp_rows(brr), .bank_rsp_fault(brfault),
                .fault(pf_fault[a]), .fault_code(fcode), .st_rows_fetched(st_rows), .st_blocks_written(st_blk),
                .st_sectors_read(st_srd), .st_sectors_written(st_swr),
                .m_v(pm_v), .m_rdy(pm_rdy), .m_addr(pm_addr), .m_len(pm_len), .m_tag(pm_tag), .m_we(pm_we),
                .m_wdata(pm_wdata), .m_wstrb(pm_wstrb), .m_wr_done(pm_wr_done), .s_v(ps_v), .s_rdy(ps_rdy),
                .s_tag(ps_tag), .s_beat(ps_beat), .s_data(ps_data));
        end
        assign rows_fetched[a] = st_rows;
        assign w_tag[a] = pm_tag; assign w_v[a] = pm_v;
        wire mf; wire [31:0] rg, rw;
        ot_chip_v41x_kv_rope_reqmux #(.HAW(HAW), .TAGW(TAGW)) u_mux (
            .clk(clk), .rst_n(rst_n),
            .w_v(pm_v), .w_rdy(pm_rdy), .w_addr(pm_addr), .w_len(pm_len), .w_tag(pm_tag), .w_we(pm_we),
            .w_wdata(pm_wdata), .w_wstrb(pm_wstrb), .w_wr_done(pm_wr_done), .w_sv(ps_v), .w_srdy(ps_rdy),
            .w_stag(ps_tag), .w_sbeat(ps_beat), .w_sdata(ps_data),
            .c_v(4'd0), .c_rdy(), .c_addr({4*HAW{1'b0}}), .c_len(16'd0), .c_tag({4*TAGW{1'b0}}), .c_we(4'd0), .c_wdata(1024'd0), .c_wstrb(128'd0),
            .c_wr_done(), .c_sv(), .c_srdy(4'hf), .c_stag(), .c_sbeat(), .c_sdata(),
            .p_v(4'd0), .p_rdy(), .p_addr({4*HAW{1'b0}}), .p_len(16'd0), .p_tag({4*TAGW{1'b0}}), .p_we(4'd0), .p_wdata(1024'd0), .p_wstrb(128'd0),
            .p_wr_done(), .p_sv(), .p_srdy(4'hf), .p_stag(), .p_sbeat(), .p_sdata(),
            .m_v(mm_v), .m_rdy(mm_rdy), .m_addr(mm_addr), .m_len(mm_len), .m_tag(mm_tag), .m_we(mm_we),
            .m_wdata(mm_wdata), .m_wstrb(mm_wstrb), .m_wr_done(mm_wr_done), .s_v(ms_v), .s_rdy(ms_rdy),
            .s_tag(ms_tag), .s_beat(16'd0), .s_data(ms_data), .fault(mf), .rope_grants(rg), .rope_wait_cycles(rw));
        assign mux_fault[a] = mf;
        assign m_v[a] = mm_v; assign m_addr[a] = mm_addr; assign m_tag[a] = mm_tag;
        // bounded out-of-order memory on stack 0: 8 slots, deterministic latency per request index
        reg qa [0:7]; integer qdue [0:7], qaddr [0:7]; reg [TAGW-1:0] qtag [0:7];
        integer nreq = 0, pend = 0, ch, fs;
        initial for (integer j = 0; j < 8; j = j + 1) qa[j] = 0;
        assign mm_rdy = {3'b0, pend < 8};
        assign mm_wr_done = 4'd0;
        always @(posedge clk) begin
            ms_vr <= 0;
            ch = -1;
            for (integer j = 0; j < 8; j = j + 1) if (qa[j] && qdue[j] <= cycle) ch = j;   // last ready wins: OOO
            if (ch >= 0) begin
                qa[ch] = 0;
                ms_vr[0] <= 1'b1; ms_tag[0 +: TAGW] <= qtag[ch]; ms_data[0 +: 256] <= sector_data(qaddr[ch]);
                // +STALE_AT_WRAP: the first reply of B's 512th refill (epoch wrapped to 0) carries epoch 511's tag
                if (a == 1 && stale_mode && refill_i == 511 && !stale_injected) begin
                    ms_tag[0 +: TAGW] <= {2'b00, 9'd511, qtag[ch][4:0]}; stale_injected = 1;
                end
            end
            if (rst_n && mm_v[0] && mm_rdy[0]) begin
                if (mm_we[0] || mm_len[3:0] != 1 || mm_addr[0 +: HAW] < BASE || mm_addr[0 +: HAW] >= BASE + COUNT)
                    $fatal(1, "arm %0d: bad memory request", a);
                fs = -1;
                for (integer j = 7; j >= 0; j = j - 1) if (!qa[j]) fs = j;
                qa[fs] = 1; qdue[fs] = cycle + 2 + ((nreq * 7) % 13); qaddr[fs] = mm_addr[0 +: HAW];
                qtag[fs] = mm_tag[0 +: TAGW]; nreq = nreq + 1;
            end
            pend = 0;
            for (integer j = 0; j < 8; j = j + 1) pend = pend + integer'(qa[j]);
        end
    end endgenerate

    // expected staged row of absolute row r (user 0)
    function automatic [4223:0] expect_row(input integer r);
        reg [4223:0] e;
        integer sbase;
        begin
            e = 0; sbase = BASE + (r % 128) * 17;
            for (integer s = 0; s < 16; s = s + 1) e[256*s +: 256] = sector_data(sbase + s);
            e[4096 +: 128] = sector_data(sbase + 16);
            expect_row = e;
        end
    endfunction

    // per-cycle equivalence monitors
    integer ab_first_diff = -1, ab_first_diff_refill = -1, ca_diffs = 0, fe_diffs = 0;
    integer a_fault_cycle = -1, a_bad_tag = -1, b_wrap_seen = 0;
    function automatic [4*30+4*16+4+1+1+1+1+32-1:0] obs(input integer k);
        obs = {m_v[k], m_addr[k], m_tag[k], prefetch_ready[k], kv_ok[k], pf_fault[k], mux_fault[k], rows_fetched[k]};
    endfunction
    always @(posedge clk) if (rst_n) begin
        cycle <= cycle + 1;
        if (obs(0) !== obs(2) || packed_row[0] !== packed_row[2] || packed_valid[0] !== packed_valid[2]) ca_diffs <= ca_diffs + 1;
        if (obs(3) !== obs(4) || packed_row[3] !== packed_row[4] || packed_valid[3] !== packed_valid[4]) fe_diffs <= fe_diffs + 1;
        if (ab_first_diff < 0 && (obs(0) !== obs(1) || packed_row[0] !== packed_row[1])) begin
            ab_first_diff <= cycle; ab_first_diff_refill <= refill_i;
            $display("AB_FIRST_DIFF cycle=%0d refill=%0d a_wtag=%h b_wtag=%h a_mv=%0d b_mv=%0d", cycle, refill_i,
                     w_tag[0][15:0], w_tag[1][15:0], m_v[0][0], m_v[1][0]);
        end
        if (a_fault_cycle < 0 && mux_fault[0]) begin a_fault_cycle <= cycle; a_bad_tag <= w_tag[0][15:0]; end
        if (stale_mode && stale_injected && pf_fault[1]) begin
            repeat (16) begin @(negedge clk); if (kv_ok[1] || (m_v[1] != 0)) $fatal(1, "publication or request after stale reject"); end
            $display("STALE_AT_WRAP_REJECTED refill=%0d b_rows=%0d", refill_i, rows_fetched[1]); $finish;
        end
        if ((pf_fault[1] && !stale_mode) || mux_fault[1] || pf_fault[3] || mux_fault[3]) $fatal(1, "fault in a healthy arm at refill %0d pf=%b mux=%b", refill_i, pf_fault, mux_fault);
        if (w_v[1][0] && w_tag[1][15:14] != 2'b00) $fatal(1, "successor emitted an owner bit");
    end

    integer t0;
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; @(negedge clk);
        for (refill_i = 0; refill_i < N_REFILL; refill_i = refill_i + 1) begin
            while (!prime_ready[1]) @(negedge clk);
            prime_v = 1; prime_row = 21'(refill_i % 128); @(negedge clk); prime_v = 0;
            while (!prefetch_ready[1] || !prefetch_ready[3]) @(negedge clk);
            prefetch_v = 1; prefetch_row = 21'(refill_i % 128); t0 = cycle; @(negedge clk); prefetch_v = 0;
            // wait for both B (credits 8) and E (credits 1) to stage the row; record their cycles
            while (!(kv_ok[1] && kv_ok[3])) @(negedge clk);
            if (packed_row[1] !== expect_row(refill_i) || !packed_valid[1]) $fatal(1, "B row mismatch refill %0d", refill_i);
            if (packed_row[3] !== expect_row(refill_i) || !packed_valid[3]) $fatal(1, "E row mismatch refill %0d", refill_i);
            if (refill_i < 511 && (packed_row[0] !== expect_row(refill_i) || !packed_valid[0]))
                $fatal(1, "A row mismatch refill %0d", refill_i);
            if (refill_i == 511 || refill_i == 512)
                $display("B_EPOCH refill=%0d epoch=%0d", refill_i, g_arm[1].g_succ.u_pf.refill_epoch);
            if (refill_i == 511 && g_arm[1].g_succ.u_pf.refill_epoch == 0) b_wrap_seen = 1;
        end
        repeat (40) @(negedge clk);
        $display("RESULT refills=%0d a_rows=%0d b_rows=%0d e_rows=%0d a_mux_fault=%0d a_fault_cycle=%0d a_bad_tag=%h a_pf_state_stuck=%0d ab_first_diff=%0d ab_first_diff_refill=%0d ca_diffs=%0d fe_diffs=%0d b_fault=%0d b_wrap=%0d b_epoch_end=%0d cycles=%0d",
                 N_REFILL, rows_fetched[0], rows_fetched[1], rows_fetched[3], mux_fault[0], a_fault_cycle, a_bad_tag,
                 !prefetch_ready[0], ab_first_diff, ab_first_diff_refill, ca_diffs, fe_diffs, pf_fault[1] | mux_fault[1],
                 b_wrap_seen, g_arm[1].g_succ.u_pf.refill_epoch, cycle);
        $finish;
    end
    // cycles per refill (B credits 8 vs E credits 1), measured from prefetch accept to staged
    integer sb = 0, se = 0, nb = 0, ne = 0, tb_start = 0;
    reg pb = 0, pe = 0;
    always @(posedge clk) if (rst_n) begin
        if (prefetch_v && prefetch_ready[1]) begin tb_start <= cycle; pb <= 1; pe <= 1; end
        if (pb && kv_ok[1] && !(prefetch_v)) begin sb <= sb + (cycle - tb_start); nb <= nb + 1; pb <= 0; end
        if (pe && kv_ok[3] && !(prefetch_v)) begin se <= se + (cycle - tb_start); ne <= ne + 1; pe <= 0; end
    end
    final $display("REFILL_CYCLES b_credits8_total=%0d b_n=%0d e_credits1_total=%0d e_n=%0d", sb, nb, se, ne);
    initial begin #20000000; $fatal(1, "timeout"); end
endmodule
