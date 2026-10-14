`timescale 1ns/1ps
// Unit bench (el1013-hbm-redesign-suvop): 1 x ot_hgi_sv_lane2 (lid 3: banks 6, 7; chain end) + ot_hgi_sv_lmem + a behavioural VM wide-lane model.
// Prints LEAF_TB PASS / LEAF_TB FAIL.  +define+MUT_V=n builds the leaf mutant (1, 2, 5 must FAIL).
`ifndef LQ
`define LQ 8
`endif
`ifndef MUT_V
`define MUT_V 0
`endif
module tb_hgi_sv_leaf;
    localparam integer N = 16, AW = 24, NSJ = 6, LQ = `LQ, L0 = 6, NR = 2;
    reg clk = 1'b0, rst_n = 1'b0; always #5 clk = ~clk;
    integer errors = 0;
    function automatic longint now(); now = $time / 10; endfunction
    task automatic fail(input string s);
        begin errors = errors + 1; if (errors <= 30) $display("ERR @%0d %s", now(), s); end
    endtask

    // ------------------------------------------------------------------ DUT wiring
    reg [N-1:0] vi_re = '0; reg [N*AW-1:0] vi_addr = '0; wire [N*32-1:0] vi_q;
    wire [4*N*32-1:0] rd_q;
    reg [N-1:0] vm_we = '0; reg [N*AW-1:0] vm_waddr = '0; reg [N*32-1:0] vm_wdata = '0;
    reg [NR-1:0] res_we = '0; reg [NR*AW-1:0] res_addr = '0; reg [NR*32-1:0] res_data = '0;
    reg [15:0] wep = 16'd0;
    wire [1:0] l_lsw_v, l_lsw_scrub, l_ldr_v; wire [29:0] l_lsw_sec, l_ldr_sec; wire [511:0] l_lsw_d;
    wire [31:0] ldr_rv; wire [32*256-1:0] ldr_d; wire [32*12-1:0] ldr_em;
    reg [3:0] rf_clr = 4'd0; reg rf_rv = 1'b0; reg [4:0] rf_rsec = 5'd0; wire rf_rrv; wire [255:0] rf_rd; wire [7:0] rf_rm;
    wire bank_err;
    wire [31:0] lsw_v = 32'(l_lsw_v) << L0, lsw_scrub = 32'(l_lsw_scrub) << L0, ldr_v = 32'(l_ldr_v) << L0;
    wire [32*15-1:0] lsw_sec = 480'(l_lsw_sec) << (L0*15), ldr_sec = 480'(l_ldr_sec) << (L0*15);
    wire [32*256-1:0] lsw_d = 8192'(l_lsw_d) << (L0*256);
    ot_hgi_sv_lmem #(.N(N), .LWB(18), .AW(AW), .NR(NR), .RLAT(1)) u_mem (.clk(clk), .rst_n(rst_n),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_re({4*N{1'b0}}), .rd_addr({4*N*AW{1'b0}}), .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .res_we(res_we), .res_addr(res_addr), .res_data(res_data),
        .wep(wep), .lsw_v(lsw_v), .lsw_sec(lsw_sec), .lsw_d(lsw_d), .lsw_scrub(lsw_scrub),
        .ldr_v(ldr_v), .ldr_sec(ldr_sec), .ldr_rv(ldr_rv), .ldr_d(ldr_d), .ldr_em(ldr_em),
        .rf_clr(rf_clr), .rf_rv(rf_rv), .rf_rsec(rf_rsec), .rf_rrv(rf_rrv), .rf_rd(rf_rd), .rf_rm(rf_rm), .bank_err(bank_err));
    wire [31:0] wrq; reg [1:0] wrq_cr = 2'd0; reg [513:0] wrr = '0;
    wire [559:0] wwq; reg [1:0] wwq_cr = 2'd0, wwq_done = 2'd0;
    reg [53:0] jb = '0; reg [13:0] dfr0 = '0, dfr1 = '0; reg [NSJ-1:0] ssel = '0; reg dsel = 1'b0;
    wire [54+28+NSJ:0] cmd = {dsel, ssel, dfr1, dfr0, jb};
    wire [NSJ+32:0] status;
    ot_hgi_sv_lane2 #(.LQ(LQ), .NSJ(NSJ), .MUT_V(`MUT_V)) u_leaf (.clk(clk), .rst_n(rst_n), .lid(4'(L0 / 2)), .cmd_r(),
        .st_in({1'b0, 14'h3FFF, 14'h3FFF, 4'b1111, {NSJ{1'b1}}}),   // chain end: the neutral status word
        .wrq(wrq), .wrq_cr(wrq_cr), .wrr(wrr), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done),
        .lsw_v(l_lsw_v), .lsw_sec(l_lsw_sec), .lsw_d(l_lsw_d), .lsw_scrub(l_lsw_scrub),
        .ldr_v(l_ldr_v), .ldr_sec(l_ldr_sec), .ldr_rv(ldr_rv[L0 +: 2]), .ldr_d(ldr_d[L0*256 +: 512]), .ldr_em(ldr_em[L0*12 +: 24]),
        .cmd(cmd), .status(status));
    wire [NSJ-1:0] sdone = status[NSJ-1:0]; wire [1:0] ddone = status[NSJ +: 2];
    wire shome = status[NSJ+2], dhome = status[NSJ+3];
    wire [13:0] spre = status[NSJ+4 +: 14], dpre = status[NSJ+18 +: 14]; wire err = status[NSJ+32];

    // ------------------------------------------------------------------ shadows
    function automatic [255:0] vdata(input [14:0] s);
        for (integer w = 0; w < 8; w = w + 1) vdata[32*w +: 32] = ({17'd0, s} * 32'h9E3779B1) ^ {13'h0AA5, s, 1'b1, 3'(w)};
    endfunction
    function automatic owned(input [14:0] sec); owned = sec[4:0] == 5'(L0) || sec[4:0] == 5'(L0 + 1); endfunction
    // stage jobs
    reg sj_act [0:NSJ-1]; reg sj_scrub [0:NSJ-1]; reg [14:0] sj_vsec [0:NSJ-1], sj_lsec [0:NSJ-1]; integer sj_n [0:NSJ-1];
    longint sj_valid [0:NSJ-1]; longint ssel_valid = 0, dsel_valid = 0;
    reg landed [0:32767]; reg scrubbed [0:32767];
    integer n_wrq = 0, n_land = 0, n_scrub = 0, spre_mid = 0, dpre_mid = 0;
    // drain jobs
    reg dj_act [0:1]; reg [14:0] dj_vsec [0:1], dj_lsec [0:1]; integer dj_n [0:1]; longint dj_valid [0:1];
    integer tb_fr [0:1];
    reg [7:0] ex_mask [0:1][0:1023]; reg [255:0] ex_data [0:1][0:1023]; reg rd_seen [0:1][0:1023]; reg got [0:1][0:1023];
    integer last_i [0:1][0:1]; integer n_wwq = 0, n_ldr = 0;
    reg vm_done [0:32767];
    initial begin
        for (integer q = 0; q < NSJ; q = q + 1) begin sj_act[q] = 0; sj_scrub[q] = 0; sj_valid[q] = 0; sj_n[q] = 0; end
        for (integer q = 0; q < 2; q = q + 1) begin dj_act[q] = 0; dj_valid[q] = 0; dj_n[q] = 0; tb_fr[q] = 0; end
        for (integer q = 0; q < 32768; q = q + 1) begin landed[q] = 0; scrubbed[q] = 0; vm_done[q] = 0; end
    end

    // ------------------------------------------------------------------ behavioural VM lanes (random latency, credits)
    localparam integer QD = 4096;
    reg [14:0] rq_sec [0:1][0:QD-1]; longint rq_due [0:1][0:QD-1], rc_due [0:1][0:QD-1];
    integer rq_h [0:1], rq_t [0:1], rc_h [0:1], rd_out [0:1]; longint rc_last [0:1];
    longint wc_due [0:1][0:QD-1], wd_due [0:1][0:QD-1]; reg [14:0] wd_sec [0:1][0:QD-1];
    integer wc_h [0:1], wd_h [0:1], w_t [0:1], wr_out [0:1]; longint wc_last [0:1], wd_last [0:1];
    initial for (integer g = 0; g < 2; g = g + 1) begin
        rq_h[g] = 0; rq_t[g] = 0; rc_h[g] = 0; rd_out[g] = 0; rc_last[g] = 0;
        wc_h[g] = 0; wd_h[g] = 0; w_t[g] = 0; wr_out[g] = 0; wc_last[g] = 0; wd_last[g] = 0;
    end
    task automatic chk_write(input integer g, input [14:0] sec, input [255:0] d, input [7:0] m);
        integer r, i; reg hit;
        begin
            hit = 0;
            for (r = 0; r < 2; r = r + 1)
                if (dj_act[r] && sec >= dj_vsec[r] && 32'(sec) < 32'(dj_vsec[r]) + dj_n[r]) begin
                    hit = 1; i = 32'(sec) - 32'(dj_vsec[r]);
                    if (ex_mask[r][i] == 8'd0) fail($sformatf("VM write of an unwritten / stale sector: slot %0d idx %0d mask %02x", r, i, m));
                    else begin
                        if (m != ex_mask[r][i]) fail($sformatf("VM write mask %02x != %02x (slot %0d idx %0d)", m, ex_mask[r][i], r, i));
                        for (integer w = 0; w < 8; w = w + 1)
                            if (m[w] && ex_mask[r][i][w] && d[32*w +: 32] != ex_data[r][i][32*w +: 32])
                                fail($sformatf("VM write data mismatch slot %0d idx %0d word %0d", r, i, w));
                    end
                    if (i <= last_i[r][g]) fail($sformatf("VM write out of order / repeated: slot %0d idx %0d", r, i));
                    last_i[r][g] = i; got[r][i] = 1;
                end
            if (!hit) fail($sformatf("VM write outside every drain job: sector %0d", sec));
        end
    endtask
    always @(posedge clk) begin : vm
        longint t, d; reg [14:0] s;
        t = now();
        for (integer g = 0; g < 2; g = g + 1) begin
            wrq_cr[g] <= 1'b0; wrr[g*257 + 256] <= 1'b0; wwq_cr[g] <= 1'b0; wwq_done[g] <= 1'b0;
            // read lane
            if (wrq[g*16 + 15]) begin
                s = wrq[g*16 +: 15]; n_wrq = n_wrq + 1;
                rd_out[g] = rd_out[g] + 1; if (rd_out[g] > LQ) fail("read credits exceeded");
                if (s[4:0] != 5'(L0 + g)) fail("wrq sector on the wrong lane");
                rq_sec[g][rq_t[g] % QD] = s; rq_due[g][rq_t[g] % QD] = t + 2 + longint'($urandom % 9);
                d = t + 1 + longint'($urandom % 6); if (d <= rc_last[g]) d = rc_last[g] + 1; rc_last[g] = d;
                rc_due[g][rq_t[g] % QD] = d; rq_t[g] = rq_t[g] + 1;
            end
            if (rc_h[g] != rq_t[g] && t >= rc_due[g][rc_h[g] % QD]) begin wrq_cr[g] <= 1'b1; rc_h[g] = rc_h[g] + 1; rd_out[g] = rd_out[g] - 1; end
            if (rq_h[g] != rq_t[g] && t >= rq_due[g][rq_h[g] % QD]) begin
                wrr[g*257 +: 257] <= {1'b1, vdata(rq_sec[g][rq_h[g] % QD])}; rq_h[g] = rq_h[g] + 1;
            end
            // write lane
            if (wwq[g*280 + 279]) begin
                s = wwq[g*280 + 264 +: 15]; n_wwq = n_wwq + 1;
                wr_out[g] = wr_out[g] + 1; if (wr_out[g] > LQ) fail("write credits exceeded");
                if (s[4:0] != 5'(L0 + g)) fail("wwq sector on the wrong lane");
                chk_write(g, s, wwq[g*280 + 8 +: 256], wwq[g*280 +: 8]);
                // Delay legal credit returns long enough to fill the local prefetch queue; data are checked independently.
                d = t + 64 + longint'($urandom % 7); if (d <= wc_last[g]) d = wc_last[g] + 1; wc_last[g] = d;
                wc_due[g][w_t[g] % QD] = d;
                d = d + 1 + longint'($urandom % 5); if (d <= wd_last[g]) d = wd_last[g] + 1; wd_last[g] = d;
                wd_due[g][w_t[g] % QD] = d; wd_sec[g][w_t[g] % QD] = s; w_t[g] = w_t[g] + 1;
            end
            if (wc_h[g] != w_t[g] && t >= wc_due[g][wc_h[g] % QD]) begin wwq_cr[g] <= 1'b1; wc_h[g] = wc_h[g] + 1; wr_out[g] = wr_out[g] - 1; end
            if (wd_h[g] != w_t[g] && t >= wd_due[g][wd_h[g] % QD]) begin
                wwq_done[g] <= 1'b1; vm_done[wd_sec[g][wd_h[g] % QD]] = 1; wd_h[g] = wd_h[g] + 1;
            end
        end
    end

    // ------------------------------------------------------------------ checkers (sample pre-edge, then update shadows)
    always @(posedge clk) if (rst_n) begin : chk
        longint t; reg [14:0] s; reg hit; integer i;
        t = now();
        // status claims
        for (integer q = 0; q < NSJ; q = q + 1) if (sj_act[q] && t >= sj_valid[q]) begin
            if (sdone[q])
                for (i = 0; i < sj_n[q]; i = i + 1) if (owned(sj_vsec[q] + 15'(i))) begin
                    if (!(sj_scrub[q] ? scrubbed[sj_lsec[q] + 15'(i)] : landed[sj_lsec[q] + 15'(i)]))
                        fail($sformatf("sdone[%0d] with idx %0d not landed", q, i));
                end
            if (ssel[q] && t >= ssel_valid && !sj_scrub[q]) begin
                for (i = 0; i < sj_n[q]; i = i + 1)
                    if (owned(sj_vsec[q] + 15'(i)) && (spre == 14'h3FFF || i < 32'(spre)) && !landed[sj_lsec[q] + 15'(i)])
                        fail($sformatf("spre %0d ahead of the memory: slot %0d idx %0d", spre, q, i));
                if (spre != 14'h3FFF && spre > 14'd31) spre_mid = spre_mid + 1;
            end
        end
        for (integer r = 0; r < 2; r = r + 1) if (dj_act[r] && t >= dj_valid[r]) begin
            if (ddone[r])
                for (i = 0; i < dj_n[r]; i = i + 1) if (owned(dj_vsec[r] + 15'(i)) && ex_mask[r][i] != 8'd0) begin
                    if (!got[r][i] || !vm_done[dj_vsec[r] + 15'(i)]) fail($sformatf("ddone[%0d] with idx %0d not in the VM", r, i));
                end
            if (dsel == 1'(r) && t >= dsel_valid) begin
                for (i = 0; i < dj_n[r]; i = i + 1)
                    if (owned(dj_vsec[r] + 15'(i)) && (dpre == 14'h3FFF || i < 32'(dpre)) && !rd_seen[r][i])
                        fail($sformatf("dpre %0d ahead of the reads: slot %0d idx %0d", dpre, r, i));
                if (dpre != 14'h3FFF && dpre > 14'd31) dpre_mid = dpre_mid + 1;
            end
        end
        // bank-port activity
        for (integer g = 0; g < 2; g = g + 1) begin
            s = l_lsw_sec[g*15 +: 15];
            if (l_lsw_v[g] && l_lsw_scrub[g]) fail("lsw_v and lsw_scrub together");
            if (l_lsw_v[g]) begin
                hit = 0; n_land = n_land + 1;
                for (integer q = 0; q < NSJ; q = q + 1)
                    if (sj_act[q] && !sj_scrub[q] && s >= sj_lsec[q] && 32'(s) < 32'(sj_lsec[q]) + sj_n[q]) begin
                        hit = 1;
                        if (l_lsw_d[g*256 +: 256] != vdata(sj_vsec[q] + (s - sj_lsec[q]))) fail($sformatf("landing data wrong, local sector %0d", s));
                    end
                if (!hit) fail($sformatf("landing outside every stage job: local sector %0d", s));
                if (landed[s]) fail($sformatf("sector %0d landed twice", s));
                if (s[4:0] != 5'(L0 + g)) fail("landing on the wrong bank");
                landed[s] = 1;
            end
            if (l_lsw_scrub[g]) begin
                hit = 0; n_scrub = n_scrub + 1;
                for (integer q = 0; q < NSJ; q = q + 1)
                    if (sj_act[q] && sj_scrub[q] && s >= sj_lsec[q] && 32'(s) < 32'(sj_lsec[q]) + sj_n[q]) hit = 1;
                if (!hit) fail($sformatf("scrub outside every scrub job: local sector %0d", s));
                if (scrubbed[s]) fail("sector scrubbed twice");
                scrubbed[s] = 1;
            end
            s = l_ldr_sec[g*15 +: 15];
            if (l_ldr_v[g]) begin
                hit = 0; n_ldr = n_ldr + 1;
                for (integer r = 0; r < 2; r = r + 1)
                    if (dj_act[r] && s >= dj_lsec[r] && 32'(s) < 32'(dj_lsec[r]) + dj_n[r]) begin
                        hit = 1; i = 32'(s) - 32'(dj_lsec[r]);
                        if (i >= tb_fr[r]) fail($sformatf("drain read beyond the frontier: slot %0d idx %0d frontier %0d", r, i, tb_fr[r]));
                        if (rd_seen[r][i]) fail("drain sector read twice");
                        rd_seen[r][i] = 1;
                    end
                if (!hit) fail($sformatf("drain read outside every drain job: local sector %0d", s));
            end
        end
    end

    // ------------------------------------------------------------------ stimulus helpers
    task automatic load_stage(input [2:0] slot, input [14:0] vsec, input integer n, input [14:0] lsec, input scrub);
        begin
            @(posedge clk);
            jb <= {scrub, 4'd0, lsec, 14'(n), vsec, slot, 1'b0, 1'b1};
            for (integer i = 0; i < n; i = i + 1) begin landed[lsec + 15'(i)] = 0; scrubbed[lsec + 15'(i)] = 0; end
            sj_vsec[slot] = vsec; sj_lsec[slot] = lsec; sj_n[slot] = n; sj_scrub[slot] = scrub; sj_valid[slot] = now() + 3; sj_act[slot] = 1;
        end
    endtask
    task automatic load_drain(input slot, input [14:0] vsec, input integer n, input [14:0] lsec, input [3:0] ep, input chk);
        begin
            @(posedge clk);
            jb <= {chk, ep, lsec, 14'(n), vsec, 2'd0, slot, 1'b1, 1'b1};
            for (integer i = 0; i < n; i = i + 1) begin rd_seen[slot][i] = 0; got[slot][i] = 0; vm_done[vsec + 15'(i)] = 0; end
            last_i[slot][0] = -1; last_i[slot][1] = -1;
            dj_vsec[slot] = vsec; dj_lsec[slot] = lsec; dj_n[slot] = n; dj_valid[slot] = now() + 3; dj_act[slot] = 1;
        end
    endtask
    task automatic cmd_idle(); begin @(posedge clk); jb[0] <= 1'b0; end endtask
    // an ssel change shows in spre after 6 edges, a dsel change in dpre after 5 (10-13: the stage prefix is two
    // registered steps + the lane-pair step, the drain prefix one step + the lane-pair step; was 4 / 4)
    task automatic set_ssel(input [NSJ-1:0] v); begin @(posedge clk); ssel <= v; ssel_valid = now() + 6; end endtask
    task automatic set_dsel(input v); begin @(posedge clk); dsel <= v; dsel_valid = now() + 5; end endtask
    // final check of a finished stage job against the memory itself, then retire the shadow
    task automatic finish_stage(input integer q);
        integer cnt;
        begin
            cnt = 0;
            for (integer i = 0; i < sj_n[q]; i = i + 1) if (owned(sj_vsec[q] + 15'(i))) begin
                cnt = cnt + 1;
                if (!sj_scrub[q])
                    for (integer w = 0; w < 8; w = w + 1)
                        if (u_mem.lm[{sj_lsec[q] + 15'(i), 3'(w)}] != vdata(sj_vsec[q] + 15'(i))[32*w +: 32]) begin
                            fail($sformatf("memory word wrong: slot %0d idx %0d word %0d", q, i, w));
                        end
                if (sj_scrub[q] && u_mem.em[sj_lsec[q] + 15'(i)] != 12'd0) fail($sformatf("em not scrubbed: idx %0d", i));
            end
            if (!sj_scrub[q]) exp_sec = exp_sec + cnt; sj_act[q] = 0;
        end
    endtask
    integer exp_sec = 0, exp_scr = 0;
    task automatic wait_stage_all(input integer tmo);
        integer w; reg any;
        begin
            w = 0; any = 1;
            while (any && w < tmo) begin
                @(posedge clk); w = w + 1; any = 0;
                for (integer q = 0; q < NSJ; q = q + 1) if (sj_act[q]) begin
                    if (now() >= sj_valid[q] && sdone[q]) finish_stage(q); else any = 1;
                end
                if (w % 41 == 0) set_ssel(NSJ'(1) << ((w / 41) % (NSJ + 1)) | {NSJ{(w / 41) % (NSJ + 1) == NSJ}});
            end
            if (any) fail("stage jobs timed out");
        end
    endtask
    // one sector's vec writes on lanes l0 .. l0 + 7 (caller is at a posedge; cleared by wr_clear)
    task automatic wr_sec(input integer l0, input [14:0] lsec, input [7:0] m, input [255:0] d);
        for (integer w = 0; w < 8; w = w + 1) if (m[w]) begin
            vm_we[l0 + w] <= 1'b1; vm_waddr[(l0 + w)*AW +: AW] <= {6'd0, lsec, 3'(w)}; vm_wdata[(l0 + w)*32 +: 32] <= d[32*w +: 32];
        end
    endtask
    function automatic [255:0] rnd256(); for (integer w = 0; w < 8; w = w + 1) rnd256[32*w +: 32] = $urandom; endfunction
    task automatic wait_drain(input [1:0] which, input integer tmo);
        integer w; reg any;
        begin
            w = 0; any = 1;
            while (any && w < tmo) begin
                @(posedge clk); w = w + 1; any = 0;
                for (integer r = 0; r < 2; r = r + 1)
                    if (which[r] && !(now() >= dj_valid[r] && ddone[r])) any = 1;
                if (w % 29 == 0) set_dsel(1'((w / 29) % 2));
            end
            if (any) fail("drain jobs timed out");
        end
    endtask
    task automatic finish_drain(input integer r);
        begin
            for (integer i = 0; i < dj_n[r]; i = i + 1) if (owned(dj_vsec[r] + 15'(i))) begin
                if (!rd_seen[r][i]) fail($sformatf("drain slot %0d idx %0d never read", r, i));
                if ((ex_mask[r][i] != 8'd0) != got[r][i]) fail($sformatf("drain slot %0d idx %0d: VM write %0d, expected mask %02x", r, i, got[r][i], ex_mask[r][i]));
                if (ex_mask[r][i] != 8'd0) exp_wwq = exp_wwq + 1;
            end
            dj_act[r] = 0;
        end
    endtask
    integer exp_wwq = 0;

    // ------------------------------------------------------------------ the tests
    localparam [14:0] A_L = 15'd16424, A_V = 15'h2008, B_L = 15'd24646, B_V = 15'h5006;   // drain regions (frames 2, 3)
    localparam integer A_N = 990, B_N = 151;
    integer jn [0:5]; reg [14:0] jv [0:5];
    integer k, fa, fb, todo, mid0; reg [14:0] v, l; reg [7:0] m; reg [255:0] d;
    initial begin
        repeat (5) @(posedge clk); rst_n <= 1'b1; repeat (3) @(posedge clk);
        if (sdone != '1 || ddone != 2'b11 || !shome || !dhome || err || spre != 14'h3FFF) fail("status after reset");
        // ---- T0 lmem: rfile route (a[18]), written bits, clear, 1-edge reads
        @(posedge clk); res_we <= 2'b11; res_addr <= {24'h040045, 24'h040080}; res_data <= {32'hCAFE0045, 32'hBEEF0080};
        vm_we[0] <= 1'b1; vm_waddr[0 +: AW] <= 24'h000123; vm_wdata[0 +: 32] <= 32'h12340123;
        @(posedge clk); res_we <= 2'b00; vm_we <= '0; vi_re <= 16'h0003; vi_addr[0 +: AW] <= 24'h040045; vi_addr[AW +: AW] <= 24'h000123;
        rf_rv <= 1'b1; rf_rsec <= 5'b01_000;
        @(posedge clk); vi_re <= '0; rf_rv <= 1'b0;
        @(posedge clk);
        if (vi_q[31:0] != 32'hCAFE0045 || vi_q[63:32] != 32'h12340123) fail("lmem vi read (rfile / local)");
        if (!rf_rrv || rf_rm != 8'h20 || rf_rd[5*32 +: 32] != 32'hCAFE0045) fail("lmem rfile sector read");
        rf_clr <= 4'b0010; @(posedge clk); rf_clr <= 4'd0; rf_rv <= 1'b1; rf_rsec <= 5'b01_000;
        @(posedge clk); rf_rsec <= 5'b10_000;
        @(posedge clk); rf_rv <= 1'b0; if (!rf_rrv || rf_rm != 8'h00) fail("lmem rf_clr");
        @(posedge clk); if (!rf_rrv || rf_rm != 8'h01 || rf_rd[31:0] != 32'hBEEF0080) fail("lmem rf_clr cleared another slot");
        @(posedge clk); if (rf_rrv) fail("lmem rf_rrv not valid-driven");
        // ---- T1 stage: six regions at once (bank offsets 3, 6, 7, 10, 20, 31; n 700, 1, 5, 31, 10, 333)
        jn[0] = 700; jv[0] = 15'h0103; jn[1] = 1; jv[1] = 15'h0A06; jn[2] = 5; jv[2] = 15'h0B07;
        jn[3] = 31; jv[3] = 15'h0C0A; jn[4] = 10; jv[4] = 15'h0D14; jn[5] = 333; jv[5] = 15'h7E1F;
        set_ssel(6'b000001);
        for (k = 0; k < 6; k = k + 1) load_stage(3'(k), jv[k], jn[k], 15'(k*4096 + 64) + {10'd0, jv[k][4:0]}, 1'b0);   // back to back
        cmd_idle();
        wait_stage_all(4000);
        mid0 = spre_mid; if (mid0 == 0) fail("spre never showed a partial prefix");
        // ---- T1b: random jobs, slots reloaded as they finish
        todo = 30; k = 0;
        while ((todo > 0 || k != 0) && errors == 0) begin
            @(posedge clk); k = 0;
            for (integer q = 0; q < NSJ; q = q + 1) begin
                if (sj_act[q] && now() >= sj_valid[q] && sdone[q]) finish_stage(q);
                if (sj_act[q]) k = k + 1;
            end
            if (now() % 37 == 0) set_ssel(6'($urandom));
            for (integer q = 0; q < NSJ; q = q + 1) if (!sj_act[q] && todo > 0 && ($urandom % 4 == 0)) begin
                fa = ($urandom % 3 == 0) ? 1 + $urandom % 40 : 1 + $urandom % 700;
                v = 15'($urandom % (32768 - 800));
                load_stage(3'(q), v, fa, 15'(q*4096 + 32*($urandom % 64)) + {10'd0, v[4:0]}, 1'b0); cmd_idle();
                todo = todo - 1; k = k + 1;
            end
            if (now() > 200000) begin fail("random stage jobs timed out"); todo = 0; k = 0; end
        end
        set_ssel('1); repeat (6) @(posedge clk);
        if (spre != 14'h3FFF || sdone != '1) fail("spre / sdone not at rest after the stage jobs");
        repeat (30) @(posedge clk); if (!shome) fail("shome low at rest");
        if (n_land != exp_sec || n_wrq != exp_sec) fail($sformatf("sector count: wrq %0d landed %0d expected %0d", n_wrq, n_land, exp_sec));
        // ---- T2 scrub (frame 1, local 8292 .. +200) next to a stage job; em pre-set under epoch 5
        wep <= 16'h0050;
        for (k = 0; k < 264; k = k + 2) begin
            @(posedge clk); vm_we <= '0; wr_sec(0, 15'(8292 + k), 8'h81, rnd256()); wr_sec(8, 15'(8293 + k), 8'h18, rnd256());
        end
        @(posedge clk); vm_we <= '0;
        k = n_wrq;
        load_stage(3'd2, 15'd8292, 200, 15'd8292, 1'b1); load_stage(3'd0, 15'h1234, 90, 15'd148, 1'b0); cmd_idle();
        wait_stage_all(3000);
        for (integer i = 0; i < 264; i = i + 1) begin
            l = 15'(8292 + i);
            if (!(owned(l) && i < 200) && u_mem.em[l] != {4'd5, (i % 2 == 0) ? 8'h81 : 8'h18}) fail($sformatf("em wrong / scrubbed outside the job: local %0d = %03x", l, u_mem.em[l]));
        end
        exp_scr = 0; for (integer i = 0; i < 200; i = i + 1) if (owned(15'(8292 + i))) exp_scr = exp_scr + 1;
        if (n_scrub != exp_scr) fail($sformatf("scrub count %0d != %0d", n_scrub, exp_scr));
        if (n_land != exp_sec) fail("scrub job made VM traffic");
        // ---- T3 drain: two dense regions at once (partial first / last sector), frontier follows the writes
        wep <= 16'h3950;
        for (k = 0; k < 1024; k = k + 1) begin ex_mask[0][k] = 8'd0; ex_mask[1][k] = 8'd0; end
        dfr0 <= 14'd0; dfr1 <= 14'd0; tb_fr[0] = 0; tb_fr[1] = 0;
        load_drain(1'b0, A_V, A_N, A_L, 4'd9, 1'b1); load_drain(1'b1, B_V, B_N, B_L, 4'd3, 1'b1); cmd_idle();
        set_dsel(1'b0);
        fa = 0; fb = 0;
        while (fa < A_N || fb < B_N) begin
            // hold the frontier in front of a sector owned by this leaf (an early read would be seen), else a short gap
            if ((fa < A_N && owned(A_V + 15'(fa))) || (fb < B_N && owned(B_V + 15'(fb)))) repeat (12) @(posedge clk);
            else repeat ($urandom % 3) @(posedge clk);
            @(posedge clk); vm_we <= '0;
            if (fa < A_N) begin
                m = (fa == 0) ? 8'hF8 : (fa == A_N - 1) ? 8'h07 : 8'hFF; d = rnd256();
                wr_sec(0, A_L + 15'(fa), m, d); ex_mask[0][fa] = m; ex_data[0][fa] = d; fa = fa + 1;
            end
            if (fb < B_N && ($urandom % 2 == 0 || fa >= A_N)) begin
                m = (fb == 0) ? 8'h80 : (fb == B_N - 1) ? 8'h3F : 8'hFF; d = rnd256();
                wr_sec(8, B_L + 15'(fb), m, d); ex_mask[1][fb] = m; ex_data[1][fb] = d; fb = fb + 1;
            end
            dfr0 <= 14'(fa); dfr1 <= 14'(fb); tb_fr[0] = fa; tb_fr[1] = fb;
            if (now() % 5 == 0) begin @(posedge clk); vm_we <= '0; set_dsel(~dsel); end
        end
        @(posedge clk); vm_we <= '0;
        wait_drain(2'b11, 3000);
        finish_drain(0); finish_drain(1);
        if (dpre_mid == 0) fail("dpre never showed a partial prefix");
        repeat (40) @(posedge clk);
        if (!dhome || ddone != 2'b11 || dpre != 14'h3FFF) fail("dhome / ddone / dpre not at rest after the drains");
        if (n_wwq != exp_wwq) fail($sformatf("VM writes %0d != expected %0d", n_wwq, exp_wwq));
        if (`MUT_V == 0 && err) fail("err raised by a clean dense drain");
        // ---- T3c stale epochs: region A again under epoch 10, every third sector NOT rewritten (still epoch 9), chk = 0
        wep <= 16'h3A50; dfr0 <= 14'd0; tb_fr[0] = 0;
        for (k = 0; k < A_N; k = k + 1) begin
            @(posedge clk); vm_we <= '0;
            if (k % 3 != 1) begin
                m = 8'($urandom) | 8'h10; d = rnd256(); wr_sec(0, A_L + 15'(k), m, d); ex_mask[0][k] = m; ex_data[0][k] = d;
            end else ex_mask[0][k] = 8'd0;
        end
        @(posedge clk); vm_we <= '0; @(posedge clk);
        for (k = 0; k < A_N; k = k + 1) begin
            if (k % 3 != 1 && u_mem.em[A_L + 15'(k)] != {4'd10, ex_mask[0][k]}) fail($sformatf("em after a new-epoch write: idx %0d = %03x", k, u_mem.em[A_L + 15'(k)]));
            if (k % 3 == 1 && u_mem.em[A_L + 15'(k)][11:8] != 4'd9) fail("em of an untouched sector changed epoch");
        end
        load_drain(1'b0, A_V, A_N, A_L, 4'd10, 1'b0); cmd_idle();
        @(posedge clk); dfr0 <= 14'(A_N); tb_fr[0] = A_N;
        wait_drain(2'b01, 3000); finish_drain(0);
        if (n_wwq != exp_wwq) fail($sformatf("VM writes %0d != expected %0d (stale-epoch walk)", n_wwq, exp_wwq));
        repeat (20) @(posedge clk);
        if (`MUT_V == 0 && err) fail("err raised with chk = 0");
        if (bank_err) fail("bank_err");
        // ---- T3d the same walk with chk = 1 must raise err (stale sectors in a dense sink)
        dfr0 <= 14'd0; tb_fr[0] = 0;
        load_drain(1'b0, A_V, A_N, A_L, 4'd10, 1'b1); cmd_idle();
        @(posedge clk); dfr0 <= 14'(A_N); tb_fr[0] = A_N;
        wait_drain(2'b01, 3000); finish_drain(0);
        repeat (20) @(posedge clk);
        if (!err) fail("err not raised by stale sectors under chk = 1");
        if (!dhome || !shome) fail("credits not home at the end");
        $display("LEAF_TB stats: wrq %0d landed %0d scrubs %0d ldr %0d wwq %0d spre_mid %0d dpre_mid %0d cycles %0d errors %0d",
                 n_wrq, n_land, n_scrub, n_ldr, n_wwq, spre_mid, dpre_mid, now(), errors);
        if (errors == 0) $display("LEAF_TB PASS (MUT_V %0d)", `MUT_V); else $display("LEAF_TB FAIL (MUT_V %0d, %0d errors)", `MUT_V, errors);
        $finish;
    end
    initial begin #20000000; $display("LEAF_TB FAIL (watchdog)"); $finish; end
endmodule
