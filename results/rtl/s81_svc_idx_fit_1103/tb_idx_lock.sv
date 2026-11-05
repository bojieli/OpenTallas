`timescale 1ns/1ps
// S81 svc_lo idx fit (DIE-S81-51/MEM, 2026-11-03): old-vs-new lockstep of the paired index reader.
// Stands in for dsdv_idx_rg3 in tb_dsdv_idx_rg3 (same ports as the rtl/ reader, st[0] = fault): drives the bench from
// the kit reader (portfix178 dsdv_idx_rg3, 13 x 1024x256) and compares the fit child (dsdv_idx_rg3_fit) on every
// output every edge.  Coverage counters show that each right-sized memory range was written / read.
module idx_lock #(
    parameter integer MUT = 0, parameter bit SRAM_MACRO = 0, parameter integer DQR = 24, parameter integer IQD = 512,
    parameter integer SQD = 256, parameter integer LFD = 256, parameter integer EL = 124, parameter integer OH = 2,
    parameter integer RH = 2, parameter integer IH = 0, parameter integer KR = 0,
    parameter bit LK = 0                     // 1: also the behavioural fit control + the NM mutants (one reader)
) (
    input  wire          ck, input wire rst, input wire [3:0] sid,
    input  wire [512:0]  qi, output wire [512:0] qo, input wire [275:0] si, output wire [275:0] so,
    output wire [183:0]  rqo, input wire [1087:0] rri, output wire [9:0] st
);
    wire [512:0] qo_f; wire [275:0] so_f; wire [183:0] rqo_f; wire f_r, f_f;
    dsdv_idx_rg3 #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH),
        .RH(RH), .IH(IH), .KR(KR)) u_ref (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(qo), .si(si), .so(so), .rqo(rqo),
        .rri(rri), .fault(f_r));
    dsdv_idx_rg3_fit #(.MUT(MUT), .SRAM_MACRO(SRAM_MACRO), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH),
        .RH(RH), .IH(IH), .KR(KR)) u_fit (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(qo_f), .si(si), .so(so_f),
        .rqo(rqo_f), .rri(rri), .fault(f_f));
    assign st = {9'd0, f_r};
    // behavioural fit control (must match) and mutants (each must mismatch): SRAM_MACRO 0 masters, sized as named
    localparam integer NM = 8;               // [0] control, [1..7] mutants (run_lock.sh MUTS)
    wire [NM-1:0] dm;
    genvar gm;
    generate if (LK) begin : g_mut
        for (gm = 0; gm < NM; gm = gm + 1) begin : g_m
            wire [512:0] q_; wire [275:0] s_; wire [183:0] r_; wire f_;
            if (gm == 0) begin : g0 dsdv_idx_rg3_fit  #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 1) begin : g1 dsdv_idx_rg3_fit_m1 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 2) begin : g2 dsdv_idx_rg3_fit_m2 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 3) begin : g3 dsdv_idx_rg3_fit_m3 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 4) begin : g4 dsdv_idx_rg3_fit_m4 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 5) begin : g5 dsdv_idx_rg3_fit_m5 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 6) begin : g6 dsdv_idx_rg3_fit_m6 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            if (gm == 7) begin : g7 dsdv_idx_rg3_fit_m7 #(.MUT(MUT), .SRAM_MACRO(1'b0), .DQR(DQR), .IQD(IQD), .SQD(SQD), .LFD(LFD), .EL(EL), .OH(OH), .RH(RH), .IH(IH), .KR(KR)) u (.ck(ck), .rst(rst), .sid(sid), .qi(qi), .qo(q_), .si(si), .so(s_), .rqo(r_), .rri(rri), .fault(f_)); end
            assign dm[gm] = {qo, so, rqo, f_r} !== {q_, s_, r_, f_};
        end
    end else begin : g_nomut
        assign dm = '0;
    end endgenerate
    longint mm [0:NM-1];
    initial for (int k = 0; k < NM; k++) mm[k] = 0;
    always @(negedge ck) if (rst) for (int k = 0; k < NM; k++) if (dm[k]) mm[k] = mm[k] + 1;
    final if (LK) for (int k = 0; k < NM; k++) $display("IDXLOCK_MUT sid %0d m%0d mis %0d", sid, k, mm[k]);
    longint nc = 0, nm = 0, h0lo = 0, h0sc = 0, h0g = 0, h1 = 0, lfw = 0, lfr = 0, iqw = 0, sqw = 0, h0r = 0, h1r = 0;
    integer i;
    always @(negedge ck) if (rst) begin
        nc = nc + 1;
        if ({qo, so, rqo, f_r} !== {qo_f, so_f, rqo_f, f_f}) begin
            nm = nm + 1;
            if (nm <= 4) $display("IDXLOCK MISMATCH sid %0d t %0t qo %0d so %0d rqo %0d fault %0d", sid, $time,
                qo !== qo_f, so !== so_f, rqo !== rqo_f, f_r !== f_f);
        end
    end
    // coverage on the kit reader's memory pins (identical stimulus drives the fit child)
    wire [3:0] w0 = {u_ref.g_land[3].u_h0.we, u_ref.g_land[2].u_h0.we, u_ref.g_land[1].u_h0.we, u_ref.g_land[0].u_h0.we};
    wire [3:0] w1 = {u_ref.g_land[3].u_h1.we, u_ref.g_land[2].u_h1.we, u_ref.g_land[1].u_h1.we, u_ref.g_land[0].u_h1.we};
    wire [3:0] r0 = {u_ref.g_land[3].u_h0.re, u_ref.g_land[2].u_h0.re, u_ref.g_land[1].u_h0.re, u_ref.g_land[0].u_h0.re};
    wire [3:0] r1 = {u_ref.g_land[3].u_h1.re, u_ref.g_land[2].u_h1.re, u_ref.g_land[1].u_h1.re, u_ref.g_land[0].u_h1.re};
    wire [9:0] a0 [0:3];
    assign a0[0] = u_ref.g_land[0].u_h0.wa; assign a0[1] = u_ref.g_land[1].u_h0.wa;
    assign a0[2] = u_ref.g_land[2].u_h0.wa; assign a0[3] = u_ref.g_land[3].u_h0.wa;
    always @(posedge ck) if (rst) begin
        for (i = 0; i < 4; i = i + 1) begin
            if (w0[i] && a0[i] < 10'd256) h0lo = h0lo + 1;
            if (w0[i] && a0[i] >= 10'd256 && a0[i] < 10'd512) h0sc = h0sc + 1;
            if (w0[i] && a0[i] >= 10'd512) h0g = h0g + 1;
            if (w1[i]) h1 = h1 + 1;
            if (r0[i]) h0r = h0r + 1;
            if (r1[i]) h1r = h1r + 1;
        end
        if (u_ref.g_lm[0].u_mem.we) lfw = lfw + 1;
        if (u_ref.g_lm[0].u_mem.re) lfr = lfr + 1;
        if (u_ref.u_iq.we) iqw = iqw + 1;
        if (u_ref.u_sq.we) sqw = sqw + 1;
    end
    final $display("IDXLOCK sid %0d cyc %0d mis %0d h0_lo %0d h0_scan %0d h0_gath %0d h1 %0d h0_rd %0d h1_rd %0d lf_w %0d lf_r %0d iq_w %0d sq_w %0d",
        sid, nc, nm, h0lo, h0sc, h0g, h1, h0r, h1r, lfw, lfr, iqw, sqw);
endmodule
