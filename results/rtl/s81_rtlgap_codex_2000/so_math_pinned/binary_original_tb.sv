`timescale 1ns/1ps
// RTLGAP-SO (10-21): L0 normalised SO on the 16 REAL per-slice SM shares ot_s81_su_sms (-DSU_SMU_T, the share every
// dsdv_svc_rs instantiates; cfg_g = the slice's tile = head g).  Images: tools/s81_dv/layer_prog/svc/so_bench.py.
//   qcyc / qwd   the SMJ q words (SE kind 4 frame of lower_svc + the SO programme of lower_svc.so_frames: SMJ kind 5 +
//                16 operand frames = 534 words, operand payload = the REAL ALLQ P.V words of tb_svc_lower, transposed)
//   secyc/serow  the SE operand rows of every slice (the REAL svc SE assembler rows of the same tb_svc_lower run)
//   eexp / oexp  expected SE e rows (fixture attn.exp FP32) and SO o rows (fixture attn.normalize.unrope BF16)
// Every slice decodes the q words exactly as dsdv_svc_att.sv (frame parser; SMJ: sm_st = hdr[0], sm_kind = hdr[4:1],
// sm_jid = hdr[12:5]; payload: sm_rv = !hdr[13] || hdr[14 + tile], sm_rp = !hdr[13], sm_rj = payload index, sm_rd = word).
// ONE real SM share replays the job 16 times (pass g: reset, cfg_g = tile = g; Verilator frontend memory of 16
// flattened hard clusters exceeded 24 GB).  PASS = per head 8 SE rows (addr SE obase + 16 n + g, mask FFFF, data = attn.exp) and 32 SO rows (addr SO obase + 8 k
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
    // ---------------- passes: head g = 0..15, each from reset, q / SE rows at qcyc + pb (never early, never late)
    integer g = 0, pb = 100, qi = 0, si = 0, late = 0, se_r = 0;
    reg q_v = 0; reg [511:0] q_d = 0; reg se_v = 0;
    reg [3:0] tile = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        q_v <= 0; se_v <= 0;
        if (cyc == pb - 20) rst <= 0;
        if (cyc == pb - 10) rst <= 1;
        if (qi < NQ && cyc == qcyc[qi] + pb) begin q_v <= 1; q_d <= qwd[qi]; qi = qi + 1; end
        else if (qi < NQ && cyc > qcyc[qi] + pb) late = late + 1;
        if (si < NV && cyc == secyc[si] + pb) begin se_v <= 1; se_r <= si; si = si + 1; end
    end
    // ---------------- dsdv_svc_att frame parser + SMJ decode (tile = g of the pass)
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
    reg sm_st, sm_rv, sm_rp, opr; reg [3:0] sm_kind; reg [7:0] sm_jid; reg [2:0] sm_rj; reg [511:0] sm_rd;
    always @(posedge clk or negedge rst) begin
        if (!rst) begin sm_st <= 0; sm_rv <= 0; sm_rp <= 0; sm_rj <= 0; sm_kind <= 0; sm_jid <= 0; sm_rd <= 0; opr <= 0; end
        else begin
            sm_st <= 1'b0; sm_rv <= 1'b0; opr <= 1'b0;
            if (hdr_mine && h_type == 4'd9) begin sm_st <= q_d[0]; sm_kind <= q_d[4:1]; sm_jid <= q_d[12:5]; end
            if (pay_mine && f_type == 4'd9) begin
                sm_rv <= !f_hdr[13] || f_hdr[14 + tile]; sm_rp <= !f_hdr[13]; sm_rj <= 3'(f_idx); sm_rd <= q_d;
                opr <= f_hdr[13] && f_hdr[14 + tile];
            end
            if (se_v) begin sm_rv <= 1'b1; sm_rp <= 1'b0; sm_rj <= 3'd0; sm_rd <= serow[tile * NV + se_r]; end
        end
    end
    wire w_v, o_fu, o_fo, o_al, o_den; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [7:0] o_rj;
    ot_s81_su_sms #(.MUT(0)) u_sms (
        .clk(clk), .rst_in(rst), .cfg_g(tile), .j_st(sm_st), .j_kind(sm_kind), .j_jid(sm_jid),
        .r_v(sm_rv), .r_p(sm_rp), .r_j(sm_rj), .r_d(sm_rd),
        .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_al), .o_den(o_den), .o_rjid(o_rj));
    // ---------------- checks
    integer nrow = 0, err = 0, se_chk = 0, so_chk = 0, lat = -1, lat_bad = 0, rope_err = 0, plain_err = 0, rows_bad = 0;
    integer opq [$];
    reg [15:0] den_seen = 0, fu = 0, fo = 0;
    always @(posedge clk) begin
        if (opr) opq.push_back(cyc);
        if (o_den && rst) den_seen[tile] = 1'b1;
        if (w_v) begin
            if (nrow < NV) begin
                se_chk = se_chk + 1;
                if (w_m !== 16'hFFFF || w_a !== 14'(SE_OB + 16 * nrow + tile) || w_d !== eexp[tile * NV + nrow]) begin
                    err = err + 1;
                    if (err < 10) $display("SE ROW MISMATCH head %0d row %0d a %0h m %0h", tile, nrow, w_a, w_m);
                end
            end else begin
                integer k, x; reg [255:0] hv; k = nrow - NV;
                so_chk = so_chk + 1;
                hv = tile[0] ? w_d[511:256] : w_d[255:0];
                if (k >= 32 || w_m !== (tile[0] ? 16'hFF00 : 16'h00FF) || w_a !== 14'(SO_OB + 8 * k + tile / 2) ||
                    hv !== oexp[tile * 32 + k]) begin
                    err = err + 1;
                    if (k >= 28) rope_err = rope_err + 1; else plain_err = plain_err + 1;
                    if (err < 10) $display("SO ROW MISMATCH head %0d row %0d (dims %0d..%0d) a %0h m %0h got %064h exp %064h",
                                           tile, k, 16 * k, 16 * k + 15, w_a, w_m, hv, oexp[tile * 32 + k]);
                end
                if (opq.size() == 0) lat_bad = lat_bad + 1;
                else begin x = cyc - opq.pop_front(); if (lat < 0) lat = x; else if (x != lat) lat_bad = lat_bad + 1; end
            end
            nrow = nrow + 1;
        end
        if (rst && cyc == pb + qcyc[NQ - 1] + 400) begin            // end of pass g
            if (nrow != NV + 32) rows_bad = rows_bad + 1;
            fu[tile] = o_fu; fo[tile] = o_fo;
            if (qi != NQ) late = late + 1;
            if (tile == 4'd15) begin
                $display("SOGOLD se_checked=%0d so_checked=%0d errors=%0d rope_row_errors=%0d plain_row_errors=%0d rows_bad=%0d so_latency=%0d lat_bad=%0d den_mask=%04x fu=%04x fo=%04x late_q=%0d cycles=%0d verdict=%s",
                    se_chk, so_chk, err, rope_err, plain_err, rows_bad, lat, lat_bad, den_seen, fu, fo, late, cyc,
                    (err == 0 && rows_bad == 0 && se_chk == 16 * NV && so_chk == 16 * 32 && lat_bad == 0 && lat > 0 &&
                     den_seen == 16'hFFFF && fu == 0 && fo == 0 && late == 0) ? "PASS" : "FAIL");
                $finish;
            end
            tile <= tile + 1'b1; nrow = 0; qi = 0; si = 0; opq.delete(); pb = cyc + 60;
        end
    end
endmodule
