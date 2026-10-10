`timescale 1ns/1ps
// hgi-adapters (2026-10-09): bench of ot_hgi_fused_record.  Vectors tools/hgi_adapters/fused_bench.py (+DIR=).
//  RUN cases: records -> the adapter -> the REAL ot_hdc_v41x_vec (N32 M8 LV7: a 4,096-element row is 128 vectors) + VM, with a behavioural DMA mover (LOAD of
//    the BF16 gain from an HBM model): VM out == the expected (hbm-sim CF-NORM vm_out / hgi_sim lib.row_norm).
//  FIELD cases: HC_PRE_NORM / HC_POST norm-engine job words and QDQ quant-bus forwarding == the reference, retire on the
//    peer's done.  NEGATIVE cases: rec_fault, nothing issued.  Prints HGI_FUSED PASS / FAIL.
module tb_hgi_fused_record;
`ifdef MUT_SEG
    localparam integer MS = 1;
`else
    localparam integer MS = 0;
`endif
    `include "fu_sizes.svh"
    localparam integer N = 32, M = 8, AW = 24, NR = N / 8, VMA = 18;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [1214:0] recm [0:NREC-1];
    reg [686:0]  expm [0:NREC-1];
    reg [287:0]  casem [0:NCASE-1];
    reg [63:0]   vmim [0:NVMI-1];
    reg [63:0]   vmem [0:NVME-1];
    reg [71:0]   hbmm [0:NHBM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/fu_rec.mem"}, recm); $readmemh({dir, "/fu_exp.mem"}, expm); $readmemh({dir, "/fu_case.mem"}, casem);
        $readmemh({dir, "/fu_vmi.mem"}, vmim); $readmemh({dir, "/fu_vme.mem"}, vmem); $readmemh({dir, "/fu_hbm.mem"}, hbmm);
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [1214:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v, op_v, ne_v; wire [226:0] mv; wire [669:0] w; wire [148:0] ne_job;
    wire [682:0] q_rec; reg mv_done = 0, ne_done = 0, q_done = 0; wire ready, idle, vfault;
    ot_hgi_fused_record #(.MUT_SEG(MS)) u (.clk(clk), .rst_n(rst_n), .cfg_scratch(18'd240000), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_c(cur[895:640]),
        .rec_o(cur[1151:896]), .rec_n_a(cur[1172:1152]), .rec_n_b(cur[1193:1173]), .rec_n_o(cur[1214:1194]),
        .rec_done(done), .rec_fault(fault), .halted(halted), .mv_v(mv_v), .mv_rdy(1'b1), .mv(mv), .mv_done(mv_done),
        .mv_fault(1'b0), .op_v(op_v), .op_rdy(ready), .op_w(w), .su_idle(idle), .su_fault(vfault), .ne_v(ne_v),
        .ne_rdy(1'b1), .ne_job(ne_job), .ne_done(ne_done), .ne_fault(1'b0), .q_rec(q_rec), .q_done(q_done), .q_fault(1'b0));
    // ---- the stream unit + VM
    reg [31:0] vm [0:(1<<VMA)-1];
    wire [N-1:0] vi_re, vm_we, kv_we; wire [N*AW-1:0] vi_addr, vm_waddr, kv_waddr; reg [N*32-1:0] vi_q;
    wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; reg [4*N*32-1:0] rd_q;
    wire [N*32-1:0] vm_wdata, kv_wdata; wire [NR-1:0] res_we; wire [NR*AW-1:0] res_addr; wire [NR*32-1:0] res_data;
    wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire of, ro, de, dr, ds; wire [7:0] es, rs, ss;
    ot_hdc_v41x_vec #(.N(N), .M(M), .LV(7)) dut (
        .clk(clk), .rst_n(rst_n), .go(op_v), .ready(ready), .idle(idle),
        .i_nout(w[0 +: 16]), .i_nin(w[16 +: 16]), .i_asrc(w[32 +: 2]), .i_bsrc(w[34 +: 2]), .i_csrc(w[36 +: 2]),
        .i_dsrc(w[38 +: 2]), .i_abase(w[40 +: 24]), .i_aso(w[64 +: 24]), .i_asi(w[88 +: 24]),
        .i_aibase(w[112 +: 24]), .i_aind(w[136 +: 2]), .i_bbase(w[138 +: 24]), .i_bso(w[162 +: 24]),
        .i_bsi(w[186 +: 24]), .i_bhalf(w[210]), .i_cbase(w[211 +: 24]), .i_cso(w[235 +: 24]),
        .i_csi(w[259 +: 24]), .i_cpair(w[283]), .i_dbase(w[284 +: 24]), .i_dso(w[308 +: 24]),
        .i_dsi(w[332 +: 24]), .i_arnd(w[356]), .i_arelu(w[357]), .i_amin(w[358]), .i_cclip(w[359]),
        .i_m1(w[360 +: 3]), .i_m2(w[363 +: 2]), .i_qm(w[365 +: 3]), .i_ad(w[368 +: 3]), .i_sfu(w[371 +: 3]),
        .i_e1(w[374 +: 3]), .i_e2(w[377 +: 2]), .i_rnd(w[379]), .i_dst(w[380 +: 2]), .i_obase(w[382 +: 24]),
        .i_oso(w[406 +: 24]), .i_osi(w[430 +: 24]), .i_orow(w[454 +: 24]), .i_red(w[478 +: 2]),
        .i_redsq(w[480]), .i_redwhole(w[481]), .i_redtree(w[482]), .i_redrnd(w[483]), .i_rbase(w[484 +: 24]),
        .i_rso(w[508 +: 24]), .i_imm1(w[532 +: 32]), .i_imm2(w[564 +: 32]), .i_imm3(w[596 +: 32]),
        .i_ch_src(w[628 +: 2]), .i_ch_seq(w[630 +: 8]), .i_ch_lead(w[638 +: 16]), .i_ch_mul(w[654 +: 16]),
        .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0), .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src), .rd_q(rd_q),
        .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .res_we(res_we), .res_addr(res_addr), .res_data(res_data), .fault(vfault), .order_fault(of), .emitted(emitted),
        .retire_o(ro), .dbg_emit(de), .dbg_eseq(es), .dbg_ret(dr), .dbg_rseq(rs), .dbg_res(ds), .dbg_sseq(ss));
    integer l, s;
    always @(posedge clk) begin
        for (l = 0; l < N; l = l + 1) begin
            if (vi_re[l]) vi_q[32*l +: 32] <= vm[vi_addr[l*AW +: AW] & ((1<<VMA)-1)];
            for (s = 0; s < 4; s = s + 1)
                if (rd_re[4*l + s]) rd_q[(4*l + s)*32 +: 32] <= vm[rd_addr[(4*l + s)*AW +: AW] & ((1<<VMA)-1)];
        end
        for (l = 0; l < N; l = l + 1) if (vm_we[l]) vm[vm_waddr[l*AW +: AW] & ((1<<VMA)-1)] <= vm_wdata[32*l +: 32];
        for (l = 0; l < NR; l = l + 1) if (res_we[l]) vm[res_addr[l*AW +: AW] & ((1<<VMA)-1)] <= res_data[32*l +: 32];
    end
    // ---- behavioural DMA mover: LOAD HBM {BF16 | FP32} -> VM FP32 (the peer, stubbed)
    reg [31:0] hbm [longint];
    integer e, mlat = -1; longint ba; reg [31:0] hw;
    always @(posedge clk) begin
        mv_done <= 0;
        if (rst_n && mv_v) begin
            if (mv[1:0] != 2'd0 || mv[94:93] != 2'd1 || mv[205:186] != 20'd1) begin $display("ERR mover: unexpected move"); errors = errors + 1; end
            for (e = 0; e < mv[226:206]; e = e + 1) begin
                ba = (mv[4:2] == 3'd1) ? mv[44:5] + 2 * e : mv[44:5] + 4 * e;
                hw = hbm.exists(ba >> 2) ? hbm[ba >> 2] : 32'd0;
                vm[mv[115:98] + e] = (mv[4:2] == 3'd1) ? {(ba[1] ? hw[31:16] : hw[15:0]), 16'd0} : hw;
            end
            mlat = 5;
        end else if (mlat > 0) mlat = mlat - 1;
        else if (mlat == 0) begin mv_done <= 1; mlat = -1; end
    end
    // ---- stub norm engine / quant (retire after a latency) + checks
    integer k = 0, base = 0, nlat = -1, qlat = -1, issued = 0, nfault = 0;
    always @(posedge clk) begin
        ne_done <= 0; q_done <= 0;
        if (rst_n && ne_v) begin
            issued = issued + 1; nlat = 7;
            if (expm[base + k][686:683] != 4'd1 || ne_job !== expm[base + k][148:0]) begin
                $display("ERR norm-engine job mismatch at record %0d", base + k); errors = errors + 1; end
        end else if (nlat > 0) nlat = nlat - 1; else if (nlat == 0) begin ne_done <= 1; nlat = -1; end
        if (rst_n && q_rec[0]) begin
            issued = issued + 1; qlat = 9;
            if (expm[base + k][686:683] != 4'd2 || q_rec !== expm[base + k][682:0]) begin
                $display("ERR quant forward mismatch at record %0d", base + k); errors = errors + 1; end
        end else if (qlat > 0) qlat = qlat - 1; else if (qlat == 0) begin q_done <= 1; qlat = -1; end
        if (rst_n && op_v && ready) issued = issued + 1;
        if (rst_n && done) begin
            if (nlat != -1 || qlat != -1 || mlat != -1 || !idle) begin $display("ERR record %0d retired early", base + k); errors = errors + 1; end
            k = k + 1;
        end
        if (rst_n && fault) begin nfault = nfault + 1;
            if (nfault == 1) $display("FAULT at record %0d: adapter state %0d, su halted %0d, vec fault %0d", base + k, u.st, u.s_halt, vfault); end
        if (rst_n && u.s_fault) $display("SU FAULT: fused state %0d, su bad_q %0d exec %0d, vec fault seen %0d", u.st, u.u_su.bad_q, u.u_su.exec, u.u_su.in_fault);
        if (rst_n && vfault) $display("VEC FAULT at %0d (fused state %0d)", cyc, u.st);
    end
    integer c, j, kind, r0, nr, vi0, nvi, ve0, nve, h0, nh, t, runs = 0, negs = 0, words = 0, a;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][287:256]; r0 = casem[c][255:224]; nr = casem[c][223:192]; vi0 = casem[c][191:160];
            nvi = casem[c][159:128]; ve0 = casem[c][127:96]; nve = casem[c][95:64]; h0 = casem[c][63:32]; nh = casem[c][31:0];
            rst_n = 0;
            for (a = 0; a < (1 << VMA); a = a + 1) vm[a] = 0;
            hbm.delete();
            for (j = 0; j < nvi; j = j + 1) vm[vmim[vi0 + j][63:32]] = vmim[vi0 + j][31:0];
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][71:32]] = hbmm[h0 + j][31:0];
            repeat (3) @(posedge clk); rst_n = 1; @(posedge clk);
            base = r0; k = 0; issued = 0; nfault = 0;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 400000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nfault == 0 && t < 400000) begin @(posedge clk); t = t + 1; end
            repeat (20) @(posedge clk);
            if (kind == 3) begin
                if (nfault != 1 || issued != 0 || !halted) begin $display("ERR negative case %0d", c); errors = errors + 1; end
                else negs = negs + 1;
            end else begin
                if (k != nr || nfault != 0) begin $display("ERR case %0d: retired %0d of %0d faults %0d", c, k, nr, nfault); errors = errors + 1; end
                for (j = 0; j < nve; j = j + 1) if (vm[vmem[ve0 + j][63:32]] !== vmem[ve0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], vm[vmem[ve0 + j][63:32]], vmem[ve0 + j][31:0]);
                    errors = errors + 1;
                end
                words = words + nve; runs = runs + nr;
            end
        end
        $display("summary: %0d records run (%0d VM words exact), %0d negatives refused", runs, words, negs);
        if (errors == 0) $display("HGI_FUSED PASS"); else $display("HGI_FUSED FAIL errors=%0d", errors);
        $finish;
    end
endmodule
