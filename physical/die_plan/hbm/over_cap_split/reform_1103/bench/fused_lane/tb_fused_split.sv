`timescale 1ns/1ps
`default_nettype none
// tb_fused_split (DIE-HBM-61/SPLIT 11-03): tb_hnx_fused (HBM-NEXT-UNITS-FUSED 2026-10-19, f6d6de957c) on the face-shelled
// bench tops of mk_top.py (`TOPM = ot_hnx_fused_top_k | _s); VM model returns VMD = RR - 2 edges after rq (lane faces).
// `SHADOW: a reference kit lane (hnx_fused_lane) shadows lane 0 on the SAME inputs (dn / r relays, rr) and every lane-0
// output is compared under the declared shift map: rq +0, scalar up (up_t 0) +0, chunk-sum up (up_t 1) +SH, wq_* +SH,
// fin +SH, flt +SH  (SH = 4).  Prints SHADOW PASS/FAIL with event counts.
// Original header: tb_hnx_fused (HBM-NEXT-UNITS-FUSED 2026-10-19): one N-row FUSED record on ot_hnx_fused_top against 32 fixed-latency
// VM bank lanes (bank L serves only lane L: a request on another bank is an error), vectors from
// tools/hbm_next/hnx_fused_vec.py (golden hdc_golden_v41 chunk8).  Run in the case dir: +NVMI= +NVME= (plus.txt).
// Prints HNX_FUSED_CYCLES (job launch edge -> done edge) and HNX_FUSED PASS / FAIL (exact words, no fault, every
// output sector written once, no bank violation).
module tb_fused_split #(parameter integer KX = 4, RR = 10, RL = 4, MUT = 0, NMAX = 8, SMUT = 0, SH = 4);
    localparam integer VMD = RR - 2;
    reg clk = 1'b0, rst_n = 1'b0;
    always #1 clk = ~clk;
    reg job_v = 1'b0; reg [216:0] job;
    wire done, fault, busy;
    wire [31:0] rq_v, wq_v; wire [32*16-1:0] rq_s, wq_s; wire [32*256-1:0] wq_d;
    reg [31:0] rr_v; reg [32*256-1:0] rr_d;
    `TOPM #(.KX(KX), .RR(RR), .RL(RL), .NMAX(NMAX), .MUT(MUT)`ifdef SPLIT , .SMUT(SMUT)`endif ) dut (.clk(clk), .rst_n(rst_n), .job_v(job_v),
        .job(job), .done(done), .fault(fault), .busy(busy), .rq_v(rq_v), .rq_s(rq_s), .rr_v(rr_v), .rr_d(rr_d),
        .wq_v(wq_v), .wq_s(wq_s), .wq_d(wq_d));
    reg [255:0] vm [0:65535];
    reg [256:0] dl [0:31][0:VMD-1];
    integer bankerr = 0, nwr = 0, nrd = 0;
    always @(posedge clk) begin
        for (integer L = 0; L < 32; L = L + 1) begin
            dl[L][0] <= {rq_v[L], vm[rq_s[L*16 +: 16]]};
            for (integer i = 1; i < VMD; i = i + 1) dl[L][i] <= dl[L][i - 1];
            if (rq_v[L]) begin nrd = nrd + 1; if (rq_s[L*16 +: 5] != 5'(L)) bankerr = bankerr + 1; end
            if (wq_v[L]) begin
                vm[wq_s[L*16 +: 16]] <= wq_d[L*256 +: 256]; nwr = nwr + 1;
                if (wq_s[L*16 +: 5] != 5'(L)) bankerr = bankerr + 1;
            end
        end
    end
    always @* for (integer L = 0; L < 32; L = L + 1) begin rr_v[L] = dl[L][VMD-1][256]; rr_d[L*256 +: 256] = dl[L][VMD-1][255:0]; end


`ifdef SHADOW
    // ---- reference kit lane shadowing lane 0 (same dn / r / rr inputs as the DUT's lane 0)
    wire s_rqv, s_wqv, s_upv, s_upt, s_fin, s_flt; wire [15:0] s_rqs, s_wqs; wire [255:0] s_wqd, s_upd; wire [9:0] s_upx;
    hnx_fused_lane u_sh (.clk(clk), .rst_n(rst_n), .lid(5'd0), .rq_v(s_rqv), .rq_s(s_rqs), .rr_v(rr_v[0]), .rr_d(rr_d[255:0]),
        .wq_v(s_wqv), .wq_s(s_wqs), .wq_d(s_wqd), .dn_v(dut.g_ln[0].dv), .dn_op(dut.g_ln[0].dd[138:136]),
        .dn_x(dut.g_ln[0].dd[135:128]), .dn_d(dut.g_ln[0].dd[127:0]), .r_v(dut.g_ln[0].lrv), .r_d(dut.g_ln[0].lr),
        .up_v(s_upv), .up_t(s_upt), .up_x(s_upx), .up_d(s_upd), .fin(s_fin), .flt(s_flt));
    // shifted reference streams: {wq_v, wq_s, wq_d}, {cs up v, x, d}, fin, flt
    localparam integer SW = 1 + 16 + 256 + 1 + 10 + 256 + 1 + 1;
    reg [SW-1:0] sh [0:SH];
    always @* sh[0] = {s_wqv, s_wqs, s_wqd, s_upv && s_upt, s_upx, s_upd, s_fin, s_flt};
    always @(posedge clk) for (integer i = 1; i <= SH; i = i + 1) sh[i] <= sh[i - 1];
    wire [SW-1:0] rs = sh[SH];
    wire r_wqv = rs[SW-1]; wire [15:0] r_wqs = rs[SW-2 -: 16]; wire [255:0] r_wqd = rs[SW-18 -: 256];
    wire r_csv = rs[SW-274]; wire [9:0] r_upx = rs[SW-275 -: 10]; wire [255:0] r_upd = rs[SW-285 -: 256];
    wire r_fin = rs[1]; wire r_flt = rs[0];
    wire d_upv = dut.g_ln[0].uv, d_upt = dut.g_ln[0].ut; wire [9:0] d_upx = dut.g_ln[0].ux; wire [255:0] d_upd = dut.g_ln[0].ud;
    integer se = 0, n_rq = 0, n_wq = 0, n_cs = 0, n_sc = 0, n_fin = 0, nz_wq = 0;
    always @(posedge clk) if (rst_n && cc > SH + 4) begin
        if (s_rqv !== rq_v[0] || (s_rqv && s_rqs !== rq_s[15:0])) begin se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d rq", cc); end
        if (s_rqv) n_rq = n_rq + 1;
        if (r_wqv !== wq_v[0] || (r_wqv && (r_wqs !== wq_s[15:0] || r_wqd !== wq_d[255:0]))) begin
            se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d wq ref_v=%b dut_v=%b", cc, r_wqv, wq_v[0]); end
        if (r_wqv) begin n_wq = n_wq + 1; if (r_wqd != 256'd0) nz_wq = nz_wq + 1; end
        if ((s_upv && !s_upt) !== (d_upv && !d_upt) || (s_upv && !s_upt && (s_upx !== d_upx || s_upd !== d_upd))) begin
            se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d scalar up", cc); end
        if (s_upv && !s_upt) n_sc = n_sc + 1;
        if (r_csv !== (d_upv && d_upt) || (r_csv && (r_upx !== d_upx || r_upd[31:0] !== d_upd[31:0]))) begin
            se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d chunk-sum up ref=%b dut=%b", cc, r_csv, d_upv && d_upt); end
        if (r_csv) n_cs = n_cs + 1;
        if (r_fin !== dut.g_ln[0].fn) begin se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d fin", cc); end
        if (r_fin) n_fin = n_fin + 1;
        if (r_flt !== dut.g_ln[0].fl) begin se = se + 1; if (se <= 5) $display("SHADOW MISMATCH cc=%0d flt ref=%b dut=%b", cc, r_flt, dut.g_ln[0].fl); end
    end
`endif
    localparam integer MAXE = 262144;
    reg [51:0] vmi [0:MAXE-1]; reg [51:0] vme [0:MAXE-1]; reg [219:0] jm [0:0];
    integer nvmi, nvme, cyc, mism, nflt = 0, ndone = 0, rgap, nrow, cc = 0, t0c = 0, t1c = 0;
    reg seen = 1'b0;
    always @(posedge clk) begin
        cc <= cc + 1;
        if (job_v) t0c <= cc;
        if ((done || fault) && !seen) begin seen <= 1'b1; t1c <= cc; if (fault) nflt <= 1; else ndone <= 1; end
    end
    reg [8*8-1:0] opn;
    initial begin
        if (!$value$plusargs("NVMI=%d", nvmi)) nvmi = 0;
        if (!$value$plusargs("NVME=%d", nvme)) nvme = 0;
        if (!$value$plusargs("RGAP=%d", rgap)) rgap = 0;
        if (!$value$plusargs("N=%d", nrow)) nrow = 0;
        if (!$value$plusargs("OP=%s", opn)) opn = "?";
        for (integer s = 0; s < 65536; s = s + 1) vm[s] = '0;
        $readmemh("vmi.mem", vmi, 0, nvmi - 1);
        $readmemh("vme.mem", vme, 0, nvme - 1);
        $readmemh("job.mem", jm);
        for (integer i = 0; i < nvmi; i = i + 1) vm[vmi[i][50:35]][32*vmi[i][34:32] +: 32] = vmi[i][31:0];
        job = jm[0][216:0];
        repeat (6) @(posedge clk);
        rst_n = 1'b1;
        repeat (8) @(posedge clk);
        #0.1 job_v = 1'b1;
        @(posedge clk); #0.1 job_v = 1'b0;
        while (!seen && cc < 60000) @(posedge clk);
        repeat (4 * RR + 8) @(posedge clk);
        cyc = t1c - 1 - t0c;
        mism = 0;
        for (integer i = 0; i < nvme; i = i + 1)
            if (vm[vme[i][50:35]][32*vme[i][34:32] +: 32] !== vme[i][31:0]) begin
                if (mism < 5) $display("MISMATCH word %0d: got %08h exp %08h", vme[i][50:32],
                                       vm[vme[i][50:35]][32*vme[i][34:32] +: 32], vme[i][31:0]);
                mism = mism + 1;
            end
        $display("HNX_FUSED_CYCLES op=%0s N=%0d rgap=%0d KX=%0d MUT=%0d cycles=%0d done=%0d fault=%0d reads=%0d writes=%0d",
                 opn, nrow, rgap, KX, MUT, cyc, ndone, nflt, nrd, nwr);
        if (ndone == 1 && nflt == 0 && mism == 0 && bankerr == 0 && nwr * 8 == nvme && nvme > 0)
            $display("HNX_FUSED PASS op=%0s N=%0d words=%0d", opn, nrow, nvme);
        else
            $display("HNX_FUSED FAIL op=%0s N=%0d mism=%0d fault=%0d done=%0d bankerr=%0d writes=%0d expect_sectors=%0d",
                     opn, nrow, mism, nflt, ndone, bankerr, nwr, nvme / 8);
`ifdef SHADOW
        if (se == 0 && n_rq > 0 && n_wq > 0 && n_fin > 0) $display("SHADOW PASS shift=%0d rq=%0d wq=%0d wq_nonzero=%0d chunk_ups=%0d scalar_ups=%0d fin=%0d", SH, n_rq, n_wq, nz_wq, n_cs, n_sc, n_fin);
        else $display("SHADOW FAIL mismatches=%0d rq=%0d wq=%0d chunk_ups=%0d scalar_ups=%0d fin=%0d", se, n_rq, n_wq, n_cs, n_sc, n_fin);
`endif
        $finish;
    end
endmodule
`default_nettype wire
