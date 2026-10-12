`timescale 1ns/1ps
// hgi-1010/c2 (2026-10-10, AUDIT N5): DIE-MASTER bench of the FUSED station: the generated quant die wrapper hfd_quant
// (physical/hbm_accel_die_views/quant_hgi/rtl: ot_hgi_fused_station = FUSED front + quant unit + FUSED mover) driven ONLY
// through its die ports, as the die drives it:
//   * f_hgi_cmdproc 1,216 b = the CP's unit-4 record {n_O, n_B, n_A, O, C, B, A, header, valid} (ot_hgi_cp_die FUSED 1),
//     issued as the CP does (one credit; valid a one-edge pulse while the credit and ready are up; credit back on done /
//     fault from t_hgi_cmdproc);
//   * the REAL HGI VM (ot_hgi_vm_unit NC 4, RP / W2 32, LQ 32) on the three VM packet clients (quant, FUSED body, FUSED
//     mover) and, through ot_hgi_vm_lanearb (K 3, FUSED = slot 2, RLY 2 = the lgE station + relays), on the lgE taps
//     unpacked by the tap contract;
//   * the loader end of the remote kport lane: ot_hgi_hbm_rdq_server + an in-order HBM lane model (random ready and
//     latency) holding the case's HBM words.
// el1011-hbm-fused 10-12 (HCE 2): + the generated hfd_hc_eng view (ot_hgi_hc_eng_station: the lane-local one-pass HC
// engine) on lgE slot 3, fed by hfd_quant over fused_ne / fused_ne_r through NERL die relay stages each way (the
// quant -> hc_eng distance, ~3.5 mm at <= 504 um a stage); the d = 5120 HC_POST / HC_PRE_NORM records (vectors with
// FUSED_HLL = 1: GPK gain, bank-phase aligned) run there end to end.  LANE_LOAD: the bench preloads / checks VM as an lgE
// client on slot 0 (32 sectors a cycle, granted like any client) instead of word-by-word packets.
// Mutants: fused_hce_m4 / fused_hce_m2 = the hc_eng view generated at engine MUT 4 (retire before the writes land) /
// MUT 2 (lane 0 swaps rows 0 / 1): must FAIL.
// Vectors: tools/hgi_adapters/fused_bench.py DATA cases (CF-NORM ROW_NORM, Qwen ROW_NORM, DS HC_PRE_NORM / HC_POST):
// every record retires without fault and VM out == expected.  Prints HGI_FUSED_STATION PASS / FAIL.
// Mutant: build with the wrapper generated at MUT 1 (wl lane from the wrong sector bits) -> the VM rejects / data FAIL.
module tb_hgi_fused_station;
    `include "fu_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [1214:0] recm [0:NREC-1]; reg [287:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [71:0] hbmm [0:NHBM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/fu_rec.mem"}, recm); $readmemh({dir, "/fu_case.mem"}, casem);
        $readmemh({dir, "/fu_vmi.mem"}, vmim); $readmemh({dir, "/fu_vme.mem"}, vmem); $readmemh({dir, "/fu_hbm.mem"}, hbmm);
    end
    integer errors = 0, cyc = 0, seed = 7; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [1215:0] rec = 0; wire [2:0] ret;
    wire [337:0] qq, fq, mq; wire [273:0] qr, fr, mr, tr; reg [337:0] tq = 0;
    wire [512:0] rup; wire [8256:0] rdn; wire [8960:0] wup; wire [64:0] wdn; wire [37:0] xq; wire [256:0] xr;
    wire [150:0] ne_q, ne_e; wire [2:0] ne_rq, ne_re;     // fused_ne at hfd_quant / at hfd_hc_eng (and the return)
    hfd_quant dut (.ck(clk), .rst(!rst_n), .f_hgi_cmdproc(rec), .t_hgi_cmdproc(ret), .t_hgi_vmq(qq), .f_hgi_vmr(qr),
        .t_hgi_vmq_fused(fq), .f_hgi_vmr_fused(fr), .t_hgi_vmq_fmv(mq), .f_hgi_vmr_fmv(mr),
        .t_lgE_rup(rup), .f_lgE_rdn(rdn), .t_lgE_wup(wup), .f_lgE_wdn(wdn), .t_hgi_fmkq(xq), .f_hgi_fmkr(xr),
        .t_fused_ne(ne_q), .f_fused_ne(ne_rq));
    // ---- the die net fused_ne: NERL relay flops each way (every bit of a bundle the same latency)
`ifndef NERL
 `define NERL 7
`endif
    reg [150:0] ne_rl [0:`NERL]; reg [2:0] ner_rl [0:`NERL];
    always @* begin ne_rl[0] = ne_q; ner_rl[0] = ne_re; end
    for (genvar r = 1; r <= `NERL; r = r + 1) begin : g_nerl
        always @(posedge clk) begin ne_rl[r] <= ne_rl[r - 1]; ner_rl[r] <= ner_rl[r - 1]; end
    end
    assign ne_e = ne_rl[`NERL]; assign ne_rq = ner_rl[`NERL];
    wire [512:0] erup; wire [8256:0] erdn; wire [8960:0] ewup; wire [64:0] ewdn;
    hfd_hc_eng dhe (.ck(clk), .rst(!rst_n), .f_fused_ne(ne_e), .t_fused_ne(ne_re), .t_lgE_rup(erup), .f_lgE_rdn(erdn),
        .t_lgE_wup(ewup), .f_lgE_wdn(ewdn));
    // ---- lgE: lane head (slot 0 = this bench's LANE_LOAD client, 1 idle, 2 = FUSED (hfd_quant), 3 = HC_ENG) + VM unit
    wire [3:0] rgnt, wgnt; wire [4*32-1:0] rcr, wcr, wdone; wire [4*32*257-1:0] rrs;
    wire [32*16-1:0] g_rq; wire [31:0] g_rcr, g_wcr, g_wdone; wire [32*257-1:0] g_rr; wire [32*280-1:0] g_wq;
    reg b_rreq = 0, b_wreq = 0; reg [32*16-1:0] t_rq = 0; reg [32*280-1:0] t_wq = 0;
    ot_hgi_vm_lanearb #(.K(4), .REQW(16), .RSPW(257), .RLY(2)) u_ar (.clk(clk), .rst_n(rst_n),
        .c_req({erup[0], rup[0], 1'b0, b_rreq}), .c_gnt(rgnt), .c_q({erup[512:1], rup[512:1], 512'd0, t_rq}), .c_cr(rcr),
        .c_rsp(rrs), .g_q(g_rq), .g_cr(g_rcr), .g_rsp(g_rr));
    ot_hgi_vm_lanearb #(.K(4), .REQW(280), .RSPW(1), .RLY(2)) u_aw (.clk(clk), .rst_n(rst_n),
        .c_req({ewup[0], wup[0], 1'b0, b_wreq}), .c_gnt(wgnt), .c_q({ewup[8960:1], wup[8960:1], {32*280{1'b0}}, t_wq}),
        .c_cr(wcr), .c_rsp(wdone), .g_q(g_wq), .g_cr(g_wcr), .g_rsp(g_wdone));
    assign rdn = {rrs[2*32*257 +: 32*257], rcr[64 +: 32], rgnt[2]};
    assign wdn = {wdone[64 +: 32], wcr[64 +: 32], wgnt[2]};
    assign erdn = {rrs[3*32*257 +: 32*257], rcr[96 +: 32], rgnt[3]};
    assign ewdn = {wdone[96 +: 32], wcr[96 +: 32], wgnt[3]};
    ot_hgi_vm_unit #(.NC(4), .RP(32), .W2(32), .LQ(32)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, mq, fq, qq}),
        .cr({tr, mr, fr, qr}), .status(), .wq(280'd0), .wq_done(), .rq(g_rq), .rq_cr(g_rcr), .rr(g_rr), .w2q(g_wq),
        .w2q_cr(g_wcr), .w2q_done(g_wdone));
    // ---- loader end of the remote kport lane + an in-order HBM lane model
    wire k_v, sflt; wire [36:0] k_a; reg k_rdy = 0, k_rv = 0; reg [255:0] k_rd = 0;
    ot_hgi_hbm_rdq_server #(.Q(32)) u_srv (.clk(clk), .rst_n(rst_n), .xq(xq), .xr(xr), .req_v(k_v), .req_rdy(k_rdy),
        .req_addr(k_a), .rsp_v(k_rv), .rsp_data(k_rd), .fault(sflt));
    reg [31:0] hbm [longint];
    reg [36:0] lq_a [0:255]; integer lq_t [0:255]; integer lh = 0, ln = 0, q;
    always @(posedge clk) begin
        k_rv <= 0;
        if (rst_n && ln > 0 && lq_t[lh % 256] <= cyc) begin
            for (q = 0; q < 8; q = q + 1)
                k_rd[32*q +: 32] <= hbm.exists((lq_a[lh % 256] >> 2) + q) ? hbm[(lq_a[lh % 256] >> 2) + q] : 32'd0;
            k_rv <= 1; lh = lh + 1; ln = ln - 1;
        end
        if (rst_n && k_v && k_rdy) begin
            lq_a[(lh + ln) % 256] = k_a;
            lq_t[(lh + ln) % 256] = cyc + 20 + ($random(seed) & 31);
            if (ln > 0 && lq_t[(lh + ln) % 256] < lq_t[(lh + ln - 1) % 256]) lq_t[(lh + ln) % 256] = lq_t[(lh + ln - 1) % 256];
            ln = ln + 1;
        end
        k_rdy <= ln < 200 && ($random(seed) & 3) != 0;
    end
    // ---- bench VM client (load / check)
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 1000) begin errors = errors + 1; $display("ERR bench VM request timed out"); end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    // ---- LANE_LOAD: VM preload / check as the lgE slot-0 client (sector entries {sec 15, mask 8, data 256} a lane)
    reg [278:0] lw_q [0:31][$]; reg [278:0] lr_q [0:31][$]; reg [278:0] lr_e [0:31][$];
    integer lwcr [0:31], lrcr [0:31];
    task automatic lanes_run(input integer cs);
        integer b, busy, tw, q2;
        begin
            @(negedge clk); b_rreq = 1; b_wreq = 1;
            tw = 0; while (!(rgnt[0] && wgnt[0]) && tw < 100000) begin @(negedge clk); tw = tw + 1; end
            for (b = 0; b < 32; b = b + 1) begin lwcr[b] = 32; lrcr[b] = 32; end
            busy = 1; tw = 0;
            while (busy && tw < 400000) begin
                @(negedge clk);
                t_rq = 0; t_wq = 0; busy = 0;
                for (b = 0; b < 32; b = b + 1) begin
                    if (wcr[b]) lwcr[b] = lwcr[b] + 1;
                    if (rcr[b]) lrcr[b] = lrcr[b] + 1;
                    if (rrs[b*257 + 256]) begin : rsp
                        reg [278:0] e; e = lr_e[b].pop_front();
                        for (q2 = 0; q2 < 8; q2 = q2 + 1)
                            if (e[256 + q2] && rrs[b*257 + 32*q2 +: 32] !== e[32*q2 +: 32]) begin
                                if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", cs, {e[278:264], 3'(q2)},
                                                          rrs[b*257 + 32*q2 +: 32], e[32*q2 +: 32]);
                                errors = errors + 1;
                            end
                    end
                    if (lw_q[b].size() > 0 && lwcr[b] > 0) begin : wr
                        reg [278:0] x; x = lw_q[b].pop_front();
                        t_wq[b*280 +: 280] = {1'b1, x[278:264], x[255:0], x[263:256]}; lwcr[b] = lwcr[b] - 1;
                    end else if (lw_q[b].size() == 0 && lr_q[b].size() > 0 && lrcr[b] > 0 && lwcr[b] == 32) begin : rd
                        reg [278:0] x; x = lr_q[b].pop_front();
                        t_rq[b*16 +: 16] = {1'b1, x[278:264]}; lrcr[b] = lrcr[b] - 1; lr_e[b].push_back(x);
                    end
                    if (lw_q[b].size() > 0 || lr_q[b].size() > 0 || lr_e[b].size() > 0 || lwcr[b] != 32 || lrcr[b] != 32) busy = 1;
                end
                tw = tw + 1;
            end
            @(negedge clk); t_rq = 0; t_wq = 0; b_rreq = 0; b_wreq = 0;
            if (busy) begin $display("ERR bench lane traffic hung"); errors = errors + 1; end
            repeat (8) @(negedge clk);
        end
    endtask
    task automatic lanes_words(input integer first, input integer n, input integer wr);
        integer j2; reg [278:0] x; reg [31:0] a2; reg have;
        begin
            have = 0; x = 0;
            for (j2 = 0; j2 < n; j2 = j2 + 1) begin
                a2 = wr ? vmim[first + j2][63:32] : vmem[first + j2][63:32];
                if (have && x[278:264] != a2[17:3]) begin
                    if (wr) lw_q[x[268:264]].push_back(x); else lr_q[x[268:264]].push_back(x);
                    have = 0;
                end
                if (!have) begin x = 0; x[278:264] = a2[17:3]; have = 1; end
                x[256 + a2[2:0]] = 1'b1;
                x[32*a2[2:0] +: 32] = wr ? vmim[first + j2][31:0] : vmem[first + j2][31:0];
            end
            if (have) begin if (wr) lw_q[x[268:264]].push_back(x); else lr_q[x[268:264]].push_back(x); end
        end
    endtask
    // HC engine occupancy of a case (the record in S_NEW = waiting on hfd_hc_eng)
    // and the record-level busy time (rec_v taken .. rec_done: the unit's own cycles, without the die-face stages)
    integer hce_cyc = 0, rb_cyc = 0;
    always @(posedge clk) begin
        if (rst_n && dut.u_fs.u_f.st == 5'd9) hce_cyc <= hce_cyc + 1;
        if (rst_n && dut.u_fs.u_f.st != 5'd0 && dut.u_fs.u_f.st != 5'd11) rb_cyc <= rb_cyc + 1;
    end
    // ---- the CP's unit-4 dispatch: one credit
    integer k, nf; reg credit = 1;
    always @(posedge clk) begin
        if (rst_n && ret[1]) k = k + 1;
        if (rst_n && ret[2]) nf = nf + 1;
        if (!rst_n) credit <= 1; else if (ret[1] || ret[2]) credit <= 1; else if (rec[0]) credit <= 0;
    end
    // progress watchdog: no record retire for 1,000,000 edges while a case runs = hang: dump the station and FAIL
    integer last_prog = 0; reg running = 0;
    always @(posedge clk) if (!running || ret[1] || ret[2]) last_prog = cyc;   // a held request is not progress: only a record retire is
    always @(posedge clk) if (running && cyc - last_prog > 1000000) begin
        $display("ERR hang: fused st %0d mph %0d own %0d fifo %0d mv_v %0d mv_rdy %0d credit %0d ret %b rup0 %0d wup0 %0d rgnt %b wgnt %b k_v %0d inflight %0d k %0d",
                 dut.u_fs.u_f.st, dut.u_fs.mph, dut.u_fs.own, dut.u_fs.fn, dut.u_fs.mv_v, dut.u_fs.mv_rdy, credit, ret, rup[0], wup[0],
                 rgnt, wgnt, k_v, dut.u_fs.u_cl.inf, k);
        $display("HGI_FUSED_STATION FAIL errors=hang"); $finish;
    end
    always @(posedge clk) if (running && cyc % 20000 == 0) begin $display("progress cyc %0d k %0d fused st %0d su span/stage/run/drain %0d%0d%0d%0d rreq %0d rgnt %b wreq %0d wgnt %b", cyc, k, dut.u_fs.u_f.st,
        dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.a_span, dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.a_stage, dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.a_run,
        dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.a_drain, rup[0], rgnt, wup[0], wgnt); $fflush; end
`ifdef DBG_DRAIN
    // drain bookkeeping of the SU WIDE controller (lane 0 / 1 credits and pending dones, lanes not yet done)
    always @(posedge clk) if (running && cyc % 20000 == 10000) begin
        $display("drain cyc %0d d_ph %0d wdr_go %0d ldone %h wcr0 %0d wcr1 %0d wpend0 %0d wpend1 %0d lane_ovf %0d st_cr0 %0d mph %0d",
            cyc, dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.d_ph, dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wdr_go,
            dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wdr_ldone, dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wcr[0],
            dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wcr[1], dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wpend[0],
            dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.wpend[1], dut.u_fs.u_f.g_unit.u_su.g_wctl.u_ctl.lane_ovf,
            dut.u_fs.cr[0], dut.u_fs.mph); $fflush; end
`endif
    integer c, j, t, kind, r0, nr, vi0, nvi, ve0, nve, h0, nh, words = 0, cases = 0, t0;
    reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][287:256]; r0 = casem[c][255:224]; nr = casem[c][223:192]; vi0 = casem[c][191:160];
            nvi = casem[c][159:128]; ve0 = casem[c][127:96]; nve = casem[c][95:64]; h0 = casem[c][63:32]; nh = casem[c][31:0];
            if (kind != 0) continue;
            rst_n = 0; hbm.delete(); repeat (4) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk);
`ifdef LANE_LOAD
            lanes_words(vi0, nvi, 1); lanes_run(c);
`else
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
`endif
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][71:32]] = hbmm[h0 + j][31:0];
            k = 0; nf = 0; t0 = cyc; running = 1; hce_cyc = 0; rb_cyc = 0;
            for (j = 0; j < nr; j = j + 1) begin
                t = 0; while (!(credit && ret[0]) && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(negedge clk); rec = {recm[r0 + j], 1'b1};
                @(negedge clk); rec[0] = 1'b0;
                t = 0; while (credit && t < 100) begin @(negedge clk); t = t + 1; end      // the credit is taken
            end
            t = 0; while (k < nr && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            running = 0;
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            if (sflt) begin $display("ERR case %0d: remote lane server overflow", c); errors = errors + 1; end
            $display("case %0d: %0d records retired in %0d cycles (die ports, real VM, remote kport lane; record busy %0d, on hfd_hc_eng %0d)", c, k, cyc - t0, rb_cyc, hce_cyc); $fflush;
`ifdef LANE_LOAD
            lanes_words(ve0, nve, 0); lanes_run(c);
            for (j = 0; j < 0; j = j + 1) begin
`else
            for (j = 0; j < nve; j = j + 1) begin
`endif
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve; cases = cases + 1;
        end
        $display("summary: %0d FUSED data cases through the hfd_quant die master, %0d VM words exact", cases, words);
        if (errors == 0 && cases > 0) $display("HGI_FUSED_STATION PASS"); else $display("HGI_FUSED_STATION FAIL errors=%0d", errors);
        $finish;
    end
endmodule
