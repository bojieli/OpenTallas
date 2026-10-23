`timescale 1ns/1ps
// RTLGAP-SO (10-21): L0 normalised SO on the 16 REAL per-slice SM shares ot_s81_su_sms (-DSU_SMU_T, the share every
// dsdv_svc_rs instantiates; cfg_g = the slice's tile = head g).  Images: tools/s81_dv/layer_prog/svc/so_bench.py.
//   qcyc / qwd   the SMJ q words (SE kind 4 frame of lower_svc + the SO programme of lower_svc.so_frames: SMJ kind 5 +
//                16 operand frames = 534 words, operand payload = the REAL ALLQ P.V words of tb_svc_lower, transposed)
//   secyc/serow  the SE operand rows of every slice (the REAL svc SE assembler rows of the same tb_svc_lower run)
//   eexp / oexp  expected SE e rows (fixture attn.exp FP32) and SO o rows (fixture attn.normalize.unrope BF16)
// Every slice decodes the q words exactly as dsdv_svc_att.sv (frame parser; SMJ: sm_st = hdr[0], sm_kind = hdr[4:1],
// sm_jid = hdr[12:5]; payload: sm_rv = !hdr[13] || hdr[14 + tile], sm_rp = !hdr[13], sm_rj = payload index, sm_rd = word).
// PASS = per head 8 SE rows (addr SE obase + 16 n + g, mask FFFF, data = attn.exp) and 32 SO rows (addr SO obase + 8 k
// + g / 2, mask 00FF / FF00 by head parity, half = attn.normalize.unrope dims 16 k .. 16 k + 15) bit-exact, o row k a
// CONSTANT latency after operand row k, o_den reached, no o_fu / o_fo.  Prints "SOGOLD ... verdict=PASS|FAIL" last.
module tb_so_golden;
    localparam integer H = 16, QMAX = 1024;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst = 0;
    integer cyc = 0;
    reg [1023:0] dir;
    reg [31:0] meta [0:15];
    reg [31:0] qcyc [0:QMAX-1]; reg [511:0] qwd [0:QMAX-1];
    reg [31:0] secyc [0:63]; reg [511:0] serow [0:16*64-1];
    reg [255:0] oexp [0:16*32-1]; reg [511:0] eexp [0:16*64-1];
    integer NQ, NV, SO_OB, SE_OB;
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("+dir missing"); $finish; end
        $readmemh({dir, "/meta.hex"}, meta);
        NQ = meta[0]; NV = meta[1]; SO_OB = meta[2]; SE_OB = meta[3];
        $readmemh({dir, "/qcyc.hex"}, qcyc, 0, NQ - 1);
        $readmemh({dir, "/qwd.hex"}, qwd, 0, NQ - 1);
        $readmemh({dir, "/secyc.hex"}, secyc, 0, NV - 1);
        $readmemh({dir, "/serow.hex"}, serow, 0, 16 * NV - 1);
        $readmemh({dir, "/oexp.hex"}, oexp);
        $readmemh({dir, "/eexp.hex"}, eexp, 0, 16 * NV - 1);
        $display("SOGOLD_IMG dir=%0s nq=%0d nv=%0d so_obase=%0h se_obase=%0h", dir, NQ, NV, SO_OB, SE_OB);
    end
    // ---------------- stimulus: q words and SE rows at their cycles (never early, never late)
    reg q_v = 0; reg [511:0] q_d = 0; integer qi = 0, si = 0, late = 0; reg se_v = 0; integer se_r = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst <= 1;
        q_v <= 0; se_v <= 0;
        if (qi < NQ && cyc == qcyc[qi]) begin q_v <= 1; q_d <= qwd[qi]; qi = qi + 1; end
        else if (qi < NQ && cyc > qcyc[qi]) late = late + 1;
        if (si < NV && cyc == secyc[si]) begin se_v <= 1; se_r <= si; si = si + 1; end
    end
    // ---------------- 16 slices: dsdv_svc_att SMJ decode + the real SM share
    wire [15:0] w_v, o_fu, o_fo, o_al, o_den; wire [13:0] w_a [0:15]; wire [15:0] w_m [0:15]; wire [511:0] w_d [0:15];
    wire [7:0] o_rj [0:15];
    wire [15:0] op_tick;                                     // an SO operand row reaches this slice's share pins
    genvar g;
    generate for (g = 0; g < H; g = g + 1) begin : g_s
        reg in_frame; reg [11:0] left; reg [3:0] f_type; reg f_mine; reg [511:0] f_hdr; reg [11:0] f_idx;
        wire [3:0] h_type = q_d[511:508]; wire [3:0] h_mask = q_d[506:503]; wire [11:0] h_len = q_d[491:480];
        wire is_hdr = q_v && !in_frame, is_pay = q_v && in_frame;
        wire hdr_mine = is_hdr && h_mask[0], pay_mine = is_pay && f_mine;
        always @(posedge clk or negedge rst) begin
            if (!rst) begin in_frame <= 0; left <= 0; f_type <= 0; f_mine <= 0; f_idx <= 0; end
            else if (is_hdr) begin f_type <= h_type; f_mine <= h_mask[0]; f_idx <= 0; left <= h_len; in_frame <= h_len != 0; end
            else if (is_pay) begin f_idx <= f_idx + 1'b1; left <= left - 1'b1; if (left == 12'd1) in_frame <= 1'b0; end
        end
        always @(posedge clk) if (is_hdr) f_hdr <= q_d;
        reg sm_st, sm_rv, sm_rp; reg [3:0] sm_kind; reg [7:0] sm_jid; reg [2:0] sm_rj; reg [511:0] sm_rd; reg opr;
        always @(posedge clk or negedge rst) begin
            if (!rst) begin sm_st <= 0; sm_rv <= 0; sm_rp <= 0; sm_rj <= 0; sm_kind <= 0; sm_jid <= 0; sm_rd <= 0; opr <= 0; end
            else begin
                sm_st <= 1'b0; sm_rv <= 1'b0; opr <= 1'b0;
                if (hdr_mine && h_type == 4'd9) begin sm_st <= q_d[0]; sm_kind <= q_d[4:1]; sm_jid <= q_d[12:5]; end
                if (pay_mine && f_type == 4'd9) begin
                    sm_rv <= !f_hdr[13] || f_hdr[14 + g]; sm_rp <= !f_hdr[13]; sm_rj <= 3'(f_idx); sm_rd <= q_d;
                    opr <= f_hdr[13] && f_hdr[14 + g];
                end
                if (se_v) begin sm_rv <= 1'b1; sm_rp <= 1'b0; sm_rj <= 3'd0; sm_rd <= serow[g * NV + se_r]; end
            end
        end
        assign op_tick[g] = opr;
        ot_s81_su_sms #(.MUT(0)) u_sms (
            .clk(clk), .rst_in(rst), .cfg_g(4'(g)), .j_st(sm_st), .j_kind(sm_kind), .j_jid(sm_jid),
            .r_v(sm_rv), .r_p(sm_rp), .r_j(sm_rj), .r_d(sm_rd),
            .w_v(w_v[g]), .w_a(w_a[g]), .w_m(w_m[g]), .w_d(w_d[g]),
            .o_fu(o_fu[g]), .o_fo(o_fo[g]), .o_alive(o_al[g]), .o_den(o_den[g]), .o_rjid(o_rj[g]));
    end endgenerate
    // ---------------- checks
    integer nrow [0:15], err = 0, se_chk = 0, so_chk = 0, lat = -1, lat_bad = 0, den_seen = 0, rope_err = 0, plain_err = 0;
    integer opq [0:15][$];
    integer last_q = 0;
    initial for (int s = 0; s < 16; s++) nrow[s] = 0;
    always @(posedge clk) begin
        for (int s = 0; s < 16; s++) begin
            if (op_tick[s]) opq[s].push_back(cyc);
            if (o_den[s]) den_seen = den_seen | (1 << s);
            if (w_v[s]) begin
                if (nrow[s] < NV) begin
                    se_chk = se_chk + 1;
                    if (w_m[s] !== 16'hFFFF || w_a[s] !== 14'(SE_OB + 16 * nrow[s] + s) || w_d[s] !== eexp[s * NV + nrow[s]]) begin
                        err = err + 1;
                        if (err < 10) $display("SE ROW MISMATCH head %0d row %0d a %0h m %0h", s, nrow[s], w_a[s], w_m[s]);
                    end
                end else begin
                    integer k, x; reg [255:0] hv; k = nrow[s] - NV;
                    so_chk = so_chk + 1;
                    hv = s[0] ? w_d[s][511:256] : w_d[s][255:0];
                    if (k >= 32 || w_m[s] !== (s[0] ? 16'hFF00 : 16'h00FF) || w_a[s] !== 14'(SO_OB + 8 * k + s / 2) ||
                        hv !== oexp[s * 32 + k]) begin
                        err = err + 1;
                        if (k >= 28) rope_err = rope_err + 1; else plain_err = plain_err + 1;
                        if (err < 10) $display("SO ROW MISMATCH head %0d row %0d (dims %0d..%0d) a %0h m %0h got %064h exp %064h",
                                               s, k, 16 * k, 16 * k + 15, w_a[s], w_m[s], hv, oexp[s * 32 + k]);
                    end
                    if (opq[s].size() == 0) lat_bad = lat_bad + 1;
                    else begin x = cyc - opq[s].pop_front(); if (lat < 0) lat = x; else if (x != lat) lat_bad = lat_bad + 1; end
                end
                nrow[s] = nrow[s] + 1;
            end
        end
        if (cyc == 10) last_q = qcyc[NQ - 1];
        if (cyc > 10 && cyc >= last_q + 400) begin
            integer rows_bad; rows_bad = 0;
            for (int s = 0; s < 16; s++) if (nrow[s] != NV + 32) rows_bad = rows_bad + 1;
            $display("SOGOLD se_checked=%0d so_checked=%0d errors=%0d rope_row_errors=%0d plain_row_errors=%0d rows_bad=%0d so_latency=%0d lat_bad=%0d den_mask=%04x fu=%04x fo=%04x late_q=%0d q_sent=%0d/%0d cycles=%0d verdict=%s",
                se_chk, so_chk, err, rope_err, plain_err, rows_bad, lat, lat_bad, den_seen[15:0], o_fu, o_fo, late, qi, NQ, cyc,
                (err == 0 && rows_bad == 0 && se_chk == 16 * NV && so_chk == 16 * 32 && lat_bad == 0 && lat > 0 &&
                 den_seen[15:0] == 16'hFFFF && o_fu == 0 && o_fo == 0 && late == 0 && qi == NQ) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
