`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// DS-ROM integration checkpoint, vehicle (a): ONE re-index stage of one rank (die) at full shape,
// every adopted flag on, verify positions issued back to back by the wavefront package
// controller (rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv, WAVE = 1, WIN = 6, NW = 21, the S81
// stage's XWORDS = 1 control message) into ot_dsrom_reindex_chain (candidate-block gather on
// four timed HBM3E stacks -> scorer -> mask-drop -> top-512 select).
//
// The stage's controller receives HIDDEN messages for positions P0, P0+1, ... (the user is
// already at P0: the controller's expected-position register is preset, labelled below), starts
// the chain on each, and forwards the HIDDEN message when the chain's selection is complete.
// The candidate lists of ALL jobs are written before the first job starts (the wavefront case:
// L20's lists of the positions behind arrive before L24 consumes the first), each into slot
// pos mod 2^LSW (LSW = 0: the as-built single list).
//
// SCORER STAND-IN (labelled): the index scorer is not in this vehicle.  A per-stack elastic
// pipe of the measured idx-array latency (LAT, results/rtl/w11_idx_array.json) returns each key
// beat with the golden BF16 index score of each lane's position (+SC<j>=file: one 16-bit word per
// position of the rank).  The key bits themselves are checked against the gather bench's HBM
// pattern (every key of every beat), so the gather is verified under the select's back-pressure.
//
// Checked per job and quarter: the selection (position, BF16 value, -inf flag, order) against
// +EX<j>=prefix (.exp<q>: "S n" then n "pos bits ninf" lines, tools/hdc_golden_v41
// topk_lowest_index on that job's MASKED scores).  Prints JOB / HANDOFF lines and PASS / FAIL.
// ---------------------------------------------------------------------------
module tb_dsrom_integ_reindex_wf #(
    parameter integer NJOBS = 2,
    parameter integer LSW = 3,
    parameter integer MDROP = 1,
    parameter integer LAT = 48,              // scorer stand-in latency (idx array)
    parameter integer SETTLE = 24,           // query settle before the first key is scored
    parameter integer BASE = 123, BSTEP = 777, OSTEP = 8,
    parameter integer MAX_CYCLES = 400000,
    parameter integer CLK_PS = 833,
    parameter longint REFI_PS = 3900000
) (input wire clk);
    localparam integer Q = 4, NPC = 32, AW = 28, HW = 20, TAGW = 16, LENW = 4, BEATW = 4, DW = 256;
    localparam integer LBW = 14, LMW = 11, IW = 20, K = 512, KW = $clog2(K + 1), NW = 21;
    localparam integer SLW = (LSW > 0) ? LSW : 1;
    localparam integer PER_RANK = 262144, PER_STACK = 65536;
    localparam integer FLIT = 512, VWA = 8;
    reg rst_n = 1'b0;
    // run-time: the rank (die) and the first job's position (+RANK=, +P0=)
    integer RANK = 0, P0 = 1048574;
    initial begin
        if (!$value$plusargs("RANK=%d", RANK)) RANK = 0;
        if (!$value$plusargs("P0=%d", P0)) P0 = 1048574;
    end

    // ---------------------------------------------------------------- HBM stacks
    wire [Q*NPC-1:0] h_req_v, h_req_rdy, h_rsp_v, h_rsp_rdy;
    wire [Q*NPC*AW-1:0] h_req_addr;
    wire [Q*NPC*LENW-1:0] h_req_len;
    wire [Q*NPC*TAGW-1:0] h_req_tag, h_rsp_tag;
    wire [Q*NPC*BEATW-1:0] h_rsp_beat;
    wire [Q*NPC*DW-1:0] h_rsp_data;
    genvar gs;
    generate for (gs = 0; gs < Q; gs = gs + 1) begin : g_hbm
        ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .DW(DW), .MEM_WORDS(1), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW),
            .QD(64), .RQD(32), .RW(16), .MAXSKIP(16), .CLK_PS(CLK_PS), .REFPB(3), .REFI_PS(REFI_PS), .MEM_MODE(1)) hm (
            .clk(clk), .rst_n(rst_n), .req_v(h_req_v[gs*NPC +: NPC]), .req_rdy(h_req_rdy[gs*NPC +: NPC]),
            .req_addr(h_req_addr[gs*NPC*AW +: NPC*AW]), .req_len(h_req_len[gs*NPC*LENW +: NPC*LENW]),
            .req_tag(h_req_tag[gs*NPC*TAGW +: NPC*TAGW]), .req_we({NPC{1'b0}}), .req_wdata({NPC*DW{1'b0}}),
            .req_wstrb({NPC*32{1'b0}}), .wr_done(),
            .rsp_v(h_rsp_v[gs*NPC +: NPC]), .rsp_rdy(h_rsp_rdy[gs*NPC +: NPC]),
            .rsp_tag(h_rsp_tag[gs*NPC*TAGW +: NPC*TAGW]), .rsp_beat(h_rsp_beat[gs*NPC*BEATW +: NPC*BEATW]),
            .rsp_data(h_rsp_data[gs*NPC*DW +: NPC*DW]));
    end endgenerate

    // ---------------------------------------------------------------- chain
    reg  [Q-1:0] lw_v = 0;
    reg  [SLW-1:0] lw_slot = 0;
    reg  [LMW-1:0] lw_addr = 0;
    reg  [Q*LBW-1:0] lw_blk = 0;
    wire c_start;
    reg  [SLW-1:0] c_slot;
    reg  [IW-1:0] c_pos;
    reg  [Q*HW-1:0] c_base;
    reg  [Q*10-1:0] c_skip;
    reg  [Q*(LMW+1)-1:0] c_n;
    reg  [Q*IW-1:0] c_qb;
    wire c_done, c_busy, c_fault, c_ovf, c_short;
    wire [3:0] c_passes;
    wire [Q-1:0] ks_valid, ks_last, sc_ready, out_valid, out_last;
    reg  [Q-1:0] ks_ready, sc_valid, sc_last;
    wire [Q*16-1:0] ks_lv, out_lv, out_ninf;
    wire [Q*16*544-1:0] ks_key;
    wire [Q*16*IW-1:0] ks_idx, out_idx;
    reg  [Q*16-1:0] sc_lv;
    reg  [Q*16*16-1:0] sc_val;
    reg  [Q*16*IW-1:0] sc_idx;
    wire [Q*16*16-1:0] out_val;
    wire [Q*48-1:0] c_keys, c_beats;
    ot_dsrom_reindex_chain #(.Q(Q), .NPC(NPC), .AW(AW), .HW(HW), .TAGW(TAGW), .LENW(LENW), .BEATW(BEATW), .DW(DW),
        .LBW(LBW), .LMW(LMW), .LSW(LSW), .IW(IW), .K(K), .MDROP(MDROP)) dut (
        .clk(clk), .rst_n(rst_n), .lw_v(lw_v), .lw_slot(lw_slot), .lw_addr(lw_addr), .lw_blk(lw_blk),
        .start(c_start), .start_slot(c_slot), .start_pos(c_pos), .start_k(KW'(K)), .start_base(c_base),
        .start_skip(c_skip), .start_n(c_n), .start_qbase(c_qb), .done(c_done), .busy(c_busy), .fault(c_fault),
        .req_v(h_req_v), .req_rdy(h_req_rdy), .req_addr(h_req_addr), .req_len(h_req_len), .req_tag(h_req_tag),
        .rsp_v(h_rsp_v), .rsp_rdy(h_rsp_rdy), .rsp_tag(h_rsp_tag), .rsp_beat(h_rsp_beat), .rsp_data(h_rsp_data),
        .ks_valid(ks_valid), .ks_ready(ks_ready), .ks_lv(ks_lv), .ks_key(ks_key), .ks_idx(ks_idx), .ks_last(ks_last),
        .sc_valid(sc_valid), .sc_ready(sc_ready), .sc_lv(sc_lv), .sc_val(sc_val), .sc_idx(sc_idx), .sc_last(sc_last),
        .out_valid(out_valid), .out_ready({Q{1'b1}}), .out_last(out_last), .out_lv(out_lv), .out_val(out_val),
        .out_idx(out_idx), .out_ninf(out_ninf), .ovf(c_ovf), .short(c_short), .passes(c_passes),
        .cnt_keys(c_keys), .cnt_beats(c_beats));

    // ---------------------------------------------------------------- wavefront package controller
    reg              in_valid, in_last;
    wire             in_ready;
    reg  [FLIT-1:0]  in_data;
    wire             out_v, out_l;
    wire [FLIT-1:0]  out_d;
    wire             core_start;
    wire [NW-1:0]    core_token, core_pos;
    wire [7:0]       core_user;
    wire [23:0]      kv_base;
    wire             vm_we, vm_re, pr_re, tok_valid, proto_fault, wf_issue, wf_reject, wf_squash, core_busy;
    wire [VWA-1:0]   vm_waddr, vm_raddr;
    wire [FLIT-1:0]  vm_wdata;
    reg  [FLIT-1:0]  vm_rq;
    reg  [FLIT-1:0]  vm [0:(1 << VWA) - 1];
    always @(posedge clk) begin
        if (vm_we) vm[vm_waddr] <= vm_wdata;
        if (vm_re) vm_rq <= vm[vm_raddr];
    end
    ot_rom_pkg_ctrl_wf #(.PKG_ID(1), .FLIT(FLIT), .NW(NW), .AW(24), .VWA(VWA), .MAXU(1), .USER_W(8), .KVW(1024),
        .XWORDS(1), .RXB(0), .TXB(0), .SOURCE(0), .SEND_HIDDEN(1), .HID_DEST(2), .SEND_RESULT(0),
        .WAVE(1), .WIN(6)) ctrl (
        .clk(clk), .rst_n(rst_n), .cfg_users(8'd1), .cfg_prompt_len({NW{1'b0}}), .cfg_gen_len({NW{1'b0}}),
        .in_valid(in_valid), .in_ready(in_ready), .in_data(in_data), .in_last(in_last),
        .out_valid(out_v), .out_ready(1'b1), .out_data(out_d), .out_last(out_l),
        .core_start(core_start), .core_token(core_token), .core_pos(core_pos), .core_user(core_user),
        .core_done(c_done), .core_next_token({NW{1'b0}}), .core_next_val(32'd0), .kv_base(kv_base),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .vm_re(vm_re), .vm_raddr(vm_raddr), .vm_rq(vm_rq),
        .pr_re(pr_re), .pr_user(), .pr_pos(), .pr_q({NW{1'b0}}), .pr_blk(), .pr_qk(1'b0),
        .core_busy(core_busy), .tok_valid(tok_valid), .tok_user(), .tok_pos(), .tok_id(), .users_done(),
        .proto_fault(proto_fault), .wf_issue(wf_issue), .wf_reject(wf_reject), .wf_squash(wf_squash));
    assign c_start = core_start;
    // the job descriptor the stage program supplies with the start (combinational on core_pos)
    integer dq, dj;
    always @* begin
        dj = int'(core_pos) - P0;
        if (dj < 0 || dj >= NJOBS) dj = 0;
        c_slot = SLW'(jslot(dj)); c_pos = IW'(core_pos);
        for (dq = 0; dq < Q; dq = dq + 1) begin
            c_base[dq*HW +: HW] = HW'(obase(dq)); c_skip[dq*10 +: 10] = 10'(ooff(dq));
            c_n[dq*(LMW+1) +: LMW+1] = (LMW+1)'(nlist[dj*Q + dq]);
            c_qb[dq*IW +: IW] = IW'(RANK*PER_RANK + dq*PER_STACK);
        end
    end

    // ---------------------------------------------------------------- job tables
    localparam integer MAXJ = 4;
    integer nlist [0:MAXJ*Q-1];
    reg [LBW-1:0] list [0:MAXJ*Q*2048-1];
    reg [15:0] score [0:MAXJ*PER_RANK-1];
    integer fexp [0:MAXJ*Q-1];
    integer left [0:MAXJ*Q-1];
    function automatic integer ooff(input integer q);  ooff = (q * OSTEP) % 1024; endfunction
    function automatic integer obase(input integer q); obase = BASE + q * BSTEP; endfunction
    function automatic integer jslot(input integer j); jslot = (LSW > 0) ? ((P0 + j) % (1 << LSW)) : 0; endfunction
    // key pattern of the HBM model (tb_hdc_v41x_idx_kgather.sv)
    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin for (w = 0; w < 8; w = w + 1) pat[32*w +: 32] = (sec * 32'd8 + w) * 32'h9E3779B1 ^ 32'h5bd1e995; end
    endfunction
    function automatic [543:0] expkey(input integer a, input integer lb, input integer k);
        integer lk, sb, pp;
        reg [AW-1:0] sc, cs;
        reg [255:0] sw;
        begin
            lk = ooff(a) + 8 * lb + k; sb = lk / 1024; pp = lk % 1024;
            sc = AW'((obase(a) + 17 * sb) * 128 + pp / 8);
            cs = AW'((obase(a) + 17 * sb + 1) * 128 + 2 * pp);
            sw = pat(sc);
            expkey = {sw[32*(pp%8) +: 32], pat(cs + 1), pat(cs)};
        end
    endfunction
    string fn, pfx;
    initial begin : load
        integer fd, j, q, i, v, r;
        for (j = 0; j < NJOBS; j = j + 1) begin
            if (!$value$plusargs($sformatf("L%0d=%%s", j), pfx)) $fatal(1, "+L%0d required", j);
            for (q = 0; q < Q; q = q + 1) begin
                fd = $fopen($sformatf("%s.s%0d", pfx, q), "r");
                if (fd == 0) $fatal(1, "list %0d/%0d", j, q);
                r = $fscanf(fd, "%d", nlist[j*Q+q]);
                for (i = 0; i < nlist[j*Q+q]; i = i + 1) begin r = $fscanf(fd, "%h", v); list[(j*Q+q)*2048+i] = LBW'(v); end
                $fclose(fd);
            end
            if (!$value$plusargs($sformatf("SC%0d=%%s", j), fn)) $fatal(1, "+SC%0d required", j);
            $readmemh(fn, score, j * PER_RANK, (j + 1) * PER_RANK - 1);
            if (!$value$plusargs($sformatf("EX%0d=%%s", j), pfx)) $fatal(1, "+EX%0d required", j);
            for (q = 0; q < Q; q = q + 1) begin
                fd = $fopen($sformatf("%s.exp%0d", pfx, q), "r");
                if (fd == 0) $fatal(1, "exp %0d/%0d", j, q);
                fexp[j*Q+q] = fd;
                r = $fscanf(fd, "S %d\n", left[j*Q+q]);
            end
        end
    end

    // ---------------------------------------------------------------- scorer stand-in
    localparam integer SD = 64;
    reg [16-1:0]      f_lv  [0:Q*SD-1];
    reg [16*16-1:0]   f_val [0:Q*SD-1];
    reg [16*IW-1:0]   f_idx [0:Q*SD-1];
    reg               f_last[0:Q*SD-1];
    integer           f_t   [0:Q*SD-1];
    integer f_wp [0:Q-1], f_rp [0:Q-1], f_n [0:Q-1];
    integer cyc = 0, job = -1, t_job_start = 0;
    integer key_err = 0;
    integer j_start [0:MAXJ-1], j_first_key [0:MAXJ-1], j_last_key [0:MAXJ-1], j_last_sc [0:MAXJ-1];
    integer j_done [0:MAXJ-1], j_err [0:MAXJ-1], j_out [0:MAXJ-1], j_passes [0:MAXJ-1], j_keys [0:MAXJ-1];
    integer q, l, i, b, jj, x_pos, x_bits, x_ninf, rc, lb, nk, fdx;
    initial for (q = 0; q < Q; q = q + 1) begin f_wp[q] = 0; f_rp[q] = 0; f_n[q] = 0; end
    initial for (jj = 0; jj < MAXJ; jj = jj + 1) begin
        j_start[jj] = -1; j_first_key[jj] = -1; j_last_key[jj] = -1; j_last_sc[jj] = -1; j_done[jj] = -1;
        j_err[jj] = 0; j_out[jj] = 0; j_passes[jj] = 0; j_keys[jj] = 0;
    end
    // combinational: ready while there is room; head visible LAT edges after it was pushed
    always @* begin
        for (q = 0; q < Q; q = q + 1) begin
            ks_ready[q] = (f_n[q] < SD) && (cyc >= t_job_start + SETTLE);
            sc_valid[q] = (f_n[q] > 0) && (cyc >= f_t[q*SD + f_rp[q]] + LAT);
            sc_lv[q*16 +: 16] = f_lv[q*SD + f_rp[q]];
            sc_val[q*256 +: 256] = f_val[q*SD + f_rp[q]];
            sc_idx[q*16*IW +: 16*IW] = f_idx[q*SD + f_rp[q]];
            sc_last[q] = f_last[q*SD + f_rp[q]];
        end
    end

    // ---------------------------------------------------------------- driver
    localparam [3:0] MT_HIDDEN = 4'd1;
    localparam integer HDR_POS = 40;
    integer wi = 0, wj = 0, phase = 0, fi = 0, outs = 0, last_done = -1, errors = 0, prev_done = -1;
    reg done_q = 0;
    always @* begin
        in_valid = (phase == 1) && (fi < 2 * NJOBS);
        in_last = fi[0];
        in_data = {FLIT{1'b0}};
        if (!fi[0]) begin
            in_data[0 +: 8] = 8'd1; in_data[16 +: 4] = MT_HIDDEN; in_data[24 +: 8] = 8'd1;
            in_data[HDR_POS +: NW] = NW'(P0 + fi / 2);
        end else in_data = {16{32'(P0 + fi / 2)}};
    end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        // the user is already at position P0 (1M context): preset the controller's expected
        // position (bench-only; a real user reaches it by decoding)
        if (cyc == 6) ctrl.upos[0] = NW'(P0);
        if (cyc > MAX_CYCLES) begin $display("TIMEOUT"); $display("FAIL"); $finish; end
        if (proto_fault) begin $display("E proto_fault"); $display("FAIL"); $finish; end
        if (c_fault) begin $display("E chain fault"); $display("FAIL"); $finish; end
        lw_v <= 0;
        // phase 0: write every job's lists (one entry per stack per cycle), job by job
        if (rst_n && cyc > 8 && phase == 0) begin
            for (q = 0; q < Q; q = q + 1) begin
                lw_v[q] <= (wi < nlist[wj*Q+q]);
                lw_blk[q*LBW +: LBW] <= list[(wj*Q+q)*2048 + wi];
            end
            lw_addr <= LMW'(wi); lw_slot <= SLW'(jslot(wj));
            if (wi == 2047) begin wi <= 0; wj <= wj + 1; if (wj == NJOBS - 1) phase <= 1; end
            else wi <= wi + 1;
        end
        // phase 1: HIDDEN messages (header + one payload flit each), offered back to back
        if (phase == 1 && in_valid && in_ready) fi <= fi + 1;
        // chain job descriptor, presented with core_start (combinational from the controller)
        if (core_start) begin
            job = core_pos - P0; t_job_start = cyc;
            j_start[core_pos - P0] = cyc;
            if (dut.run || (|dut.g_busy))
                $display("E start while busy: run=%0d g_busy=%b", dut.run, dut.g_busy);
            if (prev_done >= 0) $display("HANDOFF job %0d start-after-prev-done=%0d", core_pos - P0, cyc - prev_done);
        end
        if (c_done && !done_q && job >= 0) begin j_done[job] = cyc; prev_done = cyc; j_passes[job] = c_passes; end
        done_q <= c_done;
        if (out_v && out_l) outs = outs + 1;
        // scorer: push accepted key beats (score lookup + key check), pop accepted scored beats
        for (q = 0; q < Q; q = q + 1) begin
            if (ks_valid[q] && ks_ready[q]) begin
                if (j_first_key[job] < 0) j_first_key[job] = cyc;
                j_last_key[job] = cyc;
                f_lv[q*SD + f_wp[q]] = ks_lv[q*16 +: 16];
                f_idx[q*SD + f_wp[q]] = ks_idx[q*16*IW +: 16*IW];
                f_last[q*SD + f_wp[q]] = ks_last[q];
                f_t[q*SD + f_wp[q]] = cyc;
                for (l = 0; l < 16; l = l + 1) begin
                    x_pos = int'(ks_idx[(q*16 + l)*IW +: IW]);
                    f_val[q*SD + f_wp[q]][16*l +: 16] =
                        ks_lv[q*16 + l] ? score[job*PER_RANK + (x_pos - RANK*PER_RANK)] : 16'hFF80;
                    if (ks_lv[q*16 + l]) begin
                        j_keys[job] = j_keys[job] + 1;
                        lb = (x_pos - RANK*PER_RANK - q*PER_STACK) / 8;
                        if (ks_key[(q*16 + l)*544 +: 544] !== expkey(q, lb, x_pos % 8)) key_err = key_err + 1;
                    end
                end
                f_wp[q] = (f_wp[q] + 1) % SD; f_n[q] = f_n[q] + 1;
            end
            if (sc_valid[q] && sc_ready[q]) begin
                j_last_sc[job] = cyc;
                f_rp[q] = (f_rp[q] + 1) % SD; f_n[q] = f_n[q] - 1;
            end
        end
        // selection check
        for (q = 0; q < Q; q = q + 1) if (out_valid[q] && job >= 0) begin
            for (l = 0; l < 16; l = l + 1) if (out_lv[q*16 + l]) begin
                j_out[job] = j_out[job] + 1;
                if (left[job*Q+q] <= 0) begin
                    j_err[job] = j_err[job] + 1;
                    if (j_err[job] < 6) $display("E job %0d q %0d extra %0d", job, q, out_idx[(q*16+l)*IW +: IW]);
                end else begin
                    fdx = fexp[job*Q+q];
                    rc = $fscanf(fdx, "%h %h %d\n", x_pos, x_bits, x_ninf);
                    left[job*Q+q] = left[job*Q+q] - 1;
                    if (out_idx[(q*16+l)*IW +: IW] != IW'(x_pos) || out_val[(q*16+l)*16 +: 16] != 16'(x_bits) ||
                        out_ninf[q*16+l] != x_ninf[0]) begin
                        j_err[job] = j_err[job] + 1;
                        if (j_err[job] < 6) $display("E job %0d q %0d got %0h/%0h want %0h/%0h", job, q,
                            out_idx[(q*16+l)*IW +: IW], out_val[(q*16+l)*16 +: 16], x_pos, x_bits);
                    end
                end
            end
            if (out_last[q] && left[job*Q+q] != 0) begin
                j_err[job] = j_err[job] + left[job*Q+q];
                if (j_err[job] < 6) $display("E job %0d q %0d missing %0d", job, q, left[job*Q+q]);
                left[job*Q+q] = 0;
            end
        end
        if (outs == NJOBS && !c_busy && last_done < 0) last_done = cyc;
        if (last_done >= 0 && cyc == last_done + 4) begin
            for (jj = 0; jj < NJOBS; jj = jj + 1) begin
                $display("JOB %0d pos=%0d slot=%0d start=%0d first_key=%0d last_key=%0d last_scored=%0d done=%0d busy=%0d passes=%0d keys=%0d out=%0d errors=%0d",
                         jj, P0 + jj, jslot(jj), j_start[jj], j_first_key[jj] - j_start[jj], j_last_key[jj] - j_start[jj],
                         j_last_sc[jj] - j_start[jj], j_done[jj] - j_start[jj], j_done[jj] - j_start[jj], j_passes[jj],
                         j_keys[jj], j_out[jj], j_err[jj]);
                errors = errors + j_err[jj];
            end
            $display("SUMMARY njobs=%0d lsw=%0d mdrop=%0d lat=%0d key_errors=%0d short=%0d ovf=%0d hidden_out=%0d errors=%0d cycles=%0d",
                     NJOBS, LSW, MDROP, LAT, key_err, c_short, c_ovf, outs, errors + key_err, cyc);
            if (errors + key_err == 0) $display("PASS"); else $display("FAIL");
            $finish;
        end
    end
endmodule
