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
    hfd_quant dut (.ck(clk), .rst(!rst_n), .f_hgi_cmdproc(rec), .t_hgi_cmdproc(ret), .t_hgi_vmq(qq), .f_hgi_vmr(qr),
        .t_hgi_vmq_fused(fq), .f_hgi_vmr_fused(fr), .t_hgi_vmq_fmv(mq), .f_hgi_vmr_fmv(mr),
        .t_lgE_rup(rup), .f_lgE_rdn(rdn), .t_lgE_wup(wup), .f_lgE_wdn(wdn), .t_hgi_fmkq(xq), .f_hgi_fmkr(xr));
    // ---- lgE: lane head (FUSED = slot 2; slots 0 / 1 idle) and the VM unit
    wire [2:0] rgnt, wgnt; wire [3*32-1:0] rcr, wcr, wdone; wire [3*32*257-1:0] rrs;
    wire [32*16-1:0] g_rq; wire [31:0] g_rcr, g_wcr, g_wdone; wire [32*257-1:0] g_rr; wire [32*280-1:0] g_wq;
    ot_hgi_vm_lanearb #(.K(3), .REQW(16), .RSPW(257), .RLY(2)) u_ar (.clk(clk), .rst_n(rst_n), .c_req({rup[0], 2'b00}),
        .c_gnt(rgnt), .c_q({rup[512:1], 1024'd0}), .c_cr(rcr), .c_rsp(rrs), .g_q(g_rq), .g_cr(g_rcr), .g_rsp(g_rr));
    ot_hgi_vm_lanearb #(.K(3), .REQW(280), .RSPW(1), .RLY(2)) u_aw (.clk(clk), .rst_n(rst_n), .c_req({wup[0], 2'b00}),
        .c_gnt(wgnt), .c_q({wup[8960:1], {2*32*280{1'b0}}}), .c_cr(wcr), .c_rsp(wdone), .g_q(g_wq), .g_cr(g_wcr), .g_rsp(g_wdone));
    assign rdn = {rrs[2*32*257 +: 32*257], rcr[64 +: 32], rgnt[2]};
    assign wdn = {wdone[64 +: 32], wcr[64 +: 32], wgnt[2]};
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
    // ---- the CP's unit-4 dispatch: one credit
    integer k, nf; reg credit = 1;
    always @(posedge clk) begin
        if (rst_n && ret[1]) k = k + 1;
        if (rst_n && ret[2]) nf = nf + 1;
        if (!rst_n) credit <= 1; else if (ret[1] || ret[2]) credit <= 1; else if (rec[0]) credit <= 0;
    end
    integer c, j, t, kind, r0, nr, vi0, nvi, ve0, nve, h0, nh, words = 0, cases = 0, t0;
    reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][287:256]; r0 = casem[c][255:224]; nr = casem[c][223:192]; vi0 = casem[c][191:160];
            nvi = casem[c][159:128]; ve0 = casem[c][127:96]; nve = casem[c][95:64]; h0 = casem[c][63:32]; nh = casem[c][31:0];
            if (kind != 0) continue;
            rst_n = 0; hbm.delete(); repeat (4) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][71:32]] = hbmm[h0 + j][31:0];
            k = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                t = 0; while (!(credit && ret[0]) && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(negedge clk); rec = {recm[r0 + j], 1'b1};
                @(negedge clk); rec[0] = 1'b0;
                t = 0; while (credit && t < 100) begin @(negedge clk); t = t + 1; end      // the credit is taken
            end
            t = 0; while (k < nr && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            if (sflt) begin $display("ERR case %0d: remote lane server overflow", c); errors = errors + 1; end
            $display("case %0d: %0d records retired in %0d cycles (die ports, real VM, remote kport lane)", c, k, cyc - t0); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
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
